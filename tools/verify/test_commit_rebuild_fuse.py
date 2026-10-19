"""Independent model and emitted-instruction interpreter for commit/RF fuse."""
from __future__ import annotations

from pathlib import Path
import random
import unittest

from commit_rebuild_fuse import (
    ANCHOR,
    CODE_LIMIT,
    CODE_START,
    ROUTINE,
    CommitRebuildFuseContractError,
    estimated_bytes,
    transform,
)


MASK16 = 0xFFFF
MAP = 0x42C000
COMMITTED = 0x42C800
REFS = 0x42D000
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
    result = (left - right) & MASK16
    p = _nz(p, result)
    if left >= right:
        p |= 1
    else:
        p &= ~1
    return p


def _state(maps: list[int], refs: list[int], committed: list[int], *,
           a=0xA55A, x=0x6B4D, y=0x39C3, p=0xCD,
           sp=0x1800, d=0x3400, dbr=0x7E, dp70=0x55AA) -> dict:
    return dict(a=a & MASK16, x=x & MASK16, y=y & MASK16, p=p & 0xCF,
                sp=sp & MASK16, d=d & MASK16, dbr=dbr & 0xFF,
                dp70=dp70 & MASK16,
                maps=[v & MASK16 for v in maps],
                committed=[v & MASK16 for v in committed],
                refs=[v & MASK16 for v in refs],
                map_writes=[], ref_writes=[], events=[],
                stack=[], stack_writes=[], terminal=None)


def _append_word_writes(s: dict, kind: str, address: int, value: int) -> None:
    target = s['map_writes'] if kind == 'map' else s['ref_writes']
    low_high = ((address, value & 0xFF), (address + 1, (value >> 8) & 0xFF))
    target.extend(low_high)
    s['events'].extend((kind, addr, byte) for addr, byte in low_high)


def _reference(maps: list[int], refs: list[int], committed: list[int], **context) -> dict:
    """Model original MVN copy, 768-word clear loop, and 1024-word RF loop."""
    s = _state(maps, refs, committed, **context)
    for index, value in enumerate(s['maps']):
        s['committed'][index] = value
        _append_word_writes(s, 'map', COMMITTED + 2 * index, value)
    for index in range(768):
        value = s['refs'][index] & 0x8000
        s['refs'][index] = value
        _append_word_writes(s, 'ref', REFS + 2 * index, value)
    for index, value in enumerate(s['maps']):
        slot = value
        s['refs'][slot] = (s['refs'][slot] + 1) & MASK16
        _append_word_writes(s, 'ref', REFS + 2 * slot, s['refs'][slot])
    s['a'] = s['refs'][s['maps'][-1]]
    s['x'] = s['maps'][-1] * 2
    s['y'] = 2048
    # Final accepted RF instruction is CPY #2048; no earlier instruction
    # changes V, D or I, and this compare establishes N=0, Z=1, C=1.
    s['p'] = _cmp(s['p'], 2048, 2048)
    s['terminal'] = 'RfContinue'
    return s


def _num(text: str) -> int:
    if text.startswith('$'):
        return int(text[1:], 16)
    return int(text, 0)


