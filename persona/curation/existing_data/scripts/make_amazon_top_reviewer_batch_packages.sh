#!/usr/bin/env bash
#
# Retrieve one reviewer queue from Hugging Face, prepare it once, optionally
# enrich selected evidence with compact product info, then split the prepared
# JSONL into fixed-size worker packages.
#
# Usage:
#   QUEUE=/path/to/reviewer_ids.md \
#   MATRIX_DATA_ROOT=/path/to/cache \
#   MATRIX_PACKAGE_OUT_ROOT=/path/to/packages \
#   persona/curation/existing_data/scripts/make_amazon_top_reviewer_batch_packages.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${MATRIX_REPO_ROOT:-$(cd "${SCRIPT_DIR}/../../../.." && pwd)}"

TOP_REVIEWER_QUEUE="${QUEUE:-${TOP_REVIEWER_QUEUE:-${REPO_ROOT}/persona/curation/existing_data/samples/amazon_reviews_2023/top_reviewers/amazon_top_10000_rich_persona_reviewer_ids_2018_2023.md}}"
DIMENSIONS="${MATRIX_DIMENSIONS:-${REPO_ROOT}/persona/schema/dimensions.json}"
DATA_ROOT="${MATRIX_DATA_ROOT:-${TMPDIR:-/tmp}/matraix_existing_data/amazon_top_reviewers_batch}"
OUT_ROOT="${MATRIX_PACKAGE_OUT_ROOT:-${TMPDIR:-/tmp}/matraix_packages/amazon_top_reviewers_batch}"
LOG_ROOT="${MATRIX_LOG_ROOT:-${DATA_ROOT}/logs}"
RUN_NAME="${RUN_NAME:-amazon_top_reviewers_batch}"

HF_REPO_ID="${AMAZON_REVIEWS_REPO_ID:-MatrAIx/MatrAIx}"
HF_ARTIFACT_PREFIX="${AMAZON_REVIEWS_ARTIFACT_PREFIX:-amazon/modal_artifacts/amazon_reviews_2018_2023_user_buckets_min30_verified70_text2000}"
HF_METADATA_ARTIFACT_PREFIX="${AMAZON_METADATA_ARTIFACT_PREFIX:-amazon/modal_artifacts/amazon_reviews_2023_metadata_by_parent_asin_bucket_v2}"
HF_CATEGORIES="${AMAZON_CATEGORIES:-all}"
HF_DOWNLOAD_DELAY_SECONDS="${HF_DOWNLOAD_DELAY_SECONDS:-0.30}"
HF_METADATA_DOWNLOAD_DELAY_SECONDS="${HF_METADATA_DOWNLOAD_DELAY_SECONDS:-0.05}"
TEMPORAL_TRAIN_FRACTION="${TEMPORAL_TRAIN_FRACTION:-0.8}"
MIN_REVIEW_TEXT_CHARS="${MIN_REVIEW_TEXT_CHARS:-0}"
MAX_TEXT_REVIEWS_PER_USER="${MAX_TEXT_REVIEWS_PER_USER:-200}"
MAX_USERS="${MAX_USERS:-0}"
PACKAGE_SIZE="${PACKAGE_SIZE:-100}"
MAX_PACKAGES="${MAX_PACKAGES:-0}"
INCLUDE_PRODUCT_INFO="${INCLUDE_PRODUCT_INFO:-1}"

RAW_HISTORIES="${DATA_ROOT}/${RUN_NAME}.raw.jsonl"
PREPARED_HISTORIES="${DATA_ROOT}/${RUN_NAME}.prepared.jsonl"
ENRICHED_HISTORIES="${DATA_ROOT}/${RUN_NAME}.prepared.product_info.jsonl"
FILTER_SUMMARY="${DATA_ROOT}/${RUN_NAME}.filter_summary.json"
ENRICH_SUMMARY="${DATA_ROOT}/${RUN_NAME}.product_enrich_summary.json"
ENRICH_CACHE="${DATA_ROOT}/${RUN_NAME}.product_metadata_cache.json"
MANIFEST_JSONL="${OUT_ROOT}/${RUN_NAME}.package_manifest.jsonl"
MANIFEST_MD="${OUT_ROOT}/${RUN_NAME}.package_manifest.md"
LOG_FILE="${LOG_ROOT}/${RUN_NAME}.log"

if [[ ! -f "${TOP_REVIEWER_QUEUE}" ]]; then
  echo "reviewer queue not found: ${TOP_REVIEWER_QUEUE}" >&2
  exit 2
fi
if [[ ! -f "${DIMENSIONS}" ]]; then
  echo "persona dimensions not found: ${DIMENSIONS}" >&2
  exit 2
fi

mkdir -p "${DATA_ROOT}" "${OUT_ROOT}" "${LOG_ROOT}"
cd "${REPO_ROOT}"
export PYTHONPATH="${REPO_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

