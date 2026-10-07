"""Source animation energy-cost triples keyed by mutable frame handles."""
import argparse,hashlib,json,struct
from pathlib import Path
from compiler import Source,key
from source_profile import document,discover
from script_dispatch_4086 import compile_source
from source_model_core_4086 import integer
from dialect_4086 import ENGINE_COMMIT

FIELDS=('cost','mponly','disable')

def load(rows):
 result=[];current=None
 for row in rows:
  name,v=row['directive'],row['values']
  if name=='anim':
   current=dict(role=' '.join(v),fields=dict(cost=0,mponly=0,disable=0),numframes=0);result.append(current)
   if current['role'].lower() in ('special','special1'):current['fields']['cost']=6
  elif name=='frame' and current is not None:current['numframes']+=1
  elif name in ('energycost','mpcost','mponly'):
   if current is None:raise ValueError('ANIMATION_ENERGY_WITHOUT_ANIMATION')
   if name=='mponly':current['fields']['mponly']=integer(v)
   else:current['fields']=dict(zip(FIELDS,(integer(v,i)for i in range(3))))
 return result

def derive(source):
 docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')};discovery=discover(source,docs)
 handles={(h['model'],h['role']):h['handle']for h in compile_source(source)['animation_handles']};animations=[]
 for model in discovery['models']:
  doc=docs[key(model['source_path'])]
  for an in load(doc['directives']):
   an.update(model=model['declaration'],handle=handles[model['declaration'],an['role']],source_path=doc['source_path'],source_sha256=doc['sha256']);animations.append(an)
 return dict(schema='BYOR_4086_ANIMATION_ENERGY_IR_V1',engine_authority=ENGINE_COMMIT,fields=list(FIELDS),animations=animations,runtime_bound=False,motu_gameplay_proven=False)

def pack(report):
 animations=sorted(report['animations'],key=lambda a:a['handle'])
 if not 1<=len(animations)<=2047:raise ValueError('ANIMATION_ENERGY_TABLE_CAPACITY')
 data=bytearray(struct.pack('<4s6H',b'B4AE',1,len(animations),16,0,0,0))
 for i,an in enumerate(animations,1):
  if an['handle']!=i:raise ValueError('ANIMATION_ENERGY_HANDLE_ORDER')
  if an['numframes']==0:raise ValueError('ANIMATION_ENERGY_EMPTY_FRAMES_UNBOUND')
  data.extend(struct.pack('<4i',*(an['fields'][f]for f in FIELDS),0))
 return bytes(data)

def check(which,fields,entity_type,seal,mp,health,present=True):
 if not present:return False
 cost,only,disable=(fields[f]for f in FIELDS)
 if disable==entity_type or disable==-1 or disable==-2 and entity_type&514 or disable==-3 and entity_type&513 or disable==-4 and entity_type&3:return False
 if seal and seal<cost:return False
 return bool(which==1 and only!=2 and mp>=cost or which==0 and only!=1 and health>cost)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 report=derive(Source(a.source));data=pack(report);report.update(table_bytes=len(data),table_sha256=hashlib.sha256(data).hexdigest());a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');a.output.with_suffix('.b4ae').write_bytes(data);print('Derived',len(report['animations']),'energy triples;',len(data),'bytes')

if __name__=='__main__':main()
