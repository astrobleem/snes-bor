"""Literal BOR range macro against bounded Q16.16 numeric adaptation."""
import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from source_check_range_4086 import check
from dialect_4086 import ENGINE_COMMIT


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ranges',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    header=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.h'],cwd='E:/gh/openbor-bcec').decode('latin1')
    macro=header[header.index('#define check_range(self, target, animnum)'):header.index('#define check_range_both(')]
    ir=json.loads(a.ranges.read_text());rows=[]
    for an in ir['animations']:
        r=an['ranges']
        for direction in (0,1,65536):
            for axis in range(4):
                for bound in r[2*axis:2*axis+2]:
                    for fraction in (-65537,-65536,-1,0,1,65535,65536):
                        source=[0]*4;target=[(r[2*i]+r[2*i+1])//2*65536 for i in range(4)]
                        if direction!=1:target[0]=-target[0]
                        target[axis]=bound*65536+fraction
                        if axis==0 and direction!=1:target[0]=-target[0]
                        rows.append(dict(handle=an['handle'],ranges=r,source=source,target=target,direction=direction))
    # Fractional self X exposes the macro's asymmetric truncation; large
    # binary32 values expose representational differences explicitly.
    for origin in (-2147483648,-1073741825,-65537,-1,1,65535,1073741823,2147483000):
        for axis in range(4):
            for delta in (-65537,-65536,-1,0,1,65535,65536):
                source=[0]*4;target=[0]*4;source[axis]=origin;target[axis]=origin+delta
                if not -2147483648<=target[axis]<=2147483647:continue
                rows.append(dict(handle=0,ranges=[0,0]*4,source=source,target=target,direction=1))
    rows.extend(dict(handle=0,ranges=[-10,80,-12,12,-1000,1000,-1000,1000],source=[0]*4,target=None,direction=d) for d in (0,1,65536))
    code='''#include <stdio.h>
#define DIRECTION_RIGHT 1
typedef struct {int x,z,y,base;} axes;
typedef struct {struct {axes min,max;}range;} animation;
typedef struct {struct {float x,z,y;}position;float base;int direction;struct {animation*animation[1];}modeldata;} entity;
'''+macro+'\ntypedef struct {int direction,present,ranges[8];float source[4],target[4];} input;\ninput cases[]={\n'
    for c in rows:
        code+='{'+str(c['direction'])+','+str(int(c['target']is not None))+',{'+','.join(str(n)for n in c['ranges'])+'},{'+','.join(repr(n/65536)+'f'for n in c['source'])+'},{'+','.join(repr(n/65536)+'f'for n in(c['target']or [0]*4))+'}},\n'
    code+='''};
int main(void){unsigned i;entity ent,victim,*self=&ent,*target;animation anim;input*c;
self->modeldata.animation[0]=&anim;
for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){c=&cases[i];self->direction=c->direction;target=c->present?&victim:NULL;
'''
    for i,axis in enumerate(('x','z','y','base')):
        field='base'if axis=='base'else'position.'+axis
        code+='self->'+field+'=c->source['+str(i)+'];victim.'+field+'=c->target['+str(i)+'];'
        code+='anim.range.min.'+axis+'=c->ranges['+str(2*i)+'];anim.range.max.'+axis+'=c->ranges['+str(2*i+1)+'];\n'
    code+='printf("%d\\n",!!check_range(self,target,0));}return 0;}\n';(a.output/'check_range.c').write_text(code)
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','check_range.c','-fe=check_range.exe'],cwd=a.output,env=env,capture_output=True,text=True)
    (a.output/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
    log=subprocess.check_output([str(a.output/'check_range.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log)
    actual=[int(l) for l in log.splitlines()];adapted=[int(check(c['ranges'],c['source'],c['target'],c['direction']))for c in rows]
    differences=[dict(index=i,input=c,source=v,q16=e)for i,(c,v,e)in enumerate(zip(rows,actual,adapted))if v!=e]
    # For exactly represented integral coordinates, retain source identity.
    integral=[i for i,c in enumerate(rows)if all(n%65536==0 for n in c['source']+(c['target']or []))]
    ok=len(actual)==len(rows) and all(actual[i]==adapted[i]for i in integral)
    report=dict(schema='BYOR_4086_CHECK_RANGE_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,
                literal_macro_sha256=hashlib.sha256(macro.encode()).hexdigest(),cases=len(rows),inputs=rows,source_results=actual,q16_results=adapted,
                exact_integral_cases=len(integral),accepted_compat_differences=differences,numeric_policy='ACCEPTED_COMPAT_Q16_16',
                native_bound=False,motu_gameplay_proven=False)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'range macro cases;',len(differences),'explicit Q16 differences');assert ok


if __name__=='__main__':main()
