"""Independent reference model and emitted-helper interpreter for abort copy."""
from __future__ import annotations

from pathlib import Path
import random
import unittest

from abort_copy import (
    ANCHOR,
    CODE_LIMIT,
    CODE_START,
    ROUTINE,
    AbortCopyContractError,
    estimated_bytes,
    transform,
)


MASK16 = 0xFFFF
PENDING = 0x42C000
COMMITTED = 0x42C800
BASE_SOURCE = Path('out/byor-motu-commit-rebuild-fuse-static-v2/candidate/native/publisher.pasm')


def _nz(p: int, value: int, bits: int = 16) -> int:
    p &= ~(0x80 | 0x02)
    value &= (1 << bits) - 1
    if value & (1 << (bits - 1)):
        p |= 0x80
    if value == 0:
        p |= 0x02
    return p


def _state(pending: list[int], committed: list[int], refs: list[int] | None = None, *,
           owner=4,
           a=0xA55A, x=0x6B4D, y=0x39C3, p=0xCD,
           sp=0x1800, d=0x3400, dbr=0x7E, dp70=0x55AA) -> dict:
    if p & 0x30:
        raise AssertionError('helper contract requires 16-bit accumulator and index registers')
    if d != 0x3400 or not 0x1000 <= sp <= 0x1FFF:
        raise AssertionError('model contract requires D=$3400 and SP in $1000..$1FFF')
    return dict(a=a & MASK16, x=x & MASK16, y=y & MASK16, p=p & 0xFF,
                sp=sp & MASK16, d=d & MASK16, dbr=dbr & 0xFF,
                dp70=dp70 & MASK16,
                pending=[v & MASK16 for v in pending],
                committed=[v & MASK16 for v in committed],
                refs=[v & MASK16 for v in (refs if refs is not None else [0xA55A] * 768)],
                owner=owner & MASK16,
                sentinels={0x42BFFE: 0x5AA5, 0x42D600: 0xC33C,
                           0x42D7FE: 0x3CC3},
                reads=[], writes=[], events=[], stack=[], stack_writes=[],
                terminal=None)


def _word_bytes(address: int, value: int) -> tuple[tuple[int, int], tuple[int, int]]:
    return ((address, value & 0xFF), (address + 1, (value >> 8) & 0xFF))


def _reference(pending: list[int], committed: list[int], refs: list[int] | None = None,
               **context) -> dict:
    """Model original 2048-byte MVN followed by PLB and LDA #0."""
    s = _state(pending, committed, refs, **context)
    source = [byte for word in s['committed'] for byte in (word & 0xFF, word >> 8)]
    destination = [byte for word in s['pending'] for byte in (word & 0xFF, word >> 8)]
    for offset in range(2048):
        s['reads'].append((COMMITTED + offset, source[offset]))
        s['events'].append(('read', COMMITTED + offset, source[offset]))
        destination[offset] = source[offset]
        s['writes'].append((PENDING + offset, destination[offset]))
        s['events'].append(('write', PENDING + offset, destination[offset]))
    s['pending'] = [destination[i] | (destination[i + 1] << 8)
                    for i in range(0, 2048, 2)]
    # MVN increments X/Y by byte count and leaves A=$FFFF; PLB then LDA #0
    # establish the exact state immediately before the original close STA.
    s['a'] = 0
    s['x'] = 0xD000
    s['y'] = 0xC800
    s['p'] = (s['p'] & 0x7D) | 0x02
    s['terminal'] = 'CaContinue'
    return s


def _num(text: str) -> int:
    if text.startswith('$'):
        return int(text[1:], 16)
    return int(text, 0)


