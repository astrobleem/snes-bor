"""Source model data for constructor scalar/body and default palette setup.

B5CI records source lifespan, summonkill, alpha and the cached display name.
This table supplies no admission shortcut for constructor services or rendering.
"""
import argparse,hashlib,json,math,struct,zlib
from pathlib import Path
from compiler import Source,key
from source_profile import document,discover
from source_model_core_4086 import integer
from source_integer_ticks_4086 import ticks
from dialect_4086 import ENGINE_COMMIT
HEADER=24
STRIDE=64

def derive(source):
 docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')};structure=discover(source,docs);models=[]
 for i,m in enumerate(structure['models']):
  doc=docs[key(m['source_path'])];rows=doc['directives'];name=m['declaration']
  # cache_model -> _peek_model_name chooses the first source NAME declaration.
  for r in rows:
   if r['directive']=='name':
    if len(r['values'])!=1:raise ValueError('CTOR_STATE_NAME_ARITY')
    name=r['values'][0];break
  if name.casefold()!=m['declaration'].casefold():raise ValueError('CTOR_STATE_REGISTRY_NAME_PAIR:'+m['declaration'])
  encoded=name.encode('ascii')
  if not 1<=len(encoded)<=47 or b'\0'in encoded:raise ValueError('CTOR_STATE_DISPLAY_NAME_CAPACITY')
  lifespan=0x7fffffff;summonkill=1;alpha=0
  for r in rows:
   n,v=r['directive'],r['values']
   if n=='anim':break
   if n=='name'and name.casefold()=='steam':alpha=1 # Pinned lcmHandleCommandName rule.
   elif n=='lifespan':
    if len(v)!=1:raise ValueError('CTOR_STATE_LIFESPAN_ARITY')
    lifespan=ticks(v[0])
   elif n=='summonkill':summonkill=integer(v)
   elif n=='alpha':alpha=integer(v)
  if not 0<=alpha<=6:raise ValueError('CTOR_STATE_ALPHA_CAPABILITY_REQUIRED')
  models.append(dict(id=i,identity=m['declaration'],display_name=name,source_sha256=doc['sha256'],lifespan=lifespan,summonkill=summonkill,alpha=alpha,initial_map=0,default_palette_owner=i))
 if not 1<=len(models)<=16:raise ValueError('CTOR_STATE_MODEL_CAPACITY')
 return dict(schema='BYOR_4086_CONSTRUCTOR_STATE_INPUTS_V1',engine_commit=ENGINE_COMMIT,models=models,authority='init_model defaults; _peek_model_name/lcmHandleCommandName; CMD_MODEL_LIFESPAN/SUMMONKILL/ALPHA; spawn; ent_set_colourmap(ent,0)',numeric_policy='lifespan GET_FLOAT_ARG times GAME_SPEED direct signed-int assignment without an intermediate float store, per pinned C authority; entity positions handled separately as ACCEPTED_COMPAT Q16.16',initial_palette_policy='map=0 uses modeldata.palette, not colourmap[0]; no opaque rendering adaptation implied',native_body_reset_bound=False,source_palette_installation_bound=False,full_constructor_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)

def pack(report):
 body=bytearray()
 for i,m in enumerate(report['models']):
  if m['id']!=i:raise ValueError('CTOR_STATE_MODEL_ID')
  name=m['display_name'].encode('ascii');body.extend(struct.pack('<HHiiHH',i,0,m['lifespan'],m['summonkill'],m['alpha'],len(name))+name+bytes(48-len(name)))
 return struct.pack('<4sHHHHIII',b'B5CI',1,STRIDE,len(report['models']),0,len(body),zlib.crc32(body)&0xffffffff,0)+body

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=derive(Source(a.source));b=pack(r);a.output.mkdir(parents=True,exist_ok=True);(a.output/'state.b5ci').write_bytes(b);r.update(bytes=len(b),sha256=hashlib.sha256(b).hexdigest());(a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(len(r['models']),'source constructor state records; body reset/palette installation unbound')
if __name__=='__main__':main()
