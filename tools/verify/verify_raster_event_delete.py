"""Independent fixed-event deletion certificate and source/PPU byte replay.

Uses no solver. Slot-state reachability proves unavoidable original events;
contiguous-range enumeration certifies the lower cost on the critical row.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
from compiler import Source
from raster_math_windows import evaluate
from raster_obj_chr import compile as compile_chr
from raster_obj_compact import unpack
from raster_obj_math_cover import apply_math
from source_bg_feasibility import rgb555
from source_scene_bg import compose_rgb8
from source_scene_obj_raster import prepare


def exact_partition(points):
    """Enumerate all partitions, independently of the planner's gap algorithm."""
    points = sorted(set(points))
    if not points:
        return 0, []
    best = None
    for count in range(1, min(4, len(points)) + 1):
        for cuts in itertools.combinations(range(1, len(points)), count - 1):
            edges = (0, *cuts, len(points))
            ranges = [(points[edges[i]], points[edges[i + 1] - 1]) for i in range(count)]
            value = max(0, sum(24 + 16 * (hi - lo + 1) for lo, hi in ranges) - 40)
            if best is None or (value, ranges) < best:
                best = value, ranges
    return best


def physical_rows(schedule):
    """Replay CGADD resets, low latch and high-byte commits from payload bytes."""
    physical = [0] * 256
    for e in schedule['trace'][0]['updates']:
        physical[128 + 16 * e['bank'] + e['slot']] = e['color']
    logical = physical.copy()
    rows, commits = [], 0
    if len(schedule['trace']) != len(schedule['prepared_dma_packets']):
        raise ValueError('VERIFY_PACKET_HEIGHT')
    for y, row in enumerate(schedule['prepared_dma_packets']):
        if row['scanline'] != y:
            raise ValueError('VERIFY_PACKET_ORDER')
        if len(row['packets']) > 4:
            raise ValueError('VERIFY_CHANNEL_CAPACITY')
        for e in schedule['trace'][y]['updates']:
            logical[128 + 16 * e['bank'] + e['slot']] = e['color']
        clocks = 0
        for packet in row['packets']:
            address = packet['cgram_word_address']
            raw = bytes.fromhex(packet['data_hex'])
            if not 128 <= address < 256 or len(raw) != 2 * packet['word_count'] or address + len(raw) // 2 > 256:
                raise ValueError('VERIFY_CGRAM_PACKET_DOMAIN')
            low = None
            clocks += 24 + 8 * len(raw)
            for byte in raw:
                if low is None:
                    low = byte
                else:
                    physical[address] = low | (byte & 127) << 8
                    low = None
                    address = (address + 1) & 255
                    commits += 1
            if low is not None:
                raise ValueError('VERIFY_UNCOMMITTED_LOW_BYTE')
        if max(0, clocks - 40) != row['prepared_commit_span']:
            raise ValueError('VERIFY_PACKET_COST')
        if physical != logical:
            raise ValueError('VERIFY_FULL_CGRAM_IDENTITY')
        rows.append(physical.copy())
    return rows, commits


def slot_requirements(schedule, physical):
    refs = {}
    for piece, mask in zip(schedule['pieces'], schedule['piece_pixel_masks']):
        for ly, row in enumerate(unpack(mask)):
            y = piece['y'] + ly
            for slot in row:
                if slot:
                    key = piece['bank'], int(slot)
                    word = physical[y][128 + 16 * key[0] + key[1]]
                    if refs.setdefault(key, {}).setdefault(y, word) != word:
                        raise ValueError('VERIFY_SLOT_COLLISION')
    return refs


def mandatory_certificate(original, refs):
    initial = {(e['bank'], e['slot']): e['color'] for e in original['trace'][0]['updates']}
    slots = {}
    for y, row in enumerate(original['trace'][1:], 1):
        for i, e in enumerate(row['updates']):
            slots.setdefault((e['bank'], e['slot']), []).append((y, i, e['color']))
    mandatory, optional = [], []
    for key, sequence in slots.items():
        universe = {initial.get(key, -1)} | {word for y, i, word in sequence}
        allowed = []
        for n, (y, i, word) in enumerate(sequence):
            end = sequence[n + 1][0] if n + 1 < len(sequence) else len(original['trace'])
            required = {c for line, c in refs.get(key, {}).items() if y <= line < end}
            if len(required) > 1:
                raise ValueError('VERIFY_INPUT_SLOT_INTERVAL')
            allowed.append(required or universe)
        forward = [{initial.get(key, -1)}]
        for n, (y, i, word) in enumerate(sequence):
            forward.append((forward[-1] | {word}) & allowed[n])
        backward = [set() for _ in range(len(sequence) + 1)]
        backward[-1] = universe
        for n in range(len(sequence) - 1, -1, -1):
            valid_after = allowed[n] & backward[n + 1]
            backward[n] = universe if sequence[n][2] in valid_after else valid_after
        if initial.get(key, -1) not in backward[0]:
            raise ValueError('VERIFY_NO_SLOT_PATH')
        for n, (y, i, word) in enumerate(sequence):
            omission = forward[n] & allowed[n] & backward[n + 1]
            event = dict(scanline=y, update_index=i, bank=key[0], slot=key[1], color=word)
            (optional if omission else mandatory).append(event)
    rows = {}
    for e in mandatory:
        rows.setdefault(e['scanline'], []).append(16 * e['bank'] + e['slot'])
    lower_rows = [(exact_partition(points)[0], y, points) for y, points in rows.items()]
    bound, critical, points = max(lower_rows, default=(0, 0, []))
    return dict(mandatory_events=mandatory, optional_events=optional,
                independently_certified_peak_lower_bound=bound, critical_scanline=critical,
                critical_dirty_addresses=sorted(points), critical_optimal_ranges=exact_partition(points)[1],
                method='Forward/backward exact per-slot event-subset reachability; exhaustive <=4 contiguous-range partitions of mandatory addresses')


