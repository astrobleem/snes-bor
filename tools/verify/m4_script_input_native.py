"""Native typed playerkeys masks over a checked source-tick snapshot lease."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_script_input import authority,snapshot,query,ADDRESS
from script_ir_4086 import parse_script
from script_bytecode import compile_library
from script_native_module import lower,POLICY
from _harness import MESEN_EXE,_free_tcp_port,pasm_constant_in,read_block,run_frames_exact,exact_input_edge,Reporter
from actor_s5_entity_fixture import symbols
from m4_vm_cost_observer import observed_session,pause_for_injection
import game_bor_startup_select as startup


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('rom','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parents[2];sy=symbols(root/'src/main.sym')
    def c(file,name):return pasm_constant_in(str(root/file),name)
    rows=[(0x1fff,0x1dc0,0x003c),(0x80000004,0,4),(0,0,0),(0x1080,0,0)]
    cases=[]
    for key in authority()['keys']:
        for mode in range(3):
            cases.append(dict(name=key['name']+'_'+str(mode),index='0',mode=str(mode),
                              key=json.dumps(key['name'].upper()),value=query(rows,0,mode,key['name'])))
        cases.append(dict(name=key['name']+'_selector',index='0',mode='0',key=str(key['selector']),value=key['mask']))
    cases.extend([
        dict(name='second_player',index='1',mode='0',key='"moveleft"',value=4),
        dict(name='fourth_player',index='3',mode='0',key='"attack4"',value=4096),
        dict(name='fractional_index',index='-0.25',mode='0',key='"attack"',value=64),
        dict(name='fractional_mode',index='0',mode='1.75',key='"moveleft"',value=0),
        dict(name='default_index',index='"not a number"',mode='0',key='"jump"',value=128),
        dict(name='default_mode',index='0',mode='NULL()',key='"special"',value=256),
        dict(name='other_mode',index='0',mode='65537',key='"attack2"',value=1024),
        dict(name='dynamic_key',index='0',mode='0',key='"move"+"left"',value=4),
        dict(name='unknown_key',index='0',mode='0',key='"no such key"',value=0),
        dict(name='negative_selector',index='0',mode='0',key='-1',value=0),
        dict(name='decimal_selector',index='0',mode='0',key='1.0',value=0),
        dict(name='missing_owner',index='0',mode='0',key='"attack"',fault=True,ready=0),
        dict(name='oversized_owner',index='0',mode='0',key='"attack"',fault=True,count=5),
        dict(name='empty_owner',index='0',mode='0',key='"attack"',fault=True,count=0),
        dict(name='negative_player',index='-1',mode='0',key='"attack"',fault=True),
        dict(name='past_player',index='4',mode='0',key='"attack"',fault=True),
    ])
    reporter=Reporter('M4-SOURCE-INPUT',kind='GATE');results=[]
    const='src/core/vm/vm_consts.pasm';call='src/core/vm/vm_call.pasm'
    session=observed_session(folder,sy,0)
    with session(rom=a.rom.resolve(),mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('SOURCE_INPUT_PLAYING_REQUIRED')
        run_frames_exact(m,12)
        reporter.check('source input lease is cold-disabled',read_block(m,ADDRESS,32)[:2]==bytes(2))
        for case in cases:
            text='void main(){void value=playerkeys('+case['index']+','+case['mode']+','+case['key']+');}'
            blob,compiled=lower(compile_library(parse_script(text,'input-probe.c'),['playerkeys','NULL']),numeric_policy=POLICY)
            checkpoint=pause_for_injection(m,sy);m.pause();offsets=struct.unpack_from('<6I',blob,24)
            instructions,slots=struct.unpack_from('<2H',blob,8)
            m.write_memory('snesMemory',c(const,'VmCode_Wram'),blob.hex())
            m.write_memory('snesMemory',c(const,'VmSlots_Wram'),blob[offsets[1]:offsets[1]+slots*8].hex())
            for file,name,value in [('src/core/vm/vm_run.pasm','VmPriv_InstrOff',offsets[0]),
                (call,'VmCall_CallsitesOff',offsets[2]),(call,'VmCall_ArgSlotsOff',offsets[3]),
                ('src/core/vm/vm_string.pasm','VmStr_StringsOff',offsets[4])]:m.write_u16(c(file,name),value)
            lease=bytearray(snapshot(rows,12345))
            if 'ready' in case:struct.pack_into('<H',lease,0,case['ready'])
            if 'count' in case:struct.pack_into('<H',lease,2,case['count'])
            m.write_memory('snesMemory',ADDRESS,lease.hex())
            m.write_u16(sy['VmNativeVariant_ContextValid'],0xb48f)
            for name,value in [('VmState_Ip',0),('VmState_Error',0),('VmState_InstrCount',instructions),
                               ('VmState_SlotCount',slots),('VmState_FrameTop',0)]:m.write_u16(c(const,name),value)
            m.write_u8(c(const,'VmState_Status'),1)
            for fields in range(1,31):
                run_frames_exact(m,1);state=read_block(m,c(const,'VM_STATE_FIRST'),32)
                status=state[c(const,'VmState_Status')-c(const,'VM_STATE_FIRST')]
                error=struct.unpack_from('<H',state,c(const,'VmState_Error')-c(const,'VM_STATE_FIRST'))[0]
                if status in (4,5):break
            terminal=(5,10) if case.get('fault') else (4,0)
            reporter.check(case['name']+' terminal',(status,error)==terminal)
            slot=compiled['function_local_slots']['main']['value']
            value=read_block(m,c(const,'VmSlots_Wram')+slot*8,32)[:8]
            if not case.get('fault'):
                reporter.check(case['name']+' exact mask variant',value==struct.pack('<BBHI',1,0,0,case['value']))
            reporter.check(case['name']+' input snapshot stays immutable',read_block(m,ADDRESS,len(lease))==lease)
            results.append(dict(case=case['name'],status=status,error=error,result=value.hex(),fields=fields,
                                injection_checkpoint=checkpoint))
        m.write_u16(ADDRESS,0)
    r=dict(schema='BYOR_SOURCE_PLAYERKEYS_NATIVE_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',
           rom_sha256=hashlib.sha256(a.rom.read_bytes()).hexdigest(),engine_authority=authority(),cases=results,
           scope='Typed source API with injected immutable source-key snapshots after original-BOR bootstrap. No real controller mapping, live MOTU input owner or gameplay claim.',bank0_growth=0)
    (folder/'report.json').write_text(json.dumps(r,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
