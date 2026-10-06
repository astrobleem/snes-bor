"""Pinned level player spawn-height inputs, source integers to exact Q16."""
import argparse,json,struct
from pathlib import Path
from compiler import Source,key
from source_profile import document
from source_environment_4086 import derive as environment
from source_model_core_4086 import integer
from dialect_4086 import ENGINE_COMMIT

def load(rows):
 heights=[300]*4
 for r in rows:
  n=r['directive']
  if n in ('spawn1','spawn2','spawn3','spawn4'):
   y=integer(r['values'],2);heights[int(n[-1])-1]=300 if y<0 else y
 return heights

def derive(source):
 stages=[]
 for stage in environment(source)['stages']:
  doc=document(source,stage['source_path']);heights=load(doc['directives'])
  if any(not 0<=h<=32767 for h in heights):raise ValueError('PLAYER_SPAWN_HEIGHT_Q16_DOMAIN')
  stages.append(dict(stage_id=stage['stage_id'],source_path=stage['source_path'],source_sha256=doc['sha256'],heights=heights,descriptor_hex=struct.pack('<HH4i',0xb505,stage['stage_id'],*[h*65536 for h in heights]).hex()))
 return dict(schema='BYOR_4086_PLAYER_SPAWN_HEIGHTS_V1',engine_commit=ENGINE_COMMIT,authority='loadlevel default 300; CMD_LEVEL_SPAWN1..4 GET_INT_ARG(3), negative resets 300',stages=stages,numeric_policy='Source integer heights 0..32767 represented exactly as native Q16',native_world_installation_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=derive(Source(a.source));a.output.mkdir(parents=True,exist_ok=True);(a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n')
 for s in r['stages']:(a.output/('stage-'+str(s['stage_id'])+'.b505')).write_bytes(bytes.fromhex(s['descriptor_hex']))
 print([(s['stage_id'],s['heights'])for s in r['stages']])

if __name__=='__main__':main()
