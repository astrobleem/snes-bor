#!/usr/bin/env python3
"""Build the test-only ROM source for the FOOTDIE long-SFX streamer.

The payload is produced by the pinned TAD compiler from the source PAK.  The
normal common-data compiler output is used only as an extraction container;
FOOTDIE is not added to the shipped common bank by this tool.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools/audio"), str(ROOT / "tools/bor_converter")]
from pak_extract import extract
from production_sfx import canonical_wav, duration_ticks

COMPILER = Path(r"E:\gh\terrific-audio-driver\target\release\tad-compiler.exe")
ASSET = r"DATA\SOUNDS\FOOTDIE.WAV"
PAK = ROOT / "Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak"
BRR_BYTES = 32733
BRR_BLOCK = 9
FRAME_BYTES = 144
RING_BUFFERS = 8


def main() -> int:
    if not COMPILER.exists():
        raise SystemExit(f"missing pinned compiler: {COMPILER}")
    raw = extract(PAK, ASSET)
    wav, rate = canonical_wav(raw)
    frames, ticks, seconds = duration_ticks(wav, rate)
    with tempfile.TemporaryDirectory(prefix="bor-footdie-stream-") as td:
        project = Path(td) / "project"
        shutil.copytree(ROOT / "soundwork/tad/project", project)
        samples = project / "samples"
        samples.mkdir(exist_ok=True)
        (samples / "footdie.wav").write_bytes(wav)
        config = json.loads((project / "02_coin.terrificaudio").read_text())
        config["samples"] = [{
            "name": "footdie", "source": "samples/footdie.wav",
            "sample_rates": [rate], "loop": "none", "evaluator": "default",
            "ignore_gaussian_overflow": False, "envelope": "gain F127",
        }]
        config["sound_effects"] = ["footdie"]
        config["sound_effect_file"] = "sound-effects.txt"
        (project / "02_coin.terrificaudio").write_text(json.dumps(config, indent=2) + "\n")
        (project / "sound-effects.txt").write_text(
            f"=== footdie ===\n    set_instrument footdie\n    play_note 0 {ticks}\n"
        )
        output = Path(td) / "export"
        output.mkdir()
        subprocess.run([
            str(COMPILER), "ca65-export", str(project / "02_coin.terrificaudio"),
            "-a", str(output / "audio-data.s"), "-b", str(output / "audio-data.bin"),
            "-i", str(output / "audio-enums.inc"), "-s", "AUDIO0", "--lorom",
        ], check=True)
        export_text = (output / "audio-data.s").read_text()
        table = int(re.search(r"Tad_DataTable := .*?\+ (\d+)", export_text).group(1))
        blob = (output / "audio-data.bin").read_bytes()
        starts = [int.from_bytes(blob[table + i * 3:table + i * 3 + 3], "little") for i in range(2)]
        common = blob[starts[0]:starts[1]]
        if len(common) < 19 + BRR_BYTES:
            raise SystemExit("compiled Foot common is shorter than the accepted BRR payload")
        brr = common[19:19 + BRR_BYTES]
    if len(brr) != BRR_BYTES or len(brr) % BRR_BLOCK != 0:
        raise SystemExit("FOOTDIE BRR length/block invariant failed")
    if hashlib.sha256(wav).hexdigest() != "7a1b298b5599c86137edce7fb55955f9073a18e5894e22f798b134087dc8fa11":
        raise SystemExit("canonical FOOTDIE PCM identity drifted")
    out_dir = ROOT / "assets" / "audio"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "footdie.brr").write_bytes(brr)
    # HDMA channel 0 receives a marker row followed by 36 four-port payload
    # rows. The marker synchronizes the SPC command; transport framing never
    # means sample END.
    hdma = bytearray()
    for pos in range(0, len(brr), FRAME_BYTES):
        chunk = brr[pos:pos + FRAME_BYTES]
        hdma.extend((1, 0xD7, 0, 0, 0))
        for off in range(0, FRAME_BYTES, 4):
            part = chunk[off:off + 4]
            hdma.append(1)
            hdma.extend(part)
            hdma.extend(b"\0" * (4 - len(part)))
        hdma.append(0)
    (out_dir / "footdie.hdma").write_bytes(hdma)
    evidence = {
        "asset": "tmnt:DATA\\SOUNDS\\FOOTDIE.WAV",
        "source_pak_sha256": hashlib.sha256(PAK.read_bytes()).hexdigest(),
        "canonical_pcm_sha256": hashlib.sha256(wav).hexdigest(),
        "sample_identity": hashlib.sha256(wav + str(rate).encode()).hexdigest(),
        "sample_rate_hz": rate, "source_frames": frames,
        "duration_seconds": seconds, "duration_ticks": ticks,
        "brr_bytes": len(brr), "brr_sha256": hashlib.sha256(brr).hexdigest(),
        "brr_blocks": len(brr) // BRR_BLOCK,
        "transport": {"payload_bytes_per_scanline": 3, "frame_bytes": FRAME_BYTES,
                       "ring_buffers": RING_BUFFERS, "ring_bytes": RING_BUFFERS * FRAME_BYTES,
                       "hdma_channel": 0, "hdma_table_bytes": len(hdma)},
        "parents": {"generator": "tools/audio/build_footdie_stream_source.py",
                    "compiler": str(COMPILER), "production_lifetime": "tools/audio/semantic_lifetime_residency.json"},
    }
    (out_dir / "footdie.stream.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
