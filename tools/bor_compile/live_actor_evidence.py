"""Attribute bounded CPU evidence without promoting whole-model certificates.

The selected lowering target remains fail-closed. A fixture can prove a
consumer and selected media without proving organic AI, raster equivalence,
the damage lifecycle, or an automatically publishable actor build.
"""
import copy
import json
from pathlib import Path

from compiler import digest


def attach_entity_evidence(report, proof, *, proof_sha256, runtime_sha256):
    if not proof.get('project_id') or proof['project_id']!=report.get('project_id'):
        raise ValueError('ACTOR_EVIDENCE_PROJECT_MISMATCH')
    if (proof.get('status')!='PASS' or proof.get('proof',{}).get('status')!='PASS'
            or proof.get('production_rom_sha256')!=runtime_sha256
            or not proof.get('production_artifacts_unchanged')):
        raise ValueError('STALE_OR_FAILED_ACTOR_RUNTIME_EVIDENCE')
    results=proof['proof']
    attached=[]
    for name,source_hash in proof['source_hashes'].items():
        model=report['models'].get(name.casefold())
        if model is None or model['ir']['source_sha256']!=source_hash:
            raise ValueError('ACTOR_EVIDENCE_SOURCE_MISMATCH: '+name)
        rows=[r for r in results['cases'] if r.get('actor','').casefold()==name.casefold()]
        loaders=[r for r in results.get('loaders',[]) if r.get('actor','').casefold()==name.casefold()]
        maps=[r for r in results.get('maps',[]) if r.get('actor','').casefold()==name.casefold()]
        timing=[r for r in results.get('timing',[]) if r.get('actor','').casefold()==name.casefold()]
        if not (rows or loaders or maps or timing): continue
        evidence=dict(status='PROVED_IN_CONTROLLED_FIXTURE',proof_sha256=proof_sha256,
            runtime_sha256=runtime_sha256,source_sha256=source_hash,cases=copy.deepcopy(rows),
            fixture_rom_sha256=proof.get('clone_rom_sha256'),fixture_msu_sha256=proof.get('msu_sha256'),
            consumer_sha256=proof.get('core_sha256'),
            loaders=copy.deepcopy(loaders),maps=copy.deepcopy(maps),timing=copy.deepcopy(timing),
            whole_actor_certificate=False,
            nonclaims={key:results[key] for key in ('organic_attack_selection','organic_spawn',
                'source_raster_alignment','full_damage_callback','full_actor_certification')},
            certification_effect='none; fixed-slot target and complete source requirements remain independent')
        model.setdefault('runtime_fixture_evidence',[]).append(evidence)
        attached.append(name)
    return dict(proof_sha256=proof_sha256,models=sorted(attached),
                whole_actor_certificates_added=0)


def load_entity_evidence(report,path,runtime_rom):
    data=Path(path).read_bytes()
    return attach_entity_evidence(report,json.loads(data),proof_sha256=digest(data),
                                  runtime_sha256=digest(Path(runtime_rom).read_bytes()))
