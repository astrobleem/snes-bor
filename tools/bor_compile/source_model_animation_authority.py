"""Pinned ent_set_model/ent_set_anim transition with frame-zero service observed."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_animation_init_4086 import set_animation
from source_model_switch_4086 import set_model_animation

IDS=(0,23,104,59)
COUNTS=((4,2,3,1),(2,0,0,0),(0,1,1,1))


def fixtures():
    return [dict(mask=mask,variant=variant,sync=sync,type=type_,select=select,time=time,frame=frame,old=old)
        for mask in (0,1,2,4,8,15) for variant in range(3) for sync in (0,1) for type_ in (0,1)
        for select in (0,1) for time in (0,48,0xffffffff) for frame in (0,3,7) for old in (0,1)]


def expected(c):
    animations=[dict(identity=i+2,numframes=count,sync=1 if c['variant']==1 else -1,animhits=17+i,
                     delay=[6+2*i+j for j in range(count)]) for i,count in enumerate(COUNTS[c['variant']])]
    old=dict(identity=1,numframes=8,sync=1,animhits=77,delay=list(range(8)))
    cache={n:animations[i] if c['mask']&(1<<i) else None for i,n in enumerate(IDS)}
    e=dict(modeldata=dict(animation=cache,type=c['type']),animations=cache,animation=old if c['old'] else None,
        animnum=0,animpos=c['frame'],animating=-1,lasthit=77,grabbing=123,altbase=13,nextanim=456,attacking=1)
    calls=[]
    def update(e,f):calls.append(f)
    def choose(e,n,r):set_animation(e,n,r,dict(maximum=168,update_frame=update))
    owner=dict(time=c['time'],select=c['select'],idle=0,spawn=23,respawn=104,select_animation=59,set_animation=choose)
    unsafe=bool(c['sync'] and cache[0] is not None and not cache[0]['numframes'])
    if unsafe:
        return dict(unsafe=True,state=None)
    set_model_animation(e,c['sync'],owner)
    state=[e['animnum'],e['animation']['identity'] if e['animation'] else 0,e['animpos'],e['animating'],e['lasthit'],e['altbase'],e['nextanim'],e['attacking'],*[a['animhits'] for a in animations],len(calls),0]
    return dict(unsafe=False,state=state)


def run(engine,folder):
    folder.mkdir(parents=True,exist_ok=True);raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=engine).decode('latin1')
    functions='\n\n'.join(extract(raw,n) for n in ('ent_set_anim','ent_set_model'));rows=fixtures()
    c=r'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define TYPE_PLAYER 1
#define ANI_IDLE 0
#define ANI_SPAWN 23
#define ANI_RESPAWN 104
#define ANI_SELECT 59
typedef struct {int identity,numframes,sync,animhits,delay[8];} s_anim;
typedef struct {char *name;int type;s_anim **animation;} s_model;
typedef struct entity {s_model *model,modeldata;int animnum,animpos,animating,lasthit,grabbing,altbase,attacking,map;s_anim *animation;unsigned nextanim;} entity;
s_model nextmodel;int max_animations=168,selectScreen,calls,unsafe;unsigned time;
s_model *findmodel(char *name){return &nextmodel;}
void shutdown(int i,char *format,...){exit(3);}
void ent_copy_uninit(entity *e,s_model *old){}
void ent_set_colourmap(entity *e,int n){}
int validanim(entity *e,int n){return n>=0&&n<168&&e->modeldata.animation[n]&&e->modeldata.animation[n]->numframes>0;}
int calculate_edelay(entity *e,int f){if(f<0||f>=e->animation->numframes){unsafe++;return 0;}return e->animation->delay[f];}
void update_frame(entity *e,int f){if(f!=0)exit(4);calls++;}
'''+functions+'\n'
    c+='int cases[][8]={'+','.join('{'+','.join(str(r[k]) if k!='time' else str(r[k])+'UL' for k in ('mask','variant','sync','type','select','time','frame','old'))+'}' for r in rows)+'};\n'
    c+=r'''int main(void){unsigned i;int j,*r,ids[4]={0,23,104,59},counts[3][4]={{4,2,3,1},{2,0,0,0},{0,1,1,1}};s_anim anim[5],*cache[168];entity e;
 if(sizeof(int)!=4||sizeof(unsigned)!=4||sizeof(void*)!=4)return 2;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
 r=cases[i];memset(anim,0,sizeof(anim));memset(cache,0,sizeof(cache));memset(&e,0,sizeof(e));calls=unsafe=0;
 anim[0].identity=1;anim[0].numframes=8;anim[0].sync=1;anim[0].animhits=77;
 for(j=0;j<4;j++){int k;anim[j+1].identity=j+2;anim[j+1].numframes=counts[r[1]][j];anim[j+1].sync=r[1]==1?1:-1;anim[j+1].animhits=17+j;
 for(k=0;k<anim[j+1].numframes;k++)anim[j+1].delay[k]=6+2*j+k;
 if(r[0]&(1<<j))cache[ids[j]]=anim+j+1;}
 nextmodel.type=r[3];nextmodel.name="next";nextmodel.animation=cache;e.modeldata=nextmodel;
 e.animation=r[7]?anim:NULL;e.animnum=0;e.animpos=r[6];e.animating=-1;e.lasthit=77;e.grabbing=123;e.altbase=13;e.nextanim=456;e.attacking=1;
 selectScreen=r[4];time=(unsigned)r[5];ent_set_model(&e,"next",r[2]);
 printf("MODELTRANSITION|%u|%d,%d,%d,%d,%d,%d,%u,%d,%d,%d,%d,%d,%d,%d\n",i,e.animnum,e.animation?e.animation->identity:0,e.animpos,e.animating,e.lasthit,e.altbase,e.nextanim,e.attacking,anim[1].animhits,anim[2].animhits,anim[3].animhits,anim[4].animhits,calls,unsafe);
 }return 0;}
'''
    (folder/'model_animation.c').write_text(c)
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    proc=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','model_animation.c','-fe=model_anim_authority.exe'],cwd=folder,env=env,capture_output=True,text=True)
    (folder/'build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('MODEL_ANIMATION_AUTHORITY_BUILD')
    out=subprocess.check_output([str((folder/'model_anim_authority.exe').resolve())],cwd=folder,text=True);results=[]
    for line in out.splitlines():
        if not line.startswith('MODELTRANSITION|'):continue
        _,i,values=line.split('|');i=int(i);actual=list(map(int,values.split(',')));wanted=expected(rows[i])
        passed=actual[-1]==1 and actual[2]==-1 if wanted['unsafe'] else actual==wanted['state']
        results.append(dict(case=rows[i],actual=actual,expected=wanted,passed=passed))
    report=dict(schema='BYOR_4086_MODEL_ANIMATION_AUTHORITY_V1',status='PASS' if len(results)==len(rows) and all(r['passed'] for r in results) else 'FAIL',engine_commit=ENGINE_COMMIT,
        functions_sha256=hashlib.sha256(functions.encode('latin1')).hexdigest(),cases=len(rows),results=results,
        source_undefined_zero_frame_sync_cases=sum(r['expected']['unsafe'] for r in results),frame_zero_service_instrumented=True,modeldata_copy_instrumented=True,native_owner_bound=False,motu_gameplay_proven=False)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=run(a.engine,a.output.resolve());print(json.dumps({k:r[k] for k in ('status','cases','functions_sha256','source_undefined_zero_frame_sync_cases')}))
    if r['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
