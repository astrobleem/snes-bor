"""Exact event-subset search at fixed palette slots and fixed scanline times.

Deletes unnecessary loads, including cancelled excursions between pixel uses.
No event is moved, invented or reindexed. Costs cover actual contiguous DMA
payloads with at most four ranges; setup/contention/native timing are excluded.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

import numpy as np
from ortools.sat.python import cp_model
from raster_obj_compact import unpack
from raster_physical_ranges import constrain_fixed_addresses
from raster_physical_relabel import point_partition
from raster_slot_greedy import demand
from raster_slot_refine import verify_packets


def references(source):
    """Derive required slot identities from replayed pixels, never event labels."""
    _, _, pixels = demand(source)
    refs = {}
    for piece, mask, words in zip(source['pieces'], source['piece_pixel_masks'], pixels):
        image = unpack(mask)
        for ly, lx in zip(*np.where(image)):
            key = piece['bank'], int(image[ly, lx])
            y = piece['y'] + int(ly)
            word = int(words[ly, lx])
            if refs.setdefault(key, {}).setdefault(y, word) != word:
                raise ValueError('EVENT_DELETE_SLOT_COLLISION')
    return refs


def rebuild(source, selected):
    """Rebuild descriptors and replay independently of the constraint model."""
    result = copy.deepcopy(source)
    state = {b: [None] * 15 for b in range(8)}
    trace, packets = [], []
    for y, original in enumerate(source['trace']):
        before = copy.deepcopy(state)
        updates = []
        for i, event in enumerate(original['updates']):
            if y and (y, i) not in selected:
                continue
            event = dict(event)
            b, s = event['bank'], event['slot']
            event['old'] = state[b][s - 1]
            state[b][s - 1] = event['color']
            updates.append(event)
        trace.append(dict(scanline=y, resident_before=before, updates=updates))
        span, ranges = point_partition([16 * e['bank'] + e['slot'] for e in updates] if y else [])
        groups = []
        for lo, hi in ranges:
            words = [0 if a % 16 == 0 or state[a // 16][a % 16 - 1] is None
                     else state[a // 16][a % 16 - 1] for a in range(lo, hi + 1)]
            groups.append(dict(cgram_word_address=128 + lo, word_count=len(words),
                               data_hex=b''.join(w.to_bytes(2, 'little') for w in words).hex()))
        packets.append(dict(scanline=y, packets=groups, prepared_commit_span=span))
    result.update(trace=trace, prepared_dma_packets=packets, native_presentation_proven=False)
    # Remove derived reports that describe the original schedule.
    for key in ('physical_slot_layout', 'physical_slot_refinement', 'bank_residency',
                'optimistic_bank_order', 'compiled_transfer_descriptor_sha256',
                'maximum_noninitial_prefetch_latency_lines', 'schedule_latency_requirement',
                'noninitial_prefetch_latency_replayed', 'noninitial_prefetch_lookahead_enforced'):
        if key in result:
            result['input_event_delete_' + key] = result.pop(key)
    result.update(peak_scheduled_writes=max(len(r['updates']) for r in trace[1:]),
                  peak_cgram_data_bytes=2 * max(len(r['updates']) for r in trace[1:]),
                  average_writes=float(np.mean([len(r['updates']) for r in trace[1:]])),
                  worst_scanline=max(range(1, len(trace)), key=lambda y: len(trace[y]['updates'])))
    verify_packets(result)
    old_pixels, new_pixels = demand(source)[2], demand(result)[2]
    if any(not np.array_equal(a, b) for a, b in zip(old_pixels, new_pixels)):
        raise AssertionError('EVENT_DELETE_PIXEL_IDENTITY')
    payload = dict(pieces=result['pieces'], pixel_masks=result['piece_pixel_masks'], trace=trace)
    if result.get('scanline_math_controls_source_bound'):
        payload.update(selected_modes=result['selected_modes'],
                       compiled_color_window_descriptors=result['compiled_color_window_descriptors'])
    result['compiled_schedule_sha256'] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    result['compiled_transfer_descriptor_sha256'] = hashlib.sha256(json.dumps(packets, sort_keys=True).encode()).hexdigest()
    return result


def optimize(source, time_limit=120):
    if not 0 < time_limit <= 120:
        raise ValueError('EVENT_DELETE_TIME_LIMIT')
    refs = references(source)
    verify_packets(source)
    height = len(source['trace'])
    initial = {(e['bank'], e['slot']): e['color'] for e in source['trace'][0]['updates']}
    events = {}
    for y, row in enumerate(source['trace'][1:], 1):
        seen = set()
        for i, e in enumerate(row['updates']):
            key = e['bank'], e['slot']
            if key in seen:
                raise ValueError('EVENT_DELETE_DUPLICATE_ROW_SLOT')
            seen.add(key)
            events.setdefault(key, []).append((y, i, e['color']))
    model = cp_model.CpModel()
    flags, choices = {}, {}
    for key in sorted(set(events) | set(refs)):
        b, slot = key
        sequence = events.get(key, [])
        previous = initial.get(key, -1)
        for y, word in refs.get(key, {}).items():
            if not sequence or y < sequence[0][0]:
                if word != previous:
                    raise ValueError('EVENT_DELETE_INITIAL_REFERENCE')
        for n, (y, i, word) in enumerate(sequence):
            keep = model.new_bool_var(f'keep_{y}_{i}')
            state = model.new_int_var(-1, 32767, f'state_{y}_{i}')
            model.add(state == word).only_enforce_if(keep)
            model.add(state == previous).only_enforce_if(keep.Not())
            end = sequence[n + 1][0] if n + 1 < len(sequence) else height
            for line, required in refs.get(key, {}).items():
                if y <= line < end:
                    model.add(state == required)
            previous = state
            choices[y, i] = keep
            flags.setdefault((y, b), []).append((15 * b + slot - 1, keep))
            model.add_hint(keep, 1)
            model.add_hint(state, word)
    _, peak = constrain_fixed_addresses(model, flags, height, 4, 4096)
    # Lexicographic peak then retained event count. Weight exceeds all events.
    weight = len(choices) + 1
    model.minimize(weight * peak + sum(choices.values()))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 8
    status = solver.solve(model)
    bound = solver.best_objective_bound
    lower = max(0, (int(np.ceil(bound)) - len(choices) + weight - 1) // weight - 40)
    report = dict(schema='BYOR_FIXED_EVENT_DELETION_V1', solver_status=solver.status_name(status),
                  result='SAT' if status in (cp_model.FEASIBLE, cp_model.OPTIMAL) else solver.status_name(status),
                  solver_seconds=solver.wall_time, time_limit_seconds=time_limit,
                  model_variables=len(model.proto.variables), model_constraints=len(model.proto.constraints),
                  raw_objective_bound=bound, objective_peak_weight=weight,
                  restricted_peak_commit_span_lower_bound=lower,
                  original_noninitial_events=len(choices), maximum_ranges=4,
                  family='Delete subset of existing noninitial events; fixed times, slots, indices, banks, initial palette and math/window controls',
                  native_timing_admitted=False, physical_witness=False, no_color_reduction=True,
                  universal_raster_rejected=False)
    if status not in (cp_model.FEASIBLE, cp_model.OPTIMAL):
        return report
    selected = {key for key, flag in choices.items() if solver.value(flag)}
    result = rebuild(source, selected)
    actual = max(r['prepared_commit_span'] for r in result['prepared_dma_packets'])
    if actual != max(0, solver.value(peak) - 40):
        raise AssertionError('EVENT_DELETE_COST_REPLAY')
    removed = [dict(scanline=y, update_index=i, **source['trace'][y]['updates'][i])
               for y, i in choices if (y, i) not in selected]
    report.update(removed_events=removed, retained_noninitial_events=len(selected),
                  input_peak_commit_span=max(r['prepared_commit_span'] for r in source['prepared_dma_packets']),
                  peak_prepared_commit_span=actual, all_packet_cgram_identities_verified=True,
                  indexed_pixel_operands_verified=True, solver_objective=solver.objective_value)
    result['physical_event_delete'] = report
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schedule', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--time-limit', type=float, default=120)
    args = parser.parse_args()
    result = optimize(json.loads(args.schedule.read_text()), args.time_limit)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result.get('physical_event_delete', result)))


if __name__ == '__main__':
    main()
