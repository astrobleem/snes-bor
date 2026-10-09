"""Source type-filter inventory; actual runtime candidate checks stay required.

This is not a claim that an arbitrary engine service cannot change a type.
It derives the declared namespace and checks the complete parsed authored
script corpus for explicit or dynamic type/model property writes.
"""
import argparse
import hashlib
import json
from pathlib import Path
from compiler import Source
from dialect_4086 import ENGINE_COMMIT
from source_model_core_4086 import derive as model_inputs
from script_ir_4086 import inspect
from script_native_api import SIGNATURES


def walk(node):
    yield node
    for edge in node.get('children',[]):
        yield from walk(edge['node'])


def child(node,name):
    return next((c['node']for c in node.get('children',[])if c['edge']==name),None)


def derive(source,mask):
    if not isinstance(mask,int)or not 0<mask<=0xffffffff:
        raise ValueError('TYPE_FILTER_MASK_DOMAIN')
    core=model_inputs(source);scripts=inspect(source)
    writes=[];trees=[]
    for library in scripts['libraries'].values():
        trees.extend((library['source_path'],f['name'],f['ast'])for f in library['functions'].values())
    trees.extend((b['declaration']['source_path'],'inline',b['ast'])for b in scripts['inline_blocks'])
    for path,function,tree in trees:
        for node in walk(tree):
            if node['kind']!='FuncCall':continue
            name=child(node,'name')
            if name is None or name['kind']!='ID':raise ValueError('TYPE_FILTER_INDIRECT_SCRIPT_CALL')
            if name['name']not in ('changeentityproperty','changemodelproperty'):continue
            args=child(node,'args');values=[]if args is None else[c['node']for c in args['children']]
            key=values[1]if len(values)>1 else None
            property_key=key.get('value','')[1:-1].lower()if key and key['kind']=='Constant'and key.get('type')=='string'else None
            # Conservative for C escapes/concatenation: such a key needs the
            # actual variant-string lowering rather than a spelling comparison.
            if property_key is not None and any(c in property_key for c in ('\\','"')):property_key=None
            writes.append(dict(source_path=path,function=function,line=node.get('source_line'),api=name['name'],property=property_key))
    blockers=[w for w in writes if w['api']=='changemodelproperty'or w['property']in(None,'type','model','modeldata')]
    matching=[m['id']for m in core['models']if m['fields']['type']&mask]
    declared_absent=not matching
    unknown_calls=sorted(set(scripts['engine_api_requirements'])-{name for name,_ in SIGNATURES})
    return dict(schema='BYOR_SOURCE_TYPE_FILTER_ABSENCE_V1',engine_commit=ENGINE_COMMIT,
        mask=mask,capability='SOURCE_DECLARED_TYPE_ABSENCE_WITH_RUNTIME_CHECK'if declared_absent and not(blockers or unknown_calls or scripts['diagnostics'])else 'FULL_CANDIDATE_OWNER_REQUIRED',
        declared_types_absent=declared_absent,matching_models=matching,script_mutation_blockers=blockers,
        models=[dict(id=m['id'],identity=m['identity'],type=m['fields']['type'],source_path=m['source_path'],source_sha256=m['source_sha256'])for m in core['models']],
        property_writes=writes,script_libraries=[dict(source_path=l['source_path'],source_sha256=l['source_sha256'])for l in scripts['libraries'].values()],
        inline_blocks=len(scripts['inline_blocks']),authored_bindings=len(scripts['bindings']),script_diagnostics=scripts['diagnostics'],
        unknown_engine_calls=unknown_calls,engine_api_requirements=scripts['engine_api_requirements'],
        runtime_candidate_check_required=True,matching_runtime_candidate_must_fault=True,
        arbitrary_engine_type_mutation_proven_absent=False,full_pickup_owner_bound=False,
        foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True)
    p.add_argument('--mask',type=lambda v:int(v,0),required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=derive(Source(a.source),a.mask)
    digest=hashlib.sha256()
    with a.source.open('rb')as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    r['source_pak_sha256']=digest.hexdigest()
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(r['capability'],len(r['models']),'models;',len(r['property_writes']),'property writes; runtime candidate guard remains required')


if __name__=='__main__':main()
