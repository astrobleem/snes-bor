"""Pack literal-C cutoffs for a closed immutable source coefficient profile."""
import argparse,hashlib,json,struct
from pathlib import Path
from compiler import Source
from source_attack_timing_4086 import derive,bits
from dialect_4086 import ENGINE_COMMIT

def pack(source,authority):
 profile=derive(source);models=profile['models'];compiled=authority['source_models']
 if authority['status']!='PASS' or authority['engine_commit']!=ENGINE_COMMIT or not authority['normal_equal_bound_call_verified']or not authority['literal_functions_unmodified']or authority['globals']!=profile['globals']or len(compiled)!=len(models):raise ValueError('NORMAL_CHANCE_PROFILE_AUTHORITY')
 data=bytearray(struct.pack('<4s6H2I',b'B4NC',2,len(models),8,*authority['source_viewport'],0,bits(profile['globals']['min_noatk_chance']),bits(profile['globals']['offscreen_noatk_factor'])))
 for i,(m,c)in enumerate(zip(models,compiled)):
  if c['index']!=i or c['identity']!=m['identity']:raise ValueError('NORMAL_CHANCE_PROFILE_MODEL_IDENTITY')
  rows=authority['inputs'][i*5:(i+1)*5];results=authority['actual'][i*5:(i+1)*5]
  if len(rows)!=5 or any(r['model']!=i or r['minimum']!=profile['globals']['min_noatk_chance']or r['throttle']!=m['fields']['attackthrottle']or r['offscreen_factor']!=profile['globals']['offscreen_noatk_factor']or r['aiattack']!=0 for r in rows):raise ValueError('NORMAL_CHANCE_PROFILE_COEFFICIENT_IDENTITY')
  if [r['x']for r in rows]!=[-11,-10,0,330,331]or authority['source_viewport']!=[320,240]:raise ValueError('NORMAL_CHANCE_PROFILE_VIEWPORT_AUTHORITY_UNBOUND')
  onscreen,offscreen=c['onscreen_last_allowed'],c['offscreen_last_allowed']
  if [r[0]for r in results]!=[offscreen,onscreen,onscreen,onscreen,offscreen]or not all(r[1:]==[10000,1]for r in results)or not all(-1<=v<=9999 for v in (onscreen,offscreen)):raise ValueError('NORMAL_CHANCE_PROFILE_CUTOFF_IDENTITY')
  data.extend(struct.pack('<hhI',onscreen,offscreen,bits(m['fields']['attackthrottle'])))
 return bytes(data)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();authority=json.loads(a.authority.read_text());data=pack(Source(a.source),authority);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(data);print('Compiled',len(authority['source_models']),'C-derived model cutoffs;',len(data),'bytes')

if __name__=='__main__':main()
