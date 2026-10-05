"""Portable, source-derived model identities for generic script name lookup.

The selected engine caches model identity by registry name. findmodel lowercases
that name and only searches loaded models. Loading/residency is a separate live
owner; this ROM table does not silently mark every cached model loaded.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib
from compiler import Source,key
from source_profile import document,discover
from dialect_4086 import ENGINE_COMMIT

STRIDE=64
HEADER=24
NULL_MODEL=0xffff
MAX_NAME=47


def derive(source):
    docs={k:document(source,n) for k,(n,_) in source.index.items() if k.endswith('.txt')}
    structure=discover(source,docs);models=[];seen=set()
    if structure['diagnostics']:raise ValueError('MODEL_REGISTRY_SOURCE_DIAGNOSTICS')
    for model in structure['models']:
        name=model['declaration'];raw=name.encode('ascii')
        if not raw or len(raw)>MAX_NAME or b'\0' in raw:raise ValueError('MODEL_REGISTRY_NAME_CAPACITY')
        identity=raw.lower()
        if identity in seen:raise ValueError('MODEL_REGISTRY_DUPLICATE_IDENTITY')
        seen.add(identity);rows=docs[key(model['source_path'])]['directives']
        if any(r['directive']=='subclass' for r in rows):raise ValueError('MODEL_REGISTRY_SUBCLASS_LOADER_REQUIRED')
        def scalar(name,default):
            declarations=[r for r in rows if r['directive']==name]
            if not declarations:return default
            if len(declarations[-1]['values'])!=1:raise ValueError('MODEL_REGISTRY_SCALAR_ARITY')
            return declarations[-1]['values'][0]
        # init_model uses calloc and does not install a health/alpha default.
        health=int(scalar('health','0'),10);alpha=int(scalar('alpha','0'),10)
        if not -2147483648<=health<=2147483647 or not 0<=alpha<=6:
            raise ValueError('MODEL_REGISTRY_PROPERTY_RANGE')
        models.append(dict(id=len(models),identity=name,lookup_name=identity.decode('ascii'),
                           source_path=model['source_path'],source_sha256=docs[key(model['source_path'])]['sha256'],
                           registry_mode=model['registry_mode'],maxhealth=health,alpha=alpha,
                           declared_type=scalar('type',None)))
    return dict(schema='BYOR_SOURCE_MODEL_REGISTRY_V1',engine_authority=ENGINE_COMMIT,models=models,
                model_identity_authority='init_model/cache registry name; findmodel/makelowercp in source/gamelib/models.c',
                zero_default_authority='init_model calloc; health and alpha have no nonzero initializer',
                live_loaded_bitmap_required=True,world_owner_bound=False,motu_gameplay_proven=False)


def pack(report):
    models=report['models']
    if not 1<=len(models)<=511:raise ValueError('MODEL_REGISTRY_ROM_BANK_CAPACITY')
    body=bytearray()
    for index,model in enumerate(models):
        raw=model['lookup_name'].encode('ascii')
        if model['id']!=index or not 1<=len(raw)<=MAX_NAME:raise ValueError('MODEL_REGISTRY_RECORD_IDENTITY')
        body.extend(struct.pack('<HHiHHI',index,len(raw),model['maxhealth'],model['alpha'],0,0))
        body.extend(raw+b'\0'*(48-len(raw)))
    header=struct.pack('<4sHHHHIII',b'B4MR',1,STRIDE,len(models),0,len(body),zlib.crc32(body)&0xffffffff,0)
    return header+body


def unpack(table):
    if len(table)<HEADER:raise ValueError('MODEL_REGISTRY_HEADER')
    magic,version,stride,count,reserved,size,crc,flags=struct.unpack_from('<4sHHHHIII',table)
    if (magic!=b'B4MR' or version!=1 or stride!=STRIDE or reserved or flags or not 1<=count<=511
        or size!=count*STRIDE or len(table)!=HEADER+size or crc!=zlib.crc32(table[HEADER:])&0xffffffff):
        raise ValueError('MODEL_REGISTRY_ABI')
    models=[];seen=set()
    for index in range(count):
        offset=HEADER+index*STRIDE
        identity,length,health,alpha,r1,r2=struct.unpack_from('<HHiHHI',table,offset)
        name=table[offset+16:offset+16+48]
        if identity!=index or not 1<=length<=MAX_NAME or r1 or r2 or not 0<=alpha<=6:
            raise ValueError('MODEL_REGISTRY_RECORD')
        if any(name[length:]) or b'\0' in name[:length] or name[:length]!=name[:length].lower():
            raise ValueError('MODEL_REGISTRY_NAME')
        value=name[:length].decode('ascii')
        if value in seen:raise ValueError('MODEL_REGISTRY_DUPLICATE_IDENTITY')
        seen.add(value);models.append(dict(id=index,lookup_name=value,maxhealth=health,alpha=alpha))
    return models


def lookup(table,loaded,name):
    models=unpack(table)
    if len(loaded)!=(len(models)+7)//8:raise ValueError('MODEL_REGISTRY_LOADED_BITMAP')
    identity=name.encode('ascii').lower().decode('ascii')
    for model in models:
        index=model['id']
        if model['lookup_name']==identity and loaded[index//8]&(1<<(index%8)):return index
    return NULL_MODEL


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    report=derive(Source(a.source));table=pack(report)
    report.update(bytes=len(table),sha256=hashlib.sha256(table).hexdigest(),source_pak_sha256=hashlib.sha256(Path(a.source).read_bytes()).hexdigest())
    (a.output/'models.b4mr').write_bytes(table);(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(models=len(report['models']),bytes=len(table),world_owner_bound=False)))


if __name__=='__main__':main()
