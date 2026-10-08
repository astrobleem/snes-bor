"""Verbatim pinned gravity/adjust_base/inair landing branch against services."""
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
from source_check_gravity_landing_4086 import land
from source_model_core_4086 import binary32 as f32


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
 raw=subprocess.check_output(['git','-C',str(a.engine),'show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1');bodies={n:extract(raw,n)for n in ('check_gravity','adjust_base','inair','diff')}
 pre=PREAMBLE.replace('int inair(entity *e){unexpected();return 0;}','').replace('float diff(float a,float b){return a>b?a-b:b-a;}','')
 pre=pre.replace('void update_frame(entity *e,int frame){unexpected();}','int frame_calls;void update_frame(entity *e,int frame){frame_calls++;e->animpos=frame;}')
 pre=pre.replace('void execute_onmovea_script(entity *e){unexpected();}','int movea_calls;void execute_onmovea_script(entity *e){movea_calls++;}')
 pre=pre.replace('int tobounce(entity *e){unexpected();return 0;}','int bounce_calls,bounce_result;int tobounce(entity *e){bounce_calls++;return bounce_result;}')
 pre=pre.replace('void kill(entity *e){unexpected();}','int kill_calls;void kill(entity *e){kill_calls++;}')
 pre+='int damage_calls;void damage(entity *e,s_attack *a){damage_calls++;}\n'
 code=pre+bodies['diff']+bodies['inair']+bodies['adjust_base']+'\nvoid observe_adjust_base(entity *e,entity **p){adjust_calls++;adjust_base(e,p);}\n#define adjust_base observe_adjust_base\n'+bodies['check_gravity']+'\n#undef adjust_base\n'
 code+='unsigned bits(float f){unsigned v;memcpy(&v,&f,4);return v;}float frombits(unsigned v){float f;memcpy(&f,&v,4);return f;}\nstruct Case{unsigned mark,toss,time,a,v;int frozen,framebase,framey,landframe,pos,numframes,force,dead,callback,bounce;unsigned defense;}cases[]={\n'
 bits=lambda v:struct.unpack('<I',struct.pack('<f',v))[0];inputs=[];expected=[]
 shapes=((0,0),(0.05,0),(0.1,0),(1,-2),(2,-6))
 frames=((-1,0,5),(1,0,5),(3,0,5),(5,0,5),(6,0,5),(3,3,5))
 damages=((0,0,0,1),(7,0,0,1.5),(150,0,0,1),(7,0,1,1),(7,1,0,1))
 for mark,freeze,(alt,vel),(lf,pos,nf),(force,dead,cb,defense),(fb,fy),bounce in itertools.product((0,8),(0,1),shapes,frames,damages,((0,0),(40,0),(0,1)),(0,1)):
  e=dict(update_mark=mark,toss_time=0,falling=1,velocity_y=f32(vel),a=f32(alt),base=0.,height=0,subject_to_platform=1,animation_antigrav=0,antigravity=0.,subject_to_gravity=1,dropframe=-1,animpos=pos,idling=0,walkoff_valid=False,hithead=1,velocity_x=1.5,velocity_z=-0.75,fall_land_dust=-1,drop=0,model_bounce=0,frame_base=fb,frame_move_y=fy,landed_on_platform=None,platform_below=None,landframe=lf,numframes=nf,landframe_entity=-1,damage_on_landing=force,dead=dead,health=100,land_defense=f32(defense))
  calls=[]
  def landing(e):
   land(e,lambda e:(calls.append('bounce')or bounce),lambda e,f:(calls.append('frame'),e.update(animpos=f)),take_damage=(lambda e,f:calls.append('damage'))if cb else None,kill=lambda e:calls.append('kill'))
  check_gravity_air(e,48,dict(gravity=f32(-.1),maxfallspeed=-6.,maxtossspeed=100.),lambda e:calls.append('adjust'),lambda e:(calls.append('freeze')or freeze),lambda e:calls.append('movea'),landing=landing)
  inputs.append(dict(mark=mark,freeze=freeze,a=alt,velocity_y=vel,landframe=lf,animpos=pos,numframes=nf,damage_on_landing=force,dead=dead,damage_callback=cb,defense=defense,frame_base=fb,frame_move_y=fy,bounce_predicate=bounce))
  expected.append([bits(e['a']),bits(e['velocity_y']),bits(e['velocity_x']),bits(e['velocity_z']),e['falling'],e['animpos'],e['health'],e['damage_on_landing'],int(e['hithead']is not None),e['update_mark'],e['toss_time'],*[calls.count(n)for n in ('adjust','freeze','movea','bounce','frame','damage','kill')],1])
  code+='{%du,0u,48u,%du,%du,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%du},\n'%(mark,bits(alt),bits(vel),freeze,fb,fy,lf,pos,nf,force,dead,cb,bounce,bits(defense))
 code+=r'''};int main(void){Animation anim;Level lev;Move move,*moves[8];unsigned i,j;struct Case *c;
for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){c=cases+i;memset(&ent,0,sizeof(ent));memset(&anim,0,sizeof(anim));memset(&lev,0,sizeof(lev));self=&previous;adjust_calls=freeze_calls=platform_calls=movea_calls=bounce_calls=frame_calls=damage_calls=kill_calls=0;
ent.animation=&anim;anim.dropframe.frame=-1;anim.landframe.frame=c->landframe;anim.landframe.ent=-1;anim.numframes=c->numframes;move.base=c->framebase;move.y=c->framey;for(j=0;j<8;j++)moves[j]=&move;anim.move=moves;
ent.modeldata.no_adjust_base=1;ent.modeldata.subject_to_platform=1;ent.modeldata.subject_to_gravity=1;ent.modeldata.dust.fall_land=-1;ent.position.y=frombits(c->a);ent.velocity.y=frombits(c->v);ent.velocity.x=1.5;ent.velocity.z=-.75;ent.falling=1;ent.animpos=c->pos;ent.hithead=&previous;ent.health=100;ent.damage_on_landing=c->force;ent.dead=c->dead;ent.defense[0].factor=frombits(c->defense);ent.takedamage=c->callback?damage:NULL;ent.update_mark=c->mark;ent.toss_time=c->toss;time=c->time;frozen=c->frozen;bounce_result=c->bounce;
level=&lev;lev.gravity=-.1f;lev.maxfallspeed=-6;lev.maxtossspeed=100;check_gravity(&ent);
printf("%u,%u,%u,%u,%d,%d,%d,%d,%d,%u,%u,%d,%d,%d,%d,%d,%d,%d,%d\n",bits(ent.position.y),bits(ent.velocity.y),bits(ent.velocity.x),bits(ent.velocity.z),ent.falling,ent.animpos,ent.health,ent.damage_on_landing,ent.hithead!=NULL,ent.update_mark,ent.toss_time,adjust_calls,freeze_calls,movea_calls,bounce_calls,frame_calls,damage_calls,kill_calls,self==&previous);
}return 0;}'''
 (folder/'landing.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-bt=nt','landing.c','-fe=landing.exe'],cwd=folder,env=env,capture_output=True,text=True);(folder/'build.log').write_text(build.stdout+build.stderr)
 if build.returncode:raise ValueError('LANDING_AUTHORITY_BUILD:'+build.stdout+build.stderr)
 log=subprocess.check_output([str(folder/'landing.exe')],cwd=folder,text=True);(folder/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()];mismatches=[i for i,(v,w)in enumerate(zip(actual,expected))if v!=w]
 r=dict(schema='BYOR_4086_NONBOUNCING_LANDING_AUTHORITY_V1',status='PASS'if actual==expected else'FAIL',engine_commit=ENGINE_COMMIT,source_function_hashes={n:hashlib.sha256(b.encode('latin1')).hexdigest()for n,b in bodies.items()},source_functions_unmodified=True,cases=len(inputs),inputs=inputs,actual=actual,expected=expected,mismatch_cases=mismatches,empty_platform_and_sticky_base=True,frame_and_damage_and_bounce_predicate_and_kill_services_instrumented=True,dust_or_bounce_or_platform_branches_proven=False,native_gravity_or_landing_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
 (folder/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],len(inputs),'non-bouncing landing cases',mismatches[:3]);assert actual==expected


if __name__=='__main__':main()
