"""Compile exact normal-attack chance cutoffs with literal source randf/chance.

Finite source inputs and equal min/max arguments admit an offline cutoff.
The RNG draw is controlled here; the production engine stream is proven apart.
"""
import argparse,hashlib,itertools,json,os,re,subprocess
from pathlib import Path
from compiler import Source
from source_attack_timing_4086 import derive,bits
from script_nested_authority import extract
from dialect_4086 import ENGINE_COMMIT

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd='E:/gh/openbor-bcec').decode('latin1');chance=extract(raw,'check_attack_chance');randf=extract(raw,'randf');diff=extract(raw,'diff');normal=extract(raw,'common_try_normalattack');assert 'check_attack_chance(target, 1.0f - min_noatk_chance, 1.0f - min_noatk_chance)'in normal
 profile=derive(Source(a.source));rows=[]
 for m in profile['models']:
  for x in (-11,-10,0,330,331):rows.append(dict(model=m['index'],minimum=profile['globals']['min_noatk_chance'],throttle=m['fields']['attackthrottle'],offscreen_factor=profile['globals']['offscreen_noatk_factor'],x=x,count=1,dest=0,aiattack=0))
 for minimum,throttle,factor,x,count,dest,flag in itertools.product((0,.05,.5,1),(-1,0,.05,.5,.95,1,2),(.5,1.5),(-11,-10,0,330,331),(0,1,128),(0,640),(0,8)):
  rows.append(dict(model=None,minimum=minimum,throttle=throttle,offscreen_factor=factor,x=x,count=count,dest=dest,aiattack=flag))
 code='''#include <stdio.h>
#include <string.h>
#define AIATTACK1_ALWAYS 8
#define MIN(a,b) ((a)<(b)?(a):(b))
typedef struct entity {struct {float x,z;}position;float destx,destz;struct {int aiattack,type;float attackthrottle;}modeldata;} entity;
entity ent,victim,*self=&ent;struct {int hRes,vRes;}videomodes={320,240};
float screenx=0,move_noatk_factor=3.0f,group_noatk_factor=.01f,offscreen_noatk_factor;
int population;unsigned draw,drawcalls;
unsigned int rand32(void){drawcalls++;return draw;}
int count_ents(int type){return population;}
'''+diff+'\n'+randf+'\n'+chance+'''
float frombits(unsigned n){float f;memcpy(&f,&n,4);return f;}
typedef struct {unsigned minimum,throttle,factor;int x,count,dest,flags;} input;
input cases[]={
'''
 for r in rows:code+='{'+','.join(str(bits(r[k]))+'u'for k in ('minimum','throttle','offscreen_factor'))+','+','.join(str(r[k])for k in ('x','count','dest','aiattack'))+'},\n'
 code+='''};int main(void){unsigned i,n,calls;int last,monotonic,afterfalse,allowed;input*c;
for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){c=&cases[i];ent.modeldata.aiattack=c->flags;ent.modeldata.type=2;ent.modeldata.attackthrottle=frombits(c->throttle);offscreen_noatk_factor=frombits(c->factor);ent.position.x=c->x;ent.position.z=220;ent.destx=c->dest;ent.destz=220;population=c->count;calls=0;last=-1;monotonic=1;afterfalse=0;
for(n=0;n<10000;n++){draw=n;drawcalls=0;allowed=check_attack_chance(&victim,1.0f-frombits(c->minimum),1.0f-frombits(c->minimum));calls+=drawcalls;
 if(drawcalls!=((c->flags&8)?0:1))return 3;
 if(allowed){last=n;if(afterfalse)monotonic=0;}else afterfalse=1;}
printf("%d,%u,%d\\n",last,calls,monotonic);}return 0;}
''';(a.output/'chance.c').write_text(code)
 env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-ei','-bt=nt','chance.c','-fe=chance.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 log=subprocess.check_output([str(a.output/'chance.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()];ok=len(actual)==len(rows)and all(v[2]==1 and v[1]==(0 if r['aiattack']&8 else 10000)for r,v in zip(rows,actual))
 # Verify the equal-bound invariant across real finite distance/population
 # inputs. The retained C cutoff, rather than a Python float, is authority.
 cutoffs={}
 for r,v in zip(rows,actual):
  off=r['x']<-10 or r['x']>330;k=(bits(r['minimum']),bits(r['throttle']),bits(r['offscreen_factor']),off,r['aiattack'])
  if k in cutoffs and cutoffs[k]!=v[0]:ok=False
  cutoffs[k]=v[0]
 models=[]
 for i,m in enumerate(profile['models']):
  result=actual[i*5:(i+1)*5];models.append(dict(index=i,identity=m['identity'],onscreen_last_allowed=result[2][0],offscreen_last_allowed=result[0][0]))
 report=dict(schema='BYOR_4086_NORMAL_CHANCE_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,cases=len(rows),residues_per_case=10000,decisions=len(rows)*10000,inputs=rows,actual=actual,source_models=models,globals=profile['globals'],source_sha256={k:hashlib.sha256(v.encode()).hexdigest()for k,v in dict(chance=chance,randf=randf,diff=diff).items()},normal_equal_bound_call_verified=True,literal_functions_unmodified=True,rand32_draw_controlled=True,actual_world_population_instrumented=True,source_coordinates_finite=True,source_viewport=[320,240],runtime_bound=False,motu_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],report['decisions'],'literal chance decisions');assert ok

if __name__=='__main__':main()
