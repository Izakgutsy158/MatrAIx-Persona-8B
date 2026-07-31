"""Tests for CLI persona retrieval helpers."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = REPO_ROOT / "application" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
if str(REPO_ROOT / "application" / "playground") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "application" / "playground"))

from persona_retrieval import (  # noqa: E402
    build_retrieval_plan,
    parse_filter_args,
    parse_filters_json,
    retrieve_personas,
)


def test_parse_filter_args_multi_value() -> None:
    assert parse_filter_args(
        ["age_bracket=25-34,35-44", "life_stage=Mid-life"]
    ) == {
        "age_bracket": ["25-34", "35-44"],
        "life_stage": ["Mid-life"],
    }


def test_parse_filters_json() -> None:
    assert parse_filters_json('{"age_bracket":["25-34"],"region":"North America"}') == {
        "age_bracket": ["25-34"],
        "region": ["North America"],
    }


def test_build_retrieval_plan_applies_task_strategy(tmp_path: Path) -> None:
    task_dir = tmp_path / "application" / "tasks" / "demo-task"
    task_dir.mkdir(parents=True)
    (task_dir / "persona_strategy.json").write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "pool": "persona/datasets/matraix-persona-dev-sample",
                "defaultMode": "stratified",
                "sources": ["wiki"],
                "dimensionFilters": {"age_bracket": ["25-34", "35-44"]},
                "stratifyFields": ["age_bracket"],
                "sampleSize": 4,
                "seed": 7,
            }
        ),
        encoding="utf-8",
    )

    plan = build_retrieval_plan(
        task_path="application/tasks/demo-task",
        repo_root=tmp_path,
        default_pool="persona/datasets/other",
    )
    assert plan.persona_pool == "persona/datasets/matraix-persona-dev-sample"
    assert plan.sources == ["wiki"]
    assert plan.dimension_filters == {"age_bracket": ["25-34", "35-44"]}
    assert plan.stratify_fields == ["age_bracket"]
    assert plan.sample_size == 4
    assert plan.seed == 7


def test_cli_filters_override_strategy_keys(tmp_path: Path) -> None:
    task_dir = tmp_path / "application" / "tasks" / "demo-task"
    task_dir.mkdir(parents=True)
    (task_dir / "persona_strategy.json").write_text(
        json.dumps(
            {
                "dimensionFilters": {
                    "age_bracket": ["25-34"],
                    "region": ["North America"],
                },
                "sources": ["wiki"],
            }
        ),
        encoding="utf-8",
    )

    plan = build_retrieval_plan(
        task_path="application/tasks/demo-task",
        repo_root=tmp_path,
        default_pool="persona/datasets/matraix-persona-dev-sample",
        filters={"age_bracket": ["45-54"]},
        sources=["amazon"],
        sample_size=2,
        seed=1,
        stratify_fields=[],
    )
    assert plan.dimension_filters == {
        "age_bracket": ["45-54"],
        "region": ["North America"],
    }
    assert plan.sources == ["amazon"]
    assert plan.stratify_fields == []


def test_retrieve_personas_filters_dev_sample() -> None:
    plan = build_retrieval_plan(
        task_path="application/tasks/example-survey_product-feedback",
        repo_root=REPO_ROOT,
        default_pool="persona/datasets/matraix-persona-dev-sample",
        dataset="persona/datasets/matraix-persona-dev-sample",
        sample_size=3,
        seed=42,
        filters={"age_bracket": ["25-34"]},
        stratify_fields=[],
        use_strategy=False,
    )
    result = retrieve_personas(
        plan,
        repo_root=REPO_ROOT,
        task_path="application/tasks/example-survey_product-feedback",
    )
    assert len(result.persona_ids) == 3
    assert result.matched_count >= 3
    assert result.persona_pool.endswith("matraix-persona-dev-sample")
