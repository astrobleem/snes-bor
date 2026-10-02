#!/usr/bin/env python3
"""Extract, canonicalize, and BRR-compile Batch B authored SFX.

This is deliberately separate from the protected production-bank generator.
It writes only Batch B provenance/canonical files and stream payloads; the
resident project is updated explicitly by the Batch B authoring step.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROOT_AUDIO = ROOT / "assets" / "audio"
CANONICAL = ROOT_AUDIO / "batch_b" / "canonical"
SPEC = ROOT / "tools" / "audio" / "batch_b_audio.json"
COMPILER = Path(r"E:\gh\terrific-audio-driver\target\release\tad-compiler.exe")
COMMON_MEMMAP = Path(r"E:\gh\terrific-audio-driver\audio-driver\src\common-memmap.inc")
sys_path = [ROOT / "tools" / "audio", ROOT / "tools" / "bor_converter"]
import sys
sys.path[:0] = [str(p) for p in sys_path]
from pak_extract import extract  # noqa: E402
from production_sfx import canonical_wav, duration_ticks  # noqa: E402

PAKS = {
    "bor-original": ROOT / "Beats of Rage Original [v.3.0 Build 4086].pak",
    "tmnt": ROOT / "Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak",
}
BRR_BLOCK = 9
HEADER = 28
DIR_ITEM = 4


def common_data_addr() -> int:
    text = COMMON_MEMMAP.read_text(encoding="utf-8")
    match = re.search(r"^COMMON_DATA_ADDR\s*=\s*\$([0-9A-Fa-f]+)\s*-\s*28\s*$", text, re.MULTILINE)
    if not match:
        raise SystemExit("cannot derive TAD common-data address")
    value = int(match.group(1), 16) - HEADER
    if value != 0x17E4:
        raise SystemExit(f"unexpected TAD common-data address ${value:04X}")
    return value


def bracked_project(root: Path, wav: bytes, rate: int, ticks: int, name: str) -> tuple[bytes, int]:
    with tempfile.TemporaryDirectory(prefix="bor-batch-b-") as td:
        work = Path(td) / "project"
        shutil.copytree(root / "soundwork/tad/project", work)
        samples = work / "samples"
        samples.mkdir(exist_ok=True)
        (samples / f"{name}.wav").write_bytes(wav)
        project = json.loads((work / "02_coin.terrificaudio").read_text(encoding="utf-8"))
        project["samples"] = [{
            "name": name, "source": f"samples/{name}.wav", "sample_rates": [rate],
            "loop": "none", "evaluator": "default", "ignore_gaussian_overflow": False,
            "envelope": "gain F127",
        }]
        project["sound_effects"] = [name]
        project["sound_effect_file"] = "sound-effects.txt"
        (work / "02_coin.terrificaudio").write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")
        (work / "sound-effects.txt").write_text(
            f"=== {name} ===\n    set_instrument {name}\n    play_note 0 {ticks}\n", encoding="utf-8"
        )
        export = Path(td) / "export"
        export.mkdir()
        subprocess.run([
            str(COMPILER), "ca65-export", str(work / "02_coin.terrificaudio"),
            "-a", str(export / "audio-data.s"), "-b", str(export / "audio-data.bin"),
            "-i", str(export / "audio-enums.inc"), "-s", "AUDIO0", "--lorom",
        ], check=True, capture_output=True, text=True)
        text = (export / "audio-data.s").read_text(encoding="utf-8")
        data_base = int(re.search(r"\.assert \.sizeof\(LoadAudioData\) = (\d+)", text).group(1))
        table = int(re.search(r"Tad_DataTable := .*?\+ (\d+)", text).group(1))
        blob = (export / "audio-data.bin").read_bytes()
        starts = [int.from_bytes(blob[table + i * 3:table + i * 3 + 3], "little") for i in range(2)]
        common = blob[starts[0] - data_base:starts[1] - data_base]
        if common[25] != 1:
            raise SystemExit(f"temporary {name} common data is not one-effect data")
        directory = int.from_bytes(common[HEADER:HEADER + 2], "little")
        offset = directory - common_data_addr()
        brr = common[offset:]
        if len(brr) == 0 or len(brr) % BRR_BLOCK:
            raise SystemExit(f"invalid {name} BRR size {len(brr)}")
        return brr, len(common)


def wav_info(data: bytes) -> tuple[int, int, int, int]:
    with wave.open(io.BytesIO(data), "rb") as source:
        return source.getnchannels(), source.getsampwidth(), source.getframerate(), source.getnframes()


def main() -> int:
    if not COMPILER.exists():
        raise SystemExit(f"missing compiler: {COMPILER}")
    if not COMMON_MEMMAP.exists():
        raise SystemExit(f"missing TAD memory map: {COMMON_MEMMAP}")
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    ROOT_AUDIO.mkdir(parents=True, exist_ok=True)
    CANONICAL.mkdir(parents=True, exist_ok=True)
    rows = []
    for key in spec["resident"] + spec["stream"]:
        family, source = key.split(":", 1)
        pak = PAKS[family]
        raw = extract(pak, source)
        canonical, rate = canonical_wav(raw)
        frames, ticks, seconds = duration_ticks(canonical, rate)
        name = Path(source).stem.lower().replace("~1", "")
        brr, common_bytes = bracked_project(ROOT, canonical, rate, ticks, name)
        canonical_path = CANONICAL / f"{name}.wav"
        canonical_path.write_bytes(canonical)
        backend = "resident_tad_sfx" if key in spec["resident"] else "stream_voice0"
        record = {
            "asset": key,
            "source_pak": pak.name,
            "source_pak_sha256": hashlib.sha256(pak.read_bytes()).hexdigest(),
            "raw_sha256": hashlib.sha256(raw).hexdigest(),
            "raw_bytes": len(raw),
            "raw_channels": wav_info(raw)[0],
            "raw_sample_width_bytes": wav_info(raw)[1],
            "raw_sample_rate_hz": wav_info(raw)[2],
            "raw_frames": wav_info(raw)[3],
            "canonical_path": str(canonical_path.relative_to(ROOT)).replace("\\", "/"),
            "canonical_sha256": hashlib.sha256(canonical).hexdigest(),
            "canonical_frames": frames,
            "canonical_rate_hz": rate,
            "duration_seconds": seconds,
            "duration_ticks": ticks,
            "brr_bytes": len(brr),
            "brr_blocks": len(brr) // BRR_BLOCK,
            "brr_sha256": hashlib.sha256(brr).hexdigest(),
            "single_effect_common_bytes": common_bytes,
            "backend": backend,
        }
        if backend == "resident_tad_sfx":
            sample_path = ROOT / "soundwork/tad/project/samples" / f"{name}.wav"
            sample_path.write_bytes(canonical)
            record["project_sample_path"] = str(sample_path.relative_to(ROOT)).replace("\\", "/")
        else:
            brr_path = ROOT_AUDIO / "batch_b" / f"{name}.brr"
            brr_path.write_bytes(brr)
            record["stream_brr_path"] = str(brr_path.relative_to(ROOT)).replace("\\", "/")
        (ROOT_AUDIO / f"batch_b_{name}.source.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        rows.append(record)
    budget = {
        "schema_version": 1,
        "source_revision": spec["source_revision"],
        "resident": [r for r in rows if r["backend"] == "resident_tad_sfx"],
        "stream": [r for r in rows if r["backend"] == "stream_voice0"],
        "resident_brr_bytes": sum(r["brr_bytes"] for r in rows if r["backend"] == "resident_tad_sfx"),
        "stream_brr_bytes": sum(r["brr_bytes"] for r in rows if r["backend"] == "stream_voice0"),
        "compiler": str(COMPILER),
    }
    (ROOT_AUDIO / "batch_b_budget.json").write_text(json.dumps(budget, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(budget, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