def verify(original, candidate, source):
    for key in ('pieces', 'piece_pixel_masks', 'selected_modes', 'compiled_color_window_descriptors', 'metadata'):
        if original[key] != candidate[key]:
            raise ValueError('VERIFY_FIXED_FAMILY_' + key)
    if original['trace'][0]['updates'] != candidate['trace'][0]['updates']:
        raise ValueError('VERIFY_FIXED_INITIAL_PALETTE')
    if len(original['trace']) != len(candidate['trace']):
        raise ValueError('VERIFY_FIXED_HEIGHT')
    for old, new in zip(original['trace'][1:], candidate['trace'][1:]):
        allowed = {(e['bank'], e['slot'], e['color']) for e in old['updates']}
        if any((e['bank'], e['slot'], e['color']) not in allowed for e in new['updates']):
            raise ValueError('VERIFY_EVENT_NOT_ORIGINAL_SUBSET')
    old_rows, _ = physical_rows(original)
    new_rows, commits = physical_rows(candidate)
    refs = slot_requirements(original, old_rows)
    for (b, slot), values in refs.items():
        for y, word in values.items():
            if new_rows[y][128 + 16 * b + slot] != word:
                raise ValueError('VERIFY_REQUIRED_OPERAND')
    certificate = mandatory_certificate(original, refs)
    stage, scene = original['metadata']['stage'], original['metadata']['scene']
    _, metadata, expected8 = prepare(source, stage, scene)
    if metadata != original['metadata']:
        raise ValueError('VERIFY_SOURCE_METADATA')
    expected = rgb555(expected8)
    background = rgb555(compose_rgb8(source, stage, dict(scene, actors=[]))[0])
    replay = background.copy()
    for piece, mask in zip(candidate['pieces'], candidate['piece_pixel_masks']):
        for ly, row in enumerate(unpack(mask)):
            y = piece['y'] + ly
            for lx, slot in enumerate(row):
                if not slot:
                    continue
                x = piece['x'] + lx
                word = new_rows[y][128 + 16 * piece['bank'] + int(slot)]
                gate = piece['bank'] >= 4 and evaluate(candidate['compiled_color_window_descriptors'][str(y)], x)
                replay[y, x] = apply_math(word, int(background[y, x]), candidate['selected_modes'][str(y)]) if gate else word
    mismatch = int(np.count_nonzero(replay != expected))
    digest = hashlib.sha256(replay.astype('<u2').tobytes()).hexdigest()
    if mismatch or digest != original['source_rgb555_sha256']:
        raise ValueError('VERIFY_SOURCE_PIXEL_REPLAY')
    old_chr, old_data, old_oam = compile_chr(original)
    geometry, data, oam = compile_chr(candidate)
    if data != old_data or oam != old_oam or not geometry['hardware_scanline_geometry_admitted']:
        raise ValueError('VERIFY_CHR_OAM_GEOMETRY')
    peak = max(r['prepared_commit_span'] for r in candidate['prepared_dma_packets'])
    return dict(schema='BYOR_EVENT_DELETE_INDEPENDENT_REPLAY_V1', source_exact=True,
                viewport_pixels=int(expected.size), source_mismatches=mismatch,
                source_rgb555_sha256=digest, palette_high_byte_commits=commits,
                peak_prepared_commit_span=peak, geometry=geometry,
                chr_oam_byte_identical=True, certificate=certificate,
                deletion_family_peak_optimal=certificate['independently_certified_peak_lower_bound'] == peak,
                family_infeasible_at_344_and_356=certificate['independently_certified_peak_lower_bound'] > 356,
                physical_witness=False, native_timing_admitted=False,
                production_mode6_admitted=False, concurrent_actor_admitted=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = verify(json.loads(args.original.read_text()), json.loads(args.candidate.read_text()), Source(args.source))
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('certificate', 'geometry')}))
    print(json.dumps({k: v for k, v in report['certificate'].items() if k not in ('mandatory_events', 'optional_events')}))


if __name__ == '__main__':
    main()
