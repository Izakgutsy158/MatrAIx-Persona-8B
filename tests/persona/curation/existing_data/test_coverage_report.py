"""Unit tests for the coverage/quality reporter.

Confirms `summarize()` separates non-null from *grounded* (direct/structured/summary)
attributions and ignores fields outside the schema.
"""

from persona.curation.existing_data.scripts.coverage_report import (
    GROUNDED_AT,
    summarize,
)


def test_summarize_separates_nonnull_from_grounded():
    allowed = {"a": {"X"}, "b": {"Y"}, "c": {"Z"}}
    categories = {"a": "demo", "b": "demo", "c": "trait"}
    records = [
        {
            "fields": [
                {"field_id": "a", "value": "X", "assignment_type": "direct"},
                {"field_id": "b", "value": None, "assignment_type": "unsupported"},
                {"field_id": "c", "value": "Z", "assignment_type": "unsupported"},
            ]
        }
    ]
    s = summarize(records, allowed, categories)
    assert s["personas"] == 1
    assert s["avg_nonnull"] == 2.0  # a + c
    assert s["avg_grounded"] == 1.0  # only a (direct)


def test_summarize_ignores_unknown_fields():
    allowed = {"a": {"X"}}
    records = [
        {
            "fields": [
                {"field_id": "a", "value": "X", "assignment_type": "direct"},
                {
                    "field_id": "not_in_schema",
                    "value": "Q",
                    "assignment_type": "direct",
                },
            ]
        }
    ]
    s = summarize(records, allowed, {"a": "demo"})
    assert s["avg_nonnull"] == 1.0


def test_grounded_set_is_the_three_supported_types():
    assert GROUNDED_AT == {"direct", "structured_claim", "summary_inference"}
