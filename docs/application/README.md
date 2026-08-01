# Application

Persona-driven **product scenarios** under `application/tasks/`: a simulated
user runs a survey, chatbot, website, or native app; a verifier scores the
trial; batch reporting rolls up a cohort.

## Task types

| Type | Reference task | Notes |
|------|----------------|-------|
| Survey | `example-survey_product-feedback` | Host auto; form / questionnaire |
| Chat | `example-chat-api_support_chatbot` | Host auto + optional sidecar |
| Web | `example-web-playwright_quote-choice` | Docker; see [web interaction](../environment/web-interaction.md) |
| OS-app | `example-computer-use-linux_note-to-csv` | Docker or use.computer (macOS/iOS) |

## Author a task (one path)

1. **Contracts** — [`application/task-spec/README.md`](../../application/task-spec/README.md)
   (type diagrams, metrics, reporting). Deep dives:
   [`application/task-spec/docs/`](../../application/task-spec/docs/authoring-bundle.md).
2. **Checklist** — [task-guide.md](task-guide.md) (`task.toml`, registration).
3. **Copy** an `example-*` under `application/tasks/`, edit, smoke via
   [Quickstart](../quickstart.md).

Ops notes also live in [`application/tasks/README.md`](../../application/tasks/README.md).

## Run

| How | Where |
|-----|--------|
| Hands-on path | [Quickstart](../quickstart.md) |
| Playground UI | Quickstart § Playground |
| HTTP API | [playground-api.md](playground-api.md) |
| Job recipes / generator | [Configuration](../configuration.md) · Quickstart § CLI |

```bash
uv run python application/scripts/generate_application_job.py \
  --task application/tasks/example-survey_product-feedback \
  --execution-mode auto \
  --persona-ids 0042
uv run harbor run -c configs/jobs/application-task-job-recipe/<generated>.yaml
```

## Related

| Doc | Role |
|-----|------|
| [Handbook](../README.md) | Docs home |
| [Quickstart](../quickstart.md) | First runs |
| [Task contracts](../../application/task-spec/README.md) | Specs and metrics |
| [Persona](../persona/README.md) | Pools, 1M, sampling |
| [Environment](../environment/README.md) | Harbor, agents, images |
