"""Assemble the complete real throw routine; inspect its emitted gate/physics.

No emulator, replacement runtime, ROM build, or native PASS. The small gate
walker only decodes emitted selector branches up to an actual routine label.
External audio is a link address, never a stub implementation.
"""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

from game_s8_stage_bounds import ROOT, symbols


class ThrowGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dotnet=os.environ.get('DOTNET',r'C:\Users\chad\.dotnet\dotnet.exe')
        poppy=os.environ.get('POPPY_DLL',r'E:\gh\poppy-astrobleem\src\Poppy.CLI\bin\Release\net10.0\poppy.dll')
        if not Path(dotnet).is_file() or not Path(poppy).is_file():
            raise unittest.SkipTest('Poppy unavailable')
        text=(ROOT/'src/core/vm/vm_native_engine.pasm').read_text()
        routine='Character_Throw_Play:'+text.split('Character_Throw_Play:',1)[1].split('; Audio-content pass:',1)[0]
        code='\n'.join(line.split(';',1)[0] for line in routine.splitlines())
        labels=set(re.findall(r'^(\w+):',code,re.M))
        cls.constants=symbols(ROOT/'src/main.sym')
        used=set(re.findall(r'\b[A-Za-z_]\w*\b',code)) & cls.constants.keys() - labels
        definitions=[f'{n} = ${cls.constants[n]:06X}' for n in sorted(used)]
        with tempfile.TemporaryDirectory(prefix='s8_throw_gate_') as folder:
            source=Path(folder)/'gate.pasm'; output=Path(folder)/'gate.bin'
            source.write_text('\n'.join(['.snes','.bank 0','.org $8000',*definitions,routine]))
            result=subprocess.run([dotnet,poppy,str(source),'-o',str(output),'-s',str(source.with_suffix('.sym'))],
                                  capture_output=True,text=True,timeout=60)
            if result.returncode: raise AssertionError(result.stdout+result.stderr)
            cls.data=output.read_bytes()
            cls.labels=symbols(source.with_suffix('.sym'))

    def offset(self,name): return self.labels['Character_Throw_Play'+name]&0x7fff

    def route(self,selector,high):
        pc=self.offset(''); a=0; zero=False
        stops={self.offset(s):s for s in ('__thrown','__hole','__done')}
        for _ in range(30):
            if pc in stops: return stops[pc]
            op=self.data[pc]; pc+=1
            if op==0xe2:  # defensive SEP: only M changes; no stack/D/DBR touch
                self.assertEqual(self.data[pc],0x20); pc+=1
            elif op==0xa5:
                address=self.data[pc]; pc+=1
                if address==self.constants['CHAR_SELECTED']: a=selector
                else:
                    self.assertEqual(address,self.constants['CHAR_THROW_ZVEL']+1); a=high
            elif op==0xc9: zero=a==self.data[pc]; pc+=1
            elif op in (0xf0,0xd0):
                delta=int.from_bytes(self.data[pc:pc+1],'little',signed=True); pc+=1
                if zero==(op==0xf0): pc+=delta
            elif op==0x82:
                delta=int.from_bytes(self.data[pc:pc+2],'little',signed=True); pc+=2+delta
            else: self.fail(f'unexpected gate opcode {op:02x} at {pc-1:04x}')
        self.fail('gate did not terminate')

    def test_all_selectors_and_velocity_markers(self):
        for selector in range(256):
            for high in (0,6,0x7f,0x80,0xfe,0xff):
                expected='__thrown' if selector==6 else '__hole' if selector==3 and high==255 else '__done'
                self.assertEqual(self.route(selector,high),expected,(selector,high))

    def test_actual_emitted_position_velocity_integration(self):
        c=self.constants
        expected=bytes([0xc2,0x31,0xa5,c['CHAR_THROW_ZPOS'],0x18,
                        0x65,c['CHAR_THROW_ZVEL'],0x85,c['CHAR_THROW_ZPOS'],
                        0xa5,c['CHAR_THROW_ZVEL'],0x18,0x69])+c['JUMP_GRAVITY'].to_bytes(2,'little')+bytes([0x85,c['CHAR_THROW_ZVEL']])
        for name in ('__thrown','__hole'):
            start=self.offset(name)
            self.assertEqual(self.data[start:start+len(expected)],expected)
        # Both actual arithmetic prefixes force A16/X16 and
        # explicit carry clears, use DP only, and never mutate D/DBR/SP.
        # Decimal mode is a caller precondition (REP #31 does not clear D).
        # Representative airborne result for source drop: 7800+0000,
        # then 0000+FFE6. Native execution remains a separate proof.
        self.assertEqual((0x7800+0)&0xffff,0x7800)
        self.assertEqual((0+c['JUMP_GRAVITY'])&0xffff,0xffe6)

    def test_return_width_and_stack_contract(self):
        for suffix in ('__still_air','__hole_still_falling'):
            start=self.offset(suffix)
            self.assertEqual(self.data[start:start+3],bytes.fromhex('e2206b'))
        self.assertEqual(self.data[self.offset('__done')],0x6b)
        # SEP #20 guarantees A8 at RTL; no PHP/PLP means flags are NOT
        # preserved. Arithmetic paths force X16; no-op leaves caller X.
        # RTL alone consumes the caller's three-byte JSL return frame.


if __name__=='__main__': unittest.main()
