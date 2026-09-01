"""Measure independent whole-stage/selected-player SFX working sets."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools/audio"), str(ROOT / "tools/bor_converter"), str(ROOT / "soundwork/tad")]
from production_compile import compile_production_sfx_set
from shipped_content import ROSTER_CONFIGS, STAGE_CONFIGS, source_character_identity

CAPACITY = 60828


def key(family, path):
    return f"{family}:{path.upper()}"


def main():
    manifest_path = ROOT / "tools/audio/audio_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assets = {(f["family"], a["source_path"]): (f, a) for f in manifest["families"] for a in f["assets"] if a["kind"] == "sfx" and a["shipped_reachable"]}
    globals_by_event = {}
    for (family, path), (_, asset) in assets.items():
        for ref in asset["references"]:
            if ref.get("directive") == "engine-global-default" and ref.get("snes_reachable"):
                globals_by_event.setdefault((family, ref["semantic_event"]), set()).add(key(family, path))

    def model_assets(index):
        entry = ROSTER_CONFIGS[index]
        ident = entry["source_character"].split("\\CHARS\\", 1)[1].upper()
        return {key(family, path) for (family, path), (_, asset) in assets.items() if family == entry["family"] and any(("DATA\\CHARS\\" + ident) in ref.get("source_file", "").upper() and ref.get("reachability") == "shipped-reachable" for ref in asset["references"])}

    def stage_assets(stage):
        level = stage["source_level"].upper()
        out = {key(family, path) for (family, path), (_, asset) in assets.items() if family == stage["family"] and any(level in ref.get("source_file", "").upper() for ref in asset["references"])}
        for event in ("pause-entry", "ui-beep", "ui-beep-secondary", "landed-hit", "attack-swing", "jump", "health-pickup", "score-pickup", "one-up", "fall"):
            out.update(globals_by_event.get((stage["family"], event), set()))
        return out

    rows = []
    unique = {}
    for stage in STAGE_CONFIGS:
        base = stage_assets(stage)
        playable = [(i, e) for i, e in enumerate(ROSTER_CONFIGS) if e["playable"]]
        for index, player in playable:
            assets_for_context = base | model_assets(index)
            signature = tuple(sorted(assets_for_context))
            row = unique.setdefault(signature, {"stages": [], "players": [], "assets": list(signature)})
            row["stages"].append(stage["family"] + ":" + stage["source_level"])
            row["players"].append(player["converted_prefix"])
    for row in unique.values():
        try:
            result = compile_production_sfx_set(ROOT, row["assets"], policy_name="baseline")
            row.update({k: result[k] for k in ("common_data_bytes", "common_data_sha256", "sample_count", "effect_count", "compiler_version", "policy_name")})
        except RuntimeError as exc:
            match = re.search(r"too large \((\d+) bytes, max: (\d+)\)", str(exc))
            if not match:
                raise
            row.update({"common_data_bytes": int(match.group(1)), "common_data_sha256": None, "sample_count": None, "effect_count": None, "compiler_version": None, "policy_name": "baseline", "compile_error": str(exc).strip()})
        row["margin"] = CAPACITY - row["common_data_bytes"]
        row["classification"] = "fail" if row["margin"] < 0 else ("tight fit" if row["margin"] < 1024 else "comfortable fit")
    output = {"schema_version": 1, "policy": "baseline-policy capacity; not final shipping policy", "manifest_hash": hashlib.sha256(manifest_path.read_bytes()).hexdigest(), "nominal_context_count": len(STAGE_CONFIGS) * sum(e["playable"] for e in ROSTER_CONFIGS), "unique_logical_union_count": len(unique), "contexts": list(unique.values())}
    out = ROOT / "tools/audio/coarse_stage_residency.json"
    out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"coarse stage residency: {output['nominal_context_count']} nominal contexts, {len(unique)} unique unions")
    for row in output["contexts"]:
        print(f"{','.join(row['stages'])} / {','.join(row['players'])}: {row['common_data_bytes']} bytes, margin {row['margin']}, {row['classification']}")


if __name__ == "__main__":
    main()
