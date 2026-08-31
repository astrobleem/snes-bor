#!/usr/bin/env python3
"""Fail closed if generated global SFX IDs drift from the manifest."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    manifest_path = ROOT / "tools/audio/audio_manifest.json"
    ids_path = ROOT / "tools/audio/sfx_global_ids.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    ids = json.loads(ids_path.read_text(encoding="utf-8"))
    expected = sorted(f"{f['family']}:{a['source_path']}" for f in manifest["families"] for a in f["assets"] if a["kind"] == "sfx" and a["shipped_reachable"])
    actual = sorted(ids["ids"])
    if expected != actual:
        raise SystemExit("FAIL: global SFX IDs do not match current reachable manifest")
    digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    if ids["manifest_hash"] != digest:
        raise SystemExit("FAIL: global SFX IDs were generated from a stale manifest")
    values = [v["global_id"] for v in ids["ids"].values()]
    if sorted(values) != list(range(len(values))):
        raise SystemExit("FAIL: global SFX IDs are not deterministic and contiguous")
    print(f"SFX global ID verifier PASS: {len(values)} IDs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
