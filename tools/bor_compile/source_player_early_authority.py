"""Literal BOR player_think prefix with mandatory service trace comparison."""
import argparse,hashlib,itertools,json,os,struct,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_player_early_4086 import execute,Service
from source_player_run_4086 import KEYS


def cases():
    for match,dead,time,rush,charging,inpain,link,grab,intercept,mutation in itertools.product(
            (0,1),(0,-3),(0,17,0xffffffff),(0,16,0x80000000),
            (0,-3),(0,-4),(0,1),(0,1),(0,1),range(4)):
        yield dict(match=match,dead=dead,time=time,rush=rush,charging=charging,inpain=inpain,link=link,grab=grab,intercept=intercept,mutation=mutation)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    source=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
    full=extract(source,'player_think');prefix=full[:full.index('    // falling? check for landing')]
    rows=list(cases())
    defs=''.join('#define FLAG_'+n.upper()+' '+str(KEYS[n])+'u\n'for n in ('moveleft','moveright','moveup','movedown','attack'))+'#define FLAG_BACKWARD 2147483648u\n'
    code=defs+r"""
#include <stdio.h>
#include <string.h>
#include <io.h>
#include <fcntl.h>
typedef unsigned int u32;
typedef struct entity entity;
struct entity {int running,playerindex,dead,charging,inpain;entity *link,*grabbing;struct{float x,y,z;}position;
struct{struct{int current,maximum;}count;u32 time;}rush;struct{int score,subtype;char *branch;}modeldata;};
typedef struct{entity *ent;}s_player;
entity e,other_ent,*self=&e;s_player player[4];u32 time,trace,continuation,intercept,mutation;
int reached[4],level_completed;char branch_name[256];
#define TYPE_ENDLEVEL 256
#define TYPE_PLAYER 1
#define SUBTYPE_BOTH 3
#define MAX_NAME_LEN 256
void addscore(int p,int score){}int count_ents(int type){return 1;}
float diff(float a,float b){return a>b?a-b:b-a;}
entity *find_ent_here(entity *e,float x,float z,int type,void *predicate){trace=trace*8+1;return NULL;}
int player_preinput(void){trace=trace*8+2;if(mutation==1){self->charging=7;self->inpain=0;}
else if(mutation==2){self->charging=0;self->inpain=7;}else if(mutation==3){self->charging=self->inpain=0;self->link=&other_ent;self->grabbing=NULL;}
return intercept;}
void player_charge_check(void){trace=trace*8+3;}
void player_pain_check(void){trace=trace*8+4;}
"""+prefix+'\ncontinuation=1;\nendthinkcheck:return;\n}\n'
    names=('match','dead','time','rush','charging','inpain','link','grab','intercept','mutation')
    code+='u32 rows[][10]={'+',\n'.join('{'+','.join(str(c[k]&0xffffffff)+'u'for k in names)+'}'for c in rows)+'};\n'
    code+=r"""
int main(void){unsigned i;u32 result[6],*r;setmode(fileno(stdout),O_BINARY);if(sizeof(int)!=4||sizeof(void*)!=4)return 3;
for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){r=rows[i];memset(&e,0,sizeof(e));self->running=-3;self->playerindex=2;
player[2].ent=r[0]?self:&other_ent;self->dead=(int)r[1];time=r[2];self->rush.time=r[3];self->rush.count.current=7;
self->charging=(int)r[4];self->inpain=(int)r[5];self->link=r[6]?&other_ent:NULL;self->grabbing=r[7]?&other_ent:NULL;
intercept=r[8];mutation=r[9];trace=continuation=0;player_think();result[0]=trace;result[1]=continuation;
result[2]=self->rush.count.current;result[3]=(u32)self->rush.time;result[4]=self->charging;result[5]=self->inpain;
fwrite(result,4,6,stdout);}return 0;}
"""
    (out/'early.c').write_text(code)
    build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','early.c','-fe=early.exe'],cwd=out,
        env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT'),capture_output=True,text=True)
    (out/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise ValueError('SOURCE_PLAYER_EARLY_AUTHORITY_BUILD')
    actual=subprocess.check_output([str(out/'early.exe')],cwd=out);expected=b''
    for c in rows:
        e=dict(playerindex=2,running=-3,dead=c['dead'],rush_time=c['rush'],rush_current=7,charging=c['charging'],inpain=c['inpain'],link=c['link'],grabbing=c['grab'])
        players=[dict(entity=None)for _ in range(4)];players[2]['entity']=e if c['match']else None
        context=dict(time=c['time']);gen=execute(e,context,players);trace=0;reply=None
        while True:
            try:s=gen.send(reply)
            except StopIteration as done:result=done.value;break
            trace=trace*8+int(s);reply=None
            if s==Service.PREINPUT:
                if c['mutation']==1:e.update(charging=7,inpain=0)
                elif c['mutation']==2:e.update(charging=0,inpain=7)
                elif c['mutation']==3:e.update(charging=0,inpain=0,link=1,grabbing=0)
                reply=c['intercept']
        assert context['entry_playerindex']==2 and context['oldrunning']==-3
        expected+=struct.pack('<6I',*(v&0xffffffff for v in (trace,result=='CONTINUE',e['rush_current'],e['rush_time'],e['charging'],e['inpain'])))
    errors=[i for i in range(len(rows))if actual[i*24:(i+1)*24]!=expected[i*24:(i+1)*24]]
    report=dict(schema='BYOR_4086_PLAYER_EARLY_AUTHORITY_V1',status='PASS'if actual==expected else'FAIL',engine_commit=ENGINE_COMMIT,
        player_think_sha256=hashlib.sha256(full.encode()).hexdigest(),literal_prefix_sha256=hashlib.sha256(prefix.encode()).hexdigest(),literal_prefix_unmodified=True,
        cases=len(rows),compared_bytes=len(expected),actual_sha256=hashlib.sha256(actual).hexdigest(),expected_sha256=hashlib.sha256(expected).hexdigest(),errors=errors[:8],
        endlevel_search_domain='mandatory empty search; no candidate completion admission',helper_callbacks_instrumented=True,
        native_bound=False,full_player_think_bound=False,motu_gameplay_proven=False)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'early-dispatch authority cases');assert actual==expected


if __name__=='__main__':main()
