#!/usr/bin/env python3
"""Whole-file JSR/JSL/JMP/JML/branch target integrity auditor for main.bin.

Does a real state-tracking (m/x width, native-mode) recursive-descent walk
of the actual instruction stream starting from a set of known entry points,
rather than scanning raw bytes for opcode-like values (which would produce
false positives from data bytes). For every JSR/JSL/JMP/JML (absolute forms
only -- indirect forms aren't statically resolvable) and every conditional/
unconditional branch encountered, records the real return-address-relative
target and checks whether that target lands exactly on a real decoded
instruction boundary -- or, if not, whether the bytes between the target and
the nearest following real instruction are all NOP ($EA), which is this
project's established, safe "falls through" pattern. Anything else is
flagged as a genuine drift bug (the same class that broke the abandoned
TAD-gap attempt -- see handoff.md).

Usage: python audit_jumps.py <main.bin path> <entry_addr_hex> [<entry_addr_hex> ...]
Example (this project's real entry points):
    python audit_jumps.py src/main.bin FC00 FF00 FF10 8000

KNOWN LIMITATION (found during the facing-flip session, not yet fixed):
this checker only verifies that a target address is a genuinely real,
validly-decoded instruction -- it does NOT catch the case where a target
is a real instruction that belongs to a DIFFERENT routine than the caller
intended (e.g. a `jsr Foo` landing mid-body of some unrelated `Bar`,
re-entering Bar's tail code instead of Foo's real entry). That exact
collision is what broke the abandoned TAD-gap attempt; this tool's basic
"real address" check does not flag it (see audit_ownership.py, sketched in
that session, which tried to add per-routine ownership tracking but hit
non-determinism from routines called with different m/x states from
different call sites -- not fully reliable yet, not included here). If a
new ROM region behaves strangely at runtime despite this tool reporting
clean, don't assume it's proven safe -- corroborate with the raw-byte
blob/immediate checks (see handoff.md's verification pattern) and real
Mesen behavioral testing before trusting a "0 suspicious edges" result.
"""
import sys

