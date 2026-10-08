"""Actual gravity landing -> native frame motion/quake/self retirement.

Nonanimating source frames deliberately skip SCRIPT, as pinned BOR does.
No host frame/cursor acknowledgement and no actor mutation after initialization.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from source_animation_physics_4086 import pack as pack_physics
from source_landing_plan_4086 import pack as pack_landing
from source_frame_effects_4086 import loader_frames, pack as pack_frames
from source_frame_effect_plan import derive, pack as pack_effects
from m4_gravity_landing_commit_native import LUA as COMMIT_LUA, ASM
from _source_leaf_fixture import run_fixture
from _harness import Reporter


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    animations=[];physics=[];plans=[];rows=[]
    for lf in (-1,0,1,2,3):
        handle=len(animations)+1
        events=loader_frames([dict(directive='anim',values=['idle'],line=1)])[0]['events']
        events.update(flipframe=1,quake_start=1,quake_value=7,quake_repeat=0)
        animations.append(dict(handle=handle,events=events,frames=[
            dict(move=dict(base=-1,x=0,y=0,z=0),sound=None,delay_ticks=6),
            dict(move=dict(base=-1,x=3,y=2,z=-1),sound=None,delay_ticks=8)]))
        physics.append(dict(handle=handle,antigrav=0,dropframe=-1,landframe=lf,land_entity_index=-1,
                            frames=[dict(movement=dict(base=-1,y=0)) for _ in range(2)]))
        plans.append(dict(handle=handle,model_index=0,animation_bounce=0.,model_bounce=1,noquake=0))
        for slot in (0,63,127):
            for direction in (0,1):
                # Only LF=1 invokes a real frame. LF=count=2 is the literal no-op.
                active=lf==1
                rows.append(dict(slot=slot,handle=handle,a=0,base=0,altbase=0,vy=-65536,noadjust=1,
                    hole=1,wall=1,platform=1,freeze=0,mark=0,time=48,toss=0,falling=1,hithead=1,
                    gravity=0,minfall=-6*65536,maxtoss=100*65536,subject=0,damage=0,autoland=0,
                    noquake=0,fault=0,bounced=0,direction=direction,active=int(active),lf=lf,
                    expected=[0,0,0,0,0,49,8,7 if active else 11]))
    fe=pack_frames(dict(models=['effect'],animations=animations))
    ep=pack_effects(derive(dict(models=['effect'],animations=animations)))
    ph=pack_physics(dict(animations=physics));lp=pack_landing(dict(plans=plans))
    crc=struct.unpack_from('<I',ep,24)[0]
    lua=COMMIT_LUA[:COMMIT_LUA.index("emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1]\n if c.landing_bad")]
    lua=lua.replace('TABLEBYTES',str(len(ph))).replace('PLANBYTES',str(len(lp))).replace('PLANCOUNT','5')
    lua=lua.replace("set('SourceAnimationPhysics4086_Animations',6)","set('SourceAnimationPhysics4086_Animations',5)")
    install="""
 set('SourceUpdateFrame4086_State',0);set('SourceUpdateFrame4086_Pending',0);set('SourceUpdateFrame4086_Fault',0)
 set('SourceUpdateFrame4086_Base',0x8000);set('SourceUpdateFrame4086_Bank',60);set('SourceUpdateFrame4086_Bytes',FEBYTES);set('SourceUpdateFrame4086_Animations',5)
 set('SourceFrameEffectPlan4086_Ready',0xb4f2);set('SourceFrameEffectPlan4086_State',0);set('SourceFrameEffectPlan4086_Service',0);set('SourceFrameEffectPlan4086_Acknowledged',0)
 set('SourceFrameEffectPlan4086_Base',0x9000);set('SourceFrameEffectPlan4086_Bank',60);set('SourceFrameEffectPlan4086_Bytes',EPBYTES);set('SourceFrameEffectPlan4086_Animations',5);set('SourceFrameEffectPlan4086_PairedCrcLo',PAIRCRC,4);set('SourceFrameEffectPlan4086_BodyCrcLo',BODYCRC,4)
 set('SourceFrameMotion4086_Ready',0xb4e8);set('SourceFrameMotion4086_Status',0);set('SourceFrameEffectLeaf4086_Ready',0xb4f4)
 set('SourceIdle4086_Ready',0xb4f3)
 set('VmState_Status',0,1);set('VmState_Error',0);put(aux,0,4);put(aux+4,0,4);put(aux+12,17,4);put(aux+16,0)
 put(view+16,1);put(view+18,0);put(view+20,0,4);put(view+28,c.direction,4);put(0x43fb00+(c.handle-1)*4,0,4)
