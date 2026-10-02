#!/usr/bin/env python3
"""Convert OpenBOR BOR ADPCM music to a valid MSU-1 PCM file.

The output is ``MSU1`` plus a little-endian stereo-frame loop point, followed
by signed 16-bit interleaved stereo PCM at 44,100 Hz. BOR's authored music
argument is a repeat boolean; the legacy container has no encoded loop point.
"""
from __future__ import annotations

import argparse
import struct
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from decode_bor_music import decode_bor  # noqa: E402

TARGET_RATE = 44100


def bor_loop_frames(offset_bytes: int, channels: int) -> int:
    if offset_bytes < 0 or channels not in (1, 2):
        raise ValueError("invalid BOR loop offset or channel count")
    return offset_bytes * 2 // channels


def msu_loop_frames(decoded_frame: int, source_rate: int) -> int:
    if decoded_frame < 0 or source_rate <= 0:
        raise ValueError("invalid decoded loop frame or source rate")
    return decoded_frame * TARGET_RATE // source_rate


def to_stereo(samples: list[tuple[int, ...]], channels: int) -> list[tuple[int, int]]:
    return [(s[0], s[0]) if channels == 1 else (s[0], s[1]) for s in samples]


def resample_stereo(samples: list[tuple[int, int]], source_rate: int) -> list[tuple[int, int]]:
    if source_rate == TARGET_RATE:
        return samples
    count = (len(samples) * TARGET_RATE + source_rate - 1) // source_rate
    result = []
    for i in range(count):
        position = i * source_rate / TARGET_RATE
        low = min(int(position), len(samples) - 1)
        high = min(low + 1, len(samples) - 1)
        fraction = position - low
        result.append(tuple(round(samples[low][c] + (samples[high][c] - samples[low][c]) * fraction) for c in (0, 1)))
    return result


def convert(source: Path, output: Path, repeat: bool = True,
            bor_loop_offset_bytes: int = 0) -> dict:
    header, pcm = decode_bor(source.read_bytes())
    values = struct.unpack("<" + "h" * (len(pcm) // 2), pcm)
    frames = [values[i:i + header.channels] for i in range(0, len(values), header.channels)]
    converted = resample_stereo(to_stereo(frames, header.channels), header.frequency)
    source_loop_frame = bor_loop_frames(bor_loop_offset_bytes, header.channels)
    if source_loop_frame > len(frames):
        raise ValueError("BOR loop frame is outside decoded source")
    msu_loop_frame = msu_loop_frames(source_loop_frame, header.frequency)
    if not 0 <= msu_loop_frame <= len(converted):
        raise ValueError("resampled loop frame is outside MSU PCM")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as f:
        f.write(b"MSU1")
        f.write(struct.pack("<I", msu_loop_frame))
        for left, right in converted:
            f.write(struct.pack("<hh", left, right))
    return {"source_rate_hz": header.frequency, "source_channels": header.channels,
            "source_sample_count": len(frames), "msu_rate_hz": TARGET_RATE,
            "msu_channels": 2, "msu_sample_count": len(converted),
            "duration_seconds": len(converted) / TARGET_RATE,
            "repeat": bool(repeat), "bor_loop_offset_bytes": bor_loop_offset_bytes,
            "source_loop_frame": source_loop_frame,
            "msu_loop_frame": msu_loop_frame}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    print(convert(args.source, args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
