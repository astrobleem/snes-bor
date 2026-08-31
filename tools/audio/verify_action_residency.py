#!/usr/bin/env python3
"""Compile every executable action signature with the pinned TAD compiler."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPILE = ROOT / "tools/audio/compile_reachable_sfx.py"
INPUT = ROOT / "tools/audio/action_residency.json"


def main() -> int:
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    results = []
    for signature in data["signatures"]:
        assets = signature["assets"]
        if not assets:
            results.append({"assets": [], "compile_pass": True, "compiled_common_bytes": 0, "diagnostic": "empty action signature"})
            continue
        cmd = [sys.executable, str(COMPILE)]
        for asset in assets:
            cmd += ["--asset", asset]
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout + result.stderr
        common = None
        for line in output.splitlines():
            if line.startswith("compiled common-data:"):
                common = int(line.split()[2])
                break
        results.append({"assets": assets, "users": signature["users"], "compile_pass": result.returncode == 0, "compiled_common_bytes": common, "diagnostic": output[-500:]})
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
