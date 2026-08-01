#!/usr/bin/env python3
"""
Generate one Chat probe task per attribute, cloning the working chat template
(probe-chat_code-comment). The chat scenario (acme support, via sidecar) is
fixed; only the target attribute + persona_strategy change. Style attributes
manifest in the USER's chat messages; judged from the trajectory afterwards.
"""
from __future__ import annotations
import shutil
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASKS = ROOT / "persona/validation/tasks"
TEMPLATE = TASKS / "probe-chat_code-comment"

# attr -> (X, Y). All 10; coding ones still run (persona still chats), but they
# manifest weakly in a support chat — kept for completeness / cross-env comparison.
ATTRS = {
 "code_comment_style": ("Extensive inline comments", "No comments"),
 "code_naming_verbosity": ("Highly verbose (long descriptive names)", "Single-letter names"),
 "code_summary_documentation": ("Always includes function-level TLDR", "Never includes TLDR"),
 "cog_use_of_jargon": ("Heavy", "Avoids jargon"),
 "cog_emoji_use": ("Heavy", "Never"),
 "cog_verbosity": ("Rambling", "Terse"),
 "cog_politeness": ("Very polite", "Rude"),
 "register": ("Formal / standard", "Colloquial"),
 "cog_humor": ("Playful", "Serious"),
 "cog_storytelling": ("Very high", "None"),
}

STRATEGY = '''{{
  "schemaVersion": "1.0",
  "sources": [],
  "defaultMode": "stratified",
  "dimensionFilters": {{ "{attr}": ["{X}", "{Y}"] }},
  "stratifyFields": ["{attr}"],
  "sampleSize": 10
}}
'''

README = '''# probe-chat_{slug}

**Attribute:** `{attr}` — X=`{X}` / Y=`{Y}`  **Env:** Chat (acme-support sidecar)
Persona chats with support; the attribute shows in the USER's messages. A/B over
5+5 personas. Judge from trajectory with judge_adherence.py (reward not needed).
'''


def slug(a): return a.replace("_", "-")


def main():
    made = []
    for attr, (X, Y) in ATTRS.items():
        s = slug(attr)
        d = TASKS / f"probe-chat_{s}"
        if d.exists() and d != TEMPLATE:
            shutil.rmtree(d)
        if d == TEMPLATE:
            # rewrite template's own strategy/tags too for consistency, skip copy
            pass
        else:
            shutil.copytree(TEMPLATE, d)
        # task.toml: swap name + attribute tag
        toml = (d / "task.toml").read_text()
        toml = re.sub(r'name = "application/probe-chat-[^"]+"',
                      f'name = "application/probe-chat-{s}"', toml)
        toml = re.sub(r'tags = \[[^\]]*\]',
                      f'tags = [ "attribute-probe", "{attr}", "multi-turn", "ab-validation",]', toml)
        (d / "task.toml").write_text(toml)
        (d / "persona_strategy.json").write_text(STRATEGY.format(attr=attr, X=X, Y=Y))
        (d / "README.md").write_text(README.format(slug=s, attr=attr, X=X, Y=Y))
        # drop stale pycache
        pc = d / "tests" / "__pycache__"
        if pc.exists():
            shutil.rmtree(pc)
        made.append(d.name)
    print(f"generated {len(made)} chat probe tasks:")
    for m in made:
        print("  " + m)


if __name__ == "__main__":
    main()
