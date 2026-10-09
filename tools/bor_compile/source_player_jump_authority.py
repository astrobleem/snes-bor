"""Unchanged complete player_jump_check in the derived zero-control domain."""
import argparse,hashlib,itertools,json,os,struct,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_player_run_4086 import KEYS


def cases():
    for port,play,held,nospecial,running,vx,available in itertools.product(range(4),(0,64,256,320),(0,16,32,48),
            (-1,0,2,3),(0,-3),(-1,0,1),(0,1)):
        yield dict(port=port,play=play|0x80010000,held=held,nospecial=nospecial,running=running,vx=vx,available=available)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    source=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1');body=extract(source,'player_jump_check')
    rows=list(cases())
    code=r"""
#include <stdio.h>
#include <io.h>
#include <fcntl.h>
typedef unsigned int u32;
typedef struct{struct{int cost;}energycost;}animation;
typedef struct entity entity;
struct entity{int playerindex,animating,animnum;struct{int id;}jump;int mp,health,attacking,running,direction;
struct{float x,y,z;}velocity;struct{animation *animation[7];int jumpmovex,jumpmovez;float speed;}modeldata;};
typedef struct{u32 playkeys,keys;}s_player;s_player player[4];entity e,*self=&e;
struct{int nospecial;}l,*level=&l;int noaircancel=0,healthcheat=0,available;u32 trace,sets;
#define ANI_JUMPSPECIAL 0
#define ANI_JUMPCANT 1
#define ANI_JUMPATTACK2 2
#define ANI_JUMPATTACK3 3
#define ANI_RUNJUMPATTACK 4
#define ANI_JUMPFORWARD 5
#define ANI_JUMPATTACK 6
#define COST_CHECK_MP 1
#define COST_CHECK_HP 0
#define DIRECTION_LEFT 0
#define DIRECTION_RIGHT 1
int validanim(entity *ent,int role){trace=trace*8+role+1;return role==6&&available;}
int check_energy(int which,int role){return 0;}
void ent_set_anim(entity *ent,int role,int reset){sets++;ent->animnum=role;}
"""
    code+=''.join('#define FLAG_'+n.upper()+' '+str(KEYS[n])+'u\n'for n in ('special','attack','moveleft','moveright','moveup','movedown'))+body+'\n'
    code+='u32 rows[][7]={'+',\n'.join('{'+','.join(str(c[k]&0xffffffff)+'u'for k in ('port','play','held','nospecial','running','vx','available'))+'}'for c in rows)+'};\n'
    code+=r"""
int main(void){unsigned i;u32 *r,result[7];setmode(fileno(stdout),O_BINARY);if(sizeof(int)!=4||sizeof(void*)!=4)return 3;
for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){r=rows[i];self->playerindex=r[0];player[r[0]].playkeys=r[1];player[r[0]].keys=r[2];level->nospecial=(int)r[3];
self->running=(int)r[4];self->velocity.x=(float)(int)r[5];self->velocity.z=-1;self->modeldata.jumpmovex=self->modeldata.jumpmovez=0;
self->animnum=99;self->attacking=-5;available=r[6];trace=sets=0;player_jump_check();result[0]=trace;result[1]=sets;
result[2]=self->attacking;result[3]=player[r[0]].playkeys;result[4]=self->animnum;result[5]=(int)self->velocity.x;result[6]=(int)self->velocity.z;
fwrite(result,4,7,stdout);}return 0;}
"""
    (out/'jump.c').write_text(code)
    build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','jump.c','-fe=jump.exe'],cwd=out,
        env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT'),capture_output=True,text=True)
    (out/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise ValueError('SOURCE_JUMP_AUTHORITY_BUILD')
    actual=subprocess.check_output([str(out/'jump.exe')],cwd=out);expected=b''
    for c in rows:
        trace=0;special=c['nospecial']in(0,3)and c['play']&KEYS['special'];attack=bool(not special and c['play']&KEYS['attack'])
        if special:trace=1
        elif attack:
            if c['held']&KEYS['movedown']:trace=trace*8+3
            if c['held']&KEYS['moveup']:trace=trace*8+4
            if c['running']:trace=trace*8+5
            if c['vx']:trace=trace*8+6
            trace=trace*8+7
        sets=bool(attack and c['available'])
        expected+=struct.pack('<7I',*(v&0xffffffff for v in (trace,sets,1 if attack else -5,c['play']&~KEYS['attack']if attack else c['play'],6 if sets else 99,c['vx'],-1)))
    errors=[i for i in range(len(rows))if actual[i*28:(i+1)*28]!=expected[i*28:(i+1)*28]]
    report=dict(schema='BYOR_4086_PLAYER_JUMP_ZERO_CONTROL_AUTHORITY_V1',status='PASS'if actual==expected else'FAIL',engine_commit=ENGINE_COMMIT,
        literal_function_sha256=hashlib.sha256(body.encode()).hexdigest(),literal_function_unmodified=True,cases=len(rows),compared_bytes=len(expected),
        actual_sha256=hashlib.sha256(actual).hexdigest(),expected_sha256=hashlib.sha256(expected).hexdigest(),errors=errors[:8],
        domain='noaircancel=0; zero jumpmovex/z; absent alternate air moves; default attack optional; velocities -1/0/1',
        callbacks_instrumented=True,native_bound=False,motu_gameplay_proven=False)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'jump authority cases');assert actual==expected


if __name__=='__main__':main()
