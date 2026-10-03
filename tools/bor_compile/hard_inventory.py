"""Compact source-authority evidence for BYOR's Hard milestone."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

from compiler import ROOT, Source, digest, key, model_catalog, project, stage
from normal_coverage import inventory, PAK


def compact_inventory():
    source = Source(PAK)
    sets = project(source).sets
    hard = next(s for s in sets if s.name == 'Hard')
    normal = next(s for s in sets if s.name == 'Normal')
    report = inventory(source, source_set='Hard')
    models = model_catalog(source)
    counts = Counter()
    normal_models = set()
    normal_directives = set()
    for entry in normal.entries:
        if entry.kind != 'STAGE':
            continue
        ir = stage(source, entry.source_path)
        normal_directives.update(d.name for d in ir.directives)
        normal_models.update(e.character.casefold() for e in ir.queue if e.character)
    rows = []
    directives = set()
    for entry, linked in zip(hard.entries, report['entries']):
        row = {k: v for k, v in linked.items() if k in
               ('ordinal', 'kind', 'source_path', 'next_after', 'physical_id',
                'queue_records', 'hole_prefix', 'packed_records', 'packed_sha256')}
        row['source_sha256'] = digest(source.read(entry.source_path))
        if entry.kind == 'STAGE':
            ir = stage(source, entry.source_path)
            directives.update(d.name for d in ir.directives)
            counts.update(e.character.casefold() for e in ir.queue if e.character)
            row['queue_kinds'] = dict(Counter(e.kind for e in ir.queue))
            row['spawn_identities'] = dict(Counter(e.character.casefold()
                                          for e in ir.queue if e.character))
            row['groups'] = [dict(min=e.group_min, max=e.group_max)
                             for e in ir.queue if e.kind == 'group']
            row['environment'] = ir.environment
            row['scroll'] = ir.scroll
        rows.append(row)
    bor_c = ROOT / 'out/bor_compile_s6/BOR.C'
    return dict(compiler='BYOR — Bring Your Own Rage', evidence='SOURCE_AND_IN_MEMORY_LINKAGE_ONLY',
                source_pak=str(PAK.relative_to(ROOT)), source_pak_sha256=digest(PAK.read_bytes()),
                levels_sha256=digest(source.read('DATA/LEVELS.TXT')),
                original_bor_c_sha256=digest(bor_c.read_bytes()),
                completion_source=dict(file='out/bor_compile_s6/BOR.C',
                    load_levelorder_default_ifcomplete_line=1761,
                    preceding_entry_gonext_line=1796,
                    showcomplete_gonext_line=5638, terminal_increment_line=5647),
                sets=[dict(name=s.name, id=s.source_id, ifcomplete=s.ifcomplete) for s in sets],
                hard_set_id=hard.source_id, entries=rows,
                totals=dict(entries=len(rows), stages=sum(r['kind'] == 'stage' for r in rows),
                            source_queue_records=sum(r.get('queue_records', 0) for r in rows),
                            packed_records=sum(r.get('packed_records', 0) for r in rows),
                            source_spawns=sum(counts.values())),
                identities={name: dict(source_definition=b['source_definition'],
                       source_sha256=digest(source.read(b['source_definition'])),
                       source_type=b['source_type'], runtime_slot=b['runtime_slot'],
                       source_health=models[name]['entity'].get('health'),
                       spawn_occurrences=counts[name]) for name, b in report['model_bindings'].items()},
                new_spawn_identities=sorted(counts.keys() - normal_models),
                new_stage_directives=sorted(directives - normal_directives),
                stage_directives=sorted(directives),
                compatibility_limitations=report['native_coverage']['compatibility_limitations'],
                held_items=report['held_item_coverage'],
                structural_coverage=report['structural_coverage'])


if __name__ == '__main__':
    print(json.dumps(compact_inventory(), indent=2))
