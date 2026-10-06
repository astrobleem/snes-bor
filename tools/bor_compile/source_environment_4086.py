"""Source-derived empty-wall query admission, never a silent wall omission.

The source checkwall script API returns DECIMAL zero for a level with no walls,
including failed numeric conversions. Nonempty geometry needs a separate native
backend and is explicitly rejected by this capability. A world owner must
invalidate the lease before changing level geometry.
"""
import argparse
import json
from pathlib import Path
import struct
from compiler import Source, key
from source_profile import document, discover
from dialect_4086 import ENGINE_COMMIT

READY = 0xb4d1
ADDRESS = 0x7ffa82
FIRST_UNUSED = 0x7ffa88


def wall_requirement(rows):
    walls = [r for r in rows if r['directive'] == 'wall']
    return dict(walls=walls, wall_count=len(walls), admitted=not walls,
                capability='SOURCE_EMPTY_WALL_QUERY',
                diagnostics=[] if not walls else ['CHECKWALL_NONEMPTY_GEOMETRY_UNBOUND'])


def derive(source):
    docs = {k: document(source, n) for k, (n, _) in source.index.items() if k.endswith('.txt')}
    structure = discover(source, docs); stages = []; seen = set()
    if structure['diagnostics']: raise ValueError('ENVIRONMENT_SOURCE_DIAGNOSTICS')
    for source_set in structure['sets']:
        for entry in source_set['entries']:
            if entry['kind'] != 'STAGE' or key(entry['source_path']) in seen: continue
            seen.add(key(entry['source_path'])); doc = docs[key(entry['source_path'])]
            stages.append(dict(stage_id=len(stages)+1, source_path=doc['source_path'],
                               source_sha256=doc['sha256'], **wall_requirement(doc['directives'])))
    return dict(schema='BYOR_4086_EMPTY_WALL_QUERY_V1', engine_authority=ENGINE_COMMIT,
                authority='openborscript.c openbor_checkwall; openbor.c checkwall_below', stages=stages,
                scope='immutable zero-wall query only', live_world_bound=False)


def descriptor(stage):
    if not stage['admitted'] or stage['wall_count'] or stage['walls'] or stage['diagnostics']:
        raise ValueError('CHECKWALL_NONEMPTY_GEOMETRY_UNBOUND')
    if not 1 <= stage['stage_id'] <= 65535: raise ValueError('ENVIRONMENT_STAGE_ID')
    return struct.pack('<HHH', READY, 0, stage['stage_id'])


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--source', required=True)
    p.add_argument('--output', type=Path, required=True); a = p.parse_args()
    r = derive(Source(a.source)); a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(r, indent=2)+'\n')
    print(json.dumps(dict(stages=len(r['stages']), admitted=sum(s['admitted'] for s in r['stages']))))


if __name__ == '__main__': main()
