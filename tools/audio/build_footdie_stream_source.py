#!/usr/bin/env python3
"""Build the test-only ROM source for the FOOTDIE long-SFX streamer.

The payload is produced by the pinned TAD compiler from the source PAK.  The
normal common-data compiler output is used only as an extraction container;
FOOTDIE is not added to the shipped common bank by this tool.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools/audio"), str(ROOT / "tools/bor_converter")]
from pak_extract import extract
from production_sfx import canonical_wav, duration_ticks

COMPILER = Path(r"E:\gh\terrific-audio-driver\target\release\tad-compiler.exe")
COMMON_MEMMAP = Path(r"E:\gh\terrific-audio-driver\audio-driver\src\common-memmap.inc")
ASSET = r"DATA\SOUNDS\FOOTDIE.WAV"
PAK = ROOT / "Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak"
BRR_BYTES = 32733
BRR_BLOCK = 9
FRAME_BYTES = 144
RING_BUFFERS = 8
PAYLOAD_ROWS = 72
PAYLOAD_BYTES_PER_SCANLINE = 2
SUBMIT_MARKER = 0x57
COMMON_DATA_HEADER_SIZE = 28
COMMON_DATA_POINTERS_SIZE = 24
DIR_ITEM_SIZE = 4


def compiler_common_data_addr() -> int:
    if not COMMON_MEMMAP.exists():
        raise SystemExit(f"missing pinned TAD memory map: {COMMON_MEMMAP}")
    text = COMMON_MEMMAP.read_text()
    match = re.search(r"^COMMON_DATA_ADDR\s*=\s*\$([0-9A-Fa-f]+)\s*-\s*28\s*$", text, re.MULTILINE)
    if not match:
        raise SystemExit("unable to prove COMMON_DATA_ADDR from pinned TAD source")
    addr = int(match.group(1), 16) - COMMON_DATA_HEADER_SIZE
    if addr != 0x17E4:
        raise SystemExit(f"unexpected patched COMMON_DATA_ADDR: ${addr:04X}")
    return addr


def decode_brr(brr: bytes) -> list[int]:
    samples: list[int] = []
    p1 = 0
    p2 = 0
    for offset in range(0, len(brr), BRR_BLOCK):
        header = brr[offset]
        shift = header >> 4
        filter_id = (header >> 2) & 3
        for i in range(16):
            packed = brr[offset + 1 + i // 2]
            nibble = ((packed >> 4) if i % 2 == 0 else packed) & 0x0F
            signed = nibble if nibble < 8 else nibble - 16
            value = ((signed << shift) >> 1) if shift <= 12 else (0 if nibble < 8 else -2048)
            if filter_id == 1:
                value += p1 + ((-p1) >> 4)
            elif filter_id == 2:
                value += (p1 << 1) + (-((p1 << 1) + p1) >> 5) - p2 + (p2 >> 4)
            elif filter_id == 3:
                value += (p1 << 1) + (-(p1 + (p1 << 2) + (p1 << 3)) >> 6) - p2 + (((p2 << 1) + p2) >> 4)
            value = max(-32768, min(32767, value))
            value = max(-16384, min(16383, value))
            p2, p1 = p1, value
            samples.append(value * 2)
        if header & 0x01:
            break
    return samples


def waveform_correlation(decoded: list[int], wav_bytes: bytes) -> float:
    with wave.open(io.BytesIO(wav_bytes), "rb") as source:
        if source.getsampwidth() not in (1, 2) or source.getnchannels() not in (1, 2):
            raise SystemExit("canonical FOOTDIE WAV is not 8/16-bit mono/stereo PCM")
        channels = source.getnchannels()
        width = source.getsampwidth()
        raw = source.readframes(source.getnframes())
    if width == 1:
        values = [byte - 128 for byte in raw]
    else:
        values = [int.from_bytes(raw[i:i + 2], "little", signed=True) for i in range(0, len(raw), 2)]
    reference = [sum(values[i:i + channels]) / channels for i in range(0, len(values), channels)]
    if len(decoded) != len(reference):
        raise SystemExit(f"decoded sample count {len(decoded)} != source frames {len(reference)}")
    mean_a = sum(decoded) / len(decoded)
    mean_b = sum(reference) / len(reference)
    numerator = sum((a - mean_a) * (b - mean_b) for a, b in zip(decoded, reference))
    denominator = math.sqrt(sum((a - mean_a) ** 2 for a in decoded) * sum((b - mean_b) ** 2 for b in reference))
    return numerator / denominator if denominator else 0.0


def main() -> int:
    if not COMPILER.exists():
        raise SystemExit(f"missing pinned compiler: {COMPILER}")
    common_data_addr = compiler_common_data_addr()
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
        load_match = re.search(r"\.assert \.sizeof\(LoadAudioData\) = (\d+)", export_text)
        if not load_match:
            raise SystemExit("compiled Foot export has no LoadAudioData size")
        data_base = int(load_match.group(1))
        table = int(re.search(r"Tad_DataTable := .*?\+ (\d+)", export_text).group(1))
        blob = (output / "audio-data.bin").read_bytes()
        starts = [int.from_bytes(blob[table + i * 3:table + i * 3 + 3], "little") for i in range(2)]
        common_starts = [start - data_base for start in starts]
        if not 0 <= common_starts[0] < common_starts[1] <= len(blob):
            raise SystemExit(f"invalid Common Audio Data range: {common_starts}")
        common = blob[common_starts[0]:common_starts[1]]
        if len(common) < COMMON_DATA_HEADER_SIZE + DIR_ITEM_SIZE:
            raise SystemExit("compiled Foot common is shorter than header plus one directory item")
        if len(common) < COMMON_DATA_POINTERS_SIZE:
            raise SystemExit("compiled Foot common is missing its twelve header pointers")
        if common[25] != 1:
            raise SystemExit(f"temporary Foot project header mismatch: table={table} starts={starts} common_len={len(common)} header={[f'{i:02X}:{v:02X}' for i, v in enumerate(common[:32])]} (expected nSoundEffects=1)")
        dir_start = int.from_bytes(common[COMMON_DATA_HEADER_SIZE:COMMON_DATA_HEADER_SIZE + 2], "little")
        dir_loop = int.from_bytes(common[COMMON_DATA_HEADER_SIZE + 2:COMMON_DATA_HEADER_SIZE + 4], "little")
        if dir_loop != dir_start:
            raise SystemExit(f"loop:none directory mismatch: start=${dir_start:04X} loop=${dir_loop:04X}")
        brr_offset = dir_start - common_data_addr
        if brr_offset < COMMON_DATA_HEADER_SIZE + DIR_ITEM_SIZE or brr_offset >= len(common):
            raise SystemExit(f"directory-derived BRR offset out of range: ${brr_offset:04X}")
        if brr_offset + BRR_BYTES > len(common):
            raise SystemExit("directory-derived BRR range exceeds Common Audio Data")
        brr = common[brr_offset:brr_offset + BRR_BYTES]
        trailing = common[brr_offset + BRR_BYTES:]
        if trailing and any(trailing):
            raise SystemExit("nonzero bytes follow the expected FOOTDIE BRR payload")
    if len(brr) != BRR_BYTES or len(brr) % BRR_BLOCK != 0:
        raise SystemExit("FOOTDIE BRR length/block invariant failed")
    if hashlib.sha256(wav).hexdigest() != "7a1b298b5599c86137edce7fb55955f9073a18e5894e22f798b134087dc8fa11":
        raise SystemExit("canonical FOOTDIE PCM identity drifted")
    headers = brr[0::BRR_BLOCK]
    end_count = sum(bool(header & 0x01) for header in headers)
    loop_count = sum(bool(header & 0x02) for header in headers)
    if end_count != 1 or headers[-1] & 0x01 == 0 or any(header & 0x01 for header in headers[:-1]):
        raise SystemExit(f"FOOTDIE BRR END structure failed: {end_count} END headers; common_len={len(common)} dir=${dir_start:04X} offset=${brr_offset:04X} first={brr[:18].hex()} last={brr[-18:].hex()}")
    if loop_count != 0:
        raise SystemExit(f"loop:none FOOTDIE BRR unexpectedly has {loop_count} LOOP headers")
    decoded = decode_brr(brr)
    if len(decoded) != frames or len(decoded) != BRR_BYTES // BRR_BLOCK * 16:
        raise SystemExit(f"decoded FOOTDIE sample count failed: {len(decoded)}")
    correlation = waveform_correlation(decoded, wav)
    out_dir = ROOT / "assets" / "audio"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "footdie.brr").write_bytes(brr)
    evidence = {
        "asset": "tmnt:DATA\\SOUNDS\\FOOTDIE.WAV",
        "source_pak_sha256": hashlib.sha256(PAK.read_bytes()).hexdigest(),
        "canonical_pcm_sha256": hashlib.sha256(wav).hexdigest(),
        "sample_identity": hashlib.sha256(wav + str(rate).encode()).hexdigest(),
        "sample_rate_hz": rate, "source_frames": frames,
        "duration_seconds": seconds, "duration_ticks": ticks,
        "brr_bytes": len(brr), "brr_sha256": hashlib.sha256(brr).hexdigest(),
        "brr_blocks": len(brr) // BRR_BLOCK,
        "common_data_addr": f"${common_data_addr:04X}",
        "directory_start_aram": f"${dir_start:04X}",
        "directory_loop_aram": f"${dir_loop:04X}",
        "brr_offset": brr_offset,
        "first_header": f"${headers[0]:02X}",
        "final_header": f"${headers[-1]:02X}",
        "end_headers": end_count,
        "loop_headers": loop_count,
        "decoded_samples": len(decoded),
        "decoded_source_correlation": correlation,
        "transport": {"frame_bytes": FRAME_BYTES,
                       "payload_bytes_per_scanline": PAYLOAD_BYTES_PER_SCANLINE,
                       "payload_rows": PAYLOAD_ROWS,
                       "command_port": "APUIO0",
                       "payload_ports": ["APUIO1", "APUIO2"],
                       "commit_port": "APUIO3",
                       "submit_marker": "$57",
                       "hdma_channel": 0,
                       "runtime_table": "dynamic",
                       "ring_buffers": RING_BUFFERS,
                       "ring_bytes": RING_BUFFERS * FRAME_BYTES},
        "parents": {"generator": "tools/audio/build_footdie_stream_source.py",
                    "compiler": str(COMPILER), "production_lifetime": "tools/audio/semantic_lifetime_residency.json"},
    }
    (out_dir / "footdie.stream.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
