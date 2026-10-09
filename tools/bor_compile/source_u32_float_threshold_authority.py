"""Pinned release-attack float expression with exact source integer widths."""
import argparse,hashlib,json,os,random,struct,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_u32_float_threshold_4086 import compare,binary32
DURATIONS={0:0,200:1,400:2,800:4,8000:40,25600:128,65500:327.5}

def cases():
    rng=random.Random(4086);rows=[]
    for delay in DURATIONS:
        stalls=[0,1,399,400,401,0xffffffff,0xffffff00,0xffffff7f,0xffffff80]
        for bit in range(24,33):
            stalls += [((1<<bit)+offset)&0xffffffff for offset in(-257,-256,-255,-129,-128,-127,-3,-2,-1,0,1,2,3,127,128,129,255,256,257)]
        stalls += [rng.getrandbits(32)for _ in range(32)]
        for stall in stalls:
            threshold=int(binary32(binary32(stall)+delay))
            for offset in(-257,-1,0,1,257):
                time=min(0xffffffff,max(0,threshold+offset));rows.append(dict(stall=stall,time=time,delay=delay,fault=0))
    return rows

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    source=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1');full=extract(source,'player_think')
    start=full.index('self->stalltime + (GAME_SPEED * self->modeldata.animation[animattacks[');end=full.index(' < time',start)+len(' < time');expression=full[start:end]
    rows=cases();code=r"""
#include <stdio.h>
#include <io.h>
#include <fcntl.h>
#define GAME_SPEED 200
typedef unsigned int u32;
struct anim{float chargetime;}anim;
struct entity{u32 stalltime;struct{int chainlength,atchain[1];struct anim *animation[1];}modeldata;}e,*self=&e;
int animattacks[1]={0};u32 time;
int compare_source(void){return
"""+expression+';}\n'
    code+='struct row{u32 stall,time;float chargetime;}rows[]={'+',\n'.join('{'+str(c['stall'])+'u,'+str(c['time'])+'u,'+str(float(DURATIONS[c['delay']]))+'f}'for c in rows)+'};\n'
    code+=r"""
int main(void){unsigned i;u32 result;setmode(fileno(stdout),O_BINARY);if(sizeof(u32)!=4||sizeof(float)!=4)return 3;e.modeldata.chainlength=1;e.modeldata.atchain[0]=1;e.modeldata.animation[0]=&anim;
for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){e.stalltime=rows[i].stall;time=rows[i].time;anim.chargetime=rows[i].chargetime;result=compare_source();fwrite(&result,4,1,stdout);}return 0;}
"""
    (out/'threshold.c').write_text(code);build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','threshold.c','-fe=threshold.exe'],cwd=out,env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT'),capture_output=True,text=True);(out/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise ValueError('U32_FLOAT_THRESHOLD_SOURCE_BUILD')
    actual=subprocess.check_output([str(out/'threshold.exe')],cwd=out);expected=b''.join(struct.pack('<I',compare(c['stall'],c['time'],c['delay']))for c in rows)
    makefile=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/Makefile'])
    assert b'ARCHFLAGS       = -m32' in makefile and b'-mfpmath' not in makefile
    gcc=out/'gcc_expression.s';gcc_exe=Path('C:/msys64/mingw64/bin/gcc.exe')
    probe=out/'gcc_expression.c';probe.write_text('typedef unsigned int u32;struct anim{float chargetime;}anim;struct entity{u32 stalltime;struct{int chainlength,atchain[1];struct anim *animation[1];}modeldata;}e,*self=&e;int animattacks[1]={0};u32 time;\n#define GAME_SPEED 200\nint probe(void){return '+expression+';}\n')
    gcc_env=dict(os.environ,PATH=str(gcc_exe.parent)+';'+os.environ['PATH'])
    subprocess.run([str(gcc_exe),'-m32','-O2','-S',str(probe),'-o',str(gcc)],env=gcc_env,check=True,capture_output=True)
    macros=subprocess.check_output([str(gcc_exe),'-m32','-O2','-dM','-E',str(probe)],env=gcc_env).decode()
    assert '#define __FLT_EVAL_METHOD__ 2' in macros and '#define __SIZEOF_POINTER__ 4' in macros
    (out/'gcc_macros.txt').write_text('\n'.join(l for l in macros.splitlines()if 'FLT_EVAL_METHOD' in l or 'SIZEOF_POINTER' in l or '__GNUC__' in l)+'\n')
    gcc_version=subprocess.check_output([str(gcc_exe),'--version'],env=gcc_env).decode().splitlines()[0]
    report=dict(schema='BYOR_4086_U32_FLOAT_THRESHOLD_AUTHORITY_V1',status='PASS'if actual==expected else'FAIL',engine_commit=ENGINE_COMMIT,player_think_sha256=hashlib.sha256(full.encode()).hexdigest(),literal_expression=expression,literal_expression_sha256=hashlib.sha256(expression.encode()).hexdigest(),literal_expression_unmodified=True,cases=len(rows),compared_bytes=len(expected),actual_sha256=hashlib.sha256(actual).hexdigest(),expected_sha256=hashlib.sha256(expected).hexdigest(),tested_chargetime_products=DURATIONS,evaluation_policy='WIN32_X87_EXTENDED',makefile_sha256=hashlib.sha256(makefile).hexdigest(),gcc_probe_sha256=hashlib.sha256(gcc.read_bytes()).hexdigest(),gcc_probe_compiler_version=gcc_version,gcc_eval_method=2,gcc_pointer_bytes=4,original_engine_binary_disassembly_proven=False,binary32_result_differences=sum(compare(c['stall'],c['time'],c['delay'],'BINARY32')!=compare(c['stall'],c['time'],c['delay'])for c in rows),native_bound=False,release_attack_body_bound=False,motu_gameplay_proven=False)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'source float threshold cases');assert actual==expected
if __name__=='__main__':main()
