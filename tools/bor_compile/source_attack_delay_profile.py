"""Compile literal-C randf timer delays; deduplicate by binary32 maximum."""
import argparse,hashlib,json,os,struct,subprocess
from pathlib import Path
from compiler import Source
from source_attack_timing_4086 import derive,bits
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('source','authority','output'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);authority=json.loads(a.authority.read_text());profile=derive(Source(a.source))
 if authority['status']!='PASS'or authority['engine_commit']!=ENGINE_COMMIT or not authority['literal_expressions_and_randf_unmodified']or not authority['integer_delay_lowering_proven']:raise ValueError('ATTACK_DELAY_LOWERING_AUTHORITY')
 models=profile['models'];maxima=[];rows=[]
 for m,c in zip(models,authority['profiles']):
  f=m['fields'];aggression=f['aggression'];maximum=f['attackthrottletime']
  if c!=dict(identity=m['identity'],maximum=maximum,aggression=aggression):raise ValueError('ATTACK_DELAY_MODEL_AUTHORITY')
  if not 0<=maximum<=65535 or not -65385<=aggression<=0x7fffffff:raise ValueError('ATTACK_DELAY_UINT16_CAPACITY')
  stall=max(1,150-aggression);indices=[]
  for value in (maximum,stall):
   valuebits=bits(value)
   if valuebits not in maxima:maxima.append(valuebits)
   indices.append(maxima.index(valuebits))
  rows.append(dict(index=m['index'],identity=m['identity'],aggression=aggression,attackthrottletime_bits=bits(maximum),next_table=indices[0],stall_table=indices[1],next_consumes_rng=maximum!=0))
 if not 1<=len(models)<=16 or len(authority['profiles'])<len(models):raise ValueError('ATTACK_DELAY_MODEL_CAPACITY')
 start=16+16*len(rows);size=start+20000*len(maxima)
 if size>32768:raise ValueError('ATTACK_DELAY_ROM_BANK_CAPACITY')
 raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd='E:/gh/openbor-bcec').decode('latin1');randf=extract(raw,'randf')
 code='''#include <stdio.h>
#include <string.h>
unsigned draw,calls;
unsigned int rand32(void){calls++;return draw;}
'''+randf+'''
float frombits(unsigned n){float f;memcpy(&f,&n,4);return f;}
unsigned maxima[]={'''+','.join(str(v)+'u'for v in maxima)+'''};
int main(void){unsigned i,n;FILE*out=fopen("delays.bin","wb");if(!out)return 1;for(i=0;i<sizeof(maxima)/sizeof(maxima[0]);i++){float maximum=frombits(maxima[i]);for(n=0;n<10000;n++){float value;unsigned delta;unsigned short packed;draw=n;calls=0;value=randf(maximum);delta=(unsigned)value;if(value<0||delta>65535||calls!=(maximum==0?0:1))return 2;packed=(unsigned short)delta;if(fwrite(&packed,2,1,out)!=1)return 3;}}return fclose(out)!=0;}
'''
 (a.output/'delay.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-ei','-bt=nt','delay.c','-fe=delay.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(build.stdout+build.stderr);assert build.returncode==0
 subprocess.run([str(a.output/'delay.exe')],cwd=a.output,check=True);delays=(a.output/'delays.bin').read_bytes();assert len(delays)==20000*len(maxima)
 data=bytearray(struct.pack('<4s6H',b'B4TD',1,len(rows),16,len(maxima),start,0))
 for r in rows:data.extend(struct.pack('<iI4H',r['aggression'],r['attackthrottletime_bits'],start+20000*r['next_table'],start+20000*r['stall_table'],int(r['next_consumes_rng']),0))
 data.extend(delays);assert len(data)==size;(a.output/'profile.b4td').write_bytes(data)
 report=dict(schema='BYOR_4086_ATTACK_DELAY_PROFILE_V1',status='PASS',engine_commit=ENGINE_COMMIT,models=rows,unique_maximum_bits=maxima,table_bytes=len(data),table_sha256=hashlib.sha256(data).hexdigest(),literal_randf_sha256=hashlib.sha256(randf.encode()).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),literal_randf_unmodified=True,residues_per_table=10000,native_bound=False,original_2014_binary_fpu_configuration_proven=False,motu_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS',len(rows),'models,',len(maxima),'unique tables,',len(data),'bytes')

if __name__=='__main__':main()
