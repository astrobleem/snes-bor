"""Authoritative production SFX-set compilation primitive."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from pak_extract import extract
from production_sfx import canonical_wav, duration_ticks, effect_policy, physical_effect_identity
from rebuild import check_compiler_version, find_compiler


def compile_production_sfx_set(root: Path, asset_keys, policy_name="baseline", need_binary=False, need_enums=False, allow_source_canonical=False):
    root = Path(root)
    manifest = json.loads((root / "tools/audio/audio_manifest.json").read_text(encoding="utf-8"))
    reachable = {}
    for family in manifest["families"]:
        for asset in family["assets"]:
            key = f"{family['family']}:{asset['source_path'].upper()}"
            if asset["kind"] == "sfx" and (asset["shipped_reachable"] or allow_source_canonical):
                reachable[key] = (family, asset)
    compiler = find_compiler(None)
    compiler_version = check_compiler_version(compiler)
    asset_keys = sorted(set(asset_keys))
    with tempfile.TemporaryDirectory(prefix="bor-production-sfx-") as tmp:
        project_root = Path(tmp) / "project"
        shutil.copytree(root / "soundwork/tad/project", project_root)
        samples_dir = project_root / "samples"
        samples_dir.mkdir(exist_ok=True)
        sample_ids = {}
        effect_ids = {}
        sample_rows = []
        effects = []
        asset_rows = []
        for asset_key in asset_keys:
            if asset_key not in reachable:
                raise ValueError(f"non-reachable SFX asset: {asset_key}")
            family, source = asset_key.split(":", 1)
            family_row, _ = reachable[asset_key]
            wav, rate = canonical_wav(extract(root / family_row["pak"], source))
            frames, ticks, seconds = duration_ticks(wav, rate)
            policy = effect_policy(rate, ticks)
            sample_identity = hashlib.sha256(wav + str(rate).encode()).hexdigest()
            if sample_identity not in sample_ids:
                sample_name = f"sample{len(sample_ids):03d}"
                sample_ids[sample_identity] = sample_name
                (samples_dir / f"{sample_name}.wav").write_bytes(wav)
                sample_rows.append({"name": sample_name, "source": f"samples/{sample_name}.wav", "sample_rates": [rate], "loop": "none", "evaluator": "default", "ignore_gaussian_overflow": False, "envelope": "gain F127", "source_frames": frames, "source_duration_seconds": seconds, "duration_ticks": ticks, "sample_identity": sample_identity, "brr_bytes": ((frames + 15) // 16) * 9})
            effect_identity = physical_effect_identity(wav, policy)
            if effect_identity not in effect_ids:
                effect_name = f"fx{len(effect_ids):03d}"
                effect_ids[effect_identity] = effect_name
                effects += [f"=== {effect_name} ===", f"    set_instrument {sample_ids[sample_identity]}", f"    play_note 0 {ticks}", ""]
            asset_rows.append({"asset": asset_key, "canonical_pcm_hash": hashlib.sha256(wav).hexdigest(), "sample_identity": sample_identity, "effect_identity": effect_identity, "source_frames": frames, "sample_rate_hz": rate, "duration_seconds": seconds, "duration_ticks": ticks, "effect_symbol": effect_ids[effect_identity], "policy": policy})
        project_file = project_root / "02_coin.terrificaudio"
        project = json.loads(project_file.read_text(encoding="utf-8"))
        project["samples"] = sample_rows
        project["sound_effects"] = list(effect_ids.values())
        project["high_priority_sound_effects"] = []
        project["low_priority_sound_effects"] = []
        project["sound_effect_file"] = "sound-effects.txt"
        project_file.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")
        (project_root / "sound-effects.txt").write_text("\n".join(effects), encoding="utf-8")
        common_path = Path(tmp) / "common.bin"
        result = subprocess.run([str(compiler), "common", "--output", str(common_path), str(project_file)], capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        common = common_path.read_bytes()
        enum_ids = {}
        if need_enums:
            export = Path(tmp) / "export"
            export.mkdir()
            result = subprocess.run([str(compiler), "ca65-export", str(project_file), "-a", str(export / "audio-data.s"), "-b", str(export / "audio-data.bin"), "-i", str(export / "audio-enums.inc"), "-s", "AUDIO0", "--lorom"], capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(result.stdout + result.stderr)
            enum_text = (export / "audio-enums.inc").read_text(encoding="utf-8")
            enum_ids = {name: int(number) for name, number in re.findall(r"\b(fx\d+)\s*=\s*(\d+)", enum_text)}
        for row in asset_rows:
            row["local_effect_id"] = enum_ids.get(row["effect_symbol"])
        brr_bytes = sum(row["brr_bytes"] for row in sample_rows)
        return {"common_data_bytes": len(common), "common_data_sha256": hashlib.sha256(common).hexdigest(), "common_data_blob": common if need_binary else None, "compiler": str(compiler), "compiler_version": compiler_version, "policy_name": policy_name, "logical_assets": asset_keys, "sample_count": len(sample_ids), "effect_count": len(effect_ids), "samples": sample_rows, "effects": asset_rows, "brr_sample_bytes": brr_bytes, "non_sample_common_bytes": len(common) - brr_bytes}
