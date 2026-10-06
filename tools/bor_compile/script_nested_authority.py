"""Compile pinned interpreter control functions in a bounded nested-call probe.

Only instruction dispatch and external services are mocked. The five control
functions are compiled verbatim from Git, with hashes retained. This establishes
control-flow policy, not a full parser/variant/entity execution certification.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from dialect_4086 import ENGINE_COMMIT


def extract(text, name):
    match = re.search(r'^(?:(?:HRESULT|int|void)\s+|entity\s*\*\s*)' + re.escape(name) + r'\s*\([^;]*?\)\s*\{', text, re.M)
    if not match: raise ValueError('AUTHORITY_FUNCTION_MISSING:' + name)
    begin = match.start(); i = text.index('{', match.start()); depth = 0; state = 'code'
    while i < len(text):
        c = text[i]; pair = text[i:i+2]
        if state == 'code':
            if pair == '//': state = 'line'; i += 2; continue
            if pair == '/*': state = 'comment'; i += 2; continue
            if c in ('"', "'"): state = c
            elif c == '{': depth += 1
            elif c == '}':
                depth -= 1
                if not depth: return text[begin:i+1]
        elif state == 'line':
            if c == '\n': state = 'code'
        elif state == 'comment':
            if pair == '*/': state = 'code'; i += 2; continue
        elif c == '\\': i += 2; continue
        elif c == state: state = 'code'
        i += 1
    raise ValueError('AUTHORITY_FUNCTION_UNTERMINATED:' + name)


PREAMBLE = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef int HRESULT; typedef int BOOL;
typedef const char *LPCSTR;
#define S_OK 0
#define E_FAIL (-1)
#define TRUE 1
#define FALSE 0
#define SUCCEEDED(h) ((h)>=0)
#define FAILED(h) ((h)<0)
#define VT_STR 3
#define IMMEDIATE 10
#define DEFERRED 11
typedef struct ScriptVariant { int vt; long lVal; } ScriptVariant;
typedef struct List { int size; void **solidlist; } List;
typedef struct Instruction Instruction;
typedef HRESULT (*Native)(ScriptVariant **, ScriptVariant **, int);
struct Instruction { int OpCode; Instruction **ptheJumpTarget; Native functionRef;
 ScriptVariant *theVal; List *theRefList; ScriptVariant *theRef; int step; };
typedef struct Interpreter {
 Instruction **pCurrentCall, **pCurrentInstruction, **pMainEntry, **pReturnEntry;
 BOOL bReset,bCallCompleted,bMainCompleted,bHasImmediateCode;
 List theInstructionList; void *ptheFunctionList;
 struct { const char *name; } theSymbolTable;
} Interpreter;
typedef struct Script { Interpreter *pinterpreter; const char *comment; } Script;
Script *pcurrentscript;
int no_nested_script=0, no_cmd_compatible=0;
HRESULT Interpreter_EvalInstruction(Interpreter *);
HRESULT Interpreter_EvaluateCall(Interpreter *);
HRESULT Interpreter_EvaluateImmediate(Interpreter *);
HRESULT Interpreter_Call(Interpreter *);
void Interpreter_Reset(Interpreter *);
int Script_Execute(Script *);
void List_Includes(void *p, Native n) { (void)p; (void)n; }
const char *List_GetName(void *p) { (void)p; return "probe"; }
void ScriptVariant_ToString(ScriptVariant *v,char *b) { sprintf(b,"%ld",v->lVal); }
void shutdown(int code,const char *message, const char *name,const char *comment) {
 fprintf(stderr,"%s %s %s",message,name,comment); exit(code);
}
'''

DRIVER = r'''
enum { MOCK_CALL=1, MOCK_TAIL=2, MOCK_RETURN=3 };
static int nested_entries, tail_executed, nesting;
static Script script;
static Instruction *outer_code[3], *nested_code[1];
static HRESULT native_updateframe(ScriptVariant **a,ScriptVariant **r,int count) {
 Interpreter *p=script.pinterpreter;
 (void)a;(void)r;(void)count;
 nested_entries++;
 p->pMainEntry=nested_code;
 nesting++;
 Script_Execute(&script);
 nesting--;
 p->pMainEntry=outer_code;
 return S_OK;
}
HRESULT Interpreter_EvalInstruction(Interpreter *p) {
 Instruction *ins=*p->pCurrentInstruction;
 HRESULT hr=S_OK;
 switch(ins->OpCode) {
 case MOCK_CALL: hr=Interpreter_Call(p); break;
 case MOCK_TAIL: tail_executed++; break;
 case MOCK_RETURN: p->bCallCompleted=TRUE; break;
 default: return E_FAIL;
 }
 p->pCurrentInstruction+=ins->step;
 return hr;
}
int main(void) {
 Interpreter interpreter;
 Instruction call,tail,ret,child_ret;
 ScriptVariant argc={0,0}; List args={0,NULL};
 int mode, result;
 memset(&interpreter,0,sizeof(interpreter));
 memset(&call,0,sizeof(call)); memset(&tail,0,sizeof(tail));
 memset(&ret,0,sizeof(ret)); memset(&child_ret,0,sizeof(child_ret));
 call.OpCode=MOCK_CALL; call.step=1; call.functionRef=native_updateframe;
 call.theRef=&argc;call.theRefList=&args;
 tail.OpCode=MOCK_TAIL;tail.step=1;
 ret.OpCode=child_ret.OpCode=MOCK_RETURN;ret.step=child_ret.step=0;
 outer_code[0]=&call;outer_code[1]=&tail;outer_code[2]=&ret;
 nested_code[0]=&child_ret;
 script.pinterpreter=&interpreter;interpreter.theSymbolTable.name="nested-authority";
 for(mode=0;mode<3;mode++) {
  interpreter.pMainEntry=outer_code;
  no_nested_script=mode==2;no_cmd_compatible=mode==1;
  nested_entries=tail_executed=nesting=0;
  Interpreter_Reset(&interpreter);
  /* Script_Compile leaves bReset FALSE before the first invocation. */
  interpreter.bReset=FALSE;
  result=Script_Execute(&script);
  printf("NESTED|%d|%d|%d|%d|%d\n",mode,result,nested_entries,tail_executed,interpreter.bReset);
 }
 return 0;
}
'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--engine-repo', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); a.output = a.output.resolve(); a.output.mkdir(parents=True, exist_ok=True)
    sources = {}
    for file in ('engine/openborscript.c', 'engine/source/scriptlib/Interpreter.c'):
        raw = subprocess.check_output(['git','-C',str(a.engine_repo),'show',ENGINE_COMMIT+':'+file])
        sources[file] = (raw, raw.decode('latin1'))
    blocks = []; functions = []
    names = ['Script_Execute','Interpreter_Reset','Interpreter_Call','Interpreter_EvaluateCall','Interpreter_EvaluateImmediate']
    for name in names:
        file = 'engine/openborscript.c' if name == 'Script_Execute' else 'engine/source/scriptlib/Interpreter.c'
        block = extract(sources[file][1],name); blocks.append(block)
        functions.append(dict(name=name,source_path=file,sha256=hashlib.sha256(block.encode('latin1')).hexdigest()))
    path = a.output / 'nested.c'; path.write_text(PREAMBLE+'\n'+'\n\n'.join(blocks)+'\n'+DRIVER)
    env = os.environ.copy(); env['WATCOM']='C:/WATCOM'; env['INCLUDE']='C:/WATCOM/H;C:/WATCOM/H/NT'
    proc = subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','-fe=nested.exe','nested.c'],
                          cwd=a.output,env=env,capture_output=True,text=True)
    (a.output/'compiler.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode: raise ValueError('PINNED_NESTED_AUTHORITY_COMPILE')
    proc = subprocess.run([str(a.output/'nested.exe')],capture_output=True,text=True)
    (a.output/'execution.log').write_text(proc.stdout+proc.stderr)
    rows = [list(map(int,l.split('|')[1:])) for l in proc.stdout.splitlines() if l.startswith('NESTED|')]
    expected = [[0,1,1,0,0],[1,1,1,1,0],[2,1,1,1,0]]
    report = dict(schema='BYOR_PINNED_NESTED_CONTROL_AUTHORITY_V1',status='PASS' if proc.returncode==0 and rows==expected else 'FAIL',
        engine_authority=ENGINE_COMMIT,source_files=[dict(path=f,sha256=hashlib.sha256(r).hexdigest()) for f,(r,t) in sources.items()],
        verbatim_functions=functions,observations=rows,expected=expected,
        scope='Pinned control functions with mocked instruction dispatch and external services; same-interpreter nested callback. No full parser, variants, entity or native SNES proof.',
        default_nested_call_resumes_outer_tail=False,native_bound=False)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if report['status'] != 'PASS': raise SystemExit(1)


if __name__ == '__main__': main()
