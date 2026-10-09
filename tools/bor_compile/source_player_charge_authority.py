"""Compare charging helper against unchanged pinned BOR C, with callback order."""
import argparse,hashlib,itertools,json,os,struct,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_player_run_4086 import KEYS


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    source=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
    body=extract(source,'player_charge_check')
    rows=[dict(port=port,keys=0x80000000|mask,charging=charging,action=action,mutation=mutation)
          for port,mask,charging,action,mutation in itertools.product(range(4),(0,KEYS['jump'],KEYS['special'],KEYS['jump']|KEYS['special']),(-2147483648,0,1,7),(0,17),range(2))]
    code=r"""
#include <stdio.h>
#include <io.h>
#include <fcntl.h>
typedef unsigned int u32;
typedef struct{int playerindex,charging;void(*takeaction)(void);}entity;
typedef struct{u32 keys;}s_player;
entity e,*self=&e;s_player player[4];u32 calls,prefix,mutation;
void set_idle(entity *ent){calls++;prefix=ent->charging==0&&ent->takeaction==NULL;
 if(mutation){ent->charging=7;ent->takeaction=(void(*)(void))9;}}
"""
    code+=f"#define FLAG_JUMP {KEYS['jump']}u\n#define FLAG_SPECIAL {KEYS['special']}u\n"+body+'\n'
    code+='u32 rows[][5]={'+',\n'.join('{'+','.join(str(c[k]&0xffffffff)+'u'for k in ('port','keys','charging','action','mutation'))+'}'for c in rows)+'};\n'
    code+=r"""
int main(void){unsigned i;u32 result[4],*r;setmode(fileno(stdout),O_BINARY);
 if(sizeof(void*)!=4||sizeof(u32)!=4)return 3;
 for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){r=rows[i];self->playerindex=r[0];player[r[0]].keys=r[1];
 self->charging=(int)r[2];self->takeaction=(void(*)(void))r[3];mutation=r[4];calls=prefix=0;
 player_charge_check();result[0]=(u32)self->charging;result[1]=(u32)self->takeaction;result[2]=calls;result[3]=prefix;
 fwrite(result,4,4,stdout);}return 0;}
"""
    (out/'charge.c').write_text(code)
    build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','charge.c','-fe=charge.exe'],cwd=out,
        env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT'),capture_output=True,text=True)
    (out/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise ValueError('SOURCE_CHARGE_AUTHORITY_BUILD')
    actual=subprocess.check_output([str(out/'charge.exe')],cwd=out)
    expected=b''
    for c in rows:
        held=bool(c['keys']&KEYS['jump']and c['keys']&KEYS['special'])
        values=(c['charging'],c['action'],0,0)if held else (7,9,1,1)if c['mutation']else(0,0,1,1)
        expected+=struct.pack('<4I',*(v&0xffffffff for v in values))
    report=dict(schema='BYOR_4086_PLAYER_CHARGE_AUTHORITY_V1',status='PASS'if actual==expected else'FAIL',engine_commit=ENGINE_COMMIT,
        literal_function_sha256=hashlib.sha256(body.encode()).hexdigest(),literal_function_unmodified=True,cases=len(rows),compared_bytes=len(expected),
        actual_sha256=hashlib.sha256(actual).hexdigest(),expected_sha256=hashlib.sha256(expected).hexdigest(),callback_instrumented=True,
        callback_prefix_observed=True,native_canonical_binding_proven=False,motu_gameplay_proven=False)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'charging authority cases');assert actual==expected


if __name__=='__main__':main()
