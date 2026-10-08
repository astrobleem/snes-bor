"""Literal pinned combo choice/preinput with costmove mutation instrumented."""
import argparse,hashlib,json,os,random,re,struct,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_player_combo_4086 import select
from source_player_input_4086 import empty_player

from source_script_input import authority
CONTROL=sum(r['mask']for r in authority()['keys']if r['name']in ('special','attack','attack2','attack3','attack4','jump','moveup','movedown','moveleft','moveright'))


def inputs(authored):
    rng=random.Random(4086);groups=[m['combos']for m in authored['models']if m['combos']]
    for n in range(2400):
        combos=[dict(c)for c in groups[n%len(groups)]]
        # Synthetic overlapping commands exercise longest-choice and equal ties.
        if n%3==0:
            combos=[dict(anim=2,cancel=0,frame_min=0,frame_max=0,hits=0,input=[4]),
                    dict(anim=3,cancel=0,frame_min=0,frame_max=0,hits=0,input=[8,4]),
                    dict(anim=4,cancel=0,frame_min=0,frame_max=0,hits=0,input=[8,4])]
        if n%5==0:
            combos=[dict(c,cancel=5,frame_min=1,frame_max=3,hits=2)for c in combos]
        p=empty_player();p['combostep']=n%27;p['playkeys']=(0,4,0x80001dfc,0xffffffff)[n%4]
        p['combokey']=[rng.getrandbits(32)for _ in range(27)]
        target=combos[n%len(combos)]
        for j,k in enumerate(target['input']):p['combokey'][(p['combostep']-len(target['input'])+j)%27]=k
        if n%7==0:p['combokey'][(p['combostep']-1)%27]=0
        state=dict(cancel=(0,3)[n%2],animnum=(4,5,6)[n%3],animpos=n%5,animhits=n%4,
                   idling=n%3!=0,alt=(0,1,2,-2)[(n//4)%4],base=0)
        # Each anim's three decisions are independent, including MP short circuit.
        flags={c['anim']:(rng.randrange(2),rng.randrange(2),rng.randrange(2))for c in combos}
        trace=[]
        def valid(a):trace.append(10000+a);return flags[a][0]
        def energy(which,a):trace.append((20000 if which else 30000)+a);return flags[a][1 if which else 2]
        chosen=select(combos,p,state,valid,energy)if p['playkeys']else-1
        allowed=n%3!=0;costcalls=0
        if chosen>=0:trace.append(40000+chosen);costcalls=1
        accepted=int(chosen>=0 and allowed)
        expectedkeys=p['playkeys']&~CONTROL if accepted else p['playkeys']
        h=2166136261
        for op in trace:h=((h^op)*16777619)&0xffffffff
        yield dict(combos=combos,p=p,state=state,flags=flags,allowed=allowed,jumping=n%2,
                   expected=struct.pack('<5I',chosen&0xffffffff,accepted,expectedkeys,costcalls,h))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--combos',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    source=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
    header=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.h'])
    if hashlib.sha256(header).hexdigest()!=authority()['files']['engine/openbor.h']:raise ValueError('SOURCE_COMBO_HEADER_AUTHORITY')
    key_enum=re.search(r'typedef enum\s*\{[^}]*\}\s*e_key_def\s*;',header.decode('latin1'),re.S)[0]
    functions={n:extract(source,n)for n in ('diff','match_combo','check_combo','player_preinput')}
    rows=list(inputs(json.loads(a.combos.read_text())))
    code='''#include <stdio.h>
#include <string.h>
#include <io.h>
#include <fcntl.h>
#define MAX_SPECIAL_INPUTS 27
KEY_ENUM
#define COST_CHECK_MP 1
#define COST_CHECK_HP 0
typedef unsigned long u32;
typedef struct {int anim,cancel;struct {int min,max;}frame;int hits,steps,input[27];}s_com;
typedef struct {int combostep;u32 combokey[27],playkeys;}s_player;
typedef struct {int cancel,animhits;}animation;
typedef struct {int playerindex,animnum,animpos,idling,jumping;struct {float y;}position;float base;animation*animation;struct {int specials_loaded;s_com*special;}modeldata;}entity;
s_player player[4];entity e,*self=&e;animation live;s_com commands[16];
int flags[256][3],allowed,chosen,costcalls;u32 h;
void trace(int v){h=(h^(u32)v)*16777619UL;}
int validanim(entity*e,int a){trace(10000+a);return flags[a][0];}
int check_energy(int which,int a){trace((which?20000:30000)+a);return flags[a][which?1:2];}
int check_costmove(int a,int fs,int jumping){trace(40000+a);chosen=a;costcalls++;return allowed;}
'''.replace('KEY_ENUM',key_enum)+ '\n'.join(functions.values())+'\nint main(void){u32 row[5];int ret;setmode(fileno(stdout),O_BINARY);if(sizeof(u32)!=4)return3;\n'.replace('return3','return 3')
    for c in rows:
        s=c['state'];p=c['p'];code+='memset(commands,0,sizeof(commands));memset(flags,0,sizeof(flags));memset(&e,0,sizeof(e));memset(player,0,sizeof(player));e.animation=&live;e.modeldata.special=commands;'
        for k in ('animnum','animpos','idling'):code+='e.'+k+'='+str(int(s[k]))+';'
        code+='live.cancel='+str(s['cancel'])+';live.animhits='+str(s['animhits'])+';e.position.y='+str(s['alt'])+';e.base=0;e.jumping='+str(c['jumping'])+';e.modeldata.specials_loaded='+str(len(c['combos']))+';player[0].combostep='+str(p['combostep'])+';player[0].playkeys=0x%08xUL;'%p['playkeys']
        for i,k in enumerate(p['combokey']):code+='player[0].combokey[%d]=0x%08xUL;'%(i,k)
        for i,b in enumerate(c['combos']):
            for k in ('anim','cancel','hits'):code+='commands[%d].%s=%d;'%(i,k,b[k])
            code+='commands[%d].frame.min=%d;commands[%d].frame.max=%d;commands[%d].steps=%d;'%(i,b['frame_min'],i,b['frame_max'],i,len(b['input']))
            for j,v in enumerate(b['input']):code+='commands[%d].input[%d]=(int)0x%08xUL;'%(i,j,v)
        for a,flags in c['flags'].items():
            for j,v in enumerate(flags):code+='flags[%d][%d]=%d;'%(a,j,v)
        code+='h=2166136261UL;chosen=-1;costcalls=0;allowed='+str(int(c['allowed']))+';ret=player_preinput();row[0]=chosen;row[1]=ret;row[2]=player[0].playkeys;row[3]=costcalls;row[4]=h;fwrite(row,4,5,stdout);\n'
    code+='return 0;}\n';(out/'combo.c').write_text(code,encoding='utf-8')
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','combo.c','-fe=combo.exe'],cwd=out,env=env,capture_output=True,text=True)
    (out/'build.log').write_text(build.stdout+build.stderr,encoding='utf-8')
    if build.returncode:raise ValueError('SOURCE_COMBO_AUTHORITY_BUILD')
    actual=subprocess.check_output([str(out/'combo.exe')],cwd=out);expected=b''.join(c['expected']for c in rows);ok=actual==expected
    mismatches=[dict(case=i,actual=list(struct.unpack('<5I',actual[20*i:20*i+20])),expected=list(struct.unpack('<5I',c['expected'])))for i,c in enumerate(rows)if actual[20*i:20*i+20]!=c['expected']]
    report=dict(schema='BYOR_4086_PLAYER_COMBO_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,cases=len(rows),
                function_sha256={n:hashlib.sha256(s.encode()).hexdigest()for n,s in functions.items()},literal_functions_unmodified=True,
                ordered_query_trace_exact=ok,mismatches=mismatches[:10],actual_sha256=hashlib.sha256(actual).hexdigest(),
                check_energy_instrumented=True,check_costmove_mutation_instrumented=True,full_player_think_bound=False,motu_gameplay_proven=False)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(report['status'],len(rows),'literal combo/preinput cases');assert ok

if __name__=='__main__':main()
