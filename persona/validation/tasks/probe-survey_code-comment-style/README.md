# probe-survey_code-comment-style

**Attribute:** `code_comment_style` — X=`Extensive inline comments` / Y=`No comments` (code commenting habit)
**Env:** Survey · `application/shared-survey-form`

Neutral survey question that lets the persona express `code_comment_style`. A/B over 5 positive
+ 5 negative personas (`persona_strategy.json`). Judge with `judge_adherence.py`
looking at: how many comments the code has.

Run:
```
persona/validation/scripts/run_probe.sh <recipe> persona/validation/tasks/probe-survey_code-comment-style
```
