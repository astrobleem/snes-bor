"""Unchanged source set_opponent over acyclic roots, aliases and NULL."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_opponent_4086 import set_opponent


def cases():
    rows=[]
    for count in range(1,129):
        for ent in (None,*sorted(set((0,count-1)))):
            for other in (None,*sorted(set((0,count-1)))):
                for mode in range(4):
                    owners=[None]*count
                    for i in range(count-1):
                        if mode==1:owners[i]=count-1
                        elif mode==2:owners[i]=i+1
                        elif mode==3:owners[i]=count-1 if i%2 or i==count-2 else count-2
                    rows.append(dict(count=count,ent=ent,other=other,owners=owners))
    return rows


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=a.engine).decode('latin1');body=extract(raw,'set_opponent');rows=cases()
    code='#include <stdio.h>\n#include <string.h>\ntypedef struct entity {struct entity *owner,*opponent;} entity;entity pool[128];\n'+body+r'''
int main(void){int count,ent,other,i,o;while(scanf("%d %d %d",&count,&ent,&other)==3){
 memset(pool,0,sizeof(pool));for(i=0;i<count;i++){scanf("%d",&o);pool[i].owner=o<0?NULL:pool+o;pool[i].opponent=pool+(i+1)%count;}
 set_opponent(ent<0?NULL:pool+ent,other<0?NULL:pool+other);
 for(i=0;i<count;i++)printf("%s%d",i?" ":"",pool[i].opponent?(int)(pool[i].opponent-pool):-1);puts("");}
return 0;}
'''
    (a.output/'opponent.c').write_text(code,encoding='latin1');env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    q=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','opponent.c','-fe=opponent.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(q.stdout+q.stderr)
    if q.returncode:raise ValueError('SET_OPPONENT_C_BUILD:'+q.stdout+q.stderr)
    inputs=''.join(' '.join(str(v if v is not None else -1)for v in (r['count'],r['ent'],r['other'],*r['owners']))+'\n'for r in rows)
    q=subprocess.run([str(a.output/'opponent.exe')],input=inputs,capture_output=True,text=True);actual=[list(map(int,l.split()))for l in q.stdout.splitlines()];expected=[]
    for r in rows:
        pool=[dict(owner=o,opponent=(i+1)%r['count'])for i,o in enumerate(r['owners'])];set_opponent(pool,r['ent'],r['other']);expected.append([v['opponent']if v['opponent']is not None else -1 for v in pool])
    failures=[dict(index=i,input=rows[i],actual=x,expected=y)for i,(x,y)in enumerate(zip(actual,expected))if x!=y]
    report=dict(schema='BYOR_SET_OPPONENT_AUTHORITY_V1',status='PASS'if q.returncode==0 and actual==expected else'FAIL',engine_commit=ENGINE_COMMIT,cases=len(rows),
        function_sha256=hashlib.sha256(body.encode('latin1')).hexdigest(),source_function_unmodified=True,owner_cycles_outside_source_terminating_domain=True,
        output_sha256=hashlib.sha256(q.stdout.encode()).hexdigest(),failures=failures,native_body_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'unchanged source opponent assignments;',len(failures),'mismatches')
    if report['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
