"""Closed-source uninitialized onfall, with the literal pinned dispatcher."""
import argparse,hashlib,json,os,re,subprocess
from pathlib import Path
from compiler import Source
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_uninitialized_onpain import derive as closed,emit as finish

def derive(source):
 r=closed(source,kind='onfall');assert r['schema']=='BYOR_UNINITIALIZED_ONFALL_REQUIREMENTS_V1'and all(m['onfall_initialized']is False for m in r['models']);return r
def emit(work,requirements,sy):return finish(work,requirements,sy,kind='onfall',magic=0xb6b6,prefix='SetFall')

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);req=derive(Source(a.source))
 engine=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1');scripts=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openborscript.c']).decode('latin1');initialized=extract(scripts,'Script_IsInitialized');onfall=extract(engine,'execute_onfall_script');alloc=re.search(r'Script \*alloc_script\(\)\s*\{.*?\n\}',scripts,re.S)[0];assert 'calloc(1, sizeof(*pscript))'in alloc
 code='''#include <stdio.h>
#include <string.h>
#define LONG int
#define VOID void
#define VT_PTR 3
#define VT_INTEGER 1
typedef struct{int initialized;}Script;
typedef struct{Script*onfall_script;}Scripts;
typedef struct{Scripts*scripts;}entity;
typedef struct{void*ptrVal;int lVal;}ScriptVariant;
int actions;
void ScriptVariant_Init(ScriptVariant*v){actions++;memset(v,0,sizeof(*v));}
void ScriptVariant_ChangeType(ScriptVariant*v,int t){actions++;}
void Script_Set_Local_Variant(Script*s,char*n,ScriptVariant*v){actions++;}
void Script_Execute(Script*s){actions++;}
void ScriptVariant_Clear(ScriptVariant*v){actions++;}
'''+initialized+'\n'+onfall+'''
int main(void){Script s;Scripts scripts;entity e,other;int init,type,force;scripts.onfall_script=&s;e.scripts=&scripts;other.scripts=&scripts;
for(init=0;init<2;init++)for(type=-1;type<=20;type++)for(force=0;force<2;force++){
s.initialized=init;actions=0;execute_onfall_script(&e,&other,force*7,1,type,2,3,4,5);printf("ONFALL|%d|%d|%d|%d\\n",init,type,force,actions);}return 0;}
'''
 (a.output/'authority.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');q=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','authority.c','-fe=authority.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(q.stdout+q.stderr)
 if q.returncode:raise ValueError('ONFALL_C_BUILD')
 log=subprocess.check_output([str(a.output/'authority.exe')],text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split('|')[1:]))for l in log.splitlines()if l.startswith('ONFALL|')];expected=[[i,t,f,23 if i else 0]for i in range(2)for t in range(-1,21)for f in range(2)]
 report=dict(schema='BYOR_UNINITIALIZED_ONFALL_AUTHORITY_V1',status='PASS'if actual==expected else'FAIL',cases=len(actual),actual=actual,expected=expected,engine_commit=ENGINE_COMMIT,source_functions_unmodified=True,source_function_sha256={n:hashlib.sha256(v.encode('latin1')).hexdigest()for n,v in [('Script_IsInitialized',initialized),('execute_onfall_script',onfall)]},source_zero_allocator_sha256=hashlib.sha256(alloc.encode('latin1')).hexdigest(),requirements=req,initialized_branch_instrumented=True,initialized_branch_native_admitted=False,motu_gameplay_proven=False,no_color_reduction=True);(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(req['models']),'models',len(actual),'literal cases')
 if actual!=expected:raise SystemExit(1)
if __name__=='__main__':main()
