"""
从 MatrAIx 1M 四源 coreset (MatrAIx2026/MatrAIx_Persona_1M_Public_Release) 抽取
persona subset: 每个目标 attribute 抽 5 正 + 5 反 (来源混合, 不分源)。

用法:
    python extract_subset.py            # 抽取并写出 subset yaml + manifest 到 validation-subset
输出:
    persona/datasets/validation-subset/persona_XXXX.yaml + manifest.json

依赖: huggingface_hub, pyarrow, pyyaml; 需 org 成员权限访问 gated repo。
"""
import json
import os
import sys
from collections import Counter
from huggingface_hub import hf_hub_download
import pyarrow.parquet as pq
import yaml as _yaml

sys.path.insert(0, os.path.dirname(__file__))
from decode_persona_1m import load_schema, decode_row, REPO

# 目标 attribute: (id, 正向取值 X, 反向取值 Y)
SPEC = [
    ('register', 'Formal / standard', 'Colloquial'),
    ('tech_savviness', 'Digital native', 'Reluctant'),
    ('decision_style', 'Analytical', 'Intuitive'),
    ('trait_empathy', 'Strong', 'Absent'),
    ('code_comment_style', 'Extensive inline comments', 'No comments'),
    ('expertise_gap', 'Expert testing the system', 'Novice asking expert'),
    ('risk_tolerance', 'Risk-seeking', 'Cautious'),
    ('trust_level', 'Trusting', 'Skeptical'),
    ('economic_motivation', 'Premium-seeking', 'Cost-sensitive'),
    ('cog_feedback_receptiveness', 'High', 'Low'),
]
# 各源代表性 shard (1M coreset 按源排序: wiki 0-3, amazon 3-4, so 4-5, synthetic 6-9)
SHARDS = [0, 3, 4, 5, 6]
N_PER_SIDE = 5
NEED = ['source', 'source_record_id', 'attributes', 'null_bitmap']

# 输出目录相对本脚本定位到 repo 的 persona/datasets
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
DEST = os.path.join(REPO_ROOT, 'persona', 'datasets', 'validation-subset')


def main():
    cols = load_schema()
    picked = {a: {'positive': [], 'negative': []} for a, _, _ in SPEC}

    def need_more():
        return any(len(picked[a]['positive']) < N_PER_SIDE or len(picked[a]['negative']) < N_PER_SIDE
                   for a, _, _ in SPEC)

    for si in SHARDS:
        if not need_more():
            break
        p = hf_hub_download(REPO, f"data/persona-1m-{si:04d}.parquet", repo_type="dataset")
        for batch in pq.ParquetFile(p).iter_batches(batch_size=8000, columns=NEED):
            if not need_more():
                break
            for r in batch.to_pylist():
                d = decode_row(r, cols)
                if not d:
                    continue
                for attr, X, Y in SPEC:
                    slot = picked[attr]
                    v = d.get(attr)
                    if v == X and len(slot['positive']) < N_PER_SIDE:
                        slot['positive'].append((r['source'], r['source_record_id'], d))
                    elif v == Y and len(slot['negative']) < N_PER_SIDE:
                        slot['negative'].append((r['source'], r['source_record_id'], d))

    # 组装 + 去重成唯一 persona
    records = []
    for attr, X, Y in SPEC:
        for pol, val in [('positive', X), ('negative', Y)]:
            for src, rid, d in picked[attr][pol][:N_PER_SIDE]:
                records.append({'attribute': attr, 'polarity': pol, 'target_value': val,
                                'source': src, 'source_record_id': rid, 'dimensions': d})

    uniq = {}
    for r in records:
        k = (r['source'], str(r['source_record_id']))
        uniq.setdefault(k, {'dims': r['dimensions'], 'hits': []})
        uniq[k]['hits'].append((r['attribute'], r['polarity'], r['target_value']))

    os.makedirs(DEST, exist_ok=True)
    for f in os.listdir(DEST):
        if f.startswith('persona_') and f.endswith('.yaml'):
            os.remove(os.path.join(DEST, f))

    man, alldim = [], set()
    for i, (k, b) in enumerate(sorted(uniq.items()), 1):
        src, rid = k
        nid = f"{i:04d}"
        alldim |= set(b['dims'])
        _yaml.safe_dump({'persona_id': nid, 'version': '1.0', 'source': f"{src}:{rid}",
                         'dimensions': b['dims']},
                        open(f"{DEST}/persona_{nid}.yaml", "w"),
                        sort_keys=False, allow_unicode=True, default_flow_style=False)
        man.append({'persona_id': nid, 'source': src, 'orig_id': str(rid),
                    'attribute_hits': [{'attribute': a, 'polarity': p, 'value': v} for a, p, v in b['hits']]})

    json.dump({'kind': 'validation-subset', 'count': len(uniq), 'schema_version': '1.0',
               'source_dataset': REPO,
               'design': f'{len(records)} records = {len(SPEC)} attributes x (5 pos + 5 neg), '
                         f'source-merged from 4-source 1M coreset; {len(uniq)} unique personas',
               'source_breakdown': dict(Counter(r['source'] for r in records)),
               'attributes': [a for a, _, _ in SPEC], 'dimension_ids': sorted(alldim),
               'personas': man},
              open(f"{DEST}/manifest.json", "w"), ensure_ascii=False, indent=2)

    print(f"records={len(records)} unique_personas={len(uniq)}")
    print("source breakdown:", dict(Counter(r['source'] for r in records)))
    for attr, X, Y in SPEC:
        print(f"  {attr:<26} pos={len(picked[attr]['positive'])} neg={len(picked[attr]['negative'])}")


if __name__ == "__main__":
    main()
