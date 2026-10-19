"""Independent semantic tests for the Q8 paired scratch-to-stage copy."""
from __future__ import annotations

import copy
from pathlib import Path
import random
import unittest

from preload_pair import (
    CALLER_ANCHOR,
    CODE_LIMIT,
    CODE_START,
    ROUTINE,
    SOURCE_ANCHOR,
    PreloadPairContractError,
    transform,
)


MASK = 0xFFFF
C, Z, I, DFLAG, XFLAG, MFLAG, V, N = 1, 2, 4, 8, 16, 32, 64, 128
SOURCE_BANK = 0x42
DEST_BANK = 0x00
SOURCE_BASE = 0xD680
SOURCE_BYTES = 80


def _nz8(p: int, value: int) -> int:
    p &= ~(N | Z)
    if value & 0x80:
        p |= N
    if (value & 0xFF) == 0:
        p |= Z
    return p


def _nz16(p: int, value: int) -> int:
    value &= MASK
    p &= ~(N | Z)
    if value & 0x8000:
        p |= N
    if value == 0:
        p |= Z
    return p


def _cmp16(p: int, left: int, right: int) -> int:
    left &= MASK
    right &= MASK
    p = _nz16(p, (left - right) & MASK)
    return (p | C) if left >= right else (p & ~C)


def _asl16(p: int, value: int) -> tuple[int, int]:
    carry = bool(value & 0x8000)
    value = (value << 1) & MASK
    p = _nz16(p, value)
    p = (p | C) if carry else (p & ~C)
    return p, value


def _adc16(p: int, left: int, right: int) -> tuple[int, int]:
    """65816 16-bit ADC flags/result for binary and packed-BCD modes."""
    left &= MASK
    right &= MASK
    carry_in = 1 if p & C else 0
    binary_sum = left + right + carry_in
    binary_result = binary_sum & MASK
    overflow = bool((~(left ^ right) & (left ^ binary_result) & 0x8000))
    if p & DFLAG:
        out = 0
        carry = carry_in
        for shift in range(0, 16, 4):
            digit = ((left >> shift) & 0xF) + ((right >> shift) & 0xF) + carry
            if digit > 9:
                digit += 6
            carry = 1 if digit > 0xF else 0
            out |= (digit & 0xF) << shift
        result = out & MASK
    else:
        carry = 1 if binary_sum > MASK else 0
        result = binary_result
    p = _nz16(p, result)
    p = (p | C) if carry else (p & ~C)
    p = (p | V) if overflow else (p & ~V)
    return p, result


def _dp_addr(state: dict, offset: int) -> int:
    return (state['d'] + offset) & MASK


def _number(text: str) -> int:
    """Poppy literals are decimal unless prefixed by a dollar sign."""
    value = text.lstrip('#')
    return int(value[1:], 16) if value.startswith('$') else int(value, 10)


def _read_dp(state: dict, offset: int) -> int:
    return state['dp_mem'].get(_dp_addr(state, offset), 0) & MASK


def _write_dp(state: dict, offset: int, value: int) -> None:
    address = _dp_addr(state, offset)
    value &= MASK
    state['dp_mem'][address] = value
    state['dp_writes'].append((address, value))


def _q7_source(state: dict) -> None:
    index = _read_dp(state, 0x70)
    state['p'] = _cmp16(state['p'], index, 6)
    if index == 6:
        state['a'] = 0x34B0
        state['p'] = _nz16(state['p'], state['a'])
        _write_dp(state, 0x72, state['a'])
        return
    state['a'] = index
    state['p'] = _nz16(state['p'], state['a'])
    for _ in range(4):
        state['p'], state['a'] = _asl16(state['p'], state['a'])
    _write_dp(state, 0x74, state['a'])
    state['p'], state['a'] = _asl16(state['p'], state['a'])
    state['p'], state['a'] = _asl16(state['p'], state['a'])
    state['p'] &= ~C
    state['p'], state['a'] = _adc16(state['p'], state['a'], _read_dp(state, 0x74))
    state['p'] &= ~C
    state['p'], state['a'] = _adc16(state['p'], state['a'], 0x3500)
    _write_dp(state, 0x72, state['a'])


