"""Verifier for the cog_verbosity chatbot probe.

Presence-checks transcript.json, then measures how verbose the CUSTOMER (the
persona) was across their turns — mean words per customer message. Terse vs
Rambling personas should differ here. The metric is a convenience signal; the
primary judgement is intended to be an LLM-judge over the customer turns.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

OUTPUT_DIR = Path(
    os.environ.get("HARBOR_OUTPUT_DIR")
    or os.environ.get("MATRIX_OUTPUT_DIR")
    or "/app/output"
)
TRANSCRIPT_PATH = OUTPUT_DIR / "transcript.json"


def _verifier_dir() -> Path:
    explicit = os.environ.get("HARBOR_VERIFIER_DIR")
    if explicit:
        path = Path(explicit)
        path.mkdir(parents=True, exist_ok=True)
        return path
    container_default = Path("/logs/verifier")
    try:
        container_default.mkdir(parents=True, exist_ok=True)
        return container_default
    except OSError:
        pass
    raise RuntimeError(
        "HARBOR_VERIFIER_DIR is required when running outside a Harbor trial container."
    )


def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def main() -> int:
    if not TRANSCRIPT_PATH.is_file():
        return fail("missing /app/output/transcript.json")
    try:
        data = json.loads(TRANSCRIPT_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        return fail("transcript.json is not valid JSON: {}".format(exc))
    if not isinstance(data, dict):
        return fail("transcript.json must contain an object")
    messages = data.get("messages")
    if not isinstance(messages, list) or not messages:
        return fail("transcript.messages must be a non-empty list")

    customer_turns: list[str] = []
    for entry in messages:
        if not isinstance(entry, dict):
            return fail("each transcript message must be an object")
        if entry.get("role") not in {"customer", "support"}:
            return fail("invalid transcript message role")
        content = entry.get("content")
        if not isinstance(content, str) or not content.strip():
            return fail("message content must be a non-empty string")
        if entry.get("role") == "customer":
            customer_turns.append(content.strip())

    if not customer_turns:
        return fail("transcript has no customer turns")

    words = [len(t.split()) for t in customer_turns]
    chars = [len(t) for t in customer_turns]
    total_words = sum(words)
    mean_words = round(total_words / len(words), 2)
    mean_chars = round(sum(chars) / len(chars), 2)

    contexts: list[dict[str, object]] = []
    for i, turn in enumerate(customer_turns, start=1):
        contexts.append(
            {
                "key": "customer_turn.{}".format(i),
                "label": "Customer turn {}".format(i),
                "contextType": "customer_message",
                "facets": [
                    {"key": "text", "label": "Message", "role": "primary", "kind": "textual", "value": turn},
                    {"key": "word_count", "label": "Words", "role": "score", "kind": "numerical", "value": len(turn.split())},
                ],
            }
        )
    contexts.append(
        {
            "key": "verbosity.summary",
            "label": "Verbosity summary",
            "contextType": "trial_summary",
            "facets": [
                {"key": "customer_turns", "label": "Customer turns", "role": "score", "kind": "numerical", "value": len(customer_turns)},
                {"key": "total_words", "label": "Total customer words", "role": "score", "kind": "numerical", "value": total_words},
                {"key": "mean_words_per_turn", "label": "Mean words per customer turn", "role": "score", "kind": "numerical", "value": mean_words},
                {"key": "mean_chars_per_turn", "label": "Mean chars per customer turn", "role": "score", "kind": "numerical", "value": mean_chars},
            ],
        }
    )

    fields = [
        {"key": "verbosity.summary.mean_words_per_turn", "label": "Mean words per customer turn",
         "group": "verbosity.summary", "role": "score", "kind": "numerical", "value": mean_words},
        {"key": "verbosity.summary.total_words", "label": "Total customer words",
         "group": "verbosity.summary", "role": "score", "kind": "numerical", "value": total_words},
    ]

    (_verifier_dir() / "structured_output.json").write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "artifactType": "matraix.trial_evaluation",
                "taskType": "chatbot",
                "presenceCheck": {
                    "passed": True,
                    "requiredArtifacts": ["transcript.json"],
                    "missingArtifacts": [],
                },
                "sourceArtifacts": {"transcript": "/app/output/transcript.json"},
                "contexts": contexts,
                "fields": fields,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
