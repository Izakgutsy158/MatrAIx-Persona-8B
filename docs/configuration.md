# Configuration

A MatrAIx run is fully described by a **job recipe** — a YAML file that specifies the task, persona agent, language model, and persona profile(s) to instantiate. Job recipes live under `configs/jobs/`.

## Quick start

Point Harbor at a recipe with the `-c` flag:

```bash
uv run harbor run -c configs/jobs/example-job-recipe/appSim-example-survey-local.yaml
```

## Job recipe anatomy

A recipe has four main sections — run settings, environment, persona agent, and task(s):

```yaml
job_name: appSim-example-survey-local   # output label; artifacts go to jobs/<job_name>/
jobs_dir: jobs                           # where run artifacts are written
n_attempts: 1                            # repeat each (persona, task) trial N times
n_concurrent_trials: 1                   # how many trials run in parallel
timeout_multiplier: 1.0                  # scale per-task timeouts
quiet: false                             # verbosity

environment:
  type: docker                           # docker (isolated) or host (run locally)
  delete: true                           # remove the container after the run

agents:
  - name: persona-claude-code            # which persona agent to use
    model_name: anthropic/claude-sonnet-4-6  # simulated-user LLM (provider/model)
    kwargs:
      persona_path: persona/datasets/matraix-persona-dev-sample/persona_0042.yaml

tasks:
  - path: application/tasks/example-survey_product-feedback
```

## YAML fields reference

### Job metadata

| Field | Type | Meaning |
|-------|------|---------|
| `job_name` | string | Label for this run. Output artifacts appear in `jobs/<job_name>/`. |
| `jobs_dir` | string | Base directory where Harbor writes results (default: `jobs/`). |
| `n_attempts` | int | Repeat each trial N times. Useful for measuring variance or pass@k. |
| `n_concurrent_trials` | int | Number of trials to run in parallel. 1 for serial; increase for faster bulk runs. |
| `timeout_multiplier` | float | Multiply all per-task timeouts by this factor. 1.0 is standard. |
| `quiet` | bool | If `true`, suppress detailed logs during execution. |

### Environment

| Field | Type | Meaning |
|-------|------|---------|
| `environment.type` | string | `docker` (recommended, isolated) or `host` (run on the current machine). |
| `environment.delete` | bool | If `true`, remove the Docker container after the run completes. |

### Agent

| Field | Type | Meaning |
|-------|------|---------|
| `agents[].name` | string | Persona agent name (e.g., `persona-claude-code`, `persona-browser-use`). |
| `agents[].model_name` | string | Provider-prefixed model identifier (e.g., `anthropic/claude-sonnet-4-6`, `openai/gpt-4o-mini`, `dashscope/qwen3.7-max`). |
| `agents[].kwargs.persona_path` | string | Path to persona YAML profile (e.g., `persona/datasets/matraix-persona-dev-sample/persona_0042.yaml`). |
| `agents[].env` | object | Optional environment variable overrides (e.g., `agents[].env.ANTHROPIC_API_KEY`). |

### Task

| Field | Type | Meaning |
|-------|------|---------|
| `tasks[].path` | string | Path to task directory under `application/tasks/` (e.g., `application/tasks/example-survey_product-feedback`). |

## Persona agents and models

Every run specifies a **persona agent** (the automation harness), a **persona LLM** (which model plays the simulated user), and optionally the persona profile itself.

### Agent and model pairing

| Agent | Application | Persona model | Example recipe | API key on host |
|-------|-------------|---------------|-----------------|-----------------|
| `persona-json-survey` | Survey | Any (auto pick) | – | `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `DASHSCOPE_API_KEY` |
| `persona-user-sim` | Chatbot | Any (auto pick) | – | `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `DASHSCOPE_API_KEY` |
| `persona-claude-code` | Survey, Chatbot | `anthropic/claude-*` | `appSim-example-survey-local.yaml`, `appSim-example-chat-local.yaml` | `ANTHROPIC_API_KEY` |
| `persona-gemini-cli` | Survey, Chatbot | `google/gemini-*` | `appSim-example-survey-local.yaml` | `GEMINI_API_KEY` |
| `persona-codex` | Survey, Chatbot | `openai/gpt-*` | `appSim-example-survey-local.yaml` | `OPENAI_API_KEY` |
| `persona-openhands-sdk` | Web (Playwright) | Any | `appSim-example-web-playwright-local.yaml` | `LLM_API_KEY` (or `DASHSCOPE_API_KEY` for DashScope models) |
| `persona-browser-use` | Web (browser automation) | Any | `appSim-example-web-browser-use-local.yaml` | `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `DASHSCOPE_API_KEY`, or `LLM_API_KEY` |
| `persona-cocoa` | Web (browser + shell) | Any | `appSim-example-web-cocoa-local.yaml` | `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `DASHSCOPE_API_KEY`, or `LLM_API_KEY` |
| `persona-computer-1` | Web / Computer-use (macOS, iOS, Linux) | `anthropic/claude-*` or `dashscope/*` | `appSim-example-computer-use-macos-local.yaml` | `ANTHROPIC_API_KEY`, `DASHSCOPE_API_KEY`, and optionally `USE_COMPUTER_API_KEY` (macOS/iOS) |

