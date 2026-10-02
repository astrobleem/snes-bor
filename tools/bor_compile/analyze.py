"""One real PAK/tree in, one isolated compatibility report out.

This analysis backend never labels unencoded actors or unresolved dialects as
certified ROM inputs. It emits source IR even when compilation is blocked.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from compiler import ROOT, Source, key, digest, stage, scene, baseline
from queue_abi import RECORD_SIZE, TARGET_CAPACITY, QueueCapacityError, check_count
from model_ir import (parse_model, validate_model_ir,
                      DIRECT, ADAPTER, UNSUPPORTED, UNKNOWN, MISSING)
from environment_capabilities import matrix
from stage_environment_abi import MAP_MAX, PALETTE_BYTES
from actor_media_abi import ACTOR_MEDIA_ADDRESS_BITS


@dataclass
class EnvironmentIR:
    source_path: str
    scroll: str
    geometry: dict
    holes: list
    endholes: list
    water: list
    blocked: list
    rocking: list
    mirrors: list
    spawn_altitudes: list
    display_aliases: list


ENVIRONMENT_CAPABILITIES={
    'direction':(ADAPTER,'Stage_ScrollDirectionMap and source-axis queue transform'),
    'hole':(ADAPTER,'hole queue control; Stage_Hole source geometry adapter'),
    'mirror':(ADAPTER,'Stage_MirrorMap'),
    'alias':(UNSUPPORTED,'spawn-instance alias ID/name is preserved separately from model; general opponent-name HUD remains unbound'),
    'coords_z':(UNSUPPORTED,'signed altitude requires source driver binding; fixed-base emitters have a Q16.16 adapter, other spawn altitude remains unbound'),
    'water':(UNSUPPORTED,'texture wave renderer (wave parameter min 2) is not bound'),
    'rock':(UNSUPPORTED,'time-driven rocking vertical display offset is not bound'),
    'blocked':(UNSUPPORTED,'depth-dependent exit x clamp is not bound'),
    'endhole':(UNSUPPORTED,'depth-dependent exit pit predicate is not bound'),
    'map':(ADAPTER,'environment ABI v1: byte map selector, full palette emission and per-model base fallback'),
}


def scoped_id(source):
    # Canonical content identity also works for extracted trees, without root-path dependence.
    inventory=[(k,digest(source.read(p))) for k,(p,_) in sorted(source.index.items())]
    return digest(json.dumps(inventory,separators=(',',':')).encode())


def inventory_project(source):
    sets=[];diagnostics=[];directives=list(source.lines('DATA/LEVELS.TXT'))
    for d in directives:
        v=d.values
        try:
            if d.name=='set' and len(v)==1:
                sets.append(dict(name=v[0],source_id=len(sets),ifcomplete=0,entries=[]))
            elif d.name in ('file','scene') and len(v)==1 and sets:
                # Keep missing authored entries in the inventory; the entry
                # analyzer will report the unresolved resource independently.
                try: resolved=source.resolve(v[0])
                except ValueError: resolved=v[0]
                sets[-1]['entries'].append(dict(kind='STAGE' if d.name=='file' else 'SCENE',
                    source_path=resolved,authored_path=v[0],next_after=False))
            elif d.name=='next' and not v and sets and sets[-1]['entries'] and not sets[-1]['entries'][-1]['next_after']:
                sets[-1]['entries'][-1]['next_after']=True
            elif d.name=='ifcomplete' and len(v)==1 and sets and int(v[0])>=0:
                sets[-1]['ifcomplete']=int(v[0])
            else:
                diagnostics.append(dict(source_file=source.resolve('DATA/LEVELS.TXT'),line=d.line,
                    directive=d.name,value=v,category=UNKNOWN,reason='uninterpreted progression/global control; retained, scope not guessed'))
        except ValueError as error:
            diagnostics.append(dict(source_file='DATA/LEVELS.TXT',line=d.line,directive=d.name,value=v,category=UNKNOWN,reason=str(error)))
    return dict(sets=sets,directives=[asdict(d) for d in directives],diagnostics=diagnostics)


def environment(ir):
    e=ir.environment
    return EnvironmentIR(ir.source_path,ir.scroll,dict(dimensions=ir.dimensions,panels=ir.panels,order=ir.order),
        e.get('hole',[]),e.get('endhole',[]),e.get('water',[]),e.get('blocked',[]),e.get('rock',[]),e.get('mirror',[]),
        [dict(queue=i,altitude=q.altitude,depth=q.coords[1]) for i,q in enumerate(ir.queue) if q.altitude is not None],
        [dict(queue=i,model=q.character,display_alias=q.alias) for i,q in enumerate(ir.queue) if q.alias is not None])


def validate_environment(ir, models=None, dialect='historical-bor'):
    diagnostics=[];bindings=[]
    if len(ir.environment.get('hole',[]))>2:
        diagnostics.append(dict(source_file=ir.source_path,directive='hole',value=ir.environment['hole'],
                                category=UNSUPPORTED,reason='HOLE_CAPACITY_EXCEEDED: runtime binds at most two hole positions'))
    current_model=None
    for d in ir.directives:
        if d.name=='spawn': current_model=d.values[0].casefold() if d.values else None
        feature='coords_z' if d.name=='coords' and len(d.values)==3 else d.name
        if feature not in ENVIRONMENT_CAPABILITIES: continue
        category,reason=ENVIRONMENT_CAPABILITIES[feature]
        try:
            if feature=='map':
                int(d.values[0])
                if dialect != 'historical-bor':
                    category,reason=UNKNOWN,'map ABI supports 0..255; source dialect map/default semantics are not certified'
            if feature=='coords_z' and int(d.values[2])==0: category,reason=ADAPTER,'zero altitude matches default only'
            elif feature=='coords_z' and models is not None and dialect=='historical-bor':
                # Associate source directive with its actual queue entry, not a
                # stage/model-name correspondence table.
                model=models.get(current_model,{})
                stats=model.get('ir',{}).get('stats',{})
                if stats.get('type')=='steamer':
                    category,reason=ADAPTER,'signed fixed base Q16.16, independent from jump/throw Z; child inherits base'
                    lowered=round(int(d.values[2])*4*65536/5)
                    if not -(1<<31)<=lowered<(1<<31):
                        category,reason=UNSUPPORTED,'ALTITUDE_TARGET_RANGE: signed Q16.16 base overflow'
        except (ValueError,IndexError): category,reason=UNKNOWN,'malformed environment value retained'
        row=dict(source_file=ir.source_path,line=d.line,directive=d.name,value=d.values,category=category,reason=reason)
        (bindings if category in (ADAPTER,DIRECT) else diagnostics).append(row)
    return dict(bindings=bindings,diagnostics=diagnostics)


def target_limits():
    pack=(ROOT/'tools/bor_converter/pack_msu_roster.py').read_text()
    def number(text,name): return int(re.search(rf'(?m)^{name}\s*=\s*(\d+)',text)[1])
    return dict(queue_records=TARGET_CAPACITY,queue_record_bytes=RECORD_SIZE,
        actor_media_pointer_bits=ACTOR_MEDIA_ADDRESS_BITS,
        actor_media_end_exclusive=1<<ACTOR_MEDIA_ADDRESS_BITS,
        current_actor_catalog_capacity=number(pack,'MAX_CHARACTERS'),actor_id_hardware_limit=255,
        current_stage_catalog_capacity=number(pack,'MAX_BGS'),stage_id_hardware_limit=255,
        frame_bytes=number(pack,'ANIM_FRAME_BYTES'),frame_count_limit=255,
        actor_canvas=[32,48],alternate_palettes=MAP_MAX,bytes_per_palette=PALETTE_BYTES,stage_hole_positions=2,
        scene_canvas=[256,192],scene_tile_limit=384,
        rom_bytes=None,final_msu_bytes=None,
        note='null footprints require successful encoding/link, not an invented estimate; catalog maxima are current build settings')


def analyze(source, dialect='unspecified'):
    project_id=scoped_id(source);project=inventory_project(source)
    models={};global_diagnostics=[];model_lines=list(source.lines('DATA/MODELS.TXT'))
    for d in model_lines:
        if d.name not in ('load','know') or len(d.values)!=2:
            global_diagnostics.append(dict(source_file='DATA/MODELS.TXT',line=d.line,directive=d.name,value=d.values,
                                           category=UNKNOWN,reason='uninterpreted model/global control'))
            continue
        name,path=d.values
        try:
            if name.casefold() in models: raise ValueError('duplicate model declaration')
            ir=parse_model(source,path,name,project_id,dialect)
            models[name.casefold()]=dict(ir=asdict(ir),capability=validate_model_ir(ir))
            from actor_lowering import lower_model, certify_current
            lowered=lower_model(ir)
            models[name.casefold()]['actor_lowering']=lowered
            models[name.casefold()]['actor_certification']=certify_current(ir,lowered)
        except (ValueError,OSError) as error:
            global_diagnostics.append(dict(source_file='DATA/MODELS.TXT',line=d.line,directive=d.name,value=d.values,category=MISSING,reason=str(error)))
    # Project-local IDs are a link plan, not accepted runtime IDs or emitted actors.
    paths=sorted({key(m['ir']['source_path']) for m in models.values()})
    for m in models.values():
        m['candidate_id']=paths.index(key(m['ir']['source_path']))
        m['actor_lowering']['runtime_id']=m['candidate_id']
        # Allocation is project-local shadow identity, not runtime publication.
        m['actor_certification']['matrix']['IDENTITY']=dict(status='CERTIFIED',blockers=[])
    for m in models.values():
        for dep in m['ir']['dependencies']:
            if dep.casefold() not in models:
                m['capability']['diagnostics'].append(dict(category=MISSING,source_file=m['ir']['source_path'],directive='load',value=dep,reason='unresolved project-local model dependency'))
                m['capability']['status']='BLOCKED'
    # Dependency closure is project-scoped and cycle-safe. Retain root causes
    # without expanding the same diagnostic recursively on each pass.
    def dependencies(name, visited):
        if name in visited or name not in models: return set()
        visited.add(name)
        result={d.casefold() for d in models[name]['ir']['dependencies']}
        for dep in tuple(result): result.update(dependencies(dep,visited))
        return result
    initially_blocked={n for n,m in models.items() if m['capability']['status']=='BLOCKED'}
    for name,m in models.items():
        blocked=sorted(dependencies(name,set()) & initially_blocked - {name})
        if blocked:
            m['capability']['diagnostics'].append(dict(category=UNSUPPORTED,source_file=m['ir']['source_path'],
                directive='load',value=blocked,reason='project-local dependency has explicit compatibility blockers; inspect its model diagnostics'))
            m['capability']['status']='BLOCKED'
        m['capability']['classifications']=sorted({d['category'] for d in m['capability']['diagnostics']} or {ADAPTER})
    limits=target_limits();entries=[];stage_inventory=Counter();scene_inventory=Counter()
    seen_stages={};seen_scenes={}
    for s in project['sets']:
        for ordinal,e in enumerate(s['entries']):
            path=e['source_path'];k=key(path)
            diagnostics=[];metadata={}
            try:
                if e['kind']=='STAGE':
                    ir=stage(source,path);seen_stages[k]=asdict(ir)
                    env=validate_environment(ir,models,dialect);stage_inventory.update(d.name for d in ir.directives)
                    diagnostics+=ir.diagnostics+env['diagnostics']
                    required=sorted({n.casefold() for q in ir.queue for n in (q.character,q.item) if n})
                    for name in required:
                        if name not in models:
                            diagnostics.append(dict(category=MISSING,source_file=path,directive='spawn',value=name,reason='model is not declared in this project'))
                        elif models[name]['capability']['status']=='BLOCKED':
                            diagnostics.extend(models[name]['capability']['diagnostics'])
                    packed_candidate=len(ir.queue)+len(ir.environment.get('hole',[]))
                    if packed_candidate>limits['queue_records']:
                        try:
                            check_count(packed_candidate,project=project_id,set_name=s['name'],stage=ordinal,source_path=path)
                        except QueueCapacityError as error:
                            diagnostics.append(dict(category=UNSUPPORTED,source_file=path,directive='queue_capacity',value=packed_candidate,
                                reason='QUEUE_CAPACITY_EXCEEDED',details=error.diagnostic))
                    metadata=dict(environment=asdict(environment(ir)),environment_bindings=env['bindings'],
                                  authored_queue_count=len(ir.queue),packed_queue_candidate_count=packed_candidate,
                                  queue_inventory_complete=not bool(ir.diagnostics),
                                  packed_queue_count=None,required_models=required,
                                  max_group_requirement=max((q.group_max for q in ir.queue),default=0),
                                  simultaneous_actor_verdict='requires scheduler capacity proof; group bound is not total spawns')
                else:
                    ir=scene(source,path);seen_scenes[k]=asdict(ir);scene_inventory.update(d.name for d in ir.directives)
                    diagnostics+=ir.diagnostics
                    metadata=dict(scene=asdict(ir))
            except (ValueError,OSError) as error:
                diagnostics.append(dict(category=MISSING,source_file=path,directive='resource',reason=str(error)))
            # Unknown controls are global blockers, not silently scoped away.
            controls=project['diagnostics']+global_diagnostics
            blocked=bool(diagnostics or controls)
            entries.append(dict(**e,set_name=s['name'],ordinal=ordinal,
                status='BLOCKED',capability='BLOCKED_SOURCE_OR_RUNTIME' if blocked else 'LOWERABLE_WITH_ADAPTER',
                diagnostics=diagnostics,global_control_blockers=len(controls),
                link_blocker='project-local media/actor encoding and final build backend required',**metadata))
    resources=dict(limits=limits,source_model_count=len(models),source_stage_count=len(seen_stages),
        source_scene_count=len(seen_scenes),max_model_maps=max((len(m['ir']['remaps']) for m in models.values()),default=0),
        unique_frame_assets=len({f['asset_sha256'] for m in models.values() for a in m['ir']['animations'] for f in a['frames']}),
        required_audio=sorted({d['values'][0] for ir in [*seen_stages.values(),*seen_scenes.values()] for d in ir['directives'] if d['name'] in ('music','bossmusic') and d['values']}),
        actor_catalog_exceeded=len(paths)>limits['current_actor_catalog_capacity'],
        actor_id_limit_exceeded=len(paths)>limits['actor_id_hardware_limit'])
    return dict(schema=1,mode='analysis-only',project_id=project_id,input_name=source.path.name,dialect=dialect,
        environment_capabilities=matrix(seen_stages.values(),dialect,models),
        project=project,model_controls=global_diagnostics,models=models,entries=entries,resources=resources,
        inventory=dict(levels=dict(Counter(d['name'] for d in project['directives'])),
                       model=dict(Counter(d['name'] for m in models.values() for d in m['ir']['directives'])),
                       stage=dict(stage_inventory),scene=dict(scene_inventory)),
        summary=dict(sets=len(project['sets']),stage_entries=sum(e['kind']=='STAGE' for e in entries),
                     scene_entries=sum(e['kind']=='SCENE' for e in entries),source_models=len(models),
                     certified=0,adapter_candidates=sum(e['capability']=='LOWERABLE_WITH_ADAPTER' for e in entries),
                     blocked_source_or_runtime=sum(e['capability']=='BLOCKED_SOURCE_OR_RUNTIME' for e in entries)),
        publication=dict(enabled=False,reason='dry run; model IR is not an executable actor artifact'))


def golden_actor_comparison(report,ref):
    """Accepted catalog is an adapter/oracle, never the generic identity allocator."""
    cfg,git=baseline(ref);rows=[]
    by_path={key(m['ir']['source_path']):m for m in report['models'].values()}
    for i,c in enumerate(cfg['ROSTER_CONFIGS']):
        if c['family']!='bor-original': continue
        candidates=[m for p,m in by_path.items() if p.rsplit('/',1)[0]==key(c['source_character']) or p.rsplit('.',1)[0]==key(c['source_character'])]
        if len(candidates)!=1:
            rows.append(dict(runtime_id=i,status='BLOCKED',reason='accepted identity has no unique declared source model'));continue
        m=candidates[0];ir=m['ir'];prefix=c['converted_prefix']
        moveset=json.loads(git(prefix+'_moveset.json'));diffs=[];animations=[]
        for a in ir['animations']:
            packed=next((x for x in moveset['animations'] if x['name'].casefold()==a['role']),None)
            if packed is None:
                diffs.append(dict(role=a['role'],field='role',reason='source animation absent from accepted moveset'));continue
            manifest=json.loads(git(packed['dir']+'/manifest.json'))
            field_diffs=[]
            for j,(f,p) in enumerate(zip(a['frames'],manifest['frames'])):
                for field in ('offset','bbox','delay','move'):
                    expected=f['state'].get(field);actual=p.get(field)
                    # Keep default-vs-omitted distinguishable; no silent normalization.
                    if expected!=actual: field_diffs.append(dict(frame=j,field=field,source=expected,accepted=actual))
                attack=f['state'].get('attack');expected=None if attack is None else attack['box']+[attack['force'],attack['drop']]
                if expected!=p.get('attack'): field_diffs.append(dict(frame=j,field='attack',source=expected,accepted=p.get('attack')))
            animations.append(dict(role=a['role'],source_frames=len(a['frames']),accepted_frames=len(manifest['frames']),
                frame_count_matches=len(a['frames'])==len(manifest['frames']),differences=field_diffs,
                frame_reference_proof='accepted manifest omits original GIF paths; source paths retained in ModelIR, pixel re-encode not claimed'))
        rows.append(dict(runtime_id=i,source_identity=ir['identity'],source_path=ir['source_path'],
            source_stats=ir['stats'],source_behavior=m['capability']['behavior'],accepted_role_map=moveset['roles'],
            source_maps=len(ir['remaps']),converted_maps=len(moveset.get('remap_palettes',[])),packed_maps=min(3,len(moveset.get('remap_palettes',[]))),
            animations=animations,role_differences=diffs,capability=m['capability']['status'],
            stat_binding='no complete base-stat/AI contract in accepted actor directory; not certified by frame equivalence'))
    return rows


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source');p.add_argument('--output',type=Path,required=True)
    p.add_argument('--dialect',choices=['historical-bor','unspecified'],default='unspecified')
    p.add_argument('--golden-baseline');p.add_argument('--evidence',type=Path);args=p.parse_args()
    report=analyze(Source(args.source),args.dialect)
    if args.golden_baseline: report['golden_actors']=golden_actor_comparison(report,args.golden_baseline)
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'compatibility.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    if args.evidence:
        args.evidence.parent.mkdir(parents=True,exist_ok=True)
        args.evidence.write_text(json.dumps(compact_report(report),indent=2,sort_keys=True)+'\n',encoding='utf-8')
    lines=['# PAK compatibility analysis','',json.dumps(report['summary'],sort_keys=True),'',
        'No runtime publication. LOWERABLE_WITH_ADAPTER is not CERTIFIED. Unknown dialect controls fail closed.','',
        '| Set | Ordinal | Source | Capability |','|---|---:|---|---|']
    lines += [f"| {e['set_name']} | {e['ordinal']} | {e['source_path']} | {e['capability']} |" for e in report['entries']]
    lines += ['','## Model compatibility','',
              '| Model | Candidate ID (not runtime) | Status | Reasons |','|---|---:|---|---|']
    for name,m in report['models'].items():
        reasons='; '.join(sorted({d['reason'] for d in m['capability']['diagnostics']})) or 'encoding and binding proof required'
        lines.append(f"| {name} | {m['candidate_id']} | {m['capability']['status']} | {reasons} |")
    lines += ['','## Resource limits','',json.dumps(report['resources'],sort_keys=True),'',
              'Exact diagnostics, source directives, model/frame IR and resource requirements are in compatibility.json.']
    lines += ['', '## Environment capabilities', '', '| Feature | Source seen | Compiler | Runtime | Certified |',
              '|---|---|---|---|---|']
    lines += [f"| {name} | {v['source_seen']} | {v['compiler']} | {v['runtime']} | {v['certified']} |"
              for name,v in report['environment_capabilities'].items()]
    (args.output/'compatibility.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(report['summary'],indent=2))


def compact_report(report):
    """Commit-sized evidence. Complete lossless IR stays in the output tree."""
    result={k:report[k] for k in ('schema','mode','project_id','input_name','dialect','summary','resources','inventory','publication','environment_capabilities')}
    result['sets']=[{k:v for k,v in s.items() if k!='entries'} for s in report['project']['sets']]
    result['global_controls']=report['project']['diagnostics']+report['model_controls']
    result['models']={}
    for name,m in report['models'].items():
        ir=m['ir'];cap=m['capability']
        result['models'][name]=dict(identity=ir['identity'],candidate_id=m['candidate_id'],source_path=ir['source_path'],
            stats=ir['stats'],remap_count=len(ir['remaps']),roles={a['role']:len(a['frames']) for a in ir['animations']},
            status=cap['status'],behavior=cap['behavior'],
            diagnostics=sorted({d['reason'] for d in cap['diagnostics']}),
            actor_certification=m['actor_certification'])
    result['entries']=[]
    for e in report['entries']:
        row={k:v for k,v in e.items() if k not in ('diagnostics','environment','environment_bindings','scene')}
        row['diagnostics']=sorted({d['reason'] for d in e['diagnostics']})
        result['entries'].append(row)
    if 'golden_actors' in report:
        result['golden_actors']=[]
        for a in report['golden_actors']:
            row={k:v for k,v in a.items() if k!='animations'}
            row['animation_comparison']=[dict(role=x['role'],source_frames=x['source_frames'],
                accepted_frames=x['accepted_frames'],frame_count_matches=x['frame_count_matches'],
                difference_fields=dict(Counter(d['field'] for d in x['differences'])),
                frame_reference_proof=x['frame_reference_proof']) for x in a.get('animations',[])]
            result['golden_actors'].append(row)
    return result


if __name__=='__main__': main()
