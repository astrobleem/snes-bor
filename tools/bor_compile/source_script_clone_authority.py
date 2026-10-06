"""Compile pinned constructor Script_Clear/Copy without init/clear entries."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
from script_nested_authority import extract
from dialect_4086 import ENGINE_COMMIT
PRE=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define FALSE 0
#define VT_INTEGER 1
#define LONG int
#define FAILED(v) ((v)<0)
typedef struct {int vt,lVal;} ScriptVariant;
typedef struct {char names[3][8];ScriptVariant values[3];} Names;
typedef struct {Names *list;ScriptVariant *vars;} Varlist;
typedef struct {char *name;} Symbol;
typedef struct {void *pClearEntry,*pInitEntry,*pCurrentInstruction;int bReset;Symbol theSymbolTable;} Interpreter;
typedef struct Script {Interpreter *pinterpreter;char *comment;int interpreterowner,initialized;Varlist *varlist;} Script;
Script *pcurrentscript;int evaluations,cleanups;
void ScriptVariant_Init(ScriptVariant *v){memset(v,0,sizeof(*v));}
void ScriptVariant_ChangeType(ScriptVariant *v,int t){v->vt=t;}
void ScriptVariant_Clear(ScriptVariant *v){memset(v,0,sizeof(*v));}
void Script_Set_Local_Variant(Script *s,char *name,ScriptVariant *v){evaluations+=100;}
void Interpreter_Reset(Interpreter *i){evaluations+=100;}
int Interpreter_EvaluateCall(Interpreter *i){evaluations++;return 0;}
void Interpreter_Clear(Interpreter *i){evaluations+=100;}
void shutdown(int n,char *f,...){exit(7);}
void clear_named_var_list(Names *n,int mode){int i;cleanups++;for(i=0;i<3;i++)ScriptVariant_Clear(n->values+i);}
void Varlist_Clear(Varlist *v){evaluations+=100;}
'''

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 text=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openborscript.c'],cwd=a.engine).decode('latin1');names=('Varlist_Cleanup','Script_Clear','execute_init_method','Script_Copy');functions=[extract(text,n)for n in names]
 code=PRE+'\n'.join(functions)+r'''
int main(void){int srcinit,dstinit,n,i;Names names;ScriptVariant indices[1];Varlist vars;Interpreter srcprogram,oldprogram;Script src,dst;char keep[24];
if(sizeof(void*)!=4||sizeof(int)!=4)return 3;
for(n=0;n<24;n++){srcinit=n&1;dstinit=(n>>1)&1;memset(&srcprogram,0,sizeof(srcprogram));memset(&oldprogram,0,sizeof(oldprogram));memset(&src,0,sizeof(src));memset(&dst,0,sizeof(dst));memset(&names,0,sizeof(names));memset(indices,0,sizeof(indices));
vars.list=&names;vars.vars=indices;for(i=0;i<3;i++){sprintf(names.names[i],"key%d",i);names.values[i].vt=i+1;names.values[i].lVal=100+n+i;}memcpy(keep,names.names,24);
src.initialized=srcinit;src.pinterpreter=&srcprogram;src.comment="source";dst.initialized=dstinit;dst.pinterpreter=&oldprogram;dst.comment="old";dst.varlist=&vars;dst.interpreterowner=0;evaluations=cleanups=0;
Script_Clear(&dst,1);Script_Copy(&dst,&src,1);
printf("CLONE|%d|%d|%d|%d|%d|%d|%d|%d|%d|%d|%d\n",n,dst.initialized,dst.interpreterowner,dst.pinterpreter==(srcinit?&srcprogram:NULL),dst.varlist==&vars,memcmp(keep,names.names,24)==0,names.values[0].vt|names.values[1].vt|names.values[2].vt,names.values[0].lVal|names.values[1].lVal|names.values[2].lVal,evaluations,cleanups,dst.comment==(srcinit?src.comment:NULL));}return 0;}
'''
 (a.output/'clone.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');pr=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','clone.c','-fe=clone.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(pr.stdout+pr.stderr)
 if pr.returncode:raise ValueError('SCRIPT_CLONE_AUTHORITY_C_BUILD')
 log=subprocess.check_output([str(a.output/'clone.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);rows=[list(map(int,l.split('|')[1:]))for l in log.splitlines()if l.startswith('CLONE|')];expected=[[n,n&1,0,int(bool(n&3)),1,1,0,0,0,1,int(bool(n&3))]for n in range(24)]
 r=dict(schema='BYOR_4086_SCRIPT_CLONE_CONSTRUCTOR_AUTHORITY_V1',status='PASS'if rows==expected else'FAIL',engine_commit=ENGINE_COMMIT,verbatim_functions=[dict(name=n,sha256=hashlib.sha256(f.encode('latin1')).hexdigest())for n,f in zip(names,functions)],cases=len(rows),results=rows,expected=expected,scope='method-1 constructor clears non-owning script instance then copies initialized/absent model script, absent init/clear entries, named values only, zero indexed count',variant_clear_and_interpreter_bodies_instrumented=True,native_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],len(rows),'pinned C script clone cases')
 if r['status']!='PASS':raise SystemExit(1)

if __name__=='__main__':main()
