"""CLI helpers: Playground-parity persona retrieval for job generators.

Wraps ``PersonaPoolService.sample_pool`` / ``resolve_cohort_launch`` so Harbor
job scripts can use sources, dimension filters, task ``persona_strategy.json``,
cohorts, and matraix-persona-1m sampling.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PersonaRetrievalPlan:
    """Resolved sampling inputs after merging CLI flags + optional strategy."""

    persona_pool: str
    sample_size: int
    seed: int
    sources: list[str] = field(default_factory=list)
    dimension_filters: dict[str, list[str]] = field(default_factory=dict)
    stratify_fields: list[str] = field(default_factory=list)
    sample_size_per_value_group: int | None = None
    cohort_id: str | None = None
    persona_ids: list[str] = field(default_factory=list)
    strategy_path: str | None = None


@dataclass
class PersonaRetrievalResult:
    persona_pool: str
    persona_ids: list[str]
    matched_count: int
    sample_size: int
    seed: int
    sources: list[str]
    dimension_filters: dict[str, list[str]]
    stratify_fields: list[str]
    cohort_id: str | None = None
    strategy_path: str | None = None


def parse_filter_args(raw_filters: list[str] | None) -> dict[str, list[str]]:
    """Parse ``--filter dim=value`` / ``--filter dim=a,b`` into multi-value maps."""
    out: dict[str, list[str]] = {}
    for item in raw_filters or []:
        text = str(item).strip()
        if not text:
            continue
        if "=" not in text:
            raise ValueError(
                f"invalid --filter {text!r}; expected dim=value or dim=a,b"
            )
        key, _, value = text.partition("=")
        dim = key.strip().removeprefix("dimensions.").strip()
        if not dim:
            raise ValueError(f"invalid --filter {text!r}; empty dimension id")
        values = [part.strip() for part in value.split(",") if part.strip()]
        if not values:
            raise ValueError(f"invalid --filter {text!r}; empty value list")
        bucket = out.setdefault(dim, [])
        for val in values:
            if val not in bucket:
                bucket.append(val)
    return out


def parse_filters_json(raw: str | None) -> dict[str, list[str]]:
    if not raw or not str(raw).strip():
        return {}
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("--filters-json must be a JSON object")
    out: dict[str, list[str]] = {}
    for key, value in payload.items():
        dim = str(key).strip().removeprefix("dimensions.").strip()
        if not dim:
            continue
        if isinstance(value, list):
            vals = [str(item).strip() for item in value if str(item).strip()]
        else:
            text = str(value).strip()
            vals = [text] if text else []
        if vals:
            out[dim] = vals
    return out


def load_task_strategy(
    task_path: str,
    *,
    repo_root: Path,
    strategy_path: str | Path | None = None,
    enabled: bool = True,
) -> tuple[dict[str, Any] | None, str | None]:
    """Load strategy JSON. Returns ``(payload, relative_path)``."""
    if not enabled:
        return None, None
    from backend.service.persona_strategy import (
        load_persona_strategy,
        normalize_persona_strategy,
    )

    if strategy_path:
        path = Path(strategy_path)
        if not path.is_absolute():
            path = repo_root / path
        if not path.is_file():
            raise FileNotFoundError(f"strategy file not found: {strategy_path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"strategy file must be a JSON object: {strategy_path}")
        normalized = normalize_persona_strategy(payload)
        try:
            rel = str(path.relative_to(repo_root))
        except ValueError:
            rel = str(path)
        return normalized, rel

    task_dir = repo_root / task_path.strip().replace("\\", "/").strip("/")
    strategy = load_persona_strategy(task_dir)
    if strategy is None:
        return None, None
    return strategy, f"{task_path.strip().strip('/')}/persona_strategy.json"


def build_retrieval_plan(
    *,
    task_path: str,
    repo_root: Path,
    default_pool: str,
    persona_ids: list[str] | None = None,
    sample_size: int | None = None,
    seed: int | None = None,
    dataset: str | None = None,
    sources: list[str] | None = None,
    filters: dict[str, list[str]] | None = None,
    stratify_fields: list[str] | None = None,
    sample_size_per_value_group: int | None = None,
    cohort_id: str | None = None,
    use_strategy: bool = True,
    strategy_path: str | None = None,
) -> PersonaRetrievalPlan:
    """Merge CLI args with optional task ``persona_strategy.json`` defaults."""
    strategy, strategy_rel = load_task_strategy(
        task_path,
        repo_root=repo_root,
        strategy_path=strategy_path,
        enabled=use_strategy,
    )
    strategy = strategy or {}

    cli_ids = [value.strip() for value in (persona_ids or []) if value.strip()]
    strategy_cohort = str(strategy.get("cohortId") or "").strip() or None
    resolved_cohort = (cohort_id or "").strip() or strategy_cohort

    strategy_filters = {
        str(key): [str(v) for v in (value if isinstance(value, list) else [value])]
        for key, value in dict(strategy.get("dimensionFilters") or {}).items()
    }
    cli_filters = dict(filters or {})
    # Strategy defaults, then CLI replaces any overlapping dimension keys entirely.
    merged_filters = dict(strategy_filters)
    for key, values in cli_filters.items():
        merged_filters[key] = list(values)

    strategy_sources = [str(s).strip() for s in (strategy.get("sources") or []) if str(s).strip()]
    cli_sources = [str(s).strip() for s in (sources or []) if str(s).strip()]
    resolved_sources = cli_sources if cli_sources else strategy_sources

    strategy_stratify = [
        str(field).strip() for field in (strategy.get("stratifyFields") or []) if str(field).strip()
    ]
    if stratify_fields is not None:
        resolved_stratify = [
            str(field).strip() for field in stratify_fields if str(field).strip()
        ]
    else:
        default_mode = str(strategy.get("defaultMode") or "").strip().lower()
        if default_mode == "stratified" or strategy_stratify:
            resolved_stratify = strategy_stratify
        else:
            resolved_stratify = []

    resolved_pool = (
        (dataset or "").strip()
        or str(strategy.get("pool") or "").strip()
        or default_pool
    )
    resolved_seed = seed if seed is not None else int(strategy.get("seed") or 42)

    strategy_sample = strategy.get("sampleSize")
    resolved_sample = (
        sample_size
        if sample_size is not None
        else (int(strategy_sample) if isinstance(strategy_sample, int) else 1)
    )
    if resolved_sample < 1:
        resolved_sample = 1

    strategy_per_cell = strategy.get("sampleSizePerValueGroup")
    resolved_per_cell = sample_size_per_value_group
    if resolved_per_cell is None and isinstance(strategy_per_cell, int):
        resolved_per_cell = strategy_per_cell

    return PersonaRetrievalPlan(
        persona_pool=resolved_pool,
        sample_size=resolved_sample,
        seed=resolved_seed,
        sources=resolved_sources,
        dimension_filters=merged_filters,
        stratify_fields=resolved_stratify,
        sample_size_per_value_group=resolved_per_cell,
        cohort_id=resolved_cohort,
        persona_ids=cli_ids,
        strategy_path=strategy_rel,
    )


def retrieve_personas(
    plan: PersonaRetrievalPlan,
    *,
    repo_root: Path,
    task_path: str | None = None,
) -> PersonaRetrievalResult:
    """Run Playground pool retrieval and return concrete persona ids + pool."""
    from backend.service.persona_pool_service import PersonaPoolService

    service = PersonaPoolService.from_repo(repo_root=repo_root)

    if plan.persona_ids:
        return PersonaRetrievalResult(
            persona_pool=plan.persona_pool,
            persona_ids=list(plan.persona_ids),
            matched_count=len(plan.persona_ids),
            sample_size=len(plan.persona_ids),
            seed=plan.seed,
            sources=list(plan.sources),
            dimension_filters=dict(plan.dimension_filters),
            stratify_fields=list(plan.stratify_fields),
            cohort_id=plan.cohort_id,
            strategy_path=plan.strategy_path,
        )

    if plan.cohort_id:
        resolved = service.resolve_cohort_launch(
            plan.cohort_id,
            sample_size_override=plan.sample_size,
        )
        persona_ids = [str(pid) for pid in (resolved.get("personaIds") or []) if str(pid).strip()]
        if not persona_ids:
            raise ValueError(f"cohort {plan.cohort_id!r} resolved to zero personas")
        return PersonaRetrievalResult(
            persona_pool=str(resolved.get("pool") or plan.persona_pool),
            persona_ids=persona_ids,
            matched_count=len(persona_ids),
            sample_size=len(persona_ids),
            seed=int(resolved.get("seed") or plan.seed),
            sources=[str(s) for s in (resolved.get("sources") or plan.sources)],
            dimension_filters={
                str(k): [str(v) for v in (vals if isinstance(vals, list) else [vals])]
                for k, vals in dict(resolved.get("dimensionFilters") or plan.dimension_filters).items()
            },
            stratify_fields=list(plan.stratify_fields),
            cohort_id=str(resolved.get("cohortId") or plan.cohort_id),
            strategy_path=plan.strategy_path,
        )

    sampled = service.sample_pool(
        persona_pool=plan.persona_pool,
        sample_size=plan.sample_size,
        seed=plan.seed,
        sources=plan.sources or None,
        dimension_filters=plan.dimension_filters or None,
        stratify_fields=plan.stratify_fields or None,
        sample_size_per_value_group=plan.sample_size_per_value_group,
        task_path=task_path,
    )
    persona_ids = [str(pid) for pid in (sampled.get("personaIds") or []) if str(pid).strip()]
    if not persona_ids:
        raise ValueError("persona retrieval returned zero personas")
    return PersonaRetrievalResult(
        persona_pool=str(sampled.get("pool") or plan.persona_pool),
        persona_ids=persona_ids,
        matched_count=int(sampled.get("matchedCount") or len(persona_ids)),
        sample_size=int(sampled.get("sampleSize") or len(persona_ids)),
        seed=int(sampled.get("seed") or plan.seed),
        sources=list(plan.sources),
        dimension_filters=dict(plan.dimension_filters),
        stratify_fields=list(sampled.get("stratifyFields") or plan.stratify_fields),
        cohort_id=plan.cohort_id,
        strategy_path=plan.strategy_path,
    )
