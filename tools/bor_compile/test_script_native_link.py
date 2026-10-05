import struct
import unittest
import zlib
from script_ir_4086 import parse_script
from script_bytecode import compile_library
from script_native_module import lower,POLICY
from script_native_link import link,unpack
from openbor_script.oracle import Oracle


def materialize(code,metadata):
    """Reconstruct legacy host layout only to exercise the linked operands."""
    body=bytearray(metadata[:64]+code+metadata[64:]);body[:4]=b'B48S'
    struct.pack_into('<I',body,24,64)
    for field in range(28,48,4):
        struct.pack_into('<I',body,field,struct.unpack_from('<I',metadata,field)[0]+len(code))
    struct.pack_into('<I',body,52,len(body))
    struct.pack_into('<I',body,56,zlib.crc32(body[64:])&0xffffffff)
    return bytes(body)


class ScriptLinkTests(unittest.TestCase):
    def program(self,text):return lower(compile_library(parse_script(text,'source.c'),[]),numeric_policy=POLICY)

    def test_distinct_program_scopes_relocate_calls_slots_and_branches(self):
        first=self.program('int f(int x){if(x<3)return x+7;return x-1;} '
            'void main(){int a=f(2);int b=f(8);return a*10+b;}')
        second=self.program('int f(int x){if(x==4)return 23;return x*x+1;} '
            'void main(){return f(4);}')
        code,metadata,report=link([('first',first[0]),('second',second[0])])
        m,arities=unpack(materialize(code,metadata))
        for i,expected in [(0,97),(1,23)]:
            m.entry_main=report['programs'][i]['entry_ip'];o=Oracle(m,{},{});o.run()
            source=(first,second)[i][1]
            slot=source['function_stack_slots']['main'][0]+report['programs'][i]['slot_base']
            self.assertEqual(o.get(slot),(1,expected))
            self.assertFalse(o.frames)
        self.assertEqual(report['instruction_count'],sum(struct.unpack_from('<H',x[0],8)[0] for x in (first,second)))
        self.assertTrue(report['no_functions_removed'])

    def test_external_format_is_rejected_by_legacy_loader_identity(self):
        code,metadata,report=link([('one',self.program('void main(){return 1;}')[0])])
        self.assertEqual(metadata[:4],b'B48R')
        with self.assertRaisesRegex(ValueError,'MODULE_ABI'):unpack(metadata)
        self.assertEqual(zlib.crc32(metadata[64:])&0xffffffff,struct.unpack_from('<I',metadata,56)[0])


if __name__=='__main__':unittest.main()
