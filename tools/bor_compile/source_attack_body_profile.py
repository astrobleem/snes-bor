"""Source model turn/chain fields used by normal_prepare and attack chains."""
import argparse,hashlib,json,re,struct,subprocess
from pathlib import Path
from compiler import Source,key
from source_profile import document,discover
from source_animation_ids import configure
from source_model_core_4086 import integer
from dialect_4086 import ENGINE_COMMIT

def chain_capacity():
 header=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.h'],cwd='E:/gh/openbor-bcec').decode('latin1')
 return int(re.search(r'^#define\s+MAX_ATCHAIN\s+(\d+)',header,re.M)[1])

def load(rows,maximum,capacity):
 d=dict(noflip=0,chainlength=1,atchain=[1]*capacity)
 for r in rows:
  n,v=r['directive'],r['values']
  if n=='nomove':d['noflip']=integer(v,1)
  elif n=='atchain':
   d['atchain']=[min(maximum,max(0,integer(v,i)))for i in range(capacity)];d['chainlength']=max((i+1 for i,x in enumerate(d['atchain'])if x),default=0)
 return d

def derive(source):
 docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')};found=discover(source,docs);config=configure(docs[key('data/models.txt')]['directives']);maximum=len(config['arrays']['normal_attacks']);capacity=chain_capacity();models=[]
 if found['diagnostics']:raise ValueError('ATTACK_BODY_SOURCE_DIAGNOSTICS')
 for i,m in enumerate(found['models']):
  doc=docs[key(m['source_path'])]
  if any(r['directive']=='subclass'for r in doc['directives']):raise ValueError('ATTACK_BODY_SUBCLASS_UNBOUND')
  models.append(dict(index=i,identity=m['declaration'],source_path=m['source_path'],source_sha256=doc['sha256'],fields=load(doc['directives'],maximum,capacity)))
 return dict(schema='BYOR_4086_ATTACK_BODY_PROFILE_V1',engine_commit=ENGINE_COMMIT,maximum_attacks=maximum,chain_capacity=capacity,normal_prepare_weights=[max(5-i,0)+1 for i in range(maximum)],models=models,runtime_bound=False,motu_gameplay_proven=False)

def pack(r):
 count=len(r['models']);capacity=r['chain_capacity'];stride=8+4*capacity
 if not 1<=count<=16 or capacity!=12:raise ValueError('ATTACK_BODY_PROFILE_CAPACITY')
 data=bytearray(struct.pack('<4s6H',b'B4BP',1,count,stride,capacity,r['maximum_attacks'],0))
 for m in r['models']:
  f=m['fields'];data.extend(struct.pack('<'+'i'*(2+capacity),f['noflip'],f['chainlength'],*f['atchain']))
 return bytes(data)

def pack_runtime(r):
 # Twelve chain entries need 36 bits; chainlength occupies the last nibble.
 # Values retain exact source integer identity in the admitted 0..7 domain.
 if not 1<=len(r['models'])<=16 or r['chain_capacity']!=12 or not 1<=r['maximum_attacks']<=7:raise ValueError('ATTACK_BODY_PACKED_DOMAIN')
 data=bytearray(struct.pack('<4s6H',b'B4BC',1,len(r['models']),9,12,r['maximum_attacks'],0))
 for m in r['models']:
  f=m['fields'];chain=f['atchain'];length=f['chainlength']
  if len(chain)!=12 or not 0<=length<=12 or any(not 0<=n<=r['maximum_attacks']for n in chain):raise ValueError('ATTACK_BODY_PACKED_CHAIN_DOMAIN')
  value=sum(n<<(3*i)for i,n in enumerate(chain))|(length<<36)
  data.extend(struct.pack('<i',f['noflip'])+value.to_bytes(5,'little'))
 return bytes(data)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=derive(Source(a.source));data=pack(r);runtime=pack_runtime(r);r.update(table_bytes=len(data),table_sha256=hashlib.sha256(data).hexdigest(),runtime_table_bytes=len(runtime),runtime_table_sha256=hashlib.sha256(runtime).hexdigest());a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');a.output.with_suffix('.b4bp').write_bytes(data);a.output.with_suffix('.b4bc').write_bytes(runtime);print('Derived',len(r['models']),'turn/chain rows;',len(data),'bytes')

if __name__=='__main__':main()
