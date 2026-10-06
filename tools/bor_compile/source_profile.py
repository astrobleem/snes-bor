"""Evidence-first foreign PACK inspection. Recognition is never runtime support.

This reader deliberately does not feed an unfamiliar dialect to the historical
parser. Every text directive, script block and asset remains discoverable even
when a later build needs a new lowering or a hardware presentation decision.
"""
from collections import Counter
import hashlib
import io
import json
import math
from pathlib import Path
import re

import numpy as np
from PIL import Image

from compiler import Source, CAPABILITIES, key
from model_ir import MODEL_CAPABILITIES
from source_palette import model_palettes


def sha(data):
    return hashlib.sha256(data).hexdigest()


def resolve_profile(source_hash):
    """Identity/policy bindings only. Routes and rosters never live here."""
    catalog = json.loads(Path(__file__).with_name('source_profiles.json').read_text(encoding='utf-8'))
    matches = [p for p in catalog['profiles'] if p['sha256'] == source_hash]
    if len(matches) > 1:
        raise ValueError('SOURCE_PROFILE_AMBIGUOUS: ' + source_hash)
    return matches[0] if matches else None


def document(source, path):
    """Keep physical source lines; don't interpret C statements as directives."""
    rows, blocks = [], []
    block = None
    for line, raw in enumerate(source.read(path).decode('latin1').splitlines(), 1):
        if block is not None:
            if raw.strip().lower().startswith('@end_script'):
                block['end_line'] = line
                blocks.append(block)
                block = None
            else:
                block['text'].append(raw)
            continue
        tokens = raw.split('#', 1)[0].split()
        if not tokens:
            continue
        row = dict(source_path=source.resolve(path), line=line,
                   directive=tokens[0].lower(), values=tokens[1:])
        rows.append(row)
        if tokens[0].lower() == '@script':
            block = dict(source_path=row['source_path'], line=line, text=[])
    if block is not None:
        block['unterminated'] = True
        blocks.append(block)
    return dict(source_path=source.resolve(path), sha256=sha(source.read(path)),
                directives=rows, inline_scripts=blocks)


def image_requirement(source, path, *, model_palette=None):
    raw = source.read(path)
    with Image.open(io.BytesIO(raw)) as image:
        image.load()
        report = dict(source_path=source.resolve(path), sha256=sha(raw),
                      bytes=len(raw), dimensions=list(image.size), mode=image.mode,
                      frames=getattr(image, 'n_frames', 1))
        delays = []
        for frame_number in range(report['frames']):
            image.seek(frame_number)
            delays.append(image.info.get('duration', 0))
        report['frame_delays_ms'] = delays
        report['declared_duration_ms'] = sum(delays)
        image.seek(0)
        if image.mode == 'P':
            indices = np.asarray(image)
            palette = list(model_palette if model_palette is not None else image.getpalette() or [])
            palette += [0] * (768 - len(palette))
            lut = np.array([(palette[i*3] >> 3) | ((palette[i*3+1] >> 3) << 5)
                            | ((palette[i*3+2] >> 3) << 10) for i in range(256)])
            # BOR indexed actor convention; background/scene use is separate.
            mask = indices != 0
            colors = lut[indices]
            report['nonzero_source_indices'] = len(np.unique(indices[mask]))
            report['actor_transparency_assumption'] = 'indexed zero transparent'
        else:
            pixels = np.asarray(image.convert('RGBA')).astype(np.uint16)
            mask = pixels[:, :, 3] != 0
            colors = ((pixels[:, :, 0] >> 3) | ((pixels[:, :, 1] >> 3) << 5)
                      | ((pixels[:, :, 2] >> 3) << 10))
            report['actor_transparency_assumption'] = 'image alpha channel'
        report['nontransparent_rgb555_colors'] = len(np.unique(colors[mask]))
        line_counts = [len(np.unique(colors[y][mask[y]])) for y in range(image.height)]
        report['maximum_scanline_rgb555_colors'] = max(line_counts, default=0)
        report['minimum_static_obj_palettes'] = math.ceil(report['nontransparent_rgb555_colors']/15)
        occupied = [(x, y) for y in range(0, image.height, 8)
                    for x in range(0, image.width, 8) if mask[y:y+8, x:x+8].any()]
        report['occupied_8x8_cells'] = len(occupied)
        report['uncompressed_occupied_4bpp_bytes'] = len(occupied)*32
        report['capacity_scope'] = 'requirements only; not packed OAM/VRAM admission'
        if occupied:
            ys, xs = np.nonzero(mask)
            report['opaque_bounds'] = [int(xs.min()), int(ys.min()), int(xs.max()+1), int(ys.max()+1)]
    return report


