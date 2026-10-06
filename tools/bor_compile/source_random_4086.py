"""Win32 execution of the pinned 4086 rand32 and script rand authority."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_actor_numeric import random32_step,random32_limbs


SEEDS=(1234567890,0,1,0xffffffff,0x80000000,0x1234ffff,0xfedcba98)


def derive(engine,folder):
    folder.mkdir(parents=True,exist_ok=True)
    def pinned(path):return subprocess.check_output(['git','show',ENGINE_COMMIT+':'+path],cwd=engine)
    paths=('engine/source/randlib/rand32.c','engine/source/randlib/rand32.h','engine/openborscript.c')
    authority={p:pinned(p) for p in paths}
    api=extract(authority[paths[2]].decode('latin1'),'system_rand')
    (folder/'rand32.c').write_bytes(authority[paths[0]]);(folder/'rand32.h').write_bytes(authority[paths[1]])
    (folder/'types.h').write_text('typedef unsigned long long u64;\n')
    source='''#include <stdio.h>
#include "rand32.h"
typedef long LONG;
typedef int HRESULT;
typedef struct {int vt; LONG lVal;} ScriptVariant;
enum {VT_INTEGER=1,S_OK=0};
void ScriptVariant_ChangeType(ScriptVariant *v,int t){v->vt=t;}
typedef char abi_long32[(sizeof(long)==4 && sizeof(int)==4 && sizeof(unsigned long long)==8)?1:-1];
'''+api+'''
int main(void){
 unsigned long seeds[]={SEEDS};
 unsigned int i,j;ScriptVariant value;ScriptVariant *result=&value;
 for(i=0;i<sizeof(seeds)/sizeof(seeds[0]);i++){
  seed=seeds[i];
  for(j=0;j<32;j++){
   unsigned long before=seed;
   if(system_rand(0,&result,0)!=S_OK || value.vt!=VT_INTEGER)return 2;
   printf("%08lx %08lx %08lx\\n",before,seed,(unsigned long)value.lVal);
  }
 }
 return 0;
}
'''.replace('SEEDS',','.join('0x%08xUL'%s for s in SEEDS))
    (folder/'probe.c').write_text(source)
    env=os.environ.copy();env.update(WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    proc=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','probe.c','rand32.c','-fe=probe.exe'],
        cwd=folder,env=env,capture_output=True,text=True)
    (folder/'compiler.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('SOURCE_RANDOM_AUTHORITY_COMPILE_FAILED')
    output=subprocess.check_output([str((folder/'probe.exe').resolve())],cwd=folder,text=True)
    rows=[tuple(int(v,16) for v in line.split()) for line in output.splitlines()]
    expected=[]
    for start in SEEDS:
        seed=start
        for i in range(32):
            after,value=random32_step(seed)
            assert (after,value)==random32_limbs(seed)
            expected.append((seed,after,value));seed=after
    passed=rows==expected
    result=dict(schema='BYOR_SOURCE_RANDOM_AUTHORITY_4086_V1',status='PASS' if passed else 'FAIL',
        engine_commit=ENGINE_COMMIT,source_sha256={p:hashlib.sha256(v).hexdigest() for p,v in authority.items()},
        script_function_sha256=hashlib.sha256(api.encode('latin1')).hexdigest(),
        win32_32bit_long=True,comparisons=len(rows),seeds=list(SEEDS),rows=rows,
        semantics='32-bit seed truncation; full product bits 16..47 returned as signed Win32 LONG; global shared stream',
        initial_seed=1234567890,world_seed_installation_and_call_order_bound=False,
        harness='Verbatim rand32.c/header and system_rand; types.h supplies u64 and ScriptVariant shell supplies ChangeType')
    (folder/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    if not passed:raise ValueError('SOURCE_RANDOM_AUTHORITY_MISMATCH')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=derive(a.engine,a.output.resolve());print(json.dumps({k:v for k,v in r.items() if k!='rows'}))


if __name__=='__main__':main()
