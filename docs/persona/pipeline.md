# Persona Pipeline

This page is the technical reference for how the MatrAIx persona corpus is
built — from the 1,290-dimension schema, through source curation and extraction,
to synthetic generation, and finally the post-processing chain that produces the
published 8.4B corpus and the 1M public coreset.

It consolidates the per-stage engineering notes that previously lived in
directory READMEs. Each stage below links to the actual code directory; run
commands from the repository root unless stated otherwise. For the user-facing
overview of the schema, the Treiver extractor, grounding tasks, and the public
dataset, see [Persona](README.md).

Large generated artifacts (raw dumps, `outputs/`, `results/`, `generated/`,
SQLite DBs, worker archives, Parquet snapshots) are intentionally git-ignored at
every stage; only scripts, small fixtures, and manifests are committed.

## Pipeline at a glance

```text
schema (1,290 dims)
  │
  ├─ curation ──────────────  attribute pool (schema construction)
  │                           existing-data sources (Wiki, Amazon, surveys)
  │
  ├─ human_extraction ──────  1,290-dim personas from real profiles (vLLM)
  │
  ├─ synthesis ─────────────  Full-DAG graph → 10B synthetic personas
  │                           visualization of the graph/schema
  │
  └─ post_process
        quality_filter ─────  contradiction rules → reject bitmaps
        deduplication ──────  human MinHash + synthetic projection dedup
        unified_dataset ────  materialize retained rows to Parquet (Persona8B)
        coreset_1m ─────────  calibrated 1M public coreset
        dataset_statistics ─  aggregate profiling for paper tables/figures
```

## Schema

The 1,290-dimension categorical taxonomy is the contract every stage reads.
It lives in [`../../persona/schema/`](../../persona/schema/):

- `dimensions.json` — the 1,290 attributes across 43 categories, each with its
  allowed categorical values.
- `dimension_categories.json`, `persona_taxonomy.json`,
  `persona_taxonomy_mapping.csv` — category grouping and the official
  taxonomy-table mapping (9 groups / 35 sub-categories / 1,290 attributes).
- `render_persona_schema_taxonomy.py` — renders the taxonomy figure.

