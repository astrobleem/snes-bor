"""Independent source model and interpreter tests for borrowed-home lookup."""
from __future__ import annotations

import copy
import random
import unittest

from borrow_invalidate import (
    ANCHOR,
    CODE_LIMIT,
    CODE_START,
    ROUTINE,
    BorrowInvalidateContractError,
    transform,
)


MASK = 0xFFFF
COUNT_LIMIT = 596
REF_BASE = 0x42D000
OWNER_BASE = 0x42D710


def _nz(p: int, value: int) -> int:
    value &= MASK
    p &= ~(0x80 | 0x02)
    if value & 0x8000:
        p |= 0x80
    if value == 0:
        p |= 0x02
    return p


def _nz8(p: int, value: int) -> int:
    value &= 0xFF
    p &= ~(0x80 | 0x02)
    if value & 0x80:
        p |= 0x80
    if value == 0:
        p |= 0x02
    return p


def _cmp(p: int, left: int, right: int) -> int:
    left &= MASK
    right &= MASK
    result = (left - right) & MASK
    p = _nz(p, result)
    if left >= right:
        p |= 1
    else:
        p &= ~1
    return p


def _asl(p: int, value: int) -> tuple[int, int]:
    carry = bool(value & 0x8000)
    value = (value << 1) & MASK
    p = _nz(p, value)
    p = (p | 1) if carry else (p & ~1)
    return p, value


def _lsr(p: int, value: int) -> tuple[int, int]:
    carry = bool(value & 1)
    value = (value >> 1) & MASK
    p = _nz(p, value)
    p = (p | 1) if carry else (p & ~1)
    return p, value


def _initial(owners, refs, *, owner_id, active=1, a=0xA55A, x=0x6B4D,
             y=0x39C3, p=0xCD, dbr=0x7E, sp=0x1FF0, dp=0x3400,
             emulation=0, pbr=0x39, return_pc=0xBEEF):
    return dict(a=a & MASK, x=x & MASK, y=y & MASK, p=p & 0xCF,
                d=dp & MASK, dbr=dbr & 0xFF, sp=sp & MASK,
                emulation=emulation, pbr=pbr & 0xFF, return_pc=return_pc & MASK,
                id=owner_id & MASK, active=active & MASK,
                owners=[v & MASK for v in owners], refs=[v & MASK for v in refs],
                writes=[], stack=[])


def _push8(s, value):
    s['stack'].append(value & 0xFF)
    s['sp'] = (s['sp'] - 1) & MASK


def _pull8(s):
    value = s['stack'].pop()
    s['sp'] = (s['sp'] + 1) & MASK
    return value


def _push16(s, value):
    _push8(s, value >> 8)
    _push8(s, value)


def _pull16(s):
    low = _pull8(s)
    high = _pull8(s)
    return low | (high << 8)


def _store(s, address, value):
    value &= MASK
    if address < REF_BASE + 2 * len(s['refs']):
        index = (address - REF_BASE) // 2
        s['refs'][index] = value
    else:
        index = (address - OWNER_BASE) // 2
        s['owners'][index] = value
    s['writes'].append((address, value))


