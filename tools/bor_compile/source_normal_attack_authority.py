"""Literal pinned normal_attack selector order, full32 running and side effects."""
import argparse,hashlib,itertools,json,os,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

def reference(c):
 running=c['running'];exists=1;trace=[];result=0
 for step in range(1,7):
  trace.append(step)
  if c['mutation']==1:exists=0
  if c['mutation']==2:running=-1
  if c['mask']&(1<<(step-1)):running=0;result=1;break
 return [len(trace),*trace,*([0]*(6-len(trace))),running&0xffffffff,exists,result]

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 text=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd='E:/gh/openbor-bcec').decode('latin1');function=extract(text,'normal_attack')
 rows=[dict(running=r,mask=m,value=v,mutation=mutation)for r,m,v,mutation in itertools.product((0,1,-1,65536),(0,1,2,4,8,16,32,63),(-1,1,65536),(0,1,2))]
 names=('common_try_grab','common_try_upper','common_try_block','common_try_runattack','common_try_normalattack','common_try_jumpattack')
 code='''#include <stdio.h>
#include <stddef.h>
typedef struct entity {int running,exists;} entity;
entity ent,*self=&ent;int trace[6],count,value,mutation;unsigned mask;
int handler(int step){trace[count++]=step;if(mutation==1)self->exists=0;if(mutation==2)self->running=-1;return(mask&(1u<<(step-1)))?value:0;}
'''+''.join('int '+n+'(entity *target){return handler('+str(i+1)+');}\n'for i,n in enumerate(names))+function+'\nint cases[][4]={'+','.join('{'+','.join(str(c[k])for k in ('running','mask','value','mutation'))+'}'for c in rows)+'''};
int main(void){unsigned i;int j,result;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){ent.running=cases[i][0];mask=cases[i][1];value=cases[i][2];mutation=cases[i][3];ent.exists=1;count=0;for(j=0;j<6;j++)trace[j]=0;result=normal_attack();printf("%d",count);for(j=0;j<6;j++)printf(",%d",trace[j]);printf(",%u,%d,%d\\n",(unsigned)ent.running,ent.exists,result);}return 0;}
'''
 (a.output/'normal_attack.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','normal_attack.c','-fe=normal_attack.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 log=subprocess.check_output([str(a.output/'normal_attack.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()];expected=[reference(c)for c in rows];ok=actual==expected
 report=dict(schema='BYOR_4086_NORMAL_ATTACK_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,function_sha256=hashlib.sha256(function.encode()).hexdigest(),cases=len(rows),inputs=rows,actual=actual,expected=expected,selector_bodies_instrumented=True,motu_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'normal attack selector cases');assert ok
if __name__=='__main__':main()
