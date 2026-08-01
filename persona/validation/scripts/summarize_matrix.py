#!/usr/bin/env python3
"""Merge per-trial shard files into a 10x4 attribute x env result table."""

from __future__ import annotations
import json
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parents[3]
CELLS = REPO / "persona/validation/results/cells"
OUT = REPO / "persona/validation/results/matrix_summary.json"

ATTRS = [
    "code-comment-style",
    "code-naming-verbosity",
    "code-summary-documentation",
    "cog-emoji-use",
    "cog-humor",
    "cog-politeness",
    "cog-storytelling",
    "cog-use-of-jargon",
    "cog-verbosity",
    "register",
]
ENVS = ["survey", "chat", "web", "osapp-linux"]


def main():
    data = defaultdict(lambda: defaultdict(lambda: {"pos": [], "neg": []}))
    for f in sorted(CELLS.glob("*.json")):
        r = json.loads(f.read_text())
        data[r["attr"]][r["env"]][r["pol"]].append(r)

    summary = {}

    # cell verdict: "clean" if pos expressed=true AND neg expressed=true(反向也体现其Y值)
    def verdict(cell):
        pos = cell["pos"]
        neg = cell["neg"]
        pe = [t.get("expressed") for t in pos]
        ne = [t.get("expressed") for t in neg]
        if not pos or not neg:
            return "—"
        p_ok = any(x is True for x in pe)
        n_ok = any(x is True for x in ne)
        if p_ok and n_ok:
            return "✅"
        if p_ok or n_ok:
            return "◐"
        return "✗"

    # print table
    hdr = f"{'attribute':<28}" + "".join(f"{e:<14}" for e in ENVS)
    print(hdr)
    print("-" * len(hdr))
    for a in ATTRS:
        row = f"{a:<28}"
        for e in ENVS:
            cell = data.get(a, {}).get(e)
            row += f"{(verdict(cell) if cell else '—'):<14}"
            if cell:
                summary.setdefault(a, {})[e] = {
                    "pos": [
                        {"expressed": t.get("expressed"), "conf": t.get("confidence")}
                        for t in cell["pos"]
                    ],
                    "neg": [
                        {"expressed": t.get("expressed"), "conf": t.get("confidence")}
                        for t in cell["neg"]
                    ],
                    "verdict": verdict(cell),
                }
        print(row)
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    # counts
    allv = [v["verdict"] for a in summary.values() for v in a.values()]
    from collections import Counter

    print(
        "\ncells:",
        dict(Counter(allv)),
        "  (✅ pos&neg both expressed, ◐ one side, ✗ neither)",
    )


if __name__ == "__main__":
    main()