Extraction, synthesis, dedup, and calibration all validate values against this
schema. See [Persona → schema](README.md#the-1290-dimension-schema) for the
conceptual overview.

## Curation

Source: [`../../persona/curation/`](../../persona/curation/).

### Attribute pool

Directory: [`../../persona/curation/attribute_pool/`](../../persona/curation/attribute_pool/)

Aggregation, normalization, and LLM-assisted deduplication of candidate persona
attributes into the schema. `scripts/` holds the pipeline (aggregate →
normalize → dedup → graph prep → final merge); `docs/` holds method notes
(including `industry_related_persona_attributes.md`, which maps application
domains to useful schema attributes); `sources/` holds small source notes.

Only high-confidence `duplicate_of` / `alias_of` merge decisions are collapsed;
correlated, inverse, broader/narrower, conflict, and review pairs stay as
separate attributes represented as graph edges. Scripts resolve paths relative
to the `attribute_pool/` directory: inputs in `sources/`, generated outputs in
the git-ignored `outputs/` (see `OUTPUTS.md` for the large-artifact policy).

### Existing-data curation

Directory: [`../../persona/curation/existing_data/`](../../persona/curation/existing_data/)

Repo-local tools that build persona records from external datasets (Wikipedia
person pages, Amazon Reviews 2023, and survey/reference registries) and package
work for human collaborators.

Layout: `manifests/` (source metadata), `protocols/` (prompt/schema contracts),
`scripts/` (curation CLIs), `wiki_collab/` + `worker_kit/` (collaboration
contracts and owner-side runners), `samples/`/`examples/` (small git fixtures).

Typical flows:

```bash
# Fetch a small source sample into the ignored raw/ tree
python persona/curation/existing_data/scripts/fetch_sources.py \
  --source literature_references \
  --target-dir persona/curation/existing_data/raw

# Build a local SQLite profile DB from cleaned Wikipedia person-page JSONL
python persona/curation/existing_data/scripts/build_wiki_profile_db.py \
  --clean-dir /path/to/person_pages_clean \
  --out-db /tmp/wiki-profiles.sqlite \
  --manifest /tmp/wiki-profiles.manifest.json \
  --dataset-id personabench_wiki_profiles_v1

# Build a worker-facing collaboration package (unified entrypoint; --source wiki|amazon)
python persona/curation/existing_data/scripts/make_package.py \
  --source wiki --db /tmp/wiki-profiles.sqlite \
  --dimensions persona/schema/dimensions.json \
  --range 0:100 --out-dir /tmp/pkg_A_0_100 \
  --assignment-id A_0_100 --worker-id alice \
  --dataset-id personabench_wiki_profiles_v1 --dataset-sha256 DATASET_SHA256 --force
```

A worker returns `results.jsonl`; validate and merge with
`validate_wiki_results.py` / `merge_wiki_results.py` (archived flow) or
`merge_collab_results.py` (plain worker packages). Amazon-specific helpers
(`select_amazon_top_reviewers.py`, `export_hf_amazon_user_histories.py`,
`infer_amazon_review_dimensions.py`, and the rating-holdout evaluator) follow
the same pattern; a smoke-test fixture ships at
`samples/amazon_reviews_2023/user_histories_sample.jsonl`. Small Nemotron
selection fixtures live under `samples/`, and optional Modal/HuggingFace
indexing needs the extra `pip install -e ".[amazon-modal]"` dependencies.

> Do not confuse this directory with `persona/existing_data_curation/`, a
> separate importable package exercised by the unit tests.

## Human extraction

Directory: [`../../persona/human_extraction/`](../../persona/human_extraction/)

Extracts 1,290-dim personas from **real** human data (MatrAIx wiki person
profiles), in contrast to synthesis. The directory README doubles as a GPU
runbook; the essentials:

- **Model**: `Qwen/Qwen3.6-35B-A3B` (a multimodal hybrid-attention MoE, used
  text-only). Requires `transformers` 5.8.0 and **vLLM ≥ 0.24.0**.
- **CUDA gotcha**: match the torch CUDA build to the node's driver. The default
  vLLM 0.24.0 PyPI wheel targets CUDA 13 (`torch 2.11.0+cu130`); on a
  driver-12.9 H200 you must force-install the `cu129` wheel or
  `torch.cuda.is_available()` is `False`. Check `nvidia-smi | grep "CUDA Version"`
  first.
- **Cache pitfall**: pin every cache to netscratch — including `HF_XET_CACHE`,
  which ignores `HF_HOME` and otherwise fills your home dir.
- **Source data**: gated HF SQLite `wiki/source/matraix_wiki_profiles_*.sqlite`
  (~7.9 GB, ~2.13M `profiles` rows); downloaded into the git-ignored `data/`.
- **Outputs** land in the HF dataset `MatrAIx2026/MatrAIx-1290-extractions`
  (this repo keeps scripts + a small sample only).

Run (from the repo root):

```bash
# throughput / config sweep (see docs/BENCHMARK.md)
python persona/human_extraction/scripts/run_bench_extraction.py --random --n-profiles 20

# full run: single-card SLURM array, resumable (skips already-done global_idx)
cd persona/human_extraction/jobs && mkdir -p sbatch_logs
NUM_SHARDS=200 sbatch -p seas_gpu  --time=2-00:00 --array=0-99%50    extract_shard.job
NUM_SHARDS=200 sbatch -p gpu_h200  --time=2-12:00 --array=100-199%50 extract_shard.job
```

Each SLURM array task is an independent single-card job; the two arrays must
cover **disjoint** shard ranges. Re-running the same lines tops up unfinished
shards. Output is `data/wiki/extraction_v1/shard_XXXX.jsonl`, one JSON object per
profile with ~1,290 field objects each carrying `value`, a 1–2 sentence
`description` of the person, verbatim `evidence`, a `[0,1]` `confidence`, and an
`assignment_type` (`direct | structured_claim | summary_inference |
unsupported`). Prompts are chunked by schema `category` (≤ 50 dims/chunk).
Selected config and quality caveats are in `docs/BENCHMARK.md`; inspect/score
with `scripts/score_personas.py`.

## Synthesis

Source: [`../../persona/synthesis/`](../../persona/synthesis/). A Full-DAG graph over
the schema drives synthetic persona sampling; the sampler and renderers live in
`../../persona/synthesis/scripts/` (`sample_personas.py`, `render_personas.py`).

### Full-DAG 10B generation

Directory: [`../../persona/synthesis/jobs/graph_10b_generation/`](../../persona/synthesis/jobs/graph_10b_generation/)

CPU-only SLURM templates that generate large synthetic shards as compressed
graph `codes.gz` (not rendered text — render lazily for samples/analytics).
Files: `generate_graph_shard.job` (one array task = one shard),
`submit_graph_10b.sh` (submission wrapper), `monitor_generation.sh` (progress).

Default output root is the git-ignored
`persona/synthesis/generated/<RUN_TAG>/` with `shards/*.codes.gz`,
matching `.schema.json`, and per-shard `manifests/*.manifest.json` (row count,
seed, bytes, sha256, elapsed, host, SLURM metadata).

Benchmark first (an "aggressive" default of 48 workers × 20 concurrent shards
assumes real multi-core allocations), then submit:

```bash
cd persona/synthesis/jobs/graph_10b_generation

# small dry run: 2 shards × 1M rows
TOTAL_SHARDS=2 ROWS_PER_SHARD=1000000 ARRAY_CONCURRENCY=2 \
  CPUS_PER_TASK=48 WORKERS=48 TIME=0-01:00 RUN_TAG=full_dag_dryrun_2m \
  ./submit_graph_10b.sh

# full 10B: 100 shards × 100M rows
TOTAL_SHARDS=100 ROWS_PER_SHARD=100000000 ARRAY_CONCURRENCY=20 \
  CPUS_PER_TASK=48 WORKERS=48 MEM=128G TIME=0-06:00 RUN_TAG=full_dag_10b_20260703 \
  ./submit_graph_10b.sh
```

Storage rule of thumb: ~404 compressed bytes/persona ⇒ 10B ≈ 4 TB (allow
6–8 TB for codes-only, more for a Parquet/analytics copy). A shard job resumes
by skipping shards whose `.codes.gz` and `.schema.json` already exist and are
non-empty, so resubmitting the same `RUN_TAG`/counts only runs missing shards.
Monitor with `./monitor_generation.sh <RUN_TAG> <SLURM_JOB_ID>`.

### Visualization

Directory: [`../../persona/synthesis/visualization/`](../../persona/synthesis/visualization/)

Generated static views of the Full-DAG graph and schema (not checked in —
regenerate). Run from the repo root:

```bash
# interactive node-link view (reads persona/synthesis/graph/full_dag.json + schema)
uv run python persona/synthesis/scripts/render_graph_visualization.py
# → persona/synthesis/visualization/full_dag_overview.html

# publication-quality two-ring chord diagram of the schema
uv run --extra viz python persona/synthesis/scripts/render_persona_schema_chord.py
```

The overview HTML embeds the graph payload (search/filter/zoom controls, X by
topological order, Y by category, node size by degree). The chord diagram is
aligned to the taxonomy table (35 sub-categories coloured by their 9 parent
groups); latent/helper nodes with no `category` are excluded so the figure
covers exactly the 1,290 real attributes. Do not hand-edit generated
`full_dag_overview.html` / `persona_schema_chord.{png,pdf}` — regenerate them.

## Post-processing

Source: [`../../persona/post_process/`](../../persona/post_process/). This chain turns
the raw synthetic codes plus human-extracted products into the published corpus.
It is **non-destructive**: each stage emits per-shard rejection bitmaps rather
than rewriting the ~4 TB of source codes. Reported figures below come from the
audited production runs recorded in each directory.

### Quality filter

Directory: [`../../persona/post_process/quality_filter/`](../../persona/post_process/quality_filter/)

Scans all six persona products against conservative categorical contradiction
rules in `contradictions.json`. Each source shard produces `*.reject.bits` (one
little-endian packed bit per row; `1` = reject) and a `*.report.json`
(provenance, totals, per-rule counts). Synthetic shards are checked directly
from nibble-packed codes; human JSONL from populated `fields` (missing/
unsupported fields never trigger a contradiction).

```bash
cd persona/post_process/quality_filter/jobs && ./submit_all.sh
```

After the arrays succeed, a dependent job validates all shard reports and writes
`summary.json` with dataset-level and global rejection counts.

### Deduplication

Directory: [`../../persona/post_process/deduplication/`](../../persona/post_process/deduplication/)

Separates two operations. **Deduplication** removes exact/near-identical
personas; **diversity selection** then trims dense regions deterministically
until the corpus hits its publication target.

- **Human products** (~2.29M rows): exact 128-bit canonical hashes always merge;
  MinHash LSH (64 permutations, 8 bands × 8 rows) generates candidates that must
  meet a signature-agreement threshold (default 0.95 → ≥ 61 equal components).
  Signatures are threshold-independent and reusable, so a threshold can be
  changed by rerunning only the merge.
- **Synthetic products** do **not** use MinHash — a dense 1,290-code vector calls
  for weighted Hamming similarity, `S(x,y)=Σ wᵢ·1[xᵢ=yᵢ]/Σ wᵢ`. Instead a
  reproducible **coordinate projection** of ≤ 16 fields (selected by descending
  graph-prior entropy, round-robin across categories) is encoded exactly into one
  `uint64`. A projection-cardinality pilot uses mergeable HyperLogLog sketches
  (precision 20, ≈ 0.102% relative error) to pick the narrowest projection width
  safely above the target, then the production pass keeps one deterministic
  survivor per projection bucket. Projection equality is a diversity bucket, not
  a full-vector similarity claim.

Run the pilot:

```bash
cd persona/post_process/deduplication/jobs && ./submit_projection_pilot.sh
```

The audited production run derived the synthetic target from the human dedup
result (`8,400,000,000 − human_dedup_kept`) and enforced the exact total with a
deterministic 64-bit priority cutoff (a 65,536-bin histogram locates the
boundary bin without sorting all survivors), verifying `target_met: true`. The
directory README records the full stage-by-stage accounting, SLURM job IDs, and
acceptance criteria.

### Unified dataset (Persona8B)

Directory: [`../../persona/post_process/unified_dataset/`](../../persona/post_process/unified_dataset/)

Materializes the post-filter, post-dedup corpus as a physical Parquet dataset —
every retained persona is written out, so downstream reads need neither the raw
10B codes nor the rejection bitmaps. For a file-by-file map see the directory's
`CODE_INDEX.md`.

Unified columns include `source`, `source_row_index`, `source_record_id`, a
fixed 645-byte `attributes` vector (two 4-bit codes per byte for the 1,290
dimensions), an optional 162-byte `null_bitmap`, sparse `attribute_overrides`
for legacy values outside the codebook, `has_description` + sparse
`descriptions`, sparse `grounding` (evidence/confidence/assignment type), and
`metadata_json`. Synthetic personas are skeletons with no descriptions.

Output layout is `results/<run>/data/<source>/**/*.parquet` with per-task
`reports/*.json`, `persona_codes.schema.json`, and `manifest.json`; synthetic
files hold ≤ 5M rows each. The published snapshot mirrors are on Hugging Face
(`MatrAIx/Persona8B`). The accepted 2026-07-20 snapshot is deliberately a
**partial** release (one Wiki materialization task failed on a numeric-string
confidence conversion); its `manifest.json` carries
`release_status: incomplete_accepted_as_is`, and every accepted Parquet footer
was validated against the unified Arrow schema before upload.

### 1M coreset

Directory: [`../../persona/post_process/coreset_1m/`](../../persona/post_process/coreset_1m/)

Builds the public **MatrAIx Persona 1M** — a deterministic, quality-filtered,
deduplicated 1,000,000-row coreset (600,000 human-grounded / 400,000 synthetic).
Build and finalize via the SLURM job:

```bash
cd persona/post_process/coreset_1m/jobs
REPO_ROOT=… PYTHON_BIN=… INPUT_ROOT=… CODEBOOK=… OUTPUT=… sbatch build.job
```

`build_coreset.py` reads `targets.json`; `finalize.py` writes the release
`RESULTS.md`, `audit.json`, and the dataset-card README (from
`coreset_dataset_card.md`).

**Calibration method** — constrained, without-replacement calibration against
observed marginals rather than a full unobserved joint distribution:

1. Apply the upstream contradiction filter and 0.95 MinHash dedup.
2. Include every retained row from the five smaller human sources; calibrate
   Wiki against evidence-supported global marginal targets.
3. Convert each global target into a **synthetic residual** so synthetic rows
   compensate for missing human coverage: for value `v` of dimension `d`,
   `r_dv = p_dv·(H_d + 400,000) − h_dv`; negative residuals are clipped and the
   clipped mass is reported as infeasibility (never hidden).
4. Every candidate has one **shared** sampling weight updated multiplicatively
   (`w_i ← w_i·T_dv/E_dv`) across age → region → gender identity → urbanicity,
   iterating (≤ 200 sweeps) because each sweep can perturb earlier margins.
   Expected counts use fixed-size inclusion probabilities `π_i = 1 − e^(−t·w_i)`
   with `t` solved so `Σ π_i = n`.
5. Turn weights into an exact-size sample with a **deterministic
   exponential-race**: priority `q_i = −log(U_i)/w_i` with `U_i` derived from the
   seed and stable row ID; take the `n` smallest. This is input-order
   independent and reproducible (seed `20260720`).

Missing values are never imputed. Calibration is honest about scope: hard
evidence is 2024 global population for `age_bracket`, `region` (with a documented
crosswalk), `gender_identity` (UN anchors only Woman/Man; the small tail is a
schema prior — medium confidence), and `urbanicity` (World Bank/UN urban share —
medium confidence). Language is deliberately *not* hard-calibrated. `audit.json`
and `RESULTS.md` report per-dimension target vs. achieved share, absolute error,
known/missing counts, clipped residual mass, and synthetic candidate provenance.

The published Parquet uses the same packed representation as the unified dataset
(645-byte `attributes`, `null_bitmap`, sparse overrides/descriptions/grounding);
ten 100K-row Zstandard shards with a `manifest.json` of exact counts, byte sizes,
and SHA-256 hashes. See [Persona → Public Coreset](README.md#public-coreset-matraix-persona-1m)
for setup, download, and Playground usage.

### Dataset statistics

Directory: [`../../persona/post_process/dataset_statistics/`](../../persona/post_process/dataset_statistics/)

Profiles the six persona products once and caches compact aggregates for fast
paper analysis and plotting. `profile_datasets.py` is the streaming profiler
(writes `results/dataset_statistics.json` plus `dataset_summary.csv`,
`category_summary.csv`, `dimension_summary.csv`); `dataset_statistics.ipynb`
reads only the cache and renders tables/figures into `results/images/`. The
`results/` cache is generated, not checked in.

Coverage policy avoids re-scanning the ~3.7 TB synthetic data (counts come from
the 10B manifests); Wiki uses a deterministic stratified sample (sample-derived
metrics are labeled estimates); Amazon, Stack Overflow, PRISM, and GSS are
scanned in full.

```bash
# expensive stage — only when source data changes
python persona/post_process/dataset_statistics/profile_datasets.py

# refresh selected products, keep the rest cached
python persona/post_process/dataset_statistics/profile_datasets.py \
  --products wiki --merge-existing
```

Then rerun the notebook, which finishes in seconds.
