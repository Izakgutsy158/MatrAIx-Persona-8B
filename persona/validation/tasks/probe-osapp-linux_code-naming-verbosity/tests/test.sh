#!/usr/bin/env bash
set -uo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/verifier_env.sh"
export VERIFIER_DIR
set +e
python3 - <<'PY'
import json, os, sys, re
from pathlib import Path
OUT=Path(os.environ.get("HARBOR_OUTPUT_DIR") or os.environ.get("MATRIX_OUTPUT_DIR") or os.environ.get("PLAYGROUND_OUTPUT_DIR") or "/app/output")
path=OUT/"average.py"
if not path.is_file():
    # try recover from final_answer
    for fa in (OUT/"final_answer.txt", Path("/tmp/harbor/logs/agent/final_answer.txt"), Path("/logs/agent/final_answer.txt")):
        if fa.is_file():
            txt=fa.read_text(errors="replace")
            path.parent.mkdir(parents=True,exist_ok=True); path.write_text(txt); break
if not path.is_file():
    print("missing average.py",file=sys.stderr); sys.exit(1)
content=path.read_text(errors="replace")
vd=Path(os.environ.get("VERIFIER_DIR") or os.environ.get("HARBOR_VERIFIER_DIR") or "/logs/verifier")
vd.mkdir(parents=True,exist_ok=True)
(vd/"structured_output.json").write_text(json.dumps({
  "schemaVersion":"1.0","artifactType":"matraix.trial_evaluation","taskType":"os-app",
  "presenceCheck":{"passed":True,"requiredArtifacts":["average.py"],"missingArtifacts":[]},
  "sourceArtifacts":{"output":str(path)},
  "contexts":[{"key":"output","label":"Output","contextType":"artifact",
    "facets":[{"key":"content","label":"Content","role":"primary","kind":"textual","value":content[:6000]}]}],
  "fields":[],
}, ensure_ascii=False, indent=2), encoding="utf-8")
print("ok len=%d"%len(content))
PY
rc=$?
set -e
if [ $rc -eq 0 ]; then printf '1\n' > "${VERIFIER_DIR}/reward.txt"; else printf '0\n' > "${VERIFIER_DIR}/reward.txt"; fi
exit $rc
