#!/usr/bin/env python3
"""Build Amazon top-reviewer packages from one prepared JSONL and write a manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable


def iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def reviewer_id(row: dict[str, Any]) -> str:
    value = row.get("user_id") or row.get("reviewer_id")
    if not value:
        raise ValueError("prepared row is missing user_id/reviewer_id")
    return str(value)


def build_packages(args: argparse.Namespace, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    row_count = len(rows)
    limit = row_count if args.max_users <= 0 else min(row_count, args.max_users)
    package_count = (limit + args.package_size - 1) // args.package_size
    if args.max_packages > 0:
        package_count = min(package_count, args.max_packages)

    dataset_sha256 = sha256_file(args.user_histories)
    records: list[dict[str, Any]] = []
    for package_index in range(package_count):
        start = package_index * args.package_size
        end = min(start + args.package_size, limit)
        if start >= end:
            break

        worker_id = args.worker_prefix + f"{package_index:03d}"
        assignment_id = f"{args.assignment_prefix}_{start}_{end}"
        dataset_id = f"{args.dataset_prefix}_{start}_{end}"
        out_dir = args.out_root / f"{assignment_id}_{worker_id}"
        archive = out_dir.with_suffix(out_dir.suffix + ".tar.gz")

        if not (
            args.reuse_packages
            and archive.exists()
            and archive.stat().st_size > 0
            and out_dir.is_dir()
        ):
            cmd = [
                sys.executable,
                "persona/curation/existing_data/scripts/make_package.py",
                "--source",
                args.source,
                "--user-histories",
                str(args.user_histories),
                "--dimensions",
                str(args.dimensions),
                "--range",
                f"{start}:{end}",
                "--out-dir",
                str(out_dir),
                "--assignment-id",
                assignment_id,
                "--worker-id",
                worker_id,
                "--dataset-id",
                dataset_id,
                "--dataset-sha256",
                dataset_sha256,
                "--max-reviews-per-user",
                str(args.max_text_reviews_per_user),
            ]
            if args.all_dimensions:
                cmd.append("--all-dimensions")
            if args.force_packages:
                cmd.append("--force")
            subprocess.run(cmd, check=True)

        package_rows = rows[start:end]
        records.append(
            {
                "run_name": args.run_name,
                "assignment_id": assignment_id,
                "worker_id": worker_id,
                "range_start": start,
                "range_end": end,
                "reviewer_count": len(package_rows),
                "reviewer_ids": [reviewer_id(row) for row in package_rows],
                "package_dir": str(out_dir),
                "archive": str(archive),
                "dataset_id": dataset_id,
                "dataset_sha256": dataset_sha256,
                "source_histories": str(args.user_histories),
            }
        )
    return records


def write_manifest(
    *,
    rows: list[dict[str, Any]],
    records: list[dict[str, Any]],
    args: argparse.Namespace,
) -> None:
    args.manifest_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.manifest_jsonl.open("w", encoding="utf-8") as out:
        for record in records:
            out.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    with args.manifest_md.open("w", encoding="utf-8") as out:
        out.write(f"# {args.run_name} Package Manifest\n\n")
        out.write(f"- Prepared users: {len(rows)}\n")
        out.write(f"- Package size: {args.package_size}\n")
        out.write(f"- Package count: {len(records)}\n")
        out.write(f"- Source histories: `{args.user_histories}`\n\n")
        for record in records:
            out.write(f"## {record['assignment_id']} ({record['worker_id']})\n\n")
            out.write(f"- Reviewer count: {record['reviewer_count']}\n")
            out.write(f"- Package dir: `{record['package_dir']}`\n")
            out.write(f"- Archive: `{record['archive']}`\n\n")
            for index, rid in enumerate(
                record["reviewer_ids"], start=record["range_start"] + 1
            ):
                out.write(f"{index}. `{rid}`\n")
            out.write("\n")


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-histories", required=True, type=Path)
    parser.add_argument("--dimensions", required=True, type=Path)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--manifest-jsonl", required=True, type=Path)
    parser.add_argument("--manifest-md", required=True, type=Path)
    parser.add_argument("--run-name", default="amazon_top_reviewers")
    parser.add_argument("--source", default="amazon")
    parser.add_argument("--assignment-prefix", default="AMZ_FAST500")
    parser.add_argument("--dataset-prefix", default="matraix_amazon_reviews_2023_fast500")
    parser.add_argument("--worker-prefix", default="worker_")
    parser.add_argument("--package-size", type=int, default=100)
    parser.add_argument("--max-users", type=int, default=0)
    parser.add_argument("--max-packages", type=int, default=0)
    parser.add_argument("--max-text-reviews-per-user", type=int, default=200)
    parser.add_argument("--reuse-packages", action="store_true")
    parser.add_argument("--force-packages", action="store_true")
    parser.add_argument("--all-dimensions", action="store_true")
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    if args.package_size <= 0:
        raise SystemExit("--package-size must be positive")
    rows = list(iter_jsonl(args.user_histories))
    if not rows:
        raise SystemExit(f"no prepared rows found in {args.user_histories}")
    args.out_root.mkdir(parents=True, exist_ok=True)
    records = build_packages(args, rows)
    write_manifest(rows=rows, records=records, args=args)
    print(
        json.dumps(
            {
                "package_count": len(records),
                "reviewer_count": sum(record["reviewer_count"] for record in records),
                "manifest_jsonl": str(args.manifest_jsonl),
                "manifest_md": str(args.manifest_md),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
