#!/usr/bin/env python3
"""Run one Amazon reviewer persona extraction through OpenRouter.

This is a laptop-friendly runner for prepared top-reviewer history JSONL files.
It avoids pandas/vLLM and uses the current Amazon extraction prompt from
run_extraction_amazon.py.
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

REVIEW_TMPL = (
    "[{date}] {category} | {parent_asin} | rating={rating}/5 | "
    "verified={verified}\nTitle: {title}\n{text}"
)


def load_one_history(path: Path, user_index: int) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        for idx, line in enumerate(fh):
            if idx == user_index:
                return json.loads(line)
    raise ValueError(f"user index {user_index} not found in {path}")


def assemble_profile(history: dict[str, Any], max_chars: int) -> str:
    reviews = sorted(history.get("reviews", []), key=lambda r: r.get("timestamp") or 0)
    categories = {r.get("category") or "Unknown" for r in reviews}
    parts = []
    for r in reviews:
        parts.append(
            REVIEW_TMPL.format(
                date=r.get("date") or "",
                category=r.get("category") or "Unknown",
                parent_asin=r.get("parent_asin") or r.get("asin") or "",
                rating=r.get("rating") if r.get("rating") is not None else "",
                verified=bool(r.get("verified_purchase")),
                title=r.get("title") or "",
                text=r.get("text") or "",
            )
        )
    header = (
        f"Amazon reviewer profile - {len(reviews)} reviews across "
        f"{len(categories)} categories.\n\n"
    )
    return (header + "\n\n".join(parts))[:max_chars]


def dimension_lines(dimensions: list[dict[str, Any]]) -> list[str]:
    lines = []
    for dim in dimensions:
        allowed = " | ".join(str(v) for v in dim.get("values", [])) or "(free value)"
        desc = str(dim.get("description", "")).strip()
        lines.append(
            f"- {dim['id']} - {dim.get('label', dim['id'])} - {desc} - [{allowed}]"
        )
    return lines


def build_amazon_prompt(profile_text: str, dimensions: list[dict[str, Any]]) -> str:
    """Current Amazon-reviewer persona-extraction prompt."""
    lines = [
        "You are mapping observable Amazon review evidence to schema-constrained "
        "persona fields for one reviewer. Fill attributes that are well supported "
        "by the review history, and leave unsupported or identity-like claims null.",
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
        '"evidence": "<one short exact quote copied from REVIEWER HISTORY, or empty string>", '
        '"description": "<1-2 concrete sentences, or empty string>", '
        '"assignment_type": "direct|structured_claim|summary_inference|unsupported"}]}',
        "",
        "Allowed support:",
        "- direct: use when the reviewer explicitly states the fact about "
        "themselves in review text.",
        "- structured_claim: use for repeated owned/use-context statements or "
        "concrete non-sensitive purchase/review facts supported by at least 2 "
        "distinct reviews, products, or category clusters.",
        "- summary_inference: use for non-sensitive interests, shopping behavior, "
        "preferences, review style, communication style, or expertise when a "
        "repeated pattern is visible across the review history.",
        "- Overall writing style may support communication/cognitive-style "
        "dimensions only when the pattern is visible across at least 5 reviews.",
        "- unsupported: use when evidence is absent, one-off, ambiguous, generic, "
        "gift-related, or mainly about someone other than the reviewer.",
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
        "- Do not infer personality inventories, values, worldview, MBTI, Big "
        "Five, HEXACO, clinical attributes, or mental-state attributes from "
        "ordinary shopping reviews unless the reviewer explicitly states the "
        "trait or belief.",
        "",
        "Output rules:",
        "- Emit exactly one object per dimension listed below.",
        "- Do not output any field_id that is not listed in DIMENSIONS.",
        "- Do not duplicate field_id. Each listed field_id appears exactly once.",
        "- Do not omit assignment_type. Every object must include one of the four "
        "assignment_type strings above.",
        "- value MUST be exactly one of that dimension's allowed values, copied "
        "verbatim, OR null.",
        '- Never use "Unsupported", "unsupported", "Not applicable", "N/A", '
        '"unknown", or "" as value unless that exact string appears in that '
        "field's allowed values.",
        "- If value is null: assignment_type must be unsupported, confidence 0.0, "
        'evidence "", and description "".',
        "- Every non-null value MUST include a short evidence quote copied "
        "verbatim from one of the reviews.",
        "- Evidence must be an exact quote from REVIEWER HISTORY, not your reasoning, "
        "a paraphrase, or a summary. If you cannot copy an exact quote, return "
        "unsupported.",
        "- If you cannot copy an exact quote, return unsupported.",
        "- Do not append support counts, explanations, or labels to evidence. "
        "Evidence must be only text that appears in REVIEWER HISTORY.",
        "- Most dimensions can be unsupported. Do not make the persona complete.",
        "",
        "DIMENSIONS (field_id - label - description - allowed values):",
        *dimension_lines(dimensions),
        "",
        "REVIEWER HISTORY:",
        profile_text,
    ]
    return "\n".join(lines)


def load_dimension_chunks(path: Path, per_chunk: int, max_chunks: int) -> list[list[dict[str, Any]]]:
    schema_doc = json.load(path.open(encoding="utf-8"))
    by_category: dict[str, list[dict[str, Any]]] = {}
    for dim in schema_doc["dimensions"]:
        by_category.setdefault(dim.get("category", "Uncategorized"), []).append(dim)

    chunks = []
    for cat_dims in by_category.values():
        for i in range(0, len(cat_dims), per_chunk):
            chunks.append(cat_dims[i : i + per_chunk])
            if max_chunks and len(chunks) >= max_chunks:
                return chunks
    return chunks


def parse_fields(text: str) -> list[dict[str, Any]]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return []
    obj = json.loads(text[start : end + 1])
    fields = obj.get("fields")
    return fields if isinstance(fields, list) else []


def call_openrouter(prompt: str, args: argparse.Namespace, label: str) -> str:
    payload: dict[str, Any] = {
        "model": args.model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "top_p": 1.0,
        "max_tokens": args.max_tokens,
    }
    if args.response_format:
        payload["response_format"] = {"type": "json_object"}

    req = urllib.request.Request(
        args.base_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {os.environ[args.api_key_env]}",
            "Content-Type": "application/json",
            "X-Title": "MatrAIx one Amazon persona extraction",
        },
        method="POST",
    )
    for attempt in range(args.retries):
        try:
            print(
                f"Calling OpenRouter {label} "
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

    raise RuntimeError("OpenRouter request exhausted retries")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-histories", type=Path, required=True)
    parser.add_argument("--user-index", type=int, default=0)
    parser.add_argument("--dimensions", type=Path, default=DIMENSIONS_JSON)
    parser.add_argument("--model", default=OPENROUTER_MODEL)
    parser.add_argument("--base-url", default=OPENROUTER_CHAT_URL)
    parser.add_argument("--api-key-env", default="OPENROUTER_API_KEY")
    parser.add_argument("--max-dims-per-chunk", type=int, default=50)
    parser.add_argument("--max-chunks", type=int, default=0)
    parser.add_argument("--max-profile-chars", type=int, default=48000)
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--response-format", action="store_true")
    parser.add_argument("--write-json", type=Path, default=Path("/tmp/amazon_one_persona_openrouter.json"))
    parser.add_argument("--dry-run-prompt", action="store_true")
    args = parser.parse_args()

    if not os.environ.get(args.api_key_env) and not args.dry_run_prompt:
        raise RuntimeError(f"{args.api_key_env} is not set")

    history = load_one_history(args.user_histories, args.user_index)
    profile_text = assemble_profile(history, args.max_profile_chars)
    chunks = load_dimension_chunks(args.dimensions, args.max_dims_per_chunk, args.max_chunks)
    print(
        f"user_id={history.get('user_id')} reviews={len(history.get('reviews', []))} "
        f"profile_chars={len(profile_text)} chunks={len(chunks)}",
        flush=True,
    )

    if args.dry_run_prompt:
        print(build_amazon_prompt(profile_text, chunks[0]))
        return 0

    all_fields: list[dict[str, Any]] = []
    raw_outputs = []
    for i, chunk in enumerate(chunks, start=1):
        prompt = build_amazon_prompt(profile_text, chunk)
        text = call_openrouter(prompt, args, f"chunk {i}/{len(chunks)}")
        raw_outputs.append({"chunk_index": i, "dimension_ids": [d["id"] for d in chunk], "raw": text})
        fields = parse_fields(text)
        all_fields.extend(fields)
        print(f"chunk {i}/{len(chunks)} parsed_fields={len(fields)}", flush=True)

    result = {
        "user_id": history.get("user_id"),
        "source": str(args.user_histories),
        "model": args.model,
        "field_count": len(all_fields),
        "non_null_field_count": sum(1 for field in all_fields if field.get("value") is not None),
        "fields": all_fields,
        "raw_outputs": raw_outputs,
    }
    args.write_json.parent.mkdir(parents=True, exist_ok=True)
    args.write_json.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        "summary: "
        f"field_count={result['field_count']} "
        f"non_null_field_count={result['non_null_field_count']}",
        flush=True,
    )
    print(f"wrote {args.write_json}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
