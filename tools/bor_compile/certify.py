"""Read-only, hash-pinned runtime binding audit. Never publishes content.

Accepted binary reproduction is deliberately NOT source certification.
Missing proof is a blocker, not permission to discard a source directive.
"""
from __future__ import annotations

import argparse
import ast
import io
import json
import re
import struct
from collections import Counter
from pathlib import Path

from compiler import (ROOT, Source, baseline, compile_project, digest, key,
                      model_catalog, presentation, stage)
from pack_msu_roster import pack_roster
import pack_msu_roster as physical_backend
from PIL import Image
from model_ir import parse_model, validate_model_ir
from analyze import validate_environment, target_limits

BASE = '0ef9a82bbd754aa979359df43d23821e48724ad8'
MSU_SHA = 'e7fe744af2928939f926a1c9121f6ac9e7f1d378533b95366e4afefd6bfe90af'
STAGE_REQUIREMENTS = ('source', 'directives', 'models', 'presentation',
                      'environment', 'scroll', 'queue', 'audio', 'campaign', 'layout')
SCENE_REQUIREMENTS = ('source', 'audio', 'animation_order', 'timing', 'media', 'layout')


def verdict(requirements, bindings, blockers):
    missing = [name for name in requirements if not bindings.get(name)]
    return dict(status='BLOCKED' if missing or blockers else 'CERTIFIED',
                bindings=bindings, missing_bindings=missing, blockers=blockers)


def table(text, name):
    match = re.search(rf'(?m)^{re.escape(name)}:\s*\.d[wb] ([^\r\n]+)', text)
    if not match:
        raise ValueError(f'missing generated table {name}')
    return [v.strip() for v in match[1].split(',')]


def constant(text, name):
    value = re.search(rf'(?m)^{re.escape(name)}\s*=\s*(\$[0-9A-Fa-f]+|\d+)', text)
    if not value:
        raise ValueError(f'missing constant {name}')
    return int(value[1][1:], 16) if value[1].startswith('$') else int(value[1])


def clips_from_msu(msu):
    start = msu.index(b'BORVID1\0')
    version, count, size = struct.unpack_from('<HHI', msu, start + 8)
    if version != 1 or size != count * 24:
        raise ValueError('invalid scene directory')
    result = []
    end = start + 16 + size
    for i in range(count):
        values = struct.unpack_from('<HHHHHHIII', msu, start + 16 + 24*i)
        entry = dict(zip(('scene_id', 'flags', 'width', 'height', 'fps_num',
                          'fps_den', 'frame_count', 'payload_offset', 'payload_size'), values))
        if entry['payload_offset'] != end or end + entry['payload_size'] > len(msu):
            raise ValueError('scene payload not contiguous/in bounds')
        end += entry['payload_size']
        entry['payload'] = msu[entry['payload_offset']:end]
        result.append(entry)
    if end != len(msu):
        raise ValueError('unaccounted MSU tail')
    return result


def queue_record(raw):
    trigger, x, y, facing, flags, hp, item, actor = struct.unpack('<HHBBBBBB', raw)
    return dict(trigger=trigger, x=x, y=y, facing=facing, kind=flags & 7,
                map=(flags >> 3) & 3, subtype_or_pickup=flags >> 5,
                hp_or_2p=hp, item_runtime_id=item, actor_runtime_id=actor)


