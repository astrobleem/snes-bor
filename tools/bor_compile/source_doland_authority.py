"""Pinned doland/common_land mutation ordering and explicit animation children."""
import argparse,hashlib,itertools,json,os,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_animation_ids import configure

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);raw=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1');bodies={n:extract(raw,n)for n in ('doland','common_land')};land=configure([])['authority']['enum']['ANI_LAND'];rows=[dict(callback=c,direction=d,valid=v,animating=m)for c,d,v,m in itertools.product((0,1),(-1,0,1,2,65536),(0,1),(0,1,-1))]
 code='''#include <stdio.h>
#include <string.h>
'''+f'#define ANI_LAND {land}\n'+'''
typedef struct entity{struct{float x,y,z;}velocity;int drop,projectile,damage_on_landing,direction,animating;void(*takeaction)(void);}entity;
entity e,*self=&e;int valid,n,events[16];
void common_fall(void){}void common_land(void);
int validanim(entity*e,int role){events[n++]=3;return role==ANI_LAND&&valid;}
void ent_set_anim(entity*e,int role,int reset){if(role!=ANI_LAND)return;events[n++]=1;events[n++]=reset;}
void set_idle(entity*e){events[n++]=2;}
unsigned bits(float v){unsigned n;memcpy(&n,&v,4);return n;}
'''+bodies['doland']+'\n'+bodies['common_land']+'\nint main(void){int c,d,v,m,i;while(scanf("%d %d %d %d",&c,&d,&v,&m)==4){memset(&e,0,sizeof(e));e.velocity.x=1.25f;e.velocity.y=3.75f;e.velocity.z=2.5f;e.drop=-7;e.projectile=2;e.damage_on_landing=-2;e.direction=d;e.animating=m;e.takeaction=c?common_land:common_fall;valid=v;n=0;if(c)common_land();else doland();printf("%u %u %u %d %d %d %d %d|",bits(e.velocity.x),bits(e.velocity.y),bits(e.velocity.z),e.drop,e.projectile,e.damage_on_landing,e.direction,e.takeaction==common_fall?1:e.takeaction==common_land?2:0);for(i=0;i<n;i++)printf("%s%d",i?" ":"",events[i]);puts("");}return 0;}\n'
 (a.output/'doland.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','doland.c','-fe=doland.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0;log=subprocess.check_output([str(a.output/'doland.exe')],input='\n'.join(' '.join(str(c[k])for k in ('callback','direction','valid','animating'))for c in rows)+'\n',text=True);(a.output/'authority.log').write_text(log);actual=[];expected=[]
 for c,line in zip(rows,log.splitlines()):
  state,events=line.split('|');actual.append([list(map(int,state.split())),list(map(int,events.split()))])
  if c['callback']==0:expected.append([[0,1081081856,0,0,0,0,int(not c['direction'])if c['valid']else c['direction'],2 if c['valid']else 0],[3,1,0]if c['valid']else[3,2]])
  else:expected.append([[0,1081081856,0,-7,2,-2,c['direction'],2 if c['animating']else 0],[]if c['animating']else[2]])
 ok=len(actual)==len(rows)and actual==expected;r=dict(schema='BYOR_DOLAND_COMMON_LAND_SOURCE_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,function_sha256={n:hashlib.sha256(s.encode('latin1')).hexdigest()for n,s in bodies.items()},cases=len(rows),inputs=rows,actual=actual,expected=expected,animation_children_instrumented=True,native_doland_bound=False,native_common_land_bound=False,motu_gameplay_proven=False,no_color_reduction=True);(a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],len(rows),'doland/common_land source cases');assert ok

if __name__=='__main__':main()
