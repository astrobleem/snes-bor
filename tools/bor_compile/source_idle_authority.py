"""Compare generic idle policy with verbatim pinned set_idle/idle-series C."""
import argparse
import hashlib
import itertools
import json
import os
import subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_idle_4086 import common_idle_anim, set_idle

IDS = (61, 80, 0, 105, 106)


def fixtures():
    keys = ('type', 'subtype', 'idling', 'mask', 'health', 'time', 'force', 'target')
    values = ((0, 1, 2, 65536), (0, 1), (0, 1, -2), (0, 1, 2, 4, 8, 16, 24, 31),
              (-1, 25, 26), (48, 49), (0, 1, 2, 3), (0, 1, 2))
    return [dict(zip(keys, row)) for row in itertools.product(*values)]


def expected(row, direct):
    calls = []
    targets = []
    ent = dict(model=dict(type=row['type'], subtype=row['subtype']), modeldata=dict(health=100),
               health=row['health'], idling=row['idling'], attacking=7, inpain=-1,
               jumping=3, blocking=2, vx=1.25, vz=-2.5, sleeptime=48, idlemode=row['force'])
    previous = object()
    owner = dict(self=previous, biker=1, faint=61, sleep=80, idle=0, idles=(0, 105, 106), time=row['time'])
    owner['valid_animation'] = lambda e, n: bool(row['mask'] & (1 << IDS.index(n)))
    def target(n, mode):
        assert owner['self'] is ent
        targets.append(n)
        return n == (105 if row['target'] == 1 else 106 if row['target'] == 2 else -1)
    def animation(e, n, reset):
        assert owner['self'] is ent and reset == 0
        calls.append(n)
    owner.update(find_target=target, set_animation=animation)
    result = common_idle_anim(ent, owner) if direct else set_idle(ent, owner)
    assert owner['self'] is previous
    return [result, ent['idling'], ent['attacking'], ent['inpain'], ent['jumping'], ent['blocking'],
            int(ent['vx'] * 4), int(ent['vz'] * 4), calls[0] if calls else -1, len(calls),
            len(targets), *(targets + [-1, -1])[:2], 1]


def run(engine, folder):
    folder.mkdir(parents=True, exist_ok=True)
    raw = subprocess.check_output(['git', 'show', ENGINE_COMMIT + ':engine/openbor.c'], cwd=engine).decode('latin1')
    series = extract(raw.replace('static int common_anim_series(', 'int common_anim_series('), 'common_anim_series')
    series = series.replace('int common_anim_series(', 'static int common_anim_series(', 1)
    functions = '\n\n'.join((series, extract(raw, 'common_idle_anim'), extract(raw, 'set_idle')))
    rows = fixtures()
    c = r'''#include <stdio.h>
#include <string.h>
#define SUBTYPE_BIKER 1
#define TYPE_NONE 0
#define ANI_FAINT 61
#define ANI_SLEEP 80
#define ANI_IDLE 0
typedef struct {int type,subtype,health;} s_model;
typedef struct entity {s_model *model,modeldata;int idling,attacking,inpain,jumping,blocking,health,idlemode;unsigned sleeptime;struct {float x,z;} velocity;} entity;
entity *self,oldself;unsigned time;int animidles[3]={0,105,106},max_idles=3,mask,target,chosen,calls,targets[2],targetcalls,badself;
int validanim(entity *ent,int number){int ids[5]={61,80,0,105,106},i;for(i=0;i<5;i++)if(number==ids[i])return !!(mask&(1<<i));return 0;}
int normal_find_target(int number,int mode){if(self==&oldself||mode)badself=1;if(targetcalls<2)targets[targetcalls]=number;targetcalls++;return number==(target==1?105:target==2?106:-1);}
void ent_set_anim(entity *ent,int number,int reset){if(self!=ent||reset)badself=1;chosen=number;calls++;}
''' + functions + '\nint cases[][8]={' + ','.join('{' + ','.join(str(r[k]) for k in ('type','subtype','idling','mask','health','time','force','target')) + '}' for r in rows) + '};\n'
    c += r'''int main(void){unsigned i;int direct,*r,result;s_model model;entity e;
if(sizeof(int)!=4||sizeof(unsigned)!=4||sizeof(void*)!=4)return 2;
for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++)for(direct=0;direct<2;direct++){
r=cases[i];memset(&e,0,sizeof(e));model.type=r[0];model.subtype=r[1];e.model=&model;e.modeldata.health=100;
e.idling=r[2];mask=r[3];e.health=r[4];time=r[5];e.idlemode=r[6];target=r[7];e.sleeptime=48;
e.attacking=7;e.inpain=-1;e.jumping=3;e.blocking=2;e.velocity.x=1.25f;e.velocity.z=-2.5f;
self=&oldself;chosen=targets[0]=targets[1]=-1;calls=targetcalls=badself=0;
result=direct?common_idle_anim(&e):set_idle(&e);
printf("IDLE|%u|%d|%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d\n",i,direct,result,e.idling,e.attacking,e.inpain,e.jumping,e.blocking,(int)(e.velocity.x*4),(int)(e.velocity.z*4),chosen,calls,targetcalls,targets[0],targets[1],self==&oldself&&!badself);
}return 0;}
'''
    (folder/'idle_policy.c').write_text(c)
    env = dict(os.environ, WATCOM='C:/WATCOM', INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    p = subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','idle_policy.c','-fe=idle_policy_authority.exe'],cwd=folder,env=env,capture_output=True,text=True)
    (folder/'build.log').write_text(p.stdout+p.stderr)
    if p.returncode: raise ValueError('IDLE_AUTHORITY_BUILD')
    output = subprocess.check_output([str((folder/'idle_policy_authority.exe').resolve())],cwd=folder,text=True)
    results=[]
    for line in output.splitlines():
        if not line.startswith('IDLE|'): continue
        _,i,direct,values=line.split('|');i=int(i);direct=int(direct);actual=list(map(int,values.split(',')));wanted=expected(rows[i],direct)
        results.append(dict(case=rows[i],direct=bool(direct),actual=actual,expected=wanted,passed=actual==wanted))
    report=dict(schema='BYOR_4086_IDLE_AUTHORITY_V1',status='PASS' if len(results)==2*len(rows) and all(r['passed'] for r in results) else 'FAIL',engine_commit=ENGINE_COMMIT,functions_sha256=hashlib.sha256(functions.encode('latin1')).hexdigest(),cases=len(results),results=results,animation_and_target_services_instrumented=True,native_idle_bound=False,motu_gameplay_proven=False)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=run(a.engine,a.output.resolve());print(json.dumps({k:r[k] for k in ('status','cases','functions_sha256')}))
    if r['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
