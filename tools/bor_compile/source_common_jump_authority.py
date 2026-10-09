"""Unchanged common_jump/common_jumpland and actual source inair predicate."""
import argparse, hashlib, itertools, json, os, struct, subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_model_core_4086 import binary32
from source_common_jump_4086 import execute, jumpland, Service


def bits(value):return struct.unpack('<I',struct.pack('<f',value))[0]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    source=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
    helpers={n:extract(source,n)for n in('diff','inair','common_jump','common_jumpland')}
    names=('height','vy','runhold','valid','landframe','animating','dust','spawn_ok','mutation')
    heights=(0.,.0999999,.1,.1000001,2.)
    rows=[dict(zip(names,values))for values in itertools.product(range(len(heights)),(-1,0,1),(0,-3),(0,1),(-2,-1,0,3),(0,-3),(-1,7),(0,1),(0,1))]
    code=r'''
#include <stdio.h>
#include <string.h>
#include <io.h>
#include <fcntl.h>
typedef unsigned int u32;
typedef struct {float x,y,z;} axis;
typedef struct {struct {int frame;}landframe;} Animation;
typedef struct entity {void(*takeaction)(void);axis position,velocity;float base;int direction,jumping,idling,attacking,running,animating,autokill;Animation *animation;struct {int runhold;struct {int jump_land;}dust;}modeldata;} entity;
entity e,d,*self=&e;Animation anim;
u32 h;int available,spawn_ok,mutation,frames,spawns,onspawns,idles;
u32 bits(float f){u32 v;memcpy(&v,&f,4);return v;}
void mark(u32 v){h=(h^v)*16777619u;}
void common_jumpland(void);void old_action(void){}
#define ANI_JUMPLAND 107
int validanim(entity *e,int role){mark(100+role);return available;}
void ent_set_anim(entity *e,int role,int reset){mark(1);mark(role);mark(reset);frames++;if(mutation){e->modeldata.dust.jump_land=9;e->position.y=11;e->animating=0;}}
entity *spawn(float x,float z,float y,int direction,void *name,int model,void *map){mark(2);mark(bits(x));mark(bits(z));mark(bits(y));mark(direction);mark(model);spawns++;if(mutation)e.position.y=12;return spawn_ok?&d:NULL;}
void execute_onspawn_script(entity *dust){mark(3);mark(bits(dust->base));mark(dust->autokill);onspawns++;if(mutation){anim.landframe.frame=2;e.animating=-5;e.running=13;}}
void set_idle(entity *e){mark(4);mark(e->takeaction==NULL);idles++;e->idling=1;e->direction=1;}
'''+ '\n'.join(helpers.values())+'\n'
    code+='int rows[][9]={'+',\n'.join('{'+','.join(str(c[n])for n in names)+'}'for c in rows)+'};\nfloat heights[]={0.f,.0999999f,.1f,.1000001f,2.f};\n'
    code+=r'''
int main(void){unsigned i;int *r;u32 v[17];setmode(fileno(stdout),O_BINARY);if(sizeof(u32)!=4||sizeof(void*)!=4)return 3;
for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){r=rows[i];memset(&e,0,sizeof(e));memset(&d,0,sizeof(d));memset(&anim,0,sizeof(anim));e.animation=&anim;e.takeaction=old_action;e.position.x=2;e.position.y=heights[r[0]];e.position.z=3;e.velocity.x=4;e.velocity.y=r[1];e.velocity.z=5;e.base=0;e.jumping=-7;e.attacking=-3;e.running=-5;e.idling=6;e.direction=0;e.modeldata.runhold=r[2];available=r[3];anim.landframe.frame=r[4];e.animating=r[5];e.modeldata.dust.jump_land=r[6];spawn_ok=r[7];mutation=r[8];d.base=-1;d.autokill=-2;h=2166136261u;frames=spawns=onspawns=idles=0;
common_jump();if(e.takeaction==common_jumpland)common_jumpland();
v[0]=h;v[1]=e.takeaction==NULL?0:e.takeaction==common_jumpland?20:19;v[2]=bits(e.position.y);v[3]=bits(e.velocity.x);v[4]=bits(e.velocity.y);v[5]=bits(e.velocity.z);v[6]=e.jumping;v[7]=e.attacking;v[8]=e.running;v[9]=e.idling;v[10]=e.animating;v[11]=bits(d.base);v[12]=d.autokill;v[13]=frames;v[14]=spawns;v[15]=onspawns;v[16]=idles;fwrite(v,4,17,stdout);}return 0;}
'''
    (out/'common_jump.c').write_text(code)
    build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','common_jump.c','-fe=common_jump.exe'],cwd=out,env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT'),capture_output=True,text=True);(out/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise ValueError('COMMON_JUMP_AUTHORITY_BUILD')
    actual=subprocess.check_output([str(out/'common_jump.exe')],cwd=out);expected=bytearray()
    for c in rows:
        e=dict(takeaction='COMMON_JUMP',position=dict(x=2,y=binary32(heights[c['height']]),z=3),velocity=dict(x=4,y=c['vy'],z=5),base=0,direction=0,jumping=-7,attacking=-3,running=-5,idling=6,animating=c['animating'],modeldata=dict(runhold=c['runhold'],dust_jump_land=c['dust']),animation=dict(landframe=c['landframe']))
        dust=dict(base=-1,autokill=-2);trace=[];counts=[0]*4
        def valid(role):trace.append(100+role);return c['valid']
        def run(gen):
            result=None
            while True:
                try:request=gen.send(result)
                except StopIteration:return
                result=None;service=request[0];counts[service-1]+=1;trace.append(int(service))
                if service==Service.SET_ANIMATION:
                    trace.extend(request[1:])
                    if c['mutation']:e['modeldata']['dust_jump_land']=9;e['position']['y']=11;e['animating']=0
                elif service==Service.SPAWN:
                    trace.extend([bits(v)for v in request[1:4]]+[request[4],request[6]])
                    if c['mutation']:e['position']['y']=12
                    result=dust if c['spawn_ok']else None
                elif service==Service.ONSPAWN:
                    trace.extend((bits(dust['base']),dust['autokill']))
                    if c['mutation']:e['animation']['landframe']=2;e['animating']=-5;e['running']=13
                elif service==Service.SET_IDLE:trace.append(e['takeaction']is None);e['idling']=1;e['direction']=1
        run(execute(e,107,valid))
        if e['takeaction']=='COMMON_JUMPLAND':run(jumpland(e))
        h=2166136261
        for value in trace:h=((h^(int(value)&0xffffffff))*16777619)&0xffffffff
        v=(h,0 if e['takeaction']is None else 20 if e['takeaction']=='COMMON_JUMPLAND'else 19,bits(e['position']['y']),bits(e['velocity']['x']),bits(e['velocity']['y']),bits(e['velocity']['z']),e['jumping'],e['attacking'],e['running'],e['idling'],e['animating'],bits(dust['base']),dust['autokill'],*counts)
        expected.extend(struct.pack('<17I',*(int(n)&0xffffffff for n in v)))
    report=dict(schema='BYOR_4086_COMMON_JUMP_AUTHORITY_V1',status='PASS'if actual==expected else'FAIL',engine_commit=ENGINE_COMMIT,literal_bodies_unmodified=True,literal_body_sha256={k:hashlib.sha256(v.encode()).hexdigest()for k,v in helpers.items()},cases=len(rows),compared_bytes=len(expected),actual_sha256=hashlib.sha256(actual).hexdigest(),expected_sha256=hashlib.sha256(expected).hexdigest(),external_services_and_callback_mutations_instrumented=True,native_bound=False,motu_gameplay_proven=False)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'common jump authority cases')
    if actual!=expected:
        first=next(i for i,(x,y)in enumerate(zip(actual,expected))if x!=y);raise AssertionError(('COMMON_JUMP_MISMATCH',first//68,first%68,rows[first//68]))


if __name__=='__main__':main()
