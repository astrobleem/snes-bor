#!/usr/bin/env python3
"""Detect Poppy bug #4 (label address off-by-N) by opcode agreement.

WHY THIS AND NOT A BOUNDARY CHECK
---------------------------------
tools/rom_audit's other checks verify that decoded bytes land on real
instruction/label boundaries. That check is structurally blind to this bug:
a drifted label very often lands squarely on a *valid* instruction, just the
wrong one. Both confirmed Phase 7 blockers did exactly that --
`Tad_LoadSong__SongRequested` resolved onto a perfectly well-formed `bra`,
and `TadPrivate_Process_Loading` onto the previous routine's `rtl`. The
audit returned ALL CHECKS PASS across a ROM whose audio driver could not
load a single byte.

What actually discriminates is much simpler: read the source line that
follows a label, and assert the byte at that label's address is an opcode
for that mnemonic. `TadPrivate_Process_Loading:` is followed by `jsr`, so
the byte there must be $20 or $FC; it was $6B (rtl). Caught.

A `nop` ($EA) at the label counts as OK -- that is this codebase's standing
workaround, deliberately placed so an early-landing branch falls through
into the real instruction.

SCOPE -- read this before trusting a clean result
-------------------------------------------------
Drift accumulates *within* a fixed `.org` region and resets at the next one
(measured: both $8800 and $AC00 re-entered at drift 0). So every `.org`
region accrues independently and a clean sweep of one says nothing about
the others. This defaults to the whole ROM ($8000-$FFFF) for that reason;
narrow it with --start/--end only when you already know where you're
looking.

`source_labels()` follows `.include` directives, so labels defined in
src/core/*.pasm (which land in the $C100 region) are covered too. Without
that, "0 DRIFTED over $C100-$FBFF" would have meant only "0 among
main.pasm's own labels there" -- far less than it appears to say.

Usage:
    python tools/rom_audit/check_label_drift.py [--start $8000] [--end $FFFF]

Exit status is 1 if any label disagrees, so this can gate a build.
"""
import argparse
import os
import re
import sys

