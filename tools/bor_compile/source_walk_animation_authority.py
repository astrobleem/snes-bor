"""Verbatim 4086 common_walk_anim macro and animation-series dispatch authority."""
import argparse,hashlib,itertools,json,os,re,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_idle_4086 import common_anim_series

def run(engine,folder):
 folder.mkdir(parents=True,exist_ok=True)
 raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=engine).decode('latin1')
 function=extract(raw.replace('static int common_anim_series(','int common_anim_series('),'common_anim_series').replace('int common_anim_series(','static int common_anim_series(',1)
 macro=re.search(r'^#define common_walk_anim\(ent\) \\\r?\n\s*common_anim_series\([^\n]+',raw,re.M).group(0)
 rows=[dict(maximum=n,force=f,mask=m,target=t,self_id=s)for n in (1,3)for f in range(n+1)for m,t,s in itertools.product(range(8),range(3),(0,1,2))]
 preamble=r'''
#include <stdio.h>
#define ANI_WALK 1
typedef struct entity {int walkmode;} entity;
entity entities[2], *self;int animwalks[3]={1,102,103},max_walks,mask,target,chosen,calls,targets;
int validanim(entity *ent,int number){int i;for(i=0;i<3;i++)if(number==animwalks[i])return !!(mask&(1<<i));return 0;}
int normal_find_target(int number,int mode){targets++;return number==(target==1?102:target==2?103:-1);}
void ent_set_anim(entity *ent,int number,int reset){chosen=number;calls++;}
'''
 c=preamble+function+'\n'+macro+'\nint cases[][5]={'+','.join('{'+','.join(str(r[k])for k in ('maximum','force','mask','target','self_id'))+'}'for r in rows)+'};\n'
 c+=r'''
int main(void){int i,*r,result;entity value,*e=&value;
if(sizeof(int)!=4||sizeof(void*)!=4)return 2;
for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
r=cases[i];max_walks=r[0];e->walkmode=r[1];mask=r[2];target=r[3];self=r[4]?&entities[r[4]-1]:NULL;
chosen=-1;calls=targets=0;result=common_walk_anim(e);
printf("WALK|%d|%d,%d,%d,%d,%d\n",i,result,chosen,calls,targets,self==(r[4]?&entities[r[4]-1]:NULL));
}return 0;}
'''
 (folder/'walk_policy.c').write_text(c)
 env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
 proc=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','walk_policy.c','-fe=walk_policy.exe'],cwd=folder,env=env,capture_output=True,text=True);(folder/'build.log').write_text(proc.stdout+proc.stderr)
 if proc.returncode:raise ValueError('WALK_AUTHORITY_BUILD')
 output=subprocess.check_output([str((folder/'walk_policy.exe').resolve())],cwd=folder,text=True);results=[]
 for line in output.splitlines():
  if not line.startswith('WALK|'):continue
  _,i,values=line.split('|');i=int(i);r=rows[i];calls=[];targets=[]
  owner=dict(valid_animation=lambda e,n:bool(r['mask']&(1<<(1,102,103).index(n))),find_target=lambda n,mode:(targets.append(n)or n==(102 if r['target']==1 else 103 if r['target']==2 else -1)),set_animation=lambda e,n,reset:calls.append(n))
  result=common_anim_series({},(1,102,103)[:r['maximum']],r['force'],1,owner)
  wanted=[result,calls[0]if calls else-1,len(calls),len(targets),1];actual=list(map(int,values.split(',')));results.append(dict(case=r,actual=actual,expected=wanted,passed=actual==wanted))
 report=dict(schema='BYOR_4086_WALK_ANIMATION_AUTHORITY_V1',status='PASS'if len(results)==len(rows)and all(r['passed']for r in results)else'FAIL',engine_commit=ENGINE_COMMIT,function_sha256=hashlib.sha256(function.encode()).hexdigest(),macro_sha256=hashlib.sha256(macro.encode()).hexdigest(),macro=macro,cases=len(rows),results=results,animation_and_target_services_instrumented=True,max_walks_one_requires_no_target_queries=True,common_walk_does_not_replace_global_self=True,native_walk_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)
 (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=run(a.engine,a.output.resolve());print(r['status'],r['cases']);raise SystemExit(0 if r['status']=='PASS'else 1)
