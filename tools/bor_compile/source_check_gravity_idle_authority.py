"""Compile verbatim pinned check_gravity for its inactive-air source branch."""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import subprocess
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_check_gravity_idle_4086 import check_gravity_idle


PREAMBLE=r'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef struct entity entity;
typedef struct {float x,z,y;} Vec;
typedef struct {int frame,ent;} Frame;
typedef struct {float base,y;} Move;
typedef struct {Vec size;int antigrav,numframes;Frame dropframe,landframe;Move **move;float **platform;float bounce;} Animation;
typedef struct {int attack_force,attack_type;} s_attack;
typedef struct {Vec size;int subject_to_platform,subject_to_gravity,subject_to_wall,subject_to_hole,no_adjust_base;float antigravity;struct {int fall_land;}dust;int bounce,noquake,type;} Model;
struct entity {unsigned update_mark,toss_time;Vec position,velocity;float base,altbase;int falling;Animation *animation;Model modeldata;entity *hithead,*landed_on_platform;int animpos,idling,drop,direction,damage_on_landing,dead,health,playerindex,autokill;void(*takeaction)(void);void(*takedamage)(entity*,s_attack*);struct{float factor;}defense[1];};
typedef struct {float gravity,maxfallspeed,maxtossspeed;int quake;struct{float height;}walls[1];} Level;
entity ent,previous,*self=&previous;Level *level=NULL;
float default_level_gravity=-0.1f,default_level_maxfallspeed=-6,default_level_maxtossspeed=6;
s_attack emptyattack;struct{int effectvol;}savedata;
unsigned time;int frozen,adjust_calls,freeze_calls,platform_calls;
#define GAME_SPEED 200
#define ANI_WALKOFF 1
#define TYPE_PLAYER 1
#define NO_QUAKE 1
#define SAMPLE_FALL -1
#define MAX_PLAYERS 4
#define ATK_LAND 0
void unexpected(void){fprintf(stderr,"UNEXPECTED_AIRBORNE_SERVICE\n");exit(9);}
void check_gravity(entity *e);
entity *check_platform_below_entity(entity *e){platform_calls++;return NULL;}
int testplatform(entity *e,float x,float z,void *p){unexpected();return 0;}
int checkwall_below(float x,float z,float y){unexpected();return -1;}
float check_basemap(float x,float z){unexpected();return -1000;}
int checkhole(float x,float z){unexpected();return 0;}
void ent_unlink(entity *e){unexpected();}
int is_frozen(entity *e){freeze_calls++;return frozen;}
entity *check_platform_above_entity(entity *e){unexpected();return NULL;}
void execute_onblocka_script(entity *e,entity *o){unexpected();}
void update_frame(entity *e,int frame){unexpected();}
void execute_onmovea_script(entity *e){unexpected();}
int validanim(entity *e,int n){unexpected();return 0;}
float diff(float a,float b){return a>b?a-b:b-a;}
void common_walkoff(void){unexpected();}
void ent_set_anim(entity *e,int a,int b){unexpected();}
int inair(entity *e){unexpected();return 0;}
entity *spawn(float x,float z,float a,int d,char *name,int index,void *model){unexpected();return NULL;}
void execute_onspawn_script(entity *e){unexpected();}
int tobounce(entity *e){unexpected();return 0;}
void toss(entity *e,float v){unexpected();}
void sound_play_sample(int n,int p,int l,int r,int rate){unexpected();}
void control_rumble(int p,int n){unexpected();}
void kill(entity *e){unexpected();}
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));a=p.parse_args()
    folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','-C',str(a.engine),'show',ENGINE_COMMIT+':engine/openbor.c'])
    body=extract(raw.decode('latin1'),'check_gravity');base_body=extract(raw.decode('latin1'),'adjust_base')
    code=PREAMBLE+base_body+'\nvoid observe_adjust_base(entity *e,entity **p){adjust_calls++;adjust_base(e,p);}\n#define adjust_base observe_adjust_base\n'+body+'\n#undef adjust_base\nint main(void){\n'
    expected=[];inputs=[]
    for mark,freeze,toss,time,altitude,air,platform in itertools.product((0,4,8,12,0x80000000),(0,1),(0,48,49,0xffffffff),(48,0xffffffff),(0,34), (0,1),(-1,0,1)):
        e=dict(update_mark=mark,toss_time=toss,falling=air,velocity_y=0,a=altitude,base=altitude)
        calls=[]
        try:check_gravity_idle(e,time,lambda e:calls.append('adjust'),lambda e:(calls.append('freeze')or bool(freeze)))
        except ValueError:continue
        inputs.append(dict(mark=mark,freeze=freeze,toss=toss,time=time,altitude=altitude,falling=air,subject_to_platform=platform,no_adjust_base=1))
        expected.append([e['update_mark'],e['toss_time'],calls.count('adjust'),calls.count('freeze'),1,calls.count('adjust')if platform>0 else 0])
        code+='memset(&ent,0,sizeof(ent));self=&previous;adjust_calls=freeze_calls=platform_calls=0;ent.modeldata.no_adjust_base=1;ent.modeldata.subject_to_platform=%d;'%platform
        code+='ent.update_mark=%du;ent.toss_time=%du;ent.falling=%d;ent.position.y=ent.base=%d;time=%du;frozen=%d;'%(mark,toss,air,altitude,time,freeze)
        code+='check_gravity(&ent);printf("%u,%u,%d,%d,%d,%d\\n",ent.update_mark,ent.toss_time,adjust_calls,freeze_calls,self==&previous,platform_calls);\n'
    code+='return 0;}\n';(folder/'gravity.c').write_text(code)
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-bt=nt','gravity.c','-fe=gravity.exe'],cwd=folder,env=env,capture_output=True,text=True)
    (folder/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise ValueError('CHECK_GRAVITY_IDLE_AUTHORITY_BUILD_FAILED:'+build.stdout+build.stderr)
    log=subprocess.check_output([str(folder/'gravity.exe')],cwd=folder,text=True);(folder/'authority.log').write_text(log)
    actual=[list(map(int,s.split(',')))for s in log.splitlines()]
    report=dict(schema='BYOR_4086_CHECK_GRAVITY_IDLE_AUTHORITY_V1',status='PASS'if actual==expected else'FAIL',
                engine_commit=ENGINE_COMMIT,source_function_sha256=hashlib.sha256(body.encode('latin1')).hexdigest(),source_function_unmodified=True,
                cases=len(inputs),inputs=inputs,actual=actual,expected=expected,adjust_base_call_instrumented=True,freeze_service_instrumented=True,
                adjust_base_body_proven=True,adjust_base_function_sha256=hashlib.sha256(base_body.encode('latin1')).hexdigest(),adjust_base_source_function_unmodified=True,
                empty_platform_service_instrumented=True,sticky_base_no_adjust_policy=True,active_airborne_branch_proven=False,native_gravity_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(inputs),'inactive-air gravity cases');assert actual==expected


if __name__=='__main__':main()