def _run_emitted(pending: list[int], committed: list[int], refs: list[int] | None = None,
                 *, routine=None, owner=4, **context) -> dict:
    """Interpret the emitted helper with 16-bit memory and byte traces."""
    s = _state(pending, committed, refs, owner=owner, **context)
    program = transform(BASE_SOURCE.read_text().splitlines())
    if routine is not None:
        program = program[:-len(ROUTINE)] + list(routine)
    code = [line.strip() for line in program]
    labels = {line[:-1]: i for i, line in enumerate(code) if line.endswith(':')}
    pc = labels['CaCopy'] + 1
    steps = 0

    def push(value: int) -> None:
        s['stack_writes'].append((s['sp'], value & 0xFF))
        s['sp'] = (s['sp'] - 1) & MASK16
        s['stack'].append(value & 0xFF)

    def pull() -> int:
        s['sp'] = (s['sp'] + 1) & MASK16
        return s['stack'].pop()

    def indexed_operand(op: str) -> int:
        start = op.index('$')
        comma = op.index(',')
        return int(op[start + 1:comma], 16)

    def read_word(base: int, index: int) -> int:
        address = base + index
        if 0xC800 <= address <= 0xCFFE and address % 2 == 0:
            word = s['committed'][(address - 0xC800) // 2]
        elif 0xC000 <= address <= 0xC7FE and address % 2 == 0:
            word = s['pending'][(address - 0xC000) // 2]
        else:
            raise AssertionError(f'bad absolute indexed read ${address:04X}')
        for addr, byte in _word_bytes(0x420000 + address, word):
            s['reads'].append((addr, byte))
            s['events'].append(('read', addr, byte))
        return word

    def write_word(base: int, index: int, value: int) -> None:
        address = base + index
        if not 0xC000 <= address <= 0xC7FE or address % 2:
            raise AssertionError(f'bad absolute indexed write ${address:04X}')
        slot = (address - 0xC000) // 2
        s['pending'][slot] = value & MASK16
        for addr, byte in _word_bytes(0x420000 + address, value):
            s['writes'].append((addr, byte))
            s['events'].append(('write', addr, byte))

    while steps < 10000:
        steps += 1
        op = code[pc]
        pc += 1
        if op == 'CaContinue:':
            s['terminal'] = 'CaContinue'
            break
        if not op or op.startswith('.') or op.endswith(':'):
            continue
        if op == 'php':
            push(s['p'])
        elif op == 'phb':
            push(s['dbr'])
        elif op == 'pea $4242':
            push(0x42); push(0x42)
        elif op == 'plb':
            s['dbr'] = pull()
            s['p'] = _nz(s['p'], s['dbr'], 8)
        elif op == 'plp':
            s['p'] = pull()
        elif op == 'cld':
            s['p'] &= ~0x08
        elif op.startswith('ldx #'):
            s['x'] = _num(op[5:]); s['p'] = _nz(s['p'], s['x'])
        elif op.startswith('ldy #'):
            s['y'] = _num(op[5:]); s['p'] = _nz(s['p'], s['y'])
        elif op == 'txa':
            s['a'] = s['x']; s['p'] = _nz(s['p'], s['a'])
        elif op == 'tax':
            s['x'] = s['a']; s['p'] = _nz(s['p'], s['x'])
        elif op == 'clc':
            s['p'] &= ~1
        elif op.startswith('adc #'):
            if s['p'] & 0x08:
                raise AssertionError('binary ADC requires CLD')
            operand = _num(op[5:]); left = s['a']; carry = s['p'] & 1
            total = left + operand + carry
            value = total & MASK16
            s['p'] = _nz(s['p'], value)
            if total > MASK16:
                s['p'] |= 1
            else:
                s['p'] &= ~1
            if (~(left ^ operand) & (left ^ value) & 0x8000):
                s['p'] |= 0x40
            else:
                s['p'] &= ~0x40
            s['a'] = value
        elif op == 'lda.l $42D600':
            s['a'] = s['owner']; s['p'] = _nz(s['p'], s['a'])
        elif op.startswith('lda $') and op.endswith(',x'):
            if s['dbr'] != 0x42:
                raise AssertionError('helper must select DBR $42')
            base = indexed_operand(op)
            s['a'] = read_word(base, s['x'])
            s['p'] = _nz(s['p'], s['a'])
        elif op.startswith('sta $') and op.endswith(',x'):
            if s['dbr'] != 0x42:
                raise AssertionError('helper must select DBR $42')
            base = indexed_operand(op)
            write_word(base, s['x'], s['a'])
        elif op == 'cpx #2048':
            value = (s['x'] - 2048) & MASK16
            s['p'] = _nz(s['p'], value)
            if s['x'] >= 2048:
                s['p'] |= 1
            else:
                s['p'] &= ~1
        elif op == 'cmp #5':
            value = (s['a'] - 5) & MASK16
            s['p'] = _nz(s['p'], value)
            if s['a'] >= 5:
                s['p'] |= 1
            else:
                s['p'] &= ~1
        elif op == 'bne CaPhaseCheck':
            if not (s['p'] & 0x02):
                pc = labels['CaPhaseCheck'] + 1
        elif op == 'bcc CaFast':
            if not (s['p'] & 1):
                pc = labels['CaFast'] + 1
        elif op == 'bcs CaDone':
            if s['p'] & 1:
                pc = labels['CaDone'] + 1
        elif op == 'jmp CaFallback':
            pc = labels['CaFallback'] + 1
        elif op == 'jmp CaLoop':
            pc = labels['CaLoop'] + 1
        elif op == 'jmp CaLegacyCopy':
            pc = labels['CaLegacyCopy'] + 1
        elif op == 'jmp CaContinue':
            s['terminal'] = 'CaContinue'
            break
        elif op == 'lda #0':
            s['a'] = 0; s['p'] = _nz(s['p'], 0)
        elif op == 'lda #2047':
            s['a'] = 2047; s['p'] = _nz(s['p'], s['a'])
        elif op == 'ldx #51200':
            s['x'] = 51200; s['p'] = _nz(s['p'], s['x'])
        elif op == 'ldy #49152':
            s['y'] = 49152; s['p'] = _nz(s['p'], s['y'])
        elif op == 'mvn $42,$42':
            if s['a'] != 2047 or s['x'] != 0xC800 or s['y'] != 0xC000:
                raise AssertionError('legacy MVN entry state drift')
            source = [byte for word in s['committed'] for byte in (word & 0xFF, word >> 8)]
            destination = [byte for word in s['pending'] for byte in (word & 0xFF, word >> 8)]
            for offset in range(2048):
                s['reads'].append((COMMITTED + offset, source[offset]))
                s['events'].append(('read', COMMITTED + offset, source[offset]))
                destination[offset] = source[offset]
                s['writes'].append((PENDING + offset, destination[offset]))
                s['events'].append(('write', PENDING + offset, destination[offset]))
            s['pending'] = [destination[i] | (destination[i + 1] << 8)
                            for i in range(0, 2048, 2)]
            s['a'] = MASK16; s['x'] = 0xD000; s['y'] = 0xC800
            s['dbr'] = 0x42
        else:
            raise AssertionError('unsupported emitted instruction: ' + op)
    else:
        raise AssertionError('emitted helper exceeded step bound')
    s['steps'] = steps
    s['path'] = 'fast' if s['stack_writes'] and len(s['stack_writes']) == 4 else 'fallback'
    return s


def _assert_same(test: unittest.TestCase, expected: dict, actual: dict) -> None:
    for key in ('a', 'x', 'y', 'p', 'sp', 'd', 'dbr', 'dp70',
                'pending', 'committed', 'refs', 'sentinels', 'writes'):
        test.assertEqual(expected[key], actual[key], key)
    test.assertEqual(expected['reads'], actual['reads'])
    test.assertEqual('CaContinue', actual['terminal'])
    test.assertEqual([], actual['stack'])
    test.assertEqual(expected['sp'], actual['sp'])
    expected_stack_writes = 4 if actual['path'] == 'fast' else 2
    test.assertEqual(expected_stack_writes, len(actual['stack_writes']))
    expected_min_stack_address = expected['sp'] - 3 if actual['path'] == 'fast' else expected['sp']
    test.assertEqual(expected_min_stack_address,
                     min(address for address, _ in actual['stack_writes']))
    test.assertEqual(list(range(PENDING, PENDING + 2048)),
                     [address for address, _ in actual['writes']])
    test.assertEqual(list(range(COMMITTED, COMMITTED + 2048)),
                     [address for address, _ in actual['reads']])
    test.assertNotIn((actual['d'] + 0x70) & MASK16,
                     [address for address, _ in actual['stack_writes']])


def _asm_size(line: str) -> int:
    line = line.strip()
    if line in ('php', 'phb', 'plb', 'plp', 'cld', 'txa', 'tax', 'clc'):
        return 1
    if line == 'pea $4242':
        return 3
    if line == 'lda.l $42D600':
        return 4
    if line.startswith(('ldx #', 'ldy #', 'lda #', 'adc #', 'cmp #', 'cpx #')):
        return 3
    if line.startswith(('lda $', 'sta $')) and line.endswith(',x'):
        return 3
    if line.startswith(('bcs ', 'bcc ', 'beq ', 'bne ')):
        return 2
    if line.startswith('jmp '):
        return 3
    raise AssertionError('unknown size-check instruction: ' + line)


class AbortCopyTests(unittest.TestCase):
    def _base(self) -> list[str]:
        return BASE_SOURCE.read_text().splitlines()

    def test_transform_exact_patch_continuation_and_disabled_identity(self):
        base = self._base()
        changed = transform(base)
        self.assertEqual(base, transform(base, enabled=False))
        normalized = [line.strip() for line in base]
        start = next(i for i in range(len(normalized) - len(ANCHOR) + 1)
                     if normalized[i:i + len(ANCHOR)] == ANCHOR)
        prefix = start + ANCHOR.index('phb')
        legacy = start + ANCHOR.index('ldx #51200')
        sta = start + ANCHOR.index('sta.l $42D600')
        expected = base.copy()
        expected[prefix:prefix + 2] = [' jmp CaCopy', ' nop']
        expected[legacy:legacy] = ['CaLegacyCopy:', '.a16', '.i16']
        expected[sta + 3:sta + 3] = ['CaContinue:', '.a16', '.i16']
        expected.extend(ROUTINE)
        self.assertEqual(expected, changed)
        rewritten = [line.strip() for line in changed]
        self.assertEqual(['jmp CaCopy', 'nop'], rewritten[prefix:prefix + 2])
        self.assertEqual('CaLegacyCopy:', rewritten[legacy])
        self.assertEqual('CaContinue:', rewritten[sta + 3])
        self.assertEqual(['.a16','.i16'],rewritten[legacy+1:legacy+3])
        self.assertEqual(['.a16','.i16'],rewritten[sta+4:sta+6])

    def test_transform_rejects_drift_duplicate_and_reapplication(self):
        base = self._base()
        variants = []
        for source, replacement in (
            ('sta.l $42D660', 'sta.l $42D662'), ('jsr BhRollback', 'jsr BhCommit'),
            ('lda #2047', 'lda #2046'), ('ldx #51200', 'ldx #51201'),
            ('ldy #49152', 'ldy #49153'), ('mvn $42,$42', 'mvn $41,$42'),
            ('plb', 'plp'), ('sta.l $42D600', 'sta.l $42D602'),
            ('jmp OnlineReject', 'jmp NbFree'),
        ):
            altered = base.copy()
            begin = next(i for i in range(len(base) - len(ANCHOR) + 1)
                         if [x.strip() for x in base[i:i + len(ANCHOR)]] == ANCHOR)
            altered[begin + ANCHOR.index(source)] = replacement
            variants.append(altered)
        variants.extend((base + base, transform(base)))
        for variant in variants:
            with self.subTest(length=len(variant)):
                with self.assertRaises(AbortCopyContractError):
                    transform(variant)

    def test_literal_layout_branches_and_read_write_callback_pcs(self):
        self.assertEqual(256, estimated_bytes())
        self.assertLessEqual(CODE_START + estimated_bytes(), CODE_LIMIT)
        lines = [line.strip() for line in ROUTINE]
        labels = {}; branches = []; reads = []; writes = []; pc = 0
        for line in lines:
            if not line or line.startswith('.'):
                continue
            if line.endswith(':'):
                labels[line[:-1]] = pc
                continue
            if line.startswith(('bcs ', 'bcc ', 'beq ', 'bne ')):
                branches.append((pc, line.split()[1])); pc += 2
            else:
                if line == 'lda.l $42D600':
                    pc += 4
                elif line.startswith('lda $C8'):
                    reads.append(CODE_START + pc + 3)
                    pc += 3
                elif line.startswith('sta $C0'):
                    writes.append(CODE_START + pc + 3)
                    pc += 3
                else:
                    pc += _asm_size(line)
        self.assertEqual(256, pc)
        self.assertEqual({'CaCopy': 0x39AE40, 'CaPhaseCheck': 0x39AE4A,
                          'CaFast': 0x39AE52, 'CaLoop': 0x39AE5C,
                          'CaDone': 0x39AF2A, 'CaFallback': 0x39AF38,
                          'CaCodeEnd': 0x39AF40},
                         {name: CODE_START + labels[name] for name in
                          ('CaCopy', 'CaPhaseCheck', 'CaFast', 'CaLoop',
                           'CaDone', 'CaFallback', 'CaCodeEnd')})
        self.assertEqual(3, len(branches))
        self.assertEqual([3, 3, 3], [labels[target] - (pc + 2)
                                     for pc, target in branches])
        self.assertEqual([0x39AE5F + 6 * i for i in range(32)], reads)
        self.assertEqual([0x39AE62 + 6 * i for i in range(32)], writes)

    def test_random_words_context_and_full_exit_state_match(self):
        rng = random.Random(0xAE40)
        for case in range(12):
            committed = [rng.randrange(65536) for _ in range(1024)]
            pending = [rng.randrange(65536) for _ in range(1024)]
            if case % 4 == 0:
                committed[0], committed[-1] = 0, 0xFFFF
            context = dict(a=rng.randrange(65536), x=rng.randrange(65536),
                           y=rng.randrange(65536), p=rng.randrange(256),
                           sp=rng.choice((0x1000, 0x1001, 0x1FFE, 0x1FFF,
                                          rng.randrange(0x1000, 0x2000))),
                           d=0x3400, dbr=rng.randrange(256),
                           dp70=rng.randrange(65536))
            refs = [rng.randrange(65536) for _ in range(768)]
            context['p'] &= 0xCF
            owner = (0, 1, 2, 3, 4, 5, 0xFFFF)[case % 7]
            with self.subTest(case=case):
                _assert_same(self, _reference(pending, committed, refs, **context),
                             _run_emitted(pending, committed, refs,
                                          owner=owner, **context))

    def test_decimal_context_is_restored_and_binary_adc_is_enforced(self):
        pending = [0xA55A] * 1024
        committed = [((i * 137) ^ 0xD00D) & MASK16 for i in range(1024)]
        refs = [0x8000 | (i * 17 & 0x7FFF) for i in range(768)]
        context = dict(p=0xCD, sp=0x1000, d=0x3400, dbr=0x7E)
        _assert_same(self, _reference(pending, committed, refs, **context),
                     _run_emitted(pending, committed, refs, owner=4, **context))
        without_cld = [line for line in ROUTINE if line.strip() != 'cld']
        with self.assertRaisesRegex(AssertionError, 'binary ADC requires CLD'):
            _run_emitted(pending, committed, refs, routine=without_cld,
                         owner=4, **context)

    def test_candidate_interleaving_is_explicitly_different_but_bytes_match(self):
        pending = [0x0000] * 1024
        committed = [((i * 251) ^ 0xA55A) & MASK16 for i in range(1024)]
        refs = [rng & MASK16 for rng in range(768)]
        reference = _reference(pending, committed, refs)
        candidate = _run_emitted(pending, committed, refs, owner=4)
        _assert_same(self, reference, candidate)
        self.assertNotEqual(reference['events'], candidate['events'])
        self.assertEqual([
            ('read', COMMITTED, committed[0] & 0xFF),
            ('read', COMMITTED + 1, committed[0] >> 8),
            ('write', PENDING, committed[0] & 0xFF),
            ('write', PENDING + 1, committed[0] >> 8),
        ], candidate['events'][:4])
        self.assertEqual(2048, len(candidate['reads']))
        self.assertEqual(2048, len(candidate['writes']))
        self.assertEqual('fast', candidate['path'])

    def test_phase_gate_fast_only_for_owners_one_through_four(self):
        pending = [0xA55A] * 1024
        committed = [((i * 193) ^ 0x817F) & MASK16 for i in range(1024)]
        refs = [((i * 29) ^ 0xF000) & MASK16 for i in range(768)]
        for owner in (0, 1, 2, 3, 4, 5, 0xFFFF):
            with self.subTest(owner=owner):
                expected = _reference(pending, committed, refs)
                actual = _run_emitted(pending, committed, refs, owner=owner)
                _assert_same(self, expected, actual)
                if 1 <= owner <= 4:
                    self.assertEqual('fast', actual['path'])
                    self.assertNotEqual(expected['events'], actual['events'])
                else:
                    self.assertEqual('fallback', actual['path'])
                    self.assertEqual(expected['events'], actual['events'])


if __name__ == '__main__':
    unittest.main()
