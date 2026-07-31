# Persona

The Persona module provides a 1,290-dimensional schema for representing human profiles, attribute extraction pipelines, grounding validation tasks, and a public 1 million row coreset for developing and evaluating persona-aware AI systems.

> **Pipeline internals:** for how the corpus is actually built end to end — curation, human extraction, synthetic generation, and the post-processing chain (quality filter → deduplication → unified dataset → 1M coreset → statistics) — see [Persona Pipeline](persona-pipeline.md).

## Overview

A **persona** is a rich structured profile of a person represented as 1,290 categorical attributes across core demographics (age, region, gender identity, urbanicity), professional domains, skills, interests, values, and psychological traits. The MatrAIx Persona system enables:

- **Schema**: A comprehensive 1,290-dimension taxonomy organized in `persona/schema/dimensions.json`
- **Extraction**: Automatic attribute extraction from free-text descriptions using a hybrid regex + LLM pipeline (Treiver)
- **Validation**: Grounding tasks that verify persona-aware AI behavior through structured probes
- **Public dataset**: The MatrAIx Persona 1M — a balanced, quality-filtered, deduplicated coreset of 1,000,000 personas (60% human-grounded, 40% synthetic)

## The 1,290-Dimension Schema

The persona schema defines 1,290 categorical dimensions organized hierarchically:

- **Core demographics**: age brackets, region, gender identity, urbanicity
- **Professional domains**: 143 technical proficiencies (programming, data science, cloud platforms, etc.)
- **Skills and expertise**: communication, leadership, analytical reasoning across generic scale values
- **Interests and values**: hobbies, causes, preferences
- **Psychological traits**: values alignment, personality dimensions

Each dimension has specific categorical values (e.g., age: "Under 5", "5-12", ..., "85+"; proficiency: "Expert", "Proficient", "Intermediate", "Familiar", "No knowledge"). A persona assigns exactly one value per dimension, though extraction may discover only a subset of assignments from source text.

See `../persona/schema/` for the complete taxonomy, calibration targets, and category mappings.

## Attribute Extraction: Treiver

The **Treiver** (trait-retriever) turns a free-text description of a person into structured `(dimension_id, value)` attributes from the schema. It's a lightweight RAG pipeline with two stages:

```
prompt ──▶ [1] regex retrieval ──▶ candidate dimensions ──▶ [2] LLM judge ──▶ attributes
                │                                               │
                └──────────────── regex attributes ─────────────┘
```

### Stage 1: Regex Retrieval
For each dimension, match the prompt against patterns built from its allowed values plus aliases. A dimension that matches becomes a *candidate*. This stage:
- Runs **fully offline**, deterministic, no API key required
- Applies **topic gating** for generic dimensions: "expert" alone doesn't reveal *what*, so 143+ "Proficient/Expert" dimensions also require the topic (e.g., "Data science") to match
- Outputs high-precision, low-recall candidates
- Is usable standalone for deterministic attribute extraction

### Stage 2: LLM Judge
Claude (with structured outputs) sees the prompt and only the candidate dimensions with their allowed values. For each candidate, it:
- Picks the single best value or returns `null` if unsupported
- Quotes evidence from the prompt
- Rates confidence (e.g., "high", "medium", "low")

Both stages emit records with `(dimension_id, value, evidence, method, confidence)` fields, feeding directly into extraction-quality reporting.

### Usage

Python:
```python
from persona.extraction import Treiver

t = Treiver()  # loads the bundled schema

# Stage 1 only — offline, deterministic:
result = t.match("a retired nurse in rural Kentucky")
for a in result.attributes:
    print(a.dimension_id, "=", a.value, f"[{a.method} {a.confidence}]")

# Stages 1 + 2 — with Claude judge:
result = t.match("a retired nurse in rural Kentucky", use_llm=True)
```

Command line:
```bash
python -m persona.extraction "a retired nurse in rural Kentucky, born 1950"
python -m persona.extraction --llm "senior python developer who loves astronomy"
echo "young woman, expert in data science" | python -m persona.extraction --json
```

The extraction module (`persona/extraction/`) contains:
- `schema.py` — load and index `dimensions.json`
- `regex_matcher.py` — regex retrieval and topic gating
- `embed_retriever.py` — semantic retrieval (local embeddings, optional)
- `llm_judge.py` — LLM judge with structured outputs
- `treiver.py` — orchestrator, merges regex and LLM results
- `__main__.py` — CLI interface

For deep details on algorithms, dependencies, and edge cases, see `../persona/extraction/README.md`.

## Curation and Data Sources

The 1M coreset combines multiple human-grounded sources:

- **Wikipedia extraction** (323,438 rows) — calibrated sample from 1.9M extracted profiles
- **Amazon Reviews 2023** (97,915 rows) — all retained profiles from review extraction
- **Stack Overflow survey** (113,120 rows) — all retained respondent profiles
- **GSS / World Values Survey** (63,532 rows) — mapped survey respondents
- **PRISM Alignment** (1,487 rows) — aligned human interviews
- **Real Human Survey** (508 rows) — direct respondent collection
- **Full-DAG synthetic** (400,000 rows) — calibrated sample from 8.4B-row synthetic pool

