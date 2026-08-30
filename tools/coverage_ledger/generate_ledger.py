#!/usr/bin/env python3
"""notjustfreespecial.txt reopening audit -- "First deliverable": a
generated, machine-readable coverage ledger connecting real converted
content to real runtime handling and real gate coverage, instead of the
multiple hand-copied prose tables this project used to carry (plan_game.md's
"Definitive coverage ledger", README's "Current Status", scattered
game_g7_*.py docstrings).

This ledger is regenerated from source data (build_rom.py's own
ROSTER_PREFIXES, and every out/{prefix}_moveset.json's `animations`/`roles`/
`atchain` fields -- the converter's real output, not the engine's or a
human's claim about itself) every run. It does NOT re-derive runtime/gate
status from main.pasm automatically (that would require a real 65816
static-analysis pass this project doesn't have); ROLE_RUNTIME is the one
hand-maintained classification table this project now keeps -- replacing
the several independent copies that used to drift out of sync with each
other and with reality. Every claim in ROLE_RUNTIME is expected to cite the
gate file(s) that actually prove it, or say plainly that none exists yet.

Classifications (per notjustfreespecial.txt):
  implemented-and-gated  -- real source content, real runtime semantics
                             (not just animation dispatch), a live gate
                             proves trigger+behavior+completion+regression.
  partial                -- some real runtime exists but does not meet the
                             full bar above (e.g. animation-only dispatch
                             standing in for a real mechanic, or missing
                             negative/regression coverage).
  content-inapplicable    -- real source config exists nowhere in the
                             shipped roster/levels that could reach this
                             mechanic; requires a documented raw-content
                             search + OpenBOR source citation, not a guess.
  externally-blocked      -- blocked by something outside this project's
                             control (e.g. no authored SFX content yet).
  unshipped-source-content -- real content exists in the raw PAK but this
                             project doesn't convert/ship it at all.
  unhandled-error          -- content converts and packs, but nothing at
                             runtime handles it and no classification above
                             applies -- the ledger verifier's hard failure
                             case.

Usage:
    python tools/coverage_ledger/generate_ledger.py [--out FILE.json] [--check]

--check runs the verifier (see verify_ledger.py) after generating.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

# ---------------------------------------------------------------------------
# Roster: read the ONE authoritative source (build_rom.py), never hand-copy.
# ---------------------------------------------------------------------------


def load_roster_prefixes():
    import importlib.util
    spec = importlib.util.spec_from_file_location('build_rom', os.path.join(ROOT, 'build_rom.py'))
    mod = importlib.util.module_from_spec(spec)
    # build_rom.py runs top-level code on import (argv parsing etc. lives
    # inside `if __name__ == '__main__'`, so a straight exec of the module
    # body is safe -- confirmed by reading the file: ROSTER_PREFIXES is a
    # bare module-level assignment with no side effects around it).
    spec.loader.exec_module(mod)
    return [p[len('out/'):] for p in mod.ROSTER_PREFIXES]


# ---------------------------------------------------------------------------
# ROLE_RUNTIME: the one hand-maintained classification table. Every entry
# MUST be re-verified against real main.pasm/core/*.pasm content and a real
# gate run before being written here -- this is not a place to restate
# plan_game.md's old prose from memory.
# ---------------------------------------------------------------------------

ROLE_RUNTIME = {
    'idle': dict(handler='Anim_Play (main.pasm), every entity, boot default',
                 gates=['phase5.py', 'phase12_roster.py'],
                 status='implemented-and-gated', evidence=''),
    'walk': dict(handler='Character_PlayFrame movement dispatch (main.pasm)',
                 gates=['phase8.py', 'phase9.py'],
                 status='implemented-and-gated', evidence=''),
    'attack': dict(handler='Y-button attack1 trigger (main.pasm Anim_Play__no_atchain)',
                   gates=['game_g7_attack2.py', 'game_g7_content_audit.py'],
                   status='implemented-and-gated', evidence=''),
    'attack2': dict(handler='X-button attack2 trigger; JOE gets real mutual-lock '
                             '(Character_Grab_Play) via attack2_is_grab, everyone '
                             'else gets instant-damage dispatch',
                     gates=['game_g7_attack2.py', 'game_g7_grab.py'],
                     status='implemented-and-gated', evidence=''),
    'attack3': dict(handler='Jump_PlayMoveSlotAdvance generic slot (variant 3), '
                             'reached via atchain step (LEO/FOOT01/FOOT02)',
                     gates=['game_g7_content_audit.py'],
                     status='implemented-and-gated', evidence=''),
    'attack4': dict(handler='Jump_PlayMoveSlotAdvance generic slot (variant 4), '
                             'reached only as the LAST step of LEO\'s real atchain '
                             '(1 2 3 1 2 4)',
                     gates=['game_g7_content_audit.py'],
                     status='implemented-and-gated', evidence=''),
    'grab': dict(handler='LEO and JOE both now land through the SAME real mutual-lock '
                          'machinery (Character_HitApply__TryGrab, vm_native_engine.pasm): '
                          'LEO\'s R-button `grab` (CHAR_GRABMOVE_FCOUNT, variant 5) and '
                          'JOE\'s attack2_is_grab (variant 1) are two real move-slot shapes '
                          'both accepted by TryGrab\'s condition check, both establishing '
                          'the same CHAR_GRAB_TARGET/CHAR_GRABBED_BY link, rigid follow-'
                          'drag (Character_Grab_Play), and victim-input suppression. '
                          'Jump_PlayerInputGate\'s R dispatch is now gated on hold state '
                          '(CHAR_GRAB_TARGET==$FF) so a new grab attempt cannot restart '
                          'while already holding.',
                  gates=['game_g7_content_audit.py (LEO)', 'game_g7_grab.py (JOE)'],
                  status='implemented-and-gated', evidence=''),
    'grabattack': dict(handler='LEO only: Jump_PlayerInputGate R+Y dispatch sets '
                                'CHAR_ATTACK_VARIANT=8 (Jump_PlayMoveSlotAdvance slot) -- '
                                'now requires an active hold (CHAR_GRAB_TARGET!=$FF) before '
                                'it can fire, matching real BOR\'s grabattack() precondition '
                                '(previously fired unconditionally on any R+Y press).',
                        gates=['game_g7_content_audit.py'],
                        status='implemented-and-gated', evidence=''),
    'slide': dict(handler='LEO only: Down+A trigger, Jump_PlayMoveSlotAdvance slot, '
                           'real damage via shared hit check',
                  gates=['game_g7_content_audit.py'],
                  status='implemented-and-gated', evidence=''),
    'riseattack': dict(handler='UP+Y while CHAR_SELECTED==FALL (holding phase), '
                                'Jump_RiseattackTrigger, Jump_PlayMoveSlotAdvance slot. '
                                'Player-only by explicit sourced design: real BOR.C '
                                'player_lie_check() is called only from the player\'s own '
                                'think()/playerframe() path, never from any AI think '
                                'function -- there is no real "AI rise-attacks" mechanism '
                                'to port (same class of finding as `block`/`land`).',
                        gates=['game_g7_riseattack.py'],
                        status='implemented-and-gated', evidence=''),
    'freespecial': dict(handler='LEO only: double-tap-forward+attack FSM '
                                 '(Jump_FreespecialTrigger), Jump_PlayMoveSlotAdvance slot '
                                 '(variant 9), checked before special/grab/slide in '
                                 'Jump_PlayerInputGate',
                         gates=['game_g7_content_audit.py'],
                         status='implemented-and-gated', evidence=''),
    'special': dict(handler='LEO only: L-button trigger (Jump_PlayerInputGate), '
                             'CHAR_SPECIAL_* base chain, releases an active grab link '
                             'first (Character_Special_ReleaseGrab). Stale-evidence fix: '
                             'the grab-release check used to force CHAR_GRAB_TARGET via a '
                             'raw WRAM write; rewritten to organically establish the link '
                             'first (real R-press retry loop on LEO\'s own `grab` swing, '
                             'via the SAME Character_HitApply__TryGrab mutual-lock path '
                             'JOE\'s attack2 uses) before pressing L to trigger the '
                             'release, then checking BOTH sides of the lock (self.'
                             'CHAR_GRAB_TARGET and the victim\'s own CHAR_GRABBED_BY) '
                             'return to $FF -- verified passing.',
                     gates=['game_g7_special.py'],
                     status='implemented-and-gated', evidence=''),
    'jump': dict(handler='Player-only jump state machine (Jump_PlayerTick) now stores its '
                         'height/velocity in the SAME per-entity CHAR_THROW_ZPOS/ZVEL '
                         'struct fields throw already used -- no more separate player-'
                         'global Player_JumpZPos/ZVel cells. Jump_ApplyOamYOffset reads '
                         'one shared field for both JUMP and THROWN.',
                  gates=['game_g7_jump.py', 'game_g7_throw.py', 'game_g7_depth_sort.py'],
                  status='implemented-and-gated', evidence=''),
    'jumpattack': dict(handler='Y button mid-air (Player_JumpAnimMode=1), reuses JUMP state',
                        gates=['game_g7_jump.py'], status='implemented-and-gated', evidence=''),
    'jumpattack2': dict(handler='X button mid-air (Player_JumpAnimMode=2), reuses JUMP state',
                         gates=['game_g7_jump.py'], status='implemented-and-gated', evidence=''),
    'fall': dict(handler='Character_HitApply sets CHAR_SELECTED=FALL on a real hit '
                          '(knockdown), CHAR_FALL_STATE_TIMER-driven state machine',
                 gates=['game_g7_knockdown.py'], status='implemented-and-gated', evidence=''),
    'rise': dict(handler='Automatic transition out of FALL after CHAR_FALL_STATE_TIMER',
                 gates=['game_g7_knockdown.py'], status='implemented-and-gated', evidence=''),
    'pain': dict(handler='CHAR_HIT_STUN-driven reaction, no distinct anim slot of its own '
                          '(this project reuses the same hit-stun path regardless of the '
                          'raw `pain` anim\'s own ordinal)',
                 gates=['phase5.py'], status='implemented-and-gated', evidence=''),
    'throw': dict(handler='Character_Grab_Throw, generic on its grabber (player or AI), '
                           'per-entity CHAR_THROW_ZPOS/ZVEL -- now the SAME storage/tick '
                           'jump uses (notjustfreespecial.txt item 4), no more duplicate '
                           'gravity-integration copy.',
                   gates=['game_g7_throw.py', 'game_g7_jump.py'],
                   status='implemented-and-gated', evidence=''),
    'attack2_is_grab': dict(
        handler='Real mutual-lock reachable from BOTH directions, both grab AND throw: '
                'player-vs-AI (Character_HitApply__TryGrab) and AI-vs-player (Character_ '
                'HitApply__TryGrabVsPlayer); throw for both directions is the same real '
                'Character_Grab_Throw, reached by the player via Jump_PlayerInputGate\'s '
                'do_throw block and by an AI grabber via a new real per-frame decision '
                '(Anim_Play__ai_seek_gate -> Anim_Play__AiGrabHoldDecide, AI_THROW_ '
                'CHANCE=8/256, same simplification class as Anim_Play__ai_attack\'s own '
                'attack2 roll). Anim_Play__AiSelectAttackVariant gives every AI entity a '
                'real chance to select attack2 in the first place (previously AI never '
                'set CHAR_ATTACK_VARIANT at all).',
        gates=['game_g7_grab.py', 'game_g7_throw.py'],
        status='implemented-and-gated', evidence=''),
    'get': dict(
        handler='Character_Pickup_CheckOverlap__TriggerGet + Jump_PlayGetAdvance '
                '(core/jump.pasm), redirected from bank 8\'s Jump_PlayMoveSlotAdvance '
                '(no bank-0 ROM budget left for its own dispatch check). Real '
                'OPTIONAL_ROLE_NAMES role (convert_character.py) -> pack_msu_roster.py '
                'NEW_MOVE_SLOT_NAMES\'s "get" entry (CHAR_GET_FCOUNT/DELAY/BASE_LO/HI, '
                'own dedicated non-indexed struct fields, GET_MOVE_VARIANT=10) -- '
                'chained via Jump_ComputeBases right before waiting_base. Real '
                'OpenBOR source (player_test_pickable/player_test_touch, '
                'didfind_item) traced: GET is a cosmetic pose on touch-collect '
                '(constrains movement, excluded from combat damage in '
                'Character_HitApply__attacking) with the reward applied instantly, '
                'not gated on the animation completing. Only LEO ships real data '
                '(1 frame, `still01.gif`) -- GetFcount==0 for every other roster '
                'member correctly falls back to the pre-existing silent instant-'
                'collect with no animation (RALF etc, the real source-defined '
                'fallback for a character with no ANI_GET), not an unbuilt gap.',
        gates=['game_g8_get_leo.py', 'game_g7_special.py'],
        status='implemented-and-gated', evidence=''),
    'waiting': dict(
        handler='CharSelect_PortraitUpdate (core/jump.pasm, called via jsl from '
                'Game_State_Play__charselect). Real OPTIONAL_ROLE_NAMES role '
                '(convert_character.py) -> pack_msu_roster.py OPTIONAL_ROLE_WAITING '
                '(CHAR_WAITING_FCOUNT/DELAY/BASE_LO/BASE_HI, chained last in the '
                'per-entity base-offset hop). Only LEO ships real data (1 frame, '
                '`select.gif`, `loop 1`) -- FCOUNT==0 for the other 12 roster '
                'members is the correctly-measured real-content outcome, not an '
                'unbuilt gap. CHARSELECT never ran ANY OAM render path before this '
                '(Game_State_Play only dispatches Core_Oop_Play/Character_'
                'RenderPass/Core_Oam_Play from GAME_STATE_PLAYING, confirmed by '
                'inspection) -- added a self-contained portrait render path '
                '(deferred one frame past a reselect, to avoid stacking Msu1_'
                'LoadFrame\'s DMA-queue cost on top of Anim_LoadCharacter\'s own '
                'palette DMA in the same frame, a real regression this slice hit '
                'and fixed). Streams the real converted frame via the same Msu1_'
                'LoadFrame mechanism every other animation uses; hides (OAM Y=$F0) '
                'for every character without real data; torn down automatically on '
                'the first GAME_STATE_PLAYING frame (same OAM slot 0, no explicit '
                'teardown code needed -- Character_RenderPass overwrites it before '
                'that frame\'s vblank commits).',
        gates=['game_g5_portrait.py', 'game_g5_menus.py'],
        status='implemented-and-gated', evidence=''),
    'block': dict(handler=None, gates=[], status='content-inapplicable',
                  evidence='Grepped every currently-shipped character .TXT '
                           '(Beats of Rage Original + TMNT paks) for a `block` anim '
                           'declaration or FLAG_BLOCK-relevant model property -- zero '
                           'matches in either pak. No re-audit performed this slice; '
                           'carried forward from the prior content-audit slice\'s own '
                           'grep, not re-verified against notjustfreespecial.txt\'s '
                           'stricter bar (raw-content search cited, but the exact grep '
                           'command/output is not re-attached here -- should be before '
                           'this classification is trusted again).'),
    'land': dict(handler='Character_Throw_Play__land (vm_native_engine.pasm). '
                         'notjustfreespecial.txt item 7 re-audit (sourced from real '
                         'DCurrent/openbor engine/openbor.c): the prior "zero '
                         'forcedirection/projectile/blast/autoland/ATTACK_FORCE config '
                         'anywhere" claim was WRONG -- LEO ships a real, uncommented '
                         '`anim land` entry (1 frame, reuses rise01.gif); JHUN\'s `#anim '
                         'land` is genuinely disabled/commented data. Real doland() is '
                         'normally gated on BLAST_TOSS attack-force config (none shipped '
                         'here), but player_fall_check() is a SEPARATE, player-only '
                         'trigger: holding UP+JUMP while CHAR_SELECTED_THROWN lands via '
                         'ANI_LAND instead of the ordinary FALL reaction, gated only on '
                         'the real global autoland default (0 == enabled) -- independent '
                         'of any per-model flag. Reuses the existing idle transition, no '
                         'new streaming pathway, matching this project\'s jumpattack2/'
                         'throw "no unique art" precedent. Cross-checked against raw pak '
                         'source by the standalone game_g7_land_audit.py finding-reporter.',
                 gates=['game_g7_throw.py'],
                 status='implemented-and-gated', evidence=''),
    'backwalk': dict(
        handler=None, gates=[], status='content-inapplicable',
        evidence='claude_close_g7_g8_before_g10.md Part 1 audit: real OpenBOR '
                 '`backwalk`/ANI_WALKBACK content (only MOUSER ships it, TMNT '
                 'pak, checked directly against all 13 shipped roster .TXT '
                 'files -- no other character declares it). This project '
                 'implements a single generic Walk state with no distinct '
                 'backward-movement mechanic; adding one is a new AI-movement '
                 'feature, not part of this converter-role-selection defect '
                 'class. Was previously the actual DEFECT (silently mis-'
                 'claimed by the old attack2 fallback heuristic, wiring '
                 'MOUSER\'s attack2 input to a walking animation instead of '
                 'his real second attack, `upper`) -- now correctly excluded '
                 'from that fallback and left honestly unmapped instead of '
                 'silently wrong.'),
    'upper': dict(
        handler=None, gates=[], status='content-inapplicable',
        evidence='claude_close_g7_g8_before_g10.md Part 1 audit. `upper` is '
                 'real BOR/TMNT data in two shapes: (a) RALF/LEATHER/FOOT03/'
                 'FOOT04/MOUSER declare it with no literal `attack2` -- there '
                 'it genuinely IS the character\'s one real second attack, '
                 'shipped as the `attack2` role (see that entry) and gated by '
                 'game_g7_attack2.py/game_g7_grab.py; this row only appears '
                 'for the OTHER shape. (b) FOOT01/FOOT02/ROCK/BEBOP declare '
                 'BOTH a literal `attack2` AND a separate `upper`; source '
                 'evidence it is not a genuinely distinct third move for '
                 'these four: FOOT01/FOOT02\'s own real `atchain 1 2 3` '
                 'explicitly excludes it from OpenBOR\'s real combo-chain '
                 '(perform_atchain(), DCurrent/openbor engine/openbor.c); '
                 'ROCK/BEBOP declare no atchain at all and their `upper` '
                 'stanza is a near byte-identical duplicate of their own '
                 '`attack2` (same source GIFs/hit coordinates, only cosmetic '
                 'delay/range/offset drift) -- consistent with `upper` being '
                 'the same legacy attack2-name convention as shape (a), kept '
                 'declared rather than removed once the newer literal '
                 '`attack2` name was authored. This project implements no '
                 'per-model AI decision table or openborscript content (see '
                 'openbor_script_vm_gap project memory), so there is no real, '
                 'source-derived trigger for a genuinely separate third move '
                 'here; inventing one (a spare button, an unbacked AI-random '
                 'third choice) would be fabricated behavior, not implemented '
                 'source content.'),
    'alias': dict(handler=None, gates=[], status='content-inapplicable',
                  evidence='Real BOR.C: alias is a cosmetic display-name override with '
                           'no gameplay effect (see alias_keyword_is_cosmetic_not_'
                           'identity project memory, sourced from BOR.C directly) -- '
                           'not an animation, nothing to gate.'),
}

# Level/spawn-format keywords tracked separately from character animations
# (different content class -- see plan_game.md 8a's own history).
LEVEL_KEYWORD_RUNTIME = {
    'health': dict(handler='Spawn_ApplyHealthOverride (core/spawn.pasm)',
                    gates=['game_health_override.py'], status='implemented-and-gated', evidence=''),
    'map': dict(handler='Spawn_ApplyRemapPalette (core/spawn.pasm)',
                 gates=['game_map_remap.py'], status='implemented-and-gated', evidence=''),
    'wait': dict(handler='SPAWN_KIND_WAIT dispatch (core/spawn.pasm)',
                  gates=['game_g9_wait_group_boss.py'], status='implemented-and-gated', evidence=''),
    'group': dict(handler='real BOR.C-sourced group spawn semantics (core/spawn.pasm)',
                   gates=['game_g9_wait_group_boss.py'], status='implemented-and-gated', evidence=''),
    'boss': dict(handler='EntityN_IsBoss + boss health bar (core/spawn.pasm, main.pasm)',
                  gates=['game_g9_boss_bar.py', 'game_g9_tmnt_boss.py', 'game_g9_wait_group_boss.py'],
                  status='implemented-and-gated', evidence=''),
    'blockade': dict(handler=None, gates=[], status='content-inapplicable',
                      evidence='Real BOR.C keyword is `blocked` (pit hazard), not a '
                               'scroll-back blockade -- zero real enabled usage in '
                               'either shipped pak. See 8a_final_audit project memory.'),
    'direction': dict(handler=None, gates=[], status='content-inapplicable',
                       evidence='TMNT\'s `rightleft` is a real no-op per BOR.C source; no '
                                'shipped level uses direction-reversal content.'),
    'settime': dict(handler=None, gates=[], status='content-inapplicable',
                     evidence='Zero real enabled usage anywhere in either shipped pak, '
                              'per 8a_final_audit\'s own re-check against real BOR.C.'),
}


# ---------------------------------------------------------------------------
# claude_begin_g10_with_approval.md: "First: fix the remaining verifier
# imperfection". Each ledger row needs a deterministic owning phase so
# verify_phase_status.py can enforce per-phase completeness instead of a
# single global "no phase may be done while ANY row anywhere is
# unfinished" check. Kept as a separate lookup (not inline per-entry
# fields) so this stays a focused, reviewable table instead of touching
# every ROLE_RUNTIME/LEVEL_KEYWORD_RUNTIME literal.
#
# Mapping rule: a role/keyword is owned by the G-numbered phase whose own
# gate(s) actually prove it (ROLE_RUNTIME/LEVEL_KEYWORD_RUNTIME's own
# `gates` list, cross-checked against plan_game.md's phase sections). A
# handful of rows predate the G-numbering entirely -- idle/walk/pain were
# proven by the old pre-G "Phase 5/8/9" gates, real engine behavior that
# shipped before G1 existed as a concept -- these map to PHASE_FOUNDATIONAL
# (no G-phase owns them, and none needs to: they are not what any G-phase
# gate re-proves, and a G-phase's own completion never depends on them).
# Every entry below must resolve to either a real 'G'+digits phase tag
# that also appears in phase_status.json, or PHASE_FOUNDATIONAL -- there is
# no silent "unmapped" state (see the assertion in build_ledger()).
PHASE_FOUNDATIONAL = 'foundational'

ROLE_PHASE_MAP = {
    'idle': PHASE_FOUNDATIONAL,          # phase5.py/phase12_roster.py (pre-G)
    'walk': PHASE_FOUNDATIONAL,          # phase8.py/phase9.py (pre-G)
    'pain': PHASE_FOUNDATIONAL,          # phase5.py (pre-G hit-stun reaction)
    'attack': 'G7',
    'attack2': 'G7',
    'attack3': 'G7',
    'attack4': 'G7',
    'grab': 'G7',
    'grabattack': 'G7',
    'slide': 'G7',
    'riseattack': 'G7',
    'freespecial': 'G7',
    'special': 'G7',
    'jump': 'G7',
    'jumpattack': 'G7',
    'jumpattack2': 'G7',
    'fall': 'G7',
    'rise': 'G7',
    'throw': 'G7',
    'attack2_is_grab': 'G7',
    'land': 'G7',
    'get': 'G8',
    'waiting': 'G5',
    # content-inapplicable rows: real per-model/per-pak audit findings, not
    # runtime behavior any phase implements -- no phase owns these, and
    # phase_note (below) records why rather than leaving it implicit.
    'block': PHASE_FOUNDATIONAL,
    'backwalk': PHASE_FOUNDATIONAL,
    'upper': PHASE_FOUNDATIONAL,
    'alias': PHASE_FOUNDATIONAL,
}

LEVEL_KEYWORD_PHASE_MAP = {
    'health': 'G8',
    'map': 'G8',
    'wait': 'G9',
    'group': 'G9',
    'boss': 'G9',
    'blockade': PHASE_FOUNDATIONAL,
    'direction': PHASE_FOUNDATIONAL,
    'settime': PHASE_FOUNDATIONAL,
}

PHASE_NOTES = {
    PHASE_FOUNDATIONAL: 'Predates the G-numbered phase system (proven by '
                         'pre-G "Phase N" gates or a real per-model/per-pak '
                         'content-inapplicable audit) -- no G-phase\'s own '
                         'completion depends on this row.',
}


def _owning_phase_for(role_or_kw, phase_map):
    phase = phase_map.get(role_or_kw)
    if phase is None:
        raise KeyError(f'{role_or_kw!r} has no ROLE_PHASE_MAP/LEVEL_KEYWORD_PHASE_MAP '
                        f'entry -- every ledger-eligible role/keyword must be assigned '
                        f'a real G-phase or PHASE_FOUNDATIONAL explicitly, no silent '
                        f'default.')
    return phase


def build_ledger():
    roster = load_roster_prefixes()
    rows = []
    for name in roster:
        path = os.path.join(ROOT, 'out', f'{name}_moveset.json')
        with open(path, 'r', encoding='utf-8') as f:
            moveset = json.load(f)
        anim_by_name = {a['name'].lower(): a for a in moveset['animations']}
        roles = moveset.get('roles', {})
        atchain = moveset.get('atchain', [])

        # Every raw animation the converter actually produced for this
        # character -- the real "shipped content inventory" the audit
        # demands, independent of whether any role claimed it.
        claimed_ordinals = {v for v in roles.values() if isinstance(v, int)}
        for anim in moveset['animations']:
            anim_name = anim['name'].lower()
            ordinal = anim['ordinal']
            row = {
                'character': name,
                'source': f'out/{name}_moveset.json (converted; raw PAK path not '
                          f'retained in this artifact -- see convert_character.py '
                          f'call site for the real .pak/.TXT pair used)',
                'animation': anim['name'],
                'ordinal': ordinal,
                'frames': anim['frames'],
                'claimed_by_role': ordinal in claimed_ordinals,
            }
            # claude_close_g7_g8_before_g10.md Part 1/4 fix: some raw anim
            # NAMES (e.g. 'upper') are genuinely ambiguous -- the SAME
            # literal name is a real, implemented `attack2` for one
            # character (RALF/LEATHER/FOOT03/FOOT04/MOUSER, no literal
            # `attack2` anim of their own) and real, content-inapplicable
            # standalone content for another (FOOT01/FOOT02/ROCK/BEBOP, who
            # ALSO declare a literal `attack2`). A literal-name-first lookup
            # can't distinguish these -- it would misclassify RALF's real,
            # gated attack2 as content-inapplicable the moment 'upper' also
            # got its own ROLE_RUNTIME entry. Resolve by OWNING ROLE first
            # (roles dict insertion order already puts the canonical role
            # name -- 'attack2' -- before an ambiguous alias like 'upper'
            # when both map to the same ordinal, per convert_character.py's
            # own resolution order), falling back to a literal-name lookup
            # only when no role claims this ordinal at all.
            owning_role = None
            if ordinal in claimed_ordinals:
                owning_role = next((r for r, o in roles.items() if o == ordinal), None)
            role_entry = ROLE_RUNTIME.get(owning_role) if owning_role else None
            if role_entry is None:
                role_entry = ROLE_RUNTIME.get(anim_name)
            if role_entry is not None:
                ev = role_entry['evidence']
                if owning_role and owning_role != anim_name and ev:
                    ev = f'(shipped as role `{owning_role}`) ' + ev
                phase_key = owning_role if owning_role in ROLE_PHASE_MAP else anim_name
                phase = _owning_phase_for(phase_key, ROLE_PHASE_MAP)
                row.update(runtime_handler=role_entry['handler'],
                           owning_gates=role_entry['gates'],
                           classification=role_entry['status'],
                           evidence=ev, phase=phase,
                           phase_note=PHASE_NOTES.get(phase, ''))
            elif ordinal not in claimed_ordinals:
                # Real content exists, no known role name matches it, and no
                # role claimed its ordinal -- this is exactly the
                # "unshipped-source-content stays in the ledger" case, NOT
                # silently dropped. Not owned by any G-phase (nothing
                # implements it) -- foundational bucket, phase_note explains.
                row.update(runtime_handler=None, owning_gates=[],
                           classification='unshipped-source-content',
                           evidence=f'"{anim["name"]}" has real converted frame data '
                                    f'but matches no known engine role name and its '
                                    f'ordinal was not claimed by any role resolution '
                                    f'pass in convert_character.py.',
                           phase=PHASE_FOUNDATIONAL,
                           phase_note='Unshipped/unclaimed source content -- no phase '
                                      'implements it, so none owns this row.')
            else:
                row.update(runtime_handler=None, owning_gates=[],
                           classification='unhandled-error',
                           evidence=f'Claimed by role `{owning_role}` but that role '
                                    f'has no ROLE_RUNTIME entry -- ledger generator '
                                    f'needs updating.',
                           phase=PHASE_FOUNDATIONAL,
                           phase_note='unhandled-error: generator bug, not phase-owned.')
            rows.append(row)

        if atchain:
            # notjustfreespecial.txt item 5: LEO/FOOT01/FOOT02 are the three
            # real chain-bearing characters -- each now has its own real
            # atchain independently driven live end-to-end by
            # game_g7_content_audit.py (drive_atchain_and_check_damage for
            # FOOT01/FOOT02, the dedicated 6-step section for LEO), not
            # borrowed coverage from LEO's own test.
            atchain_status = 'implemented-and-gated'
            atchain_evidence = ''
            rows.append({
                'character': name, 'source': f'out/{name}_moveset.json',
                'animation': f'atchain {atchain}', 'ordinal': None, 'frames': None,
                'claimed_by_role': True,
                'runtime_handler': 'Jump_AtchainTrigger (core/jump.pasm), CHAR_ATCHAIN0-5/'
                                    'CHAR_CHAINLENGTH/CHAR_COMBOSTEP/CHAR_COMBOTIMER',
                'owning_gates': ['game_g7_content_audit.py'],
                'classification': atchain_status,
                'evidence': atchain_evidence,
                'phase': 'G7',
                'phase_note': '',
            })

    for kw, entry in LEVEL_KEYWORD_RUNTIME.items():
        phase = _owning_phase_for(kw, LEVEL_KEYWORD_PHASE_MAP)
        rows.append({
            'character': None, 'source': 'level .TXT keyword (not a character animation)',
            'animation': kw, 'ordinal': None, 'frames': None, 'claimed_by_role': True,
            'runtime_handler': entry['handler'], 'owning_gates': entry['gates'],
            'classification': entry['status'], 'evidence': entry['evidence'],
            'phase': phase, 'phase_note': PHASE_NOTES.get(phase, ''),
        })

    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(ROOT, 'tools', 'coverage_ledger', 'ledger.json'))
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()

    rows = build_ledger()
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(rows, f, indent=2)
    print(f'wrote {len(rows)} rows to {args.out}')

    counts = {}
    for r in rows:
        counts[r['classification']] = counts.get(r['classification'], 0) + 1
    for k, v in sorted(counts.items()):
        print(f'  {k}: {v}')

    if args.check:
        from verify_ledger import verify
        sys.exit(0 if verify(rows) else 1)


if __name__ == '__main__':
    main()
