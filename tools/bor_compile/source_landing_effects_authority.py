"""Execute pinned landing drop/effects bodies; colourmap service is observed.

The attack is the source memset-zero landing attack with ATK_LAND. Tests
include existing frozen, airborne, drop, and knockdown state. They do not
prove native colourmap application, weapon handling, or a damage callback.
"""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import subprocess
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract


def run(engine, output):
    output.mkdir(parents=True, exist_ok=True)
    def pinned(name):
        return subprocess.check_output(['git', '-C', str(engine), 'show', ENGINE_COMMIT+':engine/'+name]).decode('latin1')
    raw = pinned('openbor.c')
    header = pinned('openbor.h')
    names = ('diff', 'inair', 'checkdamagedrop', 'checkdamageeffects')
    bodies = {name: extract(raw, name) for name in names}
    macro = re.search(r'^#define unfrozen\(e\).*?(?=\n\s*\n)', header, re.M|re.S).group(0)
    rows = []
    for nodrop, frozen, drop, y in itertools.product((-1, 0, 1, 2, 3), (0, 1), (0, 1), (-0.125, -0.1, -0.05, 0., 0.05, 0.1, 0.125)):
        rows.append(dict(mode=0, nodrop=nodrop, frozen=frozen, drop=drop, y=y, animal=0, guard=0, count=3., model_count=5., deadline=47))
    for animal, guard, drop, count, deadline in itertools.product((0, 1), (0, 1), (0, 1), (-1., 0., 3.), (0, 47, 48, 49)):
        rows.append(dict(mode=1, nodrop=0, frozen=0, drop=drop, y=0., animal=animal, guard=guard, count=count, model_count=5., deadline=deadline))
    code = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define GAME_SPEED 200
#define ATK_LAND 16
typedef struct {int rise,riseattack;} Stay;
typedef struct {float x,z,y;} Vec;
typedef struct entity entity;
typedef struct {int attack_force,attack_type,attack_drop,no_pain,freeze,maptime,freezetime,forcemap,blast,steal,seal,sealtime,dot,dot_index,dot_time,dot_force,dot_rate;Stay staydown;} s_attack;
typedef struct {int health,nodrop,animal;float knockdowncount;struct{int max,current;}guardpoints;struct{int frozen;}maps;} Model;
struct entity {Model modeldata;Vec position;float base,knockdowncount;struct{float knockdown;}defense[20];entity *opponent;int health,frozen,drop,projectile,map,colourmap,seal;unsigned freezetime,maptime,sealtime,knockdowntime;Stay staydown;entity *dot_owner[4];int dot[4],dot_force[4],dot_rate[4],dot_atk[4];unsigned dot_time[4];};
entity *self;unsigned time=48;int maps,map_arg,unexpected;
void ent_set_colourmap(entity *e,int n){if(e!=self)unexpected++;maps++;map_arg=n;e->colourmap=n;}
int model_get_colourmap(Model *m,int n){unexpected++;return n;}
'''+macro+'\n'+'\n'.join(bodies.values())
    code += '\nstruct Case{int mode,nodrop,frozen,drop;float y;int animal,guard;float count,model_count;unsigned deadline;}cases[]={\n'
    code += ',\n'.join('{'+','.join(str(v) for v in r.values())+'}' for r in rows)+'\n};\n'
    code += r'''
int main(void){unsigned i;entity e;s_attack a;struct Case *c;
if(sizeof(int)!=4||sizeof(float)!=4||sizeof(void*)!=4)return 2;
for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
c=cases+i;memset(&e,0,sizeof(e));memset(&a,0,sizeof(a));self=&e;maps=unexpected=0;map_arg=-1;
e.modeldata.nodrop=c->nodrop;e.modeldata.animal=c->animal;e.modeldata.guardpoints.max=c->guard;e.modeldata.knockdowncount=c->model_count;
e.frozen=c->frozen;e.freezetime=123;e.drop=c->drop;e.position.y=c->y;e.map=7;e.colourmap=9;
e.projectile=3;e.staydown.rise=11;e.staydown.riseattack=12;e.health=100;e.modeldata.health=150;
e.knockdowncount=c->count;e.knockdowntime=c->deadline;e.defense[ATK_LAND].knockdown=1.;
a.attack_type=ATK_LAND;a.attack_force=7;
if(c->mode)checkdamagedrop(&a);else checkdamageeffects(&a);
printf("EFFECT|%u|%d,%d,%u,%d,%d,%d,%d,%d,%d,%g,%u,%d\n",i,e.drop,e.frozen,e.freezetime,e.projectile,e.staydown.rise,e.staydown.riseattack,e.colourmap,maps,map_arg,e.knockdowncount,e.knockdowntime,unexpected);
}return 0;}
'''
    (output/'landing_effects.c').write_text(code)
    env = dict(os.environ, WATCOM='C:/WATCOM', INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    build = subprocess.run(['C:/WATCOM/BINNT/wcl386.exe', '-q', '-za99', '-bt=nt', '-op', '-fpc', 'landing_effects.c', '-fe=landing_effects.exe'], cwd=output, env=env, capture_output=True, text=True)
    (output/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:
        raise ValueError('LANDING_EFFECTS_C_BUILD:'+build.stdout+build.stderr)
    log = subprocess.check_output([str(output/'landing_effects.exe')], cwd=output, text=True)
    results = []
    for line in log.splitlines():
        if not line.startswith('EFFECT|'):
            continue
        _, index, values = line.split('|')
        i = int(index); r = rows[i]
        actual = list(map(float, values.split(',')))
        drop, count, deadline = r['drop'], r['count'], r['deadline']
        if r['mode']:
            if r['animal']: drop = 1
            if not drop:
                if deadline and deadline < 48: count = r['model_count']
                deadline = 248
                drop = int(count < 0)
            expected = [drop,0,123,3,11,12,9,0,-1,count,deadline,0]
        else:
            if r['frozen']: drop = 1
            if r['nodrop']: drop = 0
            if abs(r['y']) >= .1 and r['nodrop'] < 2: drop = 1
            expected = [drop,0,0 if r['frozen'] else 123,0,0 if drop else 11,0 if drop else 12,7 if r['frozen'] else 9,r['frozen'],7 if r['frozen'] else -1,count,deadline,0]
        results.append(dict(case=r, actual=actual, expected=expected, passed=actual==expected))
    report = dict(schema='BYOR_4086_LANDING_EFFECTS_AUTHORITY_V1', status='PASS' if len(results)==len(rows) and all(r['passed'] for r in results) else 'FAIL',
                  engine_commit=ENGINE_COMMIT, functions={n:hashlib.sha256(b.encode('latin1')).hexdigest() for n,b in bodies.items()},
                  unfrozen_macro_sha256=hashlib.sha256(macro.encode('latin1')).hexdigest(), cases=len(rows), results=results,
                  attack_policy='source zeroed landing attack, force7, ATK_LAND16', colourmap_service_instrumented=True,
                  airborne_predicate='absolute source position.y minus base >= 0.1, independent of vertical velocity',
                  native_damage_callback_backend_proven=False, motu_gameplay_proven=False, no_color_reduction=True)
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=run(a.engine,a.output.resolve());print(json.dumps({k:r[k] for k in ('status','cases','functions')}))
    if r['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