# opcode -> (mnemonic, size_class)
# size_class: fixed int, or 'm' (2 if m=8 else 3), or 'x' (2 if x=8 else 3)
OPTABLE = {
    0x00: ('BRK', 2), 0x01: ('ORA', 2), 0x02: ('COP', 2), 0x03: ('ORA', 2),
    0x04: ('TSB', 2), 0x05: ('ORA', 2), 0x06: ('ASL', 2), 0x07: ('ORA', 2),
    0x08: ('PHP', 1), 0x09: ('ORA', 'm'), 0x0A: ('ASL', 1), 0x0B: ('PHD', 1),
    0x0C: ('TSB', 3), 0x0D: ('ORA', 3), 0x0E: ('ASL', 3), 0x0F: ('ORA', 4),
    0x10: ('BPL', 2), 0x11: ('ORA', 2), 0x12: ('ORA', 2), 0x13: ('ORA', 2),
    0x14: ('TRB', 2), 0x15: ('ORA', 2), 0x16: ('ASL', 2), 0x17: ('ORA', 2),
    0x18: ('CLC', 1), 0x19: ('ORA', 3), 0x1A: ('INC', 1), 0x1B: ('TCS', 1),
    0x1C: ('TRB', 3), 0x1D: ('ORA', 3), 0x1E: ('ASL', 3), 0x1F: ('ORA', 4),
    0x20: ('JSR', 3), 0x21: ('AND', 2), 0x22: ('JSL', 4), 0x23: ('AND', 2),
    0x24: ('BIT', 2), 0x25: ('AND', 2), 0x26: ('ROL', 2), 0x27: ('AND', 2),
    0x28: ('PLP', 1), 0x29: ('AND', 'm'), 0x2A: ('ROL', 1), 0x2B: ('PLD', 1),
    0x2C: ('BIT', 3), 0x2D: ('AND', 3), 0x2E: ('ROL', 3), 0x2F: ('AND', 4),
    0x30: ('BMI', 2), 0x31: ('AND', 2), 0x32: ('AND', 2), 0x33: ('AND', 2),
    0x34: ('BIT', 2), 0x35: ('AND', 2), 0x36: ('ROL', 2), 0x37: ('AND', 2),
    0x38: ('SEC', 1), 0x39: ('AND', 3), 0x3A: ('DEC', 1), 0x3B: ('TSC', 1),
    0x3C: ('BIT', 3), 0x3D: ('AND', 3), 0x3E: ('ROL', 3), 0x3F: ('AND', 4),
    0x40: ('RTI', 1), 0x41: ('EOR', 2), 0x42: ('WDM', 2), 0x43: ('EOR', 2),
    0x44: ('MVP', 3), 0x45: ('EOR', 2), 0x46: ('LSR', 2), 0x47: ('EOR', 2),
    0x48: ('PHA', 1), 0x49: ('EOR', 'm'), 0x4A: ('LSR', 1), 0x4B: ('PHK', 1),
    0x4C: ('JMP', 3), 0x4D: ('EOR', 3), 0x4E: ('LSR', 3), 0x4F: ('EOR', 4),
    0x50: ('BVC', 2), 0x51: ('EOR', 2), 0x52: ('EOR', 2), 0x53: ('EOR', 2),
    0x54: ('MVN', 3), 0x55: ('EOR', 2), 0x56: ('LSR', 2), 0x57: ('EOR', 2),
    0x58: ('CLI', 1), 0x59: ('EOR', 3), 0x5A: ('PHY', 1), 0x5B: ('TCD', 1),
    0x5C: ('JML', 4), 0x5D: ('EOR', 3), 0x5E: ('LSR', 3), 0x5F: ('EOR', 4),
    0x60: ('RTS', 1), 0x61: ('ADC', 2), 0x62: ('PER', 3), 0x63: ('ADC', 2),
    0x64: ('STZ', 2), 0x65: ('ADC', 2), 0x66: ('ROR', 2), 0x67: ('ADC', 2),
    0x68: ('PLA', 1), 0x69: ('ADC', 'm'), 0x6A: ('ROR', 1), 0x6B: ('RTL', 1),
    0x6C: ('JMP', 3), 0x6D: ('ADC', 3), 0x6E: ('ROR', 3), 0x6F: ('ADC', 4),
    0x70: ('BVS', 2), 0x71: ('ADC', 2), 0x72: ('ADC', 2), 0x73: ('ADC', 2),
    0x74: ('STZ', 2), 0x75: ('ADC', 2), 0x76: ('ROR', 2), 0x77: ('ADC', 2),
    0x78: ('SEI', 1), 0x79: ('ADC', 3), 0x7A: ('PLY', 1), 0x7B: ('TDC', 1),
    0x7C: ('JMP', 3), 0x7D: ('ADC', 3), 0x7E: ('ROR', 3), 0x7F: ('ADC', 4),
    0x80: ('BRA', 2), 0x81: ('STA', 2), 0x82: ('BRL', 3), 0x83: ('STA', 2),
    0x84: ('STY', 2), 0x85: ('STA', 2), 0x86: ('STX', 2), 0x87: ('STA', 2),
    0x88: ('DEY', 1), 0x89: ('BIT', 'm'), 0x8A: ('TXA', 1), 0x8B: ('PHB', 1),
    0x8C: ('STY', 3), 0x8D: ('STA', 3), 0x8E: ('STX', 3), 0x8F: ('STA', 4),
    0x90: ('BCC', 2), 0x91: ('STA', 2), 0x92: ('STA', 2), 0x93: ('STA', 2),
    0x94: ('STY', 2), 0x95: ('STA', 2), 0x96: ('STX', 2), 0x97: ('STA', 2),
    0x98: ('TYA', 1), 0x99: ('STA', 3), 0x9A: ('TXS', 1), 0x9B: ('TXY', 1),
    0x9C: ('STZ', 3), 0x9D: ('STA', 3), 0x9E: ('STZ', 3), 0x9F: ('STA', 4),
    0xA0: ('LDY', 'x'), 0xA1: ('LDA', 2), 0xA2: ('LDX', 'x'), 0xA3: ('LDA', 2),
    0xA4: ('LDY', 2), 0xA5: ('LDA', 2), 0xA6: ('LDX', 2), 0xA7: ('LDA', 2),
    0xA8: ('TAY', 1), 0xA9: ('LDA', 'm'), 0xAA: ('TAX', 1), 0xAB: ('PLB', 1),
    0xAC: ('LDY', 3), 0xAD: ('LDA', 3), 0xAE: ('LDX', 3), 0xAF: ('LDA', 4),
    0xB0: ('BCS', 2), 0xB1: ('LDA', 2), 0xB2: ('LDA', 2), 0xB3: ('LDA', 2),
    0xB4: ('LDY', 2), 0xB5: ('LDA', 2), 0xB6: ('LDX', 2), 0xB7: ('LDA', 2),
    0xB8: ('CLV', 1), 0xB9: ('LDA', 3), 0xBA: ('TSX', 1), 0xBB: ('TYX', 1),
    0xBC: ('LDY', 3), 0xBD: ('LDA', 3), 0xBE: ('LDX', 3), 0xBF: ('LDA', 4),
    0xC0: ('CPY', 'x'), 0xC1: ('CMP', 2), 0xC2: ('REP', 2), 0xC3: ('CMP', 2),
    0xC4: ('CPY', 2), 0xC5: ('CMP', 2), 0xC6: ('DEC', 2), 0xC7: ('CMP', 2),
    0xC8: ('INY', 1), 0xC9: ('CMP', 'm'), 0xCA: ('DEX', 1), 0xCB: ('WAI', 1),
    0xCC: ('CPY', 3), 0xCD: ('CMP', 3), 0xCE: ('DEC', 3), 0xCF: ('CMP', 4),
    0xD0: ('BNE', 2), 0xD1: ('CMP', 2), 0xD2: ('CMP', 2), 0xD3: ('CMP', 2),
    0xD4: ('PEI', 2), 0xD5: ('CMP', 2), 0xD6: ('DEC', 2), 0xD7: ('CMP', 2),
    0xD8: ('CLD', 1), 0xD9: ('CMP', 3), 0xDA: ('PHX', 1), 0xDB: ('STP', 1),
    0xDC: ('JML', 3), 0xDD: ('CMP', 3), 0xDE: ('DEC', 3), 0xDF: ('CMP', 4),
    0xE0: ('CPX', 'x'), 0xE1: ('SBC', 2), 0xE2: ('SEP', 2), 0xE3: ('SBC', 2),
    0xE4: ('CPX', 2), 0xE5: ('SBC', 2), 0xE6: ('INC', 2), 0xE7: ('SBC', 2),
    0xE8: ('INX', 1), 0xE9: ('SBC', 'm'), 0xEA: ('NOP', 1), 0xEB: ('XBA', 1),
    0xEC: ('CPX', 3), 0xED: ('SBC', 3), 0xEE: ('INC', 3), 0xEF: ('SBC', 4),
    0xF0: ('BEQ', 2), 0xF1: ('SBC', 2), 0xF2: ('SBC', 2), 0xF3: ('SBC', 2),
    0xF4: ('PEA', 3), 0xF5: ('SBC', 2), 0xF6: ('INC', 2), 0xF7: ('SBC', 2),
    0xF8: ('SED', 1), 0xF9: ('SBC', 3), 0xFA: ('PLX', 1), 0xFB: ('XCE', 1),
    0xFC: ('JSR', 3), 0xFD: ('SBC', 3), 0xFE: ('INC', 3), 0xFF: ('SBC', 4),
}

