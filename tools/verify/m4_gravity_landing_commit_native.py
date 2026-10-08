"""Actual air/landing/controller commit; unresolved source services retain owner."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from source_animation_physics_4086 import pack as pack_physics
from source_landing_plan_4086 import pack as pack_plans
from m4_landing_velocity_native import LUA as VELOCITY_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=VELOCITY_LUA.replace(' before={};for',r'''
 set('SourceGravityLanding4086_Ready',0xb627);set('SourceGravityLanding4086_State',0);set('SourceGravityLanding4086_Service',0);set('SourceGravityLanding4086_Slot',s)
 put(life+20,c.dead or 0,4)
 before={};for''')
LUA=LUA.replace("emu.log('LANDVELOCITY|'", "emu.log('GRAVITYCOMMIT|'")
LUA=LUA.replace("word(sy.SourceLandingVelocity4086_Status)..'|'..word(sy.SourceGravityAir4086_Status)",
                "word(sy.SourceGravityLanding4086_State)..'|'..word(sy.SourceGravityAir4086_Status)..'|'..word(sy.SourceGravityLanding4086_Service)")

ASM='''GravityCommitFixture_Run:
.a16
.i16
 jsl AIR
 bcs GravityCommitFixture_Bad
 jsl VELOCITY
 bcs GravityCommitFixture_Bad
GravityCommitFixture_BeforeLanding:
.a16
.i16
 nop
 jsl LANDINGBEGIN
 rtl
GravityCommitFixture_Bad:
.a16
.i16
 sec
 rtl
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True)
    p.add_argument('--velocity-proof',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    reference=json.loads(a.velocity_proof.read_text());assert reference['status']=='PASS'
    combinations=[(f,m,b,y)for f in (0.,4.,-2.,1.5)for m in (0,1)for b,y in ((0,0),(40,0),(0,1))]
    plans=pack_plans(dict(plans=[dict(handle=i+1,model_index=0,animation_bounce=f,model_bounce=m,noquake=0)
                                 for i,(f,m,b,y)in enumerate(combinations)]))
    physics=pack_physics(dict(animations=[dict(handle=i+1,antigrav=0,dropframe=-1,landframe=-1,land_entity_index=-1,
                                             frames=[dict(movement=dict(base=b,y=y))])for i,(f,m,b,y)in enumerate(combinations)]))
    rows=[]
    # Keep one source type (numeric branch is type-independent before rumble),
    # retaining all factors, threshold boundaries, autoland, noquake and geometry.
    for i,source in enumerate(reference['inputs'][:2880]):
        if (i//6)%2:continue
        r=dict(source);r['expected']=list(source['expected'])
        if not r['fault'] and not r['bounced']:r['expected'][5:7]=[49,8]
        rows.append(r)
    seed=next(r for r in rows if not r['fault'] and not r['bounced'])
    # Actual physics force drives a required damage service, not a fabricated Ack.
    for force in (1,7,150,0x7fffffff):
        expected=list(seed['expected']);expected[5:7]=[0,0]
        rows.append(dict(seed,damage=force,damage_pending=True,expected=expected))
        for dead in (1,-1,-0x80000000):
            rows.append(dict(seed,damage=force,dead=dead,expected=list(seed['expected'])))
    for bad in ('pool','side','air','pending','time','phase','tick','slot','physics','ready','state'):
        expected=list(seed['expected']);expected[5:7]=[0,0]
        rows.append(dict(seed,controller_bad=bad,fault=1,expected=expected))
    quiet=bytearray(plans)
    for i in range(len(combinations)):struct.pack_into('<I',quiet,16+i*16+12,1)
    lua=LUA.replace('TABLEBYTES',str(len(physics))).replace('PLANBYTES',str(len(plans))).replace('PLANCOUNT',str(len(combinations)))
    lua=lua.replace("set('SourceAnimationPhysics4086_Animations',6)","set('SourceAnimationPhysics4086_Animations',"+str(len(combinations))+')')
    lua=lua.replace("set('SourceLandingPlan4086_Base',0x8000)","set('SourceLandingPlan4086_Base',c.noquake==1 and 0x9000 or 0x8000)")
    # These rows reject the controller after AIR and velocity ran successfully.
    lua=lua[:lua.index("emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1]\n if c.landing_bad")]
    lua+=r'''
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 local faults={pool={'VmSourceWorld_PoolBase',0x4002},side={'VmSourceWorld_SideBase',0x6802},
 air={'SourceGravityAir4086_Status',2},pending={'SourceGravityAir4086_LandingNeeded',0},
 time={'SourceWorldTick4086_TimeLo',47},phase={'SourceWorldTick4086_Phase',10},
 tick={'SourceWorldTick4086_Ready',0},slot={'SourceGravityLanding4086_Slot',128},
 physics={'SourcePhysicsState4086_Ready',0},ready={'SourceGravityLanding4086_Ready',0},state={'SourceGravityLanding4086_State',2}}
 if faults[c.controller_bad]then local f=faults[c.controller_bad];set(f[1],f[2]);for i=0,1 do if before[sy[f[1]]+i]~=nil then before[sy[f[1]]+i]=(f[2]>>(8*i))&255 end end end
end,emu.callbackType.exec,CONTROLLER,CONTROLLER,emu.cpuType.snes,mt)
'''
    reporter=Reporter('M4-GRAVITY-LANDING-COMMIT',kind='GATE')
    raw,log=run_fixture(a.rom,a.output,rows,'GravityCommitFixture_Run','SourceGravityLanding4086_Ready',0xb627,
                        [(58,0,physics),(59,0,plans),(59,0x1000,quiet)],lua,reporter,append=ASM,
                        bindings=dict(AIR='SourceGravityAir4086_Execute',VELOCITY='SourceLandingVelocity4086_Execute',
                                      LANDINGBEGIN='SourceGravityLanding4086_Begin'),
                        probes=dict(CONTROLLER='GravityCommitFixture_BeforeLanding'),frame_limit=4000)
    actual=[list(map(int,l.split('GRAVITYCOMMIT|',1)[1].split('|')))for l in log.splitlines()if 'GRAVITYCOMMIT|'in l]
    wanted=[]
    for i,r in enumerate(rows):
        pending=r['bounced'] or r.get('damage_pending')
        wanted.append([i,0,0,0 if r['fault']else 1 if pending else 2,1 if r['fault'] or pending else 2,
                       0 if r['fault']else 3 if r['bounced']else 2 if r.get('damage_pending')else 0])
        if r.get('controller_bad'):
            wanted[-1][3]=3;wanted[-1][4]=2 if r['controller_bad']=='air'else 1
    reporter.check('no-service source landing completes toss/mark/hithead only after actual numeric phases; bounce and positive damage remain pending',actual==wanted)
    report=dict(schema='BYOR_4086_GRAVITY_LANDING_COMMIT_NATIVE_V1',status='PASS'if actual==wanted else'FAIL',cases=len(rows),inputs=rows,
                actual=actual,expected=wanted,velocity_proof_sha256=hashlib.sha256(a.velocity_proof.read_bytes()).hexdigest(),
                rom_sha256=hashlib.sha256(raw).hexdigest(),no_callback_no_dust_nonbouncing_nonpositive_damage_gravity_complete=True,
                native_landframe_execution_proven=False,bounce_effects_and_damage_backend_pending=True,
                native_world_post_integration_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
