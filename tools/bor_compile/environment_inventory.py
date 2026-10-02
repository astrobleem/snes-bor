"""Lossless stage-environment pressure inventory; no runtime certification claims."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from compiler import Source, stage
from analyze import inventory_project

CATEGORIES = {
    'map': 'MAP_SELECTION', 'remap': 'MAP_SELECTION', 'palette': 'MAP_SELECTION',
    'alias': 'ALIAS', 'water': 'WATER', 'hole': 'HOLE_ENDHOLE',
    'endhole': 'HOLE_ENDHOLE', 'blocked': 'BLOCKED_REGION',
    'direction': 'SCROLL', 'background': 'GEOMETRY', 'panel': 'GEOMETRY',
    'frontpanel': 'GEOMETRY', 'order': 'GEOMETRY',
    'rock': 'OTHER_ENVIRONMENT', 'mirror': 'OTHER_ENVIRONMENT',
}


def inventory(source):
    project = inventory_project(source)
    models = []
    for d in source.lines('DATA/MODELS.TXT'):
        if d.name not in ('load', 'know') or len(d.values) != 2:
            continue
        name, path = d.values
        try:
            path = source.resolve(path)
            directives = list(source.lines(path))
            remaps = [asdict(x) for x in directives if x.name in ('remap', 'palette')]
            models.append(dict(name=name, source_path=path, palette_directives=remaps,
                               remap_count=sum(x.name == 'remap' for x in directives)))
        except ValueError as error:
            models.append(dict(name=name, source_path=path, error=str(error)))
    entries = []
    for s in project['sets']:
        for ordinal, entry in enumerate(s['entries']):
            if entry['kind'] != 'STAGE':
                continue
            ir = stage(source, entry['source_path'])
            rows = []
            for d in ir.directives:
                category = 'ALTITUDE_Z' if d.name == 'coords' and len(d.values) >= 3 else CATEGORIES.get(d.name)
                if category:
                    rows.append(dict(category=category, **asdict(d)))
            uses = [dict(queue=i, model=q.character, map=q.map, altitude=q.altitude,
                         alias=q.alias, coords=q.coords) for i, q in enumerate(ir.queue)
                    if q.kind == 'spawn']
            entries.append(dict(set=s['name'], ordinal=ordinal, source_path=ir.source_path,
                                dimensions=ir.dimensions,scroll=ir.scroll,
                                directives=rows, spawn_uses=uses, diagnostics=ir.diagnostics))
    summaries = []
    for s in project['sets']:
        stages = [e for e in entries if e['set'] == s['name']]
        uses = [dict(source_path=e['source_path'], **u) for e in stages for u in e['spawn_uses']]
        maximum = max((u['map'] for u in uses), default=0)
        referenced = {u['model'].casefold() for u in uses if u['model']}
        relevant = [m for m in models if m['name'].casefold() in referenced]
        summaries.append(dict(set=s['name'], max_selected_map=maximum,
            max_selection_uses=[u for u in uses if u['map'] == maximum],
            referenced_models=relevant,
            nonzero_altitudes=[u for u in uses if u['altitude'] not in (None, 0)],
            aliases=[u for u in uses if u['alias']],
            categories=dict(sorted(Counter(d['category'] for e in stages for d in e['directives']).items()))))
    return dict(project=source.path.name, sets=summaries, models=models, entries=entries,
                publication=False, certification='NOT_PERFORMED')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sources', nargs='+', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    reports = [inventory(Source(p)) for p in args.sources]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(reports, indent=2, sort_keys=True) + '\n', encoding='utf8')
    for r in reports:
        print(r['project'])
        for s in r['sets']:
            print(s['set'], 'map', s['max_selected_map'], 'altitudes', len(s['nonzero_altitudes']),
                  'aliases', len(s['aliases']), 'models_max_remaps',
                  max((m.get('remap_count', 0) for m in s['referenced_models']), default=0))


if __name__ == '__main__':
    main()