# opcode -> mnemonic, full 65816 table.
OPCODES = [
    'BRK', 'ORA', 'COP', 'ORA', 'TSB', 'ORA', 'ASL', 'ORA',
    'PHP', 'ORA', 'ASL', 'PHD', 'TSB', 'ORA', 'ASL', 'ORA',
    'BPL', 'ORA', 'ORA', 'ORA', 'TRB', 'ORA', 'ASL', 'ORA',
    'CLC', 'ORA', 'INC', 'TCS', 'TRB', 'ORA', 'ASL', 'ORA',
    'JSR', 'AND', 'JSL', 'AND', 'BIT', 'AND', 'ROL', 'AND',
    'PLP', 'AND', 'ROL', 'PLD', 'BIT', 'AND', 'ROL', 'AND',
    'BMI', 'AND', 'AND', 'AND', 'BIT', 'AND', 'ROL', 'AND',
    'SEC', 'AND', 'DEC', 'TSC', 'BIT', 'AND', 'ROL', 'AND',
    'RTI', 'EOR', 'WDM', 'EOR', 'MVP', 'EOR', 'LSR', 'EOR',
    'PHA', 'EOR', 'LSR', 'PHK', 'JMP', 'EOR', 'LSR', 'EOR',
    'BVC', 'EOR', 'EOR', 'EOR', 'MVN', 'EOR', 'LSR', 'EOR',
    'CLI', 'EOR', 'PHY', 'TCD', 'JML', 'EOR', 'LSR', 'EOR',
    'RTS', 'ADC', 'PER', 'ADC', 'STZ', 'ADC', 'ROR', 'ADC',
    'PLA', 'ADC', 'ROR', 'RTL', 'JMP', 'ADC', 'ROR', 'ADC',
    'BVS', 'ADC', 'ADC', 'ADC', 'STZ', 'ADC', 'ROR', 'ADC',
    'SEI', 'ADC', 'PLY', 'TDC', 'JMP', 'ADC', 'ROR', 'ADC',
    'BRA', 'STA', 'BRL', 'STA', 'STY', 'STA', 'STX', 'STA',
    'DEY', 'BIT', 'TXA', 'PHB', 'STY', 'STA', 'STX', 'STA',
    'BCC', 'STA', 'STA', 'STA', 'STY', 'STA', 'STX', 'STA',
    'TYA', 'STA', 'TXS', 'TXY', 'STZ', 'STA', 'STZ', 'STA',
    'LDY', 'LDA', 'LDX', 'LDA', 'LDY', 'LDA', 'LDX', 'LDA',
    'TAY', 'LDA', 'TAX', 'PLB', 'LDY', 'LDA', 'LDX', 'LDA',
    'BCS', 'LDA', 'LDA', 'LDA', 'LDY', 'LDA', 'LDX', 'LDA',
    'CLV', 'LDA', 'TSX', 'TYX', 'LDY', 'LDA', 'LDX', 'LDA',
    'CPY', 'CMP', 'REP', 'CMP', 'CPY', 'CMP', 'DEC', 'CMP',
    'INY', 'CMP', 'DEX', 'WAI', 'CPY', 'CMP', 'DEC', 'CMP',
    'BNE', 'CMP', 'CMP', 'CMP', 'PEI', 'CMP', 'DEC', 'CMP',
    'CLD', 'CMP', 'PHX', 'STP', 'JML', 'CMP', 'DEC', 'CMP',
    'CPX', 'SBC', 'SEP', 'SBC', 'CPX', 'SBC', 'INC', 'SBC',
    'INX', 'SBC', 'NOP', 'XBA', 'CPX', 'SBC', 'INC', 'SBC',
    'BEQ', 'SBC', 'SBC', 'SBC', 'PEA', 'SBC', 'INC', 'SBC',
    'SED', 'SBC', 'PLX', 'XCE', 'JSR', 'SBC', 'INC', 'SBC',
]

# mnemonic -> every opcode that encodes it (any addressing mode)
BY_MNEMONIC = {}
for _op, _m in enumerate(OPCODES):
    BY_MNEMONIC.setdefault(_m, set()).add(_op)

# Poppy spellings that map onto a different canonical mnemonic.
ALIASES = {'JML': 'JML', 'JSL': 'JSL', 'BLT': 'BCC', 'BGE': 'BCS'}

NOP = 0xEA

LABEL_RE = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(?:;.*)?$')
# `NAME = value` is a constant, not a code label -- never treat it as one.
ASSIGN_RE = re.compile(r'^\s*[A-Za-z_][A-Za-z0-9_]*\s*=')
INSTR_RE = re.compile(r'^\s*([A-Za-z]{3})(?:\.[bwl])?\b')


def repo_root():
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


def load_symbols(sym_path):
    syms = {}
    with open(sym_path, encoding='utf-8-sig', errors='replace') as f:
        for line in f:
            m = re.match(r'\s*([0-9A-Fa-f]{2}):([0-9A-Fa-f]{4})\s+(\S+)', line)
            if m and int(m.group(1), 16) == 0:
                # first definition wins; Poppy repeats constants at 00:0000
                syms.setdefault(m.group(3), int(m.group(2), 16))
    return syms


INCLUDE_RE = re.compile(r'^\s*\.include\s+"([^"]+)"', re.I)