def discover(source, documents):
    """Derive registries and routes without a hand-authored game manifest."""
    video = documents.get('data/video.txt', {}).get('directives', [])
    overrides = {r['directive']: r['values'] for r in video if r['values']}
    levels = 'data/' + overrides.get('levels', ['levels.txt'])[0]
    registry = 'data/' + overrides.get('models', ['models.txt'])[0]
    errors, sets, global_settings = [], [], []
    current = None
    for row in documents.get(key(levels), {}).get('directives', []):
        n, v = row['directive'], row['values']
        if n == 'set' and v:
            current = dict(id=len(sets), name=' '.join(v), ifcomplete=0,
                           entries=[], settings=[], declaration=row)
            sets.append(current)
        elif n in ('file', 'scene') and v and current is not None:
            try:
                path = source.resolve(v[0])
            except ValueError as e:
                path = v[0]
                errors.append(dict(**row, code='MISSING_SOURCE_ASSET', reason=str(e)))
            current['entries'].append(dict(ordinal=len(current['entries']),
                kind='STAGE' if n == 'file' else 'SCENE', source_path=path,
                next_after=False, declaration=row))
        elif n == 'next' and current and current['entries']:
            current['entries'][-1]['next_after'] = True
        elif n == 'ifcomplete' and current and v:
            try:
                current['ifcomplete'] = int(v[0])
            except ValueError:
                errors.append(dict(**row, code='INVALID_COMPLETION_THRESHOLD'))
        else:
            (global_settings if current is None else current['settings']).append(row)
    models = []
    for row in documents.get(key(registry), {}).get('directives', []):
        if row['directive'] not in ('load', 'know'):
            continue
        if len(row['values']) != 2:
            errors.append(dict(**row, code='MODEL_DECLARATION_SCHEMA'))
            continue
        name, path = row['values']
        doc = documents.get(key(path))
        if doc is None:
            errors.append(dict(**row, code='MODEL_SOURCE_MISSING'))
            continue
        top, animations, current_anim = {}, [], None
        for d in doc['directives']:
            if d['directive'] == 'anim':
                current_anim = dict(role=' '.join(d['values']), line=d['line'], frames=[], directives=[])
                animations.append(current_anim)
            elif current_anim is None:
                top.setdefault(d['directive'], []).append(d)
            else:
                current_anim['directives'].append(d)
                if d['directive'] == 'frame' and d['values']:
                    current_anim['frames'].append(d)
        def scalar(n, default=None):
            values = top.get(n, [{}])[-1].get('values', [])
            return values[0] if values else default
        models.append(dict(registry_order=len(models), declaration=name,
            source_path=doc['source_path'], registry_mode=row['directive'], registry_location=row,
            name=scalar('name', name), type=scalar('type'), subtype=scalar('subtype'),
            secret=scalar('secret', '0'), properties=top, animations=animations,
            maps=top.get('remap', []) + top.get('alternatepal', []),
            scripts=top.get('animationscript', []), inline_scripts=doc['inline_scripts']))
    return dict(levels_path=levels, models_path=registry, video=overrides,
                global_settings=global_settings, sets=sets, models=models, diagnostics=errors)


