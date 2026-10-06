"""Checked source property mutations; injected authoritative lease, no live world."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from script_ir_4086 import parse_script
from script_bytecode import compile_library
from script_native_module import lower,POLICY
from source_entity_abi import record,view,STRIDE
from _harness import MESEN_EXE,_free_tcp_port,pasm_constant_in,read_block,run_frames_exact,exact_input_edge,Reporter
from actor_s5_entity_fixture import symbols
from m4_vm_cost_observer import observed_session,pause_for_injection
from m4_source_entity_fixture import fixture_base
import game_bor_startup_select as startup


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--environment-only',action='store_true')
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parents[2];syms=symbols(root/'src/main.sym')
    def c(file,key):return pasm_constant_in(str(root/file),key)
    base=fixture_base(root,STRIDE);token=0x6abcde
    values=dict(a=10*65536,animationid=36,direction=0,health=100,playerindex=1,x=80*65536,z=220*65536,maxhealth=150)
    original=record(token,values);descriptor,payload=view(base,[original])
    # Expected values come directly from the pinned per-component conversion
    # rules. Do not compare native output only against another generic mutator.
    cases=[
      ('position_and_direction','changeentityproperty(self,"PoSiTiOn",98.25,221,93.5);changeentityproperty(self,"direction",1);',dict(x=98*65536+16384,z=221*65536,a=93*65536+32768,direction=1),True,token,False,True),
      ('one_component','changeentityproperty(self,"position",99);',dict(x=99*65536),True,token,False,True),
      ('two_components','changeentityproperty(self,"position",99,222);',dict(x=99*65536,z=222*65536),True,token,False,True),
      ('independent_conversion','changeentityproperty(self,"position","bad",222,94);',dict(z=222*65536,a=94*65536),True,token,False,True),
      ('integer_truncation','changeentityproperty(self,"direction",-1.5);changeentityproperty(self,"health",400.99);',dict(direction=-1,health=400),True,token,False,True),
      ('q16_edges','changeentityproperty(self,"position",-32768,32767,-32767.75);',dict(x=-32768*65536,z=32767*65536,a=-32767*65536-49152),True,token,False,True),
      ('dynamic_property','void key="pos"+"ition";changeentityproperty(self,key,99,222,94);',dict(x=99*65536,z=222*65536,a=94*65536),True,token,False,True),
      ('readonly','changeentityproperty(self,"position",99,222,94);',{},False,token,False,False),
      ('stale','changeentityproperty(self,"direction",1);',{},True,token+1,False,False),
      ('null','changeentityproperty(NULL(),"position",99,222,94);',{},False,token,False,True),
      ('unsupported','changeentityproperty(self,"velocity",1,2,3);',{},True,token,False,False),
      ('coordinate_range','changeentityproperty(self,"position",32768);',{},True,token,False,False),
      ('bad_record_tag','changeentityproperty(self,"position",99);',{},True,token,True,False),
    ]
    environments={
      'empty_integer':('void wall=checkwall(100,220);',0xb4d1,0,1,True),
      'empty_decimal':('void wall=checkwall(-123.5,220.25);',0xb4d1,0,2,True),
      'empty_invalid_number':('void wall=checkwall("invalid",NULL());',0xb4d1,0,1,True),
      'empty_pointer':('void wall=checkwall(self,220);',0xb4d1,0,1,True),
      'environment_no_lease':('void wall=checkwall(100,220);',0,0,1,False),
      'environment_nonempty':('void wall=checkwall(100,220);',0xb4d1,1,1,False),
      'environment_no_stage':('void wall=checkwall(100,220);',0xb4d1,0,0,False),
      'environment_no_context':('void wall=checkwall(100,220);',0xb4d1,0,1,False),
    }
    if a.environment_only:
        cases=[(n,v[0],{},False,token,False,v[4]) for n,v in environments.items()]
    reporter=Reporter('M4-SOURCE-PROPERTY-MUTATION',kind='GATE');results=[]
    const='src/core/vm/vm_consts.pasm';call='src/core/vm/vm_call.pasm';variant='src/core/vm/vm_native_variant.pasm'
    entity='src/core/vm/vm_source_entity.pasm';mutation='src/core/vm/vm_source_mutation.pasm'
    session=observed_session(a.output,syms,0) # checkpoint only; no execution cost claim
    script=a.output/'vm_cost.lua'
    with script.open('a') as f:
        f.write('local failures=0; emu.addMemoryCallback(function() if failures>=16 then return end; failures=failures+1; '
                'emu.log("M4MUTFAIL|"..string.format("ready=%04x,name=%04x,offset=%04x,tag=%04x,arg=%04x,keylen=%04x,lo=%04x,hi=%04x",'
                'word(0x7ff6d4),word(0x7ff6d6),word(0x7ff6dc),word(0x7ff6e2),word(0x7ff6da),word(0x7ff636),word(0x7ff6de),word(0x7ff6e0))) '
                'end,emu.callbackType.exec,'+str(syms['Vm_SourceEntityChange__bad'])+','+str(syms['Vm_SourceEntityChange__bad'])+',emu.cpuType.snes,mt)\n')
    with session(rom=a.rom.resolve(),mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=a.output/'mesen.log') as m:
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('MUTATION_PLAYING_REQUIRED')
        for name,body,changes,mutable,handle,bad_tag,success in cases:
            source='void main(){void self=getlocalvar("self");'+body+'}'
            blob,compiled=lower(compile_library(parse_script(source,'property-mutation-probe.c'),
                                ['NULL','getlocalvar','changeentityproperty','checkwall']),numeric_policy=POLICY)
            checkpoint=pause_for_injection(m,syms);m.pause();offsets=struct.unpack_from('<6I',blob,24)
            count,slots=struct.unpack_from('<2H',blob,8)
            m.write_memory('snesMemory',c(const,'VmCode_Wram'),blob.hex())
            m.write_memory('snesMemory',c(const,'VmSlots_Wram'),blob[offsets[1]:offsets[1]+slots*8].hex())
            for file,key,value in [('src/core/vm/vm_run.pasm','VmPriv_InstrOff',offsets[0]),
                                  (call,'VmCall_CallsitesOff',offsets[2]),(call,'VmCall_ArgSlotsOff',offsets[3]),
                                  ('src/core/vm/vm_string.pasm','VmStr_StringsOff',offsets[4])]:m.write_u16(c(file,key),value)
            m.write_memory('snesMemory',c(variant,'VmNativeVariant_Self'),(struct.pack('<BBHI',5,0,0,handle)+bytes(24)).hex())
            m.write_u16(c(variant,'VmNativeVariant_ContextValid'),0xb48f)
            m.write_memory('snesMemory',c(entity,'VmSourceEntity_Base'),descriptor.hex())
            initial=bytearray(payload)
            if bad_tag:initial[48]=1
            m.write_memory('snesMemory',base,initial.hex())
            m.write_u16(c(mutation,'VmSourceMutation_Ready'),0xb4a2 if mutable else 0)
            if a.environment_only:
                _,ready,walls,stage,_=environments[name]
                m.write_memory('snesMemory',c('src/core/vm/vm_source_environment.pasm','SourceEnvironment4086_Ready'),
                               struct.pack('<HHH',ready,walls,stage).hex())
                if name=='environment_no_context':m.write_u16(c(variant,'VmNativeVariant_ContextValid'),0)
            for key,value in [('VmState_Ip',0),('VmState_Error',0),('VmState_InstrCount',count),
                              ('VmState_SlotCount',slots),('VmState_FrameTop',0)]:m.write_u16(c(const,key),value)
            m.write_u8(c(const,'VmState_Status'),1)
            for fields in range(1,61):
                run_frames_exact(m,1);state=read_block(m,c(const,'VM_STATE_FIRST'),32)
                status=state[c(const,'VmState_Status')-c(const,'VM_STATE_FIRST')]
                error=struct.unpack_from('<H',state,c(const,'VmState_Error')-c(const,'VM_STATE_FIRST'))[0]
                if status in (4,5):break
            actual=read_block(m,base,STRIDE)
            expected=record(token,values|changes) if changes else bytes(initial)
            reporter.check(name+' terminal state',(status,error)==((4,0) if success else (5,10)))
            reporter.check(name+' exact record and unchanged fields',actual==expected)
            returned=read_block(m,c(variant,'VmNativeVariant_Result'),32)[:8]
            if success:
                if a.environment_only:
                    expected_variant=struct.pack('<BBHI',2,0,0,0)
                    reporter.check(name+' complete DECIMAL zero result',returned==expected_variant)
                    slot=compiled['function_local_slots']['main']['wall']
                    reporter.check(name+' typed destination variant',read_block(m,c(const,'VmSlots_Wram')+8*slot,32)[:8]==expected_variant)
                else:reporter.check(name+' complete EMPTY result',returned==bytes(8))
            results.append(dict(case=name,source=source,module_sha256=compiled['sha256'],fields=fields,
                                status=status,error=error,actual_hex=actual.hex(),expected_hex=expected.hex(),
                                return_variant_hex=returned.hex(),injection_checkpoint=checkpoint))
        m.write_u16(c(mutation,'VmSourceMutation_Ready'),0)
        if a.environment_only:m.write_u16(c('src/core/vm/vm_source_environment.pasm','SourceEnvironment4086_Ready'),0)
    report=dict(schema='BYOR_SOURCE_EMPTY_WALL_NATIVE_V1' if a.environment_only else 'BYOR_SOURCE_PROPERTY_MUTATION_NATIVE_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',
                rom_sha256=hashlib.sha256(a.rom.read_bytes()).hexdigest(),entity_fixture_base=base,cases=results,
                numeric_policy=POLICY,source_numeric_equivalence=False,live_world_owner_bound=False,
                entity_allocator_bound=False,motu_gameplay_proven=False,
                authority='af23dc9 openborscript.c openbor_checkwall' if a.environment_only else 'af23dc9 openborscript.c position/direction/health, ScriptVariant numeric conversions')
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
