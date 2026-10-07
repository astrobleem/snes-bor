"""Literal NPC common_attack_finish plus actual default walk selection."""
import argparse,hashlib,itertools,json,os,re,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--running',action='store_true');a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd='E:/gh/openbor-bcec').decode('latin1')
 functions={n:extract(raw.replace('static int common_anim_series(','int common_anim_series('),n)for n in ['common_attack_finish','adjust_walk_animation','common_anim_series','diff']}
 macro=re.search(r'^#define common_walk_anim\(ent\) \\\r?\n\s*common_anim_series\([^\n]+',raw,re.M)[0]
 rows=[]
 for x,dx,direction,rand,nomove,present in itertools.product((0,100,100.25),(-80,-79.75,-40,0,40,79.75,80),(0,1),(0,1,2,3),(0,1,-1),(0,1)):
  rows.append(dict(x=x,target_x=x+dx,z=220.25,target_z=222,direction=direction,rand=rand,nomove=nomove,present=present,speed=0.75,aggression=0,time=50,type=2))
 if a.running:
  rows=[dict(c,running=running,run_present=present)for c in rows if c['x']==100 and c['target_x']in(60,140)and c['nomove']==0 and c['present']==1 for running,present in itertools.product((1,65536,-1),(0,1))]
 code=r"""#include <stdio.h>
#include <stddef.h>
#define TYPE_PLAYER 1
#define GAME_SPEED 200
#define ANI_IDLE 0
#define ANI_WALK 1
#define ANI_UP 29
#define ANI_DOWN 30
#define ANI_BACKWALK 79
#define ANI_RUN 37
#define DIRECTION_RIGHT 1
#define MIN(a,b) ((a)<(b)?(a):(b))
#define MAX(a,b) ((a)>(b)?(a):(b))
typedef struct {int numframes;}animation;
typedef struct entity {int running,walkmode,direction,animating,animnum,idling;void(*takeaction)(void);struct {float x,z;}position,velocity;struct {int type,nomove,aggression;float speed;animation*animation[168];}modeldata;struct entity*opponent;float destx,destz;unsigned stalltime;}entity;
entity ent,target,*self=&ent;animation walk;int animwalks[]={1},max_walks=1;unsigned time,rngvalue;int rngcalls,walkcalls,idlecalls,findcalls,chosen;
#define validanim(e,a) ((e)->modeldata.animation[a]&&(e)->modeldata.animation[a]->numframes)
unsigned rand32(void){rngcalls++;return rngvalue;}
int normal_find_target(int a,int b){findcalls++;return 0;}
int testup(float x,float z){return z<0;}int testdown(float x,float z){return z>0;}
void common_up_anim(entity*e){}void common_down_anim(entity*e){}void common_backwalk_anim(entity*e){}
void ent_set_anim(entity*e,int a,int reset){walkcalls++;chosen=a;e->animnum=a;}
void set_idle(entity*e){idlecalls++;e->idling=3;}
void action(void){}
"""+functions['diff']+'\n'+functions['common_anim_series']+'\n'+macro+'\n'+functions['adjust_walk_animation']+'\n'+functions['common_attack_finish']+'\nint main(void){walk.numframes=1;self->modeldata.animation[1]=&walk;\n'
 for c in rows:
  code+='self->running='+str(c.get('running',0))+';self->modeldata.animation[37]='+('&walk'if c.get('run_present',0)else'NULL')+';self->modeldata.type=2;self->modeldata.nomove='+str(c['nomove'])+';self->modeldata.aggression=0;self->modeldata.speed=.75f;self->position.x='+str(c['x'])+'f;self->position.z=220.25f;target.position.x='+str(c['target_x'])+'f;target.position.z=222;self->opponent='+('&target'if c['present']else'NULL')+';self->direction='+str(c['direction'])+';self->animating=0;self->velocity.x=3;self->velocity.z=4;self->destx=111;self->destz=222;self->idling=55;self->takeaction=action;self->stalltime=111;time=50;rngvalue='+str(c['rand'])+';rngcalls=walkcalls=idlecalls=findcalls=0;chosen=-1;common_attack_finish();printf("%d,%d,%d,%d,%d,%d,%d,%u,%d,%d,%d,%d\\n",(int)(self->destx*65536),(int)(self->destz*65536),(int)(self->velocity.x*65536),(int)(self->velocity.z*65536),self->idling,self->animating,self->takeaction==NULL,self->stalltime,rngcalls,walkcalls,idlecalls,findcalls);\n'
 code+='return 0;}\n';code=code.replace('=0f','=0.0f').replace('=100f','=100.0f');code=re.sub(r'(?<==)(-?\d+)f;',r'\1.0f;',code)
 (a.output/'runoff.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-ei','-bt=nt','runoff.c','-fe=runoff.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 log=subprocess.check_output([str(a.output/'runoff.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()];expected=[]
 for c in rows:
  gate=c['present']and not c['nomove']and abs(c['x']-c['target_x'])<80;run=gate and c['rand']&3
  if run:
   right=c['x']>c['target_x'];dest=min(c['x']+40,c['target_x']+80)if right else max(c['x']-40,c['target_x']-80);vel=c['speed']if right else -c['speed'];reverse=vel<0 if c['direction']==1 else vel>0
   expected.append([int(dest*65536),int(c['z']*65536),int(vel*65536),0,1,0 if c.get('running',0)else(-1 if reverse else 1),1,250,1,1,0,0])
  else:expected.append([111*65536,222*65536,0,0,3,0,1,250,int(bool(gate)),0,1,0])
 ok=actual==expected;r=dict(schema='BYOR_4086_ATTACK_RUNOFF_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,cases=len(rows),inputs=rows,actual=actual,expected=expected,source_functions_unmodified=list(functions),function_sha256={n:hashlib.sha256(f.encode()).hexdigest()for n,f in functions.items()},walk_macro_sha256=hashlib.sha256(macro.encode()).hexdigest(),instrumented_services=['set_idle','ent_set_anim','rand32','normal_find_target'],ent_set_anim_instrumentation_scope='Records invocation only; absence and pointer-equality effects are proved separately by native initializer fixtures',domain='NPC, literal float integral/quarter positions, default walk only, running captured in inputs, UP/DOWN/BACKWALK absent, world time50/aggression0',native_bound=False,motu_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],len(rows),'literal runoff/walk cases');assert ok
if __name__=='__main__':main()
