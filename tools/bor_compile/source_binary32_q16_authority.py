"""32-bit C compatibility conversion authority; does not claim source float equivalence."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
from source_binary32_q16 import project,fixture_bits

def run(folder):
 folder.mkdir(parents=True,exist_ok=True);bits=fixture_bits()
 c=r'''#include <stdio.h>
#include <string.h>
unsigned cases[]={'''+','.join('0x%08xu'%b for b in bits)+r'''};
int main(void){unsigned i,b;float f;int admitted,value;
if(sizeof(int)!=4||sizeof(float)!=4)return 2;
for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
b=cases[i];memcpy(&f,&b,4);admitted=f>-32768.0f&&f<32768.0f;
value=admitted?(int)(f*65536.0f):0;printf("Q16|%u|%d|%d\n",i,admitted,value);
}return 0;}
'''
 (folder/'project.c').write_text(c);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
 p=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','project.c','-fe=project.exe'],cwd=folder,env=env,capture_output=True,text=True);(folder/'build.log').write_text(p.stdout+p.stderr)
 if p.returncode:raise ValueError('Q16_AUTHORITY_BUILD')
 output=subprocess.check_output([str((folder/'project.exe').resolve())],cwd=folder,text=True);rows=[]
 for line in output.splitlines():
  _,i,admitted,value=line.split('|');i=int(i);actual=[int(admitted),int(value)]
  try:wanted=[1,project(bits[i])]
  except ValueError:wanted=[0,0]
  rows.append(dict(bits=bits[i],actual=actual,expected=wanted,passed=actual==wanted))
 r=dict(schema='BYOR_BINARY32_Q16_COMPAT_AUTHORITY_V1',status='PASS'if len(rows)==len(bits)and all(x['passed']for x in rows)else'FAIL',c_sha256=hashlib.sha256(c.encode()).hexdigest(),cases=len(rows),results=rows,numeric_policy='ACCEPTED_COMPAT_Q16_16',source_float_equivalence=False,negative_zero_sign_preserved=False,rejected='NaN, infinity, or magnitude at least 32768',movement_error_bound='Less than one Q16.16 unit per projected input; subsequent arithmetic requires separate proof',source_colors_changed=False,no_color_reduction=True)
 (folder/'report.json').write_text(json.dumps(r,indent=2)+'\n');return r

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=run(a.output.resolve());print(r['status'],r['cases']);raise SystemExit(0 if r['status']=='PASS'else 1)
