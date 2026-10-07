"""Immutable modeldata.offscreenkill inputs for the admitted loader domain.

The field is copied on every full model replacement. It is not entity.autokill.
Loader types/subtypes/moves with additional defaults require another authority
binding and fail explicitly here; named projectile post-processing is separate.
"""
import argparse, hashlib, json, struct, zlib
from pathlib import Path
from compiler import Source, key
from dialect_4086 import ENGINE_COMMIT
from source_profile import document, discover
from source_model_core_4086 import integer

HEADER, STRIDE = 24, 8

def load(rows):
    value = 0
    for row in rows:
        name, args = row['directive'], row['values']
        if name == 'anim':
            break
        if name == 'type' and (len(args) != 1 or args[0].lower() not in ('none', 'player', 'enemy')):
            raise ValueError('OFFSCREEN_LOADER_TYPE_AUTHORITY_REQUIRED')
        if name == 'subtype' and (len(args) != 1 or args[0].lower() != 'none'):
            raise ValueError('OFFSCREEN_LOADER_SUBTYPE_AUTHORITY_REQUIRED')
        if name == 'aimove' and args and args[0].lower() in ('arrow', 'biker'):
            raise ValueError('OFFSCREEN_LOADER_MOVE_AUTHORITY_REQUIRED')
        if name == 'offscreenkill':
            if len(args) != 1:
                raise ValueError('OFFSCREEN_INPUT_ARITY')
            value = integer(args)
    return value

def derive(source):
    docs = {k: document(source, n) for k, (n, _) in source.index.items() if k.endswith('.txt')}
    models = []
    for i, model in enumerate(discover(source, docs)['models']):
        doc = docs[key(model['source_path'])]
        models.append(dict(id=i, identity=model['declaration'], source_path=model['source_path'],
                           source_sha256=doc['sha256'], offscreenkill=load(doc['directives'])))
    return dict(schema='BYOR_4086_OFFSCREEN_INPUTS_V1', engine_commit=ENGINE_COMMIT, models=models,
                authority='init_model calloc; CMD_MODEL_OFFSCREENKILL GET_INT_ARG(1)',
                native_owner_bound=False, foreign_profile_admitted=False,
                motu_gameplay_proven=False, no_color_reduction=True)

def pack(report):
    models = report['models']
    if not 1 <= len(models) <= 16:
        raise ValueError('OFFSCREEN_MODEL_CAPACITY')
    body = bytearray()
    for i, model in enumerate(models):
        if model['id'] != i:
            raise ValueError('OFFSCREEN_MODEL_ID')
        body.extend(struct.pack('<HHi', i, 0, model['offscreenkill']))
    return struct.pack('<4sHHHHIII', b'B4OS', 1, STRIDE, len(models), 0,
                       len(body), zlib.crc32(body) & 0xffffffff, 0) + body

def unpack(raw):
    if len(raw) < HEADER:
        raise ValueError('OFFSCREEN_HEADER')
    magic, version, stride, count, reserved, size, crc, flags = struct.unpack_from('<4sHHHHIII', raw)
    if (magic, version, stride, reserved, flags) != (b'B4OS', 1, STRIDE, 0, 0) or not 1 <= count <= 16 or size != count * STRIDE or len(raw) != HEADER + size or crc != zlib.crc32(raw[HEADER:]) & 0xffffffff:
        raise ValueError('OFFSCREEN_ABI')
    result = []
    for i in range(count):
        identity, reserved, value = struct.unpack_from('<HHi', raw, HEADER + i * STRIDE)
        if identity != i or reserved:
            raise ValueError('OFFSCREEN_ROW')
        result.append(dict(id=i, offscreenkill=value))
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = derive(Source(args.source)); raw = pack(report)
    assert unpack(raw) == [dict(id=m['id'], offscreenkill=m['offscreenkill']) for m in report['models']]
    report.update(table_bytes=len(raw), table_sha256=hashlib.sha256(raw).hexdigest())
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'offscreen.b4os').write_bytes(raw)
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(len(report['models']), 'models;', len(raw), 'bytes')

if __name__ == '__main__':
    main()
