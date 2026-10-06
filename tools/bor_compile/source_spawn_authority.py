"""Verbatim pinned spawn constructor, with external services instrumented."""
import argparse,hashlib,json,os,subprocess,itertools
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_spawn_4086 import spawn,Service

def fixtures():
    return [dict(mode=m,resolve=r,type=t,nohit=n,saved=s,time=time) for m,r,t,n,s,time in itertools.product(range(6),range(4),(0,1,128,129),(0,1),(0,1),(0,0xffffffff))]

def reference(c):
    model=dict(priority=2,health=150,mp=7,knockdowncount=3,lifespan=300,type=c['type'],hostile=7,candamage=11,name='model')
    es=[dict(exists=int(c['mode']!=0 or i!=0),modeldata=dict(priority=-1 if c['mode']==3 else 4),sortid=100+i,defense=200+i,offense_factors=300+i,varlist=400+i,scripts=500+i,waypoints=600+i,stale=77) for i in range(3 if c['mode']==3 else 2)]
    if c['mode']==3:es[2]['exists']=0
    o=dict(entities=es,models=[model],find_model=lambda name:model,count=sum(e['exists'] for e in es),maximum=1,override=2 if c['mode']==3 else 99,plainmethod=dict(flag=5,other=9),time=c['time'],level=dict(nohit=c['nohit']),saved_mode=c['saved'],spawnplayer=3,textbox=None,name_limit=16)
    trace=[];g=spawn(o,10,20,30,2,'model' if c['resolve']==1 else None,-1 if c['resolve'] in (1,3) else 0,model if c['resolve']==2 else None)
    reply=None
    while True:
        try:service,e,arg=g.send(reply)
        except StopIteration as end:result=end.value;break
        trace.append(int(service));reply=None
        if service==Service.ALLOCATE:
            reply=c['mode'] in (4,5)
            if c['mode']==5:es.append(dict(exists=0,modeldata=dict(priority=4),sortid=102,defense=202,offense_factors=302,varlist=402,scripts=502,waypoints=602,stale=77))
        elif service==Service.KILL:e['exists']=0;o['count']-=1
    idx=next((i for i,e in enumerate(es) if e is result),-1)
    e=result or {}
    vals=[idx,o['count'],o['maximum'],next((i for i,v in enumerate(es) if v is o['textbox']),-1)]
    vals.extend(e.get(f,0) for f in ('exists','sortid','defense','offense_factors','varlist','scripts','timestamp','health','mp','knockdowncount','x','z','a','direction','nextthink','nextmove','speedmul','lifespan','playerindex','stale','waypoints'))
    vals.extend((e.get('modeldata',{}).get('hostile',0),e.get('modeldata',{}).get('candamage',0),e.get('drawmethod',{}).get('flag',0),e.get('drawmethod',{}).get('other',0),int(e.get('model') is model),int(e.get('defaultmodel') is model)))
    return dict(trace=trace,state=vals)

PREAMBLE=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define TYPE_PLAYER 1
#define TYPE_TEXTBOX 128
#define MAX_NAME_LEN 16
typedef int Varlist;typedef int s_defense;typedef int s_scripts;
typedef struct {int flag,other;} Draw;
typedef struct {int priority,health,mp,knockdowncount,lifespan,type,hostile,candamage;char name[16];s_defense *defense;float *offense_factors;s_scripts *scripts;} s_model;
typedef struct entity {int exists,sortid; s_defense *defense;float *offense_factors;Varlist *varlist;s_scripts *scripts;void *waypoints;Draw drawmethod;s_model modeldata,*model,*defaultmodel;unsigned timestamp,nextthink,nextmove;int health,mp,knockdowncount,direction,playerindex,stale;struct {float x,z,y;} position;float speedmul;int lifespancountdown;char name[16];} entity;
typedef struct {int nohit;} Level;
entity pool[3],*ent_list[3],*textbox;s_model model,*selected;
struct {s_model *model;} model_cache[1];struct {int mode;} savedata;
Level lev,*level;int ent_count,ent_max,ent_list_size,spawnoverride,currentspawnplayer,mode;
unsigned time;Draw plainmethod;int trace[64],nt;int dfs[3],vars[3],scripts[3],mdfs,mscripts;float ofs[3],mofs;
void event(int n){trace[nt++]=n;}
int alloc_ents(void){event(1);if(mode==5){ent_list_size=3;return 1;}return mode==4;}
s_model *findmodel(char *name){return selected;}
void kill(entity *e){event(2);e->exists=0;ent_count--;}
void Varlist_Cleanup(Varlist *v){event(3);}
void clear_all_scripts(s_scripts *s,int method){event(5);}
void free_waypoints(void *p){event(6);}
void copy_all_scripts(s_scripts *s,s_scripts *d,int method){event(7);}
void ent_set_colourmap(entity *e,int n){event(8);}
void ent_default_init(entity *e){event(9);}
void *copy_factors(void *d,const void *s,unsigned n){if(d==pool[0].defense||d==pool[1].defense||d==pool[2].defense)event(4);return memcpy(d,s,n);}
#define memcpy copy_factors
#define free free_waypoints
int max_attack_types=1;
'''

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=a.engine).decode('latin1');function=extract(raw,'spawn');rows=fixtures()
    data=',\n'.join('{'+','.join(str(c[f])+'u' for f in ('mode','resolve','type','nohit','saved','time'))+'}' for c in rows)
    source=PREAMBLE+function+ '\n#undef memcpy\n#undef free\n' + 'unsigned cases[][6]={'+data+'};\n'+r'''
