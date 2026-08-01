# Authoring bundle

Onboarding and diagrams: [`../README.md`](../README.md).

Per-type file layouts for tasks under `application/tasks/<task-name>/`.
Part of [task-spec README](../README.md) **Step 2**. Per-type **diagrams** are in each
type README ([survey](../survey/README.md), [chatbot](../chatbot/README.md),
[web](../web/README.md), [os-app](../os-app/README.md)).

Each runnable task lives under `application/tasks/<task-name>/` and always
includes `instruction.md`, `task.toml`, `tests/`, `reporting.json`, and
`persona_strategy.json` (target cohort / Playground sampling defaults).
Supplementary files differ by application type:

### Survey

```text
instruction.md                 # short scenario / requirements
reporting.json                 # batch aggregation policy (contextRules)
persona_strategy.json          # target cohort + Playground sampling defaults
input/
  context.md                   # product concept (optional)
  questionnaire.yaml           # questions + askRationale / askConfidence
```

Do **not** add `input/output_schema.md`. The platform derives the answer
envelope from `questionnaire.yaml` and writes `survey_result.json`.

### Chatbot

```text
instruction.md                 # conversation goal
reporting.json                 # batch aggregation policy (contextRules)
persona_strategy.json          # target cohort + Playground sampling defaults
input/
  context.md                   # application background (optional)
  protocol.md                  # chat API / MCP contract (optional)
  chatbot.yaml                 # runtime connection metadata
  self_report_schema.yaml      # user_feedback.json
```

Platform-managed harness artifacts (`transcript.json`,
`application_result.json`) are documented in
[`eval_artifacts.md`](eval_artifacts.md), not in per-task files.

### Web / OS-app

```text
instruction.md                 # task goal, steps, optional submission JSON schema
reporting.json                 # batch aggregation policy (contextRules)
persona_strategy.json          # target cohort + Playground sampling defaults
input/
  context.md                   # scenario / product background (optional)
  self_report_schema.yaml      # user_feedback.json (optional)
```

Prefer verifying from browser/OS traces and final state. When state is hard to
read, an agent submission schema may still live inline in `instruction.md`.
Persona self-report uses the same `input/self_report_schema.yaml` convention as
chatbot tasks.

### Quick reference

| Concern | survey | chatbot | web / os-app |
|---|---|---|---|
| Scenario | `instruction.md` | `instruction.md` | `instruction.md` |
| Background context | `input/context.md` | `input/context.md` | `input/context.md` (optional) |
| Structured input | `input/questionnaire.yaml` | `input/chatbot.yaml`, optional `protocol.md` | — |
| Objective evidence | platform `survey_result.json` | platform harness artifacts | trace/state (optional agent submission) |
| Persona self-report | — | `input/self_report_schema.yaml` | `input/self_report_schema.yaml` |
| Batch reporting policy | `reporting.json` | `reporting.json` | `reporting.json` |
| Target cohort / sampling | `persona_strategy.json` | `persona_strategy.json` | `persona_strategy.json` |

### `persona_strategy.json`

Lives at the **task root** next to `reporting.json`. Most tasks declare a
**target cohort** with `dimensionFilters` (and/or `cohortId`). Field values may
use defaults; the file itself and a cohort declaration are checked in CI.

Playground uses this for Random / Stratified (and optional Quick pick) defaults.

```json
{
  "schemaVersion": "1.0",
  "defaultMode": "stratified",
  "pool": "persona/datasets/matraix-persona-dev-sample",
  "sources": ["Nemotron"],
  "dimensionFilters": {
    "age_bracket": ["25-34", "35-44"],
    "region": ["North America"]
  },
  "stratifyFields": ["age_bracket", "region"],
  "sampleSizePerValueGroup": 2,
  "cohortId": null
}
```

| Field | Notes |
|---|---|
| `schemaVersion` | Use `"1.0"` |
| `defaultMode` | `single` \| `random` \| `stratified` |
| `dimensionFilters` / `cohortId` | Non-empty filters and/or a saved `cohortId` — who this task is for |
| `sources` | Optional source allow-list |
| `stratifyFields` | Needed when `defaultMode` is `stratified`. **Every** stratify field must also appear under `dimensionFilters` with allowed values (so cell coverage is well-defined). |
| `sampleSizePerValueGroup` | **Stratified strategy A (per-cell):** take **N per combination**. Total = `N × (# cells)`. **Do not also set `sampleSize`.** |
| `sampleSize` | Random: hard sample count. **Stratified strategy B (total N):** spread as `ceil(sampleSize / #cells)` then clip to `sampleSize`. Must be **≥ # cells**. **Do not also set `sampleSizePerValueGroup`.** |
| `cohortId` | Optional saved cohort under `persona/datasets/cohorts/` |
| `pool` | Defaults to matraix-persona-dev-sample |

**Stratified sampling — two mutually exclusive strategies:**

| Strategy | Set this | Omit this | Cohort size |
|---|---|---|---|
| Per-cell | `sampleSizePerValueGroup` | `sampleSize` | `N × #cells` |
| Total N | `sampleSize` | `sampleSizePerValueGroup` | exactly `sampleSize` |

1. Thin / missing cells → sample from `matraix-persona-1m`, widen
   `dimensionFilters` / sources, or use a saved cohort — sampling never
   synthesizes personas.
2. Per-cell: guarantee N in each cell; total follows from the grid.
3. Total N: guarantee `ceil(sampleSize / #cells)` capacity per cell, sample,
   clip to `sampleSize`. Author `sampleSize` ≥ # cells.
4. Setting **both** fields is invalid (CI / Playground reject the strategy).

Playground turns on **Task default strategy** from this file (filters / mode /
per-cell N / sampleSize locked to the file). Operators can turn that switch off
to edit filters themselves, then turn it back on to re-apply the task default.

### Ensuring pool coverage

`persona/datasets/matraix-persona-dev-sample/` is a small ~200-persona fixture for
smoke and local UI work. Narrow `dimensionFilters` (and stratified cells) often
undershoot it.

**When coverage fails**, do one of:

1. Sample from production: set `"pool"` to `persona/datasets/matraix-persona-1m`
   (or choose that pool in Playground).
2. Widen `dimensionFilters` / `sources` until the fixture (or 1M) has enough matches.
3. Use a saved cohort under `persona/datasets/cohorts/` that already has enough
   personas.

Playground / job launch **does not** auto-synthesize `_generated` pools. Thin
coverage raises an error with the same recovery hint.