def source_labels(pasm_path, _seen=None):
    """Yield (label, mnemonic, line_no, srcfile) for every code label followed
    by an instruction. Directives, comments and stacked labels are skipped
    over, and `.include`d files are recursed into -- src/core/*.pasm defines
    ~half the labels in the $C100 region and they are invisible otherwise."""
    if _seen is None:
        _seen = set()
    pasm_path = os.path.abspath(pasm_path)
    if pasm_path in _seen or not os.path.exists(pasm_path):
        return []
    _seen.add(pasm_path)

    with open(pasm_path, encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

    here = os.path.dirname(pasm_path)
    rel = os.path.relpath(pasm_path, repo_root()).replace('\\', '/')

    out = []
    for i, raw in enumerate(lines):
        inc = INCLUDE_RE.match(raw)
        if inc:
            out.extend(source_labels(os.path.join(here, inc.group(1)), _seen))
            continue
        if ASSIGN_RE.match(raw):
            continue
        m = LABEL_RE.match(raw)
        if not m:
            continue
        label = m.group(1)
        for j in range(i + 1, min(i + 40, len(lines))):
            nxt = lines[j]
            stripped = nxt.strip()
            if not stripped or stripped.startswith(';'):
                continue
            if stripped.startswith('.'):
                # .a8/.i16/.org/.db ... -- a data directive means this is a
                # data label, so stop rather than mis-attributing an opcode.
                if re.match(r'^\.(db|dw|dl|incbin|org|bank)\b', stripped, re.I):
                    break
                continue
            if LABEL_RE.match(nxt):
                continue
            im = INSTR_RE.match(nxt)
            if im:
                out.append((label, im.group(1).upper(), i + 1, rel))
            break
    return out


def main():
    root = repo_root()
    ap = argparse.ArgumentParser()
    ap.add_argument('--start', default='0x8000')
    ap.add_argument('--end', default='0xFFFF')
    ap.add_argument('--pasm', default=os.path.join(root, 'src', 'main.pasm'))
    ap.add_argument('--sym', default=os.path.join(root, 'src', 'main.sym'))
    ap.add_argument('--bin', default=os.path.join(root, 'src', 'main.bin'))
    args = ap.parse_args()

    start = int(args.start, 0)
    end = int(args.end, 0)

    syms = load_symbols(args.sym)
    with open(args.bin, 'rb') as f:
        blob = f.read()

    def byte_at(addr):
        off = addr - 0x8000
        return blob[off] if 0 <= off < len(blob) else None

    checked = bad = guarded = 0
    problems = []

    for label, mnem, line_no, srcfile in source_labels(args.pasm):
        addr = syms.get(label)
        if addr is None or not (start <= addr <= end):
            continue
        mnem = ALIASES.get(mnem, mnem)
        expected = BY_MNEMONIC.get(mnem)
        if not expected:
            continue
        got = byte_at(addr)
        if got is None:
            continue
        checked += 1
        if got == NOP and mnem != 'NOP':
            guarded += 1
            continue
        if got in expected:
            continue
        # Recover the drift amount: scan forward for the first byte that
        # could actually be this mnemonic. That distance is how many `nop`
        # bytes the guard needs (k >= d makes the early-landing branch hit a
        # nop and fall through).
        drift = None
        for k in range(1, 8):
            b = byte_at(addr + k)
            if b is not None and b in expected:
                drift = k
                break
        bad += 1
        problems.append((label, addr, mnem, got, OPCODES[got], line_no, drift, srcfile))

    print(f'label-drift check  ${start:04X}-${end:04X}: '
          f'{checked} code labels, {guarded} nop-guarded, {bad} DRIFTED')
    if problems:
        print()
        for label, addr, mnem, got, gotm, line_no, drift, srcfile in problems:
            d = f'{drift}' if drift is not None else '?'
            print(f'  DRIFT  {label}  ({srcfile}:{line_no}, needs {d} nop)')
            print(f'         .sym says ${addr:04X}, byte there is ${got:02X} ({gotm}); '
                  f'source says `{mnem.lower()}`')
        print('\nFix: insert `nop` padding immediately BEFORE the label so an '
              'early-landing\nbranch falls through into the real instruction '
              '(see poppy bug #4 in CLAUDE.md).')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
