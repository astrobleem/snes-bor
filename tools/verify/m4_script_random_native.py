"""Shared 4086 rand stream through the real typed VM; no world call-order claim."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_actor_numeric import random32_step,random32_limbs
from script_ir_4086 import parse_script
from script_bytecode import compile_library
from script_native_module import lower,POLICY
from actor_s5_entity_fixture import symbols
from _harness import MESEN_EXE,_free_tcp_port,Reporter,exact_input_edge,run_frames_exact,read_block
from m4_vm_cost_observer import observed_session,pause_for_injection
import game_bor_startup_select as startup


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--authority',type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parents[2];sy=symbols(root/'src/main.sym')
    authority=json.loads(a.authority.read_text())
    if authority['status']!='PASS' or not authority['win32_32bit_long']:raise ValueError('RANDOM_C_AUTHORITY_REQUIRED')
    golden={seed:authority['rows'][i*32:(i+1)*32] for i,seed in enumerate(authority['seeds'])}
    rom=a.output/'bor.sfc';rom.write_bytes(a.rom.read_bytes())
    for source in [a.rom.resolve().with_suffix('.msu'),*a.rom.resolve().parent.glob('bor-*.pcm')]:
        target=a.output/source.name
        if not target.exists():os.link(source,target)
    cases=[dict(name=f'seed_{seed:08x}',seed=seed,count=32) for seed in
        (1234567890,0,1,0xffffffff,0x80000000,0x1234ffff)]
    cases += [dict(name='counter_wrap',seed=0xfedcba98,count=5,calls=0xfffffffe),
        dict(name='unowned',seed=0x12345678,count=1,ready=0,fault=True),
        dict(name='wrong_lease',seed=0x12345678,count=1,ready=0xb4d3,fault=True),
        dict(name='busy',seed=0x12345678,count=1,busy=1,fault=True),
        dict(name='missing_context',seed=0x12345678,count=1,context=0,fault=True)]
    reporter=Reporter('M4-SOURCE-RAND',kind='GATE');results=[]
    session=observed_session(a.output,sy,0)
    with session(rom=rom,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=a.output/'mesen.log') as m:
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        reporter.check('cold random lease retired',startup.u16(m,sy['SourceRandom4086_Ready'])==0)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('RANDOM_NATIVE_PLAYING_REQUIRED')
        run_frames_exact(m,12)
        for case in cases:
            source='void main(){'+''.join(f'void v{i}=rand();' for i in range(case['count']))+'}'
            blob,compiled=lower(compile_library(parse_script(source,'source-rand-probe.c'),['rand']),numeric_policy=POLICY)
            checkpoint=pause_for_injection(m,sy);m.pause()
            offsets=struct.unpack_from('<6I',blob,24);count,slots=struct.unpack_from('<2H',blob,8)
            m.write_memory('snesMemory',sy['VmCode_Wram'],blob.hex())
            m.write_memory('snesMemory',sy['VmSlots_Wram'],blob[offsets[1]:offsets[1]+slots*8].hex())
            for name,value in [('VmPriv_InstrOff',offsets[0]),('VmCall_CallsitesOff',offsets[2]),
                ('VmCall_ArgSlotsOff',offsets[3]),('VmStr_StringsOff',offsets[4]),
                ('VmState_Ip',0),('VmState_Error',0),('VmState_InstrCount',count),
                ('VmState_SlotCount',slots),('VmState_FrameTop',0),
                ('VmNativeVariant_ContextValid',case.get('context',0xb48f))]:m.write_u16(sy[name],value)
            initial_calls=case.get('calls',0)
            request=struct.pack('<HIIH',case.get('ready',0xb4d4),case['seed'],initial_calls,case.get('busy',0))
            m.write_memory('snesMemory',sy['SourceRandom4086_Ready'],request.hex())
            m.write_u8(sy['VmState_Status'],1)
            for fields in range(1,61):
                run_frames_exact(m,1);state=read_block(m,sy['VM_STATE_FIRST'],32)
                status=state[sy['VmState_Status']-sy['VM_STATE_FIRST']]
                error=struct.unpack_from('<H',state,sy['VmState_Error']-sy['VM_STATE_FIRST'])[0]
                if status in (4,5):break
            reporter.check(case['name']+' terminal',(status,error)==((5,10) if case.get('fault') else (4,0)))
            seed=case['seed'];checks=[]
            if not case.get('fault'):
                for i in range(case['count']):
                    before,after,value=golden[case['seed']][i]
                    assert before==seed
                    expected=(after,value);assert expected==random32_step(seed)==random32_limbs(seed)
                    seed,value=expected;index=compiled['function_local_slots']['main'][f'v{i}']
                    actual=read_block(m,sy['VmSlots_Wram']+index*8,32)[:8]
                    reference=struct.pack('<BBHI',1,0,0,value)
                    checks.append(dict(index=i,actual_hex=actual.hex(),expected_hex=reference.hex()))
                reporter.check(case['name']+' all full-width returned variants',all(v['actual_hex']==v['expected_hex'] for v in checks))
            final=read_block(m,sy['SourceRandom4086_Ready'],32)[:12]
            ready,observed_seed,calls,busy=struct.unpack('<HIIH',final)
            wanted_calls=initial_calls if case.get('fault') else (initial_calls+case['count'])&0xffffffff
            reporter.check(case['name']+' shared seed and counter',observed_seed==seed and calls==wanted_calls)
            reporter.check(case['name']+' guard ownership',ready==case.get('ready',0xb4d4) and busy==case.get('busy',0))
            results.append(dict(case=case,checks=checks,status=status,error=error,fields=fields,
                final_descriptor_hex=final.hex(),injection_checkpoint=checkpoint))
        m.write_u16(sy['SourceRandom4086_Ready'],0);m.write_u16(sy['VmNativeVariant_ContextValid'],0)
    report=dict(schema='BYOR_NATIVE_SOURCE_RANDOM_V1',status='PASS' if all(v for _,v in reporter.results) else 'FAIL',
        rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest(),cases=results,
        authority_report_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),
        authority='af23dc9 engine/source/randlib/rand32.c and openborscript.c system_rand; Win32 32-bit long',
        world_stream_call_order_bound=False,world_initial_seed_policy_bound=False,motu_gameplay_proven=False)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
