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
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parents[2];syms=symbols(root/'src/main.sym')
    def c(file,key):return pasm_constant_in(str(root/file),key)
    models=(a.registry/'models.b4mr').read_bytes();rows=unpack_models(models)
    births=(a.birth_templates/'birth.b4bt').read_bytes();count=unpack_birth(births)
    if count!=len(rows):raise ValueError('BIRTH_REGISTRY_PAIRED_COUNT')
    address=syms['SourceVM_InstructionReservation'];offset=(address>>16)*32768+(address&65535)-32768
    raw=bytearray(a.rom.resolve().read_bytes())
    if raw[offset:offset+32768]!=b'\xff'*32768:raise ValueError('BIRTH_TABLE_ROM_RESERVATION_OCCUPIED')
    raw[offset:offset+len(models)]=models;raw[offset+len(models):offset+len(models)+len(births)]=births
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
    }
    cases.extend((n,'HBreath',None,'PTR') for n in motion_cases)
    reporter=Reporter('M4-SOURCE-WORLD-BIRTH',kind='GATE');results=[]
    const='src/core/vm/vm_consts.pasm';call='src/core/vm/vm_call.pasm';registry='src/core/vm/vm_source_models.pasm'
    world='src/core/vm/vm_source_world_birth.pasm'
    session=observed_session(a.output,syms,0)
    with session(rom=rom,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=a.output/'mesen.log') as m:
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('BIRTH_PLAYING_REQUIRED')
        run_frames_exact(m,12)
        for name,model,override,outcome in cases:
            body=motion_cases.get(name,('',{}))[0]
            source='void main(){clearspawnentry();setspawnentry("name","'+model+'");void born=spawn();'+body+'}'
            blob,compiled=lower(compile_library(parse_script(source,'birth-probe.c'),
                                ['clearspawnentry','setspawnentry','spawn','changeentityproperty','NULL']),numeric_policy=POLICY)
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
            m.write_memory('snesMemory',(POOL_BANK<<16)+POOL_BASE,pool.hex())
            m.write_memory('snesMemory',(POOL_BANK<<16)+SIDE_BASE,sides.hex())
            ordered=name in ('reordered_allocated','invalid_order')
            m.write_u16(syms['SourceWorldTick4086_Ready'],0xb4d5 if ordered else 0)
            m.write_u16(syms['SourceWorldTick4086_Maximum'],0)
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
            if outcome=='PTR':
                model_id=next(row['id'] for row in rows if row['lookup_name']==model.lower())
                template=births[24+model_id*STRIDE:24+(model_id+1)*STRIDE]
                at=born_slot*80
                born=pool[at:at+4]+b'\x01\0\0\0'+template[16:88]
                expected_pool=pool[:at]+born+pool[at+80:]
                side=bytearray(template[88:152])
                struct.pack_into('<II',side,8,48+struct.unpack_from('<I',side,56)[0],48)
                struct.pack_into('<II',side,20,49,49)
                for offset,value in motion_cases.get(name,('',{}))[1].items():struct.pack_into('<i',side,offset,value)
                at=born_slot*64
                expected_sides=sides[:at]+bytes(side)+sides[at+64:]
            reporter.check(name+' terminal state',(status,error)==((5,10) if outcome=='FAULT' else (4,0)))
            reporter.check(name+' exact pool publication or no mutation',actual_pool==expected_pool and actual_sides==expected_sides)
            if outcome!='FAULT':
                expected=struct.pack('<BBHI',5,0,0,(POOL_BANK<<16)+POOL_BASE+born_slot*80) if outcome=='PTR' else bytes(8)
                reporter.check(name+' complete PTR/EMPTY result',returned==expected)
            if name=='reordered_allocated':
                reporter.check('birth extends the source traversal prefix',startup.u16(m,syms['SourceWorldTick4086_Maximum'])==1)
            results.append(dict(case=name,fields=fields,status=status,error=error,return_variant_hex=returned.hex(),
                                pool_sha256=hashlib.sha256(actual_pool).hexdigest(),sides_sha256=hashlib.sha256(actual_sides).hexdigest(),
                                injection_checkpoint=checkpoint))
        m.write_u16(c(world,'VmSourceWorld_Ready'),0)
        m.write_u16(syms['SourceWorldTick4086_Ready'],0)
    report=dict(schema='BYOR_CHECKED_NATIVE_WORLD_BIRTH_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',
                rom_sha256=hashlib.sha256(raw).hexdigest(),cases=results,fixture_pool_count=2,compiler_pool_capacity=128,
                pool_ownership_scope='Injected exclusive BW-RAM lease after legacy candidate bootstrap; no production world loader',
                live_world_owner_bound=False,physics_bound=False,presentation_bound=False,motu_gameplay_proven=False,no_pcm_copies=True,
                motion_property_cases=list(motion_cases),motion_numeric_policy='ACCEPTED_COMPAT_Q16_16')
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
