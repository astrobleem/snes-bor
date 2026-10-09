"""Unchanged pre-attack button section, including mandatory special helper."""
import argparse,hashlib,itertools,json,os,struct,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_player_button_precheck_4086 import execute
from source_player_run_4086 import KEYS

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    source=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1');full=extract(source,'player_think');body=full[full.index('    if(!ajspecial'):full.index('    if((pl->releasekeys')]
    names=('ajspecial','play','held','notinair','success','block')
    rows=[dict(zip(names,r))for r in itertools.product((0,1,-1,65536),(0,128,256,384,0x80000180),(0,64,256,320),(0,1),(0,1),(0,1))if not(r[3]and r[5])]
    code=''.join('#define FLAG_'+n.upper()+' '+str(KEYS[n])+'u\n'for n in('jump','attack','special','moveleft','moveright'))+r"""
#include <stdio.h>
#include <string.h>
#include <io.h>
#include <fcntl.h>
#define ANI_ATTACKBOTH 1
#define ANI_CHARGE 2
#define ANI_SPECIAL2 3
#define ANI_BLOCK 4
#define DIRECTION_LEFT 0
typedef unsigned int u32;
struct entity{void(*takeaction)(void);int direction,combostep[5],stalltime;struct{float x,z;}velocity;}e,*self=&e;
struct player{u32 keys,playkeys;}player;
int ajspecial,notinair,success,block,trace,count,continuation;
int validanim(void *e,int role){trace=trace*8+role;count++;return role==4&&block;}
void common_attack_proc(void){}void common_charge(void){}void common_block(void){}void set_attacking(void *e){}void set_charging(void *e){}void set_blocking(void *e){}void ent_set_anim(void *e,int role,int reset){}
int check_costmove(int a,int b,int c){return 0;}
int player_check_special(void){trace=trace*8+5;count++;return success;}
void probe(void){struct player *pl=&player;
"""+body+'continuation=1;\nendthinkcheck:return;}\n'
    code+='u32 rows[][6]={'+',\n'.join('{'+','.join(str(c[k]&0xffffffff)+'u'for k in names)+'}'for c in rows)+'};\n'
    code+=r"""
int main(void){unsigned i;u32 result[5],*r;struct entity before;setmode(fileno(stdout),O_BINARY);if(sizeof(int)!=4||sizeof(void*)!=4)return 3;
for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){r=rows[i];memset(&e,0,sizeof(e));e.stalltime=-7;e.direction=-3;before=e;ajspecial=(int)r[0];player.playkeys=r[1];player.keys=r[2];notinair=r[3];success=r[4];block=r[5];trace=count=continuation=0;probe();result[0]=trace;result[1]=count;result[2]=continuation;result[3]=player.playkeys;result[4]=memcmp(&e,&before,sizeof(e))!=0;fwrite(result,4,5,stdout);}return 0;}
"""
    (out/'buttons.c').write_text(code);build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','buttons.c','-fe=buttons.exe'],cwd=out,env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT'),capture_output=True,text=True);(out/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise ValueError('SOURCE_PLAYER_BUTTON_BUILD')
    actual=subprocess.check_output([str(out/'buttons.exe')],cwd=out);expected=b''
    for c in rows:
        pl=dict(playkeys=c['play'],keys=c['held']);gen=execute(c,pl,c['notinair']);trace=count=0;reply=None
        while True:
            try:s=gen.send(reply)
            except StopIteration as done:result=done.value;break
            trace=trace*8+int(s);count+=1;reply=c['success']if s==5 else c['block']if s==4 else 0
        expected+=struct.pack('<5I',trace,count,result=='CONTINUE',pl['playkeys'],0)
    report=dict(schema='BYOR_4086_PLAYER_BUTTON_AUTHORITY_V1',status='PASS'if actual==expected else'FAIL',engine_commit=ENGINE_COMMIT,player_think_sha256=hashlib.sha256(full.encode()).hexdigest(),literal_body_sha256=hashlib.sha256(body.encode()).hexdigest(),literal_body_unmodified=True,cases=len(rows),compared_bytes=len(expected),actual_sha256=hashlib.sha256(actual).hexdigest(),expected_sha256=hashlib.sha256(expected).hexdigest(),animation_queries_and_special_callback_instrumented=True,present_grounded_block_owner_bound=False,full_player_think_bound=False,motu_gameplay_proven=False)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'button authority cases');assert actual==expected
if __name__=='__main__':main()
