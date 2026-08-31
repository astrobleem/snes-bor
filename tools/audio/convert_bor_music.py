#!/usr/bin/env python3
"""Convert decoded OpenBOR BOR music to MSU-1 PCM.

MSU-1 PCM is raw little-endian signed 16-bit stereo at 44,100 Hz.  Source
rate/channel conversion is deterministic linear interpolation and does not
alter the source track selection or loop metadata.
"""
from __future__ import annotations

import argparse
import struct
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from decode_bor_music import decode_bor  # noqa: E402

TARGET_RATE = 44100


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


def convert(source: Path, output: Path) -> dict:
    header, pcm = decode_bor(source.read_bytes())
    values = struct.unpack("<" + "h" * (len(pcm) // 2), pcm)
    frames = [values[i:i + header.channels] for i in range(0, len(values), header.channels)]
    converted = resample_stereo(to_stereo(frames, header.channels), header.frequency)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as f:
        for left, right in converted:
            f.write(struct.pack("<hh", left, right))
    return {"source_rate_hz": header.frequency, "source_channels": header.channels,
            "source_sample_count": len(frames), "msu_rate_hz": TARGET_RATE,
            "msu_channels": 2, "msu_sample_count": len(converted),
            "duration_seconds": len(converted) / TARGET_RATE}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    print(convert(args.source, args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
