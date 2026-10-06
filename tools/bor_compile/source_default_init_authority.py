"""Differential proof of complete default-init branching against pinned C."""
import argparse,hashlib,json,os,subprocess,struct,itertools
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_default_init_4086 import initialize,Service

CALLBACKS=['player_takedamage','player_think','player_trymove','common_spawn','common_drop','common_think','biker_takedamage','arrow_takedamage','common_trymove','common_takedamage','trap_think','obstacle_takedamage','steamer_think','text_think','anything_walk']
ANIMS=['idle','spawn','respawn','select','jump','walk']
FIELDS=['nograb','attacking','health','dead','invincible','blink','invinctime','arrowon','playerindex','direction','ptype']
MODELFIELDS=['multiple','subject_to_gravity','no_adjust_base']
FLOATS=['x','a','base','vx','speedmul']
CFIELDS=['takedamage','think','trymove','takeaction']

def fixtures():
    base=dict(type=0,subtype=0,mask=0,level=1,select=0,time=48,direction=1,speed=0,nomove=0,makeinv=0,environment=0,existing=0,ptype=0,health=10,scroll=0,nodrop=0,x=10,multiple=0,mutation=0)
    rows=[dict(base,type=t,subtype=s,mask=m,level=l) for t,s,m,l in itertools.product((0,1,2,3,4,8,16,32,64,128,129,256,512,1024,0x40000000),(0,1,2,3),(0,2,4,8,16,32,6,63),(0,1))]
    for field,values in dict(time=[0,0xffffffff],select=[1],direction=[0,2],speed=[3],nomove=[1],makeinv=[-20,20],environment=[1,2,3,4],existing=[1],ptype=[1],health=[0,-1],scroll=[1,2],nodrop=[1],x=[-30,350],multiple=[-1]).items():
        for v in values:
            for t in (0,1,2,32,512):rows.append(dict(base,type=t,**{field:v}))
    rows.extend(dict(base,type=t,mask=m,select=s,time=time) for t,m,s,time in itertools.product((0,1,2,32,512),(2,4,8,6,63),(0,1),(0,48,0xffffffff)))
    rows.extend(dict(base,type=t,subtype=sub,mask=mask,direction=direction,speed=speed,nomove=nomove,ptype=ptype) for t,sub,mask in ((0,0,32),(2,1,0),(2,3,0),(32,0,0)) for direction,speed,nomove,ptype in itertools.product((0,1,2),(0,3),(0,1),(0,1)))
    rows.extend(dict(base,type=t,mask=mask,level=level,mutation=mutation) for t,mask,mutation in ((2,2,1),(1,16,2),(0,32,3),(0,0,4),(2,2,5)) for level in (0,1))
    return rows

def bits(f):return struct.unpack('<I',struct.pack('<f',f))[0]
def reference(c):
    d=dict(type=c['type'],subtype=c['subtype'],animations={n:1 for i,n in enumerate(ANIMS) if c['mask']&(1<<i)},speed=float(c['speed']),nomove=c['nomove'],makeinv=c['makeinv'],multiple=c['multiple'],subject_to_gravity=-1,no_adjust_base=-1,subject_to_platform=int(c['environment']>0),subject_to_wall=int(c['environment']>0))
    e=dict.fromkeys(FIELDS+FLOATS,0);e.update(modeldata=d,model=dict(speed=c['speed']),animation='idle' if c['existing'] else None,x=c['x'],a=0,health=c['health'],speedmul=1,direction=c['direction'],ptype=c['ptype'],playerindex=0)
    o=dict(level=dict(spawn_y=[20]*4,scroll=['normal','up','down'][c['scroll']],walls=[10,200]) if c['level'] else None,time=c['time'],select=c['select'],nodropspawn=c['nodrop'],advancex=0,width=320,height=240,max_wall_height=100)
    g=initialize(e,o);trace=[];reply=None;mutated=False
    while True:
        try:s,_,arg=g.send(reply)
        except StopIteration:break
        trace.extend((int(s),ANIMS.index(arg) if s==Service.SET_ANIMATION else int(arg) if s in (Service.RANDOM_FLOAT,Service.WALL_BELOW,Service.NEAREST_WALL_X) else 0));reply=None
        if s==Service.SET_ANIMATION:e['animation']=arg
        elif s==Service.SET_IDLE:e['animation']='idle'
        elif s==Service.RANDOM_FLOAT:reply=0.125
        elif s==Service.IN_AIR:reply=e['a']!=e['base']
        elif s==Service.WALK_ANIMATION:e['animation']='walk'
        elif s==Service.PLATFORM_BELOW:reply=dict(a=5,platform_height=7) if c['environment']==1 else None
        elif s==Service.WALL_BELOW:reply=-1 if c['environment']==4 else 1 if c['environment']==3 else 0
        elif s==Service.NEAREST_WALL_X:reply=99
        trigger=(c['mutation'] in (1,5) and s==Service.SET_ANIMATION and arg in ('spawn','respawn','select') or c['mutation']==2 and s==Service.SET_ANIMATION and arg=='jump' or c['mutation']==3 and s==Service.WALK_ANIMATION or c['mutation']==4 and s==Service.SET_IDLE)
        if trigger and not mutated:
            d=dict(e['modeldata']);d.update(type={1:1,2:0,3:32,4:2,5:32}[c['mutation']],makeinv=-20 if c['mutation']==2 else 20,multiple=-1,speed=3.0,subject_to_gravity=-1,no_adjust_base=-1,subject_to_platform=1,subject_to_wall=1);e['modeldata']=d;mutated=True
    d=e['modeldata']
    vals=[e[f]&0xffffffff for f in FIELDS]+[d[f]&0xffffffff for f in MODELFIELDS]+[bits(e[f]) for f in FLOATS]+[bits(d['speed'])]+[CALLBACKS.index(e[f])+1 if e.get(f) else 0 for f in CFIELDS]+[ANIMS.index(e['animation']) if e['animation'] is not None else -1]
    return dict(trace=trace,state=vals)

