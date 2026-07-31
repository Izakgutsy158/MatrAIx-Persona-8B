# DeepTutor chatbot sidecar

Local endpoint host for `application/tasks/chat_deeptutor-learning-goal`.
Vendors **[DeepTutor](https://github.com/HKUDS/DeepTutor)** (HKUDS,
Apache-2.0) as the real product under test, pinned by GHCR image digest
(release 1.5.1), plus a thin HTTP adapter that exposes the MatrAIx chatbot
contract.

## Services

| Service | Role |
|---|---|
| `deeptutor` | The product under test — pinned `ghcr.io/hkuds/deeptutor` image, backend on port 8001 (internal only) |
| `tutor-adapter` | `/v1/messages` ⇄ DeepTutor partner-chat bridge, port 8000 (internal only) |
| `main` | Harbor persona-agent container overlay (`depends_on` the adapter being healthy) |

## What the adapter does

On first request (idempotent, lock-guarded):

1. Waits for the DeepTutor backend to come up.
2. **Seeds the model catalog** (`PUT /api/v1/settings/catalog`) with one LLM
   profile built from env — DeepTutor normally requires this via its web
   Settings UI; seeding it via API is what makes the sidecar reproducible
   headlessly. Existing profiles with a real key are left as-is; the one
   exception is a profile whose `api_key` is empty (e.g. seeded on a first
   boot before a key was available in the `deeptutor-data` volume) — its key
   is refreshed from env so a later start with a real key recovers.
3. **Ensures a tutor partner exists** (`POST /api/v1/partners`, `start: true`)
   with a neutral adaptive-tutor description.

Then per message: `POST /v1/messages {sessionId, message}` →
`POST /api/v1/partners/{id}/chat {content, session_id}` → `{sessionId, reply,
turn}`. DeepTutor keeps per-session conversation context server-side.

## Configuration

| Env | Default | Meaning |
|---|---|---|
| `OPENAI_API_KEY` | — | Key for the default `openai` binding |
| `ANTHROPIC_API_KEY` | — | Used if no OpenAI key is set (set binding too) |
| `DEEPTUTOR_LLM_BINDING` | `openai` | DeepTutor model binding (`openai`, `anthropic`, …) |
| `DEEPTUTOR_LLM_MODEL` | `gpt-4o-mini` | Tutor model id |
| `DEEPTUTOR_LLM_BASE_URL` | (empty) | Override provider base URL |
| `DEEPTUTOR_LLM_API_KEY` | — | Explicit key, wins over the provider keys above |
| `DEEPTUTOR_PARTNER_NAME` | `MatrAIx Tutor` | Partner display name |

## Standalone smoke (without Harbor)

The `main` service is an overlay merged in by the runtime; to run the sidecar
alone, stub it:

```bash
cat > /tmp/main-stub.yaml <<'EOF'
services:
  main:
    image: alpine:3.20
    command: sleep infinity
EOF
docker compose -f docker-compose.yaml -f /tmp/main-stub.yaml up -d --build
docker compose -f docker-compose.yaml -f /tmp/main-stub.yaml exec tutor-adapter \
  python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read())"
```

## Data policy

No datasets are vendored. DeepTutor state (settings, sessions) lives in the
`deeptutor-data` named volume, created at runtime and disposable.