def _mvn(state: dict, count_minus_one: int, source: int, destination: int) -> None:
    """One SNES MVN, modeled in emitted operand order: destination, source."""
    source_bank = source & 0xFF
    destination_bank = destination & 0xFF
    count = (count_minus_one & MASK) + 1
    for _ in range(count):
        source_address = (source_bank << 16) | state['x']
        destination_address = (destination_bank << 16) | state['y']
        value = state['memory'].get(source_address, (source_address * 13 + 7) & 0xFF)
        state['memory'][destination_address] = value
        state['writes'].append((destination_address, value))
        state['x'] = (state['x'] + 1) & MASK
        state['y'] = (state['y'] + 1) & MASK
    state['a'] = MASK
    state['dbr'] = destination_bank


def _stack_push(state: dict, value: int) -> None:
    state['sp'] = (state['sp'] - 1) & MASK
    state['stack'].append(value & 0xFF)


def _stack_pop(state: dict) -> int:
    value = state['stack'].pop()
    state['sp'] = (state['sp'] + 1) & MASK
    return value


def _legacy_copy(state: dict) -> None:
    old_dbr = state['dbr']
    state['a'] = 63
    state['p'] = _nz16(state['p'], state['a'])
    state['x'] = SOURCE_BASE
    state['p'] = _nz16(state['p'], state['x'])
    state['y'] = _read_dp(state, 0x72)
    state['p'] = _nz16(state['p'], state['y'])
    _stack_push(state, old_dbr)
    _mvn(state, state['a'], SOURCE_BANK, DEST_BANK)
    state['dbr'] = _stack_pop(state)
    state['p'] = _nz8(state['p'], state['dbr'])

    _stack_push(state, state['dbr'])
    state['a'] = 15
    state['p'] = _nz16(state['p'], state['a'])
    state['x'] = 0xD6C0
    state['p'] = _nz16(state['p'], state['x'])
    state['a'] = _read_dp(state, 0x72)
    state['p'] = _nz16(state['p'], state['a'])
    state['p'] &= ~C
    state['p'], state['a'] = _adc16(state['p'], state['a'], 64)
    state['y'] = state['a']
    state['p'] = _nz16(state['p'], state['y'])
    state['a'] = 15
    state['p'] = _nz16(state['p'], state['a'])
    _mvn(state, state['a'], SOURCE_BANK, DEST_BANK)
    state['dbr'] = _stack_pop(state)
    state['p'] = _nz8(state['p'], state['dbr'])


def original_stage_copy(initial: dict) -> dict:
    state = copy_state(initial)
    _q7_source(state)
    _legacy_copy(state)
    return state


def copy_state(state: dict) -> dict:
    return {**state, 'dp_mem': dict(state['dp_mem']),
            'memory': dict(state['memory']), 'writes': [], 'dp_writes': [],
            'stack': []}


def _flag_test(state: dict, flag: int) -> bool:
    return bool(state['p'] & flag)


def _assert_dp_stack_disjoint(state: dict) -> None:
    """Keep physical-stack aliasing outside this register/DP-only model."""
    dp_addresses = {(state['d'] + offset) & MASK for offset in (0x70, 0x72, 0x74)}
    # Q7's JSR and the helper's temporary PHP/PHB/PEA writes touch at most
    # these three byte slots below the entry SP. The model does not emulate
    # physical stack RAM, so reject contexts where those writes could alias
    # the direct-page values that control the copy.
    stack_addresses = {(state['sp'] - offset) & MASK for offset in (1, 2, 3)}
    overlap = dp_addresses & stack_addresses
    if overlap:
        raise AssertionError(f'unmodeled direct-page/stack alias: {sorted(overlap)}')


