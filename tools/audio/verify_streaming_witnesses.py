"""Fail-closed parent and exact-capacity checks for streaming witness evidence."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "tools/audio/streaming_witnesses.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
assert data["semantic_lifetime_parent_hash"] == sha(ROOT / "tools/audio/semantic_lifetime_residency.json")
assert data["production_compiler_hash"] == sha(ROOT / "tools/audio/production_compile.py")
assert data["analyzer_hash"] == sha(ROOT / "tools/audio/analyze_streaming_witnesses.py")
assert len(data["failures"]) == 8
for row in data["failures"]:
    witness = row["minimum_nonresident_witness"]
    assert row["original"]["margin"] < 0
    assert witness["assets"]
    assert witness["recompiled"]["margin"] >= 0
    assert witness["recompiled"]["common_data_sha256"]
print("streaming witnesses: PASS (parents current; 8 failing contexts have exact fitting witnesses)")
