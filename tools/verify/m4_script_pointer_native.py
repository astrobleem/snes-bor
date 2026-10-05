"""Native source PTR key formatting and PTR/EMPTY equality boundary proof."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bor_compile'))
from script_ir_4086 import parse_script
from script_bytecode import compile_library
from script_native_module import lower, POLICY
from _harness import (McpSession, MESEN_EXE, _free_tcp_port, pasm_constant_in,
                      read_block, run_frames_exact, exact_input_edge, Reporter)
import game_bor_startup_select as startup

SOURCE = '''void main(){void self=getlocalvar("self");
 void key="T"+self; void reverse=self+"x";
 int same=self==self; int absent=self==NULL();
 int present=self!=NULL(); int both=NULL()==NULL();
 int distinct=NULL()!=self; int truth=!!self;}'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    blob,compiled=lower(compile_library(parse_script(SOURCE,'pointer-variant-probe.c'),
        ['NULL','getlocalvar']),numeric_policy=POLICY)
    (a.output/'probe.b48s').write_bytes(blob)
    root=Path(__file__).resolve().parents[2]
    def c(file,name):return pasm_constant_in(str(root/file),name)
    const='src/core/vm/vm_consts.pasm';call='src/core/vm/vm_call.pasm'
    code=c(const,'VmCode_Wram');slots=c(const,'VmSlots_Wram')
    offsets=struct.unpack_from('<6I',blob,24);count,slotcount=struct.unpack_from('<2H',blob,8)
    reporter=Reporter('M4-SOURCE-POINTER-VARIANTS',kind='GATE');cases=[]
    with McpSession(rom=a.rom.resolve(),mesen=MESEN_EXE,port=_free_tcp_port(),
                    stderr_log=a.output/'mesen.log') as m:
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('POINTER_PROBE_PLAYING_REQUIRED')
        for token in (0,1,0x80000000,0xffffffff):
            m.pause();m.write_memory('snesMemory',code,blob.hex())
            m.write_memory('snesMemory',slots,blob[offsets[1]:offsets[1]+slotcount*8].hex())
            for file,key,value in [('src/core/vm/vm_run.pasm','VmPriv_InstrOff',offsets[0]),
                    (call,'VmCall_CallsitesOff',offsets[2]),(call,'VmCall_ArgSlotsOff',offsets[3]),
                    ('src/core/vm/vm_string.pasm','VmStr_StringsOff',offsets[4])]:m.write_u16(c(file,key),value)
            m.write_memory('snesMemory',c('src/core/vm/vm_native_variant.pasm','VmNativeVariant_Self'),
                (struct.pack('<BBHI',5,0,0,token)+bytes(24)).hex())
            m.write_u16(c('src/core/vm/vm_native_variant.pasm','VmNativeVariant_ContextValid'),0xb48f)
            for key,value in [('VmState_Ip',0),('VmState_Error',0),('VmState_InstrCount',count),
                              ('VmState_SlotCount',slotcount),('VmState_FrameTop',0)]:m.write_u16(c(const,key),value)
            m.write_u8(c(const,'VmState_Status'),c(const,'VMSTAT_READY'))
            for field in range(1,61):
                run_frames_exact(m,1);state=read_block(m,c(const,'VM_STATE_FIRST'),32)
                status=state[c(const,'VmState_Status')-c(const,'VM_STATE_FIRST')]
                error=struct.unpack_from('<H',state,c(const,'VmState_Error')-c(const,'VM_STATE_FIRST'))[0]
                if status in (4,5):break
            reporter.check(hex(token)+' native terminal state',(status,error)==(4,0))
            signed=struct.unpack('<i',struct.pack('<I',token))[0];text='#'+str(signed)
            checks=[]
            for key,expected in [('key','T'+text),('reverse',text+'x')]:
                index=compiled['function_local_slots']['main'][key]
                kind,flags,length,handle=struct.unpack('<BBHI',read_block(m,slots+index*8,32)[:8])
                actual=read_block(m,c(const,'VmStrPool_Wram')+(handle&0xffff)*64+2,64)[:length].decode('ascii')
                reporter.check(hex(token)+' '+key,kind==6 and handle&0x80000000 and actual==expected)
                checks.append(dict(local=key,type=kind,text=actual,expected=expected))
            for key,expected in [('same',1),('absent',0),('present',1),('both',1),('distinct',1),('truth',int(bool(token)))]:
                index=compiled['function_local_slots']['main'][key]
                actual=struct.unpack('<BBHI',read_block(m,slots+index*8,32)[:8])
                reporter.check(hex(token)+' '+key,actual==(1,0,0,expected))
                checks.append(dict(local=key,actual=list(actual),expected=expected))
            cases.append(dict(token=token,fields=field,status=status,error=error,checks=checks))
    result=dict(schema='BYOR_SOURCE_POINTER_NATIVE_VARIANTS_V1',
        status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',
        source=SOURCE,module=compiled,cases=cases,rom_sha256=hashlib.sha256(a.rom.read_bytes()).hexdigest(),
        engine_authority='af23dc9c2316bb7853bb266ccf40986aa9765aeb:ScriptVariant.c',
        pointer_format='# plus signed 32-bit decimal',ordered_pointer_comparisons_bound=False,
        persistent_script_locals_bound=False,motu_gameplay_proven=False,
        scope='Typed source caller lease; PTR+STR/STR+PTR and PTR/EMPTY EQ/NE only')
    (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
