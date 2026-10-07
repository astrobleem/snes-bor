"""Closed source stage queue inputs, before live smartspawn admission.

Preserves physical declaration order and empty AT records. Construction and
post-construction overrides are separate services, never fixture aliases.
"""
import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path
from compiler import Source, key
from dialect_4086 import ENGINE_COMMIT
from source_profile import document, discover
from source_model_registry import derive as registry
from source_model_core_4086 import integer, binary32

HEADER, STRIDE = 24, 128
KINDS = dict(empty=0, spawn=1, wait=2, group=3)
PROPERTIES = {'coords','alias','health','2phealth','3phealth','4phealth','map','flip','boss'}
COMMAND_VALUES = PROPERTIES | {'spawn','wait','group','at'}
OTHER_QUEUE_PROPERTIES = {'item','itemalias','itemmap','itemhealth','itemplayer','spawnplayer','weapon','mp','score','multiple','aggression','alpha','dying','nolife','itemtrans','spawnscript','@script','musicfade','join','music'}
STAGE_METADATA = {'background','frontpanel','panel','order','palette','bossmusic','spawn1','spawn2','spawn3','spawn4','nohit','wall','hole','minz','maxz','cameraxoffset','camerazoffset','scrollspeed','direction','scrolldir'}

def empty():
    return dict(kind='empty',model=65535,coords=[0.0]*3,flip=0,health=[0]*4,map=0,boss=0,group=[0,0],alias='')

def load(rows, model_ids):
    pending=empty();result=[]
    for i,row in enumerate(rows):
        n,v=row['directive'],row['values']
        if n in COMMAND_VALUES and any('"'in x or "'"in x for x in v):raise ValueError('STAGE_QUEUE_QUOTED_ARGUMENT_PARSER_REQUIRED')
        if n in ('spawn','wait','group'):
            pending=empty();pending['kind']=n
            if n=='spawn':
                if len(v)!=1 or key(v[0])not in model_ids:raise ValueError('STAGE_QUEUE_MODEL_RESOLUTION_REQUIRED')
                pending['model']=model_ids[key(v[0])]
            elif n=='group':pending['group']=[integer(v)if integer(v)>=1 else 100,max(1,integer(v,1))]
        elif n=='at':
            if len(v)!=1:raise ValueError('STAGE_QUEUE_AT_ARITY')
            result.append(dict(pending,at=integer(v),line=row['line']))
            pending=empty()
        elif n in PROPERTIES:
            if n=='coords':
                if not 1<=len(v)<=3:raise ValueError('STAGE_QUEUE_COORDS_ARITY')
                pending['coords']=[binary32(v[j]if j<len(v)else 0)for j in range(3)]
                if any(not -32768<=x<32768 for x in pending['coords']):raise ValueError('STAGE_QUEUE_POSITION_Q16_DOMAIN')
            elif n=='alias':
                if len(v)!=1:raise ValueError('STAGE_QUEUE_ALIAS_ARITY')
                raw=v[0].encode('ascii')
                if len(raw)>47 or b'\0'in raw:raise ValueError('STAGE_QUEUE_ALIAS_CAPACITY')
                pending['alias']=v[0]
            elif n=='health':pending['health']=[integer(v)]*4
            elif n in ('2phealth','3phealth','4phealth'):
                for player in range(int(n[0])-1,4):pending['health'][player]=integer(v)
            else:pending[n]=integer(v)
        elif n in OTHER_QUEUE_PROPERTIES:
            # Stage music before an entry is global, except an immediately
            # following AT (the loader's distinct queued-music branch).
            if n=='music'and pending['kind']=='empty'and not(i+1<len(rows)and rows[i+1]['directive']=='at'):continue
            raise ValueError('STAGE_QUEUE_PROPERTY_SERVICE_REQUIRED:'+n)
        elif n not in STAGE_METADATA:raise ValueError('STAGE_QUEUE_DIRECTIVE_SERVICE_REQUIRED:'+n)
    if pending!=empty():raise ValueError('STAGE_QUEUE_UNTERMINATED_ENTRY')
    return result

