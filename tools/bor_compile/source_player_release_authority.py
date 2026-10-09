"""Unchanged player attack-release body with observed sound/frame services."""
import argparse,hashlib,itertools,json,os,struct,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_player_release_4086 import execute,Service
from source_u32_float_threshold_4086 import compare

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    source=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1');full=extract(source,'player_think');body=full[full.index('    if((pl->releasekeys'):full.index('    if((pl->playkeys & FLAG_ATTACK)')]
    names=('release','notinair','stall','time','present','length','sample','mutation');rows=[dict(zip(names,r))for r in itertools.product((0,64,0x80000040),(0,1),(0,1,65536,0xffffffff),(0,400,401,402,0xffffffff),(0,1),(0,1),(-1,3),(0,1))]
    undefined=[c for c in rows if c['release']&64 and c['notinair'] and c['stall'] and c['present'] and not c['length'] and c['sample']>=0 and c['mutation'] and compare(c['stall'],c['time'],400)]
    rows=[c for c in rows if c not in undefined]
    code=r"""
#include <stdio.h>
#include <string.h>
#include <io.h>
#include <fcntl.h>
#define FLAG_ATTACK 64
#define GAME_SPEED 200
#define ANI_CHARGEATTACK 1
typedef unsigned int u32;
struct anim{float chargetime;}anims[4];
struct entity{void(*takeaction)(void);int attacking,idling,combostep[5];u32 stalltime;struct{float x,z;}velocity;struct{int chainlength,atchain[2];struct anim *animation[4];}modeldata;}e,*self=&e;
struct player{u32 releasekeys;}player;struct{int effectvol;}savedata;
int animattacks[2]={2,3};int present,notinair,SAMPLE_PUNCH,mutation,continuation,sounds,frames,selected;u32 time,h;
void mark(u32 n){h=(h^n)*16777619u;}void common_attack_proc(void){}void old_action(void){}
void set_attacking(struct entity *e){e->attacking=1;e->idling=0;}
int validanim(struct entity *e,int a){mark(100+a);return a==1?present:1;}
void sound_play_sample(int a,int b,int c,int d,int f){mark(200+a);sounds++;if(mutation){present=!present;e.stalltime=99;e.idling=-9;e.combostep[0]=7;e.modeldata.atchain[0]=2;}}
void ent_set_anim(struct entity *e,int a,int reset){mark(300+a);frames++;selected=a;if(mutation){e->stalltime=123;e->combostep[0]=5;e->velocity.x=9;e->velocity.z=-9;}}
void probe(void){struct player *pl=&player;
"""+body+'continuation=1;\nendthinkcheck:return;}\n'
    code+='u32 rows[][8]={'+',\n'.join('{'+','.join(str(c[k]&0xffffffff)+'u'for k in names)+'}'for c in rows)+'};\n'
    code+=r"""
int main(void){unsigned i,j;u32 *r,result[13];setmode(fileno(stdout),O_BINARY);if(sizeof(u32)!=4||sizeof(void*)!=4)return 3;
for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){r=rows[i];memset(&e,0,sizeof(e));player.releasekeys=r[0];notinair=r[1];e.stalltime=r[2];time=r[3];present=r[4];e.modeldata.chainlength=r[5];SAMPLE_PUNCH=(int)r[6];mutation=r[7];e.modeldata.atchain[0]=1;for(j=0;j<4;j++){anims[j].chargetime=2;e.modeldata.animation[j]=anims+j;}
e.takeaction=old_action;e.attacking=-5;e.idling=7;e.combostep[0]=3;e.combostep[1]=4;e.velocity.x=2;e.velocity.z=3;h=2166136261u;continuation=sounds=frames=selected=0;probe();result[0]=h;result[1]=continuation;result[2]=e.takeaction==common_attack_proc?17:9;result[3]=e.attacking;result[4]=e.idling;result[5]=e.stalltime;result[6]=e.combostep[0];result[7]=e.combostep[1];result[8]=(int)e.velocity.x;result[9]=(int)e.velocity.z;result[10]=sounds;result[11]=frames;result[12]=selected;fwrite(result,4,13,stdout);}return 0;}
"""
    (out/'release.c').write_text(code);build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','release.c','-fe=release.exe'],cwd=out,env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT'),capture_output=True,text=True);(out/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise ValueError('PLAYER_RELEASE_SOURCE_BUILD')
    actual=subprocess.check_output([str(out/'release.exe')],cwd=out);expected=b''
    for c in rows:
        e=dict(takeaction=9,attacking=-5,idling=7,stalltime=c['stall'],combostep=[3,4,0,0,0],velocity=dict(x=2,z=3),modeldata=dict(chainlength=c['length'],atchain=[1,0],animation={n:dict(chargetime=2)for n in(1,2,3)}))
        context=dict(time=c['time'],sample_punch=c['sample'],chargeattack=1,attacks=[2,3]);live=[c['present']];trace=[]
        def valid(a):trace.append(100+a);return live[0]if a==1 else 1
        gen=execute(e,context,dict(releasekeys=c['release']),c['notinair'],valid);sounds=frames=selected=0
        while True:
            try:s=next(gen)
            except StopIteration as done:result=done.value;break
            if s==Service.PUNCH:
                trace.append(200+c['sample']);sounds+=1
                if c['mutation']:live[0]=not live[0];e.update(stalltime=99,idling=-9);e['combostep'][0]=7;e['modeldata']['atchain'][0]=2
            else:
                kind,selected,reset=s;assert kind==Service.SET_ANIMATION and reset==0;frames+=1;trace.append(300+selected)
                if c['mutation']:e['stalltime']=123;e['combostep'][0]=5;e['velocity'].update(x=9,z=-9)
        h=2166136261
        for n in trace:h=((h^n)*16777619)&0xffffffff
        values=(h,result=='CONTINUE',e['takeaction'],e['attacking'],e['idling'],e['stalltime'],e['combostep'][0],e['combostep'][1],e['velocity']['x'],e['velocity']['z'],sounds,frames,selected)
        expected+=struct.pack('<13I',*(int(n)&0xffffffff for n in values))
    rejected=0
    for c in undefined:
        e=dict(takeaction=9,attacking=-5,idling=7,stalltime=c['stall'],combostep=[3,4,0,0,0],velocity=dict(x=2,z=3),modeldata=dict(chainlength=0,atchain=[1,0],animation={n:dict(chargetime=2)for n in(1,2,3)}))
        context=dict(time=c['time'],sample_punch=c['sample'],chargeattack=1,attacks=[2,3]);live=[1]
        gen=execute(e,context,dict(releasekeys=c['release']),c['notinair'],lambda a:live[0]if a==1 else 1)
        assert next(gen)==Service.PUNCH;live[0]=0
        try:next(gen)
        except ValueError as error:
            assert str(error)=='PLAYER_RELEASE_CHAIN_INDEX_UNDEFINED';rejected+=1
        else:raise AssertionError('PLAYER_RELEASE_UNDEFINED_SOURCE_DOMAIN_ADMITTED')
    report=dict(schema='BYOR_4086_PLAYER_RELEASE_AUTHORITY_V1',status='PASS'if actual==expected else'FAIL',engine_commit=ENGINE_COMMIT,player_think_sha256=hashlib.sha256(full.encode()).hexdigest(),literal_body_sha256=hashlib.sha256(body.encode()).hexdigest(),literal_body_unmodified=True,cases=len(rows),compared_bytes=len(expected),actual_sha256=hashlib.sha256(actual).hexdigest(),expected_sha256=hashlib.sha256(expected).hexdigest(),query_sound_frame_and_callback_mutations_instrumented=True,evaluation_policy='WIN32_X87_EXTENDED',excluded_source_undefined_post_sound_chain_reads=len(undefined),undefined_source_domain_rejections=rejected,native_release_body_bound=False,motu_gameplay_proven=False)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'release authority cases');assert actual==expected
if __name__=='__main__':main()
