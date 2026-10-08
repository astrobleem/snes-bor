"""Bounded checked native birth allocation; no live foreign-world admission."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_model_registry import unpack as unpack_models
from source_birth_templates import unpack as unpack_birth,STRIDE
from source_birth_core import unpack as unpack_core,STRIDE as CORE_STRIDE
from source_lifecycle_inputs import unpack as unpack_lifecycle
from source_model_attack_policy import unpack as unpack_policy
from source_world_pool import empty_pool,descriptor,POOL_BANK,POOL_BASE,SIDE_BASE
from script_ir_4086 import parse_script
from script_bytecode import compile_library
from script_native_module import lower,POLICY
from _harness import MESEN_EXE,_free_tcp_port,pasm_constant_in,read_block,run_frames_exact,exact_input_edge,Reporter
from actor_s5_entity_fixture import symbols
from m4_vm_cost_observer import observed_session,pause_for_injection
import game_bor_startup_select as startup


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True)
    p.add_argument('--registry',type=Path,required=True);p.add_argument('--birth-templates',type=Path,required=True)
    p.add_argument('--frame-aux',action='store_true',help='Lease and verify auxiliary update_frame state during birth')
    p.add_argument('--ai-state-birth',action='store_true',help='Verify distinct AI row reset before alive publication and preserve sibling/rejected state.')
    p.add_argument('--birth-core',type=Path,help='Paired B4BI physical core/flags/relation augmentation')
    p.add_argument('--lifecycle',type=Path,help='Paired B4LI current-model scalars at physical birth')
    p.add_argument('--model-attack-policy',type=Path,help='B4AP model blocking and stealth table, installed before alive')
    p.add_argument('--case',action='append',help='Run only these bounded native probe names.')
    p.add_argument('--physics-state-birth',action='store_true',help='opt-in native physics reset before checked birth publication');p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parents[2];syms=symbols(root/'src/main.sym')
    def c(file,key):return pasm_constant_in(str(root/file),key)
    models=(a.registry/'models.b4mr').read_bytes();rows=unpack_models(models)
    policytable=a.model_attack_policy.read_bytes()if a.model_attack_policy else b''
    if policytable:
        if not a.birth_core or len(unpack_policy(policytable))!=len(rows):raise ValueError('WORLD_BIRTH_ATTACK_POLICY_PAIRED_CORE_REQUIRED')
        a.ai_state_birth=True
    births=(a.birth_templates/'birth.b4bt').read_bytes();count=unpack_birth(births)
    if count!=len(rows):raise ValueError('BIRTH_REGISTRY_PAIRED_COUNT')
    address=syms['SourceVM_InstructionReservation'];offset=(address>>16)*32768+(address&65535)-32768
    raw=bytearray(a.rom.resolve().read_bytes())
    if raw[offset:offset+32768]!=b'\xff'*32768:raise ValueError('BIRTH_TABLE_ROM_RESERVATION_OCCUPIED')
    raw[offset:offset+len(models)]=models;raw[offset+len(models):offset+len(models)+len(births)]=births
    coretable=a.birth_core.read_bytes() if a.birth_core else b''
    coreaddress=address+len(models)+len(births)
    if coretable:
        if unpack_core(coretable)!=count or len(models)+len(births)+len(coretable)>32768:raise ValueError('BIRTH_CORE_PAIRED_RESERVATION')
        raw[offset+len(models)+len(births):offset+len(models)+len(births)+len(coretable)]=coretable
    lifetable=a.lifecycle.read_bytes() if a.lifecycle else b''
    lifeaddress=coreaddress+len(coretable)
    if lifetable:
        if not coretable or len(unpack_lifecycle(lifetable))!=count or lifeaddress-address+len(lifetable)>32768:raise ValueError('LIFECYCLE_BIRTH_PAIRED_RESERVATION')
        raw[offset+lifeaddress-address:offset+lifeaddress-address+len(lifetable)]=lifetable
    rom=a.output/'bor.sfc';rom.write_bytes(raw)
    for path in [a.rom.resolve().with_suffix('.msu'),*a.rom.resolve().parent.glob('bor-*.pcm')]:
        destination=a.output/path.name
        if not destination.exists():os.link(path,destination)
    cases=[('allocated','HBreath',None,'PTR'),('reordered_allocated','HBreath',None,'PTR'),
           ('invalid_order','HBreath',None,'FAULT'),('no_level','HBreath',('VmSourceWorld_Level',0),'EMPTY'),
           ('no_owner','HBreath',('VmSourceWorld_Ready',0),'FAULT'),('missing_model','absent',None,'EMPTY'),
           ('unadmitted','He_Man',None,'FAULT'),('full','HBreath',None,'EMPTY'),
           ('bad_base','HBreath',('VmSourceWorld_PoolBase',0x4001),'FAULT'),
           ('bad_count','HBreath',('VmSourceWorld_Count',129),'FAULT'),
           ('bad_table','HBreath',('VmSourceWorld_TemplateBase',(address+len(models)+2)&65535),'FAULT'),
           ('zero_token','HBreath',None,'FAULT')]
    motion_cases={
        'velocity_full':('changeentityproperty(born,"VeLoCiTy",1.5,-0.75,2.25);changeentityproperty(born,"speed",3.5);',
                         {36:98304,40:-49152,44:147456,60:229376}),
        'velocity_one':('changeentityproperty(born,"velocity",-2);',{36:-131072}),
        'velocity_skip':('changeentityproperty(born,"velocity","invalid",2,NULL());',{40:131072}),
        'speed_skip':('changeentityproperty(born,"speed","invalid");',{}),
        'speed_zero':('changeentityproperty(born,"speed",0);',{60:0}),
        'speed_negative':('changeentityproperty(born,"speed",-0.5);',{60:-32768}),
    }
    toss_cases={
        'toss_full':('tossentity(born,0.25,1.5,-0.75);',{36:98304,40:-49152,44:16384},32768,49),
        'toss_zero':('changeentityproperty(born,"velocity",4,5,6);tossentity(born,0,1.5,-0.75);',
                     {36:98304,40:-49152,44:393216},0,0),
        'toss_one':('tossentity(born);',{36:0,40:0,44:0},0,0),
        'toss_two':('tossentity(born,0.25);',{36:0,40:0,44:16384},32768,49),
        'toss_three':('tossentity(born,0.25,1.5);',{36:98304,40:0,44:16384},32768,49),
        'toss_non_numeric':('changeentityproperty(born,"velocity",4,5,6);tossentity(born,"invalid",1.5,NULL());',
                            {36:98304,40:0,44:393216},0,0),
        'toss_range':('tossentity(born,40000,1.5,-0.75);',{},0,0),
        'toss_no_aux':('tossentity(born,0.25,1.5,-0.75);',{},0,0x11223344),
    }
    cases.extend((n,'HBreath',None,'PTR') for n in motion_cases)
    cases.extend((n,'HBreath',None,'PTR_FAULT' if n in ('toss_range','toss_no_aux') else 'PTR') for n in toss_cases)
    if coretable:cases.extend((n,'HBreath',None,'FAULT') for n in ('missing_core','existing_vars'))
    if coretable:cases.extend([(n,'HBreath',None,outcome) for n,outcome in (('kill_birth','PTR_KILLED'),('kill_dead_birth','PTR_KILLED'),('retire_reuse','PTR'))])
    if lifetable:cases.extend((n,'HBreath',None,'FAULT')for n in ('life_bad_ready','life_bad_table','life_paired','life_sticky'))
    if a.case:
        if set(a.case)-{c[0]for c in cases}:raise ValueError('UNKNOWN_BIRTH_PROBE')
        cases=[c for c in cases if c[0]in a.case]
    reporter=Reporter('M4-SOURCE-WORLD-BIRTH',kind='GATE');results=[]
    const='src/core/vm/vm_consts.pasm';call='src/core/vm/vm_call.pasm';registry='src/core/vm/vm_source_models.pasm'
    world='src/core/vm/vm_source_world_birth.pasm'
    session=observed_session(a.output,syms,0)
    if lifetable:
        observer=a.output/'vm_cost.lua'
        with observer.open('a')as f:
            f.write('''
local publications=0
emu.addMemoryCallback(function()
 if word(LIFEREADY)~=0xb4fb or publications>=128 then return end
 publications=publications+1
 local slot=word(BIRTHSLOT);local base=0x439000+slot*80
 emu.log('BIRTHLIFEPUBLISH|'..slot..'|'..word(base+16)..'|'..word(base+18)..'|'..word(base+74)..'|'..word(0x414004+slot*80))
end,emu.callbackType.exec,PUBLISHADDRESS,PUBLISHADDRESS,emu.cpuType.snes,mt)
'''.replace('LIFEREADY',str(syms['SourceLifecycle4086_Ready'])).replace('BIRTHSLOT',str(syms['SourceBirthCore4086_Slot'])).replace('PUBLISHADDRESS',str(syms['Vm_SourceWorldSpawn__core_published'])))
    if a.ai_state_birth:
        with (a.output/'vm_cost.lua').open('a')as f:
            f.write('''
emu.addMemoryCallback(function()
 local slot=word(BIRTHSLOT);local cleared=0;for j=0,23 do cleared=cleared+emu.read(0x42f400+slot*24+j,mt)end
 emu.log('WORLDBIRTHAI|'..slot..'|'..cleared..'|'..word(0x414004+slot*80))
end,emu.callbackType.exec,PUBLISHADDRESS,PUBLISHADDRESS,emu.cpuType.snes,mt)
'''.replace('BIRTHSLOT',str(syms['SourceBirthCore4086_Slot'])).replace('PUBLISHADDRESS',str(syms['Vm_SourceWorldSpawn__ai_state_published'])))
    if a.physics_state_birth:
        with (a.output/'vm_cost.lua').open('a')as f:
            f.write('''
emu.addMemoryCallback(function()
 local slot=word(BIRTHSLOT);local sum=0;for j=0,15 do sum=sum+emu.read(0x42d800+slot*16+j,mt)end
 emu.log('WORLDBIRTHPHYSICS|'..slot..'|'..sum..'|'..word(0x414004+slot*80))
end,emu.callbackType.exec,PUBLISHADDRESS,PUBLISHADDRESS,emu.cpuType.snes,mt)
'''.replace('BIRTHSLOT',str(syms['SourceBirthCore4086_Slot'])).replace('PUBLISHADDRESS',str(syms['Vm_SourceWorldSpawn__physics_state_published'])))
    if policytable:
        with (a.output/'vm_cost.lua').open('a')as f:
            f.write('''
emu.addMemoryCallback(function()
 local slot=word(BIRTHSLOT);local model=word(BIRTHMODEL);local mismatch,head=0,0
 for j=0,7 do head=head+emu.read(0x42f400+slot*24+j,mt)end
 for j=0,15 do if emu.read(0x42f408+slot*24+j,mt)~=emu.read(0x40bc00+model*16+j,mt)then mismatch=mismatch+1 end end
 emu.log('WORLDBIRTHPOLICY|'..slot..'|'..mismatch..'|'..head..'|'..(word(0x414004+slot*80)|(word(0x414006+slot*80)<<16)))
end,emu.callbackType.exec,PUBLISHADDRESS,PUBLISHADDRESS,emu.cpuType.snes,mt)
'''.replace('BIRTHSLOT',str(syms['SourceBirthCore4086_Slot'])).replace('BIRTHMODEL',str(syms['SourceBirthCore4086_Model'])).replace('PUBLISHADDRESS',str(syms['Vm_SourceWorldSpawn__policy_published'])))
    with session(rom=rom,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=a.output/'mesen.log') as m:
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('BIRTH_PLAYING_REQUIRED')
        run_frames_exact(m,12)
        for name,model,override,outcome in cases:
            body=toss_cases[name][0] if name in toss_cases else motion_cases.get(name,('',{}))[0]
            if name in ('kill_birth','kill_dead_birth','retire_reuse'):body='int killed=killentity(born);'+('int second=killentity(born);' if name=='kill_dead_birth' else 'void again=spawn();' if name=='retire_reuse' else '')
            source='void main(){clearspawnentry();setspawnentry("name","'+model+'");void born=spawn();'+body+'}'
            blob,compiled=lower(compile_library(parse_script(source,'birth-probe.c'),
                                ['clearspawnentry','setspawnentry','spawn','changeentityproperty','NULL','tossentity','killentity']),numeric_policy=POLICY)
            checkpoint=pause_for_injection(m,syms);m.pause();offsets=struct.unpack_from('<6I',blob,24)
            instructions,slots=struct.unpack_from('<2H',blob,8)
            m.write_memory('snesMemory',c(const,'VmCode_Wram'),blob.hex())
            m.write_memory('snesMemory',c(const,'VmSlots_Wram'),blob[offsets[1]:offsets[1]+slots*8].hex())
            for file,key,value in [('src/core/vm/vm_run.pasm','VmPriv_InstrOff',offsets[0]),
                                  (call,'VmCall_CallsitesOff',offsets[2]),(call,'VmCall_ArgSlotsOff',offsets[3]),
                                  ('src/core/vm/vm_string.pasm','VmStr_StringsOff',offsets[4])]:m.write_u16(c(file,key),value)
            pool,sides=empty_pool(2);pool=bytearray(pool)
            if name=='full':
                for n in range(2):struct.pack_into('<H',pool,n*80+4,1)
            if name=='zero_token':pool[:4]=bytes(4)
            pool=bytes(pool)
            m.write_u16(syms['SourceLifecycle4086_Ready'],0)
            m.write_u16(syms['SourceBirthCore4086_Ready'],0)
            m.write_u16(syms['SourceRetirement4086_Ready'],0)
            initial_core=bytes([0xa5])*192;initial_flags=bytes([0xa5])*64;initial_relations=bytes(128)
            if coretable:
                for at,data in ((0x40c000,initial_core),(0x43eb00,initial_flags),(0x409000,bytes(8192)),(0x43fd80,bytes(32)),(0x418800,bytes(24576))):m.write_memory('snesMemory',at,data.hex())
                m.write_u16(0x43fd80,2 if name=='full' else 0)
                for k,v in [('SourceModelEntityCopy4086_Ready',0xb4eb),('SourceModelEntityCopy4086_Entities',2),('SourceModelEntityCopy4086_Models',16),('SourceIdle4086_Ready',0xb4f3),('SourceSelf4086_Ready',0xb4f6),('SourceSelf4086_GlobalLow',0),('SourceSelf4086_GlobalHigh',0),('SourceSelf4086_Active',0),('SourceSelf4086_Fault',0),('VmSourceVars_Ready',0xb4a4),('VmSourceVars_Base',0x8800),('VmSourceVars_Bank',0x41),('VmSourceVars_Count',384),('SourceRetirement4086_Ready',0xb4f8),('SourceRetirement4086_Status',0),('SourceBirthCore4086_Ready',0xb4f9),('SourceBirthCore4086_Status',0),('SourceBirthCore4086_Base',coreaddress&65535),('SourceBirthCore4086_Bank',coreaddress>>16),('SourceBirthCore4086_Bytes',len(coretable)),('SourceBirthCore4086_Models',16)]:m.write_u16(syms[k],v)
                if name=='missing_core':m.write_u16(syms['SourceBirthCore4086_Ready'],0)
                if name=='existing_vars':m.write_memory('snesMemory',0x418800,struct.pack('<I',0x414000).hex())
            initial_life=bytes([0xa5])*160
            if lifetable:
                m.write_memory('snesMemory',0x439000,initial_life.hex())
                for k,v in [('SourceLifecycle4086_Ready',0xb4fb),('SourceLifecycle4086_Status',0),('SourceLifecycle4086_Base',lifeaddress&65535),('SourceLifecycle4086_Bank',lifeaddress>>16),('SourceLifecycle4086_Bytes',len(lifetable)),('SourceLifecycle4086_Models',16)]:m.write_u16(syms[k],v)
                if name=='life_bad_ready':m.write_u16(syms['SourceLifecycle4086_Ready'],0xffff)
                if name=='life_bad_table':m.write_u16(syms['SourceLifecycle4086_Base'],(lifeaddress+2)&65535)
                if name=='life_paired':m.write_u16(syms['SourceLifecycle4086_Models'],15)
                if name=='life_sticky':m.write_u16(syms['SourceLifecycle4086_Status'],3)
            m.write_memory('snesMemory',(POOL_BANK<<16)+POOL_BASE,pool.hex())
            if a.ai_state_birth:m.write_memory('snesMemory',0x42f400,bytes([0xa5]*48).hex())
            if policytable:
                m.write_memory('snesMemory',0x40bc00,policytable[16:].hex())
                m.write_u16(syms['SourceModelAttackPolicy4086_Models'],len(rows));m.write_u16(syms['SourceModelAttackPolicy4086_Ready'],0xb5f0)
            m.write_memory('snesMemory',(POOL_BANK<<16)+SIDE_BASE,sides.hex())
            m.write_u16(syms['SourcePhysicsState4086_Ready'],0xb61c if a.physics_state_birth else 0)
            if a.physics_state_birth:m.write_memory('snesMemory',0x42d800,(bytes([165])*32).hex())
            ordered=name in ('reordered_allocated','invalid_order')
            m.write_u16(syms['SourceWorldTick4086_Ready'],0xb4d5 if ordered else 0)
            m.write_u16(syms['SourceWorldTick4086_Maximum'],0)
            m.write_u16(syms['SourceToss4086_Ready'],0xb4e2 if name in toss_cases and name!='toss_no_aux' else 0)
            m.write_u16(syms['SourceUpdateFrame4086_Ready'],0xb4e3 if a.frame_aux else 0)
            m.write_u16(syms['SourceUpdateFrame4086_State'],0)
            m.write_u16(syms['SourceUpdateFrame4086_Pending'],0)
            initial_aux=bytes([0xA5])*40
            if a.frame_aux:m.write_memory('snesMemory',syms['SOURCE_UPDATE_FRAME_AUX'],initial_aux.hex())
            m.write_memory('snesMemory',syms['SOURCE_WORLD_TOSS_TIMES'],struct.pack('<II',0x11223344,0x55667788).hex())
            m.write_memory('snesMemory',syms['SOURCE_TARGET_ORDER'],
                           struct.pack('<HH',2 if name=='invalid_order' else 1,0).hex())
            if read_block(m,(POOL_BANK<<16)+POOL_BASE,len(pool))!=pool:
                raise ValueError('BIRTH_POOL_WRITEBACK_REQUIRED_BEFORE_LEASE')
            m.write_memory('snesMemory',c(world,'VmSourceWorld_Ready'),
                           descriptor(2,address+len(models),count,len(births),time=48).hex())
            m.write_u16(c(world,'VmSourceWorld_Players'),1)
            m.write_memory('snesMemory',c(world,'VmSourceWorld_AdvanceX'),bytes(10).hex())
            # The same canonical pool view is authoritative during this
            # private lease; the ordinary WRAM read-view cannot own sidecars.
            entity='src/core/vm/vm_source_entity.pasm'
            for key,value in [('VmSourceEntity_Base',POOL_BASE),('VmSourceEntity_Bank',POOL_BANK),
                              ('VmSourceEntity_Count',2),('VmSourceEntity_Ready',0xb48b)]:m.write_u16(c(entity,key),value)
            m.write_u16(c('src/core/vm/vm_source_mutation.pasm','VmSourceMutation_Ready'),0xb4a2)
            m.write_u16(c('src/core/vm/vm_native_variant.pasm','VmNativeVariant_ContextValid'),0xb48f)
            if override:m.write_u16(c(world,override[0]),override[1])
            for key,value in [('VmSourceModels_Base',address&65535),('VmSourceModels_Count',len(rows)),
                              ('VmSourceModels_Bytes',len(models)),('VmSourceModels_Ready',0xb4a1)]:m.write_u16(c(registry,key),value)
            m.write_u8(c(registry,'VmSourceModels_Bank'),address>>16)
            bitmap=bytearray(64)
            for row in rows:bitmap[row['id']//8]|=1<<(row['id']%8)
            m.write_memory('snesMemory',c(registry,'VmSourceModels_Loaded'),bitmap.hex())
            for key,value in [('VmState_Ip',0),('VmState_Error',0),('VmState_InstrCount',instructions),
                              ('VmState_SlotCount',slots),('VmState_FrameTop',0)]:m.write_u16(c(const,key),value)
            m.write_u8(c(const,'VmState_Status'),1)
            for fields in range(1,61):
                run_frames_exact(m,1);state=read_block(m,c(const,'VM_STATE_FIRST'),32)
                status=state[c(const,'VmState_Status')-c(const,'VM_STATE_FIRST')]
                error=struct.unpack_from('<H',state,c(const,'VmState_Error')-c(const,'VM_STATE_FIRST'))[0]
                if status in (4,5):break
            result_slot=compiled['function_local_slots']['main']['born']
            returned=read_block(m,c(const,'VmSlots_Wram')+8*result_slot,32)[:8]
            actual_pool=read_block(m,(POOL_BANK<<16)+POOL_BASE,len(pool))
            actual_sides=read_block(m,(POOL_BANK<<16)+SIDE_BASE,len(sides))
            expected_pool=pool;expected_sides=sides
            born_slot=1 if name=='reordered_allocated' else 0
            if outcome in ('PTR','PTR_FAULT','PTR_KILLED'):
                model_id=next(row['id'] for row in rows if row['lookup_name']==model.lower())
                template=births[24+model_id*STRIDE:24+(model_id+1)*STRIDE]
                at=born_slot*80
                born=bytearray(pool[at:at+4]+b'\x01\0\0\0'+template[16:88])
                if outcome=='PTR_KILLED':born[4:8]=bytes(4);born[36:40]=bytes(4)
                if name in toss_cases:struct.pack_into('<I',born,12,toss_cases[name][2])
                born=bytes(born)
                expected_pool=pool[:at]+born+pool[at+80:]
                side=bytearray(template[88:152])
                struct.pack_into('<II',side,8,48+struct.unpack_from('<I',side,56)[0],48)
                struct.pack_into('<II',side,20,49,49)
                for offset,value in motion_cases.get(name,('',{}))[1].items():struct.pack_into('<i',side,offset,value)
                if name in toss_cases:
                    for offset,value in toss_cases[name][1].items():struct.pack_into('<i',side,offset,value)
                at=born_slot*64
                expected_sides=sides[:at]+bytes(side)+sides[at+64:]
            reporter.check(name+' terminal state',(status,error)==((5,10) if outcome in ('FAULT','PTR_FAULT') else (4,0)))
            reporter.check(name+' exact pool publication or no mutation',actual_pool==expected_pool and actual_sides==expected_sides)
            if outcome!='FAULT':
                expected=struct.pack('<BBHI',5,0,0,(POOL_BANK<<16)+POOL_BASE+born_slot*80) if outcome in ('PTR','PTR_FAULT','PTR_KILLED') else bytes(8)
                reporter.check(name+' complete PTR/EMPTY result',returned==expected)
            if name in toss_cases:
                reporter.check(name+' exact toss timestamp and untouched adjacent slot',
                    read_block(m,syms['SOURCE_WORLD_TOSS_TIMES'],32)[:8]==struct.pack('<II',toss_cases[name][3],0x55667788))
            if a.frame_aux:
                expected_aux=bytearray(initial_aux)
                if outcome in ('PTR','PTR_FAULT','PTR_KILLED'):
                    expected_aux[born_slot*20:(born_slot+1)*20]=bytes(16)+struct.pack('<hH',1,0)
                reporter.check(name+' initialized frame auxiliary row and preserved neighbor',
                    read_block(m,syms['SOURCE_UPDATE_FRAME_AUX'],40)==bytes(expected_aux))
            if coretable:
                expected_core=bytearray(initial_core);expected_flags=bytearray(initial_flags);expected_relations=bytearray(initial_relations)
                if outcome in ('PTR','PTR_FAULT','PTR_KILLED'):
                    row=coretable[24+model_id*CORE_STRIDE:24+(model_id+1)*CORE_STRIDE]
                    expected_core[born_slot*96:(born_slot+1)*96]=row[16:112]
                    expected_flags[born_slot*32:(born_slot+1)*32]=row[112:144]
                    expected_relations[born_slot*64:(born_slot+1)*64]=row[144:208]
                reporter.check(name+' exact core/flags/relations and count at alive publication',read_block(m,0x40c000,192)==bytes(expected_core) and read_block(m,0x43eb00,64)==bytes(expected_flags) and read_block(m,0x409000,128)==bytes(expected_relations) and startup.u16(m,0x43fd80)==(1 if outcome in ('PTR','PTR_FAULT') else 2 if name=='full' else 0))
                if name in ('kill_birth','kill_dead_birth','retire_reuse'):
                    local=compiled['function_local_slots']['main'];expected_kill=struct.pack('<BBHI',1,0,0,1)
                    reporter.check(name+' typed kill result and dead pointer/reuse identity',read_block(m,c(const,'VmSlots_Wram')+8*local['killed'],32)[:8]==expected_kill and (name!='kill_dead_birth' or read_block(m,c(const,'VmSlots_Wram')+8*local['second'],32)[:8]==expected_kill) and (name!='retire_reuse' or read_block(m,c(const,'VmSlots_Wram')+8*local['again'],32)[:8]==returned))
            if lifetable:
                expected_life=bytearray(initial_life)
                if outcome in ('PTR','PTR_FAULT','PTR_KILLED'):
                    row=bytearray(80);struct.pack_into('<I',row,16,1);row[48:68]=lifetable[24+model_id*32+4:24+model_id*32+24];struct.pack_into('<HH',row,72,model_id,0xb4fb)
                    if name in motion_cases and 60 in motion_cases[name][1]:
                        struct.pack_into('<I',row,68,int(motion_cases[name][1][60]!=0));struct.pack_into('<H',row,76,0xb508)
                    expected_life[born_slot*80:(born_slot+1)*80]=row
                reporter.check(name+' current lifecycle row published before alive, or preserved on rejection',read_block(m,0x439000,160)==bytes(expected_life))
            if a.ai_state_birth:
                expected_ai=bytearray([0xa5]*48)
                if outcome in ('PTR','PTR_FAULT','PTR_KILLED'):expected_ai[born_slot*24:(born_slot+1)*24]=bytes(24)
                if policytable and outcome in ('PTR','PTR_FAULT','PTR_KILLED'):expected_ai[born_slot*24+8:(born_slot+1)*24]=policytable[16+model_id*16:32+model_id*16]
                reporter.check(name+' AI birth state resets only the published actor and retains rejected/sibling rows',read_block(m,0x42f400,48)==bytes(expected_ai))
            if a.physics_state_birth:
                expected_physics=bytearray([165]*32)
                if outcome in ('PTR','PTR_FAULT','PTR_KILLED'):
                    expected_physics[born_slot*16:(born_slot+1)*16]=bytes(16)
                reporter.check(name+' physics birth resets only the published row and preserves sibling/rejected rows',read_block(m,0x42d800,32)==bytes(expected_physics))
            if name=='reordered_allocated':
                reporter.check('birth extends the source traversal prefix',startup.u16(m,syms['SourceWorldTick4086_Maximum'])==1)
            results.append(dict(case=name,fields=fields,status=status,error=error,return_variant_hex=returned.hex(),
                                pool_sha256=hashlib.sha256(actual_pool).hexdigest(),sides_sha256=hashlib.sha256(actual_sides).hexdigest(),
                                injection_checkpoint=checkpoint))
        m.write_u16(c(world,'VmSourceWorld_Ready'),0)
        m.write_u16(syms['SourceWorldTick4086_Ready'],0)
        m.write_u16(syms['SourceToss4086_Ready'],0)
        m.write_u16(syms['SourceUpdateFrame4086_Ready'],0)
        m.write_u16(syms['SourceLifecycle4086_Ready'],0)
        m.write_u16(syms['SourceBirthCore4086_Ready'],0)
        m.write_u16(syms['SourceRetirement4086_Ready'],0)
        m.write_u16(syms['SourcePhysicsState4086_Ready'],0)
    publications=[list(map(int,line.split('BIRTHLIFEPUBLISH|',1)[1].split('|')))for line in (a.output/'mesen.log').read_text(errors='replace').splitlines()if 'BIRTHLIFEPUBLISH|'in line]
    if lifetable:
        expected_publications=sum(c[3]in ('PTR','PTR_FAULT','PTR_KILLED')for c in cases)+sum(c[0]=='retire_reuse'for c in cases)
        reporter.check('observer proves source nograb and current model marker before alive publication',len(publications)==expected_publications and all(r[1:]==[1,0,0xb4fb,0]for r in publications))
    report=dict(schema='BYOR_CHECKED_NATIVE_WORLD_BIRTH_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',
                rom_sha256=hashlib.sha256(raw).hexdigest(),cases=results,fixture_pool_count=2,compiler_pool_capacity=128,
                pool_ownership_scope='Injected exclusive BW-RAM lease after legacy candidate bootstrap; no production world loader',
                live_world_owner_bound=False,physics_bound=False,presentation_bound=False,motu_gameplay_proven=False,no_pcm_copies=True,
                motion_property_cases=list(motion_cases),motion_numeric_policy='ACCEPTED_COMPAT_Q16_16')
    report['toss_cases']=list(toss_cases)
    report['frame_auxiliary_initialization_proven']=a.frame_aux
    report['physical_birth_core_initialization_proven']=bool(coretable)
    report['current_lifecycle_birth_installation_proven']=bool(lifetable)
    report['lifecycle_table_sha256']=hashlib.sha256(lifetable).hexdigest() if lifetable else None
    report['lifecycle_before_alive_observer']=publications
    if a.ai_state_birth:
        ai_publications=[list(map(int,line.split('WORLDBIRTHAI|',1)[1].split('|')))for line in (a.output/'mesen.log').read_text(errors='replace').splitlines()if 'WORLDBIRTHAI|'in line]
        expected_publications=sum(c[3]in ('PTR','PTR_FAULT','PTR_KILLED')for c in cases)+sum(c[0]=='retire_reuse'for c in cases)
        reporter.check('observer proves distinct AI row cleared before exists publication',len(ai_publications)==expected_publications and all(r[1:]==[0,0]for r in ai_publications))
        report.update(ai_before_alive_observer=ai_publications,ai_birth_initialization_proven=True,status='PASS'if all(ok for _,ok in reporter.results)else'FAIL')
    if policytable:
        policy_publications=[list(map(int,line.split('WORLDBIRTHPOLICY|',1)[1].split('|')))for line in (a.output/'mesen.log').read_text(errors='replace').splitlines()if 'WORLDBIRTHPOLICY|'in line]
        reporter.check('observer proves full model policy installed after AI reset and before exists publication',len(policy_publications)==expected_publications and all(r[1:]==[0,0,0]for r in policy_publications))
        report.update(model_attack_policy_before_alive_observer=policy_publications,model_attack_policy_birth_installation_proven=True,model_attack_policy_table_sha256=hashlib.sha256(policytable).hexdigest(),status='PASS'if all(ok for _,ok in reporter.results)else'FAIL')
    if a.physics_state_birth:
        physics_publications=[list(map(int,line.split('WORLDBIRTHPHYSICS|',1)[1].split('|')))for line in (a.output/'mesen.log').read_text(errors='replace').splitlines()if'WORLDBIRTHPHYSICS|'in line]
        expected_physics=sum(c[3]in ('PTR','PTR_FAULT','PTR_KILLED')for c in cases)+sum(c[0]=='retire_reuse'for c in cases)
        reporter.check('checked minimal birth clears canonical physics row before alive publication',len(physics_publications)==expected_physics and all(v[1:]==[0,0]for v in physics_publications))
        report.update(physics_birth_before_alive_observer=physics_publications,physics_birth_initialization_proven=True,native_active_gravity_or_landing_proven=False,status='PASS'if all(ok for _,ok in reporter.results)else'FAIL')
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
