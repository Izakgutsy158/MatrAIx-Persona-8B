# probe-survey_cog-verbosity

**Attribute:** `cog_verbosity` — X=`Rambling` / Y=`Terse` (verbosity / response length)
**Env:** Survey · `application/shared-survey-form`

Neutral survey question that lets the persona express `cog_verbosity`. A/B over 5 positive
+ 5 negative personas (`persona_strategy.json`). Judge with `judge_adherence.py`
looking at: how long / elaborated the answer is.

Run:
```
persona/validation/scripts/run_probe.sh <recipe> persona/validation/tasks/probe-survey_cog-verbosity
```
