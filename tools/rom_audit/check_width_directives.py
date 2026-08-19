#!/usr/bin/env python3
"""Enforce an explicit M/X width directive at every branch/jump target that
runs a width-dependent immediate.

WHY THIS EXISTS
===============
poppy#386 is the one assembler bug this project still has to write around, and
it is deliberately unfixed both upstream and in the astrobleem fork: unlike the
five fixed on 2026-08-18, it needs a real control-flow analysis pass with a
false-positive budget rather than a reconciliation between two passes that
already disagree. See CLAUDE.md's toolchain section.

The bug: Poppy infers the 65816 accumulator/index width by walking the source
LINEARLY. A label reached by a branch that jumps OVER a `rep`/`sep` therefore
inherits the wrong width, and the first `lda #` / `cmp #` / `ldx #` after it is
sized wrong. Measured: `cmp #$02` at such a label assembles as `c9 02 00`; the
trailing `00` decodes as a phantom BRK and every byte after it misaligns.

The fix, and the rule this script enforces: **open every branch/jump target
label with an explicit width directive** -- `sep #$20` / `rep #$20` / `rep #$30`
or a bare `.a8` / `.a16` / `.i8` / `.i16` -- before the first width-dependent
immediate. It is a runtime no-op when the width already matches, so it gets
applied unconditionally rather than reasoned about case by case. That is
precisely why a human cannot be trusted to remember it: six recurrences in this
project before the mechanism was even understood.

WHAT IT FLAGS (and what it deliberately does not)
=================================================
A label is IN SCOPE when it is the target of a branch or jump somewhere in the
source (`bcc/bcs/beq/bne/bmi/bpl/bvc/bvs/bra/brl/jmp/jml/jsr/jsl`).
Fall-through labels are out of scope: the linear inference is correct for them
by definition.

A label FAILS when, scanning forward from it, a width-dependent immediate
(`lda #`, `cmp #`, `adc #`, `sbc #`, `and #`, `ora #`, `eor #`, `bit #`,
`ldx #`, `ldy #`, `cpx #`, `cpy #`) is reached before any explicit width
directive. `sep`/`rep` count as the directive, as do the bare `.a8`/`.a16`/
`.i8`/`.i16` assertions -- either one pins the width Poppy uses.

Scanning stops at the next label, at an `rts`/`rtl`/`rti`/`brk`/`jmp`/`jml`/
`bra`/`brl` (control leaves, so a later immediate belongs to some other path),
and at a data directive. A label whose first instruction is not width-dependent
is fine without a directive -- the rule is about the immediate, not the label.

This is a source-level lint. It cannot prove a given site is actually
mis-assembled -- only a CFG could -- so it errs toward the cheap, always-safe
directive. check_label_drift.py is the ground-truth counterpart: it reads the
emitted bytes and catches this bug's downstream misalignment after the fact.

BASELINE
========
Sites already in the tree when this check was written are listed in
check_width_directives_baseline.txt and reported as baselined, not failures.
The check fails on NEW violations only, so it can be wired into audit_all.py
without a flag day. Fixing a baselined site and dropping its line is always
welcome; --write-baseline regenerates the file after a bulk fix. Never add a
line to silence a new site -- add the directive instead.

Usage:
    python tools/rom_audit/check_width_directives.py [--write-baseline]
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
MAIN = os.path.join(ROOT, 'src', 'main.pasm')
BASELINE = os.path.join(HERE, 'check_width_directives_baseline.txt')

LABEL_RE = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(?:;.*)?$')
ASSIGN_RE = re.compile(r'^\s*[A-Za-z_][A-Za-z0-9_]*\s*=')
INCLUDE_RE = re.compile(r'^\s*\.include\s+"([^"]+)"', re.I)

BRANCH_OPS = ('bcc', 'bcs', 'beq', 'bne', 'bmi', 'bpl', 'bvc', 'bvs',
              'bra', 'brl', 'blt', 'bge', 'jmp', 'jml', 'jsr', 'jsl')
BRANCH_RE = re.compile(
    r'^\s*(' + '|'.join(BRANCH_OPS) + r')(?:\.[bwl])?\s+([A-Za-z_][A-Za-z0-9_]*)\s*$',
    re.I)

# Instructions whose immediate operand is sized by the M or X flag.
WIDTH_IMM_RE = re.compile(
    r'^\s*(lda|cmp|adc|sbc|and|ora|eor|bit|ldx|ldy|cpx|cpy)(?:\.[bwl])?\s+#', re.I)
# Anything that pins the width Poppy will use from here on.
WIDTH_DIR_RE = re.compile(r'^\s*(?:sep|rep)\s+#|^\s*\.(?:a8|a16|i8|i16)\b', re.I)
# Control leaves this straight-line run; a later immediate is on another path.
LEAVE_RE = re.compile(r'^\s*(rts|rtl|rti|brk|jmp|jml|bra|brl)\b', re.I)
DATA_RE = re.compile(
    r'^\s*\.(db|dw|dl|incbin|org|bank|ende|enum|macro|endmacro)\b', re.I)


def flatten(path, seen=None):
    """[(srcfile, lineno, text)] for main.pasm with .include's spliced in."""
    if seen is None:
        seen = set()
    path = os.path.abspath(path)
    if path in seen or not os.path.exists(path):
        return []
    seen.add(path)
    rel = os.path.relpath(path, ROOT).replace('\\', '/')
    here = os.path.dirname(path)
    out = []
    with open(path, encoding='utf-8', errors='replace') as f:
        for i, raw in enumerate(f, 1):
            inc = INCLUDE_RE.match(raw)
            if inc:
                out.extend(flatten(os.path.join(here, inc.group(1)), seen))
                continue
            out.append((rel, i, raw.rstrip('\n')))
    return out


