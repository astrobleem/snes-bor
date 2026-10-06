"""Source-derived immutable constructor/default-init model scalars.

B4LI supplies additional payload beyond the existing cached model core.
Installation and complete lifecycle ownership remain separate capabilities.
"""
import argparse,hashlib,json,struct,zlib,math
from pathlib import Path
from compiler import Source,key
from dialect_4086 import ENGINE_COMMIT
from source_profile import document,discover
from source_model_core_4086 import binary32,integer

HEADER=24
STRIDE=32
SUBTYPES=dict(none=0,biker=1,notgrab=2,arrow=3,touch=4,weapon=5,noskip=6,flydie=7,both=8,projectile=9,follow=10,chase=11)

def load(rows):
    d=dict(subtype=0,nomove=0,makeinv=0,priority=1,knockdowncount=0.0)
    for r in rows:
        n,v=r['directive'],r['values']
        if n=='anim':break
        if n=='subtype':
            if len(v)!=1 or v[0].lower() not in SUBTYPES:raise ValueError('LIFECYCLE_SUBTYPE_REQUIRED')
            d[n]=SUBTYPES[v[0].lower()]
        elif n in ('nomove','priority'):d[n]=integer(v)
        elif n=='makeinv':
            if not 1<=len(v)<=2:raise ValueError('LIFECYCLE_MAKEINV_ARITY')
            value=binary32(binary32(v[0])*200)
            if not -2147483648<=value<=2147483647:raise ValueError('LIFECYCLE_MAKEINV_DOMAIN')
            value=int(value)
            d[n]=-value if integer(v,1) else value
            if d[n]==-2147483648:raise ValueError('LIFECYCLE_ABS_INT_MIN_UNDEFINED')
        elif n=='knockdowncount':
            if len(v)!=1:raise ValueError('LIFECYCLE_KNOCKDOWN_ARITY')
            d[n]=binary32(v[0])
            if not math.isfinite(d[n]):raise ValueError('LIFECYCLE_KNOCKDOWN_FINITE_REQUIRED')
    return d

def derive(source):
    docs={k:document(source,n) for k,(n,_) in source.index.items() if k.endswith('.txt')};structure=discover(source,docs);models=[]
    for i,m in enumerate(structure['models']):
        doc=docs[key(m['source_path'])];models.append(dict(id=i,identity=m['declaration'],source_path=m['source_path'],source_sha256=doc['sha256'],fields=load(doc['directives'])))
    return dict(schema='BYOR_4086_LIFECYCLE_INPUTS_V1',engine_commit=ENGINE_COMMIT,models=models,field_authority='init_model priority=1/calloc; CMD_MODEL_SUBTYPE/NOMOVE/MAKEINV/KNOCKDOWNCOUNT',makeinv_policy='binary32 GET_FLOAT_ARG * GAME_SPEED(200), truncated signed int; optional second argument negates',native_lifecycle_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)

def pack(report):
    if not 1<=len(report['models'])<=16:raise ValueError('LIFECYCLE_MODEL_CAPACITY')
    body=bytearray()
    for i,m in enumerate(report['models']):
        if m['id']!=i:raise ValueError('LIFECYCLE_MODEL_ID')
        d=m['fields'];body.extend(struct.pack('<HHIiiif8x',i,0,d['subtype'],d['nomove'],d['makeinv'],d['priority'],d['knockdowncount']))
    return struct.pack('<4sHHHHIII',b'B4LI',1,STRIDE,len(report['models']),0,len(body),zlib.crc32(body)&0xffffffff,0)+body

def unpack(raw):
    if len(raw)<HEADER:raise ValueError('LIFECYCLE_HEADER')
    magic,version,stride,count,res,size,crc,flags=struct.unpack_from('<4sHHHHIII',raw)
    if (magic,version,stride,res,flags)!=(b'B4LI',1,STRIDE,0,0) or not 1<=count<=16 or size!=count*STRIDE or len(raw)!=HEADER+size or crc!=zlib.crc32(raw[HEADER:])&0xffffffff:raise ValueError('LIFECYCLE_ABI')
    models=[]
    for i in range(count):
        row=raw[HEADER+i*STRIDE:HEADER+(i+1)*STRIDE];identity,res,subtype,nomove,makeinv,priority,knock=struct.unpack_from('<HHIiiif',row)
        if identity!=i or res or subtype not in SUBTYPES.values() or row[24:]!=bytes(8) or makeinv==-2147483648 or not math.isfinite(knock):raise ValueError('LIFECYCLE_ROW')
        models.append(dict(id=i,fields=dict(subtype=subtype,nomove=nomove,makeinv=makeinv,priority=priority,knockdowncount=knock)))
    return models

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=derive(Source(a.source));raw=pack(r);decoded=unpack(raw)
    assert all(x['fields']==y['fields'] for x,y in zip(r['models'],decoded));r.update(table_bytes=len(raw),table_sha256=hashlib.sha256(raw).hexdigest());a.output.mkdir(parents=True,exist_ok=True);(a.output/'lifecycle.b4li').write_bytes(raw);(a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(len(decoded),'lifecycle models;',len(raw),'bytes')

if __name__=='__main__':main()
