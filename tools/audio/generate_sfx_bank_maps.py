#!/usr/bin/env python3
"""Generate global-SFX to bank-local physical effect maps."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    ids = json.loads((ROOT / "tools/audio/sfx_global_ids.json").read_text(encoding="utf-8"))
    banks = json.loads((ROOT / "tools/audio/sfx_banks.json").read_text(encoding="utf-8"))
    by_asset = ids["ids"]
    maps = []
    for bank in banks["banks"]:
        local_by_source = {}
        local = 0
        for asset in bank["assets"]:
            source = by_asset[asset]
            physical = source["source_hash"]
            prior = next((value for value, key in local_by_source.items() if key == physical), None)
            if prior is None:
                prior = local
                local += 1
                local_by_source[prior] = physical
            maps.append({"bank_id": bank["bank_id"], "global_id": source["global_id"], "local_id": prior, "asset": asset, "exact_alias_key": physical})
    output = {
        "schema_version": 1,
        "bank_plan_hash": hashlib.sha256((ROOT / "tools/audio/sfx_banks.json").read_bytes()).hexdigest(),
        "global_ids_hash": hashlib.sha256((ROOT / "tools/audio/sfx_global_ids.json").read_bytes()).hexdigest(),
        "maps": maps,
    }
    path = ROOT / "tools/audio/sfx_bank_maps.json"
    path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"SFX bank maps: {len(maps)} global mappings across {banks['bank_count']} banks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
