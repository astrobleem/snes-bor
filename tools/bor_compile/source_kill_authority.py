"""Verbatim pinned kill/unlink with instrumented callback/clear/damage services."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_kill_4086 import Entity,Owner,Service,kill

def fixtures():
    return [dict(summon=s,completed=l,damage=d,mode=m,roles=r) for s in (0,1,2) for l in (0,1) for d in (0,1) for m in (0,1,2) for r in (0,1)]

def reference(c):
    es=[Entity(i) for i in range(6)];v=es[1]
    for e in es:e.health=100+e.identity
    v.type=32;es[0].type=1;es[5].type=128
    v.owner=es[0];v.parent=es[0];es[0].subentity=v;v.summonkill=c['summon'];v.subentity=es[2]
    v.link=es[4];v.grabbing=es[4];es[4].link=v;es[4].grabbing=v;v.weapent=es[3]
    for e in es[2:]:
        e.parent=v;e.owner=v;e.opponent=v;e.binding=v;e.landed=v;e.hithead=v;e.lasthit=v;e.takedamage=bool(c['damage'])
    if c['mode']==1:v.exists=False
    o=Owner(es,[v,v,es[3],v] if c['roles'] else [None]*4,es[5],v if c['roles'] else None,v if c['roles'] else None,sum(e.exists for e in es),bool(c['completed']))
    trace=[]
    for service,e,arg in kill(o,v):
        trace.extend((int(service),e.identity,arg if arg is not None else -1))
        if service==Service.ONKILL and c['mode']==2 and e is v:e.exists=False
        if service==Service.CLEAR_SCRIPTS:e.cleared+=1
        if service==Service.DAMAGE_MINION:e.exists=False;e.health=0;o.ent_count-=1
    def token(e):return -1 if e is None else e.identity
    state=[o.ent_count,token(o.self_entity),token(o.smartbomber),token(o.textbox),*[token(p) for p in o.players]]
    for e in es:state.extend([int(e.exists),e.health,e.cantfire,e.cleared,*[token(getattr(e,f)) for f in ('parent','subentity','owner','opponent','binding','landed','hithead','lasthit','link','grabbing','weapent')]])
    return dict(trace=trace,state=state)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=a.engine).decode('latin1')
    functions='\n\n'.join(extract(raw,n) for n in ('ent_unlink','kill'));rows=fixtures()
    source=r'''#include <stdio.h>
#include <string.h>
#define TYPE_SHOT 32
#define TYPE_PLAYER 1
#define TYPE_TEXTBOX 128
typedef struct {int attack_force,attack_type;struct {float x,z,y;} dropv;} s_attack;
typedef struct entity {int exists,health,cantfire,cleared;struct {int type,summonkill;} modeldata;struct entity *owner,*parent,*subentity,*opponent,*landed_on_platform,*hithead,*lasthit,*link,*grabbing,*weapent;struct {struct entity *ent;} binding;void *scripts;void (*takedamage)(struct entity *,s_attack *);} entity;
typedef struct {int summon,completed,damage,mode,roles;} fixture;
entity pool[6],*ent_list[6],*self,*smartbomber,*textbox;struct {entity *ent;} player[4];
int ent_count,ent_max=6,max_attack_types=17,level_completed,trace[512],nt;fixture *test;
s_attack emptyattack;struct {float x,z,y;} default_model_dropv;
int token(entity *e){return e?(int)(e-pool):-1;}
void event(int n,entity *e,int arg){trace[nt++]=n;trace[nt++]=token(e);trace[nt++]=arg;}
void execute_onkill_script(entity *e){event(1,e,-1);if(test->mode==2&&e==pool+1)e->exists=0;}
void clear_all_scripts(void *s,int method){entity *e=(entity *)s;event(2,e,method);e->cleared++;}
void damage(entity *e,s_attack *a){event(3,e,a->attack_force);e->exists=0;e->health=0;ent_count--;}
void kill(entity *e);
''' + functions + '\nfixture cases[]={'+','.join('{'+','.join(str(c[k]) for k in ('summon','completed','damage','mode','roles'))+'}' for c in rows)+r'''};
int main(void){unsigned n;int i,j;entity *v;
if(sizeof(void *)!=4||sizeof(int)!=4)return 2;
for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
test=cases+n;memset(pool,0,sizeof(pool));nt=0;v=pool+1;self=pool+5;level_completed=test->completed;
for(i=0;i<6;i++){ent_list[i]=pool+i;pool[i].exists=1;pool[i].health=100+i;pool[i].cantfire=1;pool[i].scripts=pool+i;}
v->modeldata.type=TYPE_SHOT;pool[0].modeldata.type=TYPE_PLAYER;pool[5].modeldata.type=TYPE_TEXTBOX;
v->owner=v->parent=pool;pool[0].subentity=v;v->modeldata.summonkill=test->summon;v->subentity=pool+2;
v->link=v->grabbing=pool+4;pool[4].link=pool[4].grabbing=v;v->weapent=pool+3;
for(i=2;i<6;i++){entity *e=pool+i;e->parent=e->owner=e->opponent=e->binding.ent=e->landed_on_platform=e->hithead=e->lasthit=v;e->takedamage=test->damage?damage:NULL;}
if(test->mode==1)v->exists=0;ent_count=6-(test->mode==1);
player[0].ent=player[1].ent=player[3].ent=test->roles?v:NULL;player[2].ent=test->roles?pool+3:NULL;
smartbomber=textbox=test->roles?v:NULL;kill(v);
printf("KILLAUTH|%u|",n);for(j=0;j<nt;j++)printf("%s%d",j?",":"",trace[j]);
printf("|%d,%d,%d,%d",ent_count,token(self),token(smartbomber),token(textbox));for(i=0;i<4;i++)printf(",%d",token(player[i].ent));
for(i=0;i<6;i++){entity *e=pool+i;printf(",%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d",e->exists,e->health,e->cantfire,e->cleared,token(e->parent),token(e->subentity),token(e->owner),token(e->opponent),token(e->binding.ent),token(e->landed_on_platform),token(e->hithead),token(e->lasthit),token(e->link),token(e->grabbing),token(e->weapent));}puts("");
}return 0;}
'''
    (folder/'kill.c').write_text(source)
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    proc=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','kill.c','-fe=kill.exe'],cwd=folder,env=env,capture_output=True,text=True);(folder/'build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('KILL_AUTHORITY_C_BUILD')
    log=subprocess.check_output([str(folder/'kill.exe')],cwd=folder,text=True);(folder/'authority.log').write_text(log)
    results=[]
    for line in log.splitlines():
        if not line.startswith('KILLAUTH|'):continue
        _,index,trace,state=line.split('|');i=int(index);actual=dict(trace=list(map(int,trace.split(','))),state=list(map(int,state.split(','))));expected=reference(rows[i]);results.append(dict(case=rows[i],actual=actual,expected=expected,pass_case=actual==expected))
    ok=len(results)==len(rows) and all(r['pass_case'] for r in results)
    report=dict(schema='BYOR_4086_KILL_POLICY_AUTHORITY_V1',status='PASS' if ok else 'FAIL',engine_commit=ENGINE_COMMIT,functions_sha256=hashlib.sha256(functions.encode()).hexdigest(),cases=len(rows),results=results,callback_script_clear_and_damage_bodies_instrumented=True,native_retirement_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(results),'kill/unlink C cases')
    if not ok:raise SystemExit(1)

if __name__=='__main__':main()
