import unittest
import struct
from pathlib import Path
from compiler import Source
from script_ir_4086 import parse_script
from script_bytecode import compile_library
from script_vm_reference import Machine,Value,integer,unary


class ScriptBytecodeTests(unittest.TestCase):
    def compile(self,text,builtins=()):return compile_library(parse_script(text,'source.c'),list(builtins))

    def test_declared_int_does_not_truncate_variant_decimal(self):
        lib=self.compile('void f(){int x=1.5;return x;}')
        self.assertEqual(Machine(lib,{}).call('f'),Value('DECIMAL',1.5))

    def test_4086_decimal_negation_union_fallthrough(self):
        lib=self.compile('void f(){return -0.3;}')
        result=Machine(lib,{}).call('f')
        self.assertEqual(struct.pack('<d',result.data).hex(),'cdcccccc3333d3bf')
        self.assertNotEqual(result.data,-0.3)
        self.assertEqual(unary('NEG',Value('STRING','x')),Value('STRING','x'))
        self.assertEqual(unary('POS',Value('POINTER',7)),Value('POINTER',7))
        with self.assertRaisesRegex(ValueError,'SIGNED_OVERFLOW_UNPROVEN'):
            unary('NEG',Value('DECIMAL',struct.unpack('<d',bytes.fromhex('000000800000f03f'))[0]))

    def test_engine_integer_division_and_empty_zero_result(self):
        lib=self.compile('void f(int x,int y){return x/y;}')
        self.assertEqual(Machine(lib,{}).call('f',[integer(-7),integer(2)]),integer(-3))
        self.assertEqual(Machine(lib,{}).call('f',[integer(7),integer(0)]),Value())

    def test_eager_logical_calls_and_source_function_call(self):
        calls=[];lib=self.compile('void g(){return record();} void f(){return 0 && g();}',('record',))
        machine=Machine(lib,{'record':lambda:(calls.append('called') or integer(1))})
        self.assertEqual(machine.call('f'),integer(0));self.assertEqual(calls,['called'])

    def test_branch_local_shadow_and_assignment_value(self):
        lib=self.compile('void f(int x){if(x){int x=9;x=x+2;return x;}return x;}')
        self.assertEqual(Machine(lib,{}).call('f',[integer(1)]),integer(11))
        self.assertEqual(Machine(lib,{}).call('f',[integer(0)]),integer(0))

    def test_numeric_constant_and_hook_admission_are_explicit(self):
        lib=self.compile('void f(){return effect(0.3);}',('effect',))
        self.assertEqual(lib['constants'][0]['little_endian'],struct.pack('<d',0.3).hex())
        with self.assertRaisesRegex(ValueError,'REFERENCE_ENGINE_API_UNBOUND'):Machine(lib,{}).call('f')
        self.assertFalse(lib['native_bound'])

    def test_actual_spawn_body_preserves_altitude_and_facing_offsets(self):
        source=Source(Path(__file__).resolve().parents[2]/'Masters of the Universe [v.3.0 Build 4086].pak')
        path='data/scripts/script.c'
        library=compile_library(parse_script(source.read(path).decode('latin1'),path),
            ['getlocalvar','getentityproperty','clearspawnentry','setspawnentry','spawn','changeentityproperty',
             'tossentity','playerkeys','openborconstant','projectile'])
        changes=[];entries=[]
        properties={'direction':integer(0),'x':Value('DECIMAL',80.0),
                    'z':Value('DECIMAL',220.0),'a':Value('DECIMAL',0.0)}
        hooks={'getlocalvar':lambda key:Value('POINTER',1),
               'getentityproperty':lambda entity,key:properties[key.data],
               'clearspawnentry':lambda:Value(),
               'setspawnentry':lambda *args:(entries.append(args) or Value()),
               'spawn':lambda:Value('POINTER',2),
               'changeentityproperty':lambda *args:(changes.append(args) or Value())}
        machine=Machine(library,hooks)
        result=machine.call('spawn01',[Value('STRING','HBreath'),integer(18),integer(93),integer(0)])
        self.assertEqual(result,Value('POINTER',2))
        self.assertEqual([v.data for v in changes[0]],[2,'position',62.0,220.0,93.0])
        self.assertEqual([v.data for v in changes[1]],[2,'direction',0])
        self.assertEqual([v.data for v in entries[0]],['name','HBreath'])


if __name__=='__main__':unittest.main()