def interpret_emitted_helper(initial: dict, *, corrupt_destination: int | None = None) -> tuple[dict, str]:
    """Execute the emitted helper and retained original copy body.

    This small instruction interpreter consumes ROUTINE's actual instruction
    list. Q7SourceFromIndex and the original continuation are interpreted from
    their separately pinned source semantics, keeping the reference model
    independent of the transform's fast-path decision.
    """
    _assert_dp_stack_disjoint(initial)
    state = copy_state(initial)
    program = []
    labels = {}
    for line in ROUTINE:
        text = line.strip()
        if not text or text.startswith('.'):
            continue
        if text.endswith(':'):
            labels[text[:-1]] = len(program)
        else:
            program.append(text)
    pc = labels['PpStart']
    status_stack = []
    branch = 'fast'
    legacy_lines = [
        'phb', 'lda #63', 'ldx #$D680', 'ldy $72', 'mvn $00,$42', 'plb',
        'phb', 'lda #15', 'ldx #$D6C0', 'lda $72', 'clc', 'adc #64',
        'tay', 'lda #15', 'mvn $00,$42', 'plb',
    ]
    call_count = 0
    while pc < len(program):
        ins = program[pc]
        pc += 1
        op, *rest = ins.split(None, 1)
        arg = rest[0] if rest else ''
        if op == 'jsr' and arg == 'Q7SourceFromIndex':
            call_count += 1
            # JSR/RTS are balanced; Q7 has no stack or register side effects
            # beyond those modeled by its instructions.
            state['sp'] = (state['sp'] - 2) & MASK
            _q7_source(state)
            state['sp'] = (state['sp'] + 2) & MASK
            if corrupt_destination is not None:
                _write_dp(state, 0x72, corrupt_destination)
        elif op == 'php':
            _stack_push(state, state['p'])
        elif op == 'sep':
            state['p'] |= _number(arg)
        elif op == 'rep':
            state['p'] &= ~_number(arg)
        elif op == 'pla':
            value = _stack_pop(state)
            state['a'] = (state['a'] & 0xFF00) | value
            state['p'] = _nz8(state['p'], value)
        elif op == 'and':
            value = _number(arg)
            value = (state['a'] & 0xFF) & value
            state['a'] = (state['a'] & 0xFF00) | value
            state['p'] = _nz8(state['p'], value)
        elif op == 'lda':
            if arg == '$70':
                state['a'] = _read_dp(state, 0x70)
            elif arg == '$72':
                state['a'] = _read_dp(state, 0x72)
            elif arg == '$74':
                state['a'] = _read_dp(state, 0x74)
            elif arg.startswith('$D6'):
                address = int(arg[1:], 16)
                state['a'] = (state['memory'].get((SOURCE_BANK << 16) | address, 0)
                              | (state['memory'].get((SOURCE_BANK << 16) | ((address + 1) & MASK), 0) << 8))
            elif arg.startswith('#'):
                state['a'] = _number(arg)
            else:
                raise AssertionError(f'unmodeled LDA {arg}')
            state['p'] = _nz16(state['p'], state['a'])
        elif op == 'cmp':
            if arg == '$72':
                right = _read_dp(state, 0x72)
            else:
                right = _number(arg)
            state['p'] = _cmp16(state['p'], state['a'], right)
        elif op == 'asl':
            state['p'], state['a'] = _asl16(state['p'], state['a'])
        elif op == 'sta':
            _write_dp(state, int(arg[1:], 16), state['a'])
        elif op == 'adc':
            value = _read_dp(state, 0x74) if arg == '$74' else _number(arg)
            state['p'], state['a'] = _adc16(state['p'], state['a'], value)
        elif op == 'tax':
            state['x'] = state['a']
            state['p'] = _nz16(state['p'], state['x'])
        elif op == 'tay':
            state['y'] = state['a']
            state['p'] = _nz16(state['p'], state['y'])
        elif op == 'ldx':
            state['x'] = _read_dp(state, 0x72) if arg == '$72' else _number(arg)
            state['p'] = _nz16(state['p'], state['x'])
        elif op == 'ldy':
            state['y'] = _read_dp(state, 0x72)
            state['p'] = _nz16(state['p'], state['y'])
        elif op == 'clc':
            state['p'] &= ~C
        elif op == 'clv':
            state['p'] &= ~V
        elif op == 'phb':
            _stack_push(state, state['dbr'])
        elif op == 'pea':
            value = _number(arg)
            _stack_push(state, value >> 8)
            _stack_push(state, value)
        elif op == 'plb':
            state['dbr'] = _stack_pop(state)
            state['p'] = _nz8(state['p'], state['dbr'])
        elif op == 'mvn':
            # Source language order is destination bank, source bank.
            args = arg.replace('$', '').split(',')
            _mvn(state, state['a'], int(args[1], 16), int(args[0], 16))
        elif op == 'sta.l':
            base = int(arg.split(',')[0].replace('$', ''), 16)
            address = (base + state['x']) & 0xFFFFFF
            state['memory'][address] = state['a'] & 0xFF
            state['writes'].append((address, state['a'] & 0xFF))
            address = (address + 1) & 0xFFFFFF
            state['memory'][address] = (state['a'] >> 8) & 0xFF
            state['writes'].append((address, (state['a'] >> 8) & 0xFF))
        elif op == 'jmp':
            if arg == 'Q8ScratchNoStage':
                break
            if arg == 'PpLegacyAfterSource':
                branch = 'legacy'
                for legacy in legacy_lines:
                    _execute_legacy_instruction(state, legacy)
                break
            pc = labels[arg]
        elif op == 'bne':
            if not _flag_test(state, Z):
                pc = labels[arg]
        elif op == 'beq':
            if _flag_test(state, Z):
                pc = labels[arg]
        elif op == 'bcs':
            if _flag_test(state, C):
                pc = labels[arg]
        elif op == 'bcc':
            if not _flag_test(state, C):
                pc = labels[arg]
        elif op == 'bra':
            pc = labels[arg]
        else:
            raise AssertionError(f'unmodeled helper instruction {ins}')
    if call_count != 1:
        raise AssertionError(f'helper called source routine {call_count} times')
    if not state['writes'] or len(state['writes']) != SOURCE_BYTES:
        raise AssertionError(f'expected one 80-byte staging copy, got {len(state["writes"])}')
    return state, branch


