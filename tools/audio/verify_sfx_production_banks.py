#!/usr/bin/env python3
"""Fail closed on stale or incomplete compiler-derived SFX bank artifacts."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "tools/audio/audio_manifest.json"
IDS = ROOT / "tools/audio/sfx_global_ids.json"
PLAN = ROOT / "tools/audio/sfx_banks.json"
ARTIFACT = ROOT / "tools/audio/sfx_production_banks.json"
OUT = ROOT / "soundwork/tad/build/sfx_banks"
CAPACITY = 60828


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    for path in (MANIFEST, IDS, PLAN, ARTIFACT):
        if not path.exists():
            raise SystemExit(f"FAIL: missing production SFX input {path}")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ids = json.loads(IDS.read_text(encoding="utf-8"))
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    if artifact.get("bank_plan_hash") != digest(PLAN):
        raise SystemExit("FAIL: compiled SFX banks are stale relative to sfx_banks.json")
    if artifact.get("global_ids_hash") != digest(IDS):
        raise SystemExit("FAIL: compiled SFX banks are stale relative to global SFX IDs")
    reachable = {
        f"{family['family']}:{asset['source_path'].upper()}"
        for family in manifest["families"]
        for asset in family["assets"]
        if asset["kind"] == "sfx" and asset["shipped_reachable"]
    }
    expected_ids = set(ids["ids"])
    maps = artifact.get("maps", [])
    if expected_ids != reachable:
        raise SystemExit("FAIL: global SFX IDs do not equal reachable manifest assets")
    maps_by_bank = {}
    for row in maps:
        if row["asset"] not in reachable:
            raise SystemExit(f"FAIL: production bank map contains non-reachable asset {row['asset']}")
        maps_by_bank.setdefault(row["bank_id"], set()).add(row["asset"])
    enum_ids = {}
    for bank in artifact.get("banks", []):
        expected_bank_assets = {asset.upper() for asset in bank["assets"]}
        actual_bank_assets = {asset.upper() for asset in maps_by_bank.get(bank["bank_id"], set())}
        if actual_bank_assets != expected_bank_assets:
            raise SystemExit(f"FAIL: bank {bank['bank_id']} map coverage mismatch")
        if bank["common_data_bytes"] > CAPACITY:
            raise SystemExit(f"FAIL: bank {bank['bank_id']} exceeds common-data capacity")
        binary = OUT / f"bank_{bank['bank_id']:02d}" / "common-data.bin"
        enum = OUT / f"bank_{bank['bank_id']:02d}" / "audio-enums.inc"
        if not binary.exists() or not enum.exists():
            raise SystemExit(f"FAIL: missing compiled output for bank {bank['bank_id']}")
        if binary.stat().st_size != bank["common_data_bytes"]:
            raise SystemExit(f"FAIL: bank {bank['bank_id']} persisted common-data size mismatch")
        if digest(binary) != bank["common_data_sha256"]:
            raise SystemExit(f"FAIL: bank {bank['bank_id']} binary hash mismatch")
        enum_ids[bank["bank_id"]] = {
            int(value) for value in re.findall(r"^\s+\w+\s*=\s*(\d+)", enum.read_text(encoding="utf-8"), re.M)
        }
    for row in maps:
        if row["local_effect_id"] not in enum_ids.get(row["bank_id"], set()):
            raise SystemExit(f"FAIL: map uses absent local effect {row}")
    if artifact.get("bank_count") != len(artifact.get("banks", [])):
        raise SystemExit("FAIL: bank count metadata mismatch")
    print(
        f"production SFX bank verifier PASS: {artifact['bank_count']} banks, "
        f"{len(maps)} mappings, largest common "
        f"{max((b['common_data_bytes'] for b in artifact['banks']), default=0)} bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
