from persona.human_extraction.scripts import run_one_amazon_openrouter
from persona.human_extraction.scripts import compare_amazon_prompts_openrouter


def test_amazon_openrouter_prompt_defaults_to_unsupported_and_blocks_sensitive_guessing():
    prompt = run_one_amazon_openrouter.build_amazon_prompt(
        "REVIEWER HISTORY TEXT",
        [
            {
                "id": "age_bracket",
                "label": "Age bracket",
                "description": "Age range.",
                "values": ["18-24", "25-34"],
            },
            {
                "id": "domain",
                "label": "Domain",
                "description": "Interest or expertise domain.",
                "values": ["Cooking", "Books"],
            },
        ],
    )

    assert 'start from value=null and assignment_type="unsupported"' in prompt
    assert "non-null value only from an explicit self-statement" in prompt
    assert "Do not use product category alone" in prompt
    assert "at least 2 distinct reviews" in prompt
    assert "at least 5 reviews" in prompt
    assert "Do not output any field_id that is not listed" in prompt
    assert "If you cannot copy an exact quote, return unsupported" in prompt
    assert "Do not append support counts" in prompt
    assert "Most dimensions can be unsupported. Do not make the persona complete." in prompt
    assert "a softer inference from the overall pattern" not in prompt
    assert "plus support count" not in prompt


def test_medium_amazon_prompt_variants_keep_sensitive_and_personality_guards():
    dimensions = [
        {
            "id": "demo_parental_status",
            "label": "Parenthood",
            "description": "Parenthood status.",
            "values": ["Not a parent", "Parent of minors"],
        },
        {
            "id": "mbti_type",
            "label": "MBTI type",
            "description": "MBTI-like personality type.",
            "values": ["INTJ", "ESFP"],
        },
        {
            "id": "topic_cooking",
            "label": "Cooking",
            "description": "Interest in cooking.",
            "values": ["Interested", "Not interested"],
        },
    ]

    medium_a = compare_amazon_prompts_openrouter.build_medium_a_prompt(
        "REVIEWER HISTORY TEXT", dimensions
    )
    medium_b = compare_amazon_prompts_openrouter.build_medium_b_prompt(
        "REVIEWER HISTORY TEXT", dimensions
    )

    assert "at least 2 distinct reviews" in medium_a
    assert "only from an explicit self-statement" in medium_a
    assert "It is normal for many dimensions to be unsupported." in medium_a
    assert "ordinary shopping reviews" in medium_b
    assert "MBTI, Big Five, HEXACO" in medium_b
    assert "Prefer unsupported over a plausible but weak persona guess." in medium_b
