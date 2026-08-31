"""Focused guards for production SFX selection and jump capability."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPILE = ROOT / "tools/audio/compile_reachable_sfx.py"


def main() -> int:
    for path in (r"DATA\SOUNDS\EEK.WAV", r"DATA\SOUNDS\LEONAHEY.WAV"):
        result = subprocess.run([sys.executable, str(COMPILE), "--asset", f"bor-original:{path}"], capture_output=True, text=True)
        if result.returncode == 0 or "not shipped-reachable" not in result.stdout + result.stderr:
            raise SystemExit(f"unreachable production asset was accepted: {path}")
    leo = (ROOT / "out/leo_moveset.json").read_text(encoding="utf-8")
    ralf = (ROOT / "out/ralf_moveset.json").read_text(encoding="utf-8")
    if '"jump": null' in leo or '"jump": null' not in ralf:
        raise SystemExit("jump capability fixture does not distinguish LEO and RALF")
    print("residency input guards PASS: unreachable assets rejected; LEO jump-capable; RALF not jump-capable")


if __name__ == "__main__":
    raise SystemExit(main())
