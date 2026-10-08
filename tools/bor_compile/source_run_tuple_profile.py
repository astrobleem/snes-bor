"""Lossless entity snapshots of source RUN fields without duplicate floats.

Pinned cached-model inheritance copies these five fields as one tuple. Under
that admitted policy every reachable tuple is an initially compiled tuple.
An entity keeps its own handle; later shared-cache changes cannot retarget it.
Unadmitted direct field mutations must fail rather than use the cached model
as a substitute for the entity's earlier shallow copy.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from compiler import Source
from dialect_4086 import ENGINE_COMMIT
from source_model_core_4086 import derive as cores, FLOAT_FIELDS
from source_model_switch_4086 import RUN_FIELDS


def tuple_bytes(fields):
    return b''.join(struct.pack('<f' if f in FLOAT_FIELDS else '<i',fields[f])for f in RUN_FIELDS)


def derive(source):
    core=cores(source);tuples=[];models=[]
    if len(core['cache_fields'])!=39 or core['cache_fields'][1:6]!=RUN_FIELDS:
        raise ValueError('RUN_TUPLE_CACHED_MODEL_ABI')
    for m in core['models']:
        raw=tuple_bytes(m['fields'])
        if raw not in tuples:tuples.append(raw)
        models.append(dict(id=m['id'],identity=m['identity'],source_sha256=m['source_sha256'],
                           initial_tuple=tuples.index(raw)+1))
    if not 1<=len(models)<=16:raise ValueError('RUN_TUPLE_MODEL_CAPACITY')
    # Byte identity, including signed zero, is retained even though the source
    # numeric zero test decides whether an entire tuple is inherited.
    closure=[]
    for old in tuples:
        for new in tuples:
            speed=struct.unpack_from('<f',new)[0]
            result=old if speed==0 else new
            assert result in tuples
            closure.append(tuples.index(result)+1)
    return dict(schema='BYOR_4086_RUN_TUPLE_PROFILE_V1',engine_commit=ENGINE_COMMIT,
                fields=RUN_FIELDS,tuples=[r.hex()for r in tuples],models=models,
                tuple_count=len(tuples),tuple_bytes=20,entity_handle_bytes=256,
                uncompressed_entity_bytes=2560,cache_inheritance_closure_pairs=len(closure),
                closure_sha256=hashlib.sha256(bytes(closure)).hexdigest(),
                admitted_mutations='initial loader and atomic cached-model RUN inheritance; direct RUN writes require a separate owner',
                entity_snapshot_policy='capture before animation/model callbacks; immutable tuple handle per physical entity',
                native_model_copy_bound=False,motu_gameplay_proven=False,no_color_reduction=True)


def pack(report):
    rows=[bytes.fromhex(r)for r in report['tuples']]
    if not 1<=len(rows)<=16 or any(len(r)!=20 for r in rows):raise ValueError('RUN_TUPLE_TABLE_DOMAIN')
    return struct.pack('<4s6H',b'B4RT',1,len(rows),20,len(report['models']),0,0)+b''.join(rows)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=derive(Source(a.source));data=pack(r)
    r.update(table_bytes=len(data),table_sha256=hashlib.sha256(data).hexdigest())
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    a.output.with_suffix('.b4rt').write_bytes(data)
    print('Compiled',r['tuple_count'],'lossless RUN tuples;',r['entity_handle_bytes'],'entity bytes')


if __name__=='__main__':main()
