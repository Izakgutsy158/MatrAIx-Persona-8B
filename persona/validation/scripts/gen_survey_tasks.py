#!/usr/bin/env python3
"""
Generate one Survey probe task per attribute (A/B on that attribute).

Each task = a short survey whose open-ended question(s) give the persona a chance
to express the target attribute, with a NEUTRAL instruction (never mentions the
attribute). Judged afterwards by judge_adherence.py (LLM judge) + optional
rule-based signal noted in the README.

Writes persona/validation/tasks/probe-survey_<attr-slug>/ for each attribute.
"""
from __future__ import annotations
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASKS = ROOT / "persona/validation/tasks"

# attribute -> (X positive, Y negative, one-line what it is, the survey question,
#               the observable signal for the judge)
ATTRS = {
 "code_comment_style": ("Extensive inline comments", "No comments",
    "code commenting habit",
    'Write a Python function `fizzbuzz(n)` that prints 1..n, "Fizz" for multiples of 3, '
    '"Buzz" for 5, "FizzBuzz" for both. Paste your complete code.',
    "how many comments the code has"),
 "cog_emoji_use": ("Heavy", "Never",
    "emoji usage",
    "You just tried a new note-taking app you love. Write a short one-paragraph review "
    "of it for the app store.",
    "how many emoji appear"),
 "cog_verbosity": ("Rambling", "Terse",
    "verbosity / response length",
    "Describe how you keep track of your daily tasks and what you like or dislike about "
    "your approach.",
    "how long / elaborated the answer is"),
 "code_naming_verbosity": ("Highly verbose (long descriptive names)", "Single-letter names",
    "variable naming style",
    "Write a Python function that takes a list of numbers and returns their average. "
    "Paste your complete code.",
    "how long/descriptive the variable names are"),
 "code_summary_documentation": ("Always includes function-level TLDR", "Never includes TLDR",
    "code TLDR/docstring habit",
    "Write a Python function `is_prime(n)` that returns whether n is prime. Paste your "
    "complete code.",
    "whether a docstring / TLDR summary is included"),
 "cog_use_of_jargon": ("Heavy", "Avoids jargon",
    "jargon usage",
    "Explain how a computer connects to a website when you type its address, in your own words.",
    "how much technical jargon is used"),
 "cog_politeness": ("Very polite", "Rude",
    "politeness",
    "Write a message to a coworker asking them to send you a file they forgot to attach.",
    "how polite the wording is (please/thanks vs blunt)"),
 "register": ("Formal / standard", "Colloquial",
    "register (formal vs casual)",
    "Write a short message telling a friend about your weekend plans.",
    "how formal vs colloquial the writing is (contractions/slang)"),
 "cog_humor": ("Playful", "Serious",
    "humor",
    "Someone asks you 'how's your week going?'. Write your reply.",
    "whether the reply is playful/joking vs serious"),
 "cog_storytelling": ("Very high", "None",
    "storytelling tendency",
    "Explain why staying organized matters to you.",
    "whether the answer uses anecdotes/examples/stories vs a direct point"),
}


def slug(a: str) -> str:
    return a.replace("_", "-")


TASK_TOML = '''version = "1.0"
artifacts = [ "/app/output",]

[task]
name = "application/probe-survey-{slug}"

[metadata]
difficulty = "easy"
type = "survey"
domain = "software"
tags = [ "attribute-probe", "{attr}", "ab-validation",]

[verifier]
timeout_sec = 120.0

[agent]
timeout_sec = 600.0

[environment]
definition = "application/shared-survey-form"
build_timeout_sec = 600.0
cpus = 1
memory_mb = 2048
storage_mb = 10240
gpus = 0
'''

INSTRUCTION = '''# Short survey

Please answer the question(s) in the answer box. Write your answer the way that
feels natural to you — there are no style requirements.
'''

CONTEXT = '''# Survey

A short survey. Answer honestly and naturally; there are no right answers and no
style requirements.
'''

STRATEGY = '''{{
  "schemaVersion": "1.0",
  "sources": [],
  "defaultMode": "stratified",
  "dimensionFilters": {{ "{attr}": ["{X}", "{Y}"] }},
  "stratifyFields": ["{attr}"],
  "sampleSize": 10
}}
'''

