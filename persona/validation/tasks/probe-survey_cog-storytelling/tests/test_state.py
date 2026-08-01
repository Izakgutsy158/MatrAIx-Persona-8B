from __future__ import annotations
import json
import os
import sys
from pathlib import Path

OUT = Path(
    os.environ.get("HARBOR_OUTPUT_DIR")
    or os.environ.get("MATRIX_OUTPUT_DIR")
    or "/app/output"
)
p = OUT / "survey_result.json"
if not p.is_file():
    print("missing survey_result.json", file=sys.stderr)
    raise SystemExit(1)
d = json.loads(p.read_text())
answers = d.get("answers")
if not isinstance(answers, list) or not answers:
    print("no answers", file=sys.stderr)
    raise SystemExit(1)
vd = os.environ.get("HARBOR_VERIFIER_DIR") or "/logs/verifier"
Path(vd).mkdir(parents=True, exist_ok=True)
Path(vd, "structured_output.json").write_text(
    json.dumps(
        {
            "schemaVersion": "1.0",
            "artifactType": "matraix.trial_evaluation",
            "taskType": "survey",
            "presenceCheck": {
                "passed": True,
                "requiredArtifacts": ["survey_result.json"],
                "missingArtifacts": [],
            },
            "sourceArtifacts": {"surveyResult": "/app/output/survey_result.json"},
            "contexts": [
                {
                    "key": "answer",
                    "label": "Answer",
                    "contextType": "question_response",
                    "facets": [
                        {
                            "key": "response",
                            "label": "Answer",
                            "role": "primary",
                            "kind": "textual",
                            "value": " ".join(str(a.get("value", "")) for a in answers),
                        }
                    ],
                }
            ],
            "fields": [],
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
print("ok answers=%d" % len(answers))