def queue_provenance(config, git, queues, msu):
    directory = struct.unpack_from('<I', msu, 12)[0]
    rows = []
    for i, cfg in enumerate(config['STAGE_CONFIGS']):
        if cfg['family'] != 'bor-original':
            continue
        tracked = git(cfg['spawn'])
        offset, count = struct.unpack_from('<IH', msu, directory + 40*i + 32)
        accepted = msu[offset:offset+count*10]
        generated = queues[key(cfg['source_level'])]
        if tracked == accepted:
            continue
        differences = []
        for j in range(max(len(tracked), len(accepted)) // 10):
            a, b = tracked[j*10:j*10+10], accepted[j*10:j*10+10]
            if a != b:
                differences.append(dict(record=j, committed=queue_record(a) if len(a)==10 else None,
                                        accepted=queue_record(b) if len(b)==10 else None))
        rows.append(dict(source_stage=cfg['source_level'], tracked_path=cfg['spawn'],
                         committed_sha256=digest(tracked), compiler_sha256=digest(generated),
                         accepted_msu_sha256=digest(accepted),
                         worktree_sha256=digest((ROOT/cfg['spawn']).read_bytes()),
                         compiler_matches_accepted=generated == accepted,
                         worktree_matches_accepted=(ROOT/cfg['spawn']).read_bytes() == accepted,
                         classification='stale derived artifact still used as production build input',
                         provenance='build_rom.build_msu_assets reads SPAWN_TABLES from disk; '
                         'committed bytes differ, current corrected worktree bytes and source lowering '
                         'match the hash-pinned MSU. This proves input provenance, not who/when edited it.',
                         differences=differences))
    return rows


def shadow_layout(config, git, queues, msu):
    # Explicit legacy palette mode is the pinned binary reproduction target.
    # The complete image hash below remains authoritative even when the
    # packer also offers newer, separately validated environment encodings.
    path = 'tools/bor_converter/pack_msu_roster.py'
    spawns = [queues[key(s['source_level'])] if s['family']=='bor-original' else git(s['spawn'])
              for s in config['STAGE_CONFIGS']]
    build = git('build_rom.py').decode()
    vm_path = re.search(r'(?m)^VM_MODULE = "([^"]+)"', build)[1]
    image, sidecar = pack_roster(config['ROSTER_PREFIXES'],
        bgs=[(s['bg'], 'out/hud') for s in config['STAGE_CONFIGS']],
        fps=[s.get('frontpanel') for s in config['STAGE_CONFIGS']],
        spawns=spawns, vm_blob=git(vm_path), playable_count=msu[11],
        scene_video_entries=clips_from_msu(msu), extended_maps=False)
    scroll = git('tools/audio/stage_scroll_config.pasm').decode()
    audio = git('tools/audio/audio_music_ids.pasm').decode()
    vm = git('src/core/vm/vm_load.pasm').decode()
    counts = dict(config=len(config['STAGE_CONFIGS']), msu=msu[10],
                  linked=sidecar['bg_count'],
                  scroll=len(table(scroll,'Stage_ScrollDirectionMap')),
                  music=len(table(audio,'Music_StageTracks')),
                  music_declared=constant(audio,'Music_StageTrackCount'),
                  catalog_max=constant(git(path).decode(),'MAX_BGS'),
                  stage_count=constant(git('src/core/game_state.pasm').decode(),'STAGE_COUNT'))
    return dict(comparison='BYTE_IDENTICAL' if image==msu else 'MISMATCH',
                accepted_sha256=digest(msu), shadow_sha256=digest(image),
                counts=counts, counts_agree=len(set(counts.values()))==1,
                vm_offset=sidecar['vm_offset'],
                vm_constant=constant(vm,'VM_MSU_OFFSET'),
                vm_agrees=sidecar['vm_offset']==constant(vm,'VM_MSU_OFFSET'),
                total_size=len(image), catalog=sidecar['bgs'], scenes=sidecar['scene_video'],
                ownership='accepted encoded assets and pinned physical IDs; compiler queues; '
                'accepted pure packer recomputes all offsets. No production files written.')


def validate_model(source, model, accepted_id=None):
    """Generic contract inspection, never substitutes an actor or invents AI."""
    # S2 uses the same typed model path as independent PAK analysis. The legacy
    # JSON fields below remain compatibility output, never a second parser.
    typed=parse_model(source,model['source_path'],model['name'],'accepted-bor','historical-bor')
    typed_result=validate_model_ir(typed)
    from model_ir import MODEL_CAPABILITIES
    known = set(MODEL_CAPABILITIES)
    directives = list(source.lines(model['source_path']))
    unknown = [dict(line=d.line, directive=d.name, value=d.values) for d in directives if d.name not in known]
    entity = model['entity']
    frames, missing = [], []
    for role, anim in entity['animations'].items():
        for frame in anim['frames']:
            path = frame['gif']
            try:
                path = source.image_path(path)
                im = Image.open(io.BytesIO(source.read(path)))
                frames.append(dict(role=role, source_path=path, dimensions=list(im.size),
                                   offset=frame.get('offset'), attack=frame.get('attack'),
                                   move=frame.get('move'), delay=frame.get('delay')))
            except (ValueError, TypeError, AttributeError) as error:
                missing.append(str(error))
    blockers = []
    if unknown: blockers.append('unknown model directives (fail closed)')
    if missing: blockers.append('unresolved frame media')
    blockers.extend(sorted({d['reason'] for d in typed_result['diagnostics']}))
    if accepted_id is None:
        blockers += ['no accepted runtime identity', 'frame encoding/packed animation contract not validated',
                     'AI/movement/default-stat binding not validated']
        if entity['type'] == 'none':
            blockers.append('type none has no certified actor driver; must not become generic enemy')
        if entity['type'] == 'item':
            blockers.append('item effect requires a source-identity effect binding')
        if len(entity['remaps']) > 3:
            blockers.append('authored remaps exceed the stage queue two-bit map selector')
        if any(f['attack'] for f in frames if f['role'] not in ('attack1','attack2','attack3','attack4','special','freespecial','jumpattack','jumpattack2')):
            blockers.append('attack annotations outside attack roles require runtime dispatch validation')
    return dict(name=model['name'], source_path=model['source_path'], runtime_id=accepted_id,
                type=entity['type'], speed=entity['speed'], health=entity['health'],
                roles={r:len(a['frames']) for r,a in entity['animations'].items()},
                remaps=entity['remaps'], frames=frames, missing_media=missing,
                directives=[dict(line=d.line,directive=d.name,value=d.values) for d in directives],
                unknown_directives=unknown, blockers=blockers,
                model_ir_capability=typed_result,
                status='BLOCKED' if blockers else 'ACCEPTED_BINDING')


def audio_bindings(source, git):
    manifest = json.loads(git('tools/audio/audio_manifest.json'))
    bound = {}
    for family in manifest['families']:
        for a in family['assets']:
            if a['family']=='bor-original' and a.get('msu_track_id') is not None:
                p = source.resolve(a['source_path'])
                if digest(source.read(p)).lower() != a['source_hash'].lower():
                    raise ValueError(f'audio source hash differs: {p}')
                bound[key(p)] = a['msu_track_id']
    return bound


def accepted_clip_paths(git):
    """Legacy adapter only: read existing encoder identities, not new compiler policy."""
    rugal = ast.parse(git('tools/scene_video/convert_rugal.py').decode())
    ending = ast.parse(git('tools/scene_video/convert_ending.py').decode())
    def literal(tree, name):
        return next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
                    and any(isinstance(t,ast.Name) and t.id==name for t in n.targets))
    # Existing encoder ABI assigns Rugal clip 1 and ending clips starting at 2.
    # Assert the legacy numbering expression before relying on that adapter.
    text = git('tools/scene_video/convert_ending.py').decode()
    if 'index + 2 for index, name in enumerate(CLIPS)' not in text:
        raise ValueError('legacy clip-ID adapter needs review')
    return {1:key(literal(rugal,'SOURCE_PATH')),
            **{i+2:key('DATA/SCENES/'+name+'.GIF') for i,name in enumerate(literal(ending,'CLIPS'))}}