QUESTIONNAIRE = '''schemaVersion: "1.0"
id: probe_{attrid}_v1
title: Short survey
description: Open-ended survey to probe whether the {attr} persona attribute is expressed.
questions:
  - id: q_main
    prompt: >-
      {question}
    type: free_text
    construct: probe
    required: true
'''

REPORTING = '''{
  "schemaVersion": "1.0",
  "contextRules": []
}
'''

# reuse the code_comment survey verifier machinery: presence-check survey_result.json.
# Judgement is by judge_adherence.py (LLM), so verifier is a minimal presence check.
TEST_SH = '''#!/usr/bin/env bash
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/verifier_env.sh"
if python3 "${TESTS_DIR}/test_state.py"; then
  echo 1 > "${VERIFIER_DIR}/reward.txt"
else
  echo 0 > "${VERIFIER_DIR}/reward.txt"; exit 1
fi
'''

TEST_STATE = '''from __future__ import annotations
import json, os, sys
from pathlib import Path
OUT = Path(os.environ.get("HARBOR_OUTPUT_DIR") or os.environ.get("MATRIX_OUTPUT_DIR") or "/app/output")
p = OUT / "survey_result.json"
if not p.is_file():
    print("missing survey_result.json", file=sys.stderr); raise SystemExit(1)
d = json.loads(p.read_text())
answers = d.get("answers")
if not isinstance(answers, list) or not answers:
    print("no answers", file=sys.stderr); raise SystemExit(1)
vd = os.environ.get("HARBOR_VERIFIER_DIR") or "/logs/verifier"
Path(vd).mkdir(parents=True, exist_ok=True)
Path(vd, "structured_output.json").write_text(json.dumps({
  "schemaVersion":"1.0","artifactType":"matraix.trial_evaluation","taskType":"survey",
  "presenceCheck":{"passed":True,"requiredArtifacts":["survey_result.json"],"missingArtifacts":[]},
  "sourceArtifacts":{"surveyResult":"/app/output/survey_result.json"},
  "contexts":[{"key":"answer","label":"Answer","contextType":"question_response",
    "facets":[{"key":"response","label":"Answer","role":"primary","kind":"textual",
    "value":" ".join(str(a.get("value","")) for a in answers)}]}], "fields":[],
}, ensure_ascii=False, indent=2), encoding="utf-8")
print("ok answers=%d" % len(answers))
'''

VERIFIER_ENV = (TASKS / "probe-survey_code-comment/tests/verifier_env.sh").read_text()

README = '''# probe-survey_{slug}

**Attribute:** `{attr}` — X=`{X}` / Y=`{Y}` ({what})
**Env:** Survey · `application/shared-survey-form`

Neutral survey question that lets the persona express `{attr}`. A/B over 5 positive
+ 5 negative personas (`persona_strategy.json`). Judge with `judge_adherence.py`
looking at: {signal}.

Run:
```
persona/validation/scripts/run_probe.sh <recipe> persona/validation/tasks/probe-survey_{slug}
```
'''


def main():
    made = []
    for attr, (X, Y, what, question, signal) in ATTRS.items():
        s = slug(attr)
        d = TASKS / f"probe-survey_{s}"
        (d / "input").mkdir(parents=True, exist_ok=True)
        (d / "tests").mkdir(parents=True, exist_ok=True)
        (d / "task.toml").write_text(TASK_TOML.format(slug=s, attr=attr))
        (d / "instruction.md").write_text(INSTRUCTION)
        (d / "input/context.md").write_text(CONTEXT)
        (d / "input/questionnaire.yaml").write_text(
            QUESTIONNAIRE.format(attrid=attr, attr=attr, question=question))
        (d / "persona_strategy.json").write_text(STRATEGY.format(attr=attr, X=X, Y=Y))
        (d / "reporting.json").write_text(REPORTING)
        (d / "tests/test.sh").write_text(TEST_SH)
        (d / "tests/test_state.py").write_text(TEST_STATE)
        (d / "tests/verifier_env.sh").write_text(VERIFIER_ENV)
        (d / "README.md").write_text(README.format(slug=s, attr=attr, X=X, Y=Y, what=what, signal=signal))
        os.chmod(d / "tests/test.sh", 0o755)
        made.append(d.name)
    print(f"generated {len(made)} survey probe tasks:")
    for m in made:
        print("  " + m)


if __name__ == "__main__":
    main()
