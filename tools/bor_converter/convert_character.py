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
from PIL import Image

sys.path.append(os.path.dirname(__file__))
from convert_animation import (_load_anim_frames, _quantize_shared,
                                _write_anim_outputs, _frame_bbox_and_bg,
                                TARGET_W, TARGET_H)
from pak_extract import extract
from entity_parse import parse_entity
from convert_sprite import to_bgr555

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

# Real jump slice (plan_game.md 7): 'jump'/'jumpattack'/'jumpattack2' are
# real, unambiguous OpenBOR anim names (confirmed in LEO's real .TXT data --
# no BOR-roster character declares any of them, so this is a pure addition,
# not a behavior change for RALF/JOE/JHUN/YASHIRO/MOUSER/FOOT01-04/ROCK/
# BEBOP/LEATHER). Matched the exact same case-insensitive exact-name way as
# ROLE_NAMES above -- resolved as OPTIONAL roles downstream (pack_msu_
# roster.py's OPTIONAL_ROLE_JUMP/JUMPATTACK/JUMPATTACK2), same shape as
# 'attack2'/'attack2_is_grab', not required like ROLE_NAMES' own five.
OPTIONAL_ROLE_NAMES = ['jump', 'jumpattack', 'jumpattack2', 'special']

# G7 content-audit slice (plan_game.md 7, "no reachable content stays
# inert" pass): real, buildable, previously-unconverted-to-any-role
# animation names, found by re-reading every roster character's real
# .TXT directly rather than assuming the roster's known-role set was
# already exhaustive -- it wasn't (LEO alone has 8 more real, baked-but-
# unwired anims: attack3/attack4/grab/throw/grabattack/slide, TMNT's
# FOOT01/FOOT02 also have a real attack3). Exact-name match, same
# convention as every other role above, but each ALSO excludes any
# ordinal a higher-priority role (this list's own order, then attack2's
# own heuristic) already claimed -- see MOVE_SLOT_NAMES' own comment for
# why that matters (JOE's `grab` anim is already his attack2; it must
# not ALSO become a redundant separate `grab` role for him).
#
# Fixed slot order for pack_msu_roster.py's generic move-descriptor table
# (replaces the old one-hardcoded-struct-field-per-move scheme) -- 'attack2'
# and 'special' are resolved separately above/below (pre-existing, more
# involved logic: attack2 has a real fallback heuristic, special has none)
# but occupy slots 0/1 of this SAME table for base-offset-chain purposes.
MOVE_SLOT_NAMES = ['attack2', 'special', 'attack3', 'attack4', 'grab',
                    'slide', 'riseattack', 'grabattack']


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


