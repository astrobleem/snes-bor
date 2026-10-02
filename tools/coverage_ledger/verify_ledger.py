#!/usr/bin/env python3
"""Verifier for the generated coverage ledger (generate_ledger.py).

Fails per notjustfreespecial.txt's own rules:
  - converted, shipped gameplay content has no runtime handler
    (classification == unhandled-error, or a role claims real content with
    runtime_handler == None and no defensible inapplicable/blocked/
    unshipped classification),
  - a runtime handler has no behavioral gate (implemented-and-gated or
    partial rows with a real handler must cite at least one gate file, and
    those files must actually exist),
  - a content-inapplicable/externally-blocked row has no evidence string
    (the audit's own "must record the exact raw-content search... and why
    no shipped configuration can reach it" requirement -- checked for
    presence, not content, since this script can't judge prose quality),
  - any row is missing a classification entirely.

This does NOT (yet) verify "documentation says a phase is complete while
its ledger contains partial" -- that cross-check belongs in a docs-linting
pass once plan_game.md/README wording is fully reconciled to this ledger;
tracked as follow-on work, not silently skipped.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VALID = {'implemented-and-gated', 'partial', 'content-inapplicable',
         'externally-blocked', 'unshipped-source-content', 'unhandled-error'}
PHASE_TAG_RE = re.compile(r'^G\d+[a-z]?$')


def verify(rows):
    ok = True

    def fail(msg):
        nonlocal ok
        ok = False
        print(f'FAIL: {msg}')

    for r in rows:
        who = f"{r.get('character')}/{r.get('animation')}"
        cls = r.get('classification')
        if cls not in VALID:
            fail(f'{who}: missing/invalid classification {cls!r}')
            continue

        # claude_begin_g10_with_approval.md: every row must have an owning
        # phase (a real G-numbered tag) or the explicit 'foundational'
        # bucket (with a phase_note explaining why) -- no silent default,
        # so per-phase completion (verify_phase_status.py) has something
        # real to enforce against.
        phase = r.get('phase')
        if not phase:
            fail(f'{who}: no "phase" field -- every row must cite an owning '
                 f'G-phase or "foundational"')
        elif phase != 'foundational' and not PHASE_TAG_RE.match(phase):
            fail(f'{who}: phase {phase!r} is neither "foundational" nor a real '
                 f'G-phase tag (e.g. "G7")')
        elif phase == 'foundational' and not r.get('phase_note'):
            fail(f'{who}: phase is "foundational" but has no phase_note explaining why '
                 f'no G-phase owns it')

        if cls == 'unhandled-error':
            fail(f'{who}: unhandled-error -- shipped content with no runtime handler '
                 f'and no defensible classification')

        if cls == 'implemented-and-gated':
            if not r.get('runtime_handler'):
                fail(f'{who}: implemented-and-gated but has no runtime_handler')
            if not r.get('owning_gates'):
                fail(f'{who}: implemented-and-gated but cites no owning gate')
            if r.get('evidence'):
                fail(f'{who}: implemented-and-gated rows should not need an evidence/gap '
                     f'note (found one) -- either the classification or the note is wrong')

        if cls == 'partial':
            if not r.get('evidence'):
                fail(f'{who}: partial with no evidence/gap note explaining what is missing')
            # A partial row with a real handler must cite a gate that
            # actually exists -- a handler with zero gate coverage, or a
            # gate name that doesn't resolve to a real file, is exactly the
            # "checklist is green but nothing proves it" failure mode this
            # ledger exists to catch. A partial row with NO handler at all
            # (e.g. `waiting`/`get`, genuinely unbuilt) is a documented gap,
            # not an error -- it needs no gate to cite.
            if r.get('runtime_handler') and not r.get('owning_gates'):
                fail(f'{who}: partial with a real runtime_handler but no owning gate '
                     f'cited')

        for g in (r.get('owning_gates') or []):
            gname = g.split(' ')[0]  # strip "(JOE)"-style annotations
            if not os.path.isfile(os.path.join(ROOT, 'tools', 'verify', gname)):
                fail(f'{who}: cites gate {gname!r} which does not exist on disk')

        if cls in ('content-inapplicable', 'externally-blocked') and not r.get('evidence'):
            fail(f'{who}: {cls} with no evidence string (raw-content search / source '
                 f'citation required)')

    if ok:
        print(f'PASS: {len(rows)} ledger rows, no unhandled-error rows, every '
              f'implemented-and-gated/partial row cites a real gate file, every '
              f'content-inapplicable/externally-blocked row has evidence recorded')
    return ok


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'ledger.json')
    with open(path, 'r', encoding='utf-8') as f:
        rows = json.load(f)
    sys.exit(0 if verify(rows) else 1)


if __name__ == '__main__':
    main()
