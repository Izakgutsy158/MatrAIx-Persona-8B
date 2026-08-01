"""Persona 1M coreset 解码器: parquet row -> {attribute: value}"""

import json
from huggingface_hub import hf_hub_download

REPO = "MatrAIx2026/MatrAIx_Persona_1M_Public_Release"


def load_schema():
    sc = json.load(
        open(hf_hub_download(REPO, "persona_codes.schema.json", repo_type="dataset"))
    )
    return sc["columns"]


def _nibbles(b):
    out = []
    for byte in b:
        out.append(byte & 0x0F)
        out.append((byte >> 4) & 0x0F)
    return out


def decode_row(row, cols):
    raw = row["attributes"]
    nb = row["null_bitmap"]
    if raw is None:
        return {}
    codes = _nibbles(raw)[:1290]
    out = {}
    for i, c in enumerate(cols):
        present = (
            True if nb is None else (((nb[i // 8] >> (i % 8)) & 1) == 0)
        )  # None bitmap => all present
        if present and codes[i] < len(c["values"]):
            out[c["id"]] = c["values"][codes[i]]
    return out
