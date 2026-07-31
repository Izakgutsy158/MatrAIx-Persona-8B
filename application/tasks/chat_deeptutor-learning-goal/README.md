# Personal Tutor (DeepTutor)

MatrAIx application task for **[DeepTutor](https://github.com/HKUDS/DeepTutor)**
(HKUDS, Apache-2.0), a real open-source AI tutoring product, exposed through the
standard chatbot REST contract. The persona agent acts as a learner with a
self-chosen learning goal, has a multi-turn tutoring conversation, and saves the
transcript plus a post-chat self-report.

Unlike a README-stub environment, this task ships a **fully vendored sidecar**
(`environment/task-environments/application/chatbot-api-sidecar_deeptutor/`):
a pinned DeepTutor GHCR image plus a thin adapter that seeds the model catalog,
creates a tutor partner, and bridges `/v1/messages` to DeepTutor's
session-persistent partner chat API. `uv run harbor run` works out of the box
with only a model API key.

## What it measures

Tutoring is a domain where persona conditioning should visibly change the
interaction: the same topic asked by a primary-schooler and a doctorate holder
should produce different explanations. The task captures:

- **Outcome** — did the persona make progress on their learning goal
  (`outcome_status`, grounded in self-report)?
- **Explanation level fit** — were explanations pitched at the persona's level
  (`too_simple` / `right_level` / `too_advanced` / `inconsistent`)? This is the
  headline persona-sensitivity signal, stratified by `highest_education`.
- **Adaptation** — did the tutor adapt its explanations across turns, or repeat
  itself (`explanation_adaptation`)?
- **Understanding checks** — did the tutor verify the learner was following
  (`checked_my_understanding`, `tutor_question_count`)?

## Contract

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Adapter health + DeepTutor bootstrap status |
| `POST` | `/v1/messages` | Send one user message, receive one tutor reply |

Session persistence: pass the same `sessionId` across turns; DeepTutor keeps
conversation context server-side per session.

## Environment

```toml
[environment]
definition = "application/shared-chat-persona"
local_compose = "application/chatbot-api-sidecar_deeptutor"
```

Model key: the sidecar reads `OPENAI_API_KEY` (default binding `openai`,
model `gpt-4o-mini`) or set `DEEPTUTOR_LLM_BINDING` / `DEEPTUTOR_LLM_MODEL` /
`DEEPTUTOR_LLM_API_KEY` for another provider. See the sidecar README for
details.

## Persona sampling

Stratified by `highest_education` (the dimension the SUT should adapt to most)
and `age_bracket`; 8 personas per smoke batch, 24 for the PR evidence batch.
