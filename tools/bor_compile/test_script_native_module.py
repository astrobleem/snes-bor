import struct
import unittest
from script_ir_4086 import parse_script
from script_bytecode import compile_library
from script_native_module import lower,POLICY
from openbor_script.compiler import Module,Instr,Callsite
from openbor_script.oracle import Oracle


def unpack(blob):
    m=Module();count,slots,calls,natives,entry=struct.unpack_from('<5H',blob,8)
    offsets=struct.unpack_from('<6I',blob,24);m.entry_main=entry
    m.instructions=[Instr(op,a,b,c,flags) for op,flags,a,b,c in
        struct.iter_unpack('<BBHHH',blob[offsets[0]:offsets[0]+count*8])]
    m.slots=list(struct.iter_unpack('<BBHI',blob[offsets[1]:offsets[1]+slots*8]))
    for i in range(calls):
        kind,argc,target,result,index,flags,debug=struct.unpack_from('<BBHHHHH',blob,offsets[2]+i*12)
        args=list(struct.unpack_from('<'+'H'*argc,blob,offsets[3]+index*2))
        m.callsites.append(Callsite(kind,argc,target,result,args,index,flags,debug))
    return m


class NativeModuleTests(unittest.TestCase):
    def library(self,text,builtins=()):return compile_library(parse_script(text,'probe.c'),list(builtins))

    def test_packed_module_executes_branch_calls_and_distinct_local_slots(self):
        lib=self.library('int f(int x){if(x<3)return x+7;return x-1;} '
                         'void main(){int a=f(2);int b=f(8);return a*10+b;}')
        blob,report=lower(lib,numeric_policy=POLICY)
        oracle=Oracle(unpack(blob),{},{});oracle.run()
        self.assertEqual(oracle.get(report['function_stack_slots']['main'][0]),(1,97))
        self.assertEqual(oracle.get(report['function_local_slots']['main']['a']),(1,9))
        self.assertEqual(oracle.get(report['function_local_slots']['main']['b']),(1,7))

    def test_native_identity_keeps_name_arity_and_full_arguments(self):
        lib=self.library('void main(){effect("HBreath",18,93,0);effect("Shock");}',('effect',))
        blob,report=lower(lib,numeric_policy=POLICY,native_ids={('effect',1):0x300,('effect',4):0x301})
        requirements=report['engine_api_requirements']
        self.assertEqual([(r['name'],r['arity']) for r in requirements],[('effect',1),('effect',4)])
        m=unpack(blob);self.assertEqual([c.argc for c in m.callsites],[4,1])
        self.assertNotEqual(m.callsites[0].target_id,m.callsites[1].target_id)
        self.assertFalse(report['entity_api_bound'])

    def test_source_api_ids_do_not_alias_when_module_requirements_change(self):
        lib=self.library('void main(){getlocalvar("self");}',('getlocalvar',))
        blob,report=lower(lib,numeric_policy=POLICY)
        self.assertEqual(report['engine_api_requirements'][0]['id'],521)
        unknown=self.library('void main(){effect();}',('effect',))
        with self.assertRaisesRegex(ValueError,'SIGNATURE_UNKNOWN'):lower(unknown,numeric_policy=POLICY)

    def test_numeric_policy_and_recursion_are_explicit(self):
        lib=self.library('void main(){return 0.3;}')
        with self.assertRaisesRegex(ValueError,'NUMERIC_POLICY_REQUIRED'):lower(lib)
        blob,report=lower(lib,numeric_policy=POLICY)
        self.assertEqual(report['decimal_constants'][0]['adapted'],19661/65536)
        self.assertFalse(report['source_numeric_equivalence'])
        recursive=self.library('void f(){f();} void main(){f();}')
        with self.assertRaisesRegex(ValueError,'RECURSION_UNSUPPORTED'):lower(recursive,numeric_policy=POLICY)

    def test_export_roots_share_only_mutually_exclusive_temporary_slots(self):
        lib=self.library('int f(int x){return x+7;} void a(){int x=f(2);return x;} '
                         'void b(){int y=f(8);return y;}')
        blob,report=lower(lib,entry='a',export_roots=['a','b'],numeric_policy=POLICY)
        self.assertEqual(report['function_local_slots']['a']['x'],report['function_local_slots']['b']['y'])
        self.assertNotEqual(report['function_local_slots']['a']['x'],report['function_local_slots']['f']['x'])
        for name,result in [('a',9),('b',15)]:
            m=unpack(blob);m.entry_main=report['export_entries'][name]
            oracle=Oracle(m,{},{});oracle.run()
            self.assertEqual(oracle.get(report['function_stack_slots'][name][0]),(1,result))
        called=self.library('void a(){b();} void b(){}')
        with self.assertRaisesRegex(ValueError,'ROOT_ENTRY_CALLED'):
            lower(called,entry='a',export_roots=['b'],numeric_policy=POLICY)

    def test_exported_roots_clear_reads_before_initialization_without_redundant_stores(self):
        lib=self.library('void a(){int x=99;return x;} void b(){int x=x;return x;} '
                         'int f(int x){int y=x+1;return y;}')
        blob,report=lower(lib,entry='a',export_roots=['b'],numeric_policy=POLICY)
        self.assertEqual(report['initial_empty_locals']['a'],[])
        self.assertEqual(report['initial_empty_locals']['b'],[0])
        self.assertEqual(report['initial_empty_locals']['f'],[])
        oracle=Oracle(unpack(blob),{},{});oracle.run()
        oracle.ip=report['export_entries']['b'];oracle.run()
        self.assertEqual(oracle.get(report['function_stack_slots']['b'][0]),(0,0))


if __name__=='__main__':unittest.main()
