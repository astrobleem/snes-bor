"""Source normal-attack probability/timing inputs, retaining binary32 identity.

This table is compiler data only. It does not admit the attack action body.
"""
import argparse, hashlib, json, math, struct
from pathlib import Path
from compiler import Source, key
from source_profile import document, discover
from source_model_core_4086 import integer, binary32
from dialect_4086 import ENGINE_COMMIT

FIELDS=('aggression','attackthrottle','attackthrottletime')

def bits(value):return struct.unpack('<I',struct.pack('<f',value))[0]

def scalar(values,index=0):
 value=binary32(values[index]if index<len(values)else 0)
 if not math.isfinite(value):raise ValueError('ATTACK_TIMING_NONFINITE_SOURCE')
 return value

def load(rows,duration=.75):
 d=dict(aggression=0,attackthrottle=0.0,attackthrottletime=binary32(duration*200))
 for r in rows:
  name,v=r['directive'],r['values']
  if name=='aggression':d[name]=integer(v)
  elif name=='attackthrottle':
   d[name]=scalar(v)
   # Literal loader uses count >= 2, including the directive itself.
   # Thus a one-value declaration ALSO writes GET_FLOAT_ARG(2), or zero.
   if len(v)>=1:d['attackthrottletime']=binary32(scalar(v,1)*200)
 if not math.isfinite(d['attackthrottletime']):raise ValueError('ATTACK_TIMING_NONFINITE_SOURCE')
 return d

def derive(source):
 docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')}
 globals=dict(min_noatk_chance=0.0,offscreen_noatk_factor=.5,noatk_duration=.75)
 for r in docs[key('data/models.txt')]['directives']:
  if r['directive']=='noatk_duration':raise ValueError('ATTACK_TIMING_GLOBAL_LOAD_ORDER_UNBOUND')
  if r['directive']in globals:globals[r['directive']]=scalar(r['values'])
 models=[]
 discovery=discover(source,docs)
 if discovery['diagnostics']:raise ValueError('ATTACK_TIMING_SOURCE_DIAGNOSTICS')
 for i,m in enumerate(discovery['models']):
  doc=docs[key(m['source_path'])]
  if any(r['directive']=='subclass'for r in doc['directives']):raise ValueError('ATTACK_TIMING_SUBCLASS_UNBOUND')
  models.append(dict(index=i,identity=m['declaration'],source_path=m['source_path'],source_sha256=doc['sha256'],fields=load(doc['directives'],globals['noatk_duration'])))
 return dict(schema='BYOR_4086_ATTACK_TIMING_V1',engine_authority=ENGINE_COMMIT,globals=globals,models=models,runtime_bound=False,motu_gameplay_proven=False)

def pack(r):
 models=r['models']
 if not 1<=len(models)<=16:raise ValueError('ATTACK_TIMING_MODEL_CAPACITY')
 data=bytearray(struct.pack('<4s6H3I',b'B4AT',1,len(models),12,0,0,0,*(bits(r['globals'][k])for k in ('min_noatk_chance','offscreen_noatk_factor','noatk_duration'))))
 for i,m in enumerate(models):
  if m['index']!=i:raise ValueError('ATTACK_TIMING_MODEL_ORDER')
  f=m['fields'];data.extend(struct.pack('<iII',f['aggression'],bits(f['attackthrottle']),bits(f['attackthrottletime'])))
 return bytes(data)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=derive(Source(a.source));data=pack(r);r.update(table_bytes=len(data),table_sha256=hashlib.sha256(data).hexdigest());a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');a.output.with_suffix('.b4at').write_bytes(data);print('Derived',len(r['models']),'source attack timing rows')

if __name__=='__main__':main()
