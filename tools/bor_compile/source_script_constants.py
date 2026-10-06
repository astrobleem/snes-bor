"""Pinned animation constants and explicitly owned live level boundaries.

openbor_transconst first maps strings case-insensitively and otherwise copies
an INTEGER unchanged. Native presentation handles are never engine constants.
Unknown constants require further authority; they are not guessed or aliased.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib
from compiler import Source,key
from source_profile import document,discover
from source_animation_ids import configure,animation_constant,FAMILIES,AUTHORITY

HEADER=24
STRIDE=40
MAX_COUNT=(16384-HEADER)//STRIDE
LIVE={'PLAYER_MIN_Z':1,'PLAYER_MAX_Z':2}
ATTACK_TYPE_ARRAYS={'pains','falls','rises','riseattacks','deaths'}


def derive(source):
    docs={k:document(source,n) for k,(n,_) in source.index.items() if k.endswith('.txt')}
    structure=discover(source,docs);configuration=configure(docs[key(structure['models_path'])]['directives'])
    names=set(configuration['authority']['enum'])
    for family,array in FAMILIES.items():
        if array in ATTACK_TYPE_ARRAYS:continue
        names.update('ANI_'+family.upper()+str(n+1) for n in range(len(configuration['arrays'][array])))
    records=[dict(name=name.lower(),kind=0,value=animation_constant(configuration,name)) for name in sorted(names)]
    records.extend(dict(name=name.lower(),kind=kind,value=0) for name,kind in LIVE.items())
    records.sort(key=lambda row:(len(row['name']),row['name']))
    return dict(schema='BYOR_SOURCE_SCRIPT_CONSTANTS_V1',engine_authority=configuration['authority']['engine_commit'],
                animation_authority_sha256=hashlib.sha256(AUTHORITY.read_bytes()).hexdigest(),
                records=records,live_level_bounds_owner_required=True,
                additional_constant_families_bound=False,world_owner_bound=False,motu_gameplay_proven=False)


def pack(report):
    rows=report['records']
    if not 1<=len(rows)<=MAX_COUNT:raise ValueError('SCRIPT_CONSTANT_ROM_CAPACITY')
    if rows!=sorted(rows,key=lambda row:(len(row['name']),row['name'])):
        raise ValueError('SCRIPT_CONSTANT_CANONICAL_SEARCH_ORDER')
    body=bytearray();seen=set()
    for row in rows:
        raw=row['name'].encode('ascii')
        if not 1<=len(raw)<32 or b'\0' in raw or raw!=raw.lower() or raw in seen:
            raise ValueError('SCRIPT_CONSTANT_NAME')
        seen.add(raw)
        if row['kind'] not in (0,1,2) or not -2147483648<=row['value']<=2147483647:
            raise ValueError('SCRIPT_CONSTANT_VALUE')
        if row['kind'] and row['value']!=0:raise ValueError('SCRIPT_CONSTANT_LIVE_VALUE')
        body.extend(struct.pack('<HHi32s',len(raw),row['kind'],row['value'],raw))
    return struct.pack('<4sHHHHIII',b'B4CT',1,STRIDE,len(rows),0,len(body),zlib.crc32(body)&0xffffffff,0)+body


def unpack(table):
    if len(table)<HEADER:raise ValueError('SCRIPT_CONSTANT_HEADER')
    magic,version,stride,count,reserved,size,crc,flags=struct.unpack_from('<4sHHHHIII',table)
    if (magic!=b'B4CT' or version!=1 or stride!=STRIDE or reserved or flags or not 1<=count<=MAX_COUNT
        or size!=count*STRIDE or len(table)!=HEADER+size or crc!=zlib.crc32(table[HEADER:])&0xffffffff):
        raise ValueError('SCRIPT_CONSTANT_ABI')
    rows=[]
    for n in range(count):
        length,kind,value,raw=struct.unpack_from('<HHi32s',table,HEADER+n*STRIDE)
        if not 1<=length<32 or any(raw[length:]):raise ValueError('SCRIPT_CONSTANT_RECORD')
        rows.append(dict(name=raw[:length].decode('ascii'),kind=kind,value=value))
    if pack(dict(records=rows))!=table:raise ValueError('SCRIPT_CONSTANT_RECORD')
    return rows


def lookup(table,name,level_bounds=None):
    rows=unpack(table)
    row=next((r for r in rows if r['name']==name.lower()),None)
    if row is None:raise ValueError('SCRIPT_CONSTANT_UNBOUND:'+name)
    if row['kind']==0:return row['value']
    if level_bounds is None:raise ValueError('SCRIPT_CONSTANT_LEVEL_OWNER_REQUIRED')
    return level_bounds[row['kind']-1]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    report=derive(Source(a.source));table=pack(report);unpack(table)
    report.update(table_sha256=hashlib.sha256(table).hexdigest(),table_bytes=len(table))
    (a.output/'constants.b4ct').write_bytes(table);(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(records=len(report['records']),bytes=len(table),world_owner_bound=False)))


if __name__=='__main__':main()
