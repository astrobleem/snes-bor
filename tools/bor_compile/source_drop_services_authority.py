"""Verbatim pinned randf, diff and inair C; constant lookup and air threshold."""
import argparse,hashlib,json,os,struct,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_random_float_4086 import values,pack,unpack,bits,f32
from source_binary32_q16 import project

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--maximum',type=float,default=40);p.add_argument('--output',type=Path,required=True);a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
 raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=a.engine).decode('latin1');functions={n:extract(raw,n)for n in('randf','diff','inair')}
 default_init=extract(raw,'ent_default_init');assert 'videomodes.vRes + randf(40)'in default_init
 air=[]
 for y in(0,1,0x3dccccc9,0x3dcccccc,0x3dcccccd,0x3dccccce,0x3e000000,0x3f000000,0x43700000):
  for sign in(0,0x80000000):air.append((y|sign,0))
 air.extend([(bits(240),bits(240)),(bits(240),bits(239.9)),(bits(240),bits(239.90001)),(bits(-240),bits(-239.9))])
 pre='''#include <stdio.h>
#include <string.h>
typedef struct {struct {float y;} position;float base;} entity;
unsigned number,calls;
unsigned rand32(void){calls++;return number;}
unsigned bits(float f){unsigned u;memcpy(&u,&f,4);return u;}
float frombits(unsigned u){float f;memcpy(&f,&u,4);return f;}
'''
 source=pre+'\n'.join(functions.values())+'\nunsigned airs[][2]={'+','.join('{%uu,%uu}'%r for r in air)+'};\n'+'''int main(void){unsigned i;entity e;float f;
 if(sizeof(unsigned)!=4||sizeof(float)!=4||sizeof(void*)!=4)return 2;
 for(i=0;i<10000;i++){number=i;calls=0;f=randf(frombits(MAXIMUMBITS));printf("RAND|%u|%u|%d|%u\\n",i,bits(f),(int)(f*65536),calls);}
 calls=0;f=randf(0);printf("ZERO|%u|%u\\n",bits(f),calls);
 for(i=0;i<sizeof(airs)/sizeof(airs[0]);i++){e.position.y=frombits(airs[i][0]);e.base=frombits(airs[i][1]);printf("AIR|%u|%d|%u\\n",i,inair(&e),bits(diff(e.position.y,e.base)));}
 return 0;}
'''.replace('MAXIMUMBITS',str(bits(f32(a.maximum)))+'u')
 (folder/'services.c').write_text(source);env=os.environ.copy();env.update(WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
 proc=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','services.c','-fe=services.exe'],cwd=folder,env=env,capture_output=True,text=True);(folder/'build.log').write_text(proc.stdout+proc.stderr)
 if proc.returncode:raise ValueError('SOURCE_DROP_SERVICES_C_COMPILE')
 output=subprocess.check_output([str(folder/'services.exe')],cwd=folder,text=True);(folder/'authority.log').write_text(output)
 results=[list(map(int,line.split('|')[1:]))for line in output.splitlines()if line.startswith('RAND|')];expected=[r[1]for r in results];table=pack(a.maximum,expected);projected=unpack(table,expected)
 assert results==[[i,b,projected[i],int(a.maximum!=0)]for i,b in enumerate(expected)]
 assert 'ZERO|0|0' in output
 airresults=[list(map(int,line.split('|')[1:]))for line in output.splitlines()if line.startswith('AIR|')]
 decode=lambda b:struct.unpack('<f',struct.pack('<I',b))[0]
 delta=lambda y,base:f32(decode(base)-decode(y)if decode(y)<decode(base)else decode(y)-decode(base))
 assert airresults==[[i,int(delta(y,base)>=0.1),bits(delta(y,base))]for i,(y,base)in enumerate(air)]
 (folder/'randf.b5rf').write_bytes(table)
 if a.maximum==40:(folder/'randf40.b5rf').write_bytes(table)
 (folder/'source_values.json').write_text(json.dumps(expected)+'\n')
 report=dict(schema='BYOR_4086_DROP_SERVICES_AUTHORITY_V1',status='PASS',engine_commit=ENGINE_COMMIT,function_sha256={n:hashlib.sha256(f.encode('latin1')).hexdigest()for n,f in functions.items()},constant_randf_argument=f32(a.maximum),random_comparisons=len(results),source_modulus=10000,zero_maximum_consumes_no_rng=True,lookup_bytes=len(table),lookup_sha256=hashlib.sha256(table).hexdigest(),numeric_policy='ACCEPTED_COMPAT_Q16_16',source_binary32_then_projection_preserved=True,rational_truncation_mismatches=sum(v!=n*65536//250 for n,v in enumerate(projected))if a.maximum==40 else None,inair_semantics='binary32 absolute difference >= double literal 0.1',air_inputs=air,air_results=airresults,native_q16_threshold=6554,threshold_equivalence_to_arbitrary_source_binary32=False,world_rng_order_bound=False,drop_native_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
 (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k not in('air_inputs','air_results')}))

if __name__=='__main__':main()
