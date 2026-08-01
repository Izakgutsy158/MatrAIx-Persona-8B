# probe-survey_code-naming-verbosity

**Attribute:** `code_naming_verbosity` — X=`Highly verbose (long descriptive names)` / Y=`Single-letter names` (variable naming style)
**Env:** Survey · `application/shared-survey-form`

Neutral survey question that lets the persona express `code_naming_verbosity`. A/B over 5 positive
+ 5 negative personas (`persona_strategy.json`). Judge with `judge_adherence.py`
looking at: how long/descriptive the variable names are.

Run:
```
persona/validation/scripts/run_probe.sh <recipe> persona/validation/tasks/probe-survey_code-naming-verbosity
```
