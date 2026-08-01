# Large-scale runs

How to scale a Harbor job from a single smoke persona to hundreds or thousands
of trials — using public persona sources and local artifacts only.

For a first end-to-end run, start with [quickstart.md](../quickstart.md). This
page assumes you already have API keys, Docker (when needed), and a working
single-persona job.

---

## What “large-scale” means here

| Piece | Small / smoke | Large-scale |
|-------|---------------|-------------|
| Personas | One YAML (e.g. `persona_0042`) | Stratified sample or imported 1M subset |
| Launch | One `harbor run` or Playground trial | Job recipe with many trials + concurrency |
| Outputs | One trial under `jobs/<job>/` | Full job tree + optional batch PDF |

Tasks live under [`application/tasks/`](../../application/tasks/). Pick any
checked-in task that matches your surface (survey, chat, web, OS app).

---

## Persona cohorts

Use one of these sources — do **not** invent a private upload destination for
personas unless you manage that storage yourself.

### 1. Task strategy (recommended starting point)

Most tasks ship a `persona_strategy.json`. Generate a cohort with the Playground
or `generate_application_job.py` so filters, stratification, and `sampleSize`
come from the task:

```bash
# Example: build a job that samples from the task strategy
uv run python application/scripts/generate_application_job.py \
  --task application/tasks/<task-name> \
  --help
```

When using stratified sampling, set `sampleSize` to the **exact total** you
want. Do not also set `sampleSizePerValueGroup`: the two fields are mutually
exclusive, and `sampleSizePerValueGroup` sets a quota per stratum rather than
an exact total.

### 2. Public Persona 1M coreset

For population-scale studies, import
[`MatrAIx2026/MatrAIx_Persona_1M_Public_Release`](https://huggingface.co/datasets/MatrAIx2026/MatrAIx_Persona_1M_Public_Release)
and point jobs at the local mirror. See
[Persona setup](../persona/README.md#setup-and-usage) and
[configuration.md](../configuration.md#persona-profile-and-default-sample).

### 3. In-repo sample dataset

For development and CI-sized batches:

```text
persona/datasets/matraix-persona-dev-sample/
```

Record the persona source (path, revision if Hugging Face, count) in your job
README or recipe comments so runs stay reproducible.

---

## Running the job

1. Choose agent and model for the task surface — see [agents.md](agents.md) and
   [web-interaction.md](web-interaction.md).
2. Launch via a recipe under `configs/jobs/` or generate one from Playground /
   `generate_application_job.py`.
3. Raise concurrency only as far as your machine, Docker, and API quotas allow.
4. Keep the job on a stable git revision of this repo so task + verifier match
   the artifacts you archive.

Example shape (paths and flags vary by task):

```bash
uv run harbor run -c configs/jobs/<your-recipe>.yaml
```

Remote or multi-machine dispatch: [runtime.md](runtime.md).

---

## Where artifacts land

Harbor writes under the repo-local `jobs/` tree (gitignored):

```text
jobs/<job_name>/
├── <task>__<trial>/
│   ├── agent/          trajectory, screenshots, …
│   ├── verifier/       scores / reports
│   └── result.json
├── job.log
└── result.json         job-level rollup when present
```

Generated persona YAMLs used for a run often sit under a task or job
`_generated/` (or Playground materialization) directory — package or copy them
**before** cleaning the workspace if you need to reproduce the cohort later.

You own archival: copy `jobs/<job_name>/` (and any persona cohort you generated)
to whatever storage your org uses. This handbook does not prescribe a shared
external dataset for uploads.

---

## Batch PDF report (optional but useful)

For multi-persona jobs, Playground can export a **Persona-Task Batch Report**
PDF via **Download PDF** on the run detail view. That export is produced by
`application/playground/frontend/src/lib/exportBatchReportPdf.ts` (frontend
`jspdf` + `html-to-image`), not the compact server-side `report_pdf` helper.

```bash
cd application/playground/frontend
npm install
npm run build
```

After trials finish:

1. Confirm the job has the expected number of completed trials (no pending /
   running / errored trials you still care about).
2. Build or refresh aggregation with `application/scripts/report_job.py`
   (`--no-llm` when you only need deterministic rollups).
3. Open the job in Playground **Runs**, wait for the batch report UI to load,
   then **Download PDF**.
4. Keep the PDF next to `aggregation.json` in your own archive layout if you
   want a shareable deliverable.

Expected filename pattern: `<job_name>-persona-task-batch-report.pdf`.

---

## Related

- [Environment overview](README.md)
- [Quickstart](../quickstart.md)
- [Persona 1M](../persona/README.md#public-coreset-matraix-persona-1m)
- [Configuration](../configuration.md)
- [Playground API](../application/playground-api.md)
