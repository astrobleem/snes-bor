"""Compare all MOTU effect input records to pinned model-loader case bodies."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from compiler import Source,key
from dialect_4086 import ENGINE_COMMIT
from source_profile import document,discover
from source_frame_effects_4086 import derive,pack,unpack,ANIMATION_FIELDS,IDENTITY_FIELDS,NUMERIC_FIELDS


def run(source,engine,folder):
    folder.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=engine)
    header=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.h'],cwd=engine)
    text=raw.decode('latin1');commands=['MODEL','ANIM','FRAME']
    groups=[('DELAY','OFFSET'),('SETA','FSHADOW'),('FLIPFRAME','FOLLOWANIM'),
        ('WEAPONFRAME','AT_SCRIPT'),('THROWFRAME','DIVE'),('JUMPFRAME','BOUNCEFACTOR'),('SOUND','HITFX')]
    fragments=[]
    for start,end in groups:
        at=text.index('case CMD_MODEL_'+start+':')
        fragment=text[at:text.index('case CMD_MODEL_'+end+':',at)]
        fragments.append(fragment);commands+=re.findall(r'case CMD_MODEL_(\w+):',fragment)
    frame_macro=re.search(r'^#define GET_FRAME_ARG.*$',header.decode('latin1'),re.M)[0]
    report=derive(source);binary=pack(report);decoded=unpack(binary)
    media=decoded['media'];models=report['models']
    def c_names(names):return ','.join(json.dumps(n.lower()) for n in names) or '""'
    scalar_paths=dict(flipframe='flipframe',unsummonframe='unsummonframe',weapon_frame='weaponframe[0]',
        weapon_number='weaponframe[1]',weapon_keep='weaponframe[2]',quake_start='quakeframe.framestart',
        quake_repeat='quakeframe.repeat',quake_value='quakeframe.v',jump_frame='jumpframe.frame',
        jump_y='jumpframe.velocity.y',jump_x='jumpframe.velocity.x',jump_z='jumpframe.velocity.z',jump_entity='jumpframe.ent',
        subentity='subentity',throw_frame='projectile.throwframe',shoot_frame='projectile.shootframe',
        toss_frame='projectile.tossframe',projectile_y='projectile.position.y',knife='projectile.knife',
        star='projectile.star',bomb='projectile.bomb',flash='projectile.flash')
    print_events=[]
    for name in ANIMATION_FIELDS:
        if name.startswith(('spawn_','summon_')):
            prefix,suffix=name.split('_');index=['frame','x','z','y','relative'].index(suffix)
            expr='newanim->'+prefix+'frame ? newanim->'+prefix+'frame['+str(index)+'] : '+('-1' if index==0 else '0')
        elif name.startswith('weapon_'):
            expr='newanim->weaponframe ? newanim->'+scalar_paths[name]+' : '+('-1' if name=='weapon_frame' else '0')
        else:expr='newanim->'+scalar_paths[name]
        print_events.append('printf(" %.9g",(double)('+expr+'));')
    reset_move=text[text.index('move.base = -1;',text.index('case CMD_MODEL_ANIM:')):
        text.index('if(!newanim->range.min.x)',text.index('case CMD_MODEL_ANIM:'))]
    # Exact movement/SOUND reset statements, with unrelated frameshadow excluded.
    reset_move='\n'.join(s for s in reset_move.splitlines() if 'move.' in s or 'soundtoplay =' in s)
    defaults=[]
    for name in ('projectile.shootframe','projectile.throwframe','projectile.tossframe','jumpframe.frame',
                 'flipframe','unsummonframe','quakeframe.framestart'):
        match=re.search(r'newanim->'+re.escape(name)+r' = [^;]*;',text[text.index('case CMD_MODEL_ANIM:'):])
        if not match:raise ValueError('EFFECT_LOADER_DEFAULT_MISSING:'+name)
        defaults.append(match[0])
    default_ids=re.search(r'newanim->subentity = newanim->projectile.bomb[^;]*;',text)[0]
    code=r'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define TYPE_PLAYER 1
#define TYPE_ENEMY 2
#define TYPE_NPC 3
#define GET_ARG(n) args[n]
#define GET_INT_ARG(n) atoi(args[n])
#define GET_FLOAT_ARG(n) ((float)atof(args[n]))
''' + frame_macro + r'''
typedef struct {float x,y,z;int base;} axis;
typedef struct {int numframes,flipframe,*weaponframe,unsummonframe,subentity;
 float *spawnframe,*summonframe;struct {int framestart,repeat,v,cnt;} quakeframe;
 struct {int frame,ent;axis velocity;} jumpframe;
 struct {int throwframe,shootframe,tossframe,knife,star,bomb,flash;axis position;} projectile;} animation;
struct {int type;float jumpheight;} model={TYPE_PLAYER,4},*newchar=&model;
char args[12][256];animation *newanim;axis move;int soundtoplay=-1,delay;
char *media[]={''' + c_names(media) + r'''};
char *models[]={''' + c_names(models) + r'''};
int sound_load_sample(char *name,char *pak,int log){int i;for(i=0;i<''' + str(len(media)) + r''';i++)if(!stricmp(name,media[i]))return i;return -1;}
int get_cached_model_index(char *name){int i;for(i=0;i<''' + str(len(models)) + r''';i++)if(!stricmp(name,models[i]))return i;return -1;}
void print_animation(void){if(!newanim)return;printf("A");
''' + '\n'.join(print_events) + r'''
printf("\n");free(newanim->weaponframe);free(newanim->spawnframe);free(newanim->summonframe);free(newanim);newanim=NULL;}
enum {''' + ','.join('CMD_MODEL_'+n for n in commands) + r'''};
int main(void){int cmd,n,i;char *value,*packfile="fixture.pak";
 if(sizeof(long)!=4||sizeof(void *)!=4||sizeof(int)!=4)return 2;
 while(scanf("%d %d",&cmd,&n)==2){memset(args,0,sizeof(args));for(i=1;i<=n;i++)scanf("%255s",args[i]);
 switch(cmd){
 case CMD_MODEL_MODEL:print_animation();delay=0;break;
 case CMD_MODEL_ANIM:print_animation();newanim=calloc(1,sizeof(*newanim));
''' + reset_move + '\n'+'\n'.join(defaults)+default_ids+r'''
 break;
 case CMD_MODEL_FRAME:
 printf("F %d %.9g %.9g %.9g %d %d\n",move.base,(double)move.x,(double)move.y,(double)move.z,soundtoplay,delay*2);
 newanim->numframes++;
 soundtoplay = -1;
 break;
''' + '\n'.join(fragments) + r'''
 }
 }print_animation();return 0;}
'''
    (folder/'effect_loader.c').write_text(code)
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    built=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','effect_loader.c','-fe=effect_loader.exe'],
        cwd=folder,env=env,capture_output=True,text=True)
    (folder/'build.log').write_text(built.stdout+built.stderr)
    if built.returncode:raise ValueError('EFFECT_LOADER_AUTHORITY_BUILD')
    docs={k:document(source,n) for k,(n,_) in source.index.items() if k.endswith('.txt')};structure=discover(source,docs)
    rows=[]
    for model in structure['models']:
        rows.append('0 0');active=False
        for d in docs[key(model['source_path'])]['directives']:
            name=d['directive'].upper()
            if name=='ANIM':active=True
            if not active or name not in commands:continue
            values=[] if name in ('ANIM','FRAME') else d['values']
            if len(values)>11 or any(len(v)>=256 or re.search(r'\s',v) for v in values):
                raise ValueError('EFFECT_LOADER_FIXTURE_TOKEN_DOMAIN')
            rows.append(str(commands.index(name))+' '+str(len(values))+' '+' '.join(values))
    observed=subprocess.run([str((folder/'effect_loader.exe').resolve())],input='\n'.join(rows)+'\n',
        text=True,capture_output=True,check=True).stdout.splitlines()
    expected=[]
    for a in report['animations']:
        for f in a['frames']:
            index=-1 if f['sound_resolution'] in ('SOURCE_ASSET_MISSING','ABSENT') else media.index(f['sound'])
            expected.append(('F',[f['move'][n] for n in ('base','x','y','z')]+[index,f['delay_ticks']]))
        values=[]
        for name in ANIMATION_FIELDS:
            value=a['events'][name]
            if name in IDENTITY_FIELDS:value=-1 if value is None else value if isinstance(value,int) else [n.lower() for n in models].index(value.lower())
            values.append(value)
        expected.append(('A',values))
    mismatches=[]
    if len(observed)!=len(expected):raise ValueError(('EFFECT_LOADER_RECORD_COUNT',len(observed),len(expected)))
    for i,(line,(kind,values)) in enumerate(zip(observed,expected)):
        fields=line.split();actual=list(map(float,fields[1:]))
        if fields[0]!=kind or len(actual)!=len(values) or any(abs(a-b)>max(1e-7,abs(b)*1e-8) for a,b in zip(actual,values)):
            mismatches.append(dict(index=i,actual=line,expected=[kind,values]))
    r=dict(schema='BYOR_FRAME_EFFECT_LOADER_AUTHORITY_V1',status='PASS' if not mismatches else 'FAIL',
        engine_commit=ENGINE_COMMIT,engine_source_sha256=hashlib.sha256(raw).hexdigest(),
        engine_header_sha256=hashlib.sha256(header).hexdigest(),fragments_sha256=hashlib.sha256('\n'.join(fragments).encode()).hexdigest(),
        probe_sha256=hashlib.sha256(code.encode()).hexdigest(),source_frames=836,source_animations=80,
        records=len(expected),mismatches=mismatches,table_bytes=len(binary),table_sha256=hashlib.sha256(binary).hexdigest(),
        scope='Verbatim selected effect loader case bodies and reset statements; frame storage, model lookup and sample loading instrumented',
        numeric_policy=report['numeric_policy'],native_owner_bound=False,motu_gameplay_proven=False)
    (folder/'report.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r[k] for k in ('status','records','table_bytes','table_sha256')}))
    if mismatches:raise ValueError('EFFECT_LOADER_AUTHORITY_MISMATCH')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
    p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(Source(a.source),a.engine,a.output.resolve())
