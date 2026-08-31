#!/usr/bin/env python3
"""Fail-closed checks for the generated source-backed audio manifest."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "tools/audio/audio_manifest.json"
ALLOWED = {"implemented-and-gated", "present-not-implemented", "unused-by-shipped-content", "content-inapplicable", "intentionally-deferred", "unknown-needs-source-research"}


def main() -> int:
    if not MANIFEST.exists():
        print(f"FAIL: missing {MANIFEST}; run generate_audio_manifest.py")
        return 1
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    errors = []
    seen = set()
    track_ids = {}
    for family in data.get("families", []):
        for asset in family.get("assets", []):
            key = (asset.get("family"), asset.get("source_path"))
            if key in seen:
                errors.append(f"duplicate asset: {key}")
            seen.add(key)
            if asset.get("implementation_classification") not in ALLOWED:
                errors.append(f"invalid classification: {key}")
            refs = asset.get("references", [])
            raw_refs = sum(r.get("directive") != "engine-global-default" for r in refs)
            engine_refs = sum(r.get("directive") == "engine-global-default" for r in refs)
            if asset.get("raw_reference_count") != raw_refs:
                errors.append(f"raw reference count mismatch: {key}")
            if asset.get("engine_global_reference_count", 0) != engine_refs:
                errors.append(f"engine-global reference count mismatch: {key}")
            if asset.get("total_reference_count") != len(refs):
                errors.append(f"total reference count mismatch: {key}")
            reachable = sum(r.get("reachability") == "shipped-reachable" for r in refs)
            if asset.get("shipped_reachable_reference_count") != reachable:
                errors.append(f"reachable reference count mismatch: {key}")
            if asset.get("shipped_reachable") != bool(reachable):
                errors.append(f"reachable asset flag mismatch: {key}")
            if asset.get("kind") == "missing-source":
                if any(r.get("reachability") == "shipped-reachable" for r in refs):
                    errors.append(f"shipped-reachable source reference names missing asset: {key}")
                else:
                    print(f"INFO: unshipped broken source reference: {key}")
            if asset.get("kind") == "sfx" and asset.get("tad_sfx_id") is not None:
                if not asset.get("packed_runtime"):
                    errors.append(f"SFX has ID but no runtime dispatch: {key}")
                if asset.get("implementation_classification") != "implemented-and-gated":
                    errors.append(f"mapped SFX is not implemented-and-gated: {key}")
            if asset.get("kind") == "music" and asset.get("implementation_classification") == "implemented-and-gated" and asset.get("msu_track_id") is None:
                errors.append(f"implemented music has no MSU track: {key}")
            if asset.get("kind") == "music" and any(r.get("reachability") == "shipped-reachable" for r in refs) and asset.get("msu_track_id") is None:
                errors.append(f"shipped-reachable music has no generated MSU track: {key}")
            if asset.get("kind") == "music" and asset.get("msu_track_id") is not None:
                old = track_ids.setdefault(asset["msu_track_id"], key)
                if old != key:
                    errors.append(f"duplicate MSU track id {asset['msu_track_id']}: {old} and {key}")
            if asset.get("kind") == "music" and asset.get("implementation_classification") == "implemented-and-gated" and not asset.get("packed_runtime"):
                errors.append(f"implemented music has no runtime mapping: {key}")
            if asset.get("kind") in ("sfx", "music") and refs and asset.get("source_hash") is None:
                errors.append(f"referenced audio has no source hash: {key}")
    if errors:
        print("AUDIO MANIFEST FAIL")
        for error in errors:
            print("-", error)
        return 1
    print(f"AUDIO MANIFEST PASS: {len(seen)} source audio entries; unresolved referenced content is explicitly classified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
