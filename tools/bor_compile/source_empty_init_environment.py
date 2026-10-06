"""Source-derived closed registry with no authored platform declarations.

The world owner may grant B504 only while every installed animation comes
from this registry and no platform mutation capability is admitted. Pair it
with the checked stage's B4D1 empty-wall lease; invalidate both before changes.
"""
import argparse,hashlib,json,struct
from pathlib import Path
from compiler import Source,key
from source_profile import document,discover
from source_environment_4086 import derive as walls
from dialect_4086 import ENGINE_COMMIT

def derive(source):
 docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')};structure=discover(source,docs);models=[]
 for i,m in enumerate(structure['models']):
  d=docs[key(m['source_path'])];platforms=[r for r in d['directives']if r['directive']=='platform'];models.append(dict(id=i,identity=m['declaration'],source_path=m['source_path'],source_sha256=d['sha256'],platform_declarations=platforms))
 if not 1<=len(models)<=16:raise ValueError('EMPTY_INIT_MODEL_CAPACITY')
 admitted=all(not m['platform_declarations']for m in models)
 return dict(schema='BYOR_4086_EMPTY_INIT_ENVIRONMENT_V1',engine_commit=ENGINE_COMMIT,models=models,platform_query_admitted=admitted,diagnostics=[]if admitted else['AUTHORED_PLATFORM_QUERY_REQUIRED'],stages=walls(source)['stages'],lease='B504 paired with current B4D1 empty-wall stage',owner_requirements=['closed compiler registry covers every installed/cached animation','no platform mutation capability installed','invalidate before model registry or stage geometry changes'],native_world_owner_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)

def descriptor(report,stage_id):
 if not report['platform_query_admitted']or report['diagnostics']:raise ValueError('EMPTY_PLATFORM_CAPABILITY_UNPROVEN')
 stage=next((s for s in report['stages']if s['stage_id']==stage_id),None)
 if stage is None or not stage['admitted']or stage['wall_count']:raise ValueError('EMPTY_WALL_CAPABILITY_UNPROVEN')
 return struct.pack('<4H',0xb504,len(report['models']),stage_id,0)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=derive(Source(a.source));a.output.mkdir(parents=True,exist_ok=True);(a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n')
 for s in r['stages']:
  if r['platform_query_admitted']and s['admitted']:(a.output/('stage-'+str(s['stage_id'])+'.b504')).write_bytes(descriptor(r,s['stage_id']))
 print(len(r['models']),'models, no-platform',r['platform_query_admitted'],len(r['stages']),'stages')

if __name__=='__main__':main()
