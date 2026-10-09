"""Compare the unchanged ordinary-attack block in its explicit empty-item lane."""
import argparse,hashlib,itertools,json,os,struct,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_player_attack_4086 import execute,Service


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    source=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1');full=extract(source,'player_think')
    start=full.index('    if((pl->playkeys & FLAG_ATTACK)');body=full[start:full.index('    // 7-1-2005 spawn projectile end',start)]
    names=('play','air','held','running','runvalid','getvalid','weapon','picked','sample','mutation','attacking')
    rows=[dict(zip(names,v))for v in itertools.product((0,64,0x80000040),(0,1),(0,32),(0,-3,65536),(0,1),(0,1),(0,1,9),(0,1),(-1,26),(0,1),(0,-3))]
    code=r'''
#include <stdio.h>
#include <string.h>
#include <io.h>
#include <fcntl.h>
#define FLAG_ATTACK 64
#define FLAG_MOVEDOWN 32
#define FLAG_MOVELEFT 4
#define FLAG_MOVERIGHT 8
#define GAME_SPEED 200
#define MAX_SPECIAL_INPUTS 27
#define ANI_DUCKATTACK 0
#define ANI_RUNATTACK 1
#define ANI_ATTACKBACKWARD 2
#define ANI_GET 3
#define ANI_THROWATTACK 4
#define TYPE_ITEM 4
#define SUBTYPE_PROJECTILE 9
#define DIRECTION_LEFT 0
#define DIRECTION_RIGHT 1
typedef unsigned int u32;
typedef struct entity{void(*takeaction)(void);int attacking,idling,running,getting,direction,combostep[5];u32 stalltime;struct{float x,z;}velocity,position;struct entity *weapent;struct{int subtype;}modeldata;}entity;
entity e,*self=&e,weapon;
struct player{u32 playkeys,keys,inputtime[27],combokey[27];int combostep;}plr;
struct{int effectvol;}savedata;
int runvalid,getvalid,picked,mutation,SAMPLE_PUNCH,notinair,t,t2,PLAYER_MIN_Z,PLAYER_MAX_Z,ba[2],continuation,sounds,frames,selected;
u32 time,h;
void mark(u32 n){h=(h^n)*16777619u;}
void old_action(void){}void common_attack_proc(void){}void common_get(void){}
void set_attacking(entity *e){e->attacking=1;e->idling=0;}
void set_getting(entity *e){e->getting=1;e->idling=0;}
int validanim(entity *e,int role){mark(100+role);return role==ANI_RUNATTACK?runvalid:role==ANI_GET?getvalid:0;}
int match_combo(int *a,struct player *p,int n){mark(900);return 0;}
int player_test_pickable(entity *e,entity *item){return 0;}
entity *find_ent_here(entity *e,float x,float z,int type,int(*test)(entity*,entity*)){mark(400);return 0;}
void execute_didhit_script(entity *a,entity *b,int c,int d,int e,int f,int g,int h,int i,int j){mark(901);}
void didfind_item(entity *a){mark(902);}
void mutate(void){self->stalltime=123;self->idling=-9;self->combostep[0]=5;self->velocity.x=9;self->velocity.z=-9;self->running=55;}
void ent_set_anim(entity *e,int role,int reset){mark(300+role);frames++;selected=role;if(mutation)mutate();}
int perform_atchain(void){mark(500);if(picked){self->takeaction=common_attack_proc;set_attacking(self);self->combostep[0]=0;}if(mutation){mutate();self->attacking=0;}return picked;}
void sound_play_sample(int a,int b,int c,int d,int pitch){mark(200+a);sounds++;}
void probe(void){struct player *pl=&plr;entity *other;
'''+body+'continuation=1;\nendthinkcheck:return;}\n'
    code+='u32 rows[][11]={'+',\n'.join('{'+','.join(str(c[n]&0xffffffff)+'u'for n in names)+'}'for c in rows)+'};\n'
    code+=r'''
int main(void){unsigned i,j;u32 *r,v[14];setmode(fileno(stdout),O_BINARY);if(sizeof(u32)!=4||sizeof(void*)!=4)return 3;
for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){r=rows[i];memset(&e,0,sizeof(e));memset(&plr,0,sizeof(plr));e.takeaction=old_action;e.attacking=(int)r[10];e.idling=7;e.running=(int)r[3];e.stalltime=99;e.combostep[0]=3;e.combostep[1]=4;e.velocity.x=2;e.velocity.z=3;weapon.modeldata.subtype=r[6];e.weapent=r[6]?&weapon:0;plr.playkeys=r[0];plr.keys=r[2];notinair=r[1];runvalid=r[4];getvalid=r[5];picked=r[7];SAMPLE_PUNCH=(int)r[8];mutation=r[9];time=0xffffffffu;h=2166136261u;continuation=sounds=frames=0;selected=99;probe();
v[0]=h;v[1]=continuation;v[2]=plr.playkeys;v[3]=e.takeaction==common_attack_proc?17:e.takeaction==common_get?98:9;v[4]=e.attacking;v[5]=e.idling;v[6]=e.running;v[7]=e.stalltime;v[8]=e.combostep[0];v[9]=e.combostep[1];v[10]=(int)e.velocity.x;v[11]=(int)e.velocity.z;v[12]=sounds;v[13]=frames;fwrite(v,4,14,stdout);}return 0;}
'''
    (out/'attack.c').write_text(code);build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','attack.c','-fe=attack.exe'],cwd=out,env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT'),capture_output=True,text=True);(out/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise ValueError('PLAYER_ATTACK_SOURCE_BUILD')
    actual=subprocess.check_output([str(out/'attack.exe')],cwd=out);expected=b''
    for c in rows:
        e=dict(takeaction=9,attacking=c['attacking'],idling=7,running=c['running'],stalltime=99,combostep=[3,4,0,0,0],velocity=dict(x=2,z=3),weapent=dict(subtype=c['weapon'])if c['weapon']else None)
        player=dict(playkeys=c['play'],keys=c['held']);ctx=dict(time=0xffffffff,sample_punch=c['sample'],projectile_subtype=9,roles=dict(duckattack=0,runattack=1,attackbackward=2,get=3,throwattack=4));trace=[]
        def valid(role):trace.append(100+role);return c['runvalid']if role==1 else c['getvalid']if role==3 else 0
        def mutate():e.update(stalltime=123,idling=-9,running=55);e['combostep'][0]=5;e['velocity'].update(x=9,z=-9)
        gen=execute(e,ctx,player,c['air'],valid);sounds=frames=0;reply=None
        while True:
            try:s=gen.send(reply)
            except StopIteration as done:result=done.value;break
            reply=None
            if s==Service.FIND_ITEM_EMPTY:trace.append(400);reply=True
            elif s==Service.ATTACK_CHAIN:
                trace.append(500);reply=c['picked']
                if reply:e.update(takeaction=17,attacking=1,idling=0);e['combostep'][0]=0
                if c['mutation']:mutate();e['attacking']=0
            elif s==Service.PUNCH:trace.append(200+c['sample']);sounds+=1
            else:
                kind,role,reset=s;assert kind==Service.SET_ANIMATION and reset==0;trace.append(300+role);frames+=1
                if c['mutation']:mutate()
        h=2166136261
        for n in trace:h=((h^n)*16777619)&0xffffffff
        v=(h,result=='CONTINUE',player['playkeys'],e['takeaction'],e['attacking'],e['idling'],e['running'],e['stalltime'],e['combostep'][0],e['combostep'][1],e['velocity']['x'],e['velocity']['z'],sounds,frames)
        expected+=struct.pack('<14I',*(int(n)&0xffffffff for n in v))
    # A live item is outside this lane; it must never become a silent miss.
    guard_entity=dict(stalltime=99,running=0,attacking=0,idling=1,takeaction=9,combostep=[3,4,0,0,0],velocity=dict(x=2,z=3),weapent=None)
    guard_context=dict(roles=dict(duckattack=0,runattack=1,attackbackward=2,get=3,throwattack=4),time=50,sample_punch=26,projectile_subtype=9)
    gen=execute(guard_entity,guard_context,dict(keys=0,playkeys=64),1,lambda role:role==3)
    assert next(gen)==Service.FIND_ITEM_EMPTY
    try:gen.send(False)
    except ValueError as error:assert str(error)=='PLAYER_ATTACK_ITEM_OWNER_REQUIRED'
    else:raise AssertionError('PLAYER_ATTACK_UNOWNED_ITEM_ADMITTED')
    report=dict(schema='BYOR_4086_PLAYER_ATTACK_AUTHORITY_V1',status='PASS'if actual==expected else'FAIL',engine_commit=ENGINE_COMMIT,literal_body_sha256=hashlib.sha256(body.encode()).hexdigest(),literal_body_unmodified=True,cases=len(rows),compared_bytes=len(expected),actual_sha256=hashlib.sha256(actual).hexdigest(),expected_sha256=hashlib.sha256(expected).hexdigest(),item_search_result='INSTRUMENTED_EMPTY_ONLY',nonempty_item_service_rejections=1,chain_and_frame_mutations_instrumented=True,physical_punch_backend_bound=False,native_bound=False,motu_gameplay_proven=False)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'ordinary attack authority cases');assert actual==expected

if __name__=='__main__':main()
