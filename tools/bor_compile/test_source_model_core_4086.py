from pathlib import Path
import struct,unittest
from compiler import Source,key
from source_model_core_4086 import derive,pack,load,CACHED_FIELDS


class ModelCore(unittest.TestCase):
    def test_source_inputs_and_native_layout_require_explicit_media_binding(self):
        r=derive(Source(Path(__file__).resolve().parents[2]/'Masters of the Universe [v.3.0 Build 4086].pak'))
        with self.assertRaisesRegex(ValueError,'MODEL_CORE_MEDIA_INDEX_UNBOUND'):pack(r,{})
        paths=sorted({key(p) for m in r['models'] for p in m['media_bindings'].values()})
        data=pack(r,{p:i for i,p in enumerate(paths)})
        self.assertEqual(len(data),2560)
        models={m['identity']:m for m in r['models']}
        a,b=models['He_Man'],models['He_ManB']
        self.assertEqual(a['fields']['type'],1);self.assertEqual(b['fields']['type'],0)
        self.assertEqual((a['fields']['health'],b['fields']['health']),(150,150))
        self.assertEqual((a['fields']['speed'],b['fields']['speed']),(1.,struct.unpack('<f',struct.pack('<f',1.2))[0]))
        self.assertEqual(models['ShWave']['fields']['speed'],.5)
        self.assertEqual(models['Knightbot']['fields']['flash'],-1)
        for m in r['models']:
            self.assertEqual(struct.unpack_from('<i',data,m['id']*160+156)[0],m['fields']['type'])
            self.assertEqual(struct.unpack_from('<i',data,m['id']*160+4*CACHED_FIELDS.index('health'))[0],m['fields']['health'])
        self.assertFalse(r['complete_model_constructor_bound']);self.assertFalse(r['motu_gameplay_proven'])

    def test_unsupported_subtype_and_duplicate_icon_fail_explicitly(self):
        with self.assertRaisesRegex(ValueError,'MODEL_CORE_SUBTYPE_BACKEND_REQUIRED'):
            load([dict(directive='subtype',values=['arrow'])])
        with self.assertRaisesRegex(ValueError,'MODEL_CORE_DUPLICATE_ICON'):
            load([dict(directive='icon',values=['a']),dict(directive='icon',values=['b'])])


if __name__=='__main__':unittest.main()
