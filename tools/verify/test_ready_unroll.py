"""Independent original-loop model and instruction interpreter for READY unroll."""
from __future__ import annotations

from pathlib import Path
import random
import unittest

import ready_validate as accepted
from ready_unroll import (
    CODE_LIMIT,
    CODE_START,
    ROUTINE,
    WORDS_PER_BLOCK,
    ReadyUnrollContractError,
    estimated_bytes,
    transform,
)


MASK16 = 0xFFFF
MAP_BASE = 0x42C000
BASE_SOURCE = Path('out/byor-motu-ref-rebuild-v2/success/native/publisher.pasm')


def _nz(p: int, value: int, bits: int = 16) -> int:
    p &= ~(0x80 | 0x02)
    value &= (1 << bits) - 1
    if value & (1 << (bits - 1)):
        p |= 0x80
    if value == 0:
        p |= 0x02
    return p


def _cmp(p: int, left: int, right: int) -> int:
    left &= MASK16
    right &= MASK16
    result = (left - right) & MASK16
    p = _nz(p, result)
    if left >= right:
        p |= 1
    else:
        p &= ~1
    return p


def _state(words: list[int], p: int = 0x35, y: int = 0x7654,
           sp: int = 0x1FF0, d: int = 0x3400, dbr: int = 0x39,
           a: int = 0x1234, x: int = 0x5678) -> dict:
    mem = {MAP_BASE + 2 * i: value & MASK16 for i, value in enumerate(words)}
    mem[0x42BFFE] = 0xA55A
    mem[0x42C800] = 0x5AA5
    return {
        'a': a & MASK16, 'x': x & MASK16, 'y': y & MASK16,
        'sp': sp & MASK16, 'd': d & MASK16, 'dbr': dbr & 0xFF,
        'p': p & 0xCF, 'mem': mem, 'dp70': 0,
        'stack': [], 'stack_writes': [], 'dp_writes': [],
        'writes': [], 'terminal': None,
    }


def _reference(words: list[int], **context) -> dict:
    """Execute accepted RvValidate's original serial 1024-word loop."""
    s = _state(words, **context)
    s['x'] = 0
    s['p'] = _nz(s['p'], 0)
    for offset in range(0, 2048, 2):
        s['x'] = offset
        s['p'] = _nz(s['p'], offset)
        raw = s['mem'][MAP_BASE + offset]
        s['a'] = raw
        s['p'] = _nz(s['p'], raw)
        if raw & 0x8000:
            s['a'] = 0x8000
            s['p'] = _nz(s['p'], s['a'])
            s['dp70'] = offset
            s['dp_writes'].append(('X', offset))
            s['terminal'] = 'NbAbort'
            return s
        s['a'] = raw & 0x3FFF
        s['p'] = _nz(s['p'], s['a'])
        s['p'] = _cmp(s['p'], s['a'], 768)
        if s['p'] & 1:
            s['dp70'] = offset
            s['dp_writes'].append(('X', offset))
            s['terminal'] = 'NbAbort'
            return s
        address = MAP_BASE + offset
        s['mem'][address] = s['a']
        s['writes'].append((address, s['a']))
        s['x'] = (s['x'] + 1) & MASK16
        s['p'] = _nz(s['p'], s['x'])
        s['x'] = (s['x'] + 1) & MASK16
        s['p'] = _nz(s['p'], s['x'])
        s['p'] = _cmp(s['p'], s['x'], 2048)
        if s['p'] & 1:
            s['x'] = 2046
            s['p'] = _nz(s['p'], s['x'])
            s['a'] = 2048
            s['p'] = _nz(s['p'], s['a'])
            s['dp70'] = s['a']
            s['dp_writes'].append(('A', s['a']))
            s['p'] = _cmp(s['p'], s['a'], 2048)
            s['terminal'] = 'RvContinue'
            return s
    raise AssertionError('original validator did not terminate')


