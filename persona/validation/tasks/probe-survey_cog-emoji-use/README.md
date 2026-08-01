# probe-survey_cog-emoji-use

**Attribute:** `cog_emoji_use` — X=`Heavy` / Y=`Never` (emoji usage)
**Env:** Survey · `application/shared-survey-form`

Neutral survey question that lets the persona express `cog_emoji_use`. A/B over 5 positive
+ 5 negative personas (`persona_strategy.json`). Judge with `judge_adherence.py`
looking at: how many emoji appear.

Run:
```
persona/validation/scripts/run_probe.sh <recipe> persona/validation/tasks/probe-survey_cog-emoji-use
```
