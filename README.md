# MatrAIx

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![Website](https://img.shields.io/badge/Website-matraix.ai-0A0A0A)](https://matraix.ai/)
[![Hugging Face](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Persona%201M-ffd21e)](https://huggingface.co/datasets/MatrAIx2026/MatrAIx_Persona_1M_Public_Release)
[![Discord](https://img.shields.io/badge/Discord-Join%20us-5865F2?logo=discord&logoColor=white)](https://discord.gg/knVyQQnRFa)

> **Simulate before reality.**

**MatrAIx** is a population-scale, persona-driven infrastructure for evaluating
AI systems and interactive products with heterogeneous simulated users. Instead
of testing against a generic or interchangeable user, MatrAIx instantiates
sampled persona records as LLM agents and runs them through reproducible tasks
across four environments — **Survey**, **AI Chatbot**, **Web**, and **App**
(native desktop and mobile, including macOS and iOS).

At its foundation is a shared schema of **1,290 categorical dimensions** covering
background, psychology, capability, and behavior. Personas combine
dependency-aware synthetic generation with evidence-aware human grounding; a
deterministic, quality-filtered coreset of **one million personas** is released
for research on
[Hugging Face](https://huggingface.co/datasets/MatrAIx2026/MatrAIx_Persona_1M_Public_Release).
Shared telemetry, task-owned verification, and reporting connect individual
responses and trajectories to subgroup- and population-level findings.

The name nods to *The Matrix* — a simulated world useful for exploration, stress
testing, and hypothesis generation, **not a replacement for evidence from real
people**.

---

## What's in this repository

```text
MatrAIx/
├── persona/           Persona dimension schema, dev sample pool, curation
│                      and grounding pipelines, and quality/post-processing.
├── application/       Reusable task specifications (survey, chat, web, app),
│                      shared task contracts, and the Playground UI + API.
├── environment/       Harbor runtime, persona-conditioned agents, and the
│                      shared task environments (Docker images, sidecars).
├── packages/          playground · rewardkit · harbor-langsmith
├── apps/              viewer — frontend paired with `harbor view`
├── examples/          minimal example tasks
├── src/               the `matraix` Python package
├── configs/jobs/      curated Harbor job recipes
└── scripts/           helper scripts
```

Harbor writes run outputs to `jobs/` when you launch recipes from
`configs/jobs/`; those stay local and are gitignored. Large generated datasets
live outside git (see the Hugging Face release above).

📖 **Full documentation:** the [MatrAIx Handbook](docs/index.md) collects the
module overviews and how-to guides (getting started, running simulations,
persona, application, environment). Per-task docs live next to each task.

Browse it as a searchable site with [MkDocs](https://www.mkdocs.org/):

```bash
uv run --with mkdocs-material mkdocs serve   # then open http://127.0.0.1:8000
```

---

## Requirements

- [Docker](https://docs.docker.com/get-docker/)
- [uv](https://docs.astral.sh/uv/) and Python 3.12
- Node.js 20+ (Playground / viewer frontends only)
- Model API keys for persona-agent examples — see [choosing-an-agent.md](docs/guides/choosing-an-agent.md)

---

## Installation

```bash
git clone <repo-url> && cd MatrAIx
uv venv --python 3.12
uv pip install -e .
uv pip install pytest pytest-asyncio httpx
uv pip install -e packages/playground
uv pip install -e packages/harbor-langsmith
uv pip install -e packages/rewardkit
uv pip install -e environment/adapters/simpleqa
```

All Harbor commands run as **`uv run harbor …`**.

---

## Quick start

**Smoke test** (terminal, no API key required):

```bash
uv run harbor run -c configs/jobs/example-job-recipe/harbor-smoke-local.yaml
```

**Run an application task** — walk through [QUICKSTART.md](docs/guides/quickstart.md)
(terminal → batch → UI). For interactive play, jump to
[Playground §10](docs/guides/quickstart.md#10-playground--play-tasks-visually) (Node.js 20+).

A terminal batch run (CI, scripts) uses the same Harbor jobs, e.g.:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
uv run harbor run -c configs/jobs/example-job-recipe/appSim-example-survey-local.yaml
```

**Inspect results** — use Playground **Runs** for a cohort debrief, or
`uv run harbor view jobs/<job_name> --build` for raw trajectories, agent logs,
and file-level artifacts.

---

## How it works

1. A **job recipe** (`configs/jobs/…`) selects a task, a persona agent, a model,
   and one or more persona records to sample.
2. Each **trial** instantiates one persona as an agent, materializes the task
   instruction, and runs the agent in its environment (survey / chat / web / app).
3. A **verifier** (task-owned, under `application/tasks/<name>/tests/`) scores the
   outputs.
4. **Reporting** rolls per-trial results up to cohort- and population-level
   metrics.

Persona profiles live under `persona/datasets/`; tasks reference them by path at
launch and never copy persona data into task folders.

---

## Configuration

A run is fully described by a **job recipe** — a YAML file under
`configs/jobs/`. Point Harbor at one with `-c`:

```bash
uv run harbor run -c configs/jobs/example-job-recipe/appSim-example-survey-local.yaml
```

A recipe has three parts — run settings, the persona agent, and the task(s):

```yaml
job_name: appSim-example-survey-local   # output goes to jobs/<job_name>/
jobs_dir: jobs                           # where run artifacts are written
n_attempts: 1                            # attempts per (persona, task) trial
n_concurrent_trials: 1                   # parallelism
timeout_multiplier: 1.0                  # scale per-task timeouts
quiet: false

environment:
  type: docker                           # docker | host
  delete: true                           # remove the container after the run

agents:
  - name: persona-claude-code            # which persona agent (see table below)
    model_name: anthropic/claude-sonnet-4-6   # simulated-user LLM
    kwargs:
      persona_path: persona/datasets/matraix-persona-dev-sample/persona_0042.yaml

tasks:
  - path: application/tasks/example-survey_product-feedback
```

**Fields at a glance**

| Field | Meaning |
|-------|---------|
| `job_name` / `jobs_dir` | Run label and output location (`jobs/<job_name>/`). |
| `n_attempts` | Repeat each trial N times (variance / pass@k). |
| `n_concurrent_trials` | How many trials run in parallel. |
| `environment.type` | `docker` (isolated, default) or `host` (run on the machine). |
| `agents[].name` | The persona agent to instantiate (see below). |
| `agents[].model_name` | Provider-prefixed model, e.g. `anthropic/claude-sonnet-4-6`, `openai/gpt-4o-mini`. |
| `agents[].kwargs.persona_path` | The persona YAML to instantiate (`persona_0042` is the default smoke profile). |
| `tasks[].path` | One or more task directories under `application/tasks/`. |

**Persona agents** (pick by environment):

| Agent | Environment | Example recipe |
|-------|-------------|----------------|
| `persona-claude-code` | Survey, Chatbot | `appSim-example-survey-local.yaml`, `appSim-example-chat-local.yaml` |
| `persona-openhands-sdk` | Web (Playwright) | `appSim-example-web-playwright-local.yaml` |
| `persona-browser-use` | Web (browser automation) | `appSim-example-web-browser-use-local.yaml` |
| `persona-cocoa` | Web (macOS Cocoa) | `appSim-example-web-cocoa-local.yaml` |
| `persona-computer-1` | App / computer-use (macOS, iOS, Linux) | `appSim-example-computer-use-macos-local.yaml` |

**API keys** — set the key matching your `model_name` provider in your shell:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."   # anthropic/claude-* models
export OPENAI_API_KEY="sk-..."          # openai/gpt-* models
export DASHSCOPE_API_KEY="..."          # dashscope/* (OpenAI-compatible) models
```

The smoke recipe (`harbor-smoke-local.yaml`) uses the `oracle` reference agent
and needs **no API key**. See
[choosing-an-agent.md](docs/guides/choosing-an-agent.md) for the full
agent ↔ model ↔ key matrix, and [docs/configuration.md](docs/configuration.md#job-recipe-conventions) for recipe conventions.

To generate recipes for many personas or tasks at once, use
`application/scripts/generate_application_job.py`.

---

## Community

Questions, ideas, or want to get involved? Join us on
[Discord](https://discord.gg/knVyQQnRFa).

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
