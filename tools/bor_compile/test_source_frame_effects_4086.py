from pathlib import Path
import struct
import unittest
from compiler import Source
from source_frame_effects_4086 import derive,loader_frames,pack,unpack,validate_native_motion
from source_update_frame_authority import cases,expected


def rows(text):
    return [dict(directive=s.split()[0],values=s.split()[1:],line=i+1)
        for i,s in enumerate(text.strip().splitlines())]


class FrameEffects(unittest.TestCase):
    def test_movement_persists_sound_consumes_and_this_uses_next_frame(self):
        a=loader_frames(rows('''anim idle
move 300
sound hit.wav
frame one
frame two
move 0
jumpframe this 0 2 0
weaponframe 1 2
frame three
anim walk
frame four'''))
        self.assertEqual([f['move']['x'] for f in a[0]['frames']],[300,300,0])
        self.assertEqual([f['sound'] for f in a[0]['frames']],['hit.wav',None,None])
        self.assertEqual(a[0]['events']['jump_frame'],2)
        self.assertEqual(a[0]['events']['weapon_keep'],0)
        self.assertEqual(a[1]['frames'][0]['move'],dict(base=-1,x=0,y=0,z=0))

    def test_unsupported_legacy_jump_does_not_assume_explicit_velocity(self):
        with self.assertRaises(ValueError):loader_frames(rows('anim idle\njumpframe 0 2\nframe one'))

    def test_source_effects_roundtrip_missing_sound_and_corrupt_tables(self):
        r=derive(Source(Path(__file__).resolve().parents[2]/'Masters of the Universe [v.3.0 Build 4086].pak'))
        binary=pack(r);decoded=unpack(binary)
        self.assertEqual(validate_native_motion(binary)['frames'],836)
        self.assertLessEqual(len(binary),32768)
        self.assertEqual(len(r['animations']),80)
        self.assertEqual(sum(len(a['frames']) for a in r['animations']),836)
        models={n.lower():i for i,n in enumerate(r['models'])}
        from source_frame_effects_4086 import IDENTITY_FIELDS,NUMERIC_FIELDS
        for a,b in zip(sorted(r['animations'],key=lambda a:a['handle']),decoded['animations']):
            for name,value in a['events'].items():
                if name in IDENTITY_FIELDS:value=-1 if value is None else value if isinstance(value,int) else models[value.lower()]
                elif name in NUMERIC_FIELDS:value=int(value*65536)
                self.assertEqual(value,b['events'][name],(a['model'],a['role'],name))
            for f,g in zip(a['frames'],b['frames']):
                self.assertEqual(f['move'],g['move'])
                value=decoded['media'][g['sound_index']] if g['sound_index']>=0 else None
                self.assertEqual(None if f['sound_resolution']=='SOURCE_ASSET_MISSING' else f['sound'],value)
        by_id={(a['model'],a['role']):a for a in r['animations']}
        self.assertEqual(by_id['He_Man','freespecial']['events']['weapon_frame'],8)
        self.assertEqual(by_id['He_ManB','freespecial']['events']['weapon_frame'],7)
        self.assertTrue(any(f['sound_resolution']=='SOURCE_ASSET_MISSING' for a in r['animations'] for f in a['frames']))
        for bad in (binary[:-1],binary+b'\0',bytes(16)):
            with self.assertRaises(ValueError):unpack(bad)
        bad=bytearray(binary);struct.pack_into('<H',bad,20,0)
        with self.assertRaises(ValueError):unpack(bad)

    def test_callback_interruption_does_not_treat_killed_self_as_interrupted(self):
        c=next(c for c in cases() if c['mode']==3 and c['f']==1 and c['animating'])
        r=expected(c)
        self.assertIn(9,r['trace']);self.assertIn(10,r['trace'])
        self.assertEqual(r['state'][20],0)
        for mode in (1,2):
            c=dict(c,mode=mode);r=expected(c)
            self.assertEqual(r['trace'],[1]);self.assertEqual(r['state'][17],1)

    def test_native_motion_domain_checks_first_base_and_facing_negation(self):
        from copy import deepcopy
        a=loader_frames(rows('anim idle\nframe one\nseta 65536\nframe two'))[0]
        a['handle']=1;r=dict(models=[],animations=[a])
        self.assertEqual(validate_native_motion(pack(r))['frames'],2)
        for field,value in (('base',65536),('x',65536),('x',-32768),('y',-32769),('z',32768)):
            bad=deepcopy(r);bad['animations'][0]['frames'][0]['move'][field]=value
            with self.assertRaises(ValueError):validate_native_motion(pack(bad))


if __name__=='__main__':unittest.main()
