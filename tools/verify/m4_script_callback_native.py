"""Native installed-local begin/end lifecycle with persistent instance variables."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_script_variables import pack_record,validate_pool,descriptor,BANK,BASE,STRIDE
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
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parents[2];syms=symbols(root/'src/main.sym')
    def c(file,key):return pasm_constant_in(str(root/file),key)
    owner=0x6abcde;other=owner+1
    initial_rows=[pack_record(owner,1,'self',pointer(owner)),pack_record(owner,1,'frame',integer(4)),
                  pack_record(other,1,'Loop',integer(99)),pack_record(owner,2,'Loop',integer(77))]
    initial=b''.join(initial_rows)+bytes(12*STRIDE)
    cases=[
      dict(name='begin',request=1,body='void self=getlocalvar("self");void frame=getlocalvar("frame");void animnum=getlocalvar("animnum");void handle=getlocalvar("animhandle");setlocalvar("Loop",42);',
           returns=dict(self=pointer(owner),frame=integer(4),animnum=integer(44),handle=integer(36)),persistent=True),
      dict(name='default_model_continuation',request=0,previous=True,body='void loop=getlocalvar("Loop");setlocalvar("frame",99);setlocalvar("self",NULL());void frame=getlocalvar("frame");',
           returns=dict(loop=integer(42),frame=integer(99)),mutate=True),
      dict(name='end',request=2,previous=True,terminal=True,body='',returns={}),
      dict(name='next_begin',request=1,previous=True,body='void frame=getlocalvar("frame");void loop=getlocalvar("Loop");',returns=dict(frame=integer(4),loop=integer(42))),
      dict(name='full_pool_preflight',request=1,count=4,body='',fault=True),
      dict(name='duplicate_begin',request=1,active=0xb4a6,body='',fault=True),
      dict(name='end_without_begin',request=2,terminal=True,body='',fault=True),
      dict(name='busy_begin',request=1,status=3,body='',fault=True),
      dict(name='missing_context',request=1,context=0,body='',fault=True),
      dict(name='wrong_scope',request=1,scope=2,body='',fault=True),
      dict(name='mismatched_end_snapshot',request=2,active=0xb4a6,terminal=True,body='',fault=True,bad_snapshot=True),
    ]
    reporter=Reporter('M4-SOURCE-CALLBACK-LIFECYCLE',kind='GATE');results=[]
    const='src/core/vm/vm_consts.pasm';call='src/core/vm/vm_call.pasm';variant='src/core/vm/vm_native_variant.pasm'
    variables='src/core/vm/vm_source_variables.pasm';world='src/core/vm/vm_source_world_birth.pasm'
    callback='src/core/vm/vm_source_callback.pasm'
    session=observed_session(a.output,syms,0);last_pool=None;last_active=0
    with session(rom=a.rom.resolve(),mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=a.output/'mesen.log') as m:
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('VARIABLES_PLAYING_REQUIRED')
        run_frames_exact(m,12)
        for case in cases:
            source='void main(){'+case['body']+'}'
            blob,compiled=lower(compile_library(parse_script(source,'instance-variables-probe.c'),
                ['NULL','getlocalvar','setlocalvar','clearlocalvar']),numeric_policy=POLICY)
            checkpoint=pause_for_injection(m,syms);m.pause();offsets=struct.unpack_from('<6I',blob,24)
            count,slots=struct.unpack_from('<2H',blob,8)
            m.write_memory('snesMemory',c(const,'VmCode_Wram'),blob.hex())
            m.write_memory('snesMemory',c(const,'VmSlots_Wram'),blob[offsets[1]:offsets[1]+slots*8].hex())
            for file,key,value in [('src/core/vm/vm_run.pasm','VmPriv_InstrOff',offsets[0]),
                                  (call,'VmCall_CallsitesOff',offsets[2]),(call,'VmCall_ArgSlotsOff',offsets[3]),
                                  ('src/core/vm/vm_string.pasm','VmStr_StringsOff',offsets[4])]:m.write_u16(c(file,key),value)
            token=case.get('owner',owner)
            m.write_memory('snesMemory',c(variant,'VmNativeVariant_Self'),(pointer(token)+integer(4)+integer(44)+integer(36)).hex())
            m.write_u16(c(variant,'VmNativeVariant_ContextValid'),case.get('context',0xb48f))
            m.write_u16(c(world,'VmSourceWorld_Ready'),0xb4a3 if case.get('world',True) else 0)
            pool=last_pool if case.get('previous') else initial
            validate_pool(pool)
            m.write_memory('snesMemory',(BANK<<16)+BASE,pool.hex())
            if read_block(m,(BANK<<16)+BASE,len(pool))!=pool:raise ValueError('VARIABLE_POOL_WRITEBACK_REQUIRED_BEFORE_LEASE')
            m.write_memory('snesMemory',c(variables,'VmSourceVars_Ready'),descriptor(token,scope=case.get('scope',1),count=case.get('count',16)).hex())
            for key,value in [('VmState_Ip',0),('VmState_Error',0),('VmState_InstrCount',count),
                              ('VmState_SlotCount',slots),('VmState_FrameTop',0)]:m.write_u16(c(const,key),value)
            active=last_active if case.get('previous') else case.get('active',0)
            m.write_u16(c(callback,'VmSourceCallback_Ready'),0xb4a5)
            m.write_u16(c(callback,'VmSourceCallback_Active'),active)
            m.write_u16(c(callback,'VmSourceCallback_Request'),case['request'])
            if case.get('bad_snapshot'):m.write_memory('snesMemory',c(callback,'VmSourceCallback_Snapshot'),bytes(32).hex())
            m.write_u8(c(const,'VmState_Status'),case.get('status',4 if case.get('terminal') else 1))
            for fields in range(1,61):
                run_frames_exact(m,1);state=read_block(m,c(const,'VM_STATE_FIRST'),32)
                status=state[c(const,'VmState_Status')-c(const,'VM_STATE_FIRST')]
                error=struct.unpack_from('<H',state,c(const,'VmState_Error')-c(const,'VM_STATE_FIRST'))[0]
                if status in (4,5):break
            reporter.check(case['name']+' terminal state',(status,error)==((5,10) if case.get('fault') else (4,0)))
            checks=[]
            for name,expected in case.get('returns',{}).items():
                index=compiled['function_local_slots']['main'][name]
                actual=read_block(m,c(const,'VmSlots_Wram')+index*8,32)[:8]
                reporter.check(case['name']+' '+name+' full variant',actual==expected)
                checks.append(dict(local=name,actual_hex=actual.hex(),expected_hex=expected.hex()))
            actual_pool=read_block(m,(BANK<<16)+BASE,len(pool));expected_pool=bytearray(pool)
            def set_named(name,value):
                for row_index in range(16):
                    row=expected_pool[row_index*STRIDE:(row_index+1)*STRIDE]
                    row_owner,scope,length=struct.unpack_from('<IHH',row)
                    if length and row_owner==owner and scope==1 and row[16:16+length]==name.encode():
                        expected_pool[row_index*STRIDE+8:row_index*STRIDE+16]=value;return
                for row_index in range(16):
                    if not any(expected_pool[row_index*STRIDE:(row_index+1)*STRIDE]):
                        expected_pool[row_index*STRIDE:(row_index+1)*STRIDE]=pack_record(owner,1,name,value);return
                raise ValueError('ORACLE_CAPACITY')
            if not case.get('fault'):
                if case['request']==1:
                    for name,value in [('self',pointer(owner)),('frame',integer(4)),('animnum',integer(44)),('animhandle',integer(36))]:set_named(name,value)
                if case.get('persistent'):set_named('Loop',integer(42))
                if case.get('mutate'):set_named('frame',integer(99));set_named('self',bytes(8))
                if case['request']==2:
                    for name in ['self','frame','animnum','animhandle']:set_named(name,bytes(8))
            expected_active=active if case.get('fault') or case['request']==0 else (0xb4a6 if case['request']==1 else 0)
            actual_active=m.read_u16(c(callback,'VmSourceCallback_Active'))
            actual_context=m.read_u16(c(variant,'VmNativeVariant_ContextValid'))
            reporter.check(case['name']+' boundary state and consumed request',actual_active==expected_active and m.read_u16(c(callback,'VmSourceCallback_Request'))==0)
            reporter.check(case['name']+' context lifetime',actual_context==(0 if case['request']==2 and not case.get('fault') else case.get('context',0xb48f)))
            last_active=actual_active
            reporter.check(case['name']+' exact namespace mutation and isolation',actual_pool==expected_pool)
            validate_pool(actual_pool);last_pool=actual_pool
            results.append(dict(case=case['name'],source=source,status=status,error=error,fields=fields,checks=checks,
                                pool_sha256=hashlib.sha256(actual_pool).hexdigest(),expected_pool_sha256=hashlib.sha256(expected_pool).hexdigest(),injection_checkpoint=checkpoint))
        m.write_u16(c(variables,'VmSourceVars_Ready'),0);m.write_u16(c(world,'VmSourceWorld_Ready'),0)
    report=dict(schema='BYOR_NATIVE_ANIMATION_CALLBACK_LIFECYCLE_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',
                rom_sha256=hashlib.sha256(a.rom.read_bytes()).hexdigest(),cases=results,
                authority='af23dc9 openborscript.c Varlist_*, Script_Copy(localclear=0), system_*localvar; List.c strcmp',
                namespace='entity animation script instance; installed locals span current/default callbacks and are emptied after both',
                production_callback_owner_bound=False,
                live_callback_owner_bound=False,stored_string_values_bound=False,indexed_variables_bound=False,motu_gameplay_proven=False)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
