"""Immutable source damage model inputs; no actor-name selection."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib
from compiler import Source, key
from dialect_4086 import ENGINE_COMMIT
from source_model_core_4086 import integer
from source_profile import document, discover

HEADER=24
STRIDE=16


def load(rows):
    d=dict(animal=0,nodrop=0,guardpoints=0)
    for r in rows:
        n,v=r['directive'],r['values']
        if n=='anim':break
        if n in d:d[n]=integer(v)
        elif n=='nomove' and integer(v):d['nodrop']=1
    return d


def derive(source):
    docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')}
    models=[]
    for i,m in enumerate(discover(source,docs)['models']):
        doc=docs[key(m['source_path'])]
        models.append(dict(id=i,identity=m['declaration'],source_path=m['source_path'],source_sha256=doc['sha256'],fields=load(doc['directives'])))
    return dict(schema='BYOR_4086_DAMAGE_INPUTS_V1',engine_commit=ENGINE_COMMIT,models=models,
                field_authority='calloc zero defaults; ANIMAL/NODROP/GUARDPOINTS; ordered NOMOVE side effect sets nodrop1',
                guardpoints_policy='model initial current=max; dynamic current guardpoints requires a separate runtime capability',
                native_damage_callbacks_bound=False,motu_gameplay_proven=False,no_color_reduction=True)


def pack(report):
    if not 1<=len(report['models'])<=16:raise ValueError('DAMAGE_INPUT_MODEL_CAPACITY')
    body=bytearray()
    for i,m in enumerate(report['models']):
        if m['id']!=i:raise ValueError('DAMAGE_INPUT_MODEL_ID')
        d=m['fields'];body.extend(struct.pack('<HHiii',i,0,d['animal'],d['nodrop'],d['guardpoints']))
    return struct.pack('<4sHHHHIII',b'B4DI',1,STRIDE,len(report['models']),0,len(body),zlib.crc32(body)&0xffffffff,0)+body


def unpack(raw):
    if len(raw)<HEADER:raise ValueError('DAMAGE_INPUT_HEADER')
    magic,version,stride,count,res,size,crc,flags=struct.unpack_from('<4sHHHHIII',raw)
    if (magic,version,stride,res,flags)!=(b'B4DI',1,STRIDE,0,0)or not 1<=count<=16 or size!=count*STRIDE or len(raw)!=HEADER+size or crc!=zlib.crc32(raw[HEADER:])&0xffffffff:raise ValueError('DAMAGE_INPUT_ABI')
    rows=[]
    for i in range(count):
        identity,res,animal,nodrop,guard=struct.unpack_from('<HHiii',raw,HEADER+i*STRIDE)
        if identity!=i or res:raise ValueError('DAMAGE_INPUT_ROW')
        rows.append(dict(id=i,fields=dict(animal=animal,nodrop=nodrop,guardpoints=guard)))
    return rows


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=derive(Source(a.source));raw=pack(r);decoded=unpack(raw)
    assert all(x['fields']==y['fields']for x,y in zip(r['models'],decoded))
    r.update(table_bytes=len(raw),table_sha256=hashlib.sha256(raw).hexdigest());a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'damage.b4di').write_bytes(raw);(a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(len(decoded),'damage model inputs;',len(raw),'bytes')


if __name__=='__main__':main()