def _found_continuation(s):
    """Model the original BhInvalidateFound/OK bodies instruction by instruction."""
    _push16(s, s['x'])
    s['a'] = s['id']; s['p'] = _nz(s['p'], s['a'])
    s['p'], s['a'] = _asl(s['p'], s['a'])
    s['x'] = s['a']; s['p'] = _nz(s['p'], s['x'])
    slot = s['x'] // 2
    s['a'] = s['refs'][slot]; s['p'] = _nz(s['p'], s['a'])
    s['a'] &= 0x3FFF; s['p'] = _nz(s['p'], s['a'])
    if s['a']:
        s['x'] = _pull16(s); s['p'] = _nz(s['p'], s['x'])
        s['p'] |= 1
        return
    s['x'] = _pull16(s); s['p'] = _nz(s['p'], s['x'])
    address = OWNER_BASE + s['x']
    s['a'] = s['owners'][s['x'] // 2]; s['p'] = _nz(s['p'], s['a'])
    s['a'] |= 0x4000; s['p'] = _nz(s['p'], s['a'])
    _store(s, address, s['a'])
    s['a'] = s['id']; s['p'] = _nz(s['p'], s['a'])
    s['p'], s['a'] = _asl(s['p'], s['a'])
    s['x'] = s['a']; s['p'] = _nz(s['p'], s['x'])
    slot = s['x'] // 2
    s['a'] = s['refs'][slot]; s['p'] = _nz(s['p'], s['a'])
    s['a'] |= 0x8000; s['p'] = _nz(s['p'], s['a'])
    _store(s, REF_BASE + s['x'], s['a'])
    s['p'] &= ~1


def _bad_continuation(s):
    """Original BhInvalidateBad: SEC; RTS."""
    s['p'] |= 1


def _original_loop(s):
    """The accepted TXA/LSR/count-check and ordered linear lookup."""
    s['x'] = 0; s['p'] = _nz(s['p'], s['x'])
    while True:
        s['a'] = s['x']; s['p'] = _nz(s['p'], s['a'])  # TXA
        s['p'], s['a'] = _lsr(s['p'], s['a'])
        s['p'] = _cmp(s['p'], s['a'], len(s['owners']))
        if not (s['p'] & 1):
            s['a'] = s['owners'][s['x'] // 2]; s['p'] = _nz(s['p'], s['a'])
            s['a'] &= 0x3FFF; s['p'] = _nz(s['p'], s['a'])
            s['p'] = _cmp(s['p'], s['a'], s['id'])
            if s['p'] & 2:
                _found_continuation(s)
                return
            s['x'] = (s['x'] + 1) & MASK; s['p'] = _nz(s['p'], s['x'])
            s['x'] = (s['x'] + 1) & MASK; s['p'] = _nz(s['p'], s['x'])
            continue
        _bad_continuation(s)
        return


def _original(s):
    """Run all original BhInvalidate guards, scan and write continuations."""
    s['a'] = s['id']; s['p'] = _nz(s['p'], s['a'])
    s['p'] = _cmp(s['p'], s['a'], COUNT_LIMIT)
    if s['p'] & 1:
        s['p'] &= ~1
        return s
    s['a'] = s['active']; s['p'] = _nz(s['p'], s['a'])
    s['p'] = _cmp(s['p'], s['a'], 1)
    if not (s['p'] & 2):
        _bad_continuation(s)
        return s
    _original_loop(s)
    return s


def _execute_helper(s):
    """Interpret the emitted helper, tailing into the original pinned bodies."""
    code = [line.strip() for line in ROUTINE]
    labels = {line[:-1]: i for i, line in enumerate(code) if line.endswith(':')}
    pc = labels['IvFind'] + 1
    steps = 0
    while steps < 100000:
        steps += 1
        op = code[pc]
        pc += 1
        if not op or op.startswith('.') or op.endswith(':'):
            continue
        if op == 'phy':
            _push16(s, s['y'])
        elif op == 'phb':
            _push8(s, s['dbr'])
        elif op == 'pea $4242':
            _push16(s, 0x4242)
        elif op == 'plb':
            s['dbr'] = _pull8(s); s['p'] = _nz8(s['p'], s['dbr'])
        elif op == 'ply':
            s['y'] = _pull16(s); s['p'] = _nz(s['p'], s['y'])
        elif op == 'lda $D704':
            s['a'] = len(s['owners']); s['p'] = _nz(s['p'], s['a'])
        elif op == 'cmp #597':
            s['p'] = _cmp(s['p'], s['a'], 597)
        elif op == 'bcs IvFallback':
            if s['p'] & 1: pc = labels['IvFallback'] + 1
        elif op == 'tay':
            s['y'] = s['a']; s['p'] = _nz(s['p'], s['y'])
        elif op == 'ldx #0':
            s['x'] = 0; s['p'] = _nz(s['p'], s['x'])
        elif op == 'beq IvMiss':
            if s['p'] & 2: pc = labels['IvMiss'] + 1
        elif op == 'lda $D710,x':
            s['a'] = s['owners'][s['x'] // 2]; s['p'] = _nz(s['p'], s['a'])
        elif op == 'and #$3FFF':
            s['a'] &= 0x3FFF; s['p'] = _nz(s['p'], s['a'])
        elif op == 'cmp $2C':
            s['p'] = _cmp(s['p'], s['a'], s['id'])
        elif op == 'beq IvFound':
            if s['p'] & 2: pc = labels['IvFound'] + 1
        elif op == 'inx':
            s['x'] = (s['x'] + 1) & MASK; s['p'] = _nz(s['p'], s['x'])
        elif op == 'dey':
            s['y'] = (s['y'] - 1) & MASK; s['p'] = _nz(s['p'], s['y'])
        elif op == 'bne IvLoop':
            if not (s['p'] & 2): pc = labels['IvLoop'] + 1
        elif op == 'jmp IvMiss':
            pc = labels['IvMiss'] + 1
        elif op == 'jmp BhInvalidateFound':
            _found_continuation(s); return steps
        elif op == 'txa':
            s['a'] = s['x']; s['p'] = _nz(s['p'], s['a'])
        elif op == 'lsr a':
            s['p'], s['a'] = _lsr(s['p'], s['a'])
        elif op == 'cmp.l $42D704':
            s['p'] = _cmp(s['p'], s['a'], len(s['owners']))
        elif op == 'jmp BhInvalidateBad':
            _bad_continuation(s); return steps
        elif op == 'jmp BhInvalidateFind':
            _original_loop(s); return steps
        else:
            raise AssertionError('unsupported emitted instruction: ' + op)
    raise AssertionError('helper exceeded interpreter step bound')


def _emitted(s):
    """Run the unchanged original guards, then the patched helper dispatch."""
    s['a'] = s['id']; s['p'] = _nz(s['p'], s['a'])
    s['p'] = _cmp(s['p'], s['a'], COUNT_LIMIT)
    if s['p'] & 1:
        s['p'] &= ~1
        return 0
    s['a'] = s['active']; s['p'] = _nz(s['p'], s['a'])
    s['p'] = _cmp(s['p'], s['a'], 1)
    if not (s['p'] & 2):
        _bad_continuation(s)
        return 0
    return _execute_helper(s)


def _assert_equivalent(test, expected, actual):
    for key in ('a', 'x', 'y', 'd', 'dbr', 'sp', 'p', 'emulation', 'pbr',
                'return_pc', 'id', 'active',
                'owners', 'refs', 'writes'):
        test.assertEqual(expected[key], actual[key], key)
    test.assertEqual([], expected['stack'])
    test.assertEqual([], actual['stack'])


def _lengths():
    return {
        'phy': 1, 'phb': 1, 'pea $4242': 3, 'plb': 1, 'ply': 1,
        'lda $D704': 3, 'cmp #597': 3, 'bcs IvFallback': 2,
        'tay': 1, 'ldx #0': 3, 'beq IvMiss': 2, 'lda $D710,x': 3,
        'and #$3FFF': 3, 'cmp $2C': 2, 'beq IvFound': 2,
        'inx': 1, 'dey': 1, 'bne IvLoop': 2, 'jmp IvMiss': 3,
        'jmp BhInvalidateFound': 3, 'txa': 1, 'lsr a': 1,
        'cmp.l $42D704': 4, 'jmp BhInvalidateBad': 3,
        'jmp BhInvalidateFind': 3,
    }


class BorrowInvalidateTests(unittest.TestCase):
    def _fixture(self):
        return ['NbBefore:'] + ANCHOR + ['NbAfter:']

    def test_transform_exact_dispatch_disabled_drift_and_reapplication(self):
        fixture = self._fixture()
        self.assertEqual(fixture, transform(fixture, enabled=False))
        actual = transform(fixture)
        expected = fixture.copy()
        expected[expected.index('ldx #0')] = ' jmp IvFind'
        expected += ROUTINE
        self.assertEqual(expected, actual)
        mutations = (
            ('cmp #596', 'cmp #595'), ('lda.l $42D70C', 'lda.l $42D70E'),
            ('cmp.l $42D704', 'cmp.l $42D706'),
            ('and #$3FFF', 'and #$7FFF'),
            ('jmp BhInvalidateFind', 'jmp BhInvalidateBad'),
            ('ora #$8000', 'ora #$4000'),
        )
        for before, after in mutations:
            changed = fixture.copy(); changed[changed.index(before)] = after
            with self.subTest(before=before), self.assertRaises(BorrowInvalidateContractError):
                transform(changed)
        for changed in (fixture + fixture, actual):
            with self.assertRaises(BorrowInvalidateContractError):
                transform(changed)

    def test_emitted_branches_fit_and_fallback_is_explicit(self):
        lengths = _lengths(); code = [line.strip() for line in ROUTINE]
        labels = {}; branches = []; offset = 0
        for op in code:
            if op.endswith(':'):
                labels[op[:-1]] = offset
            elif op in lengths:
                offset += lengths[op]
                if op.startswith(('bcs ', 'beq ', 'bne ', 'bra ')):
                    branches.append((op, offset))
        self.assertLessEqual(CODE_START + offset, CODE_LIMIT)
        self.assertLessEqual(CODE_START, CODE_START + offset)
        for op, end in branches:
            delta = labels[op.split()[1]] - end
            self.assertTrue(-128 <= delta <= 127, (op, delta))
        self.assertEqual({'IvFallback', 'IvMiss', 'IvFound', 'IvLoop'} & set(labels),
                         {'IvFallback', 'IvMiss', 'IvFound', 'IvLoop'})
        self.assertEqual({
            'IvFind': 0, 'IvLoop': 0x15, 'IvFound': 0x27,
            'IvMiss': 0x2C, 'IvFallback': 0x37, 'IvCodeEnd': 0x3F,
        }, labels)
        self.assertEqual([40, 23, 8, -15],
                         [labels[op.split()[1]] - end for op, end in branches])

    def test_fast_lookup_counts_and_complete_cpu_state(self):
        rng = random.Random(0xB14A)
        for count in (0, 1, 2, 41, 95, 596):
            cases = [None] if count == 0 else [0, count - 1, count // 2, None]
            for pos in cases:
                owners = [((i * 17) & 0x3FFF) | (0x4000 if i & 1 else 0)
                          for i in range(count)]
                owner_id = (next(i for i in range(596)
                                 if all((value & 0x3FFF) != i for value in owners))
                            if pos is None else pos)
                if pos is not None:
                    owners[pos] = owner_id | (0xC000 if pos & 1 else 0)
                refs = [rng.randrange(0x4000) for _ in range(768)]
                refs[owner_id] = 0 if (count + (pos or 0)) & 1 else 7
                context = dict(a=rng.randrange(65536), x=rng.randrange(65536),
                               y=rng.randrange(65536), p=rng.randrange(256),
                               dbr=rng.randrange(256), sp=rng.randrange(0x100, 0x2000))
                expected = _original(_initial(owners, refs, owner_id=owner_id, **context))
                actual = _initial(owners, refs, owner_id=owner_id, **context)
                _emitted(actual)
                with self.subTest(count=count, pos=pos):
                    _assert_equivalent(self, expected, actual)

    def test_every_match_position_at_max_fast_count(self):
        owners = [i | (0x4000 if i & 1 else 0x8000) for i in range(596)]
        for position in range(596):
            refs = [0] * 768
            refs[position] = position % 2
            before = _initial(owners, refs, owner_id=position, p=0xC5,
                              a=0xA5A5, x=0x1234, y=0x9876, dbr=0xE1,
                              sp=0x1FEE)
            expected = _original(copy.deepcopy(before))
            actual = copy.deepcopy(before)
            _emitted(actual)
            with self.subTest(position=position):
                _assert_equivalent(self, expected, actual)

    def test_duplicate_masked_ids_choose_first_and_preserve_flags(self):
        for refcount in (0, 5):
            owners = [0xC123, 0x4123, 0x8123, 0x3FFF]
            refs = [0] * 768; refs[0x123] = refcount
            before = _initial(owners, refs, owner_id=0x123, p=0x45,
                              a=0xFFFF, x=0xAAAA, y=0x5555, dbr=0x22)
            expected = _original(copy.deepcopy(before)); actual = copy.deepcopy(before)
            _emitted(actual)
            _assert_equivalent(self, expected, actual)
            if refcount:
                self.assertEqual([], actual['writes'])
                self.assertEqual(owners, actual['owners'])
            else:
                self.assertEqual([(OWNER_BASE, 0xC123), (REF_BASE + 2 * 0x123, 0x8000)],
                                 actual['writes'])
                self.assertEqual(0x4123, actual['owners'][1])

    def test_fallback_count_above_safe_bank_local_bound(self):
        for count, position in ((597, 0), (597, 596), (640, 321), (640, None)):
            owners = [((i * 19) & 0x3FFF) | (0x4000 if i % 3 == 0 else 0)
                      for i in range(count)]
            owner_id = 0x3FFE if position is None else position
            if position is not None:
                owners[position] = owner_id | 0x8000
            refs = [0] * 768
            before = _initial(owners, refs, owner_id=owner_id, a=0xF00D,
                              x=0xA102, y=0x0B77, p=0xC9, dbr=0x55,
                              sp=0x1FE8)
            expected = _original(copy.deepcopy(before)); actual = copy.deepcopy(before)
            _emitted(actual)
            with self.subTest(count=count, position=position):
                _assert_equivalent(self, expected, actual)

    def test_outer_guards_and_boundary_ids_keep_original_returns(self):
        owners = [0, 1, 2]
        for owner_id, active in ((596, 1), (0xFFFF, 1), (12, 0), (12, 2)):
            before = _initial(owners, [0] * 768, owner_id=owner_id, active=active,
                              a=0x1357, x=0x2468, y=0xABCD, p=0xD5,
                              dbr=0x66, sp=0x1FF0)
            expected = _original(copy.deepcopy(before)); actual = copy.deepcopy(before)
            _emitted(actual)
            with self.subTest(owner_id=owner_id, active=active):
                _assert_equivalent(self, expected, actual)


if __name__ == '__main__':
    unittest.main()


