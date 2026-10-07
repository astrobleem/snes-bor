"""Literal common_attack_finish player/NULL-opponent order and stall timer."""
import argparse,hashlib,itertools,json,os,re,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 def authority(path):return subprocess.check_output(['git','show',ENGINE_COMMIT+':'+path],cwd='E:/gh/openbor-bcec').decode('latin1')
 f=extract(authority('engine/openbor.c'),'common_attack_finish');h=authority('engine/openbor.h');speed=re.search(r'^#define\s+GAME_SPEED\s+(\d+)',h,re.M);assert speed and int(speed[1])==200
 rows=[dict(type=t,aggression=g,time=now)for t,g,now in itertools.product((0,1,2,3,32,512,0x10001),(0,-1,99,100,101,200,65536,-65385),(0,50,0x7fffffff,0xffffffff))]
 code=r'''#include <stdio.h>
#include <stddef.h>
#define TYPE_PLAYER 1
#define GAME_SPEED 200
#define MIN(a,b) ((a)<(b)?(a):(b))
#define MAX(a,b) ((a)>(b)?(a):(b))
typedef struct entity {int idling;void(*takeaction)(void);struct {float x,z;}velocity,position;struct {int type,nomove,aggression;float speed;}modeldata;unsigned stalltime;struct entity*opponent;float destx,destz;}entity;
entity ent,*self=&ent;unsigned time;int idle_calls,idle_observation,other_calls;
float diff(float a,float b){other_calls++;return a>b?a-b:b-a;}
unsigned rand32(void){other_calls++;return 0;}
void adjust_walk_animation(entity*e){other_calls++;}
void action(void){}
void set_idle(entity*e){idle_calls++;idle_observation=e->takeaction==NULL&&e->velocity.x==0&&e->velocity.z==0&&e->stalltime==111;e->idling=3;}
'''+f+'\nunsigned cases[][3]={'+','.join('{'+','.join(str(c[k])+'u'for k in ('type','aggression','time'))+'}'for c in rows)+r'''};
int main(void){unsigned i;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){self->modeldata.type=cases[i][0];self->modeldata.aggression=cases[i][1];time=cases[i][2];self->velocity.x=3;self->velocity.z=4;self->opponent=NULL;self->stalltime=111;self->takeaction=action;self->idling=55;idle_calls=idle_observation=other_calls=0;common_attack_finish();printf("%u,%d,%d,%d,%d,%d,%d\n",self->stalltime,self->takeaction==NULL,self->idling,self->velocity.x==0&&self->velocity.z==0,idle_calls,idle_observation,other_calls);}return 0;}
'''
 (a.output/'finish.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-ei','-bt=nt','finish.c','-fe=finish.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 log=subprocess.check_output([str(a.output/'finish.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()];expected=[[111 if c['type']&1 else(c['time']+max(100,200-c['aggression']))&0xffffffff,1,3,1,1,1,0]for c in rows];ok=actual==expected;r=dict(schema='BYOR_4086_ATTACK_FINISH_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,function_sha256=hashlib.sha256(f.encode()).hexdigest(),game_speed=200,source_function_unmodified=True,callees_instrumented=True,cases=len(rows),inputs=rows,actual=actual,expected=expected,domain='Player cached model bit or NULL opponent; actual source idle service observed before NPC aggression read/stall write',native_bound=False,motu_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],len(rows),'literal common_attack_finish cases');assert ok

if __name__=='__main__':main()
