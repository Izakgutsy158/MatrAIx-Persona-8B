# Pre-screening chatbot task 10: Smart Inhaler Support for Uncontrolled Asthma (BREATHE-EASY)

One of ten clinical-trial eligibility pre-screening chatbot tasks
(`chat_prescreening-01-diabetes` .. `chat_prescreening-10-asthma`), one synthetic trial protocol each.
Condition: smart inhaler for uncontrolled asthma. All data is synthetic (ClinicalTrials.gov style) -
no real studies, no real patients.

## Product under test

A pre-screening assistant that walks a potential participant through this
trial's inclusion/exclusion criteria and ends with one fenced-JSON verdict
(`final_assessment: true`, `eligibility`, `criteria_not_met`,
`criteria_unknown`, `notes`), after stating that pre-screening is preliminary.

## Suggested setup (non-binding)

The shared runtime (`environment/task-environments/application/chatbot-api-sidecar_prescreening/`)
vendors a deterministic screener sidecar (compose service `prescreening-chatbot`,
port 8000) that implements this trial - no external setup is needed for smoke
runs. To test a different screener product, set `CHATBOT_UPSTREAM_PRESCREENING`
(legacy `PRESCREENING_CHATBOT_URL`) to its endpoint; connection metadata is in
`input/chatbot.yaml`.
The machine-readable trial criteria the upstream must implement are in
`tests/protocol.json` (criterion IDs, inclusion/exclusion text, unknown-handling
rules, applicability conditions).

## Verifier

`tests/test_state.py` (stdlib only) checks the transcript shape, the fenced-JSON
verdict, and the preliminary-screen disclaimer, and emits
`verifier/structured_output.json` (`task_outcome`, `conversation_summary`, and
`user_feedback` when a self-report exists). When the transcript's `personaId`
names one of the **9 labeled test cases** in `tests/ground_truth.json`
(3 eligible / 5 ineligible / 1 insufficient-information), the predicted label is additionally checked against the
deterministic ground truth.

Known limitation: the stock chat harness does not yet tag a trial with a case
id, so the label check only engages for runners that pass one (transcript
`caseId`/`personaId` or the `MATRIX_TRIAL_CASE_ID` env var); otherwise trials
verify structurally and report `partially_resolved`. Each case in
`tests/ground_truth.json` carries its full medical `profile` (including the
deliberate boundary values), so a case-bound persona cohort can be
materialized from it once the binding design is agreed.
