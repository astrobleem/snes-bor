"""Literal pinned spawnplayer against full placement/recovery mutation plan.

Terrain, smartspawn and set_weapon are instrumented child seams, not native joins.
"""
import argparse,hashlib,itertools,json,os,re,struct,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_player_spawn_4086 import spawnplayer,MAX_SPECIAL_INPUTS

FIELDS=('index','direction','hres','minz','maxz','sx','sz','wall_height','wall_before','hole_before','spawnhealth','spawnmp','weapnum','setweap','rush_policy')
BASE=dict(zip(FIELDS,(0,0,256,160,244,0,0,-1,0,0,0,0,0,5,0)))


def expected(c):
    player=dict(name='source-player',colourmap=7,ent=None,spawnhealth=c['spawnhealth'],spawnmp=c['spawnmp'],weapnum=c['weapnum'],combokey=[9]*27,inputtime=[8]*27,combostep=3)
    state=dict(players=[dict(player) for _ in range(4)],level=dict(spawn=[(c['sx'],c['sz'])]*4,scrolldir=c['direction'],setweap=c['setweap']),hres=c['hres'],minz=c['minz'],maxz=c['maxz'],advancex=17.5,max_wall_height=1000,rush_policy=c['rush_policy'],rush_saved=[21,22,23,24],currentspawnplayer=-9)
    counts=[0,0];digest=2166136261;weapon=[]
    def event(*words):
        nonlocal digest
        for word in words:digest=((digest^(word&0xffffffff))*16777619)&0xffffffff
    def bits(value):return struct.unpack('<I',struct.pack('<f',value))[0]
    def wall(x,z):
        event(1,bits(x),bits(z));n=counts[0];counts[0]+=1
        return c['wall_height'] if c['wall_height']>=0 and (c['wall_before']<0 or n<c['wall_before']) else None
    def hole(x,z):
        event(2,bits(x),bits(z));n=counts[1];counts[1]+=1
        return c['hole_before']<0 or n<c['hole_before']
    def factory(p):
        event(3,state['currentspawnplayer'],bits(p['position']['x']),bits(p['position']['z']),p['flip'],p['colourmap'],p['index'],p['itemindex'],p['weaponindex'],p['spawnplayer_count'])
        return dict(playerindex=-7,rush_max=-8,health=150,mp=80,model_health=150,model_mp=80)
    def set_weapon(e,n,keep):event(4,n,keep);weapon.append(n)
    p=spawnplayer(state,c['index'],wall,hole,factory,set_weapon);q=state['players'][c['index']&3];e=q['ent']
    return [bits(p['position']['x']),bits(p['position']['z']),p['flip'],p['colourmap'],p['index'],p['itemindex'],p['weaponindex'],p['spawnplayer_count'],state['currentspawnplayer'],e['playerindex'],e['rush_max'],e['health'],e['mp'],weapon[0],int(not any(q['combokey'])),int(not any(q['inputtime'])),q['combostep'],*counts,digest]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));parser.add_argument('--output',type=Path,required=True);a=parser.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=a.engine).decode('latin1');header=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.h'],cwd=a.engine).decode('latin1');body=extract(raw,'spawnplayer')
    for name,value in (('MAX_SPECIAL_INPUTS',27),('SCROLL_LEFT',8),('SCROLL_INWARD',32),('SCROLL_OUTWARD',64)):
        assert re.search(r'(?:#define\s+|\b)'+name+r'\s*(?:=\s*)?'+str(value)+r'\b',header)
    assert re.search(r'MAX_WALL_HEIGHT\s*=\s*1000',raw)
    cases=[]
    for index,direction,hres,zpair,sx,sz in itertools.product(range(-1,8),(0,8,32,64,40),(256,320),((160,160),(160,162),(160,244)),(0,-30,512),(0,5,100)):
        cases.append(dict(BASE,index=index,direction=direction,hres=hres,minz=zpair[0],maxz=zpair[1],sx=sx,sz=sz))
    for index,direction,hres,zpair,height,wall_before,hole_before in itertools.product(range(4),(0,8),(256,320),((160,160),(160,162),(160,244)),(-1,999,1000),(-1,0,1,3),(-1,0,1,3)):
        cases.append(dict(BASE,index=index,direction=direction,hres=hres,minz=zpair[0],maxz=zpair[1],wall_height=height,wall_before=wall_before,hole_before=hole_before))
    for index,hp,mp,weap,policy in itertools.product(range(4),(-9,0,1,149,200),(-9,0,1,79,200),(-2,0,7),(-1,0,2)):
        cases.append(dict(BASE,index=index,spawnhealth=hp,spawnmp=mp,weapnum=weap,rush_policy=policy))
    code=r"""#include <stdio.h>
#include <string.h>
#include <io.h>
#include <fcntl.h>
#define SCROLL_LEFT 8
#define SCROLL_INWARD 32
#define SCROLL_OUTWARD 64
#define MAX_SPECIAL_INPUTS 27
#define PLAYER_MIN_Z minimum_z
#define PLAYER_MAX_Z maximum_z
typedef unsigned int u32;
typedef struct {float x,y,z;} position;
typedef struct {char *name;int index,itemindex,weaponindex,colourmap,spawnplayer_count,flip;position position;} s_spawn_entry;
typedef struct {int playerindex,health,mp;struct {int health,mp;}modeldata;struct {struct {int max;}count;}rush;} entity;
struct {char *name;int colourmap;entity *ent;u32 combokey[27],inputtime[27];int combostep,spawnhealth,spawnmp,weapnum;}player[4];
struct {int scrolldir;position spawn[4];struct {int height;}walls[1];int setweap;} lev,*level=&lev;
struct {int hRes;}videomodes;
int minimum_z,maximum_z,MAX_WALL_HEIGHT=1000,currentspawnplayer,nomaxrushreset[5],wall_before,hole_before,nwall,nhole,weapon;
float advancex=17.5f;s_spawn_entry captured;entity e;u32 digest;
u32 bits(float v){u32 out;memcpy(&out,&v,4);return out;}
void add(u32 v){digest=(digest^v)*16777619u;}
int checkwall(float x,float z){int n=nwall++;add(1);add(bits(x));add(bits(z));return lev.walls[0].height>=0&&(wall_before<0||n<wall_before)?0:-1;}
int checkhole(float x,float z){int n=nhole++;add(2);add(bits(x));add(bits(z));return hole_before<0||n<hole_before;}
entity *smartspawn(s_spawn_entry *p){captured=*p;add(3);add(currentspawnplayer);add(bits(p->position.x));add(bits(p->position.z));add(p->flip);add(p->colourmap);add(p->index);add(p->itemindex);add(p->weaponindex);add(p->spawnplayer_count);memset(&e,0,sizeof(e));e.health=e.modeldata.health=150;e.mp=e.modeldata.mp=80;return &e;}
void set_weapon(entity *p,int n,int keep){add(4);add(n);add(keep);weapon=n;}
void shutdown(int code,char *format,char *name){}
"""+body+r"""
int main(void){int v[15],i,j,k;u32 w[20];if(sizeof(int)!=4||sizeof(void*)!=4||sizeof(float)!=4)return 3;setmode(fileno(stdin),O_BINARY);setmode(fileno(stdout),O_BINARY);while(fread(v,4,15,stdin)==15){memset(player,0,sizeof(player));memset(&lev,0,sizeof(lev));videomodes.hRes=v[2];minimum_z=v[3];maximum_z=v[4];lev.scrolldir=v[1];lev.setweap=v[13];lev.walls[0].height=v[7];wall_before=v[8];hole_before=v[9];nwall=nhole=0;digest=2166136261u;nomaxrushreset[4]=v[14];for(i=0;i<4;i++){player[i].name="source-player";player[i].colourmap=7;player[i].spawnhealth=v[10];player[i].spawnmp=v[11];player[i].weapnum=v[12];player[i].combostep=3;lev.spawn[i].x=v[5];lev.spawn[i].z=v[6];nomaxrushreset[i]=21+i;for(j=0;j<27;j++){player[i].combokey[j]=9;player[i].inputtime[j]=8;}}spawnplayer(v[0]);i=v[0]&3;k=0;w[k++]=bits(captured.position.x);w[k++]=bits(captured.position.z);w[k++]=captured.flip;w[k++]=captured.colourmap;w[k++]=captured.index;w[k++]=captured.itemindex;w[k++]=captured.weaponindex;w[k++]=captured.spawnplayer_count;w[k++]=currentspawnplayer;w[k++]=e.playerindex;w[k++]=e.rush.count.max;w[k++]=e.health;w[k++]=e.mp;w[k++]=weapon;w[k++]=1;w[k++]=1;for(j=0;j<27;j++){if(player[i].combokey[j])w[14]=0;if(player[i].inputtime[j])w[15]=0;}w[k++]=player[i].combostep;w[k++]=nwall;w[k++]=nhole;w[k++]=digest;fwrite(w,4,k,stdout);}return 0;}
"""
    (out/'spawnplayer.c').write_text(code)
    build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','spawnplayer.c','-fe=spawnplayer.exe'],cwd=out,env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT'),capture_output=True,text=True);(out/'build.log').write_text(build.stdout+build.stderr);assert build.returncode==0
    data=b''.join(struct.pack('<15i',*(c[k] for k in FIELDS))for c in cases)
    actual=subprocess.check_output([str(out/'spawnplayer.exe')],input=data)
    wanted=b''.join(struct.pack('<20I',*(v&0xffffffff for v in expected(c)))for c in cases)
    if actual!=wanted:
        for i,c in enumerate(cases):
            if actual[i*80:(i+1)*80]!=wanted[i*80:(i+1)*80]:
                (out/'mismatch.json').write_text(json.dumps(dict(case=c,actual=list(struct.unpack('<20I',actual[i*80:(i+1)*80])),expected=expected(c)),indent=2));break
        raise AssertionError('PLAYER_SPAWN_LITERAL_AUTHORITY_MISMATCH')
    report=dict(schema='BYOR_PLAYER_SPAWN_AUTHORITY_V1',status='PASS',cases=len(cases),engine_commit=ENGINE_COMMIT,source_body_sha256=hashlib.sha256(body.encode('latin1')).hexdigest(),fixture_sha256=hashlib.sha256(code.encode()).hexdigest(),input_sha256=hashlib.sha256(data).hexdigest(),output_sha256=hashlib.sha256(actual).hexdigest(),output_bytes=len(actual),terrain_query_order_checked_by_u32_fnv=True,combo_elements=MAX_SPECIAL_INPUTS,child_services_instrumented=True,native_player_spawn_bound=False,smartspawn_constructor_bound=False,terrain_geometry_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
