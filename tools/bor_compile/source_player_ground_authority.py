"""Compare the literal pinned ground movement block and callback continuations."""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import random
import struct
import subprocess
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_player_ground_4086 import execute, Service
from source_player_run_4086 import KEYS

ROLES = {'up': 0, 'down': 1, 'duck': 2, 'turn': 3, 'backwalk': 4, 'run': 5}


def cases():
    for mask, plane, running, direction, timer, valid in itertools.product(
            range(16), (0, 1), (0, 1), (0, 1, 2), range(5), (0, 3, 12, 31)):
        yield [mask, plane, running, direction, timer, valid, mask % 4,
               (mask // 4) % 4, (0, 2, 8, 10)[mask % 4], mask % 5, 1]
    rng = random.Random(4086)
    for _ in range(4096):
        yield [rng.randrange(16), rng.randrange(2), rng.choice((0, 1, -1)),
               rng.choice((0, 1, 2, -1)), rng.randrange(5), rng.randrange(64),
               rng.randrange(4), rng.randrange(4), rng.choice((0, 2, 8, 10)),
               rng.randrange(5), rng.randrange(2)]


def simulate(row):
    mask, plane, running, direction, timer, validmask, facing, level_facing, scroll, mutation, notinair = row
    keys = 0x80000000
    for i, name in enumerate(('moveleft', 'moveright', 'moveup', 'movedown')):
        if mask & (1 << i): keys |= KEYS[name]
    turntime, delay, time = ((0, 0, 48), (0, 7, 48), (48, 7, 48),
                             (49, 7, 48), (0, 7, 0xfffffffe))[timer]
    e = dict(direction=direction, running=running, turntime=turntime,
             velocity=dict(x=7.0, z=-3.0), turning=-3, idling=-4,
             takeaction=99, modeldata=dict(speed=2.5, runspeed=4.5,
             turndelay=delay, facing=facing))
    context = dict(min_z=0, max_z=plane, notinair=notinair, time=time,
                   level=dict(facing=level_facing, scrolldir=scroll),
                   facing_right=1, facing_left=2, facing_level=3,
                   scroll_left=8, scroll_right=2)
    trace = []
    def valid(role):
        trace.append(100 + ROLES[role])
        return validmask & (1 << ROLES[role])
    def mutate():
        if mutation == 1:
            e['direction'] = 1 - e['direction']
            e['modeldata']['facing'] = 2
            context['level']['facing'] = 1
        elif mutation == 2:
            e['velocity']['x'] = 9.0
            e['velocity']['z'] = 11.0
            e['idling'] = 0
        elif mutation == 3:
            e['turntime'] = 17
            e['modeldata']['turndelay'] = 3
            e['modeldata']['facing'] = 3
            context['level']['facing'] = 0
            context['level']['scrolldir'] = 10
        elif mutation == 4:
            e['takeaction'] = 77
            e['idling'] = 1
    for request in execute(e, dict(keys=keys), context, valid):
        service = request[0]
        trace.append(int(service))
        if service == Service.SET_ANIMATION:
            trace.append(ROLES[request[2]])
        if service in (Service.SET_ANIMATION, Service.TOUCH_ITEM): mutate()
    state = [e['direction'], e['running'], e['turntime'], e['turning'], e['idling'],
             0 if e['takeaction'] is None else 42 if e['takeaction'] == 'common_turn' else e['takeaction'],
             struct.unpack('<I', struct.pack('<f', e['velocity']['x']))[0],
             struct.unpack('<I', struct.pack('<f', e['velocity']['z']))[0],
             e['modeldata']['facing'], context['level']['facing'],
             context['level']['scrolldir'], e['modeldata']['turndelay'], len(trace)]
    return struct.pack('<45I', *(v & 0xffffffff for v in state + trace + [0]*(32-len(trace))))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    out = p.parse_args().output.resolve(); out.mkdir(parents=True, exist_ok=True)
    raw = subprocess.check_output(['git', '-C', 'E:/gh/openbor-bcec', 'show',
                                   ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
    full = extract(raw, 'player_think')
    block = full[full.index('    if(PLAYER_MIN_Z != PLAYER_MAX_Z)', full.index('//dang long run checking logic')):]
    rows = list(cases())
    code = r'''
#include <stdio.h>
#include <io.h>
#include <fcntl.h>
#include <string.h>
typedef unsigned int u32;
typedef struct {int facing,turndelay;float speed,runspeed;int subtype;}model;
typedef struct {int direction,running,turning,idling,takeaction;u32 turntime;
 struct{float x,z;}velocity;struct{float x,z;}position;model modeldata;}entity;
typedef struct{u32 keys;}s_player;
typedef struct{int facing,scrolldir;}level_t;
entity e,*self=&e;s_player p,*pl=&p;level_t l,*level=&l;
int PLAYER_MIN_Z=0,PLAYER_MAX_Z,mutation,validmask;u32 time,trace[32],nt;
#define DIRECTION_LEFT 0
#define DIRECTION_RIGHT 1
#define FACING_ADJUST_RIGHT 1
#define FACING_ADJUST_LEFT 2
#define FACING_ADJUST_LEVEL 3
#define SCROLL_LEFT 8
#define SCROLL_RIGHT 2
#define TYPE_ITEM 4
#define player_test_touch 0
#define ANI_UP 0
#define ANI_DOWN 1
#define ANI_DUCK 2
#define ANI_TURN 3
#define ANI_BACKWALK 4
#define ANI_RUN 5
#define common_turn 42
#define set_turning(x) ((x)->turning=1,(x)->idling=0)
int validanim(entity*x,int a){trace[nt++]=100+a;return validmask&(1<<a);}
void mutate(void){switch(mutation){
case 1:self->direction=1-self->direction;self->modeldata.facing=2;level->facing=1;break;
case 2:self->velocity.x=9;self->velocity.z=11;self->idling=0;break;
case 3:self->turntime=17;self->modeldata.turndelay=3;self->modeldata.facing=3;level->facing=0;level->scrolldir=10;break;
case 4:self->takeaction=77;self->idling=1;break;}}
void ent_set_anim(entity*x,int a,int reset){trace[nt++]=1;trace[nt++]=a;mutate();}
entity*find_ent_here(entity*x,float a,float b,int type,int test){trace[nt++]=2;return &e;}
void execute_didhit_script(entity*a,entity*b,int c,int d,int f,int g,int h,int i,int j,int k){mutate();}
void didfind_item(entity*x){}
void common_walk_anim(entity*x){trace[nt++]=3;}
void common_backwalk_anim(entity*x){trace[nt++]=4;}
void common_up_anim(entity*x){trace[nt++]=5;}
void common_down_anim(entity*x){trace[nt++]=6;}
void common_idle_anim(entity*x){trace[nt++]=7;}
'''
    for name, macro in (('moveleft','FLAG_MOVELEFT'), ('moveright','FLAG_MOVERIGHT'),
                        ('moveup','FLAG_MOVEUP'), ('movedown','FLAG_MOVEDOWN')):
        code += f'#define {macro} {KEYS[name]}u\n'
    # Source NULL is an action pointer; this bounded stub uses zero identity.
    code += '#undef NULL\n#define NULL 0\nvoid ground(int notinair){int action=0,bkwalk=0;entity*other=0;\n'+block+'\n'
    code += 'u32 rows[][11]={'+',\n'.join('{'+','.join(str(v&0xffffffff)+'u' for v in r)+'}' for r in rows)+'};\n'
    code += r'''
int main(void){u32 i,j,*r,output[45];setmode(fileno(stdout),O_BINARY);if(sizeof(u32)!=4)return 3;
for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){r=rows[i];memset(&e,0,sizeof(e));memset(trace,0,sizeof(trace));nt=0;
pl->keys=0x80000000u;for(j=0;j<4;j++)if(r[0]&(1<<j))pl->keys|=(j==0?FLAG_MOVELEFT:j==1?FLAG_MOVERIGHT:j==2?FLAG_MOVEUP:FLAG_MOVEDOWN);
PLAYER_MAX_Z=r[1];e.running=r[2];e.direction=r[3];e.turntime=r[4]==2?48:r[4]==3?49:0;
e.modeldata.turndelay=r[4]?7:0;time=r[4]==4?0xfffffffeu:48;
validmask=r[5];e.modeldata.facing=r[6];l.facing=r[7];l.scrolldir=r[8];mutation=r[9];
e.velocity.x=7;e.velocity.z=-3;e.modeldata.speed=2.5f;e.modeldata.runspeed=4.5f;e.turning=-3;e.idling=-4;e.takeaction=99;
ground(r[10]);output[0]=e.direction;output[1]=e.running;output[2]=e.turntime;output[3]=e.turning;output[4]=e.idling;output[5]=e.takeaction;
memcpy(output+6,&e.velocity.x,4);memcpy(output+7,&e.velocity.z,4);output[8]=e.modeldata.facing;output[9]=l.facing;output[10]=l.scrolldir;output[11]=e.modeldata.turndelay;output[12]=nt;
memcpy(output+13,trace,128);fwrite(output,4,45,stdout);}return 0;}
'''
    (out/'ground.c').write_text(code)
    env = dict(os.environ, WATCOM='C:/WATCOM', INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    build = subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','ground.c','-fe=ground.exe'],cwd=out,env=env,capture_output=True,text=True)
    (out/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode: raise ValueError('SOURCE_PLAYER_GROUND_AUTHORITY_BUILD')
    actual = subprocess.check_output([str(out/'ground.exe')],cwd=out)
    expected = b''.join(simulate(r) for r in rows)
    errors = [dict(case=i,input=r,actual=actual[i*180:(i+1)*180].hex(),expected=expected[i*180:(i+1)*180].hex())
              for i,r in enumerate(rows) if actual[i*180:(i+1)*180]!=expected[i*180:(i+1)*180]]
    report = dict(schema='BYOR_4086_PLAYER_GROUND_AUTHORITY_V1',status='PASS' if actual==expected else 'FAIL',
                  engine_commit=ENGINE_COMMIT,player_think_sha256=hashlib.sha256(full.encode()).hexdigest(),
                  literal_block_sha256=hashlib.sha256(block.encode()).hexdigest(),literal_block_unmodified=True,
                  cases=len(rows),compared_bytes=len(expected),errors=errors[:8],callback_mutation_modes=5,
                  exact_service_and_query_order=True,native_bound=False,production_player_owner_bound=False,
                  motu_gameplay_proven=False,no_color_reduction=True)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'],len(rows),'literal ground movement cases'); assert actual==expected


if __name__ == '__main__': main()
