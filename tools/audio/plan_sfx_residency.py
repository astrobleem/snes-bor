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
        key = entry["family"]
        marker = entry["source_character"].upper().replace("DATA\\", "")
        player_sets[entry["converted_prefix"]] = {(f, p) for (f, p), a in assets.items() if f == key and any(marker in r.get("source_file", "").upper() for r in a["references"])} | global_assets
    candidates = {}
    for stage in STAGE_CONFIGS:
        stage_key = stage["family"] + ":" + stage["source_level"]
        base = set(global_assets) | {(f, p) for (f, p), a in assets.items() if f == stage["family"] and any(stage["source_level"].upper() in r.get("source_file", "").upper() for r in a["references"])}
        a_set = base | set().union(*(player_sets.values() or [set()]))
        candidates["A:" + stage_key] = {"strategy": "A", "stages": [stage_key], "players": ["all"], "assets": sorted(f + ":" + p for f, p in a_set)}
        for prefix, p_set in player_sets.items():
            key = "B:" + stage_key + ":" + prefix
            candidates[key] = {"strategy": "B", "stages": [stage_key], "players": [prefix], "assets": sorted(f + ":" + p for f, p in (base | p_set))}
    unique = {}
    for candidate in candidates.values():
        signature = tuple(candidate["assets"])
        unique.setdefault(signature, candidate)
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
        results.append({**candidate, "compile_pass": result.returncode == 0, "compiled_blob_bytes": size})
    out = {"schema_version": 1, "candidate_count": len(candidates), "unique_set_count": len(results), "candidates": results}
    (ROOT / "tools/audio/sfx_residency.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"residency candidates: {len(candidates)} combinations, {len(results)} unique sets")
    print(f"compiled passing sets: {sum(r['compile_pass'] for r in results)}")
    if any(not r["compile_pass"] for r in results):
        print("Strategy A/B candidates exceed TAD capacity; finer residency is required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
