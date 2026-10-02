"""Layer strict actor-policy results over existing entry evidence.

The baseline's scene/presentation/environment evidence is retained, not
recreated by actor parsing. This is analysis only, never a build certificate.
"""
import argparse
import copy
import json
from collections import Counter
from pathlib import Path

from compiler import Source, stage
from analyze import scoped_id


def recertify(previous, actors, source):
    if actors['project_id'] != scoped_id(source):
        raise ValueError('ACTOR_ENTRY_PROJECT_MISMATCH')
    entries=[]
    for old in previous['entries']:
        entry=copy.deepcopy(old)
        if entry['kind']=='STAGE':
            ir=stage(source,entry['source_path'])
            names=sorted({name.casefold() for q in ir.queue
                          for name in (q.character,q.item) if name})
            # Replace only the previous MODEL verdict. Keep every other
            # dependency and previous layout/queue evidence load-bearing.
            entry['blockers']=[b for b in entry['blockers'] if b.get('directive')!='model-contract']
            statuses={}
            for name in names:
                model=actors['models'].get(name)
                exact=None if model is None else model['lowering_profiles']['SOURCE_EXACT']
                statuses[name]='BLOCKED' if exact is None else exact['status']
                if statuses[name]!='SOURCE_CERTIFIED':
                    entry['blockers'].append(dict(group='MODEL',directive='model-contract',value=name,
                        source_file=entry['source_path'] if model is None else model['ir']['source_path'],
                        reason=['NO_SOURCE_MODEL'] if exact is None else exact['blockers']))
            entry['source_actor_status']=statuses
            entry['bindings']['models']=all(s=='SOURCE_CERTIFIED' for s in statuses.values())
            entry['status']='BLOCKED' if entry['blockers'] or not all(entry['bindings'].values()) else 'SOURCE_CERTIFIED'
        else:
            entry['evidence_scope']='retained baseline scene certificate; actor work does not certify new media'
        entries.append(entry)
    return dict(mode='actor-policy-entry-recertification',production_enabled=False,
        scene_evidence='retained input baseline; no new scene runtime claim',entries=entries,
        per_set={name:dict(Counter(e['status'] for e in entries if e['set_name']==name))
                 for name in sorted({e['set_name'] for e in entries})})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path)
    p.add_argument('--previous',type=Path,required=True)
    p.add_argument('--actors',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    result=recertify(json.loads(args.previous.read_text()),json.loads(args.actors.read_text()),Source(args.source))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(result['per_set'],indent=2))


if __name__=='__main__': main()