def derive(source):
    docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')}
    structure=discover(source,docs)
    if structure['diagnostics']:raise ValueError('STAGE_QUEUE_SOURCE_DIAGNOSTICS')
    ids={key(m['identity']):m['id']for m in registry(source)['models']}
    stages=[];seen=set()
    for source_set in structure['sets']:
        for entry in source_set['entries']:
            k=key(entry['source_path'])
            if entry['kind']!='STAGE'or k in seen:continue
            seen.add(k);doc=docs[k]
            records=load(doc['directives'],ids)
            stages.append(dict(stage_id=len(stages)+1,source_path=doc['source_path'],source_sha256=doc['sha256'],records=records))
    return dict(schema='BYOR_4086_STAGE_QUEUE_INPUTS_V1',engine_commit=ENGINE_COMMIT,stages=stages,
                source_loader_authority_proven=False,positions_numeric_policy='Original binary32 bits retained; native Q16 conversion requires explicit measured compatibility. Authored integral MOTU stage positions are exact in Q16.',stage_metadata_execution_bound=False,live_producer_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)

def pack(report):
    body=bytearray()
    for stage in report['stages']:
        for r in stage['records']:
            alias=r['alias'].encode('ascii')
            row=struct.pack('<HHHHi3f i4i4iHH',stage['stage_id'],KINDS[r['kind']],r['model'],0,r['at'],*r['coords'],r['flip'],*r['health'],r['map'],r['boss'],*r['group'],len(alias),0)+alias.ljust(48,b'\0')
            row+=struct.pack('<3iI',*[int(x*65536)for x in r['coords']],0)
            if len(row)!=STRIDE:raise ValueError('STAGE_QUEUE_ROW_LAYOUT')
            body.extend(row)
    count=len(body)//STRIDE
    if count>65535 or len(body)>32768-HEADER:raise ValueError('STAGE_QUEUE_ROM_CAPACITY')
    return struct.pack('<4sHHHHIII',b'B5SQ',1,STRIDE,count,len(report['stages']),len(body),zlib.crc32(body),0)+body

def unpack(raw, model_count):
    if len(raw)<HEADER:raise ValueError('STAGE_QUEUE_HEADER')
    magic,version,stride,count,stages,size,crc,reserved=struct.unpack_from('<4sHHHHIII',raw)
    body=raw[HEADER:]
    if (magic,version,stride,reserved)!=(b'B5SQ',1,STRIDE,0)or size!=len(body)or size!=count*STRIDE or zlib.crc32(body)!=crc:raise ValueError('STAGE_QUEUE_ABI_CRC')
    rows=[]
    for offset in range(0,size,STRIDE):
        v=struct.unpack_from('<HHHHi3fi4i4iHH48s3iI',body,offset)
        stage,kind,model=v[:3];alias=v[19]
        if not 1<=stage<=stages or kind not in KINDS.values()or v[3]or v[18]or v[23]:raise ValueError('STAGE_QUEUE_ROW_IDENTITY')
        if (kind==1 and not 0<=model<model_count)or(kind!=1 and model!=65535):raise ValueError('STAGE_QUEUE_MODEL_PAIR')
        if v[17]>47 or b'\0'in alias[:v[17]]or any(alias[v[17]:]):raise ValueError('STAGE_QUEUE_ALIAS_ENCODING')
        coords=list(v[5:8])
        if any(not -32768<=x<32768 for x in coords)or list(v[20:23])!=[int(x*65536)for x in coords]:raise ValueError('STAGE_QUEUE_POSITION_PAIR')
        if kind==3 and (v[15]<1 or v[16]<1):raise ValueError('STAGE_QUEUE_GROUP_POLICY')
        rows.append(dict(stage_id=stage,kind=next(k for k,n in KINDS.items()if n==kind),model=model,at=v[4],coords=coords,flip=v[8],health=list(v[9:13]),map=v[13],boss=v[14],group=list(v[15:17]),alias=alias[:v[17]].decode('ascii'),coords_q16=list(v[20:23])))
    return rows

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    source=Source(a.source);d=derive(source);raw=pack(d);unpack(raw,len(registry(source)['models']));a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'stage_queue.bin').write_bytes(raw);d['table_sha256']=hashlib.sha256(raw).hexdigest()
    (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n')
    print(len(d['stages']),'stages',sum(len(s['records'])for s in d['stages']),'source queue records',len(raw),'bytes; live producer unbound')

if __name__=='__main__':main()
