# probe-survey_cog-use-of-jargon

**Attribute:** `cog_use_of_jargon` — X=`Heavy` / Y=`Avoids jargon` (jargon usage)
**Env:** Survey · `application/shared-survey-form`

Neutral survey question that lets the persona express `cog_use_of_jargon`. A/B over 5 positive
+ 5 negative personas (`persona_strategy.json`). Judge with `judge_adherence.py`
looking at: how much technical jargon is used.

Run:
```
persona/validation/scripts/run_probe.sh <recipe> persona/validation/tasks/probe-survey_cog-use-of-jargon
```
