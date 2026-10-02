"""S5 reproducible actor shadow report and optional existing-encoder probe.

No output is installed into production. Encoding success is reported
independently of full actor certification, including omitted packed roles.
"""
import argparse
import contextlib
import io
import json
import re
from collections import Counter
from pathlib import Path

from compiler import ROOT, Source, baseline, digest, key
from analyze import analyze, compact_report, golden_actor_comparison
from actor_lowering import allocate_ids
from lowering_policy import Profile, apply_policy, certify_policy, require_certified


def compare_raster_roles(accepted, regenerated, slots, info, alternate_count):
    """Compare actual fixed-slot payloads, including legacy repeated roles.

    This is raster evidence only. An accepted synthetic role is recorded as
    such, never introduced into the source model or certified as source AI.
    """
    order=('idle','walk','attack','fall','rise','attack2','jump','jumpattack',
           'jumpattack2','special','attack3','attack4','grab','slide','riseattack',
           'grabattack','freespecial','get','waiting')
    def split(blob, counts):
        position=32; result={}
        for role in order:
            size=counts.get(role,0)*768
            result[role]=blob[position:position+size]
            if len(result[role])!=size: raise ValueError('ACTOR_ROLE_PAYLOAD_TRUNCATED')
            position+=size
        if len(blob)-position!=alternate_count*32:
            raise ValueError('ACTOR_PALETTE_TAIL_SIZE_MISMATCH')
        return result,blob[position:]
    old,old_maps=split(accepted,{r:s['frame_count'] for r,s in slots.items()})
    new,new_maps=split(regenerated,{r:info.get(r+'_frame_count',0) for r in order})
    rows={}
    for role,payload in old.items():
        if not payload: continue
        matches=[r for r,b in new.items() if b and b==payload]
        rows[role]=dict(status='BYTE_IDENTICAL' if payload==new[role] else
            'ACCEPTED_REPEATED_ROLE' if matches and not new[role] else 'MISMATCH',
            source_raster_roles=matches,bytes=len(payload))
    return dict(base_palette_identical=accepted[:32]==regenerated[:32],
                alternate_palettes_identical=old_maps==new_maps,roles=rows,
                source_behavior_certified=False)


def link_compatibility(report, ref):
    cfg, _ = baseline(ref)
    pins = {};reserved=[];models=report['models']
    for i, config in enumerate(cfg['ROSTER_CONFIGS']):
        if config['family'] != 'bor-original':
            reserved.append(i);continue
        path=key(config['source_character'])
        candidates=[m for m in models.values() if
                    key(m['ir']['source_path']).rsplit('/',1)[0]==path or
                    key(m['ir']['source_path']).rsplit('.',1)[0]==path]
        if len(candidates)!=1:
            raise ValueError(f'accepted actor {i} has no unique source binding')
        pins[tuple(candidates[0]['ir']['identity'])]=i
    ids=allocate_ids([m['ir']['identity'] for m in models.values()],pins,reserved)
    for m in models.values():
        m['actor_lowering']['runtime_id']=ids[tuple(m['ir']['identity'])]
    return dict(pinned=len(pins),reserved=reserved,assigned=len(ids))


