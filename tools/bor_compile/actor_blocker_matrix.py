"""Count distinct blocked models, retaining exact diagnostic provenance.

Inputs are strict actor reports, not candidate/asset-presence summaries.
One diagnostic may require several capabilities; rows must not be summed.
"""
import argparse
import hashlib
import json
from pathlib import Path

RULES={
 'FIXED_SLOT_MEDIA_FORMAT':('MEDIA',),
 'FRAME_TRANSFORM_PROOF':('FRAME_RASTER',),
 'PALETTE_QUANTIZATION_POLICY':('PALETTE',),
 'BASE_STAT_BINDING':('STATS',),
 'ROLE_BINDING':('ROLE_TRANSITION',),
 'PER_FRAME_TIMING':('ANIMATION_TIMING',),
 'SOURCE_BODY_BOXES':('COLLISION',),
 'FRAME_ATTACK_CONSUMER':('ATTACK_ACTIVATION','DAMAGE_FORCE','DROP'),
 'FRAME_MOVE_CONSUMER':('FRAME_MOVEMENT',),
 'SOURCE_BEHAVIOR_CONTRACT':('AI',),
 'DRIFT_DRIVER':('RNG','CADENCE'),
 'EFFECT_BINDING':('SPECIAL_EFFECT',),
 'UNKNOWN_SOURCE_SEMANTIC':('DIALECT',),
 'MISSING_ASSET':('MEDIA',),
 'FRAME_COUNT_WIDTH':('RESOURCE',),
}
CAPABILITIES=('FRAME_RASTER','ANIMATION_TIMING','ROLE_TRANSITION',
 'ATTACK_ACTIVATION','DAMAGE_FORCE','COLLISION','PAIN','FALL','RISE','DEATH',
 'DROP','AI','RNG','CADENCE','SPECIAL_EFFECT','MEDIA','DIALECT','STATS',
 'PALETTE','FRAME_MOVEMENT','RESOURCE','UNCLASSIFIED')

def classify(block):
    result=set(RULES.get(block['code'],('UNCLASSIFIED',)))
    role=block.get('animation_role')
    if role in ('pain','fall','rise','death'):
        result.add(role.upper())
    return result

def matrix(inputs):
    report={'schema':'actor-blocker-frequency-v1','count_unit':'distinct source models',
      'note':'overlapping requirements, not additive; zero does not certify a capability',
      'rules':RULES,'projects':{},'rows':{c:{} for c in CAPABILITIES}}
    for label,path in inputs:
        raw=Path(path).read_bytes();data=json.loads(raw)
        selected={c:set() for c in CAPABILITIES};provenance=[]
        for name,model in sorted(data['models'].items()):
            categories=model['actor_certification']['matrix']
            for category,state in categories.items():
                for block in state['blockers']:
                    caps=classify(block)
                    for cap in caps:selected[cap].add(name)
                    provenance.append(dict(model=name,category=category,
                        capabilities=sorted(caps),diagnostic=block))
        report['projects'][label]=dict(input=str(path),sha256=hashlib.sha256(raw).hexdigest(),
            project_id=data['project_id'],models=len(data['models']),
            blocked_models={c:sorted(v) for c,v in selected.items()},provenance=provenance)
        for c,v in selected.items():report['rows'][c][label]=len(v)
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project',nargs=2,action='append',required=True,metavar=('LABEL','REPORT'))
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=matrix(a.project);a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'blockers.json').write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
    labels=list(r['projects']);lines=['# Source-exact blocker frequency','',r['note'],'',
       '| Capability | '+' | '.join(labels)+' |','|---|'+'---:|'*len(labels)]
    for cap,row in r['rows'].items():lines.append('| '+cap+' | '+' | '.join(str(row[k]) for k in labels)+' |')
    (a.output/'blockers.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':main()
