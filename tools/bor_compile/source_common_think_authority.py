"""Literal pinned common_think complete ordering, controlled handler returns."""
import argparse,hashlib,itertools,json,os,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_common_think_4086 import common_think

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 text=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd='E:/gh/openbor-bcec').decode('latin1');f=extract(text,'common_think');rows=[dict(dead=d,mask=m,value=v,mutate_dead=mut)for d,m,v,mut in itertools.product((0,1,-1,65536),(0,1,2,4,8,16,32,64,128,255),(-1,1,65536),(0,1))]
 expected=[]
 for c in rows:
  e=dict(dead=c['dead']);g=common_think(e);trace=[];reply=None
  while True:
   try:s=g.send(reply)
   except StopIteration:break
   trace.append(int(s));reply=c['value']if c['mask']&(1<<(int(s)-1))else 0
   if c['mutate_dead']:e['dead']=1
  expected.append([len(trace),*trace,*([0]*(8-len(trace)))])
 names=['ai_check_warp','ai_check_lie','ai_check_grabbed','ai_check_grab','ai_check_escape','ai_check_busy','common_attack','common_move']
 code='''#include <stdio.h>
typedef struct {int dead;} entity;
entity ent,*self=&ent;unsigned mask;int value,mutate_dead,count,trace[8];
'''+''.join('int '+n+'(void){trace[count++]='+str(i+1)+';if(mutate_dead)self->dead=1;return(mask&'+str(1<<i)+')?value:0;}\n'for i,n in enumerate(names))+f+'\nint cases[][4]={'+','.join('{'+','.join(str(c[k])for k in ('dead','mask','value','mutate_dead'))+'}'for c in rows)+'''};
int main(void){unsigned i;int j;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){ent.dead=cases[i][0];mask=cases[i][1];value=cases[i][2];mutate_dead=cases[i][3];count=0;for(j=0;j<8;j++)trace[j]=0;common_think();printf("%d",count);for(j=0;j<8;j++)printf(",%d",trace[j]);printf("\\n");}return 0;}
'''
 (a.output/'common_think.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','common_think.c','-fe=common_think.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 log=subprocess.check_output([str(a.output/'common_think.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()];ok=actual==expected
 r=dict(schema='BYOR_4086_COMMON_THINK_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,function_sha256=hashlib.sha256(f.encode()).hexdigest(),cases=len(rows),inputs=rows,actual=actual,expected=expected,handler_bodies_instrumented=True,motu_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],len(rows),'common thinker sequence cases');assert ok
if __name__=='__main__':main()
