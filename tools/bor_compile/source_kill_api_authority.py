"""Verbatim pinned killentity API: NULL, dead pointer, extra args, failure."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openborscript.c'],cwd=a.engine).decode('latin1');function=extract(raw,'openbor_killentity')
    source=r'''#include <stdio.h>
#define S_OK 0
#define E_FAIL -1
#define VT_INTEGER 1
typedef int HRESULT;typedef int LONG;
typedef struct {int alive;} entity;
typedef struct {int tag;union {int lVal;void *ptrVal;};} ScriptVariant;
entity entities[2];int calls,last;
void ScriptVariant_ChangeType(ScriptVariant *v,int tag){v->tag=tag;}
void kill(entity *e){calls++;last=(int)(e-entities);e->alive=0;}
''' + function + r'''
int main(void){int argc,which,hr;ScriptVariant arg,out,*args[1],*ret;
if(sizeof(void *)!=4||sizeof(LONG)!=4)return 2;
for(argc=0;argc<3;argc++)for(which=0;which<3;which++){
entities[0].alive=1;entities[1].alive=0;calls=0;last=-1;arg.tag=5;
arg.ptrVal=which?entities+which-1:NULL;out.tag=5;out.lVal=777;ret=&out;args[0]=&arg;
hr=openbor_killentity(args,&ret,argc);
printf("KILLAPI|%d|%d|%d|%d|%d|%d|%d|%d\n",argc,which,hr,ret==NULL,out.tag,out.lVal,calls,last);
}return 0;}
'''
    (folder/'killapi.c').write_text(source);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    proc=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','killapi.c','-fe=killapi.exe'],cwd=folder,env=env,capture_output=True,text=True);(folder/'build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('KILL_API_AUTHORITY_C_BUILD')
    log=subprocess.check_output([str(folder/'killapi.exe')],cwd=folder,text=True);(folder/'authority.log').write_text(log);results=[]
    for line in log.splitlines():
        if not line.startswith('KILLAPI|'):continue
        values=list(map(int,line.split('|')[1:]));argc,which=values[:2]
        expected=[argc,which,-1,1,5,777,0,-1] if not argc else [argc,which,0,0,1,int(which!=0),int(which!=0),which-1 if which else -1]
        results.append(dict(actual=values,expected=expected,pass_case=values==expected))
    ok=len(results)==9 and all(r['pass_case'] for r in results)
    report=dict(schema='BYOR_4086_KILLENTITY_API_AUTHORITY_V1',status='PASS' if ok else 'FAIL',engine_commit=ENGINE_COMMIT,function_sha256=hashlib.sha256(function.encode()).hexdigest(),cases=9,results=results,kill_body_instrumented=True,decimal_string_raw_pointer_reinterpretation_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],'9 pinned killentity API cases')
    if not ok:raise SystemExit(1)

if __name__=='__main__':main()
