#!/usr/bin/env python3
"""claude_close_g7_g8_before_g10.md Part 4: repair the ledger verifier so a
phase cannot be declared complete while the ledger itself still has an
unfinished row, and so plan_game.md's own prose can't silently drift out of
sync with either the ledger or its own status marker.

tools/coverage_ledger/phase_status.json is the single authoritative,
machine-readable phase-status source this script trusts. It compares that
file against two things, both via deterministic marker/field parsing (no
natural-language understanding of the documentation corpus, per this
project's own explicit "do not attempt fuzzy validation" rule):

1. tools/coverage_ledger/ledger.json -- claude_begin_g10_with_approval.md's
   own "First: fix the remaining verifier imperfection" requirement: every
   ledger row now carries a real owning `phase` field (a G-numbered tag, or
   "foundational" for rows no G-phase owns -- see generate_ledger.py's
   ROLE_PHASE_MAP/LEVEL_KEYWORD_PHASE_MAP). This check is now PER PHASE: a
   phase marked "done" in phase_status.json must own zero `partial` or
   `unhandled-error` rows of ITS OWN. A partial/unhandled-error row owned
   by a different phase (G10 mid-development, say) does not poison any
   other phase's "done" claim -- this is the exact fix the prior global-
   only version of this check was missing. It still catches the case this
   file's own governing doc names as an example ("G8 complete while `get`
   remains partial"): `get` is owned by G8 in the phase map, so a `get` row
   left `partial` would fail G8 specifically, the same as it always did,
   just precisely now instead of by accident.

2. plan_game.md's own `> **Status: ...**` markers -- each `## §N — Phase
   GN` heading's FIRST following Status block (the file's own established
   convention: newer corrections are prepended above older, superseded
   ones, so first-found is current) is parsed for a leading DONE/PARTIAL/
   COMPLETE/NOT STARTED word and normalized, then compared against
   phase_status.json's claim for that same phase. A phase with no Status
   marker at all in plan_game.md (an unnumbered/not-yet-worked phase) is
   skipped, not treated as a contradiction -- silence isn't a claim.

This does NOT (yet) cross-check README.md's Current Status prose -- that
text is dense narrative, not a structured table, and turning it into one is
plan_game.md/README reconciliation work (Part 5), not something this
checker can honestly claim to validate without the fuzzy-prose parsing this
file's own docstring says not to do. Tracked as follow-on, not silently
skipped -- same honesty standard tools/coverage_ledger/verify_ledger.py's
own docstring already holds itself to.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEDGER_DIR = os.path.dirname(os.path.abspath(__file__))

STATUS_WORD_MAP = {
    'DONE': 'done',
    'COMPLETE': 'done',
    'PARTIAL': 'partial',
    'NOT STARTED': 'not_started',
}


def parse_plan_game_statuses(text):
    """Returns {phase_tag: normalized_status} for every `## §N — Phase GN`
    section that has at least one `> **Status: ...**` block. First block
    after a heading wins (plan_game.md's own newest-first convention)."""
    headings = list(re.finditer(r'^## §\S+ — Phase (G\d+[a-z]?)\b', text, re.M))
    result = {}
    for i, h in enumerate(headings):
        phase = h.group(1)
        start = h.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        section = text[start:end]
        m = re.search(r'> \*\*Status:\s*([^*]+)\*\*', section)
        if not m:
            continue
        raw = m.group(1).strip()
        norm = None
        raw_upper = raw.upper()
        # Longest keyword first so "NOT STARTED" doesn't fall through to a
        # shorter false match, and match anywhere near the front of the
        # block (some sections lead with a qualifier like "item/pickup
        # work COMPLETE as of..." rather than a bare status word).
        for word in sorted(STATUS_WORD_MAP, key=len, reverse=True):
            if word in raw_upper[:80]:
                norm = STATUS_WORD_MAP[word]
                break
        if norm is None:
            # An unrecognized leading word is itself worth flagging -- it
            # means either this parser or the doc's own convention drifted.
            result[phase] = ('unparseable', raw[:60])
        else:
            result[phase] = (norm, raw[:60])
    return result


def verify_core(phase_status, ledger_rows, plan_text, report=print):
    """Pure function (no file I/O) so regression tests can inject synthetic
    phase_status/ledger_rows/plan_text without touching real project files.
    Returns (ok, unfinished_rows) -- callers that only need pass/fail use
    the first element; verify() below prints the same summary line as
    before."""
    ok = True

    def fail(msg):
        nonlocal ok
        ok = False
        report(f'FAIL: {msg}')

    phase_status = {k: v for k, v in phase_status.items() if not k.startswith('_')}

    # claude_begin_g10_with_approval.md: per-phase, not global. A phase
    # marked "done" may own zero partial/unhandled-error ledger rows of its
    # OWN -- a row owned by a DIFFERENT phase (e.g. G10 mid-development)
    # must not poison this phase's "done" claim.
    unfinished = [r for r in ledger_rows
                  if r.get('classification') in ('partial', 'unhandled-error')]
    unfinished_by_phase = {}
    for r in unfinished:
        unfinished_by_phase.setdefault(r.get('phase'), []).append(r)

    for phase, claimed in phase_status.items():
        if claimed != 'done':
            continue
        owned = unfinished_by_phase.get(phase, [])
        for r in owned:
            who = f"{r.get('character')}/{r.get('animation')}"
            fail(f'{phase}: phase_status.json claims done, but ledger.json has an '
                 f'unfinished row OWNED BY {phase}: {who} ({r.get("classification")})')

    # A ledger row's phase field must itself be a phase phase_status.json
    # actually knows about ('foundational' is exempt -- it owns no phase by
    # design, see generate_ledger.py's own PHASE_FOUNDATIONAL doc). Catches
    # a typo'd or stale phase tag silently falling out of every check above.
    known_phases = set(phase_status) | {'foundational'}
    for r in ledger_rows:
        phase = r.get('phase')
        if phase and phase not in known_phases:
            who = f"{r.get('character')}/{r.get('animation')}"
            fail(f'{who}: ledger row cites phase {phase!r} which has no '
                 f'phase_status.json entry')

    doc_statuses = parse_plan_game_statuses(plan_text)

    for phase, claimed in phase_status.items():
        if phase not in doc_statuses:
            continue  # no marker in plan_game.md -- not a contradiction
        doc_norm, doc_raw = doc_statuses[phase]
        if doc_norm == 'unparseable':
            fail(f'{phase}: plan_game.md\'s Status marker doesn\'t start with a '
                 f'recognized word (DONE/COMPLETE/PARTIAL/NOT STARTED): {doc_raw!r}')
        elif doc_norm != claimed:
            fail(f'{phase}: phase_status.json says {claimed!r} but plan_game.md\'s '
                 f'own Status marker says {doc_norm!r} ({doc_raw!r})')

    for phase in doc_statuses:
        if phase not in phase_status:
            fail(f'{phase}: plan_game.md has a real Status marker but '
                 f'phase_status.json has no entry for it at all')

    if ok:
        report(f'PASS: {len(phase_status)} phases in phase_status.json, '
               f'{len(unfinished)} unfinished ledger rows (checked per-phase), '
               f'{len(doc_statuses)} plan_game.md phases with a Status marker, '
               f'all consistent')
    return ok


def verify():
    with open(os.path.join(LEDGER_DIR, 'phase_status.json'), 'r', encoding='utf-8') as f:
        phase_status = json.load(f)

    with open(os.path.join(LEDGER_DIR, 'ledger.json'), 'r', encoding='utf-8') as f:
        ledger_rows = json.load(f)

    with open(os.path.join(ROOT, 'plan_game.md'), 'r', encoding='utf-8') as f:
        plan_text = f.read()

    return verify_core(phase_status, ledger_rows, plan_text)


def main():
    sys.exit(0 if verify() else 1)


if __name__ == '__main__':
    main()
