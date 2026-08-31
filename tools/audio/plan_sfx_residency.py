"""Generate and compile Strategy A/B SFX residency candidates."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "audio"))
from shipped_content import ROSTER_CONFIGS, STAGE_CONFIGS  # noqa: E402


def main() -> int:
    manifest = json.loads((ROOT / "tools/audio/audio_manifest.json").read_text(encoding="utf-8"))
    assets = {(f["family"], a["source_path"]): a for f in manifest["families"] for a in f["assets"] if a["kind"] == "sfx" and a["shipped_reachable"]}
    global_assets = {(f["family"], a["source_path"]) for f in manifest["families"] for a in f["assets"] if a["kind"] == "sfx" and any(r.get("directive") == "engine-global-default" and r.get("reachability") == "shipped-reachable" for r in a["references"])}
    player_sets = {}
    for entry in ROSTER_CONFIGS:
        if not entry["playable"]:
            continue
        key = entry["family"]
        marker = entry["source_character"].upper().replace("DATA\\", "")
        player_sets[entry["converted_prefix"]] = {(f, p) for (f, p), a in assets.items() if f == key and any(marker in r.get("source_file", "").upper() for r in a["references"])} | global_assets
    candidates = {}
    for stage in STAGE_CONFIGS:
        stage_key = stage["family"] + ":" + stage["source_level"]
        base = set(global_assets) | {(f, p) for (f, p), a in assets.items() if f == stage["family"] and any(stage["source_level"].upper() in r.get("source_file", "").upper() for r in a["references"])}
        a_set = base | set().union(*(player_sets.values() or [set()]))
        candidates["A:" + stage_key] = {"strategy": "A", "stages": [stage_key], "players": ["all"], "combinations": [{"stage": stage_key, "player": "all"}], "assets": sorted(f + ":" + p for f, p in a_set)}
        for prefix, p_set in player_sets.items():
            key = "B:" + stage_key + ":" + prefix
            candidates[key] = {"strategy": "B", "stages": [stage_key], "players": [prefix], "combinations": [{"stage": stage_key, "player": prefix}], "assets": sorted(f + ":" + p for f, p in (base | p_set))}
    expected = len(STAGE_CONFIGS) * (1 + sum(1 for entry in ROSTER_CONFIGS if entry["playable"]))
    if len(candidates) != expected:
        raise SystemExit(f"candidate formula mismatch: generated {len(candidates)}, expected {expected}")
    unique = {}
    for candidate in candidates.values():
        signature = tuple(candidate["assets"])
        if signature not in unique:
            unique[signature] = {**candidate, "stages": [], "players": [], "combinations": []}
        unique[signature]["stages"] = sorted(set(unique[signature]["stages"] + candidate["stages"]))
        unique[signature]["players"] = sorted(set(unique[signature]["players"] + candidate["players"]))
        unique[signature]["combinations"].extend(candidate["combinations"])
    results = []
    for signature, candidate in unique.items():
        cmd = [sys.executable, str(ROOT / "tools/audio/compile_reachable_sfx.py")]
        for asset in signature:
            cmd += ["--asset", asset]
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout + result.stderr
        size = None
        for line in output.splitlines():
            if line.startswith("compiled audio-data.bin:"):
                size = int(line.split()[2])
        results.append({**candidate, "compile_pass": result.returncode == 0, "compiled_blob_bytes": size, "compile_diagnostic": output[-500:] if result.returncode else None})
    out = {"schema_version": 1, "candidate_count": len(candidates), "unique_set_count": len(results), "candidates": results}
    (ROOT / "tools/audio/sfx_residency.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"residency candidates: {len(candidates)} combinations, {len(results)} unique sets")
    print(f"compiled passing sets: {sum(r['compile_pass'] for r in results)}")
    if any(not r["compile_pass"] for r in results):
        print("Strategy A/B candidates exceed TAD capacity; finer residency is required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