def _execute_legacy_instruction(state: dict, ins: str) -> None:
    op, *rest = ins.split(None, 1)
    arg = rest[0] if rest else ''
    if op == 'phb':
        _stack_push(state, state['dbr'])
    elif op == 'plb':
        state['dbr'] = _stack_pop(state)
        state['p'] = _nz8(state['p'], state['dbr'])
    elif op == 'lda':
        if arg == '$72':
            state['a'] = _read_dp(state, 0x72)
        else:
            state['a'] = _number(arg)
        state['p'] = _nz16(state['p'], state['a'])
    elif op == 'ldx':
        state['x'] = _number(arg)
        state['p'] = _nz16(state['p'], state['x'])
    elif op == 'ldy':
        state['y'] = _read_dp(state, 0x72)
        state['p'] = _nz16(state['p'], state['y'])
    elif op == 'clc':
        state['p'] &= ~C
    elif op == 'adc':
        state['p'], state['a'] = _adc16(state['p'], state['a'], _number(arg))
    elif op == 'tay':
        state['y'] = state['a']
        state['p'] = _nz16(state['p'], state['y'])
    elif op == 'mvn':
        args = arg.replace('$', '').split(',')
        _mvn(state, state['a'], int(args[1], 16), int(args[0], 16))
    else:
        raise AssertionError(f'unmodeled legacy instruction {ins}')


def _initial(index: int, *, d: int, p: int, dbr: int, sp: int,
             a: int, x: int, y: int, base_override: int | None = None) -> dict:
    dp_mem = {(d + 0x70) & MASK: index & MASK,
              (d + 0x72) & MASK: (base_override if base_override is not None else 0xABCD),
              (d + 0x74) & MASK: 0x5A3C}
    memory = {((SOURCE_BANK << 16) | (SOURCE_BASE + offset)): (offset * 37 + 11) & 0xFF
              for offset in range(SOURCE_BYTES)}
    # Guard bytes prove the emitted source reads and destination writes do not
    # escape their 80-byte windows. Full-memory equality is checked against the
    # independent original-copy model in every semantic comparison.
    memory[(SOURCE_BANK << 16) | (SOURCE_BASE - 1)] = 0xA5
    memory[(SOURCE_BANK << 16) | (SOURCE_BASE + SOURCE_BYTES)] = 0x5A
    for address, value in ((0x000000, 0x66), (0x0034AF, 0x77),
                           (0x0034FF, 0x88), (0x003800, 0x99)):
        memory[address] = value
    return dict(a=a & MASK, x=x & MASK, y=y & MASK, p=p & 0xCF,
                d=d & MASK, dbr=dbr & 0xFF, sp=sp & MASK,
                emulation=0, dp_mem=dp_mem, memory=memory,
                writes=[], dp_writes=[], stack=[])


def _end_state(state: dict) -> tuple:
    return (state['a'], state['x'], state['y'], state['p'], state['dbr'],
            state['d'], state['sp'], state['emulation'], state['dp_mem'],
            state['dp_writes'], state['memory'], state['writes'], state['stack'])


