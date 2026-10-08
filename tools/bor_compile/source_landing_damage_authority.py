"""Verbatim pinned gravity landing damage, binary32 arithmetic and service choice."""
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


def f32(v):return struct.unpack('<f',struct.pack('<f',v))[0]


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'))
 p.add_argument('--output',type=Path,required=True);a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
 raw=subprocess.check_output(['git','-C',str(a.engine),'show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
 bodies={n:extract(raw,n)for n in ('check_gravity','adjust_base','inair','diff')}
 pre=PREAMBLE.replace('int inair(entity *e){unexpected();return 0;}','').replace('float diff(float a,float b){return a>b?a-b:b-a;}','')
 pre=pre.replace('int tobounce(entity *e){unexpected();return 0;}','int tobounce(entity *e){return 0;}')
 pre=pre.replace('void execute_onmovea_script(entity *e){unexpected();}','void execute_onmovea_script(entity *e){}')
 pre=pre.replace('void kill(entity *e){unexpected();}','int kill_calls;void kill(entity *e){kill_calls++;}')
 pre+='int damage_calls,damage_force,damage_type;void damage(entity *e,s_attack *a){damage_calls++;damage_force=a->attack_force;damage_type=a->attack_type;}\n'
 code=pre+'\n'.join(bodies[n]for n in ('diff','inair','adjust_base','check_gravity'))
 rows=[];expected=[]
 for health,force,factor,dead,callback in itertools.product((0,1,7,100,300,32767,8388607,16777216,-1),(0,1,7,150,32767,8388607,16777216),(1.,2.,1.5),(0,1),(0,1)):
  row=dict(health=health,force=force,factor=factor,dead=dead,callback=callback);rows.append(row)
  after=health;clear=force;kc=dc=df=dt=0
  if force>0 and not dead:
   if callback:dc=1;df=force
   else:after=int(f32(f32(health)-f32(f32(force)*f32(factor))));kc=int(after<=0);clear=0
  expected.append([after,clear,kc,dc,df,dt,0,8,49,1])
 code+='\nstruct Case{int health,force,dead,callback;float factor;}cases[]={\n'
 code+=',\n'.join('{%d,%d,%d,%d,%sf}'%(r['health'],r['force'],r['dead'],r['callback'],str(r['factor']))for r in rows)
 code+=r'''};
int main(void){unsigned i;Animation anim;Level lev;Move move,*moves[1];struct Case *c;
for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
c=cases+i;memset(&ent,0,sizeof(ent));memset(&anim,0,sizeof(anim));memset(&lev,0,sizeof(lev));memset(&move,0,sizeof(move));
kill_calls=damage_calls=damage_force=damage_type=0;self=&previous;time=48;frozen=0;
anim.numframes=1;anim.dropframe.frame=-1;anim.landframe.frame=-1;anim.landframe.ent=-1;move.base=-1;moves[0]=&move;anim.move=moves;
ent.animation=&anim;ent.modeldata.no_adjust_base=1;ent.modeldata.subject_to_platform=1;ent.modeldata.dust.fall_land=-1;
ent.falling=1;ent.velocity.y=-1;ent.health=c->health;ent.damage_on_landing=c->force;ent.dead=c->dead;
ent.defense[ATK_LAND].factor=c->factor;ent.takedamage=c->callback?damage:NULL;ent.hithead=&previous;
level=&lev;lev.maxfallspeed=-6;lev.maxtossspeed=100;check_gravity(&ent);
printf("%d,%d,%d,%d,%d,%d,%d,%u,%u,%d\n",ent.health,ent.damage_on_landing,kill_calls,damage_calls,damage_force,damage_type,ent.hithead!=NULL,ent.update_mark,ent.toss_time,self==&previous);
}return 0;}'''
 (folder/'landing_damage.c').write_text(code)
 env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
 build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-bt=nt','-op','-fpc','landing_damage.c','-fe=landing_damage.exe'],cwd=folder,env=env,capture_output=True,text=True)
 (folder/'build.log').write_text(build.stdout+build.stderr)
 if build.returncode:raise ValueError('LANDING_DAMAGE_C_BUILD:'+build.stdout+build.stderr)
 log=subprocess.check_output([str(folder/'landing_damage.exe')],cwd=folder,text=True);(folder/'authority.log').write_text(log)
 actual=[list(map(int,l.split(',')))for l in log.splitlines()]
 mismatches=[dict(index=i,input=rows[i],actual=v,expected=w)for i,(v,w)in enumerate(zip(actual,expected))if v!=w]
 report=dict(schema='BYOR_4086_LANDING_DAMAGE_AUTHORITY_V1',status='PASS'if actual==expected else'FAIL',engine_commit=ENGINE_COMMIT,
  source_function_hashes={n:hashlib.sha256(b.encode('latin1')).hexdigest()for n,b in bodies.items()},source_functions_unmodified=True,
  cases=len(rows),inputs=rows,actual=actual,expected=expected,mismatches=mismatches,
  damage_and_kill_services_instrumented=True,positive_health_force_below_2_to_23_unit_defense_exact_integer_domain=True,
  native_damage_or_kill_backend_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
 (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'actual source landing damage cases',mismatches[:2]);assert actual==expected


if __name__=='__main__':main()
