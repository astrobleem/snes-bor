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
from shipped_content import STAGE_CONFIGS, source_character_identity  # noqa: E402


def main() -> int:
    for path in (r"DATA\SOUNDS\EEK.WAV", r"DATA\SOUNDS\LEONAHEY.WAV"):
        result = subprocess.run([sys.executable, str(COMPILE), "--asset", f"bor-original:{path}"], capture_output=True, text=True)
        if result.returncode == 0 or "not shipped-reachable" not in result.stdout + result.stderr:
            raise SystemExit(f"unreachable production asset was accepted: {path}")
    leo = (ROOT / "out/leo_moveset.json").read_text(encoding="utf-8")
    ralf = (ROOT / "out/ralf_moveset.json").read_text(encoding="utf-8")
    if '"jump": null' in leo or '"jump": null' not in ralf:
        raise SystemExit("jump capability fixture does not distinguish LEO and RALF")
    for source, expected in ((r"DATA\CHARS\MISC\CHAIR.TXT", "MISC\\CHAIR"), (r"DATA\CHARS\MISC\TABLE.TXT", "MISC\\TABLE"), (r"DATA\CHARS\RALF\RALF.TXT", "RALF"), (r"DATA\CHARS\LEO\LEO.TXT", "LEO")):
        family = "tmnt" if "\\LEO\\" in source else "bor-original"
        if source_character_identity(family, source) != expected:
            raise SystemExit(f"character identity resolver mismatch: {source}")
    manifest = json.loads((ROOT / "tools/audio/audio_manifest.json").read_text(encoding="utf-8"))
    bor = next(f for f in manifest["families"] if f["family"] == "bor-original")
    wood = next(a for a in bor["assets"] if a["source_path"] == r"DATA\SOUNDS\WOOD.WAV")
    owners = {r.get("character_identity") for r in wood["references"] if r.get("reachability") == "shipped-reachable"}
    if not {"MISC\\CHAIR", "MISC\\TABLE"}.issubset(owners):
        raise SystemExit("MISC prop diesound ownership did not make WOOD reachable")
    streets_stage = next(s for s in STAGE_CONFIGS if s["source_level"].upper().endswith("STREETS.TXT"))
    streets = explore_stage(streets_stage)
    if not any(slot["pickup_type"] == 2 for state in streets for slot in state["slots"] if slot["alive"]):
        raise SystemExit("TMNT STREETS runtime states do not expose the Pizza health pickup")
    tmnt = next(f for f in manifest["families"] if f["family"] == "tmnt")
    tmnt_get = next(a for a in tmnt["assets"] if a["source_path"] == r"DATA\SOUNDS\GET.WAV")
    if not tmnt_get["shipped_reachable"]:
        raise SystemExit("TMNT Pizza health-pickup global GET is not reachable in the manifest")
    print("residency input guards PASS: unreachable assets rejected; LEO jump-capable; RALF not jump-capable; TMNT Pizza requires GET")


if __name__ == "__main__":
    raise SystemExit(main())
