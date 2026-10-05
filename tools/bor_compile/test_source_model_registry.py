import unittest
import struct
from pathlib import Path
from compiler import Source
from source_model_registry import derive,pack,unpack,lookup,NULL_MODEL


class ModelRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=derive(Source(Path(__file__).resolve().parents[2]/'Masters of the Universe [v.3.0 Build 4086].pak'))
        cls.table=pack(cls.report)

    def test_source_identity_health_and_alpha_are_preserved(self):
        models=unpack(self.table);self.assertEqual(len(models),16)
        byname={m['lookup_name']:m for m in models}
        self.assertEqual(byname['he_man']['maxhealth'],150)
        self.assertEqual(byname['knightbot']['maxhealth'],70)
        self.assertEqual(byname['skeletor']['maxhealth'],400)
        self.assertEqual((byname['hbreath']['maxhealth'],byname['hbreath']['alpha']),(0,1))

    def test_loaded_state_casefold_and_absent_names_follow_findmodel(self):
        loaded=b'\xff\xff'
        identity=next(m['id'] for m in self.report['models'] if m['lookup_name']=='hbreath')
        self.assertEqual(lookup(self.table,loaded,'HBreath'),identity)
        self.assertEqual(lookup(self.table,loaded,'hBrEaTh'),identity)
        self.assertEqual(lookup(self.table,b'\0\0','HBreath'),NULL_MODEL)
        self.assertEqual(lookup(self.table,loaded,'missing'),NULL_MODEL)
        with self.assertRaisesRegex(ValueError,'LOADED_BITMAP'):lookup(self.table,b'\xff','HBreath')

    def test_corrupted_or_duplicate_records_fail_explicitly(self):
        bad=bytearray(self.table);bad[-1]^=1
        with self.assertRaisesRegex(ValueError,'ABI'):unpack(bad)
        report=dict(self.report,models=[dict(self.report['models'][0],id=1)])
        with self.assertRaisesRegex(ValueError,'RECORD_IDENTITY'):pack(report)


if __name__=='__main__':unittest.main()
