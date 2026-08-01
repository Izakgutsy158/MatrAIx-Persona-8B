#!/usr/bin/env bash
# Run a validation probe recipe through Harbor, using an OpenAI-compatible API as
# the persona model. Wraps all the env wiring that the host-native survey agent
# needs.
#
# Usage:
#   persona/validation/scripts/run_probe.sh <recipe.yaml> [survey_task_path]
#
# Examples:
#   persona/validation/scripts/run_probe.sh persona/validation/recipes/survey-pos.yaml \
#       persona/validation/tasks/probe-survey_code-comment
#
# Requires: OPENAI_API_KEY (and optionally OPENAI_BASE_URL) exported, uv, docker.
set -euo pipefail

RECIPE="${1:?usage: run_probe.sh <recipe.yaml> [survey_task_path]}"
SURVEY_TASK_PATH="${2:-}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO_ROOT"

# --- persona-model API key (any OpenAI-compatible endpoint) ---
: "${OPENAI_API_KEY:?no API key found; export OPENAI_API_KEY=...}"
export OPENAI_API_KEY
export OPENAI_BASE_URL="${OPENAI_BASE_URL:-https://api.openai.com/v1}"

# --- PYTHONPATH so host-native persona agents can import `backend` etc. ---
export PYTHONPATH="${REPO_ROOT}:${REPO_ROOT}/environment/runtime:${REPO_ROOT}/packages/playground/src:${REPO_ROOT}/application/playground${PYTHONPATH:+:${PYTHONPATH}}"

# --- host-native survey agent needs the task path explicitly ---
if [ -n "$SURVEY_TASK_PATH" ]; then
  export MATRIX_SURVEY_TASK_PATH="${REPO_ROOT}/${SURVEY_TASK_PATH#"${REPO_ROOT}/"}"
fi

echo "[run_probe] recipe=$RECIPE"
echo "[run_probe] OPENAI_BASE_URL=$OPENAI_BASE_URL  token_len=${#OPENAI_API_KEY}"
[ -n "${MATRIX_SURVEY_TASK_PATH:-}" ] && echo "[run_probe] MATRIX_SURVEY_TASK_PATH=$MATRIX_SURVEY_TASK_PATH"

exec uv run harbor run -c "$RECIPE"
