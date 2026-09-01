"""Compile persistent player/global floors and per-asset BRR cost evidence."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools/audio"), str(ROOT / "tools/bor_converter"), str(ROOT / "soundwork/tad")]
from production_compile import compile_production_sfx_set
from shipped_content import ROSTER_CONFIGS

CAPACITY = 60828
EXECUTABLE_ROLES = {"idle", "walk", "attack", "attack2", "upper", "jump", "jumpattack", "jumpattack2", "special", "get", "attack3", "attack4", "slide", "grabattack", "freespecial"}
GLOBAL_EVENTS = {"pause-entry", "ui-beep", "ui-beep-secondary", "landed-hit", "attack-swing", "jump"}


def main():
    manifest_path = ROOT / "tools/audio/audio_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    ids = json.loads((ROOT / "tools/audio/sfx_global_ids.json").read_text(encoding="utf-8"))["ids"]
    action = json.loads((ROOT / "tools/audio/action_residency.json").read_text(encoding="utf-8"))
    reachable = {(f["family"], a["source_path"]): (f, a) for f in manifest["families"] for a in f["assets"] if a["kind"] == "sfx" and a["shipped_reachable"]}
    globals_all = set()
    users = {}
    for (family, path), (_, asset) in reachable.items():
        k = f"{family}:{path.upper()}"
        for ref in asset["references"]:
            if ref.get("directive") == "engine-global-default" and ref.get("snes_reachable") and ref.get("semantic_event") in GLOBAL_EVENTS:
                globals_all.add(k)
                users.setdefault(k, []).append(ref.get("semantic_event"))
    models = {m["identity"]: m for m in action["models"]}
    def normalize_key(value):
        family, path = value.split(":", 1)
        return family.lower() + ":" + path.upper()
    floors = []
    all_assets = {f"{family}:{path.upper()}" for family, path in reachable}
    for entry in ROSTER_CONFIGS:
        if not entry["playable"]:
            continue
        ident = entry["source_character"].split("\\CHARS\\", 1)[1].upper()
        model = models[ident]
        values = set(globals_all)
        actions = []
        for option in model["actions"]:
            if option["role"] not in EXECUTABLE_ROLES:
                continue
            actions.append(option["role"])
            values.update(normalize_key(value) for value in option.get("frame_sound_ids", []))
        if model.get("diesound"):
            values.add(normalize_key(model["diesound"]))
        for value in values:
            users.setdefault(value, []).append(f"player:{ident}")
        all_assets.update(values)
        try:
            result = compile_production_sfx_set(ROOT, values, policy_name="baseline")
            row = {"common_data_bytes": result["common_data_bytes"], "sample_count": result["sample_count"], "effect_count": result["effect_count"], "common_data_sha256": result["common_data_sha256"]}
        except RuntimeError as exc:
            match = re.search(r"too large \((\d+) bytes, max: (\d+)\)", str(exc))
            if not match:
                raise
            row = {"common_data_bytes": int(match.group(1)), "sample_count": None, "effect_count": None, "common_data_sha256": None, "compile_error": str(exc).strip()}
        row.update({"player": entry["converted_prefix"], "identity": ident, "assets": sorted(values), "asset_count": len(values), "executable_roles": actions, "margin": CAPACITY - row["common_data_bytes"], "global_events": sorted(GLOBAL_EVENTS)})
        floors.append(row)

    inventory = []
    for asset_key in sorted(all_assets):
        result = compile_production_sfx_set(ROOT, [asset_key], policy_name="baseline")
        sample = result["samples"][0]
        effect = result["effects"][0]
        brr = ((sample["source_frames"] + 15) // 16) * 9
        inventory.append({"asset": asset_key, "canonical_pcm_hash": effect["canonical_pcm_hash"], "sample_identity": effect["sample_identity"], "effect_identity": effect["effect_identity"], "source_sample_rate": effect["sample_rate_hz"], "source_frames": effect["source_frames"], "duration_seconds": effect["duration_seconds"], "duration_ticks": effect["duration_ticks"], "brr_bytes": brr, "single_asset_common_bytes": result["common_data_bytes"], "users": sorted(set(users.get(asset_key, [])))})

    output = {"schema_version": 1, "policy": "baseline-policy capacity; not final shipping policy", "manifest_hash": hashlib.sha256(manifest_path.read_bytes()).hexdigest(), "global_ids_hash": hashlib.sha256((ROOT / "tools/audio/sfx_global_ids.json").read_bytes()).hexdigest(), "floor_count": len(floors), "floors": floors, "inventory": inventory, "total_distinct_inventory_assets": len(inventory), "total_distinct_sample_identities": len({x["sample_identity"] for x in inventory}), "total_distinct_effect_identities": len({x["effect_identity"] for x in inventory}), "total_individual_brr_bytes": sum(x["brr_bytes"] for x in inventory)}
    (ROOT / "tools/audio/persistent_floor_evidence.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for row in floors:
        print(f"{row['player']}: {row['common_data_bytes']} bytes, margin {row['margin']}, samples={row['sample_count']}, effects={row['effect_count']}")
    print(f"inventory: {len(inventory)} assets, {output['total_distinct_sample_identities']} sample identities, {output['total_distinct_effect_identities']} effect identities, {output['total_individual_brr_bytes']} BRR bytes")
    for row in sorted(inventory, key=lambda x: x["brr_bytes"], reverse=True)[:12]:
        print(f"  {row['asset']}: {row['brr_bytes']} BRR bytes, users={','.join(row['users'])}")


if __name__ == "__main__":
    main()
