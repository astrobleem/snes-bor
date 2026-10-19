"""Instruction-level regression tests for the bounded READY validator overlay."""
from __future__ import annotations

import random
import unittest

from ready_validate import (
    ANCHOR,
    CODE_LIMIT,
    CODE_START,
    ROUTINE,
    ReadyValidateContractError,
    transform,
)


def _number(text: str) -> int:
    return int(text[1:], 16) if text.startswith('$') else int(text, 0)


MASK16 = 0xFFFF
MAP_BASE = 0x42C000


def _nz(p: int, value: int) -> int:
    p &= ~(0x80 | 0x02)
    value &= MASK16
    if value & 0x8000:
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
           sp: int = 0x1FF0, dp: int = 0x3400, dbr: int = 0x42,
           a: int = 0x1234, x: int = 0x5678) -> dict:
    return {
        'a': a & MASK16, 'x': x & MASK16, 'y': y & MASK16,
        'sp': sp & MASK16, 'dp': dp & MASK16, 'dbr': dbr & 0xFF,
        'p': p & 0xCF, 'mem': {MAP_BASE + 2 * i: value & MASK16
                                for i, value in enumerate(words)},
        'dp70': 0, 'stack': [], 'writes': [], 'terminal': None,
    }


def _reference(words: list[int], **context) -> dict:
    """Model the original serial assembly loop, including its failure snapshot."""
    s = _state(words, **context)
    for offset in range(0, 2048, 2):
        s['x'] = offset
        s['p'] = _nz(s['p'], offset)  # LDX $70
        raw = s['mem'][MAP_BASE + offset]
        s['a'] = raw
        s['p'] = _nz(s['p'], raw & 0x8000)
        s['a'] &= 0x8000
        if s['a']:
            s['dp70'] = offset
            s['terminal'] = 'NbAbort'
            return s
        s['a'] = raw
        s['p'] = _nz(s['p'], raw & 0x3FFF)
        s['a'] &= 0x3FFF
        s['p'] = _cmp(s['p'], s['a'], 768)
        if s['p'] & 1:
            s['dp70'] = offset
            s['terminal'] = 'NbAbort'
            return s
        address = MAP_BASE + offset
        s['mem'][address] = s['a']
        s['writes'].append((address, s['a']))
        s['dp70'] = (s['dp70'] + 1) & MASK16
        s['p'] = _nz(s['p'], s['dp70'])  # first INC $70
        s['dp70'] = (s['dp70'] + 1) & MASK16
        s['p'] = _nz(s['p'], s['dp70'])  # second INC $70
        s['a'] = s['dp70']
        s['p'] = _nz(s['p'], s['a'])
        s['p'] = _cmp(s['p'], s['a'], 2048)
        if s['p'] & 1:
            s['terminal'] = 'NbAfterLoop'
            return s
    raise AssertionError('reference loop did not terminate')


def _run_emitted(words: list[int], **context) -> dict:
    """Execute the emitted routine's supported 65816 subset, not a Python clone."""
    s = _state(words, **context)
    code = [line.strip() for line in ROUTINE]
    labels = {line[:-1]: index for index, line in enumerate(code)
              if line.endswith(':')}
    pc = labels['RvValidate'] + 1
    steps = 0

    while steps < 30000:
        steps += 1
        op = code[pc]
        pc += 1
        if not op or op.startswith('.') or op.endswith(':'):
            continue
        if op == 'ldx #0':
            s['x'] = 0
            s['p'] = _nz(s['p'], s['x'])
        elif op == 'lda.l $42C000,x':
            s['a'] = s['mem'][MAP_BASE + s['x']]
            s['p'] = _nz(s['p'], s['a'])
        elif op.startswith('and #'):
            s['a'] &= _number(op[5:])
            s['p'] = _nz(s['p'], s['a'])
        elif op.startswith('lda #'):
            s['a'] = _number(op[5:])
            s['p'] = _nz(s['p'], s['a'])
        elif op == 'bpl RvUntagged':
            if not s['p'] & 0x80:
                pc = labels['RvUntagged'] + 1
        elif op == 'bcc RvValid':
            if not s['p'] & 1:
                pc = labels['RvValid'] + 1
        elif op == 'sta $70':
            s['dp70'] = s['a']
        elif op == 'stx $70':
            s['dp70'] = s['x']
        elif op == 'jmp NbAbort':
            s['terminal'] = 'NbAbort'
            break
        elif op == 'sta.l $42C000,x':
            address = MAP_BASE + s['x']
            s['mem'][address] = s['a']
            s['writes'].append((address, s['a']))
        elif op == 'cpx #2048':
            s['p'] = _cmp(s['p'], s['x'], 2048)
        elif op == 'ldx #2046':
            s['x'] = 2046
            s['p'] = _nz(s['p'], s['x'])
        elif op == 'inx':
            s['x'] = (s['x'] + 1) & MASK16
            s['p'] = _nz(s['p'], s['x'])
        elif op.startswith('cmp #'):
            s['p'] = _cmp(s['p'], s['a'], _number(op[5:]))
        elif op == 'bcc RvValidateLoop':
            if not s['p'] & 1:
                pc = labels['RvValidateLoop'] + 1
        elif op == 'jmp RvContinue':
            s['terminal'] = 'NbAfterLoop'
            break
        else:
            raise AssertionError(f'unsupported emitted opcode: {op}')
    else:
        raise AssertionError('emitted loop exceeded instruction bound')
    s['steps'] = steps
    return s


