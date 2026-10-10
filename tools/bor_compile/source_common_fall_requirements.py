"""Source-derived closed rise deadlines and explicit fall action requirements."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
from compiler import Source,key
from source_profile import document
from source_model_core_4086 import derive as core,integer
from source_hit_block_requirements import derive as attacks
from dialect_4086 import ENGINE_COMMIT

def derive(source):
 raw=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
 at=re.search(r'case CMD_MODEL_RISETIME\s*:',raw).start();loader=raw[at:raw.index('break;',at)+6]
 if 'newchar->risetime.riseattack = GET_INT_ARG(2);'not in loader:raise ValueError('COMMON_FALL_RISEATTACK_LOADER_AUTHORITY')
 outside=raw[:at]+raw[at+len(loader):]
 if re.search(r'newchar->risetime\.riseattack\s*=',outside):raise ValueError('COMMON_FALL_RISEATTACK_DEFAULT_OVERRIDE')
 if 's_model *newchar = calloc(1, sizeof(*newchar));'not in raw:raise ValueError('COMMON_FALL_MODEL_CALLOC_AUTHORITY')
 models=[]
 for m in core(source)['models']:
  rows=document(source,m['source_path'])['directives'];riseattack=0
  for r in rows:
   if r['directive']=='risetime':riseattack=integer(r['values'],1)
   if r['directive']=='subclass':raise ValueError('COMMON_FALL_SUBCLASS_REQUIRED')
  models.append(dict(id=m['id'],identity=m['identity'],source_sha256=m['source_sha256'],rise=m['fields']['risetime.rise'],riseattack=riseattack))
 authored=attacks(source)['attacks']
 if any(any(a['staydown'][:2])for a in authored):raise ValueError('COMMON_FALL_NONZERO_STAYDOWN_REQUIRED')
 if any(m['riseattack']!=0 or not -1<=m['rise']<=200 for m in models):raise ValueError('COMMON_FALL_OTHER_RISE_DEADLINE_BODY_REQUIRED')
 speedup=[line.strip()for line in raw.splitlines()if 'tospeedup' in line]
 if len(speedup)!=4 or not any('int' in line and 'tospeedup' in line and '= 0;'in line for line in speedup)or not any(line.startswith('tospeedup = 0;')for line in speedup)or not any(line=='tospeedup = 1;'for line in speedup):raise ValueError('COMMON_FALL_SPEEDUP_AUTHORITY_CHANGED')
 return dict(schema='BYOR_COMMON_FALL_CLOSED_REQUIREMENTS_V1',engine_commit=ENGINE_COMMIT,models=models,attacks=len(authored),source_staydown_zero=True,live_inherited_rise_values=sorted({m['rise']for m in models}),riseattack_zero=True,loader_sha256=hashlib.sha256(loader.encode('latin1')).hexdigest(),speedup_authority=speedup,speedup_source_values=[0,1],speedup_owner_bound=False,autoland_owner='SourceLandingVelocity4086_Autoland retained int32 source input',completed_owner='SourceScrollerPrefix4086_Completed retained int32 source input',doland_requires_actual_child=True,inair_policy='existing explicit ACCEPTED_COMPAT_Q16_16',model_policy_mutations_admitted=False,native_common_fall_bound=False,motu_gameplay_proven=False,no_color_reduction=True)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=derive(Source(a.source));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print('Derived',len(r['models']),'fall models;',r['attacks'],'zero-staydown attacks; rise values',r['live_inherited_rise_values'])

if __name__=='__main__':main()
