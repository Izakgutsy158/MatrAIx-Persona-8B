# Application

The Application module defines how persona-affiliated tasks are structured, executed, and evaluated in MatrAIx. A task is a runnable scenario where a simulated user interacts with a survey, chatbot, website, or native application to benchmark how well an AI agent can handle real-world interactions.

## What a Task Defines

Each task under `application/tasks/` is a self-contained folder that provides everything needed to run and evaluate one scenario:

- **`instruction.md`** — the scenario description, what the persona should accomplish, and submission requirements. Written from the user's perspective, with no agent names or implementation details.
- **`task.toml`** — Harbor metadata: task type, timeouts, resource limits, and which artifacts to collect.
- **`input/`** — task-specific materials (survey questions, chat API specs, website context, or app background).
- **`tests/`** — the verifier, which runs after each trial and scores outputs against evaluation criteria.
- **`reporting.json`** — batch reporting configuration that defines how to aggregate results across many personas.
- **`persona_strategy.json`** — target cohort filters and sampling preferences for the Playground.

Shared runtime environments live separately under `environment/task-environments/application/` — not inside task folders. Harbor resolves the `[environment].definition` in `task.toml` to locate the runtime.

## Task Types

MatrAIx supports four interaction modes. Choose the one that fits your benchmark question:

### Survey

Simulated personas answer a structured form or questionnaire.

| Aspect | Details |
|--------|---------|
| **Benchmark question** | How do personas answer this questionnaire? |
| **Reference task** | `example-survey_product-feedback` |
| **Key files** | `instruction.md`, `input/questionnaire.yaml`, `input/context.md` (optional) |
| **Runtime** | `shared-survey-form` |
| **Copy from** | `application/tasks/example-survey_product-feedback/` |

Questionnaire format (`input/questionnaire.yaml`) supports:
- Question types: `likert`, `single_choice`, `multi_choice`, `free_text`
- Optional metadata: `askRationale` (include reasoning), `askConfidence` (include confidence scores)

The verifier reads the platform-managed `survey_result.json` artifact and emits evaluation contexts for batch reporting.

### Chatbot

Simulated personas interact with an application through a chat API or MCP interface.

| Aspect | Details |
|--------|---------|
| **Benchmark question** | Can the chat experience resolve the user's goal? |
| **Reference task** | `chat_recai` |
| **Key files** | `instruction.md`, `input/chatbot.yaml`, `input/context.md` (optional), `input/protocol.md` (optional) |
| **Runtime** | `shared-chat-persona` + optional `chatbot-api-sidecar_*` or `chatbot-mcp-sidecar_*` |
| **Copy from** | `example-chat-api_support_chatbot` (REST API) or `example-chat-mcp_support_chatbot` (MCP) |

The `input/chatbot.yaml` file declares transport metadata, tool capabilities, and optional structured response fields that the persona can interact with. Platform artifacts include transcript and application result; the verifier extracts outcome, conversation process, and subjective feedback into evaluation contexts.

### Web

Simulated personas navigate a website or web application using a browser to accomplish a goal.

| Aspect | Details |
|--------|---------|
| **Benchmark question** | Can the agent use a website correctly? |
| **Reference task** | `example-web-playwright_quote-choice` |
| **Key files** | `instruction.md` (including result JSON schema), `input/context.md` (optional), `input/self_report_schema.yaml` (optional) |
| **Runtimes** | `shared-web-playwright`, `shared-web-browser-use`, `shared-web-cocoa`, `shared-web-cua-linux` |
| **Copy from** | `example-web-playwright_quote-choice` (Playwright), `example-web-browser-use_laptop-choice` (browser-use), `example-web-cocoa_plan-choice` (Cocoa), `example-web-cua_bookshop-choice` (CUA) |

Verifier evaluates the final artifact (submission, selection, or result state) and optionally captures browsing behavior and persona-specific decision-making. Supports post-run self-report via `input/self_report_schema.yaml`.

### OS / Computer-Use (App)

Simulated personas interact with native desktop or mobile applications, system settings, file systems, or multi-app workflows.

| Aspect | Details |
|--------|---------|
| **Benchmark question** | Can the agent complete native app or cross-app operating tasks safely? |
| **Reference task** | `example-computer-use-ios_photo-access-review` (iOS), `example-computer-use-macos_calendar-reminder-handoff` (macOS), `example-computer-use-linux_note-to-csv` (Linux) |
| **Key files** | `instruction.md` (including result schema), `input/context.md` (optional), `input/self_report_schema.yaml` (optional) |
| **Runtimes** | `shared-os-app-mac-ios` (macOS/iOS), `shared-os-app-linux` (Linux desktop) |
| **Copy from** | `application/tasks/example-computer-use-ios_photo-access-review/` |

