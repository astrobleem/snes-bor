"""Pinned common_pain/common_fall/common_grabbed scalar and child ordering."""
import argparse,hashlib,itertools,json,os,struct,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_animation_ids import configure
from source_common_damage_actions_4086 import run
FLOATS=('vy','rise','riseattack','model_rise','model_riseattack')
STATE=('action','inpain','falling','stall','rise_stall','rise','riseattack','speedup')
def bits(v):return struct.unpack('<I',struct.pack('<f',v))[0]
def cases():
 b=dict(callback=0,action=1,animating=0,air=0,inpain=1,link=0,blocking=0,falling=0,vy=0.,projectile=0,autoland=0,landing=0,boss=0,completed=0,speedup=0,stall=17,rise_stall=19,time=48,rise=0.,riseattack=0.,model_rise=0.,model_riseattack=0.)
 rows=[dict(b,**dict(zip(('callback','animating','air','link','blocking','falling'),v)))for v in itertools.product(range(3),(-1,0,1),range(2),range(2),range(2),range(2))]
 for vs in itertools.product((-1,0,1,2,3),(-2,-1,0,1),(0,1,2),range(2),range(2),(0,48,4294967295),(-250.,0.,0.25,300.),(-1.5,0.,220.5)):
  rows.append(dict(b,callback=1,**dict(zip(('projectile','landing','autoland','boss','completed','time','rise','model_rise'),vs))))
 for n,vs in dict(vy=(-1.,0.25),riseattack=(-2.5,0.25,220.5),model_riseattack=(-1.5,0.25,300.),inpain=(-3,),stall=(0,4294967295)).items():
  for v,cb,link in itertools.product(vs,range(3),range(2)):rows.append(dict(b,**{n:v,'callback':cb,'link':link}))
 for r in rows:r["action"]=r["callback"]+1
 return rows

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);raw=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1');names=('common_pain','common_fall','common_grabbed');bodies={n:extract(raw,n)for n in names};block=configure([])['authority']['enum']['ANI_BLOCK']
 code='''#include <stdio.h>
#include <string.h>
#define GAME_SPEED 200
#define MAX(a,b) ((a)>(b)?(a):(b))
#define ANI_BLOCK '''+str(block)+'''
typedef struct entity{int animating,inpain,blocking,falling,projectile,damage_on_landing,boss;struct{float y;}velocity;struct{float rise,riseattack;unsigned riseattack_stall;}staydown;struct{struct{float rise,riseattack;}risetime;}modeldata;struct entity*link;void(*takeaction)(void);unsigned stalltime;}entity;
entity e,linked,*self=&e;unsigned time;int autoland,level_completed,tospeedup,air,ne,events[16];
void event(int n){events[ne++]=n;}
int inair(entity*e){event(10);return air;}
void common_block(void){}void common_lie(void){}
void ent_set_anim(entity*e,int n,int reset){if(n!=ANI_BLOCK)_exit(9);event(1);event(reset);}
void set_idle(entity*e){event(2);}void doland(void){event(3);}
unsigned fbits(float f){unsigned v;memcpy(&v,&f,4);return v;}
float fvalue(unsigned v){float f;memcpy(&f,&v,4);return f;}
void common_grabbed(void);
'''+ '\n'.join(bodies.values())
 rows=cases();fields=list(rows[0]);mapping=dict(animating='e.animating',air='air',inpain='e.inpain',blocking='e.blocking',falling='e.falling',vy='e.velocity.y',projectile='e.projectile',autoland='autoland',landing='e.damage_on_landing',boss='e.boss',completed='level_completed',speedup='tospeedup',stall='e.stalltime',rise_stall='e.staydown.riseattack_stall',time='time',rise='e.staydown.rise',riseattack='e.staydown.riseattack',model_rise='e.modeldata.risetime.rise',model_riseattack='e.modeldata.risetime.riseattack')
 code+='\nint main(void){unsigned v['+str(len(fields))+'];int j;while(scanf("'+' '.join('%u'for n in fields)+'",'+','.join('&v['+str(i)+']'for i in range(len(fields)))+')=='+str(len(fields))+'){memset(&e,0,sizeof(e));ne=0;e.takeaction=common_pain;'
 for i,n in enumerate(fields):
  if n in ('callback','action'):continue
  val=f'v[{i}]'
  if n in FLOATS:val=f'fvalue({val})'
  elif n=='link':code+=f'e.link={val}?&linked:NULL;';continue
  code+=mapping[n]+'='+val+';'
 code+=f'e.takeaction=v[{fields.index("callback")}] ==0?common_pain:v[{fields.index("callback")}] ==1?common_fall:common_grabbed;if(v[{fields.index("callback")}] ==0)common_pain();else if(v[{fields.index("callback")}] ==1)common_fall();else common_grabbed();'
 expr=['e.takeaction==NULL?0:e.takeaction==common_pain?1:e.takeaction==common_fall?2:e.takeaction==common_grabbed?3:e.takeaction==common_block?4:5','e.inpain','e.falling','e.stalltime','e.staydown.riseattack_stall','fbits(e.staydown.rise)','fbits(e.staydown.riseattack)','tospeedup'];code+='printf("'+' '.join('%u'for x in expr)+'|",'+','.join(expr)+');for(j=0;j<ne;j++)printf("%s%u",j?" ":"",(unsigned)events[j]);puts("");}return 0;}'
 (a.output/'authority.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');q=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-bt=nt','-op','-fpc','authority.c','-fe=authority.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(q.stdout+q.stderr)
 if q.returncode:raise ValueError('COMMON_DAMAGE_ACTIONS_C_BUILD:'+q.stdout+q.stderr)
 q=subprocess.run([str(a.output/'authority.exe')],input=''.join(' '.join(str(bits(r[n])if n in FLOATS else r[n]&0xffffffff)for n in fields)+'\n'for r in rows),capture_output=True,text=True);(a.output/'authority.log').write_text(q.stdout);actual=[[list(map(int,v.split()))for v in line.split('|')]for line in q.stdout.splitlines()];expected=[]
 for r in rows:
  e,ev=run(r);expected.append([[bits(e[n])if n in FLOATS else e[n]&0xffffffff for n in STATE],ev])
 failures=[dict(index=i,input=rows[i],actual=x,expected=y)for i,(x,y)in enumerate(zip(actual,expected))if x!=y];report=dict(schema='BYOR_COMMON_DAMAGE_ACTIONS_AUTHORITY_V1',status='PASS'if q.returncode==0 and actual==expected else'FAIL',engine_commit=ENGINE_COMMIT,cases=len(rows),observed_cases=len(actual),source_functions_unmodified=True,function_sha256={n:hashlib.sha256(b.encode('latin1')).hexdigest()for n,b in bodies.items()},failures=failures[:20],proof_domain='exact binary32 quarter/half rise arithmetic within signed range; injected inair predicate and instrumented animation/idle/land services',native_action_handlers_bound=False,motu_gameplay_proven=False,no_color_reduction=True);(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'action cases',len(failures),'mismatches')
 if report['status']!='PASS':raise SystemExit(1)
if __name__=='__main__':main()
