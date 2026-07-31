#!/usr/bin/env bash
# Start the LiteLLM proxy that acts as the global LLM rate limiter (Plan B).
#
# Usage:
#   ./application/playground/litellm/run_proxy.sh            # port 4000
#   PORT=4100 ./application/playground/litellm/run_proxy.sh
#
# Runs from a dedicated sibling venv (application/playground/litellm/.venv) so
# the proxy's heavy extras (fastapi, granian, redis, ...) never pollute the
# project .venv. The venv is created/installed on first run.
#
# The proxy reads OPENAI_API_KEY (and optionally ANTHROPIC_API_KEY) from
# .env.local to call the real upstream providers. Clients then point at this
# proxy via OPENAI_BASE_URL — see docs/application.md § LiteLLM rate-limiter proxy.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="${SCRIPT_DIR}/config.yaml"
ENV_FILE="${SCRIPT_DIR}/../.env.local"
VENV_DIR="${SCRIPT_DIR}/.venv"
PORT="${PORT:-4000}"

# Bootstrap the isolated proxy venv on first run.
if [[ ! -x "${VENV_DIR}/bin/litellm" ]]; then
  echo "Setting up isolated proxy venv at ${VENV_DIR} (first run) ..."
  uv venv "${VENV_DIR}"
  uv pip install --python "${VENV_DIR}" 'litellm[proxy]'
fi

# Load real upstream keys from .env.local into this proxy's environment.
if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
else
  echo "warning: ${ENV_FILE} not found; relying on already-exported env vars" >&2
fi

# CRITICAL: the proxy must call the REAL providers, not itself. If .env.local
# has the routing vars uncommented (to point CLIENTS at the proxy), strip them
# here so the proxy's own upstream calls don't loop back into this process.
unset OPENAI_BASE_URL OPENAI_API_BASE

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "error: OPENAI_API_KEY is not set (needed for upstream calls + proxy master key)" >&2
  exit 1
fi

echo "Starting LiteLLM proxy on http://127.0.0.1:${PORT} (config: ${CONFIG})"
echo "Point clients at:  OPENAI_BASE_URL=http://127.0.0.1:${PORT}/v1"
# Single worker so the in-memory rpm/tpm accounting stays exact.
exec "${VENV_DIR}/bin/litellm" \
  --config "${CONFIG}" --host 127.0.0.1 --port "${PORT}" --num_workers 1
