"""Unchanged source freeze/unfreeze with real palette-pointer selection."""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import subprocess
from compiler import Source
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_current_colourmap import derive,layout


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--engine',default='E:/gh/openbor-bcec');p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','-C',a.engine,'show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1');header=subprocess.check_output(['git','-C',a.engine,'show',ENGINE_COMMIT+':engine/openbor.h']).decode('latin1')
    r=derive(Source(a.source));plan=layout();bodies={n:extract(raw,n)for n in ('diff','inair','ent_set_colourmap','checkdamageeffects')}
    start=re.search(r'unsigned char \*model_get_colourmap\([^\n]*\)\s*\n\{',raw).start();end=raw.index('\n}',start)+2;bodies['model_get_colourmap']=raw[start:end]
    bodies={n:bodies[n]for n in ('diff','inair','model_get_colourmap','ent_set_colourmap','checkdamageeffects')}
    macro=re.search(r'^#define unfrozen\(e\).*?(?=\n\s*\n)',header,re.M|re.S).group(0)
    rows=[]
    for model,freeze,frozen,restore,deadline,fmap_override in itertools.product(r['models'],range(2),range(2),(0,1,2,3,-1,0x7fffffff),(0,123),(None,-1,-2,3)):
        rows.append(dict(model=model['id'],maps=model['maps_loaded'],freeze=freeze,frozen=frozen,restore=restore,deadline=deadline,fmap=model['frozen_map']if fmap_override is None else fmap_override))
    code=r'''
#include <stdio.h>
#include <string.h>
#define GAME_SPEED 200
typedef struct {int rise,riseattack;} Stay;
typedef struct {float x,z,y;} Vec;
typedef struct entity entity;
typedef struct {int attack_force,attack_type,attack_drop,no_pain,freeze,maptime,freezetime,forcemap,blast,steal,seal,sealtime,dot,dot_index,dot_time,dot_force,dot_rate;Stay staydown;} s_attack;
typedef struct {int health,nodrop;struct{int frozen;}maps;unsigned maps_loaded;unsigned char *palette,*colourmap[2];} s_model;
struct entity {s_model modeldata;Vec position;float base;entity *opponent;int health,frozen,drop,projectile,map,seal;unsigned char *colourmap;unsigned freezetime,maptime,sealtime;Stay staydown;entity *dot_owner[4];int dot[4],dot_force[4],dot_rate[4],dot_atk[4];unsigned dot_time[4];};
entity victim,*self=&victim;unsigned time=48;unsigned char palettes[3];
'''+macro+'\n'+'\n'.join(bodies.values())+r'''
int main(void){int model,maps,freeze,frozen,restore,deadline,fmap;s_attack attack;
while(scanf("%d %d %d %d %d %d %d",&model,&maps,&freeze,&frozen,&restore,&deadline,&fmap)==7){
memset(&victim,0,sizeof(victim));memset(&attack,0,sizeof(attack));victim.modeldata.maps_loaded=maps;victim.modeldata.palette=palettes;victim.modeldata.colourmap[0]=palettes+1;victim.modeldata.colourmap[1]=palettes+2;victim.modeldata.maps.frozen=fmap;victim.map=restore;victim.colourmap=palettes+2;victim.frozen=frozen;victim.freezetime=deadline;victim.drop=1;attack.freeze=freeze;attack.freezetime=600;attack.forcemap=-1;
checkdamageeffects(&attack);printf("%d %d %u %d %d\n",victim.map,(int)(victim.colourmap-palettes),victim.freezetime,victim.frozen,victim.drop);
}return 0;}
'''
    (a.output/'colourmap.c').write_text(code,encoding='latin1');env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');q=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','-op','-fpc','colourmap.c','-fe=colourmap.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(q.stdout+q.stderr)
    if q.returncode:raise ValueError('CURRENT_COLOURMAP_C_BUILD:'+q.stdout+q.stderr)
    q=subprocess.run([str(a.output/'colourmap.exe')],input=''.join(' '.join(str(v)for v in row.values())+'\n'for row in rows),capture_output=True,text=True);actual=[list(map(int,l.split()))for l in q.stdout.splitlines()];expected=[]
    for c in rows:
        restore=c['restore'];palette=2;deadline=c['deadline'];frozen=c['frozen'];drop=1
        if c['freeze'] and not frozen:
            frozen=1;drop=0
            if not deadline:deadline=648
            if c['fmap']!=-1:palette=c['fmap'] if 1<=c['fmap']<=c['maps']else 0
        elif frozen:
            restore=restore if 1<=restore<=c['maps']else 0;palette=restore;deadline=0;frozen=0
        expected.append([restore,palette,deadline,frozen,drop])
    failures=[dict(index=i,input=rows[i],actual=x,expected=y)for i,(x,y)in enumerate(zip(actual,expected))if x!=y]
    report=dict(schema='BYOR_CURRENT_COLOURMAP_AUTHORITY_V1',status='PASS'if q.returncode==0 and actual==expected else'FAIL',cases=len(rows),observed_cases=len(actual),requirements=r,layout=plan,engine_commit=ENGINE_COMMIT,source_functions_unmodified=True,source_function_hashes={n:hashlib.sha256(b.encode('latin1')).hexdigest()for n,b in bodies.items()},actual_palette_pointer_selection=True,failures=failures,native_palette_presentation_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'freeze palette identities; CHR capacity',plan['chr_capacity']);print(json.dumps(failures[:2],indent=2))
    if report['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
