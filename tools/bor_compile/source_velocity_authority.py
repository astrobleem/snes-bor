"""Measure literal pinned update_ents velocity statements against both policies."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import struct
import subprocess
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_velocity_4086 import source, native


def bits(v):
    return struct.unpack('<I', struct.pack('<f', v))[0]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--engine', type=Path, default=Path('E:/gh/openbor-bcec'))
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); folder = a.output.resolve(); folder.mkdir(parents=True, exist_ok=True)
    raw = subprocess.check_output(['git', 'show', ENGINE_COMMIT + ':engine/openbor.c'], cwd=a.engine).decode('latin1')
    body = extract(raw, 'update_ents')
    statements = '\n'.join(line.strip() for line in body.splitlines() if 'self->movex +=' in line or 'self->movez +=' in line)
    assert len(statements.splitlines()) == 2
    rng = random.Random(408610)
    rows = []
    for speed in (0, 65536, -65536, 32768, 78643, 52429, 131072):
        for v in (0, 1, -1, 65536, -65536, 52429, -52429, 327680, -327680):
            for acc in (0, 1, -1, 16*65536, -16*65536):
                rows.append([acc, -acc, v, -v, speed])
    rows += [[rng.randint(-256*65536, 256*65536) for _ in range(4)] +
             [rng.randint(-2*65536, 2*65536)] for _ in range(1024)]
    literals = ['{' + ','.join(format(v/65536, '.17g') for v in r) + '}' for r in rows]
    code = r'''#include <stdio.h>
#include <string.h>
#define GAME_SPEED 200
typedef struct {float x,z;} vector;
typedef struct {float movex,movez;vector velocity;float speedmul;} entity;
entity ent,*self=&ent;
void accumulate(void){
''' + statements + r'''
}
float cases[][5]={''' + ','.join(literals) + r'''};
unsigned bits(float f){unsigned v;memcpy(&v,&f,4);return v;}
int main(void){unsigned i;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
self->movex=cases[i][0];self->movez=cases[i][1];self->velocity.x=cases[i][2];self->velocity.z=cases[i][3];self->speedmul=cases[i][4];
accumulate();printf("%u,%u\n",bits(self->movex),bits(self->movez));}return 0;}
'''
    (folder/'velocity.c').write_text(code)
    env = dict(os.environ, WATCOM='C:/WATCOM', INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    build = subprocess.run(['C:/WATCOM/BINNT/wcl386.exe', '-q', '-bt=nt', 'velocity.c', '-fe=velocity.exe'], cwd=folder, env=env, capture_output=True, text=True)
    (folder/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode: raise ValueError('SOURCE_VELOCITY_AUTHORITY_BUILD')
    log = subprocess.check_output([str(folder/'velocity.exe')], cwd=folder, text=True)
    (folder/'authority.log').write_text(log)
    actual = [list(map(int, line.split(','))) for line in log.splitlines()]
    expected = [[bits(v) for v in source(*(n/65536 for n in r))] for r in rows]
    failures = [i for i, (c, e) in enumerate(zip(actual, expected)) if c != e]
    errors = []
    compiled = []
    for r, c in zip(rows, actual):
        value = native(*r); compiled.append(value)
        errors.extend(abs(q/65536 - struct.unpack('<f', struct.pack('<I', b))[0]) for q, b in zip(value, c))
    guards = []
    for r in ([0x7fffffff,0,65536,0,65536],[-0x80000000,0,-65536,0,65536], [0,0,0x80000000,0,65536]):
        try: native(*r); guards.append(False)
        except ValueError: guards.append(True)
    ok = len(actual)==len(rows) and not failures and all(guards)
    report = dict(schema='BYOR_4086_VELOCITY_AUTHORITY_V1', status='PASS' if ok else 'FAIL', engine_commit=ENGINE_COMMIT,
        statements_sha256=hashlib.sha256(statements.encode()).hexdigest(), cases=len(rows), inputs=rows, source_bits=actual,
        compiled_q16=compiled, failures=failures[:20], guard_results=guards, maximum_absolute_compat_error=max(errors),
        numeric_policy='ACCEPTED_COMPAT_Q16_16: signed full 64-bit product divided by 2^17 toward zero, checked signed accumulator addition',
        authority_compiler='OpenWatcom wcl386 x87 excess precision; literal pinned statements, final binary32 storage',
        binary32_intermediate_policy_measured_separately=True,
        strict_binary32_maximum_absolute_compat_error=max(abs(q/65536-f) for r in rows for q,f in zip(native(*r), source(*(n/65536 for n in r), excess_precision=False))),
        native_backend_bound=False, collision_bound=False, motu_gameplay_proven=False, no_color_reduction=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'],len(rows),'velocity cases; maximum Q16 compatibility error',max(errors))
    if not ok: raise SystemExit(1)


if __name__ == '__main__': main()