BRANCHES_REL8 = {'BPL', 'BMI', 'BVC', 'BVS', 'BCC', 'BCS', 'BNE', 'BEQ', 'BRA'}
BRANCH_REL16 = {'BRL'}
# NOTE: 'JSR'/'JMP'/'JML' mnemonic strings are reused by BOTH the statically-
# resolvable absolute/long forms (0x20, 0x4C, 0x22, 0x5C) and the indirect
# forms (0x6C JMP(addr), 0x7C JMP(addr,X), 0xDC JML[addr], 0xFC JSR(addr,X) --
# the last one is exactly core/oop.pasm's class-dispatch indirect call).
# Distinguish by OPCODE BYTE, not mnemonic name, below.
ABS_CALL_OPCODES = {0x20, 0x4C}     # JSR addr, JMP addr
LONG_CALL_OPCODES = {0x22, 0x5C}    # JSL long, JML long
INDIRECT_JSR_OPCODES = {0xFC}       # JSR (addr,X) -- returns, but target unknown: no edge, just continue
INDIRECT_JMP_OPCODES = {0x6C, 0x7C, 0xDC}  # JMP (addr)/JMP (addr,X)/JML [addr] -- unknown target, control leaves: stop
STOP_MNEMONICS = {'RTS', 'RTI', 'RTL', 'BRK', 'STP', 'WAI'}


def size_of(mnemonic, size_class, m, x):
    if size_class == 'm':
        return 2 if m else 3
    if size_class == 'x':
        return 2 if x else 3
    return size_class