def candidate_layout(config, git, queues, msu, presentations, source_paths):
    """Pure temporary link of a source-selected scope, preserving all pinned slots.

    The legacy packer exposes capacity as a module constant. Override it only
    inside this serial shadow call and always restore it. This is not a ROM
    capacity change or proof of new source semantics.
    """
    cfgs=list(config['STAGE_CONFIGS'])
    ids={key(c['source_level']):i for i,c in enumerate(cfgs)}
    blockers=[]
    for path in source_paths:
        k=key(path)
        if k in ids: continue
        choices=presentations[k]['accepted_candidates']
        if k not in queues or not choices:
            blockers.append(dict(source_path=path,reason='queue or encoded presentation binding missing'))
            continue
        chosen=min(choices,key=lambda c:c['physical_id'])
        ids[k]=len(cfgs)
        cfgs.append(dict(family='bor-original',source_level=path,bg=chosen['bg'],frontpanel=chosen['frontpanel']))
    if blockers: return dict(status='BLOCKED',blockers=blockers)
    spawns=[queues[key(c['source_level'])] if c['family']=='bor-original' else git(c['spawn']) for c in cfgs]
    old_capacity=physical_backend.MAX_BGS
    try:
        physical_backend.MAX_BGS=len(cfgs)
        vm_path=re.search(r'(?m)^VM_MODULE = "([^"]+)"',git('build_rom.py').decode())[1]
        image,layout=pack_roster(config['ROSTER_PREFIXES'],bgs=[(c['bg'],'out/hud') for c in cfgs],
            fps=[c.get('frontpanel') for c in cfgs],spawns=spawns,vm_blob=git(vm_path),
            playable_count=msu[11],scene_video_entries=clips_from_msu(msu))
    finally:
        physical_backend.MAX_BGS=old_capacity
    return dict(status='LAYOUT_RESOLVED_NOT_SOURCE_CERTIFIED',stage_ids=ids,
                stage_count=len(cfgs),total_size=len(image),vm_offset=layout['vm_offset'],
                shadow_sha256=digest(image),catalog=layout['bgs'])


