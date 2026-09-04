"""Diagnostic-only legacy compiler for comparison fixtures.

Production capacity decisions must use production_sfx.py/build_sfx_banks.py.

The project is built in a temporary directory. No production TAD project or
generated runtime data is modified by this tool.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "bor_converter"))
from pak_extract import extract  # noqa: E402
sys.path.insert(0, str(ROOT / "soundwork" / "tad"))
from rebuild import check_compiler_version, find_compiler  # noqa: E402
from production_sfx import canonical_wav  # noqa: E402

MANIFEST = ROOT / "tools" / "audio" / "audio_manifest.json"
PROJECT = ROOT / "soundwork" / "tad" / "project"
PAK_ROOT = ROOT


def asset_key(family: str, path: str) -> str:
    return f"{family}:{path.upper()}"


def reachable_assets(selected: set[str] | None = None) -> list[dict]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    result = []
    for family in manifest["families"]:
        for asset in family["assets"]:
            key = asset_key(family["family"], asset["source_path"])
            if asset["kind"] == "sfx" and asset["shipped_reachable"] and (selected is None or key in selected):
                item = dict(asset)
                item["family"] = family["family"]
                item["pak"] = family["pak"]
                result.append(item)
    return sorted(result, key=lambda a: (a["family"], a["source_path"]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--compiler", default=None)
    ap.add_argument("--asset", action="append", help="family:source path; restrict the scratch set")
    args = ap.parse_args()
    compiler = find_compiler(args.compiler)
    version = check_compiler_version(compiler)
    selected = set(args.asset) if args.asset else None
    if selected:
        selected = {asset_key(*value.split(":", 1)) if ":" in value else value for value in selected}
        available = {asset_key(f["family"], a["source_path"]) for f in json.loads(MANIFEST.read_text(encoding="utf-8"))["families"] for a in f["assets"] if a["kind"] == "sfx" and a["shipped_reachable"]}
        missing = sorted(selected - available)
        if missing:
            raise SystemExit("FAIL: requested SFX asset key is not shipped-reachable: " + ", ".join(missing))
    assets = reachable_assets(selected)
    if not assets:
        raise SystemExit("FAIL: manifest has no shipped-reachable SFX")
    with tempfile.TemporaryDirectory(prefix="bor-reachable-sfx-") as tmp:
        root = Path(tmp) / "project"
        shutil.copytree(PROJECT, root)
        samples = root / "samples"
        samples.mkdir(exist_ok=True)
        sample_rows = []
        effects = []
        sample_by_identity = {}
        for index, asset in enumerate(assets):
            sample_name = f"reachable_{index:02d}"
            filename = sample_name + ".wav"
            data = extract(PAK_ROOT / asset["pak"], asset["source_path"])
            normalized, sample_rate = canonical_wav(data)
            identity = (hashlib.sha256(normalized).hexdigest(), sample_rate)
            physical = sample_by_identity.get(identity)
            if physical is None:
                physical = sample_name
                sample_by_identity[identity] = physical
                (samples / filename).write_bytes(normalized)
                sample_rows.append({
                    "name": physical,
                    "source": "samples/" + filename,
                    "sample_rates": [sample_rate],
                    "loop": "none",
                    "evaluator": "default",
                    "ignore_gaussian_overflow": False,
                    "envelope": "gain F127",
                })
            effects.extend([f"=== sfx_reachable_{index:02d} ===", f"    set_instrument {physical}", "    play_note 0 48", ""])
        project_file = root / "02_coin.terrificaudio"
        project = json.loads(project_file.read_text(encoding="utf-8"))
        project["samples"] = sample_rows
        project["sound_effects"] = [f"sfx_reachable_{i:02d}" for i in range(len(assets))]
        project["high_priority_sound_effects"] = []
        project["low_priority_sound_effects"] = []
        project["sound_effect_file"] = "sound-effects.txt"
        project_file.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")
        (root / "sound-effects.txt").write_text("\n".join(effects), encoding="utf-8")
        out = Path(tmp) / "out"
        out.mkdir()
        cmd = [str(compiler), "ca65-export", str(project_file), "-a", str(out / "audio-data.s"), "-b", str(out / "audio-data.bin"), "-i", str(out / "audio-enums.inc"), "-s", "AUDIO0", "--lorom"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode:
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
            raise SystemExit(f"FAIL: all-reachable SFX compile exited {result.returncode}")
        blob = out / "audio-data.bin"
        common_bytes = blob.stat().st_size - 116 - 3250 - 8 - 21
        print(f"all-reachable SFX compile PASS: {len(assets)} assets")
        print(f"compiler: {compiler} ({version})")
        print(f"compiled audio-data.bin: {blob.stat().st_size} bytes")
        print(f"compiled common-data: {common_bytes} bytes")
        labels = [a["family"] + ":" + a["source_path"] for a in assets]
        print("assets: " + ", ".join(labels))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
