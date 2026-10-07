"""Pinned warp/busy predicates, including explicit unbound FOLLOW distance cases."""
import argparse,hashlib,itertools,json,os,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 text=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd='E:/gh/openbor-bcec').decode('latin1');f='\n\n'.join(extract(text,n)for n in ('diff','ai_check_warp','ai_check_busy'))
 rows=[dict(subtype=s,link=l,parent=p,idling=i,x=x,z=z,range=80,native_follow_requires_distance=int(not l and s==10 and p))for s,l,p,i,x,z in itertools.product((0,1,9,10,11,65536),(0,1),(0,1),(0,1,3,-1,65536),(-81,-80,0,80,81),(0,81))]
 code='''#include <stdio.h>
#define SUBTYPE_FOLLOW 10
typedef struct {struct {struct {int x;} max;} range;} anim;
typedef struct entity {struct entity *link,*parent;struct {int subtype;anim *animation[1];} modeldata;struct {float x,z;} position;int idling;void (*takeaction)(void);} entity;
#define ANI_IDLE 0
entity ent,other,*self=&ent;anim idle;
void npc_warp(void){}
'''+f+'\nint cases[][7]={'+','.join('{'+','.join(str(c[k])for k in ('subtype','link','parent','idling','x','z','range'))+'}'for c in rows)+'''};
int main(void){unsigned i;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){int *r=cases[i],w,b;ent.modeldata.subtype=r[0];ent.link=r[1]?&other:0;ent.parent=r[2]?&other:0;ent.idling=r[3];ent.position.x=r[4];ent.position.z=r[5];idle.range.max.x=r[6];ent.modeldata.animation[0]=&idle;ent.takeaction=0;w=ai_check_warp();b=ai_check_busy();printf("%d,%d,%d\\n",w,b,ent.takeaction==npc_warp);}return 0;}
'''
 (a.output/'ai_readonly.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','ai_readonly.c','-fe=ai_readonly.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 log=subprocess.check_output([str(a.output/'ai_readonly.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()];expected=[]
 for c in rows:
  w=int(not c['link']and c['subtype']==10 and c['parent']and(abs(c['z'])>c['range']or abs(c['x'])>c['range']));expected.append([w,int(bool(c['link']or not c['idling'])),w])
 ok=actual==expected;r=dict(schema='BYOR_4086_AI_WARP_BUSY_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,functions_sha256=hashlib.sha256(f.encode()).hexdigest(),cases=len(rows),inputs=rows,actual=actual,expected=expected,follow_distance_native_bound=False,motu_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],len(rows),'warp/busy predicate cases');assert ok
if __name__=='__main__':main()
