"""Bounded native slot-VM check of generic source-bytecode lowering.

Uses the existing original-BOR ROM and injected VM memory, with no ROM changes.
This admits call/branch lowering only; it does not execute MOTU engine APIs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from script_ir_4086 import parse_script
from script_bytecode import compile_library
from script_native_module import lower,POLICY
from _harness import McpSession,MESEN_EXE,_free_tcp_port,pasm_constant_in,read_block,run_frames_exact,exact_input_edge,Reporter
import game_bor_startup_select as startup


SOURCE='int f(int x){if(x<3)return x+7;return x-1;} void main(){int a=f(2);int b=f(8);return a*10+b;}'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    blob,compiled=lower(compile_library(parse_script(SOURCE,'lowering-native-probe.c'),[]),numeric_policy=POLICY)
    (a.output/'probe.b48s').write_bytes(blob)
    root=Path(__file__).resolve().parents[2]
    def constant(file,name):return pasm_constant_in(str(root/file),name)
    const='src/core/vm/vm_consts.pasm';run='src/core/vm/vm_run.pasm';call='src/core/vm/vm_call.pasm'
    code=constant(const,'VmCode_Wram');slots=constant(const,'VmSlots_Wram')
    offsets=struct.unpack_from('<6I',blob,24);count,slotcount=struct.unpack_from('<2H',blob,8)
    report=Reporter('M4-SCRIPT-LOWERING',kind='GATE');samples=[]
    with McpSession(rom=a.rom.resolve(),mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=a.output/'mesen.log') as m:
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,report)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('NATIVE_VM_PROBE_PLAYING_REQUIRED')
        m.pause();m.write_memory('snesMemory',code,blob.hex())
        m.write_memory('snesMemory',slots,blob[offsets[1]:offsets[1]+slotcount*8].hex())
        m.write_u16(constant(run,'VmPriv_InstrOff'),offsets[0])
        m.write_u16(constant(call,'VmCall_CallsitesOff'),offsets[2])
        m.write_u16(constant(call,'VmCall_ArgSlotsOff'),offsets[3])
        for name,value in [('VmState_Ip',0),('VmState_Error',0),('VmState_InstrCount',count),
            ('VmState_SlotCount',slotcount),('VmState_FrameTop',0)]:m.write_u16(constant(const,name),value)
        m.write_u8(constant(const,'VmState_Status'),constant(const,'VMSTAT_READY'))
        statebase=constant(const,'VM_STATE_FIRST')
        for field in range(1,13):
            run_frames_exact(m,1);state=read_block(m,statebase,32)
            status=state[constant(const,'VmState_Status')-statebase]
            error=struct.unpack_from('<H',state,constant(const,'VmState_Error')-statebase)[0]
            samples.append(dict(field=field,status=status,error=error))
            if status in (constant(const,'VMSTAT_DONE'),constant(const,'VMSTAT_FAULT')):break
        report.check('native VM reaches DONE without fault',status==constant(const,'VMSTAT_DONE') and error==0)
        checks=[]
        for name,index,expected in [('a',compiled['function_local_slots']['main']['a'],9),
            ('b',compiled['function_local_slots']['main']['b'],7),
            ('return',compiled['function_stack_slots']['main'][0],97)]:
            kind,flags,aux,value=struct.unpack('<BBHI',read_block(m,slots+index*8,32)[:8])
            checks.append(dict(name=name,slot=index,type=kind,value=value,expected=expected))
            report.check('native '+name+' matches hand-derived source result',kind==1 and value==expected)
        guards={}
        for name,fill in [('VmGuardLo',0xa5),('VmGuardHi',0x5a)]:
            guards[name]=read_block(m,constant(const,name),32)[:16].hex()
            report.check(name+' remains intact',guards[name]==(bytes([fill])*16).hex())
    result=dict(schema='BYOR_NATIVE_SCRIPT_LOWERING_PROOF_V1',
        status='PASS' if all(ok for _,ok in report.results) else 'FAIL',
        rom_sha256=hashlib.sha256(a.rom.read_bytes()).hexdigest(),source=SOURCE,module=compiled,
        samples=samples,checks=checks,guards=guards,motu_native_apis_bound=False,motu_gameplay_proven=False,
        scope='Existing native VM call/branch/parameter/return lowering only; debug memory injection; original ROM unchanged')
    (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');report.finish()


if __name__=='__main__':main()
