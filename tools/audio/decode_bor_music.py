#!/usr/bin/env python3
"""Decode legacy OpenBOR ``.bor`` music to signed 16-bit PCM/WAV.

The header and decoder are ported from OpenBOR Team's ``bor2wav`` tool at
commit bcec7cb765eebec555c74aac64a23aa73f1cfe21 (removed by 86fae2f).
The format is not MPEG: it is BOR ADPCM with a 160-byte metadata header.
"""
from __future__ import annotations

import argparse
import struct
import wave
from dataclasses import dataclass
from pathlib import Path

INDEX_TABLE = (-1, -1, -1, -1, 2, 4, 6, 8, -1, -1, -1, -1, 2, 4, 6, 8)
STEP_TABLE = (7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60, 66, 73, 80, 88, 97, 107, 118, 130, 143, 157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449, 494, 544, 598, 658, 724, 796, 876, 963, 1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066, 2272, 2499, 2749, 3024, 3327, 3660, 4026, 4428, 4871, 5358, 5894, 6484, 7132, 7845, 8630, 9493, 10442, 11487, 12635, 13899, 15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767)
HEADER_SIZE = 160
OLD_VERSION = 0x00010000
NEW_VERSION = 0x00010001


@dataclass(frozen=True)
class BorHeader:
    artist: str
    title: str
    version: int
    frequency: int
    channels: int
    datastart: int


def _text(value: bytes) -> str:
    return value.split(b"\0", 1)[0].decode("latin1")


def parse_header(data: bytes) -> BorHeader:
    if len(data) < HEADER_SIZE:
        raise ValueError("BOR file is shorter than its 160-byte header")
    identifier, artist, title, version, frequency, channels, datastart = struct.unpack_from("<16s64s64sIiii", data)
    if identifier.split(b"\0", 1)[0] != b"BOR music":
        raise ValueError(f"invalid BOR identifier: {identifier!r}")
    if version not in (OLD_VERSION, NEW_VERSION):
        raise ValueError(f"unsupported BOR version: 0x{version:08x}")
    if channels not in (1, 2) or (version == OLD_VERSION and channels == 2):
        raise ValueError(f"invalid BOR channel/version combination: {channels}/{version:#x}")
    if frequency <= 0 or datastart != HEADER_SIZE or datastart > len(data):
        raise ValueError(f"invalid BOR frequency/datastart: {frequency}/{datastart}")
    return BorHeader(_text(artist), _text(title), version, frequency, channels, datastart)


def _nibble(value: int, previous: int, index: int) -> tuple[int, int]:
    step = STEP_TABLE[index]
    next_index = max(0, min(88, index + INDEX_TABLE[value]))
    magnitude = step >> 3
    if value & 4:
        magnitude += step
    if value & 2:
        magnitude += step >> 1
    if value & 1:
        magnitude += step >> 2
    previous = previous - magnitude if value & 8 else previous + magnitude
    previous = max(-32768, min(32767, previous))
    return previous, next_index


def decode_adpcm(encoded: bytes, channels: int) -> bytes:
    out = bytearray()
    if channels == 1:
        previous, index = 0, 0
        for byte in encoded:
            for value in ((byte >> 4) & 0x0F, byte & 0x0F):
                previous, index = _nibble(value, previous, index)
                out += struct.pack("<h", previous)
    else:
        left = right = 0
        left_index = right_index = 0
        for byte in encoded:
            left, left_index = _nibble((byte >> 4) & 0x0F, left, left_index)
            right, right_index = _nibble(byte & 0x0F, right, right_index)
            out += struct.pack("<hh", left, right)
    return bytes(out)


def decode_bor(data: bytes) -> tuple[BorHeader, bytes]:
    header = parse_header(data)
    pcm = decode_adpcm(data[header.datastart:], header.channels)
    expected_samples = len(data[header.datastart:]) * (2 if header.channels == 1 else 1)
    if len(pcm) // (2 * header.channels) != expected_samples:
        raise AssertionError("internal BOR sample-count mismatch")
    return header, pcm


def write_wav(path: Path, header: BorHeader, pcm: bytes) -> None:
    with wave.open(str(path), "wb") as output:
        output.setnchannels(header.channels)
        output.setsampwidth(2)
        output.setframerate(header.frequency)
        output.writeframes(pcm)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    header, pcm = decode_bor(args.source.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_wav(args.output, header, pcm)
    samples = len(pcm) // (2 * header.channels)
    print(f"{args.source}: version=0x{header.version:08x} rate={header.frequency} channels={header.channels} samples={samples} duration={samples/header.frequency:.6f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
