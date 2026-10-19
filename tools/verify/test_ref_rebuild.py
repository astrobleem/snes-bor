"""Independent reference-model and instruction-interpreter tests."""
from __future__ import annotations

import random
import unittest

from ref_rebuild import (
    ANCHOR,
    CODE_LIMIT,
    CODE_START,
    ROUTINE,
    RefRebuildContractError,
    transform,
)


MASK = 0xFFFF
MAP = 0x42C000
REFS = 0x42D000


def _nz(p: int, value: int) -> int:
    p &= ~(0x80 | 0x02)
    value &= MASK
    if value & 0x8000:
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


def _state(maps: list[int], refs: list[int], *, a=0xA55A, x=0x6B4D,
           y=0x39C3, p=0xCD, sp=0x1FF0, dp=0x3470, dbr=0x7E) -> dict:
    # M/X are clear at the real call site: all helper arithmetic is 16-bit.
    return dict(a=a & MASK, x=x & MASK, y=y & MASK, p=p & 0xCF,
                sp=sp & MASK, dp=dp & MASK, dbr=dbr & 0xFF,
                maps=[v & MASK for v in maps], refs=[v & MASK for v in refs],
                writes=[], stack=[])


def _reference(maps: list[int], refs: list[int], **context) -> dict:
    """Run the accepted two-loop source model, with every write recorded."""
    s = _state(maps, refs, **context)
    for offset in range(0, 1536, 2):
        s['x'] = offset
        s['p'] = _nz(s['p'], offset)  # LDX #offset
        s['a'] = s['refs'][offset // 2]
        s['p'] = _nz(s['p'], s['a'])
        s['a'] &= 0x8000
        s['p'] = _nz(s['p'], s['a'])  # AND #$8000
        s['refs'][offset // 2] = s['a']
        s['writes'].append((REFS + offset, s['a']))
        s['x'] = (s['x'] + 1) & MASK
        s['p'] = _nz(s['p'], s['x'])
        s['x'] = (s['x'] + 1) & MASK
        s['p'] = _nz(s['p'], s['x'])
        s['p'] = _cmp(s['p'], s['x'], 1536)

    s['y'] = 0
    s['p'] = _nz(s['p'], s['y'])  # LDY #0
    while True:
        s['a'] = s['y']
        s['p'] = _nz(s['p'], s['a'])  # TYA
        s['x'] = s['a']
        s['p'] = _nz(s['p'], s['x'])  # TAX
        s['a'] = s['maps'][s['x'] // 2]
        s['p'] = _nz(s['p'], s['a'])
        carry = bool(s['a'] & 0x8000)
        s['a'] = (s['a'] << 1) & MASK
        s['p'] = _nz(s['p'], s['a'])  # ASL A
        s['p'] = (s['p'] | 1) if carry else (s['p'] & ~1)
        s['x'] = s['a']
        s['p'] = _nz(s['p'], s['x'])  # TAX
        index = s['x'] // 2
        s['a'] = s['refs'][index]
        s['p'] = _nz(s['p'], s['a'])
        s['a'] = (s['a'] + 1) & MASK
        s['p'] = _nz(s['p'], s['a'])  # INC A, preserving C/V
        s['refs'][index] = s['a']
        s['writes'].append((REFS + s['x'], s['a']))
        s['y'] = (s['y'] + 1) & MASK
        s['p'] = _nz(s['p'], s['y'])
        s['y'] = (s['y'] + 1) & MASK
        s['p'] = _nz(s['p'], s['y'])
        s['p'] = _cmp(s['p'], s['y'], 2048)
        if s['p'] & 1:
            return s


def _num(text: str) -> int:
    return int(text[1:], 16) if text.startswith('$') else int(text, 0)


def _run_emitted(maps: list[int], refs: list[int], *, routine=None, **context) -> dict:
    """Interpret the actual ROUTINE instruction subset and its branches."""
    s = _state(maps, refs, **context)
    code = [line.strip() for line in (ROUTINE if routine is None else routine)]
    labels = {line[:-1]: i for i, line in enumerate(code) if line.endswith(':')}
    pc = labels['RfRebuild'] + 1
    steps = 0
    while steps < 20000:
        steps += 1
        op = code[pc]
        pc += 1
        if not op or op.startswith('.') or op.endswith(':'):
            continue
        if op == 'phb':
            s['stack'].append(s['dbr']); s['sp'] = (s['sp'] - 1) & MASK
        elif op.startswith('pea $'):
            value = _num(op[4:])
            s['stack'].extend((value & 0xFF, value >> 8)); s['sp'] = (s['sp'] - 2) & MASK
        elif op == 'plb':
            s['dbr'] = s['stack'].pop(); s['sp'] = (s['sp'] + 1) & MASK
            s['p'] = _nz(s['p'], s['dbr'])
        elif op == 'ldx #0':
            s['x'] = 0; s['p'] = _nz(s['p'], s['x'])
        elif op == 'ldy #0':
            s['y'] = 0; s['p'] = _nz(s['p'], s['y'])
        elif op == 'lda $D000,x':
            if s['dbr'] != 0x42:
                raise AssertionError(f'absolute bank mismatch: DBR=${s["dbr"]:02X}, expected $42')
            s['a'] = s['refs'][s['x'] // 2]; s['p'] = _nz(s['p'], s['a'])
        elif op == 'lda $D000,y':
            if s['dbr'] != 0x42:
                raise AssertionError(f'absolute bank mismatch: DBR=${s["dbr"]:02X}, expected $42')
            s['a'] = s['refs'][s['y'] // 2]; s['p'] = _nz(s['p'], s['a'])
        elif op == 'lda $C000,y':
            if s['dbr'] != 0x42:
                raise AssertionError(f'absolute bank mismatch: DBR=${s["dbr"]:02X}, expected $42')
            s['a'] = s['maps'][s['y'] // 2]; s['p'] = _nz(s['p'], s['a'])
        elif op == 'and #$8000':
            s['a'] &= 0x8000; s['p'] = _nz(s['p'], s['a'])
        elif op == 'sta $D000,x':
            if s['dbr'] != 0x42:
                raise AssertionError(f'absolute bank mismatch: DBR=${s["dbr"]:02X}, expected $42')
            i = s['x'] // 2; s['refs'][i] = s['a']
            s['writes'].append((REFS + s['x'], s['a']))
        elif op == 'inx':
            s['x'] = (s['x'] + 1) & MASK; s['p'] = _nz(s['p'], s['x'])
        elif op == 'iny':
            s['y'] = (s['y'] + 1) & MASK; s['p'] = _nz(s['p'], s['y'])
        elif op == 'cpx #1536':
            s['p'] = _cmp(s['p'], s['x'], 1536)
        elif op == 'cpy #2048':
            s['p'] = _cmp(s['p'], s['y'], 2048)
        elif op in ('bcs RfClearDone', 'bcs RfPublishDone'):
            if s['p'] & 1: pc = labels[op.split()[1]] + 1
        elif op in ('brl RfClearLoop', 'brl RfPublishLoop'):
            pc = labels[op.split()[1]] + 1
        elif op == 'asl a':
            carry = bool(s['a'] & 0x8000)
            s['a'] = (s['a'] << 1) & MASK
            s['p'] = _nz(s['p'], s['a'])
            s['p'] = (s['p'] | 1) if carry else (s['p'] & ~1)
        elif op == 'tax':
            s['x'] = s['a']; s['p'] = _nz(s['p'], s['x'])
        elif op == 'inc a':
            s['a'] = (s['a'] + 1) & MASK; s['p'] = _nz(s['p'], s['a'])
        elif op == 'jmp RfContinue':
            s['terminal'] = 'RfContinue'
            break
        else:
            raise AssertionError('unsupported emitted instruction: ' + op)
    else:
        raise AssertionError('emitted routine exceeded step bound')
    s['steps'] = steps
    return s


def _assert_same(test: unittest.TestCase, expected: dict, actual: dict) -> None:
    for key in ('a', 'x', 'y', 'p', 'sp', 'dp', 'dbr', 'maps', 'refs', 'writes'):
        test.assertEqual(expected[key], actual[key], key)
    test.assertEqual([], actual['stack'])
    test.assertEqual('RfContinue', actual['terminal'])


class ReferenceRebuildTests(unittest.TestCase):
    def _fixture(self) -> list[str]:
        return ['NbAbort:'] + ANCHOR + ['NbVisible:']

    def test_transform_exact_dispatch_overlay_and_disabled_identity(self):
        fixture = self._fixture()
        rewritten = transform(fixture)
        self.assertEqual(fixture, transform(fixture, enabled=False))
        expected = fixture.copy()
        dispatch = expected.index('ldx #0')
        expected[dispatch] = ' jmp RfRebuild'
        expected.insert(expected.index('lda $10'), 'RfContinue:')
        expected += ROUTINE
        self.assertEqual(expected, rewritten)
        self.assertEqual((CODE_START, CODE_LIMIT), (0x39A900, 0x39B000))
        self.assertLess(CODE_START, CODE_LIMIT)

    def test_transform_rejects_anchor_drift_duplicates_and_reapplication(self):
        fixture = self._fixture()
        variants = []
        for source, changed in (
            ('lda #2047', 'lda #2046'), ('mvn $42,$42', 'mvn $41,$42'),
            ('and #$8000', 'and #$7FFF'), ('bcc NbClearRefs', 'bcs NbClearRefs'),
            ('lda.l $42C000,x', 'lda.l $42C002,x'), ('asl a', 'lsr a'),
            ('cpy #2048', 'cpy #2047'), ('lda $10', 'lda $12'),
        ):
            altered = fixture.copy(); altered[altered.index(source)] = changed
            variants.append(altered)
        variants.extend((fixture + fixture[1:], transform(fixture)))
        for source in variants:
            with self.subTest(length=len(source)):
                with self.assertRaises(RefRebuildContractError):
                    transform(source)

    def test_random_maps_refs_high_bits_and_cpu_context(self):
        rng = random.Random(0xA900)
        for case in range(24):
            maps = [rng.randrange(768) for _ in range(1024)]
            refs = [rng.randrange(65536) for _ in range(768)]
            if case % 3 == 0:
                maps[0], maps[-1] = 0, 767
            if case % 3 == 1:
                maps = [case % 768] * 1024
            context = dict(a=rng.randrange(65536), x=rng.randrange(65536),
                           y=rng.randrange(65536), p=rng.randrange(256) & 0xCF,
                           sp=rng.randrange(0x100, 0x2000), dp=0x3400,
                           dbr=rng.randrange(256))
            with self.subTest(case=case):
                _assert_same(self, _reference(maps, refs, **context),
                             _run_emitted(maps, refs, **context))

    def test_wrong_temporary_dbr_is_rejected_by_absolute_access_model(self):
        maps = [0] * 1024; refs = [0] * 768
        wrong_bank = ROUTINE.copy()
        wrong_bank[wrong_bank.index(' pea $4242')] = ' pea $4141'
        with self.assertRaisesRegex(AssertionError, 'absolute bank mismatch'):
            _run_emitted(maps, refs, routine=wrong_bank)

    def test_every_single_slot_count_matches_full_reference_and_write_order(self):
        # Exercise counts 0..1024 at a boundary slot while every other entry
        # still visits slot 767. Each case executes both literal loops.
        refs = [((i * 257) ^ 0x8000) & MASK for i in range(768)]
        context = dict(a=0xABCD, x=0x9876, y=0x4567, p=0xC5,
                       sp=0x1FEE, dp=0x3400, dbr=0x19)
        for count in range(1025):
            maps = [0] * count + [767] * (1024 - count)
            with self.subTest(count=count):
                _assert_same(self, _reference(maps, refs, **context),
                             _run_emitted(maps, refs, **context))

    def test_literal_overlay_unrolled_branches_fit_and_stack_is_balanced(self):
        # 65816 instruction lengths used by this exact emitted block.
        lengths = {
            'phb': 1, 'pea $4242': 3, 'plb': 1, 'ldx #0': 3, 'ldy #0': 3,
            'lda $D000,x': 3, 'lda $D000,y': 3, 'lda $C000,y': 3,
            'and #$8000': 3, 'sta $D000,x': 3, 'inx': 1, 'iny': 1,
            'cpx #1536': 3, 'cpy #2048': 3, 'bcs RfClearDone': 2,
            'bcs RfPublishDone': 2, 'brl RfClearLoop': 3, 'brl RfPublishLoop': 3,
            'asl a': 1, 'tax': 1, 'inc a': 1,
            'jmp RfContinue': 3,
        }
        code = [line.strip() for line in ROUTINE]
        labels = {}; branches = []; offset = 0
        for op in code:
            if op.endswith(':'):
                labels[op[:-1]] = offset
            elif op in lengths:
                offset += lengths[op]
                if op.startswith(('bcs ', 'brl ')):
                    branches.append((op, offset))
        expected = {'bcs RfClearDone': 3, 'brl RfClearLoop': -184,
                    'bcs RfPublishDone': 3, 'brl RfPublishLoop': -232}
        for op, end in branches:
            displacement = labels[op.split()[1]] - end
            self.assertEqual(expected[op], displacement)
            limit = 128 if op.startswith('bcs ') else 32768
            self.assertTrue(-limit <= displacement < limit)
        self.assertEqual(435, offset)
        self.assertLessEqual(CODE_START + sum(lengths.get(op, 0) for op in code), CODE_LIMIT)


if __name__ == '__main__':
    unittest.main()
