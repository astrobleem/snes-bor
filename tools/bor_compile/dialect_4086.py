"""Source IR from af23dc9c's loader, before any SNES runtime lowering.

Selecting this module is an explicit dialect choice, never filename detection.
Unlowered directives remain attached; an IR report is not runtime support.
"""
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path

ENGINE_COMMIT = 'af23dc9c2316bb7853bb266ccf40986aa9765aeb'
GAME_SPEED = 200
QUEUE_RESETS = frozenset(('spawn', 'wait', 'group', 'nojoin', 'canjoin',
    'shadowcolor', 'shadowalpha', 'light', 'scrollz', 'scrollx', 'blockade', 'setpalette'))
QUEUE_MODIFIERS = frozenset(('coords', 'health', '2phealth', '3phealth', '4phealth',
    '2pspawn', '3pspawn', '4pspawn', 'mp', 'score', 'name', 'alias', 'boss',
    'flip', 'map', 'item', 'weapon', 'spawnscript', '@script', 'dying', 'nolife',
    'aggression', 'itemhealth', 'itemalias', 'itemmap', 'credit', 'musicfade'))


def stage_queue(rows):
    """AT copies and clears next, including a zero initialized empty entry.

    A reset directive replaces an uncommitted entry. Retain that source evidence
    separately instead of inventing an engine rejection for it.
    """
    records, replaced, pending = [], [], None
    for row_index, row in enumerate(rows):
        name, values = row['directive'], row['values']
        # MUSIC followed physically by AT is queued; otherwise it is stage
        # initial music. document() excludes blanks/comments, so additionally
        # require adjacent physical lines, matching getNewLineStart().
        queued_music = (name == 'music' and row_index + 1 < len(rows)
                        and rows[row_index + 1]['directive'] == 'at'
                        and rows[row_index + 1]['line'] == row['line'] + 1)
        if queued_music:
            if pending is not None and not any(m['directive'] == 'musicfade' for m in pending['modifiers']):
                replaced.append(pending)
                pending = None
            if pending is None:
                pending = dict(kind='music', declaration=row, modifiers=[])
            else:
                pending['modifiers'].append(row)
            continue
        if name in QUEUE_RESETS:
            if pending is not None:
                replaced.append(pending)
            pending = dict(kind=name, declaration=row, modifiers=[])
            if name == 'group':
                minimum, maximum = (int(values[i]) if len(values) > i else 0 for i in range(2))
                pending['group_min'] = minimum if minimum >= 1 else 100
                pending['group_max'] = max(1, maximum)
        elif name == 'at':
            record = pending if pending is not None else dict(kind='zero_initialized', declaration=row, modifiers=[],
                constructor_cache_index=0, constructor_model_residency_required=True)
            record['at'] = row
            record['scroll_position'] = int(values[0]) if values else 0
            record['ordinal'] = len(records)
            records.append(record)
            pending = None
        elif name in QUEUE_MODIFIERS:
            if pending is None:
                pending = dict(kind='zero_base_with_modifiers', declaration=row, modifiers=[])
            pending['modifiers'].append(row)
    return dict(records=records, authored_records=len(records),
                source_spawns=sum(r['kind'] == 'spawn' for r in records),
                zero_initialized_records=sum(r['kind'] == 'zero_initialized' for r in records),
                replaced_before_commit=replaced, uncommitted_tail=pending,
                engine_commit=ENGINE_COMMIT, runtime_lowered=False)


def animation_frames(rows):
    """Expose loader timing, frame state, and frame-indexed @cmd events.

    Delay survives ANIM (the loader does not reset it). Offset/BBOX reset on
    ANIM and then persist between FRAMEs. SOUND is consumed by one FRAME.
    Other directives are retained verbatim and explicitly unlowered.
    """
    animations, current, delay = [], None, 0
    for row in rows:
        name, values = row['directive'], row['values']
        if name == 'anim':
            current = dict(role=' '.join(values), declaration=row, frames=[], events=[],
                           directives=[], duration_ticks=0, runtime_lowered=False)
            animations.append(current)
            offset, bbox, sound = [0, 0], [0, 0, 0, 0], None
        elif current is not None:
            current['directives'].append(row)
            if name == 'delay':
                delay = int(values[0]) if values else 0
            elif name == 'offset':
                offset = [int(values[i]) if len(values) > i else 0 for i in range(2)]
            elif name == 'bbox':
                bbox = [int(v) for v in values]
            elif name == 'sound':
                sound = row
            elif name == '@cmd':
                current['events'].append(dict(frame_index=len(current['frames']),
                    declaration=row, function=values[0] if values else '', arguments=values[1:],
                    runtime_lowered=False))
            elif name == 'frame':
                index = len(current['frames'])
                ticks = delay * GAME_SPEED // 100
                current['frames'].append(dict(index=index, declaration=row,
                    delay_centiseconds=delay, delay_ticks=ticks,
                    start_tick=current['duration_ticks'], offset=deepcopy(offset),
                    bbox=deepcopy(bbox), sound=sound))
                current['duration_ticks'] += ticks
                sound = None
    for animation in animations:
        for event in animation['events']:
            index = event['frame_index']
            event['start_tick'] = (animation['frames'][index]['start_tick']
                                   if index < len(animation['frames']) else None)
    return animations


def source_ir(source):
    from compiler import key
    from source_profile import document, discover
    documents = {k: document(source, name) for k, (name, _) in source.index.items() if k.endswith('.txt')}
    structure = discover(source, documents)
    stages = []
    for source_set in structure['sets']:
        for entry in source_set['entries']:
            if entry['kind'] == 'STAGE':
                doc = documents[key(entry['source_path'])]
                stages.append(dict(source_set_id=source_set['id'], source_path=doc['source_path'],
                    source_sha256=doc['sha256'], queue=stage_queue(doc['directives'])))
    models = []
    for model in structure['models']:
        doc = documents[key(model['source_path'])]
        models.append(dict(name=model['name'], source_path=doc['source_path'],
            source_sha256=doc['sha256'], properties=model['properties'],
            animations=animation_frames(doc['directives']), inline_scripts=doc['inline_scripts']))
    return dict(schema='BYOR_4086_SOURCE_IR_V1', dialect_authority=ENGINE_COMMIT,
        authority_selection='explicit caller choice, not archive engine authentication',
        source_sha256=hashlib.sha256(source.path.read_bytes()).hexdigest() if source.path.is_file() else None,
        sets=structure['sets'], stages=stages, models=models,
        queue_backend_bound=False, script_runtime_bound=False,
        scope='Loader timing and queue source IR only; retained directives and scripts require runtime lowering.')


def main():
    from compiler import Source
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = source_ir(Source(args.source))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(output=str(args.output), stages=len(report['stages']),
        models=len(report['models']), authored_records=sum(s['queue']['authored_records'] for s in report['stages']),
        source_spawns=sum(s['queue']['source_spawns'] for s in report['stages']), runtime_bound=False)))


if __name__ == '__main__':
    main()
