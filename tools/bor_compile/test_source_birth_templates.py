from pathlib import Path
import struct
import unittest
import zlib
from compiler import Source
from source_birth_templates import derive,pack,unpack,STRIDE,loader_speed
from fractions import Fraction
from source_world_pool import empty_pool,descriptor,FIRST_UNUSED,SIDE_BASE,SIDE_STRIDE,CAPACITY


class BirthTemplates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=derive(Source(Path(__file__).resolve().parents[2]/'Masters of the Universe [v.3.0 Build 4086].pak'))

    def test_source_initialization_and_rejections(self):
        rows={m['identity']:m for m in self.report['models']}
        breath=rows['HBreath']
        self.assertTrue(breath['admitted'])
        self.assertEqual((breath['maxhealth'],breath['alpha'],breath['initial_animation_id'],breath['lifespan_ticks'],breath['initial_delay_ticks']),
                         (0,1,0,300,6))
        self.assertIn('INITIAL_FRAME_SIDE_EFFECT_UNBOUND',rows['HWWind']['rejections'])
        self.assertIn('INITIAL_CALLBACK_OWNER_UNBOUND',rows['SkTorn']['rejections'])
        self.assertIn('TYPE_SPECIFIC_INITIALIZATION_UNBOUND',rows['Knightbot']['rejections'])
        self.assertEqual(rows['Shock']['lifespan_ticks'],0x7fffffff)
        self.assertEqual(breath['model_speed_q16'],0)
        # Authored SPEED 8 becomes 0.8 through the pinned loader's /10 rule.
        self.assertEqual(rows['Knightbot']['model_speed_q16'],8*65536//10)

    def test_checked_immutable_table(self):
        table=pack(self.report);self.assertEqual(unpack(table),16)
        bad=bytearray(table);bad[-1]^=1
        with self.assertRaises(ValueError):unpack(bad)
        bad=bytearray(table);bad[24+16]=1
        struct.pack_into('<I',bad,16,zlib.crc32(bad[24:])&0xffffffff)
        with self.assertRaisesRegex(ValueError,'PROPERTY_TYPE'):unpack(bad)
        self.assertEqual(len(table),24+16*STRIDE)

    def test_stable_pool_identity_and_bounds(self):
        pool,sides=empty_pool();self.assertEqual(len(pool),128*80);self.assertEqual(len(sides),128*64)
        self.assertEqual(FIRST_UNUSED,SIDE_BASE+SIDE_STRIDE*CAPACITY)
        tokens=[struct.unpack_from('<I',pool,n*80)[0] for n in range(128)]
        self.assertEqual(len(set(tokens)),128)
        self.assertEqual(tokens[:2],[0x414000,0x414050])
        for n in range(128):self.assertEqual(pool[n*80+4:n*80+8],bytes(4))
        self.assertEqual(len(descriptor(128,0x268000,16,2584)),22)
        with self.assertRaises(ValueError):empty_pool(129)
        with self.assertRaises(ValueError):descriptor(128,0x26fff0,16,2584)

    def test_loader_speed_units_clamps_and_source_order(self):
        def rows(*pairs):return [dict(directive=k,values=[v]) for k,v in pairs]
        self.assertEqual(loader_speed([]),0)
        self.assertEqual(loader_speed(rows(('speed','8'))),Fraction(4,5))
        self.assertEqual(loader_speed(rows(('speed','-10'))),Fraction(1,2))
        self.assertEqual(loader_speed(rows(('speed','9999'))),30)
        self.assertEqual(loader_speed(rows(('speed','8'),('speedf','-2'))),-2)
        self.assertEqual(loader_speed(rows(('speedf','-2'),('speed','8'))),Fraction(4,5))


if __name__=='__main__':unittest.main()
