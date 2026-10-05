"""Native authored animation guard and explicit missing-API boundary proof."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import os
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
    p.add_argument('--linked',type=Path,help='B48R metadata/instructions/report directory')
    p.add_argument('--entity-view',action='store_true',help='Install a generic leased caller entity read view')
    p.add_argument('--observe-cost',action='store_true',help='Bounded native execution clocks/instruction observer')
    p.add_argument('--frame-dispatch',action='store_true',help='Exercise the offline frame-4 entry; empty-route runtime dispatcher remains unbound')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    source=compile_source(Source(a.source));item=next(x for x in source['programs'] if x['model']=='He_ManB')
    handle=next(h['handle'] for h in source['animation_handles'] if h['model']=='He_ManB' and h['role']=='freespecial4')
    blob,compiled=lower(item['program'],numeric_policy=POLICY);(a.output/'He_ManB.b48s').write_bytes(blob)
    root=Path(__file__).resolve().parents[2]
    def c(file,name):return pasm_constant_in(str(root/file),name)
    const='src/core/vm/vm_consts.pasm';call='src/core/vm/vm_call.pasm';run='src/core/vm/vm_run.pasm'
    variant='src/core/vm/vm_native_variant.pasm';code=c(const,'VmCode_Wram');slots=c(const,'VmSlots_Wram')
    rom=a.rom.resolve();entry=0;rom_address=None;linked=None
    if a.linked:
        from actor_s5_entity_fixture import symbols
        linked=json.loads((a.linked/'report.json').read_text())
        instructions=(a.linked/'instructions.bin').read_bytes();blob=(a.linked/'metadata.b48r').read_bytes()
        rom_address=symbols(root/'src/main.sym')['SourceVM_InstructionReservation']
        offset=(rom_address>>16)*32768+(rom_address&0xffff)-0x8000
        raw=bytearray(rom.read_bytes())
        if raw[offset:offset+32768]!=b'\xff'*32768:raise ValueError('ROM_SCRIPT_RESERVATION_OCCUPIED')
        raw[offset:offset+len(instructions)]=instructions
        (a.output/'bor.sfc').write_bytes(raw);rom=(a.output/'bor.sfc').resolve()
        for path in [a.rom.resolve().with_suffix('.msu'),*a.rom.resolve().parent.glob('bor-*.pcm')]:
            target=a.output/path.name
            if not target.exists():os.link(path,target)
        entry=next(p['entry_ip'] for p in linked['programs'] if p['identity']['model']==item['model'])
        if a.frame_dispatch:
            location=next(p for p in linked['programs'] if p['identity']['model']==item['model'])
            route=next(r for r in location['routes'] if r['animation_handle']==handle)
            if route['entry_ips'][3] is not None:raise ValueError('FRAME_THREE_MUST_HAVE_EMPTY_ROUTE')
            entry=route['entry_ips'][4]
            if entry is None:raise ValueError('FRAME_FOUR_ENTRY_REQUIRED')
        compiled=linked|dict(sha256=linked['metadata_sha256'])
    elif a.frame_dispatch:raise ValueError('FRAME_DISPATCH_LINK_REQUIRED')
    offsets=struct.unpack_from('<6I',blob,24);count,slotcount=struct.unpack_from('<2H',blob,8)
    reporter=Reporter('M4-AUTHORED-SCRIPT-GUARD',kind='GATE');cases=[]
    from actor_s5_entity_fixture import symbols
    from m4_vm_cost_observer import observed_session,pause_for_injection
    runtime_symbols=symbols(root/'src/main.sym')
    session_type=observed_session(a.output,runtime_symbols,count)
    with session_type(rom=rom,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=a.output/'mesen.log') as m:
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('SCRIPT_GUARD_PLAYING_REQUIRED')
        inputs=([(4,True,True,entry),(4,False,True,entry)] if a.frame_dispatch else
                [(3,True,True,entry),(4,True,True,entry),(3,False,True,entry)])
        if linked:inputs.extend([(3,True,False,0),(3,True,True,count)])
        for frame,lease,rom_mode,start_ip in inputs:
            if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('SCRIPT_GUARD_CASE_PLAYING_REQUIRED')
            at_entry=pause_for_injection(m,runtime_symbols)
            m.pause();m.write_memory('snesMemory',code,blob.hex())
            m.write_memory('snesMemory',slots,blob[offsets[1]:offsets[1]+slotcount*8].hex())
            for file,name,value in [(run,'VmPriv_InstrOff',offsets[0]),(call,'VmCall_CallsitesOff',offsets[2]),
                (call,'VmCall_ArgSlotsOff',offsets[3]),('src/core/vm/vm_string.pasm','VmStr_StringsOff',offsets[4])]:
                m.write_u16(c(file,name),value)
            context=b''.join(struct.pack('<BBHI',kind,0,0,value) for kind,value in
                [(5,0x6abcde),(1,frame),(1,0),(1,handle)])
            m.write_memory('snesMemory',c(variant,'VmNativeVariant_Self'),context.hex())
            m.write_u16(c(variant,'VmNativeVariant_ContextValid'),0xb48f if lease else 0)
            if a.entity_view:
                from source_entity_abi import record,view
                descriptor,data=view(0x7fb900,[record(0x6abcde,dict(a=0,animationid=handle,
                    direction=0,health=100,playerindex=0,x=80*65536,z=220*65536,maxhealth=100))])
                m.write_memory('snesMemory',0x7fb900,data.hex())
                m.write_memory('snesMemory',c('src/core/vm/vm_source_entity.pasm','VmSourceEntity_Base'),descriptor.hex())
            if linked:
                fetch='src/core/vm/vm_fetch_source.pasm'
                m.write_u16(c(fetch,'VmSourceInstr_Base'),rom_address&0xffff)
                m.write_u8(c(fetch,'VmSourceInstr_Bank'),rom_address>>16)
                m.write_u16(c(fetch,'VmSourceInstr_Ready'),0xb48e if rom_mode else 0)
            for name,value in [('VmState_Ip',start_ip),('VmState_Error',0),('VmState_InstrCount',count),
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
            case['injection_checkpoint']=at_entry
            case.update(rom_fetch_enabled=bool(linked and rom_mode),entry_ip=start_ip)
            case['game_state']=startup.u16(m,startup.STATE)
            case['cpu']=m.get_cpu_state()
            case['resident_module_sha256']=hashlib.sha256(read_block(m,code,len(blob))).hexdigest()
            case['module_unchanged']=case['resident_module_sha256']==compiled['sha256']
            reporter.check('resident module identity remains intact',case['module_unchanged'])
            cases.append(case)
            if linked and (not rom_mode or start_ip==count):
                expected=c(const,'VMERR_BAD_OPCODE' if not rom_mode else 'VMERR_BAD_JUMP')
                reporter.check('external-format/fetch-boundary rejection '+str(expected),
                    status==c(const,'VMSTAT_FAULT') and error==expected)
            elif frame==3 and lease:
                reporter.check('authored frame 3 returns before breath command',status==c(const,'VMSTAT_DONE') and error==0)
            else:
                expected=(518 if a.entity_view else 520) if lease else 521
                reporter.check('frame '+str(frame)+' fails at precise unbound capability '+str(expected),
                    status==c(const,'VMSTAT_FAULT') and error==c(const,'VMERR_BAD_NATIVE') and target==expected)
    observed=[]
    if a.observe_cost:
        from m4_vm_cost_observer import spans
        observed=spans(a.output/'mesen.log')
        reporter.check('one bounded CPU span per authored case',len(observed)==len(cases))
        reporter.check('observed instruction counts are bounded',all(0<x['instructions']<=200 for x in observed))
    result=dict(schema='BYOR_NATIVE_AUTHORED_FRAME_GUARD_V1',
        status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',
        rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest(),source_pak_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),
        model=item['model'],animation='freespecial4',animation_handle=handle,module=compiled,cases=cases,
        rom_instruction_address=rom_address,source_effect_native_executed=False,motu_gameplay_proven=False,
        entity_read_view_installed=a.entity_view,native_cpu_spans=observed,source_200hz_cadence_proven=False,
        offline_frame_entry=a.frame_dispatch,frame_dispatch_runtime_bound=False,
        cost_scope='Vm_Run after entry PHP/REP and first status LDA through terminal status write; includes intervening runtime work; excludes checkpoint waiting',
        scope='Authored frame guard and explicit missing engine boundary; injected caller locals/read view; CPU cost excludes host waiting')
    (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
