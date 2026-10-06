"""Pinned Build 4086 animation numbers, distinct from BYOR frame handles.

The immutable authority snapshot contains enum values, default arrays, exact
loader aliases and expansion order from af23dc9. Numbered model roles index the
loader arrays; openborconstant checks named enum values before dynamic arrays.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
from compiler import Source,key
from source_profile import document,discover

AUTHORITY=Path(__file__).with_name('authority')/'4086_animation_ids.json'
FAMILIES={'down':'downs','up':'ups','backwalk':'backwalks','walk':'walks','idle':'idles',
          'freespecial':'freespecials','attack':'normal_attacks','follow':'follows',
          'pain':'pains','fall':'falls','rise':'rises','riseattack':'riseattacks',
          'blockpain':'blkpains','die':'deaths'}


def configure(rows):
    authority=json.loads(AUTHORITY.read_text())
    defaults=authority['default_arrays'];limits={}
    for array,field in authority['expansion_order']:
        size=len(defaults[array])
        if field in limits and limits[field]!=size:raise ValueError('ANIMATION_AUTHORITY_DEFAULT_DRIFT')
        limits[field]=size
    for row in rows:
        field=authority['limit_directives'].get(row['directive'])
        if field is None:continue
        if len(row['values'])!=1:raise ValueError('ANIMATION_LIMIT_ARITY')
        # load_models clamps every requested maximum to its default capacity.
        value=int(row['values'][0],10)
        minimum=max(len(defaults[a]) for a,f in authority['expansion_order'] if f==field)
        limits[field]=max(value,minimum)
        if limits[field]>1024:raise ValueError('ANIMATION_LIMIT_COMPILER_CAPACITY')
    next_id=authority['enum']['MAX_ANIS'];arrays={}
    for array,field in authority['expansion_order']:
        values=list(defaults[array]);extra=limits[field]-len(values)
        values.extend(range(next_id,next_id+extra));next_id+=extra;arrays[array]=values
    return dict(authority=authority,limits=limits,arrays=arrays,max_animations=next_id)


def role_id(configuration,role):
    role=role.lower()
    direct=configuration['authority']['direct_loader_aliases'].get(role)
    if direct is not None:return configuration['authority']['enum'][direct]
    match=re.fullmatch(r'([a-z]+)([1-9][0-9]*)?',role)
    if not match or match[1] not in FAMILIES:raise ValueError('ANIMATION_ROLE_UNSUPPORTED:'+role)
    values=configuration['arrays'][FAMILIES[match[1]]];index=int(match[2] or 1)-1
    if not 0<=index<len(values):raise ValueError('ANIMATION_ROLE_OUTSIDE_SOURCE_LIMIT:'+role)
    return values[index]


def animation_constant(configuration,name):
    # ICMPCONST precedes ICMPSCONSTA/B; constant names use case folding.
    name=name.upper();enum=configuration['authority']['enum']
    if name in enum:return enum[name]
    match=re.fullmatch(r'ANI_([A-Z]+)([1-9][0-9]*)',name)
    if not match or match[1].lower() not in FAMILIES:
        raise ValueError('ANIMATION_CONSTANT_UNSUPPORTED:'+name)
    array=FAMILIES[match[1].lower()];index=int(match[2])-1
    # ICMPSCONSTB uses STA_ATKS for extended attack-type animation names.
    if array in ('pains','falls','rises','riseattacks','deaths'):
        raise ValueError('ANIMATION_ATTACK_TYPE_CONSTANT_AUTHORITY_REQUIRED:'+name)
    values=configuration['arrays'][array]
    if not 0<=index<len(values):raise ValueError('ANIMATION_CONSTANT_OUTSIDE_SOURCE_LIMIT:'+name)
    return values[index]


def derive(source):
    docs={k:document(source,n) for k,(n,_) in source.index.items() if k.endswith('.txt')}
    structure=discover(source,docs);configuration=configure(docs[key(structure['models_path'])]['directives'])
    models=[]
    for model in structure['models']:
        seen={};animations=[]
        for animation in model['animations']:
            role=animation['role'];number=role_id(configuration,role)
            if number in seen:
                raise ValueError('ANIMATION_SOURCE_ALIAS_REPLACEMENT_REQUIRED:'+model['declaration']+':'+role+':'+seen[number])
            seen[number]=role;animations.append(dict(role=role,engine_animation_id=number))
        models.append(dict(identity=model['declaration'],source_path=model['source_path'],animations=animations))
    return dict(schema='BYOR_4086_ANIMATION_IDENTITIES_V1',engine_authority=configuration['authority']['engine_commit'],
                authority_snapshot_sha256=hashlib.sha256(AUTHORITY.read_bytes()).hexdigest(),
                limits=configuration['limits'],max_animations=configuration['max_animations'],models=models,
                frame_handles_are_engine_animation_numbers=False,world_owner_bound=False,motu_gameplay_proven=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();report=derive(Source(a.source))
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(models=len(report['models']),animations=sum(len(m['animations']) for m in report['models']),
                          max_animations=report['max_animations'],world_owner_bound=False)))


if __name__=='__main__':main()
