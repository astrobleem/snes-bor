"""Derive immutable source recovery policy; runtime mutations require owners."""
import argparse,hashlib,json,re,struct,subprocess
from pathlib import Path
from compiler import Source
from source_profile import document
from source_model_core_4086 import derive as models,integer,number,binary32
from dialect_4086 import ENGINE_COMMIT

def derive(source):
 raw=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
 header=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.h']).decode('latin1')
 assert 's_model *newchar = calloc(1, sizeof(*newchar));'in raw
 assert re.search(r'#define\s+GAME_SPEED\s+200\b',header)
 loaders={}
 for name in ('FALLDIE','NODIEBLINK','KOMAP','RISEINV','JUGGLEPOINTS'):
  at=raw.index('case CMD_MODEL_'+name+':');loaders[name]=raw[at:raw.index('break;',at)+6]
 assert 'newchar->riseinv = GET_FLOAT_ARG(1) * GAME_SPEED;'in loaders['RISEINV']
 assert 'newchar->riseinv = -newchar->riseinv;'in loaders['RISEINV']
 assert 'newchar->jugglepoints.current = newchar->jugglepoints.max = 0;'in raw
 result=[]
 for m in models(source)['models']:
  fields=dict(falldie=0,nodieblink=0,ko=0,kotype=0,riseinv=0,juggle_max=0);declarations=[]
  for r in document(source,m['source_path'])['directives']:
   name=r['directive'];v=r['values']
   if name=='subclass':raise ValueError('RECOVERY_SUBCLASS_REQUIRED')
   if name in ('falldie','death','nodieblink'):fields['falldie'if name=='death'else name]=integer(v)
   elif name=='komap':fields.update(ko=integer(v),kotype=integer(v,1))
   elif name=='riseinv':
    ticks=binary32(number(v)*200)
    if not -0x7fffffff<=ticks<=0x7fffffff:raise ValueError('RECOVERY_RISEINV_INT_ABS_DOMAIN')
    fields['riseinv']=int(ticks)*(-1 if integer(v,1)else 1)
   elif name=='jugglepoints':fields['juggle_max']=integer(v)
   else:continue
   declarations.append(r)
  result.append(dict(id=m['id'],identity=m['identity'],source_path=m['source_path'],source_sha256=m['source_sha256'],fields=fields,declarations=declarations))
 return dict(schema='BYOR_RECOVERY_SOURCE_REQUIREMENTS_V1',engine_commit=ENGINE_COMMIT,models=result,game_speed=200,loader_sha256={k:hashlib.sha256(v.encode('latin1')).hexdigest()for k,v in loaders.items()},riseinv_policy='binary32 seconds times 200, truncated to signed source int; optional flag negates tick value',
  immutable_source_model_policy=True,live_model_property_mutations_admitted=False,source_zero_death_policy=all(not any(m['fields'][k]for k in ('falldie','nodieblink','ko','kotype'))for m in result),source_zero_juggle_max=all(m['fields']['juggle_max']==0 for m in result),native_recovery_bound=False,motu_gameplay_proven=False,no_color_reduction=True)

def pack(report):
 fields=('falldie','nodieblink','ko','kotype','riseinv','juggle_max');rows=report['models']
 if not 0<len(rows)<=16:raise ValueError('RECOVERY_MODEL_COUNT')
 body=bytearray()
 for i,r in enumerate(rows):
  if r['id']!=i:raise ValueError('RECOVERY_MODEL_ORDER')
  body.extend(struct.pack('<HH6i',i,0,*(r['fields'][k]for k in fields)))
 return struct.pack('<4sHHHH12x',b'B4RC',1,28,len(rows),0)+body

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);r=derive(Source(a.source));b=pack(r);(a.output/'policy.bin').write_bytes(b);r['descriptor_sha256']=hashlib.sha256(b).hexdigest();(a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');print('Derived',len(r['models']),'recovery models; riseinv ticks',sorted({m['fields']['riseinv']for m in r['models']}))

if __name__=='__main__':main()
