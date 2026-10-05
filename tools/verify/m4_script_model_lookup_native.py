"""Bounded model name/residency API proof; no entity allocation or loader claim."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_model_registry import unpack,NULL_MODEL
from script_ir_4086 import parse_script
from script_bytecode import compile_library
from script_native_module import lower,POLICY
from _harness import McpSession,MESEN_EXE,_free_tcp_port,pasm_constant_in,read_block,run_frames_exact,exact_input_edge,Reporter
from actor_s5_entity_fixture import symbols
from m4_vm_cost_observer import observed_session,pause_for_injection
import game_bor_startup_select as startup


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True)
    p.add_argument('--registry',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parents[2];syms=symbols(root/'src/main.sym')
    def c(file,name):return pasm_constant_in(str(root/file),name)
    table=(a.registry/'models.b4mr').read_bytes();rows=unpack(table)
    target=next(row['id'] for row in rows if row['lookup_name']=='hbreath')
    address=syms['SourceVM_InstructionReservation'];offset=(address>>16)*32768+(address&0xffff)-0x8000
    raw=bytearray(a.rom.resolve().read_bytes())
    if raw[offset:offset+32768]!=b'\xff'*32768:raise ValueError('MODEL_TABLE_RESERVATION_OCCUPIED')
    raw[offset:offset+len(table)]=table;rom=a.output/'bor.sfc';rom.write_bytes(raw)
    for path in [a.rom.resolve().with_suffix('.msu'),*a.rom.resolve().parent.glob('bor-*.pcm')]:
        destination=a.output/path.name
        if not destination.exists():os.link(path,destination)
    inputs=[('casefold','hBrEaTh',True,True,target),('unloaded','HBreath',False,True,NULL_MODEL),
            ('missing','unregistered',True,True,NULL_MODEL),('no_lease','HBreath',True,False,None)]
    programs=[]
    for identity,name,loaded,lease,expected in inputs:
        text='void main(){clearspawnentry();void result=setspawnentry("NaMe","'+name+'");}'
        blob,compiled=lower(compile_library(parse_script(text,'model-name-probe.c'),['clearspawnentry','setspawnentry']),numeric_policy=POLICY)
        programs.append((blob,compiled))
    counts={struct.unpack_from('<H',blob,8)[0] for blob,_ in programs}
    if len(counts)!=1:raise ValueError('MODEL_PROBE_OBSERVER_COUNT_MISMATCH')
    reporter=Reporter('M4-MODEL-NAME-LOOKUP',kind='GATE');results=[]
    const='src/core/vm/vm_consts.pasm';models='src/core/vm/vm_source_models.pasm';call='src/core/vm/vm_call.pasm'
    session=observed_session(a.output,syms,counts.pop())
    with session(rom=rom,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=a.output/'mesen.log') as m:
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('MODEL_LOOKUP_PLAYING_REQUIRED')
        for (identity,name,loaded,lease,expected),(blob,compiled) in zip(inputs,programs):
            checkpoint=pause_for_injection(m,syms);m.pause();offsets=struct.unpack_from('<6I',blob,24)
            count,slots=struct.unpack_from('<2H',blob,8)
            m.write_memory('snesMemory',c(const,'VmCode_Wram'),blob.hex())
            m.write_memory('snesMemory',c(const,'VmSlots_Wram'),blob[offsets[1]:offsets[1]+slots*8].hex())
            for file,key,value in [('src/core/vm/vm_run.pasm','VmPriv_InstrOff',offsets[0]),
                                  (call,'VmCall_CallsitesOff',offsets[2]),(call,'VmCall_ArgSlotsOff',offsets[3]),
                                  ('src/core/vm/vm_string.pasm','VmStr_StringsOff',offsets[4])]:m.write_u16(c(file,key),value)
            for key,value in [('VmSourceModels_Base',address&0xffff),('VmSourceModels_Count',len(rows)),
                              ('VmSourceModels_Bytes',len(table)),('VmSourceModels_Ready',0xb4a1 if lease else 0)]:m.write_u16(c(models,key),value)
            m.write_u8(c(models,'VmSourceModels_Bank'),address>>16)
            bits=bytearray(c(models,'VM_SOURCE_MODELS_BITMAP_BYTES'))
            if loaded:bits[target//8]=1<<(target%8)
            m.write_memory('snesMemory',c(models,'VmSourceModels_Loaded'),bits.hex())
            for key,value in [('VmState_Ip',0),('VmState_Error',0),('VmState_InstrCount',count),
                              ('VmState_SlotCount',slots),('VmState_FrameTop',0)]:m.write_u16(c(const,key),value)
            m.write_u8(c(const,'VmState_Status'),1)
            for fields in range(1,61):
                run_frames_exact(m,1);state=read_block(m,c(const,'VM_STATE_FIRST'),32)
                status=state[c(const,'VmState_Status')-c(const,'VM_STATE_FIRST')]
                error=struct.unpack_from('<H',state,c(const,'VmState_Error')-c(const,'VM_STATE_FIRST'))[0]
                if status in (4,5):break
            actual=struct.unpack('<H',read_block(m,c('src/core/vm/vm_source_spawn.pasm','VmSourceSpawn_Model'),32)[:2])[0]
            result_index=compiled['function_local_slots']['main']['result']
            result=read_block(m,c(const,'VmSlots_Wram')+8*result_index,32)[:8]
            reporter.check(identity+' native state',(status,error)==((4,0) if lease else (5,10)))
            if lease:
                reporter.check(identity+' lookup respects loaded-state identity',actual==expected)
                reporter.check(identity+' setter returns full INTEGER 1',result==struct.pack('<BBHI',1,0,0,1))
            results.append(dict(case=identity,name=name,loaded=loaded,table_lease=lease,fields=fields,
                                status=status,error=error,model_id=actual,return_variant_hex=result.hex(),injection_checkpoint=checkpoint))
    result=dict(schema='BYOR_NATIVE_MODEL_NAME_LOOKUP_V1',status='PASS' if all(x for _,x in reporter.results) else 'FAIL',
                rom_sha256=hashlib.sha256(raw).hexdigest(),table_sha256=hashlib.sha256(table).hexdigest(),
                cases=results,model_loader_bound=False,entity_allocator_bound=False,motu_gameplay_proven=False,no_pcm_copies=True)
    (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
