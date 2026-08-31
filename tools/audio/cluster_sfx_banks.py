#!/usr/bin/env python3
"""Cluster required logical SFX signatures into compiled physical banks."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAPACITY = 60828
RESERVE = 1024
COMPILE = ROOT / "tools/audio/compile_reachable_sfx.py"


def compile_size(assets):
    if not assets:
        return 0
    cmd = [sys.executable, str(COMPILE)]
    for asset in assets:
        cmd += ["--asset", asset]
    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout + result.stderr
    if result.returncode:
        return None
    for line in output.splitlines():
        if line.startswith("compiled common-data:"):
            return int(line.split()[2])
    return None


def main() -> int:
    plan = json.loads((ROOT / "tools/audio/action_residency.json").read_text(encoding="utf-8"))
    signatures = []
    for group in ("action_signatures", "combined_signatures", "combined_transition_signatures"):
        signatures.extend(tuple(row["assets"]) for row in plan.get(group, []))
    signatures = sorted(set(signatures), key=lambda s: (-len(s), s))
    banks = []
    assignments = []
    for signature in signatures:
        placed = False
        for index, bank in enumerate(banks):
            candidate = sorted(set(bank["assets"]) | set(signature))
            size = compile_size(candidate)
            if size is not None and size <= CAPACITY - RESERVE:
                bank["assets"] = candidate
                bank["logical_signatures"].append(list(signature))
                bank["common_bytes"] = size
                assignments.append({"signature": list(signature), "bank": index})
                placed = True
                break
        if not placed:
            size = compile_size(list(signature))
            if size is None or size > CAPACITY:
                raise SystemExit(f"FAIL: indivisible logical signature cannot compile: {signature}")
            banks.append({"bank_id": len(banks), "assets": list(signature), "logical_signatures": [list(signature)], "common_bytes": size})
            assignments.append({"signature": list(signature), "bank": len(banks) - 1})
    output = {
        "schema_version": 1,
        "logical_signature_count": len(signatures),
        "bank_count": len(banks),
        "capacity_bytes": CAPACITY,
        "engineering_reserve_bytes": RESERVE,
        "banks": banks,
        "assignments": assignments,
        "largest_common_bytes": max((b["common_bytes"] for b in banks), default=0),
        "smallest_margin_bytes": min((CAPACITY - b["common_bytes"] for b in banks), default=CAPACITY),
        "total_common_payload_bytes": sum(b["common_bytes"] for b in banks),
    }
    path = ROOT / "tools/audio/sfx_banks.json"
    path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"SFX banks: {len(signatures)} logical signatures -> {len(banks)} banks; largest {output['largest_common_bytes']} bytes; smallest margin {output['smallest_margin_bytes']}; total {output['total_common_payload_bytes']} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
