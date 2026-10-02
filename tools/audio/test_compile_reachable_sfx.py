"""Mandatory selection/self-compile check for the reachable SFX scratch tool."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "audio" / "compile_reachable_sfx.py"


def main() -> int:
    result = subprocess.run(
        [sys.executable, str(TOOL), "--asset", r"bor-original:DATA\SOUNDS\BEAT1.WAV"],
        capture_output=True, text=True,
    )
    output = result.stdout + result.stderr
    if result.returncode or "all-reachable SFX compile PASS: 1 assets" not in output:
        print(output)
        raise SystemExit("BEAT1-only scratch compile failed")
    print("BEAT1-only selection/compile PASS")
    print(output, end="")


if __name__ == "__main__":
    raise SystemExit(main())
