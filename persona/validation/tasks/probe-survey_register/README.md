# probe-survey_register

**Attribute:** `register` — X=`Formal / standard` / Y=`Colloquial` (register (formal vs casual))
**Env:** Survey · `application/shared-survey-form`

Neutral survey question that lets the persona express `register`. A/B over 5 positive
+ 5 negative personas (`persona_strategy.json`). Judge with `judge_adherence.py`
looking at: how formal vs colloquial the writing is (contractions/slang).

Run:
```
persona/validation/scripts/run_probe.sh <recipe> persona/validation/tasks/probe-survey_register
```
