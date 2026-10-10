"""Literal source death callbacks with instrumented player_die/kill children."""
import argparse,hashlib,itertools,json,os,struct,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_death_actions_4086 import player_blink,suicide

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
 raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=a.engine).decode('latin1');bodies={n:extract(raw,n)for n in ('player_blink','suicide')}
 code='''#include <stdio.h>
#include <string.h>
#include <io.h>
#include <fcntl.h>
typedef unsigned int u32;
typedef struct {int blink,boss;u32 stalltime;} entity;
entity e,*self=&e;u32 time;int level_completed,events;
void player_die(void){events|=1;}
void kill(entity *p){if(p!=self)events|=8;events|=2;}
'''+ '\n'.join(bodies.values())+'''
int main(void){u32 v[6],w[3];setmode(fileno(stdin),O_BINARY);setmode(fileno(stdout),O_BINARY);if(sizeof(int)!=4)return 3;while(fread(v,4,6,stdin)==6){time=v[1];e.stalltime=v[2];e.blink=v[3];e.boss=v[4];level_completed=v[5];events=0;if(v[0])suicide();else player_blink();w[0]=e.blink;w[1]=level_completed;w[2]=events;fwrite(w,4,3,stdout);}return 0;}
'''
 (out/'death.c').write_text(code);b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','death.c','-fe=death.exe'],cwd=out,env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT'),capture_output=True,text=True);(out/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 cases=list(itertools.product((0,1),(0,48,65535,65536,0xffffff00,0xffffffff),(0,47,48,49,65535,65536,0xffffffff),(-1,0,3),(0,1,2,-1),(0,1,2)))
 expected=[]
 for callback,time,stall,blink,boss,completed in cases:
  e=dict(blink=blink,boss=boss,stall=stall)
  if callback:completed,events=suicide(e,time,completed)
  else:events=player_blink(e,time)
  expected.append(struct.pack('<3I',e['blink']&0xffffffff,completed&0xffffffff,(1 if 'PLAYER_DIE'in events else 0)|(2 if 'KILL'in events else 0)))
 actual=subprocess.check_output([str(out/'death.exe')],input=b''.join(struct.pack('<6I',*(v&0xffffffff for v in c))for c in cases));wanted=b''.join(expected);ok=actual==wanted
 (out/'actual.bin').write_bytes(actual);(out/'expected.bin').write_bytes(wanted)
 r=dict(schema='BYOR_DEATH_ACTIONS_SOURCE_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,function_sha256={n:hashlib.sha256(body.encode('latin1')).hexdigest()for n,body in bodies.items()},cases=len(cases),actual_sha256=hashlib.sha256(actual).hexdigest(),expected_sha256=hashlib.sha256(wanted).hexdigest(),child_operations_instrumented=True,player_die_body_bound=False,kill_body_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
 (out/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],len(cases),'literal death callback cases');assert ok
if __name__=='__main__':main()
