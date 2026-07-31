# Environment

The **Environment module** owns how simulations run — Harbor jobs, trial execution, persona agents, shared task environments, and optional remote workers. This page explains the runtime contract, execution surfaces, and configuration.

If you are new to MatrAIx, read this page to understand how personas, applications, and environments connect at runtime.

---

## How it works

MatrAIx separates **what to simulate** (persona profiles and task scenarios) from **how to execute it** (runtime and agents):

```text
  persona/datasets/          application/tasks/           environment/
  (YAML profiles)            (scenario + verifier)        (runtime + agents)
        │                            │                            │
        └──────── persona_path ──────┴──── task path ─────────────┘
                                     │
                              Harbor job YAML
                                     │
                         trial → agent → artifacts
                                     │
                              jobs/<job_name>/
```

| Layer | Path | Responsibility |
|-------|------|------------------|
| Persona input | `persona/datasets/matraix-persona-dev-sample/` | *Who* the simulated user is |
| Task definition | `application/tasks/<name>/` | *What* they do (`instruction.md`, verifier, `reporting.json`) |
| Task environment | `environment/task-environments/application/` | Docker images, sidecars, browser stacks |
| Runtime | `environment/runtime/harbor/` | Job/trial loop, backends (host, docker, use-computer, …) |
| Agents | `environment/agents/matraix/agents/` | `persona-claude-code`, `persona-browser-use`, `persona-computer-1`, … |
| Job recipes | `configs/jobs/` | Multi-trial batches, concurrency, agent/model defaults |
| Outputs | `jobs/` | Per-trial artifacts, verifier results, optional aggregation |

Applications define scenarios. Environment executes them. Persona data is **referenced** (`persona_path=…`), never copied into task folders.

---

## Execution surfaces

Three ways to launch the same Harbor contract:

