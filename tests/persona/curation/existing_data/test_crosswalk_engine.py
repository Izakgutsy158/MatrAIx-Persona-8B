"""Unit tests for the rule-based crosswalk engine (observed layer).

Locks the faithfulness contract: case-insensitive mapping, deliberate-null vs
unmapped tracking, NaN/None skipping, and the hard guarantees that a mapped value
must be schema-allowed and a crosswalk may not target an unknown dimension.
"""

import pytest
from persona.curation.existing_data.scripts.crosswalk_engine import (
    apply_crosswalk,
    load_allowed,
)

ALLOWED = {
    "gender_identity": {"Man", "Woman", "Non-binary"},
    "age_bracket": {"25-34", "35-44"},
    "demo_marital_status": {"Single", "Married"},
    "bio_free_text": set(),  # free-text dim: no allowed-value constraint
}


def _crosswalk():
    return {
        "gender_identity": {
            "src": "sex",
            "map": {"male": "Man", "female": "Woman"},
            "prov": "observed",
        },
        "age_bracket": {
            "compute": lambda r: "25-34" if 25 <= int(r.get("age", 0)) <= 34 else None,
            "prov": "observed",
        },
        # 'divorced' is present in the source but intentionally not mapped -> null
        "demo_marital_status": {
            "src": "marital",
            "map": {"single": "Single", "divorced": None},
            "prov": "observed",
        },
    }


def test_basic_map():
    obs, prov, unmapped = apply_crosswalk({"sex": "Male"}, _crosswalk(), ALLOWED)
    assert obs["gender_identity"] == "Man"
    assert prov["gender_identity"] == "observed"
    assert unmapped == {}


@pytest.mark.parametrize("raw", ["male", "MALE", " Male "])
def test_case_and_whitespace_insensitive(raw):
    obs, _, _ = apply_crosswalk({"sex": raw}, _crosswalk(), ALLOWED)
    assert obs["gender_identity"] == "Man"


def test_compute_rule_hit_and_miss():
    obs, _, _ = apply_crosswalk({"age": 30}, _crosswalk(), ALLOWED)
    assert obs["age_bracket"] == "25-34"
    obs, _, _ = apply_crosswalk({"age": 50}, _crosswalk(), ALLOWED)  # compute -> None
    assert "age_bracket" not in obs


def test_deliberate_none_is_null_not_unmapped():
    obs, _, unmapped = apply_crosswalk({"marital": "Divorced"}, _crosswalk(), ALLOWED)
    assert "demo_marital_status" not in obs
    assert "demo_marital_status" not in unmapped  # mapped to None on purpose


def test_unmapped_source_value_is_recorded():
    obs, _, unmapped = apply_crosswalk({"sex": "genderqueer"}, _crosswalk(), ALLOWED)
    assert "gender_identity" not in obs
    assert unmapped["gender_identity"] == "genderqueer"


@pytest.mark.parametrize("missing", [None, float("nan")])
def test_none_and_nan_source_skipped(missing):
    obs, _, unmapped = apply_crosswalk({"sex": missing}, _crosswalk(), ALLOWED)
    assert "gender_identity" not in obs
    assert "gender_identity" not in unmapped


def test_off_allowed_value_raises():
    bad = {"gender_identity": {"src": "sex", "map": {"male": "Dude"}}}
    with pytest.raises(ValueError):
        apply_crosswalk({"sex": "male"}, bad, ALLOWED)


def test_unknown_target_dim_raises():
    with pytest.raises(KeyError):
        apply_crosswalk(
            {"x": "y"}, {"not_a_dim": {"src": "x", "map": {"y": "z"}}}, ALLOWED
        )


def test_callable_map_supported():
    cw = {
        "gender_identity": {
            "src": "sex",
            "map": lambda k: "Man" if k.startswith("m") else "Woman",
        }
    }
    obs, _, _ = apply_crosswalk({"sex": "masc"}, cw, ALLOWED)
    assert obs["gender_identity"] == "Man"


def test_provenance_defaults_to_observed():
    cw = {"gender_identity": {"src": "sex", "map": {"male": "Man"}}}  # no 'prov' key
    _, prov, _ = apply_crosswalk({"sex": "male"}, cw, ALLOWED)
    assert prov["gender_identity"] == "observed"


def test_empty_allowed_set_skips_value_validation():
    cw = {"bio_free_text": {"src": "bio", "map": lambda k: k}}
    obs, _, _ = apply_crosswalk({"bio": "anything at all"}, cw, ALLOWED)
    assert obs["bio_free_text"] == "anything at all"


def test_load_allowed(tmp_path):
    schema = tmp_path / "dims.json"
    schema.write_text(
        '{"dimensions":[{"id":"gender_identity","values":["Man","Woman"]},'
        '{"id":"bio","values":null}]}'
    )
    allowed = load_allowed(str(schema))
    assert allowed["gender_identity"] == {"Man", "Woman"}
    assert allowed["bio"] == set()  # null values -> empty (free-text)
