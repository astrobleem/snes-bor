"""Compare attack-chain continuation against literal pinned 4086 C."""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import random
import struct
import subprocess
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_attack_chain_4086 import execute


def cases():
    rng = random.Random(408619092)
    for n in range(4096):
        chain = [rng.randrange(8) for _ in range(12)]
        chain[0] = 1 + n % 7
        length = max(i + 1 for i, c in enumerate(chain) if c)
        if n % 31 == 0:
            length = 0
        yield dict(chain=chain, length=length, style=n % 8, type=(1, 2, 3, 65536)[n % 4],
                   step=n % 11, deadline=(0, 49, 50, 51, 0xffffffff)[n % 5],
                   time=(0, 50, 0xfffffffc)[n % 3], delay=(0, 100, 0xffffffff)[n % 3],
                   valid=rng.randrange(128), targets=rng.randrange(128), callback=n % 5)


def expected(c):
    e = dict(modeldata=dict(atchain=c['chain'], chainlength=c['length'],
                           combostyle=c['style'], type=c['type']),
             combostep=[c['step'], 7, 8, 9, 10], combotime=c['deadline'],
             attacking=55, idling=66, takeaction=0)
    context = dict(time=c['time'], combodelay=c['delay'], attacks=list(range(8, 15)))
    trace = []
    def valid(a):
        trace.append(100 + a)
        return c['valid'] & (1 << (a - 8))
    def target(a, _):
        trace.append(200 + a)
        return c['targets'] & (1 << (a - 8))
    animation = -1
    gen = execute(e, context, valid, target)
    try:
        service, entity, animation, reset = next(gen)
        assert entity is e and reset == 1
        trace.append(300 + animation)
        assert e['takeaction'] == 17 and e['attacking'] == 1 and e['idling'] == 0
        callback(e, context, c['callback'])
        next(gen)
        raise AssertionError('UNEXPECTED_SECOND_SERVICE')
    except StopIteration as done:
        result = done.value
    h = 2166136261
    for op in trace:
        h = ((h ^ op) * 16777619) & 0xffffffff
    return struct.pack('<10I', result, e['combostep'][0], e['combotime'],
                       e['takeaction'], e['attacking'], e['idling'], animation & 0xffffffff,
                       h, context['time'], e['modeldata']['combostyle'])


