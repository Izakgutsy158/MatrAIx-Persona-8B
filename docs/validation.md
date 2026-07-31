# Validation

The persona-adherence validation suite checks whether a persona's **attributes actually drive agent behavior** — not just whether they appear in the prompt. It lives under `application/validation/`.

For each attribute we run a *positive* persona (which should express the trait) and a *negative* persona (which should express the opposite), let the agent produce a trajectory/artifact, and LLM-judge whether the target attribute value shows up in the behavior. If persona conditioning works, the positive and negative runs separate cleanly.

The suite spans **10 attributes × 4 environments** (survey / chat / web / osapp-linux). Each `(attribute, env)` pair is a self-contained task under `application/validation/tasks/`.

---

## Layout

```text
application/validation/
├── tasks/      probe tasks, one per (env, attribute) — probe-<env>_<attr>/
├── scripts/    matrix runner, LLM judge, report builder, helpers
└── results/    committed summary report (REPORT.md, report.json)
```

Attributes covered: `code-comment-style`, `code-naming-verbosity`, `code-summary-documentation`, `cog-emoji-use`, `cog-humor`, `cog-politeness`, `cog-storytelling`, `cog-use-of-jargon`, `cog-verbosity`, `register`.

---

## Requirements

- `uv`, Docker (for the containerized web/osapp environments)
- An OpenAI-compatible API endpoint for both the persona model and the judge.

Configure everything through environment variables:

```bash
export OPENAI_API_KEY=sk-...                     # required
export OPENAI_BASE_URL=https://api.openai.com/v1 # optional; any compatible endpoint
export PERSONA_MODEL=gpt-4o                       # model the agents run as
export JUDGE_MODEL=gpt-4o                         # model the judge runs as
```

---

## Running

Run the full matrix (1 positive + 1 negative persona per cell):

```bash
python application/validation/scripts/run_matrix.py
```

Scope it down while iterating:

```bash
python application/validation/scripts/run_matrix.py \
    --attrs cog-politeness,cog-humor --envs survey,chat --n 1
```

Run a single probe recipe directly through Harbor:

```bash
application/validation/scripts/run_probe.sh <recipe.yaml> [survey_task_path]
```

Judge a finished Harbor job dir on its own:

```bash
python application/validation/scripts/judge_adherence.py jobs/<job> \
    --attribute code_comment_style --value "Extensive inline comments"
```

Build the summary report from per-cell shards:

```bash
python application/validation/scripts/build_report.py
```

---

## Notes

- The judge reads whatever trajectory/artifact text a trial produced, so it works uniformly across all four environments.
- `reward` (task completion) is **not** the signal here — adherence is judged purely from the agent's produced behavior, independent of whether the task itself succeeded.
- Probe task instructions are deliberately **neutral**: they describe a task without ever naming the attribute's direction, so the persona's trait has to surface on its own.
