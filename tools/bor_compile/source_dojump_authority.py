"""Compare complete unchanged 4086 dojump with ordered service mutations."""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import struct
import subprocess

from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_dojump_4086 import execute, Service
from source_model_core_4086 import binary32


def bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    source = subprocess.check_output(['git', '-C', 'E:/gh/openbor-bcec', 'show',
                                     ENGINE_COMMIT + ':engine/openbor.c']).decode('latin1')
    header = subprocess.check_output(['git', '-C', 'E:/gh/openbor-bcec', 'show',
                                     ENGINE_COMMIT + ':engine/openbor.h']).decode('latin1')
    body = extract(source, 'dojump')
    header_lines = header.splitlines()
    macro_start = next(i for i, line in enumerate(header_lines) if line.startswith('#define set_jumping('))
    macro_lines = [header_lines[macro_start]]
    while macro_lines[-1].rstrip().endswith('\\'):
        macro_lines.append(header_lines[macro_start + len(macro_lines)])
    macro = '\n'.join(macro_lines)
    names = ('sample', 'dust', 'spawn_ok', 'direction', 'mutations', 'argument')
    rows = [dict(zip(names, values)) for values in itertools.product(
        (-1, 0, 26), (-1, 0, 9), (0, 1), (0, 1, -3, 65536), range(16), range(4))]
    code = r'''
#include <stdio.h>
#include <string.h>
#include <io.h>
#include <fcntl.h>
typedef unsigned int u32;
typedef struct {float x,y,z;} axis;
typedef struct entity {void(*takeaction)(void);axis position,velocity;int direction,jumping,idling,autokill;float base;struct {struct {int jump_start;} dust;} modeldata;} entity;
entity e,d,*self=&e;
int SAMPLE_JUMP,spawn_ok,mutations;struct {int effectvol;} savedata;
u32 h;int sound_count,spawn_count,onspawn_count,toss_count,frame_count;
u32 bits(float f){u32 v;memcpy(&v,&f,4);return v;}
void mark(u32 v){h=(h^v)*16777619u;}
void common_jump(void){}void old_action(void){}
#define DIRECTION_LEFT 0
void sound_play_sample(int sample,int priority,int left,int right,int speed){mark(1);mark(sample);mark(priority);mark(left);mark(right);mark(speed);sound_count++;if(mutations&1){e.position.x=11;e.position.y=12;e.position.z=13;e.direction=1;e.modeldata.dust.jump_start=7;}}
entity *spawn(float x,float z,float y,int direction,void *name,int model,void *map){mark(2);mark(bits(x));mark(bits(z));mark(bits(y));mark(direction);mark(model);spawn_count++;if(mutations&2){e.position.y=21;e.direction=0;}return spawn_ok?&d:NULL;}
void execute_onspawn_script(entity *dust){mark(3);mark(bits(dust->base));mark(dust->autokill);onspawn_count++;if(mutations&4){e.direction=1;e.jumping=-3;e.idling=-5;e.takeaction=old_action;}}
void toss(entity *e,float v){mark(4);mark(bits(v));mark(e->jumping);mark(e->idling);toss_count++;if(mutations&8){e->direction=0;e->jumping=9;e->idling=8;e->takeaction=old_action;}}
void ent_set_anim(entity *e,int id,int reset){mark(5);mark(id);mark(reset);mark(bits(e->velocity.x));mark(bits(e->velocity.z));frame_count++;e->direction=1;e->velocity.x=31;e->velocity.z=32;}
'''+macro+'\n'+body+'\n'
    code += 'int rows[][6]={' + ',\n'.join('{' + ','.join(str(c[n]) for n in names) + '}' for c in rows) + '};\n'
    code += r'''
int main(void){unsigned i;int *r;u32 v[17];float y,x,z;setmode(fileno(stdout),O_BINARY);if(sizeof(u32)!=4||sizeof(void*)!=4)return 3;
for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){r=rows[i];memset(&e,0,sizeof(e));memset(&d,0,sizeof(d));e.takeaction=old_action;e.position.x=1;e.position.y=2;e.position.z=3;e.velocity.x=-2;e.velocity.z=-3;e.direction=r[3];e.jumping=-7;e.idling=6;d.base=-1;d.autokill=-2;e.modeldata.dust.jump_start=r[1];SAMPLE_JUMP=r[0];spawn_ok=r[2];mutations=r[4];savedata.effectvol=73;h=2166136261u;sound_count=spawn_count=onspawn_count=toss_count=frame_count=0;
y=r[5]==0?4.5f:r[5]==1?0.0f:r[5]==2?-2.25f:0.7f;x=r[5]==0?1.2f:r[5]==1?0.0f:r[5]==2?-3.5f:0.7f;z=r[5]==0?0.0f:r[5]==1?0.0f:r[5]==2?2.5f:-0.7f;
{u32 negative_zero=0x80000000u;if(r[5]==1){memcpy(&y,&negative_zero,4);memcpy(&x,&negative_zero,4);}if(r[5]==0)memcpy(&z,&negative_zero,4);}
dojump(y,x,z,99);
v[0]=h;v[1]=e.takeaction==common_jump;v[2]=e.jumping;v[3]=e.idling;v[4]=e.direction;v[5]=bits(e.velocity.x);v[6]=bits(e.velocity.z);v[7]=bits(d.base);v[8]=d.autokill;v[9]=sound_count;v[10]=spawn_count;v[11]=onspawn_count;v[12]=toss_count;v[13]=frame_count;v[14]=bits(e.position.x);v[15]=bits(e.position.y);v[16]=bits(e.position.z);fwrite(v,4,17,stdout);}return 0;}
'''
    (out / 'dojump.c').write_text(code)
    build = subprocess.run(['C:/WATCOM/BINNT/wcl386.exe', '-q', '-bt=nt', 'dojump.c', '-fe=dojump.exe'], cwd=out,
                           env=dict(os.environ, WATCOM='C:/WATCOM', INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT'), capture_output=True, text=True)
    (out / 'build.log').write_text(build.stdout + build.stderr)
    if build.returncode:
        raise ValueError('DOJUMP_SOURCE_BUILD')
    actual = subprocess.check_output([str(out / 'dojump.exe')], cwd=out)
    expected = bytearray()
    for c in rows:
        entity = dict(takeaction='OLD', jumping=-7, idling=6, direction=c['direction'],
                      position=dict(x=1, y=2, z=3), velocity=dict(x=-2, z=-3),
                      modeldata=dict(dust_jump_start=c['dust']))
        dust = dict(base=-1, autokill=-2)
        arguments = ((4.5, 1.2, -0.0), (-0.0, -0.0, 0.0), (-2.25, -3.5, 2.5), (.7, .7, -.7))[c['argument']]
        gen = execute(entity, *arguments, 99, c['sample'], 73)
        trace = []
        counts = [0] * 5
        result = None
        while True:
            try:
                request = gen.send(result)
            except StopIteration:
                break
            result = None
            service = request[0]
            counts[service - 1] += 1
            trace.append(int(service))
            if service == Service.SOUND:
                trace.extend(request[1:])
                if c['mutations'] & 1:
                    entity['position'] = dict(x=11, y=12, z=13)
                    entity['direction'] = 1
                    entity['modeldata']['dust_jump_start'] = 7
            elif service == Service.SPAWN:
                trace.extend([bits(v) for v in request[1:4]] + [request[4], request[6]])
                if c['mutations'] & 2:
                    entity['position']['y'] = 21
                    entity['direction'] = 0
                result = dust if c['spawn_ok'] else None
            elif service == Service.ONSPAWN:
                trace.extend((bits(dust['base']), dust['autokill']))
                if c['mutations'] & 4:
                    entity.update(direction=1, jumping=-3, idling=-5, takeaction='OLD')
            elif service == Service.TOSS:
                trace.extend((bits(request[1]), entity['jumping'], entity['idling']))
                if c['mutations'] & 8:
                    entity.update(direction=0, jumping=9, idling=8, takeaction='OLD')
            elif service == Service.SET_ANIMATION:
                trace.extend((*request[1:], bits(entity['velocity']['x']), bits(entity['velocity']['z'])))
                entity['direction'] = 1
                entity['velocity'].update(x=31, z=32)
        h = 2166136261
        for value in trace:
            h = ((h ^ (int(value) & 0xffffffff)) * 16777619) & 0xffffffff
        values = (h, entity['takeaction'] == 'COMMON_JUMP', entity['jumping'], entity['idling'], entity['direction'],
                  bits(entity['velocity']['x']), bits(entity['velocity']['z']), bits(dust['base']), dust['autokill'],
                  *counts, *(bits(entity['position'][k]) for k in ('x', 'y', 'z')))
        expected.extend(struct.pack('<17I', *(int(v) & 0xffffffff for v in values)))
    report = dict(schema='BYOR_4086_DOJUMP_AUTHORITY_V1', status='PASS' if actual == expected else 'FAIL',
                  engine_commit=ENGINE_COMMIT, literal_body_sha256=hashlib.sha256(body.encode()).hexdigest(),
                  literal_set_jumping_sha256=hashlib.sha256(macro.encode()).hexdigest(), literal_body_unmodified=True,
                  cases=len(rows), compared_bytes=len(expected), actual_sha256=hashlib.sha256(actual).hexdigest(),
                  expected_sha256=hashlib.sha256(expected).hexdigest(), external_services_instrumented=True,
                  callback_mutations_instrumented=True, native_bound=False, physical_audio_bound=False,
                  motu_gameplay_proven=False)
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(report['status'], len(rows), 'complete dojump authority cases')
    if actual != expected:
        first = next(i for i, pair in enumerate(zip(actual, expected)) if pair[0] != pair[1])
        raise AssertionError(('DOJUMP_AUTHORITY_MISMATCH', first // 68, first % 68, rows[first // 68]))


if __name__ == '__main__':
    main()