Verifier uses outcome-based evaluation: verify the final state or submitted artifact, not an exact action sequence. Captures goal completion, side effects (collateral damage), and optionally persona alignment when persona traits affect the correct solution path.

---

## Task Contracts

### Verifier Output

Every verifier must emit `verifier/structured_output.json`, a normalized structure that describes what happened in one trial:

```json
{
  "contexts": [
    {
      "key": "task_outcome.primary",
      "contextType": "task_outcome",
      "label": "Task outcome",
      "facets": [
        {
          "key": "outcome_status",
          "role": "primary",
          "kind": "categorical",
          "value": "passed"
        }
      ]
    }
  ]
}
```

**Contexts** are typed slices (e.g., `task_outcome`, `question_response`, `user_feedback`). **Facets** are small named fields within each context (`outcome_status`, `response`, `reason`). This structure lets batch reporting aggregate hundreds of trials into summaries without parsing prose.

Each task type defines which contexts are required or recommended:

| Type | Minimum contexts | Purpose |
|------|------------------|---------|
| Survey | `question_response` (per question), `trial_summary` | Track answers and coverage |
| Chatbot | `task_outcome`, `conversation_summary` | Track resolution and process |
| Web | `task_outcome`, `decision`, `decision_process` (if browse/choose) | Track success and persona choices |
| OS/app | `task_outcome`, `goal_component` (per subgoal), `side_effects` | Track completion and safety |

Reuse shared context names and facet keys from the task-spec contracts. Add task-specific detail behind a `task_` prefix (e.g., `task_selected_color`) when needed.

### Batch Reporting: Two Layers

When many trials complete as one job, the platform builds `aggregation.json` for the Runs report. Reporting has two layers:

| Layer | Your role | What happens |
|-------|-----------|--------------|
| **Layer 1 — Automatic** | Emit valid `structured_output.json` | Platform computes stats: numerical averages, categorical counts, text samples |
| **Layer 2 — Optional** | Define `reporting.json` rules | Add semantic summaries, LLM judges, or thematic grouping on top of Layer 1 |

**Minimum viable `reporting.json`:**

```json
{
  "schemaVersion": "1.0",
  "contextRules": []
}
```

This enables Layer 1 aggregation with no extra setup. To add Layer 2 rules — for example, "summarize feedback grouped by satisfaction level" — define `contextRules` entries that specify which facets to summarize and how. See `task-spec/` example files for templates.

### Persona Injection

Personas are never copied into task folders. Instead, provide their path at job launch:

```bash
persona_path=/path/to/persona/datasets/matraix-persona-dev-sample
```

The runtime injects persona context (demographics, preferences, persona-specific goals) separately from the `instruction.md`. Keep task documentation focused on the product scenario, not persona demographics.

---

## Starting a Task

Follow these steps to add a new task:

1. **Pick an interaction type** — survey, chatbot, web, or OS/app — based on your benchmark question.
2. **Copy the canonical example** from the reference task listed above.
3. **Edit the scenario bundle:**
   - `instruction.md` — persona-facing goal and steps
   - `input/questionnaire.yaml` or `input/chatbot.yaml` — task-specific interaction definition
   - `input/context.md` (optional) — product or scenario background
4. **Author the verifier** (`tests/test.sh` and `test_*.py`) to emit `verifier/structured_output.json` with appropriate contexts and facets.
5. **Define `reporting.json`** — at minimum an empty `contextRules` list for Layer 1 aggregation.
6. **Set `persona_strategy.json`** — target cohort filters and sampling mode (Random or Stratified).
7. **Register in Playground** (if UI play is needed) — add an entry to `application/playground/backend/service/playground_task_registry.py`.
8. **Smoke test** — run one persona through the task and verify the verifier output.
9. **Batch and review** — launch a multi-persona job and inspect `aggregation.json` in the Runs UI.

For detailed file layouts, per-type authoring rules, and templates, see:
- [`task-guide.md`](guides/task-guide.md) — folder structure and file reference
- [`application/task-spec/README.md`](../application/task-spec/README.md) — step-by-step guide to adding a task
- Type-specific contracts: `application/task-spec/{survey,chatbot,web,os-app}/README.md`

