import unittest
from pathlib import Path
import struct
from fractions import Fraction
from compiler import Source
from source_frame_state_4086 import loader_frames,derive,pack,unpack,FIELDS,MEDIA_FIELDS


def rows(text):
    return [dict(directive=s.split()[0],values=s.split()[1:],line=n+1)
            for n,s in enumerate(text.strip().splitlines())]


class SourceFrameState(unittest.TestCase):
    def test_persistent_depth_loader_order(self):
        f=loader_frames(rows('''anim idle
offset 4 10
bbox 5 12 8 20 2 6
attack 7 14 12 30 5
attackz 2 6
frame one.png
frame two.png'''))[0]['frames']
        self.assertEqual(f[0]['bbox'],[1,2,9,22,2,6])
        self.assertEqual(f[1]['bbox'],[1,2,9,22,-8,-4])
        self.assertEqual(f[0]['attack']['attack_coords'],[3,4,15,34,-8,-4])
        self.assertEqual(f[1]['attack']['attack_coords'],[3,4,15,34,-18,-14])

    def test_freeze_persists_until_anim_reset_and_empty_attack_is_absent(self):
        a=loader_frames(rows('''anim attack1
delay 3
freeze 1 2 3 4 10 0.5
frame one.png
attack 1 2 3 4 4
frame two.png
attack 0 0 0 0
frame three.png
anim idle
attack 1 2 3 4 2
frame four.png'''))
        self.assertEqual(a[0]['frames'][0]['attack']['freezetime'],100)
        self.assertEqual(a[0]['frames'][1]['attack']['freeze'],1)
        self.assertEqual(a[0]['frames'][1]['attack']['attack_type'],0)
        self.assertIsNone(a[0]['frames'][2]['attack'])
        self.assertEqual(a[1]['frames'][0]['attack']['freeze'],0)
        self.assertEqual(a[1]['frames'][0]['delay_ticks'],6)
        self.assertEqual(a[1]['frames'][0]['offset'],[0,0])

    def test_attack_command_restores_default_drop_velocity(self):
        f=loader_frames(rows('''anim idle
attack 0 0 4 5 2
dropv 4 0 0
frame one.png
attack2 0 0 4 5 3
frame two.png'''))[0]['frames']
        self.assertEqual(f[0]['attack']['dropv'],['4','0','0'])
        self.assertEqual(f[1]['attack']['dropv'],['3','1.2','0'])
        self.assertEqual(f[1]['attack']['attack_type'],1)

    def test_unsupported_variant_does_not_alias(self):
        for name in ('blast','attack11'):
            with self.assertRaises(ValueError):
                loader_frames(rows('anim idle\n'+name+' 0 0 4 5\nframe one.png'))
        with self.assertRaises(ValueError):
            loader_frames(rows('anim idle\nfreeze 0 0 4 5 1 0.0001\nframe one.png'))

    def test_all_source_frames_roundtrip_and_corrupt_descriptors(self):
        report=derive(Source(Path(__file__).resolve().parents[2]/'Masters of the Universe [v.3.0 Build 4086].pak'))
        binary=pack(report); decoded=unpack(binary)
        self.assertLessEqual(len(binary),32768)
        self.assertEqual(len(decoded['animations']),80)
        for source,compiled in zip(report['animations'],decoded['animations']):
            self.assertEqual(source['handle'],compiled['handle'])
            self.assertEqual(len(source['frames']),len(compiled['frames']))
            for f,c in zip(source['frames'],compiled['frames']):
                self.assertEqual((f['offset'],f['delay_ticks']),(c['offset'],c['delay_ticks']))
                self.assertEqual(f['bbox'],decoded['boxes'][c['bbox_index']-1] if c['bbox_index'] else None)
                if f['attack'] is None:
                    self.assertEqual(c['attack_index'],0); continue
                a=decoded['attacks'][c['attack_index']-1]
                for name in FIELDS+['attack_coords','staydown']: self.assertEqual(f['attack'][name],a[name])
                for name,index in zip(MEDIA_FIELDS,a['media_indices']):
                    self.assertEqual(f['attack'][name],decoded['media'][index-1] if index else None)
                expected=[struct.unpack('<f',struct.pack('<f',float(Fraction(n))))[0] for n in f['attack']['dropv']]
                self.assertEqual(expected,a['dropv'])
        for invalid in (binary[:-1],binary+b'\0'):
            with self.assertRaises(ValueError): unpack(invalid)
        bad=bytearray(binary);struct.pack_into('<H',bad,20,0)
        with self.assertRaises(ValueError): unpack(bad)
        bad=bytearray(binary);struct.pack_into('<H',bad,16+80*8+8,65535)
        with self.assertRaises(ValueError): unpack(bad)


if __name__=='__main__': unittest.main()
