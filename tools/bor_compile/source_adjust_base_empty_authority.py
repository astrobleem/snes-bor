"""Verbatim pinned empty-world adjust_base authority, source frame BASE/Y."""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import struct
import subprocess
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_check_gravity_idle_authority import PREAMBLE
from source_adjust_base_empty_4086 import adjust_base_empty
from source_model_core_4086 import binary32 as f32


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
 raw=subprocess.check_output(['git','-C',str(a.engine),'show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1');body=extract(raw,'adjust_base')
 pre=PREAMBLE.replace('int checkwall_below(float x,float z,float y){unexpected();return -1;}','int wall_calls;int checkwall_below(float x,float z,float y){wall_calls++;return -1;}').replace('float check_basemap(float x,float z){unexpected();return -1000;}','int basemap_calls;float check_basemap(float x,float z){basemap_calls++;return -1000;}').replace('int checkhole(float x,float z){unexpected();return 0;}','int hole_calls;int checkhole(float x,float z){hole_calls++;return 0;}')
 code=pre+body+'\nvoid check_gravity(entity *e){unexpected();}\nunsigned bits(float f){unsigned v;memcpy(&v,&f,4);return v;}float frombits(unsigned v){float f;memcpy(&f,&v,4);return f;}\nstruct Case{int noadjust,hole,wall,platform;unsigned base,altbase,framebase,framey,a,vy;}cases[]={\n'
 bits=lambda v:struct.unpack('<I',struct.pack('<f',v))[0];inputs=[];expected=[]
 for noadjust,hole,(wall,platform),base,altbase,fb,fy,alt,vy in itertools.product((-1,0,1),(0,1),((0,0),(1,1)),(-1000,0,34),(-50,0,.25),(-1,0,40),(0,1),(-1,93),(0,1)):
  e=dict(no_adjust_base=noadjust,subject_to_hole=hole,base=f32(base),altbase=f32(altbase),frame_base=f32(fb),frame_move_y=f32(fy),a=f32(alt),velocity_y=f32(vy),velocity_x=1.5,velocity_z=-.75,landed_on_platform=None,platform_below=1)
  adjust_base_empty(e)
  inputs.append(dict(noadjust=noadjust,hole=hole,wall=wall,platform=platform,base=base,altbase=altbase,frame_base=fb,frame_y=fy,a=alt,velocity_y=vy))
  expected.append([bits(e['base']),bits(e['a']),bits(e['velocity_x']),bits(e['velocity_z']),int(e['landed_on_platform']is not None),int(e['platform_below']is not None),int(platform>0),int(noadjust<=0 and wall>0),int(noadjust<=0),int(noadjust<=0 and hole>0),1])
  code+='{%d,%d,%d,%d,%du,%du,%du,%du,%du,%du},\n'%(noadjust,hole,wall,platform,bits(base),bits(altbase),bits(fb),bits(fy),bits(alt),bits(vy))
 code+=r'''};int main(void){Animation anim;Move move,*moves[1];entity *plat;unsigned i;struct Case *c;
for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){c=cases+i;memset(&ent,0,sizeof(ent));memset(&anim,0,sizeof(anim));self=&previous;platform_calls=wall_calls=basemap_calls=hole_calls=0;
ent.animation=&anim;moves[0]=&move;anim.move=moves;move.base=frombits(c->framebase);move.y=frombits(c->framey);ent.modeldata.no_adjust_base=c->noadjust;ent.modeldata.subject_to_hole=c->hole;ent.modeldata.subject_to_wall=c->wall;ent.modeldata.subject_to_platform=c->platform;ent.base=frombits(c->base);ent.altbase=frombits(c->altbase);ent.position.y=frombits(c->a);ent.velocity.y=frombits(c->vy);ent.velocity.x=1.5;ent.velocity.z=-.75;plat=&previous;adjust_base(&ent,&plat);
printf("%u,%u,%u,%u,%d,%d,%d,%d,%d,%d,%d\n",bits(ent.base),bits(ent.position.y),bits(ent.velocity.x),bits(ent.velocity.z),ent.landed_on_platform!=NULL,plat!=NULL,platform_calls,wall_calls,basemap_calls,hole_calls,self==&previous);
}return 0;}'''
 (folder/'base.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-bt=nt','base.c','-fe=base.exe'],cwd=folder,env=env,capture_output=True,text=True);(folder/'build.log').write_text(build.stdout+build.stderr)
 if build.returncode:raise ValueError('ADJUST_BASE_AUTHORITY_BUILD:'+build.stdout+build.stderr)
 log=subprocess.check_output([str(folder/'base.exe')],cwd=folder,text=True);(folder/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()];mismatches=[i for i,(v,w)in enumerate(zip(actual,expected))if v!=w]
 r=dict(schema='BYOR_4086_EMPTY_WORLD_ADJUST_BASE_AUTHORITY_V1',status='PASS'if actual==expected else'FAIL',engine_commit=ENGINE_COMMIT,source_function_sha256=hashlib.sha256(body.encode('latin1')).hexdigest(),source_function_unmodified=True,cases=len(inputs),inputs=inputs,actual=actual,expected=expected,mismatch_cases=mismatches,empty_geometry_services_instrumented=True,platform_and_nonempty_geometry_proven=False,native_base_adjustment_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
 (folder/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],len(inputs),'empty-world base cases',mismatches[:3]);assert actual==expected


if __name__=='__main__':main()