def encode_probe(source_path, model, folder):
    from convert_character import convert_character
    from pack_msu_roster import pack_character_blob
    folder.mkdir(parents=True,exist_ok=True)
    prefix=str(folder/'actor')
    if model['ir']['dialect']!='historical-bor':
        raise ValueError('DIALECT_BINDING_REQUIRED: raster adapter uses historical defaults')
    source_assets=Source(source_path)
    with contextlib.redirect_stdout(io.StringIO()):
        _, manifest_path=convert_character(str(source_path),model['ir']['source_path'],prefix,
                                          image_resolver=source_assets.image_path)
        manifest=json.loads(Path(manifest_path).read_text())
        defaults=[]
        for animation in manifest['animations']:
            source_animation=next(a for a in model['actor_lowering']['animations'] if a['role']==animation['name'].casefold())
            path=Path(animation['dir'])/'manifest.json'
            frames=json.loads(path.read_text())
            if len(frames['frames'])!=len(source_animation['frames']):
                raise ValueError('ENCODER_FRAME_COUNT_MISMATCH')
            for i,(encoded,source_frame) in enumerate(zip(frames['frames'],source_animation['frames'])):
                if encoded.get('delay') is None:
                    encoded['delay']=source_frame['delay']
                    defaults.append(dict(role=animation['name'],frame=i,delay=source_frame['delay']))
            path.write_text(json.dumps(frames,indent=2)+'\n',encoding='utf-8')
        blob, info=pack_character_blob(prefix,extended_maps=True)
    manifest=json.loads(Path(manifest_path).read_text())
    frames=[]
    for source_animation in model['actor_lowering']['animations']:
        match=next((a for a in manifest['animations'] if a['name'].casefold()==source_animation['role']),None)
        frames.append(dict(role=source_animation['role'],source_count=len(source_animation['frames']),
                           encoded_count=None if match is None else match['frames']))
    counts_match=all(x['source_count']==x['encoded_count'] for x in frames)
    (folder/'actor.bin').write_bytes(blob)
    return dict(status='ENCODED' if counts_match else 'MISMATCH',bytes=len(blob),
                sha256=digest(blob),palette_count=len(manifest.get('remap_palettes',[])),
                frames=frames,packed_info={k:v for k,v in info.items() if k!='prefix'},
                source_default_bindings=defaults,
                runtime_certified=False,
                note='existing raster adapter; conversion includes roles the fixed-slot packer may omit')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('--dialect',default='unspecified',choices=['unspecified','historical-bor'])
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--baseline')
    parser.add_argument('--accepted-rom',type=Path,default=ROOT/'distribution/bor.sfc')
    parser.add_argument('--accepted-msu',type=Path,default=ROOT/'distribution/bor.msu')
    parser.add_argument('--encode',action='append',default=[],help='source model declaration; shadow only')
    parser.add_argument('--encode-accepted',action='store_true',help='shadow-encode every explicitly bound accepted actor and compare its MSU payload')
    parser.add_argument('--evidence',type=Path)
    parser.add_argument('--entity-evidence',type=Path,action='append',default=[],
                        help='bounded current-ROM entity proofs; never whole-model certification')
    parser.add_argument('--runtime-rom',type=Path,default=ROOT/'distribution/bor.sfc')
    parser.add_argument('--catalog-model',action='append',default=[],
                        help='explicit analysis-only descriptor catalog scope; not a certified actor build')
    parser.add_argument('--catalog-address',type=lambda value:int(value,0),default=0x1F8000)
    choice=parser.add_mutually_exclusive_group()
    choice.add_argument('--profile',choices=[p.value for p in Profile],default=Profile.SOURCE_EXACT.value)
    choice.add_argument('--source-exact',dest='profile',action='store_const',const=Profile.SOURCE_EXACT.value)
    parser.add_argument('--require-certified',action='store_true',help='fail instead of emitting usable build inputs for blocked models')
    parser.add_argument('--analysis-only',action='store_true',help='allow report-only success with BLOCKED entries; never certify or emit a build')
    args=parser.parse_args()
    if args.analysis_only and args.require_certified:
        parser.error('--analysis-only and --require-certified are mutually exclusive')
    if args.encode_accepted and not args.baseline:
        parser.error('--encode-accepted requires an explicit accepted baseline')
    if args.catalog_model and (not args.analysis_only or args.profile!=Profile.SOURCE_EXACT.value):
        parser.error('--catalog-model is an explicit SOURCE_EXACT analysis-only artifact, never a compatibility fallback')
    report=analyze(Source(args.source),args.dialect)
    accepted={}
    if args.baseline:
        if args.dialect!='historical-bor':
            raise ValueError('original actor compatibility pins require historical-bor profile')
        report['actor_link']=link_compatibility(report,args.baseline)
        report['golden_actors']=golden_actor_comparison(report,args.baseline)
        _,git=baseline(args.baseline)
        # S4+ current-target proof, not the legacy S1 three-palette oracle.
        counts=[int(value) for row in re.findall(r'(?m)^\s*\.db\s+([^;\r\n]+)',
                git('src/generated/stage_environment_maps.pasm').decode())
                for value in row.split(',')]
        if len(counts)!=256: raise ValueError('MODEL_MAP_COUNT_TABLE_MISMATCH')
        for row in report['golden_actors']:
            row['packed_maps']=counts[row['runtime_id']]
            row['packed_map_provenance']=args.baseline+':src/generated/stage_environment_maps.pasm'
        from accepted_actor_policy import bindings
        accepted=bindings(report,args.baseline,args.accepted_msu.read_bytes(),args.accepted_rom.read_bytes())
    if args.profile==Profile.ACCEPTED_COMPAT.value and not args.baseline:
        parser.error('ACCEPTED_COMPAT requires an explicit accepted baseline')
    report['selected_profile']=args.profile
    report['analysis_only']=args.analysis_only
    for model in report['models'].values():
        source=model['actor_lowering']
        exact=apply_policy(source)
        exact['category_status']=model['actor_certification']['matrix']
        exact['blockers']=sorted({d['code']+': '+d['reason'] for category in exact['category_status'].values() for d in category['blockers']})
        exact=certify_policy(exact,source_categories={
            category:'SOURCE_CERTIFIED' if value['status']=='CERTIFIED' else 'BLOCKED'
            for category,value in exact['category_status'].items()})
        compat=apply_policy(source,Profile.ACCEPTED_COMPAT,accepted=accepted.get(tuple(source['source_identity'])))
        if tuple(source['source_identity']) in accepted:
            compat=certify_policy(compat,equivalence_proof=dict(passed=True,
                source_fingerprint=compat['source_fingerprint'],baseline=args.baseline,
                method='identity delegation to unchanged accepted ROM/MSU, verified against committed runtime evidence'))
        model['lowering_profiles']={Profile.SOURCE_EXACT.value:exact,Profile.ACCEPTED_COMPAT.value:compat}
    args.output.mkdir(parents=True,exist_ok=True)
    if args.catalog_model:
        from actor_catalog import generate_catalog
        selected=[report['models'][name]['actor_lowering'] for name in sorted({n.casefold() for n in args.catalog_model})]
        pins={tuple(m['source_identity']):m['runtime_id'] for m in selected}
        blob,manifest=generate_catalog(selected,base_address=args.catalog_address,pinned=pins)
        manifest.update(publication=False,certification='BLOCKED_UNTIL_ALL_ACTOR_REQUIREMENTS_PASS')
        (args.output/'actor_catalog.bin').write_bytes(blob)
        (args.output/'actor_catalog.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        report['descriptor_catalog']=manifest
    encode_names={name.casefold() for name in args.encode}
    if args.encode_accepted:
        encode_names.update(name for name,m in report['models'].items()
                            if tuple(m['actor_lowering']['source_identity']) in accepted)
    for name in sorted(encode_names):
        model=report['models'][name]
        try:
            model['encoding_probe']=encode_probe(args.source,model,args.output/('actor_'+str(model['candidate_id'])))
            binding=accepted.get(tuple(model['actor_lowering']['source_identity']))
            if binding:
                start=binding['contract']['blob_offset']
                size=model['encoding_probe']['bytes']
                accepted_size=binding['contract']['blob_size']
                payload=args.accepted_msu.read_bytes()[start:start+accepted_size]
                model['encoding_probe']['accepted_payload_comparison']=dict(
                    status='BYTE_IDENTICAL' if len(payload)==size and digest(payload)==model['encoding_probe']['sha256'] else 'MISMATCH',
                    accepted_sha256=digest(payload),offset=start,accepted_bytes=accepted_size,compared_bytes=len(payload),
                    scope='re-encoded raster payload only; not source behavior certification',
                    role_deltas={role:dict(accepted=slot,
                        regenerated=dict(frame_count=model['encoding_probe']['packed_info'].get(role+'_frame_count',0),
                                         delay=model['encoding_probe']['packed_info'].get(role+'_delay',0)))
                        for role,slot in binding['contract']['runtime_slots'].items()
                        if slot!={'frame_count':model['encoding_probe']['packed_info'].get(role+'_frame_count',0),
                                  'delay':model['encoding_probe']['packed_info'].get(role+'_delay',0)}})
                model['encoding_probe']['accepted_payload_comparison']['raster_roles']=compare_raster_roles(
                    payload,(args.output/('actor_'+str(model['candidate_id']))/'actor.bin').read_bytes(),
                    binding['contract']['runtime_slots'],model['encoding_probe']['packed_info'],
                    binding['contract']['palettes']['alternate_count'])
        except (ValueError,OSError,KeyError,AssertionError,TypeError) as error:
            model['encoding_probe']=dict(status='BLOCKED',reason=str(error),runtime_certified=False)
    from live_actor_evidence import load_entity_evidence
    report['runtime_fixture_evidence']=[load_entity_evidence(report,p,args.runtime_rom) for p in args.entity_evidence]
    summary=dict(models=len(report['models']),
        certified=sum(m['actor_certification']['status']=='CERTIFIED' for m in report['models'].values()),
        candidate_status=dict(Counter(m['capability']['status'] for m in report['models'].values())),
        roles=dict(sorted(Counter(a['role'] for m in report['models'].values() for a in m['ir']['animations']).items())),
        category_blocked=dict(Counter(c for m in report['models'].values() for c,v in m['actor_certification']['matrix'].items() if v['status']=='BLOCKED')))
    report['actor_summary']=summary
    summary['profiles']={p.value:dict(Counter(m['lowering_profiles'][p.value]['status'] for m in report['models'].values())) for p in Profile}
    summary['encoding_comparison']=dict(Counter(
        m['encoding_probe'].get('accepted_payload_comparison',{}).get('status',m['encoding_probe']['status'])
        for m in report['models'].values() if 'encoding_probe' in m))
    inventory=[dict(source_identity=m['actor_lowering']['source_identity'],
                    runtime_id=m['actor_lowering']['runtime_id'],**row)
               for m in report['models'].values()
               for row in m['lowering_profiles'][Profile.ACCEPTED_COMPAT.value]['adaptations']]
    summary['compatibility_inventory']=dict(
        policy_records=len(inventory),
        categories=dict(sorted(Counter(r['category'] for r in inventory).items())),
        note='Explicit policy bindings, not a count of distinct demonstrated behavioral differences; inactive roles may not exercise every policy.')
    (args.output/'compatibility-adapters.json').write_text(
        json.dumps(dict(baseline=args.baseline,records=inventory),indent=2,sort_keys=True)+'\n',encoding='utf-8')
    (args.output/'actors.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    compact=compact_report(report);compact['actor_summary']=summary
    compact['runtime_fixture_evidence']=report['runtime_fixture_evidence']
    if 'descriptor_catalog' in report:
        compact['descriptor_catalog']={k:v for k,v in report['descriptor_catalog'].items() if k!='entries'}
    if 'actor_link' in report: compact['actor_link']=report['actor_link']
    for name,m in report['models'].items():
        compact['models'][name]['shadow_runtime_id']=m['actor_lowering']['runtime_id']
        if 'encoding_probe' in m: compact['models'][name]['encoding_probe']=m['encoding_probe']
        if 'runtime_fixture_evidence' in m:
            compact['models'][name]['runtime_fixture_evidence']=m['runtime_fixture_evidence']
        compact['models'][name]['lowering_profiles']={p:{k:v for k,v in data.items() if k!='target'} for p,data in m['lowering_profiles'].items()}
    compact['selected_profile']=args.profile
    if args.evidence:
        args.evidence.parent.mkdir(parents=True,exist_ok=True)
        args.evidence.write_text(json.dumps(compact,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    lines=['# Actor runtime certification','',
           'Shadow only. Descriptor/reference/encoding PASS is not a live actor PASS.','',
           'Selected lowering policy: '+args.profile,
           'Compatibility delegates the immutable accepted build; it is never source certification.','',
           '| Model | ID | SOURCE_EXACT | ACCEPTED_COMPAT | Blocked source categories |','|---|---:|---|---|---|']
    for name,m in sorted(report['models'].items()):
        categories=', '.join(c for c,v in m['actor_certification']['matrix'].items() if v['status']=='BLOCKED')
        profiles=m['lowering_profiles']
        lines.append(f"| {name} | {m['actor_lowering']['runtime_id']} | {profiles['SOURCE_EXACT']['status']} | {profiles['ACCEPTED_COMPAT']['status']} | {categories} |")
    (args.output/'actors.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2))
    if not args.analysis_only:
        for model in report['models'].values():
            require_certified(model['lowering_profiles'][args.profile])


if __name__=='__main__': main()
