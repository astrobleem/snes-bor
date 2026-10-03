"""Compare a six-actor S-CPU replay with its persistent SA-1 replay."""
import argparse
import json
from pathlib import Path

from actor_s7_continuous_report import due_bounds
from actor_s7_cost_report import analyze as analyze_cost


def _debt_samples(report):
    rows = report['clock_rows']
    samples = []
    for row in rows:
        low, high = due_bounds(int(row[3]), int(row[4]), int(row[5]), 160)
        completed = int(row[7])
        samples.append((low - completed, high - completed, low, high,
                        completed, int(row[1])))
    return samples


def _worker_cost(report):
    starts = {int(row[3]): int(row[6]) for row in report['worker_rows']
              if row[1] == 'Worker_Execute'}
    ends = {int(row[3]): int(row[6]) for row in report['worker_rows']
            if row[1] == 'Worker_Complete'}
    assert set(starts) == set(range(1, 307)), 'WORKER_START_TICKS'
    assert set(ends) == set(range(1, 307)), 'WORKER_COMPLETE_TICKS'
    cycles = sum(ends[tick] - starts[tick] for tick in starts)
    fields = {int(row[3]): int(row[7]) for row in report['worker_rows']
              if row[1] == 'Worker_Complete'}
    return cycles, fields


def compare(before, after):
    base_semantics = before['semantic_rows']
    worker_semantics = after['persistent_semantic_rows']
    assert len(base_semantics) == len(worker_semantics) == 306, 'SNAPSHOT_COUNT'
    assert [row[1:] for row in base_semantics] == \
           [row[1:] for row in worker_semantics], 'ACTOR_SNAPSHOT_MISMATCH'
    assert before['event_rows'] == after['event_rows'], 'EVENT_ORDER_MISMATCH'
    assert len(before['world_rows']) == len(after['world_rows']) == 306, \
        'WORLD_TICK_COUNT'
    assert all(actor['exists'] for actor in after['actors']), 'ACTOR_NOT_LIVE'
    assert after['persistent_worker'], 'NOT_PERSISTENT_WORKER_RUN'
    assert not any(row[1] == 'FAULT' for row in after['persistent_rows']), \
        'WORKER_FAULT'

    for report in (before, after):
        ready = report['publisher_rows'][-1]
        assert int(ready[3]) == 18 and int(ready[4]) == 0 and int(ready[6]) == 1, \
            'SOURCE_PUBLISHER_NOT_READY'

    base_ticks = {int(row[3]): int(row[1]) for row in before['world_rows']}
    worker_cycles, worker_fields = _worker_cost(after)
    debt = [_debt_samples(before), _debt_samples(after)]
    costs = [analyze_cost(before), analyze_cost(after)]
    sync = after['sync_rows'][-1]
    present = next(row for row in after['persistent_rows']
                   if row[1] == 'PRESENT')
    event_cost_rows = after.get('event_transport_rows', [])
    selected = ('Core_StreamScroll_Play', 'S6_UpdateWorld', 'S6Bridge_Import',
                'S7Publisher_Capture', 'S7Publisher_Entry', 'Character_RenderPass',
                'S7Publisher_RenderOrCompat', 'S7Publisher_EmitPieces',
                'Core_Input_Poll', 'Tad_StreamFrameService', 'Tad_StreamLatePump',
                'Hud_Play', 'NMI/DMA measured body', 'Relay_Flush',
                'Relay_Run', 'Relay_Acquire')
    profiled = []
    for cost in costs:
        profile = cost['exclusive_master_clocks']
        profiled.append({name: profile.get(name, 0) for name in selected})

    return {
        'semantic_snapshots_equal': 306,
        'event_rows_equal': len(before['event_rows']),
        'event_kinds': sorted({row[1] for row in before['event_rows']}),
        'six_actors_live': sum(bool(actor['exists']) for actor in after['actors']),
        'physical_field_at_tick': {
            str(tick): [base_ticks[tick], worker_fields[tick]]
            for tick in (241, 247, 306)},
        'due_completed_debt_at_final_nmi': [
            {'due': [debt[0][-1][2], debt[0][-1][3]],
             'completed': debt[0][-1][4],
             'debt_min': min(row[0] for row in debt[0]),
             'debt_max': max(row[1] for row in debt[0]),
             'debt_final': debt[0][-1][1]},
            {'due': [debt[1][-1][2], debt[1][-1][3]],
             'completed': debt[1][-1][4],
             'debt_min': min(row[0] for row in debt[1]),
             'debt_max': max(row[1] for row in debt[1]),
             'debt_final': debt[1][-1][1]}],
        'elapsed_master_clocks': [cost['elapsed_through_final_release']
                                  for cost in costs],
        'profiled_exclusive_clocks': profiled,
        'sa1_worker_cycles': worker_cycles,
        'sa1_worker_master_clocks': 2 * worker_cycles,
        'sa1_worker_average_master_clocks_per_tick': 2 * worker_cycles / 306,
        'publisher': {
            'ready_resources': [int(report['publisher_rows'][-1][3])
                                for report in (before, after)],
            'inflight_resources': [int(report['publisher_rows'][-1][4])
                                   for report in (before, after)],
            'legacy_tail_missing_count': [int(report['publisher_rows'][-1][12])
                                          for report in (before, after)],
            'legacy_tail_error_latch': [hex(int(report['publisher_rows'][-1][14]))
                                        for report in (before, after)],
            'persistent_prepared': int(present[6]),
            'persistent_published': int(present[7]),
            'worker_error': int(present[8])},
        'sync': {
            'flushes': int(sync[1]), 'snapshots': int(sync[2]),
            'wait_ticks_master_clocks': int(sync[3]),
            'wait_snapshot_master_clocks': int(sync[4]),
            'acquire_master_clocks': int(sync[8]),
            'queue_calls': int(sync[10]), 'queue_master_clocks': int(sync[11]),
            'relay_calls': int(sync[13]), 'relay_master_clocks': int(sync[14])},
        'event_transport': ({
            'producer_records': int(event_cost_rows[-1][1]),
            'producer_bytes': int(event_cost_rows[-1][2]),
            'sa1_producer_cycles': int(event_cost_rows[-1][3]),
            'sa1_producer_master_clocks': int(event_cost_rows[-1][4]),
            'producer_kind_counts': {
                'frame_changed': int(event_cost_rows[-1][5]),
                'hit': int(event_cost_rows[-1][6]),
                'unlink': int(event_cost_rows[-1][7])},
            'scpu_drain_calls': costs[1]['calls'].get('Relay_DrainEvents', 0),
            'scpu_drain_master_clocks': costs[1]['exclusive_master_clocks'].get(
                'Relay_DrainEvents', 0)} if event_cost_rows else None)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('baseline', type=Path)
    parser.add_argument('persistent', type=Path)
    args = parser.parse_args()
    result = compare(json.loads(args.baseline.read_text()),
                     json.loads(args.persistent.read_text()))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
