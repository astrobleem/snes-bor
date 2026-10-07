"""Source-derived inputs for the update_animation prefix, before timed advance.

These fields follow the model value copy; they are not animation metadata.
The descriptor does not certify execution of the prefix or frame effects.
"""
import argparse
import hashlib
import json
import math
import struct
import zlib
from pathlib import Path
from compiler import Source, key
from dialect_4086 import ENGINE_COMMIT
from source_profile import document, discover
from source_model_core_4086 import binary32, integer
from source_animation_ids import configure

HEADER = 24
STRIDE = 16
FIELDS = ('facing', 'scroll', 'sleepwait', 'escapehits')


def load(rows):
    # init_model: calloc defaults except the explicit sleepwait = 1000.
    result = dict(facing=0, scroll=0.0, sleepwait=1000, escapehits=0)
    for row in rows:
        name, values = row['directive'], row['values']
        if name == 'anim':
            break
        if name in ('facing', 'sleepwait', 'escapehits'):
            result[name] = integer(values)
        elif name == 'scroll':
            # CMD_MODEL_SCROLL uses atof, assigned into its float field.
            result[name] = binary32(values[0] if values else 0)
            if not math.isfinite(result[name]):
                raise ValueError('UPDATE_ANIMATION_SCROLL_FINITE_REQUIRED')
    return result


def derive(source):
    docs = {k: document(source, n) for k, (n, _) in source.index.items()
            if k.endswith('.txt')}
    configuration = configure(docs[key('data/models.txt')]['directives'])
    models = []
    for index, model in enumerate(discover(source, docs)['models']):
        doc = docs[key(model['source_path'])]
        models.append(dict(index=index, identity=model['declaration'],
                           source_path=model['source_path'],
                           source_sha256=doc['sha256'], fields=load(doc['directives'])))
    return dict(schema='BYOR_4086_UPDATE_ANIMATION_INPUTS_V1',
                engine_commit=ENGINE_COMMIT, fields=list(FIELDS), models=models,
                sleep_animation_id=configuration['authority']['enum']['ANI_SLEEP'],
                model_copy_policy='value copy from selected model; no entity fallback for these fields',
                source_authority='init_model calloc and sleepwait=1000; CMD_MODEL_FACING/SCROLL/SLEEPWAIT/ESCAPEHITS',
                required_entity_fields=['idling', 'animnum', 'animating', 'sleeptime',
                    'invincible', 'blink', 'invinctime', 'arrowon', 'freezetime',
                    'maptime', 'map', 'sealtime', 'seal', 'inpain', 'escapecount'],
                required_services=['unfrozen', 'ent_set_colourmap', 'update_frame', 'kill'],
                prefix_bound=False, timed_advance_bound=False,
                foreign_profile_admitted=False, motu_gameplay_proven=False,
                no_color_reduction=True)


def pack(report):
    models = report['models']
    if not 1 <= len(models) <= 16:
        raise ValueError('UPDATE_ANIMATION_MODEL_CAPACITY')
    body = bytearray()
    for index, model in enumerate(models):
        if model['index'] != index:
            raise ValueError('UPDATE_ANIMATION_MODEL_ORDER')
        values = model['fields']
        body.extend(struct.pack('<ifii', *(values[name] for name in FIELDS)))
    return struct.pack('<4s6HII', b'B4UP', 1, STRIDE, len(models),
                       report['sleep_animation_id'], 0, 0, len(body),
                       zlib.crc32(body) & 0xffffffff) + body


def unpack(raw):
    if len(raw) < HEADER:
        raise ValueError('UPDATE_ANIMATION_HEADER')
    magic, version, stride, count, sleep, a, b, size, crc = struct.unpack_from('<4s6HII', raw)
    if (magic, version, stride, a, b) != (b'B4UP', 1, STRIDE, 0, 0) or not 1 <= count <= 16 or size != count * STRIDE or len(raw) != HEADER + size or zlib.crc32(raw[HEADER:]) & 0xffffffff != crc:
        raise ValueError('UPDATE_ANIMATION_ABI')
    rows = [dict(zip(FIELDS, struct.unpack_from('<ifii', raw, HEADER + i * STRIDE)))
            for i in range(count)]
    if any(not math.isfinite(row['scroll']) for row in rows):
        raise ValueError('UPDATE_ANIMATION_SCROLL_FINITE_REQUIRED')
    return sleep, rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = derive(Source(args.source))
    raw = pack(report)
    sleep, rows = unpack(raw)
    assert sleep == report['sleep_animation_id']
    assert rows == [model['fields'] for model in report['models']]
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'models.b4up').write_bytes(raw)
    report.update(table_bytes=len(raw), table_sha256=hashlib.sha256(raw).hexdigest())
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(len(rows), 'source animation-prefix model rows;', len(raw), 'bytes')


if __name__ == '__main__':
    main()