def classify(domain, row, exercised):
    n, v = row['directive'], row['values']
    status, nearest, resolution = 'UNKNOWN_SEMANTICS', None, 'Establish dialect semantics from engine or supplied script before lowering.'
    if domain in ('levels', 'stage', 'scene') and n in CAPABILITIES[domain]:
        status, nearest = 'SUPPORTED_ACCEPTED_COMPAT', 'compiler.' + domain
        resolution = 'Validate values and bind real source assets through the shared lowering; native evidence remains required.'
        if domain == 'levels':
            status = 'SUPPORTED'
        if n in ('music', 'bossmusic', 'animation', 'background', 'frontpanel', 'panel'):
            status = 'BINDING_REQUIRED'
        if domain == 'stage' and n == 'bossmusic' and len(v) == 2:
            status = 'SOURCE_DIALECT_VARIANT'
            resolution = 'Preserve the authored music start offset; extend shared audio metadata and seek transport.'
    elif domain == 'registry' and n in ('load', 'know'):
        status, nearest, resolution = 'SUPPORTED', 'source registry', 'Derive loaded and lazily known models; preserve source order.'
    elif domain == 'model' and n in MODEL_CAPABILITIES:
        status, nearest = 'SUPPORTED_ACCEPTED_COMPAT', 'model_ir.MODEL_CAPABILITIES.' + n
        if MODEL_CAPABILITIES[n] == 'UNSUPPORTED_RUNTIME_FEATURE':
            status = 'GENERIC_CAPABILITY_MISSING'
        if n in ('frame', 'icon', 'diesound', 'sound', 'remap'):
            status = 'BINDING_REQUIRED'
        resolution = 'Validate this dialect and all arguments; recognized keywords do not certify its behavior.'
        if (n == 'attack' and len(v) > 7) or (n == 'loop' and len(v) > 1):
            status = 'SOURCE_DIALECT_VARIANT'
            resolution = 'Extend shared attack/loop IR for every source argument; do not discard trailing values.'
    elif domain == 'model' and (n.startswith('@') or n.endswith('script')):
        status, nearest = 'GENERIC_CAPABILITY_MISSING', 'typed source VM and offline frame dispatch; live callback owner unbound'
        resolution = 'Bind the source world callback order and remaining engine services to the typed VM; compiled scripts alone do not certify gameplay.'
    elif domain == 'model' and n in ('palette', 'alternatepal'):
        status, nearest = 'SOURCE_DIALECT_VARIANT', 'source palette/remap catalog'
        resolution = 'Resolve per-model PNG palettes and alternatepal mappings from source; do not borrow global BOR palettes.'
    elif domain == 'stage' and n == 'palette':
        status, nearest = 'SOURCE_DIALECT_VARIANT', 'stage background palette encoder'
        resolution = 'Resolve the authored stage palette before encoding panels.'
    elif domain == 'video':
        status, nearest = 'SOURCE_DIALECT_VARIANT', 'source presentation profile'
        resolution = 'Retain resolution/color-depth metadata and resolve hardware presentation policy explicitly.'
    elif domain == 'scene' and n == 'silence':
        status, nearest = 'GENERIC_CAPABILITY_MISSING', 'scene audio stop'
        resolution = 'Lower silence to the shared scene audio stop operation.'
    if not exercised:
        status = 'NOT_USED'
    return dict(**row, domain=domain, classification=status,
        required_semantic_behavior=' '.join([n, *v]), nearest_byor_capability=nearest,
        proposed_generic_resolution=resolution, blocks_compilation=exercised and status not in ('SUPPORTED', 'SUPPORTED_ACCEPTED_COMPAT'),
        evidence_scope='static requirements, not native certification')


