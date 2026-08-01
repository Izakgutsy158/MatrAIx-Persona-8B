# probe-survey_code-summary-documentation

**Attribute:** `code_summary_documentation` — X=`Always includes function-level TLDR` / Y=`Never includes TLDR` (code TLDR/docstring habit)
**Env:** Survey · `application/shared-survey-form`

Neutral survey question that lets the persona express `code_summary_documentation`. A/B over 5 positive
+ 5 negative personas (`persona_strategy.json`). Judge with `judge_adherence.py`
looking at: whether a docstring / TLDR summary is included.

Run:
```
persona/validation/scripts/run_probe.sh <recipe> persona/validation/tasks/probe-survey_code-summary-documentation
```