def disassemble(data, base, entries):
    """Recursive-descent walk. Returns (real_addrs: set, edges: list of
    (src_addr, target_addr, kind), unknown_opcodes: list)."""
    real_addrs = set()
    edges = []
    unknown = []
    # state stack: (addr, m, x, native)
    stack = list(entries)
    visited_states = set()

    while stack:
        addr, m, x, native = stack.pop()
        while True:
            if addr in real_addrs:
                break  # already walked this path
            off = addr - base
            if off < 0 or off >= len(data):
                break
            op = data[off]
            if op not in OPTABLE:
                unknown.append((addr, op))
                break
            mnemonic, size_class = OPTABLE[op]
            eff_m = 1 if not native else m
            eff_x = 1 if not native else x
            size = size_of(mnemonic, size_class, eff_m, eff_x)
            real_addrs.add(addr)

            if off + size > len(data):
                break

            operand = data[off + 1:off + size]

            new_m, new_x, new_native = m, x, native
            if mnemonic == 'SEP':
                imm = operand[0]
                if imm & 0x20: new_m = 1
                if imm & 0x10: new_x = 1
            elif mnemonic == 'REP':
                imm = operand[0]
                if imm & 0x20: new_m = 0
                if imm & 0x10: new_x = 0
            elif mnemonic == 'XCE':
                new_native = True  # this codebase only ever goes emulation->native

            next_addr = addr + size

            if mnemonic in STOP_MNEMONICS:
                break

            if mnemonic in BRANCHES_REL8:
                rel = operand[0]
                if rel >= 0x80:
                    rel -= 0x100
                target = next_addr + rel
                edges.append((addr, target, mnemonic))
                state_key = (target, new_m, new_x, new_native)
                if mnemonic != 'BRA' and state_key not in visited_states:
                    # conditional: also continue fallthrough
                    visited_states.add(state_key)
                    stack.append((target, new_m, new_x, new_native))
                elif mnemonic == 'BRA':
                    addr, m, x, native = target, new_m, new_x, new_native
                    continue
                if mnemonic != 'BRA':
                    addr, m, x, native = next_addr, new_m, new_x, new_native
                    continue
            elif mnemonic in BRANCH_REL16:
                rel = operand[0] | (operand[1] << 8)
                if rel >= 0x8000:
                    rel -= 0x10000
                target = next_addr + rel
                edges.append((addr, target, mnemonic))
                addr, m, x, native = target, new_m, new_x, new_native
                continue
            elif op in ABS_CALL_OPCODES:
                target = operand[0] | (operand[1] << 8)
                target += (addr & 0xFF0000)  # same bank
                edges.append((addr, target, mnemonic))
                if op == 0x4C:  # JMP addr
                    addr, m, x, native = target, new_m, new_x, new_native
                    continue
                else:  # JSR addr: continue after, and explore callee
                    state_key = (target, new_m, new_x, new_native)
                    if state_key not in visited_states:
                        visited_states.add(state_key)
                        stack.append((target, new_m, new_x, new_native))
            elif op in LONG_CALL_OPCODES:
                target = operand[0] | (operand[1] << 8) | (operand[2] << 16)
                edges.append((addr, target, mnemonic))
                if op == 0x5C:  # JML long
                    addr, m, x, native = target, new_m, new_x, new_native
                    continue
                else:  # JSL long: continue after, and explore callee
                    state_key = (target, new_m, new_x, new_native)
                    if state_key not in visited_states:
                        visited_states.add(state_key)
                        stack.append((target, new_m, new_x, new_native))
            elif op in INDIRECT_JSR_OPCODES:
                pass  # JSR (addr,X): target not statically known, but control returns here -- just continue
            elif op in INDIRECT_JMP_OPCODES:
                break  # JMP/JML indirect: target not statically known, control leaves for good

            addr, m, x, native = next_addr, new_m, new_x, new_native

    return real_addrs, edges, unknown


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(1)
    path = sys.argv[1]
    entry_addrs = [int(a, 16) for a in sys.argv[2:]]
    data = open(path, 'rb').read()
    base = 0x8000

    entries = [(a, 1, 1, False) for a in entry_addrs]
    real_addrs, edges, unknown = disassemble(data, base, entries)

    print(f'Decoded {len(real_addrs)} real instruction addresses, {len(edges)} control-flow edges, {len(unknown)} unknown opcodes')

    bad = []
    for src, target, kind in edges:
        if target in real_addrs:
            continue
        # check if target..target+N (small N) are all NOP and target+N is real
        ok = False
        for n in range(0, 8):
            t2 = target + n
            if t2 in real_addrs:
                ok = (n > 0) and all(data[target + k - base] == 0xEA for k in range(n))
                if ok:
                    bad.append((src, target, kind, 'drift=%d (nop-covered, OK)' % n))
                break
            if data[t2 - base] != 0xEA:
                break
        else:
            n = None
        if not ok:
            if not any(b[0] == src and b[1] == target for b in bad):
                bad.append((src, target, kind, 'UNRESOLVED/SUSPICIOUS'))

    suspicious = [b for b in bad if 'UNRESOLVED' in b[3]]
    covered = [b for b in bad if 'OK' in b[3]]
    print(f'{len(covered)} edges land 1+ bytes early but are nop-covered (fine)')
    print(f'{len(suspicious)} SUSPICIOUS edges (target not real, not nop-covered):')
    for src, target, kind, note in suspicious[:50]:
        print(f'  {kind} at {hex(src)} -> {hex(target)}  {note}')
    if unknown:
        print(f'{len(unknown)} unknown opcodes hit during walk (first 20):')
        for addr, op in unknown[:20]:
            print(f'  {hex(addr)}: {op:02X}')


if __name__ == '__main__':
    main()
