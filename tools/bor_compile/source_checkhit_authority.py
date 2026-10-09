"""Compare source-derived collision pairs with unmodified pinned checkhit C."""
import argparse,hashlib,itertools,json,os,struct,subprocess
from pathlib import Path
from compiler import Source
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_frame_state_4086 import derive,pack,unpack
from source_checkhit_4086 import checkhit,f32


def bits(v):return struct.unpack('<I',struct.pack('<f',v))[0]


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=a.engine).decode('latin1');body=extract(raw,'checkhit');diff=extract(raw,'diff')
 ir=derive(Source(a.source));table=pack(ir);d=unpack(table);attacks=d['attacks'];boxes=d['boxes']
 # Positions are x/y/z, matching the engine's 3D coordinate record.
 poses=[((0,0,0),(0,0,0)),((80.5,0,12.25),(80.5,0,12.25)),((-.9999847412109375,.0000152587890625,0),(.9999847412109375,-.0000152587890625,0)),((200.5,0,30.25),(201.5,0,42.25)),((200.5,.5,30.25),(201.5,.5,100.25)),((-80.5,-1.5,-12.25),(-80.5,1.5,-12.25)),((1,.000000059604644775390625,1),(0,0,1))]
 grabs=(36.0,17.9)
 import re
 if not re.search(r'float\s+default_model_grabdistance\s*=\s*36\.0f',raw)or not re.search(r'newchar->grabdistance\s*=\s*default_model_grabdistance',raw):raise ValueError('CHECKHIT_SOURCE_DEFAULT_GRABDISTANCE')
 rows=[]
 for ai,bi,ad,td,pi,counter,gi in itertools.product(range(len(attacks)),range(len(boxes)),(0,1),(0,1),range(len(poses)),(0,1),range(len(grabs))):
  rows.append((ai,bi,(ai+bi)%len(attacks),ad,td,pi,counter,0,gi))
 for flags in (1,2,4,8,16):rows.append((0,0,0,0,1,0,1,flags,0))
 defs=['{'+','.join(str(x)for x in x['attack_coords'])+'},'+str(x['counterattack'])+','+str(x['attack_type'])for x in attacks]
 code=r"""#include <stdio.h>
#include <string.h>
#define DIRECTION_LEFT 0
typedef struct{float x,y,z;} vector;
typedef struct{int attack_coords[6],counterattack,attack_type;} attack;
typedef struct{attack **attacks;int **bbox_coords;int *vulnerable;} animation;
typedef struct{float grabdistance;} model;
typedef struct{vector position;animation *animation;int animpos,direction;model modeldata;} entity;
struct{vector position;int type,confirm;}lasthit;
"""+diff+'\n'+body+'\nattack attacks[]={'+','.join('{'+x+'}'for x in defs)+'};\nint boxes[][6]={'+','.join('{'+','.join(str(v)for v in b)+'}'for b in boxes)+r"""};
unsigned bits(float f){unsigned b;memcpy(&b,&f,4);return b;}
float value(unsigned b){float f;memcpy(&f,&b,4);return f;}
int main(void){int ai,bi,ti,ad,td,counter,flags,vulnerable,hit;unsigned ax,ay,az,tx,ty,tz,grab;
 entity at,t;animation aa,ta;attack *a,*b;int *box;
 if(sizeof(int)!=4||sizeof(float)!=4)return 2;
 while(scanf("%d %d %d %d %d %d %d %u %u %u %u %u %u %u",&ai,&bi,&ti,&ad,&td,&counter,&flags,&ax,&ay,&az,&tx,&ty,&tz,&grab)==14){
 memset(&at,0,sizeof(at));memset(&t,0,sizeof(t));memset(&lasthit,0,sizeof(lasthit));
 a=&attacks[ai];b=(flags&16)?NULL:&attacks[ti];box=boxes[bi];vulnerable=(flags&8)?0:1;
 aa.attacks=(flags&4)?NULL:&a;ta.attacks=&b;ta.bbox_coords=(flags&2)?NULL:&box;ta.vulnerable=&vulnerable;
 at.animation=&aa;t.animation=&ta;at.direction=ad;t.direction=td;
 at.position.x=value(ax);at.position.y=value(ay);at.position.z=value(az);t.position.x=value(tx);t.position.y=value(ty);t.position.z=value(tz);at.modeldata.grabdistance=value(grab);
 hit=checkhit(&at,(flags&1)?&at:&t,counter);
 printf("%d %u %u %u %d %d\n",hit,bits(lasthit.position.x),bits(lasthit.position.y),bits(lasthit.position.z),lasthit.type,lasthit.confirm);
 }return 0;}
"""
 (a.output/'checkhit.c').write_text(code,encoding='latin1')
 env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
 build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','checkhit.c','-fe=checkhit.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(build.stdout+build.stderr)
 if build.returncode:raise ValueError('CHECKHIT_C_BUILD:'+build.stdout+build.stderr)
 input_rows=[];expected=[]
 for ai,bi,ti,ad,td,pi,counter,flags,gi in rows:
  ap,tp=poses[pi];grab=grabs[gi]
  input_rows.append(' '.join(map(str,[ai,bi,ti,ad,td,counter,flags,*[bits(v)for v in ap],*[bits(v)for v in tp],bits(grab)])))
  attacker=dict(token=1,position=ap,direction=ad,grabdistance=grab,attack_table=not(flags&4),attack=attacks[ai])
  target=dict(token=1 if flags&1 else 2,position=tp,direction=td,bbox_table=not(flags&2),vulnerable=not(flags&8),bbox=boxes[bi],attack_table=True,attack=None if flags&16 else attacks[ti])
  r=checkhit(attacker,target,counter);expected.append([1,bits(r['x']),bits(r['y']),bits(r['z']),r['type'],1]if r else[0,0,0,0,0,0])
 input_text='\n'.join(input_rows)+'\n';proc=subprocess.run([str(a.output/'checkhit.exe')],input=input_text,capture_output=True,text=True)
 if proc.returncode:raise ValueError('CHECKHIT_C_EXECUTION')
 actual=[list(map(int,s.split()))for s in proc.stdout.splitlines()]
 mismatches=[dict(index=i,input=rows[i],actual=actual[i]if i<len(actual)else None,expected=e)for i,e in enumerate(expected)if i>=len(actual)or actual[i]!=e]
 report=dict(schema='BYOR_4086_CHECKHIT_SOURCE_GEOMETRY_AUTHORITY_V1',status='PASS'if len(actual)==len(rows)and not mismatches else'FAIL',engine_commit=ENGINE_COMMIT,checkhit_sha256=hashlib.sha256(body.encode('latin1')).hexdigest(),diff_sha256=hashlib.sha256(diff.encode('latin1')).hexdigest(),cases=len(rows),source_attack_records=len(attacks),source_bbox_records=len(boxes),collision_table_sha256=hashlib.sha256(table).hexdigest(),source_models={x['model']:x['source_sha256']for x in ir['animations']},positions=poses,grabdistances=list(grabs),source_default_grabdistance=36.0,input_sha256=hashlib.sha256(input_text.encode()).hexdigest(),actual_sha256=hashlib.sha256(proc.stdout.encode()).hexdigest(),expected_sha256=hashlib.sha256((''.join(' '.join(map(str,e))+'\n'for e in expected)).encode()).hexdigest(),mismatch_count=len(mismatches),mismatches=mismatches[:32],numeric_domain='finite binary32 positions inside Q16 range; signed source box endpoints within 16 bits; no native numeric compatibility claim',native_checkhit_bound=False,do_attack_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'source collision geometry cases;',len(mismatches),'mismatches')
 if report['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
