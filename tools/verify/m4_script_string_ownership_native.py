"""Before/after native proof for dynamic source-key result-slot ownership."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from script_ir_4086 import parse_script
from script_bytecode import compile_library
from script_native_module import lower,POLICY
from _harness import McpSession,MESEN_EXE,_free_tcp_port,pasm_constant_in,read_block,run_frames_exact,exact_input_edge,Reporter
from actor_s5_entity_fixture import symbols
from m4_vm_cost_observer import observed_session,pause_for_injection
import game_bor_startup_select as startup


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parents[2];syms=symbols(root/'src/main.sym')
    def c(file,name):return pasm_constant_in(str(root/file),name)
    const='src/core/vm/vm_consts.pasm';call='src/core/vm/vm_call.pasm';variant='src/core/vm/vm_native_variant.pasm'
    text='void main(){'+('getlocalvar("no"+"such");'*80)+'}'
    blob,compiled=lower(compile_library(parse_script(text,'source-key-ownership.c'),['getlocalvar']),numeric_policy=POLICY)
    offsets=struct.unpack_from('<6I',blob,24);count,slots=struct.unpack_from('<2H',blob,8)
    raw=a.rom.resolve().read_bytes();start=syms['Vm_NativeVariantStore__release_begin'];end=syms['Vm_NativeVariantStore__release_end']
    file_offset=(start>>16)*32768+(start&0xffff)-0x8000
    if end-start!=7 or raw[file_offset]!=0xaf or raw[file_offset+4]!=0x20:
        raise ValueError('SOURCE_RESULT_RELEASE_CONTROL_BYTES')
    control=bytearray(raw);control[file_offset:file_offset+7]=b'\xea'*7
    unchanged=control[:file_offset]==raw[:file_offset] and control[file_offset+7:]==raw[file_offset+7:]
    if not unchanged:raise ValueError('SOURCE_RESULT_RELEASE_CONTROL_SCOPE')
    cases=[];reporter=Reporter('M4-SOURCE-KEY-OWNERSHIP',kind='GATE')
    for identity,rom_bytes in [('no_release_control',bytes(control)),('release',raw)]:
        output=a.output/identity;output.mkdir(parents=True,exist_ok=True);rom=(output/'bor.sfc').resolve();rom.write_bytes(rom_bytes)
        for path in [a.rom.resolve().with_suffix('.msu'),*a.rom.resolve().parent.glob('bor-*.pcm')]:
            target=output/path.name
            if not target.exists():os.link(path,target)
        session=observed_session(output,syms,count)
        with session(rom=rom,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=output/'mesen.log') as m:
            with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
            startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
            if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('OWNERSHIP_PLAYING_REQUIRED')
            checkpoint=pause_for_injection(m,syms);m.pause()
            pool=c(const,'VmStrPool_Wram');pool_bytes=4096
            before=read_block(m,pool,pool_bytes)
            reporter.check(identity+' cold pool has no live objects',not any(before[::64]))
            m.write_memory('snesMemory',c(const,'VmCode_Wram'),blob.hex())
            m.write_memory('snesMemory',c(const,'VmSlots_Wram'),blob[offsets[1]:offsets[1]+slots*8].hex())
            for file,name,value in [('src/core/vm/vm_run.pasm','VmPriv_InstrOff',offsets[0]),
                (call,'VmCall_CallsitesOff',offsets[2]),(call,'VmCall_ArgSlotsOff',offsets[3]),
                ('src/core/vm/vm_string.pasm','VmStr_StringsOff',offsets[4])]:m.write_u16(c(file,name),value)
            context=b''.join(struct.pack('<BBHI',kind,0,0,value) for kind,value in [(5,1),(1,0),(1,0),(1,1)])
            m.write_memory('snesMemory',c(variant,'VmNativeVariant_Self'),context.hex())
            m.write_u16(c(variant,'VmNativeVariant_ContextValid'),0xb48f)
            for name,value in [('VmState_Ip',0),('VmState_Error',0),('VmState_InstrCount',count),
                               ('VmState_SlotCount',slots),('VmState_FrameTop',0)]:m.write_u16(c(const,name),value)
            m.write_u8(c(const,'VmState_Status'),1)
            for fields in range(1,121):
                run_frames_exact(m,1);state=read_block(m,c(const,'VM_STATE_FIRST'),32)
                status=state[c(const,'VmState_Status')-c(const,'VM_STATE_FIRST')]
                error=struct.unpack_from('<H',state,c(const,'VmState_Error')-c(const,'VM_STATE_FIRST'))[0]
                if status in (4,5):break
            after=read_block(m,pool,pool_bytes);live=sum(bool(x) for x in after[::64])
        # McpSession publishes its buffered stderr only during __exit__.
        from m4_vm_cost_observer import native_returns
        returns=native_returns(output/'mesen.log')
        result=dict(case=identity,status=status,error=error,fields=fields,live_objects=live,
                    successful_lookups=len(returns),rom_sha256=hashlib.sha256(rom_bytes).hexdigest(),
                    injection_checkpoint=checkpoint,pool_refcounts=list(after[::64]))
        cases.append(result)
        if identity=='release':
            reporter.check('80 dynamic lookups complete without pool exhaustion',status==4 and error==0 and len(returns)==80)
            reporter.check('overwritten source key strings have no remaining live objects',live==0)
        else:
            reporter.check('isolated no-release control exhausts 64-object pool',status==5 and live==64 and len(returns)==64)
    result=dict(schema='BYOR_SOURCE_NATIVE_RESULT_OWNERSHIP_V1',status='PASS' if all(x for _,x in reporter.results) else 'FAIL',
                source=text,module=compiled,cases=cases,control_patch_range=[start,end],
                all_other_rom_bytes_identical=unchanged,source_string_returns_bound=False,
                persistent_local_storage_bound=False,motu_gameplay_proven=False,no_pcm_copies=True)
    (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
