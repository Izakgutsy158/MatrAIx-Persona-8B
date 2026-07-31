# Shared clinical-trial pre-screening task environment

Shared runtime for the ten `application/tasks/chat_prescreening-*` tasks.

`docker-compose.yaml` starts a vendored screener sidecar (`prescreening-chatbot`,
Flask, port 8000) that `main` waits on. The sidecar is a deterministic,
rule-based smoke implementation (same tier as the Acme support sidecar): it
loads the trial's criteria from `prescreening-chatbot/protocols/`, asks every
applicable criterion one question at a time (with a yes/no/not-sure
confirmation fallback for free-text answers), gives the preliminary-screen
disclaimer, and ends with the fenced-JSON final assessment the task verifiers
check.

Protocol selection, in order: request `protocolId`/`title` matching a vendored
protocol (task folder name or `protocol_id`), the `PRESCREENING_PROTOCOL_ID`
env var, else the first protocol. `GET /health` lists the loaded protocols.

`prescreening-chatbot/protocols/*.json` are copies of each task's
`tests/protocol.json` - if a task's criteria change, refresh its copy here.

To test a different (e.g. LLM-backed) screener product instead of the vendored
sidecar, set `CHATBOT_UPSTREAM_PRESCREENING` (legacy `PRESCREENING_CHATBOT_URL`)
to your endpoint; the tasks' `input/chatbot.yaml` prefers it over the default
`http://prescreening-chatbot:8000`.
