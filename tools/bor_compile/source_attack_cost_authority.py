"""Pinned full common_attack_proc and check_energy: literal resource debit."""
import argparse,hashlib,json,os,re,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 def git(n):return subprocess.check_output(['git','show',ENGINE_COMMIT+':'+n],cwd='E:/gh/openbor-bcec').decode('latin1')
 raw=git('engine/openbor.c');header=git('engine/openbor.h');proc=extract(raw,'common_attack_proc');energy=extract(raw,'check_energy');diff=extract(raw,'diff')
 enums='\n'.join(re.search(r'typedef enum\s*\{[^}]*\}\s*'+n+r'\s*;',header,re.S)[0]for n in ('e_cost_check','e_cost_type','e_entity_type'))
 rows=[c for c in json.loads(a.inputs.read_text())['inputs']if not c['fault']and not c['bad']]
 code="""#include <stdio.h>
#include <stddef.h>
#define TRUE 1
#define FALSE 0
"""+enums+"""
typedef struct {struct {int cost,mponly,disable;}energycost;int numframes;}animation;
typedef struct entity {int animating,tocost,reactive,attacking,mp,health,seal,animnum;float base;struct {float y;}position;animation*animation;struct {int type,smartbomb;animation*animation[168];}modeldata;}entity;
entity ent,*self=&ent,*smartbomber=NULL;animation cached,live;
#define validanim(e,a) ((e)->modeldata.animation[a]&&(e)->modeldata.animation[a]->numframes)
void smart_bomb(entity*e,int v){}void subtract_shot(void){}void common_attack_finish(void){}
"""+energy+'\n'+diff+'\n'+proc+'\nint main(void){\n'
 for c in rows:
  f=c['fields'];code+='self->animnum='+str(c['role'])+';self->modeldata.type='+str(c['type'])+';cached.energycost.cost='+str(f['cost'])+';cached.energycost.mponly='+str(f['mponly'])+';cached.energycost.disable='+str(f['disable'])+';cached.numframes=1;self->modeldata.animation[self->animnum]='+('NULL'if c['absent']else'&cached')+';self->animation=&live;live.energycost.cost='+str(c['livecost'])+';self->mp='+str(c['mp'])+';self->health='+str(c['health'])+';self->seal='+str(c['seal'])+';self->tocost=(int)'+str(c['tocost'])+'u;common_attack_proc();common_attack_proc();printf("%u,%u,%u\\n",(unsigned)self->mp,(unsigned)self->health,(unsigned)self->tocost);\n'
 code+='return 0;}\n';(a.output/'cost.c').write_text(code)
 env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-ei','-bt=nt','cost.c','-fe=cost.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(build.stdout+build.stderr);assert build.returncode==0
 log=subprocess.check_output([str(a.output/'cost.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()];expected=[[c['expectedmp'],c['expectedhealth'],0]for c in rows];ok=actual==expected
 r=dict(schema='BYOR_4086_ATTACK_COST_AUTHORITY_V1',status='PASS'if ok else'FAIL',cases=len(rows),engine_commit=ENGINE_COMMIT,source_function_unmodified=True,check_energy_function_unmodified=True,diff_function_unmodified=True,source_function_sha256=hashlib.sha256(proc.encode()).hexdigest(),check_energy_sha256=hashlib.sha256(energy.encode()).hexdigest(),actual=actual,expected=expected,other_services_instrumented=True,domain='grounded/nonanimating, smartbomber NULL, reactive zero; cost block only',native_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],len(rows),'literal source cost cases');assert ok
if __name__=='__main__':main()
