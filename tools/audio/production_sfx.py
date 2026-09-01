#!/usr/bin/env python3
"""Shared production SFX semantics used by capacity and bank tooling."""
from __future__ import annotations

import hashlib
import io
import struct
import tempfile
import wave


def duration_ticks(normalized_wav: bytes, sample_rate: int) -> tuple[int, int, float]:
    with wave.open(io.BytesIO(normalized_wav), "rb") as decoded:
        frames = decoded.getnframes()
    ticks = max(1, (frames * 125 + sample_rate - 1) // sample_rate)
    return frames, ticks, frames / sample_rate


def canonical_wav(raw: bytes) -> tuple[bytes, int]:
    """Normalize PCM WAV data for the pinned TAD compiler."""
    if raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
        raise ValueError("not a RIFF/WAVE file")
    pos = 12
    fmt = data = None
    while pos + 8 <= len(raw):
        kind = raw[pos:pos + 4]
        size = struct.unpack_from("<I", raw, pos + 4)[0]
        chunk = raw[pos + 8:pos + 8 + size]
        if kind == b"fmt ":
            fmt = chunk
        elif kind == b"data":
            data = chunk
        pos += 8 + size + (size & 1)
    if fmt is None or data is None or len(fmt) < 16:
        raise ValueError("WAV lacks fmt/data chunks")
    encoding, channels, rate, _byte_rate, block_align, width = struct.unpack_from("<HHIIHH", fmt)
    if encoding != 1 or width not in (8, 16) or channels not in (1, 2):
        raise ValueError(f"unsupported PCM WAV encoding={encoding} channels={channels} width={width}")
    values = []
    for frame in range(len(data) // block_align):
        samples = []
        for channel in range(channels):
            off = frame * block_align + channel * (width // 8)
            samples.append(data[off] - 128 if width == 8 else struct.unpack_from("<h", data, off)[0] // 256)
        values.append(sum(samples) // len(samples) + 128)
    values.extend([128] * ((16 - len(values) % 16) % 16))
    out = tempfile.SpooledTemporaryFile()
    with wave.open(out, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(1)
        wav.setframerate(rate)
        wav.writeframes(bytes(values))
    out.seek(0)
    return out.read(), rate


def effect_policy(sample_rate: int, duration: int) -> dict:
    # Explicit baseline policy. These fields are part of identity and are
    # intentionally centralized before semantic priority tuning.
    return {
        "loop": "none",
        "envelope": "gain F127",
        "one_channel": True,
        "interruptible": True,
        "priority": "normal",
        "duration_ticks": duration,
        "program": f"play_note 0 {duration}",
        "sample_rate_hz": sample_rate,
    }


def physical_effect_identity(normalized_wav: bytes, policy: dict) -> str:
    material = normalized_wav + repr(sorted(policy.items())).encode("utf-8")
    return hashlib.sha256(material).hexdigest()
