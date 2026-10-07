"""Source cached-model attack/stealth policy, separate from inherited core rows."""
import argparse, hashlib, json, struct
from pathlib import Path
from compiler import Source,key
from source_profile import document,discover
from source_model_core_4086 import integer,TYPE_NAMES
from dialect_4086 import ENGINE_COMMIT

FIELDS=('nopassiveblock','blockodds','stealth.detect','stealth.hide')
STRIDE=16
CACHE_BASE=0x40bc00
CAPACITY=16
FIRST_UNUSED=CACHE_BASE+CAPACITY*STRIDE

def load(rows):
 d=dict.fromkeys(FIELDS,0)
 for row in rows:
  n,v=row['directive'],row['values']
  if n=='type':
   if len(v)!=1 or v[0].lower()not in TYPE_NAMES:raise ValueError('MODEL_ATTACK_POLICY_TYPE_UNSUPPORTED')
   if v[0].lower()=='player':d['nopassiveblock']=1
  elif n in ('nopassiveblock','blockodds'):d[n]=integer(v)
  elif n=='stealth':d['stealth.hide']=integer(v);d['stealth.detect']=integer(v,1)
 return d

def derive(source):
 docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')};discovery=discover(source,docs)
 models=[]
 for i,m in enumerate(discovery['models']):
  doc=docs[key(m['source_path'])];models.append(dict(index=i,identity=m['declaration'],source_path=m['source_path'],source_sha256=doc['sha256'],fields=load(doc['directives'])))
 return dict(schema='BYOR_4086_MODEL_ATTACK_POLICY_V1',engine_authority=ENGINE_COMMIT,fields=list(FIELDS),models=models,model_switch_policy='shallow copy these fields; no fallback/inheritance for this subset',runtime_bound=False,motu_gameplay_proven=False)

def pack(report):
 models=report['models']
 if not 1<=len(models)<=CAPACITY:raise ValueError('MODEL_ATTACK_POLICY_CAPACITY')
 result=bytearray(struct.pack('<4s6H',b'B4AP',1,len(models),STRIDE,0,0,0))
 for i,m in enumerate(models):
  if m['index']!=i:raise ValueError('MODEL_ATTACK_POLICY_ORDER')
  result.extend(struct.pack('<4i',*(m['fields'][k]for k in FIELDS)))
 return bytes(result)

def unpack(data):
 if len(data)<16:raise ValueError('MODEL_ATTACK_POLICY_HEADER')
 magic,version,count,stride,a,b,c=struct.unpack_from('<4s6H',data)
 if magic!=b'B4AP'or version!=1 or not 1<=count<=CAPACITY or stride!=STRIDE or a or b or c or len(data)!=16+count*STRIDE:raise ValueError('MODEL_ATTACK_POLICY_HEADER')
 return [dict(zip(FIELDS,struct.unpack_from('<4i',data,16+i*STRIDE)))for i in range(count)]

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True)
 report=derive(Source(a.source));data=pack(report);assert unpack(data)==[m['fields']for m in report['models']]
 report.update(table_bytes=len(data),table_sha256=hashlib.sha256(data).hexdigest());a.output.write_text(json.dumps(report,indent=2)+'\n');a.output.with_suffix('.b4ap').write_bytes(data);print('Derived',len(report['models']),'model attack policy rows',len(data),'bytes')
if __name__=='__main__':main()
