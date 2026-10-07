"""Literal normal-attack timer expressions; measure integer-delay lowering."""
import argparse,hashlib,json,os,re,subprocess
from pathlib import Path
from compiler import Source
from source_attack_timing_4086 import derive,bits
from script_nested_authority import extract
from dialect_4086 import ENGINE_COMMIT

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd='E:/gh/openbor-bcec').decode('latin1');randf=extract(raw,'randf');normal=extract(raw,'common_try_normalattack');profile=derive(Source(a.source))
 expressions=[re.search(r'self->'+name+r' = time \+ [^;]*randf[^;]+;',normal)[0]for name in ('nextattack','stalltime')]
 inputs=[]
 for m in profile['models']:inputs.append(dict(identity=m['identity'],maximum=m['fields']['attackthrottletime'],aggression=m['fields']['aggression']))
 for maximum,aggression in ((0,149),(.5,149),(100,0),(150,0),(255,-105)):inputs.append(dict(identity='synthetic',maximum=maximum,aggression=aggression))
 times=[0,1,50,1000,32767,32768,65535,65536,1000000,0xffffff,0x1000000,0x1000001,0xfffffe00]
 code='''#include <stdio.h>
#include <string.h>
#define MAX(a,b) ((a)>(b)?(a):(b))
#define GAME_SPEED 200
typedef struct {struct {float attackthrottletime;int aggression;}modeldata;unsigned nextattack,stalltime;} entity;
entity ent,*self=&ent;unsigned time,draw,calls;
unsigned int rand32(void){calls++;return draw;}
'''+randf+'''
float frombits(unsigned n){float f;memcpy(&f,&n,4);return f;}
unsigned fbits(float f){unsigned n;memcpy(&n,&f,4);return n;}
typedef struct {unsigned maximum;int aggression;} input;
input cases[]={
'''+','.join('{'+str(bits(r['maximum']))+'u,'+str(r['aggression'])+'}'for r in inputs)+'''};
unsigned times[]={'''+','.join(str(t)+'u'for t in times)+'''};
int main(void){unsigned i,j,n,delta,integer_next,integer_stall,mismatches_next,mismatches_stall,wrong_calls;float stored;
for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){self->modeldata.attackthrottletime=frombits(cases[i].maximum);self->modeldata.aggression=cases[i].aggression;
 for(j=0;j<sizeof(times)/sizeof(times[0]);j++){time=times[j];mismatches_next=mismatches_stall=wrong_calls=0;
  for(n=0;n<10000;n++){draw=n;calls=0;
'''+expressions[0]+'''
   if(calls!=(self->modeldata.attackthrottletime==0?0:1))wrong_calls++;
   calls=0;stored=randf(self->modeldata.attackthrottletime);integer_next=time+(unsigned)stored;
   if(integer_next!=self->nextattack)mismatches_next++;
   calls=0;
'''+expressions[1]+'''
   if(calls!=1)wrong_calls++;
   calls=0;stored=randf((float)MAX(1,GAME_SPEED*3/4-self->modeldata.aggression));integer_stall=time+(unsigned)stored;
   if(integer_stall!=self->stalltime)mismatches_stall++;
  }
  printf("%u,%u,%u,%u,%u\\n",i,time,mismatches_next,mismatches_stall,wrong_calls);
 }
}return 0;}
''';(a.output/'timer.c').write_text(code)
 env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-ei','-bt=nt','timer.c','-fe=timer.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 log=subprocess.check_output([str(a.output/'timer.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()];ok=len(actual)==len(inputs)*len(times)and all(v[4]==0 for v in actual)
 report=dict(schema='BYOR_4086_ATTACK_TIMER_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,profiles=inputs,times=times,residues_per_case=10000,cases=len(actual),decisions=len(actual)*10000,actual=actual,nextattack_integer_delay_mismatches=sum(v[2]for v in actual),stalltime_integer_delay_mismatches=sum(v[3]for v in actual),literal_expressions=expressions,literal_randf_sha256=hashlib.sha256(randf.encode()).hexdigest(),literal_expressions_and_randf_unmodified=True,rand32_draw_controlled=True,integer_delay_lowering_proven=all(v[2]==0 and v[3]==0 for v in actual),original_2014_binary_fpu_configuration_proven=False,runtime_bound=False,motu_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],report['decisions'],'timer decisions;',report['nextattack_integer_delay_mismatches'],'nextattack and',report['stalltime_integer_delay_mismatches'],'stall integer-delay differences');assert ok

if __name__=='__main__':main()