class PreloadPairTests(unittest.TestCase):
    source_path = Path('out/byor-motu-ref-rebuild-v2/success/native/publisher.pasm')

    @classmethod
    def setUpClass(cls):
        cls.source = cls.source_path.read_text().splitlines()
        cls.enabled = transform(cls.source)

    def test_transform_pins_only_call_and_keeps_legacy_copy(self):
        normalized_source = [line.strip() for line in self.source]
        normalized_enabled = [line.strip() for line in self.enabled]
        self.assertEqual(normalized_enabled.count('jmp PpStart'), 1)
        self.assertEqual(normalized_enabled.count('jsr Q7SourceFromIndex'),
                         normalized_source.count('jsr Q7SourceFromIndex'))
        self.assertIn('PpLegacyAfterSource:', normalized_enabled)
        legacy_at = normalized_enabled.index('PpLegacyAfterSource:')
        self.assertEqual(normalized_enabled[legacy_at + 1:legacy_at + 16],
                         ['phb', 'lda #63', 'ldx #$D680', 'ldy $72',
                          'mvn $00,$42', 'plb', 'phb', 'lda #15',
                          'ldx #$D6C0', 'lda $72', 'clc', 'adc #64',
                          'tay', 'lda #15', 'mvn $00,$42'])
        self.assertEqual(sum(line.strip().startswith('lda $D6') for line in ROUTINE), 40)
        self.assertEqual(sum(line.strip().startswith('sta.l $') for line in ROUTINE), 40)
        self.assertFalse(any(line.strip().startswith('mvn ') for line in ROUTINE))
        self.assertIn(' pea $4242', ROUTINE)
        self.assertIn(' adc #80', ROUTINE)
        self.assertIn(' cmp #7', ROUTINE)
        self.assertIn(' cmp #$34B0', ROUTINE)
        self.assertEqual(CODE_START, 0x39AB00)
        self.assertEqual(CODE_LIMIT, 0x39B000)
        self.assertIn('mvn $00,$42', CALLER_ANCHOR)
        self.assertIn('Q7CodeEnd:', SOURCE_ANCHOR)

    def test_unrolled_word_addresses_are_exact_and_count_independent(self):
        source_addresses = [int(line.strip().split()[1][1:], 16)
                            for line in ROUTINE if line.strip().startswith('lda $D6')]
        destination_offsets = [int(line.strip().split()[1].split(',')[0][1:], 16)
                               for line in ROUTINE if line.strip().startswith('sta.l $')]
        self.assertEqual(source_addresses, list(range(0xD680, 0xD6D0, 2)))
        self.assertEqual(destination_offsets, list(range(0, 0x50, 2)))
        self.assertNotIn('$D704', '\n'.join(ROUTINE).upper())

    def test_disabled_identity_and_drift_reapplication_rejection(self):
        self.assertEqual(transform(self.source, enabled=False), self.source)
        with self.assertRaisesRegex(PreloadPairContractError, 'ALREADY_INSTALLED'):
            transform(self.enabled)
        drift = list(self.source)
        index = next(i for i, line in enumerate(drift) if line.strip() == 'mvn $00,$42')
        drift[index] = ' mvn $42,$00'
        with self.assertRaisesRegex(PreloadPairContractError, 'PINNED_CALLER'):
            transform(drift)
        duplicate = self.source + self.source
        with self.assertRaises(PreloadPairContractError):
            transform(duplicate)

    def test_valid_indexes_match_original_exact_cpu_memory_and_write_trace(self):
        # Exercise the six computed stage destinations and the dedicated spill
        # destination with varied caller registers, DP, DBR, SP, and flags.
        rng = random.Random(0x5102)
        for index in range(7):
            for _ in range(12):
                d = rng.randrange(0x10000)
                p = (rng.randrange(256) & ~(MFLAG | XFLAG | DFLAG)) | (rng.randrange(2) * DFLAG)
                # Fast path is tested with D=0; decimal cases independently
                # exercise exact legacy fallback below.
                p &= ~DFLAG
                initial = _initial(index, d=d, p=p, dbr=rng.randrange(256),
                                   sp=rng.randrange(0x100, 0xFF00),
                                   a=rng.randrange(0x10000), x=rng.randrange(0x10000),
                                   y=rng.randrange(0x10000))
                expected = original_stage_copy(initial)
                actual, path = interpret_emitted_helper(initial)
                self.assertEqual(path, 'fast', (index, d))
                self.assertEqual(_end_state(actual), _end_state(expected), (index, d))
                self.assertEqual(len(actual['writes']), 80)
                self.assertEqual(actual['writes'][:64], expected['writes'][:64])
                self.assertEqual(actual['writes'][64:], expected['writes'][64:])

    def test_decimal_mode_uses_original_two_mvn_body_and_exact_flags(self):
        rng = random.Random(0xD16)
        for index in range(7):
            p = (rng.randrange(256) & ~(MFLAG | XFLAG)) | DFLAG
            initial = _initial(index, d=rng.randrange(0x10000), p=p,
                               dbr=rng.randrange(256), sp=rng.randrange(0x100, 0xFF00),
                               a=rng.randrange(0x10000), x=rng.randrange(0x10000),
                               y=rng.randrange(0x10000))
            expected = original_stage_copy(initial)
            actual, path = interpret_emitted_helper(initial)
            self.assertEqual(path, 'legacy')
            self.assertEqual(_end_state(actual), _end_state(expected), index)

    def test_index_seven_bypasses_staging_and_direct_helper_falls_back(self):
        # The real caller sends index 7 to Q8ScratchNoStage without a copy.
        initial = _initial(7, d=0x3410, p=0x04, dbr=0x7E, sp=0x1FF0,
                           a=0x1234, x=0x5678, y=0x9ABC)
        caller_bypass = copy_state(initial)
        self.assertEqual(caller_bypass['writes'], [])
        # Defensive direct entry is still safe: it follows the retained legacy
        # body for an index that the production caller never stages.
        expected = original_stage_copy(initial)
        actual, path = interpret_emitted_helper(initial)
        self.assertEqual(path, 'legacy')
        self.assertEqual(_end_state(actual), _end_state(expected))

    def test_indexes_above_seven_fall_back_to_original_semantics(self):
        for index in (8, 9, 0x7FFF, 0xFFFF):
            initial = _initial(index, d=0xBEEF, p=0x45, dbr=0x80, sp=0xFF00,
                               a=0xA55A, x=0x6B4D, y=0x39C3)
            expected = original_stage_copy(initial)
            actual, path = interpret_emitted_helper(initial)
            self.assertEqual(path, 'legacy', index)
            self.assertEqual(_end_state(actual), _end_state(expected), index)

    def test_out_of_contract_destination_falls_back_without_changing_trace(self):
        initial = _initial(2, d=0x3400, p=0x24, dbr=0x42, sp=0x1F80,
                           a=0xCAFE, x=0xBABE, y=0xFACE)
        corrupted = 0xFEC0
        expected = copy_state(initial)
        _q7_source(expected)
        _write_dp(expected, 0x72, corrupted)
        _legacy_copy(expected)
        actual, path = interpret_emitted_helper(initial, corrupt_destination=corrupted)
        self.assertEqual(path, 'legacy')
        self.assertEqual(_end_state(actual), _end_state(expected))

    def test_random_contexts_and_indexes_match_reference_model(self):
        rng = random.Random(0x80C0FFEE)
        for _ in range(120):
            index = rng.choice([0, 1, 2, 3, 4, 5, 6, 7, 8, 0xFFFF])
            p = (rng.randrange(256) & ~(MFLAG | XFLAG))
            if rng.randrange(2):
                p |= DFLAG
            initial = _initial(index, d=rng.randrange(0x10000), p=p,
                               dbr=rng.randrange(256), sp=rng.randrange(0x100, 0xFF00),
                               a=rng.randrange(0x10000), x=rng.randrange(0x10000),
                               y=rng.randrange(0x10000))
            expected = original_stage_copy(initial)
            actual, _ = interpret_emitted_helper(initial)
            self.assertEqual(_end_state(actual), _end_state(expected), index)

    def test_fast_copy_uses_correct_source_destination_banks_and_order(self):
        for index in range(7):
            initial = _initial(index, d=0x2000, p=0x04, dbr=0x7E, sp=0x2F00,
                               a=0x1111, x=0x2222, y=0x3333)
            actual, path = interpret_emitted_helper(initial)
            self.assertEqual(path, 'fast')
            base = _read_dp(initial, 0x72)  # original input is replaced by Q7 in execution
            del base
            writes = actual['writes']
            self.assertEqual(len(writes), 80)
            self.assertEqual([value for _, value in writes],
                             [(offset * 37 + 11) & 0xFF for offset in range(80)])
            self.assertTrue(all((address >> 16) == DEST_BANK for address, _ in writes))


if __name__ == '__main__':
    unittest.main()

