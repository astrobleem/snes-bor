"""Verbatim pinned check_gravity/toss and actual tobounce macro, no bounce mock."""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import struct
import subprocess
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_check_gravity_idle_authority import PREAMBLE
from source_landing_bounce_4086 import landing_velocity


def bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--engine', type=Path, default=Path('E:/gh/openbor-bcec'))
    a = p.parse_args(); folder = a.output.resolve(); folder.mkdir(parents=True, exist_ok=True)
    def git(path):
        return subprocess.check_output(['git','-C',str(a.engine),'show',ENGINE_COMMIT+':'+path]).decode('latin1')
    raw = git('engine/openbor.c'); header = git('engine/openbor.h')
    macro = re.search(r'^#define tobounce\(e\).*\\\n[^\n]+', header, re.M).group()
    bodies = {n: extract(raw,n) for n in ('check_gravity','adjust_base','inair','diff','toss')}
    pre = PREAMBLE
    for declaration in ('int inair(entity *e){unexpected();return 0;}',
                        'float diff(float a,float b){return a>b?a-b:b-a;}',
                        'int tobounce(entity *e){unexpected();return 0;}',
                        'void toss(entity *e,float v){unexpected();}'):
        pre = pre.replace(declaration, '')
    pre = pre.replace('void execute_onmovea_script(entity *e){unexpected();}', 'void execute_onmovea_script(entity *e){}')
    pre = pre.replace('#define SAMPLE_FALL -1', '#define SAMPLE_FALL 3')
    pre = pre.replace('void sound_play_sample(int n,int p,int l,int r,int rate){unexpected();}',
                      'int sound_calls;void sound_play_sample(int n,int p,int l,int r,int rate){sound_calls++;}')
    pre = pre.replace('void control_rumble(int p,int n){unexpected();}',
                      'int rumble_calls,rumble_player[5],rumble_value[5];void control_rumble(int p,int n){rumble_player[rumble_calls]=p;rumble_value[rumble_calls++]=n;}')
    code = pre + '\nint autoland;\nfloat diff(float,float);int inair(entity*);void toss(entity*,float);void adjust_base(entity*,entity**);\n' + macro + '\n' + '\n'.join(bodies.values())
    inputs=[]; expected=[]
    for factor, velocity, modelbounce, damage, auto, typ, noquake, frame in itertools.product(
            (0.,4.,-2.,1.5), (-1.,-1.5,-1.5000152587890625,-6.), (0,1),
            (0,-1,-2), (0,1), (1,2), (0,1), ((0,0),(40,0),(0,1))):
        c=dict(factor=factor,velocity=velocity,modelbounce=modelbounce,damage=damage,
               autoland=auto,type=typ,noquake=noquake,frame_base=frame[0],frame_y=frame[1])
        e=dict(a=0.,velocity_y=velocity,velocity_x=1.5,velocity_z=-.75,toss_time=0,
               animation_bounce=factor,model_bounce=modelbounce,damage_on_landing=damage,
               noquake=noquake,type=typ,playerindex=2,frame_base=frame[0],frame_move_y=frame[1])
        effects=[]
        landing_velocity(e,48,auto,quake=lambda v:effects.append(('quake',v)),
                         sound=lambda v:effects.append(('sound',v)),
                         rumble=lambda p,v:effects.append(('rumble',p,v)),sample_fall=3)
        e['toss_time']=49  # final check_gravity due timer; toss itself also writes49
        rumble=[x for x in effects if x[0]=='rumble']
        expected.append([bits(e['a']),bits(e['velocity_y']),bits(e['velocity_x']),bits(e['velocity_z']),
                         0,e['toss_time'],8,0,4 if any(x[0]=='quake'for x in effects)else 0,
                         sum(x[0]=='sound'for x in effects),len(rumble),
                         *[value for pair in [(x[1],x[2])for x in rumble]+[(0,0)]*(5-len(rumble))for value in pair],1])
        inputs.append(c)
    code += '\nstruct Case{float factor,v;int bounce,damage,auto_land,type,noquake,fb,fy;}cases[]={\n'
    for c in inputs:
        code += '{%sf,%sf,%d,%d,%d,%d,%d,%d,%d},\n' % (c['factor'],c['velocity'],c['modelbounce'],c['damage'],c['autoland'],c['type'],c['noquake'],c['frame_base'],c['frame_y'])
    code += r'''};
unsigned bits(float f){unsigned v;memcpy(&v,&f,4);return v;}
int main(void){Animation anim;Move move,*moves[1];Level lev;unsigned i,j;struct Case *c;
for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){c=cases+i;
memset(&ent,0,sizeof(ent));memset(&anim,0,sizeof(anim));memset(&lev,0,sizeof(lev));
memset(rumble_player,0,sizeof(rumble_player));memset(rumble_value,0,sizeof(rumble_value));sound_calls=rumble_calls=0;
self=&previous;level=&lev;lev.maxfallspeed=-6;lev.maxtossspeed=100;time=48;autoland=c->auto_land;frozen=0;
anim.dropframe.frame=anim.landframe.frame=-1;anim.bounce=c->factor;move.base=c->fb;move.y=c->fy;moves[0]=&move;anim.move=moves;
ent.animation=&anim;ent.modeldata.no_adjust_base=1;ent.modeldata.subject_to_platform=1;ent.modeldata.dust.fall_land=-1;
ent.modeldata.bounce=c->bounce;ent.modeldata.noquake=c->noquake;ent.modeldata.type=c->type;
ent.position.y=ent.base=0;ent.velocity.y=c->v;ent.velocity.x=1.5;ent.velocity.z=-.75;ent.falling=1;
ent.damage_on_landing=c->damage;ent.playerindex=2;ent.hithead=&previous;check_gravity(&ent);
printf("%u,%u,%u,%u,%d,%u,%u,%d,%d,%d,%d",bits(ent.position.y),bits(ent.velocity.y),bits(ent.velocity.x),bits(ent.velocity.z),ent.falling,ent.toss_time,ent.update_mark,ent.hithead!=NULL,lev.quake,sound_calls,rumble_calls);
for(j=0;j<5;j++)printf(",%d,%d",rumble_player[j],rumble_value[j]);printf(",%d\n",self==&previous);
}return 0;}'''
    (folder/'landing_bounce.c').write_text(code)
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-op','-fpc','-bt=nt','landing_bounce.c','-fe=landing_bounce.exe'],cwd=folder,env=env,capture_output=True,text=True)
    (folder/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode: raise ValueError('LANDING_BOUNCE_AUTHORITY_BUILD:'+build.stdout+build.stderr)
    log=subprocess.check_output([str(folder/'landing_bounce.exe')],cwd=folder,text=True,timeout=30)
    (folder/'authority.log').write_text(log)
    actual=[list(map(int,l.split(',')))for l in log.splitlines()]
    failures=[i for i,(x,y)in enumerate(zip(actual,expected))if x!=y]
    report=dict(schema='BYOR_4086_LANDING_BOUNCE_AUTHORITY_V1',status='PASS'if actual==expected else'FAIL',
        engine_commit=ENGINE_COMMIT,cases=len(inputs),inputs=inputs,actual=actual,expected=expected,
        failures=failures,source_function_hashes={n:hashlib.sha256(v.encode('latin1')).hexdigest()for n,v in bodies.items()},
        tobounce_macro_sha256=hashlib.sha256(macro.encode('latin1')).hexdigest(),source_bodies_unmodified=True,
        compiler_float_modes=['-op','-fpc'],quake_native_source_branch=True,sound_and_rumble_services_instrumented=True,
        landframe_dust_damage_branches_proven=False,native_landing_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'],len(inputs),'actual bounce macro/toss landing cases',failures[:5]);assert actual==expected


if __name__=='__main__':main()
