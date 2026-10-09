"""Unchanged player_lie_check first-query short circuit in absent lane."""
import argparse,hashlib,itertools,json,os,struct,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    source=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1');body=extract(source,'player_lie_check')
    rows=list(itertools.product(range(4),(-2147483648,0,150),(0,64,0xffffffff),(0,16,0xffffffff),(0,48,0xffffffff)))
    code=r"""
#include <stdio.h>
#include <io.h>
#include <fcntl.h>
typedef unsigned int u32;
typedef struct{int playerindex,health,direction,stalltime,damagetype;struct{u32 riseattack_stall;}staydown;}entity;
entity e,*self=&e;struct{u32 keys,playkeys;}player[4];u32 time,calls,sets;
#define ANI_RISEATTACK 7
#define FLAG_ATTACK 64u
#define FLAG_MOVEUP 16u
#define FLAG_MOVELEFT 4u
#define FLAG_MOVERIGHT 8u
#define DIRECTION_LEFT 0
#define DIRECTION_RIGHT 1
int validanim(entity *e,int n){calls++;return 0;}
int set_riseattack(entity *e,int type,int reset){sets++;return 1;}
"""+body+'\n'
    code+='u32 rows[][5]={'+',\n'.join('{'+','.join(str(v&0xffffffff)+'u'for v in row)+'}'for row in rows)+'};\n'
    code+=r"""
int main(void){unsigned i;u32 result[5],*r;setmode(fileno(stdout),O_BINARY);if(sizeof(int)!=4)return 3;
for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){r=rows[i];self->playerindex=r[0];self->health=(int)r[1];player[r[0]].playkeys=r[2];player[r[0]].keys=r[3];time=r[4];
self->direction=-3;self->stalltime=-7;self->staydown.riseattack_stall=0;calls=sets=0;player_lie_check();result[0]=calls;result[1]=sets;
result[2]=(u32)self->direction;result[3]=(u32)self->stalltime;result[4]=player[r[0]].playkeys;fwrite(result,4,5,stdout);}return 0;}
"""
    (out/'lie.c').write_text(code)
    build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','lie.c','-fe=lie.exe'],cwd=out,
        env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT'),capture_output=True,text=True)
    (out/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise ValueError('SOURCE_LIE_AUTHORITY_BUILD')
    actual=subprocess.check_output([str(out/'lie.exe')],cwd=out);expected=b''.join(struct.pack('<5I',1,0,0xfffffffd,0xfffffff9,row[2])for row in rows)
    report=dict(schema='BYOR_4086_PLAYER_LIE_ABSENT_AUTHORITY_V1',status='PASS'if actual==expected else'FAIL',engine_commit=ENGINE_COMMIT,
        literal_function_sha256=hashlib.sha256(body.encode()).hexdigest(),literal_function_unmodified=True,cases=len(rows),compared_bytes=len(expected),
        actual_sha256=hashlib.sha256(actual).hexdigest(),expected_sha256=hashlib.sha256(expected).hexdigest(),validanim_instrumented_absent=True,
        present_riseattack_owner_bound=False,native_bound=False,motu_gameplay_proven=False)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'lie authority cases');assert actual==expected


if __name__=='__main__':main()
