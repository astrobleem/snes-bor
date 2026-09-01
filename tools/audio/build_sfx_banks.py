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
from production_sfx import canonical_wav, duration_ticks, effect_policy, physical_effect_identity  # noqa: E402
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
                frames, ticks, seconds = duration_ticks(wav, rate)
                policy = effect_policy(rate, ticks)
                program = policy["program"]
                identity = physical_effect_identity(wav, policy)
                effect = physical.get(identity)
                if effect is None:
                    effect = f"bank{bank['bank_id']:02d}_fx{len(physical):02d}"
                    physical[identity] = effect
                    (samples / f"{effect}.wav").write_bytes(wav)
                    rows.append({"name": effect, "source": f"samples/{effect}.wav", "sample_rates": [rate], "loop": "none", "evaluator": "default", "ignore_gaussian_overflow": False, "envelope": "gain F127", "source_frames": frames, "source_duration_seconds": seconds, "duration_ticks": ticks, "one_channel": policy["one_channel"], "interruptible": policy["interruptible"], "priority": policy["priority"]})
                asset_to_effect[asset_key] = effect
            for effect in physical.values():
                effect_ticks = next(row["duration_ticks"] for row in rows if row["name"] == effect)
                effects += [f"=== {effect} ===", f"    set_instrument {effect}", f"    play_note 0 {effect_ticks}", ""]
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
            load_match = re.search(r"\.assert \.sizeof\(LoadAudioData\) = (\d+)", export_text)
            if not load_match:
                raise SystemExit(f"FAIL: TAD export has no LoadAudioData size for bank {bank['bank_id']}")
            data_base = int(load_match.group(1))
            table_match = re.search(r"Tad_DataTable\s*:=\s*__Tad_AudioData_0\s*\+\s*(\d+)", export_text)
            if not table_match:
                raise SystemExit(f"FAIL: TAD export has no DataTable for bank {bank['bank_id']}")
            table_segment = int(table_match.group(1))
            # The table is emitted inside audio-data.bin; its entries are the
            # segment-relative addresses that include the preceding callback.
            # Only item addresses need conversion to blob coordinates.
            table = table_segment
            if table < 0 or table + 8 > len(blob):
                raise SystemExit(f"FAIL: invalid binary table offset {table} for bank {bank['bank_id']}")
            common_start_segment = int.from_bytes(blob[table:table + 3], "little")
            song_start_segment = int.from_bytes(blob[table + 3:table + 6], "little")
            end_segment = int.from_bytes(blob[table + 6:table + 8], "little")
            common_start = common_start_segment - data_base
            song_start = song_start_segment - data_base
            end = end_segment - data_base
            if not 0 <= common_start < song_start <= end <= len(blob):
                raise SystemExit(f"FAIL: invalid binary data ranges for bank {bank['bank_id']}: {common_start}:{song_start}:{end}")
            common_bytes = blob[common_start:song_start]
            standalone = out / "common-standalone.bin"
            common_result = subprocess.run([str(compiler), "common", "--output", str(standalone), str(project_file)], capture_output=True, text=True)
            if common_result.returncode:
                raise SystemExit(common_result.stdout + common_result.stderr)
            if standalone.read_bytes() != common_bytes:
                raise SystemExit(f"FAIL: standalone common differs from corrected ca65 extraction for bank {bank['bank_id']}")
            (target / "common-data.bin").write_bytes(common_bytes)
            shutil.copy2(out / "audio-enums.inc", target / "audio-enums.inc")
            blob_bytes = len(blob)
            common = len(common_bytes)
            banks.append({"bank_id": bank["bank_id"], "assets": bank["assets"], "physical_effect_count": len(physical), "effect_metadata": rows, "compiled_blob_bytes": blob_bytes, "compiled_blob_sha256": hashlib.sha256(blob).hexdigest(), "load_audio_data_bytes": data_base, "data_table_segment_offset": table_segment, "data_table_binary_offset": table, "common_data_segment_start": common_start_segment, "common_data_binary_start": common_start, "song_segment_start": song_start_segment, "song_binary_start": song_start, "segment_end": end_segment, "binary_end": end, "common_data_bytes": common, "common_data_sha256": hashlib.sha256((target / "common-data.bin").read_bytes()).hexdigest()})
            for asset, effect in asset_to_effect.items():
                maps.append({"bank_id": bank["bank_id"], "asset": asset, "local_effect_id": enum_ids[effect], "effect_symbol": effect, "exact_physical_identity": hashlib.sha256((samples / f"{effect}.wav").read_bytes()).hexdigest()})
    output = {"schema_version": 1, "compiler": str(compiler), "compiler_version": version, "bank_plan_hash": hashlib.sha256(plan_path.read_bytes()).hexdigest(), "global_ids_hash": hashlib.sha256(ids_path.read_bytes()).hexdigest(), "banks": banks, "maps": maps, "bank_count": len(banks), "total_common_data_bytes": sum(b["common_data_bytes"] for b in banks), "distinct_local_effects": sum(b["physical_effect_count"] for b in banks)}
    (ROOT / "tools/audio/sfx_production_banks.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"production SFX banks PASS: {len(banks)} banks; {len(maps)} mappings; {output['distinct_local_effects']} local effects; {output['total_common_data_bytes']} common bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