def _run_emitted(words: list[int], routine=ROUTINE, **context) -> dict:
    """Interpret actual emitted opcodes, including status and stack effects."""
    s = _state(words, **context)
    code = [line.strip() for line in routine]
    labels = {line[:-1]: index for index, line in enumerate(code)
              if line.endswith(':')}
    pc = labels['RuValidate'] + 1
    steps = 0

    def push(value: int) -> None:
        s['stack_writes'].append((s['sp'], value & 0xFF))
        s['sp'] = (s['sp'] - 1) & MASK16
        s['stack'].append(value & 0xFF)

    def pull() -> int:
        s['sp'] = (s['sp'] + 1) & MASK16
        return s['stack'].pop()

    while steps < 50000:
        steps += 1
        op = code[pc]
        pc += 1
        if not op or op.startswith('.') or op.endswith(':'):
            continue
        if op == 'php':
            push(s['p'])
        elif op == 'phb':
            push(s['dbr'])
        elif op == 'pea $4242':
            # 65816 16-bit pushes put high byte first, then low byte.
            push(0x42)
            push(0x42)
        elif op == 'plb':
            s['dbr'] = pull()
            s['p'] = _nz(s['p'], s['dbr'], 8)
        elif op == 'plp':
            s['p'] = pull()
        elif op == 'cld':
            s['p'] &= ~0x08
        elif op == 'ldx #0':
            s['x'] = 0
            s['p'] = _nz(s['p'], s['x'])
        elif op == 'ldx #2046':
            s['x'] = 2046
            s['p'] = _nz(s['p'], s['x'])
        elif op == 'txa':
            s['a'] = s['x']
            s['p'] = _nz(s['p'], s['a'])
        elif op == 'tax':
            s['x'] = s['a']
            s['p'] = _nz(s['p'], s['x'])
        elif op == 'clc':
            s['p'] &= ~1
        elif op.startswith('adc #'):
            if s['p'] & 0x08:
                raise AssertionError('binary ADC model requires D clear')
            operand = int(op[5:], 0)
            left = s['a']; carry = s['p'] & 1
            result = left + operand + carry
            value = result & MASK16
            s['p'] = _nz(s['p'], value)
            if result > MASK16:
                s['p'] |= 1
            else:
                s['p'] &= ~1
            if (~(left ^ operand) & (left ^ value) & 0x8000):
                s['p'] |= 0x40
            else:
                s['p'] &= ~0x40
            s['a'] = value
        elif op.startswith('lda $') and op.endswith(',x'):
            operand = int(op[op.index('$') + 1:op.index(',')], 16)
            if s['dbr'] != 0x42:
                raise AssertionError('helper did not select bank $42')
            s['a'] = s['mem'][0x420000 + operand + s['x']]
            s['p'] = _nz(s['p'], s['a'])
        elif op == 'lda #$8000':
            s['a'] = 0x8000
            s['p'] = _nz(s['p'], s['a'])
        elif op == 'lda #2048':
            s['a'] = 2048
            s['p'] = _nz(s['p'], s['a'])
        elif op == 'and #$3FFF':
            s['a'] &= 0x3FFF
            s['p'] = _nz(s['p'], s['a'])
        elif op == 'and #$BFFF':
            s['a'] &= 0xBFFF
            s['p'] = _nz(s['p'], s['a'])
        elif op == 'cmp #768':
            s['p'] = _cmp(s['p'], s['a'], 768)
        elif op == 'cmp #2048':
            s['p'] = _cmp(s['p'], s['a'], 2048)
        elif op == 'cpx #2048':
            s['p'] = _cmp(s['p'], s['x'], 2048)
        elif op.startswith('bpl '):
            if not (s['p'] & 0x80):
                pc = labels[op[4:]] + 1
        elif op.startswith('bcc '):
            if not (s['p'] & 1):
                pc = labels[op[4:]] + 1
        elif op.startswith('bcs '):
            if s['p'] & 1:
                pc = labels[op[4:]] + 1
        elif op.startswith('beq '):
            if s['p'] & 0x02:
                pc = labels[op[4:]] + 1
        elif op == 'pha':
            push(s['a'] >> 8)
            push(s['a'])
        elif op == 'pla':
            lo = pull(); hi = pull()
            s['a'] = lo | (hi << 8)
            s['p'] = _nz(s['p'], s['a'])
        elif op.startswith('jmp '):
            target = op[4:]
            if target in ('NbAbort', 'RvContinue'):
                s['terminal'] = target
                break
            pc = labels[target] + 1
        elif op.startswith('sta $') and op.endswith(',x'):
            operand = int(op[op.index('$') + 1:op.index(',')], 16)
            if s['dbr'] != 0x42:
                raise AssertionError('helper did not select bank $42')
            address = 0x420000 + operand + s['x']
            s['mem'][address] = s['a']
            s['writes'].append((address, s['a']))
        elif op == 'stx $70':
            s['dp70'] = s['x']
            s['dp_writes'].append(('X', s['x']))
        elif op == 'sta $70':
            s['dp70'] = s['a']
            s['dp_writes'].append(('A', s['a']))
        else:
            raise AssertionError(f'unsupported emitted opcode: {op}')
    else:
        raise AssertionError('unrolled validator exceeded instruction bound')
    s['steps'] = steps
    return s


