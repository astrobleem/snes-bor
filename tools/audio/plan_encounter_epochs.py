"""Compile conservative WAIT-delimited encounter working sets.

This is feasibility evidence only. GROUP records are reported but never used
as boundaries; WAIT is used because Spawn_Play owns the camera clamp there.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools/audio"), str(ROOT / "tools/bor_converter"), str(ROOT / "soundwork/tad")]
from production_compile import compile_production_sfx_set
from runtime_sfx_states import KIND_GROUP, KIND_WAIT, explore_stage
from shipped_content import ROSTER_CONFIGS, STAGE_CONFIGS

CAPACITY = 60828
RECORD_SIZE = 10
PICKUP_EVENTS = {1: "health-pickup", 2: "health-pickup", 3: "score-pickup", 4: "one-up", 5: "score-pickup"}


def asset_key(family, path):
    return f"{family}:{path.upper()}"


def main():
    manifest_path = ROOT / "tools/audio/audio_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assets = {(f["family"], a["source_path"]): (f, a) for f in manifest["families"] for a in f["assets"] if a["kind"] == "sfx" and a["shipped_reachable"]}
    globals_by_event = {}
    for (family, path), (_, asset) in assets.items():
        for ref in asset["references"]:
            if ref.get("directive") == "engine-global-default" and ref.get("snes_reachable"):
                globals_by_event.setdefault((family, ref["semantic_event"]), set()).add(asset_key(family, path))

    def model_assets(index):
        entry = ROSTER_CONFIGS[index]
        identity = entry["source_character"].split("\\CHARS\\", 1)[1].upper()
        marker = "DATA\\CHARS\\" + identity
        return {asset_key(family, path) for (family, path), (_, asset) in assets.items() if family == entry["family"] and any(marker in r.get("source_file", "").upper() and r.get("reachability") == "shipped-reachable" for r in asset["references"])}

    def stage_base(stage):
        level = stage["source_level"].upper()
        values = {asset_key(family, path) for (family, path), (_, asset) in assets.items() if family == stage["family"] and any(level in r.get("source_file", "").upper() for r in asset["references"])}
        for event in ("pause-entry", "ui-beep", "ui-beep-secondary", "landed-hit", "attack-swing", "jump", "health-pickup", "score-pickup", "one-up", "fall"):
            values.update(globals_by_event.get((stage["family"], event), set()))
        return values

    rows = []
    for stage in STAGE_CONFIGS:
        raw = (ROOT / stage["spawn"]).read_bytes()
        kinds = [(i, raw[i * RECORD_SIZE + 6] & 7) for i in range(len(raw) // RECORD_SIZE)]
        waits = [i for i, kind in kinds if kind == KIND_WAIT]
        groups = [i for i, kind in kinds if kind == KIND_GROUP]
        states = explore_stage(stage)
        ends = waits + [len(kinds)]
        starts = [0] + [i + 1 for i in waits]
        for epoch, (start, end) in enumerate(zip(starts, ends)):
            relevant = [s for s in states if start <= s["queue_index"] <= end]
            roster_indices = {s["roster_index"] for state in relevant for s in state["slots"] if s["alive"] and not s["prop"] and s["roster_index"] < len(ROSTER_CONFIGS)}
            prop_indices = {s["roster_index"] for state in relevant for s in state["slots"] if s["alive"] and s["prop"] and s["roster_index"] < len(ROSTER_CONFIGS)}
            pickup_types = {s["pickup_type"] for state in relevant for s in state["slots"] if s["alive"] and s["prop"]}
            for player_index, player in enumerate(ROSTER_CONFIGS):
                if not player["playable"]:
                    continue
                values = stage_base(stage) | model_assets(player_index)
                for index in roster_indices | prop_indices:
                    values |= model_assets(index)
                for pickup in pickup_types:
                    event = PICKUP_EVENTS.get(pickup)
                    values |= globals_by_event.get((stage["family"], event), set()) if event else set()
                rows.append({"stage": stage["family"] + ":" + stage["source_level"], "player": player["converted_prefix"], "epoch": epoch, "queue_start": start, "queue_end": end, "wait_boundaries": waits, "group_records_not_boundaries": groups, "carry_over_roster_indices": sorted(roster_indices | prop_indices), "assets": sorted(values)})

    unique = {}
    for row in rows:
        unique.setdefault(tuple(row["assets"]), {**row, "users": []})["users"].append({"stage": row["stage"], "player": row["player"], "epoch": row["epoch"], "queue_start": row["queue_start"], "queue_end": row["queue_end"]})
    for row in unique.values():
        try:
            result = compile_production_sfx_set(ROOT, row["assets"], policy_name="baseline")
            row.update({k: result[k] for k in ("common_data_bytes", "common_data_sha256", "sample_count", "effect_count")})
        except RuntimeError as exc:
            match = re.search(r"too large \((\d+) bytes, max: (\d+)\)", str(exc))
            if not match:
                raise
            row.update({"common_data_bytes": int(match.group(1)), "common_data_sha256": None, "sample_count": None, "effect_count": None, "compile_error": str(exc).strip()})
        row["margin"] = CAPACITY - row["common_data_bytes"]
        row["classification"] = "fail" if row["margin"] < 0 else ("tight fit" if row["margin"] < 1024 else "comfortable fit")
    out = {"schema_version": 1, "boundary_policy": "WAIT only; GROUP is not a boundary", "policy": "baseline-policy capacity; not final shipping policy", "manifest_hash": hashlib.sha256(manifest_path.read_bytes()).hexdigest(), "nominal_epoch_context_count": len(rows), "unique_logical_union_count": len(unique), "epochs": list(unique.values())}
    (ROOT / "tools/audio/encounter_epoch_residency.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"encounter epochs: {len(rows)} nominal contexts, {len(unique)} unique unions")
    for row in out["epochs"]:
        users = ",".join(f"{u['stage'].split(':',1)[0]}:{u['epoch']}" for u in row["users"][:8])
        print(f"{users}: {row['common_data_bytes']} bytes, margin {row['margin']}, {row['classification']}")


if __name__ == "__main__":
    main()
