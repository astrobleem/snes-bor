#!/usr/bin/env python3
"""Generate stable semantic SFX IDs and exact physical identity aliases."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    manifest = json.loads((ROOT / "tools/audio/audio_manifest.json").read_text(encoding="utf-8"))
    dedup_path = ROOT / "tools/audio/sfx_pcm_dedup.json"
    dedup = json.loads(dedup_path.read_text(encoding="utf-8")) if dedup_path.exists() else {"canonical_assets": []}
    canonical = {row["asset"]: row["canonical_pcm_hash"] for row in dedup.get("canonical_assets", [])}
    ids = {}
    physical = {}
    next_id = 0
    for family in sorted(manifest["families"], key=lambda f: f["family"]):
        for asset in sorted(family["assets"], key=lambda a: a["source_path"]):
            if asset["kind"] != "sfx" or not asset["shipped_reachable"]:
                continue
            semantic = f"{family['family']}:{asset['source_path']}"
            ident = "SFX_" + family["family"].replace("-", "_").upper() + "_" + Path(asset["source_path"]).stem.replace("~", "_").upper()
            ids[semantic] = {"global_id": next_id, "symbol": ident, "source_hash": asset["source_hash"]}
            next_id += 1
            physical_key = f"{canonical.get(semantic, asset.get('source_hash'))}:{asset['format'].get('sample_rate_hz') if asset.get('format') else None}"
            physical.setdefault(physical_key, []).append(semantic)
    output = {
        "schema_version": 1,
        "manifest_hash": hashlib.sha256((ROOT / "tools/audio/audio_manifest.json").read_bytes()).hexdigest(),
        "ids": ids,
        "physical_identity_groups": [items for items in physical.values() if len(items) > 1],
        "reachable_count": len(ids),
    }
    path = ROOT / "tools/audio/sfx_global_ids.json"
    path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"SFX global IDs: {len(ids)}; exact physical alias groups: {len(output['physical_identity_groups'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
