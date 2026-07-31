#!/usr/bin/env python3
"""Compare current vs stricter Amazon extraction prompts on one fixed example.

The script can use either a small dimension slice or the full
persona/schema/dimensions.json schema, and calls OpenRouter with the Qwen3.6
35B A3B model. It intentionally does not use the production data path or vLLM,
so it can run on a laptop.
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DIMENSIONS_JSON = REPO_ROOT / "persona/schema/dimensions.json"
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "qwen/qwen3.6-35b-a3b"

DIMENSION_IDS = [
    "age_bracket",
    "gender_identity",
    "socioeconomic_band",
    "demo_parental_status",
    "lstyle_pet_ownership",
    "topic_pets",
    "topic_cooking",
    "lstyle_cooking_freq",
    "pref_quality_vs_quantity",
    "lstyle_shopping_style",
    "cog_detail_orientation",
    "cog_verbosity",
    "val_family",
    "health_general_health",
    "domain",
]

REVIEWER_HISTORY = """Amazon reviewer profile - 8 reviews across 5 categories.

[2022-01-14] Pet Supplies | B09DOGFOOD | rating=5/5 | verified=True
Title: My dog finally likes dinner
My senior dog is picky, but she eats this kibble without fuss. I like that the ingredient list is simple and the bag seals well.

[2022-03-02] Kitchen | B08CHEFKNIFE | rating=5/5 | verified=True
Title: Sharp and comfortable for weekly meal prep
I cook at home most weekends, and this knife made chopping vegetables much faster. Good weight, no hand fatigue.

[2022-06-19] Home & Kitchen | B07COFFEESCALE | rating=4/5 | verified=True
Title: Precise enough for pour-over
I use this every morning for coffee. The timer and gram measurements are accurate, though the buttons feel a little cheap.

[2022-10-05] Toys & Games | B00BUILDSET | rating=5/5 | verified=True
Title: Gift for my nephew
Bought this for my nephew's birthday. He loved building it with his parents, but I cannot comment on long-term durability.

[2023-01-11] Electronics | B09USBC | rating=3/5 | verified=True
Title: Works, but not sturdy
The cable charges my tablet, but the connector got loose after a month. I would rather pay a few dollars more for better build quality.

[2023-03-28] Pet Supplies | B07DOGTOY | rating=4/5 | verified=True
Title: Durable toy
My dog destroys most plush toys in a day. This one lasted about three weeks, so I will probably reorder.

[2023-07-07] Grocery | B00COFFEEBEANS | rating=5/5 | verified=True
Title: Great beans for home brewing
Balanced flavor, not too oily, and consistent from bag to bag. I use them for my morning pour-over.

