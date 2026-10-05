import unittest
from pathlib import Path
from script_ir_4086 import parse_script,inspect
from compiler import Source


class ScriptFrontendTests(unittest.TestCase):
    def test_variant_void_variables_and_return_value_preserved(self):
        r=parse_script('void renamed(float x){void value=spawn();return value;}','source.c')
        f=r['functions']['renamed']
        self.assertEqual(f['arity'],1);self.assertEqual(f['calls'],['spawn'])
        self.assertFalse(f['native_lowered'])

    def test_comments_do_not_strip_string_identity_and_unsupported_arrays_fail(self):
        r=parse_script('void f(){void s="//x/*y*/";/* comment */}', 'source.c')
        self.assertIn('//x/*y*/',str(r['functions']['f']['ast']))
        with self.assertRaisesRegex(ValueError,'SCRIPT_AST_UNSUPPORTED'):
            parse_script('void f(){int a[2];}', 'source.c')

    def test_supplied_foreign_source_all_commands_bind_to_actual_functions(self):
        source=Source(Path(__file__).resolve().parents[2]/'Masters of the Universe [v.3.0 Build 4086].pak')
        r=inspect(source)
        self.assertEqual(r['diagnostics'],[]);self.assertEqual(len(r['bindings']),65)
        self.assertEqual(len(r['inline_blocks']),5)
        self.assertTrue(all(b['source_function_bound'] for b in r['bindings']))
        self.assertEqual(sum(len(l['functions']) for l in r['libraries'].values()),27)
        self.assertFalse(r['native_lowered'])


if __name__=='__main__':unittest.main()
