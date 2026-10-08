"""Compile verbatim pinned check_move, direct/no-platform branch authority."""
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
from source_check_move_4086 import check_move

PREAMBLE=r'''#include <stdio.h>
#include <string.h>
typedef struct entity entity;
struct entity {unsigned update_mark,nextmove;entity*landed_on_platform,*link;struct {float x,z;}position;float movex,movez;int grabbing,grabwalking,idling,pathblocked;int(*trymove)(float,float);};
entity ent,previous,*self=&previous;unsigned time;int freeze,calls;
int is_frozen(entity*e){calls++;return freeze;}
void check_link_move(float x,float z){}
unsigned bits(float f){unsigned v;memcpy(&v,&f,4);return v;}
float frombits(unsigned v){float f;memcpy(&f,&v,4);return f;}
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','-C',str(a.engine),'show',ENGINE_COMMIT+':engine/openbor.c'])
    function=extract(raw.decode('latin1'),'check_move');code=PREAMBLE+function+'\nint main(void){\n';rows=[];expected=[]
    bits=lambda v:struct.unpack('<I',struct.pack('<f',v))[0]
    for mark,freeze,nextmove,time,position,motion in itertools.product(
            (0,4,0x80000000,0x80000004),(0,1),(0,48,49,0xffffffff),(48,0xfffffffe,0xffffffff),
            ((80.0,220.0),(-80.0,.25),(16777216.0,-16777216.0)),((0.0,-0.0),(1.5,-.25),(-1.5,2.0),(1e-8,-1e-8))):
        c=dict(update_mark=mark,freeze=freeze,nextmove=nextmove,time=time,position=position,motion=motion);rows.append(c)
        e=dict(update_mark=mark,landed_on_platform=None,position=dict(zip(('x','z'),position)),nextmove=nextmove,movex=motion[0],movez=motion[1],trymove=None)
        calls=[]
        def query(e):calls.append(1);return bool(freeze)
        check_move(e,time,query)
        expected.append([bits(e['position']['x']),bits(e['position']['z']),bits(e['movex']),bits(e['movez']),e['nextmove'],e['update_mark'],len(calls),1])
        code+='memset(&ent,0,sizeof(ent));self=&previous;calls=0;'
        code+='ent.update_mark=%du;ent.nextmove=%du;time=%du;freeze=%d;'%(mark,nextmove,time,freeze)
        for field,value in zip(('position.x','position.z','movex','movez'),(*position,*motion)):
            code+='ent.%s=frombits(%du);'%(field,bits(value))
        code+='check_move(&ent);printf("%u,%u,%u,%u,%u,%u,%d,%d\\n",bits(ent.position.x),bits(ent.position.z),bits(ent.movex),bits(ent.movez),ent.nextmove,ent.update_mark,calls,self==&previous);\n'
    code+='return 0;}\n';(folder/'check_move.c').write_text(code)
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-bt=nt','check_move.c','-fe=check_move.exe'],cwd=folder,env=env,capture_output=True,text=True)
    (folder/'build.log').write_text(b.stdout+b.stderr)
    if b.returncode:raise RuntimeError('CHECK_MOVE_AUTHORITY_BUILD_FAILED:'+b.stdout+b.stderr)
    log=subprocess.check_output([str(folder/'check_move.exe')],cwd=folder,text=True);(folder/'authority.log').write_text(log)
    actual=[list(map(int,line.split(',')))for line in log.splitlines()]
    mismatch=[i for i,(x,y)in enumerate(zip(actual,expected))if x!=y]
    report=dict(schema='BYOR_4086_CHECK_MOVE_AUTHORITY_V1',status='PASS'if actual==expected else'FAIL',
                engine_commit=ENGINE_COMMIT,source_function_sha256=hashlib.sha256(function.encode('latin1')).hexdigest(),
                source_function_unmodified=True,cases=len(rows),inputs=rows,actual=actual,expected=expected,mismatch_cases=mismatch,
                frozen_service_instrumented=True,platform_branch_proven=False,trymove_branch_proven=False,
                gravity_proven=False,native_position_integration_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'check_move cases',mismatch[:3]);assert actual==expected


if __name__=='__main__':main()