Human-grounded means derived from a real profile, history, or survey record. It does **not** mean every extracted attribute is a verified fact—model extraction can contain errors, and survey mappings depend on crosswalk quality.

Curation pipeline notes, schema decisions, and attribute-pool construction live in `../persona/curation/`.

## Public Coreset: MatrAIx Persona 1M

A production-ready, balanced, deterministically curated 1,000,000-row coreset available on Hugging Face: [`MatrAIx2026/MatrAIx_Persona_1M_Public_Release`](https://huggingface.co/datasets/MatrAIx2026/MatrAIx_Persona_1M_Public_Release).

### Contents

Each row contains:
- **Provenance**: source, source row index, source record ID
- **Attributes**: 1,290 categorical attributes (packed as a 645-byte vector)
- **Missing values**: bitmap for null attributes (never imputed)
- **Descriptions**: natural-language text (only for human-grounded personas)
- **Grounding**: sparse evidence, confidence rating, extraction method
- **Metadata**: source-specific context

Parquet files are 10 shards of 100K rows each, compressed with Zstandard.

### Calibration

The coreset uses constrained, without-replacement calibration to balance marginal targets:
1. Apply upstream contradiction filter and 0.95 MinHash deduplication
2. Include all rows from five smaller sources (PRISM, GSS, Survey, Stack Overflow, Amazon)
3. Calibrate Wikipedia against global marginal targets
4. Compute synthetic residual targets so synthetic rows compensate for missing human coverage
5. Deterministic exponential-race sampling ensures reproducibility and input-order independence

Calibration targets for `age_bracket`, `region`, `gender_identity`, and `urbanicity` are grounded in UN World Population Prospects 2024 and World Bank data. Missing values remain missing—**no imputation**. The achieved sample may differ slightly from expected margins due to missing attributes and incompatible constraints; `audit.json` documents achieved vs. target distributions and any infeasibility.

### Setup and Usage

Set up locally:
```bash
# Option 1: Point to an external mirror
export MATRIX_PERSONA_1M_DIR=/path/to/MatrAIx_Persona_1M_Public_Release

# Option 2: Download to Hugging Face cache (auto-discovered by Playground)
huggingface-cli download MatrAIx2026/MatrAIx_Persona_1M_Public_Release \
  --repo-type dataset --local-dir persona/datasets/matraix-persona-1m/release
```

The `MATRIX_PERSONA_1M_DIR` target must contain `data/persona-1m-*.parquet` and `persona_codes.schema.json`. Under `persona/datasets/matraix-persona-1m/`, `release/` holds the Parquet source (shown in the Dataset dropdown as `matraix-persona-1m`), `indexes/` holds the inverted postings for fast filtered/stratified sampling, and `cohorts/` is a local launch cache (not listed in the dropdown) where sampling writes cohort YAML for Harbor to run.

Optionally download the sampling indexes (`postings.sqlite` + `manifest.json`, ~2.5GB) for fast stratified sampling; they ship in the public release next to `release/`. Rebuild locally only if you change the Parquet shards:

```bash
PYTHONPATH=.:application/playground:src:environment/runtime:packages/playground/src \
  .venv/bin/python -m backend.service.build_persona_1m_indexes   # --enrich-source to refresh source postings only
```

In Playground:
1. Dataset → `matraix-persona-1m` (`All` is disabled on the full 1M root — sample a cohort instead)
2. Random or stratified sampling → up to 10,000 rows
3. Optional: **Save as dataset…** promotes a cohort to `persona/datasets/<name>/` so it appears under Dataset for reuse across tasks

The index is used automatically when present; Parquet is scanned if not.

## Grounding and Validation Tasks

Persona bench tasks validate that AI systems behave consistently with their assigned personas. Each task probes one specific dimension (e.g., economic motivation, technical expertise) via realistic scenarios.

### Task Structure

Copy a task template and customize:
```bash
cp -R persona/tasks/example-survey_product-feedback persona/tasks/example-survey_my-scenario
```

Edit in this order:
1. **`grounding.toml`** — declare `probe_dimension` and `confounders` for sampling
2. **`src/matraix/task_catalog.py`** — register task metadata (type, domain, tags, dimension index)
3. **`task.toml`** — set task name (auto-generated from catalog) and metadata
4. **`instruction.md`**, **`environment/`**, **`tests/`** — implement your scenario

Run validation:
```bash
uv run harbor run \
  -a persona-claude-code \
  --ak persona_path=persona/datasets/matraix-persona-1m/persona_0042.yaml \
  -p persona/tasks/example-survey_my-scenario
```

### Task Design

- **One probe dimension** per task, declared in `grounding.toml`
- **Probe pressure** — the stimulus should elicit generic "average" answers; grounded agents answer from their profile
- **Human instruction tone** — write like forwarding a real request; persona metadata is separate (no "as your persona")
- **Multiple valid paths** — prefer MCQ options with multiple correct answers (e.g., decline with low relevance vs. full form)
- **Verifier gates** — `test_state.py` validates output shape (reward 0 if invalid); `test_grounding.py` scores behavior and writes `/logs/verifier/grounding.json`

Gold template: [`example-survey_product-feedback`](../persona/tasks/example-survey_product-feedback/README.md) probes **economic motivation** (dim-047) via neutral spending scenarios on a control cohort.

For generic application tasks (chat, web, computer-use), start from `../application/tasks/` instead.

## Grounding Reporting

After a multi-persona Harbor job completes:
```bash
uv run python persona/reporting/eval_grounding_job.py jobs/<job_name> \
  --meta configs/jobs/persona-task-grounding-job-recipe/<name>.meta.json
```

Outputs `persona_grounding_report.json` with:
- `dim_grounding_mean` — per-dimension probe success rate
- `pass_rate` — share of trials that passed validation
- `counterfactual_rate` — share of trials where the agent's answer leaked ungrounded bias

The `--meta` sidecar is auto-generated by `persona/scripts/generate_persona_job.py`.

## Sampling and Jobs

### Production Sampling: The 1M Pool
Use `persona/datasets/matraix-persona-1m` for any Playground or job launch. This is the canonical public coreset.

### Development / Experimental Pools
Generate lightweight offline cohorts:
```bash
uv run python persona/scripts/generate_dev_personas.py
# → persona/datasets/_generated/bench-dev-2000/
```

Optional flags:
- `--task <path>` — top-up Harbor grounding cell coverage
- `--stratum-min <N>` — minimum rows per probe stratum
- `--strategy <path>` — expand a task `persona_strategy.json` into a local pool for experiments

### Job Generation
Create a Harbor job YAML from a task and persona pool:
```bash
uv run python persona/scripts/generate_persona_job.py \
  --task persona/tasks/example-survey_product-feedback
```

This reads `grounding.toml` to sample stratified cohorts and filter on confounders when present. Use `--controlled-probe` for anchor-based cohorts (default for catalog tasks); `--no-controlled-probe` to disable.

See `../persona/scripts/README.md` for full options.

## Docker Integration

Persona bench tasks using Claude Code (`persona-claude-code` agents) pull install scripts from `../environment/docker-snippets/install-claude-code.sh`. After editing this file or adding a Claude Code task, sync copies to task Dockerfiles:

```bash
python scripts/sync_docker_snippets.py --write
```

## Post-Processing and Deduplication

The 1M coreset was built through a multi-stage post-processing pipeline:

- **Contradiction detection** — detects logically inconsistent attributes
- **0.95 MinHash deduplication** — removes near-duplicates before calibration
- **Quality filtering** — enforces consistency and coverage thresholds
- **Unified dataset construction** — merges all sources and applies deduplication
- **Calibration and sampling** — balances marginals and performs deterministic selection

Implementation and audit tools are in `../persona/post_process/`. Each stage produces detailed logs and diagnostics; see [Persona Pipeline → 1M coreset](persona-pipeline.md#1m-coreset) for the full build process and reproducibility notes.

## Project Layout

```
persona/
├── schema/                          # 1,290-dimension taxonomy (dimensions.json)
├── extraction/                      # Treiver: regex + LLM attribute extraction
├── curation/                        # Source pipelines, schema decisions, attribute pool
│   ├── attribute_pool/              # Dimension construction and validation
│   └── existing_data/               # Wikipedia, Amazon, survey processing
├── tasks/                           # Persona bench validation tasks
│   ├── example-survey_*             # Copy as template
│   └── README.md                    # Task design guidelines
├── scripts/                         # Job generation and persona sampling
│   ├── generate_dev_personas.py     # Offline cohort generation
│   ├── generate_persona_job.py      # Harbor job YAML from task + pool
│   └── README.md
├── reporting/                       # Grounding evaluation
│   └── eval_grounding_job.py        # Aggregate job-level metrics
├── datasets/
│   ├── matraix-persona-1m/          # Public 1M coreset (HF mirror + indexes)
│   └── _generated/                  # Local dev cohorts (gitignored)
└── post_process/                    # Build pipeline: dedup, quality, calibration
    ├── coreset_1m/                  # 1M build, calibration, audit
    ├── deduplication/               # MinHash + contradiction detection
    ├── quality_filter/              # Consistency and coverage gates
    └── dataset_statistics/          # Marginal audits
```

## Quick Start

**Extract attributes from a person description:**
```python
from persona.extraction import Treiver
t = Treiver()
result = t.match("senior software engineer in Silicon Valley with ML expertise")
```

**Sample personas for development:**
```bash
uv run python persona/scripts/generate_dev_personas.py
```

**Launch a grounding evaluation:**
```bash
uv run harbor run -a persona-claude-code \
  --ak persona_path=persona/datasets/matraix-persona-1m/persona_0001.yaml \
  -p persona/tasks/example-survey_product-feedback
```

**Aggregate results:**
```bash
uv run python persona/reporting/eval_grounding_job.py jobs/my_job \
  --meta configs/jobs/persona-task-grounding-job-recipe/my_job.meta.json
```

For more details, see the module READMEs and docstrings in each subdirectory.
