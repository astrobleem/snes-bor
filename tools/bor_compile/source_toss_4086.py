"""Execute pinned tossentity/toss and numeric conversion with Win32 widths."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract


def cases():
    rows=[]
    for argc in range(1,5):
        for lift in (0,0.25,-1.5):
            rows.append(dict(argc=argc,lift=lift,x=1.5,z=-0.75,kind=2,time=48,entity=True))
    rows.extend([dict(argc=4,lift=1.25,x=1.5,z=-0.75,kind=3,time=48,entity=True),
        dict(argc=4,lift=1,x=2,z=-3,kind=1,time=0xffffffff,entity=True),
        dict(argc=0,lift=1,x=2,z=3,kind=1,time=48,entity=True),
        dict(argc=4,lift=1,x=2,z=3,kind=1,time=48,entity=False)])
    return rows


def derive(engine,folder):
    folder.mkdir(parents=True,exist_ok=True)
    paths=('engine/openbor.c','engine/openborscript.c','engine/source/scriptlib/ScriptVariant.c')
    raw={p:subprocess.check_output(['git','show',ENGINE_COMMIT+':'+p],cwd=engine) for p in paths}
    functions='\n\n'.join(extract(raw[p].decode('latin1'),name) for p,name in
        ((paths[2],'ScriptVariant_DecimalValue'),(paths[0],'toss'),(paths[1],'openbor_tossentity')))
    rows=cases();fixtures=[]
    for r in rows:
        fixtures.append('{%s}'%','.join(str(int(r[k]))+'u' if k in ('argc','kind','time','entity') else str(r[k])
                                     for k in ('argc','lift','x','z','kind','time','entity')))
    source=r'''#include <stdio.h>
#include <string.h>
typedef int HRESULT;typedef double DOUBLE;typedef long LONG;
#define VT_INTEGER 1
#define VT_DECIMAL 2
#define S_OK 0
#define E_FAIL (-1)
typedef struct {int vt;union {LONG lVal;DOUBLE dblVal;void *ptrVal;};} ScriptVariant;
typedef struct {float x,z,y;} vector;
typedef struct {vector velocity,position;unsigned toss_time;} entity;
unsigned time;
void ScriptVariant_ChangeType(ScriptVariant *v,int kind) {v->vt=kind;}
''' + functions + r'''
typedef struct {unsigned argc;double lift,x,z;unsigned kind,time,entity;} fixture;
fixture cases[]={''' + ',\n'.join(fixtures) + r'''};
int main(void) {
 unsigned i,j;entity e;ScriptVariant vars[4],ret,*out,*args[4];HRESULT result;fixture *f;
 if(sizeof(long)!=4 || sizeof(void *)!=4 || sizeof(unsigned)!=4) return 2;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++) {
  f=&cases[i];memset(vars,0,sizeof(vars));memset(&ret,0,sizeof(ret));
  e.velocity.x=4;e.velocity.z=5;e.velocity.y=6;e.position.y=10;e.toss_time=123;
  vars[0].vt=5;vars[0].ptrVal=f->entity ? &e:NULL;
  for(j=1;j<4;j++) {
   double number=j==1 ? f->lift:j==2 ? f->x:f->z;vars[j].vt=f->kind;
   if(f->kind==1) vars[j].lVal=(long)number;else vars[j].dblVal=number;
  }
  for(j=0;j<4;j++) args[j]=&vars[j];time=f->time;out=&ret;
  result=openbor_tossentity(args,&out,f->argc);
  printf("TOSSAUTH|%u|%d|%d|%ld|%.9g|%.9g|%.9g|%.9g|%u\n",i,result,out ? out->vt:0,
   out ? out->lVal:0,e.velocity.x,e.velocity.z,e.velocity.y,e.position.y,e.toss_time);
 }
 return 0;
}
'''
    (folder/'toss.c').write_text(source)
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    proc=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','toss.c','-fe=toss.exe'],
                         cwd=folder,env=env,capture_output=True,text=True)
    (folder/'build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('TOSS_AUTHORITY_BUILD')
    output=subprocess.check_output([str((folder/'toss.exe').resolve())],cwd=folder,text=True)
    results=[]
    for line in output.splitlines():
        if not line.startswith('TOSSAUTH|'):continue
        fields=line.split('|');index=int(fields[1]);r=rows[index]
        got=list(map(float,fields[2:]));wanted=[-1,0,0,4,5,6,10,123]
        if r['argc'] and r['entity']:
            numeric=r['kind'] in (1,2)
            lift=r['lift'] if r['argc']>=2 and numeric else 0
            x=r['x'] if r['argc']>=3 and numeric else 0
            z=r['z'] if r['argc']>=4 and numeric else 0
            if r['kind']==1:lift,x,z=map(int,(lift,x,z))
            wanted=[0,1,1,x,z,lift if lift else 6,10.5 if lift else 10,
                    (r['time']+1)&0xffffffff if lift else 123]
        results.append(dict(case=r,actual=got,expected=wanted,passed=got==wanted))
    report=dict(schema='BYOR_4086_TOSS_AUTHORITY_V1',status='PASS' if len(results)==len(rows) and all(r['passed'] for r in results) else 'FAIL',
        engine_commit=ENGINE_COMMIT,source_sha256={p:hashlib.sha256(b).hexdigest() for p,b in raw.items()},
        functions_sha256=hashlib.sha256(functions.encode('latin1')).hexdigest(),cases=len(rows),results=results,
        gravity_and_landing_bound=False,motu_gameplay_proven=False)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();d=derive(a.engine,a.output.resolve())
    print(json.dumps({k:d[k] for k in ('status','cases','functions_sha256')}))
    if d['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