""".replace('FEBYTES',str(len(fe))).replace('EPBYTES',str(len(ep))).replace('PAIRCRC',str(crc)).replace('BODYCRC',str(struct.unpack_from('<I',ep,28)[0]))
    lua=lua.replace(' before={};for',install+' before={};for')
    # The retained byte observer admits only the source frame's actual stores.
    insert="""
 if c.active==1 then
  for _,r in ipairs({{side+6,1,2},{aux, c.direction==0 and -3*65536 or 3*65536,4},
   {aux+4,-65536,4},{aux+8,2*65536,4},{side+48,2*65536,4},{view+28,1-c.direction,4}})do
   for i=0,r[3]-1 do before[r[1]+i]=(r[2]>>(8*i))&255 end
  end
 end
"""
    lua=lua.replace(' local n=0;for a,v in pairs(before)',insert+' local n=0;for a,v in pairs(before)')
    lua=lua.replace(' if c.active==1 then',' local aux=0x41f500+c.slot*20\n if c.active==1 then')
    lua=lua.replace("emu.log('GRAVITYCOMMIT|'","emu.log('LANDFRAME|'")
    lua=lua.replace("word(sy.SourceGravityLanding4086_Service))", "word(sy.SourceGravityLanding4086_Service)..'|'..word(sy.SourceUpdateFrame4086_State)..'|'..word(sy.SourceSelf4086_Active))")
    lua+=r'''
for _,name in ipairs({'SourceFrameMotion4086_Bad','SourceFrameEffectPlan4086_Bad','SourceFrameEffectLeaf4086_Bad','SourceFrameEffects4086_Bad','SourceUpdateFrame4086_Bad'})do
 if sy[name] then emu.addMemoryCallback(function()
 local s=emu.getState();emu.log('FRAMEFAULT|'..name..'|'..word(INDEX)..'|'..s['cpu.a']..'|'..s['cpu.x']..'|'..word(sy.SourceFrameEffectPlan4086_State)..'|'..word(sy.SourceFrameEffectPlan4086_Service))
 end,emu.callbackType.exec,sy[name],sy[name],emu.cpuType.snes,mt)end
end
'''
    reporter=Reporter('M4-GRAVITY-LANDFRAME',kind='GATE')
    raw,log=run_fixture(a.rom,a.output,rows,'GravityCommitFixture_Run','SourceGravityLanding4086_Ready',0xb627,
        [(58,0,ph),(59,0,lp),(60,0,fe),(60,0x1000,ep)],lua,reporter,append=ASM,
        bindings=dict(AIR='SourceGravityAir4086_Execute',VELOCITY='SourceLandingVelocity4086_Execute',LANDINGBEGIN='SourceGravityLanding4086_Begin'))
    actual=[list(map(int,l.split('LANDFRAME|',1)[1].split('|')))for l in log.splitlines()if 'LANDFRAME|' in l]
    expected=[[i,0,0,2,2,0,2 if r['lf'] in (1,2) else 0,0]for i,r in enumerate(rows)]
    reporter.check('actual landing frame, motion, quake, facing and self retirement precede gravity commit; count boundary is a no-op',actual==expected)
    report=dict(schema='BYOR_4086_GRAVITY_LANDFRAME_NATIVE_V1',status='PASS'if actual==expected else'FAIL',
        cases=len(rows),inputs=rows,actual=actual,expected=expected,rom_sha256=hashlib.sha256(raw).hexdigest(),
        frame_table_sha256=hashlib.sha256(fe).hexdigest(),effect_plan_sha256=hashlib.sha256(ep).hexdigest(),
        native_landframe_motion_quake_self=True,native_animation_script_landframe_proven=False,
        source_nonanimating_skips_script=True,host_acknowledgements=False,native_world_post_integration_bound=False,
        motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
