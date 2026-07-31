from __future__ import annotations

from pathlib import Path


JOB = Path("persona/human_extraction/jobs/extract_shard_amazon.job")


def test_amazon_job_exposes_8x24g_runtime_config():
    text = JOB.read_text(encoding="utf-8")

    assert "GPU_CONFIG=8x24g" in text
    assert 'GPU_CONFIG="${GPU_CONFIG:-a100_2x80_bf16}"' in text
    assert '8x24g)' in text
    assert 'TP="${TP:-8}"' in text
    assert 'QUANT="${QUANT:-none}"' in text
    assert 'GPU_MEM="${GPU_MEM:-0.88}"' in text
    assert 'MAX_NUM_SEQS="${MAX_NUM_SEQS:-16}"' in text
    assert 'BATCH_PROFILES="${BATCH_PROFILES:-8}"' in text
    assert '--gpu-mem "$GPU_MEM"' in text
    assert '--max-num-seqs "$MAX_NUM_SEQS"' in text
    assert '--batch-profiles "$BATCH_PROFILES"' in text