def _derive_remap_palettes(pak_path, base_dir, remaps, idle_loaded,
                            idle_frame0_indices, base_palette, out_dir):
    """plan_game.md 8a row 3 (`map`). OpenBOR's real colourmap mechanism
    (BOR.C's load_colourmap()) is a per-pixel-index substitution table built
    by diffing a base image against a same-shape `remap` image -- confirmed
    directly against this project's real pak data (RALF's idle1.gif vs
    map1.gif: 0 of 11049 pixels differ in transparency/shape, 1609 differ in
    color) that every shipped remap is the SAME pose recolored, never a
    distinct sprite. That means this project's existing per-frame tile/index
    data needs no separate conversion per remap -- only a new 16-color
    palette, derived by re-running idle frame 0's own crop/scale/placement
    transform (computed once by `_load_anim_frames` for the whole idle
    animation) against each alt GIF, then mode-voting the alt image's color
    at every canvas coordinate idle frame 0's own (already-quantized) index
    grid assigned to each of the 16 shared palette slots. An index idle
    frame 0 never used (it's covered by a different animation/frame in the
    character's shared palette) falls back to that index's base color rather
    than guessing.

    Returns a list of 16-int BGR555 lists, one per (base, alt) pair in
    `remaps`, in order."""
    scale = idle_loaded['scale']
    hx_canvas, hy_canvas = idle_loaded['hotspot_canvas']
    idle_frame0_meta = idle_loaded['frames_meta'][0]

    results = []
    for base_gif, alt_gif in remaps:
        base_path = base_gif.replace('/', '\\')
        if '\\' not in base_path:
            base_path = base_dir + '\\' + base_path
        alt_path = alt_gif.replace('/', '\\')
        if '\\' not in alt_path:
            alt_path = base_dir + '\\' + alt_path

        def _load_rgb(entry_path, tmp_name):
            data = extract(pak_path, entry_path)
            tmp_path = os.path.join(out_dir, tmp_name)
            with open(tmp_path, 'wb') as f:
                f.write(data)
            im = Image.open(tmp_path).convert('RGB')
            os.remove(tmp_path)
            return im

        base_im = _load_rgb(base_path, '_tmp_remap_base.gif')
        alt_im = _load_rgb(alt_path, '_tmp_remap_alt.gif')

        # Same bbox/hotspot _load_anim_frames derives for any single frame --
        # reused here (not recomputed against the alt image) because the
        # base and alt GIFs are confirmed pixel-shape-identical, so the
        # base's own bbox/hotspot apply unchanged.
        bbox = _frame_bbox_and_bg(base_im)
        hotspot = idle_frame0_meta['offset'] if idle_frame0_meta['offset'] is not None else (
            (bbox[0] + bbox[2]) // 2, bbox[3])
        minx, miny, maxx, maxy = bbox
        hx, hy = hotspot

        crop = alt_im.crop((minx, miny, maxx + 1, maxy + 1))
        cw, ch = crop.size
        new_w, new_h = max(1, round(cw * scale)), max(1, round(ch * scale))
        resized = crop.resize((new_w, new_h), Image.NEAREST)

        alt_canvas = Image.new('RGB', (TARGET_W, TARGET_H), alt_im.getpixel((0, 0)))
        px_pos = hx_canvas + round((minx - hx) * scale)
        py_pos = hy_canvas + round((miny - hy) * scale)
        alt_canvas.paste(resized, (px_pos, py_pos))
        apx = alt_canvas.load()

        buckets = {}
        for y in range(TARGET_H):
            for x in range(TARGET_W):
                idx = idle_frame0_indices[y][x]
                if idx == 0:
                    continue
                buckets.setdefault(idx, []).append(apx[x, y])

        alt_palette = [0] * 16
        for idx in range(1, 16):
            votes = buckets.get(idx)
            if votes:
                counts = {}
                for c in votes:
                    counts[c] = counts.get(c, 0) + 1
                winner = max(counts.items(), key=lambda kv: kv[1])[0]
                alt_palette[idx] = to_bgr555(winner)
            else:
                alt_palette[idx] = to_bgr555(base_palette.get(idx, (0, 0, 0)))
        results.append(alt_palette)
    return results


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
    per_anim_frame_indices = []
    cursor = 0
    for anim_name, L in zip(anim_names, loaded):
        n = len(L['canvases'])
        frame_indices = all_frame_indices[cursor:cursor + n]
        cursor += n
        per_anim_frame_indices.append(frame_indices)
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
    for role in OPTIONAL_ROLE_NAMES:
        roles[role] = lower_names.index(role) if role in lower_names else None
    attack_ordinal = next((i for i, n in enumerate(lower_names) if n.startswith('attack')), None)
    roles['attack'] = attack_ordinal

    # G7 content-audit slice: resolve attack3/attack4/slide/riseattack/
    # grabattack (exact-name match) BEFORE attack2's own fallback heuristic
    # runs, so that heuristic's "first otherwise-unclaimed anim" scan can
    # never mistake one of THESE for attack2. This ordering is itself the
    # fix for a real, previously-undetected instance of the exact bug the
    # comment below already documents for BEBOP/ROCK: LEATHER declares
    # 'riseattack' (ordinal 5) with no literal 'attack2' anywhere in its
    # file, so the OLD code (which resolved attack2's fallback before
    # checking for a 'riseattack' role at all) silently wired LEATHER's
    # attack2 input to riseattack -- found via this slice's own re-audit,
    # not previously caught because LEATHER was never rechecked after the
    # BEBOP/ROCK fix landed.
    #
    # 'grab' is deliberately NOT in this pre-pass -- see its own resolution
    # after attack2 below for why (JOE's real second attack move IS a real
    # grab anim, and the existing attack2_is_grab mechanism depends on the
    # fallback heuristic still being ALLOWED to claim it).
    PRE_ATTACK2_MOVE_SLOTS = [r for r in MOVE_SLOT_NAMES[2:] if r != 'grab']
    known_ordinals = {v for v in roles.values() if v is not None}
    for role in PRE_ATTACK2_MOVE_SLOTS:
        if role in lower_names and lower_names.index(role) not in known_ordinals:
            ordinal = lower_names.index(role)
        else:
            ordinal = None
        roles[role] = ordinal
        if ordinal is not None:
            known_ordinals.add(ordinal)

    # G7 content-audit slice, second real bug found the same way: JHUN's
    # real second attack (his own combo continuation) is textually named
    # 'jumpattack' in the source data -- but JHUN has no real 'jump' anim
    # at all (jumpheight not declared), so this project's own real jump
    # slice already established (main.pasm's CHAR_ATTACK2_FCOUNT comment:
    # "RALF=upper, JOE=grab, JHUN=jumpattack") that his 'jumpattack' anim
    # is his GROUND attack2, not a real jump-attack -- he can never enter
    # JUMP state to reach it any other way. `jumpattack`/`jumpattack2`
    # were added to OPTIONAL_ROLE_NAMES (real jump slice) and, like every
    # other optional role, resolved into known_ordinals before attack2's
    # own fallback ever ran -- silently reproducible the moment anyone
    # reconverted JHUN (found here by doing exactly that as part of this
    # audit's full-roster regeneration; JHUN's committed moveset.json
    # predated OPTIONAL_ROLE_NAMES entirely and had never been touched
    # since, masking this). Fixed the same way as riseattack's own
    # exclusion above, but conditionally: 'jumpattack'/'jumpattack2' only
    # block attack2's fallback when the character ALSO has a real 'jump'
    # anim (meaning those ordinals genuinely serve their real jump-attack
    # purpose and must stay reserved for it) -- verified this doesn't
    # affect LEO (has both 'jump' AND a literal 'attack2', so the fallback
    # branch never runs for him regardless).
    attack2_fallback_excluded = set(known_ordinals)
    if roles.get('jump') is None:
        for jump_role in ('jumpattack', 'jumpattack2'):
            ord_ = roles.get(jump_role)
            if ord_ is not None:
                attack2_fallback_excluded.discard(ord_)

    # plan_game.md 7 (G7 remaining: a real second attack move, generic --
    # not hardcoded to any one character's real move name). Real per-
    # character second moves in RALF/JOE/JHUN/YASHIRO are NOT named
    # 'attack2'/'attack3' (OpenBOR's own numbered-attack convention, checked
    # directly -- none of those four use it); they're distinctly-named
    # combo/special moves (upper, grab, jumpattack). So the fallback below
    # ("first anim not already claimed by another role") was written for
    # that shape and verified safe for those four characters specifically.
    #
    # REAL BUG, found and fixed converting LEO (TMNT): that fallback treats
    # "first declared, otherwise-unclaimed anim" as "the second attack",
    # which silently breaks for any character whose file declares a
    # non-role anim EARLIER than its real second attack. LEO declares
    # 'waiting' (a menu-select pose, not a combat move) before its real
    # 'attack2'; the fallback picked 'waiting'. Fixed by preferring a
    # literal anim named 'attack2' before falling back to the old
    # heuristic, AND (this slice) by resolving every other real named role
    # -- including 'riseattack' -- first, so the fallback's own "first
    # unclaimed ordinal" scan can't land on one of those either (see the
    # comment on the loop just above for the LEATHER bug this closes).
    if 'attack2' in lower_names and lower_names.index('attack2') not in attack2_fallback_excluded:
        attack2_ordinal = lower_names.index('attack2')
    else:
        attack2_ordinal = next(
            (i for i in range(len(lower_names)) if i not in attack2_fallback_excluded), None)
    roles['attack2'] = attack2_ordinal
    if attack2_ordinal is not None:
        known_ordinals.add(attack2_ordinal)

    # plan_game.md 7 (grab mutual-lock slice): whether attack2's real anim
    # name is literally 'grab' -- derived from real converted data, never
    # hardcoded per character (moveset_pipeline_generalization's standing
    # rule). Only a character whose second move IS a real grab animation
    # (currently JOE) gets real mutual-lock semantics; RALF's 'upper' and
    # JHUN's 'jumpattack' are not grabs and must keep today's instant-
    # damage attack2 behavior unchanged.
    roles['attack2_is_grab'] = (
        attack2_ordinal is not None and lower_names[attack2_ordinal] == 'grab')
    if attack2_ordinal is not None:
        known_ordinals.add(attack2_ordinal)

    # G7 content-audit slice: the generic 'grab' role -- resolved AFTER
    # attack2, excluding whatever ordinal attack2 just claimed. For JOE,
    # this means 'grab' resolves to None here (his grab anim is already
    # his attack2, via attack2_is_grab above -- unchanged, no redundant
    # second grab trigger). For LEO, whose real attack2 is a literal,
    # different 'attack2' anim, his separate real 'grab'/'throw'/
    # 'grabattack' data (ordinals 12/13/19) is genuinely unclaimed and
    # resolves as real, new, generically-detected grab-capability.
    if 'grab' in lower_names and lower_names.index('grab') not in known_ordinals:
        grab_ordinal = lower_names.index('grab')
    else:
        grab_ordinal = None
    roles['grab'] = grab_ordinal
    if grab_ordinal is not None:
        known_ordinals.add(grab_ordinal)

    # Real BOR.C `atchain` (engine/openbor.c's perform_atchain()): a real
    # per-character combo-chain sequence over attack1-4 (1-based attack-
    # number values, NOT anim ordinals) -- LEO declares `atchain 1 2 3 1 2
    # 4`, FOOT01/FOOT02 declare `atchain 1 2 3`, no other roster character
    # declares one at all (PAK-verified, all 13 currently-converted roster
    # members checked directly). Stored as raw 1-4 values here -- pack_msu_
    # roster.py, not this converter, owns mapping each value onto this
    # project's own CHAR_ATTACK_VARIANT encoding (a packing-format detail,
    # not something the converter should know about).
    moveset_atchain = list(entity.get('atchain') or [])

    # plan_game.md 8a row 3 (`map`): derive one alt palette per real `remap`
    # line this character declares (see _derive_remap_palettes' own header).
    # Every remap is keyed off the character's own idle-frame-1 image in all
    # 4 shipped roster characters (verified directly against real pak data),
    # so this needs idle's own frame-0 canvas transform/index grid -- skipped
    # (empty list) if the character has no `remap` lines or no idle role at
    # all (shouldn't happen for a real playable/AI roster character, but a
    # future pak's non-idle-having entity legitimately might).
    remap_palettes = []
    idle_ord = roles.get('idle')
    if entity.get('remaps') and idle_ord is not None:
        base_dir = entity_entry_name.replace('/', '\\').rsplit('\\', 1)[0]
        remap_palettes = _derive_remap_palettes(
            pak_path, base_dir, entity['remaps'], loaded[idle_ord],
            per_anim_frame_indices[idle_ord][0], palette, out_prefix + '_idle')

    moveset = {
        'entity': entity['name'],
        'prefix': out_prefix,
        'animations': [
            {'ordinal': i, 'name': anim_name, 'dir': out_dir, 'frames': result['frames']}
            for i, (anim_name, out_dir, result) in enumerate(results)
        ],
        'roles': roles,
        # G7 content-audit slice -- real `atchain` values (1-4), [] if this
        # character declares none.
        'atchain': moveset_atchain,
        # plan_game.md 8a row 3 -- list of 16-int BGR555 lists, [] if none
        'remap_palettes': remap_palettes,
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
