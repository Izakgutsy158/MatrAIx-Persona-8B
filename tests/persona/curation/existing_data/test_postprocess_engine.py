"""Unit tests for the §8 post-processor (faithfulness normalizer).

These lock the guarantees the whole extraction standard relies on: off-allowed and
null values are nulled, argument-from-absence and non-verbatim inferences are demoted
(value kept, evidence dropped), never-emitted dims become null, the exact observed
overlay wins, and the output is always schema-clean and full-length.
"""

import pytest
from persona.curation.existing_data.scripts.postprocess_engine import (
    SUPPORTED_AT,
    load_schema,
    normalize,
)

ORDER = [
    "age_bracket",
    "gender_identity",
    "demo_veteran_status",
    "trait_openness",
    "urbanicity",
]
ALLOWED = {
    "age_bracket": {"25-34"},
    "gender_identity": {"Man", "Woman"},
    "demo_veteran_status": {"Civilian", "Veteran"},
    "trait_openness": {"High", "Low"},
    "urbanicity": {"Urban", "Rural"},
}
PROFILE = "A 25-34-year-old woman. She loves trying new things and travel."


def _f(fid, value, evidence="", at="direct", conf=0.9):
    return {
        "field_id": fid,
        "value": value,
        "confidence": conf,
        "evidence": evidence,
        "description": "",
        "assignment_type": at,
    }


def _by(out):
    return {f["field_id"]: f for f in out}


def test_output_is_full_length_and_ordered():
    out = normalize([], ORDER, ALLOWED)
    assert [f["field_id"] for f in out] == ORDER


def test_never_emitted_dim_is_null_unsupported():
    out = _by(normalize([], ORDER, ALLOWED))
    assert out["urbanicity"]["value"] is None
    assert out["urbanicity"]["assignment_type"] == "unsupported"


def test_grounded_positive_kept():
    out = _by(
        normalize(
            [_f("gender_identity", "Woman", "A 25-34-year-old woman.", "direct")],
            ORDER,
            ALLOWED,
            profile_text=PROFILE,
        )
    )
    assert out["gender_identity"]["value"] == "Woman"
    assert out["gender_identity"]["assignment_type"] == "direct"
    assert out["gender_identity"]["evidence"]


def test_grounded_inference_kept():
    out = _by(
        normalize(
            [
                _f(
                    "trait_openness",
                    "High",
                    "loves trying new things",
                    "summary_inference",
                )
            ],
            ORDER,
            ALLOWED,
            profile_text=PROFILE,
        )
    )
    assert out["trait_openness"]["value"] == "High"
    assert out["trait_openness"]["assignment_type"] == "summary_inference"


def test_off_allowed_value_nulled():
    out = _by(
        normalize(
            [_f("age_bracket", "999", "A 25-34-year-old woman.")],
            ORDER,
            ALLOWED,
            profile_text=PROFILE,
        )
    )
    assert out["age_bracket"]["value"] is None
    assert out["age_bracket"]["assignment_type"] == "unsupported"


@pytest.mark.parametrize("value", [None, "", "null"])
def test_null_like_value_nulled(value):
    out = _by(
        normalize(
            [_f("gender_identity", value, "A 25-34-year-old woman.")],
            ORDER,
            ALLOWED,
            profile_text=PROFILE,
        )
    )
    assert out["gender_identity"]["value"] is None
    assert out["gender_identity"]["assignment_type"] == "unsupported"


@pytest.mark.parametrize(
    "evidence",
    [
        "No mention of military service",
        "no indication of veteran status",
        "There is no record of service",
        "not explicitly stated",
        "absence of any military reference",
    ],
)
def test_argument_from_absence_demoted(evidence):
    # valid allowed value, but justified by absence -> demoted; evidence dropped; value KEPT
    out = _by(
        normalize(
            [_f("demo_veteran_status", "Civilian", evidence, "direct")], ORDER, ALLOWED
        )
    )
    f = out["demo_veteran_status"]
    assert f["assignment_type"] == "unsupported"
    assert f["evidence"] == ""
    assert f["value"] == "Civilian"  # demoted, not deleted


def test_non_verbatim_inference_demoted_when_profile_given():
    out = _by(
        normalize(
            [
                _f(
                    "trait_openness",
                    "High",
                    "she is a thrill-seeking skydiver",
                    "summary_inference",
                )
            ],
            ORDER,
            ALLOWED,
            profile_text=PROFILE,
        )
    )
    assert out["trait_openness"]["assignment_type"] == "unsupported"
    assert out["trait_openness"]["evidence"] == ""


def test_without_profile_only_absence_regex_demotes():
    out = _by(
        normalize(
            [_f("trait_openness", "High", "enjoys novelty", "summary_inference")],
            ORDER,
            ALLOWED,
        )
    )
    assert out["trait_openness"]["assignment_type"] == "summary_inference"


def test_observed_overlay_overrides_junk():
    out = _by(
        normalize(
            [_f("age_bracket", "999", "junk")],
            ORDER,
            ALLOWED,
            observed={"age_bracket": "25-34"},
        )
    )
    f = out["age_bracket"]
    assert f["value"] == "25-34"
    assert f["assignment_type"] == "direct"
    assert f["confidence"] == 1.0


def test_observed_overlay_ignores_off_allowed():
    out = _by(normalize([], ORDER, ALLOWED, observed={"age_bracket": "not-a-bracket"}))
    assert out["age_bracket"]["value"] is None


def test_output_is_schema_clean():
    fields = [
        _f("age_bracket", "999"),
        _f("gender_identity", "Woman", "A 25-34-year-old woman."),
        _f("demo_veteran_status", "Civilian", "no mention of service"),
    ]
    out = normalize(
        fields, ORDER, ALLOWED, profile_text=PROFILE, observed={"age_bracket": "25-34"}
    )
    for f in out:
        assert (
            f["value"] is None or f["value"] in ALLOWED[f["field_id"]]
        )  # never off-allowed
        assert f["assignment_type"] in SUPPORTED_AT | {"unsupported"}


def test_load_schema(tmp_path):
    schema = tmp_path / "dims.json"
    schema.write_text(
        '{"dimensions":[{"id":"age_bracket","values":["25-34"]},{"id":"bio","values":null}]}'
    )
    order, allowed = load_schema(str(schema))
    assert order == ["age_bracket", "bio"]
    assert allowed["age_bracket"] == {"25-34"}
    assert allowed["bio"] == set()