def certify(source, ref=BASE, msu_path=ROOT/'distribution/bor.msu', sha=MSU_SHA):
    config, git = baseline(ref)
    family=next(f for f in json.loads(git('tools/audio/audio_manifest.json'))['families'] if f['family']=='bor-original')
    if source.path.is_file():
        if digest(source.path.read_bytes())!=family['pak_hash']:
            raise ValueError('source PAK does not match accepted source/media provenance')
    else:
        original=Source(ROOT/family['pak'])
        if digest(original.path.read_bytes())!=family['pak_hash']:
            raise ValueError('accepted reference PAK hash differs')
        if any(source.read(p)!=original.read(p) for p,_ in original.index.values()):
            raise ValueError('extracted source differs from accepted source/media provenance')
    report, queues = compile_project(source, ref, msu_path, sha)
    msu = Path(msu_path).read_bytes()
    layout = shadow_layout(config, git, queues, msu)
    layout_ok = layout['comparison']=='BYTE_IDENTICAL' and layout['counts_agree'] and layout['vm_agrees']
    audio = audio_bindings(source,git)
    clip_paths = accepted_clip_paths(git)
    catalog = model_catalog(source)
    new = {key(m['source_path']) for m in report['new_models']}
    models = {n:validate_model(source,m,None if key(m['source_path']) in new else report['model_ids'][key(m['source_path'])])
              for n,m in catalog.items()}
    assets = {}
    for i,cfg in enumerate(config['STAGE_CONFIGS']):
        if cfg['family']=='bor-original':
            sig = presentation(source,stage(source,cfg['source_level']))
            assets.setdefault(sig,[]).append(dict(physical_id=i,bg=cfg['bg'],frontpanel=cfg.get('frontpanel'),source_path=cfg['source_level']))
    presentations = {}
    for k,ir in report['stages'].items():
        sig = presentation(source,stage(source,k))
        candidates = assets.get(sig,[])
        presentations[k] = dict(signature=sig, accepted_candidates=candidates,
                               dimensions=ir['dimensions'],panels=ir['panels'],order=ir['order'],
                               resolved=bool(candidates),
                               note='source/content signature discovers candidates; accepted encodings reused, not re-encoded')
    candidate_layouts={s['name']:candidate_layout(config,git,queues,msu,presentations,
        [e['source_path'] for e in s['entries'] if e['kind']=='STAGE']) for s in report['project']['sets']}
    # Compare independently discovered content equivalence against legacy reuse.
    golden_cfg=[s for s in config['STAGE_CONFIGS'] if s['family']=='bor-original']
    reuse_equal=all(
        (presentations[key(a['source_level'])]['signature']==presentations[key(b['source_level'])]['signature']) ==
        ((a['bg'],a.get('frontpanel'))==(b['bg'],b.get('frontpanel')))
        for a in golden_cfg for b in golden_cfg)
    music_text=git('tools/audio/audio_music_ids.pasm').decode()
    scroll_text=git('tools/audio/stage_scroll_config.pasm').decode()
    tracks=list(map(int,table(music_text,'Music_StageTracks')))
    boss_tracks=list(map(int,table(music_text,'Music_StageBossTracks')))
    directions=table(scroll_text,'Stage_ScrollDirectionMap')
    mirrors=list(map(int,table(scroll_text,'Stage_MirrorMap')))
    golden_bindings=[]
    for i,cfg in enumerate(config['STAGE_CONFIGS']):
        if cfg['family']!='bor-original': continue
        ir=report['stages'][key(cfg['source_level'])]
        mirror=[int(d['values'][0]) for d in ir['directives'] if d['name']=='mirror']
        golden_bindings.append(dict(source_path=ir['source_path'],physical_id=i,
            stage_track=audio.get(key(ir['music'])),boss_track=audio.get(key(ir['bossmusic'])) if ir['bossmusic'] else 0,
            audio_matches=audio.get(key(ir['music']))==tracks[i] and (audio.get(key(ir['bossmusic'])) if ir['bossmusic'] else 0)==boss_tracks[i],
            scroll=ir['scroll'],scroll_matches=directions[i]=='STAGE_SCROLL_'+ir['scroll'].upper(),
            mirror_matches=(mirror[-1] if mirror else 0)==mirrors[i]))
    scene_text = git('src/generated/scene_sequence_meta.pasm').decode()
    clips = {c['scene_id']:c for c in clips_from_msu(msu)}
    scenes = {}
    for k,ir in report['scenes'].items():
        configs = [(i,c) for i,c in enumerate(config['SCENE_CONFIGS']) if key(c['source_scene'])==k]
        blockers = list(ir['diagnostics'])
        binding = dict(source=not blockers,audio=key(ir['music']) in audio,
                       animation_order=False,timing=False,media=False,layout=False)
        bound_clips = []
        if configs:
            i,cfg = configs[0]; prefix=f'SceneSequence_Record{i}_'
            ids = list(map(int,table(scene_text,prefix+'ClipIds')))
            timing_ok = len(ids)==len(ir['animations'])
            order_ok = timing_ok and all(clip_paths.get(cid)==key(a['source_path']) for cid,a in zip(ids,ir['animations']))
            for clip_id,anim in zip(ids,ir['animations']):
                c=clips[clip_id]; payload=c['payload']; n=c['frame_count']
                delays = list(struct.unpack_from('<'+'H'*n,payload,4+4*n)) if c['flags'] & 1 else [1000*c['fps_den']/c['fps_num']]*n
                timing_ok &= delays==anim['delays_ms'] and struct.unpack_from('<I',payload)[0]==n
                # Validate all frame pointers/IDs, not merely total duration.
                for f in range(n):
                    pos=struct.unpack_from('<I',payload,4+4*f)[0]
                    timing_ok &= pos+6<=len(payload) and struct.unpack_from('<H',payload,pos)[0]==f
                bound_clips.append(dict(clip_id=clip_id,source_path=anim['source_path'],
                                        source_sha256=digest(source.read(anim['source_path'])),
                                        payload_sha256=digest(payload),frames=n,delays_ms=delays))
            binding.update(audio=audio.get(key(ir['music']))==constant(scene_text,prefix+'AudioTrack') and ir['repeat']==constant(scene_text,prefix+'AudioRepeat'),
                           animation_order=order_ok,timing=bool(timing_ok),media=order_ok,layout=layout_ok)
        else:
            blockers.append(dict(reason='no accepted encoded scene/media directory binding; source timing available'))
        scenes[k] = dict(**verdict(SCENE_REQUIREMENTS,binding,blockers),source=ir,clips=bound_clips,
                         source_timing_known=all(a['delays_ms'] and all(d>0 for d in a['delays_ms']) for a in ir['animations']),
                         provenance='ordered clips bound through committed accepted scene metadata; no pixel re-encoding claim')
    entries=[]
    queue_capacity=target_limits()['queue_records']
    for row in report['entries']:
        k=key(row['source_path'])
        if row['kind']=='SCENE':
            result=scenes[k]
        else:
            ir=report['stages'][k]
            blockers=[b for b in row['blockers'] if b['directive'] not in ('final-link','mirror')]
            env=validate_environment(stage(source,row['source_path']))
            blockers.extend(env['diagnostics'])
            queue_count=len(queues[k])//10 if k in queues else row['packed_queue_count']
            if queue_count is not None and queue_count>queue_capacity:
                blockers.append(dict(source_file=row['source_path'],directive='queue_capacity',value=queue_count,
                                     reason=f'exceeds {queue_capacity}-record WRAM allocation; Spawn_Init copies the stage count without a capacity clamp'))
            # No pretend fix for an actual lossy backend: keep source Z/map/alias explicit.
            for b in blockers:
                if b['directive']=='map': b['reason']='runtime SPAWN_MAP_MASK=$03 and backend clamp0..3; higher authored map is not representable by this queue'
                if b['directive']=='alias': b['reason']='parser retains display alias; accepted ten-byte queue has no alias binding (spawn_parse documents unused)'
            names={n.lower() for q in ir['queue'] for n in (q['character'],q['item']) if n}
            for n in sorted(names):
                if n in models and models[n]['runtime_id'] is not None and models[n]['blockers']:
                    blockers.append(dict(source_file=models[n]['source_path'],directive='model-contract',value=n,
                                         reason='accepted model binding has unverified source directives/media; see model diagnostics'))
            binding=dict(source=not ir['diagnostics'],directives=not ir['diagnostics'],
                         models=all(n in models and models[n]['status']=='ACCEPTED_BINDING' for n in names),
                         presentation=presentations[k]['resolved'],
                         environment=not any(b['directive'] in ('coords','alias','map','water','endhole','blocked','rock') for b in blockers),
                         scroll=ir['scroll'] in ('right','left','down'),queue=k in queues,
                         audio=all(not p or key(p) in audio for p in (ir['music'],ir['bossmusic'])) and
                         (not row['next_after'] or key(config['BOR_COMPLETION_MUSIC']['source_path']) in audio),
                         campaign=True,layout=layout_ok and (k in {key(c['source_level']) for c in config['STAGE_CONFIGS']} or
                             k in candidate_layouts[row['set_name']].get('stage_ids',{})))
            result=verdict(STAGE_REQUIREMENTS,binding,blockers)
        entries.append({k:row[k] for k in ('set_name','set_id','ordinal','kind','source_path','next_after','authored_queue_count','packed_queue_count')} | result)
    golden_keys={key(x['source_path']) for x in report['golden']}
    golden_stages=[e for e in entries if key(e['source_path']) in golden_keys]
    per_set={s['name']:dict(Counter(e['status'] for e in entries if e['set_name']==s['name'])) for s in report['project']['sets']}
    bonus=next(e for e in report['entries'] if e['set_name']=='Bonus' and e['kind']=='STAGE')
    extra=report['stages'][key(bonus['source_path'])]
    return dict(schema=1,mode='shadow-certification',baseline=ref,source_pak_sha256=family['pak_hash'],
                definition=dict(stage=STAGE_REQUIREMENTS,scene=SCENE_REQUIREMENTS,
                                rule='CERTIFIED requires every binding and zero blockers; missing proof is BLOCKED'),
                stale_queues=queue_provenance(config,git,queues,msu),layout=layout,candidate_layouts=candidate_layouts,
                golden_queue_reproduction=report['golden_production_pass'],
                golden_stage_status=dict(Counter(e['status'] for e in golden_stages)),
                golden_scene_status={k:v['status'] for k,v in scenes.items() if k in {key(c['source_scene']) for c in config['SCENE_CONFIGS']}},
                golden_campaign_boundaries=report['coverage'],
                golden_campaign_matches=report['golden_progression_pass'],
                golden_presentation_reuse_matches=reuse_equal,golden_runtime_tables=golden_bindings,
                entries=entries,per_set=per_set,presentations=presentations,audio=audio,
                models=models,scenes=scenes,
                extra=dict(ir=extra,model_counts=bonus['model_counts'],
                           authored_records=len(extra['queue']),
                           kinds=dict(Counter(q['kind'] for q in extra['queue'])),
                           packed_records=None,reason='no certified Crab/Lobster binding; no fake queue emitted'),
                full_normal_certified=all(e['status']=='CERTIFIED' for e in entries if e['set_name']==report['project']['sets'][1]['name']),
                production_changed=False)


