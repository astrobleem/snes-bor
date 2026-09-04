#!/usr/bin/env python3
"""Generate the stage-indexed MSU track table from the audio manifest."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from shipped_content import STAGE_CONFIGS

ROOT = Path(__file__).resolve().parents[2]
def main() -> int:
    manifest = json.loads((ROOT / "tools/audio/audio_manifest.json").read_text(encoding="utf-8"))
    assets = [a for f in manifest["families"] for a in f["assets"] if a.get("track_key")]
    stages = []
    for stage in STAGE_CONFIGS:
        level = stage["source_level"].upper()
        refs = [r for a in assets for r in a["references"]
                if r.get("reachability") == "shipped-reachable"
                and a["family"] == stage["family"]
                and r.get("directive") == "music"
                and r.get("source_file", "").upper().endswith(level)]
        if len(refs) != 1:
            raise SystemExit(f"expected one authored music directive for {stage['source_level']}, got {len(refs)}")
        asset = next(a for a in assets if refs[0] in a["references"])
        stages.append(asset["track_key"])
    ids = {a.get("track_key"): a.get("msu_track_id") for a in assets}
    STAGES = stages
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
        # OpenBOR's level and boss music calls pass loop=1 separately from
        # the authored musicOffset byte argument.
        repeats.append(1)
    text += "Music_StageRepeats:\n    .db " + ", ".join(str(value) for value in repeats) + "\n"
    boss_tracks = []
    for stage in STAGE_CONFIGS:
        level = stage["source_level"].upper()
        refs = [r for a in assets for r in a["references"]
                if r.get("reachability") == "shipped-reachable"
                and a["family"] == stage["family"]
                and r.get("directive") == "bossmusic"
                and r.get("source_file", "").upper().endswith(level)]
        if len(refs) > 1:
            raise SystemExit(f"expected at most one authored bossmusic directive for {stage['source_level']}, got {len(refs)}")
        boss_tracks.append(0 if not refs else next(a["msu_track_id"] for a in assets if refs[0] in a["references"]))
    text += "Music_StageBossTracks:\n    .db " + ", ".join(str(value) for value in boss_tracks) + "\n"
    text += "Music_StageBossRepeats:\n    .db " + ", ".join("1" for _ in boss_tracks) + "\n"
    ending_family = STAGE_CONFIGS[-1]["family"]
    ending_refs = [r for a in assets for r in a["references"]
                   if a["family"] == ending_family
                   and r.get("reachability") == "shipped-reachable"
                   and r.get("directive") == "music"
                   and r.get("source_file", "").upper() == "DATA\\SCENES\\ENDING.TXT"]
    if len(ending_refs) != 1:
        raise SystemExit(f"expected one reachable ending music directive for {ending_family}, got {len(ending_refs)}")
    text += "Music_EndingTrack = " + str(next(a["msu_track_id"] for a in assets if ending_refs[0] in a["references"])) + "\n"
    text += "Music_EndingRepeat = 1\n"
    text += f"Music_StageTrackCount = {len(STAGES)}\n"
    (ROOT / "tools/audio/audio_music_ids.pasm").write_text(text, encoding="ascii")
    print("generated stage music IDs:", [ids[key] for key in STAGES])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