def _run_emitted(maps: list[int], refs: list[int], committed: list[int], *,
                 routine=None, **context) -> dict:
    """Interpret the emitted helper, including its stack/status and all writes."""
    s = _state(maps, refs, committed, **context)
    code = [line.strip() for line in (ROUTINE if routine is None else routine)]
    labels = {line[:-1]: i for i, line in enumerate(code) if line.endswith(':')}
    pc = labels['CfFuse'] + 1
    steps = 0

    def push(value: int) -> None:
        s['stack_writes'].append((s['sp'], value & 0xFF))
        s['sp'] = (s['sp'] - 1) & MASK16
        s['stack'].append(value & 0xFF)

    def pull() -> int:
        s['sp'] = (s['sp'] + 1) & MASK16
        return s['stack'].pop()

    def indexed_operand(op: str) -> tuple[int, str]:
        start = op.index('$')
        comma = op.index(',')
        return int(op[start + 1:comma], 16), op[comma + 1:]

    def read_word(base: int, index: int) -> int:
        address = base + index
        if 0xC000 <= address <= 0xC7FE and address % 2 == 0:
            return s['maps'][(address - 0xC000) // 2]
        if 0xC800 <= address <= 0xCFFE and address % 2 == 0:
            return s['committed'][(address - 0xC800) // 2]
        if 0xD000 <= address <= 0xD5FE and address % 2 == 0:
            return s['refs'][(address - 0xD000) // 2]
        raise AssertionError(f'bad absolute indexed read ${address:04X}')

    def write_word(base: int, index: int, value: int) -> None:
        address = base + index
        value &= MASK16
        if 0xC800 <= address <= 0xCFFE and address % 2 == 0:
            slot = (address - 0xC800) // 2
            s['committed'][slot] = value
            _append_word_writes(s, 'map', COMMITTED + 2 * slot, value)
        elif 0xD000 <= address <= 0xD5FE and address % 2 == 0:
            slot = (address - 0xD000) // 2
            s['refs'][slot] = value
            _append_word_writes(s, 'ref', REFS + 2 * slot, value)
        else:
            raise AssertionError(f'bad absolute indexed write ${address:04X}')

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
            push(0x42); push(0x42)
        elif op == 'plb':
            s['dbr'] = pull()
            s['p'] = _nz(s['p'], s['dbr'], 8)
        elif op == 'plp':
            s['p'] = pull()
        elif op == 'cld':
            s['p'] &= ~0x08
        elif op == 'ldx #0':
            s['x'] = 0; s['p'] = _nz(s['p'], s['x'])
        elif op == 'ldy #2048':
            s['y'] = 2048; s['p'] = _nz(s['p'], s['y'])
        elif op == 'txa':
            s['a'] = s['x']; s['p'] = _nz(s['p'], s['a'])
        elif op == 'tax':
            s['x'] = s['a']; s['p'] = _nz(s['p'], s['x'])
        elif op == 'tyx':
            s['x'] = s['y']; s['p'] = _nz(s['p'], s['x'])
        elif op == 'tay':
            s['y'] = s['a']; s['p'] = _nz(s['p'], s['y'])
        elif op == 'clc':
            s['p'] &= ~1
        elif op.startswith('adc #'):
            if s['p'] & 0x08:
                raise AssertionError('binary ADC requires CLD')
            operand = _num(op[5:]); left = s['a']; carry = s['p'] & 1
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
        elif op.startswith('lda $') and op.endswith((',x', ',y')):
            base, reg = indexed_operand(op)
            if s['dbr'] != 0x42:
                raise AssertionError('helper must select DBR $42')
            index = s['x'] if reg == 'x' else s['y']
            s['a'] = read_word(base, index); s['p'] = _nz(s['p'], s['a'])
        elif op.startswith('sta $') and op.endswith((',x', ',y')):
            base, reg = indexed_operand(op)
            if s['dbr'] != 0x42:
                raise AssertionError('helper must select DBR $42')
            index = s['x'] if reg == 'x' else s['y']
            write_word(base, index, s['a'])
        elif op == 'and #$8000':
            s['a'] &= 0x8000; s['p'] = _nz(s['p'], s['a'])
        elif op == 'asl a':
            carry = bool(s['a'] & 0x8000)
            s['a'] = (s['a'] << 1) & MASK16
            s['p'] = _nz(s['p'], s['a'])
            s['p'] = (s['p'] | 1) if carry else (s['p'] & ~1)
        elif op == 'inc a':
            s['a'] = (s['a'] + 1) & MASK16; s['p'] = _nz(s['p'], s['a'])
        elif op == 'cpx #1536':
            s['p'] = _cmp(s['p'], s['x'], 1536)
        elif op == 'cpx #2048':
            s['p'] = _cmp(s['p'], s['x'], 2048)
        elif op == 'cpy #2048':
            s['p'] = _cmp(s['p'], s['y'], 2048)
        elif op in ('bcs CfClearDone', 'bcs CfCountDone'):
            if s['p'] & 1:
                pc = labels[op.split()[1]] + 1
        elif op in ('jmp CfClearLoop', 'jmp CfCountLoop'):
            pc = labels[op.split()[1]] + 1
        elif op == 'jmp RfContinue':
            s['terminal'] = 'RfContinue'
            break
        else:
            raise AssertionError('unsupported emitted instruction: ' + op)
    else:
        raise AssertionError('emitted helper exceeded step bound')
    s['steps'] = steps
    return s


def _assert_same(test: unittest.TestCase, expected: dict, actual: dict) -> None:
    for key in ('a', 'x', 'y', 'p', 'sp', 'd', 'dbr', 'dp70',
                'maps', 'committed', 'refs', 'map_writes', 'ref_writes'):
        test.assertEqual(expected[key], actual[key], key)
    test.assertEqual('RfContinue', actual['terminal'])
    test.assertEqual([], actual['stack'])
    test.assertEqual(expected['sp'], actual['sp'])
    test.assertEqual(4, len(actual['stack_writes']))
    test.assertEqual(expected['sp'] - 3, min(addr for addr, _ in actual['stack_writes']))
    test.assertNotIn((actual['d'] + 0x70) & MASK16,
                     [addr for addr, _ in actual['stack_writes']])
    # The intended fused event order is: clear refs once, then for each map
    # word write committed bytes followed by that word's ref increment bytes.
    events = actual['events']
    test.assertTrue(all(kind == 'ref' for kind, _, _ in events[:1536]))
    cursor = 1536
    for index, _slot in enumerate(actual['maps']):
        map_low, map_high = actual['map_writes'][2 * index:2 * index + 2]
        ref_low, ref_high = actual['ref_writes'][1536 + 2 * index:1538 + 2 * index]
        expected_events = [
            ('map', map_low[0], map_low[1]), ('map', map_high[0], map_high[1]),
            ('ref', ref_low[0], ref_low[1]), ('ref', ref_high[0], ref_high[1]),
        ]
        test.assertEqual(expected_events, events[cursor:cursor + 4])
        cursor += 4
    test.assertEqual(cursor, len(events))


def _asm_size(line: str) -> int:
    line = line.strip()
    if line in ('php', 'phb', 'plb', 'plp', 'cld', 'txa', 'tax', 'tyx',
                'tay', 'asl a', 'inc a', 'clc'):
        return 1
    if line == 'pea $4242':
        return 3
    if line.startswith(('ldx #', 'ldy #', 'lda #', 'adc #', 'and #', 'cpx #', 'cpy #')):
        return 3
    if line.startswith(('lda $', 'sta $')) and line.endswith((',x', ',y')):
        return 3
    if line.startswith(('bcs ', 'bcc ', 'beq ', 'bne ')):
        return 2
    if line.startswith('jmp '):
        return 3
    raise AssertionError('unknown size-check instruction: ' + line)


class CommitRebuildFuseTests(unittest.TestCase):
    def _base(self) -> list[str]:
        return BASE_SOURCE.read_text().splitlines()

    def test_transform_changes_only_pinned_prefix_and_disabled_is_identity(self):
        base = self._base()
        changed = transform(base)
        self.assertEqual(base, transform(base, enabled=False))
        normalized = [line.strip() for line in base]
        start = next(i for i in range(len(normalized) - len(ANCHOR) + 1)
                     if normalized[i:i + len(ANCHOR)] == ANCHOR)
        patch = start + ANCHOR.index('phb')
        rewritten = [line.strip() for line in changed]
        self.assertEqual(['jmp CfFuse', 'nop'], rewritten[patch:patch + 2])
        self.assertEqual(normalized[:patch], rewritten[:patch])
        self.assertEqual(normalized[patch + 2:], rewritten[patch + 2:patch + 2 + len(normalized) - patch - 2])
        self.assertEqual(ROUTINE, changed[-len(ROUTINE):])

    def test_transform_rejects_anchor_drift_duplicates_and_reapplication(self):
        base = self._base()
        variants = []
        for source, replacement in (
            ('lda #2047', 'lda #2046'), ('mvn $42,$42', 'mvn $41,$42'),
            ('and #$8000', 'and #$7FFF'), ('bcc NbClearRefs', 'bcs NbClearRefs'),
            ('lda.l $42C000,x', 'lda.l $42C002,x'), ('asl a', 'lsr a'),
            ('cpy #2048', 'cpy #2047'), ('RfContinue:', 'RfNext:'),
        ):
            altered = base.copy()
            anchor_start = next(i for i in range(len(altered) - len(ANCHOR) + 1)
                                if [line.strip() for line in altered[i:i + len(ANCHOR)]] == ANCHOR)
            index = anchor_start + ANCHOR.index(source)
            altered[index] = replacement
            variants.append(altered)
        variants.extend((base + base, transform(base)))
        for variant in variants:
            with self.subTest(lines=len(variant)):
                with self.assertRaises(CommitRebuildFuseContractError):
                    transform(variant)

    def test_literal_layout_branch_ranges_and_observer_pcs(self):
        self.assertEqual(825, estimated_bytes())
        self.assertLess(CODE_START + estimated_bytes(), CODE_LIMIT)
        lines = [line.strip() for line in ROUTINE]
        labels = {}; branches = []; stores = {'clear': [], 'map': [], 'ref': []}; pc = 0
        for line in lines:
            if not line or line.startswith('.'):
                continue
            if line.endswith(':'):
                labels[line[:-1]] = pc
                continue
            if line.startswith(('bcs ', 'bcc ', 'beq ', 'bne ')):
                branches.append((pc, line.split()[1])); pc += 2
            else:
                if line.startswith('sta $D') and line.endswith(',x') and 'CfClearLoop' in labels:
                    stores['clear'].append(CODE_START + pc + 3)
                elif line.startswith('sta $C8'):
                    stores['map'].append(CODE_START + pc + 3)
                elif line == 'sta $D000,y':
                    stores['ref'].append(CODE_START + pc + 3)
                pc += _asm_size(line)
        self.assertEqual(825, pc)
        self.assertEqual({'CfFuse': 0x39AB00, 'CfClearLoop': 0x39AB0B,
                          'CfClearDone': 0x39AC39, 'CfCountLoop': 0x39AC3C,
                          'CfCountDone': 0x39AE2A, 'CfCodeEnd': 0x39AE39},
                         {name: CODE_START + labels[name] for name in
                          ('CfFuse', 'CfClearLoop', 'CfClearDone', 'CfCountLoop',
                           'CfCountDone', 'CfCodeEnd')})
        self.assertEqual(2, len(branches))
        for address, target in branches:
            displacement = labels[target] - (address + 2)
            self.assertEqual(3, displacement)
            self.assertLessEqual(abs(displacement), 127)
        self.assertEqual([0x39AB14 + 9 * i for i in range(32)], stores['clear'])
        self.assertEqual([0x39AC42 + 15 * i for i in range(32)], stores['map'])
        self.assertEqual([0x39AC4B + 15 * i for i in range(32)], stores['ref'])

    def test_random_valid_maps_refs_and_full_terminal_state_match(self):
        rng = random.Random(0xAB00)
        for case in range(20):
            maps = [rng.randrange(768) for _ in range(1024)]
            if case % 4 == 0:
                maps[0], maps[-1] = 0, 767
            elif case % 4 == 1:
                maps = [case % 768] * 1024
            elif case % 4 == 2:
                maps = [0 if i % 2 == 0 else 767 for i in range(1024)]
            refs = [rng.randrange(65536) for _ in range(768)]
            committed = [rng.randrange(65536) for _ in range(1024)]
            context = dict(a=rng.randrange(65536), x=rng.randrange(65536),
                           y=rng.randrange(65536), p=rng.randrange(256) & 0xCF,
                           sp=rng.randrange(0x1000, 0x2000), d=0x3400,
                           dbr=rng.randrange(256), dp70=rng.randrange(65536))
            with self.subTest(case=case):
                _assert_same(self, _reference(maps, refs, committed, **context),
                             _run_emitted(maps, refs, committed, **context))

    def test_decimal_context_is_restored_and_binary_adc_is_enforced(self):
        maps = [i % 768 for i in range(1024)]
        refs = [0x8000 | (i * 13 & 0x7FFF) for i in range(768)]
        committed = [0xA55A] * 1024
        context = dict(p=0xCD, sp=0x1800, d=0x3400, dbr=0x7E)
        _assert_same(self, _reference(maps, refs, committed, **context),
                     _run_emitted(maps, refs, committed, **context))
        without_cld = [line for line in ROUTINE if line.strip() != 'cld']
        with self.assertRaisesRegex(AssertionError, 'binary ADC requires CLD'):
            _run_emitted(maps, refs, committed, routine=without_cld, **context)

    def test_write_traces_match_original_per_resource_not_global_interleaving(self):
        maps = [0] * 512 + [767] * 512
        refs = [0x8000 | ((i * 31) & 0x7FFF) for i in range(768)]
        committed = [0xFFFF] * 1024
        expected = _reference(maps, refs, committed)
        actual = _run_emitted(maps, refs, committed)
        self.assertEqual(expected['map_writes'], actual['map_writes'])
        self.assertEqual(expected['ref_writes'], actual['ref_writes'])
        self.assertNotEqual(expected['events'], actual['events'])
        self.assertEqual(2048, len(actual['map_writes']))
        self.assertEqual(2 * (768 + 1024), len(actual['ref_writes']))


if __name__ == '__main__':
    unittest.main()
