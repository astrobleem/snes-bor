#!/usr/bin/env python3
"""Byte-exact BORVID oracle for the O2 native clip lookup.

This intentionally reads the generated record constants and the shipped MSU;
it does not recreate packer offsets or payload layout from source assumptions.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
MSU = ROOT / 'distribution' / 'bor.msu'
META = ROOT / 'src' / 'generated' / 'scene_video_meta.pasm'
SEQ = ROOT / 'src' / 'generated' / 'scene_sequence_meta.pasm'


def constants(path):
    out = {}
    rx = re.compile(r'^([A-Za-z0-9_]+)\s*=\s*(\d+)(?:\s*;.*)?$')
    for line in path.read_text(encoding='utf-8').splitlines():
        m = rx.match(line.strip())
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


def u16(data, off):
    return int.from_bytes(data[off:off + 2], 'little')


def u32(data, off):
    return int.from_bytes(data[off:off + 4], 'little')


def record(meta, clip_id):
    for i in range(meta['SceneVideo_Count']):
        if meta[f'SceneVideo_Record{i}_SceneId'] == clip_id:
            return i, {
                'clip_id': clip_id,
                'record_index': i,
                'flags': meta[f'SceneVideo_Record{i}_Flags'],
                'width': meta[f'SceneVideo_Record{i}_Width'],
                'height': meta[f'SceneVideo_Record{i}_Height'],
                'fps_num': meta[f'SceneVideo_Record{i}_FpsNum'],
                'fps_den': meta[f'SceneVideo_Record{i}_FpsDen'],
                'frame_count': meta[f'SceneVideo_Record{i}_FrameCount'],
                'base': meta[f'SceneVideo_Record{i}_PayloadOffset'],
                'size': meta[f'SceneVideo_Record{i}_PayloadSize'],
            }
    raise AssertionError(f'clip ID {clip_id} not in generated BORVID records')


def inspect(path, clip_id):
    meta = constants(path)
    data = MSU.read_bytes()
    i, r = record(meta, clip_id)
    base, size = r['base'], r['size']
    end = base + size
    assert end <= len(data)
    count = u32(data, base)
    assert count == r['frame_count']
    pointer_base = base + 4
    timing_base = pointer_base + count * 4 if r['flags'] & 1 else None
    timing_len = count * 2 if timing_base is not None else 0
    pointer = u32(data, pointer_base)
    frame_off = base + pointer
    frame_id = u16(data, frame_off)
    packed = int.from_bytes(data[frame_off + 2:frame_off + 6], 'little')
    map_len = (packed & 0x7ff) * 2
    tile_len = ((packed >> 11) & 0x7ff) * 32
    palette_len = ((packed >> 22) & 0xff) * 2
    frame_end = frame_off + 6 + map_len + tile_len + palette_len
    result = dict(r, payload_end=end, payload_count=count,
                  timing_offset=timing_base, timing_length=timing_len,
                  pointer_table_base=pointer_base, frame0_relative=pointer,
                  frame0_absolute=frame_off, frame_id=frame_id,
                  map_length=map_len, tile_length=tile_len,
                  palette_length=palette_len, frame0_end=frame_end)
    print(result)
    assert frame_id == 0
    assert base <= frame_off < end
    assert frame_end <= end
    return result


def first_over_24bit(path, clip_id):
    meta = constants(path)
    data = MSU.read_bytes()
    _, r = record(meta, clip_id)
    base = r['base']
    for index in range(r['frame_count']):
        rel = u32(data, base + 4 + index * 4)
        absolute = base + rel
        if absolute >= 0x01000000:
            print({'clip_id': clip_id, 'frame_index': index,
                   'relative_pointer': rel,
                   'absolute_frame_offset': absolute,
                   'absolute_hex': hex(absolute)})
            return index, absolute
    return None


def main():
    print('bor_size', MSU.stat().st_size)
    rugal = inspect(META, 1)
    falla = inspect(META, 2)
    assert rugal['record_index'] == 0
    assert falla['record_index'] == 1
    assert falla['timing_offset'] == falla['base'] + 4 + falla['frame_count'] * 4
    first_over_24bit(META, 5)
    print('oracle PASS')


if __name__ == '__main__':
    main()