### Persona model resolution

The **persona LLM** is separate from the chat sidecar backend (e.g., `MATRIX_CHATBOT_ENGINE`). Harbor resolves the model in this order:

1. **Job YAML `agents[].model_name`** (highest priority)
2. **CLI flag `-m` or `--model-name`** (when generating recipes)
3. Environment variables (checked per agent; see table below)
4. Default: `anthropic/claude-haiku-4-5`

### Supported model providers

- **Anthropic:** `anthropic/claude-haiku-4-5`, `anthropic/claude-sonnet-4-6`, etc.
- **OpenAI:** `openai/gpt-4o-mini`, `openai/gpt-4o`, etc.
- **Google Gemini:** `google/gemini-2.5-pro` (with `persona-gemini-cli`)
- **DashScope (Alibaba):** `dashscope/qwen3.7-max`, `dashscope/deepseek-v4-pro`, etc.

### API keys and environment variables

Set these in your shell before running a job. Each agent reads keys differently:

#### Auto-mode agents (most flexible)

| Agent | Required keys on host |
|-------|----------------------|
| `persona-json-survey` | `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `DASHSCOPE_API_KEY` (match `-m`) |
| `persona-user-sim` | Persona: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `DASHSCOPE_API_KEY`; chat sidecar: often `OPENAI_API_KEY` |

#### CLI harness agents (vendor-locked)

| Agent | Required key on host | Example model |
|-------|---------------------|----------------|
| `persona-claude-code` | `ANTHROPIC_API_KEY` | `anthropic/claude-sonnet-4-6` |
| `persona-gemini-cli` | `GEMINI_API_KEY` | `google/gemini-2.5-pro` |
| `persona-codex` | `OPENAI_API_KEY` | `openai/gpt-4o` |

#### Web and computer-use agents

| Agent | Required keys on host |
|-------|----------------------|
| `persona-openhands-sdk` | `LLM_API_KEY` (or `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`/`DASHSCOPE_API_KEY`; map to `LLM_API_KEY` if needed) |
| `persona-browser-use` | `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `DASHSCOPE_API_KEY`, or `LLM_API_KEY` |
| `persona-cocoa` | `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `DASHSCOPE_API_KEY`, or `LLM_API_KEY` |
| `persona-computer-1` | `ANTHROPIC_API_KEY` or `DASHSCOPE_API_KEY` (+ `USE_COMPUTER_API_KEY` for macOS/iOS via use.computer) |

### Setting API keys

Export keys in your shell before launching a run:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export GEMINI_API_KEY="..."
export DASHSCOPE_API_KEY="..."

# If using persona-openhands-sdk, map to LLM_API_KEY
export LLM_API_KEY="${ANTHROPIC_API_KEY}"

# If using persona-computer-1 on macOS or iOS
export USE_COMPUTER_API_KEY="..."
```

You can also add these to your shell profile (`~/.zshrc`, `~/.bashrc`) to make them persistent.

Alternatively, set keys per-agent in the job YAML via `agents[].env`:

```yaml
agents:
  - name: persona-claude-code
    model_name: anthropic/claude-sonnet-4-6
    env:
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
    kwargs:
      persona_path: persona/datasets/matraix-persona-dev-sample/persona_0042.yaml
```

## Web interaction modes

Web tasks support four Docker-based execution modes and computer-use (CUA):

| Mode | Agent | How the agent sees the page | Best for | Trade-off |
|------|-------|----------------------------|----------|-----------|
| **Playwright** | `persona-openhands-sdk` | Terminal agent writes Python; reads via Playwright DOM API | Lower cost, CI-friendly, repeatable | Agent must write working scripts |
| **browser-use** | `persona-browser-use` | Dedicated browser loop with page structure (DOM); optional screenshots | Purpose-built web agent | Slower than hand-written Playwright scripts |
| **Cocoa** | `persona-cocoa` | Same browser loop as browser-use; also shell + files in one container | All-in-one digital agent without CUA licensing | Heavier Docker base image |
| **CUA (computer-use)** | `persona-computer-1` | Screenshot each turn of a real remote desktop; mouse/keyboard actions | Highest human fidelity (screen-based) | Slowest, highest LLM cost |

### Example: Playwright web task

```bash
export LLM_API_KEY="${ANTHROPIC_API_KEY}"

uv run harbor run \
  -a persona-openhands-sdk \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/matraix-persona-dev-sample/persona_0042.yaml \
  -p application/tasks/example-web-playwright_quote-choice
```

Or use the checked-in recipe:

```bash
uv run harbor run -c configs/jobs/example-job-recipe/appSim-example-web-playwright-local.yaml
```

### Example: browser-use web task