def markdown(report):
    lines=['# BOR shadow certification', '',
           'Binary reproduction and source certification are separate gates. Missing bindings remain blockers.', '',
           f"Layout: {report['layout']['comparison']}; VM ${report['layout']['vm_offset']:06X}; {report['layout']['total_size']} bytes.",
           f"Golden stages: {report['golden_stage_status']}", f"Golden scenes: {report['golden_scene_status']}",
           f"Complete Normal certified: {report['full_normal_certified']}", '',
           '## Stale derived build inputs', '']
    for q in report['stale_queues']:
        lines += [f"### {q['source_stage']}", '', f"`{q['tracked_path']}`", '',
                  f"- Committed: `{q['committed_sha256']}`",
                  f"- Compiler: `{q['compiler_sha256']}`",
                  f"- Accepted MSU: `{q['accepted_msu_sha256']}`",
                  f"- Changed records: {len(q['differences'])}; worktree matches MSU: {q['worktree_matches_accepted']}",
                  '', q['provenance'], '']
    lines += ['## Entry certification', '', '| Set | Ordinal | Source | Status | Blockers |', '|---|---:|---|---|---|']
    for e in report['entries']:
        reasons=sorted({b.get('reason',str(b)) for b in e['blockers']})+e['missing_bindings']
        lines.append(f"| {e['set_name']} | {e['ordinal']} | {e['source_path']} | {e['status']} | {'; '.join(reasons)} |")
    lines += ['', 'Full decoded record differences, source model frames, environment IR, bindings and layout offsets are in certification.json.',
              '', 'No production ownership migration or content enablement is authorized by this report.']
    return '\n'.join(lines)+'\n'


