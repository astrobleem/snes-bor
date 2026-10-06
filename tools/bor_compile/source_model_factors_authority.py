"""Pinned default factor initialization and spawn copies, exact 32-bit ABI."""
import argparse,hashlib,json,os,re,struct,subprocess
from pathlib import Path
from compiler import Source
from dialect_4086 import ENGINE_COMMIT
from source_model_factors import derive

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);r=derive(Source(a.source))
 raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=a.engine).decode('latin1');header=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.h'],cwd=a.engine).decode('latin1')
 # Preserve actual initializer tokens and loop bodies; only translate C99
 # field designators for Watcom's C89 parser, retaining declaration order.
 start=raw.index('const s_defense default_defense =');end=raw.index('};',start)+2;default=raw[start:end]
 start=raw.index('    //Default offense/defense values.');end=raw.index('    //Default sight ranges.',start);loop=raw[start:end]
 start=raw.index('        for(i = 0; i < max_attack_types; i++)',raw.index('if(!newchar->offscreenkill)'));end=raw.index('        newchar->subject_to_hole',start);biker=raw[start:end]
 copies=re.findall(r'            memcpy\((?:dfs|ofs),[^;]+;',raw)
 if len(copies)!=2:raise ValueError('FACTORS_SPAWN_COPY_AUTHORITY')
 end=header.index('} s_defense;')+len('} s_defense;');start=header.rfind('typedef struct',0,end);typedef=header[start:end]
 fragments=dict(default=default,initialize=loop,biker=biker,spawn_copies='\n'.join(copies),defense_type=typedef)
 text='#include <stdio.h>\n#include <string.h>\n#define BLOCK_TYPE_MP_FIRST 1\n#define SUBTYPE_BIKER 1\ntypedef int e_blocktype;\n'+typedef+'\n'+re.sub(r'\.\w+\s*=\s*','',default)+'\n'
 text+='typedef struct {s_defense *defense;float *offense_factors;int subtype;} Model;\n'
 text+='int main(void){s_defense md[255],ed[255];float mo[255],eo[255];Model m,e0,*newchar=&m,*model=&m,*e=&e0;s_defense *dfs=ed;float *ofs=eo;int max_attack_types,i,j,k;unsigned *bits;\n'
 text+='if(sizeof(s_defense)!=28||sizeof(float)!=4||sizeof(int)!=4||sizeof(void*)!=4)return 2;\n'
 text+='for(k=0;k<3;k++){max_attack_types=k==2?23:20;newchar->defense=md;newchar->offense_factors=mo;newchar->subtype=k==1?SUBTYPE_BIKER:0;e->defense=ed;e->offense_factors=eo;memset(ed,165,sizeof(ed));memset(eo,165,sizeof(eo));\n'+loop+'\nif(newchar->subtype==SUBTYPE_BIKER){\n'+biker+'}\n'+'\n'.join(copies)+'\n'
 text+='md[0].factor=99;mo[0]=88;for(i=0;i<max_attack_types;i++){printf("FACTORS|%d|%d",k,i);bits=(unsigned*)(ed+i);for(j=0;j<7;j++)printf("|%08x",bits[j]);bits=(unsigned*)(eo+i);printf("|%08x\\n",bits[0]);}}return 0;}\n'
 (a.output/'factors.c').write_text(text);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');proc=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','factors.c','-fe=factors.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(proc.stdout+proc.stderr)
 if proc.returncode:raise ValueError('FACTOR_AUTHORITY_C_BUILD')
 log=subprocess.check_output([str(a.output/'factors.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);results=[]
 for line in log.splitlines():
  if not line.startswith('FACTORS|'):continue
  values=line.split('|');k,i=map(int,values[1:3]);actual=b''.join(struct.pack('<I',int(x,16))for x in values[3:]);want=struct.pack('<6fif',2.0 if k==1 else 1.0,0,1,0,0,0,1,1);results.append(dict(case=k,attack=i,actual_hex=actual.hex(),expected_hex=want.hex(),pass_case=actual==want))
 ok=len(results)==63 and all(x['pass_case']for x in results)and all(m['vector_hex']==results[0]['actual_hex']for m in r['models'])
 result=dict(schema='BYOR_4086_UNIFORM_FACTOR_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,fragments={k:dict(sha256=hashlib.sha256(v.encode()).hexdigest(),text=v)for k,v in fragments.items()},initializer_syntax_translation='C99 designated fields to positional initialization in the same pinned struct field order',cases=len(results),results=results,source_models=r['models'],sizeof_defense=28,sizeof_offense=4,copied_entity_independent_of_later_model_mutation=True,explicit_defense_offense_loader_branches_executed=False,native_factor_copy_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],len(results),'pinned factor copies')
 if not ok:raise SystemExit(1)
if __name__=='__main__':main()
