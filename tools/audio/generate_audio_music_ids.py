#!/usr/bin/env python3
"""Generate the stage-indexed MSU track table from the audio manifest."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STAGES = [
    "bor-original:DATA\\MUSIC\\KOF.BOR", "bor-original:DATA\\MUSIC\\ASC.BOR",
    "tmnt:DATA\\MUSIC\\NYSTREET.BOR", "tmnt:DATA\\MUSIC\\FIRE.BOR",
    "tmnt:DATA\\MUSIC\\SEWERS.BOR", "tmnt:DATA\\MUSIC\\REMIX\\PAINOVO.BOR",
    "tmnt:DATA\\MUSIC\\REMIX\\TAU1.BOR", "tmnt:DATA\\MUSIC\\REMIX\\ZETA1.BOR",
    "tmnt:DATA\\MUSIC\\REMIX\\GLIESE86.BOR", "tmnt:DATA\\MUSIC\\FIRE.BOR",
]


def main() -> int:
    manifest = json.loads((ROOT / "tools/audio/audio_manifest.json").read_text(encoding="utf-8"))
    ids = {a.get("track_key"): a.get("msu_track_id") for f in manifest["families"] for a in f["assets"] if a.get("track_key")}
    missing = [key for key in STAGES if key not in ids]
    if missing:
        raise SystemExit("missing generated track mapping: " + ", ".join(missing))
    text = "; GENERATED from tools/audio/audio_manifest.json and build_rom.py's authored stage order.\n"
    text += "; Do not edit numeric IDs by hand; regenerate with generate_audio_music_ids.py.\n\n"
    text += "Music_StageTracks:\n    .db " + ", ".join(str(ids[key]) for key in STAGES) + "\n"
    repeats = []
    for key in STAGES:
        asset = next(a for f in manifest["families"] for a in f["assets"]
                     if a.get("track_key") == key)
        args = [r.get("loop_argument") for r in asset["references"]
                if r.get("reachability") == "shipped-reachable"
                and r.get("loop_argument") is not None]
        repeats.append(1 if not args or "1" in args else 0)
    text += "Music_StageRepeats:\n    .db " + ", ".join(str(value) for value in repeats) + "\n"
    text += f"Music_StageTrackCount = {len(STAGES)}\n"
    (ROOT / "tools/audio/audio_music_ids.pasm").write_text(text, encoding="ascii")
    print("generated stage music IDs:", [ids[key] for key in STAGES])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