PREAMBLE=r'''
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#define ABS(n) abs(n)
#define TYPE_RESERVED 0x40000000
#define TYPE_ENDLEVEL 256
#define TYPE_ITEM 4
#define TYPE_PLAYER 1
#define TYPE_NPC 512
#define TYPE_ENEMY 2
#define TYPE_TRAP 64
#define TYPE_OBSTACLE 8
#define TYPE_STEAMER 16
#define TYPE_TEXTBOX 128
#define TYPE_SHOT 32
#define TYPE_NONE 0
#define TYPE_PANEL 1024
#define SUBTYPE_BIKER 1
#define SUBTYPE_NOTGRAB 2
#define SUBTYPE_ARROW 3
#define DIRECTION_RIGHT 1
#define SCROLL_UP 1
#define SCROLL_DOWN 2
#define MAX_WALL_HEIGHT 100
#define ANI_SPAWN 1
#define ANI_RESPAWN 2
#define ANI_SELECT 3
#define ANI_JUMP 4
#define ANI_WALK 5
typedef void (*Callback)(void);
typedef struct {int type,subtype,makeinv,multiple,nomove,subject_to_gravity,no_adjust_base,subject_to_platform,subject_to_wall;float speed;} Model;
typedef struct {float platform[1][8];} Anim;
typedef struct entity {Model modeldata,*model;Anim *animation;int animpos,animid,nograb,attacking,health,dead,invincible,blink,arrowon,playerindex,direction,ptype;unsigned invinctime;struct {float x,z,y;} position;struct {float x;} velocity;float base,speedmul;Callback takedamage,think,trymove,takeaction;} entity;
typedef struct {struct {float y;} spawn[4];struct {float height;} walls[2];int scrolldir;} Level;
Level lev,*level;entity ent,platform;Model cached;Anim anim;
struct {int hRes,vRes;} videomodes;
int selectScreen,nodropspawn,advancex,environment,mask,trace[128],nt,mutation,mutated;unsigned time;
void mutate(entity *e,int service,int id){int trigger=(mutation==1||mutation==5)&&service==1&&id>=1&&id<=3||mutation==2&&service==1&&id==4||mutation==3&&service==5||mutation==4&&service==2;
if(trigger&&!mutated){Model d=e->modeldata;d.type=mutation==1?1:mutation==2?0:mutation==4?2:32;d.makeinv=mutation==2?-20:20;d.multiple=-1;d.speed=3;d.subject_to_gravity=d.no_adjust_base=-1;d.subject_to_platform=d.subject_to_wall=1;e->modeldata=d;mutated=1;}}
void event(int n,int arg){trace[nt++]=n;trace[nt++]=arg;}
int validanim(entity *e,int id){return !!(mask&(1<<id));}
void ent_set_anim(entity *e,int id,int reset){event(1,id);e->animation=&anim;e->animid=id;mutate(e,1,id);}
void set_idle(entity *e){event(2,0);e->animation=&anim;e->animid=0;mutate(e,2,0);}
float randf(float maximum){event(3,(int)maximum);return .125f;}
int inair(entity *e){event(4,0);return e->position.y!=e->base;}
void common_walk_anim(entity *e){event(5,0);e->animation=&anim;e->animid=5;mutate(e,5,0);}
entity *check_platform_below(float x,float z,float y,entity *e){event(6,0);return environment==1?&platform:NULL;}
int checkwall_below(float x,float z,float y){event(7,(int)y);return environment==4?-1:environment==3?1:0;}
float find_nearest_wall_x(int wall,float x,float z){event(8,wall);return 99;}
'''

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=a.engine).decode('latin1');function=extract(raw,'ent_default_init');rows=fixtures();keys=list(rows[0])
    callbacks='\n'.join('void '+n+'(void){}' for n in CALLBACKS)+'\nCallback callbacks[]={NULL,'+','.join(CALLBACKS)+'};\n'
    data=',\n'.join('{'+','.join(str(c[k]&0xffffffff)+'u' for k in keys)+'}' for c in rows)
    get=lambda k:'c['+str(keys.index(k))+']'
    setup='\n'.join('ent.modeldata.'+k+'=(int)'+get(k)+';' for k in ('type','subtype','speed','nomove','makeinv','multiple'))
    setup+='\n'+'\n'.join(v+'='+('' if k=='time' else '(int)')+get(k)+';' for k,v in dict(mask='mask',select='selectScreen',time='time',environment='environment',scroll='lev.scrolldir',nodrop='nodropspawn',direction='ent.direction',ptype='ent.ptype',health='ent.health',x='ent.position.x',mutation='mutation').items())
    source=PREAMBLE+callbacks+function+'\nunsigned cases[][19]={'+data+'};\n'+r'''
unsigned bits(float f){unsigned n;memcpy(&n,&f,4);return n;}
int cid(Callback f){int i;for(i=0;i<16;i++)if(callbacks[i]==f)return i;return -1;}
int main(void){unsigned n,*c;int i;entity *e=&ent;
if(sizeof(void*)!=4||sizeof(unsigned)!=4)return 2;
for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
c=cases[n];memset(&ent,0,sizeof(ent));memset(&lev,0,sizeof(lev));memset(&anim,0,sizeof(anim));memset(&platform,0,sizeof(platform));nt=0;mutated=0;
''' + setup + '\nlevel='+get('level')+'?&lev:NULL;ent.animation='+get('existing')+'?&anim:NULL;ent.animid=ent.animation?0:-1;\n'+r'''
cached=ent.modeldata;ent.model=&cached;ent.modeldata.subject_to_gravity=-1;ent.modeldata.no_adjust_base=-1;ent.modeldata.subject_to_platform=ent.modeldata.subject_to_wall=environment>0;ent.speedmul=1;
for(i=0;i<4;i++)lev.spawn[i].y=20;lev.walls[0].height=10;lev.walls[1].height=200;videomodes.hRes=320;videomodes.vRes=240;platform.position.y=5;platform.animation=&anim;anim.platform[0][7]=7;advancex=0;
ent_default_init(NULL);
ent_default_init(&ent);
printf("DEFAULT|%u|",n);for(i=0;i<nt;i++)printf("%s%d",i?",":"",trace[i]);
printf("|%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%d\n",e->nograb,e->attacking,e->health,e->dead,e->invincible,e->blink,e->invinctime,e->arrowon,e->playerindex,e->direction,e->ptype,e->modeldata.multiple,e->modeldata.subject_to_gravity,e->modeldata.no_adjust_base,bits(e->position.x),bits(e->position.y),bits(e->base),bits(e->velocity.x),bits(e->speedmul),bits(e->modeldata.speed),cid(e->takedamage),cid(e->think),cid(e->trymove),cid(e->takeaction),e->animid);
}return 0;}
'''
    (folder/'default.c').write_text(source);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    proc=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','default.c','-fe=default.exe'],cwd=folder,env=env,capture_output=True,text=True);(folder/'build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('DEFAULT_INIT_AUTHORITY_C_BUILD')
    log=subprocess.check_output([str(folder/'default.exe')],cwd=folder,text=True);(folder/'authority.log').write_text(log);results=[]
    for line in log.splitlines():
        if not line.startswith('DEFAULT|'):continue
        _,n,trace,state=line.split('|');i=int(n);actual=dict(trace=[int(v) for v in trace.split(',') if v],state=list(map(int,state.split(','))));expected=reference(rows[i]);results.append(dict(case=rows[i],actual=actual,expected=expected,pass_case=actual==expected))
    ok=len(results)==len(rows) and all(r['pass_case'] for r in results)
    report=dict(schema='BYOR_4086_DEFAULT_INIT_AUTHORITY_V1',status='PASS' if ok else 'FAIL',engine_commit=ENGINE_COMMIT,function_sha256=hashlib.sha256(function.encode()).hexdigest(),cases=len(rows),results=results,animation_random_environment_bodies_instrumented=True,native_default_init_bound=False,float_native_policy_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(results),'default-init C cases')
    if not ok:raise SystemExit(1)

if __name__=='__main__':main()
