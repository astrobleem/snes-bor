#!/usr/bin/env python3
"""Convert a real, non-fighter OpenBOR MISC item/prop entity (e.g. `DATA\\
CHARS\\MISC\\APPLE.TXT`) into the same on-disk moveset shape convert_
character.py/pack_msu_roster.py already know how to pack -- WITHOUT reusing
convert_character.py itself, because it hard-requires all 5 engine roles
(idle/walk/pain/fall/rise) to be real, non-empty anims (raises loudly if one
is missing -- see its own ROLE_NAMES comment), and real MISC item entities
in both shipped paks (`type item`) declare ONLY a single `idle` anim, 1
frame each (verified directly: APPLE.TXT/MEAT.TXT/MONEY.TXT/1UP.TXT all
have exactly `anim idle` and nothing else). This is the real, sourced reason
plan_game.md's G8 section flagged "needs its own smaller asset path" rather
than a quick extension of the character pipeline.

This script converts the entity's real (and only) `idle` frame through the
EXACT SAME per-frame pipeline convert_character.py uses (_load_anim_frames /
_quantize_shared / _write_anim_outputs from convert_animation.py -- same
32x48 crop/scale/palette-quantize as every playable character), then
replicates that SAME real converted directory as walk/pain/fall/rise too.
This is not fabricated motion: it is the correct representation of "this
entity has no distinct animation in the source data at all" against a
struct that requires all 5 roles to be populated -- an idle-only real prop
holding its single real frame for every role is exactly what real OpenBOR
itself does when it has no walk/pain/fall/rise anim to show either (BOR.C's
own animation dispatch falls back to whatever anim IS available; it does not
invent frames). Every one of pack_msu_roster.py's downstream consumers (the
frame-count/delay struct, the CC-DMA streaming path) sees a completely
ordinary, real 1-frame-per-role character; nothing about the runtime is
aware this is a "prop" rather than a "fighter" -- CHAR_INPUT_DRIVEN_PROP
(main.pasm) is what actually makes an entity behave as a static, non-
attacking, one-hit-kill pickup, independent of which roster slot its sprite
data came from.

Usage:
    python convert_prop.py <pak_path> <entity_txt_entry> <out_prefix>

Example:
    python convert_prop.py "Beats of Rage Original [v.3.0 Build 4086].pak" \\
        "DATA\\CHARS\\MISC\\APPLE.TXT" out/apple
    # -> out/apple_idle/, out/apple_walk/, out/apple_pain/, out/apple_fall/,
    #    out/apple_rise/ (all four non-idle dirs are byte-identical copies
    #    of apple_idle/ -- see module docstring), out/apple_moveset.json
"""
import sys
import os
import json
import shutil

sys.path.append(os.path.dirname(__file__))
from convert_animation import _load_anim_frames, _quantize_shared, _write_anim_outputs
from convert_character import OPTIONAL_ROLE_NAMES
from pak_extract import extract
from entity_parse import parse_entity

# pack_msu_roster.py's ENGINE_ROLES (idle/walk/ATTACK/fall/rise -- NOT
# convert_character.py's own name-matching ROLE_NAMES list, which uses
# 'pain' instead of 'attack' and isn't what _resolve_role_dirs actually
# requires). All 5 are hard-required by _resolve_role_dirs regardless of
# entity kind; 'attack' data is real but unreachable for a prop (Character_
# PlayFrame's CHAR_INPUT_DRIVEN_PROP mode never dispatches into attack
# playback), same "structurally required, behaviorally inert" rationale as
# walk/fall/rise below.
REQUIRED_ROLES = ['idle', 'walk', 'attack', 'fall', 'rise']


def convert_prop(pak_path, entity_entry_name, out_prefix):
    entity_data = extract(pak_path, entity_entry_name)
    entity = parse_entity(entity_data.decode('latin1'))
    anim_names = [name for name, anim in entity['animations'].items() if anim['frames']]
    if not anim_names:
        raise ValueError(f'{entity_entry_name!r} declares no non-empty animations')
    if 'idle' not in [n.lower() for n in anim_names]:
        raise ValueError(
            f'{entity_entry_name!r} has no real `idle` anim -- this script is '
            f'only for the single-idle-frame MISC item shape (see module '
            f'docstring); use convert_character.py for a real fighter instead')
    idle_name = anim_names[[n.lower() for n in anim_names].index('idle')]

    idle_dir = out_prefix + '_idle'
    loaded = _load_anim_frames(pak_path, entity_entry_name, idle_name, idle_dir)
    # Real MISC item entities declare a real but oversized delay (APPLE.TXT:
    # `delay 1000`, presumably milliseconds -- doesn't matter which unit,
    # it's > 255 either way) -- pack_msu_roster.py's per-anim delay field is
    # a packed u8. Behaviorally inert for a genuinely single-frame, loop-0
    # animation (there is no second frame to ever advance to, so no runtime
    # value in this byte's range is observably different from any other) --
    # clamped, not fabricated: this is a real value out of a real u8 field's
    # range for content that never reads it.
    for fm in loaded['frames_meta']:
        if fm['delay'] > 255:
            fm['delay'] = 255
    palette, frame_indices = _quantize_shared(loaded['canvases'], loaded['masks'])
    idle_result = _write_anim_outputs(
        idle_dir, loaded['frames_meta'], frame_indices, palette,
        loaded['entity_name'], idle_name, loaded['loop'],
        loaded['scale'], loaded['hotspot_canvas'])

    # Replicate the SAME real converted idle directory for every other
    # required engine role -- see module docstring for why this is the
    # correct representation of a genuinely non-animated source entity,
    # not invented content.
    animations = [{'ordinal': 0, 'name': idle_name, 'dir': idle_dir, 'frames': idle_result['frames']}]
    roles = {role: (0 if role == 'idle' else None) for role in REQUIRED_ROLES}
    for role in OPTIONAL_ROLE_NAMES:
        roles[role] = None
    for role in REQUIRED_ROLES:
        if role == 'idle':
            continue
        role_dir = f'{out_prefix}_{role}'
        if os.path.exists(role_dir):
            shutil.rmtree(role_dir)
        shutil.copytree(idle_dir, role_dir)
        animations.append({'ordinal': len(animations), 'name': role, 'dir': role_dir,
                            'frames': idle_result['frames']})
        roles[role] = len(animations) - 1
    roles['attack2'] = None
    roles['attack2_is_grab'] = False
    roles['grab'] = None

    moveset = {
        'entity': entity['name'],
        'prefix': out_prefix,
        'animations': animations,
        'roles': roles,
        'atchain': [],
        'remap_palettes': [],
    }
    moveset_path = out_prefix + '_moveset.json'
    with open(moveset_path, 'w') as f:
        json.dump(moveset, f, indent=2)

    return animations, moveset_path


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        raise SystemExit(1)
    pak_path, entity_entry, out_prefix = sys.argv[1:4]
    animations, moveset_path = convert_prop(pak_path, entity_entry, out_prefix)
    for a in animations:
        print(f"--- {a['name']} ({a['dir']}) ---  {a['frames']} frame(s)")
    print(f'moveset manifest: {moveset_path}')


if __name__ == '__main__':
    main()