def strip_comment(text):
    # No string literals occur on instruction lines in this codebase.
    return text.split(';', 1)[0].rstrip()


def scan(lines):
    """(violations, targeted_label_count); violation = (file, line, label, text)."""
    targets = set()
    for _f, _n, raw in lines:
        m = BRANCH_RE.match(strip_comment(raw))
        if m:
            targets.add(m.group(2))

    violations = []
    checked = 0
    for idx, (srcfile, lineno, raw) in enumerate(lines):
        if ASSIGN_RE.match(raw):
            continue
        m = LABEL_RE.match(raw)
        if not m or m.group(1) not in targets:
            continue
        checked += 1
        for j in range(idx + 1, min(idx + 60, len(lines))):
            nxt = strip_comment(lines[j][2])
            if not nxt.strip():
                continue
            if LABEL_RE.match(lines[j][2]):
                break                      # next label: this run ended clean
            if DATA_RE.match(nxt):
                break                      # data label, not a code path
            if WIDTH_DIR_RE.match(nxt):
                break                      # width pinned: correct by rule
            if WIDTH_IMM_RE.match(nxt):
                violations.append((srcfile, lineno, m.group(1), nxt.strip()))
                break
            if LEAVE_RE.match(nxt):
                break                      # control left before any immediate
    return violations, checked


def key(v):
    return f'{v[0]}:{v[2]}'


def main():
    lines = flatten(MAIN)
    if not lines:
        print(f'FAIL: could not read {MAIN}')
        return 1
    violations, checked = scan(lines)
    keys = sorted({key(v) for v in violations})

    if '--write-baseline' in sys.argv:
        with open(BASELINE, 'w', encoding='utf-8') as f:
            f.write('# poppy#386 width-directive baseline -- see check_width_directives.py.\n')
            f.write('# Sites already present when the check was added. Fixing one and\n')
            f.write('# deleting its line here is always welcome; NEVER add a line to\n')
            f.write('# silence a new site -- add the .a8/.a16 directive instead.\n')
            for k in keys:
                f.write(k + '\n')
        print(f'wrote {BASELINE} with {len(keys)} entries')
        return 0

    baseline = set()
    if os.path.exists(BASELINE):
        with open(BASELINE, encoding='utf-8') as f:
            baseline = {l.strip() for l in f if l.strip() and not l.startswith('#')}

    new = [v for v in violations if key(v) not in baseline]
    existing = [v for v in violations if key(v) in baseline]
    stale = baseline - set(keys)

    print(f'width-directive check (poppy#386): {checked} branch/jump-target labels, '
          f'{len(new)} NEW, {len(existing)} baselined, {len(stale)} baseline entries now clean')

    for v in new:
        print(f'  NEW  {v[0]}:{v[1]}  {v[2]}:  reaches "{v[3]}" with no explicit width directive')
    if new:
        print('\nAdd an explicit `sep #$20` / `.a8` (or `rep #$30` / `.a16 .i16`) '
              'immediately after each label above.\nIt is a runtime no-op when the '
              'width already matches -- see poppy#386 and CLAUDE.md.')
        return 1

    if stale:
        print('  (baseline entries that are now clean -- delete them: '
              + ', '.join(sorted(stale)) + ')')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
