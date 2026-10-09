"""Unchanged source falling helper and full signed landing marker comparison."""
import argparse,hashlib,itertools,json,os,struct,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_player_run_4086 import KEYS


def cases():
    return [dict(port=p,autoland=a,keys=k,marker=m)for p,a,k,m in itertools.product(range(4),(-2147483648,-1,0,1,2,65538),
        (0,KEYS['moveup'],KEYS['jump'],KEYS['moveup']|KEYS['jump'],0xffffffff),(-2147483648,-3,0,7,2147483647))]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    source=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1');body=extract(source,'player_fall_check')
    rows=cases()
    code=r"""
#include <stdio.h>
#include <io.h>
#include <fcntl.h>
typedef unsigned int u32;
typedef struct{int playerindex,damage_on_landing;}entity;entity e,*self=&e;
typedef struct{u32 keys;}s_player;s_player player[4];int autoland;
"""+f"#define FLAG_MOVEUP {KEYS['moveup']}u\n#define FLAG_JUMP {KEYS['jump']}u\n"+body+'\n'
    code+='u32 rows[][4]={'+',\n'.join('{'+','.join(str(c[k]&0xffffffff)+'u'for k in ('port','autoland','keys','marker'))+'}'for c in rows)+'};\n'
    code+=r"""
int main(void){unsigned i;u32 *r,v;setmode(fileno(stdout),O_BINARY);if(sizeof(int)!=4)return 3;
for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){r=rows[i];self->playerindex=r[0];autoland=(int)r[1];player[r[0]].keys=r[2];self->damage_on_landing=(int)r[3];
player_fall_check();v=(u32)self->damage_on_landing;fwrite(&v,4,1,stdout);}return 0;}
"""
    (out/'fall.c').write_text(code)
    build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','fall.c','-fe=fall.exe'],cwd=out,
        env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT'),capture_output=True,text=True)
    (out/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise ValueError('SOURCE_FALL_AUTHORITY_BUILD')
    actual=subprocess.check_output([str(out/'fall.exe')],cwd=out);mask=KEYS['moveup']|KEYS['jump']
    expected=b''.join(struct.pack('<I',(-2 if c['autoland']!=2 and c['keys']&mask==mask else c['marker'])&0xffffffff)for c in rows)
    report=dict(schema='BYOR_4086_PLAYER_FALL_AUTHORITY_V1',status='PASS'if actual==expected else'FAIL',engine_commit=ENGINE_COMMIT,
        literal_function_sha256=hashlib.sha256(body.encode()).hexdigest(),literal_function_unmodified=True,cases=len(rows),compared_bytes=len(expected),
        actual_sha256=hashlib.sha256(actual).hexdigest(),expected_sha256=hashlib.sha256(expected).hexdigest(),native_bound=False,motu_gameplay_proven=False)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'fall authority cases');assert actual==expected


if __name__=='__main__':main()