exec > >(tee -a "${LOG_FILE}") 2>&1

echo "== Amazon top-reviewer batch package build =="
echo "queue: ${TOP_REVIEWER_QUEUE}"
echo "data root: ${DATA_ROOT}"
echo "package root: ${OUT_ROOT}"
echo "run name: ${RUN_NAME}"
echo "package size: ${PACKAGE_SIZE}"
echo "include product info: ${INCLUDE_PRODUCT_INFO}"
echo ""

if [[ "${REUSE_RAW_HISTORIES:-1}" == "1" && -s "${RAW_HISTORIES}" ]]; then
  echo ">> reusing raw histories: ${RAW_HISTORIES}"
else
  echo ">> retrieving histories once from Hugging Face"
  EXPORT_CMD=(
    python3 persona/curation/existing_data/scripts/export_hf_amazon_user_histories.py
    --user-ids "${TOP_REVIEWER_QUEUE}"
    --repo-id "${HF_REPO_ID}"
    --artifact-prefix "${HF_ARTIFACT_PREFIX}"
    --categories "${HF_CATEGORIES}"
    --download-delay-seconds "${HF_DOWNLOAD_DELAY_SECONDS}"
    --output "${RAW_HISTORIES}"
  )
  if [[ -n "${HF_TOKEN:-}" ]]; then
    EXPORT_CMD+=(--token "${HF_TOKEN}")
  fi
  "${EXPORT_CMD[@]}"
fi

if [[ "${REUSE_PREPARED_HISTORIES:-1}" == "1" && -s "${PREPARED_HISTORIES}" ]]; then
  echo ">> reusing prepared histories: ${PREPARED_HISTORIES}"
else
  echo ">> preparing histories with temporal split and review filtering"
  python3 persona/curation/existing_data/scripts/prepare_hf_amazon_user_histories.py \
    --input "${RAW_HISTORIES}" \
    --output "${PREPARED_HISTORIES}" \
    --summary-output "${FILTER_SUMMARY}" \
    --train-fraction "${TEMPORAL_TRAIN_FRACTION}" \
    --min-review-text-chars "${MIN_REVIEW_TEXT_CHARS}"
fi

if [[ "${INCLUDE_PRODUCT_INFO}" == "1" ]]; then
  if [[ "${REUSE_ENRICHED_HISTORIES:-1}" == "1" && -s "${ENRICHED_HISTORIES}" ]]; then
    echo ">> reusing targeted product histories: ${ENRICHED_HISTORIES}"
  else
    echo ">> enriching selected text reviews and non-text construction rows with product context"
    ENRICH_CMD=(
      python3 persona/curation/existing_data/scripts/enrich_prepared_amazon_product_info.py
      --input "${PREPARED_HISTORIES}"
      --output "${ENRICHED_HISTORIES}"
      --summary-output "${ENRICH_SUMMARY}"
      --repo-id "${HF_REPO_ID}"
      --metadata-artifact-prefix "${HF_METADATA_ARTIFACT_PREFIX}"
      --max-text-reviews-per-user "${MAX_TEXT_REVIEWS_PER_USER}"
      --download-delay-seconds "${HF_METADATA_DOWNLOAD_DELAY_SECONDS}"
      --cache "${ENRICH_CACHE}"
    )
    if [[ -n "${HF_TOKEN:-}" ]]; then
      ENRICH_CMD+=(--token "${HF_TOKEN}")
    fi
    "${ENRICH_CMD[@]}"
  fi
  PACKAGE_HISTORIES="${ENRICHED_HISTORIES}"
else
  PACKAGE_HISTORIES="${PREPARED_HISTORIES}"
fi

echo ">> building local packages from prepared JSONL"
PACKAGE_CMD=(
  python3 persona/curation/existing_data/scripts/make_amazon_top_reviewer_package_manifest.py
  --user-histories "${PACKAGE_HISTORIES}" \
  --dimensions "${DIMENSIONS}" \
  --out-root "${OUT_ROOT}" \
  --manifest-jsonl "${MANIFEST_JSONL}" \
  --manifest-md "${MANIFEST_MD}" \
  --run-name "${RUN_NAME}" \
  --package-size "${PACKAGE_SIZE}" \
  --max-users "${MAX_USERS}" \
  --max-packages "${MAX_PACKAGES}" \
  --max-text-reviews-per-user "${MAX_TEXT_REVIEWS_PER_USER}" \
  --source amazon
)
if [[ "${REUSE_PACKAGES:-1}" == "1" ]]; then
  PACKAGE_CMD+=(--reuse-packages)
else
  PACKAGE_CMD+=(--force-packages)
fi
"${PACKAGE_CMD[@]}"

echo ""
echo "done."
echo "packages: ${OUT_ROOT}"
echo "manifest jsonl: ${MANIFEST_JSONL}"
echo "manifest md: ${MANIFEST_MD}"
echo "log: ${LOG_FILE}"
