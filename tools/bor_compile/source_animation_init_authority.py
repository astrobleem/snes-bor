"""Verbatim 4086 animation initialization and loader-sync C authority probe."""
import argparse,hashlib,json,os,re,subprocess
from pathlib import Path
from compiler import Source,key
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_animation_ids import configure,initial_sync,role_id
from source_animation_init_4086 import set_animation
from source_profile import discover,document


def fixtures():
    return [dict(old=old,target=target,reset=reset,frame=frame,oldsync=olds,newSync=news,count=count)
        for old in (-1,0,1) for target in (-1,0,1,2,3,4) for reset in (0,1,2,3,4,-1)
        for frame in (0,1,3,7) for olds,news,count in ((-1,-1,4),(1,1,2),(1,2,1),(-1,1,0))]


def expected(c):
    animations=[dict(identity=i,numframes=4 if i==0 else c['count'],sync=c['oldsync'] if i==0 else c['newSync'],animhits=17+i) for i in range(2)]
    e=dict(animations={0:animations[0],1:animations[1],2:None,3:dict(identity=2,numframes=0,sync=1,animhits=19)},
        animation=None if c['old']<0 else animations[c['old']],animnum=99,animpos=c['frame'],animating=-1,
        lasthit=77,grabbing=123,altbase=13,nextanim=456)
    trace=[]
    def update(e,f):trace.append(f) # Instrument only; retain all state at service boundary.
    set_animation(e,c['target'],c['reset'],dict(maximum=4,update_frame=update))
    return [e['animnum'],e['animation']['identity'] if e['animation'] else -1,e['animpos'],e['animating'],e['lasthit'],e['altbase'],e['nextanim'],*[a['animhits'] for a in animations],len(trace)]


def run(engine,source,folder):
    folder.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=engine).decode('latin1')
    header=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.h'],cwd=engine).decode('latin1')
    init=extract(raw,'ent_set_anim')
    loader='static '+extract(raw.replace('static int translate_ani_id','int translate_ani_id'),'translate_ani_id')
    macros=header[header.index('#define strclen'):header.index('#define lut_mul')]
    docs={k:document(source,n) for k,(n,_) in source.index.items() if k.endswith('.txt')}
    structure=discover(source,docs);config=configure(docs[key(structure['models_path'])]['directives'])
    roles=set(config['authority']['direct_loader_aliases'])
    roles.update(a['role'] for m in structure['models'] for a in m['animations'])
    for family in ('walk','up','down','backwalk'):
        roles.add(family);roles.add(family+'1')
    roles=sorted(roles);rows=fixtures()
    c='#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n'+macros+'\n'
    for name,value in config['authority']['enum'].items():c+=f'#define {name} {value}\n'
    c+='#define MAX_ATKS 20\n#define STA_ATKS 10\n'
    aliases={'deaths':'dies','normal_attacks':'attacks','freespecials':'specials'}
    for name,values in config['arrays'].items():c+=f'int anim{aliases.get(name,name)}[]={{'+','.join(map(str,values))+'};\n'
    c+=r'''
typedef struct {int numframes,identity,sync,animhits,attackone,bounce;
 struct {int cost;} energycost;struct {struct {int x;} min,max;} range;} s_anim;
typedef struct {s_anim **animation;float jumpheight;} s_model;
typedef struct {int counterattack;} s_attack;
typedef struct entity {s_model modeldata;s_anim *animation;int animnum,animpos,animating,lasthit,grabbing,altbase;unsigned nextanim;} entity;
int max_animations=4,calls;
int validanim(entity *e,int n){return e->modeldata.animation[n]&&e->modeldata.animation[n]->numframes>0;}
void update_frame(entity *e,int frame){if(frame!=0)exit(3);calls++;}
'''+loader+'\n'+init+'\n'
    c+='int cases[][7]={'+','.join('{'+','.join(str(r[k]) for k in ('old','target','reset','frame','oldsync','newSync','count'))+'}' for r in rows)+'};\n'
    c+='char *roles[]={'+','.join(json.dumps(r) for r in roles)+'};\n'
    c+=r'''
int main(void){unsigned i;int *r;s_anim a[3],*map[4];entity e;
 if(sizeof(int)!=4||sizeof(void*)!=4)return 2;
 for(i=0;i<sizeof(roles)/sizeof(roles[0]);i++){memset(a,0,sizeof(a));a[0].sync=-1;printf("SYNC|%u|%d|",i,translate_ani_id(roles[i],NULL,a,NULL));printf("%d\n",a[0].sync);}
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){r=cases[i];memset(a,0,sizeof(a));memset(&e,0,sizeof(e));calls=0;
 a[0].numframes=4;a[0].sync=r[4];a[0].identity=0;a[0].animhits=17;
 a[1].numframes=r[6];a[1].sync=r[5];a[1].identity=1;a[1].animhits=18;
 a[2].sync=1;a[2].identity=2;a[2].animhits=19;
 map[0]=a;map[1]=a+1;map[2]=NULL;map[3]=a+2;e.modeldata.animation=map;
 e.animation=r[0]<0?NULL:a+r[0];e.animnum=99;e.animpos=r[3];e.animating=-1;e.lasthit=77;e.grabbing=123;e.altbase=13;e.nextanim=456;
 ent_set_anim(&e,r[1],r[2]);
 printf("INIT|%u|%d,%d,%d,%d,%d,%d,%u,%d,%d,%d\n",i,e.animnum,e.animation?e.animation->identity:-1,e.animpos,e.animating,e.lasthit,e.altbase,e.nextanim,a[0].animhits,a[1].animhits,calls);
 }return 0;}
'''
    (folder/'animation_init.c').write_text(c)
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    built=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','animation_init.c','-fe=anim_authority.exe'],cwd=folder,env=env,capture_output=True,text=True)
    (folder/'build.log').write_text(built.stdout+built.stderr)
    if built.returncode:raise ValueError('ANIMATION_INIT_AUTHORITY_BUILD')
    output=subprocess.check_output([str((folder/'anim_authority.exe').resolve())],cwd=folder,text=True)
    results=[];sync=[]
    for line in output.splitlines():
        if line.startswith('INIT|'):
            _,i,values=line.split('|');i=int(i);actual=list(map(int,values.split(',')));wanted=expected(rows[i])
            results.append(dict(case=rows[i],actual=actual,expected=wanted,passed=actual==wanted))
        elif line.startswith('SYNC|'):
            _,i,number,value=line.split('|');role=roles[int(i)]
            sync.append(dict(role=role,actual_id=int(number),expected_id=role_id(config,role),actual_sync=int(value),expected_sync=initial_sync(config,role)))
    passed=len(results)==len(rows) and all(r['passed'] for r in results) and len(sync)==len(roles) and all(r['actual_id']==r['expected_id'] and r['actual_sync']==r['expected_sync'] for r in sync)
    report=dict(schema='BYOR_4086_ANIMATION_INIT_AUTHORITY_V1',status='PASS' if passed else 'FAIL',engine_commit=ENGINE_COMMIT,
        initialization_function_sha256=hashlib.sha256(init.encode('latin1')).hexdigest(),loader_function_sha256=hashlib.sha256(loader.encode('latin1')).hexdigest(),
        helper_macros_sha256=hashlib.sha256(macros.encode('latin1')).hexdigest(),cases=len(rows),results=results,loader_sync=sync,
        update_frame_instrumented=True,native_owner_bound=False,motu_gameplay_proven=False)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,required=True);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=run(a.engine,Source(a.source),a.output.resolve());print(json.dumps({k:r[k] for k in ('status','cases','initialization_function_sha256')}))
    if r['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
