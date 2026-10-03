"""Stage environment ABI v1. Queue extension leaves all legacy 0..3 bytes intact.

Queue +5 bit 0 is facing; bits 1..6 carry map bits 2..7. Queue +6 bits
3..4 retain map bits 0..1. +5 bit 7 stays reserved. No record-size change.
"""
import struct
import json
from pathlib import Path
from queue_abi import RECORD_SIZE

VERSION = 1
MAP_BITS = 8
MAP_MAX = (1 << MAP_BITS) - 1
PALETTE_BYTES = 32
if RECORD_SIZE != 10:
    raise ValueError('ENVIRONMENT_QUEUE_ABI_MISMATCH: v1 requires the S3 ten-byte record')


def encode_map(facing, kind, selection):
    if facing not in (0, 1) or not 0 <= selection <= MAP_MAX:
        raise ValueError('ENVIRONMENT_MAP_RANGE: facing must be 0/1 and map 0..255')
    return facing | ((selection >> 2) << 1), (kind & ~0x18) | ((selection & 3) << 3)


def decode_map(facing_byte, kind_byte):
    if facing_byte & 0x80:
        raise ValueError('ENVIRONMENT_RESERVED_BIT: queue +5 bit 7')
    return facing_byte & 1, ((facing_byte >> 1) << 2) | ((kind_byte >> 3) & 3)


def encode_palettes(palettes):
    if len(palettes) > MAP_MAX:
        raise ValueError('ENVIRONMENT_MAP_CAPACITY_EXCEEDED: more than 255 remaps')
    if any(len(p) != 16 or any(not 0 <= c <= 0x7fff for c in p) for p in palettes):
        raise ValueError('ENVIRONMENT_PALETTE_FORMAT: expected 16 BGR555 words')
    return b''.join(struct.pack('<16H', *p) for p in palettes)


def write_model_map_counts(prefixes, output):
    counts = []
    for prefix in prefixes:
        palettes = json.loads(Path(str(prefix) + '_moveset.json').read_text())['remap_palettes']
        encode_palettes(palettes)
        counts.append(len(palettes))
    if len(counts) > 256:
        raise ValueError('ENVIRONMENT_ACTOR_CAPACITY_EXCEEDED: byte actor identity')
    text = '; Generated from emitted model palettes; do not edit.\nStageEnv_ModelMapCounts:\n'
    counts += [0] * (256 - len(counts))
    for i in range(0, 256, 16):
        text += '    .db ' + ','.join(map(str, counts[i:i + 16])) + '\n'
    Path(output).write_text(text, encoding='ascii')
