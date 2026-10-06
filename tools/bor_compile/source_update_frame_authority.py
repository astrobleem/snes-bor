"""Execute pinned update_frame verbatim against a resumable service owner.

External handlers are instrumented, not claimed as gameplay implementations.
Pinned code owns frame mutation, interruption checks, effect ordering, base,
quake, facing, timestamps, velocity and source-self restoration.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_frame_effects_4086 import loader_frames
from source_update_frame import Animation,Entity,Frame,Owner,Service,update_frame


def cases():
    return [dict(mode=mode,level=level,direction=direction,animating=animating,
        f=f,base=base,jumping=jumping,success=success,subdamage=subdamage,
        time=0xffffffff if mode==3 else 48)
        for mode in range(5) for level in (0,1) for direction in (0,1)
        for animating in (0,1) for f in (0,1,2) for base in (-1,0,7)
        for jumping,success,subdamage in ((0,0,0),(1,0,1),(1,1,0))]


def events():
    e=loader_frames([dict(directive='anim',values=['idle'],line=1)])[0]['events']
    e.update(flipframe=1,unsummonframe=1,weapon_frame=1,weapon_number=2,weapon_keep=0,
             quake_start=0,quake_repeat=3,quake_value=-8,jump_frame=1,jump_y=.25,jump_x=1.5,jump_z=-.75,
             jump_entity='dust',spawn_frame=1,summon_frame=1,subentity='effect',
             throw_frame=1,shoot_frame=1,toss_frame=1)
    return e


def expected(c):
    anim=Animation([Frame(base=c['base'],x=3,y=2,z=-1,delay=6,sound=-1),
                    Frame(base=22,x=5,y=0,z=4,delay=8,sound=7)],events(),1 if c['f']==1 else 0)
    other=Animation([Frame()],events())
    ent=Entity(anim,frame=0,animating=c['animating'],direction=c['direction'],base=-2,
               altbase=3,movex=10,movez=20,subentity=Entity(other,takedamage=bool(c['subdamage'])),jumping=bool(c['jumping']))
    sentinel=Entity(other);dust=Entity(other)
    owner=Owner(time=c['time'],level=bool(c['level']),quake=99,self_entity=sentinel)
    trace=[]
    for service,target in update_frame(owner,ent,c['f']):
        trace.append(int(service))
        if service==Service.ANIMATION_SCRIPT:
            if c['mode']==1:ent.frame=0 if c['f']==1 else 1
            elif c['mode']==2:ent.animation=other
            elif c['mode']==3:ent.exists=False
        elif service==Service.SET_IDLE and c['mode']==4:
            ent.animation=other;ent.frame=0
        elif service in (Service.UNSUMMON_DAMAGE,Service.UNSUMMON_KILL):target.exists=False
        elif service==Service.TOSS:
            ent.vy=.25;ent.altitude+=.5;ent.toss_time=(owner.time+1)&0xffffffff
        elif service==Service.DUST_BIRTH:owner.dust=dust if c['success'] else None
        elif service in (Service.THROW_STAR,Service.THROW_KNIFE):owner.projectile_succeeded=bool(c['success'])
    state=[ent.frame,ent.nextanim,ent.pausetime,ent.direction,ent.movex,ent.movez,ent.base,ent.altbase,
           owner.quake,anim.quake_count,ent.vx,ent.vz,ent.vy,ent.altitude,ent.toss_time,
           int(ent.subentity is not None),int(ent.reactive),int(owner.self_entity is sentinel),
           dust.base,dust.autokill,int(ent.exists),int(ent.animation is anim)]
    return dict(trace=trace,state=state)


def derive(engine,folder):
    folder.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=engine)
    functions='\n\n'.join(extract(raw.decode('latin1'),n) for n in ('toss','update_frame'))
    rows=cases()
    fixtures=',\n'.join('{'+','.join(str(c[k])+('u' if k=='time' else '') for k in
        ('mode','level','direction','animating','f','base','jumping','success','subdamage','time'))+'}' for c in rows)
    source=r'''#include <stdio.h>
#include <string.h>
#define DIRECTION_LEFT 0
#define DIRECTION_RIGHT 1
typedef struct {float x,z,y;int base;} s_axis_f;
typedef struct {s_axis_f dropv;int attack_force,attack_type;} s_attack;
typedef struct {int frame,ent;s_axis_f velocity;} jumpinfo;
typedef struct {int numframes,index;int delay[2];s_axis_f *move[2];
 int flipframe,*weaponframe;struct {int framestart,cnt,repeat,v;} quakeframe;
 int unsummonframe,*spawnframe,*summonframe,subentity,*soundtoplay;jumpinfo jumpframe;
 struct {int throwframe,shootframe,tossframe,knife,flash,star;s_axis_f position;} projectile;} s_anim;
typedef struct entity {s_anim *animation;int animpos,animating,direction,health,dead,jumping,reactive,exists,autokill;
 unsigned nextanim,pausetime,toss_time;float movex,movez,base,altbase;s_axis_f velocity,position;
 struct entity *subentity;void (*takedamage)(struct entity *,s_attack *);} entity;
typedef struct {int quake;} levelstruct;
typedef struct {int mode,level,direction,animating,f,base,jumping,success,subdamage;unsigned time;} fixture;
entity *self,pool,sub,dust,sentinel;s_anim anim,other;levelstruct lv,*level;
s_attack emptyattack;s_axis_f default_model_dropv;struct {int effectvol;} savedata;
int max_attack_types=17;unsigned time;fixture *test;int trace[64],trace_count;
void event(int n){trace[trace_count++]=n;}
int calculate_edelay(entity *e,int f){return e->animation->delay[f];}
void execute_animation_script(entity *e){event(1);if(test->mode==1)e->animpos=test->f==1?0:1;
 else if(test->mode==2)e->animation=&other;else if(test->mode==3)e->exists=0;}
void dropweapon(int n){event(2);}
void set_weapon(entity *e,int n,int mode){event(3);}
void set_idle(entity *e){event(4);if(test->mode==4){e->animation=&other;e->animpos=0;}}
void damage(entity *e,s_attack *a){event(5);e->exists=0;}
void kill(entity *e){event(6);e->exists=0;}
void ent_spawn_ent(entity *e){event(7);}
void ent_summon_ent(entity *e){event(8);}
void sound_play_sample(int sample,int priority,int l,int r,int rate){event(9);}
entity *spawn(float x,float z,float y,int dir,char *name,int model,void *p){event(11);return test->success?&dust:NULL;}
void execute_onspawn_script(entity *e){event(12);}
entity *knife_spawn(char *name,int model,float x,float z,float y,int dir,int shoot,int b){event(shoot?15:13);return test->success?&dust:NULL;}
entity *star_spawn(float x,float z,float y,int dir){event(14);return test->success?&dust:NULL;}
void bomb_spawn(char *name,int model,float x,float z,float y,int dir,int b){event(16);}
''' + functions.replace('void toss(entity *ent, float lift)\n{','void toss(entity *ent, float lift)\n{\n    event(10);') + r'''
fixture cases[]={''' + fixtures + r'''};
int main(void){unsigned i;int n,weapon[3]={1,2,0},spawnframe[5]={1,0,0,0,0},summonframe[5]={1,0,0,0,0},sounds[2]={-1,7};s_axis_f move[2];
 if(sizeof(long)!=4||sizeof(void *)!=4||sizeof(unsigned)!=4)return 2;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
 test=&cases[i];memset(&pool,0,sizeof(pool));memset(&sub,0,sizeof(sub));memset(&dust,0,sizeof(dust));
 memset(&anim,0,sizeof(anim));memset(&other,0,sizeof(other));memset(move,0,sizeof(move));trace_count=0;
 anim.numframes=2;anim.delay[0]=6;anim.delay[1]=8;anim.move[0]=move;anim.move[1]=move+1;
 move[0].base=test->base;move[0].x=3;move[0].y=2;move[0].z=-1;
 move[1].base=22;move[1].x=5;move[1].y=0;move[1].z=4;
 anim.flipframe=1;anim.unsummonframe=1;anim.weaponframe=weapon;anim.spawnframe=spawnframe;anim.summonframe=summonframe;
 anim.quakeframe.framestart=0;anim.quakeframe.cnt=test->f==1;anim.quakeframe.repeat=3;anim.quakeframe.v=-8;
 anim.subentity=0;anim.soundtoplay=sounds;anim.jumpframe.frame=1;anim.jumpframe.ent=0;
 anim.jumpframe.velocity.y=.25;anim.jumpframe.velocity.x=1.5;anim.jumpframe.velocity.z=-.75;
 anim.projectile.throwframe=anim.projectile.shootframe=anim.projectile.tossframe=1;
 anim.projectile.knife=anim.projectile.flash=anim.projectile.star=-1;
 pool.animation=&anim;pool.animating=test->animating;pool.direction=test->direction;pool.base=-2;pool.altbase=3;
 pool.movex=10;pool.movez=20;pool.pausetime=123;pool.position.y=10;pool.toss_time=123;pool.subentity=&sub;
 pool.exists=1;pool.jumping=test->jumping;sub.health=7;sub.takedamage=test->subdamage?damage:NULL;
 time=test->time;self=&sentinel;lv.quake=99;level=test->level?&lv:NULL;
 update_frame(&pool,test->f);
 printf("UFAUTH|%u|",i);for(n=0;n<trace_count;n++)printf("%s%d",n?",":"",trace[n]);
 printf("|%d,%u,%u,%d,%.9g,%.9g,%.9g,%.9g,%d,%d,%.9g,%.9g,%.9g,%.9g,%u,%d,%d,%d,%.9g,%d,%d,%d\n",
 pool.animpos,pool.nextanim,pool.pausetime,pool.direction,pool.movex,pool.movez,pool.base,pool.altbase,
 lv.quake,anim.quakeframe.cnt,pool.velocity.x,pool.velocity.z,pool.velocity.y,pool.position.y,pool.toss_time,
 pool.subentity!=NULL,pool.reactive,self==&sentinel,dust.base,dust.autokill,pool.exists,pool.animation==&anim);
 }return 0;}
'''
    # Instrument only the toss entry. Its body and update_frame remain verbatim.
    if 'event(10);' not in source:raise ValueError('UPDATE_FRAME_TOSS_ENTRY_NOT_FOUND')
    (folder/'update_frame.c').write_text(source)
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    proc=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','update_frame.c','-fe=uf_authority.exe'],
        cwd=folder,env=env,capture_output=True,text=True)
    (folder/'build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('UPDATE_FRAME_AUTHORITY_BUILD')
    output=subprocess.check_output([str((folder/'uf_authority.exe').resolve())],cwd=folder,text=True)
    results=[]
    for line in output.splitlines():
        if not line.startswith('UFAUTH|'):continue
        _,index,trace,state=line.split('|');index=int(index)
        actual=dict(trace=[int(n) for n in trace.split(',')] if trace else [],state=[float(n) for n in state.split(',')])
        wanted=expected(rows[index]);results.append(dict(case=rows[index],actual=actual,expected=wanted,passed=actual==wanted))
    report=dict(schema='BYOR_4086_UPDATE_FRAME_AUTHORITY_V1',
        status='PASS' if len(results)==len(rows) and all(r['passed'] for r in results) else 'FAIL',
        engine_commit=ENGINE_COMMIT,engine_source_sha256=hashlib.sha256(raw).hexdigest(),
        functions_sha256=hashlib.sha256(functions.encode('latin1')).hexdigest(),cases=len(rows),results=results,
        scope='Pinned frame mutation, interruption, ordering, movement, base, quake, facing and self restoration; external handlers instrumented',
        external_handlers_bound=False,native_owner_bound=False,motu_gameplay_proven=False)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=derive(a.engine,a.output.resolve())
    print(json.dumps({k:r[k] for k in ('status','cases','functions_sha256')}))
    if r['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
