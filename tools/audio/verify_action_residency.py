#!/usr/bin/env python3
"""Compile every executable action signature with the pinned TAD compiler."""
from __future__ import annotations

import json
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPILE = ROOT / "tools/audio/compile_reachable_sfx.py"
INPUT = ROOT / "tools/audio/action_residency.json"
BATCH_B = ROOT / "tools/audio/batch_b_audio.json"


def main() -> int:
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    stream_assets = set(json.loads(BATCH_B.read_text(encoding="utf-8")).get("stream", []))
    manifest = ROOT / "tools/audio/audio_manifest.json"
    if data.get("manifest_hash") != __import__("hashlib").sha256(manifest.read_bytes()).hexdigest():
        raise SystemExit("FAIL: action residency plan is stale relative to audio manifest")
    ids = ROOT / "tools/audio/sfx_global_ids.json"
    if ids.exists() and data.get("global_ids_hash") != __import__("hashlib").sha256(ids.read_bytes()).hexdigest():
        raise SystemExit("FAIL: action residency plan is stale relative to global SFX IDs")
    runtime = ROOT / "tools/audio/runtime_sfx_states.json"
    if data.get("runtime_summary_hash") != hashlib.sha256(runtime.read_bytes()).hexdigest():
        raise SystemExit("FAIL: action residency plan is stale relative to runtime state summary")
    joe = next(model for model in data["models"] if model["identity"] == "JOE")
    roles = {action["role"]: action["animation"] for action in joe["actions"]}
    if roles.get("attack2") != "grab" or "attack2_is_grab" in roles:
        raise SystemExit("FAIL: boolean attack2_is_grab polluted JOE action roles")
    for model in data["models"]:
        # The planner already rejects absent ordinals; this explicit guard
        # ensures metadata keys cannot appear in generated action rows.
        if any(action["role"].endswith(("_is_grab", "_is_throw")) for action in model["actions"]):
            raise SystemExit(f"FAIL: metadata field became action role for {model['identity']}")
    results = []
    compile_cache = {}
    signatures = data["action_signatures"] + data["combined_signatures"] + data["combined_transition_signatures"]
    for signature in signatures:
        assets = signature["assets"]
        resident_assets = [asset for asset in assets if asset not in stream_assets]
        streamed_assets = [asset for asset in assets if asset in stream_assets]
        if not resident_assets:
            results.append({"assets": assets, "resident_assets": [], "streamed_assets": streamed_assets, "compile_pass": True, "compiled_common_bytes": 0, "diagnostic": "stream-only action signature"})
            continue
        cache_key = tuple(sorted(resident_assets))
        cached = compile_cache.get(cache_key)
        if cached is not None:
            results.append({"assets": assets, "resident_assets": resident_assets, "streamed_assets": streamed_assets, "users": signature.get("users", [signature.get("example")]), **cached})
            continue
        cmd = [sys.executable, str(COMPILE)]
        for asset in resident_assets:
            cmd += ["--asset", asset]
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout + result.stderr
        common = None
        for line in output.splitlines():
            if line.startswith("compiled common-data:"):
                common = int(line.split()[2])
                break
        cached = {"compile_pass": result.returncode == 0, "compiled_common_bytes": common, "diagnostic": output[-500:]}
        compile_cache[cache_key] = cached
        results.append({"assets": assets, "resident_assets": resident_assets, "streamed_assets": streamed_assets, "users": signature.get("users", [signature.get("example")]), **cached})
        if result.returncode:
            print(output, file=sys.stderr)
            raise SystemExit("FAIL: executable action signature does not compile")
    data["compiler_results"] = results
    data["max_compiled_common_bytes"] = max((r["compiled_common_bytes"] or 0 for r in results), default=0)
    data["capacity_bytes"] = 60828
    data["min_margin_bytes"] = data["capacity_bytes"] - data["max_compiled_common_bytes"]
    INPUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"action residency compile PASS: {len(results)} signatures; max common {data['max_compiled_common_bytes']} bytes; margin {data['min_margin_bytes']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
