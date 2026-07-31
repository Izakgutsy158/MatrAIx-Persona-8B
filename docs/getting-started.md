# Getting Started

Welcome to MatrAIx. This guide walks you through installing and running your first persona simulation.

MatrAIx lets you **simulate interactions with AI systems using synthetic user personas** — before deploying to real users. Instead of generic testing, you instantiate sampled persona profiles as LLM agents and run them through reproducible tasks across four environments: Survey, AI Chatbot, Web, and App (native desktop/mobile). Each run is reproducible, measurable, and captures the trajectory and outputs your simulated user produces.

**Time:** ~30–60 minutes for your first end-to-end run (most time spent building Docker images on web/app tasks).

---

## What You Need

| Requirement | Why |
|-------------|-----|
| **[Docker](https://docs.docker.com/get-docker/)** | Web, desktop/mobile, and some tasks use containers |
| **uv** | Python package manager + `harbor` CLI |
| **Node.js 20+** | Playground frontend (optional but recommended for interactive exploration) |
| **Anthropic API key** | Persona agents. [Create one](https://console.anthropic.com/) if needed |

Persona pools for local runs: `persona/datasets/matraix-persona-dev-sample/` (200 profiles; the **smoke test uses persona `0042`**).

---

## 1. Install Docker

1. Install [Docker Desktop](https://docs.docker.com/get-docker/) (or Docker Engine on Linux).
2. Start Docker and wait for it to report "running".
3. Verify in a terminal:

   ```bash
   docker run --rm hello-world
   ```

   You should see a "Hello from Docker!" message. Fix any Docker issues before continuing.

---

## 2. Install uv and clone the repo

**Install [uv](https://docs.astral.sh/uv/)**:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Open a **new terminal** and check:

```bash
uv --version
```

On macOS you can also use Homebrew: `brew install uv`.

**Clone and install:**

```bash
git clone <repo-url> && cd MatrAIx
uv venv --python 3.12
uv pip install -e .
uv pip install -e packages/playground
uv pip install -e packages/harbor-langsmith
uv pip install -e packages/rewardkit
uv pip install -e environment/adapters/simpleqa
```

Verify the CLI:

```bash
uv run harbor --help
```

---

## 3. Run the smoke test

This verifies Docker and Harbor work together using a built-in reference task — no API key needed:

```bash
uv run harbor run -c configs/jobs/example-job-recipe/harbor-smoke-local.yaml
```

First run builds a Docker image (several minutes).

**Success:** the command finishes without error and writes output under `jobs/harbor-smoke-local/`.

This uses the minimal `examples/tasks/hello-world/` Docker task. The `examples/` directory holds small runnable Harbor examples for local smoke testing — keep any additions small and directly runnable, and prefer module-local examples under `persona/`, `application/`, or `environment/` when an example belongs to one module.

---

## 4. Set your API key

Persona agents read your **`ANTHROPIC_API_KEY`** from the shell:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

To persist across terminal sessions, add it to `~/.zshrc` or `~/.bashrc`, then open a new terminal.

---

## Understanding MatrAIx Runs

| Term | Meaning |
|------|---------|
| **Task** | A reproducible scenario: product brief + survey / chat / web interface + verifier. Example: `example-survey_product-feedback`. |
| **Persona** | A synthetic user profile (YAML file with demographics, preferences, communication style). Example: `persona_0042.yaml` |
| **Trial** | One complete run: **one persona** + **one task** → agent responds → verifier scores the response |
| **Job** | A batch container: Harbor runs **many trials** from a single YAML config. Output lands in `jobs/<job_name>/` with one subfolder per trial. |
| **Agent** | How the LLM is invoked (e.g., `persona-claude-code` runs Claude through the CLI with persona injected) |

---

## 5. Run a single persona (terminal)

Pick a task and run it with one persona. This is a single **trial**.

### Survey example

```bash
uv run harbor run \
  -a persona-claude-code \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/matraix-persona-dev-sample/persona_0042.yaml \
  -p application/tasks/example-survey_product-feedback
```

| Flag | Meaning |
|------|---------|
| `-p` | Task path (the scenario folder) |
| `-a` | Agent name (`persona-claude-code`, `persona-browser-use`, …) |
| `-m` | Model ID for that agent |
| `--ak persona_path=...` | Which persona to simulate (pick any `persona_XXXX.yaml` from `matraix-persona-dev-sample`) |

**What happens:**

1. Harbor reads the persona and task materials.
2. The agent generates a response.
3. A verifier scores the submission.
4. One trial folder lands in `jobs/`.

For agent-to-task mappings and other options, see the [application module docs](guides/choosing-an-agent.md).

---

## 6. Batch — run many personas at once

Running single trials by hand doesn't scale. Use `generate_application_job.py` to sample personas, build a job recipe, and launch all trials at once:

```bash
uv run python application/scripts/generate_application_job.py \
  --task application/tasks/example-survey_product-feedback \
  --execution-mode auto \
  --sample-size 10 \
  --seed 42 \
  --dataset persona/datasets/matraix-persona-dev-sample
```

The script outputs an exact `harbor run` command to execute. Run it:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
uv run harbor run -c configs/jobs/application-task-job-recipe/example-survey-product-feedback-auto-n10.yaml
```

**What a job means:** one **task**, **N trials** — each trial uses a different persona sampled from the pool. All trials share the same agent and model. Trials can run in parallel (edit `n_concurrent_trials` in the generated YAML).

**Cost note:** 10 trials ≈ 10 LLM calls. Start with `--sample-size 3` while testing.

For sampling with filters, stratification, or saved cohorts, see [Job Generation Scripts](application.md#job-generation-scripts).

---

## 7. Find your output

After a job finishes, explore the results:

```text
jobs/<job_name>/
├── result.json           # Summary stats
├── job.log
└── <trial_name>/
    ├── results.json      # Reward / verifier scores
    ├── persona_meta.json # Which persona was used
    └── artifacts/
        └── app/output/   # Agent's submission (JSON)
```

View all job trials in a browser:

```bash
uv run harbor view jobs --build
```

This opens a local viewer UI listing jobs, trials, transcripts, and artifacts. Use it to compare how different personas responded to the same task.

---

## 8. Playground — explore tasks interactively

After the smoke test passes, use the **Playground** UI to pick tasks, sample personas, launch Harbor jobs, and inspect trajectories without writing YAML by hand.

### Start the Playground

**Terminal A — API backend**

```bash
VENV=.venv bash application/playground/backend/run_dev.sh
```

**Terminal B — frontend with hot reload**

```bash
cd application/playground/frontend && npm ci && npm run dev
```

Open **http://localhost:5173** (proxies `/api` to `:8765`).

Before running tasks, check the **Preflight** chip in the footer — it validates that your API keys, Docker, and persona datasets are ready.

### Using the Playground

1. Open the **Playground** tab.
2. Switch task type: **Survey** · **Chat** · **Web** · **App**.
3. Pick a task card; read the scenario in the right panel.
4. Sample personas:
   - **Quick pick** (defaults to persona `0042`, the smoke test ID)
   - **Random** (sample uniformly)
   - **Stratified** (balance across a demographic dimension)
5. Leave **Mode → auto** and click **Run eval**.
6. Watch live progress; open a trial to see trajectory, scorecard, and verifier output.
7. Use **Runs** in the top bar to re-open past jobs.

**First-run notes by task type:**

| Type | Notes |
|------|-------|
| Survey | Fast — runs on the host without Docker |
| Chat | Host auto-mode; toggle **Start sidecar** if the task shows it's down |
| Web | Docker image builds on first run (several minutes); pick the web driver matching the task stack |
| App | Docker or use.computer depending on platform |

For API reference, see [rest-api.md](guides/rest-api.md).

---

## 9. Create a new task

### Understand the structure

Read [task-guide.md](guides/task-guide.md) for details on task folder layout, `task.toml` metadata, verifiers, and environment definitions.

### Copy an example

Start from the closest reference task:

```bash
# Survey
cp -R application/tasks/example-survey_product-feedback application/tasks/<your-task-name>

# Chat with HTTP API sidecar
cp -R application/tasks/example-chat-api_support_chatbot application/tasks/<your-task-name>

# Chat with MCP sidecar
cp -R application/tasks/example-chat-mcp_support_chatbot application/tasks/<your-task-name>

# Web (pick one)
cp -R application/tasks/example-web-playwright_quote-choice application/tasks/<your-task-name>

# App / computer-use (macOS / iOS / Linux)
cp -R application/tasks/example-computer-use-macos_calendar-reminder-handoff application/tasks/<your-task-name>
```

### Edit your task

1. **`task.toml`** — task metadata (`type`, `domain`, `tags`), timeouts, and environment definition
2. **`instruction.md`** — scenario + required `/app/output/` format (persona-facing; no agent names)
3. **`input/`** — context files, schemas, survey questions, or chatbot config
4. **`tests/`** — verifier that scores submissions and identifies key trajectory fields
5. **`reporting.json`** — (optional) batch reporting policy

### Test with one persona

```bash
uv run python application/scripts/generate_application_job.py \
  --task application/tasks/<your-task-name> \
  --execution-mode auto \
  --persona-ids 0042

# Run the printed harbor command
```

### Iterate in Playground

Register the task (see [task-guide.md § Playground registration](guides/task-guide.md#playground-registration)), restart the backend, then play with Quick pick personas before scaling.

### Batch of personas

Use the same sampling script as step 6 with your task path.

---

## Quick reference

| Goal | Command | Output |
|------|---------|--------|
| Explore/debug visually | Playground (Mode **auto**) | `jobs/` |
| Survey/chat (terminal) | `generate_application_job.py --execution-mode auto` | `jobs/<job_name>/` |
| Validate setup only | `harbor-smoke-local.yaml` | smoke task result |
| Batch with many personas | `generate_application_job.py` + `harbor run` | `jobs/` |
| Browse trajectories | `harbor view` or Playground **Runs** | local viewer |
| Create new task | copy `example-*` + register | `application/tasks/<name>/` |

---

## Learn more

| Doc | Purpose |
|-----|---------|
| [Application](application.md) | Application module overview |
| [quickstart.md](guides/quickstart.md) | Detailed walkthrough with all task types |
| [task-guide.md](guides/task-guide.md) | Task folder structure and checklist |
| [choosing-an-agent.md](guides/choosing-an-agent.md) | Agent ↔ form ↔ API keys |
| [web-interaction.md](guides/web-interaction.md) | Playwright vs browser-use vs Cocoa vs CUA |
| [application.md § Playground App](application.md#playground-app) | Playground app details |
| [persona.md](persona.md) | Persona schema and datasets |
| [Environment](environment.md) | Harbor runtime and task environments |

---

## Troubleshooting

**Docker not running:** Start Docker Desktop or verify Docker Engine is active on Linux.

**uv not found:** Ensure you opened a new terminal after installing; `source $HOME/.local/bin/env` if the installer suggested it.

**API key error:** Verify `export ANTHROPIC_API_KEY="sk-ant-..."` is set in the same terminal you run `harbor run` from. Check `echo $ANTHROPIC_API_KEY`.

**Task image build times out:** Web and app tasks build Docker images on first run. This is normal and takes several minutes. Subsequent runs reuse the cached image.

**Persona file not found:** Verify the persona YAML path matches a file in `persona/datasets/matraix-persona-dev-sample/persona_XXXX.yaml`.

**Port 5173 or 8765 already in use:** Kill the process or pass different ports to the Playground start scripts (see [application.md § Playground App](application.md#playground-app)).
