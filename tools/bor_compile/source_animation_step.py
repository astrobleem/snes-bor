"""Pinned 4086 animation advance decision and source-derived timing tables.

This operator returns an update_frame request. It does not execute that request:
callbacks, edelay, movement, sound, attacks and kill cleanup belong to the world
owner. In particular, a STOP leaves animpos unchanged; it does not display zero.
"""
from dataclasses import dataclass
import argparse
import hashlib
import json
from pathlib import Path
import struct
from compiler import Source, key
from source_profile import document, discover
from script_dispatch_4086 import compile_source
from dialect_4086 import animation_frames, ENGINE_COMMIT

NONE, FRAME, STOP, KILL = range(4)
ADDRESS = 0x7ffa50
FIRST_UNUSED = 0x7ffa80


@dataclass(frozen=True)
class Animation:
    count: int
    loop_mode: int = 0
    loop_min: int = 0
    loop_max: int = 0


def decide(animation, frame, animating, nextanim, time, autokill=0):
    """Only the timed advance branch of update_animation, not textbox input."""
    a = animation
    if not 1 <= a.count <= 32767 or not 0 <= frame < a.count:
        raise ValueError('SOURCE_ANIMATION_FRAME_DOMAIN')
    if animating not in (-1, 0, 1):
        raise ValueError('SOURCE_ANIMATION_DIRECTION_DOMAIN')
    if not all(-32768 <= n <= 32767 for n in (a.loop_mode, a.loop_min, a.loop_max)):
        raise ValueError('SOURCE_ANIMATION_LOOP_DOMAIN')
    if not 0 <= a.loop_min < a.count or not 0 <= a.loop_max <= a.count:
        raise ValueError('SOURCE_ANIMATION_LOOP_FRAME_DOMAIN')
    if not all(0 <= n <= 0xffffffff for n in (time, nextanim)):
        raise ValueError('SOURCE_ANIMATION_TIME_DOMAIN')
    if nextanim != time:
        return NONE, frame
    f = frame + animating
    if a.loop_mode and a.loop_max:
        if f == a.loop_max:
            f = a.loop_min or (a.count - 1 if f < 0 else 0)
        elif not 0 <= f < a.count:
            return (KILL if autokill else STOP), frame
    elif not 0 <= f < a.count:
        f = a.count - 1 if f < 0 else 0
        if not a.loop_mode:
            return (KILL if autokill else STOP), frame
        f = a.loop_min or f
    return (FRAME, f) if animating else (NONE, frame)


def derive(source):
    docs = {k: document(source, n) for k, (n, _) in source.index.items() if k.endswith('.txt')}
    structure = discover(source, docs)
    handles = {(h['model'], h['role']): h for h in compile_source(source)['animation_handles']}
    animations = []
    for model in structure['models']:
        doc = docs[key(model['source_path'])]
        for a in animation_frames(doc['directives']):
            loop = [d for d in a['directives'] if d['directive'] == 'loop']
            args = [int(v) for v in loop[-1]['values']] if loop else []
            if len(args) > 3:
                raise ValueError('SOURCE_ANIMATION_LOOP_ARITY')
            args += [0] * (3 - len(args))
            rule = Animation(len(a['frames']), *args)
            decide(rule, 0, 1, 0, 0)
            delays = [f['delay_ticks'] for f in a['frames']]
            if any(not 0 <= d <= 65535 for d in delays):
                raise ValueError('SOURCE_ANIMATION_DELAY_DOMAIN')
            h = handles[model['declaration'], a['role']]
            animations.append(dict(handle=h['handle'], model=h['model'], role=a['role'],
                engine_animation_id=h['engine_animation_id'], source_path=doc['source_path'],
                source_sha256=doc['sha256'], count=rule.count, loop_mode=rule.loop_mode,
                loop_min=rule.loop_min, loop_max=rule.loop_max, delays=delays,
                retained_frame_directives=a['directives']))
    return dict(schema='BYOR_4086_ANIMATION_TIMING_V1', engine_authority=ENGINE_COMMIT,
        animations=animations, scope='timed advance decision and raw loader delays',
        update_frame_bound=False, live_world_bound=False, motu_gameplay_proven=False)


