"""Literal special/key gates, unlink and energy functions across callbacks."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_animation_energy_4086 import check
from source_player_special_4086 import player_execute, Service


def cases():
    for n in range(4096):
        yield [(-1,0,1,2,3,4)[n%6], n//6%2, n//12%2, n//24%2,
               n//48%2, n//96%2, n//192%2, n//384%2,
               (0,128,256,384)[n//8%4], (0,64)[n//32%2],
               (0,5,6,7,30)[n//4%5], (0,6,7,150)[n//16%4],
               (-3,0,6,20)[n//64%4], n//256%3, n//128%5,
               n//1024%2, n//2048%2]


def simulate(row):
    ns,cant,aj,block,nocost,cheat,linked,freeze,play,keys,mp,hp,cost,only,mutation,bomb,present=row
    trace=[]
    e=dict(cantfire=cant,playerindex=0,seal=0,mp=mp,health=hp,takeaction=99,
           attacking=0,idling=3,combostep=[1,2,3,4,5],running=-7,
           velocity=dict(x=3.5,z=-2.5),grabbing=True,stalltime=99,
           modeldata=dict(type=1,smartbomb=bomb,dofreeze=freeze,
           animation={'special':dict(energycost=dict(cost=cost,mponly=only,disable=0),numframes=present)}))
    peer=dict(takeaction=99,link=e,grabbing=e)
    e['link']=peer if linked else None
    ctx=dict(nospecial=ns,ajspecial=aj,nocost=nocost,healthcheat=cheat,smartbomber=None)
    players=[dict(playkeys=play|0x80000000,keys=keys),dict(playkeys=0x800001c0,keys=64)]
    def energy(which):
        trace.append(10+which)
        an=e['modeldata']['animation']['special']
        return check(which,an['energycost'],e['modeldata']['type'],e['seal'],e['mp'],e['health'],an['numframes'])
    def valid(role):
        trace.append(100)
        return block
    def mutate():
        if mutation==1:
            e['mp']=0;e['health']=500;e['playerindex']=1
        elif mutation==2:
            e['modeldata']['dofreeze']=1;ctx['nocost']=1
        elif mutation==3:
            e['modeldata']['animation']['special']['energycost']['cost']=2
            e['mp']=2;e['health']=3
        elif mutation==4:
            e['running']=5;e['velocity']['x']=9;e['velocity']['z']=11
    gen=player_execute(e,ctx,players,valid,energy)
    while True:
        try:
            event=next(gen);trace.append(int(event[0]));mutate()
        except StopIteration as stop:
            result=stop.value;break
    bits=lambda v:struct.unpack('<I',struct.pack('<f',v))[0]
    state=[result,e['mp'],e['health'],e['takeaction'],e['attacking'],e['idling'],
           *e['combostep'],int(peer['link'] is not None),int(peer['grabbing'] is not None),
           0 if peer['takeaction'] is None else peer['takeaction'],int(e['link'] is not None),
           int(e['grabbing'] is not None),e['running'],bits(e['velocity']['x']),bits(e['velocity']['z']),
           int(ctx['smartbomber'] is e),e['playerindex'],e['stalltime'],
           players[0]['playkeys'],players[1]['playkeys'],len(trace)]
    return struct.pack('<57I',*(v&0xffffffff for v in state+trace+[0]*(32-len(trace))))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    out=p.parse_args().output.resolve();out.mkdir(parents=True,exist_ok=True)
    def pinned(path):return subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':'+path]).decode('latin1')
    raw=pinned('engine/openbor.c');header=pinned('engine/openbor.h')
    funcs={n:extract(raw,n)for n in ('check_energy','ent_unlink','check_special','player_check_special')}
    enums='\n'.join(re.search(r'typedef enum\s*\{[^}]*\}\s*'+n+r'\s*;',header,re.S)[0]for n in ('e_cost_check','e_cost_type','e_entity_type'))
    macro=re.search(r'#define set_attacking\(e\)[^\n]*\\\s*\n[^\n]*',header)[0]
    rows=list(cases())
    code=r'''
#include <stdio.h>
#include <string.h>
#include <io.h>
#include <fcntl.h>
#define TRUE 1
#define FALSE 0
#define ANI_SPECIAL 5
#define ANI_BLOCK 6
#define FLAG_ATTACK 64u
#define FLAG_JUMP 128u
#define FLAG_SPECIAL 256u
typedef unsigned int u32;
'''+enums+'\n'+macro+r'''
typedef struct{struct{int cost,mponly,disable;}energycost;int numframes;}animation;
typedef struct entity{struct{int type,smartbomb,dofreeze;animation*animation[168];}modeldata;
int seal,mp,health,attacking,idling,combostep[5],running,playerindex;u32 stalltime;
void(*takeaction)(void);struct{float x,z;}velocity;struct entity*link,*grabbing;}entity;
typedef struct{u32 playkeys,keys;}s_player;
entity e,peer,*self=&e,*smartbomber;animation an,bl;s_player player[2];
struct{int nospecial;}lev,*level=&lev;int nocost,healthcheat,ajspecial,mutation;
u32 trace[32],nt;
void common_attack_proc(void){}void old_action(void){}
int valid(entity*x,int a){if(a==ANI_BLOCK)trace[nt++]=100;return x->modeldata.animation[a]&&x->modeldata.animation[a]->numframes;}
#define validanim(x,a) valid(x,a)
void mutate(void){switch(mutation){
case 1:self->mp=0;self->health=500;self->playerindex=1;break;
case 2:self->modeldata.dofreeze=1;nocost=1;break;
case 3:an.energycost.cost=2;self->mp=2;self->health=3;break;
case 4:self->running=5;self->velocity.x=9;self->velocity.z=11;break;}}
void set_idle(entity*x){trace[nt++]=1;mutate();}
void smart_bomb(entity*x,int bomb){trace[nt++]=2;mutate();}
void ent_set_anim(entity*x,int a,int reset){trace[nt++]=3;mutate();}
'''+funcs['check_energy']+'\n'+funcs['ent_unlink']+r'''
int energy_observed(int which,int a){trace[nt++]=10+which;return check_energy(which,a);}
#define check_energy energy_observed
'''+funcs['check_special']+'\n'+funcs['player_check_special']+'\n'
    code+='int rows[][17]={'+',\n'.join('{'+','.join(str(v)for v in row)+'}'for row in rows)+'};\n'
    code+=r'''
int main(void){u32 words[57];int i,n,ret,*r;setmode(fileno(stdout),O_BINARY);if(sizeof(u32)!=4||sizeof(float)!=4)return 3;
for(n=0;n<sizeof(rows)/sizeof(rows[0]);n++){r=rows[n];memset(&e,0,sizeof(e));memset(&peer,0,sizeof(peer));memset(trace,0,sizeof(trace));nt=0;smartbomber=NULL;
level->nospecial=r[0];e.cantfire=r[1];ajspecial=r[2];bl.numframes=r[3];nocost=r[4];healthcheat=r[5];e.link=r[6]?&peer:NULL;e.modeldata.dofreeze=r[7];
player[0].playkeys=(u32)r[8]|0x80000000u;player[0].keys=r[9];player[1].playkeys=0x800001c0u;player[1].keys=64;
e.mp=r[10];e.health=r[11];an.energycost.cost=r[12];an.energycost.mponly=r[13];an.energycost.disable=0;mutation=r[14];e.modeldata.smartbomb=r[15];an.numframes=r[16];
e.modeldata.type=1;e.modeldata.animation[5]=&an;e.modeldata.animation[6]=&bl;e.takeaction=old_action;e.idling=3;e.running=-7;e.velocity.x=3.5f;e.velocity.z=-2.5f;
e.grabbing=&peer;e.stalltime=99;peer.takeaction=old_action;peer.link=&e;peer.grabbing=&e;for(i=0;i<5;i++)e.combostep[i]=i+1;
ret=player_check_special();words[0]=ret;words[1]=e.mp;words[2]=e.health;words[3]=e.takeaction==common_attack_proc?17:99;words[4]=e.attacking;words[5]=e.idling;
for(i=0;i<5;i++)words[6+i]=e.combostep[i];words[11]=peer.link!=NULL;words[12]=peer.grabbing!=NULL;words[13]=peer.takeaction==NULL?0:99;words[14]=e.link!=NULL;words[15]=e.grabbing!=NULL;
words[16]=e.running;memcpy(words+17,&e.velocity.x,4);memcpy(words+18,&e.velocity.z,4);words[19]=smartbomber==&e;words[20]=e.playerindex;words[21]=e.stalltime;
words[22]=player[0].playkeys;words[23]=player[1].playkeys;words[24]=nt;memcpy(words+25,trace,128);fwrite(words,4,57,stdout);}return 0;}
'''
    # cantfire is part of the source relation row, not modeldata.
    code=code.replace('int seal,mp,health,attacking','int cantfire,seal,mp,health,attacking')
    (out/'special.c').write_text(code)
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','special.c','-fe=special.exe'],cwd=out,env=env,capture_output=True,text=True)
    (out/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise ValueError('SOURCE_PLAYER_SPECIAL_AUTHORITY_BUILD')
    actual=subprocess.check_output([str(out/'special.exe')],cwd=out);expected=b''.join(simulate(r)for r in rows)
    errors=[dict(case=i,input=r,actual=actual[i*228:(i+1)*228].hex(),expected=expected[i*228:(i+1)*228].hex())for i,r in enumerate(rows)if actual[i*228:(i+1)*228]!=expected[i*228:(i+1)*228]]
    report=dict(schema='BYOR_4086_PLAYER_SPECIAL_AUTHORITY_V1',status='PASS'if actual==expected else'FAIL',
                engine_commit=ENGINE_COMMIT,literal_functions_unmodified=True,function_sha256={n:hashlib.sha256(s.encode()).hexdigest()for n,s in funcs.items()},
                macro_sha256=hashlib.sha256(macro.encode()).hexdigest(),cases=len(rows),compared_bytes=len(expected),errors=errors[:8],
                callback_mutation_modes=5,exact_service_and_energy_query_order=True,services_instrumented=True,
                native_bound=False,production_player_owner_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'literal special cases');assert actual==expected


if __name__=='__main__':main()
