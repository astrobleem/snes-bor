"""S4 strict recertification: retain model/media blockers, verify actual build queues.

The baseline certificate remains an immutable legacy oracle. This report
checks the environment-v1 candidate against it, never relabels the old binary.
"""
import argparse
import copy
import json
import struct
from collections import Counter
from pathlib import Path

from compiler import ROOT, Source, baseline, key, stage, digest
from regenerate_queues import generate_environment_queues
from analyze import validate_environment
from certify import clips_from_msu, verdict, STAGE_REQUIREMENTS

ENV = {'map','alias','coords','water','blocked','endhole','rock','mirror'}
RESOLVED_MODEL_MAP_FINDINGS = {
    'actor packer retains only three alternate palettes; queue map selector is two bits',
    'authored remaps exceed the stage queue two-bit map selector',
}


def certify(before, analysis, source, accepted_msu, candidate_msu, runtime):
    current=candidate_msu.read_bytes();old=accepted_msu.read_bytes()
    if runtime['msu_sha256']!=digest(current): raise ValueError('STALE_RUNTIME_MSU')
    if runtime['rom_sha256']!=digest((ROOT/'distribution/bor.sfc').read_bytes()): raise ValueError('STALE_RUNTIME_ROM')
    if not runtime.get('passed'): raise ValueError('ENVIRONMENT_RUNTIME_NOT_PASSED')
    cfg,_=baseline('c474617ee150b28b5b23677d89a9010b087dfa78')
    candidates=generate_environment_queues(source,accepted_msu)
    directory=struct.unpack_from('<I',current,12)[0]
    olddir=struct.unpack_from('<I',old,12)[0]
    queues=[]
    golden=set()
    for physical,s in enumerate(cfg['STAGE_CONFIGS']):
        off,count=struct.unpack_from('<IH',current,directory+physical*40+32)
        if s['family']!='bor-original': continue
        data=current[off:off+count*10]
        if data!=candidates[s['spawn']]: raise ValueError(f'QUEUE_CANDIDATE_MISMATCH: {s["source_level"]}')
        oldoff,oldcount=struct.unpack_from('<IH',old,olddir+physical*40+32)
        if count!=oldcount: raise ValueError('QUEUE_COUNT_CHANGED')
        queues.append(dict(physical=physical,source_path=s['source_level'],count=count,
                           candidate_sha256=digest(data),legacy_sha256=digest(old[oldoff:oldoff+count*10])))
        golden.add(key(s['source_level']))
    a,b=clips_from_msu(old),clips_from_msu(current)
    if len(a)!=len(b) or any(x['payload']!=y['payload'] for x,y in zip(a,b)):
        raise ValueError('SCENE_MEDIA_CHANGED')
    entries=[]
    for original in before['entries']:
        row=copy.deepcopy(original)
        if row['kind']=='STAGE':
            ir=stage(source,row['source_path'])
            env=validate_environment(ir,analysis['models'],'historical-bor')
            blockers=[x for x in row['blockers'] if x.get('directive') not in ENV|{'model-contract'}]
            blockers+=env['diagnostics']
            names={n.casefold() for q in ir.queue for n in (q.character,q.item) if n}
            models_bound=True
            for name in sorted(names):
                model=before['models'].get(name)
                if model is None or model['runtime_id'] is None:
                    models_bound=False
                    blockers.append(dict(source_file=model['source_path'] if model else row['source_path'],
                                         directive='model-contract',value=name,reason='no accepted runtime actor/media binding'))
                else:
                    # Only obsolete map-width findings are resolved. Every
                    # other prior actor proof obligation stays load-bearing.
                    remaining=[x for x in model['blockers'] if x not in RESOLVED_MODEL_MAP_FINDINGS]
                    remaining+=sorted({d['reason'] for d in analysis['models'][name]['capability']['diagnostics']})
                    if remaining:
                        models_bound=False
                        blockers.append(dict(source_file=model['source_path'],directive='model-contract',value=name,reason=sorted(set(remaining))))
            bindings=row['bindings']
            bindings['models']=models_bound
            bindings['environment']=not env['diagnostics']
            bindings['queue']=key(row['source_path']) in golden
            if key(row['source_path']) not in golden:
                # Old layout-only dry run is not a new palette/model link.
                bindings['layout']=False
                blockers.append(dict(source_file=row['source_path'],directive='shadow-link',reason='unpublished environment-v1 full-entry link not emitted'))
            row.update(verdict(STAGE_REQUIREMENTS,bindings,blockers))
        entries.append(row)
    return dict(mode='strict-environment-recertification',production_enabled=False,
                rom_sha256=runtime['rom_sha256'],msu_sha256=digest(current),
                msu_bytes_before=len(old),msu_bytes_after=len(current),scene_payloads_unchanged=True,
                golden_queues=queues,golden_before=before['golden_stage_status'],
                golden_after=dict(Counter(e['status'] for e in entries if key(e['source_path']) in golden)),
                per_set={s:dict(Counter(e['status'] for e in entries if e['set_name']==s)) for s in sorted({e['set_name'] for e in entries})},
                entries=entries,full_normal_certified=all(e['status']=='CERTIFIED' for e in entries if e['set_name']=='Normal'))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before',type=Path,required=True);p.add_argument('--analysis',type=Path,required=True)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--accepted-msu',type=Path,required=True)
    p.add_argument('--runtime',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    report=certify(json.loads(args.before.read_text()),json.loads(args.analysis.read_text()),Source(args.source),
                   args.accepted_msu,ROOT/'distribution/bor.msu',json.loads(args.runtime.read_text()))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:report[k] for k in ('golden_before','golden_after','per_set','full_normal_certified')},indent=2))


if __name__=='__main__': main()
