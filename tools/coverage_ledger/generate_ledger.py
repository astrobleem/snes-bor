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
                     status='partial',
                     evidence='game_g7_content_audit.py exercises atchain steps 0/1/3 '
                              '(attack1->attack2->attack3) but never independently '
                              'proves attack4 (variant 4) is reachable for LEO -- see '
                              'attack4 row. Real damage IS proven for attack3-family '
                              'moves via the shared CHAR_SELECTED==2 hit check, but no '
                              'gate isolates attack3 specifically the way slide/grab/ '
                              'grabattack get their own dedicated checks.'),
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
                                'Jump_RiseattackTrigger, Jump_PlayMoveSlotAdvance slot',
                        gates=['game_g7_content_audit.py'],
                        status='partial',
                        evidence='notjustfreespecial.txt item 6: only BEBOP is exercised '
                                 'end-to-end (trigger + CHAR_FALL_STATE_TIMER reset); '
                                 'ROCK and LEATHER (also real riseattack data per the '
                                 'ledger below) are never independently driven through '
                                 'the same gate. No gate proves real hit/damage from a '
                                 'riseattack swing, rejection outside the lie window, '
                                 'dead-state rejection, or whether an AI-controlled '
                                 'BEBOP/ROCK/LEATHER can ever reach this trigger (Jump_ '
                                 'RiseattackTrigger is only ever called from the player-'
                                 'input path -- AI entities never call it, and this has '
                                 'not been checked against real BOR AI decision-making '
                                 'to confirm that omission is correct rather than a gap).'),
    'freespecial': dict(handler='LEO only: double-tap-forward+attack FSM '
                                 '(Jump_FreespecialTrigger), Jump_PlayMoveSlotAdvance slot '
                                 '(variant 9), checked before special/grab/slide in '
                                 'Jump_PlayerInputGate',
                         gates=['game_g7_content_audit.py'],
                         status='implemented-and-gated', evidence=''),
    'special': dict(handler='LEO only: L-button trigger (Jump_PlayerInputGate), '
                             'CHAR_SPECIAL_* base chain, releases an active grab link '
                             'first (Character_Special_ReleaseGrab)',
                     gates=['game_g7_special.py'],
                     status='partial',
                     evidence='notjustfreespecial.txt item 8: game_g7_special.py\'s '
                              'grab-release check forces CHAR_GRAB_TARGET via a raw WRAM '
                              'write (LEO has no real grab role that would establish one '
                              'organically today) -- explicitly flagged in that gate\'s '
                              'own docstring as structural/plumbing, not an organic '
                              'sequence. Once `grab` above is fixed to a real link, this '
                              'should become an organic grab-then-special sequence.'),
    'jump': dict(handler='Player-only jump state machine (Jump_PlayerTick), '
                         'Player_JumpZPos/ZVel WRAM cells (NOT part of the CHAR_ZP_LEN '
                         'per-entity struct)',
                  gates=['game_g7_jump.py'],
                  status='partial',
                  evidence='notjustfreespecial.txt item 4: jump keeps a separate, '
                           'player-global altitude/velocity representation while throw '
                           'keeps its own per-entity CHAR_THROW_ZPOS/ZVEL and its own '
                           'second gravity-integration copy (Character_Grab_Throw / '
                           'Character_Throw_Play) -- two physics systems for what should '
                           'be one shared per-entity airborne representation. Not '
                           'unified.'),
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
    'throw': dict(handler='JOE (grabber-side) only: Character_Grab_Throw, per-entity '
                           'CHAR_THROW_ZPOS/ZVEL, own gravity integration copy',
                   gates=['game_g7_throw.py'], status='partial',
                   evidence='Real and gated for JOE, but see `jump` row above -- shares '
                            'the physics-duplication defect (notjustfreespecial.txt item '
                            '4). AI-side grab/throw reachability also unresolved -- see '
                            'the `attack2_is_grab` row below.'),
    'attack2_is_grab': dict(
        handler='Real mutual-lock reachable from BOTH directions: player-vs-AI '
                '(Character_HitApply__TryGrab) and AI-vs-player (Character_HitApply__ '
                'TryGrabVsPlayer, vm_native_engine.pasm) -- the latter previously did not '
                'exist at all (Character_HitApply_VsPlayer never called any grab-check). '
                'Anim_Play__AiSelectAttackVariant gives every AI entity a real (64/256) '
                'chance to select attack2, a structural gap fixed alongside this (AI '
                'never set CHAR_ATTACK_VARIANT at all before).',
        gates=['game_g7_grab.py', 'game_g7_throw.py'],
        status='partial',
        evidence='notjustfreespecial.txt item 3, AI-side grab reachability now real and '
                 'gated (game_g7_grab.py section 7). AI-side THROW reachability remains '
                 'unresolved: Character_Grab_Throw is still only ever called from the '
                 'player-input path (Jump_PlayerInputGate\'s do_throw block) -- no AI '
                 'throw-trigger exists.'),
    'get': dict(handler=None, gates=[], status='partial',
                evidence='Converted (real frame data exists per-character where '
                         'authored) but not resolved to any engine role at all -- '
                         '`get` never appears in convert_character.py\'s ROLE_NAMES/ '
                         'OPTIONAL_ROLE_NAMES/MOVE_SLOT_NAMES, so pack_msu_roster.py '
                         'never ships it and nothing in main.pasm references it. G8 '
                         'scope (item pickup pose) -- not started.'),
    'waiting': dict(handler=None, gates=[], status='partial',
                    evidence='Converted (real frame data exists, e.g. LEO ordinal 0, 1 '
                             'frame) but never resolved to any engine role and never '
                             'referenced anywhere in main.pasm (grep-confirmed, no '
                             'ANI_SELECT/portrait code exists at all). MEASURED (not '
                             'just grepped) via game_g5_menus.py, 2026-08-29: GAME_STATE_'
                             'CHARSELECT (core/charselect.pasm) never calls Core_Oop_Play '
                             'or any OAM update at all -- during real char-select, '
                             'nothing is rendered on screen, not even a stale/frozen '
                             'sprite or the character\'s ordinary idle animation (that '
                             'was this ledger\'s prior, WRONG assumption -- corrected '
                             'here). Real hardware OAM stays at the dead-hide Y sentinel '
                             'and CHAR_FRAME_INDEX never advances across 48 sampled '
                             'frames after a real reselect. G5 scope -- not started.'),
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
    'land': dict(handler=None, gates=[], status='content-inapplicable',
                 evidence='notjustfreespecial.txt item 7: NOT YET RE-AUDITED against '
                          'the stricter bar this reopening demands (global autoland '
                          'behavior, model configuration, throw/attack-force flags, '
                          'blast/toss configuration, every shipped model containing '
                          '`land`). Prior classification was "zero forcedirection/ '
                          'projectile/blast/autoland/ATTACK_FORCE config anywhere" -- a '
                          'grep-level check, not the full source-path audit item 7 '
                          'requires. Flagged here as needing re-verification, not '
                          'trusted as-is.'),
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
            role_entry = ROLE_RUNTIME.get(anim_name)
            row = {
                'character': name,
                'source': f'out/{name}_moveset.json (converted; raw PAK path not '
                          f'retained in this artifact -- see convert_character.py '
                          f'call site for the real .pak/.TXT pair used)',
                'animation': anim['name'],
                'ordinal': anim['ordinal'],
                'frames': anim['frames'],
                'claimed_by_role': anim['ordinal'] in claimed_ordinals,
            }
            if role_entry is not None:
                row.update(runtime_handler=role_entry['handler'],
                           owning_gates=role_entry['gates'],
                           classification=role_entry['status'],
                           evidence=role_entry['evidence'])
            elif anim['ordinal'] not in claimed_ordinals:
                # Real content exists, no known role name matches it, and no
                # role claimed its ordinal -- this is exactly the
                # "unshipped-source-content stays in the ledger" case, NOT
                # silently dropped.
                row.update(runtime_handler=None, owning_gates=[],
                           classification='unshipped-source-content',
                           evidence=f'"{anim["name"]}" has real converted frame data '
                                    f'but matches no known engine role name and its '
                                    f'ordinal was not claimed by any role resolution '
                                    f'pass in convert_character.py.')
            else:
                # Claimed by a role whose name differs from the anim's own
                # literal name (e.g. RALF's 'upper' anim claimed by the
                # generic 'attack2' role) -- look up by role name instead.
                owning_role = next((r for r, o in roles.items() if o == anim['ordinal']), None)
                role_entry2 = ROLE_RUNTIME.get(owning_role) if owning_role else None
                if role_entry2 is not None:
                    ev = role_entry2['evidence']
                    if ev:
                        ev = f'(shipped as role `{owning_role}`) ' + ev
                    row.update(runtime_handler=role_entry2['handler'],
                               owning_gates=role_entry2['gates'],
                               classification=role_entry2['status'],
                               evidence=ev)
                else:
                    row.update(runtime_handler=None, owning_gates=[],
                               classification='unhandled-error',
                               evidence=f'Claimed by role `{owning_role}` but that role '
                                        f'has no ROLE_RUNTIME entry -- ledger generator '
                                        f'needs updating.')
            rows.append(row)

        if atchain:
            # Classification mirrors the weakest link in the chain (attack3/
            # attack4 rows above) -- as of this slice both are real and
            # gated for LEO (game_g7_content_audit.py drives the FULL 6-step
            # sequence), but FOOT01/FOOT02's own real chains (`1 2 3`, no
            # attack4) are only proven up through their first-3-step subset
            # of the SAME LEO-driven test, never independently for their own
            # roster slot -- flag that honestly rather than borrowing LEO's
            # gate coverage for a different character's data.
            is_leo = name == 'leo'
            atchain_status = ROLE_RUNTIME['attack4']['status'] if is_leo else 'partial'
            atchain_evidence = '' if is_leo else (
                f'Real atchain data ({atchain}) confirmed via CHAR_CHAINLENGTH ground '
                f'truth, but no gate independently drives THIS character\'s own chain '
                f'end-to-end -- only LEO\'s is actually exercised by '
                f'game_g7_content_audit.py.')
            rows.append({
                'character': name, 'source': f'out/{name}_moveset.json',
                'animation': f'atchain {atchain}', 'ordinal': None, 'frames': None,
                'claimed_by_role': True,
                'runtime_handler': 'Jump_AtchainTrigger (core/jump.pasm), CHAR_ATCHAIN0-5/'
                                    'CHAR_CHAINLENGTH/CHAR_COMBOSTEP/CHAR_COMBOTIMER',
                'owning_gates': ['game_g7_content_audit.py'],
                'classification': atchain_status,
                'evidence': atchain_evidence,
            })

    for kw, entry in LEVEL_KEYWORD_RUNTIME.items():
        rows.append({
            'character': None, 'source': 'level .TXT keyword (not a character animation)',
            'animation': kw, 'ordinal': None, 'frames': None, 'claimed_by_role': True,
            'runtime_handler': entry['handler'], 'owning_gates': entry['gates'],
            'classification': entry['status'], 'evidence': entry['evidence'],
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
