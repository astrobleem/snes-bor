"""Literal running block from pinned player_think against source policy."""
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
from source_player_run_4086 import retain, KEYS


def cases():
    for flags, running, old, mask, vx, vz in itertools.product(
            (0,1,2,3,4,5,6,7,-1,65536,0x7fffffff), (0,1,-1,65536),
            (0,1), range(16), (-2.0,0.0,2.0), (-2.0,0.0,2.0)):
        keys = 0x80000000
        for i, name in enumerate(('moveleft','moveright','moveup','movedown')):
            if mask & (1 << i): keys |= KEYS[name]
        yield dict(flags=flags,running=running,old=old,keys=keys,vx=vx,vz=vz)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
    full=extract(raw,'player_think')
    begin=full.index('    //dang long run checking logic')
    end=full.index('    if(PLAYER_MIN_Z != PLAYER_MAX_Z)',begin)
    block=full[begin:end]
    rows=list(cases())
    code=r'''
#include <stdio.h>
#include <io.h>
#include <fcntl.h>
typedef unsigned int u32;
typedef struct {int running;struct{int runupdown;}modeldata;struct{float x,z;}velocity;}entity;
typedef struct {u32 keys;}player;
entity e,*self=&e;player p,*pl=&p;int oldrunning,runx,runz,movex,movez;
float diff(float a,float b){return a>b?a-b:b-a;}
'''
    for name, enum in (('moveleft','FLAG_MOVELEFT'),('moveright','FLAG_MOVERIGHT'),
                       ('moveup','FLAG_MOVEUP'),('movedown','FLAG_MOVEDOWN')):
        code+=f'#define {enum} {KEYS[name]}u\n'
    code+='void cancel(void){\n'+block+'}\n'
    code+='u32 rows[][6]={'+',\n'.join('{'+','.join(str(v&0xffffffff)+'u'for v in
        (c['flags'],c['running'],c['old'],c['keys'],int(c['vx']),int(c['vz'])))+'}'for c in rows)+'};\n'
    code+=r'''
int main(void){unsigned i;u32 *r,v;setmode(fileno(stdout),O_BINARY);if(sizeof(u32)!=4)return 3;
for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){r=rows[i];self->modeldata.runupdown=(int)r[0];self->running=(int)r[1];
oldrunning=r[2];pl->keys=r[3];self->velocity.x=(int)r[4];self->velocity.z=(int)r[5];
cancel();v=self->running;fwrite(&v,4,1,stdout);}return 0;}
'''
    (out/'running.c').write_text(code,encoding='utf-8')
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','running.c','-fe=running.exe'],cwd=out,env=env,capture_output=True,text=True)
    (out/'build.log').write_text(b.stdout+b.stderr,encoding='utf-8')
    if b.returncode:raise ValueError('SOURCE_PLAYER_RUN_AUTHORITY_BUILD')
    actual=subprocess.check_output([str(out/'running.exe')],cwd=out)
    expected=b''.join(struct.pack('<I',retain(c['running'],c['old'],c['flags'],c['keys'],c['vx'],c['vz'])&0xffffffff)for c in rows)
    errors=[dict(case=i,input=c,actual=actual[i*4:(i+1)*4].hex(),expected=expected[i*4:(i+1)*4].hex())
            for i,c in enumerate(rows)if actual[i*4:(i+1)*4]!=expected[i*4:(i+1)*4]]
    report=dict(schema='BYOR_4086_PLAYER_RUNNING_AUTHORITY_V1',status='PASS'if actual==expected else'FAIL',
                engine_commit=ENGINE_COMMIT,player_think_sha256=hashlib.sha256(full.encode()).hexdigest(),
                literal_block_sha256=hashlib.sha256(block.encode()).hexdigest(),literal_block_unmodified=True,
                cases=len(rows),compared_bytes=len(expected),actual_sha256=hashlib.sha256(actual).hexdigest(),
                errors=errors[:10],domain='running cancellation only; velocities -2,0,2; all directional combinations; arbitrary signed flags/running retained',
                earlier_player_think_branches_bound=False,ordinary_movement_bound=False,native_bound=False,motu_gameplay_proven=False)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(report['status'],len(rows),'literal running-policy cases');assert actual==expected


if __name__=='__main__':main()