def _assert_same_result(test: unittest.TestCase, expected: dict, actual: dict) -> None:
    for key in ('a', 'x', 'y', 'sp', 'dp', 'dbr', 'p', 'mem', 'dp70',
                'writes', 'terminal'):
        test.assertEqual(expected[key], actual[key], key)
    test.assertEqual([], actual['stack'])
    test.assertEqual(expected['dp'], actual['dp'])


class ReadyValidateTests(unittest.TestCase):
    def _fixture(self) -> list[str]:
        return ['NbAbort:'] + ANCHOR + ['NbGuard4:']

    def test_transform_pinned_overlay_and_disabled_identity(self):
        fixture = self._fixture()
        rewritten = transform(fixture)
        self.assertEqual(fixture, transform(fixture, enabled=False))
        start = fixture.index('ldx $70')
        expected = fixture.copy()
        expected[start:start + 2] = [' jmp RvValidate', ' nop', ' nop', ' nop']
        continuation = expected.index('lda.l $42D604')
        expected.insert(continuation, 'RvContinue:')
        expected += ROUTINE
        self.assertEqual(expected, rewritten)
        self.assertGreaterEqual(CODE_START, 0x39A800)
        self.assertLessEqual(CODE_LIMIT, 0x39B000)

    def test_transform_fails_closed_on_anchor_drift_duplicates_and_reapplication(self):
        fixture = self._fixture()
        changed_loop = fixture.copy()
        changed_loop[changed_loop.index('cmp #768')] = 'cmp #767'
        changed_init = fixture.copy()
        changed_init[changed_init.index('lda #0')] = 'lda #1'
        changed_counter = fixture.copy()
        changed_counter[changed_counter.index('sta $70')] = 'sta $72'
        for bad in (changed_loop, changed_init, changed_counter,
                    fixture + fixture[1:], transform(fixture)):
            with self.subTest(case=len(bad), first=bad[0]):
                with self.assertRaises(ReadyValidateContractError):
                    transform(bad)

    def test_all_1024_failure_positions_match_original_loop(self):
        rng = random.Random(0xA1F7)
        for slot in range(1024):
            words = [rng.randrange(768) | (0x4000 if rng.randrange(2) else 0)
                     for _ in range(1024)]
            context = {'p': rng.randrange(256) & 0xCF, 'y': rng.randrange(65536),
                       'sp': rng.randrange(0x100, 0x2000), 'dp': 0x3400,
                       'dbr': rng.randrange(256), 'a': rng.randrange(65536),
                       'x': rng.randrange(65536)}
            for tagged in (True, False):
                words[slot] = ((0x8000 | rng.randrange(768)) if tagged
                               else (768 + rng.randrange(0x4000 - 768)))
                with self.subTest(slot=slot, tagged=tagged):
                    _assert_same_result(self, _reference(words, **context),
                                        _run_emitted(words, **context))

    def test_success_checks_all_entries_and_masks_bit14(self):
        words = [((i * 53) % 768) | (0x4000 if i % 3 else 0)
                 for i in range(1024)]
        words[0] = 0x4000
        words[767] = 0x42FF
        context = {'p': 0xC5, 'y': 0xABCD, 'sp': 0x1FEE, 'dp': 0x3400,
                   'dbr': 0x7E, 'a': 0x1111, 'x': 0x2222}
        expected = _reference(words, **context)
        actual = _run_emitted(words, **context)
        _assert_same_result(self, expected, actual)
        self.assertEqual(2048, actual['dp70'])
        self.assertEqual(2046, actual['x'])
        self.assertEqual(2048, actual['a'])
        self.assertEqual('NbAfterLoop', actual['terminal'])
        self.assertEqual(1024, sum(actual['mem'][MAP_BASE + 2 * i] == (words[i] & 0x3FFF)
                                   for i in range(1024)))

    def test_randomized_maps_and_context_match_reference(self):
        rng = random.Random(0x39A800)
        for case in range(24):
            words = [rng.randrange(768) | (0x4000 if rng.randrange(2) else 0)
                     for _ in range(1024)]
            if case % 3 == 0:
                words[case * 31 % 1024] = 0x8000 | rng.randrange(768)
            elif case % 3 == 1:
                words[case * 31 % 1024] = 768 + rng.randrange(0x4000 - 768)
            context = {'p': rng.randrange(256) & 0xCF, 'y': rng.randrange(65536),
                       'sp': rng.randrange(0x100, 0x2000), 'dp': 0x3400,
                       'dbr': rng.randrange(256), 'a': rng.randrange(65536),
                       'x': rng.randrange(65536)}
            with self.subTest(case=case):
                _assert_same_result(self, _reference(words, **context),
                                    _run_emitted(words, **context))


if __name__ == '__main__':
    unittest.main()
