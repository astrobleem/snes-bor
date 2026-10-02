#!/usr/bin/env python3
"""Authoritative non-recursive audio build used by Python and Make builds."""
from __future__ import annotations

import subprocess
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run(script: str, *args: str) -> None:
    subprocess.run([sys.executable, str(ROOT / "tools/audio" / script), *args],
                   cwd=ROOT, check=True)


def main(sfx_only: bool = False) -> int:
    run("verify_shipped_content.py")
    run("generate_audio_manifest.py")
    run("verify_audio_manifest.py")
    # The legacy three-NPC exploration report is standalone analysis, not a
    # production build prerequisite. Keep action/bank validation fail-closed.
    run("generate_sfx_global_ids.py")
    run("verify_sfx_global_ids.py")
    run("plan_action_residency.py", "--runtime-actions")
    run("generate_normal_audio.py")
    run("verify_sfx_production_banks.py", "--runtime-actions")
    # Fail on source/SFX coverage before paying for the music encoder.
    if not sfx_only:
        run("generate_audio_music_ids.py")
        run("build_music_catalog.py", "--output", "distribution", "--catalog",
            "tools/audio/music_catalog.json")
        run("verify_msu_pcm.py")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sfx-only", action="store_true", help="run source/SFX gates without music encoding")
    raise SystemExit(main(parser.parse_args().sfx_only))
