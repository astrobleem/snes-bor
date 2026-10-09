"""Unchanged 4086 jump entry, tryjump and common_prejump with external dojump."""
import argparse,hashlib,itertools,json,os,struct,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_model_core_4086 import binary32
from source_player_jump_entry_4086 import execute,try_jump,common_prejump,Service


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    source=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1');full=extract(source,'player_think')
    start=full.index('    if(pl->playkeys & FLAG_JUMP  && notinair)');body=full[start:full.index('    //dang long run checking logic',start)]
    helpers={n:extract(source,n)for n in('tryjump','common_prejump')}
    names=('play','air','held','running','jumpvalid','delayvalid','animating','mutation','movez')
    rows=[dict(zip(names,v))for v in itertools.product((0,128,0x80000080),(0,1),(0,4,8,12,32,36,48,60),(0,-3,65536),(0,1),(0,1),(0,-3),(0,1),(0,-2))]
    code=r'''
#include <stdio.h>
#include <string.h>
#include <io.h>
#include <fcntl.h>
typedef unsigned int u32;
#define FLAG_JUMP 128
#define FLAG_MOVEDOWN 32
#define FLAG_MOVELEFT 4
#define FLAG_MOVERIGHT 8
#define ANI_SLIDE 0
#define ANI_RUNSLIDE 1
#define ANI_RUNJUMP 2
#define ANI_FORWARDJUMP 3
#define ANI_JUMP 4
#define ANI_JUMPDELAY 5
#define DIRECTION_LEFT 0
#define DIRECTION_RIGHT 1
typedef struct {float x,y,z;} axis;
typedef struct {axis velocity;int id;} jumpinfo;
typedef struct entity{void(*takeaction)(void);int running,idling,attacking,direction,animating,combostep[5];axis velocity;jumpinfo jump;struct {float jumpheight,jumpspeed,runjumpheight,runjumpdist;int jumpmovez;} modeldata;} entity;
entity e,*self=&e;
struct player {u32 playkeys,keys;} plr;
int notinair,jumpvalid,delayvalid,mutation,continuation,docalls,frames;
float args[3];int argrole;u32 h;
void mark(u32 n){h=(h^n)*16777619u;}
void old_action(void){}void common_attack_proc(void){}void common_prejump(void);
void set_attacking(entity *e){e->attacking=1;e->idling=0;}
int validanim(entity *e,int role){mark(100+role);return role==ANI_JUMP?jumpvalid:role==ANI_JUMPDELAY?delayvalid:0;}
void dojump(float y,float x,float z,int id){mark(200+id);args[0]=y;args[1]=x;args[2]=z;argrole=id;docalls++;}
void ent_set_anim(entity *e,int role,int reset){mark(300+role);frames++;if(mutation){e->jump.velocity.y=11;e->jump.velocity.x=12;e->jump.velocity.z=13;e->jump.id=99;e->direction=1;}}
'''+helpers['tryjump']+'\n'+helpers['common_prejump']+'\nvoid probe(void){struct player *pl=&plr;\n'+body+'continuation=1;\nendthinkcheck:return;}\n'
    code+='u32 rows[][9]={'+',\n'.join('{'+','.join(str(c[n]&0xffffffff)+'u'for n in names)+'}'for c in rows)+'};\n'
    code+=r'''
u32 bits(float f){u32 v;memcpy(&v,&f,4);return v;}
int main(void){unsigned i;u32 *r,v[19];setmode(fileno(stdout),O_BINARY);if(sizeof(u32)!=4||sizeof(void*)!=4)return 3;
for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){r=rows[i];memset(&e,0,sizeof(e));memset(&plr,0,sizeof(plr));e.takeaction=old_action;e.idling=7;e.running=(int)r[3];e.direction=0;e.velocity.x=2;e.velocity.z=3;e.jump.velocity.y=-1;e.jump.velocity.x=-2;e.jump.velocity.z=-3;e.jump.id=77;e.modeldata.jumpheight=4.5f;e.modeldata.runjumpheight=5.25f;e.modeldata.jumpspeed=.7f;e.modeldata.runjumpdist=1.3f;e.modeldata.jumpmovez=(int)r[8];plr.playkeys=r[0];plr.keys=r[2];notinair=r[1];jumpvalid=r[4];delayvalid=r[5];mutation=r[7];continuation=docalls=frames=0;args[0]=args[1]=args[2]=0;argrole=0;h=2166136261u;probe();e.animating=(int)r[6];if(e.takeaction==common_prejump)common_prejump();
v[0]=h;v[1]=continuation;v[2]=plr.playkeys;v[3]=e.takeaction==common_prejump?18:9;v[4]=e.direction;v[5]=e.idling;v[6]=bits(e.velocity.x);v[7]=bits(e.velocity.z);v[8]=bits(e.jump.velocity.y);v[9]=bits(e.jump.velocity.x);v[10]=bits(e.jump.velocity.z);v[11]=e.jump.id;v[12]=docalls;v[13]=frames;v[14]=bits(args[0]);v[15]=bits(args[1]);v[16]=bits(args[2]);v[17]=argrole;v[18]=e.animating;fwrite(v,4,19,stdout);}return 0;}
'''
    (out/'jump_entry.c').write_text(code);build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','jump_entry.c','-fe=jump_entry.exe'],cwd=out,env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT'),capture_output=True,text=True);(out/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise ValueError('PLAYER_JUMP_ENTRY_SOURCE_BUILD')
    actual=subprocess.check_output([str(out/'jump_entry.exe')],cwd=out);expected=bytearray()
    def bits(n):return struct.unpack('<I',struct.pack('<f',n))[0]
    for c in rows:
        e=dict(takeaction=9,idling=7,running=c['running'],direction=0,velocity=dict(x=2,z=3),jump=dict(y=-1,x=-2,z=-3,id=77),modeldata=dict(jumpheight=4.5,runjumpheight=5.25,jumpspeed=binary32(.7),runjumpdist=binary32(1.3),jumpmovez=c['movez']))
        player=dict(playkeys=c['play'],keys=c['held']);roles=dict(slide=0,runslide=1,runjump=2,forwardjump=3,jump=4,jumpdelay=5);trace=[];counts=dict(direct=0,frames=0,args=[0,0,0,0])
        def valid(role):trace.append(100+role);return c['jumpvalid']if role==4 else c['delayvalid']if role==5 else 0
        def run(gen):
            while True:
                try:s=next(gen)
                except StopIteration as done:return done.value
                if s[0]==Service.TRY_JUMP:run(try_jump(e,roles,valid,*s[1:]))
                elif s[0]==Service.SET_ANIMATION:
                    trace.append(300+s[1]);counts['frames']+=1
                    if c['mutation']:e['jump']=dict(y=11,x=12,z=13,id=99);e['direction']=1
                elif s[0]==Service.DO_JUMP:
                    trace.append(200+s[4]);counts['direct']+=1;counts['args']=list(s[1:])
                else:raise AssertionError('JUMP_ENTRY_UNKNOWN_SERVICE')
        result=run(execute(e,player,c['air'],roles,valid));e['animating']=c['animating']
        if e['takeaction']=='COMMON_PREJUMP':run(common_prejump(e))
        h=2166136261
        for n in trace:h=((h^n)*16777619)&0xffffffff
        jump=e['jump'];args=counts['args'];v=(h,result=='CONTINUE',player['playkeys'],18 if e['takeaction']=='COMMON_PREJUMP'else 9,e['direction'],e['idling'],bits(e['velocity']['x']),bits(e['velocity']['z']),bits(jump['y']),bits(jump['x']),bits(jump['z']),jump['id'],counts['direct'],counts['frames'],bits(args[0]),bits(args[1]),bits(args[2]),args[3],e['animating'])
        expected.extend(struct.pack('<19I',*(int(n)&0xffffffff for n in v)))
    report=dict(schema='BYOR_4086_PLAYER_JUMP_ENTRY_AUTHORITY_V1',status='PASS'if actual==expected else'FAIL',engine_commit=ENGINE_COMMIT,literal_entry_sha256=hashlib.sha256(body.encode()).hexdigest(),literal_helper_sha256={k:hashlib.sha256(v.encode()).hexdigest()for k,v in helpers.items()},literal_bodies_unmodified=True,cases=len(rows),compared_bytes=len(expected),actual_sha256=hashlib.sha256(actual).hexdigest(),expected_sha256=hashlib.sha256(expected).hexdigest(),dojump_service_instrumented=True,frame_mutations_instrumented=True,pending_descriptor_owner_bound=False,native_bound=False,motu_gameplay_proven=False)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'jump-entry authority cases');assert actual==expected


if __name__=='__main__':main()
