"""Run pinned update_ents/arrange_ents verbatim against the resumable owner.

External gameplay handlers are deterministic instrumentation here. This proves
traversal, death checks, fresh-birth exclusion and compaction, not those handlers.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_world_tick import World, Entity, Service


def cases():
    result = []
    rng = random.Random(4086)
    for n in range(1, 7):
        for mask in range(1 << n):
            order = list(range(n)); rng.shuffle(order)
            maximum = n
            for variant in range(3):
                result.append(dict(n=n, order=order, maximum=maximum, alive=mask,
                    fresh=(mask & 0x15) if variant == 1 else 0,
                    frozen=(mask & 0x2a) if variant == 2 else 0,
                    level=variant != 2, kill_stage=0, kill_slot=0, spawn_stage=0,
                    time=0xffffffff if variant == 1 else 48))
    for stage in (2, 5, 6, 7, 8, 9, 11):
        for slot in range(4):
            result.append(dict(n=4, order=[2, 0, 3, 1], maximum=4, alive=15,
                fresh=0, frozen=0, level=True, kill_stage=stage, kill_slot=slot,
                spawn_stage=0, time=48))
    for stage in (5, 6, 7, 8):
        result.append(dict(n=4, order=[2, 0, 3, 1], maximum=2, alive=5,
            fresh=0, frozen=0, level=True, kill_stage=0, kill_slot=0,
            spawn_stage=stage, time=48))
    return result


def expected(case):
    world = World([Entity(bool(case['alive'] & (1 << s)),
        case['time'] if case['fresh'] & (1 << s) else (case['time'] - 1) & 0xffffffff,
        bool(case['frozen'] & (1 << s))) for s in range(case['n'])],
        list(case['order']), case['maximum'], case['time'], bool(case['level']))
    events = []; spawned = False
    for service, slot in world.tick():
        events.append([int(service), slot])
        if int(service) == case['kill_stage'] and slot == case['kill_slot']:
            world.entities[slot].alive = False
        if int(service) == case['spawn_stage'] and not spawned:
            world.spawn_slot(); spawned = True
    return dict(events=events, maximum=world.maximum,
        alive=sum(1 << s for s, e in enumerate(world.entities) if e.alive),
        order=world.order, completed=world.completed)


def derive(engine, folder):
    folder.mkdir(parents=True, exist_ok=True)
    raw = subprocess.check_output(['git', 'show', ENGINE_COMMIT + ':engine/openbor.c'], cwd=engine)
    text = raw.decode('latin1')
    functions = '\n\n'.join(extract(text, name) for name in ('arrange_ents', 'update_ents'))
    rows = cases(); fixtures = []
    for c in rows:
        fixtures.append('{%s,{%s}}' % (','.join(str(int(c[k]))+'u' for k in
            ('n','maximum','alive','fresh','frozen','level','kill_stage','kill_slot','spawn_stage','time')),
            ','.join(str(s) for s in c['order'])))
    source = r'''#include <stdio.h>
#include <string.h>
#define GAME_SPEED 200
typedef struct {float x,z;} vector;
typedef struct {int exists; unsigned timestamp; int update_mark, frozen, slot;
 float movex,movez,speedmul; vector velocity;} entity;
typedef struct {unsigned n,maximum,alive,fresh,frozen,has_level,kill_stage,kill_slot,spawn_stage,time; int order[128];} fixture;
entity pool[128], *ent_list[128], *self;
int ent_count, ent_max, case_index, did_spawn;
unsigned time; void *level; fixture *test;
void event(int stage, entity *e) {
 int i; printf("E %d %d %d\n",case_index,stage,e->slot);
 if(stage==test->kill_stage && e->slot==test->kill_slot && e->exists) {e->exists=0;ent_count--;}
 if(stage==test->spawn_stage && !did_spawn) {
  did_spawn=1;
  for(i=0;i<test->n;i++) if(!ent_list[i]->exists) {
   ent_list[i]->exists=1;ent_list[i]->timestamp=time;ent_count++;
   if(ent_count>ent_max) ent_max=ent_count; break;
  }
 }
}
void check_lost(void) {event(2,self);}
int is_frozen(entity *e) {event(3,e);return e->frozen;}
void expand_time(entity *e) {event(4,e);}
void execute_updateentity_script(entity *e) {event(5,e);}
void check_ai(void) {event(6,self);}
void update_animation(void) {event(7,self);}
void check_attack(void) {event(8,self);}
void update_health(void) {event(9,self);}
void ent_post_update(entity *e) {event(11,e);}
''' + functions + '\nfixture tests[]={' + ',\n'.join(fixtures) + r'''};
int main(void) {
 int i; unsigned mask;
 for(case_index=0;case_index<sizeof(tests)/sizeof(tests[0]);case_index++) {
  test=&tests[case_index];memset(pool,0,sizeof(pool));ent_count=0;ent_max=test->maximum;
  time=test->time;level=test->has_level ? test:NULL;did_spawn=0;
  for(i=0;i<test->n;i++) {
   pool[i].slot=i;pool[i].exists=(test->alive>>i)&1;ent_count+=pool[i].exists;
   pool[i].timestamp=((test->fresh>>i)&1)?time:time-1;
   pool[i].frozen=(test->frozen>>i)&1;pool[i].speedmul=2;
   ent_list[i]=&pool[test->order[i]];
  }
  update_ents();mask=0;for(i=0;i<test->n;i++) if(pool[i].exists) mask|=1u<<i;
  printf("S %d %d %u",case_index,ent_max,mask);
  for(i=0;i<test->n;i++) printf(" %d",ent_list[i]->slot);
  printf("\n");
 }
 return 0;
}
'''
    (folder/'world_tick.c').write_text(source)
    env = dict(os.environ, WATCOM='C:/WATCOM', INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    build = subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','world_tick.c',
                            '-fe=world_tick.exe'],cwd=folder,env=env,capture_output=True,text=True)
    (folder/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode: raise ValueError('WORLD_TICK_AUTHORITY_BUILD_FAILED')
    output = subprocess.check_output([str((folder/'world_tick.exe').resolve())],cwd=folder,text=True)
    observed=[dict(events=[]) for _ in rows]
    for line in output.splitlines():
        words=line.split(); index=int(words[1]); values=list(map(int,words[2:]))
        if words[0]=='E': observed[index]['events'].append(values)
        elif words[0]=='S': observed[index].update(maximum=values[0],alive=values[1],order=values[2:])
        else: raise ValueError('WORLD_TICK_AUTHORITY_OUTPUT')
    results=[]
    for c,got in zip(rows,observed):
        wanted=expected(c)
        visible=[e for e in wanted['events'] if e[0] not in (1,10,12)]
        passed=(got['events']==visible and all(got[k]==wanted[k] for k in ('maximum','alive','order')))
        results.append(dict(case=c,expected=wanted,observed=got,passed=passed))
    report=dict(schema='BYOR_4086_WORLD_TICK_AUTHORITY_V1',status='PASS' if all(r['passed'] for r in results) else 'FAIL',
        engine_commit=ENGINE_COMMIT,source_sha256=hashlib.sha256(raw).hexdigest(),
        functions_sha256=hashlib.sha256(functions.encode('latin1')).hexdigest(),
        cases=len(results),results=results,live_gameplay_handlers_bound=False,motu_gameplay_proven=False)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=derive(a.engine,a.output.resolve())
    print(json.dumps({k:r[k] for k in ('status','cases','functions_sha256')}))
    if r['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
