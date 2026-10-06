import struct
import unittest
from source_script_input import authority,snapshot,query,emit_names,ADDRESS,FIRST_UNUSED


class ScriptInput(unittest.TestCase):
    def test_every_key_and_mode_returns_source_mask(self):
        rows=[(0x1fff,0x1dc0,0x003c),(0x80000000,0,0)]
        for key in authority()['keys']:
            for mode,mask in enumerate(rows[0]):
                self.assertEqual(query(rows,0,mode,key['name'].upper()),mask&key['mask'])
                self.assertEqual(query(rows,0,mode,key['selector']),mask&key['mask'])
            self.assertEqual(query(rows,0,-1,key['name']),rows[0][0]&key['mask'])
        self.assertEqual(query(rows,0,0,'attack'),64)
        self.assertEqual(query(rows,0,0,'attack4'),4096)
        self.assertEqual(query(rows,0,0,'attack','attack4'),4096)
        self.assertEqual(query(rows,0,1,'moveup','attack'),0)
        self.assertEqual(query(rows,1,0,'anybutton'),0)
        self.assertEqual(query(rows,0,0,'unknown'),0)
        with self.assertRaisesRegex(ValueError,'UNDEFINED'):query(rows,-1,0,'attack')

    def test_snapshot_preserves_full_source_flags_and_tick(self):
        data=snapshot([(0x80000004,0x80000000,4)]*4,0xffffffff)
        self.assertEqual(len(data),56)
        self.assertEqual(FIRST_UNUSED-ADDRESS,len(data))
        self.assertEqual(struct.unpack_from('<III',data,8),(0x80000004,0x80000000,4))
        self.assertEqual(struct.unpack_from('<I',data,4)[0],0xffffffff)
        self.assertEqual(len(emit_names().splitlines()),15)
        with self.assertRaises(ValueError):snapshot([(0,0,0)]*5,0)
        with self.assertRaises(ValueError):snapshot([(-1,0,0)],0)


if __name__=='__main__':unittest.main()
