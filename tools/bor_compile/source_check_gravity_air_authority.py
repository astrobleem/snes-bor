"""Verbatim pinned airborne check_gravity/adjust_base/inair, before landing."""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import struct
import subprocess
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_check_gravity_idle_authority import PREAMBLE
from source_check_gravity_air_4086 import check_gravity_air
from source_model_core_4086 import binary32 as f32


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','-C',str(a.engine),'show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
    bodies={name:extract(raw,name)for name in ('check_gravity','adjust_base','inair','diff')}
    preamble=PREAMBLE.replace('void execute_onmovea_script(entity *e){unexpected();}','int movea_calls;void execute_onmovea_script(entity *e){movea_calls++;}')
    preamble=preamble.replace('int inair(entity *e){unexpected();return 0;}','')
    preamble=preamble.replace('float diff(float a,float b){return a>b?a-b:b-a;}','')
    code=preamble+bodies['diff']+bodies['inair']+bodies['adjust_base']+'\nvoid observe_adjust_base(entity *e,entity **p){adjust_calls++;adjust_base(e,p);}\n#define adjust_base observe_adjust_base\n'+bodies['check_gravity']+'\n#undef adjust_base\n'
    code+='unsigned bits(float f){unsigned v;memcpy(&v,&f,4);return v;}float frombits(unsigned v){float f;memcpy(&f,&v,4);return f;}\nstruct Case {unsigned mark,toss,time;int frozen;unsigned velocity,antigravity,gravity;int subject,antigrav;}cases[]={\n'
    bits=lambda f:struct.unpack('<I',struct.pack('<f',f))[0]
    inputs=[];expected=[]
    for mark,freeze,toss,time,velocity,gravity,antigravity,subject,antigrav in itertools.product((0,4,8),(0,1),(0,49),(48,0xffffffff),(-20,-6,0,1.5,100,200),(-.1,0,-.2),(0,.5,1,1.5),(0,1),(0,1)):
        physics=dict(gravity=f32(gravity),maxfallspeed=f32(-6),maxtossspeed=f32(100))
        e=dict(update_mark=mark,toss_time=toss,falling=0,velocity_y=f32(velocity),a=f32(100),base=f32(34),height=0,subject_to_platform=1,animation_antigrav=antigrav,antigravity=f32(antigravity),subject_to_gravity=subject,dropframe=-1,animpos=0,idling=0,walkoff_valid=False,hithead=1)
        calls=[];check_gravity_air(e,time,physics,lambda e:calls.append('adjust'),lambda e:(calls.append('freeze')or bool(freeze)),lambda e:calls.append('movea'))
        inputs.append(dict(mark=mark,freeze=freeze,toss=toss,time=time,velocity=velocity,gravity=gravity,antigravity=antigravity,subject=subject,animation_antigrav=antigrav))
        expected.append([bits(e['a']),bits(e['velocity_y']),e['update_mark'],e['toss_time'],int(e['hithead']is not None),calls.count('adjust'),calls.count('freeze'),calls.count('movea'),1])
        code+='{%du,%du,%du,%d,%du,%du,%du,%d,%d},\n'%(mark,toss,time,freeze,bits(velocity),bits(antigravity),bits(gravity),subject,antigrav)
    code+=r'''};
int main(void){Animation anim;Level lev;unsigned i;struct Case *c;
for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
c=cases+i;memset(&ent,0,sizeof(ent));memset(&anim,0,sizeof(anim));memset(&lev,0,sizeof(lev));self=&previous;adjust_calls=freeze_calls=platform_calls=movea_calls=0;
ent.animation=&anim;anim.dropframe.frame=anim.landframe.frame=-1;ent.modeldata.no_adjust_base=1;ent.modeldata.subject_to_platform=1;ent.hithead=&previous;ent.position.y=100;ent.base=34;
ent.update_mark=c->mark;ent.toss_time=c->toss;time=c->time;frozen=c->frozen;ent.velocity.y=frombits(c->velocity);ent.modeldata.subject_to_gravity=c->subject;ent.modeldata.antigravity=frombits(c->antigravity);anim.antigrav=c->antigrav;
level=&lev;lev.gravity=frombits(c->gravity);lev.maxfallspeed=-6;lev.maxtossspeed=100;
check_gravity(&ent);printf("%u,%u,%u,%u,%d,%d,%d,%d,%d\n",bits(ent.position.y),bits(ent.velocity.y),ent.update_mark,ent.toss_time,ent.hithead!=NULL,adjust_calls,freeze_calls,movea_calls,self==&previous);
}return 0;}
''';(folder/'air.c').write_text(code)
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-bt=nt','air.c','-fe=air.exe'],cwd=folder,env=env,capture_output=True,text=True);(folder/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise ValueError('CHECK_GRAVITY_AIR_AUTHORITY_BUILD:'+build.stdout+build.stderr)
    log=subprocess.check_output([str(folder/'air.exe')],cwd=folder,text=True);(folder/'authority.log').write_text(log)
    actual=[list(map(int,s.split(',')))for s in log.splitlines()];mismatch=[i for i,(v,w)in enumerate(zip(actual,expected))if v!=w]
    r=dict(schema='BYOR_4086_AIRBORNE_GRAVITY_AUTHORITY_V1',status='PASS'if actual==expected else'FAIL',engine_commit=ENGINE_COMMIT,source_function_hashes={k:hashlib.sha256(v.encode('latin1')).hexdigest()for k,v in bodies.items()},source_functions_unmodified=True,cases=len(inputs),inputs=inputs,actual=actual,expected=expected,mismatch_cases=mismatch,empty_platform_service_instrumented=True,onmovea_event_instrumented=True,sticky_base_policy=True,ceiling_or_dropframe_or_walkoff_or_landing_proven=False,native_numeric_policy_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
    (folder/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],len(inputs),'airborne integration cases',mismatch[:3]);assert actual==expected


if __name__=='__main__':main()
