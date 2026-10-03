"""S6 policy/isolation/ABI guards. Does not promote bounded proofs to certification."""
import ast
from pathlib import Path
import re
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
PYTHON_FILES=[ROOT/'tools/bor_compile'/n for n in (
    'source_actor_execution.py','source_actor_link.py','source_actor_numeric.py','source_actor_raster.py')]
ASM_FILES=sorted((ROOT/'src/core').glob('actor_source*.pasm'))


class ContractTests(unittest.TestCase):
    def test_no_named_actor_behavior(self):
        forbidden={'kula','lobster','crab','ramon','time'}
        for path in PYTHON_FILES:
            tree=ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node,(ast.Compare,ast.Subscript,ast.If,ast.Match)):
                    literals={v.value.casefold() for v in ast.walk(node)
                              if isinstance(v,ast.Constant) and isinstance(v.value,str)}
                    self.assertFalse(literals&forbidden,(path,node.lineno,literals&forbidden))
        for path in ASM_FILES:
            code='\n'.join(line.split(';',1)[0] for line in path.read_text().splitlines())
            self.assertFalse(set(re.findall(r'\b\w+\b',code.casefold()))&forbidden,path)

    def test_native_widths_and_compat_isolation(self):
        sys.path.insert(0,str(ROOT/'tools/rom_audit'))
        import check_width_directives as width
        lines=[]
        for path in ASM_FILES:lines.extend(width.flatten(str(path)))
        violations,checked=width.scan(lines)
        self.assertGreater(checked,20);self.assertEqual(violations,[])
        production='\n'.join(line for _,_,line in width.flatten(str(ROOT/'src/main.pasm')))
        self.assertNotIn('S6_SetRole:',production)
        self.assertNotIn('S6_TryHitOne:',production)

    def test_no_illegal_long_y_encoding(self):
        # Poppy currently accepts .l ...,y but emits an extra operand byte.
        # SNES has no absolute-long-Y LDA. Keep that malformed mode out.
        for path in [*ASM_FILES,ROOT/'src/core/actor_s6_raster_fixture.pasm',ROOT/'src/core/actor_s6_raster_clock_fixture.pasm']:
            code='\n'.join(line.split(';',1)[0] for line in path.read_text().splitlines())
            self.assertIsNone(re.search(r'(?im)^\s*\w+\.l\s+[^\n]+,y\s*$',code),path)


if __name__=='__main__':unittest.main()