[2023-11-20] Kitchen | B09CASTIRON | rating=4/5 | verified=True
Title: Heavy but reliable
This pan is heavy, but it gives a great sear and cleans up well when seasoned correctly. Good value if you actually cook often.
"""


def load_dimensions() -> list[dict[str, Any]]:
    schema = json.load(open(DIMENSIONS_JSON, encoding="utf-8"))
    by_id = {d["id"]: d for d in schema["dimensions"]}
    return [by_id[dim_id] for dim_id in DIMENSION_IDS]


def load_all_dimensions() -> list[dict[str, Any]]:
    schema = json.load(open(DIMENSIONS_JSON, encoding="utf-8"))
    return list(schema["dimensions"])


def dimension_chunks(dimensions: list[dict[str, Any]], per_chunk: int) -> list[list[dict[str, Any]]]:
    by_category: dict[str, list[dict[str, Any]]] = {}
    for dim in dimensions:
        by_category.setdefault(dim.get("category", "Uncategorized"), []).append(dim)

    chunks = []
    for cat_dims in by_category.values():
        for idx in range(0, len(cat_dims), per_chunk):
            chunks.append(cat_dims[idx : idx + per_chunk])
    return chunks


def dimension_lines(dimensions: list[dict[str, Any]]) -> list[str]:
    lines = []
    for dim in dimensions:
        allowed = " | ".join(str(v) for v in dim.get("values", [])) or "(free value)"
        desc = str(dim.get("description", "")).strip()
        lines.append(
            f"- {dim['id']} - {dim.get('label', dim['id'])} - {desc} - [{allowed}]"
        )
    return lines


def build_current_prompt(profile_text: str, dimensions: list[dict[str, Any]]) -> str:
    lines = [
        "You are building a persona for a single Amazon shopper from their "
        "complete product-review history.",
        "",
        "The input is a chronological list of that ONE person's reviews. Each "
        "review has a date, product category, product id (ASIN), star rating, a "
        "verified-purchase flag, a title, and body text. Infer who this shopper "
        "is from the WHOLE history together:",
        "- WHAT they buy: product categories and specific items reveal interests, "
        "hobbies, life stage, household, budget, and needs.",
        "- HOW they write: tone, length, detail, sentiment, and vocabulary reveal "
        "personality, values, and writing style.",
        "- WHAT they say: facts a reviewer states about themselves (\"as a "
        "nurse\", \"for my kids\", \"at 65 I...\") are the strongest signal.",
        "",
        "Return ONLY JSON with this shape (no markdown, no commentary):",
        '{"fields": [{"field_id": "<one id from DIMENSIONS below>", '
        '"value": "<one allowed value, copied verbatim, or null>", '
        '"confidence": 0.0, '
        '"evidence": "<short quote copied verbatim from one review>", '
        '"description": "<1-2 sentence description of this shopper for this attribute>", '
        '"assignment_type": "direct"}]}',
        "",
        "assignment_type values (Amazon context):",
        "- direct: the reviewer explicitly states it about themselves in a review.",
        "- structured_claim: strongly implied by concrete purchase facts (e.g. "
        "repeatedly buying baby products -> has a young child).",
        "- summary_inference: a softer inference from the overall pattern, tone, "
        "or writing style across many reviews.",
        "- unsupported: not supported by the reviews.",
        "",
        "Rules:",
        "- Emit exactly one object per dimension listed below.",
        "- value MUST be exactly one of that dimension's allowed values (copied "
        "verbatim), OR null.",
        "- Judge the history as a whole; prefer attributes backed by MULTIPLE "
        "reviews over a single purchase (one-off items may be gifts for others).",
        "- If the reviews do not support a dimension, set value to null, "
        'assignment_type to "unsupported", and description to "".',
        "- Every non-null value MUST include a short evidence quote copied "
        "verbatim from one of the reviews.",
        "- description: 1-2 concrete sentences describing THIS shopper for this "
        "attribute using details from their reviews (categories, products, "
        "statements). Describe the person; do not justify the label.",
        "- Be conservative with sensitive attributes (age, gender, health, "
        "ethnicity, religion, income): assign only when clearly stated or very "
        "strongly implied; otherwise null/unsupported.",
        "- Return valid JSON only, with no markdown.",
        "",
        "DIMENSIONS (field_id - label - description - allowed values):",
        *dimension_lines(dimensions),
        "",
        "REVIEWER HISTORY:",
        profile_text,
    ]
    return "\n".join(lines)


def build_strict_prompt(profile_text: str, dimensions: list[dict[str, Any]]) -> str:
    lines = [
        "You are auditing persona-schema dimensions for evidence in one Amazon "
        "reviewer's history. Your goal is high recall for truly supported "
        "attributes and zero unsupported claims.",
        "",
        "Important: emitting one field object is bookkeeping, not permission to "
        "fill the attribute. For every dimension, start from value=null and "
        'assignment_type="unsupported". Change value only when the evidence '
        "passes the rules below.",
        "",
        "Return ONLY JSON with this shape (no markdown, no commentary):",
        '{"fields": [{"field_id": "<one id from DIMENSIONS below>", '
        '"value": "<one allowed value, copied verbatim, or null>", '
        '"confidence": 0.0, '
        '"evidence": "<verbatim quote(s) plus support count, or empty string>", '
        '"description": "<1-2 concrete sentences, or empty string>", '
        '"assignment_type": "direct|structured_claim|summary_inference|unsupported"}]}',
        "",
        "Evidence rules:",
        "- direct: requires an explicit self-statement by the reviewer. Use for "
        "sensitive or identity/life-status claims.",
        "- structured_claim: requires concrete purchase/review facts from at "
        "least 2 distinct reviews, unless the reviewer states the claim directly.",
        "- summary_inference: requires a repeated pattern across at least 3 "
        "distinct reviews. Use only for non-sensitive interests, shopping "
        "preferences, review style, product-use patterns, or expertise signals.",
        "- unsupported: use when evidence is absent, one-off, ambiguous, "
        "gift-related, generic, or could describe someone other than the reviewer.",
        "",
        "Hard limits:",
        "- For age, gender, health, disability, ethnicity, religion, politics, "
        "income, family/household status, occupation, location, employment, and "
        "parenthood: assign a non-null value only from an explicit self-statement. "
        "Do not use product category alone.",
        "- Do not attribute traits of gift recipients or other product users to "
        "the reviewer. A gift may support shopping behavior, not the reviewer's "
        "own identity, household, or hobbies.",
        "- Generic praise like \"great product\" or product titles alone is not "
        "diagnostic evidence for persona attributes.",
        "",
        "Output rules:",
        "- Emit exactly one object per dimension listed below.",
        "- value MUST be exactly one of that dimension's allowed values, copied "
        "verbatim, OR null.",
        "- If value is null: assignment_type must be unsupported, confidence 0.0, "
        'evidence "", and description "".',
        "- Every non-null value must include quote(s) that directly support that "
        "specific allowed value and must mention the number of supporting reviews.",
        "- Most dimensions can be unsupported. Do not make the persona complete.",
        "",
        "DIMENSIONS (field_id - label - description - allowed values):",
        *dimension_lines(dimensions),
        "",
        "REVIEWER HISTORY:",
        profile_text,
    ]
    return "\n".join(lines)


def build_medium_a_prompt(profile_text: str, dimensions: list[dict[str, Any]]) -> str:
    """Medium-conservative prompt: explicit-only sensitive claims, repeated signals otherwise."""
    lines = [
        "You are extracting persona-schema dimensions from one Amazon reviewer's "
        "review history. Be evidence-grounded and conservative, but do not omit "
        "clear non-sensitive patterns that are repeatedly supported.",
        "",
        "Return ONLY JSON with this shape (no markdown, no commentary):",
        '{"fields": [{"field_id": "<one id from DIMENSIONS below>", '
        '"value": "<one allowed value, copied verbatim, or null>", '
        '"confidence": 0.0, '
        '"evidence": "<short verbatim quote(s), or empty string>", '
        '"description": "<1-2 concrete sentences, or empty string>", '
        '"assignment_type": "direct|structured_claim|summary_inference|unsupported"}]}',
        "",
        "Evidence rules:",
        "- direct: use when the reviewer explicitly states the fact about "
        "themselves in review text.",
        "- structured_claim: use for concrete non-sensitive facts supported by "
        "at least 2 distinct reviews, products, or category clusters.",
        "- summary_inference: use for non-sensitive preferences, interests, "
        "shopping behavior, review style, or expertise when supported by at "
        "least 2 distinct reviews and no stronger assignment type fits.",
        "- unsupported: use when evidence is absent, one-off, ambiguous, generic, "
        "gift-related, or mainly about someone other than the reviewer.",
        "",
        "Sensitive and life-status limits:",
        "- For age, gender, health, disability, ethnicity, religion, politics, "
        "income, family/household status, occupation, location, employment, and "
        "parenthood: assign a non-null value only from an explicit self-statement. "
        "Do not infer these from product categories, product titles, or gifts.",
        "- Gift purchases can support shopping behavior only; do not treat gift "
        "recipients as the reviewer's household, hobbies, or identity.",
        "",
        "Output rules:",
        "- Emit exactly one object per dimension listed below.",
        "- value MUST be exactly one of that dimension's allowed values, copied "
        "verbatim, OR null.",
        "- If value is null: assignment_type must be unsupported, confidence 0.0, "
        'evidence "", and description "".',
        "- Every non-null value must cite evidence that supports that specific "
        "allowed value. Prefer multiple reviews when available.",
        "- It is normal for many dimensions to be unsupported.",
        "",
        "DIMENSIONS (field_id - label - description - allowed values):",
        *dimension_lines(dimensions),
        "",
        "REVIEWER HISTORY:",
        profile_text,
    ]
    return "\n".join(lines)


def build_medium_b_prompt(profile_text: str, dimensions: list[dict[str, Any]]) -> str:
    """Medium-conservative prompt: separates observable behavior from identity claims."""
    lines = [
        "You are mapping observable Amazon review evidence to persona-schema "
        "dimensions. Fill attributes that are well supported by the review "
        "history, and leave unsupported or identity-like claims null.",
        "",
        "Return ONLY JSON with this shape (no markdown, no commentary):",
        '{"fields": [{"field_id": "<one id from DIMENSIONS below>", '
        '"value": "<one allowed value, copied verbatim, or null>", '
        '"confidence": 0.0, '
        '"evidence": "<short verbatim quote(s), or empty string>", '
        '"description": "<1-2 concrete sentences, or empty string>", '
        '"assignment_type": "direct|structured_claim|summary_inference|unsupported"}]}',
        "",
        "Allowed support:",
        "- Explicit self-statements may support any dimension when the stated "
        "fact directly matches the allowed value.",
        "- Repeated owned/use-context statements may support non-sensitive "
        "lifestyle and interest dimensions (for example, repeated 'my dog' "
        "reviews can support dog ownership).",
        "- Repeated product-review behavior may support non-sensitive shopping "
        "preferences, topic interests, communication style, and domain expertise.",
        "- Overall writing style may support communication/cognitive-style "
        "dimensions only when the pattern is visible across at least 5 reviews.",
        "",
        "Not allowed:",
        "- Do not infer demographic, protected, health, political, religious, "
        "family, occupation, location, income, or employment dimensions unless "
        "the reviewer explicitly says them.",
        "- Do not infer personality inventories, values, worldview, MBTI, Big "
        "Five, HEXACO, or clinical/mental-state attributes from ordinary shopping "
        "reviews unless the reviewer explicitly describes the trait or belief.",
        "- Do not use a single purchase, generic praise, star rating, or product "
        "title alone as enough evidence.",
        "- Do not attribute a gift recipient's traits to the reviewer.",
        "",
        "Output rules:",
        "- Emit exactly one object per dimension listed below.",
        "- value MUST be exactly one of that dimension's allowed values, copied "
        "verbatim, OR null.",
        "- If value is null: assignment_type must be unsupported, confidence 0.0, "
        'evidence "", and description "".',
        "- Every non-null value must cite quote(s) or concrete repeated review "
        "facts that support the selected allowed value.",
        "- Prefer unsupported over a plausible but weak persona guess.",
        "",
        "DIMENSIONS (field_id - label - description - allowed values):",
        *dimension_lines(dimensions),
        "",
        "REVIEWER HISTORY:",
        profile_text,
    ]
    return "\n".join(lines)


PROMPT_BUILDERS = {
    "current": build_current_prompt,
    "medium_a": build_medium_a_prompt,
    "medium_b": build_medium_b_prompt,
    "strict": build_strict_prompt,
}


def call_openrouter(prompt: str, args: argparse.Namespace, label: str) -> str:
    payload = {
        "model": args.model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "top_p": 1.0,
        "max_tokens": args.max_tokens,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        args.base_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {os.environ[args.api_key_env]}",
            "Content-Type": "application/json",
            "X-Title": "MatrAIx Amazon prompt comparison",
        },
        method="POST",
    )
    for attempt in range(args.retries):
        try:
            print(
                f"Calling OpenRouter for {label} "
                f"(attempt {attempt + 1}/{args.retries}, model={args.model})...",
                flush=True,
            )
            with urllib.request.urlopen(req, timeout=args.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            choices = data.get("choices") or []
            if not choices:
                raise RuntimeError(f"OpenRouter response had no choices: {data}")
            message = choices[0].get("message") or {}
            content = message.get("content")
            if content is None:
                raise RuntimeError(
                    "OpenRouter response message had content=null. "
                    f"Finish reason: {choices[0].get('finish_reason')!r}. "
                    f"Message keys: {sorted(message)}. "
                    f"Full response: {json.dumps(data, ensure_ascii=False)[:2000]}"
                )
            return content
        except urllib.error.HTTPError as err:
            body = err.read().decode("utf-8", errors="replace")
            if err.code in {408, 429, 500, 502, 503, 504} and attempt < args.retries - 1:
                time.sleep(min(60, 2 ** attempt))
                continue
            raise RuntimeError(f"OpenRouter API error {err.code}: {body[:1000]}") from err


def parse_fields(text: str) -> list[dict[str, Any]]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return []
    obj = json.loads(text[start : end + 1])
    fields = obj.get("fields")
    return fields if isinstance(fields, list) else []


def summarize(label: str, fields: list[dict[str, Any]]) -> None:
    non_null = [f for f in fields if f.get("value") is not None]
    unsupported = [f for f in fields if f.get("assignment_type") == "unsupported"]
    print(f"\n## {label}")
    print(f"fields={len(fields)} non_null={len(non_null)} unsupported={len(unsupported)}")
    for f in fields:
        print(
            f"- {f.get('field_id')}: value={f.get('value')!r} "
            f"type={f.get('assignment_type')!r} conf={f.get('confidence')!r}"
        )
        ev = str(f.get("evidence") or "")
        if ev:
            print(f"  evidence: {ev[:220]}")


def summarize_compact(label: str, fields: list[dict[str, Any]]) -> None:
    non_null = [f for f in fields if f.get("value") is not None]
    unsupported = [f for f in fields if f.get("assignment_type") == "unsupported"]
    print(f"{label}: fields={len(fields)} non_null={len(non_null)} unsupported={len(unsupported)}")
    print(
        f"{label} non_null_ids="
        + ",".join(str(f.get("field_id", "")) for f in non_null)
    )


def write_checkpoint(
    path: Path,
    *,
    model: str,
    dimension_ids: list[str],
    chunks: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "model": model,
                "dimension_ids": dimension_ids,
                "reviewer_history": REVIEWER_HISTORY,
                "chunks": chunks,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def run_chunked(args: argparse.Namespace, dimensions: list[dict[str, Any]]) -> int:
    chunks = dimension_chunks(dimensions, args.max_dims_per_chunk)
    print(
        f"running prompts={args.prompt} dimensions={len(dimensions)} "
        f"chunks={len(chunks)} max_dims_per_chunk={args.max_dims_per_chunk}",
        flush=True,
    )
    prompt_builders = selected_prompt_builders(args.prompt)

    chunk_rows: list[dict[str, Any]] = []
    for chunk_index, chunk in enumerate(chunks, start=1):
        row: dict[str, Any] = {
            "chunk_index": chunk_index,
            "dimension_ids": [dim["id"] for dim in chunk],
            "results": {},
        }
        for label, builder in prompt_builders:
            text = call_openrouter(
                builder(REVIEWER_HISTORY, chunk),
                args,
                f"{label} prompt chunk {chunk_index}/{len(chunks)}",
            )
            fields = parse_fields(text)
            row["results"][label] = {"raw": text, "fields": fields}
            summarize_compact(f"{label} chunk {chunk_index}/{len(chunks)}", fields)
            write_checkpoint(
                args.write_json,
                model=args.model,
                dimension_ids=[dim["id"] for dim in dimensions],
                chunks=chunk_rows + [row],
            )
        chunk_rows.append(row)

    for label, _builder in prompt_builders:
        fields = [
            field
            for row in chunk_rows
            for field in row["results"].get(label, {}).get("fields", [])
        ]
        summarize_compact(f"{label} total", fields)
    print(f"wrote {args.write_json}")
    return 0


def selected_prompt_builders(prompt: str) -> list[tuple[str, Any]]:
    if prompt == "all":
        return list(PROMPT_BUILDERS.items())
    if prompt == "both":
        return [
            ("current", build_current_prompt),
            ("strict", build_strict_prompt),
        ]
    return [(prompt, PROMPT_BUILDERS[prompt])]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=OPENROUTER_MODEL)
    parser.add_argument("--base-url", default=OPENROUTER_CHAT_URL)
    parser.add_argument("--api-key-env", default="OPENROUTER_API_KEY")
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--write-json", type=Path, default=Path("/tmp/amazon_prompt_ab.json"))
    parser.add_argument("--dry-run-prompts", action="store_true")
    parser.add_argument("--all-dimensions", action="store_true")
    parser.add_argument("--chunked", action="store_true")
    parser.add_argument("--max-dims-per-chunk", type=int, default=25)
    parser.add_argument(
        "--prompt",
        choices=("both", "all", "current", "medium_a", "medium_b", "strict"),
        default="both",
    )
    args = parser.parse_args()

    dimensions = load_all_dimensions() if args.all_dimensions else load_dimensions()

    if args.chunked:
        if not os.environ.get(args.api_key_env):
            raise RuntimeError(f"{args.api_key_env} is not set")
        return run_chunked(args, dimensions)

    prompt_builders = selected_prompt_builders(args.prompt)

    if args.dry_run_prompts:
        for index, (label, builder) in enumerate(prompt_builders):
            if index:
                print()
            print(f"===== {label.upper()} PROMPT =====")
            print(builder(REVIEWER_HISTORY, dimensions))
        return 0

    if not os.environ.get(args.api_key_env):
        raise RuntimeError(f"{args.api_key_env} is not set")

    results = {}
    for label, builder in prompt_builders:
        text = call_openrouter(builder(REVIEWER_HISTORY, dimensions), args, f"{label} prompt")
        fields = parse_fields(text)
        results[label] = {"raw": text, "fields": fields}
        summarize(f"{label} prompt", fields)

    args.write_json.write_text(
        json.dumps(
            {
                "model": args.model,
                "dimension_ids": [dim["id"] for dim in dimensions],
                "reviewer_history": REVIEWER_HISTORY,
                **results,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"\nwrote {args.write_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
