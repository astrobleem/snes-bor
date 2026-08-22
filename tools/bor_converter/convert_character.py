#!/usr/bin/env python3
"""Convert EVERY animation a character's real entity .TXT declares (not a
fixed hardcoded list) through convert_animation.py's own per-animation
pipeline (shared scale, per-frame placement -- see that module's docstring),
quantized into ONE shared 16-color palette across all of them.

Why this exists: convert_animation.py already shares a palette *within*
one animation (all of idle's frames quantize together), but each
animation is converted in its own separate CLI invocation, so each of a
character's animations would otherwise end up with its own independently-
chosen 16 colors. Quantizing every animation's frames together fixes this
at the source: `palette.txt` ends up identical across every
`<prefix>_<anim>` directory, so gen_pasm_animset.py's existing
`load_palette()` is reading the right, shared, answer regardless of which
directory it's pointed at.

**Generalized 2026-08-22** (plan_game.md 7, "generalize the moveset
pipeline" slice): the old `ANIMS` list hardcoded exactly
`[idle, walk, attack1, fall, rise]`. Real OpenBOR characters declare wildly
different animation sets -- measured directly across 3 real paks, BOR has
20 distinct anim names across its 45 characters (up to 19/character), TMNT
24 names across 81 characters (up to 21/character), DDM 80 names across 227
characters (up to 33/character). No fixed list can cover this, and the
project's own conversion-tooling standing instruction (CLAUDE.md) requires
general OpenBOR compatibility, not a fit to today's roster.

This script now enumerates every `anim <name>` block the character's real
.TXT actually declares, converts each to its own `<prefix>_<sanitized-name>`
directory (ordinal-ordered, in file declaration order), and writes a
`<prefix>_moveset.json` character-level manifest listing every ordinal's
real name plus which of the SNES engine's known ROLE_NAMES (the only
animation names any Poppy/.pasm code is allowed to know about -- see
pack_msu_roster.py's ROLE_NAMES and main.pasm's Anim_Play__dispatch) it
matches, case-insensitively, by exact name. A character missing a role
(e.g. YASHIRO has no second attack; some real entities skip `pain`) simply
has no ordinal for it -- pack_msu_roster.py encodes that as $FF, never a
guess. Animations beyond the known roles are still converted (real frame
data, a real ordinal slot) but are not wired to any engine behavor yet --
inert data, not dropped, ready for whenever multi-move dispatch is scoped
(see plan_game.md 7's role-table design note for why that's deliberately
deferred rather than hand-built here).

Usage:
    python convert_character.py <pak_path> <entity_txt_entry> <out_prefix>

Example:
    python convert_character.py "Beats of Rage Original [v.3.0 Build 4086].pak" \\
        "DATA\\CHARS\\RALF\\RALF.TXT" out/ralf
    # -> out/ralf_idle/, out/ralf_walk/, out/ralf_pain/, out/ralf_attack1/,
    #    out/ralf_fall/, out/ralf_rise/, out/ralf_upper/ (whatever RALF.TXT
    #    really declares), out/ralf_moveset.json
"""
import sys
import os
import re
import json

sys.path.append(os.path.dirname(__file__))
from convert_animation import _load_anim_frames, _quantize_shared, _write_anim_outputs
from pak_extract import extract
from entity_parse import parse_entity

# The ONLY animation names any .pasm/engine code is allowed to know about --
# see main.pasm's ROLE_IDLE/WALK/PAIN/ATTACK/FALL/RISE constants. Matched
# case-insensitively against each character's real anim names; first
# real anim name in this list's synonyms wins if a character somehow
# declares more than one match (shouldn't happen in real data, but the
# ordinal chosen is deterministic -- first declared -- either way).
#
# 'attack' is special: OpenBOR's own convention (confirmed across all 4
# shipped characters' real .TXT data) names the base attack `attack1`, with
# `attack2`/`attack3`/... reserved for combo continuations -- there is no
# bare `attack` animation name in real data. This project implements only
# the single base attack today (multi-move combat is explicitly deferred,
# see plan_game.md 7's role-table design note), so 'attack' resolves to the
# FIRST declared anim whose name starts with "attack" (case-insensitive),
# not an exact-name match like the other four roles.
ROLE_NAMES = ['idle', 'walk', 'pain', 'fall', 'rise']


def _sanitize(anim_name):
    """Filesystem-safe directory suffix for a real (possibly odd) anim
    name -- real paks are all plain alnum today, but DDM-style names with
    inline comment tokens are already reduced to just the name by
    entity_parse.py's tokenizer (comment tokens never reach args[0])."""
    return re.sub(r'[^A-Za-z0-9_-]', '_', anim_name.lower())


def _enumerate_anims(pak_path, entity_entry_name):
    """Returns (entity_dict, ordered list of real anim names) -- declaration
    order, matching entity['animations'] dict insertion order (Python dicts
    preserve insertion order; entity_parse.py inserts as it parses top to
    bottom)."""
    entity_data = extract(pak_path, entity_entry_name)
    entity = parse_entity(entity_data.decode('latin1'))
    anim_names = [name for name, anim in entity['animations'].items() if anim['frames']]
    if not anim_names:
        raise ValueError(f'{entity_entry_name!r} declares no non-empty animations')
    return entity, anim_names


def convert_character(pak_path, entity_entry_name, out_prefix):
    entity, anim_names = _enumerate_anims(pak_path, entity_entry_name)

    loaded = [
        _load_anim_frames(pak_path, entity_entry_name, anim_name,
                           out_prefix + '_' + _sanitize(anim_name))
        for anim_name in anim_names
    ]

    all_canvases = [c for L in loaded for c in L['canvases']]
    all_masks = [m for L in loaded for m in L['masks']]
    palette, all_frame_indices = _quantize_shared(all_canvases, all_masks)

    results = []
    cursor = 0
    for anim_name, L in zip(anim_names, loaded):
        n = len(L['canvases'])
        frame_indices = all_frame_indices[cursor:cursor + n]
        cursor += n
        out_dir = out_prefix + '_' + _sanitize(anim_name)
        result = _write_anim_outputs(
            out_dir, L['frames_meta'], frame_indices, palette,
            L['entity_name'], anim_name, L['loop'], L['scale'], L['hotspot_canvas'])
        results.append((anim_name, out_dir, result))

    # Role assignment: first declared anim whose real name matches a role,
    # case-insensitively. $FF-equivalent (None) if the character has none.
    lower_names = [n.lower() for n in anim_names]
    roles = {}
    for role in ROLE_NAMES:
        roles[role] = lower_names.index(role) if role in lower_names else None
    attack_ordinal = next((i for i, n in enumerate(lower_names) if n.startswith('attack')), None)
    roles['attack'] = attack_ordinal

    moveset = {
        'entity': entity['name'],
        'prefix': out_prefix,
        'animations': [
            {'ordinal': i, 'name': anim_name, 'dir': out_dir, 'frames': result['frames']}
            for i, (anim_name, out_dir, result) in enumerate(results)
        ],
        'roles': roles,
    }
    moveset_path = out_prefix + '_moveset.json'
    with open(moveset_path, 'w') as f:
        json.dump(moveset, f, indent=2)

    return results, moveset_path


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        raise SystemExit(1)
    pak_path, entity_entry, out_prefix = sys.argv[1:4]
    results, moveset_path = convert_character(pak_path, entity_entry, out_prefix)
    for anim_name, out_dir, result in results:
        print(f'--- {anim_name} ({out_dir}) ---')
        for k, v in result.items():
            print(f'{k}: {v}')
    print(f'moveset manifest: {moveset_path}')


if __name__ == '__main__':
    main()
