"""Unchanged pinned common_trymove/player_trymove/testmove service-order proof."""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import random
import struct
import subprocess

from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_trymove_4086 import common_trymove, player_trymove, testmove

INT_FIELDS = ('mode type idling min max screen hole obstacle platform wall aimove hostile '
              'animheight height jump_range random throw grab jump found grabbed airborne '
              'hole_result wall_result below between wall_below solid minz maxz').split()
FLOAT_FIELDS = ('x y z xd zd advancex base otherx otherz wallheight wallz walldepth').split()
FIELDS = INT_FIELDS + FLOAT_FIELDS
EVENTS = dict(rand=1, throw=2, grab=3, jump=4, find=5, trygrab=6,
              inair=7, hole=8, wall=9, below=10, between=11, wall_below=12,
              blockz=13, blocks=14, blocko=15, blockw=16, movex=17, movez=18)


def bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


class Services:
    def __init__(self, row):
        self.row, self.events = row, []
        self.other = dict(x=row['otherx'], z=row['otherz'], token=1,
                          platform_solid=row['solid'])

    def record(self, name, *args):
        self.events.extend((EVENTS[name], *(bits(v) if isinstance(v, float) else v & 0xffffffff for v in args)))

    def rand(self):
        self.record('rand'); return self.row['random']

    def valid(self, name):
        self.record(name); return self.row[name]

    def find(self, x, z, mask):
        self.record('find', x, z, mask)
        return self.other if self.row['found'] else None

    def grab(self, other):
        self.record('trygrab', other['token']); return self.row['grabbed']

    def inair(self):
        self.record('inair'); return self.row['airborne']

    def hole(self, x, z):
        self.record('hole', x, z); return self.row['hole_result']

    def wall(self, x, z):
        self.record('wall', x, z); return self.row['wall_result']

    def below(self, x, z, y):
        self.record('below', x, z, y); return self.row['below']

    def between(self, x, z, y, top):
        self.record('between', x, z, y, top); return self.row['between']

    def wall_below(self, x, z, y):
        self.record('wall_below', x, z, y); return self.row['wall_below']

    def event(self, name, *args):
        self.record(name, *args)


def evaluate(row):
    e = dict(x=row['x'], y=row['y'], z=row['z'], idling=row['idling'],
             frame_base=row['base'], anim_height=row['animheight'], jump_range=row['jump_range'])
    e['modeldata'] = dict(type=row['type'], hostile=row['hostile'], aimove=row['aimove'], height=row['height'],
                         **{'subject_to_'+k: row[v] for k, v in
                            (('minz','min'),('maxz','max'),('screen','screen'),('hole','hole'),
                             ('obstacle','obstacle'),('platform','platform'),('wall','wall'))})
    world = dict(minz=row['minz'], maxz=row['maxz'], advancex=row['advancex'], hres=320,
                 wall_height=row['wallheight'], wall_z=row['wallz'], wall_depth=row['walldepth'])
    s = Services(row)
    if row['mode'] == 2:
        result = testmove(e, e['x'], e['z'], row['xd'], row['zd'], world, s)
    else:
        result = (common_trymove if row['mode'] == 0 else player_trymove)(e, row['xd'], row['zd'], world, s)
    return [result, bits(e['x']), bits(e['z']), *s.events]


