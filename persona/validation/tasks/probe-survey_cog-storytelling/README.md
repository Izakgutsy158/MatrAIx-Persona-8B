# probe-survey_cog-storytelling

**Attribute:** `cog_storytelling` — X=`Very high` / Y=`None` (storytelling tendency)
**Env:** Survey · `application/shared-survey-form`

Neutral survey question that lets the persona express `cog_storytelling`. A/B over 5 positive
+ 5 negative personas (`persona_strategy.json`). Judge with `judge_adherence.py`
looking at: whether the answer uses anecdotes/examples/stories vs a direct point.

Run:
```
persona/validation/scripts/run_probe.sh <recipe> persona/validation/tasks/probe-survey_cog-storytelling
```
