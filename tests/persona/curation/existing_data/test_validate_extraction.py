"""Smoke tests for the extraction validator (the gate every shard must pass).

Confirms a clean shard returns 0, an off-allowed value returns non-zero, and gzip
shards are accepted -- exercising the real `validate()` entry point. The validator
lives under `persona/human_extraction/scripts/` (not an importable package), so it
is loaded directly from its file.
"""

import gzip
import importlib.util
import json
from argparse import Namespace
from pathlib import Path

_VALIDATOR = (
    Path(__file__).resolve().parents[4]
    / "persona"
    / "human_extraction"
    / "scripts"
    / "validate_extraction.py"
)
_spec = importlib.util.spec_from_file_location("validate_extraction", _VALIDATOR)
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)

SCHEMA = {
    "dimensions": [
        {"id": "age_bracket", "values": ["25-34", "35-44"]},
        {"id": "gender_identity", "values": ["Man", "Woman"]},
    ]
}


def _field(fid, value, at="direct"):
    return {
        "field_id": fid,
        "value": value,
        "confidence": 1.0 if value else 0.0,
        "evidence": "",
        "description": "",
        "assignment_type": at,
    }


def _args(shard, schema):
    return Namespace(input=str(shard), schema=str(schema), profiles=None, strict=False)


def _schema_file(tmp_path):
    sp = tmp_path / "dims.json"
    sp.write_text(json.dumps(SCHEMA))
    return sp


def test_valid_shard_passes(tmp_path):
    rec = {
        "user_id": "u1",
        "fields": [_field("age_bracket", "25-34"), _field("gender_identity", "Woman")],
    }
    shard = tmp_path / "shard.jsonl"
    shard.write_text(json.dumps(rec) + "\n")
    assert V.validate(_args(shard, _schema_file(tmp_path))) == 0


def test_off_allowed_value_fails(tmp_path):
    rec = {
        "user_id": "u1",
        "fields": [_field("age_bracket", "25-34"), _field("gender_identity", "Alien")],
    }
    shard = tmp_path / "shard.jsonl"
    shard.write_text(json.dumps(rec) + "\n")
    assert V.validate(_args(shard, _schema_file(tmp_path))) == 1


def test_gzip_shard_supported(tmp_path):
    rec = {
        "user_id": "u1",
        "fields": [_field("age_bracket", "25-34"), _field("gender_identity", "Woman")],
    }
    shard = tmp_path / "shard.jsonl.gz"
    with gzip.open(shard, "wt") as f:
        f.write(json.dumps(rec) + "\n")
    assert V.validate(_args(shard, _schema_file(tmp_path))) == 0
