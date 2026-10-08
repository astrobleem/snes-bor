"""Source-derived model score and explicit per-actor death-field extension.

Copied diesound comes from the current mutable cached model, after source
cached fallback, rather than an immutable actor-name lookup. The table stores
only score, whose calloc default is zero and CMD_MODEL_SCORE assigns arg1.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from compiler import Source,key
from dialect_4086 import ENGINE_COMMIT
from source_profile import document,discover
from source_model_core_4086 import integer

HEADER=24
STRIDE=8
MAGIC=0xB638


def loader_score(rows):
 score=0;declaration=None
 for row in rows:
  if row['directive']=='score':score=integer(row['values']);declaration=row['line']
 return score,declaration


def derive(source):
 docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')}
 structure=discover(source,docs);models=[]
 for i,model in enumerate(structure['models']):
  doc=docs[key(model['source_path'])];score,declaration=loader_score(doc['directives'])
  models.append(dict(id=i,identity=model['declaration'],source_path=model['source_path'],source_sha256=doc['sha256'],score=score,score_source_line=declaration))
 return dict(schema='BYOR_SOURCE_DEATH_FIELDS_4086_V1',engine_commit=ENGINE_COMMIT,models=models,
  view_extension=dict(score_offset=72,diesound_offset=76),relation_extension=dict(model_offset=56,marker_offset=58,item_offset=60),
  current_diesound_policy='copy current cached int32 at offset76 after source fallback',
  item_nonnull_service_bound=False,boss_service_bound=False,motu_gameplay_proven=False,no_color_reduction=True)


def pack(report):
 if not 0<len(report['models'])<=16:raise ValueError('DEATH_FIELDS_MODEL_COUNT')
 body=bytearray()
 for i,row in enumerate(report['models']):
  if row['id']!=i:raise ValueError('DEATH_FIELDS_MODEL_ORDER')
  if not isinstance(row['score'],int)or not -0x80000000<=row['score']<=0x7fffffff:raise ValueError('DEATH_FIELDS_SCORE_INT32')
  body.extend(struct.pack('<HHi',i,0,row['score']))
 return struct.pack('<4sHHHH12x',b'B4DF',1,STRIDE,len(report['models']),0)+body


def unpack(data):
 if len(data)<HEADER:raise ValueError('DEATH_FIELDS_HEADER_SHORT')
 magic,version,stride,count,reserved=struct.unpack_from('<4sHHHH',data)
 if (magic,version,stride,reserved)!=(b'B4DF',1,STRIDE,0)or any(data[12:24]):raise ValueError('DEATH_FIELDS_HEADER')
 if not 0<count<=16 or len(data)!=HEADER+count*STRIDE:raise ValueError('DEATH_FIELDS_EXTENT')
 models=[]
 for i in range(count):
  identity,reserved,score=struct.unpack_from('<HHi',data,HEADER+i*STRIDE)
  if identity!=i or reserved:raise ValueError('DEATH_FIELDS_ROW_ID')
  models.append(dict(id=i,score=score))
 return dict(models=models)


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 a.output.mkdir(parents=True,exist_ok=True);report=derive(Source(a.source));data=pack(report);unpack(data)
 report['table_sha256']=hashlib.sha256(data).hexdigest();(a.output/'death_fields.bin').write_bytes(data)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 print(len(report['models']),'source-derived death-field rows')


if __name__=='__main__':main()
