"""Compare generic model-switch policy to verbatim pinned engine functions.

Animation initialization, scripts and model-copy callbacks are instrumented.
This proves mutable cached inheritance, per-entity fallback, synchronized frame
selection and weapon/type policy; it does not certify those external services.
"""
import argparse
import hashlib,json,os
from pathlib import Path
import subprocess
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_model_switch_4086 import GLOBAL_NEGATIVE,ENTITY_NEGATIVE,RUN_FIELDS,set_weapon

FIELDS=['speed',*RUN_FIELDS,*GLOBAL_NEGATIVE,*ENTITY_NEGATIVE,'aimove','aiattack','health','mp','risetime.rise','weapnum']


def fixtures():
    return [dict(flags=flags,anim_flag=anim_flag,oldtype=oldtype,newtype=newtype,number=number,
        select=select,time=48 if time else 0,map=map_,variant=variant)
        for flags in range(8) for anim_flag in (0,1) for oldtype,newtype in ((0,0),(1,0),(1,1))
        for number in (0,1,2,3) for select,time,map_,variant in ((0,1,1,0),(1,1,2,1),(0,0,0,0))]


def expected(c):
    animations=[dict(identity=1,numframes=4,delay=[6,8,10,12]),dict(identity=2,numframes=2,delay=[14,16]),
                dict(identity=3,numframes=0,delay=[]),dict(identity=4,numframes=1,delay=[18])]
    old=dict(zip(FIELDS,range(10,10+len(FIELDS))))
    old.update(identity=0,type=c['oldtype'],model_flag=0,animation={0:animations[0],1:animations[1],2:animations[2],3:None},
        weapon=[1,0],numweapons=2,weaploss=[3,-1],maps_loaded=1,palette=100,colourmap=[101],onmodelcopy=0)
    new=dict(zip(FIELDS,range(110,110+len(FIELDS))))
    for i,field in enumerate(FIELDS):
        if not c['variant'] or i%3:
            new[field]=0 if field in ('speed','runspeed','health','mp') else -1
    new.update(identity=1,type=c['newtype'],model_flag=c['flags'],animation={0:None,1:animations[1],2:None,3:animations[3]},
        weapon=None,numweapons=0,weaploss=[3,-1],maps_loaded=1,palette=200,colourmap=[201],onmodelcopy=c['variant'])
    entity=dict(model=old,defaultmodel=old,modeldata=dict(old),health=500,mp=500,playerindex=0,animnum=0,
        animation=animations[0],animpos=3,nextanim=123,attacking=1,map=c['map'],exists=1,onmodelcopy=0,
        offense_factors=[7,8],defense=[9,10])
    for field in ENTITY_NEGATIVE+['aimove','aiattack','health','mp','risetime.rise']:
        entity['modeldata'][field]+=60
    trace=[]
    def set_animation(e,n,reset):
        trace.append(10+n);a=e['modeldata']['animation'].get(n)
        if a and a['numframes']:
            e.update(animation=a,animnum=n,animpos=0,nextanim=(c['time']+a['delay'][0])&0xffffffff)
    def clear_scripts(e,localclear):trace.append(20);e['onmodelcopy']=0
    def copy_scripts(m,e,localclear):
        trace.append(21)
        if m['onmodelcopy']:e['onmodelcopy']=m['onmodelcopy']
    def combat(e):trace.append(22);e['defense']=[31,32];e['offense_factors']=[41,42]
    def callback(e,old):trace.append(23+old['exists'])
    owner=dict(time=c['time'],select=c['select'],idle=1,spawn=3,respawn=2,select_animation=3,
        set_animation=set_animation,snapshot_entity=lambda e:dict(e),clear_scripts=clear_scripts,
        copy_scripts=copy_scripts,copy_combat_factors=combat,onmodelcopy=callback,
        models=[old,new],player_weapons=[77],level_weapon=5)
    set_weapon(entity,c['number'],c['anim_flag'],owner)
    state=[entity['model']['identity'],entity['modeldata']['type'],entity['health'],entity['mp'],entity['animnum'],
        entity['animation']['identity'],entity['animpos'],entity['nextanim'],entity['attacking'],entity['map'],
        entity.get('colourmap',0),owner['player_weapons'][0],entity['onmodelcopy'],*entity['defense'],*entity['offense_factors']]
    for model in (new,entity['modeldata']):
        state.extend(model[f] for f in FIELDS)
        state.extend(model['animation'].get(n)['identity'] if model['animation'].get(n) else 0 for n in range(4))
        state.extend([model['numweapons'],int(model['weapon'] is old['weapon'])])
    return dict(trace=trace,state=state)


def run(engine,folder):
    folder.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=engine)
    names=('ent_set_colourmap','ent_copy_uninit','ent_set_model','set_model_ex','set_weapon')
    functions='\n\n'.join(extract(raw.decode('latin1'),name) for name in names)
    rows=fixtures()
    source=r'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define TYPE_PLAYER 1
