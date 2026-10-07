"""Pinned common_spawn action, with externally verified set_idle body."""
import argparse,hashlib,json,os,subprocess,itertools
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 text=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd='E:/gh/openbor-bcec').decode('latin1');f=extract(text,'common_spawn')
 rows=[dict(idling=i,animating=anim)for i,anim in itertools.product((0,1,3,-1,65536),(-2147483648,-1,0,1,65536,2147483647))]
 code='''#include <stdio.h>
typedef struct {int idling,animating;void (*takeaction)(void);} entity;
entity ent,*self=&ent;int calls;
void action(void){}
void set_idle(entity *e){calls++;e->idling=3;}
'''+f+'\nint cases[][2]={'+','.join('{'+str(c['idling'])+','+str(c['animating'])+'}'for c in rows)+'''};
int main(void){unsigned i;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){calls=0;ent.idling=cases[i][0];ent.animating=cases[i][1];ent.takeaction=action;common_spawn();printf("%d,%d,%d\\n",ent.idling,ent.takeaction!=0,calls);}return 0;}
'''
 (a.output/'common_spawn.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','common_spawn.c','-fe=common_spawn.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 log=subprocess.check_output([str(a.output/'common_spawn.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()];expected=[[0,1,0]if c['animating']else[3,0,1]for c in rows];ok=actual==expected
 r=dict(schema='BYOR_4086_COMMON_SPAWN_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,function_sha256=hashlib.sha256(f.encode()).hexdigest(),cases=len(rows),inputs=rows,actual=actual,expected=expected,set_idle_body_instrumented=True,motu_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],len(rows),'common_spawn cases');assert ok
if __name__=='__main__':main()
