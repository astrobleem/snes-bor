"""Closed Script_Clear/Script_Copy method-1 constructor binding.

Only animation script instances without init/clear entries are admitted. Shared
program identities are paired with B4CO; no interpreter address is fabricated.
"""
import argparse,hashlib,json,struct,zlib
from pathlib import Path
from compiler import Source,key
from source_profile import document,discover
from script_ir_4086 import parse_script
from script_callback_owner import derive as callback_owners,pack as pack_callbacks
from dialect_4086 import ENGINE_COMMIT
HEADER=24
STRIDE=8

def derive(source):
 docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')};structure=discover(source,docs);callbacks,*_=callback_owners(source);data=pack_callbacks(callbacks);rows=[]
 for i,m in enumerate(structure['models']):
  d=docs[key(m['source_path'])];scripts=[];mask=0
  for r in d['directives']:
   if r['directive']=='anim':break
   if r['directive'].endswith('script'):
    if r['directive']!='animationscript':raise ValueError('SOURCE_SCRIPT_CLONE_KIND_UNBOUND:'+r['directive'])
    if len(r['values'])!=1:raise ValueError('SOURCE_SCRIPT_CLONE_ARITY')
    path=r['values'][0];raw=source.read(path);ir=parse_script(raw.decode('latin1'),path)
    if 'init'in ir['functions']:raise ValueError('SOURCE_SCRIPT_CLONE_INIT_ENTRY_REQUIRED:'+path)
    if 'clear'in ir['functions']:raise ValueError('SOURCE_SCRIPT_CLONE_CLEAR_ENTRY_REQUIRED:'+path)
    scripts.append(dict(kind=r['directive'],path=path,sha256=hashlib.sha256(raw).hexdigest(),functions=list(ir['functions'])));mask=1
  # Inline animation blocks also construct an initialized animation script.
  program=callbacks['models'][i]['program']
  if m['inline_scripts']:mask=1
  if bool(mask)!=(program!=0xffff):raise ValueError('SOURCE_SCRIPT_CLONE_CALLBACK_PAIR:'+m['declaration'])
  rows.append(dict(id=i,identity=m['declaration'],source_sha256=d['sha256'],scripts=scripts,initialized_mask=mask,inline_blocks=len(m['inline_scripts']),callback_program=program))
 if not 1<=len(rows)<=16:raise ValueError('SOURCE_SCRIPT_CLONE_MODEL_CAPACITY')
 return dict(schema='BYOR_4086_SCRIPT_CLONE_NO_ENTRIES_V1',engine_commit=ENGINE_COMMIT,models=rows,callback_table_sha256=hashlib.sha256(data).hexdigest(),callback_table_crc32=zlib.crc32(data)&0xffffffff,policy='constructor clears entity-owned named values while retaining names; then clones admitted shared animation program with initialized bit and interpreterowner=0; no init/clear entry exists',relation_initialized_offset=44,animation_variable_scope=1,script_instance_pointer_policy='stable entity token plus scope, shared immutable B4CO program identity',indexed_variable_api_admitted=False,native_constructor_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)

def pack(report):
 body=bytearray()
 for i,m in enumerate(report['models']):
  if m['id']!=i or m['initialized_mask']not in(0,1):raise ValueError('SOURCE_SCRIPT_CLONE_ROW')
  body.extend(struct.pack('<4H',i,m['initialized_mask'],m['callback_program'],0))
 return struct.pack('<4sHHHHIII',b'B5SC',1,STRIDE,len(report['models']),0,len(body),zlib.crc32(body)&0xffffffff,report['callback_table_crc32'])+body

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=derive(Source(a.source));data=pack(r);a.output.mkdir(parents=True,exist_ok=True);(a.output/'scripts.b5sc').write_bytes(data);r.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest());(a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(len(r['models']),'source script-clone descriptors',len(data),'bytes; constructor not yet bound')

if __name__=='__main__':main()