#define WEAPLOSS_TYPE_CHANGE 3
#define MODEL_NO_COPY 1
#define MODEL_NO_WEAPON_COPY 2
#define MODEL_NO_SCRIPT_COPY 4
#define ANI_IDLE 1
#define ANI_SPAWN 3
#define ANI_RESPAWN 2
#define ANI_SELECT 3
typedef struct {int numframes,identity,delay[4];} s_anim;
typedef int s_defense;
typedef struct {int onmodelcopy_script;} s_scripts;
typedef struct s_model {char *name;int identity,type,model_flag;
 float speed,runspeed,runjumpheight,runjumpdist;int runupdown,runhold;
 struct {int def,pain,get,die;} icon;
 int shadow,knife,pshotno,bomb,star,flash,bflash,diesound;
 struct {int fall_land,jump_land;} dust;
 int multiple,subject_to_wall,subject_to_platform,subject_to_obstacle,subject_to_hole;
 int subject_to_gravity,subject_to_screen,subject_to_minz,subject_to_maxz,no_adjust_base;
 int hostile,candamage,projectilehit,aimove,aiattack,health,mp;
 struct {int rise;} risetime;
 int weapnum,*weapon,numweapons,weaploss[2],maps_loaded;
 unsigned char *palette,**colourmap;s_anim **animation;
 s_scripts *scripts;s_defense *defense;float *offense_factors;
} s_model;
typedef struct entity {char *name;s_model *model,*defaultmodel; s_model modeldata;
 int exists,health,mp,playerindex,animnum,animpos,attacking;unsigned nextanim,map;
 s_anim *animation;unsigned char *colourmap;s_scripts *scripts;
 s_defense *defense;float *offense_factors;
} entity;
typedef struct {int flags,anim_flag,oldtype,newtype,number,select,time,map,variant;} fixture;
s_model models[2];struct {s_model *model;} model_cache[2];
struct {int weapnum;} player[1];struct {int setweap;} lv,*level=&lv;
unsigned time;int selectScreen,max_animations=4,max_attack_types=2;
int trace[32],trace_count;
void event(int n){trace[trace_count++]=n;}
void shutdown(int a,char *s,...){exit(3);}
s_model *findmodel(char *s){return strcmp(s,"old")==0?models:models+1;}
int validanim(entity *e,int n){return n>=0&&n<4&&e->modeldata.animation[n]&&e->modeldata.animation[n]->numframes>0;}
int calculate_edelay(entity *e,int f){return e->animation->delay[f];}
void ent_set_anim(entity *e,int n,int r){event(10+n);if(validanim(e,n)){e->animation=e->modeldata.animation[n];e->animnum=n;e->animpos=0;e->nextanim=time+calculate_edelay(e,0);}}
int Script_IsInitialized(int script){return script!=0;}
void clear_all_scripts(s_scripts *s,int localclear){event(20);s->onmodelcopy_script=0;}
void copy_all_scripts(s_scripts *a,s_scripts *b,int localclear){event(21);if(a->onmodelcopy_script)b->onmodelcopy_script=a->onmodelcopy_script;}
void execute_onmodelcopy_script(entity *e,entity *old){event(23+old->exists);}
''' + functions + '\nfixture cases[]={'+',\n'.join('{'+','.join(str(c[k]) for k in
        ('flags','anim_flag','oldtype','newtype','number','select','time','map','variant'))+'}' for c in rows)+'};\n'
    source+=r'''int main(void){unsigned i;int j,n,weapons[2]={1,0};entity ent;s_anim anim[4]={{4,1,{6,8,10,12}},{2,2,{14,16}},{0,3,{0}},{1,4,{18}}};
 s_anim *ma[2][4];s_scripts scripts[3];s_defense defense[3][2];float offense[3][2];unsigned char *maps[2][1];fixture *c;
 if(sizeof(long)!=4||sizeof(void*)!=4||sizeof(unsigned)!=4)return 2;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
 c=&cases[i];memset(models,0,sizeof(models));memset(&ent,0,sizeof(ent));memset(scripts,0,sizeof(scripts));trace_count=0;
 for(j=0;j<2;j++){models[j].name=j?"new":"old";models[j].identity=j;models[j].animation=ma[j];models[j].scripts=scripts+j;
 models[j].defense=defense[j];models[j].offense_factors=offense[j];defense[j][0]=31;defense[j][1]=32;offense[j][0]=41;offense[j][1]=42;
 models[j].maps_loaded=1;models[j].palette=(unsigned char*)(100+100*j);maps[j][0]=(unsigned char*)(101+100*j);models[j].colourmap=maps[j];
 models[j].weaploss[0]=3;models[j].weaploss[1]=-1;}
 models[0].type=c->oldtype;models[1].type=c->newtype;models[1].model_flag=c->flags;models[0].weapon=weapons;models[0].numweapons=2;
 ma[0][0]=anim;ma[0][1]=anim+1;ma[0][2]=anim+2;ma[0][3]=NULL;
 ma[1][0]=NULL;ma[1][1]=anim+1;ma[1][2]=NULL;ma[1][3]=anim+3;
 scripts[1].onmodelcopy_script=c->variant;
'''
    for n,f in enumerate(FIELDS):
        default='0' if f in ('speed','runspeed','health','mp') else '-1'
        source+=f' models[0].{f}={10+n};models[1].{f}=(!c->variant||{n}%3)?{default}:{110+n};\n'
    source+=r''' ent.model=ent.defaultmodel=models;ent.modeldata=models[0];ent.health=ent.mp=500;ent.exists=1;
 ent.animation=anim;ent.animnum=0;ent.animpos=3;ent.nextanim=123;ent.attacking=1;ent.map=c->map;
 ent.scripts=scripts+2;ent.defense=defense[2];ent.offense_factors=offense[2];defense[2][0]=9;defense[2][1]=10;offense[2][0]=7;offense[2][1]=8;
'''
    for f in ENTITY_NEGATIVE+['aimove','aiattack','health','mp','risetime.rise']:source+=f' ent.modeldata.{f}+=60;\n'
    source+=r''' time=c->time;selectScreen=c->select;lv.setweap=5;player[0].weapnum=77;model_cache[0].model=models;model_cache[1].model=models+1;
 set_weapon(&ent,c->number,c->anim_flag);
 /* Factor copies are verbatim memcpy calls. Put their observer event in the
    expected trace immediately after script copy, before model-copy callback. */
 if(ent.model==models+1){for(j=trace_count;j>0;j--){if(trace[j-1]==21){memmove(trace+j+1,trace+j,(trace_count-j)*sizeof(int));trace[j]=22;trace_count++;break;}}}
 printf("MODELAUTH|%u|",i);for(j=0;j<trace_count;j++)printf("%s%d",j?",":"",trace[j]);
 printf("|%d,%d,%d,%d,%d,%d,%d,%u,%d,%u,%u,%d,%d,%d,%d,%.9g,%.9g",ent.model->identity,ent.modeldata.type,ent.health,ent.mp,ent.animnum,ent.animation->identity,ent.animpos,ent.nextanim,ent.attacking,ent.map,(unsigned)ent.colourmap,player[0].weapnum,ent.scripts->onmodelcopy_script,ent.defense[0],ent.defense[1],ent.offense_factors[0],ent.offense_factors[1]);
 for(n=0;n<2;n++){s_model *m=n?&ent.modeldata:models+1;
'''
    for f in FIELDS:source+=f' printf(",%.9g",(double)m->{f});\n'
    source+=r''' for(j=0;j<4;j++)printf(",%d",m->animation[j]?m->animation[j]->identity:0);
 printf(",%d,%d",m->numweapons,m->weapon==models[0].weapon);
 }puts("");}return 0;}
