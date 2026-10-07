"""Pinned loader animation ranges, indexed by mutable animation handles."""
import argparse
import hashlib
import json
import struct
from compiler import Source, key
from source_profile import document, discover
from script_dispatch_4086 import compile_source
from source_model_core_4086 import integer, number
from dialect_4086 import ENGINE_COMMIT

FIELDS = ('min.x', 'max.x', 'min.z', 'max.z', 'min.y', 'max.y', 'min.base', 'max.base')
AXES = {'range': 0, 'rangez': 2, 'rangea': 4, 'rangeb': 6}


def load(rows):
    jumpheight, grabdistance = 4.0, 36.0
    result = []
    current = None
    for row in rows:
        name, values = row['directive'], row['values']
        if name == 'jumpheight':
            jumpheight = number(values)
        elif name == 'grabdistance':
            grabdistance = number(values)
        elif name == 'anim':
            role = ' '.join(values).lower()
            # Cast to int BEFORE division, then truncate integer division to zero.
            depth = int(int(grabdistance) / 3)
            ranges = [-10, int(jumpheight)*20, -depth, depth, -1000, 1000, -1000, 1000]
            if role == 'jump': ranges[:2] = [50, 60]
            elif role == 'upper': ranges[:2] = [-10, 120]
            elif role == 'jumpattack' and jumpheight == 4: ranges[:2] = [150, 200]
            elif role == 'block': ranges[:2] = [1, 100]
            current = dict(role=' '.join(values), source_line=row['line'], ranges=ranges)
            result.append(current)
        elif name in AXES:
            if current is None: raise ValueError('ANIMATION_RANGE_WITHOUT_ANIMATION')
            offset = AXES[name]
            lower, upper = integer(values), integer(values, 1)
            if name == 'range' and lower == upper:
                if lower == -0x80000000: raise ValueError('ANIMATION_RANGE_SOURCE_SIGNED_OVERFLOW')
                lower -= 1
            current['ranges'][offset:offset+2] = [lower, upper]
    return result


def derive(source):
    docs = {k: document(source, n) for k, (n, _) in source.index.items() if k.endswith('.txt')}
    discovery = discover(source, docs)
    # Global defaults change through registry processing. This subset has not
    # bound that ordering; reject rather than silently choosing final defaults.
    if any(r['directive'] in ('jumpheight', 'grabdistance') for r in docs[key(discovery['models_path'])]['directives']):
        raise ValueError('ANIMATION_RANGE_GLOBAL_DEFAULT_ORDER_UNBOUND')
    handles = {(h['model'], h['role']): h['handle'] for h in compile_source(source)['animation_handles']}
    animations = []
    for model in discovery['models']:
        doc = docs[key(model['source_path'])]
        for animation in load(doc['directives']):
            animation.update(model=model['declaration'], handle=handles[model['declaration'], animation['role']],
                             source_path=doc['source_path'], source_sha256=doc['sha256'])
            animations.append(animation)
    return dict(schema='BYOR_4086_ANIMATION_RANGE_IR_V1', engine_authority=ENGINE_COMMIT,
                fields=list(FIELDS), animations=animations, runtime_bound=False, motu_gameplay_proven=False)


def pack(report):
    animations = sorted(report['animations'], key=lambda a: a['handle'])
    if not 1 <= len(animations) <= 1023: raise ValueError('ANIMATION_RANGE_TABLE_CAPACITY')
    table = bytearray(struct.pack('<4s6H', b'B4AR', 1, len(animations), 32, 0, 0, 0))
    for handle, animation in enumerate(animations, 1):
        if animation['handle'] != handle: raise ValueError('ANIMATION_RANGE_HANDLE_ORDER')
        table.extend(struct.pack('<8i', *animation['ranges']))
    return bytes(table)


def unpack(data):
    if len(data) < 16: raise ValueError('ANIMATION_RANGE_TABLE_HEADER')
    magic, version, count, stride, a, b, c = struct.unpack_from('<4s6H', data)
    if magic != b'B4AR' or version != 1 or not 1 <= count <= 1023 or stride != 32 or a or b or c or len(data) != 16+count*32:
        raise ValueError('ANIMATION_RANGE_TABLE_HEADER')
    return [list(struct.unpack_from('<8i', data, 16+i*32)) for i in range(count)]


def main():
    from pathlib import Path
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); report = derive(Source(a.source)); table = pack(report)
    assert unpack(table) == [v['ranges'] for v in sorted(report['animations'], key=lambda v: v['handle'])]
    report.update(table_bytes=len(table), table_sha256=hashlib.sha256(table).hexdigest())
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2)+'\n'); a.output.with_suffix('.b4ar').write_bytes(table)
    print('Derived', len(report['animations']), 'animation range rows;', len(table), 'bytes')


if __name__ == '__main__': main()
