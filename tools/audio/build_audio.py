#!/usr/bin/env python3
"""Authoritative non-recursive audio build used by Python and Make builds."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run(script: str, *args: str) -> None:
    subprocess.run([sys.executable, str(ROOT / "tools/audio" / script), *args],
                   cwd=ROOT, check=True)


def main() -> int:
    run("generate_audio_manifest.py")
    run("verify_audio_manifest.py")
    run("generate_audio_music_ids.py")
    run("build_music_catalog.py", "--output", "distribution", "--catalog",
        "tools/audio/music_catalog.json")
    run("verify_msu_pcm.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