'''
    (folder/'model_switch.c').write_text(source)
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    built=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','model_switch.c','-fe=model_authority.exe'],
        cwd=folder,env=env,capture_output=True,text=True)
    (folder/'build.log').write_text(built.stdout+built.stderr)
    if built.returncode:raise ValueError('MODEL_SWITCH_AUTHORITY_BUILD')
    output=subprocess.check_output([str((folder/'model_authority.exe').resolve())],cwd=folder,text=True)
    results=[]
    for line in output.splitlines():
        if not line.startswith('MODELAUTH|'):continue
        _,number,trace,state=line.split('|');number=int(number)
        actual=dict(trace=[int(n) for n in trace.split(',')] if trace else [],state=[float(n) for n in state.split(',')])
        wanted=expected(rows[number]);results.append(dict(case=rows[number],actual=actual,expected=wanted,passed=actual==wanted))
    report=dict(schema='BYOR_4086_MODEL_SWITCH_AUTHORITY_V1',status='PASS' if len(results)==len(rows) and all(r['passed'] for r in results) else 'FAIL',
        engine_commit=ENGINE_COMMIT,engine_source_sha256=hashlib.sha256(raw).hexdigest(),
        functions_sha256=hashlib.sha256(functions.encode('latin1')).hexdigest(),functions=list(names),cases=len(rows),results=results,
        scope='Cached model mutation, entity fallback/health clamp, retained type, weapon selection, synchronized animation/frame/time and color-map bounds',
        animation_initialization_instrumented=True,scripts_instrumented=True,model_copy_callback_instrumented=True,
        native_model_switch_bound=False,motu_gameplay_proven=False)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=run(a.engine,a.output.resolve())
    print(json.dumps({k:r[k] for k in ('status','cases','functions_sha256')}))
    if r['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
