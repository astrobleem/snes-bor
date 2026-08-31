#!/usr/bin/env python3
"""Shared production SFX semantics used by capacity and bank tooling."""
from __future__ import annotations

import hashlib
import io
import wave


def duration_ticks(normalized_wav: bytes, sample_rate: int) -> tuple[int, int, float]:
    with wave.open(io.BytesIO(normalized_wav), "rb") as decoded:
        frames = decoded.getnframes()
    ticks = max(1, (frames * 125 + sample_rate - 1) // sample_rate)
    return frames, ticks, frames / sample_rate


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
