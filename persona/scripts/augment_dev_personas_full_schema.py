#!/usr/bin/env python3
"""Upgrade matraix-persona-dev-sample (or any YAML pool) to the full 1290-dim schema.

Preserves ``persona_id`` / ``source`` / existing dimension values. Samples only
missing catalog fields with a deterministic RNG seeded by
``(seed, persona_id, full-schema)``.

Updates ``manifest.json``: ``dimension_ids`` / ``dimension_count`` = full
catalog; per-persona ``dimensions`` kept as a small card subset so the
manifest stays manageable (full values live in YAML).
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from matraix.persona_generator import load_catalog_values  # noqa: E402

DEFAULT_SAMPLE = REPO_ROOT / "persona" / "datasets" / "matraix-persona-dev-sample"
DEFAULT_CATALOG = REPO_ROOT / "persona" / "schema" / "dimensions.json"
DEFAULT_SEED = 42
CARD_DIMENSIONS = (
    "age_bracket",
    "region",
    "domain",
    "intent",
    "life_stage",
)


def _pick(rng: random.Random, values: list[str]) -> str:
    if not values:
        raise ValueError("empty catalog values")
    return rng.choice(values)


def _load_catalog_order(catalog_path: Path) -> tuple[list[str], dict[str, int]]:
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    rows = [row for row in (payload.get("dimensions") or []) if isinstance(row, dict) and row.get("id")]
    ids: list[str] = []
    order: dict[str, int] = {}
    for index, row in enumerate(rows):
        dim_id = str(row["id"])
        ids.append(dim_id)
        # Prefer explicit catalog index when present.
        raw_index = row.get("index")
        order[dim_id] = int(raw_index) if raw_index is not None else index
    return ids, order


def _augment_dimensions(
    dimensions: dict[str, object],
    *,
    all_ids: list[str],
    catalog: dict[str, list[str]],
    order: dict[str, int],
    rng: random.Random,
) -> dict[str, object]:
    updated = {
        str(key): value
        for key, value in dimensions.items()
        if value is not None and str(value).strip()
    }
    for dim_id in all_ids:
        if dim_id in updated:
            continue
        values = catalog.get(dim_id) or []
        if not values:
            continue
        updated[dim_id] = _pick(rng, values)
    return dict(
        sorted(
            updated.items(),
            key=lambda item: (order.get(str(item[0]), 99999), str(item[0])),
        )
    )


def _write_persona_yaml(path: Path, payload: dict[str, object]) -> None:
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


def _card_dimensions(dimensions: dict[str, object]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in CARD_DIMENSIONS:
        value = dimensions.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            out[key] = text
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-dir", type=Path, default=DEFAULT_SAMPLE)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()

    sample_dir = args.sample_dir.resolve()
    catalog_path = args.catalog.resolve()
    if not catalog_path.is_file():
        catalog_path = REPO_ROOT / "persona" / "schema" / "dimensions.json"
    if not catalog_path.is_file():
        raise SystemExit(f"missing catalog: {catalog_path}")

    manifest_path = sample_dir / "manifest.json"
    if not manifest_path.is_file():
        raise SystemExit(f"missing manifest: {manifest_path}")

    catalog = load_catalog_values(catalog_path)
    all_ids, order = _load_catalog_order(catalog_path)
    if len(all_ids) < 1000:
        raise SystemExit(f"expected ~1290 catalog dims, got {len(all_ids)}")
    for dim_id in all_ids:
        if dim_id not in catalog or not catalog[dim_id]:
            raise SystemExit(f"catalog missing values for {dim_id}")

    yaml_paths = sorted(sample_dir.glob("persona_*.yaml"))
    if not yaml_paths:
        raise SystemExit(f"no persona_*.yaml under {sample_dir}")

    seen_ids: set[str] = set()
    for path in yaml_paths:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise SystemExit(f"invalid persona yaml: {path}")
        persona_id = str(payload.get("persona_id") or path.stem.removeprefix("persona_"))
        if persona_id in seen_ids:
            raise SystemExit(f"duplicate persona_id {persona_id} in {path}")
        seen_ids.add(persona_id)
        dims = payload.get("dimensions")
        if not isinstance(dims, dict):
            raise SystemExit(f"missing dimensions: {path}")
        before = len(dims)
        rng = random.Random(f"{args.seed}:{persona_id}:full-schema")
        payload["dimensions"] = _augment_dimensions(
            dims,
            all_ids=all_ids,
            catalog=catalog,
            order=order,
            rng=rng,
        )
        after = len(payload["dimensions"])
        if after < len(all_ids):
            raise SystemExit(
                f"{path}: expected {len(all_ids)} dims, got {after} (had {before})"
            )
        _write_persona_yaml(path, payload)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["dimension_ids"] = list(all_ids)
    manifest["dimension_count"] = len(all_ids)
    manifest["schema_version"] = str(manifest.get("schema_version") or "1.0")
    # Point Playground at the full catalog for filters.
    manifest["dimension_categories"] = "persona/schema/dimensions.json"

    personas = manifest.get("personas") or []
    by_id: dict[str, Path] = {}
    for path in yaml_paths:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        by_id[str(payload["persona_id"])] = path

    for entry in personas:
        if not isinstance(entry, dict):
            continue
        persona_id = str(entry.get("persona_id") or "")
        path = by_id.get(persona_id)
        if path is None:
            continue
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        dims = dict(payload.get("dimensions") or {})
        entry["dimensions"] = _card_dimensions(dims)
        if "source" in payload:
            entry["source"] = payload["source"]
        if payload.get("display_name"):
            entry["display_name"] = payload["display_name"]

    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"augmented {len(yaml_paths)} unique personas → "
        f"dimension_count={len(all_ids)} (full schema)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
