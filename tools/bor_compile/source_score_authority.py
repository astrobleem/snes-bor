"""Pinned addscore scalar behavior and ordered sound/script observations."""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import subprocess
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','-C',str(a.engine),'show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1');body=extract(raw,'addscore')
    rows=[dict(index=i,score=s,add=add,sample=sample,script=script,lifescore=50000)for i,s,add,sample,script in itertools.product((-1,0,3,4,7),(0,1,49999,50000,50001,999999990),(0,1,-1,70,2147483647,-2147483648),(-1,22),(0,1))]
    rows.extend(dict(index=2147483647,score=score,add=add,sample=-1,script=0,lifescore=life)for life,score,add in itertools.product((1,65535,65536,2147483648,4294967295),(0,1,65535,50000,999999990),(0,1,70)))
    code=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define LONG long
#define VT_INTEGER 1
typedef struct{long lVal;int type;}ScriptVariant;
typedef struct{int initialized;}Script;
struct{unsigned score;int lives;}player[4];Script score_script[4];unsigned lifescore=50000;int SAMPLE_1UP;struct{int effectvol;}savedata;
int sounds,scripts,sets,clears,types,script_add,script_seen_lives;unsigned script_seen_score;
void sound_play_sample(int sample,int loop,int l,int r,int speed){if(sample!=SAMPLE_1UP||loop||speed!=100)exit(7);sounds++;}
int Script_IsInitialized(Script *s){return s->initialized;}
void ScriptVariant_Init(ScriptVariant *v){memset(v,0,sizeof(*v));}
void ScriptVariant_ChangeType(ScriptVariant *v,int type){v->type=type;types++;}
void Script_Set_Local_Variant(Script *s,char *name,ScriptVariant *v){if(strcmp(name,"score"))exit(8);sets++;if(v->type==VT_INTEGER)script_add=v->lVal;}
void Script_Execute(Script *s){int i=s-score_script;scripts++;script_seen_score=player[i].score;script_seen_lives=player[i].lives;}
void ScriptVariant_Clear(ScriptVariant *v){v->type=0;clears++;}
'''+body+'\nstruct Case{int index;unsigned score;int add,sample,script;unsigned lifescore;}cases[]={\n'
    code+=',\n'.join('{'+','.join('(-2147483647-1)'if v==-2147483648 else str(v)for v in r.values())+'}'for r in rows)+'\n};\n'
    code+=r'''
int main(void){unsigned i;int j;struct Case *c;if(sizeof(int)!=4||sizeof(unsigned)!=4||sizeof(long)!=4)return 2;
for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
c=cases+i;for(j=0;j<4;j++){player[j].score=c->score;player[j].lives=5;score_script[j].initialized=c->script;}
SAMPLE_1UP=c->sample;lifescore=c->lifescore;sounds=scripts=sets=clears=types=0;script_add=-777;script_seen_score=0;script_seen_lives=-1;
addscore(c->index,c->add);
printf("SCORE|%u|%u,%d,%d,%d,%d,%d,%d,%d,%u,%d|",i,player[c->index<0?0:c->index&3].score,player[c->index<0?0:c->index&3].lives,sounds,scripts,sets,clears,types,script_add,script_seen_score,script_seen_lives);
for(j=0;j<4;j++)printf("%s%u,%d",j?",":"",player[j].score,player[j].lives);puts("");
}return 0;}
'''
    (folder/'score.c').write_text(code)
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','score.c','-fe=score.exe'],cwd=folder,env=env,capture_output=True,text=True);(folder/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise ValueError('SCORE_AUTHORITY_C_BUILD:'+build.stdout+build.stderr)
    log=subprocess.check_output([str(folder/'score.exe')],cwd=folder,text=True);results=[]
    for line in log.splitlines():
        if not line.startswith('SCORE|'):continue
        _,index,values,players=line.split('|');r=rows[int(index)];actual=list(map(int,values.split(',')));actual_players=list(map(int,players.split(',')))
        score,lives=r['score'],5;gain=0
        if r['index']>=0:
            score=min((score+r['add'])&0xffffffff,999999999)
            nextup=((r['score']//r['lifescore'])+1)*r['lifescore']
            if score>nextup:gain=(score-nextup+r['lifescore']-1)//r['lifescore']
            lives+=gain
        script=r['script']if r['index']>=0 else 0
        expected=[score,lives,gain if r['sample']>=0 else 0,script,script*2,script,script,r['add']if script else -777,score if script else 0,lives if script else -1]
        expected_players=[v for _ in range(4)for v in(r['score'],5)]
        if r['index']>=0:expected_players[(r['index']&3)*2:(r['index']&3)*2+2]=[score,lives]
        results.append(dict(case=r,actual=actual,expected=expected,players_actual=actual_players,players_expected=expected_players,passed=actual==expected and actual_players==expected_players))
    ok=len(results)==len(rows)and all(r['passed']for r in results)
    report=dict(schema='BYOR_4086_SCORE_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,function_sha256=hashlib.sha256(body.encode('latin1')).hexdigest(),cases=len(rows),results=results,
                source_policy='negative player index returns; index&3; unsigned score addition wraps then caps999999999; next1up from old score; strict greater-than threshold; score stored after 1up loop and before script',
                sound_service_instrumented=True,score_script_service_instrumented=True,native_score_backend_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'pinned source score cases')
    if not ok:raise SystemExit(1)


if __name__=='__main__':main()
