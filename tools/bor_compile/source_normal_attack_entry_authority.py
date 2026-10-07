"""Literal common_try_normalattack NULL-target return before body services."""
import argparse,hashlib,itertools,json,os,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--wide',action='store_true');a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 s=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd='E:/gh/openbor-bcec').decode('latin1');f=extract(s,'common_try_normalattack')
 truth=(0,1,65536,-1)if a.wide else(0,1)
 rows=[dict(found=t,passed=p,vulnerable=v,drop=d,attacking=k,rise=r)for t,p,v,d,k,r in itertools.product((0,1),(0,1),(0,1),truth,truth,(0,1))]
 code='''#include <stdio.h>
#include <stddef.h>
#define MAX(a,b) ((a)>(b)?(a):(b))
#define GAME_SPEED 200
typedef struct animation {int vulnerable[1];} animation;
typedef struct entity {int combostep[1],idling,attacking,drop,animpos;unsigned combotime,stalltime,nextattack;void(*takeaction)(void);struct {float x,z;}velocity;struct {float attackthrottletime;int aggression;}modeldata;animation*animation;} entity;
entity ent,victim,*self=&ent;animation anim;unsigned time=48;float min_noatk_chance=.05f;int found,findcalls,rechecks,picks,mutations,randomcalls;
entity*normal_find_target(int a,int b){findcalls++;return found?&victim:NULL;}
unsigned recheck_nextattack(entity*e){rechecks++;return 0;}
int pick_random_attack(entity*e,int n){picks++;return -1;}
int check_attack_chance(entity*e,float a,float b){mutations++;return 0;}
float randf(float f){randomcalls++;return 0;}
void common_rise(void){}
void normal_prepare(void){}
void set_idle(entity*e){mutations++;}
'''+f+'\nint cases[][6]={'+','.join('{'+','.join(str(c[k])for k in ('found','passed','vulnerable','drop','attacking','rise'))+'}'for c in rows)+'''};
int main(void){unsigned i;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){int r;found=cases[i][0];anim.vulnerable[0]=cases[i][2];victim.animation=&anim;victim.animpos=0;victim.drop=cases[i][3];victim.attacking=cases[i][4];victim.takeaction=cases[i][5]?common_rise:NULL;findcalls=rechecks=picks=mutations=randomcalls=0;r=common_try_normalattack(cases[i][1]?&victim:NULL);printf("%d,%d,%d,%d,%d,%d\\n",r,findcalls,rechecks,picks,mutations,randomcalls);}return 0;}
'''
 (a.output/'normal_entry.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','normal_entry.c','-fe=normal_entry.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 log=subprocess.check_output([str(a.output/'normal_entry.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()]
 expected=[[0,1,2*c['found'],int(bool(c['found']and(c['vulnerable']or not(c['drop']or c['attacking']or c['rise'])))),0,0]for c in rows];ok=actual==expected
 (a.output/'report.json').write_text(json.dumps(dict(schema='BYOR_4086_NORMAL_ATTACK_ENTRY_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,function_sha256=hashlib.sha256(f.encode()).hexdigest(),cases=len(rows),inputs=rows,actual=actual,expected=expected,target_and_body_services_instrumented=True,motu_gameplay_proven=False),indent=2)+'\n');print('PASS'if ok else'FAIL',len(rows),'literal normal attack entry cases');assert ok
if __name__=='__main__':main()
