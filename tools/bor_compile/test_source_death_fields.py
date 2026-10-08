import struct
import unittest
from source_death_fields_4086 import loader_score,pack,unpack
from source_entity_abi import PROPERTIES,source_record,view,get_property


class DeathFields(unittest.TestCase):
 def test_loader_order_after_animation_and_missing_argument(self):
  rows=[dict(directive='score',values=['7','5'],line=1),dict(directive='anim',values=['idle'],line=2),dict(directive='score',values=['-9junk','2'],line=3)]
  self.assertEqual(loader_score(rows),(-9,3));self.assertEqual(loader_score([]),(0,None))
  self.assertEqual(loader_score([dict(directive='score',values=[],line=4)]),(0,4))
 def test_table_signed_and_mutation_rejection(self):
  rows=[dict(id=i,score=v)for i,v in enumerate((-2147483648,-1,0,2147483647))]
  data=pack(dict(models=rows));self.assertEqual(unpack(data)['models'],rows)
  for offset in (0,4,6,8,10,12,23,24,26):
   mutated=bytearray(data);mutated[offset]^=1
   with self.assertRaises(ValueError):unpack(mutated)
  with self.assertRaises(ValueError):unpack(data[:-1])

 def test_explicit_tail_and_script_property_independence(self):
  values={name:7 for name,_ in PROPERTIES}
  row=source_record(91,values,death_fields=dict(score=-7,diesound=18))
  self.assertEqual(struct.unpack_from('<ii',row,72),(-7,18))
  with self.assertRaises(ValueError):view(0x7e4000,[row],source_exists=True)
  with self.assertRaises(ValueError):view(0x7e4000,[row],death_fields=True)
  descriptor,payload=view(0x7e4000,[row],source_exists=True,death_fields=True)
  self.assertEqual(payload,row);self.assertEqual(struct.unpack_from('<H',descriptor,6)[0],0xb5ef)
  self.assertEqual(struct.unpack_from('<i',get_property([row],91,'health',source_exists=True),4)[0],7)
  for fields in ({'score':0},{'score':0,'diesound':2**31}):
   with self.assertRaises(ValueError):source_record(91,values,death_fields=fields)


if __name__=='__main__':unittest.main()
