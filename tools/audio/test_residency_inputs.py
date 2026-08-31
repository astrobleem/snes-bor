"""Focused guards for production SFX selection and jump capability."""
from __future__ import annotations

import subprocess
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPILE = ROOT / "tools/audio/compile_reachable_sfx.py"
sys.path.insert(0, str(ROOT / "tools/audio"))
from runtime_sfx_states import explore_stage  # noqa: E402
from shipped_content import STAGE_CONFIGS  # noqa: E402


def main() -> int:
    for path in (r"DATA\SOUNDS\EEK.WAV", r"DATA\SOUNDS\LEONAHEY.WAV"):
        result = subprocess.run([sys.executable, str(COMPILE), "--asset", f"bor-original:{path}"], capture_output=True, text=True)
        if result.returncode == 0 or "not shipped-reachable" not in result.stdout + result.stderr:
            raise SystemExit(f"unreachable production asset was accepted: {path}")
    leo = (ROOT / "out/leo_moveset.json").read_text(encoding="utf-8")
    ralf = (ROOT / "out/ralf_moveset.json").read_text(encoding="utf-8")
    if '"jump": null' in leo or '"jump": null' not in ralf:
        raise SystemExit("jump capability fixture does not distinguish LEO and RALF")
    streets_stage = next(s for s in STAGE_CONFIGS if s["source_level"].upper().endswith("STREETS.TXT"))
    streets = explore_stage(streets_stage)
    if not any(slot["pickup_type"] == 2 for state in streets for slot in state["slots"] if slot["alive"]):
        raise SystemExit("TMNT STREETS runtime states do not expose the Pizza health pickup")
    residency = json.loads((ROOT / "tools/audio/sfx_residency.json").read_text(encoding="utf-8"))
    pizza_state = next((row for row in residency["strategy_c_results"] if row["stage"] == "tmnt:DATA\\LEVELS\\STREETS.TXT" and any(slot["pickup_type"] == 2 for slot in streets[row["state_index"]]["slots"] if slot["alive"])), None)
    if pizza_state is None or "tmnt:DATA\\SOUNDS\\GET.WAV" not in pizza_state["assets"]:
        raise SystemExit("TMNT Pizza state lacks the TMNT health-pickup GET asset")
    print("residency input guards PASS: unreachable assets rejected; LEO jump-capable; RALF not jump-capable; TMNT Pizza requires GET")


if __name__ == "__main__":
    raise SystemExit(main())
