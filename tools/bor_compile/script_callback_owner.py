"""Source model -> animation script instance/program ownership descriptors.

Current/default callbacks share one entity animation variable list. Optimized
frame routes require installed locals to remain stable between executions.
Mutable installed-local writes and keys whose namespace is unproven are rejected,
not silently evaluated using the entry snapshot. Nested engine actions still
require a separate continuation owner.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import struct
import zlib
from compiler import Source,key
from source_profile import document,discover
from script_ir_4086 import parse_script
from script_frame_dispatch import compile_frames,link_frames,pack_dispatch
from source_model_registry import derive as registry,pack as pack_registry

HEADER=32
STRIDE=16
NULL_PROGRAM=0xffff
CAP_STABLE_INSTALLED_LOCALS=1
INSTALLED={'self','frame','animnum','animhandle'}


def installed_local_writes(tree):
    writes=[]
    def prefix(node):
        if node.get('kind')=='Constant' and node.get('type')=='string':
            try:return ast.literal_eval(node['value'])
            except (SyntaxError,ValueError):raise ValueError('CALLBACK_LOCAL_KEY_LITERAL') from None
        if node.get('kind')=='BinaryOp' and node.get('op')=='+':
            children={c['edge']:c['node'] for c in node.get('children',[])}
            return prefix(children.get('left',{}))
        return None
    def visit(node):
        children={c['edge']:c['node'] for c in node.get('children',[])}
        if node['kind']=='FuncCall' and children.get('name',{}).get('name')=='setlocalvar':
            args=children.get('args',{}).get('children',[])
            first=args[0]['node'] if args else {}
            guaranteed_prefix=prefix(first)
            if guaranteed_prefix is not None and not any(name.startswith(guaranteed_prefix) for name in INSTALLED):
                pass # Every possible successful concatenation stays outside the installed namespace.
            elif first.get('kind')!='Constant' or first.get('type')!='string':
                writes.append(dict(key=None,line=node.get('source_line'),reason='DYNAMIC_LOCAL_KEY'))
            else:
                try:name=ast.literal_eval(first['value'])
                except (SyntaxError,ValueError):raise ValueError('CALLBACK_LOCAL_KEY_LITERAL') from None
                if name in INSTALLED:writes.append(dict(key=name,line=node.get('source_line'),reason='INSTALLED_LOCAL_WRITE'))
        for child in children.values():visit(child)
    for function in tree['functions'].values():visit(function['ast'])
    return writes


def derive(source):
    dispatch_source=compile_frames(source);instructions,metadata,linked=link_frames(dispatch_source)
    dispatch=pack_dispatch(dispatch_source,linked,instructions,metadata)
    models=registry(source);model_table=pack_registry(models)
    docs={k:document(source,n) for k,(n,_) in source.index.items() if k.endswith('.txt')}
    structure=discover(source,docs);by_model={p['identity']['model']:i for i,p in enumerate(linked['programs'])}
    slots_offset=struct.unpack_from('<I',metadata,28)[0];rows=[]
    for model,row in zip(structure['models'],models['models']):
        writes=[]
        for script in model['scripts']:
            name=script['values'][0]
            writes+=installed_local_writes(parse_script(source.read(name).decode('latin1'),name))
        # Inline blocks can also mutate installed locals between current/default
        # callbacks. Check all functions/blocks, including currently unreachable
        # paths, before granting optimized dispatch ownership.
        for block in model['inline_scripts']:
            writes+=installed_local_writes(parse_script('void __probe(){'+ '\n'.join(block['text'])+'}',
                                                        model['source_path']+'#inline'))
        program=by_model.get(model['declaration'],NULL_PROGRAM)
        detail=linked['programs'][program] if program!=NULL_PROGRAM else None
        rows.append(dict(id=row['id'],model=row['identity'],program=program,
            slot_base=detail['slot_base'] if detail else 0,slot_count=detail['slots'] if detail else 0,
            initializers_offset=slots_offset+8*detail['slot_base'] if detail else 0,
            capability=CAP_STABLE_INSTALLED_LOCALS if detail and not writes else 0,
            rejections=writes,source_sha256=row['source_sha256']))
    report=dict(schema='BYOR_SOURCE_ANIMATION_CALLBACK_OWNER_V1',models=rows,
        program_count=len(linked['programs']),metadata_bytes=len(metadata),
        model_registry_crc32=zlib.crc32(model_table)&0xffffffff,
        instruction_crc32=zlib.crc32(instructions)&0xffffffff,
        metadata_crc32=zlib.crc32(metadata)&0xffffffff,dispatch_crc32=zlib.crc32(dispatch)&0xffffffff,
        sharing_policy='entity token plus animation scope; install locals once, current then source-eligible default, clear once',
        optimization_policy='Reject installed-local writes and unproven dynamic keys; literal prefixes outside the installed namespace are safe. No entry-snapshot substitution for mutable locals.',
        nested_callback_owner_bound=False,live_callback_owner_bound=False,motu_gameplay_proven=False)
    return report,instructions,metadata,dispatch


def pack(report):
    rows=report['models'];body=bytearray()
    for n,row in enumerate(rows):
        if row['id']!=n:raise ValueError('CALLBACK_OWNER_MODEL_ORDER')
        if row['rejections']:raise ValueError('CALLBACK_OWNER_MUTABLE_INSTALLED_LOCALS:'+row['model'])
        body.extend(struct.pack('<8H',n,row['program'],row['slot_base'],row['slot_count'],
            row['initializers_offset'],row['capability'],0,0))
    return struct.pack('<4s6H4I',b'B4CO',1,STRIDE,len(rows),report['program_count'],report['metadata_bytes'],0,
        *(report[n] for n in ('model_registry_crc32','instruction_crc32','metadata_crc32','dispatch_crc32')))+body


def unpack(data):
    if len(data)<HEADER:raise ValueError('CALLBACK_OWNER_HEADER')
    fields=struct.unpack_from('<4s6H4I',data);magic,version,stride,count,programs,metadata_bytes,reserved=fields[:7]
    if magic!=b'B4CO' or version!=1 or stride!=STRIDE or reserved or not count or not programs or metadata_bytes>17760 or len(data)!=HEADER+count*stride:
        raise ValueError('CALLBACK_OWNER_ABI')
    result=[]
    for n in range(count):
        row=struct.unpack_from('<8H',data,HEADER+n*stride)
        if row[0]!=n or row[6:]!=(0,0):raise ValueError('CALLBACK_OWNER_RECORD')
        if row[1]==NULL_PROGRAM:
            if any(row[2:6]):raise ValueError('CALLBACK_OWNER_EMPTY_PROGRAM')
        elif row[1]>=programs or row[5]!=CAP_STABLE_INSTALLED_LOCALS or not row[3] or row[4]+8*row[3]>metadata_bytes:
            raise ValueError('CALLBACK_OWNER_PROGRAM')
        result.append(row)
    return result


def validate_pair(data,model_registry,instructions,metadata,dispatch):
    rows=unpack(data);crcs=struct.unpack_from('<4I',data,16)
    if crcs!=tuple(zlib.crc32(raw)&0xffffffff for raw in (model_registry,instructions,metadata,dispatch)):
        raise ValueError('CALLBACK_OWNER_PAIRED_IDENTITY')
    return rows


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r,code,metadata,dispatch=derive(Source(a.source));data=pack(r);unpack(data)
    a.output.mkdir(parents=True,exist_ok=True)
    r.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
    for name,raw in [('callbacks.b4co',data),('instructions.bin',code),('metadata.b48r',metadata),('dispatch.b4fd',dispatch)]:
        (a.output/name).write_bytes(raw)
    (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(dict(models=len(r['models']),programs=r['program_count'],bytes=len(data))))


if __name__=='__main__':main()
