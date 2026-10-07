"""Pinned grab predicate and literal common_grab_check null-victim return."""
import argparse, hashlib, itertools, json, os, subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 text=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd='E:/gh/openbor-bcec').decode('latin1')
 functions='\n\n'.join(extract(text,n) for n in ('common_grab_check','ai_check_grab'))
 rows=[dict(grabbing=g,attacking=t,link=l)for g,t,l in itertools.product((0,1,3,-1,65536),(0,1,3,-1,65536),(0,1))]
 code='''#include <stdio.h>
#define GAME_SPEED 200
#define WEAPLOSS_TYPE_ANY 1
#define ANI_THROW 15
typedef struct entity {struct entity *link;int grabbing,attacking,animating,grabwalking;float base;unsigned releasetime;void (*takeaction)(void);struct {int grabfinish,weaploss[1],throwframewait;} modeldata;} entity;
entity ent,other,*self=&ent;unsigned time;int nolost=1,grab_attacks[5][1],calls;
void ent_unlink(entity *e){calls++;}void set_idle(entity *e){calls++;}void dropweapon(int n){calls++;}
unsigned rand32(void){calls++;return 8;}int validanim(entity *e,int n){return 0;}
void doprethrow(void){calls++;}void dothrow(void){calls++;}void dograbattack(int n){calls++;}
'''+functions+'\nint cases[][3]={'+','.join('{'+','.join(str(c[k])for k in ('grabbing','attacking','link'))+'}'for c in rows)+'''};
int main(void){unsigned i;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){int result;ent.grabbing=cases[i][0];ent.attacking=cases[i][1];ent.link=cases[i][2]?&other:0;ent.releasetime=1;calls=0;result=ai_check_grab();printf("%d,%d,%d,%u\\n",result,calls,ent.grabbing,(unsigned)ent.attacking);}return 0;}
'''
 (a.output/'ai_grab.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
 b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','ai_grab.c','-fe=ai_grab.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 log=subprocess.check_output([str(a.output/'ai_grab.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log)
 actual=[list(map(int,l.split(',')))for l in log.splitlines()]
 expected=[[int(bool(c['grabbing']and not c['attacking'])),int(bool(c['grabbing']and not c['attacking']and c['link'])),c['grabbing'],c['attacking']&0xffffffff]for c in rows]
 ok=actual==expected
 report=dict(schema='BYOR_4086_AI_GRAB_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,functions_sha256=hashlib.sha256(functions.encode()).hexdigest(),cases=len(rows),inputs=rows,expected=expected,actual=actual,linked_handler_helpers_instrumented=True,null_victim_handler_literal=True,motu_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'source grab cases');assert ok
if __name__=='__main__':main()
