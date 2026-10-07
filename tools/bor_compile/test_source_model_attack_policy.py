import struct
import unittest
from pathlib import Path
from compiler import Source
from source_model_attack_policy import derive,pack,unpack,CAPACITY

class ModelAttackPolicyTableTests(unittest.TestCase):
    def test_source_roundtrip_and_corrupt_admission_headers(self):
        source=Path(__file__).resolve().parents[2]/'Masters of the Universe [v.3.0 Build 4086].pak'
        report=derive(Source(source));table=pack(report)
        self.assertEqual(len(table),272)
        self.assertEqual(unpack(table),[m['fields']for m in report['models']])
        for at,value in ((0,0),(4,2),(6,0),(6,CAPACITY+1),(8,12),(10,1),(12,1),(14,1)):
            malformed=bytearray(table);struct.pack_into('<H',malformed,at,value)
            with self.assertRaises(ValueError):unpack(malformed)
        for data in (table[:15],table[:-1],table+b'\0'):
            with self.assertRaises(ValueError):unpack(data)
        with self.assertRaisesRegex(ValueError,'CAPACITY'):pack(dict(models=report['models']+[report['models'][0]]))
        wrong=dict(report['models'][0],index=1)
        with self.assertRaisesRegex(ValueError,'ORDER'):pack(dict(models=[wrong]))

if __name__=='__main__':unittest.main()
