"""Real native air -> checked landing velocity, actual toss and quake; no POST Ack."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from source_animation_physics_4086 import pack as pack_physics
from source_landing_plan_4086 import pack as pack_plans
from source_landing_bounce_4086 import bounce_predicate
from m4_gravity_air_native import LUA as AIR_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=AIR_LUA
LUA=LUA.replace('local before,cpu,ctx={},{},0','local before,cpu,ctx={},{},0;local started=0')
LUA=LUA.replace('local s=emu.getState();cpu={};','local s=emu.getState();started=s.masterClock;cpu={};')
LUA=LUA.replace(" if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end", " if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end\n emu.log('LANDCOST|'..word(INDEX)..'|'..(s.masterClock-started))")
LUA=LUA.replace('put(phy+12,99,4)','put(phy+12,c.damage,4)')
LUA=LUA.replace(' before={};for',r'''
 set('SourceLandingPlan4086_Ready',0xb625);set('SourceLandingPlan4086_Status',0);set('SourceLandingPlan4086_Base',0x8000)
 set('SourceLandingPlan4086_Bank',59);set('SourceLandingPlan4086_Bytes',PLANBYTES);set('SourceLandingPlan4086_Animations',PLANCOUNT)
 set('SourceLandingVelocity4086_Ready',0xb626);set('SourceLandingVelocity4086_Status',0);set('SourceLandingVelocity4086_Autoland',c.autoland);set('SourceLandingVelocity4086_Slot',s)
 set('SourceEntityToss4086_Ready',0xb624);set('SourceEntityToss4086_Status',0)
 put(sy.SourceFrameEffectLeaf4086_LevelQuakeLo,11,4)
 before={};for''')
LUA=LUA.replace('{life-8,96}','{life-8,96},{sy.SourceFrameEffectLeaf4086_LevelQuakeLo,4}')
start=LUA.index(' local c=rows[word(INDEX)+1];local side=0x416800+c.slot*64',LUA.index('AFTER,AFTER'))
end=LUA.index('end,emu.callbackType.exec,RESULT',start)
LUA=LUA[:start]+r'''
 local c=rows[word(INDEX)+1];local side=0x416800+c.slot*64;local view=0x414000+c.slot*80;local phy=0x42d800+c.slot*16;local freeze=0x42e000+c.slot*40
 for _,r in ipairs({{view+12,c.expected[1]},{side+44,c.expected[2]},{side+36,c.expected[3]},{side+40,c.expected[4]},
 {phy,c.expected[5]},{0x41f300+c.slot*4,c.expected[6]},{freeze+36,c.expected[7]},{phy+4,0},{sy.SourceFrameEffectLeaf4086_LevelQuakeLo,c.expected[8]}})do for i=0,3 do before[r[1]+i]=(r[2]>>(8*i))&255 end end
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('LANDVELOCITY|'..word(INDEX)..'|'..ctx..'|'..n..'|'..word(sy.SourceLandingVelocity4086_Status)..'|'..word(sy.SourceGravityAir4086_Status))
'''+LUA[end:]
LUA+=r'''
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 if c.landing_bad=='ready'then set('SourceLandingVelocity4086_Ready',1)
 elseif c.landing_bad=='air'then set('SourceGravityAir4086_Status',2)
 elseif c.landing_bad=='pending'then set('SourceGravityAir4086_LandingNeeded',0)
 elseif c.landing_bad=='slot'then set('SourceLandingVelocity4086_Slot',128)
 elseif c.landing_bad=='plan'then set('SourceLandingPlan4086_Ready',0)
 elseif c.landing_bad=='toss'then set('SourceEntityToss4086_Ready',0)
 elseif c.landing_bad=='sticky'then set('SourceEntityToss4086_Status',3)end
end,emu.callbackType.exec,LANDING,LANDING,emu.cpuType.snes,mt)
'''

ASM='''LandingVelocityFixture_Run:
.a16
.i16
 jsl AIR
 bcs LandingVelocityFixture_Bad
LandingVelocityFixture_Landing:
.a16
.i16
 nop
 jsl LAND
 rtl
LandingVelocityFixture_Bad:
.a16
.i16
 sec
 rtl
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True)
    p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    authority=json.loads(a.authority.read_text());assert authority['status']=='PASS'
    combinations=[(factor,modelbounce,fb,fy)for factor in (0.,4.,-2.,1.5)for modelbounce in (0,1)for fb,fy in ((0,0),(40,0),(0,1))]
    plans=pack_plans(dict(plans=[dict(handle=i+1,model_index=0,animation_bounce=factor,model_bounce=mb,noquake=0)
                                 for i,(factor,mb,fb,fy)in enumerate(combinations)]))
    physics=pack_physics(dict(animations=[dict(handle=i+1,antigrav=0,dropframe=-1,landframe=-1,land_entity_index=-1,
                                             frames=[dict(movement=dict(base=fb,y=fy))])for i,(factor,mb,fb,fy)in enumerate(combinations)]))
    rows=[];peak_error=0
    def make(c,index):
        combo=(c['factor'],c['modelbounce'],c['frame_base'],c['frame_y']);handle=combinations.index(combo)+1
        # Two noquake table identities per handle are exercised in separate copies.
        # Input chooses ROM base; row flags remain immutable during native execution.
        row=dict(slot=(0,63,127)[index%3],handle=handle,a=0,base=0,altbase=0,vy=round(c['velocity']*65536),noadjust=1,
                 hole=1,wall=1,platform=1,freeze=0,mark=0,time=48,toss=0,falling=1,hithead=1,gravity=0,minfall=-6*65536,
                 maxtoss=100*65536,subject=0,damage=c['damage'],autoland=c['autoland'],noquake=c['noquake'],fault=0)
        predicate=bounce_predicate(dict(animation_bounce=c['factor'],velocity_y=c['velocity'],damage_on_landing=c['damage']),c['autoland']) and c['modelbounce']
        row['bounced']=int(bool(predicate));row['fault']=int(bool(predicate and c['factor']!=4))
        if row['fault']:row['expected']=[row['vy']>>1,row['vy'],98304,-49152,1,0,0,11]
        elif predicate:row['expected']=[32768,-(row['vy']>>2),98304>>2,-49152>>2,0,49,0,11 if c['noquake']else 4]
        else:row['expected']=[0,0,98304 if c['frame_base']>0 or c['frame_y']>0 else 0,-49152 if c['frame_base']>0 or c['frame_y']>0 else 0,0,0,0,11]
        return row
    for i,c in enumerate(authority['inputs']):
        row=make(c,i);rows.append(row)
        if not row['fault']:
            for native,source in zip(row['expected'][:4],authority['actual'][i][:4]):
                value=struct.unpack('<f',struct.pack('<I',source))[0]*65536;peak_error=max(peak_error,abs(native-value))
    seed=next(r for r in rows if r['bounced']and not r['fault'])
    for bad in ('ready','air','pending','slot','plan','toss','sticky'):
        rows.append(dict(seed,landing_bad=bad,fault=1,expected=[seed['vy']>>1,seed['vy'],98304,-49152,1,0,0,11]))
    # Distinct immutable table copy for source NOQUAKE bit1.
    quiet=bytearray(plans)
    for i in range(len(combinations)):struct.pack_into('<I',quiet,16+i*16+12,1)
    lua=LUA.replace('TABLEBYTES',str(len(physics))).replace('PLANBYTES',str(len(plans))).replace('PLANCOUNT',str(len(combinations)))
    lua=lua.replace("set('SourceAnimationPhysics4086_Animations',6)","set('SourceAnimationPhysics4086_Animations',"+str(len(combinations))+')')
    lua=lua.replace("set('SourceLandingPlan4086_Base',0x8000)","set('SourceLandingPlan4086_Base',c.noquake==1 and 0x9000 or 0x8000)")
    reporter=Reporter('M4-LANDING-VELOCITY',kind='GATE')
    raw,log=run_fixture(a.rom,a.output,rows,'LandingVelocityFixture_Run','SourceLandingVelocity4086_Ready',0xb626,
                        [(58,0,physics),(59,0,plans),(59,0x1000,quiet)],lua,reporter,append=ASM,
                        bindings=dict(AIR='SourceGravityAir4086_Execute',LAND='SourceLandingVelocity4086_Execute'),
                        probes=dict(LANDING='LandingVelocityFixture_Landing'),batch_size=8,frame_limit=4000)
    actual=[list(map(int,l.split('LANDVELOCITY|',1)[1].split('|')))for l in log.splitlines()if 'LANDVELOCITY|'in l]
    costs=[list(map(int,l.split('LANDCOST|',1)[1].split('|')))for l in log.splitlines()if 'LANDCOST|'in l]
    wanted=[[i,0,0,3 if r['fault']else 1 if r['bounced']else 2,2 if r.get('landing_bad')=='air'else 1]for i,r in enumerate(rows)]
    reporter.check('actual native air -> source landing snap/velocity/falling/toss/quake; unsupported necessary divisors and stale owners reject; no early gravity Ack',actual==wanted)
    report=dict(schema='BYOR_4086_LANDING_VELOCITY_NATIVE_V1',status='PASS'if actual==wanted else'FAIL',cases=len(rows),inputs=rows,
                actual=actual,expected=wanted,native_costs_master_cycles=costs,source_authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),
                rom_sha256=hashlib.sha256(raw).hexdigest(),peak_numeric_error_q16_units=peak_error,
                numerical_policy='ACCEPTED_COMPAT_Q16_16; arithmetic floor division; measured binary32 velocity difference',
                source_air_and_entity_toss_and_quake_native=True,source_zero_and_four_bounce_capability=True,
                bounce_sound_and_rumble_pending=True,landframe_and_damage_and_full_gravity_commit_pending=True,
                camera_quake_presentation_bound=False,gameplay_service_rate_proven=False,
                foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
