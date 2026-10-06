import unittest
from pathlib import Path
from compiler import Source
from source_script_constants import derive,pack,unpack,lookup


class ScriptConstants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=derive(Source(Path(__file__).resolve().parents[2]/'Masters of the Universe [v.3.0 Build 4086].pak'))
        cls.table=pack(cls.report)
    def test_engine_ids_and_dynamic_aliases(self):
        self.assertEqual(lookup(self.table,'ANI_FREESPECIAL4'),44)
        self.assertEqual(lookup(self.table,'ani_follow5'),162)
        self.assertEqual(lookup(self.table,'ANI_FOLLOW6'),163)
        self.assertEqual(lookup(self.table,'ANI_ATTACK'),7)
        self.assertEqual(lookup(self.table,'ANI_ATTACK1'),8)
        self.assertEqual(lookup(self.table,'MAX_ANIS'),162)
        self.assertEqual(lookup(self.table,'PLAYER_MIN_Z',(180,232)),180)
        self.assertEqual(lookup(self.table,'PLAYER_MAX_Z',(180,232)),232)
    def test_owner_and_table_validation(self):
        with self.assertRaisesRegex(ValueError,'LEVEL_OWNER'):lookup(self.table,'PLAYER_MIN_Z')
        with self.assertRaisesRegex(ValueError,'UNBOUND'):lookup(self.table,'ANI_FOLLOW11')
        bad=bytearray(self.table);bad[-1]^=1
        with self.assertRaisesRegex(ValueError,'ABI'):unpack(bad)
        self.assertEqual(len(unpack(self.table)),188)


if __name__=='__main__':unittest.main()
