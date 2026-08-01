# Packages

MatrAIx is modular. Beyond the core Playground runtime, the packages directory provides optional libraries for extending Harbor jobs and grading agent outputs. This page covers the optional packages and the viewer app paired with `harbor view`.

---

## Overview

All packages are installed the same way — from the repository root:

```bash
uv pip install -e packages/playground
uv pip install -e packages/rewardkit
uv pip install -e packages/harbor-langsmith
```

You can install any subset of these; none are required for basic Harbor task execution.

---

## Playground Core

The Playground core library (`packages/playground/`) powers both the Playground UI backend and the in-process Harbor runtime adapters. It is a shared foundation providing:

- **Persona loading** — instantiating personas from coreset data
- **User simulation** — embedding personas into agents for task execution
- **In-process runners** (`playground.inprocess`) — running Harbor jobs without needing a separate server
- **Scoring helpers** — utilities for defining and computing task scores

This package is typically installed as a dependency of other packages or the main application backend. It shares some modules with the backend source tree (`backend.*` modules) in the application layer.

---

## Rewardkit

**Harbor Rewardkit** is a lightweight grading toolkit for defining and running verifiers. It discovers and runs folder-based reward criteria against an agent's workspace, producing structured JSON scores. Rewardkit works standalone or with the Harbor task format.

### What it does

Rewardkit scans a `tests/` directory for reward definitions in two forms:

1. **Programmatic criteria** — Python functions that check outputs directly
2. **Judge-based evaluation** — LLM or agent CLI judges that assess work against criteria

Both approaches run concurrently and combine into a single score per reward.

### Installation

```bash
python -m pip install -e packages/rewardkit
```

### Programmatic example

Create Python criterion functions in your tests directory:

```python
# tests/check.py
from rewardkit import criteria

criteria.file_exists("output.txt")
criteria.file_contains("output.txt", "hello")
```

### Judge-based example

Define LLM or agent evaluation in a TOML file:

```toml
# tests/quality.toml
[judge]
judge = "anthropic/claude-sonnet-4-6"
files = ["/app/main.py"]

[[criterion]]
description = "Is the code correct?"
type = "binary"
```

### Running verifiers

Add Rewardkit to your test script:

```bash
# tests/test.sh
uvx harbor-rewardkit@0.1 /tests
```

Rewardkit will write results to `/logs/verifier/reward.json` with per-reward scores and a detailed breakdown.

### Learn more

See the [Rewardkit documentation](https://harborframework.com/docs/rewardkit) and a [full working example](https://github.com/harbor-framework/harbor/tree/main/examples/tasks/reward-kit-example) on GitHub.

---

## harbor-langsmith

**harbor-langsmith** integrates LangSmith tracing and dataset management with Harbor jobs. Use it to log job execution traces, compare agent behavior, and manage test datasets.

### Installation

```bash
python -m pip install -e packages/harbor-langsmith
export LANGSMITH_API_KEY=your-api-key
```

### Basic usage

Pass the plugin when running a Harbor job:

```bash
harbor run -c config.yaml --plugin langsmith
```

Or use the full import path:

```bash
harbor run -c config.yaml --plugin harbor_langsmith:LangSmithPlugin
```

### Configuration

The plugin accepts configuration through environment variables or CLI arguments. Environment variables:

- `LANGSMITH_API_KEY` — LangSmith API key (required)
- `HARBOR_LANGSMITH_DATASET` — dataset name to log traces into
- `HARBOR_LANGSMITH_EXPERIMENT` — experiment name for organizing runs
- `LANGSMITH_ENDPOINT` — custom LangSmith endpoint (optional)
- `LANGSMITH_WORKSPACE_ID` — workspace identifier (optional)
- `HARBOR_LANGSMITH_SYNC_DATASET` — auto-sync dataset after job (default: true)
- `HARBOR_LANGSMITH_FAIL_FAST` — stop on first trace error (default: false)

Alternatively, pass options via CLI:

```bash
harbor run -c config.yaml --plugin langsmith \
  --pk dataset_name=my-dataset \
  --pk experiment_name=my-run
```

Or in your job config under `kwargs:`.

### What gets logged

Each Harbor job run with the LangSmith plugin logs:
- All agent interactions and tool calls
- Step-by-step trajectories
- Environment observations and actions
- Final scores and outcomes

These are available in your LangSmith workspace for analysis and comparison.

---

## PersonaBench Viewer

The **PersonaBench Viewer** (`apps/viewer/`) is a web UI for browsing and inspecting simulation job results, trials, and agent trajectories. It is served by the `harbor view` command.

### Starting the viewer

View a completed job and its results:

```bash
harbor view ./jobs/my-job-name
```

This starts both the backend API server (which reads job outputs) and serves the viewer frontend at `http://localhost:5173`.

### Development mode

For frontend development with hot reloading:

```bash
npm ci
npm run dev
```

The frontend will be available at `http://localhost:5173`. To connect to a running Harbor backend, use the full command from the repository root:

```bash
harbor view ./jobs/my-job-name --dev
```

### Features

The viewer supports two modes:

- **Jobs mode** — browse evaluation results across multiple job runs, filter trials, compare task outcomes
- **Tasks mode** — browse task definitions and interact with them via AI chat

Navigation includes:
- Job listing and comparison across runs
- Task results within a job with filtering and sorting
- Trial trajectory viewer for step-by-step agent execution traces
- Task definition browser with embedded AI chat

### Building for deployment

Build the production bundle:

```bash
npm run build
```

Output is written to `build/client/`. Type-check before opening a PR:

```bash
npm run typecheck
```

### Deployment

`harbor view` serves static files from `environment/runtime/harbor/viewer/static/`, **not** directly from `apps/viewer/build/client/`. So after editing frontend code you must both build and copy the output:

```bash
# Option 1: Let harbor handle it (recommended)
harbor view ./jobs/my-job-name --build

# Option 2: Manual build + copy
cd apps/viewer
npm run build
rm -rf ../../environment/runtime/harbor/viewer/static
cp -r build/client ../../environment/runtime/harbor/viewer/static
```

After either option, restart the `harbor view` server for changes to take effect.

### Technology stack

- React 19 with React Router 7
- TanStack Query for data fetching
- TanStack Table for sortable data
- Tailwind CSS v4 for styling
- shadcn/ui components
- Shiki for syntax highlighting

### Requirements

Use Node.js 20.19.0 or newer. The checked-in `.node-version` and `.nvmrc` files specify the tested runtime version.

---

## Related

- [Handbook](README.md) — docs home
- [Quickstart](quickstart.md) — first runs
- [Environment](environment/README.md) — Harbor runtime
- Integrate Rewardkit into Harbor tasks for automated grading
- Use harbor-langsmith to trace agent behavior and manage evaluation datasets
- Explore job results with `harbor view`
