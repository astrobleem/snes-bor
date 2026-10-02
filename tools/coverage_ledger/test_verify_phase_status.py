#!/usr/bin/env python3
"""claude_begin_g10_with_approval.md: "Add regression coverage proving the
verifier catches" the 3 named per-phase scenarios. Not a pytest suite (this
project has no test framework, per CLAUDE.md) -- a standalone script with
the same Reporter-free PASS/FAIL-and-exit-nonzero convention
verify_phase_status.py itself uses, callable directly:

    python tools/coverage_ledger/test_verify_phase_status.py

Exercises verify_core() (the pure, file-I/O-free function) with synthetic
phase_status/ledger_rows/plan_text so it never touches the real project
files -- these are unit tests of the checker's OWN logic, not a live gate
against real project state (real project state is checked by running
verify_phase_status.py itself).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify_phase_status import verify_core  # noqa: E402

PLAN_TEXT = ''  # no plan_game.md markers involved in any of these cases


def row(phase, classification='partial', character='TEST', animation='thing'):
    return {'character': character, 'animation': animation, 'phase': phase,
            'classification': classification}


def check(name, expect_pass, phase_status, ledger_rows):
    silence = []
    ok = verify_core(phase_status, ledger_rows, PLAN_TEXT, report=silence.append)
    got = 'PASS' if ok else 'FAIL'
    want = 'PASS' if expect_pass else 'FAIL'
    status = 'PASS' if got == want else 'FAIL'
    print(f'{status}: {name} (expected verify_core to {want}, got {got})')
    if status == 'FAIL':
        for line in silence:
            print(f'    {line}')
    return status == 'PASS'


def main():
    results = []

    # 1. G10 marked done with a G10 partial row -- must fail.
    results.append(check(
        'G10 done with a G10 partial row fails',
        expect_pass=False,
        phase_status={'G10': 'done'},
        ledger_rows=[row('G10', 'partial')],
    ))

    # 2. G7 done with a G7 partial row -- must fail.
    results.append(check(
        'G7 done with a G7 partial row fails',
        expect_pass=False,
        phase_status={'G7': 'done'},
        ledger_rows=[row('G7', 'partial')],
    ))

    # 3. G7 done while only G10 has a partial row -- must NOT fail G7 (the
    # exact per-phase isolation this whole verifier fix exists to add).
    results.append(check(
        'G7 done while only G10 has a partial row does not fail',
        expect_pass=True,
        phase_status={'G7': 'done', 'G10': 'partial'},
        ledger_rows=[row('G10', 'partial')],
    ))

    # Bonus: unhandled-error behaves the same as partial for this check.
    results.append(check(
        'G8 done with a G8 unhandled-error row fails',
        expect_pass=False,
        phase_status={'G8': 'done'},
        ledger_rows=[row('G8', 'unhandled-error')],
    ))

    # Bonus: a row citing a phase phase_status.json doesn't know about is
    # itself a failure (catches a stale/typo'd phase tag).
    results.append(check(
        'ledger row citing an unknown phase tag fails',
        expect_pass=False,
        phase_status={'G7': 'done'},
        ledger_rows=[row('G99', 'implemented-and-gated')],
    ))

    # Bonus: 'foundational' rows never poison any phase.
    results.append(check(
        'foundational rows never poison a done phase',
        expect_pass=True,
        phase_status={'G7': 'done'},
        ledger_rows=[row('foundational', 'partial')],
    ))

    if all(results):
        print(f'\nPASS: all {len(results)} verify_phase_status.py regression cases behaved '
              f'as expected')
        return 0
    print(f'\nFAIL: {sum(1 for r in results if not r)}/{len(results)} regression cases '
          f'did not behave as expected')
    return 1


if __name__ == '__main__':
    sys.exit(main())
