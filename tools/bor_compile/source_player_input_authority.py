"""Execute literal pinned inputrefresh/match_combo against the input owner IR."""
import argparse
import hashlib
import itertools
import json
import os
import re
import struct
import subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_script_input import authority
from source_player_input_4086 import empty_player,refresh,match_combo,pack_player


def cases():
    for step,present,direction,time,new in itertools.product(
            range(27),(0,1),(0,1,0xffffffff,65536),
            (0,1,0xfffffff0,0xffffffff),(0,4,8,12,64,0x80000001)):
        p=empty_player()
        p.update(combostep=step,present=present,direction=direction,
                 movetime=(time+(step%3)-1)&0xffffffff,
                 keys=0xcc,playkeys=0xa5,token=0x12345678)
        p['combokey']=[1<<((i+step)%32)for i in range(27)]
        p['inputtime']=[0x10101010^(i*97)for i in range(27)]
        result,both,bothnew=refresh([p,*[empty_player()for _ in range(3)]],
                                   [(new,new),(0,0),(0,0),(0,0)],time)
        length=(0,1,2,27)[step%4]
        sequence=[result[0]['combokey'][(result[0]['combostep']-length+i)%27]for i in range(length)]
        if sequence and new==64:sequence[0]=0
        if sequence and new==8:sequence[-1]^=0xffffffff
        yield dict(player=p,time=time,new=new,sequence=sequence,
                   expected=pack_player(result[0])+struct.pack('<III',both,bothnew,match_combo(sequence,result[0])))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    source_repo='E:/gh/openbor-bcec'
    def pinned(path):return subprocess.check_output(['git','show',ENGINE_COMMIT+':'+path],cwd=source_repo)
    header=pinned('engine/openbor.h')
    if hashlib.sha256(header).hexdigest()!=authority()['files']['engine/openbor.h']:
        raise ValueError('PLAYER_INPUT_HEADER_AUTHORITY')
    constants={n:int(re.search(rb'#define\s+'+n.encode()+rb'\s+(\d+)',header).group(1))for n in ('MAX_PLAYERS','MAX_SPECIAL_INPUTS','GAME_SPEED')}
    if constants!=dict(MAX_PLAYERS=4,MAX_SPECIAL_INPUTS=27,GAME_SPEED=200):raise ValueError('PLAYER_INPUT_CONSTANT_AUTHORITY')
    text=pinned('engine/openbor.c').decode('latin1')
    functions={n:extract(text,n)for n in ('inputrefresh','match_combo')}
    rows=list(cases())
    prefix='''#include <stdio.h>
#include <string.h>
#include <io.h>
#include <fcntl.h>
typedef unsigned long u32;
#define MAX_PLAYERS 4
#define MAX_SPECIAL_INPUTS 27
#define GAME_SPEED 200
#define FLAG_MOVELEFT 4
#define FLAG_MOVERIGHT 8
#define FLAG_FORWARD 0x40000000UL
#define FLAG_BACKWARD 0x80000000UL
typedef struct entity {u32 movetime;int direction;} entity;
typedef struct s_player {entity *ent;u32 keys,newkeys,playkeys,releasekeys;int combostep;u32 combokey[27],inputtime[27];} s_player;
typedef struct controls {u32 keyflags,newkeyflags;} controls;
s_player player[4];controls pads[4],*playercontrolpointers[4];entity actors[4];
u32 time,bothkeys,bothnewkeys;
void control_update(controls **p,int n){}
'''
    initializer=[]
    for r in rows:
        p=r['player'];values=[p['combostep'],p['present'],p['direction'],p['movetime'],r['time'],r['new'],len(r['sequence']),*r['sequence'],*[0]*(27-len(r['sequence']))]
        initializer.append('{'+','.join('0x%08xUL'%v for v in values)+'}')
    code=prefix+'\n'.join(functions.values())+'\nu32 cases[][34]={'+',\n'.join(initializer)+'''};
int main(void){unsigned n,i,j;u32 words[67];
 setmode(fileno(stdout),O_BINARY);
 if(sizeof(u32)!=4||sizeof(int)!=4)return 3;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  memset(player,0,sizeof(player));memset(pads,0,sizeof(pads));memset(actors,0,sizeof(actors));
  for(i=0;i<4;i++)playercontrolpointers[i]=pads+i;
  player[0].combostep=cases[n][0];player[0].ent=cases[n][1]?actors:NULL;
  actors[0].direction=cases[n][2];actors[0].movetime=cases[n][3];time=cases[n][4];
  player[0].keys=0xcc;player[0].playkeys=0xa5;pads[0].keyflags=pads[0].newkeyflags=cases[n][5];
  for(i=0;i<27;i++){player[0].combokey[i]=1UL<<((i+cases[n][0])%32);player[0].inputtime[i]=0x10101010UL^(i*97);}
  inputrefresh();j=0;
  for(i=0;i<27;i++)words[j++]=player[0].inputtime[i];
  for(i=0;i<27;i++)words[j++]=player[0].combokey[i];
  words[j++]=player[0].keys;words[j++]=player[0].newkeys;words[j++]=player[0].playkeys;words[j++]=player[0].releasekeys;words[j++]=player[0].combostep;
  words[j++]=actors[0].movetime;words[j++]=cases[n][1];words[j++]=cases[n][2];words[j++]=0x12345678;words[j++]=0;
  words[j++]=bothkeys;words[j++]=bothnewkeys;words[j++]=match_combo((int*)(cases[n]+7),player,cases[n][6]);
  if(j!=67)return 4;fwrite(words,4,67,stdout);
 }return 0;}
'''
    (out/'player_input.c').write_text(code,encoding='utf-8')
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','player_input.c','-fe=player_input.exe'],cwd=out,env=env,capture_output=True,text=True)
    (out/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise ValueError('PLAYER_INPUT_AUTHORITY_BUILD')
    actual=subprocess.check_output([str(out/'player_input.exe')],cwd=out)
    expected=b''.join(r['expected']for r in rows)
    ok=actual==expected
    if not ok:
        (out/'mismatch.json').write_text(json.dumps(dict(actual_bytes=len(actual),expected_bytes=len(expected),first_mismatch=next((i for i,(x,y)in enumerate(zip(actual,expected))if x!=y),None)),indent=2)+'\n')
    report=dict(schema='BYOR_4086_PLAYER_INPUT_HISTORY_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,constants=constants,cases=len(rows),full_record_bytes_compared=len(expected),literal_function_sha256={n:hashlib.sha256(f.encode('latin1')).hexdigest()for n,f in functions.items()},header_sha256=hashlib.sha256(header).hexdigest(),actual_sha256=hashlib.sha256(actual).hexdigest(),expected_sha256=hashlib.sha256(expected).hexdigest(),controller_update_instrumented=True,player_think_bound=False,check_combo_energy_and_cost_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'],len(rows),'pinned full history/unsigned direction/match cases;',len(expected),'bytes compared')
    if not ok:raise ValueError('PLAYER_INPUT_AUTHORITY_MISMATCH')


if __name__=='__main__':main()
