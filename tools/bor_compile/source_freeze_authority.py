"""Run literal 4086 freeze macros with pinned unsigned timer declarations."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import re
import subprocess
from dialect_4086 import ENGINE_COMMIT
from source_freeze_4086 import TIMERS, frozen, expand


def macro(text, name):
    lines=text.splitlines();start=next(i for i,line in enumerate(lines) if line.startswith('#define '+name+'('))
    result=[lines[start]]
    while result[-1].rstrip().endswith('\\'):
        result.append(lines[start+len(result)])
    return '\n'.join(result)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    text=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.h'],cwd=a.engine).decode('latin1')
    macros='\n'.join(macro(text,n)for n in ('is_frozen','expand_time'))
    declaration=text[text.index('    u32\tlastmove;'):text.index('    int update_mark;')]
    assert all(re.search(r'\bu32\s+'+n+r'\s*;',declaration)for n in TIMERS)
    rng=random.Random(408612);rows=[];expected=[]
    for typ in (0,1,2,128,129,0xffffffff):
        for textbox in (0,1):
            for bomber in (0,1,2):
                for self_other in (0,1):
                    for time,deadline in ((0,0),(0,1),(48,47),(48,48),(48,49),(0xffffffff,1),(0xffffffff,0xffffffff),(0,0xffffffff)):
                        timers=[rng.choice((0,1,48,65535,65536,0x7fffffff,0x80000000,0xffffffff)) for _ in TIMERS]
                        timers[TIMERS.index('freezetime')]=deadline
                        flag=rng.choice((0,1,-1,65536))
                        row=dict(type=typ,textbox=textbox,bomber=bomber,self_other=self_other,time=time,frozen=flag,timers=timers)
                        rows.append(row)
                        ent=dict(token=1,type=typ,frozen=flag,**dict(zip(TIMERS,timers)))
                        other=dict(token=2,type=128,frozen=-1,freezetime=(time+1)&0xffffffff)
                        state=frozen(ent,other if self_other else ent,textbox=textbox,smartbomber=bomber,time=time)
                        expand(ent,textbox=textbox,smartbomber=bomber)
                        expected.append([int(state),*[ent[n]for n in TIMERS]])
    crows=['{'+','.join(str(r[k])+'u' for k in ('type','textbox','bomber','self_other','time'))+','+str(r['frozen'])+',{'+','.join(str(v)+'u'for v in r['timers'])+'}}'for r in rows]
    code='''#include <stdio.h>
#include <string.h>
#define TYPE_TEXTBOX 128
typedef unsigned u32;
typedef struct {struct {u32 type;} modeldata;int frozen;'''+''.join('u32 '+n+';'for n in TIMERS)+'''} entity;
entity ent,other,*self,*textbox,*smartbomber,*test=&ent;u32 time;
'''+macros+'''
struct {u32 type,textbox,bomber,self_other,time;int frozen;u32 timers[13];} cases[]={'''+','.join(crows)+'''};
int main(void){unsigned i;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
memset(&ent,0,sizeof(ent));memset(&other,0,sizeof(other));ent.modeldata.type=cases[i].type;ent.frozen=cases[i].frozen;
'''+''.join(f'ent.{n}=cases[i].timers[{i}];\n'for i,n in enumerate(TIMERS))+'''
time=cases[i].time;other.modeldata.type=128;other.frozen=-1;other.freezetime=time+1;
self=cases[i].self_other?&other:&ent;textbox=cases[i].textbox?&other:0;smartbomber=cases[i].bomber==1?&ent:cases[i].bomber==2?&other:0;
printf("%d",!!is_frozen(test));expand_time(test);
'''+''.join(f'printf(",%u",ent.{n});'for n in TIMERS)+'''printf("\\n");}return 0;}
'''
    (folder/'freeze.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','freeze.c','-fe=freeze.exe'],cwd=folder,env=env,capture_output=True,text=True);(folder/'build.log').write_text(b.stdout+b.stderr)
    if b.returncode:raise ValueError('SOURCE_FREEZE_AUTHORITY_BUILD')
    log=subprocess.check_output([str(folder/'freeze.exe')],cwd=folder,text=True);(folder/'authority.log').write_text(log)
    actual=[list(map(int,line.split(',')))for line in log.splitlines()];failures=[i for i,(e,v)in enumerate(zip(expected,actual))if e!=v]
    ok=len(actual)==len(rows)and not failures
    d=dict(schema='BYOR_4086_FREEZE_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,macros_sha256=hashlib.sha256(macros.encode()).hexdigest(),timer_declarations_sha256=hashlib.sha256(declaration.encode()).hexdigest(),cases=len(rows),inputs=rows,expected=expected,actual=actual,failures=failures[:20],timer_fields=list(TIMERS),native_backend_bound=False,motu_gameplay_proven=False)
    (folder/'report.json').write_text(json.dumps(d,indent=2)+'\n');print(d['status'],len(rows),'freeze macro cases')
    if not ok:raise SystemExit(1)


if __name__=='__main__':main()
