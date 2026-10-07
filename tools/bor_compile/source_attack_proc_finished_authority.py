"""Literal grounded callback and NULL-weapon subtract_shot authority."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inputs',type=Path,nargs='+',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd='E:/gh/openbor-bcec').decode('latin1');proc=extract(raw,'common_attack_proc');shot=extract(raw,'subtract_shot');diff=extract(raw,'diff')
 rows=[]
 for path in a.inputs:
  r=json.loads(path.read_text());assert r['status']=='PASS'
  for c in r['inputs']:
   if c['fault']:continue
   rows.append(dict(type=c['type'],reactive=c['reactive'],tocost=c.get('tocost',0),cost=10 if r.get('cost_payment')else 0,mp=77,health=88,smart_other=c.get('smart_other',0)))
 code=r"""#include <stdio.h>
#include <stddef.h>
#define COST_CHECK_MP 1
typedef struct {struct {int cost;}energycost;}animation;
typedef struct entity {int animating,tocost,reactive,attacking,mp,health,animnum;float base;struct {float y;}position;animation*animation;struct entity*weapent;struct {int type,shootnum,counter,smartbomb;}modeldata;}entity;
entity ent,other,*self=&ent,*smartbomber;animation live;int drops,bombs,finishes;
int check_energy(int which,int ani){return self->modeldata.type!=0;} /* paired cached idle descriptor cost/only/disable=0; predicate proved separately */
void dropweapon(int n){drops++;}void smart_bomb(entity*e,int n){bombs++;}void common_attack_finish(void){finishes++;}
"""+shot+'\n'+diff+'\n'+proc+'\nint main(void){\n'
 for c in rows:
  code+='self->animation=&live;self->tocost=(int)'+str(c['tocost'])+'u;self->reactive=(int)'+str(c['reactive'])+'u;self->attacking=99;self->mp=77;self->health=88;self->modeldata.type='+str(c['type'])+';live.energycost.cost='+str(c['cost'])+';smartbomber='+('&other'if c['smart_other']else'NULL')+';drops=bombs=finishes=0;common_attack_proc();printf("%u,%u,%u,%u,%u,%d,%d,%d\\n",(unsigned)self->mp,(unsigned)self->health,(unsigned)self->tocost,(unsigned)self->reactive,(unsigned)self->attacking,drops,bombs,finishes);\n'
 code+='return 0;}\n';(a.output/'finished.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-ei','-bt=nt','finished.c','-fe=finished.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 log=subprocess.check_output([str(a.output/'finished.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()];expected=[[77-(c['cost']if c['tocost']and c['type']!=0 else 0),88-(c['cost']if c['tocost']and c['type']==0 else 0),0,0 if c['reactive']==1 else c['reactive'],0,0,0,1]for c in rows];ok=actual==expected
 r=dict(schema='BYOR_4086_FINISHED_ATTACK_PROC_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,cases=len(rows),inputs=rows,actual=actual,expected=expected,source_functions_unmodified=['common_attack_proc','subtract_shot','diff'],function_sha256={n:hashlib.sha256(f.encode()).hexdigest()for n,f in [('common_attack_proc',proc),('subtract_shot',shot),('diff',diff)]},instrumented_services=['paired cost-zero cached-idle check_energy','common_attack_finish','smart_bomb','dropweapon'],domain='grounded; smartbomber NULL/other; NULL weapent; full32 reactive and tocost',motu_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],len(rows),'literal grounded callback cases');assert ok
if __name__=='__main__':main()
