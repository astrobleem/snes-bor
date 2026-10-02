#!/usr/bin/env python3
"""Verify compact runtime-state evidence against current source inputs."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/audio"))
from runtime_sfx_states import explore_stage, ROSTER_CONFIGS, STAGE_CONFIGS

def main() -> int:
    path = ROOT / "tools/audio/runtime_sfx_states.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("explorer_sha256") != hashlib.sha256((ROOT / "tools/audio/runtime_sfx_states.py").read_bytes()).hexdigest():
        raise SystemExit("FAIL: runtime state summary is stale relative to explorer")
    if data.get("roster_config_sha256") != hashlib.sha256(json.dumps(ROSTER_CONFIGS, sort_keys=True).encode()).hexdigest():
        raise SystemExit("FAIL: runtime state summary is stale relative to roster")
    expected = {}
    for stage in STAGE_CONFIGS:
        key = stage["family"] + ":" + stage["source_level"]
        if data["input_spawn_hashes"].get(key) != hashlib.sha256((ROOT / stage["spawn"]).read_bytes()).hexdigest():
            raise SystemExit(f"FAIL: stale spawn hash for {key}")
        expected[key] = len(explore_stage(stage))
    if expected != data["state_count_by_stage"] or sum(expected.values()) != data["total_state_count"]:
        raise SystemExit("FAIL: runtime state counts do not reproduce")
    if data.get("max_non_player_slots") != 3:
        raise SystemExit("FAIL: runtime slot invariant changed")
    print(f"runtime state verifier PASS: {data['total_state_count']} states across {len(expected)} stages; max slots 3")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
