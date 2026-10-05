"""Native authored animation guard and explicit missing-API boundary proof."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from compiler import Source
from script_dispatch_4086 import compile_source
from script_native_module import lower,POLICY
from _harness import McpSession,MESEN_EXE,_free_tcp_port,pasm_constant_in,read_block,run_frames_exact,exact_input_edge,Reporter
import game_bor_startup_select as startup


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    source=compile_source(Source(a.source));item=next(x for x in source['programs'] if x['model']=='He_ManB')
    handle=next(h['handle'] for h in source['animation_handles'] if h['model']=='He_ManB' and h['role']=='freespecial4')
    blob,compiled=lower(item['program'],numeric_policy=POLICY);(a.output/'He_ManB.b48s').write_bytes(blob)
    root=Path(__file__).resolve().parents[2]
    def c(file,name):return pasm_constant_in(str(root/file),name)
    const='src/core/vm/vm_consts.pasm';call='src/core/vm/vm_call.pasm';run='src/core/vm/vm_run.pasm'
    variant='src/core/vm/vm_native_variant.pasm';code=c(const,'VmCode_Wram');slots=c(const,'VmSlots_Wram')
    offsets=struct.unpack_from('<6I',blob,24);count,slotcount=struct.unpack_from('<2H',blob,8)
    reporter=Reporter('M4-AUTHORED-SCRIPT-GUARD',kind='GATE');cases=[]
    with McpSession(rom=a.rom.resolve(),mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=a.output/'mesen.log') as m:
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('SCRIPT_GUARD_PLAYING_REQUIRED')
        for frame,lease in [(3,True),(4,True),(3,False)]:
            if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('SCRIPT_GUARD_CASE_PLAYING_REQUIRED')
            m.pause();m.write_memory('snesMemory',code,blob.hex())
            m.write_memory('snesMemory',slots,blob[offsets[1]:offsets[1]+slotcount*8].hex())
            for file,name,value in [(run,'VmPriv_InstrOff',offsets[0]),(call,'VmCall_CallsitesOff',offsets[2]),
                (call,'VmCall_ArgSlotsOff',offsets[3]),('src/core/vm/vm_string.pasm','VmStr_StringsOff',offsets[4])]:
                m.write_u16(c(file,name),value)
            context=b''.join(struct.pack('<BBHI',kind,0,0,value) for kind,value in
                [(5,0x6abcde),(1,frame),(1,0),(1,handle)])
            m.write_memory('snesMemory',c(variant,'VmNativeVariant_Self'),context.hex())
            m.write_u16(c(variant,'VmNativeVariant_ContextValid'),0xb48f if lease else 0)
            for name,value in [('VmState_Ip',0),('VmState_Error',0),('VmState_InstrCount',count),
                ('VmState_SlotCount',slotcount),('VmState_FrameTop',0)]:m.write_u16(c(const,name),value)
            m.write_u8(c(const,'VmState_Status'),c(const,'VMSTAT_READY'))
            base=c(const,'VM_STATE_FIRST')
            for field in range(1,61):
                run_frames_exact(m,1);state=read_block(m,base,32)
                status=state[c(const,'VmState_Status')-base]
                error=struct.unpack_from('<H',state,c(const,'VmState_Error')-base)[0]
                if status in (c(const,'VMSTAT_DONE'),c(const,'VMSTAT_FAULT')):break
            target=struct.unpack('<H',read_block(m,c(call,'VmCall_TargetId'),32)[:2])[0]
            case=dict(frame=frame,context_lease=lease,fields=field,status=status,error=error,native_id=target)
            case['game_state']=startup.u16(m,startup.STATE)
            case['cpu']=m.get_cpu_state()
            case['resident_module_sha256']=hashlib.sha256(read_block(m,code,len(blob))).hexdigest()
            case['module_unchanged']=case['resident_module_sha256']==compiled['sha256']
            reporter.check('resident module identity remains intact',case['module_unchanged'])
            cases.append(case)
            if frame==3 and lease:
                reporter.check('authored frame 3 returns before breath command',status==c(const,'VMSTAT_DONE') and error==0)
            else:
                expected=520 if lease else 521
                reporter.check('frame '+str(frame)+' fails at precise unbound capability '+str(expected),
                    status==c(const,'VMSTAT_FAULT') and error==c(const,'VMERR_BAD_NATIVE') and target==expected)
    result=dict(schema='BYOR_NATIVE_AUTHORED_FRAME_GUARD_V1',
        status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',
        rom_sha256=hashlib.sha256(a.rom.read_bytes()).hexdigest(),source_pak_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),
        model=item['model'],animation='freespecial4',animation_handle=handle,module=compiled,cases=cases,
        source_effect_native_executed=False,motu_gameplay_proven=False,
        scope='Authored frame guard, installed caller locals and explicit missing getentityproperty capability only')
    (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
