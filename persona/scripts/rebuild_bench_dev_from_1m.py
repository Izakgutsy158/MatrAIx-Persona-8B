#!/usr/bin/env python3
"""Rebuild ``matraix-persona-dev-sample`` as 200 personas sampled from MatrAIx Persona 1M.

Samples evenly across 1M ``source`` values (source diversify), remaps to
``persona_0001`` … ``persona_0200``, and rewrites the pool directory so it
contains exactly those 200 YAML files.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
for path in (
    REPO_ROOT,
    REPO_ROOT / "application" / "playground",
    REPO_ROOT / "src",
    REPO_ROOT / "environment" / "runtime",
    REPO_ROOT / "packages" / "playground" / "src",
):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)

from backend.service.persona_1m_index import (  # noqa: E402
    Persona1MIndex,
    resolve_index_dir,
)
from backend.service.persona_1m_pool import (  # noqa: E402
    HF_1M_REPO,
    _parquet_row_counts,
    _read_decoded_rows_at_global,
    load_codec,
    resolve_1m_paths,
)
from matraix.persona_display_name import synthetic_display_name  # noqa: E402

DEFAULT_OUT = REPO_ROOT / "persona" / "datasets" / "matraix-persona-dev-sample"
DEFAULT_COUNT = 200
DEFAULT_SEED = 42
CARD_DIMENSIONS = (
    "age_bracket",
    "region",
    "domain",
    "intent",
    "life_stage",
)
# Prefer human-grounded sources when handing out remainder slots.
SOURCE_PRIORITY = (
    "wiki",
    "stackoverflow",
    "amazon",
    "gss",
    "real_human_survey",
    "prism",
    "synthetic",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _allocate_per_source(sources: list[str], total: int) -> dict[str, int]:
    if not sources:
        raise ValueError("no sources available")
    base = total // len(sources)
    rem = total % len(sources)
    alloc = {source: base for source in sources}
    for source in SOURCE_PRIORITY:
        if rem <= 0:
            break
        if source in alloc:
            alloc[source] += 1
            rem -= 1
    # Any leftover (unknown sources): give in sorted order.
    for source in sorted(sources):
        if rem <= 0:
            break
        if alloc[source] == base:
            alloc[source] += 1
            rem -= 1
    return alloc


def _sample_diversified_rows(
    *,
    repo_root: Path,
    count: int,
    seed: int,
) -> list[dict]:
    paths = resolve_1m_paths(repo_root)
    codec = load_codec(paths.schema_path)
    index_dir = resolve_index_dir(repo_root, paths)
    if index_dir is None:
        raise SystemExit(
            "1M indexes required. Build or download indexes under "
            "persona/datasets/matraix-persona-1m/indexes/"
        )

    rng = np.random.default_rng(seed)
    with Persona1MIndex.open(index_dir) as index:
        sources = [s for s in SOURCE_PRIORITY if index.has_field("source") and s in set(index.values_for_field("source"))]
        # Include any other source values the index knows.
        for value in index.values_for_field("source"):
            if value not in sources:
                sources.append(value)
        alloc = _allocate_per_source(sources, count)
        chosen_ids: list[int] = []
        for source, take in alloc.items():
            if take <= 0:
                continue
            pool = index.row_ids_for("source", [source])
            if pool.size == 0:
                raise SystemExit(f"no rows for source={source}")
            if take > int(pool.size):
                raise SystemExit(
                    f"source={source} only has {pool.size} rows, need {take}"
                )
            pick = rng.choice(pool, size=take, replace=False)
            chosen_ids.extend(int(x) for x in np.atleast_1d(pick))

    if len(chosen_ids) != count:
        raise SystemExit(f"expected {count} row ids, got {len(chosen_ids)}")
    rng.shuffle(chosen_ids)
    counts = _parquet_row_counts(paths)
    return _read_decoded_rows_at_global(counts, codec, chosen_ids)


def _write_persona_yaml(path: Path, payload: dict) -> None:
    path.write_text(
        yaml.safe_dump(
            payload,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
            width=120,
        ),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="MatrAIx repo root",
    )
    args = parser.parse_args()

    if args.count < 1:
        raise SystemExit("count must be >= 1")

    repo_root = args.repo_root.resolve()
    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = _sample_diversified_rows(
        repo_root=repo_root, count=args.count, seed=args.seed
    )

    # Wipe previous persona YAML so the pool is exactly ``count`` files.
    for stale in out_dir.glob("persona_*.yaml"):
        stale.unlink()

    source_counts: Counter[str] = Counter()
    manifest_personas: list[dict] = []
    for index, row in enumerate(rows, start=1):
        persona_id = f"{index:04d}"
        source = str(row.get("source") or "unknown")
        dimensions = {
            str(key): str(value)
            for key, value in dict(row.get("dimensions") or {}).items()
            if value is not None and str(value).strip()
        }
        display_name = synthetic_display_name(persona_id, dimensions)
        payload = {
            "persona_id": persona_id,
            "version": "1.0",
            "source": source,
            "display_name": display_name,
            "dimensions": dimensions,
            "provenance": {
                "parent_pool": "persona/datasets/matraix-persona-1m",
                "hf_repo": HF_1M_REPO,
                "origin_persona_id": str(row.get("persona_id") or ""),
                "origin_source_row_index": row.get("source_row_index"),
            },
        }
        rel_yaml = f"persona/datasets/matraix-persona-dev-sample/persona_{persona_id}.yaml"
        # If --out is not the default path, keep paths relative to repo when possible.
        try:
            rel_yaml = str((out_dir / f"persona_{persona_id}.yaml").relative_to(repo_root))
        except ValueError:
            rel_yaml = str(out_dir / f"persona_{persona_id}.yaml")
        _write_persona_yaml(out_dir / f"persona_{persona_id}.yaml", payload)
        source_counts[source] += 1
        card = {
            key: dimensions[key]
            for key in CARD_DIMENSIONS
            if key in dimensions
        }
        manifest_personas.append(
            {
                "persona_id": persona_id,
                "path": rel_yaml,
                "source": source,
                "display_name": display_name,
                "dimensions": card,
            }
        )

    # Catalog order for dimension_ids.
    catalog_path = repo_root / "persona" / "schema" / "dimensions.json"
    dimension_ids = [
        str(row["id"])
        for row in json.loads(catalog_path.read_text(encoding="utf-8")).get("dimensions") or []
        if isinstance(row, dict) and row.get("id")
    ]

    manifest = {
        "kind": "matraix-persona-dev-sample",
        "count": len(manifest_personas),
        "seed": args.seed,
        "schema_version": "1.0",
        "smoke_persona_id": "0042" if args.count >= 42 else manifest_personas[0]["persona_id"],
        "dimension_count": len(dimension_ids),
        "dimension_ids": dimension_ids,
        "source_counts": dict(source_counts),
        "dimension_categories": "persona/schema/dimensions.json",
        "parent_pool": "persona/datasets/matraix-persona-1m",
        "hf_repo": HF_1M_REPO,
        "created_at": _utc_now(),
        "personas": manifest_personas,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(
        f"wrote {len(manifest_personas)} personas → {out_dir} "
        f"sources={dict(source_counts)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
