#!/usr/bin/env python3
"""Single entry point for every static ROM-audit check this project uses,
re-seeded to actually cover oop-dispatched code.

Why this exists (see plan.md Part Two, section 2.2, "Tool A"): audit_jumps.py
and audit_ownership.py are normally seeded with the four boot entry points
(FC00 FF20 FF30 8000). Those seeds never reach anything dispatched through
core/oop.pasm's indirect `jsr (ClassPlay,x)` -- so Anim_Play,
Character_PlayFrame, Character_HitApply, CharacterEntity_Init,
CharacterEntity_Play (all of the entity-system code) went unaudited by every
previous invocation of these tools in this project's history. Their real
addresses move every build, so they're looked up by name from src/main.sym
rather than hardcoded here.

This script also asserts two things that have already broken silently in
this project:
  - Entity1_Base (a hand-maintained literal, since Poppy can't forward-
    reference CHAR_ZP_LEN) staying in sync with CHAR_ZP_LEN.
  - The gap between scpu_main_loop and nmi_handler staying positive (the
    fixed-.org-truncation class of bug).

Usage: python tools/rom_audit/audit_all.py
(no arguments -- paths are derived from this script's own location)
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)

from audit_jumps import disassemble  # noqa: E402
from audit_ownership import load_labels, find_owner, redo_call_edges  # noqa: E402

BIN_PATH = os.path.join(REPO_ROOT, 'src', 'main.bin')
SYM_PATH = os.path.join(REPO_ROOT, 'src', 'main.sym')
PASM_PATH = os.path.join(REPO_ROOT, 'src', 'main.pasm')
BASE = 0x8000

BOOT_SEED_NAMES_HEX = ['FC00', '8000']
BOOT_SEED_NAMES = ['nmi_handler', 'irq_handler']  # looked up by name, not
# hardcoded hex, same rationale as OOP_SEED_NAMES above: these addresses
# move as scpu_boot grows (already pushed at least twice in this project's
# history -- see CLAUDE.md's ".org truncation" note). The old hardcoded
# 'FF20'/'FF30' were a stale snapshot from an earlier push; growing
# scpu_boot further (Phase 10, plan.md 2.10) shifted what bytes now live at
# those addresses, and decoding a misaligned instruction stream from there
# walked off into a bogus jump target far past $FFFF, crashing this script
# with an IndexError instead of failing cleanly. Looking these up from
# main.sym means the seed always matches the CURRENT real entry points.
OOP_SEED_NAMES = [
    'Anim_Play',
    'Character_PlayFrame',
    'Character_HitApply',
    'Character_HitApply_VsEntity1',
    'Character_HitApply_VsEntity2',
    'Character_HitApply_VsEntity3',
    'Character_HitApply_VsPlayer',
    'CharacterEntity_Init',
    'CharacterEntity_Play',
]

SYM_LINE = re.compile(r'([0-9A-Fa-f]{2}):([0-9A-Fa-f]+)\s+(\S+)')


def parse_sym_by_name(sym_path):
    by_name = {}
    with open(sym_path, encoding='utf-8-sig') as f:
        for line in f:
            m = SYM_LINE.match(line.strip())
            if not m:
                continue
            bank, addr_s, name = m.groups()
            if bank != '00':
                continue
            addr = int(addr_s, 16)
            by_name.setdefault(name, addr)
    return by_name


def run_one_seed_set(label, entry_addrs, data, labels_sorted, addrs, label_by_addr):
    """Runs both the audit_jumps-style 'suspicious edge' check and the
    audit_ownership-style 'CALL target ownership' check against one
    disassembly walk, and returns True if this seed set is clean."""
    entries = [(a, 1, 1, False) for a in entry_addrs]
    real_addrs, call_edges, all_edges, unknown = redo_call_edges(data, BASE, entries)

    print(f'--- seed set: {label} ({len(entry_addrs)} entries) ---')
    print(f'Decoded {len(real_addrs)} real instruction addresses, '
          f'{len(all_edges)} control-flow edges, {len(call_edges)} CALL-class, '
          f'{len(unknown)} unknown opcodes')

    ok = True

    # audit_jumps-style: every edge must land on a real instruction, or on
    # NOP padding that falls through to one (this project's established
    # "nop guard" convention).
    suspicious = []
    for src, target, kind in all_edges:
        if target in real_addrs:
            continue
        found_ok = False
        for n in range(0, 8):
            t2 = target + n
            if t2 in real_addrs:
                found_ok = (n > 0) and all(
                    data[target + k - BASE] == 0xEA for k in range(n)
                )
                break
            if data[t2 - BASE] != 0xEA:
                break
        if not found_ok:
            suspicious.append((src, target, kind))
    if suspicious:
        ok = False
        print(f'{len(suspicious)} SUSPICIOUS edges (target not real, not nop-covered):')
        for src, target, kind in suspicious[:50]:
            print(f'  {kind} at {hex(src)} -> {hex(target)}')
    else:
        print('No suspicious edges.')

    # audit_ownership-style: every CALL-class target must land exactly on a
    # known label, not mid-body of some unrelated routine.
    violations = []
    for src, target, kind in call_edges:
        if target in label_by_addr:
            continue
        owner_addr, owner_names, _next_addr = find_owner(labels_sorted, addrs, target)
        violations.append((src, target, kind, owner_addr, owner_names))
    if violations:
        ok = False
        print(f'{len(violations)} OWNERSHIP VIOLATIONS:')
        for src, target, kind, owner_addr, owner_names in violations[:50]:
            if owner_addr is None:
                print(f'  {kind} at {hex(src)} -> {hex(target)}  BEFORE first known label')
            else:
                offset = target - owner_addr
                print(f'  {kind} at {hex(src)} -> {hex(target)}  '
                      f'{offset} bytes into {"/".join(owner_names)} (starts {hex(owner_addr)})')
    else:
        print('No ownership violations.')

    if unknown:
        ok = False
        print(f'{len(unknown)} unknown opcodes hit during walk (first 20):')
        for addr, op in unknown[:20]:
            print(f'  {hex(addr)}: {op:02X}')

    print()
    return ok, real_addrs


def run_verify_layout():
    """Runs verify_layout.py as a subprocess (it's a self-contained argv
    script with its own SystemExit(1)-on-unsafe behavior; not worth
    re-implementing its M1/M2/M3 drift model inline)."""
    print('--- verify_layout.py ---')
    result = subprocess.run(
        [sys.executable, os.path.join(HERE, 'verify_layout.py'), PASM_PATH, SYM_PATH],
        capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    print()
    return result.returncode == 0


def check_entity_base_sync(pasm_path):
    """Entity1_Base/Entity2_Base/Entity3_Base are hand-maintained literals
    (Poppy can't forward-reference CHAR_ZP_LEN -- see main.pasm's comment
    above Entity1_Base). Assert each is still exactly slot*CHAR_ZP_LEN."""
    entity_literals = {}
    char_zp_len = None
    with open(pasm_path, encoding='utf-8') as f:
        for line in f:
            m = re.match(r'\s*Entity([123])_Base\s*=\s*\$7[eE]0[aA]00\s*\+\s*(\d+)', line)
            if m:
                entity_literals[int(m.group(1))] = int(m.group(2))
            m2 = re.match(r'\s*CHAR_ZP_LEN\s*=\s*(\d+)', line)
            if m2:
                char_zp_len = int(m2.group(1))
    if char_zp_len is None:
        print('FAIL: could not find CHAR_ZP_LEN = N in main.pasm')
        return False
    ok = True
    for slot in (1, 2, 3):
        expected = slot * char_zp_len
        actual = entity_literals.get(slot)
        if actual is None:
            print(f'FAIL: could not find Entity{slot}_Base = $7E0a00 + N in main.pasm')
            ok = False
        elif actual != expected:
            print(f'FAIL: Entity{slot}_Base uses literal {actual} but '
                  f'{slot}*CHAR_ZP_LEN is {expected} -- these have drifted apart. '
                  f'Update the literal in Entity{slot}_Base\'s definition (main.pasm).')
            ok = False
        else:
            print(f'Entity{slot}_Base literal ({actual}) matches {slot}*CHAR_ZP_LEN ({expected}). OK.')
    return ok


def check_main_loop_margin(sym_by_name, real_addrs):
    loop_addr = sym_by_name.get('scpu_main_loop')
    nmi_addr = sym_by_name.get('nmi_handler')
    if loop_addr is None or nmi_addr is None:
        print('FAIL: scpu_main_loop or nmi_handler missing from main.sym')
        return False
    # No finer-grained label exists inside scpu_main_loop's body, so use the
    # last actually-decoded instruction address below nmi_handler as a proxy
    # for "where the real code ends" -- more accurate than the label address
    # alone, which only marks where the routine *starts*.
    candidates = [a for a in real_addrs if loop_addr <= a < nmi_addr]
    if not candidates:
        print('FAIL: no decoded instructions found between scpu_main_loop and nmi_handler')
        return False
    last_real = max(candidates)
    margin = nmi_addr - last_real
    print(f'scpu_main_loop last decoded instruction at {hex(last_real)}, '
          f'nmi_handler at {hex(nmi_addr)}: margin = {margin} bytes.')
    if margin <= 0:
        print('FAIL: margin is not positive -- scpu_main_loop has overrun into '
              'nmi_handler (the fixed-.org-truncation bug).')
        return False
    return True


def main():
    if not os.path.exists(BIN_PATH):
        print(f'FAIL: {BIN_PATH} does not exist -- run python build_rom.py first')
        raise SystemExit(1)

    sym_by_name = parse_sym_by_name(SYM_PATH)

    missing = [n for n in OOP_SEED_NAMES + BOOT_SEED_NAMES if n not in sym_by_name]
    if missing:
        print(f'FAIL: the following names are missing from {SYM_PATH}: {missing}')
        print('(they may have been renamed -- update OOP_SEED_NAMES/BOOT_SEED_NAMES in this script)')
        raise SystemExit(1)

    data = open(BIN_PATH, 'rb').read()
    labels_sorted = load_labels(SYM_PATH)
    addrs = [a for a, _ in labels_sorted]
    label_by_addr = dict(labels_sorted)

    all_ok = True

    boot_entries = [int(h, 16) for h in BOOT_SEED_NAMES_HEX] + \
        [sym_by_name[n] for n in BOOT_SEED_NAMES]
    ok, real_addrs_boot = run_one_seed_set(
        'boot entry points', boot_entries, data, labels_sorted, addrs, label_by_addr)
    all_ok &= ok

    oop_entries = [sym_by_name[n] for n in OOP_SEED_NAMES]
    ok, real_addrs_oop = run_one_seed_set(
        'oop-dispatched entry points', oop_entries, data, labels_sorted, addrs, label_by_addr)
    all_ok &= ok

    all_ok &= run_verify_layout()
    all_ok &= check_entity_base_sync(PASM_PATH)
    all_ok &= check_main_loop_margin(sym_by_name, real_addrs_boot | real_addrs_oop)

    print()
    if all_ok:
        print('ALL CHECKS PASS')
        raise SystemExit(0)
    else:
        print('FAILURES ABOVE -- see output')
        raise SystemExit(1)


if __name__ == '__main__':
    main()
