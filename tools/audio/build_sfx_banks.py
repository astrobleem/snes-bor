#!/usr/bin/env python3
"""Compile clustered SFX banks and derive maps from TAD's real enum output."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools/audio"), str(ROOT / "tools/bor_converter"), str(ROOT / "soundwork/tad")]
from compile_reachable_sfx import canonical_wav  # noqa: E402
from pak_extract import extract  # noqa: E402
from rebuild import check_compiler_version, find_compiler  # noqa: E402


def main() -> int:
    plan_path = ROOT / "tools/audio/sfx_banks.json"
    ids_path = ROOT / "tools/audio/sfx_global_ids.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    ids = json.loads(ids_path.read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "tools/audio/audio_manifest.json").read_text(encoding="utf-8"))
    reachable = {}
    for family_row in manifest["families"]:
        for asset in family_row["assets"]:
            key = f"{family_row['family']}:{asset['source_path'].upper()}"
            if asset["kind"] == "sfx" and asset["shipped_reachable"]:
                reachable[key] = (family_row, asset)
    compiler = find_compiler(None)
    version = check_compiler_version(compiler)
    out_root = ROOT / "soundwork/tad/build/sfx_banks"
    if out_root.exists():
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True)
    banks = []
    maps = []
    for bank in plan["banks"]:
        with tempfile.TemporaryDirectory(prefix=f"bor-sfx-bank-{bank['bank_id']}-") as tmp:
            root = Path(tmp) / "project"
            shutil.copytree(ROOT / "soundwork/tad/project", root)
            samples = root / "samples"
            samples.mkdir(exist_ok=True)
            physical = {}
            rows = []
            effects = []
            asset_to_effect = {}
            for asset_index, asset_key in enumerate(bank["assets"]):
                if asset_key not in reachable:
                    raise SystemExit(f"FAIL: bank contains non-reachable asset {asset_key}")
                family, source_path = asset_key.split(":", 1)
                family_row, source = reachable[asset_key]
                raw = extract(ROOT / family_row["pak"], source_path)
                wav, rate = canonical_wav(raw)
                identity = (hashlib.sha256(wav).hexdigest(), rate, "none", "gain F127", "play_note 0 48")
                effect = physical.get(identity)
                if effect is None:
                    effect = f"bank{bank['bank_id']:02d}_fx{len(physical):02d}"
                    physical[identity] = effect
                    (samples / f"{effect}.wav").write_bytes(wav)
                    rows.append({"name": effect, "source": f"samples/{effect}.wav", "sample_rates": [rate], "loop": "none", "evaluator": "default", "ignore_gaussian_overflow": False, "envelope": "gain F127"})
                asset_to_effect[asset_key] = effect
            for effect in physical.values():
                effects += [f"=== {effect} ===", f"    set_instrument {effect}", "    play_note 0 48", ""]
            project_file = root / "02_coin.terrificaudio"
            project = json.loads(project_file.read_text(encoding="utf-8"))
            project["samples"] = rows
            project["sound_effects"] = list(physical.values())
            project["high_priority_sound_effects"] = []
            project["low_priority_sound_effects"] = []
            project["sound_effect_file"] = "sound-effects.txt"
            project_file.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")
            (root / "sound-effects.txt").write_text("\n".join(effects), encoding="utf-8")
            out = Path(tmp) / "out"
            out.mkdir()
            result = subprocess.run([str(compiler), "ca65-export", str(project_file), "-a", str(out / "audio-data.s"), "-b", str(out / "audio-data.bin"), "-i", str(out / "audio-enums.inc"), "-s", "AUDIO0", "--lorom"], capture_output=True, text=True)
            if result.returncode:
                raise SystemExit(result.stdout + result.stderr)
            enum = (out / "audio-enums.inc").read_text(encoding="utf-8")
            enum_ids = {name: int(number) for name, number in re.findall(r"\b(bank\d+_fx\d+)\s*=\s*(\d+)", enum)}
            target = out_root / f"bank_{bank['bank_id']:02d}"
            target.mkdir()
            blob = (out / "audio-data.bin").read_bytes()
            export_text = (out / "audio-data.s").read_text(encoding="utf-8")
            table_match = re.search(r"Tad_DataTable\s*:=\s*__Tad_AudioData_0\s*\+\s*(\d+)", export_text)
            if not table_match:
                raise SystemExit(f"FAIL: TAD export has no DataTable for bank {bank['bank_id']}")
            table = int(table_match.group(1))
            common_start = int.from_bytes(blob[table:table + 3], "little")
            common_end = int.from_bytes(blob[table + 3:table + 6], "little")
            if not 0 <= common_start < len(blob):
                raise SystemExit(f"FAIL: invalid common start {common_start} for bank {bank['bank_id']}")
            emitted_common_end = min(common_end, len(blob))
            (target / "common-data.bin").write_bytes(blob[common_start:emitted_common_end])
            shutil.copy2(out / "audio-enums.inc", target / "audio-enums.inc")
            blob_bytes = len(blob)
            common = emitted_common_end - common_start
            banks.append({"bank_id": bank["bank_id"], "assets": bank["assets"], "physical_effect_count": len(physical), "compiled_blob_bytes": blob_bytes, "compiled_blob_sha256": hashlib.sha256(blob).hexdigest(), "common_data_offset": common_start, "common_data_declared_end": common_end, "common_data_bytes": common, "common_data_bytes_emitted": common, "common_data_sha256": hashlib.sha256((target / "common-data.bin").read_bytes()).hexdigest()})
            for asset, effect in asset_to_effect.items():
                maps.append({"bank_id": bank["bank_id"], "asset": asset, "local_effect_id": enum_ids[effect], "effect_symbol": effect, "exact_physical_identity": hashlib.sha256((samples / f"{effect}.wav").read_bytes()).hexdigest()})
    output = {"schema_version": 1, "compiler": str(compiler), "compiler_version": version, "bank_plan_hash": hashlib.sha256(plan_path.read_bytes()).hexdigest(), "global_ids_hash": hashlib.sha256(ids_path.read_bytes()).hexdigest(), "banks": banks, "maps": maps, "bank_count": len(banks), "total_common_data_bytes": sum(b["common_data_bytes"] for b in banks), "distinct_local_effects": sum(b["physical_effect_count"] for b in banks)}
    (ROOT / "tools/audio/sfx_production_banks.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"production SFX banks PASS: {len(banks)} banks; {len(maps)} mappings; {output['distinct_local_effects']} local effects; {output['total_common_data_bytes']} common bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
