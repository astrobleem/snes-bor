"""Native Q16 air fields and explicit pending landing; no full gravity Ack."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from source_animation_physics_4086 import pack
from source_check_gravity_air_q16 import check_gravity_air_q16
from m4_adjust_base_empty_native import LUA as BASE_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=BASE_LUA.replace("put(phy,1,4);put(phy+4,123,4)","put(phy,c.falling,4);put(phy+4,c.hithead,4)")
LUA=LUA.replace("set('VmSourceWorld_Time',48,4)","set('VmSourceWorld_Time',c.time,4)")
LUA=LUA.replace("set('SourceWorldTick4086_TimeLo',48,4)","set('SourceWorldTick4086_TimeLo',c.time,4)")
LUA=LUA.replace(" before={};for",r'''
 set('SourceGravityAir4086_Ready',c.air_ready or 0xb621);set('SourceGravityAir4086_Status',0)
 set('SourceGravityAir4086_LandingNeeded',0);put(0x43fd94,0,4);put(0x43fd98,c.freeze==1 and c.time==0xffffffff and 1 or 0,4)
 set('SourceGravityAir4086_ZeroProfileReady',c.zero_ready or 0xb622);set('SourceGravityAir4086_ZeroModels',1)
 set('SourceGravityAir4086_StageReady',c.stage_ready or 0xb623);set('SourceGravityAir4086_StageId',1)
 set('SourceGravityAir4086_Gravity',c.gravity,4);set('SourceGravityAir4086_MinFall',c.minfall,4);set('SourceGravityAir4086_MaxToss',c.maxtoss,4)
 set('SourceToss4086_Ready',0xb4e2);put(0x41f300+s*4,c.toss,4);put(core+20,c.subject,4)
 put(freeze+4,c.freeze==1 and(c.time+1)&0xffffffff or 0,4)
 if c.bad=='bounds'then set('SourceGravityAir4086_MinFall',100*65536,4);set('SourceGravityAir4086_MaxToss',-6*65536,4)end
 before={};for''')
LUA=LUA.replace("{life-8,96}","{life-8,96},{0x41f300+s*4-8,20}")
start=LUA.index(" local c=rows[word(INDEX)+1];local side=0x416800+c.slot*64",LUA.index('AFTER,AFTER'))
end=LUA.index('end,emu.callbackType.exec,RESULT',start)
LUA=LUA[:start]+r'''
 local c=rows[word(INDEX)+1];local side=0x416800+c.slot*64;local view=0x414000+c.slot*80;local phy=0x42d800+c.slot*16;local freeze=0x42e000+c.slot*40
 if c.fault==0 then for _,r in ipairs({{view+12,c.expected[1]},{side+44,c.expected[2]},{phy+4,c.expected[3]},{0x41f300+c.slot*4,c.expected[4]},{freeze+36,c.expected[5]}})do for i=0,3 do before[r[1]+i]=(r[2]>>(8*i))&255 end end end
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('GRAVITYAIR|'..word(INDEX)..'|'..ctx..'|'..n..'|'..word(sy.SourceGravityAir4086_Status)..'|'..word(sy.SourceGravityAir4086_LandingNeeded))
'''+LUA[end:]


def q(value):return round(struct.unpack('<f',struct.pack('<f',value))[0]*65536)


def expected(c):
    entity=dict(update_mark=c['mark'],toss_time=c['toss'],falling=c['falling'],velocity_y=c['vy'],a=c['a'],base=c['base'],
        height=0,subject_to_platform=1,animation_antigrav=c['handle']-1,antigravity=0,subject_to_gravity=c['subject'],
        dropframe=-1,animpos=0,idling=0,walkoff_valid=False,hithead=c['hithead'])
    pending=[]
    check_gravity_air_q16(entity,c['time'],dict(gravity=c['gravity'],maxfallspeed=c['minfall'],maxtossspeed=c['maxtoss']),
        lambda e:None,lambda e:bool(c['freeze']),lambda e:None,lambda e:pending.append(True))
    if pending:
        entity['toss_time']=c['toss'];entity['update_mark']=c['mark']
    return [entity['a'],entity['velocity_y'],entity['hithead'] or 0,entity['toss_time'],entity['update_mark']],int(bool(pending))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True)
    p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    source=json.loads(a.authority.read_text());assert source['status']=='PASS'
    table=pack(dict(animations=[dict(handle=i+1,antigrav=i,dropframe=-1,landframe=-1,land_entity_index=-1,
        frames=[dict(movement=dict(base=-1,y=0))])for i in range(2)]))
    rows=[]
    for i,c in enumerate(source['inputs']):
        if c['antigravity']!=0:continue
        r=dict(slot=(0,63,127)[len(rows)%3],handle=c['animation_antigrav']+1,a=q(100),base=q(34),altbase=0,
            vy=q(c['velocity']),noadjust=1,hole=1,wall=1,platform=1,fault=0,freeze=c['freeze'],mark=c['mark'],
            time=c['time'],toss=c['toss'],falling=0,hithead=1,gravity=q(c['gravity']),minfall=q(-6),maxtoss=q(100),subject=c['subject'],
            source_authority_index=i)
        r['expected'],r['landing']=expected(r);rows.append(r)
    seed=dict(rows[0],mark=0,freeze=0,toss=0,time=48,vy=q(-1),subject=1,gravity=q(-.1),handle=1)
    for altitude,falling in ((0,1),(0,0),(q(.1),1),(q(.5),1)):
        r=dict(seed,a=altitude,base=0,falling=falling);r['expected'],r['landing']=expected(r);rows.append(r)
    for change in (dict(air_ready=0xb624),dict(zero_ready=0xb624),dict(stage_ready=0xb624),dict(bad='bounds'),
        dict(a=0x7fffffff,vy=2*65536,noadjust=0),dict(a=-0x80000000,vy=-2*65536,noadjust=0),
        dict(vy=-0x80000000,gravity=q(-.1)),dict(a=0x7fffffff,base=-0x80000000,vy=0,subject=0)):
        r=dict(seed,expected=[0]*5,landing=0,fault=1);r.update(change);rows.append(r)
    reporter=Reporter('M4-GRAVITY-AIR',kind='GATE')
    raw,log=run_fixture(a.rom,a.output,rows,'SourceGravityAir4086_Execute','SourceGravityAir4086_Ready',0xb621,
        [(58,0,table)],LUA.replace('TABLEBYTES',str(len(table))).replace("set('SourceAnimationPhysics4086_Animations',6)","set('SourceAnimationPhysics4086_Animations',2)"),reporter,batch_size=8)
    results=[list(map(int,line.split('GRAVITYAIR|',1)[1].split('|')))for line in log.splitlines()if 'GRAVITYAIR|'in line]
    wanted=[[i,0,0,3 if c['fault']else 1 if c['landing']else 2,c['landing']]for i,c in enumerate(rows)]
    failures=[dict(index=i,input=rows[i],actual=x,expected=y)for i,(x,y)in enumerate(zip(results,wanted))if x!=y]
    reporter.check('native active air fields agree with measured Q16 policy; pending landing never commits toss/mark; rejection rolls back base and retains actor state',results==wanted)
    report=dict(schema='BYOR_4086_GRAVITY_AIR_NATIVE_V1',status='PASS'if results==wanted else'FAIL',cases=len(rows),inputs=rows,results=results,expected=wanted,failures=failures,
        authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),
        zero_height_zero_model_antigravity_no_drop_walkoff_onmovea_compiler_contract=True,
        base_adjustment_native=True,landing_action_is_pending_service=True,native_landing_completion_bound=False,
        native_world_post_integration_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
