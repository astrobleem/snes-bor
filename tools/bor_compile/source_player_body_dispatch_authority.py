"""Compare unchanged source body dispatch against every crossed branch."""
import argparse,hashlib,itertools,json,os,struct,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_player_body_dispatch_4086 import select

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    source=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
    full=extract(source,'player_think');body=full[full.index('    // falling? check for landing'):full.index('    // cant do anything if busy')]
    names=('projectile','grabbing','attacking','throw_wait','jumping','drop','y','base','vy')
    rows=[dict(zip(names,r))for r in itertools.product((0,2,65538),(0,-3),(0,-5),(0,1),(0,-7),(0,-9),(-1,0,1),(-1,0,1),(-1,0,1))]
    code=r"""
#include <stdio.h>
#include <string.h>
#include <io.h>
#include <fcntl.h>
typedef unsigned int u32;
struct entity {int projectile,grabbing,attacking,jumping,drop;void (*takeaction)(void);struct {float y;}position,velocity;float base;}e,*self=&e;
u32 trace;void common_throw_wait(void){}
void player_fall_check(void){trace=1;}void player_grab_check(void){trace=2;}
void player_jump_check(void){trace=3;}void player_lie_check(void){trace=4;}
void player_think(void){
"""+body+'trace=5;\nendthinkcheck:return;\n}\n'
    code+='int rows[][9]={'+',\n'.join('{'+','.join(str(c[k])for k in names)+'}'for c in rows)+'};\n'
    code+=r"""
int main(void){unsigned i;int *r;setmode(fileno(stdout),O_BINARY);if(sizeof(int)!=4||sizeof(void*)!=4)return 3;
for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){r=rows[i];memset(&e,0,sizeof(e));e.projectile=r[0];e.grabbing=r[1];e.attacking=r[2];e.takeaction=r[3]?common_throw_wait:NULL;e.jumping=r[4];e.drop=r[5];e.position.y=(float)r[6];e.base=(float)r[7];e.velocity.y=(float)r[8];trace=0;player_think();fwrite(&trace,4,1,stdout);}return 0;}
"""
    (out/'dispatch.c').write_text(code)
    build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','dispatch.c','-fe=dispatch.exe'],cwd=out,env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT'),capture_output=True,text=True)
    (out/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise ValueError('SOURCE_PLAYER_BODY_DISPATCH_BUILD')
    actual=subprocess.check_output([str(out/'dispatch.exe')],cwd=out)
    ids=dict(FALL=1,GRAB=2,JUMP=3,LIE=4,CONTINUE=5);expected=b''.join(struct.pack('<I',ids[select(c)])for c in rows)
    report=dict(schema='BYOR_4086_PLAYER_BODY_DISPATCH_AUTHORITY_V1',status='PASS'if actual==expected else'FAIL',engine_commit=ENGINE_COMMIT,player_think_sha256=hashlib.sha256(full.encode()).hexdigest(),literal_body_sha256=hashlib.sha256(body.encode()).hexdigest(),literal_body_unmodified=True,cases=len(rows),compared_bytes=len(expected),actual_sha256=hashlib.sha256(actual).hexdigest(),expected_sha256=hashlib.sha256(expected).hexdigest(),helper_callbacks_instrumented=True,coordinates='exact integer binary32; native Q16 accepted compatibility',native_grab_owner_bound=False,full_player_think_bound=False,motu_gameplay_proven=False)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'body dispatch authority cases');assert actual==expected

if __name__=='__main__':main()
