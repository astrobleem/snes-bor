"""Compile verbatim pinned arrow_move with observed wall/animation services."""
import argparse
from copy import deepcopy
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import struct
import subprocess
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_arrow_move_4086 import arrow_move

PREAMBLE = r'''#include <stdio.h>
#include <string.h>
typedef struct entity entity;
typedef struct {int subtype,hostile,noflip,nomove,subject_to_wall,subject_to_platform,subject_to_hole,subject_to_gravity,no_adjust_base;float speed;} model;
struct entity {model modeldata;int direction,autokill,ptype,attacking,health,projectile,damage_on_landing;struct {float x,z,y;}position;struct {float x,z;}velocity;void(*takeaction)(void);};
typedef struct {float height;} wall_t;
typedef struct {wall_t walls[1];} stage;
entity ent,*self=&ent;stage scene,*level;int hit,fall,wall_calls,anim_calls;
#define SUBTYPE_CHASE 11
#define DIRECTION_LEFT 0
#define DIRECTION_RIGHT 1
#define ANI_UP 1
#define ANI_DOWN 2
#define ANI_WALK 3
#define ANI_IDLE 4
#define ANI_FALL 5
#define ATK_NORMAL 0
entity*homing_find_target(int hostile){return NULL;}
float diff(float a,float b){return a>b?a-b:b-a;}
int validanim(entity*e,int anim){anim_calls++;return fall;}
void common_up_anim(entity*e){}void common_down_anim(entity*e){}void common_walk_anim(entity*e){}
void ent_set_anim(entity*e,int a,int b){}void common_fall(void){}
int checkwall(float x,float z){wall_calls++;return hit;}
float randf(float value){return 0;}
void toss(entity*e,float v){}void set_fall(entity*a,int b,int c,entity*d,int e,int f,int g,int h,int i,int j){}
unsigned bits(float f){unsigned v;memcpy(&v,&f,4);return v;}
float frombits(unsigned v){float f;memcpy(&f,&v,4);return f;}
'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--engine', type=Path, default=Path('E:/gh/openbor-bcec'))
    a = p.parse_args(); folder = a.output.resolve(); folder.mkdir(parents=True, exist_ok=True)
    raw = subprocess.check_output(['git', '-C', str(a.engine), 'show', ENGINE_COMMIT+':engine/openbor.c'])
    header = subprocess.check_output(['git', '-C', str(a.engine), 'show', ENGINE_COMMIT+':engine/openbor.h']).decode('latin1')
    # Assert enum values from pinned authority, not the external working tree.
    subtype = re.search(r'SUBTYPE_NONE\s*,(.*?)SUBTYPE_CHASE', header, re.S)
    assert subtype and len(re.findall(r'\bSUBTYPE_\w+\s*,', 'SUBTYPE_NONE,'+subtype[1])) == 11
    assert re.search(r'typedef enum\s*\{\s*(?:/\*.*?\*/\s*)?DIRECTION_LEFT\s*,\s*DIRECTION_RIGHT\s*\}\s*e_direction', header, re.S)
    function = extract(raw.decode('latin1'), 'arrow_move')
    rows = []; expected = []; code = PREAMBLE+function+'\nint main(void){\n'
    for direction, speed, level_present, subject, hit, altitude, height in itertools.product(
            (0, 1, 2, -1), (0.0, -0.0, .5, 2.0, -1.5), (0, 1), (0, 1, -1),
            (-1, 0), (34.0, 100.0), (34.0, 100.0)):
        c = dict(direction=direction, speed=speed, level_present=level_present,
                 subject_to_wall=subject, hit=hit, altitude=altitude, height=height)
        e = dict(modeldata=dict(subtype=0, speed=speed, subject_to_wall=subject),
                 direction=direction, velocity=dict(x=3.25, z=-4.5),
                 position=dict(x=12.0, z=220.0, y=altitude), autokill=0x80000002, ptype=0x40000004)
        calls = []
        def query(x, z):
            calls.append((x, z)); return height if hit >= 0 else None
        result = arrow_move(e, level_present=bool(level_present), checkwall=query, valid_fall=False)
        blocked = bool(level_present and subject and hit >= 0 and altitude < height)
        expected.append([result, *[struct.unpack('<I', struct.pack('<f', e['velocity'][axis]))[0] for axis in ('x', 'z')], e['autokill'], len(calls), int(blocked), 99, 7, 1])
        rows.append(c)
        code += ('memset(&ent,0,sizeof(ent));ent.direction=%d;ent.modeldata.speed=frombits(%du);'
                 'ent.modeldata.subject_to_wall=%d;level=%s;hit=%d;ent.position.y=%sf;'
                 'scene.walls[0].height=%sf;ent.velocity.x=3.25f;ent.velocity.z=-4.5f;'
                 'ent.autokill=0x80000002u;ent.ptype=0x40000004u;ent.health=99;ent.attacking=7;ent.projectile=1;'
                 'wall_calls=anim_calls=fall=0;'
                 'printf("%%d,%%u,%%u,%%u,%%d,%%d,%%d,%%d,%%d\\n",arrow_move(),bits(ent.velocity.x),bits(ent.velocity.z),(unsigned)ent.autokill,wall_calls,anim_calls,ent.health,ent.attacking,ent.projectile);\n') % (
                     direction, struct.unpack('<I', struct.pack('<f', speed))[0], subject, '&scene' if level_present else 'NULL', hit, repr(altitude), repr(height))
    # Separate call from printf: C argument evaluation order must not decide the observation.
    code = code.replace('printf("%d,%u,%u,%u,%d,%d,%d,%d,%d\\n",arrow_move(),', '{int result=arrow_move();printf("%d,%u,%u,%u,%d,%d,%d,%d,%d\\n",result,')
    code = code.replace('ent.projectile);\n', 'ent.projectile);}\n')+'return 0;}\n'
    (folder/'arrow_move.c').write_text(code)
    env = dict(os.environ, WATCOM='C:/WATCOM', INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    b = subprocess.run(['C:/WATCOM/BINNT/wcl386.exe', '-q', '-za99', '-bt=nt', 'arrow_move.c', '-fe=arrow_move.exe'], cwd=folder, env=env, capture_output=True, text=True)
    (folder/'build.log').write_text(b.stdout+b.stderr)
    if b.returncode: raise RuntimeError('ARROW_AUTHORITY_BUILD_FAILED:'+b.stdout+b.stderr)
    log = subprocess.check_output([str(folder/'arrow_move.exe')], cwd=folder, text=True)
    (folder/'authority.log').write_text(log)
    actual = [list(map(int, line.split(','))) for line in log.splitlines()]
    mismatch = [i for i, (x, y) in enumerate(zip(actual, expected)) if x != y]
    r = dict(schema='BYOR_4086_ARROW_MOVE_AUTHORITY_V1', status='PASS' if actual == expected else 'FAIL',
             engine_commit=ENGINE_COMMIT, source_function_sha256=hashlib.sha256(function.encode('latin1')).hexdigest(),
             source_function_unmodified=True, cases=len(rows), inputs=rows, actual=actual, expected=expected,
             mismatch_cases=mismatch, wall_and_animation_services_instrumented=True,
             admitted_subtype='NON_CHASE', valid_fall=False, position_integration_proven=False,
             native_projectile_bound=False, motu_gameplay_proven=False, no_color_reduction=True)
    (folder/'report.json').write_text(json.dumps(r, indent=2)+'\n')
    print(r['status'], len(rows), 'ordinary arrow cases', 'mismatches', mismatch[:3])
    assert actual == expected


if __name__ == '__main__': main()
