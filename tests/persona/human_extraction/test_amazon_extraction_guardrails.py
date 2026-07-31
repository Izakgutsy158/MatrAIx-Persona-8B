from __future__ import annotations

import importlib
import sys
import types


def _load_amazon_module():
    sys.modules.setdefault("pandas", types.SimpleNamespace())
    sys.modules.setdefault(
        "vllm",
        types.SimpleNamespace(
            LLM=object,
            SamplingParams=lambda *args, **kwargs: None,
        ),
    )
    return importlib.import_module(
        "persona.human_extraction.scripts.run_extraction_amazon"
    )


def _dimensions() -> list[dict]:
    return [
        {
            "id": "age_bracket",
            "label": "Age bracket",
            "category": "Demographic: Core",
            "description": "Life-age band of the persona.",
            "values": ["18-24", "25-34", "35-44", "45-54"],
        },
        {
            "id": "topic_cooking",
            "label": "Interest: Cooking",
            "category": "Interests: Topics",
            "description": "Interest in cooking.",
            "values": ["Passionate", "Interested", "Neutral", "Indifferent", "Averse"],
        },
        {
            "id": "lstyle_smoking",
            "label": "Smoking / vaping",
            "category": "Interests: Culture",
            "description": "Smoking or vaping pattern.",
            "values": ["Never", "Former", "Occasional", "Regular"],
        },
    ]


def test_amazon_prompt_requires_schema_only_conservative_output():
    mod = _load_amazon_module()

    prompt = mod.build_amazon_prompt(
        "Title: Great skillet\nI bought this as a gift for my nephew.",
        _dimensions(),
    )

    assert "Do not output any field_id that is not listed" in prompt
    assert "Do not duplicate field_id" in prompt
    assert "Do not omit assignment_type" in prompt
    assert 'Never use "Unsupported", "unsupported", "Not applicable"' in prompt
    assert "Sensitive / high-risk fields require explicit self-statements" in prompt
    assert "Do not infer these fields from product category" in prompt
    assert "If you cannot copy an exact quote, return unsupported" in prompt


def test_sanitize_fields_enforces_schema_contract_and_exact_evidence():
    mod = _load_amazon_module()
    profile_text = (
        "Title: Dutch oven\nI cook stews every weekend and compare recipes.\n"
        "Title: Pan\nThis pan went to my nephew for his apartment."
    )
    raw_fields = [
        {
            "field_id": "topic_cooking",
            "value": "Interested",
            "confidence": 0.7,
            "evidence": "I cook stews every weekend",
            "description": "Regularly reviews cooking gear.",
            "assignment_type": "summary_inference",
        },
        {
            "field_id": "topic_cooking",
            "value": "Passionate",
            "confidence": 0.9,
            "evidence": "The reviewer has strong cooking interests.",
            "description": "This is a model summary, not a quote.",
            "assignment_type": "summary_inference",
        },
        {
            "field_id": "age_bracket",
            "value": "35-44",
            "confidence": 0.85,
            "evidence": "This pan went to my nephew",
            "description": "Infers age from nephew reference.",
        },
        {
            "field_id": "lstyle_smoking",
            "value": "unsupported",
            "confidence": 0.5,
            "evidence": "No evidence",
            "description": "Bad enum value.",
            "assignment_type": "unsupported",
        },
        {
            "field_id": "sport_hunting",
            "value": "Interested",
            "confidence": 0.8,
            "evidence": "I hunt for deals",
            "description": "Unknown schema field.",
            "assignment_type": "summary_inference",
        },
    ]

    fields = mod.sanitize_fields(raw_fields, _dimensions(), profile_text)

    assert [field["field_id"] for field in fields] == [
        "age_bracket",
        "topic_cooking",
        "lstyle_smoking",
    ]
    assert fields[0] == {
        "field_id": "age_bracket",
        "value": None,
        "confidence": 0.0,
        "evidence": "",
        "description": "",
        "assignment_type": "unsupported",
    }
    assert fields[1] == {
        "field_id": "topic_cooking",
        "value": "Interested",
        "confidence": 0.7,
        "evidence": "I cook stews every weekend",
        "description": "Regularly reviews cooking gear.",
        "assignment_type": "summary_inference",
    }
    assert fields[2]["value"] is None
    assert fields[2]["assignment_type"] == "unsupported"
