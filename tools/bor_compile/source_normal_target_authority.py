"""Unchanged normal_find_target and range macro against bounded target policy."""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import struct
import subprocess
from compiler import Source
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_animation_range_4086 import derive
from source_target_4086 import Target,normal_find


def cases(profile):
    rows=[];orders=list(itertools.permutations(range(3)))
    for animation in profile['animations']:
        ranges=animation['ranges']
        for direction,axis,bound,fraction in itertools.product((0,1,65536),range(4),(0,1),(-65536,-1,0,1,65536)):
            first=[(ranges[2*j]+ranges[2*j+1])//2*65536 for j in range(4)]
            second=first.copy();first[axis]=ranges[2*axis+bound]*65536+fraction
            if direction!=1:first[0]=-first[0];second[0]=-second[0]
            i=len(rows);mode=i%10
            actor=Target(1,type=1,hostile=2,direction=direction,alive=mode!=9)
            one=Target(2,x=first[0],z=first[1],y=first[2],base=first[3],type=4 if mode==3 else 2,dead=mode==1,alive=mode!=2,hide=1 if mode==4 else 0,vulnerable=mode!=6,invincible=1 if mode==7 else 2 if mode==8 else 0)
            two=Target(3,x=second[0],z=second[1],y=second[2],base=second[3],type=2,hide=-1)
            rows.append(dict(handle=animation['handle'],ranges=ranges,rows=[actor,one,two],adjustment=-2 if mode==5 else 1 if mode==4 else 0,order=list(orders[i%6]),scan_count=1+i%3))
    for fraction in(-65536,-1,0,1,65536):
        for direction in(0,1):
            rows.append(dict(handle=0,ranges=None,rows=[Target(1,type=1,hostile=2,direction=direction),Target(2,type=2,x=9999*65536+fraction),Target(3,type=2,x=-9999*65536)],adjustment=0,order=[0,1,2],scan_count=3))
    return rows


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    source=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
    header=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.h']).decode('latin1')
    helpers={name:extract(source,name)for name in('diff','normal_find_target')}
    macro=header[header.index('#define check_range(self, target, animnum)'):header.index('#define check_range_both(')]
    rows=cases(derive(Source(a.source)))
    code=r'''
#include <stdio.h>
#include <string.h>
#include <io.h>
#include <fcntl.h>
typedef unsigned int u32;
typedef struct {float x,y,z;} axis;
typedef struct {int x,y,z,base;} rangeaxis;
typedef struct animation {struct {rangeaxis min,max;}range;int vulnerable[1];} animation;
typedef struct entity {int exists,dead,invincible,direction,animpos;float base;axis position;animation *animation;struct {int type,hostile;struct {int detect,hide;}stealth;animation *animation[1];}modeldata;}entity;
entity e[3],*ent_list[3],*self;animation anim[3];int ent_max;
#define DIRECTION_RIGHT 1
'''+macro+'\n'+'\n'.join(helpers.values())+'\n'
    values=[]
    for c in rows:
        r=c['rows'];one=r[1]
        values.append([r[0].direction,int(r[0].alive),c['scan_count'],*c['order'],*(c['ranges']or[0]*8),c['adjustment'],r[0].x,r[0].z,r[0].y,r[0].base,one.x,one.z,one.y,one.base,r[2].x,r[2].z,r[2].y,r[2].base,one.type,int(one.dead),int(one.alive),one.invincible,int(one.vulnerable),one.hide,r[2].hide,0 if c['ranges']is not None else -1])
    code+='int rows[][35]={'+',\n'.join('{'+','.join(map(str,v))+'}'for v in values)+'};\n'
    code+=r'''
int main(void){unsigned i,j;int *r;entity *target;u32 result;setmode(fileno(stdout),O_BINARY);if(sizeof(int)!=4||sizeof(void*)!=4)return 3;
for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){r=rows[i];memset(e,0,sizeof(e));memset(anim,0,sizeof(anim));self=&e[0];ent_max=r[2];
for(j=0;j<3;j++){ent_list[j]=&e[r[3+j]];e[j].exists=1;e[j].animation=&anim[j];e[j].modeldata.animation[0]=&anim[j];anim[j].vulnerable[0]=1;e[j].modeldata.type=j?2:1;e[j].modeldata.hostile=j?1:2;
e[j].position.x=(float)(r[15+j*4]/65536.0);e[j].position.z=(float)(r[16+j*4]/65536.0);e[j].position.y=(float)(r[17+j*4]/65536.0);e[j].base=(float)(r[18+j*4]/65536.0);}
e[0].direction=r[0];e[0].exists=r[1];e[1].modeldata.type=r[27];e[1].dead=r[28];e[1].exists=r[29];e[1].invincible=r[30];anim[1].vulnerable[0]=r[31];e[1].modeldata.stealth.hide=r[32];e[2].modeldata.stealth.hide=r[33];
anim[0].range.min.x=r[6];anim[0].range.max.x=r[7];anim[0].range.min.z=r[8];anim[0].range.max.z=r[9];anim[0].range.min.y=r[10];anim[0].range.max.y=r[11];anim[0].range.min.base=r[12];anim[0].range.max.base=r[13];
target=normal_find_target(r[34],r[14]);result=target?(u32)(target-e)+1:0;fwrite(&result,4,1,stdout);}return 0;}
'''
    (out/'normal_target.c').write_text(code)
    build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-bt=nt','normal_target.c','-fe=normal_target.exe'],cwd=out,env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT'),capture_output=True,text=True)
    (out/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise ValueError('NORMAL_TARGET_AUTHORITY_BUILD')
    raw=subprocess.check_output([str(out/'normal_target.exe')],cwd=out);actual=list(struct.unpack('<'+'I'*len(rows),raw))
    adapted=[normal_find(c['rows'],1,c['ranges'],c['adjustment'],c['order'],c['scan_count'])or 0 for c in rows]
    integral=[i for i,c in enumerate(rows)if all(n%65536==0 for r in c['rows']for n in(r.x,r.z,r.y,r.base))]
    differences=[dict(index=i,handle=c['handle'],source=v,q16=e)for i,(c,v,e)in enumerate(zip(rows,actual,adapted))if v!=e]
    ok=all(actual[i]==adapted[i]for i in integral)
    report=dict(schema='BYOR_NORMAL_TARGET_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,literal_bodies_unmodified=True,literal_body_sha256={n:hashlib.sha256(v.encode()).hexdigest()for n,v in helpers.items()},literal_range_macro_sha256=hashlib.sha256(macro.encode()).hexdigest(),cases=len(rows),exact_integral_cases=len(integral),accepted_compat_differences=differences,actual_sha256=hashlib.sha256(raw).hexdigest(),adapted_sha256=hashlib.sha256(struct.pack('<'+'I'*len(rows),*adapted)).hexdigest(),numeric_policy='EXISTING_Q16_16_ACCEPTED_COMPAT',native_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'target cases;',len(differences),'explicit numeric differences')
    if not ok:raise AssertionError('NORMAL_TARGET_INTEGRAL_MISMATCH')


if __name__=='__main__':main()