def evidence_summary(report):
    """Compact commit-friendly evidence; full IR stays in the reproducible report."""
    result={k:report[k] for k in ('schema','baseline','source_pak_sha256','definition',
        'stale_queues','golden_queue_reproduction','golden_stage_status','golden_scene_status',
        'golden_campaign_boundaries','golden_campaign_matches','golden_presentation_reuse_matches',
        'golden_runtime_tables','per_set','full_normal_certified','production_changed')}
    result['layout']={k:v for k,v in report['layout'].items() if k not in ('catalog','scenes')}
    result['candidate_layouts']={s:{k:v for k,v in r.items() if k!='catalog'} for s,r in report['candidate_layouts'].items()}
    result['entries']=[]
    for entry in report['entries']:
        e={k:v for k,v in entry.items() if k!='blockers'}
        grouped={}
        for b in entry['blockers']:
            reason=b.get('reason',str(b));grouped.setdefault(reason,[]).append({k:v for k,v in b.items() if k not in ('reason','status')})
        e['blockers']=grouped;result['entries'].append(e)
    result['models']={n:{k:v for k,v in m.items() if k not in ('frames','directives')}
                      for n,m in report['models'].items() if m['blockers']}
    result['extra']={k:v for k,v in report['extra'].items() if k!='ir'}
    result['sewer']=report['scenes']['data/scenes/sewer.txt']
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source');p.add_argument('--out',type=Path,required=True)
    p.add_argument('--baseline',default=BASE);p.add_argument('--msu',type=Path,default=ROOT/'distribution/bor.msu')
    p.add_argument('--sha256',default=MSU_SHA)
    p.add_argument('--evidence',type=Path,help='optional compact JSON evidence file, not runtime data')
    p.add_argument('--require-golden',action='store_true',help='exit 2 unless every golden entry is CERTIFIED')
    args=p.parse_args()
    report=certify(Source(args.source),args.baseline,args.msu,args.sha256)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'certification.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    (args.out/'certification.md').write_text(markdown(report),encoding='utf-8')
    if args.evidence:
        args.evidence.parent.mkdir(parents=True,exist_ok=True)
        args.evidence.write_text(json.dumps(evidence_summary(report),indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('golden_stage_status','golden_scene_status','per_set','full_normal_certified')},indent=2))
    if report['layout']['comparison']!='BYTE_IDENTICAL': raise SystemExit('accepted layout reproduction failed')
    if args.require_golden and (report['golden_stage_status'].get('BLOCKED',0) or
                               any(v!='CERTIFIED' for v in report['golden_scene_status'].values())):
        raise SystemExit(2)


if __name__=='__main__': main()