def inspect(path, *, measure_images=True):
    source = Source(path)
    docs = {k: document(source, name) for k, (name, _) in source.index.items() if k.endswith('.txt')}
    structure = discover(source, docs)
    stages = {key(e['source_path']) for s in structure['sets'] for e in s['entries'] if e['kind'] == 'STAGE'}
    campaign_scenes = {key(e['source_path']) for s in structure['sets'] for e in s['entries'] if e['kind'] == 'SCENE'}
    models = {key(m['source_path']) for m in structure['models']}
    matrix = []
    for k, doc in docs.items():
        domain = ('levels' if k == key(structure['levels_path']) else
                  'registry' if k == key(structure['models_path']) else
                  'video' if k == 'data/video.txt' else
                  'stage' if k in stages else
                  'scene' if '/scenes/' in k else 'model' if '/chars/' in k else 'other')
        exercised = domain in ('levels', 'registry', 'video') or k in stages or k in models or k in campaign_scenes
        matrix.extend(classify(domain, r, exercised) for r in doc['directives'])
    images, asset_errors = {}, []
    if measure_images:
        for k, (name, _) in source.index.items():
            if k.endswith(('.gif', '.png', '.bmp', '.jpg', '.jpeg')):
                try:
                    images[k] = image_requirement(source, name)
                except (ValueError, OSError) as e:
                    asset_errors.append(dict(source_path=name, code='IMAGE_DECODE_FAILED', reason=str(e)))
    queues = []
    for k in sorted(stages):
        rows = docs.get(k, {}).get('directives', [])
        records, stray, pending = [], [], None
        for row in rows:
            n = row['directive']
            if n in ('spawn', 'wait', 'group'):
                if pending is not None:
                    stray.append(dict(**pending['declaration'], code='QUEUE_UNTERMINATED'))
                pending = dict(kind=n, declaration=row, modifiers=[])
            elif n == 'at':
                if pending is None:
                    stray.append(dict(**row, code='QUEUE_AT_WITHOUT_RECORD'))
                else:
                    pending['at'] = row
                    records.append(pending)
                    pending = None
            elif pending is not None:
                pending['modifiers'].append(row)
        if pending:
            stray.append(dict(**pending['declaration'], code='QUEUE_UNTERMINATED'))
        queues.append(dict(source_path=source.resolve(k), records=records,
            authored_records=len(records), source_spawns=sum(r['kind']=='spawn' for r in records),
            hole_prefix_records=sum(r['directive']=='hole' for r in rows), diagnostics=stray))
        for error in stray:
            matrix.append(dict(**error,domain='queue_schema',classification='UNKNOWN_SEMANTICS',
                required_semantic_behavior='Determine how the source dialect commits an at without a pending record.',
                nearest_byor_capability='compiler.stage pending queue record',
                proposed_generic_resolution='Establish the dialect parser behavior; retain this directive and do not silently discard it.',
                blocks_compilation=True,evidence_scope='source schema diagnostic, not packed queue'))
    scripts = []
    for k, (name, _) in source.index.items():
        if k.endswith(('.c', '.h')):
            raw = source.read(name)
            text = raw.decode('latin1')
            scripts.append(dict(source_path=name, sha256=sha(raw), bytes=len(raw),
                functions=re.findall(r'\b(?:void|int|float|double|char)\s+(\w+)\s*\(', text),
                called_symbols=sorted(set(re.findall(r'\b(\w+)\s*\(', text))),
                source_text=text))
    # Static OBJ palettes hold eight banks with 15 opaque colors each.
    # Do not call this a universal rendering impossibility: raster palette
    # reuse/BG effects are alternate architectures, requiring measured proof.
    limits = []
    for model in structure['models']:
        model_palette = None
        if measure_images:
            try:
                model['source_palettes'] = model_palettes(source,model)
                base = model['source_palettes']['base']
                if base is not None:
                    model_palette = base['rgb8']
                    model['palette_authority'] = {k:v for k,v in base.items() if k not in ('rgb8','rgb555')}
            except (OSError, ValueError) as error:
                asset_errors.append(dict(source_path=model['source_path'],code='MODEL_PALETTE_UNRESOLVED',reason=str(error)))
        for animation in model['animations']:
            for frame in animation['frames']:
                try:
                    image = images.get(key(source.image_path(frame['values'][0])))
                    if image and model_palette is not None:
                        image = image_requirement(source, image['source_path'], model_palette=model_palette)
                except ValueError as e:
                    asset_errors.append(dict(**frame, code='FRAME_ASSET_MISSING', reason=str(e)))
                    continue
                if image and image['nontransparent_rgb555_colors'] > 120:
                    limits.append(dict(**frame, model=model['declaration'], role=animation['role'],
                        classification='RESOURCE_LIMIT', code='STATIC_OBJ_PALETTE_CAPACITY',
                        required_colors=image['nontransparent_rgb555_colors'], available_colors=120,
                        minimum_palettes=image['minimum_static_obj_palettes'], available_palettes=8,
                        asset_sha256=image['sha256'], dimensions=image['dimensions'],
                        palette_authority=model.get('palette_authority'),
                        maximum_scanline_colors=image['maximum_scanline_rgb555_colors'],
                        blocks_compilation=True,
                        required_semantic_behavior='Preserve source-sized actor pixels after RGB555 conversion.',
                        nearest_byor_capability='source-sized masked OBJ palette banks',
                        proposed_generic_resolution='Derive and admit a generic lossless raster OBJ or BG/hybrid capability; static overflow is not a universal rendering limit.',
                        scope='current static OBJ/CGRAM architecture; not proof all SNES rendering strategies fail'))
    counts = Counter(r['classification'] for r in matrix)
    counts.update(r['classification'] for r in limits)
    pak_bytes = Path(path).read_bytes() if Path(path).is_file() else None
    source_hash = sha(pak_bytes) if pak_bytes is not None else None
    return dict(schema='BYOR_SOURCE_SURVEY_V1', profile=resolve_profile(source_hash), source=dict(path=str(Path(path).resolve()),
        sha256=source_hash, archive_entries=len(source.index),
        filename_claim=Path(path).name, authenticated_engine_build=None,
        dialect_evidence=sorted({r['directive'] for r in matrix if r['directive'] in
             ('@script', '@cmd', 'animationscript', 'alternatepal', 'colourdepth', 'know')}),
        dialect='UNRESOLVED_FROM_SOURCE_FEATURES'), **structure,
        players=[dict(declaration=m['declaration'], name=m['name'], source_path=m['source_path'],
                      registry_order=m['registry_order'], secret=m['secret'], maps=m['maps'])
                 for m in structure['models'] if m['type']=='player' and m['registry_mode']=='load'],
        documents=list(docs.values()), scripts=scripts, images=list(images.values()),
        music=[dict(source_path=name, sha256=sha(source.read(name)), bytes=len(source.read(name)))
               for k, (name, _) in source.index.items() if k.endswith(('.bor', '.ogg', '.mp3'))],
        sounds=[dict(source_path=name, sha256=sha(source.read(name)), bytes=len(source.read(name)))
                for k, (name, _) in source.index.items() if k.endswith('.wav')],
        queues=queues, resource_limits=limits, asset_diagnostics=asset_errors,
        capability_matrix=matrix, capability_counts=dict(sorted(counts.items())),
        status='INSPECTED_NOT_COMPILED', native_status='NOT_RUN')


