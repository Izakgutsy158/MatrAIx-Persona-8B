# Amazon Top Reviewer Queues

This directory contains reusable reviewer ID queues for staged Amazon Reviews
2023 persona curation.

`amazon_top_10000_rich_persona_reviewer_ids_2018_2023.md` lists 10,000
high-signal reviewer IDs selected from the 2018-2023 eligible-user artifact.
It stores IDs and lightweight selection context only, not review histories.

## Build One Package

To build a worker-facing package directly from one rank slice of this queue,
run:

```bash
persona/curation/existing_data/scripts/make_amazon_top_reviewer_package.sh \
  0:100 \
  alice
```

This creates one package for ranks `[0, 100)`.

## Build Packages From a Queue

For production package generation, retrieve and prepare the queue once, enrich
that prepared JSONL once, then split it locally into 100-reviewer packages:

```bash
export MATRIX_DATA_ROOT=/path/to/local/amazon_cache
export MATRIX_PACKAGE_OUT_ROOT=/path/to/package_output
export HF_TOKEN=...  # optional, only needed for private HF dataset access

persona/curation/existing_data/scripts/make_amazon_top_reviewer_batch_packages.sh
```

Each package is written under `MATRIX_PACKAGE_OUT_ROOT` and contains only
worker-facing assignment files. Raw, prepared, enriched, and cached metadata
files stay under `MATRIX_DATA_ROOT`.

Useful overrides:

- `QUEUE`: reviewer queue path; defaults to the checked-in 10K queue
- `RUN_NAME`: output file prefix; default `amazon_top_reviewers_batch`
- `PACKAGE_SIZE`: reviewers per package; default `100`
- `MAX_USERS`: cap the prepared rows used for this run; `0` means all rows
- `MAX_PACKAGES`: cap package count; `0` means no explicit package cap
- `REUSE_RAW_HISTORIES=1`: reuse existing HF review retrieval cache
- `REUSE_PREPARED_HISTORIES=1`: reuse the prepared temporal-split JSONL
- `REUSE_ENRICHED_HISTORIES=1`: reuse the product-enriched JSONL
- `REUSE_PACKAGES=1`: skip package rebuilds when package archives already exist
- `INCLUDE_PRODUCT_INFO=0`: skip targeted product enrichment

## Retrieval and Preparation Flow

The wrappers export raw user histories from the Hugging Face user-bucket
artifact, prepare those histories into the Amazon inference/evaluation contract,
optionally enrich the prepared construction split with compact product context
from the Hugging Face metadata artifact, and build Amazon collaborator packages
with `make_package.py`. Product context is limited to `product_title`,
`product_main_category`, and `product_category_path`; full item metadata is not
copied into the package input.

The flow is Hugging Face only; it does not require Modal.

The prepared history JSONL contains:

- `reviews`: chronological construction split used for persona extraction
- `validation_reviews`: held-out temporal tail for downstream rating holdout
- `temporal_split`: per-user split metadata
- `category_review_stats` and `validation_category_review_stats`
- `review_filter_summary`: low-signal/template/duplicate review removals
- compact product fields on each review when available

Product enrichment happens after the temporal split. It requests metadata only
for selected high-signal text reviews and non-text construction rows, then
recomputes construction and validation category stats. Rows without review
title/text are kept when they have a valid rating and compact product context.
Their product/category signals are summarized in the category stats and rendered
into the package `profile_text` summary section. They are not rendered as
individual review blocks.

For individual review evidence, the package renders at most 200 high-signal
text reviews per reviewer from the temporal construction split. Text reviews
are ranked by signal features such as text length, helpful votes, verified
purchase, review title, product context, and rating specificity, then rendered
chronologically. Override this with `MAX_TEXT_REVIEWS_PER_USER`.

## Temporal Split vs Package Evidence Folds

Persona extraction uses only the temporal construction split in `reviews`.
With the default `TEMPORAL_TRAIN_FRACTION=0.8`, this means the earliest 80% of
each reviewer's retained chronological rows are used for persona inference.
The latest 20% are written to `validation_reviews` for downstream evaluation
and are not rendered into the package `profile_text`.

Inside the package, `cv_fold_texts` are only evidence chunks created from the
construction split. They are used by the default solver for consistency checks
across chunks; they are not the temporal validation split.

## Configuration

Set `MATRIX_DATA_ROOT` and `MATRIX_PACKAGE_OUT_ROOT` to control where local
histories and package archives are written. Set `TEMPORAL_TRAIN_FRACTION`
to change the default `0.8` construction/validation split. Set
`INCLUDE_PRODUCT_INFO=0` to disable the HF metadata join for review-text-only
ablations.

Other useful overrides:

- `TOP_REVIEWER_QUEUE`: path to a different reviewer queue file
- `AMAZON_REVIEWS_REPO_ID`: Hugging Face dataset repo, default `MatrAIx/MatrAIx`
- `AMAZON_REVIEWS_ARTIFACT_PREFIX`: HF user-bucket artifact prefix
- `AMAZON_METADATA_ARTIFACT_PREFIX`: HF metadata artifact prefix
- `AMAZON_CATEGORIES`: comma-separated category subset, or `all`
- `MAX_TEXT_REVIEWS_PER_USER`: max rendered text reviews per user, default `200`
- `HF_DOWNLOAD_DELAY_SECONDS`: throttle between HF review shard downloads, default `0.4`
- `HF_METADATA_DOWNLOAD_DELAY_SECONDS`: throttle between HF metadata shard downloads
- `REUSE_RAW_HISTORIES=1`: skip HF review retrieval when raw histories exist
- `REUSE_PREPARED_HISTORIES=1`: skip preparation when prepared histories exist
- `REUSE_ENRICHED_HISTORIES=1`: skip product enrichment when enriched histories exist

## Track Packaged vs Unpackaged Reviewers

After generating package manifests, compare them against the 10K reviewer queue:

```bash
python3 persona/curation/existing_data/scripts/track_amazon_top_reviewer_packages.py \
  --queue persona/curation/existing_data/samples/amazon_reviews_2023/top_reviewers/amazon_top_10000_rich_persona_reviewer_ids_2018_2023.md \
  --package-root /path/to/package_output \
  --output-json /path/to/package_tracker.json \
  --output-md /path/to/package_tracker.md
```

The tracker writes packaged reviewer IDs, not-yet-packaged reviewer IDs,
package-level provenance, duplicate package assignments, and any packaged IDs
that are not present in the source queue.

## Retrieve Histories Only

To retrieve only the corresponding review histories, pass this file to:

```bash
python3 persona/curation/existing_data/scripts/export_hf_amazon_user_histories.py \
  --user-ids persona/curation/existing_data/samples/amazon_reviews_2023/top_reviewers/amazon_top_10000_rich_persona_reviewer_ids_2018_2023.md \
  --output /path/to/user_histories.jsonl.gz
```
