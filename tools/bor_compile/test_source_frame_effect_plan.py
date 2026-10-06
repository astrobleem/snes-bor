import json,struct,unittest,zlib
from pathlib import Path
from unittest.mock import patch
from compiler import Source
from source_frame_effects_4086 import derive as effects,pack as pack_effects,unpack as unpack_effects
from source_frame_effect_plan import derive,pack,unpack,Op,update_frame_with_plan
import source_update_frame_authority as authority


class FrameEffectPlan(unittest.TestCase):
    def test_plan_execution_matches_verbatim_pinned_engine_corpus(self):
        path=Path(__file__).resolve().parents[2]/'out/byor-motu-update-frame-authority/report.json'
        r=json.loads(path.read_text());self.assertEqual(r['status'],'PASS')
        self.assertEqual(r['functions_sha256'],'72d75ee216c7c00ceb01f6f811b77184dda3a8f22f0174b7f0be6e35205183d7')
        with patch.object(authority,'update_frame',update_frame_with_plan):
            for case in r['results']:
                actual=case['actual'];expected=authority.expected(case['case'])
                self.assertEqual(expected,actual,case['case'])

    def test_every_authored_frame_pairs_with_fe_and_preserves_media_admission(self):
        e=effects(Source(Path(__file__).resolve().parents[2]/'Masters of the Universe [v.3.0 Build 4086].pak'));r=derive(e);fe=pack_effects(e);table=pack(r)
        self.assertEqual(unpack(table,fe),r['animations']);self.assertEqual(len(r['animations']),80)
        self.assertEqual(sum(len(a['frames']) for a in r['animations']),836)
        numeric=unpack_effects(fe)
        for plan,frames in zip(r['animations'],numeric['animations']):
            for row,frame in zip(plan['frames'],frames['frames']):
                self.assertEqual(Op.SOUND in row['ops'],frame['sound_index']>=0)
                self.assertEqual(row['ops'][-1],Op.RESTORE_SELF)
        with self.assertRaisesRegex(ValueError,'PAIRING'):unpack(table,fe+b'wrong')
        broken=bytearray(table);broken[-1]=255;struct.pack_into('<I',broken,28,zlib.crc32(broken[32:])&0xffffffff)
        with self.assertRaisesRegex(ValueError,'OPCODE'):unpack(broken,fe)


if __name__=='__main__':unittest.main()
