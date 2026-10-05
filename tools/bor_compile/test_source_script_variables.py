import struct
import unittest
from source_script_variables import Instances,pack_record,validate_pool,descriptor,CAPACITY,STRIDE,FIRST_UNUSED


class ScriptVariableOwnership(unittest.TestCase):
    def test_entity_instance_and_callback_model_switch(self):
        instances=Instances();current=instances.for_script(1);default=instances.for_script(1)
        value=struct.pack('<BBHI',1,0,0,3)
        self.assertEqual(current.set('Loop',value),1)
        self.assertIs(current,default)
        self.assertEqual(default.get('Loop'),value)
        self.assertEqual(default.get('loop'),bytes(8))
        self.assertEqual(instances.for_script(2).get('Loop'),bytes(8))
        self.assertEqual(instances.for_script(1,'onspawn').get('Loop'),bytes(8))
        current.cleanup();self.assertEqual(default.get('Loop'),bytes(8))
        self.assertIn('Loop',current.names)
        self.assertEqual(current.set('',value),0)
        self.assertEqual(current.set(-1,value),0)
        self.assertEqual(current.set(3.9,value),1)
        self.assertEqual(current.get(3),value)

    def test_bounded_native_record_identity_and_types(self):
        value=struct.pack('<BBHI',5,0,0,0x414050)
        row=pack_record(0x414000,1,'T#4276224',value)
        validate_pool(row+bytes(STRIDE))
        with self.assertRaisesRegex(ValueError,'DUPLICATE'):validate_pool(row+row)
        with self.assertRaisesRegex(ValueError,'KEY_CAPACITY'):pack_record(1,1,'x'*48,value)
        with self.assertRaisesRegex(ValueError,'VALUE_CAPABILITY'):pack_record(1,1,'T',struct.pack('<BBHI',3,0,0,0))
        self.assertEqual(FIRST_UNUSED,0xe800)
        self.assertEqual(len(descriptor(1,count=CAPACITY)),14)
        self.assertEqual(len(bytes(CAPACITY*STRIDE)),24576)


if __name__=='__main__':unittest.main()
