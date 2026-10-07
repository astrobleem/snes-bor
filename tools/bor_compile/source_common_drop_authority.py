"""Pinned common_drop/diff/inair and measured Q16 predicate adaptation."""
import argparse,hashlib,json,os,subprocess,itertools,struct
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

def f32(v):return struct.unpack('<f',struct.pack('<f',v))[0]
def q16(v):return round(f32(v)*65536)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 text=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd='E:/gh/openbor-bcec').decode('latin1');f='\n\n'.join(extract(text,n)for n in ('diff','inair','common_drop'));rows=[]
 for base,delta,health in itertools.product((-32000,-1,0,1,100,32000),(-1,-.10000000149,-.099999994,.0,.099999994,.10000000149,1),(-2147483648,-1,0,1,65536,2147483647)):
  y=f32(base+delta);base=f32(base);air=int(abs(q16(y)-q16(base))>=6554);rows.append(dict(y=y,base=base,y_q16=q16(y),base_q16=q16(base),health=health,compat_air=air,compat_expected=[3 if air else 1,1 if air else 0,int(not air and health<=0)]))
 code='''#include <stdio.h>
typedef struct {struct {float y;} position;float base;int health,idling;void (*takeaction)(void);} entity;
entity ent,*self=&ent;int killed;
void action(void){}
void kill(entity *e){killed++;}
'''+f+'\nstruct {float y,base;int health;} cases[]={'+','.join('{'+format(c['y'],'.17g')+','+format(c['base'],'.17g')+','+str(c['health'])+'}'for c in rows)+'''};
int main(void){unsigned i;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){ent.position.y=cases[i].y;ent.base=cases[i].base;ent.health=cases[i].health;ent.idling=3;ent.takeaction=action;killed=0;common_drop();printf("%d,%d,%d\\n",ent.idling,ent.takeaction!=0,killed);}return 0;}
'''
 (a.output/'common_drop.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','common_drop.c','-fe=common_drop.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 log=subprocess.check_output([str(a.output/'common_drop.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()];assert len(actual)==len(rows);differences=[]
 for i,(c,v)in enumerate(zip(rows,actual)):
  assert v in ([3,1,0],[1,0,int(c['health']<=0)])
  c['source_expected']=v
  if v!=c['compat_expected']:differences.append(i)
 r=dict(schema='BYOR_4086_COMMON_DROP_AUTHORITY_V1',status='PASS',engine_commit=ENGINE_COMMIT,functions_sha256=hashlib.sha256(f.encode()).hexdigest(),cases=len(rows),inputs=rows,actual=actual,q16_compat_differences=differences,policy='ACCEPTED_COMPAT Q16 inair absolute difference >=6554; differences measured and retained',retirement_body_instrumented=True,motu_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS',len(rows),'common_drop cases;',len(differences),'measured Q16 predicate differences')
if __name__=='__main__':main()
