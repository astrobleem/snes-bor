"""Pinned source constant identities and live level-boundary owner proof."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import os
import sys
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_script_constants import unpack,lookup
from script_ir_4086 import parse_script
from script_bytecode import compile_library
from script_native_module import lower,POLICY
from _harness import MESEN_EXE,_free_tcp_port,pasm_constant_in,read_block,run_frames_exact,exact_input_edge,Reporter
from actor_s5_entity_fixture import symbols
from m4_vm_cost_observer import observed_session,pause_for_injection
import game_bor_startup_select as startup


def integer(value):return struct.pack('<BBHI',1,0,0,value&0xffffffff)
def pointer(value):return struct.pack('<BBHI',5,0,0,value)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True)
    p.add_argument('--constants',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parents[2];syms=symbols(root/'src/main.sym')
    def c(file,key):return pasm_constant_in(str(root/file),key)
    table=(a.constants/'constants.b4ct').read_bytes();rows=unpack(table)
    location=syms['SourceVM_ConstantReservation'];offset=(location>>16)*32768+(location&65535)-32768
    raw=bytearray(a.rom.read_bytes())
    if raw[offset:offset+16384]!=b'\xff'*16384:raise ValueError('CONSTANT_RESERVATION_OCCUPIED')
    raw[offset:offset+len(table)]=table;rom=a.output/'bor.sfc';rom.write_bytes(raw)
    for path in [a.rom.resolve().with_suffix('.msu'),*a.rom.resolve().parent.glob('bor-*.pcm')]:
        target=a.output/path.name
        if not target.exists():os.link(path,target)
    cases=[]
    for name in ['ANI_FALL','ANI_ATTACK','ANI_ATTACK1','ANI_FOLLOW5','ani_follow6','MAX_ANIS']:
        cases.append(dict(name=name,body='void value=openborconstant("'+name+'");',value=integer(lookup(table,name))))
    cases.extend([
      dict(name='dynamic_name',body='void value=openborconstant("ANI_FOLLOW"+"5");',value=integer(162),heap_zero=True),
      dict(name='repeat_dynamic_80',body='openborconstant("ANI_FOLLOW"+"5");'*80+'void value=openborconstant("ANI_FOLLOW6");',value=integer(163),heap_zero=True),
      dict(name='integer_passthrough_without_table',body='void value=openborconstant(-2147483647);',value=integer(-2147483647),ready=0),
      dict(name='live_minimum',body='void value=openborconstant("PLAYER_MIN_Z");',value=integer(180)),
      dict(name='live_maximum',body='void value=openborconstant("player_max_z");',value=integer(232)),
      dict(name='no_table',body='openborconstant("ANI_FALL");',fault=True,ready=0),
      dict(name='bad_bank',body='openborconstant("ANI_FALL");',fault=True,bank=64),
      dict(name='bad_base',body='openborconstant("ANI_FALL");',fault=True,base=0x7000),
      dict(name='bad_count',body='openborconstant("ANI_FALL");',fault=True,count=0),
      dict(name='bank_spill',body='openborconstant("ANI_FALL");',fault=True,base=0xffff),
      dict(name='header_count_mismatch',body='openborconstant("ANI_FALL");',fault=True,count=len(rows)-1,size=24+(len(rows)-1)*40),
      dict(name='unbound_name',body='openborconstant("ANI_FOLLOW11");',fault=True),
      dict(name='decimal_rejected',body='openborconstant(2.5);',fault=True),
      dict(name='no_level_bounds_owner',body='openborconstant("PLAYER_MIN_Z");',fault=True,level_ready=0),
      dict(name='no_world_owner',body='openborconstant("PLAYER_MIN_Z");',fault=True,world=0),
      dict(name='no_level',body='openborconstant("PLAYER_MIN_Z");',fault=True,level=0),
    ])
    reporter=Reporter('M4-SOURCE-CONSTANTS',kind='GATE');results=[]
    const='src/core/vm/vm_consts.pasm';call='src/core/vm/vm_call.pasm';variant='src/core/vm/vm_native_variant.pasm'
    constants='src/core/vm/vm_source_constants.pasm';world='src/core/vm/vm_source_world_birth.pasm'
    session=observed_session(a.output,syms,0);last_pool=None
    with session(rom=rom.resolve(),mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=a.output/'mesen.log') as m:
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('VARIABLES_PLAYING_REQUIRED')
        run_frames_exact(m,12)
        for case in cases:
            source='void main(){'+case['body']+'}'
            blob,compiled=lower(compile_library(parse_script(source,'source-constants-probe.c'),
                ['openborconstant']),numeric_policy=POLICY)
            checkpoint=pause_for_injection(m,syms);m.pause();offsets=struct.unpack_from('<6I',blob,24)
            count,slots=struct.unpack_from('<2H',blob,8)
            m.write_memory('snesMemory',c(const,'VmCode_Wram'),blob.hex())
            m.write_memory('snesMemory',c(const,'VmSlots_Wram'),blob[offsets[1]:offsets[1]+slots*8].hex())
            for file,key,value in [('src/core/vm/vm_run.pasm','VmPriv_InstrOff',offsets[0]),
                                  (call,'VmCall_CallsitesOff',offsets[2]),(call,'VmCall_ArgSlotsOff',offsets[3]),
                                  ('src/core/vm/vm_string.pasm','VmStr_StringsOff',offsets[4])]:m.write_u16(c(file,key),value)
            m.write_memory('snesMemory',c(constants,'VmSourceConstants_Ready'),struct.pack('<5H',case.get('ready',0xb4a8),case.get('base',location&65535),case.get('bank',location>>16),case.get('count',len(rows)),case.get('size',len(table))).hex())
            m.write_memory('snesMemory',c(constants,'VmSourceLevelBounds_Ready'),struct.pack('<Hii',case.get('level_ready',0xb4a9),180,232).hex())
            m.write_u16(c(world,'VmSourceWorld_Ready'),case.get('world',0xb4a3))
            m.write_u16(c(world,'VmSourceWorld_Level'),case.get('level',1))
            m.write_u16(c(variant,'VmNativeVariant_ContextValid'),0)
            for key,value in [('VmState_Ip',0),('VmState_Error',0),('VmState_InstrCount',count),
                              ('VmState_SlotCount',slots),('VmState_FrameTop',0)]:m.write_u16(c(const,key),value)
            m.write_u8(c(const,'VmState_Status'),1)
            for fields in range(1,61):
                run_frames_exact(m,1);state=read_block(m,c(const,'VM_STATE_FIRST'),32)
                status=state[c(const,'VmState_Status')-c(const,'VM_STATE_FIRST')]
                error=struct.unpack_from('<H',state,c(const,'VmState_Error')-c(const,'VM_STATE_FIRST'))[0]
                if status in (4,5):break
            reporter.check(case['name']+' terminal state',(status,error)==((5,10) if case.get('fault') else (4,0)))
            checks=[]
            if 'value' in case:
                index=compiled['function_local_slots']['main']['value'];actual=read_block(m,c(const,'VmSlots_Wram')+index*8,32)[:8]
                reporter.check(case['name']+' complete INTEGER variant',actual==case['value'])
                checks.append(dict(actual_hex=actual.hex(),expected_hex=case['value'].hex()))
            if case.get('heap_zero'):
                heap=read_block(m,0x7fe400,4096);live=sum(heap[n*64]!=0 for n in range(64))
                reporter.check(case['name']+' no residual dynamic-key ownership',live==0)
            results.append(dict(case=case['name'],source=source,status=status,error=error,fields=fields,checks=checks,injection_checkpoint=checkpoint))
        m.write_u16(c(constants,'VmSourceConstants_Ready'),0);m.write_u16(c(constants,'VmSourceLevelBounds_Ready'),0);m.write_u16(c(world,'VmSourceWorld_Ready'),0)
    report=dict(schema='BYOR_NATIVE_SOURCE_CONSTANTS_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',
                rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest(),constant_table_sha256=hashlib.sha256(table).hexdigest(),cases=results,
                authority='af23dc9 openborscript.c mapstrings_transconst/openbor_transconst; pinned animation enum/expansion arrays',
                capability='source animation constants plus exclusively owned live PLAYER_MIN_Z/MAX_Z',
                live_level_owner_bound=False,other_constant_families_bound=False,motu_gameplay_proven=False)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
