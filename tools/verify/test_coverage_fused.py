"""Instruction-level tests for the fused exact-coverage overlay."""
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'bor_compile'))

from coverage_fused import (
    ANCHOR, CODE_LIMIT, CODE_START, ROUTINE, CoverageFusedContractError,
    transform,
)


def _u16(value):
    return value & 0xFFFF


class _Restricted65816:
    """Small interpreter for the emitted routine's instruction subset.

    OnlineRowPointers is a boundary hook: the test seeds its documented DP
    outputs ($08/$0A/$46/$48/$54/$56). Every emitted FcCoverage instruction
    after that call executes in this interpreter.
    """
    def __init__(self, rows, source_base=0xF40000, source_index=0,
                 foreground_base=0x120000, stride=4, height=8, row=0):
        self.mem = bytearray(1 << 24)
        self.dp = {}
        self.a = self.x = self.y = 0
        self.a8 = False
        self.c = self.z = self.n = False
        self.source_base = source_base
        self.source_index = source_index
        self.foreground_base = foreground_base
        self.stride = stride
        self.height = height
        self.row = row
        self.rows = rows
        self.dp.update({
            0x08: foreground_base & 0xFFFF,
            0x0A: (foreground_base >> 16) & 0xFF,
            0x46: height,
            0x48: stride,
            0x54: source_index,
            0x56: row,
            0x58: 0,
            0x32: 0,
        })
        for i, (alpha, available) in enumerate(rows):
            self.mem[(source_base + source_index + i) & 0xFFFFFF] = alpha & 0xFF
            address = (foreground_base + i * stride) & 0xFFFFFF
            self.mem[address] = available & 0xFF
            self.mem[(address + 1) & 0xFFFFFF] = (available >> 8) & 0xFF

    def _read8(self, addr):
        return self.mem[addr & 0xFFFFFF]

    def _read16(self, addr):
        return self._read8(addr) | (self._read8(addr + 1) << 8)

    def _dpget(self, addr):
        return self.dp.get(addr, 0) & 0xFFFF

    def _load(self, value):
        value &= 0xFF if self.a8 else 0xFFFF
        if self.a8:
            self.a = (self.a & 0xFF00) | value
        else:
            self.a = value
        self._flags(self.a)

    def _flags(self, value):
        value &= 0xFF if self.a8 else 0xFFFF
        self.z = value == 0
        self.n = bool(value & (0x80 if self.a8 else 0x8000))

    @staticmethod
    def _num(token):
        token = token.strip()
        return int(token[1:], 16) if token.startswith('$') else int(token, 10)

    def _get_dp_or_imm(self, token):
        token = token.strip()
        if token.startswith('#'):
            return self._num(token[1:])
        return self._dpget(self._num(token))

    def run(self, routine=ROUTINE):
        code, labels = [], {}
        for line in routine:
            stripped = line.strip()
            if not stripped or stripped.startswith('.'):
                continue
            if stripped.endswith(':'):
                labels[stripped[:-1].lower()] = len(code)
            else:
                code.append(stripped)
        pc = labels['fccoverage']
        steps = 0
        while True:
            steps += 1
            if steps > 10000:
                raise AssertionError('instruction loop did not terminate')
            ins = code[pc].lower()
            pc += 1
            op, _, arg = ins.partition(' ')
            arg = arg.strip()
            if op == 'jsr':
                if arg != 'onlinerowpointers':
                    raise AssertionError('unexpected call: ' + ins)
            elif op in ('lda', 'lda.l'):
                if arg.startswith('#'):
                    v = self._num(arg[1:])
                elif arg.startswith('$f40000,x'):
                    v = self._read8(0xF40000 + self.x)
                elif arg.startswith('[$08],y'):
                    ptr = self._dpget(8) | ((self._dpget(10) & 0xFF) << 16)
                    v = self._read16(ptr + self.y)
                elif arg.startswith('$'):
                    v = self._dpget(self._num(arg))
                else:
                    raise AssertionError('unsupported LDA: ' + ins)
                self._load(v)
            elif op in ('ldx', 'ldy'):
                v = self._get_dp_or_imm(arg)
                if op == 'ldx':
                    self.x = _u16(v)
                else:
                    self.y = _u16(v)
            elif op == 'sta':
                addr = self._num(arg)
                self.dp[addr] = self.a & (0xFF if self.a8 else 0xFFFF)
            elif op == 'sep':
                if self._num(arg[1:]) & 0x20:
                    self.a8 = True
            elif op == 'rep':
                if self._num(arg[1:]) & 0x20:
                    self.a8 = False
            elif op == 'and':
                if arg == '[$08],y':
                    ptr = self._dpget(8) | ((self._dpget(10) & 0xFF) << 16)
                    rhs = self._read16(ptr + self.y)
                else:
                    rhs = self._get_dp_or_imm(arg)
                self.a &= rhs
                self.a &= 0xFFFF
                self._flags(self.a)
            elif op == 'ora':
                self.a |= self._get_dp_or_imm(arg)
                self.a &= 0xFFFF
                self._flags(self.a)
            elif op == 'eor':
                self.a ^= self._get_dp_or_imm(arg)
                self.a &= 0xFFFF
                self._flags(self.a)
            elif op == 'xba':
                self.a = ((self.a << 8) | (self.a >> 8)) & 0xFFFF
                self._flags(self.a)
            elif op == 'clc':
                self.c = False
            elif op == 'adc':
                rhs = self._get_dp_or_imm(arg)
                mask = 0xFF if self.a8 else 0xFFFF
                total = (self.a & mask) + rhs + int(self.c)
                self.c = total > mask
                self._load(total & mask)
            elif op == 'cmp':
                rhs = self._get_dp_or_imm(arg)
                mask = 0xFF if self.a8 else 0xFFFF
                lhs = self.a & mask
                self.c = lhs >= rhs
                self.z = lhs == rhs
                self.n = bool((lhs - rhs) & (0x80 if self.a8 else 0x8000))
            elif op == 'inc':
                addr = self._num(arg)
                self.dp[addr] = _u16(self._dpget(addr) + 1)
                self.z = self.dp[addr] == 0
                self.n = bool(self.dp[addr] & 0x8000)
            elif op in ('bra', 'bcs', 'bcc', 'bne', 'bmi'):
                take = (True if op == 'bra' else
                        {'bcs': self.c, 'bcc': not self.c,
                         'bne': not self.z, 'bmi': self.n}[op])
                if take:
                    pc = labels[arg]
            elif op == 'rts':
                return self.a & 0xFFFF, self.dp[0x58], self.dp
            else:
                raise AssertionError('unsupported instruction: ' + ins)