def _assert_same_result(test: unittest.TestCase, expected: dict, actual: dict) -> None:
    for key in ('a', 'x', 'y', 'sp', 'd', 'dbr', 'p', 'mem', 'dp70',
                'dp_writes', 'writes', 'terminal'):
        test.assertEqual(expected[key], actual[key], key)
    test.assertEqual([], actual['stack'])
    test.assertEqual(expected['sp'], actual['sp'])
    # The model proves stack balance and confines temporary writes below the
    # caller SP. It deliberately does not compare stale physical stack bytes:
    # PHP/PHB/PEA/PHA touch bytes that the legacy loop does not touch.
    writes = 4
    written = [address for address, _ in actual['stack_writes']]
    # PEA's two bytes are consumed while selecting DBR; the cold classifier
    # reloads the source word, so every terminal has only the four entry pushes.
    test.assertEqual(writes, len(written))
    test.assertEqual(expected['sp'] - 3, min(written))
    test.assertTrue(all(address <= expected['sp'] for address in written))
    test.assertNotIn((expected['d'] + 0x70) & MASK16, written,
                     'tested DP $70 must not alias temporary stack bytes')


class ReadyUnrollTests(unittest.TestCase):
    def _base(self) -> list[str]:
        return BASE_SOURCE.read_text().splitlines()

    def test_transform_pins_dispatch_and_preserves_original_body(self):
        base = self._base()
        result = transform(base)
        self.assertEqual(base, transform(base, enabled=False))
        start = [line.strip() for line in base].index('NbValidate:')
        rewritten = [line.strip() for line in result]
        self.assertEqual(['jmp RuValidate', 'nop', 'nop', 'nop'],
                         rewritten[start + 3:start + 7])
        original = [line.strip() for line in accepted.ROUTINE]
        self.assertEqual(1, sum(rewritten[i:i + len(original)] == original
                                for i in range(len(rewritten) - len(original) + 1)))
        self.assertEqual(ROUTINE, result[-len(ROUTINE):])

    def test_transform_rejects_drift_duplicates_and_reapplication(self):
        base = self._base()
        altered = base.copy()
        index = [line.strip() for line in altered].index('jmp RvValidate')
        altered[index] = 'jmp RvOther'
        modified_body = base.copy()
        index = [line.strip() for line in modified_body].index('RvValidateLoop:')
        modified_body[index + 1] = ' lda.l $42C002,x'
        for bad in (altered, modified_body, base + base, transform(base)):
            with self.assertRaises(ReadyUnrollContractError):
                transform(bad)

    def test_layout_branches_and_cold_fixups_fit_reserved_gap(self):
        self.assertEqual(911, estimated_bytes())
        self.assertLess(CODE_START + estimated_bytes(), CODE_LIMIT)
        lines = [line.strip() for line in ROUTINE]
        labels = {}; pc = 0; branches = []
        for line in lines:
            if not line or line.startswith('.'):
                continue
            if line.endswith(':'):
                labels[line[:-1]] = pc
                continue
            if line.startswith(('bpl ', 'bcc ', 'bcs ', 'beq ')):
                branches.append((pc, line.split()[1])); pc += 2
            else:
                pc += _asm_size(line)
        self.assertEqual(911, pc)
        self.assertEqual(35, len(branches))
        for branch_pc, target in branches:
            displacement = labels[target] - (branch_pc + 2)
            self.assertGreaterEqual(displacement, -128)
            self.assertLessEqual(displacement, 127)
        self.assertEqual('RuCodeEnd:', next(line.strip() for line in ROUTINE
                                             if line.strip() == 'RuCodeEnd:'))

    def test_every_tagged_and_untagged_invalid_slot_matches_original(self):
        rng = random.Random(0xA1F7)
        valid = [rng.randrange(768) | (0x4000 if rng.randrange(2) else 0)
                 for _ in range(1024)]
        for slot in range(1024):
            context = {'p': rng.randrange(256) & 0xCF, 'y': rng.randrange(65536),
                       'sp': rng.randrange(0x1000, 0x2000), 'd': 0x3400,
                       'dbr': rng.randrange(256), 'a': rng.randrange(65536),
                       'x': rng.randrange(65536)}
            for tagged in (True, False):
                words = valid.copy()
                words[slot] = (0x8000 | rng.randrange(768)) if tagged else (768 + rng.randrange(0x4000 - 768))
                with self.subTest(slot=slot, tagged=tagged):
                    _assert_same_result(self, _reference(words, **context),
                                        _run_emitted(words, **context))

    def test_success_masks_bit14_and_has_only_final_dp_write(self):
        words = [((i * 53) % 768) | (0x4000 if i % 3 else 0)
                 for i in range(1024)]
        words[0] = 0x4000; words[767] = 0x42FF
        context = {'p': 0xCD, 'y': 0xABCD, 'sp': 0x1FEE, 'd': 0x3400,
                   'dbr': 0x7E, 'a': 0x1111, 'x': 0x2222}
        expected = _reference(words, **context); actual = _run_emitted(words, **context)
        _assert_same_result(self, expected, actual)
        self.assertEqual(2048, actual['dp70'])
        self.assertEqual([('A', 2048)], actual['dp_writes'])
        self.assertEqual(1024, len(actual['writes']))
        self.assertEqual(0xA55A, actual['mem'][0x42BFFE])
        self.assertEqual(0x5AA5, actual['mem'][0x42C800])

    def test_tagged_slot_zero_preserves_both_entry_carry_values(self):
        words = [0] * 1024; words[0] = 0x8001
        for carry in (0, 1):
            context = {'p': (0xC4 | carry), 'y': 0x5A5A, 'sp': 0x1F00,
                       'd': 0x3400, 'dbr': 0x91, 'a': 0xABCD, 'x': 0x9876}
            _assert_same_result(self, _reference(words, **context),
                                _run_emitted(words, **context))

    def test_interpreter_rejects_decimal_adc_if_cld_is_removed(self):
        words = [0] * 1024
        without_cld = [line for line in ROUTINE if line.strip() != 'cld']
        context = {'p': 0x08, 'y': 0x1234, 'sp': 0x1800, 'd': 0x3400,
                   'dbr': 0x39, 'a': 0x5678, 'x': 0x9ABC}
        with self.assertRaisesRegex(AssertionError, 'binary ADC model requires D clear'):
            _run_emitted(words, routine=without_cld, **context)

    def test_decimal_mode_and_random_context_restore_on_all_terminals(self):
        rng = random.Random(0xD1)
        for case in range(24):
            words = [rng.randrange(768) | (0x4000 if rng.randrange(2) else 0)
                     for _ in range(1024)]
            slot = rng.randrange(1024)
            words[slot] = (0x8000 | rng.randrange(768) if case % 2
                           else 768 + rng.randrange(100))
            context = {'p': 0x08 | (rng.randrange(256) & 0xC7),
                       'y': rng.randrange(65536), 'sp': rng.randrange(0x1000, 0x2000),
                       'd': 0x3400, 'dbr': rng.randrange(256),
                       'a': rng.randrange(65536), 'x': rng.randrange(65536)}
            _assert_same_result(self, _reference(words, **context),
                                _run_emitted(words, **context))


def _asm_size(line: str) -> int:
    """Independent literal size decoder used only for branch range checks."""
    line = line.strip()
    if line in ('phb', 'plb', 'php', 'plp', 'cld', 'txa', 'tax', 'pha', 'pla', 'clc'):
        return 1
    if line == 'pea $4242':
        return 3
    if line.startswith(('lda #', 'adc #', 'and #', 'cmp #', 'cpx #', 'ldx #')):
        return 3
    if line.startswith(('lda $', 'sta $')) and line.endswith(',x'):
        return 3
    if line in ('sta $70', 'stx $70'):
        return 2
    if line.startswith('jmp '):
        return 3
    raise AssertionError(f'unsupported size-check instruction: {line}')


if __name__ == '__main__':
    unittest.main()
