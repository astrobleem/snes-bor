from pathlib import Path
import struct
import unittest
from compiler import Source
from source_animation_step import Animation, decide, derive, pack, unpack, NONE, FRAME, STOP, KILL


class SourceAnimationStep(unittest.TestCase):
    def test_equality_and_stop_do_not_change_frame(self):
        a = Animation(40)
        self.assertEqual(decide(a, 39, 1, 240, 240), (STOP, 39))
        self.assertEqual(decide(a, 39, 1, 240, 241), (NONE, 39))
        self.assertEqual(decide(a, 0, -1, 0, 0, 2), (KILL, 0))
        self.assertEqual(decide(a, 2, 0, 0, 0), (NONE, 2))
        self.assertEqual(decide(a, 3, 1, 0xffffffff, 0xffffffff), (FRAME, 4))

    def test_loop_break_and_reverse_are_distinct(self):
        a = Animation(18, 1, 3, 17)
        self.assertEqual(decide(a, 16, 1, 0, 0), (FRAME, 3))
        self.assertEqual(decide(a, 0, -1, 0, 0), (STOP, 0))
        self.assertEqual(decide(a, 17, 1, 0, 0, 1), (KILL, 17))
        self.assertEqual(decide(Animation(18, 1), 0, -1, 0, 0), (FRAME, 17))
        self.assertEqual(decide(Animation(18, 1, 3), 0, -1, 0, 0), (FRAME, 3))
        self.assertEqual(decide(Animation(18, 0, 3, 17), 16, 1, 0, 0), (FRAME, 17))

    def test_invalid_descriptor_rejected(self):
        for a in (Animation(0), Animation(3, 1, 3), Animation(3, 1, 0, 4)):
            with self.assertRaises(ValueError): decide(a, 0, 1, 0, 0)
        with self.assertRaises(ValueError): decide(Animation(3), 0, 2, 0, 0)

    def test_source_timing_and_handles(self):
        r = derive(Source(Path(__file__).resolve().parents[2] / 'Masters of the Universe [v.3.0 Build 4086].pak'))
        rows = {(a['model'], a['role']): a for a in r['animations']}
        breath = rows['HBreath', 'idle']
        self.assertEqual((breath['count'], breath['loop_mode'], breath['delays']), (40, 0, [6] * 40))
        sk = rows['Skeletor', 'attack1']
        self.assertEqual((sk['count'], sk['loop_mode'], sk['loop_min'], sk['loop_max']), (18, 1, 3, 17))
        table = pack(r)
        self.assertEqual(len(unpack(table)), 80)
        with self.assertRaises(ValueError): unpack(table[:-1])
        with self.assertRaises(ValueError): unpack(table + bytes(2))
        bad = bytearray(table); struct.pack_into('<H', bad, 8 + 12, 0)
        with self.assertRaises(ValueError): unpack(bad)
        self.assertEqual(struct.unpack_from('<4sHH', table), (b'B4AT', 1, 80))
        for n, a in enumerate(r['animations']):
            h, aid, count, mode, lo, hi, offset, reserved = struct.unpack_from('<HHHhhhHH', table, 8 + n * 16)
            self.assertEqual((h, aid, count, mode, lo, hi, reserved),
                (a['handle'], a['engine_animation_id'], a['count'], a['loop_mode'], a['loop_min'], a['loop_max'], 0))
            self.assertEqual(list(struct.unpack_from('<' + 'H' * count, table, offset)), a['delays'])


if __name__ == '__main__': unittest.main()