def cases():
    b = dict(mode=0,type=1,idling=1,min=1,max=1,screen=1,hole=1,obstacle=1,platform=1,wall=1,
             aimove=0,hostile=11,animheight=0,height=40,jump_range=80,random=1,throw=1,grab=1,jump=1,
             found=0,grabbed=0,airborne=0,hole_result=0,wall_result=-1,below=0,between=0,wall_below=-1,solid=0,
             x=80.,y=0.,z=220.,xd=1.5,zd=-.25,minz=190,maxz=240,advancex=0.,base=0.,
             otherx=81.,otherz=221.,wallheight=30.,wallz=230.,walldepth=40.)
    axes = {k: sorted(set((b[k],-1,0,1,65536))) for k in INT_FIELDS}
    axes.update(mode=[0,1,2],type=[0,1,2,3,8,64,65536],random=[0,1,7,8,32767],
                aimove=[0,1,65536,65537,-1],wall_result=[-1,0,1],wall_below=[-1,0],solid=[0,1,-1],
                height=[-40,0,1,40],animheight=[-20,0,1,20],jump_range=[-1,0,40,80],minz=[-80,0,190,220,240],maxz=[-80,0,190,220,240])
    for k in FLOAT_FIELDS:
        axes[k] = sorted(set((b[k],-80.,-1.5,-0.,.25,80.,190.,220.,240.,310.,16777216.,1/16777216)))
    rows = [b]
    for k in FIELDS:
        rows.extend(dict(b, **{k:v}) for v in axes[k])
    # Cross gates with movement and geometry; deterministic random broadens combinations.
    for k, l in itertools.combinations(INT_FIELDS[:15] + ['x','z','xd','zd','minz','maxz'], 2):
        rows.extend(dict(b, **{k:v,l:w}) for v,w in itertools.product(axes[k],axes[l]))
    rng = random.Random(4086)
    rows.extend({k:rng.choice(axes[k]) for k in FIELDS} for _ in range(16000))
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'))
    p.add_argument('--output',type=Path,required=True)
    a = p.parse_args(); a.output = a.output.resolve(); a.output.mkdir(parents=True,exist_ok=True)
    def read(n):
        return subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/'+n],cwd=a.engine).decode('latin1')
    source, header = read('openbor.c'), read('openbor.h')
    import re
    for n in ('PLAYER_MIN_Z','PLAYER_MAX_Z'):
        if not re.search(r'\bint\s+'+n+r'\s*=',source):raise ValueError('TRYMOVE_Z_BOUND_TYPE_AUTHORITY')
    if not re.search(r'\bfloat\s+advancex\s*;',source):raise ValueError('TRYMOVE_CAMERA_TYPE_AUTHORITY')
    functions = {n:extract(source,n) for n in ('testmove','common_trymove','player_trymove')}
    def enum(token):
        at=header.index(token);start=header.rfind('typedef enum',0,at);end=header.index(';',at)+1
        return header[start:end]
    enums=enum('TYPE_PLAYER')+'\n'+enum('AIMOVE2_IGNOREHOLES')
    ids=json.loads((Path(__file__).parent/'authority/4086_animation_ids.json').read_text())['enum']
    code='''#include <stdio.h>
#include <string.h>
'''+enums+'\n'+''.join('#define '+n+' '+str(ids[n])+'\n' for n in ('ANI_THROW','ANI_GRAB','ANI_JUMP'))+r'''
typedef struct {int y;} size;
typedef struct {struct {int x;} max;} range;
typedef struct {size size;range range;float (*platform)[8];struct {float base;} **move;} anim;
typedef struct entity {struct {float x,y,z;} position;struct {int type,hostile,subject_to_minz,subject_to_maxz,subject_to_screen,subject_to_hole,subject_to_obstacle,subject_to_platform,subject_to_wall,aimove;size size;anim *animation[168];} modeldata;anim *animation;int animpos,idling;} entity;
entity actor,other,*self=&actor;anim animation,otheranimation,jumpanimation;struct {float base;} move;void *moveptr[1];float platform[1][8];
struct {struct {float height,z,depth;}walls[1];} lev,*level=&lev;
int PLAYER_MIN_Z,PLAYER_MAX_Z;float advancex;struct {int hRes;}videomodes;
int random_result,throw_result,grab_result,jump_result,found_result,grabbed_result,air_result,hole_result,wall_result,below_result,between_result,wall_below_result;
unsigned events[512];int nevents;
unsigned bits(float f){unsigned u;memcpy(&u,&f,4);return u;}
float frombits(unsigned u){float f;memcpy(&f,&u,4);return f;}
void event(unsigned n){events[nevents++]=n;}
void coords(unsigned n,float x,float z){event(n);event(bits(x));event(bits(z));}
int rand(void){event(1);return random_result;}
int validanim(entity *e,int n){if(n==ANI_THROW){event(2);return throw_result;}if(n==ANI_GRAB){event(3);return grab_result;}event(4);return jump_result;}
entity *find_ent_here(entity *e,float x,float z,int mask,entity *exclude){coords(5,x,z);event((unsigned)mask);return found_result?&other:NULL;}
int trygrab(entity *e){event(6);event(1);return grabbed_result;}
int inair(entity *e){event(7);return air_result;}
int checkhole(float x,float z){coords(8,x,z);return hole_result;}
int checkwall(float x,float z){coords(9,x,z);return wall_result;}
entity *check_platform_below(float x,float z,float y,entity *e){coords(10,x,z);event(bits(y));return below_result?&other:NULL;}
entity *check_platform_between(float x,float z,float y,float top,entity *e){coords(11,x,z);event(bits(y));event(bits(top));return between_result?&other:NULL;}
int checkwall_below(float x,float z,float y){coords(12,x,z);event(bits(y));return wall_below_result;}
void execute_onblockz_script(entity *e){event(13);}
void execute_onblocks_script(entity *e){event(14);}
void execute_onblocko_script(entity *e,entity *o){event(15);event(1);}
void execute_onblockw_script(entity *e,int axis,double height){event(16);event(axis);event(bits((float)height));}
void execute_onmovex_script(entity *e){event(17);}
void execute_onmovez_script(entity *e){event(18);}
'''+ '\n'.join(functions.values())+'\nint main(void){unsigned v['+str(len(FIELDS))+'];int i,r;float xd,zd;\n'
    code+='if(sizeof(int)!=4 || sizeof(void*)!=4 || TYPE_PLAYER!=1 || TYPE_OBSTACLE!=8 || TYPE_TRAP!=64 || AIMOVE2_IGNOREHOLES!=65536)return 2;\n'
    code+='for(;;){for(i=0;i<'+str(len(FIELDS))+';i++)if(scanf("%u",v+i)!=1)return i?3:0;memset(&actor,0,sizeof(actor));memset(&other,0,sizeof(other));nevents=0;\n'
    assigns = dict(type='actor.modeldata.type',idling='actor.idling',min='actor.modeldata.subject_to_minz',max='actor.modeldata.subject_to_maxz',
        screen='actor.modeldata.subject_to_screen',hole='actor.modeldata.subject_to_hole',obstacle='actor.modeldata.subject_to_obstacle',
        platform='actor.modeldata.subject_to_platform',wall='actor.modeldata.subject_to_wall',aimove='actor.modeldata.aimove',hostile='actor.modeldata.hostile',
        animheight='animation.size.y',height='actor.modeldata.size.y',jump_range='jumpanimation.range.max.x',random='random_result',throw='throw_result',grab='grab_result',
        jump='jump_result',found='found_result',grabbed='grabbed_result',airborne='air_result',hole_result='hole_result',wall_result='wall_result',below='below_result',between='between_result',wall_below='wall_below_result')
    assigns.update(x='actor.position.x',y='actor.position.y',z='actor.position.z',xd='xd',zd='zd',minz='PLAYER_MIN_Z',maxz='PLAYER_MAX_Z',advancex='advancex',
        base='move.base',otherx='other.position.x',otherz='other.position.z',wallheight='lev.walls[0].height',wallz='lev.walls[0].z',walldepth='lev.walls[0].depth')
    for k,lhs in assigns.items():
        code+=lhs+'='+('frombits' if k in FLOAT_FIELDS else '(int)')+'(v['+str(FIELDS.index(k))+']);\n'
    code+='platform[0][7]=(float)(int)v['+str(FIELDS.index('solid'))+'];otheranimation.platform=platform;other.animation=&otheranimation;actor.animation=&animation;actor.modeldata.animation[ANI_JUMP]=&jumpanimation;moveptr[0]=&move;animation.move=(void*)moveptr;videomodes.hRes=320;\n'
    code+='r=v[0]==0?common_trymove(xd,zd):v[0]==1?player_trymove(xd,zd):testmove(&actor,actor.position.x,actor.position.z,xd,zd);printf("%d %u %u",r,bits(actor.position.x),bits(actor.position.z));for(i=0;i<nevents;i++)printf(" %u",events[i]);printf("\\n");}}\n'
    (a.output/'trymove.c').write_text(code,encoding='latin1')
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','trymove.c','-fe=trymove.exe'],cwd=a.output,env=env,capture_output=True,text=True)
    (a.output/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise ValueError('TRYMOVE_AUTHORITY_BUILD:'+build.stdout+build.stderr)
    rows=cases();inputs=''.join(' '.join(str(bits(r[k]) if k in FLOAT_FIELDS else r[k]&0xffffffff) for k in FIELDS)+'\n' for r in rows)
    proc=subprocess.run([str(a.output/'trymove.exe')],input=inputs,capture_output=True,text=True)
    actual=[list(map(int,l.split())) for l in proc.stdout.splitlines()];expected=[evaluate(r) for r in rows]
    mismatch=[dict(index=i,input=rows[i],actual=actual[i] if i<len(actual) else None,expected=expected[i]) for i in range(len(rows)) if i>=len(actual) or actual[i]!=expected[i]]
    report=dict(schema='BYOR_4086_TRYMOVE_SERVICE_ORDER_AUTHORITY_V1',status='PASS' if proc.returncode==0 and actual==expected else 'FAIL',engine_commit=ENGINE_COMMIT,
        cases=len(rows),modes={str(m):sum(r['mode']==m for r in rows) for m in range(3)},source_functions_unmodified=True,
        function_sha256={n:hashlib.sha256(f.encode('latin1')).hexdigest() for n,f in functions.items()},enum_sha256=hashlib.sha256(enums.encode('latin1')).hexdigest(),
        inputs_sha256=hashlib.sha256(inputs.encode()).hexdigest(),outputs_sha256=hashlib.sha256(proc.stdout.encode()).hexdigest(),
        event_codes=EVENTS,events_include_float_argument_bits=True,return_code=proc.returncode,mismatches=mismatch,
        service_results_instrumented=True,script_mutation_proven=False,geometric_service_bodies_proven=False,
        numeric_policy='Measured 32-bit Watcom x87 corpus; common screen expressions spill to float, testmove comparisons retain expression precision',
        original_engine_binary_float_equivalence=False,
        native_trymove_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'],len(rows),'pinned movement/service-order cases;',len(mismatch),'mismatches')
    if report['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
