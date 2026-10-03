#!/usr/bin/env python3
"""Generated authored-scene sequence description for BOR animation clips."""
from __future__ import annotations

from pathlib import Path

RUGAL_SCENE_ID = 1
ENDING_SCENE_ID = 2


def render(scenes):
    lines = [
        "; GENERATED from authored BOR scene declarations; do not edit.",
        "; BORVID1 records are video clip IDs; scenes own ordered clip lists.",
        "", f"SceneSequence_Count = {len(scenes)}", "",
    ]
    clip_ids = []
    clip_offsets = []
    for index, scene in enumerate(scenes):
        prefix = f"SceneSequence_Record{index}_"
        lines += [f"{prefix}SceneId = {scene['scene_id']}",
                  f"{prefix}AudioTrack = {scene['audio_track']}",
                  f"{prefix}AudioRepeat = {scene['audio_repeat']}",
                  f"{prefix}ClipCount = {len(scene['clips'])}",
                  f"{prefix}ClipIds:", "    .db " + ", ".join(map(str, scene["clips"])), ""]
        clip_offsets.append(len(clip_ids))
        clip_ids.extend(scene["clips"])
    lines += [
        "; Indexed tables consumed by the generic scene-sequence runtime.",
        "SceneSequence_SceneIds:",
        "    .db " + ", ".join(str(scene["scene_id"]) for scene in scenes),
        "SceneSequence_AudioTracks:",
        "    .db " + ", ".join(str(scene["audio_track"]) for scene in scenes),
        "SceneSequence_AudioRepeats:",
        "    .db " + ", ".join(str(scene["audio_repeat"]) for scene in scenes),
        "SceneSequence_ClipCounts:",
        "    .db " + ", ".join(str(len(scene["clips"])) for scene in scenes),
        "SceneSequence_ClipOffsets:",
        "    .dw " + ", ".join(str(offset) for offset in clip_offsets),
        "SceneSequence_ClipIds:",
        "    .db " + ", ".join(map(str, clip_ids)),
        "",
        "SceneSequence_Rugal = 1", "SceneSequence_Ending = 2"]
    return "\n".join(lines) + "\n"


def write(path: str | Path, scenes):
    Path(path).write_text(render(scenes), encoding="ascii", newline="\n")
