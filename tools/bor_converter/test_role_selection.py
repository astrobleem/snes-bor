#!/usr/bin/env python3
"""Regression coverage for convert_character.py's role-selection logic
(claude_close_g7_g8_before_g10.md Part 1's required "converter-level
regression coverage" -- this is that file).

Exercises resolve_roles() (pure, no pak/image I/O) against the exact real
declaration-order anim-name lists this project's shipped roster members
carry (re-verified directly against the raw .TXT source when this file was
written -- not invented data). Run directly:

    python tools/bor_converter/test_role_selection.py

Exits nonzero and prints every failure if any check fails.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from convert_character import resolve_roles  # noqa: E402

FAILURES = []


def check(label, cond, detail=''):
    if not cond:
        FAILURES.append(f'{label}: {detail}')


def main():
    # -- The real bug this slice fixes: MOUSER declares 'backwalk' BEFORE
    # its real second attack 'upper'. The old fallback ("first otherwise-
    # unclaimed ordinal") picked 'backwalk' as attack2. Must never happen
    # again for Mouser or any future character shaped the same way.
    mouser = resolve_roles(
        ['idle', 'backwalk', 'walk', 'pain', 'fall', 'rise', 'attack1', 'upper'])
    check('mouser backwalk not attack2', mouser['attack2'] != 1,
          f"attack2={mouser['attack2']} (backwalk's ordinal)")
    check('mouser backwalk recognized', mouser.get('backwalk') == 1, mouser)
    check('mouser attack2 is upper', mouser['attack2'] == 7, mouser)
    check('mouser upper mirrors attack2', mouser.get('upper') == 7, mouser)

    # -- An arbitrary first-unclaimed animation must never become attack2:
    # a synthetic character with a menu/noncombat anim declared before its
    # real second attack (same shape as LEO's real 'waiting' bug and
    # Mouser's real 'backwalk' bug -- generalized, not anim-name-specific).
    synthetic = resolve_roles(
        ['idle', 'walk', 'pain', 'fall', 'rise', 'waiting', 'attack1', 'special_move'])
    check('unclaimed noncombat anim (waiting) never becomes attack2',
          synthetic['attack2'] != 5, synthetic)
    check('real trailing move still found via fallback',
          synthetic['attack2'] == 7, synthetic)

    # -- RALF: real second move is 'upper', no literal 'attack2' -- must
    # still resolve via the fallback (regression guard: the Part 1 fix
    # must not break this working case).
    ralf = resolve_roles(['idle', 'walk', 'pain', 'fall', 'rise', 'attack1', 'upper'])
    check('RALF attack2 == upper ordinal', ralf['attack2'] == 6, ralf)
    check('RALF upper mirrors attack2', ralf.get('upper') == 6, ralf)

    # -- JOE: real second move is a literal 'grab' anim -- attack2_is_grab
    # must stay True (existing, previously-verified behavior).
    joe = resolve_roles(['idle', 'walk', 'pain', 'fall', 'rise', 'attack1', 'grab'])
    check('JOE attack2 is grab', joe['attack2'] == 6, joe)
    check('JOE attack2_is_grab True', joe['attack2_is_grab'] is True, joe)

    # -- JHUN: real second move is 'jumpattack', but JHUN has no 'jump' --
    # must still resolve to attack2 (ground move, not a real jump-attack).
    jhun = resolve_roles(['idle', 'walk', 'pain', 'fall', 'rise', 'attack1', 'jumpattack'])
    check('JHUN attack2 is jumpattack (no real jump)', jhun['attack2'] == 6, jhun)
    check('JHUN jumpattack role also set', jhun.get('jumpattack') == 6, jhun)

    # -- LEATHER: real second move is 'upper' with a real 'riseattack'
    # ALSO present -- riseattack must not get swallowed by attack2, and
    # upper must still resolve correctly (real bug this project already
    # fixed once; guards against regressing it back).
    leather = resolve_roles(
        ['idle', 'walk', 'pain', 'fall', 'rise', 'riseattack', 'attack1', 'upper'])
    check('LEATHER riseattack stays riseattack', leather['riseattack'] == 5, leather)
    check('LEATHER attack2 is upper (not riseattack)', leather['attack2'] == 7, leather)

    # -- FOOT01/FOOT02 shape: literal 'attack2' AND 'attack3' AND a
    # separate 'upper'. The real bug's second half: 'upper' must NOT
    # regress attack2 (which must stay the literal 'attack2' anim), must
    # NOT be silently absorbed into attack3, and must be recorded (for
    # audit completeness) as excluded from attack2's own fallback pool --
    # proven content-inapplicable by source (see convert_character.py's
    # own long comment), not merely omitted.
    foot01 = resolve_roles(
        ['idle', 'walk', 'pain', 'fall', 'rise', 'attack1', 'attack2', 'attack3', 'upper'])
    check('FOOT01 attack2 stays literal attack2', foot01['attack2'] == 6, foot01)
    check('FOOT01 attack3 stays literal attack3', foot01['attack3'] == 7, foot01)
    check('FOOT01 upper recorded, distinct ordinal', foot01.get('upper') == 8, foot01)
    check('FOOT01 upper excluded from attack2', foot01['attack2'] != 8, foot01)

    # -- ROCK/BEBOP shape: literal 'attack2' with no attack3, plus 'upper'
    # -- same exclusion requirement as FOOT01/FOOT02, simpler anim set.
    rock = resolve_roles(
        ['idle', 'walk', 'pain', 'fall', 'rise', 'riseattack', 'attack1', 'attack2', 'upper'])
    check('ROCK attack2 stays literal attack2', rock['attack2'] == 7, rock)
    check('ROCK riseattack unaffected', rock['riseattack'] == 5, rock)
    check('ROCK upper recorded, excluded from attack2', rock.get('upper') == 8, rock)

    # -- LEO shape: 'waiting' declared before literal 'attack2' -- the
    # original real bug this fallback was first fixed for (regression
    # guard against ever picking 'waiting' as attack2 again).
    leo = resolve_roles(
        ['waiting', 'idle', 'slide', 'walk', 'get', 'jump', 'jumpattack', 'jumpattack2',
         'attack1', 'attack2', 'attack3', 'attack4', 'grab', 'throw', 'pain', 'fall',
         'rise', 'special', 'freespecial', 'grabattack', 'land'])
    check('LEO attack2 stays literal attack2 (not waiting)', leo['attack2'] == 9, leo)
    check('LEO grab is a real separate role (not swallowed by attack2)',
          leo['grab'] == 12, leo)

    # -- YASHIRO: no second move at all -- attack2 must stay None, not
    # accidentally pick up idle/walk/pain/fall/rise.
    yashiro = resolve_roles(['idle', 'walk', 'pain', 'fall', 'rise', 'attack1'])
    check('YASHIRO has no attack2', yashiro['attack2'] is None, yashiro)

    if FAILURES:
        print(f'FAIL: {len(FAILURES)} role-selection regression(s):')
        for f in FAILURES:
            print(f'  - {f}')
        return 1
    print('PASS: all role-selection regression checks clean')
    return 0


if __name__ == '__main__':
    sys.exit(main())