class CoverageFusedTests(unittest.TestCase):
    def test_instruction_execution_matches_per_pixel_oracle_alignments_and_clipping(self):
        rng = random.Random(0xFC740)
        source = [rng.randrange(256) for _ in range(8)]
        # 1 bits in alpha mean transparent; foreground 1 bits mean available.
        available = [rng.randrange(65536) for _ in range(16)]
        for ox in range(-7, 8):
            for oy in range(-7, 8):
                source_index = max(0, -oy)
                start_row = max(0, oy)
                run_rows = []
                for step in range(8):
                    sy = source_index + step
                    screen_y = start_row + step
                    # Map each source pixel through the requested horizontal
                    # alignment into a 16-bit foreground row, independently
                    # of the assembly mask construction.
                    word = 0
                    # A deterministic open/occluded pattern over the screen
                    # positions; lower byte lanes are source pixel positions.
                    for sx in range(8):
                        target_x = sx + ox
                        lane = target_x + 7
                        if (0 <= target_x < 8 and screen_y < 8
                                and 0 <= lane < 16
                                and ((available[screen_y] >> lane) & 1)):
                            word |= 1 << sx
                    alpha = source[sy] if sy < 8 else 0xFF
                    run_rows.append((alpha, word))
                cpu = _Restricted65816(
                    run_rows, source_index=source_index,
                    foreground_base=0x12FFF8, stride=3, height=8,
                    row=source_index,
                )
                result, visited, _ = cpu.run()
                expected = False
                expected_visits = 8
                for step in range(8):
                    sy = source_index + step
                    screen_y = start_row + step
                    if sy >= 8 or screen_y >= 8:
                        continue
                    alpha = source[sy]
                    # oracle evaluates source pixels against the projected
                    # foreground row; it does not reduce emitted row words.
                    for sx in range(8):
                        target_x = sx + ox
                        lane = sx + ox + 7
                        if (0 <= target_x < 8 and 0 <= lane < 16
                                and not ((alpha >> sx) & 1)
                                and ((available[screen_y] >> lane) & 1)):
                            expected = True
                            expected_visits = step + 1
                            break
                    if expected:
                        break
                self.assertEqual((bool(result), visited), (expected, expected_visits),
                                 (ox, oy, run_rows[:2], source[source_index:source_index + 2],
                                  available[start_row:start_row + 2]))

    def test_first_last_and_no_hit_row_counts(self):
        base = [(0xFF, 0)] * 8
        rows = list(base)
        rows[0] = (0x00, 0x0001)
        self.assertEqual(_Restricted65816(rows).run()[:2], (1, 1))
        rows = list(base)
        rows[7] = (0x00, 0x0080)
        self.assertEqual(_Restricted65816(rows).run()[:2], (1, 8))
        self.assertEqual(_Restricted65816(base).run()[:2], (0, 8))
        # A negative row is clipped as unsigned >= height; stepping wraps it
        # to row zero without advancing the foreground pointer.
        negative = [(0xFF, 0x0001), (0x00, 0)] + [(0xFF, 0)] * 6
        result, visited, dp = _Restricted65816(negative, row=-1).run()
        self.assertEqual((result, visited), (1, 2))
        self.assertEqual(dp[8] | ((dp[10] & 0xFF) << 16), 0x120000)

    def test_foreground_occlusion_transparency_and_source_pointer_carry(self):
        # Foreground zeros occlude every opaque source bit.
        opaque_occluded = [(0x00, 0)] * 8
        result, visited, dp = _Restricted65816(
            opaque_occluded, foreground_base=0x12FFFC, stride=4
        ).run()
        self.assertEqual((result, visited), (0, 8))
        # Confirm the inline long pointer advances across $xx:ffff correctly.
        self.assertEqual((dp[8] | ((dp[10] & 0xFF) << 16)), 0x13001C)
        # Transparent source over all-available foreground remains clear.
        transparent = [(0xFF, 0xFFFF)] * 8
        self.assertEqual(_Restricted65816(transparent).run()[:2], (0, 8))

    def test_xba_duplicate_mask_hits_upper_byte_and_rejects_clear_or_transparent_lanes(self):
        rows = [(0xFF, 0)] * 8
        rows[0] = (0xFE, 0x0100)
        self.assertEqual(_Restricted65816(rows).run()[:2], (1, 1))

        # The inverted source byte is duplicated by XBA/ORA, so bit 8 can
        # match; without foreground availability, or with alpha bit 0 set
        # (transparent), that same high lane must remain clear.
        occluded = [(0xFF, 0)] * 8
        occluded[0] = (0xFE, 0)
        self.assertEqual(_Restricted65816(occluded).run()[:2], (0, 8))
        transparent = [(0xFF, 0)] * 8
        transparent[0] = (0xFF, 0x0100)
        self.assertEqual(_Restricted65816(transparent).run()[:2], (0, 8))

    def test_fully_clipped_zero_height_and_negative_eight_preserve_dead_dp(self):
        opaque_available = [(0x00, 0xFFFF)] * 8
        for height, row in ((8, 8), (0, 0), (8, -8)):
            with self.subTest(height=height, row=row):
                cpu = _Restricted65816(opaque_available, height=height, row=row)
                cpu.dp[0x0C] = 0xCAFE
                cpu.dp[0x0E] = 0xBEEF
                before = dict(cpu.dp)
                result, visited, after = cpu.run()
                self.assertEqual((result, visited), (0, 8))
                self.assertEqual(after[0x0C], before[0x0C])
                self.assertEqual(after[0x0E], before[0x0E])
                allowed_writes = {0x08, 0x0A, 0x32, 0x54, 0x56, 0x58}
                changed = {key for key in set(before) | set(after)
                           if before.get(key) != after.get(key)}
                self.assertLessEqual(changed, allowed_writes)

    def test_transform_retargets_only_exact_anchor_and_preserves_routines(self):
        fixture = [
            *ANCHOR,
            'EcCoverage:', ' rts', 'OnlineCoverage:', ' rts',
            'Other:', ' jsr EcCoverage', ' rts',
        ]
        rewritten = transform(fixture)
        call = ANCHOR.index('jsr EcCoverage')
        expected = fixture.copy()
        expected[call] = 'jsr FcCoverage'
        self.assertEqual(rewritten[:len(fixture)], expected)
        self.assertEqual(rewritten[-len(ROUTINE):], ROUTINE)
        self.assertEqual(transform(fixture, enabled=False), fixture)
        self.assertEqual(CODE_START, 0x39A740)
        self.assertEqual(CODE_LIMIT, 0x39B000)

    def test_transform_rejects_missing_duplicate_and_rewritten_anchors(self):
        fixture = [*ANCHOR, 'EcCoverage:', ' rts', 'OnlineCoverage:', ' rts']
        altered = fixture.copy()
        altered[ANCHOR.index('jsr EcCoverage')] = 'jsr OnlineCoverage'
        cases = (
            altered,
            fixture + fixture,
            [*ANCHOR[:ANCHOR.index('jsr EcCoverage')], 'jsr FcCoverage',
             *ANCHOR[ANCHOR.index('jsr EcCoverage') + 1:],
             'EcCoverage:', ' rts', 'OnlineCoverage:', ' rts'],
        )
        for case in cases:
            with self.subTest(case=case[:5]):
                with self.assertRaises(CoverageFusedContractError):
                    transform(case)


if __name__ == '__main__':
    unittest.main()