def callback(e, context, mode):
    if mode == 1:
        e['combostep'][0] = 12
        e['modeldata']['chainlength'] = 1
    elif mode == 2:
        e['modeldata']['combostyle'] ^= 2
        context['time'] = (context['time'] + 17) & 0xffffffff
    elif mode == 3:
        e['combostep'][0] = 0
        e['attacking'] = 0
        e['idling'] = 1
    elif mode == 4:
        e['modeldata']['combostyle'] = 2
        context['combodelay'] = 37


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    raw = subprocess.check_output(['git', '-C', 'E:/gh/openbor-bcec', 'show',
                                   ENGINE_COMMIT + ':engine/openbor.c']).decode('latin1')
    header = subprocess.check_output(['git', '-C', 'E:/gh/openbor-bcec', 'show',
                                      ENGINE_COMMIT + ':engine/openbor.h']).decode('latin1')
    function = extract(raw, 'perform_atchain')
    begin = header.index('#define set_attacking(')
    end = header.index('\n\n', begin)
    macro = header[begin:end]
    rows = list(cases())
    code = r'''
#include <stdio.h>
#include <string.h>
#include <io.h>
#include <fcntl.h>
#define TYPE_PLAYER 1
typedef unsigned int u32;
typedef struct entity {struct {int chainlength,atchain[12],combostyle,type;} modeldata;
int combostep[5];u32 combotime;void(*takeaction)(void);int attacking,idling;} entity;
entity ent,*self=&ent;u32 time,combodelay,h;int validmask,targetmask,mode,animation;
int animattacks[7]={8,9,10,11,12,13,14};
void common_attack_proc(void){}
void mark(int n){h=(h^(u32)n)*16777619u;}
int validanim(entity*e,int n){mark(100+n);return validmask&(1<<(n-8));}
entity*normal_find_target(int n,int z){mark(200+n);return targetmask&(1<<(n-8))?self:NULL;}
void ent_set_anim(entity*e,int n,int reset){animation=n;mark(300+n);
if(reset!=1||e->takeaction!=common_attack_proc||e->attacking!=1||e->idling!=0){puts("BAD_ENTRY");return;}
if(mode==1){e->combostep[0]=12;e->modeldata.chainlength=1;}
if(mode==2){e->modeldata.combostyle^=2;time+=17;}
if(mode==3){e->combostep[0]=0;e->attacking=0;e->idling=1;}
if(mode==4){e->modeldata.combostyle=2;combodelay=37;}}
''' + macro + '\n' + function
    code += '\nu32 inputs[][23]={' + ',\n'.join(
        '{' + ','.join(str(v) + 'u' for v in [*c['chain'], *[c[k] for k in
        ('length', 'style', 'type', 'step', 'deadline', 'time', 'delay', 'valid', 'targets', 'callback')], 0]) + '}'
        for c in rows) + '};\n'
    code += r'''
int main(void){unsigned i,j;u32 *c,row[10];int result;setmode(fileno(stdout),O_BINARY);
if(sizeof(u32)!=4)return 3;
for(i=0;i<sizeof(inputs)/sizeof(inputs[0]);i++){c=inputs[i];memset(&ent,0,sizeof(ent));
for(j=0;j<12;j++)ent.modeldata.atchain[j]=c[j];
ent.modeldata.chainlength=c[12];ent.modeldata.combostyle=c[13];ent.modeldata.type=c[14];
ent.combostep[0]=c[15];ent.combotime=c[16];time=c[17];combodelay=c[18];
validmask=c[19];targetmask=c[20];mode=c[21];animation=-1;
ent.attacking=55;ent.idling=66;h=2166136261u;result=perform_atchain();
row[0]=result;row[1]=ent.combostep[0];row[2]=ent.combotime;
row[3]=ent.takeaction==common_attack_proc?17:0;row[4]=ent.attacking;row[5]=ent.idling;
row[6]=animation;row[7]=h;row[8]=time;row[9]=ent.modeldata.combostyle;
fwrite(row,4,10,stdout);}return 0;}
'''
    (out / 'chain.c').write_text(code, encoding='utf-8')
    env = dict(os.environ, WATCOM='C:/WATCOM', INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    b = subprocess.run(['C:/WATCOM/BINNT/wcl386.exe', '-q', '-bt=nt', 'chain.c',
                        '-fe=chain.exe'], cwd=out, env=env, capture_output=True, text=True)
    (out / 'build.log').write_text(b.stdout + b.stderr, encoding='utf-8')
    if b.returncode:
        raise ValueError('SOURCE_ATTACK_CHAIN_AUTHORITY_BUILD')
    actual = subprocess.check_output([str(out / 'chain.exe')], cwd=out)
    wanted = b''.join(expected(deepcopy(c)) for c in rows)
    mismatches = [dict(case=i, input=c, actual=actual[i*40:(i+1)*40].hex(),
                       expected=wanted[i*40:(i+1)*40].hex()) for i, c in enumerate(rows)
                  if actual[i*40:(i+1)*40] != wanted[i*40:(i+1)*40]]
    report = dict(schema='BYOR_4086_ATTACK_CHAIN_AUTHORITY_V1', status='PASS' if actual == wanted else 'FAIL',
                  engine_commit=ENGINE_COMMIT, function_sha256=hashlib.sha256(function.encode()).hexdigest(),
                  macro_sha256=hashlib.sha256(macro.encode()).hexdigest(), literal_function_unmodified=True,
                  literal_set_attacking_macro=True, cases=len(rows), compared_state_bytes=len(wanted),
                  callback_mutation_modes=5, ordered_query_trace_exact=actual == wanted,
                  actual_sha256=hashlib.sha256(actual).hexdigest(), mismatches=mismatches[:10],
                  target_search_instrumented=True, animation_callback_instrumented=True,
                  native_bound=False, full_player_think_bound=False, motu_gameplay_proven=False)
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(report['status'], len(rows), 'literal attack-chain cases')
    assert actual == wanted


if __name__ == '__main__':
    main()
