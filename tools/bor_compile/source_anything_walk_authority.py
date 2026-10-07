"""Pinned anything_walk strict horizontal offscreen bounds."""
import argparse,hashlib,json,os,subprocess,itertools
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 text=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd='E:/gh/openbor-bcec').decode('latin1');f=extract(text,'anything_walk');rows=[]
 for ax,h in itertools.product((-32000,-400,-80,0,80,200,2224,32000),(1,256,320,512)):
  for x in (ax-80-.25,ax-80,ax-80+.25,ax,ax+h+80-.25,ax+h+80,ax+h+80+.25):
   rows.append(dict(ax_q16=int(ax*65536),hres=h,x_q16=int(x*65536),kill=int(x<ax-80 or x>ax+h+80)))
 code='''#include <stdio.h>
typedef struct {struct {float x;} position;} entity;
entity ent,*self=&ent;float advancex;struct {int hRes;} videomodes;int killed;
void kill(entity *e){killed++;}
'''+f+'\nint cases[][3]={'+','.join('{'+','.join(str(c[k])for k in ('ax_q16','hres','x_q16'))+'}'for c in rows)+'''};
int main(void){unsigned i;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){advancex=cases[i][0]/65536.0f;videomodes.hRes=cases[i][1];ent.position.x=cases[i][2]/65536.0f;killed=0;anything_walk();printf("%d\\n",killed);}return 0;}
'''
 (a.output/'anything_walk.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','anything_walk.c','-fe=anything_walk.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 log=subprocess.check_output([str(a.output/'anything_walk.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=list(map(int,log.splitlines()));ok=actual==[c['kill']for c in rows]
 r=dict(schema='BYOR_4086_ANYTHING_WALK_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,function_sha256=hashlib.sha256(f.encode()).hexdigest(),cases=len(rows),inputs=rows,actual=actual,retirement_body_instrumented=True,motu_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],len(rows),'anything_walk cases');assert ok
if __name__=='__main__':main()
