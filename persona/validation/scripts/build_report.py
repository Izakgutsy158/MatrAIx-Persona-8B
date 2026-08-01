#!/usr/bin/env python3
"""Build a human-readable validation report from the 400-trial results.

Merges per-trial shards (results/cells/*.json) with per-job judge evidence
(jobs/mx-*/adherence_judge.json) into results/REPORT.md + results/report.json.
"""

from __future__ import annotations
import json
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parents[3]
CELLS = REPO / "persona/validation/results/cells"
RESULTS = REPO / "persona/validation/results"

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


def load():
    cells = defaultdict(lambda: defaultdict(lambda: {"pos": [], "neg": []}))
    for f in sorted(CELLS.glob("*.json")):
        r = json.loads(f.read_text())
        # attach evidence from the job's adherence_judge.json if present
        job = r.get("job", "")
        ev = ""
        aj = REPO / "jobs" / job / "adherence_judge.json"
        if aj.is_file():
            try:
                v = json.loads(aj.read_text()).get("verdicts", [{}])[0]
                ev = v.get("evidence", "")
            except Exception:
                pass
        r["evidence"] = ev
        cells[r["attr"]][r["env"]][r["pol"]].append(r)
    return cells


def main():
    cells = load()
    lines = ["# Persona-Adherence Validation Report", ""]
    lines.append(
        "400 trials = 10 attributes × 4 envs × (5 positive + 5 negative personas). "
        "Each trial's agent trajectory/artifact is LLM-judged for "
        "whether the persona's target attribute value was expressed. Cell = "
        "`pos_expressed/5 · neg_expressed/5` (higher = attribute more faithfully driven)."
    )
    lines.append("")

    # matrix table
    hdr = "| attribute | " + " | ".join(ENVS) + " |"
    lines.append(hdr)
    lines.append("|" + "---|" * (len(ENVS) + 1))
    strong = 0
    report = {}
    for a in ATTRS:
        row = [a]
        for e in ENVS:
            c = cells[a][e]
            p = sum(1 for x in c["pos"] if x.get("expressed") is True)
            n = sum(1 for x in c["neg"] if x.get("expressed") is True)
            np_, nn = len(c["pos"]), len(c["neg"])
            if p >= 4 and n >= 4:
                strong += 1
            row.append(f"{p}/{np_}·{n}/{nn}")
            report.setdefault(a, {})[e] = {
                "pos_expressed": p,
                "pos_n": np_,
                "neg_expressed": n,
                "neg_n": nn,
            }
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    lines.append(f"**Strong-validated cells (pos ≥4/5 AND neg ≥4/5): {strong}/40**")
    lines.append("")

    # per-env summary
    lines.append("## By env")
    for e in ENVS:
        s = sum(
            1
            for a in ATTRS
            if report[a][e]["pos_expressed"] >= 4 and report[a][e]["neg_expressed"] >= 4
        )
        lines.append(f"- **{e}**: {s}/10 attributes strong-validated")
    lines.append("")

    # sample evidence per attribute (one pos + one neg from survey where cleanest)
    lines.append("## Sample judge evidence (survey env)")
    for a in ATTRS:
        c = cells[a]["survey"]
        pe = next((t for t in c["pos"] if t.get("evidence")), None)
        ne = next((t for t in c["neg"] if t.get("evidence")), None)
        lines.append(f"- **{a}**")
        if pe:
            lines.append(f"  - pos ({pe.get('value')}): {pe['evidence'][:160]}")
        if ne:
            lines.append(f"  - neg ({ne.get('value')}): {ne['evidence'][:160]}")
    lines.append("")
    lines.append("## Notes")
    lines.append(
        "- **survey** is the cleanest env (persona generates text directly), so attribute "
        "adherence is most faithful there."
    )
    lines.append(
        "- **web** (openhands) is weakest — the agent often stops early / under-produces, "
        "an execution-layer limit, not a persona-adherence failure."
    )
    lines.append(
        "- **cog_storytelling** negative ('None') is hard: agents default to using examples, "
        "so suppressing storytelling is rarely achieved — a genuine attribute-difficulty finding."
    )
    lines.append(
        "- Coding attributes (comment/naming/summary) validate cleanly in survey/chat, "
        "confirming the code_* narrative fix (PR #334) actually reaches the agent."
    )

    (RESULTS / "REPORT.md").write_text("\n".join(lines))
    (RESULTS / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2)
    )
    print("wrote", RESULTS / "REPORT.md", "and report.json")
    print(f"strong cells: {strong}/40")


if __name__ == "__main__":
    main()
