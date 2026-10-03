"""Source-preserving BOR compiler front end and shadow linker.

The accepted ten-byte queue backend is a compatibility target, not a claim
that every source feature is faithfully implemented by that backend.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import subprocess
import struct
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/bor_converter'), str(ROOT / 'tools/bg_converter')]
from pak_extract import read_entries
from spawn_parse import SpawnEvent, WaitEvent, GroupEvent
from spawn_parse import parse_spawns
from build_spawn_table import convert_events
from entity_parse import parse_entity
from PIL import Image
from queue_abi import check_count, RECORD_SIZE
from build_spawn_table import RECORD_SIZE as LEGACY_RECORD_SIZE
if LEGACY_RECORD_SIZE!=RECORD_SIZE:
    raise ValueError('accepted queue encoder ABI disagrees with authoritative queue contract')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def key(path):
    parts = path.replace('\\', '/').split('/')
    if '..' in parts or path.startswith(('/', '\\')) or ':' in path:
        raise ValueError(f'unsafe source path: {path}')
    return '/'.join(p for p in parts if p and p != '.').casefold()


class Source:
    """One case-insensitive namespace, retaining discovered spelling."""
    def __init__(self, path):
        self.path = Path(path)
        self.index = {}
        self.cache = {}
        entries = ((p.relative_to(self.path).as_posix(), p) for p in sorted(self.path.rglob('*')) if p.is_file()) if self.path.is_dir() else ((e.name, e) for e in read_entries(self.path))
        for name, entry in entries:
            k = key(name)
            if k in self.index:
                raise ValueError(f'ambiguous normalized path: {name}')
            self.index[k] = (name, entry)

    def resolve(self, path):
        if key(path) not in self.index:
            raise ValueError(f'missing source asset: {path}')
        return self.index[key(path)][0]

    def image_path(self, path):
        # Same implicit GIF suffix as the accepted PakIndex image reader.
        return self.resolve(path if key(path) in self.index else path + '.gif')

    def read(self, path):
        k = key(path)
        self.resolve(path)
        if k not in self.cache:
            entry = self.index[k][1]
            if self.path.is_dir():
                data = entry.read_bytes()
            else:
                with self.path.open('rb') as f:
                    f.seek(entry.offset)
                    data = f.read(entry.size)
            self.cache[k] = data
        return self.cache[k]

    def lines(self, path):
        for n, raw in enumerate(self.read(path).decode('latin1').splitlines(), 1):
            tokens = raw.split('#', 1)[0].split()
            if tokens:
                yield Directive(n, tokens[0].lower(), tokens[1:])


@dataclass
class Directive:
    line: int
    name: str
    values: list[str]


@dataclass
class EntryIR:
    kind: str
    source_path: str
    authored_path: str
    next_after: bool = False


@dataclass
class SetIR:
    name: str
    source_id: int
    ifcomplete: int = 0
    entries: list[EntryIR] = field(default_factory=list)


@dataclass
class PakProject:
    levels_path: str
    sets: list[SetIR]


@dataclass
class QueueIR:
    kind: str
    at: int = 0
    character: str | None = None
    coords: tuple[int, int] = (0, 0)
    altitude: int | None = None
    health: int | None = None
    alias: str | None = None
    map: int = 0
    item: str | None = None
    if2p: bool = False
    boss: bool = False
    flip: int = 0
    group_min: int = 0
    group_max: int = 0


@dataclass
class StageIR:
    source_path: str
    directives: list[Directive]
    background: str | None = None
    frontpanel: str | None = None
    panels: list[list[str]] = field(default_factory=list)
    order: str = ''
    dimensions: dict = field(default_factory=dict)
    scroll: str = 'right'
    music: str | None = None
    bossmusic: str | None = None
    queue: list[QueueIR] = field(default_factory=list)
    environment: dict = field(default_factory=dict)
    diagnostics: list[dict] = field(default_factory=list)


@dataclass
class SceneIR:
    source_path: str
    directives: list[Directive]
    music: str | None = None
    repeat: int = 0
    animations: list[dict] = field(default_factory=list)
    diagnostics: list[dict] = field(default_factory=list)


# Value and backend restrictions are applied below; recognition alone never
# confers executable support. Values remain in the IR even when blocked.
CAPABILITIES = {
    'levels': {n: 'SUPPORTED' for n in ('set', 'file', 'scene', 'next', 'ifcomplete')},
    'stage': {n: 'SUPPORTED_WITH_LOWERING' for n in (
        'background frontpanel panel order direction music bossmusic spawn wait group at '
        'coords health item 2pitem boss flip map alias hole endhole water blocked mirror rock').split()},
    'scene': {'music': 'SUPPORTED', 'animation': 'SUPPORTED_WITH_LOWERING'},
}


def diagnostic(path, d, reason):
    return dict(source_file=path, line=d.line, directive=d.name,
                value=d.values, status='UNSUPPORTED', reason=reason)


def validate_directives(path, lines, domain):
    return [diagnostic(path, d, 'unknown directive; no registered semantics')
            for d in lines if d.name not in CAPABILITIES[domain]]


def project(source, levels='DATA/LEVELS.TXT'):
    path = source.resolve(levels)
    sets = []
    for d in source.lines(path):
        if d.name not in CAPABILITIES['levels']:
            raise ValueError(diagnostic(path, d, 'unknown progression directive'))
        a = d.values
        if d.name == 'set' and len(a) == 1:
            sets.append(SetIR(a[0], len(sets)))
        elif not sets:
            raise ValueError(f'{path}:{d.line}: directive before set')
        elif d.name in ('file', 'scene') and len(a) == 1:
            sets[-1].entries.append(EntryIR('STAGE' if d.name == 'file' else 'SCENE', source.resolve(a[0]), a[0]))
        elif d.name == 'next' and not a and sets[-1].entries and not sets[-1].entries[-1].next_after:
            sets[-1].entries[-1].next_after = True
        elif d.name == 'ifcomplete' and len(a) == 1 and int(a[0]) >= 0:
            sets[-1].ifcomplete = int(a[0])
        else:
            raise ValueError(f'{path}:{d.line}: malformed {d.name} {a}')
    if not sets:
        raise ValueError('no source sets')
    return PakProject(path, sets)


def stage(source, path):
    ir = StageIR(source.resolve(path), list(source.lines(path)))
    ir.diagnostics = validate_directives(ir.source_path, ir.directives, 'stage')
    pending = None
    for d in ir.directives:
        n, a = d.name, d.values
        if n not in CAPABILITIES['stage']:
            continue
        try:
            if n in ('spawn', 'wait', 'group'):
                if pending:
                    raise ValueError('previous queue entry has no at terminator')
                expected = {'spawn': 1, 'wait': 0, 'group': 2}[n]
                if len(a) != expected:
                    raise ValueError('wrong queue argument count')
                pending = QueueIR(n)
                if n == 'spawn': pending.character = a[0]
                if n == 'group': pending.group_min, pending.group_max = map(int, a)
            elif n == 'at':
                if pending is None or len(a) != 1:
                    raise ValueError('at requires one value and a pending queue entry')
                pending.at = int(a[0])
                ir.queue.append(pending)
                pending = None
            elif n in ('coords', 'health', 'alias', 'map', 'item', '2pitem', 'boss', 'flip'):
                if pending is None or pending.kind != 'spawn':
                    raise ValueError('spawn modifier without spawn')
                if len(a) not in ((2, 3) if n == 'coords' else (1,)):
                    raise ValueError('wrong modifier argument count')
                if n == 'coords':
                    pending.coords = tuple(map(int, a[:2]))
                    pending.altitude = int(a[2]) if len(a) == 3 else None
                elif n in ('item', '2pitem'): pending.item, pending.if2p = a[0], n == '2pitem'
                elif n in ('boss', 'flip'):
                    if int(a[0]) not in (0, 1): raise ValueError('expected boolean')
                    setattr(pending, n, bool(int(a[0])) if n == 'boss' else int(a[0]))
                else: setattr(pending, n, a[0] if n == 'alias' else int(a[0]))
            elif n == 'panel':
                if len(a) not in (1, 3): raise ValueError('expected one or three panel layers')
                ir.panels.append([source.image_path(v) if v.lower() != 'none' else 'none' for v in a])
            elif n in ('background', 'frontpanel', 'music', 'bossmusic'):
                if len(a) != 1: raise ValueError('expected one asset path')
                setattr(ir, n, source.image_path(a[0]) if n in ('background', 'frontpanel') else source.resolve(a[0]))
            elif n == 'order':
                if len(a) != 1: raise ValueError('expected order string')
                ir.order += a[0]
            elif n == 'direction':
                if len(a) != 1 or a[0].lower() not in ('right', 'left', 'down'):
                    raise ValueError('unsupported scroll mode/parameters')
                ir.scroll = a[0].lower()
            elif n == 'water':
                if len(a) != 2: raise ValueError('expected water bitmap and mode')
                ir.environment.setdefault(n, []).append(dict(source_path=source.image_path(a[0]), mode=int(a[1])))
            else:
                if len(a) != 1: raise ValueError('expected one environment value')
                ir.environment.setdefault(n, []).append(int(a[0]))
        except (ValueError, IndexError) as exc:
            ir.diagnostics.append(diagnostic(ir.source_path, d, str(exc)))
    if pending:
        ir.diagnostics.append(diagnostic(ir.source_path, ir.directives[-1], 'unterminated queue record'))
    if not ir.order: ir.order = ''.join(chr(97+i) for i in range(len(ir.panels)))
    for p in [ir.background, ir.frontpanel] + [p for layer in ir.panels for p in layer]:
        if p and p != 'none':
            with Image.open(io.BytesIO(source.read(p))) as im:
                ir.dimensions[p] = list(im.size)
    return ir


def scene(source, path):
    ir = SceneIR(source.resolve(path), list(source.lines(path)))
    ir.diagnostics = validate_directives(ir.source_path, ir.directives, 'scene')
    for d in ir.directives:
        a = d.values
        try:
            if d.name == 'music':
                if len(a) != 2 or int(a[1]) not in (0, 1): raise ValueError('expected music path and repeat flag')
                ir.music, ir.repeat = source.resolve(a[0]), int(a[1])
            elif d.name == 'animation':
                if len(a) != 3: raise ValueError('expected animation path x y')
                p = source.resolve(a[0])
                with Image.open(io.BytesIO(source.read(p))) as im:
                    size = list(im.size)
                    delays = []
                    for i in range(im.n_frames):
                        im.seek(i)
                        delays.append(im.info.get('duration', 0))
                ir.animations.append(dict(source_path=p, x=int(a[1]), y=int(a[2]),
                                          dimensions=size, delays_ms=delays, duration_ms=sum(delays)))
                if min(delays) < 1000/60:
                    ir.diagnostics.append(diagnostic(ir.source_path, d, 'frame duration cannot present every frame at 60Hz'))
                if int(a[1]) or int(a[2]):
                    ir.diagnostics.append(diagnostic(ir.source_path, d, 'nonzero animation placement requires runtime validation'))
        except (ValueError, IndexError) as exc:
            ir.diagnostics.append(diagnostic(ir.source_path, d, str(exc)))
    return ir


def legacy_events(ir):
    result = []
    for q in ir.queue:
        if q.kind == 'spawn':
            e = SpawnEvent(q.character, q.at)
            for name in ('coords', 'health', 'alias', 'map', 'item', 'if2p', 'boss', 'flip'):
                setattr(e, name, getattr(q, name))
        elif q.kind == 'wait': e = WaitEvent(q.at)
        else: e = GroupEvent(q.group_min, q.group_max, q.at)
        result.append(e)
    return result


def lower(ir, roster, entities):
    if ir.diagnostics:
        raise ValueError(ir.diagnostics)
    width = sum(ir.dimensions[ir.panels[ord(c.lower())-97][0]][0] for c in ir.order
                if 0 <= ord(c.lower())-97 < len(ir.panels))
    count,blob = convert_events(legacy_events(ir), {n: str(e.get('type') or 'enemy').lower() for n, e in entities.items()},
                          roster, entities, ir.environment.get('hole', []), direction=ir.scroll, level_width=width)
    check_count(count,project='source lowering',set_name='unplaced source entry',stage=ir.source_path,source_path=ir.source_path)
    if len(blob)!=count*RECORD_SIZE: raise ValueError('lowered queue record size disagrees with queue ABI')
    return count,blob


def model_catalog(source):
    result = {}
    for d in source.lines('DATA/MODELS.TXT'):
        if d.name not in ('load', 'know') or len(d.values) != 2:
            raise ValueError(diagnostic('DATA/MODELS.TXT', d, 'unsupported model declaration'))
        name, path = d.values
        p = source.resolve(path)
        if name.lower() in result: raise ValueError(f'duplicate model name: {name}')
        result[name.lower()] = dict(name=name, source_path=p, declaration=d.name,
                                    entity=parse_entity(source.read(p).decode('latin1')))
    return result


def assign_ids(paths, pinned):
    result = {key(p): i for p, i in pinned.items()}
    if len(set(result.values())) != len(result): raise ValueError('duplicate pinned ID')
    for p in sorted(set(map(key, paths)) - result.keys()):
        result[p] = max(result.values(), default=-1) + 1
    return result


def presentation(source, ir):
    def asset(p): return None if not p or p == 'none' else digest(source.read(p))
    signature = dict(background=asset(ir.background), frontpanel=asset(ir.frontpanel),
                     panels=[[asset(p) for p in row] for row in ir.panels], order=ir.order,
                     water=[dict(bitmap=asset(w['source_path']), mode=w['mode']) for w in ir.environment.get('water', [])])
    return digest(json.dumps(signature, sort_keys=True).encode())


def baseline(ref):
    """Load committed configuration without importing build_rom or dirty data."""
    def git(path): return subprocess.check_output(['git', 'show', f'{ref}:{path}'], cwd=ROOT)
    ns = {'__name__': 'golden_config'}
    exec(compile(git('tools/audio/shipped_content.py'), 'golden_config', 'exec'), ns)
    return ns, git


def partial_set(s, count, completions=0):
    if not 0 <= count <= len(s.entries): raise ValueError('prefix outside source set')
    return dict(set_id=s.source_id, name=s.name, ifcomplete=s.ifcomplete,
                source_entries=len(s.entries), compiled_prefix=count,
                content_available=count == len(s.entries),
                source_unlocked=completions >= s.ifcomplete,
                selectable=count == len(s.entries) and completions >= s.ifcomplete,
                next_flags=[int(e.next_after) for e in s.entries[:count]])


def compile_project(source, ref, golden_msu=None, golden_sha=None):
    proj = project(source)
    config, git = baseline(ref)
    for path in ('tools/bg_converter/build_spawn_table.py', 'tools/bg_converter/spawn_parse.py', 'tools/bor_converter/entity_parse.py'):
        # Newline conventions may differ between checkout and Git.
        if (ROOT/path).read_text().replace('\r\n','\n') != git(path).decode().replace('\r\n','\n'):
            raise ValueError(f'accepted backend changed: {path}; refresh the golden adapter explicitly')
    msu = None
    if golden_msu:
        msu = Path(golden_msu).read_bytes()
        if not golden_sha or digest(msu) != golden_sha.lower():
            raise ValueError('golden MSU requires an explicit matching accepted SHA-256')
    stages = {key(e.source_path): stage(source, e.source_path) for s in proj.sets for e in s.entries if e.kind == 'STAGE'}
    scenes = {key(e.source_path): scene(source, e.source_path) for s in proj.sets for e in s.entries if e.kind == 'SCENE'}
    models = model_catalog(source)
    roster = {p.rsplit('/', 1)[-1].lower(): i for i, p in enumerate(config['ROSTER_PREFIXES'])}
    for i, e in enumerate(config['ROSTER_CONFIGS']):
        roster.setdefault(e['source_character'].replace('\\', '/').rsplit('/', 1)[-1].lower(), i)
    pinned_models = {}
    for m in models.values():
        parent = key(m['source_path']).rsplit('/', 1)[0]
        for i, e in enumerate(config['ROSTER_CONFIGS']):
            identity = key(e['source_character'])
            if identity == parent or identity == key(m['source_path']).rsplit('.', 1)[0]:
                pinned_models[m['source_path']] = i
    # Reserve all accepted IDs including non-BOR actors; append after the full catalog.
    model_ids = assign_ids([m['source_path'] for m in models.values()],
                           {**{f'__reserved/{i}': i for i in range(len(config['ROSTER_CONFIGS'])) if i not in pinned_models.values()}, **pinned_models})
    entities = {}
    # Match accepted backend discovery order to establish byte reproducibility.
    for name, _ in source.index.values():
        if '/chars/' not in '/' + key(name) or not key(name).endswith('.txt'): continue
        ent = parse_entity(source.read(name).decode('latin1'))
        entities[key(name).rsplit('/', 1)[-1][:-4]] = ent
        if ent.get('name'): entities.setdefault(str(ent['name']).lower(), ent)
    pinned_stages = {s['source_level']: i for i, s in enumerate(config['STAGE_CONFIGS'])}
    stage_ids = assign_ids([s.source_path for s in stages.values()], pinned_stages)
    golden = []
    queues = {}
    accepted_keys = {key(s['source_level']) for s in config['STAGE_CONFIGS'] if s['family']=='bor-original'}
    for k, ir in stages.items():
        unresolved = any(models.get(n.lower(), {}).get('source_path') not in pinned_models
                         for q in ir.queue for n in (q.character, q.item) if n)
        # Only reproduce legacy identity fallback for the explicitly accepted
        # golden corpus. Never emit new content with borrowed actor identities.
        if not ir.diagnostics and (k in accepted_keys or not unresolved):
            count, blob = lower(ir, roster, entities)
            queues[k] = blob
    for i, cfg in enumerate(config['STAGE_CONFIGS']):
        if cfg['family'] != 'bor-original': continue
        k = key(cfg['source_level'])
        ir = stages[k]
        # Dirty accepted spawn blobs are NOT an oracle. Record mismatches honestly.
        expected = git(cfg['spawn'])
        # Separate committed artifact provenance from accepted converter output.
        # The repo has pre-existing dirty queue corrections; never absorb those.
        events = parse_spawns(source.read(ir.source_path).decode('latin1'))
        source_queue_equal = [vars(e) for e in legacy_events(ir)] == [vars(e) for e in events]
        width = sum(ir.dimensions[ir.panels[ord(c.lower())-97][0]][0] for c in ir.order
                    if 0 <= ord(c.lower())-97 < len(ir.panels))
        _, regenerated = convert_events(events, {n: str(e.get('type') or 'enemy').lower() for n,e in entities.items()},
                                         roster, entities, ir.environment.get('hole', []), direction=ir.scroll, level_width=width)
        golden.append(dict(source_path=ir.source_path, physical_id=i,
                           queue_equal=queues.get(k) == expected,
                           accepted_converter_equal=queues.get(k) == regenerated,
                           source_queue_equal=source_queue_equal,
                           accepted_sha256=digest(expected), generated_sha256=digest(queues[k]) if k in queues else None,
                           authored_count=len(ir.queue), packed_count=len(queues.get(k, b''))//10,
                           scroll_equal=ir.scroll == cfg.get('scroll_direction', 'right')))
        if msu:
            directory = struct.unpack_from('<I', msu, 12)[0]
            offset, count = struct.unpack_from('<IH', msu, directory + 40*i + 32)
            if offset + count*10 > len(msu): raise ValueError('golden queue out of bounds')
            golden[-1]['production_msu_equal'] = queues.get(k) == msu[offset:offset+count*10]
    assets = {}
    for ir in stages.values():
        assets.setdefault(presentation(source, ir), []).append(ir.source_path)
    rows = []
    for s in proj.sets:
        for ordinal, entry in enumerate(s.entries):
            k = key(entry.source_path)
            ir = stages[k] if entry.kind == 'STAGE' else scenes[k]
            issues = list(ir.diagnostics)
            if entry.kind == 'STAGE':
                for d in ir.directives:
                    if d.name == 'alias':
                        issues.append(diagnostic(ir.source_path, d, 'accepted queue format has no alias field'))
                    if d.name == 'map' and int(d.values[0]) > 3:
                        issues.append(diagnostic(ir.source_path, d, 'accepted backend clamps palette map to 3'))
                    if d.name == 'coords' and len(d.values) == 3:
                        issues.append(diagnostic(ir.source_path, d, 'source altitude retained; accepted queue encoder reads only x/y'))
                    if d.name in ('water','blocked','endhole','rock','mirror'):
                        issues.append(diagnostic(ir.source_path, d, 'retained in IR; environment lowering needs a verified runtime binding'))
                for q in ir.queue:
                    for n in [q.character, q.item]:
                        if not n: continue
                        m = models.get(n.lower())
                        if m is None:
                            issues.append(dict(source_file=ir.source_path, directive='model', value=n, status='UNSUPPORTED', reason='model is not declared'))
                        elif m['source_path'] not in pinned_models:
                            issues.append(dict(source_file=ir.source_path, directive='model', value=n, status='UNSUPPORTED', reason='new identity requires media encoding and behavior validation; no borrowed actor allowed'))
            elif k not in {key(c['source_scene']) for c in config['SCENE_CONFIGS']}:
                issues.append(dict(source_file=ir.source_path, directive='scene-media', value=ir.source_path, status='UNSUPPORTED', reason='parsed timing; new scene media not encoded/validated'))
            registry_clear = not issues
            issues.append(dict(source_file=ir.source_path, directive='final-link', value='shadow',status='UNSUPPORTED',
                               reason='production asset/model/media bindings and finalized ROM/MSU linker are not compiler-owned'))
            rows.append(dict(set_id=s.source_id, set_name=s.name, ordinal=ordinal, **asdict(entry),
                             backend_lowerable=k in queues if entry.kind=='STAGE' else not ir.diagnostics,
                             registry_clear=registry_clear, fully_compilable=False, blockers=issues,
                             authored_queue_count=len(ir.queue) if entry.kind=='STAGE' else 0,
                             packed_queue_count=len(queues.get(k,b''))//10,
                             proposed_packed_queue_count=len(ir.queue)+len(ir.environment.get('hole',[])) if entry.kind=='STAGE' else 0,
                             model_counts=dict(Counter(q.character for q in ir.queue if q.character)) if entry.kind=='STAGE' else {}))
    coverage = []
    for s in proj.sets:
        n = 0
        for e in s.entries:
            known = key(e.source_path) in accepted_keys if e.kind == 'STAGE' else key(e.source_path) in {key(c['source_scene']) for c in config['SCENE_CONFIGS']}
            if not known: break
            n += 1
        coverage.append(partial_set(s, n))
    campaign_text = git('tools/audio/campaign_config.pasm').decode()
    normal_config = config['CAMPAIGN_CONFIGS']['BOR_NORMAL_1A_INTERNAL']
    normal_source_keys = [key(p) for p in normal_config['source_levels']]
    matching_set = next(s for s in proj.sets if [key(e.source_path) for e in s.entries[:len(normal_source_keys)]] == normal_source_keys)
    expected_flags = [int(v.strip()) for v in re.search(r'Campaign_BorNormalDev_NextFlags:\s*\.db ([^\r\n]+)',campaign_text)[1].split(',')]
    progression_equal = expected_flags == [int(e.next_after) for e in matching_set.entries[:len(expected_flags)]]
    scene_text = git('src/generated/scene_sequence_meta.pasm').decode()
    scene_contract = []
    for i,c in enumerate(config['SCENE_CONFIGS']):
        ir = scenes[key(c['source_scene'])]
        def constant(name): return int(re.search(rf'SceneSequence_Record{i}_{name} = (\d+)',scene_text)[1])
        scene_contract.append(dict(source_path=ir.source_path, scene_id=c['runtime_id'],
                                   matches=constant('SceneId')==c['runtime_id'] and constant('AudioRepeat')==ir.repeat and constant('ClipCount')==len(ir.animations)))
    asset_groups = {}
    for ir in [*stages.values(), *scenes.values()]:
        paths = [ir.music]
        if isinstance(ir, StageIR):
            paths += [ir.bossmusic, ir.background, ir.frontpanel]
            paths += [p for layers in ir.panels for p in layers]
            paths += [w['source_path'] for w in ir.environment.get('water', [])]
        else:
            paths += [a['source_path'] for a in ir.animations]
        for p in paths:
            if not p or p == 'none': continue
            h = digest(source.read(p))
            asset_groups.setdefault(h, set()).add(p)
    asset_link = [dict(asset_id=i,sha256=h,source_paths=sorted(paths),source_bytes=len(source.read(sorted(paths)[0])))
                  for i,(h,paths) in enumerate(sorted(asset_groups.items()))]
    scene_ids = assign_ids([s.source_path for s in scenes.values()], {c['source_scene']:c['runtime_id'] for c in config['SCENE_CONFIGS']})
    report = dict(schema=1, mode='shadow-only', baseline=ref, project=asdict(proj),
                  capabilities=CAPABILITIES, stages={k:asdict(v) for k,v in stages.items()},
                  scenes={k:asdict(v) for k,v in scenes.items()}, entries=rows,
                  golden=golden, golden_bytes_pass=all(x['queue_equal'] and x['scroll_equal'] for x in golden),
                  golden_converter_pass=all(x['accepted_converter_equal'] and x['scroll_equal'] for x in golden),
                  golden_progression_pass=progression_equal, golden_scene_contract=scene_contract,
                  golden_production_pass=all(x.get('production_msu_equal',False) and x['scroll_equal'] for x in golden),
                  golden_msu_sha256=digest(msu) if msu else None,
                  coverage=coverage, presentation_groups=assets,
                  asset_link=asset_link, scene_ids=scene_ids,
                  source_model_count=len(models),
                  per_set={s.name: dict(entries=sum(e['set_id']==s.source_id for e in rows),
                                        queue_backend_lowerable=sum(e['set_id']==s.source_id and e['kind']=='STAGE' and e['backend_lowerable'] for e in rows),
                                        registry_clear=sum(e['set_id']==s.source_id and e['registry_clear'] for e in rows)) for s in proj.sets},
                  stage_ids=stage_ids, model_ids=model_ids,
                  new_models=[dict(name=m['name'],source_path=m['source_path'],runtime_id=model_ids[key(m['source_path'])],
                                   type=m['entity']['type'],speed=m['entity']['speed'], animations=list(m['entity']['animations']))
                              for m in models.values() if m['source_path'] not in pinned_models],
                  summary=dict(stage_entries=sum(e['kind']=='STAGE' for e in rows), scene_entries=sum(e['kind']=='SCENE' for e in rows),
                               fully_compilable=sum(e['fully_compilable'] for e in rows),blocked=sum(not e['fully_compilable'] for e in rows),
                               queue_bytes=sum(len(b) for b in queues.values()),final_msu_size=None,
                               note='Queue-only shadow output. No final media layout or production ownership transfer.'))
    return report, queues


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', help='PAK or extracted source directory')
    p.add_argument('--baseline', default='0ef9a82bbd754aa979359df43d23821e48724ad8')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--golden-msu', type=Path)
    p.add_argument('--golden-sha256')
    p.add_argument('--scope', action='append', default=[], metavar='SET_ID:COUNT', help='shadow development prefix; never enables production')
    args = p.parse_args()
    report, queues = compile_project(Source(args.source), args.baseline, args.golden_msu, args.golden_sha256)
    if args.scope:
        proj = project(Source(args.source))
        report['requested_scope'] = [partial_set(proj.sets[int(s.split(':')[0])], int(s.split(':')[1])) for s in args.scope]
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out/'compatibility.json').write_text(json.dumps(report, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    lines = ['# BOR compiler shadow report', '', json.dumps(report['summary'], sort_keys=True), '',
             f"Golden committed queue files: {report['golden_bytes_pass']}",
             f"Golden converter: {report['golden_converter_pass']}",
             f"Golden hash-pinned production MSU: {report['golden_production_pass']}", '',
             '| Set | Ordinal | Source | Queue backend | Source faithful |', '|---|---:|---|---|---|']
    for e in report['entries']:
        lines.append(f"| {e['set_name']} | {e['ordinal']} | {e['source_path']} | {e['backend_lowerable']} | {e['fully_compilable']} |")
    lines += ['', 'Full IR, exact scene delays, model inventory and per-directive blockers are in compatibility.json.']
    lines += ['', '## Scope and limits', '',
              'Fully compilable means ready for a complete source-faithful ROM/MSU link. None is certified by this shadow-only compiler. Backend-lowerable means queue bytes (stages) or parsed timing (scenes), and is deliberately separate.',
              'No production counts, campaign tables, selector, audio allocator or VM offsets are changed.',
              '', '## Per-set inventory', '', json.dumps(report['per_set'],indent=2),
              '', '## Newly assigned source models', '']
    for m in report['new_models']:
        lines.append(f"- {m['name']}: {m['source_path']}, shadow ID {m['runtime_id']}, type {m['type']}, speed {m['speed']}")
    lines += ['', '## Blockers by entry', '']
    for e in report['entries']:
        if e['blockers']:
            lines.append(f"- {e['set_name']} {e['ordinal']} {e['source_path']}: " + '; '.join(sorted({b['reason'] for b in e['blockers']})))
    (args.out/'compatibility.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    for k, blob in queues.items():
        target = args.out/'queues'/Path(k).with_suffix('.bin')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
    print(json.dumps(report['summary'], indent=2))
    print('golden_bytes_pass:', report['golden_bytes_pass'])
    print('golden_production_pass:', report['golden_production_pass'])
    return 0 if report['golden_production_pass'] or report['golden_bytes_pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
