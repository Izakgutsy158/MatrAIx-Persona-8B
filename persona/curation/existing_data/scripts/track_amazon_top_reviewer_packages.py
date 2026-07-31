#!/usr/bin/env python3
"""Track which Amazon top-reviewer IDs have already been assigned to packages."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


QUEUE_LINE_RE = re.compile(r"^\d+\.\s+`([^`]+)`", re.MULTILINE)


def read_queue(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    ids = QUEUE_LINE_RE.findall(text)
    if not ids:
        ids = [line.strip() for line in text.splitlines() if line.strip() and not line.startswith("#")]
    return ids


def iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def discover_manifests(paths: list[Path], roots: list[Path]) -> list[Path]:
    manifests = list(paths)
    for root in roots:
        if root.is_file():
            manifests.append(root)
        elif root.exists():
            manifests.extend(sorted(root.rglob("*.package_manifest.jsonl")))
            manifests.extend(sorted(root.rglob("amazon_fast500_no_product_join_package_manifest.jsonl")))
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in manifests:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(path)
    return unique


def load_package_records(manifests: list[Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for manifest in manifests:
        for record in iter_jsonl(manifest):
            reviewer_ids = [str(value) for value in record.get("reviewer_ids") or []]
            if not reviewer_ids:
                continue
            records.append(
                {
                    "manifest": str(manifest),
                    "run_name": record.get("run_name"),
                    "assignment_id": record.get("assignment_id"),
                    "worker_id": record.get("worker_id"),
                    "range_start": record.get("range_start"),
                    "range_end": record.get("range_end"),
                    "reviewer_count": len(reviewer_ids),
                    "reviewer_ids": reviewer_ids,
                    "package_dir": record.get("package_dir"),
                    "archive": record.get("archive"),
                }
            )
    return records


def build_tracker(queue_ids: list[str], records: list[dict[str, Any]]) -> dict[str, Any]:
    queue_set = set(queue_ids)
    packaged_locations: dict[str, list[str]] = defaultdict(list)
    unknown_ids: set[str] = set()

    for record in records:
        location = str(record.get("assignment_id") or record.get("package_dir") or record.get("manifest"))
        for rid in record["reviewer_ids"]:
            packaged_locations[rid].append(location)
            if rid not in queue_set:
                unknown_ids.add(rid)

    packaged_ids = [rid for rid in queue_ids if rid in packaged_locations]
    unpackaged_ids = [rid for rid in queue_ids if rid not in packaged_locations]
    duplicates = {
        rid: locations
        for rid, locations in sorted(packaged_locations.items())
        if len(locations) > 1
    }

    return {
        "source_reviewer_count": len(queue_ids),
        "package_count": len(records),
        "packaged_reviewer_count": len(packaged_ids),
        "unpackaged_reviewer_count": len(unpackaged_ids),
        "duplicate_packaged_reviewer_count": len(duplicates),
        "unknown_packaged_reviewer_count": len(unknown_ids),
        "packaged_reviewers": packaged_ids,
        "unpackaged_reviewers": unpackaged_ids,
        "duplicate_packaged_reviewers": duplicates,
        "unknown_packaged_reviewers": sorted(unknown_ids),
        "packages": records,
    }


def write_markdown(path: Path, tracker: dict[str, Any], *, limit_unpacked: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as out:
        out.write("# Amazon Top-Reviewer Package Tracker\n\n")
        out.write(f"- Source reviewers: {tracker['source_reviewer_count']}\n")
        out.write(f"- Packages: {tracker['package_count']}\n")
        out.write(f"- Packaged reviewers: {tracker['packaged_reviewer_count']}\n")
        out.write(f"- Not yet packaged: {tracker['unpackaged_reviewer_count']}\n")
        out.write(f"- Duplicate packaged reviewers: {tracker['duplicate_packaged_reviewer_count']}\n")
        out.write(f"- Packaged reviewers outside queue: {tracker['unknown_packaged_reviewer_count']}\n\n")

        out.write("## Packages\n\n")
        out.write("| Assignment | Worker | Reviewers | Manifest |\n")
        out.write("| --- | --- | ---: | --- |\n")
        for record in tracker["packages"]:
            out.write(
                "| {assignment} | {worker} | {count} | `{manifest}` |\n".format(
                    assignment=record.get("assignment_id") or "",
                    worker=record.get("worker_id") or "",
                    count=record.get("reviewer_count") or 0,
                    manifest=record.get("manifest") or "",
                )
            )

        out.write("\n## Not Yet Packaged\n\n")
        unpackaged = tracker["unpackaged_reviewers"]
        shown = unpackaged[:limit_unpacked] if limit_unpacked > 0 else unpackaged
        for index, rid in enumerate(shown, start=1):
            out.write(f"{index}. `{rid}`\n")
        if limit_unpacked > 0 and len(unpackaged) > limit_unpacked:
            out.write(f"\n... {len(unpackaged) - limit_unpacked} more not shown.\n")

        duplicates = tracker["duplicate_packaged_reviewers"]
        if duplicates:
            out.write("\n## Duplicate Packaged Reviewers\n\n")
            for rid, locations in duplicates.items():
                out.write(f"- `{rid}`: {', '.join(locations)}\n")


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", required=True, type=Path)
    parser.add_argument("--manifest-jsonl", action="append", type=Path, default=[])
    parser.add_argument("--package-root", action="append", type=Path, default=[])
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-md", required=True, type=Path)
    parser.add_argument("--limit-unpackaged-md", type=int, default=200)
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    queue_ids = read_queue(args.queue)
    if not queue_ids:
        raise SystemExit(f"no reviewer IDs found in queue: {args.queue}")
    manifests = discover_manifests(args.manifest_jsonl, args.package_root)
    records = load_package_records(manifests)
    tracker = build_tracker(queue_ids, records)
    tracker["queue"] = str(args.queue)
    tracker["manifest_files"] = [str(path) for path in manifests]

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(tracker, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_markdown(args.output_md, tracker, limit_unpacked=args.limit_unpackaged_md)
    print(
        json.dumps(
            {
                "package_count": tracker["package_count"],
                "packaged_reviewer_count": tracker["packaged_reviewer_count"],
                "unpackaged_reviewer_count": tracker["unpackaged_reviewer_count"],
                "output_json": str(args.output_json),
                "output_md": str(args.output_md),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