def write_survey(report, output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    matrix = output.with_name(output.stem+'-capabilities.json')
    matrix.write_text(json.dumps(dict(source=report['source'], counts=report['capability_counts'],
        requirements=report['capability_matrix'], resource_limits=report['resource_limits']), indent=2)+'\n', encoding='utf-8')
    summary = output.with_suffix('.md')
    lines = ['# BYOR source survey', '', 'Status: INSPECTED_NOT_COMPILED; native NOT_RUN.', '',
             'Source SHA-256: `'+str(report['source']['sha256'])+'`', '',
             'Engine build is not authenticated by the archive filename.', '', '## Discovered sets', '']
    for s in report['sets']:
        lines.append(f"- {s['id']}: {s['name']}, ifcomplete {s['ifcomplete']}, {len(s['entries'])} typed entries")
        lines.extend(f"  - {e['ordinal']}: {e['kind']} {e['source_path']}; next={e['next_after']}" for e in s['entries'])
    lines += ['', '## Source roster', '']
    lines.extend(f"- {m['registry_order']}: {m['declaration']} ({m['registry_mode']}, type {m['type']}, subtype {m['subtype']})" for m in report['models'])
    lines += ['', '## Queues', '']
    lines.extend(f"- {q['source_path']}: {q['authored_records']} records, {q['source_spawns']} spawns; {len(q['diagnostics'])} diagnostics" for q in report['queues'])
    lines += ['', '## Capability classifications (source uses)', '']
    lines.extend(f'- {n}: {v}' for n, v in report['capability_counts'].items())
    lines += ['', '## Hardware presentation requirements', '',
              'Static OBJ palettes provide 120 opaque colors total. Source requirements below already collapse RGB8 colors to RGB555. This does not rule out a different raster/BG renderer.', '']
    unique = {r['values'][0]: r for r in report['resource_limits']}
    lines.extend(f"- {r['model']} {p}: {r['required_colors']} colors, >= {r['minimum_palettes']} palettes; scanline maximum {r['maximum_scanline_colors']}" for p, r in unique.items())
    summary.write_text('\n'.join(lines)+'\n', encoding='utf-8')
    return matrix, summary
