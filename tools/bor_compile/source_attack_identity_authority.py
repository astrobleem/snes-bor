"""Compare attack identity assignment with the unchanged pinned do_attack block."""
import argparse,hashlib,itertools,json,os,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_attack_identity_4086 import assign


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'))
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=a.engine).decode('latin1')
    body=extract(raw,'do_attack')
    start=body.index('    current_attack_id = e->attack_id;')
    end=body.index('    force = attack->attack_force;',start)
    block=body[start:end]
    if 'static unsigned int new_attack_id = 1;' not in body or 'int current_attack_id;' not in body:
        raise ValueError('SOURCE_ATTACK_ID_AUTHORITY')
    values=(0,1,2,65535,65536,0x7fffffff,0x80000000,0xfffffffe,0xffffffff)
    rows=list(itertools.product(values,values))
    code="""#include <stdio.h>
#include <string.h>
typedef struct {int attack_id;} entity;
int main(void){entity actor,*e=&actor;unsigned input,new_attack_id;int current_attack_id;
if(sizeof(int)!=4 || sizeof(unsigned)!=4)return 2;
while(scanf("%u %u",&input,&new_attack_id)==2){memcpy(&actor.attack_id,&input,4);
"""+block+"""printf("%u %u %u\\n",(unsigned)actor.attack_id,new_attack_id,(unsigned)current_attack_id);
}return 0;}
"""
    (a.output/'attack_identity.c').write_text(code,encoding='latin1')
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','attack_identity.c','-fe=attack_identity.exe'],cwd=a.output,env=env,capture_output=True,text=True)
    (a.output/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise ValueError('ATTACK_ID_BUILD:'+build.stdout+build.stderr)
    inputs=''.join(f'{i} {s}\n'for i,s in rows)
    proc=subprocess.run([str((a.output/'attack_identity.exe').resolve())],input=inputs,capture_output=True,text=True)
    actual=[list(map(int,l.split()))for l in proc.stdout.splitlines()]
    expected=[[i,s,i]for i,s in (assign(*r)for r in rows)]
    passed=proc.returncode==0 and actual==expected
    report=dict(schema='BYOR_ATTACK_ID_AUTHORITY_V1',status='PASS'if passed else'FAIL',engine_commit=ENGINE_COMMIT,cases=len(rows),block_sha256=hashlib.sha256(block.encode('latin1')).hexdigest(),input_sha256=hashlib.sha256(inputs.encode()).hexdigest(),output_sha256=hashlib.sha256(proc.stdout.encode()).hexdigest(),initial_sequence=1,first_assigned_id=2,zero_wrap_skipped=True,entity_signed_storage_bits_preserved=True,production_sequence_storage_bound=False,native_combat_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'],len(rows),'pinned do_attack identity cases')
    if not passed:raise SystemExit(1)


if __name__=='__main__':main()
