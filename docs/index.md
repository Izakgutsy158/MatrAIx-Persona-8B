# MatrAIx Handbook

MatrAIx is a population-scale, persona-driven infrastructure for evaluating AI
systems and interactive products with heterogeneous simulated users, across four
environments — **Survey**, **AI Chatbot**, **Web**, and **App**.

This handbook is the single entry point to the documentation. Per-task
documentation lives next to each task under `application/tasks/…` and
`examples/tasks/…`.

## Contents

1. **[Getting Started](getting-started.md)** — install, run the smoke test, run a
   task with one persona, batch runs, and the Playground UI.
2. **[Configuration](configuration.md)** — job-recipe YAML fields, the
   persona-agent ↔ environment ↔ model ↔ API-key matrix, and web interaction
   modes.
3. **[Persona](persona.md)** — the 1,290-dimension schema, curation and
   extraction pipelines, grounding tasks, the public 1M coreset, and the 1M pool.
4. **[Application](application.md)** — task types (survey / chat / web / app),
   what a task defines, task contracts, and batch reporting.
5. **[Environment](environment.md)** — Harbor runtime, execution surfaces,
   persona agents, task environments, and benchmark adapters.
6. **[Packages](packages.md)** — the optional `playground`, `rewardkit`, and
   `harbor-langsmith` packages, and the viewer app.
7. **[Persona Pipeline](persona-pipeline.md)** — technical reference for how the
   persona corpus is built: curation, human extraction, synthetic generation,
   and the post-processing chain (quality filter, deduplication, unified
   dataset, 1M coreset, statistics).
8. **[Validation](validation.md)** — the persona-adherence probe suite that
   checks whether persona attributes actually drive agent behavior (10
   attributes × 4 environments, positive/negative personas, LLM-judged).

## Guides

Hands-on, task-facing walkthroughs for running the application module:

- **[Quickstart](guides/quickstart.md)** — zero to a first multi-persona run,
  then into the Playground UI.
- **[Choosing an agent](guides/choosing-an-agent.md)** — persona-agent ↔ form
  mapping, model backends, and API keys.
- **[Web interaction](guides/web-interaction.md)** — browser modes (Playwright,
  browser-use, Cocoa, CUA) and web submission contracts.
- **[Task guide](guides/task-guide.md)** — task folder anatomy, `task.toml`,
  verifiers, and reference scenarios.
- **[Large-scale runs](guides/large-scale-runs.md)** — scaling batch runs.
- **[REST API](guides/rest-api.md)** — the Playground HTTP API reference.
- **[Unified runtime](guides/unified-runtime.md)** — Harbor vs remote execution
  planes.

## Task specification

Deep-dive contracts and cheat sheets for authoring task bundles (the onboarding
index lives at [`application/task-spec/README.md`](../application/task-spec/README.md)):

- **[Authoring a bundle](task-spec/authoring-bundle.md)** — per-type file trees
  and `persona_strategy.json`.
- **[Reporting and evaluation](task-spec/reporting-and-evaluation.md)** — batch
  aggregation internals and `contextRules`.
- **[Structured output quick reference](task-spec/structured-output-quick-reference.md)**
  — verifier context/facet keys and example JSON paths.
- **[Shared core metrics](task-spec/shared-core-metrics.md)** — the web/os-app
  shared core and subjective channel.
- **[Runtime boundary](task-spec/runtime-boundary.md)** — what runs where.
- **[Eval artifacts](task-spec/eval_artifacts.md)** — platform-managed chatbot
  artifacts.

See the [project README](../README.md) for a one-page overview and quick start.
