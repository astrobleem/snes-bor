"""Source-derived immutable uniform attack factors for constructor copies.

B5UF stores one exact binary32 defense/offense vector per model when all
configured attack types match. Nonuniform models reject this capability.
This does not admit factor mutation APIs or bind native combat arithmetic.
"""
import argparse,hashlib,json,math,struct,zlib
from pathlib import Path
from compiler import Source,key
from source_profile import document,discover
from source_model_core_4086 import binary32,integer
from source_lifecycle_inputs import load as life
from dialect_4086 import ENGINE_COMMIT
ATTACKS=('normal','normal2','normal3','normal4','blast','burn','freeze','shock','steal','normal5','normal6','normal7','normal8','normal9','normal10','item','land','pit','lifespan','timeover')
DEFAULT=[1.0,0.0,1.0,0.0,0.0,0.0,1]
HEADER=24
STRIDE=36

def vector_bytes(defense,offense):return struct.pack('<6fif',*defense,offense)

def derive(source):
 docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')};structure=discover(source,docs);globals=docs[key(structure['models_path'])]['directives'];count=20
 for r in globals:
  if r['directive']=='maxattacktypes':count=max(20,integer(r['values'])+10)
 if not 20<=count<=255:raise ValueError('UNIFORM_FACTORS_ATTACK_CAPACITY')
 models=[]
 for i,m in enumerate(structure['models']):
  doc=docs[key(m['source_path'])];rows=doc['directives'];defense=[list(DEFAULT)for _ in range(count)];offense=[1.0]*count;subtype=0
  for r in rows:
   n,v=r['directive'],r['values']
   if n=='anim':break
   if n=='subtype':subtype=life([r])['subtype']
   if n in('defense','offense'):raise ValueError('UNIFORM_FACTORS_EXPLICIT_LOADER_REQUIRED:'+m['declaration']+':'+n)
  # finish_model normalizes biker defense factors after parsing declarations.
  if subtype==1:
   for d in defense:d[0]=2.0
  values=[vector_bytes(d,o)for d,o in zip(defense,offense)];uniform=all(v==values[0]for v in values)
  if not uniform:raise ValueError('UNIFORM_FACTORS_NONUNIFORM_MODEL:'+m['declaration'])
  models.append(dict(id=i,identity=m['declaration'],source_sha256=doc['sha256'],subtype=subtype,defense=defense[0],offense=offense[0],vector_hex=values[0].hex()))
 if not 1<=len(models)<=16:raise ValueError('UNIFORM_FACTORS_MODEL_CAPACITY')
 return dict(schema='BYOR_4086_UNIFORM_MODEL_FACTORS_V1',engine_commit=ENGINE_COMMIT,capability='UNIFORM_IMMUTABLE_ATTACK_FACTORS',attack_types=count,attack_identity=list(ATTACKS),models=models,source_authority='default_defense, init_model factor loop, biker finish normalization; explicit defense/offense declarations reject until their loader is certified; spawn memcpy copies independent defense/offense arrays',representation='One independent 32-byte vector per entity; all admitted attack indices read the same exact binary32 values. Mutable per-attack APIs require another capability and explicitly fail.',proposed_entity_bytes=128*32,proposed_model_bytes=16*32,mutation_api_admitted=False,native_factor_copy_bound=False,native_combat_bound=False,full_constructor_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)

def pack(report):
 body=bytearray()
 for i,m in enumerate(report['models']):
  if m['id']!=i:raise ValueError('UNIFORM_FACTORS_MODEL_ID')
  vector=bytes.fromhex(m['vector_hex'])
  if len(vector)!=32:raise ValueError('UNIFORM_FACTORS_VECTOR_ABI')
  body.extend(struct.pack('<HH',i,0)+vector)
 return struct.pack('<4sHHHHIII',b'B5UF',1,STRIDE,len(report['models']),report['attack_types'],len(body),zlib.crc32(body)&0xffffffff,0)+body

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=derive(Source(a.source));b=pack(r);a.output.mkdir(parents=True,exist_ok=True);(a.output/'factors.b5uf').write_bytes(b);r.update(bytes=len(b),sha256=hashlib.sha256(b).hexdigest());(a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(len(r['models']),'models',r['attack_types'],'attack types, uniform exact factors; native copy unbound')
if __name__=='__main__':main()
