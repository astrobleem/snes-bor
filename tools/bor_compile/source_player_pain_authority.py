"""Pinned pain helper callback ordering and fresh inpain cleanup."""
import argparse,hashlib,itertools,json,os,struct,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    source=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
    body=extract(source,'player_pain_check')
    rows=list(itertools.product((-2147483648,-7,0,1,7,2147483647),(0,1,-3),(0,1)))
    code=r"""
#include <stdio.h>
#include <io.h>
#include <fcntl.h>
typedef unsigned int u32;
typedef struct{int inpain;}entity;entity e,*self=&e;
int outcome,mutation;u32 calls;
int player_check_special(void){calls++;if(mutation)self->inpain=-3;return outcome;}
"""+body+'\n'
    code+='u32 rows[][3]={'+',\n'.join('{'+','.join(str(v&0xffffffff)+'u'for v in row)+'}'for row in rows)+'};\n'
    code+=r"""
int main(void){unsigned i;u32 result[2],*r;setmode(fileno(stdout),O_BINARY);
if(sizeof(int)!=4)return 3;
for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){r=rows[i];self->inpain=(int)r[0];outcome=(int)r[1];mutation=r[2];calls=0;
player_pain_check();result[0]=(u32)self->inpain;result[1]=calls;fwrite(result,4,2,stdout);}return 0;}
"""
    (out/'pain.c').write_text(code)
    build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','pain.c','-fe=pain.exe'],cwd=out,
        env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT'),capture_output=True,text=True)
    (out/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise ValueError('SOURCE_PAIN_AUTHORITY_BUILD')
    actual=subprocess.check_output([str(out/'pain.exe')],cwd=out)
    expected=b''.join(struct.pack('<2I',(0 if result else -3 if mutation else inpain)&0xffffffff,1)for inpain,result,mutation in rows)
    report=dict(schema='BYOR_4086_PLAYER_PAIN_AUTHORITY_V1',status='PASS'if actual==expected else'FAIL',engine_commit=ENGINE_COMMIT,
        literal_function_sha256=hashlib.sha256(body.encode()).hexdigest(),literal_function_unmodified=True,cases=len(rows),compared_bytes=len(expected),
        actual_sha256=hashlib.sha256(actual).hexdigest(),expected_sha256=hashlib.sha256(expected).hexdigest(),callback_instrumented=True,
        native_canonical_binding_proven=False,motu_gameplay_proven=False)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'pain authority cases');assert actual==expected


if __name__=='__main__':main()