```bash
uv run harbor run -c configs/jobs/example-job-recipe/appSim-example-web-browser-use-local.yaml
```

See [web-interaction.md](guides/web-interaction.md) for detailed mode comparison, web submission contracts, and how to author new web tasks.

## Persona profile and default sample

Personas are instantiated via the YAML path in `agents[].kwargs.persona_path`. The recommended smoke profile for testing is:

```
persona/datasets/matraix-persona-dev-sample/persona_0042.yaml
```

This lightweight profile requires no external data and is suitable for smoke tests, demos, and development.

For larger studies, use the [public 1M coreset](https://huggingface.co/datasets/MatrAIx2026/MatrAIx_Persona_1M_Public_Release) on Hugging Face or the in-repo sample dataset at `persona/datasets/matraix-persona-dev-sample/`.

## Job recipe conventions

All job recipes live under `configs/jobs/` and follow these guidelines:

- Use paths that exist in this repository.
- Reference personas from the checked-in sample dataset or document external data dependencies in the recipe README.
- Do not commit generated `jobs/` outputs; they are gitignored.
- Keep generated or bulk recipes separate from hand-curated examples.

### Recipe directories

- `example-job-recipe/` — local application task examples backed by `application/tasks/` and the sample persona dataset; includes smoke recipe `harbor-smoke-local.yaml` for API-key-free testing.
- `application-task-job-recipe/` — generated application job recipes from Playground UI launches and `application/scripts/generate_application_job.py`; most files are gitignored; a small set of curated fixtures is checked in.
- `persona-task-grounding-job-recipe/` — curated generated persona grounding recipe fixtures.

### Example recipes

Run any example recipe from the repository root with:

```bash
uv run harbor run -c configs/jobs/example-job-recipe/<recipe>.yaml
```

The example recipes use the checked-in sample persona `persona/datasets/matraix-persona-dev-sample/persona_0042.yaml`:

- `harbor-smoke-local.yaml` — no-API-key smoke check using the generic `hello-world` task and built-in `oracle` agent (preferred quick check).
- `appSim-example-survey-local.yaml`
- `appSim-example-chat-local.yaml`
- `appSim-example-debug-local.yaml`
- `appSim-example-web-playwright-local.yaml`
- `appSim-example-web-browser-use-local.yaml`
- `appSim-example-web-cocoa-local.yaml`
- `appSim-example-web-linux-cua-local.yaml`
- `appSim-example-computer-use-linux-local.yaml`
- `appSim-example-computer-use-macos-local.yaml`
- `appSim-example-computer-use-ios-local.yaml`

Some recipes require API keys, local Docker, use-computer, Apple container runtime support, or browser/Cocoa-specific task images.

## Batch job generation

To generate job recipes for many personas or tasks at once, use the job generator script:

```bash
uv run python application/scripts/generate_application_job.py \
  --task application/tasks/example-survey_product-feedback \
  --execution-mode auto \
  --model-name anthropic/claude-sonnet-4-6 \
  --persona-ids 0042,0100,0200
```

The script outputs a YAML recipe and a Harbor command to run it. The recipe pins `agents[].model_name` so you can edit it or pass `--model-name` on regenerate to change the persona LLM.

Generated recipes land under `configs/jobs/application-task-job-recipe/` (see [Recipe directories](#recipe-directories) above).

## Examples

### Survey task with Claude

```bash
export ANTHROPIC_API_KEY="sk-ant-..."

uv run harbor run \
  -a persona-claude-code \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/matraix-persona-dev-sample/persona_0042.yaml \
  -p application/tasks/example-survey_product-feedback
```

### Chatbot task with Claude

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."  # optional, for chat sidecar

uv run harbor run \
  -a persona-user-sim \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/matraix-persona-dev-sample/persona_0042.yaml \
  -p application/tasks/chat_recai
```

### Computer-use task (macOS)

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export USE_COMPUTER_API_KEY="..."

uv run harbor run \
  -a persona-computer-1 \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/matraix-persona-dev-sample/persona_0042.yaml \
  -p application/tasks/example-computer-use-macos_calendar-reminder-handoff
```

Or use the pre-configured recipe:

```bash
uv run harbor run -c configs/jobs/example-job-recipe/appSim-example-computer-use-macos-local.yaml
```

### No API key required (smoke test)

```bash
uv run harbor run -c configs/jobs/example-job-recipe/harbor-smoke-local.yaml
```

This uses the `oracle` reference agent (not a real LLM) and is useful for verifying setup before using API keys.

## Related

- [../README.md](../README.md) — Project overview and quick start.
- [quickstart.md](guides/quickstart.md) — End-to-end walkthrough: terminal → batch → Playground UI.
- [choosing-an-agent.md](guides/choosing-an-agent.md) — Detailed agent, model, and API-key matrix with subscription auth options.
- [web-interaction.md](guides/web-interaction.md) — Deep dive into web interaction modes, submission contracts, and task authoring.