| Surface | When to use | Entry |
|---------|-------------|-------|
| **Harbor CLI** | Scripts, CI, debugging | `uv run harbor run -c configs/jobs/…` |
| **Playground** | Interactive task play, persona sampling | [quickstart.md §10](guides/quickstart.md#10-playground--play-tasks-visually) |
| **Playground API** | Automation, external tools | `POST /api/harbor/jobs` — [rest-api.md](guides/rest-api.md) |

All paths share:

- the same task folders under `application/tasks/`
- the same artifact layout under `jobs/<job_name>/`
- the same agent and backend resolution rules

### Execution planes

| Plane | Meaning | Configure |
|-------|---------|-----------|
| `harbor` (default) | API or laptop runs `harbor run` locally | `MATRIX_EXECUTION_PLANE=harbor` |
| `remote` | API dispatches to a Remote Runner worker over HTTP | `MATRIX_EXECUTION_PLANE=remote` + `REMOTE_RUNNER_API_URL` |

Remote plane details: [unified-runtime.md](guides/unified-runtime.md).

**Security note:** the remote plane sends only `PYTHONPATH` and `MATRIX_*` task exports over HTTP. API keys must live on the **worker**, not in the dispatch payload.

---

## Directory structure

```text
environment/
  adapters/                 Optional external benchmark adapters (manifest-backed)
  agents/matraix/      Persona-conditioned agent implementations
  runtime/harbor/           Harbor CLI, trial loop, models, verifier, viewer backend
  task-environments/
    application/            Persona shared-* + SUT *-sidecar_* (shared-chat-persona, 
                            chatbot-api-sidecar_*, chatbot-mcp-sidecar_*, 
                            web-sidecar_*, shared-web-*, shared-os-app-*, …)

configs/jobs/
  example-job-recipe/       Smoke + small local demos
  application-task-job-recipe/  Generated multi-persona application jobs

packages/
  playground/             Playground Python package (remote runner, harbor helpers)
  rewardkit/                Verifier / LLM-judge toolkit

apps/viewer/                Frontend paired with `harbor view`
```

Python import names stay stable: `harbor.*`, `matraix.agents.*`, `playground.*`.

---

## Environment variables

### Execution plane

| Variable | Purpose |
|----------|---------|
| `MATRIX_EXECUTION_PLANE` | `harbor` (default) or `remote` |
| `REMOTE_RUNNER_API_URL` | Remote runner base URL (required for `remote`) |
| `REMOTE_RUNNER_API_KEY` | Optional bearer token for the worker API |
| `REMOTE_RUNNER_HARBOR_COMMAND` | Override `harbor` CLI on the worker |
| `REMOTE_RUNNER_INLINE` | Dev/tests: run jobs inline in the API process |

### Task exports (local + remote worker)

Set before `harbor run`, or let `generate_application_job.py` print them:

| Variable | When |
|----------|------|
| `MATRIX_SURVEY_TASK_PATH` | Survey / json-survey trials |
| `MATRIX_CHATBOT_TASK_PATH` | Chatbot / user-sim trials |
| `MATRIX_CHATBOT_DOMAIN` | Recommender domain (legacy compat) |
| `MATRIX_CHATBOT_APPLICATION_ID` | Chat sidecar application id |
| `MATRIX_CHATBOT_APPLICATION_CONTEXT` | Chat sidecar context |
| `MATRIX_CHATBOT_MAX_TURNS` | User-sim turn cap |

### Model credentials (local process / worker)

Not sent over the remote plane. Per-agent names:

| Agents | Typical keys |
|--------|----------------|
| `persona-claude-code`, `persona-json-survey`, browser/CUA personas | `ANTHROPIC_API_KEY` |
| User-sim / OpenAI backends | `OPENAI_API_KEY` |
| `persona-browser-use`, OpenHands SDK | `LLM_API_KEY` or provider-specific |
| `persona-computer-1` on use.computer | `USE_COMPUTER_API_KEY` |

Full matrix: [choosing-an-agent.md](guides/choosing-an-agent.md).

### Playground reporting (optional)

| Variable | Purpose |
|----------|---------|
| `PLAYGROUND_REPORTING_ENABLE_LLM` | Enable LLM judge rollups in aggregation |
| `PLAYGROUND_REPORTING_LLM_MODEL` | Override judge model |

---

## One trial, end to end

```mermaid
flowchart LR
  subgraph inputs
    P[persona YAML]
    T[task.toml + instruction]
  end
  subgraph harbor
    J[job YAML]
    TR[trial]
    A[persona agent]
    V[verifier]
  end
  subgraph outputs
    O[jobs/.../artifacts]
    R[reward + aggregation]
  end
  P --> TR
  T --> TR
  J --> TR
  TR --> A
  A --> O
  O --> V
  V --> R
```

1. **Job recipe** selects task path, agent, model, and N persona paths.
2. **Trial** picks one persona, materializes instruction, runs the agent.
3. **Verifier** (`application/tasks/.../tests/`) scores outputs under `/logs/verifier/`.
4. **Aggregation** (`report_job.py` or Playground) rolls up batch metrics from `reporting.json`.

---

## Benchmark adapters

Adapters convert external benchmarks into Harbor-compatible task directories. They belong under `environment/adapters/<adapter-name>/` because they are runtime integration code, not Persona schema or application task definitions.

### Adapter layout

Each adapter keeps its code and generated outputs local to its own directory:

```text
environment/adapters/
  manifest.schema.json
  <adapter-name>/
    README.md
    manifest.toml
    pyproject.toml
    src/<package-name>/
    _generated/       ignored local output
```

Generated tasks, downloaded datasets, trajectories, screenshots, videos, and historical job outputs do not belong in git. Put them under the adapter-local `_generated/` directory while developing, then upload selected artifacts to external storage and link them from documentation.

### Adapter manifest

Every adapter must include `manifest.toml` with:

- source repository, path, and commit
- target path in Playground
- package name and Python package import name
- owner or original author
- external data and credential requirements
- smoke commands that validate the adapter without writing to shared paths
- excluded source paths, especially lockfiles and generated outputs
- status: `enabled`, `experimental`, or `archived`

Use `manifest.schema.json` as the contract for required fields.

### Current adapters

- `simpleqa/`: experimental OpenAI SimpleQA adapter migrated from MatrAIx-ai/MatrAIx/adapters/simpleqa.

---

## Docker snippets

`environment/docker-snippets/` holds shared Docker helper scripts for Playground task images. Because Harbor builds each task from its own `environment/` directory, task Dockerfiles cannot reliably `COPY` from this shared location, so the canonical script lives here and is synced into task-local copies:

```bash
python scripts/sync_docker_snippets.py --write    # sync copies (CI uses --check)
```

The main snippet is `install-claude-code.sh`, which installs Claude Code, `uv`, and base runtime directories for the `persona-claude-code` survey/chat task images.

---

## Singularity / Apptainer (HPC)

`environment/runtime/harbor/environments/singularity/` provides a Harbor environment backend for running tasks on HPC/SLURM clusters using [Singularity/Apptainer](https://apptainer.org/) containers instead of Docker. The host-side `singularity.py` converts Docker images to `.sif`, launches the container, and drives it over HTTP to a small FastAPI server (`server.py`) started by `bootstrap.sh`. Features include file-locked image caching, a memory watchdog, port-collision retry, and dpkg overlay-compatibility fixes.

```bash
harbor trials start -p /path/to/task \
  --environment-type singularity \
  --environment-kwarg singularity_image_cache_dir=/path/to/sif/cache
```

In `task.toml`, set `[environment].docker_image` to a Docker image name (converted to `.sif` automatically) or to a pre-built `.sif` path. Additional kwargs: `singularity_image_cache_dir`, `singularity_force_pull`, and `singularity_no_mount`.

---

## Leaderboard submission (CLI)

`environment/runtime/harbor/leaderboard/` adds CLI support for submitting a run to a Harbor Hub leaderboard and validating it. `harbor leaderboard submit` runs static validation plus the Hub RPCs. Dynamic validation runs in a separate deployable worker (its Docker image and deploy workflow are not part of this repository).

---

## Related documentation

| Doc | Topic |
|-----|-------|
| [Choosing an agent](guides/choosing-an-agent.md) | Agent ↔ API key matrix |
| [Harbor vs remote plane](guides/unified-runtime.md) | Execution plane details |
| [Playground HTTP API](guides/rest-api.md) | REST API reference |
