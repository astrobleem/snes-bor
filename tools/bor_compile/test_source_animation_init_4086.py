import struct,unittest
from pathlib import Path
from compiler import Source
from source_animation_init_4086 import derive,pack


class AnimationInit(unittest.TestCase):
    def test_authored_input_pairing_and_capacity(self):
        report=derive(Source(Path(__file__).resolve().parents[2]/'Masters of the Universe [v.3.0 Build 4086].pak'))
        data=pack(report)
        self.assertEqual(struct.unpack_from('<4s6H',data),(b'B4AI',1,80,168,8,16,0))
        self.assertEqual([a['handle'] for a in report['animations'] if a['sync']>=0],[7,26,53,75])
        self.assertEqual(sum(a['numframes'] for a in report['animations']),836)
        for i,a in enumerate(report['animations']):
            self.assertEqual(struct.unpack_from('<HHhH',data,16+8*i),(a['handle'],a['numframes'],a['sync'],a['engine_animation_id']))
        with self.assertRaisesRegex(ValueError,'ANIMATION_INIT_ROW_DOMAIN'):
            pack(dict(report,animations=[dict(report['animations'][0],sync=168)]))
        with self.assertRaisesRegex(ValueError,'ANIMATION_INIT_CAPACITY'):
            pack(dict(report,maximum_animations=1025))


if __name__=='__main__':unittest.main()
