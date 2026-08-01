# probe-survey_cog-politeness

**Attribute:** `cog_politeness` — X=`Very polite` / Y=`Rude` (politeness)
**Env:** Survey · `application/shared-survey-form`

Neutral survey question that lets the persona express `cog_politeness`. A/B over 5 positive
+ 5 negative personas (`persona_strategy.json`). Judge with `judge_adherence.py`
looking at: how polite the wording is (please/thanks vs blunt).

Run:
```
persona/validation/scripts/run_probe.sh <recipe> persona/validation/tasks/probe-survey_cog-politeness
```