int main(void){unsigned n,*c;int i,j,id;entity *e;
if(sizeof(void*)!=4||sizeof(unsigned)!=4)return 2;
for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
c=cases[n];mode=c[0];memset(pool,0,sizeof(pool));memset(&model,0,sizeof(model));
model.priority=2;model.health=150;model.mp=7;model.knockdowncount=3;model.lifespan=300;model.type=c[2];model.hostile=7;model.candamage=11;strcpy(model.name,"model");model.defense=&mdfs;model.offense_factors=&mofs;model.scripts=&mscripts;selected=&model;model_cache[0].model=&model;
ent_count=0;ent_max=1;ent_list_size=mode==3?3:2;spawnoverride=mode==3?2:99;currentspawnplayer=3;time=c[5];lev.nohit=c[3];level=&lev;savedata.mode=c[4];plainmethod.flag=5;plainmethod.other=9;textbox=NULL;nt=0;
for(i=0;i<3;i++){e=pool+i;ent_list[i]=e;e->exists=i<2&&(mode!=0||i!=0);ent_count+=e->exists;e->modeldata.priority=mode==3?-1:4;e->sortid=100+i;e->defense=dfs+i;e->offense_factors=ofs+i;e->varlist=vars+i;e->scripts=scripts+i;e->waypoints=(void*)(600+i);e->stale=77;}
e=spawn(10,20,30,2,c[1]==1?"model":NULL,c[1]==1||c[1]==3?-1:0,c[1]==2?&model:NULL);id=e?(int)(e-pool):-1;
printf("SPAWN|%u|",n);for(j=0;j<nt;j++)printf("%s%d",j?",":"",trace[j]);
printf("|%d,%d,%d,%d",id,ent_count,ent_max,textbox?(int)(textbox-pool):-1);
if(!e){for(j=0;j<27;j++)printf(",0");}
else printf(",%d,%d,%d,%d,%d,%d,%u,%d,%d,%d,%d,%d,%d,%d,%u,%u,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d",e->exists,e->sortid,200+(int)(e->defense-dfs),300+(int)(e->offense_factors-ofs),400+(int)(e->varlist-vars),500+(int)(e->scripts-scripts),e->timestamp,e->health,e->mp,e->knockdowncount,(int)e->position.x,(int)e->position.z,(int)e->position.y,e->direction,e->nextthink,e->nextmove,(int)e->speedmul,e->lifespancountdown,e->playerindex,e->stale,(int)e->waypoints,e->modeldata.hostile,e->modeldata.candamage,e->drawmethod.flag,e->drawmethod.other,e->model==&model,e->defaultmodel==&model);
puts("");}return 0;}
'''
    (folder/'spawn.c').write_text(source);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    proc=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','spawn.c','-fe=spawn.exe'],cwd=folder,env=env,capture_output=True,text=True);(folder/'build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('SPAWN_AUTHORITY_C_BUILD')
    log=subprocess.check_output([str(folder/'spawn.exe')],cwd=folder,text=True);(folder/'authority.log').write_text(log);results=[]
    for line in log.splitlines():
        if not line.startswith('SPAWN|'):continue
        _,n,trace,state=line.split('|');i=int(n);actual=dict(trace=[int(v) for v in trace.split(',') if v],state=list(map(int,state.split(','))));expected=reference(rows[i]);results.append(dict(case=rows[i],actual=actual,expected=expected,pass_case=actual==expected))
    ok=len(results)==len(rows) and all(r['pass_case'] for r in results)
    report=dict(schema='BYOR_4086_SPAWN_CONSTRUCTOR_AUTHORITY_V1',status='PASS' if ok else 'FAIL',engine_commit=ENGINE_COMMIT,function_sha256=hashlib.sha256(function.encode()).hexdigest(),cases=len(rows),results=results,external_services_instrumented=True,default_init_bound=False,native_constructor_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(results),'spawn constructor C cases')
    if not ok:raise SystemExit(1)

if __name__=='__main__':main()
