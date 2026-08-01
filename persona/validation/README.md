# Persona-Adherence Validation

A probe suite that checks whether a persona's **attributes actually drive agent
behavior** — not just whether they appear in the prompt. For each attribute we
run a *positive* persona (which should express the trait) and a *negative*
persona (which should express the opposite), let the agent produce a
trajectory/artifact, and LLM-judge whether the target attribute value shows up
in the behavior. If persona conditioning works, the positive and negative runs
separate cleanly.

The suite spans **10 attributes × 4 environments** (survey / chat / web /
osapp-linux), for **40 probe tasks**. Run with 5 positive and 5 negative
personas each, that is the 400-trial matrix summarized in
[`results/REPORT.md`](results/REPORT.md).

## Layout

```
validation/
├── tasks/      40 probe tasks, one per (env, attribute): probe-<env>_<attr>/
├── scripts/    matrix runner, LLM judge, report builder, task generators
└── results/    committed summary (REPORT.md, report.json); raw runs gitignored
```

Each `tasks/probe-<env>_<attr>/` is self-contained: `task.toml`,
`instruction.md`, `persona_strategy.json` (how the positive/negative cohorts
are sampled), `reporting.json`, `input/`, `tests/`, and its own `README.md`.

## Scripts

| Script | Purpose |
|---|---|
| `run_probe.sh` | Run one probe recipe through Harbor with an OpenAI-compatible persona model. |
| `run_matrix.py` | Drive the full attribute × environment matrix (`--attrs`, `--envs`, `--n`). |
| `gen_all_tasks.py`, `gen_survey_tasks.py`, `gen_chat_tasks.py` | Generate the probe task directories. |
| `judge_adherence.py` | LLM-judge a probe run: read each trial's trajectory + target attribute, verdict whether it was expressed. |
| `summarize_matrix.py` | Merge per-trial shards into the 10×4 attribute × environment table. |
| `build_report.py` | Build the human-readable [`results/REPORT.md`](results/REPORT.md) from the 400-trial results. |
| `extract_subset.py`, `decode_persona_1m.py` | Persona-subset helpers. |

## Reading the results

Each cell in [`results/REPORT.md`](results/REPORT.md) is `pos/5 · neg/5`: how
many of five positive personas expressed the declared attribute value, and how
many of five negative personas expressed the *opposite* value (target correctly
suppressed). Both counts are "higher is better". A cell is **strong** when both
are ≥ 4/5. See the report for the per-cell table, the by-environment summary,
and cited judge evidence.

## Data policy

Only [`results/REPORT.md`](results/REPORT.md) and `results/report.json` are
committed; raw per-trial runs, generated recipes, and caches are gitignored
(see [`.gitignore`](.gitignore)).
