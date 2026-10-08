"""Source-derived LAND frames through real scripts, POST and world acknowledgement.

Controlled landing inputs, no live combat or presentation claim. Source tables
and linked callback programs are immutable and paired before installing leases.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from compiler import Source
from script_callback_owner import derive as callbacks,pack as pack_callbacks,validate_pair
from source_model_registry import derive as registry,pack as pack_registry
from source_birth_templates import derive as births,pack as pack_births
from source_frame_effects_4086 import derive as frames,pack as pack_frames
from source_frame_effect_plan import derive as effects,pack as pack_effects,unpack as unpack_effects
from source_animation_physics_4086 import derive as physics,pack as pack_physics
from source_landing_plan_4086 import derive as landing,pack as pack_landing
from source_script_variables import descriptor
from script_dispatch_4086 import compile_source
from m4_gravity_landing_commit_native import LUA as BASE_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter

ASM='''AuthoredLandingFixture_Run:
.a16
.i16
 php
 rep #$38
 jsl POSTBEGIN
AuthoredLandingFixture_Progress:
.a16
.i16
 bcs AuthoredLandingFixture_Bad
 cmp #0
 beq AuthoredLandingFixture_Complete
 cmp #$8001
 bne AuthoredLandingFixture_Bad
 jsl POSTCONTINUE
 bra AuthoredLandingFixture_Progress
AuthoredLandingFixture_Complete:
.a16
.i16
 lda #11
 jsl WORLDACK
 bcs AuthoredLandingFixture_Bad
 plp
 clc
 rtl
AuthoredLandingFixture_Bad:
.a16
.i16
 plp
 sec
 rtl
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True)
    p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);source=Source(a.source)
    co,code,metadata,dispatch=callbacks(source);co_bytes=pack_callbacks(co)
    models=registry(source);model_bytes=pack_registry(models);birth_bytes=pack_births(births(source))
    validate_pair(co_bytes,model_bytes,code,metadata,dispatch)
    fr=frames(source);fe=pack_frames(fr);ep_report=effects(fr);ep=pack_effects(ep_report);unpack_effects(ep,fe)
    ph_report=physics(source);ph=pack_physics(ph_report);lp=pack_landing(landing(source))
    identities={h['handle']:h for h in compile_source(source)['animation_handles']}
    models_by_name={m['identity']:m['id']for m in models['models']}
    bundle=bytearray();locations={}
    for name,data in [('code',code),('dispatch',dispatch),('models',model_bytes),('births',birth_bytes),('callbacks',co_bytes)]:
        locations[name]=0x8000+len(bundle);bundle.extend(data)
    assert len(bundle)<=32768 and len(ep)<=0x7000 and len(lp)<=0x1000
    rows=[]
    for animation in ph_report['animations']:
        lf=animation['landframe']
        if lf<0:continue
        handle=animation['handle'];identity=identities[handle];model=models_by_name[animation['model']]
        operations=ep_report['animations'][handle-1]['frames'][lf]['ops']
        if operations!=[17,23]:raise ValueError('AUTHORED_LAND_EXTERNAL_EFFECT_REQUIRED')
        for slot in (0,63,127):
            for direction in (0,1):
                rows.append(dict(slot=slot,model=model,handle=handle,animid=identity['engine_animation_id'],
                    lf=lf,delay=fr['animations'][handle-1]['frames'][lf]['delay_ticks'],direction=direction,
                    a=0,base=0,altbase=0,vy=-65536,noadjust=1,hole=1,wall=1,platform=1,freeze=0,mark=0,
                    time=48,toss=0,falling=1,hithead=1,gravity=0,minfall=-6*65536,maxtoss=100*65536,
                    subject=0,damage=0,autoland=0,noquake=0,fault=0,bounced=0,
                    expected=[0,0,0,0,0,49,12,11]))
    lua=BASE_LUA[:BASE_LUA.index("emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1]\n if c.landing_bad")]
    lua=lua.replace('TABLEBYTES',str(len(ph))).replace('PLANBYTES',str(len(lp))).replace('PLANCOUNT','80')
    lua=lua.replace("set('SourceAnimationPhysics4086_Animations',6)","set('SourceAnimationPhysics4086_Animations',80)")
    lua=lua.replace("set('SourceLandingPlan4086_Base',0x8000)","set('SourceLandingPlan4086_Base',0xf000)")
    slots=struct.unpack_from('<H',metadata,10)[0];offs=struct.unpack_from('<6I',metadata,24)
    controls=dict(SourcePostAir4086_Ready=0xb628,SourcePostAir4086_State=0,SourcePostAir4086_Service=0,
        SourcePostStationary4086_Ready=0,SourceCheckMove4086_Ready=0xb617,SourceCheckMove4086_Status=0,
        SourceUpdateFrame4086_State=0,SourceUpdateFrame4086_Pending=0,SourceUpdateFrame4086_Fault=0,
        SourceUpdateFrame4086_Base=0x8000,SourceUpdateFrame4086_Bank=60,SourceUpdateFrame4086_Bytes=len(fe),
        SourceFrameEffectPlan4086_Ready=0xb4f2,SourceFrameEffectPlan4086_State=0,SourceFrameEffectPlan4086_Service=0,
        SourceFrameEffectPlan4086_Acknowledged=0,SourceFrameEffectPlan4086_Base=0x8000,SourceFrameEffectPlan4086_Bank=59,
        SourceFrameEffectPlan4086_Bytes=len(ep),SourceFrameEffectPlan4086_Animations=80,
        SourceFrameMotion4086_Ready=0xb4e8,SourceFrameMotion4086_Status=0,SourceFrameEffectLeaf4086_Ready=0xb4f4,
        SourceIdle4086_Ready=0xb4f3,SourceAnimationCallback4086_Ready=0xb4e6,SourceAnimationCallback4086_State=0,
        SourceAnimationCallback4086_Base=locations['callbacks'],SourceAnimationCallback4086_Bank=38,
        SourceAnimationCallback4086_Bytes=len(co_bytes),SourceWorldTick4086_Index=0,
        VmSourceModels_Ready=0xb4a1,VmSourceModels_Base=locations['models'],VmSourceModels_Bank=38,
        VmSourceModels_Count=16,VmSourceModels_Bytes=len(model_bytes),VmSourceEntity_Ready=0xb48b,
        VmSourceEntity_Base=0x4000,VmSourceEntity_Bank=0x41,VmSourceEntity_Count=128,VmSourceMutation_Ready=0xb4a2,
        SourceVMRun4086_Ready=0xb4d7,SourceVMRun4086_Busy=0,VmSourceCallback_Ready=0xb4a5,
        VmSourceCallback_Active=0,VmSourceCallback_Request=0,VmSourceFrame_Ready=0xb4fd,
        VmSourceFrame_Base=locations['dispatch'],VmSourceFrame_Bank=38,VmSourceFrame_Bytes=len(dispatch),
        VmSourceFrame_Programs=co['program_count'],VmSourceFrame_Handles=80,VmSourceFrame_Pending=0,
        VmSourceInstr_Ready=0xb48e,VmSourceInstr_Base=0x8000,VmSourceInstr_Bank=38,
        VmPriv_InstrOff=0,VmCall_CallsitesOff=offs[2],VmCall_ArgSlotsOff=offs[3],VmStr_StringsOff=offs[4],
        VmState_InstrCount=len(code)//8,VmState_SlotCount=slots,VmState_FrameTop=0,VmState_Error=0,
        VmNativeVariant_ContextValid=0,SourceClock4086_Ready=0,SourceAnimationInit4086_Ready=0,
        SourceModelAnimation4086_Ready=0,SourceModelTransition4086_Ready=0,SourceFrameStack4086_Ready=0,
        SourceRetirement4086_Ready=0,SourceBirthCore4086_Ready=0)
    install='\n'+''.join(" set('"+k+"',"+str(v)+');\n'for k,v in controls.items())
    install+=r'''
 for i,v in ipairs(metadata)do emu.write(sy.VmCode_Wram+i-1,v,mt)end
 for i,v in ipairs(vars_descriptor)do emu.write(sy.VmSourceVars_Ready+i-1,v,mt)end
 for i=0,24575 do emu.write(0x418800+i,0,mt)end
 for i=0,63 do emu.write(sy.VmSourceModels_Loaded+i,i<2 and 255 or 0,mt)end
 set('VmState_Status',0,1);set('SourcePostAir4086_Slot',s);set('SourceSelf4086_GlobalLow',0,4)
 set('SourceEmptyInitEnvironment4086_Models',16);set('SourceModelEntityCopy4086_Models',16);set('SourceGravityAir4086_ZeroModels',16)
 set('VmSourceWorld_TemplateBase',BIRTHBASE);set('VmSourceWorld_TemplateBank',38);set('VmSourceWorld_TemplateCount',16);set('VmSourceWorld_TemplateBytes',BIRTHBYTES)
 set('SourceFrameEffectPlan4086_PairedCrcLo',PAIRCRC,4);set('SourceFrameEffectPlan4086_BodyCrcLo',BODYCRC,4)
 put(side,c.model);put(side+2,c.model);put(life+72,c.model);put(life+20,0,4);put(life+4,0,4)
 put(view+16,1);put(view+18,0);put(view+20,c.animid,4);put(view+28,c.direction,4)
 put(aux,0,4);put(aux+4,0,4);put(aux+12,17,4);put(aux+16,1);put(side+24,48,4);put(core+72,32,4)
 put(view+48,2);put(view+50,0);put(view+52,10*65536,4);put(view+56,2);put(view+58,0);put(view+60,20*65536,4)
 put(0x43fb00+(c.handle-1)*4,0,4)
'''
    for name,value in dict(BIRTHBASE=locations['births'],BIRTHBYTES=len(birth_bytes),PAIRCRC=struct.unpack_from('<I',ep,24)[0],BODYCRC=struct.unpack_from('<I',ep,28)[0]).items():install=install.replace(name,str(value))
    lua=lua.replace(' before={};for',install+' before={};for')
    # At slot127 the side-row fence crosses into the owned script-variable
    # heap. Its descriptor/name cache legitimately changes during callbacks.
    # Exclude that domain from actor fences and verify its values separately.
    lua=lua.replace('emu.addMemoryCallback(function()\n local s=emu.getState();started=',
        'emu.addMemoryCallback(function()\n for addr in pairs(before)do if addr>=0x418800 and addr<0x41e800 then before[addr]=nil end end\n local s=emu.getState();started=')
    lua=lua.replace(' local n=0;for a,v in pairs(before)',r'''
 local aux=0x41f500+c.slot*20
 for _,r in ipairs({{side+6,c.lf,2},{side+8,c.time+c.delay,4},{side+24,49,4},{aux+12,0,4}})do for i=0,r[3]-1 do before[r[1]+i]=(r[2]>>(8*i))&255 end end
 local n=0;for a,v in pairs(before)''')
    lua=lua.replace("emu.log('GRAVITYCOMMIT|'","emu.log('AUTHOREDLAND|'")
    lua=lua.replace("emu.log('AUTHOREDLAND|'", "local variable_faults=0;for row=0,383 do for j=8,15 do if emu.read(0x418800+row*64+j,mt)~=0 then variable_faults=variable_faults+1 end end end\n local metadata_faults=0;for i,v in ipairs(metadata)do if emu.read(sy.VmCode_Wram+i-1,mt)~=v then metadata_faults=metadata_faults+1 end end\n emu.log('AUTHOREDLAND|'")
    lua=lua.replace("word(sy.SourceGravityLanding4086_Service))", "word(sy.SourceGravityLanding4086_Service)..'|'..word(sy.SourcePostAir4086_State)..'|'..word(sy.SourceCheckMove4086_Status)..'|'..word(sy.SourceAnimationCallback4086_State)..'|'..word(sy.VmSourceCallback_Active)..'|'..word(sy.VmNativeVariant_ContextValid)..'|'..word(sy.SourceSelf4086_GlobalLow)..'|'..word(sy.SourceSelf4086_GlobalHigh)..'|'..word(sy.SourceWorldTick4086_Pending)..'|'..variable_faults..'|'..metadata_faults)")
    lua='local metadata={'+','.join(map(str,metadata))+'}\nlocal vars_descriptor={'+','.join(map(str,descriptor(0x414000,count=384)))+'}\n'+lua
    reporter=Reporter('M4-AUTHORED-LANDFRAME',kind='GATE')
    raw,log=run_fixture(a.rom,a.output,rows,'AuthoredLandingFixture_Run','SourcePostAir4086_Ready',0xb628,
        [(38,0,bundle),(58,0,ph),(59,0,ep),(59,0x7000,lp),(60,0,fe)],lua,reporter,append=ASM,
        bindings=dict(POSTBEGIN='SourcePostAir4086_Begin',POSTCONTINUE='SourcePostAir4086_Continue',WORLDACK='SourceWorldTick4086_Ack'))
    actual=[list(map(int,l.split('AUTHOREDLAND|',1)[1].split('|')))for l in log.splitlines()if 'AUTHOREDLAND|'in l]
    expected=[[i,0,0,2,2,0,2,2,3,0,0,0,0,0,0,0]for i in range(len(rows))]
    reporter.check('all authored LAND identities run actual callback/effects and native POST before world Ack, preserving unrelated bytes and CPU',actual==expected)
    report=dict(schema='BYOR_4086_AUTHORED_LANDFRAME_NATIVE_V1',status='PASS'if actual==expected else'FAIL',cases=len(rows),
        inputs=rows,actual=actual,expected=expected,source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),
        rom_sha256=hashlib.sha256(raw).hexdigest(),compiled_tables_sha256={k:hashlib.sha256(v).hexdigest()for k,v in dict(callbacks=co_bytes,code=code,metadata=metadata,dispatch=dispatch,frames=fe,effects=ep,physics=ph,landing=lp).items()},
        native_authored_landing_scripts_proven=actual==expected,controlled_landing_inputs=True,
        actual_full_world_traversal_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