def pack(report):
    rows = sorted(report['animations'], key=lambda a: a['handle'])
    data = bytearray(struct.pack('<4sHH', b'B4AT', 1, len(rows)))
    offset = 8 + 16 * len(rows)
    delays = bytearray()
    for n, a in enumerate(rows, 1):
        if a['handle'] != n:
            raise ValueError('SOURCE_ANIMATION_HANDLE_ORDER')
        data.extend(struct.pack('<HHHhhhHH', n, a['engine_animation_id'], a['count'],
            a['loop_mode'], a['loop_min'], a['loop_max'], offset + len(delays), 0))
        delays.extend(struct.pack('<' + 'H' * a['count'], *a['delays']))
    if len(data) + len(delays) > 32768:
        raise ValueError('SOURCE_ANIMATION_TABLE_BANK_LIMIT')
    return bytes(data + delays)


def unpack(table):
    if len(table) < 8:
        raise ValueError('SOURCE_ANIMATION_TABLE_HEADER')
    magic, version, count = struct.unpack_from('<4sHH', table)
    if magic != b'B4AT' or version != 1 or not 1 <= count <= 1024 or len(table) > 32768:
        raise ValueError('SOURCE_ANIMATION_TABLE_HEADER')
    cursor = 8 + count * 16
    if cursor > len(table):
        raise ValueError('SOURCE_ANIMATION_TABLE_DIRECTORY')
    rows = []
    for n in range(count):
        handle, animation_id, frames, mode, lo, hi, offset, reserved = struct.unpack_from('<HHHhhhHH', table, 8 + n * 16)
        if handle != n + 1 or reserved or offset != cursor or cursor + frames * 2 > len(table):
            raise ValueError('SOURCE_ANIMATION_TABLE_RECORD')
        rule = Animation(frames, mode, lo, hi)
        decide(rule, 0, 1, 0, 0)
        rows.append(dict(handle=handle, engine_animation_id=animation_id, animation=rule,
                         delays=list(struct.unpack_from('<' + 'H' * frames, table, cursor))))
        cursor += frames * 2
    if cursor != len(table):
        raise ValueError('SOURCE_ANIMATION_TABLE_TRAILING_BYTES')
    return rows


def validate_update_frame_pairing(timing_table, frame_table):
    """Grant timed playback only for the same captured update_frame identities.

    The native owner reads loop decisions from B4AT and performs delay writes
    through B4FE. Their complete handle/count/delay correspondence is therefore
    an installation requirement, including frames not initially visible.
    """
    from source_frame_effects_4086 import unpack as unpack_frames
    timing_rows = unpack(timing_table)
    frame_rows = unpack_frames(frame_table)['animations']
    if len(timing_rows) != len(frame_rows):
        raise ValueError('UPDATE_ANIMATION_FRAME_TABLE_COUNT')
    frames = 0
    for timing_row, frame_row in zip(timing_rows, frame_rows):
        if timing_row['handle'] != frame_row['handle']:
            raise ValueError('UPDATE_ANIMATION_FRAME_TABLE_HANDLE')
        delays = [frame['delay_ticks'] for frame in frame_row['frames']]
        if timing_row['animation'].count != len(delays):
            raise ValueError('UPDATE_ANIMATION_FRAME_TABLE_FRAMES')
        if timing_row['delays'] != delays:
            raise ValueError('UPDATE_ANIMATION_FRAME_TABLE_DELAYS')
        frames += len(delays)
    return dict(capability='TIMED_UPDATE_ANIMATION_4086',
                animations=len(timing_rows), frames=frames,
                timing_sha256=hashlib.sha256(timing_table).hexdigest(),
                frame_sha256=hashlib.sha256(frame_table).hexdigest(),
                frame_services_required=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=True)
    r = derive(Source(a.source)); table = pack(r); unpack(table)
    r.update(table_bytes=len(table), table_sha256=hashlib.sha256(table).hexdigest())
    (a.output / 'animation.b4at').write_bytes(table)
    (a.output / 'report.json').write_text(json.dumps(r, indent=2) + '\n')
    print(json.dumps(dict(animations=len(r['animations']), frames=sum(v['count'] for v in r['animations']), bytes=len(table))))


if __name__ == '__main__': main()
