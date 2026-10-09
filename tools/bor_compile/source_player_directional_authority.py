"""Unchanged source directional controller section compared with real ring logic."""
import argparse,hashlib,itertools,json,os,struct,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_player_directional_4086 import execute
from source_player_input_4086 import empty_player
from source_player_run_4086 import KEYS

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    source=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
    full=extract(source,'player_think');body=full[full.index('    if(pl->playkeys & FLAG_MOVEUP)'):full.index('    if(!ajspecial')]
    matcher=extract(source,'match_combo')
    names=('notinair','runupdown','direction','play','step','pattern','runavailable')
    rows=[dict(zip(names,r))for r in itertools.product((0,1),(0,1,2,-1),(-3,0,1,2),(0,4,8,12,16,32,48,60),(0,1,26),(0,1,2),(0,1))]
    defs=''.join('#define FLAG_'+n.upper()+' '+str(KEYS[n])+'u\n'for n in ('moveleft','moveright','moveup','movedown'))
    code=defs+r"""
#include <stdio.h>
#include <string.h>
#include <io.h>
#include <fcntl.h>
#define MAX_SPECIAL_INPUTS 27
#define DIRECTION_RIGHT 1
#define DIRECTION_LEFT 0
#define ANI_RUN 1
#define ANI_ATTACKUP 2
#define ANI_ATTACKDOWN 3
#define ANI_DODGE 4
#define ANI_ATTACKFORWARD 5
typedef unsigned int u32;
typedef struct{u32 combokey[27],inputtime[27],playkeys;int combostep;}s_player;
struct entity{int running,direction,combostep[5],idling;void(*takeaction)(void);struct{float x,z;}velocity;struct{int runupdown;float speed;}modeldata;}e,*self=&e;
s_player player;int available,trace,count,notinair;
int validanim(void *e,int role){trace=trace*8+role;count++;return role==ANI_RUN&&available;}
void common_attack_proc(void){}void common_dodge(void){}void set_attacking(void *e){}void ent_set_anim(void *e,int role,int reset){}
"""+matcher+'\nvoid probe(void){s_player *pl=&player;int t;static int uu[]={FLAG_MOVEUP,FLAG_MOVEUP},dd[]={FLAG_MOVEDOWN,FLAG_MOVEDOWN},rr[]={FLAG_MOVERIGHT,FLAG_MOVERIGHT},ll[]={FLAG_MOVELEFT,FLAG_MOVELEFT};\n'+body+'endthinkcheck:return;}\n'
    code+='int rows[][7]={'+',\n'.join('{'+','.join(str(c[k])for k in names)+'}'for c in rows)+'};\n'
    code+=r"""
int main(void){unsigned i,j;int *r;u32 result[5];setmode(fileno(stdout),O_BINARY);if(sizeof(int)!=4||sizeof(void*)!=4)return 3;
for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){r=rows[i];memset(&e,0,sizeof(e));memset(&player,0,sizeof(player));notinair=r[0];e.modeldata.runupdown=r[1];e.direction=r[2];player.playkeys=0x80010000u|r[3];player.combostep=r[4];available=r[6];e.running=-7;
for(j=0;j<27;j++)player.combokey[j]=r[5]==0?60u:r[5]==1?(j%2?4u:8u):(j%3?16u:32u);
trace=count=0;probe();result[0]=trace;result[1]=count;result[2]=player.playkeys;result[3]=player.combostep;result[4]=e.running;fwrite(result,4,5,stdout);}return 0;}
"""
    (out/'directional.c').write_text(code)
    build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','directional.c','-fe=directional.exe'],cwd=out,env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT'),capture_output=True,text=True)
    (out/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise ValueError('SOURCE_PLAYER_DIRECTIONAL_BUILD')
    actual=subprocess.check_output([str(out/'directional.exe')],cwd=out);expected=b''
    for c in rows:
        e=dict(runupdown=c['runupdown'],direction=c['direction'],running=-7);pl=empty_player();pl.update(playkeys=0x80010000|c['play'],combostep=c['step']);pl['combokey']=[60 if c['pattern']==0 else(4 if j%2 else 8)if c['pattern']==1 else(16 if j%3 else 32)for j in range(27)]
        gen=execute(e,pl,c['notinair']);trace=count=0;reply=None
        while True:
            try:s=gen.send(reply)
            except StopIteration:break
            trace=trace*8+int(s);count+=1;reply=s==1 and c['runavailable']
        expected+=struct.pack('<5I',trace,count,pl['playkeys'],pl['combostep'],e['running']&0xffffffff)
    report=dict(schema='BYOR_4086_PLAYER_DIRECTIONAL_AUTHORITY_V1',status='PASS'if actual==expected else'FAIL',engine_commit=ENGINE_COMMIT,player_think_sha256=hashlib.sha256(full.encode()).hexdigest(),literal_body_sha256=hashlib.sha256(body.encode()).hexdigest(),literal_match_combo_sha256=hashlib.sha256(matcher.encode()).hexdigest(),literal_body_unmodified=True,literal_matcher_unmodified=True,cases=len(rows),compared_bytes=len(expected),actual_sha256=hashlib.sha256(actual).hexdigest(),expected_sha256=hashlib.sha256(expected).hexdigest(),animation_queries_instrumented=True,native_bound=False,full_player_think_bound=False,motu_gameplay_proven=False)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'directional authority cases');assert actual==expected
if __name__=='__main__':main()