---

## Shared Metrics and Evaluation

Web and OS/app tasks share a common evaluation philosophy. Both use outcome-based verification (final state, not action sequence) and a shared set of core contexts:

| Context | Role |
|---------|------|
| `task_outcome` | Main result: passed, failed, infeasible, error |
| `goal_component` | Per-subgoal completion tracking |
| `side_effects` | Collateral damage, safety checks, unintended edits |
| `execution_profile` | Steps, runtime, app/tool usage, GUI vs terminal paths |
| `user_feedback` | Post-run persona satisfaction, effort, trust, clarity |
| `persona_alignment` / `persona_constraint` | When persona traits affect correct behavior |

See [`shared-core-metrics.md`](task-spec/shared-core-metrics.md) for the shared contract and cross-task reuse rules.

---

## Running and Scaling Tasks

### Single Persona (Smoke Test)

Verify a new task with one persona before scaling:

```bash
cd /path/to/matraix-release
uv run harbor run -c configs/jobs/example-job-recipe/appSim-example-survey-local.yaml
```

See [`quickstart.md`](guides/quickstart.md) for the full end-to-end walkthrough.

### Multi-Persona Batch Job

Generate and run a job with many personas:

```bash
# Generate job config (via script)
uv run python application/scripts/generate_application_job.py \
  --task application/tasks/example-survey_product-feedback \
  --execution-mode auto \
  --sample-size 10

# Run the job (the script prints the exact recipe path)
uv run harbor run -c configs/jobs/application-task-job-recipe/<generated-recipe>.yaml
```

Results appear in `jobs/<job-id>/aggregation.json` and in the Playground **Runs** UI.

---

## Playground App

The **Playground** (`application/playground/`) is the MatrAIx workbench for evaluating interactive applications with simulated persona users. It bundles a React/Vite frontend (`frontend/`), a FastAPI backend (`backend/`), and the shared simulator package (`packages/playground/src/playground/`), and launches evaluations as **Harbor** batch jobs (`POST /api/harbor/jobs`).

### Running it

Build the frontend once, then start the backend:

```bash
cd application/playground/frontend && npm ci && npm run build && cd ../../..
PYTHONPATH=.:environment/runtime:packages/playground/src:application/playground \
  .venv/bin/python -m uvicorn backend.api.app:app --host 127.0.0.1 --port 8765 --workers 1
# then open http://127.0.0.1:8765
```

The packaged launcher `application/playground/run_demo.sh` does the same after a frontend build. For frontend development, run the API and the Vite dev server in separate terminals:

```bash
bash application/playground/backend/run_dev.sh
cd application/playground/frontend && npm run dev
```

Playground loads secrets from `application/playground/.env.local` (gitignored; copy `.env.local.example`). The dev/demo launchers source it automatically — keys exported only in your shell profile are not visible to non-interactive launchers.

### API surface

All endpoints mount under `/api` (interactive OpenAPI docs at `/docs`). Key endpoints include `/api/health`, `/api/preflight` (key/catalog/runtime readiness), `/api/config/options`, `/api/playground/personas`, and the Harbor job launch/poll pair `POST /api/harbor/jobs` + `GET /api/harbor/jobs/{job}`. See [`rest-api.md`](guides/rest-api.md) for the full contract and [`unified-runtime.md`](guides/unified-runtime.md) for the Harbor-backed unified startup commands.

### LiteLLM rate-limiter proxy (optional)

`application/playground/litellm/` provides an optional single-process proxy that funnels every OpenAI-family LLM call (Harbor agents/verifiers, persona/user-sim, batch reporting) through one shared `rpm`/`tpm` budget, so you can raise `n_concurrent_trials` without hitting provider 429 storms. Start it, then point callers at it:

```bash
./application/playground/litellm/run_proxy.sh   # PORT=4100 ... for a custom port
export OPENAI_BASE_URL=http://127.0.0.1:4000/v1
export OPENAI_API_BASE=http://127.0.0.1:4000/v1
```

Set per-model limits in `application/playground/litellm/config.yaml`. Claude personas auto-route through the proxy's OpenAI-compatible endpoint when `OPENAI_BASE_URL` is set. Stop the proxy and unset those vars to send calls directly to providers again.

---

## Job Generation Scripts

`application/scripts/` holds the CLI helpers for turning a task into a runnable Harbor job:

- [`generate_application_job.py`](../application/scripts/generate_application_job.py) samples personas and writes a multi-trial job YAML plus a `.meta.json` sidecar under `configs/jobs/application-task-job-recipe/` (the same directory Playground UI launches write to). It supports `--sample-size`, `--persona-ids` (explicit personas, skips sampling), `--execution-mode` (default `auto`, matching Playground Mode **auto**), repeated/comma-separated `--stratify`, `--name`, `--job-name`, and `--dataset`. The script prints the exact `export` lines and `harbor run` command to execute next.
- [`report_job.py`](../application/scripts/report_job.py) refreshes `jobs/<job_name>/aggregation.json` for a completed job and runs any configured `llm_*` reporting directives. Pass `--no-llm` for aggregation only, without live LLM calls.

Generated job recipes are gitignored unless a maintainer curates one in; use `--out` to write to a scratch path while testing.

```bash
uv run python application/scripts/generate_application_job.py \
  --task application/tasks/example-survey_product-feedback --execution-mode auto --persona-ids 0042
uv run python application/scripts/report_job.py jobs/<job_name>
```

---

## Files and Directories

```
application/
  tasks/                    ← your task folders
  task-spec/                ← type contracts, templates, and examples
  playground/               ← Playground UI, FastAPI backend, runner client
  scripts/                  ← generate_application_job.py, report_job.py
docs/guides/                ← quickstart, task-guide, choosing-an-agent, web-interaction
docs/task-spec/             ← shared metric + artifact contract deep dives
```

Shared environments:

```
environment/task-environments/application/
  shared-survey-form/
  shared-chat-persona/       ← chatbot persona agent
  chatbot-api-sidecar_*/     ← optional REST chat endpoints
  chatbot-mcp-sidecar_*/     ← optional MCP chat endpoints
  shared-web-playwright/
  shared-web-browser-use/
  shared-web-cocoa/
  shared-web-cua-linux/
  shared-os-app-mac-ios/
  shared-os-app-linux/
```

---

## Examples by Form

Use these as copy-from templates:

| Form | Path | Suggested Agent |
|------|------|-----------------|
| Survey | `application/tasks/example-survey_product-feedback/` | `persona-claude-code` |
| Chat (REST API) | `application/tasks/example-chat-api_support_chatbot/` | `persona-claude-code` |
| Chat (MCP) | `application/tasks/example-chat-mcp_support_chatbot/` | `persona-claude-code` |
| Chat (Recommender) | `application/tasks/chat_recai/` | `persona-claude-code` |
| Web (Playwright) | `application/tasks/example-web-playwright_quote-choice/` | `persona-openhands-sdk` |
| Web (browser-use) | `application/tasks/example-web-browser-use_laptop-choice/` | `persona-browser-use` |
| Web (Cocoa) | `application/tasks/example-web-cocoa_plan-choice/` | `persona-cocoa` |
| Web (CUA) | `application/tasks/example-web-cua_bookshop-choice/` | `persona-computer-1` |
| App (iOS) | `application/tasks/example-computer-use-ios_photo-access-review/` | `persona-computer-1` |
| App (macOS) | `application/tasks/example-computer-use-macos_calendar-reminder-handoff/` | `persona-computer-1` |
| App (Linux) | `application/tasks/example-computer-use-linux_note-to-csv/` | `persona-computer-1` |

---

## Further Reading

- [`quickstart.md`](guides/quickstart.md) — installation through batch runs and Playground
- [`task-guide.md`](guides/task-guide.md) — task folder anatomy and file reference
- [`application/task-spec/README.md`](../application/task-spec/README.md) — adding a task, with diagrams
- [`application/task-spec/survey/README.md`](../application/task-spec/survey/README.md) — survey contract and `questionnaire.yaml` format
- [`application/task-spec/chatbot/README.md`](../application/task-spec/chatbot/README.md) — chatbot contract and transcript handling
- [`application/task-spec/web/README.md`](../application/task-spec/web/README.md) — web interaction metrics and persona-sensitive choices
- [`application/task-spec/os-app/README.md`](../application/task-spec/os-app/README.md) — outcome-based app evaluation and safety checks
- [`choosing-an-agent.md`](guides/choosing-an-agent.md) — agent selection and API key setup
- [`web-interaction.md`](guides/web-interaction.md) — browser mode details (Playwright, browser-use, Cocoa, CUA)
