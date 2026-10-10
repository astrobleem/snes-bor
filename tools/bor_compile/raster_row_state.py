"""Exact row-resident palette search without fixed color lifetime slots.

OAM banks stay fixed. Offline row pixels may use different slots. Prepared DMA
intervals and bounded prefetch are constraints; native timing is not admitted.
"""
import argparse, copy, hashlib, json
from pathlib import Path
import numpy as np
from raster_slot_greedy import demand
from raster_physical_ranges import constrain


def optimize(schedule, window=356, lookahead=17, maximum_ranges=4, time_limit=180, fixed_initial_slots=False):
    from ortools.sat.python import cp_model
    if window < 1 or lookahead < 0 or not 1 <= maximum_ranges <= 4:
        raise ValueError('ROW_STATE_DOMAIN')
    required, uses, pixel_colors = demand(schedule)
    height = len(required)
    if height < 2: raise ValueError('ROW_STATE_HEIGHT')
    active_banks = [b for b in range(8) if uses[b]]
    model = cp_model.CpModel()
    rows, flags, slots = {}, {}, []
    ids = {b: {c: i+1 for i, c in enumerate(sorted(uses[b]))} for b in active_banks}
    original = {b: [None]*15 for b in range(8)}
    hints = []
    for row in schedule['trace']:
        for e in row['updates']: original[e['bank']][e['slot']-1] = e['color']
        hints.append(copy.deepcopy(original))
    first_use = {b:min(y for y in range(height) if required[y][b]) for b in active_banks}
    variable_begin = {b:max(1,first_use[b]-lookahead) if fixed_initial_slots else first_use[b] for b in active_banks}
    for y in range(height):
        for b in active_banks:
            # Idle prefix/suffix shares state, avoiding unneeded IRQ events.
            if y and not any(required[t][b] for t in range(y, height)):
                rows[y,b] = rows[y-1,b]
                continue
            if y and y < variable_begin[b]:
                rows[y,b] = rows[0,b]
                continue
            full = len(required[y][b]) == 15
            domain = cp_model.Domain.from_values(sorted(ids[b][c] for c in required[y][b])) if full else cp_model.Domain(0,len(ids[b]))
            state = [model.new_int_var_from_domain(domain, f'c{y}_{b}_{s}') for s in range(15)]
            if full: model.add_all_different(state)
            rows[y,b] = state
            for s, v in enumerate(state): model.add_hint(v, ids[b].get(hints[y][b][s], 0))
            if y == 0 and fixed_initial_slots:
                for s,v in enumerate(state): model.add(v == ids[b].get(hints[y][b][s],0))
            for c in sorted(required[y][b]):
                s = model.new_int_var(0,14,f'required{y}_{b}_{c}')
                model.add_element(s, state, ids[b][c])
                if c in hints[y][b]: model.add_hint(s, hints[y][b].index(c))
            if not y: continue
            future = {ids[b][c] for t in range(y,min(height,y+lookahead+1)) for c in required[t][b]}
            for s, v in enumerate(state):
                dirty = model.new_bool_var(f'dirty{y}_{b}_{s}')
                model.add(v != rows[y-1,b][s]).only_enforce_if(dirty)
                model.add(v == rows[y-1,b][s]).only_enforce_if(dirty.Not())
                # Writes must install a color actually needed within the bound.
                if future: model.add_allowed_assignments([v], [(c,) for c in sorted(future)]).only_enforce_if(dirty)
                else: model.add(dirty == 0)
                model.add_hint(dirty, int(hints[y][b][s] != hints[y-1][b][s]))
                i = len(slots); slots.append(model.new_constant(s))
                flags.setdefault((y,b), []).append((i,dirty))
    ranges, peak = constrain(model,flags,slots,height,maximum_ranges,window)
    model.minimize(peak)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 4
    solver.parameters.cp_model_probing_level = 0
    status = solver.solve(model)
    report = dict(schema='BYOR_ROW_STATE_RASTER_V1',status='BOUNDED_ROW_STATE_NO_CANDIDATE',
        solver_status=solver.status_name(status),solver_seconds=solver.wall_time,
        solver_model_variables=len(model.proto.variables),solver_model_constraints=len(model.proto.constraints),
        solver_branches=solver.num_branches,solver_conflicts=solver.num_conflicts,
        window_master_clocks=window,lookahead_lines=lookahead,maximum_ranges=maximum_ranges,
        fixed_initial_slots=fixed_initial_slots,
        fixed_piece_bank_permutation={b:b for b in range(8)},
        initial_palette_may_preload_entire_frame=True,universal_raster_rejected=False,
        native_timing_admitted=False,no_color_reduction=True)
    if status not in (cp_model.FEASIBLE,cp_model.OPTIMAL): return report
    decoded = {b:{v:c for c,v in values.items()} for b,values in ids.items()}
    states, trace, packets = [], [], []
    before = {b:[None]*15 for b in range(8)}
    physical = [0]*128
    latency = 0
    for y in range(height):
        state = {b:[decoded[b].get(solver.value(v)) for v in rows[y,b]] if b in ids else [None]*15 for b in range(8)}
        events = []
        for b in range(8):
            for s,c in enumerate(state[b]):
                if c == before[b][s]: continue
                if c is None: raise AssertionError('ROW_STATE_EMPTY_WRITE')
                if y:
                    lead = next(t-y for t in range(y,height) if c in required[t][b])
                    if lead > lookahead: raise AssertionError('ROW_STATE_PREFETCH_BOUND')
                    latency = max(latency,lead)
                events.append(dict(bank=b,slot=s+1,old=before[b][s],color=c,
                    kind='required' if c in required[y][b] else 'prefetch'))
        groups = []
        if y == 0:
            for e in events: physical[16*e['bank']+e['slot']] = e['color']
        for (line,r),(active,lo,hi,length) in ranges.items():
            if line != y or not solver.value(active): continue
            begin,end = solver.value(lo),solver.value(hi)
            data = bytearray()
            for address in range(begin,end+1):
                b,s = divmod(address,16)
                c = 0 if not s else state[b][s-1]
                data.extend((0 if c is None else c).to_bytes(2,'little'))
            groups.append(dict(cgram_word_address=128+begin,word_count=end-begin+1,data_hex=data.hex()))
            for i in range(end-begin+1): physical[begin+i] = int.from_bytes(data[2*i:2*i+2],'little')
        span = max(0,sum(16*p['word_count']+24 for p in groups)-40)
        if span >= window: raise AssertionError('ROW_STATE_PACKET_WINDOW')
        for b in range(8):
            if not required[y][b].issubset(state[b]): raise AssertionError('ROW_STATE_DEMAND_REPLAY')
            if physical[16*b] != 0 or physical[16*b+1:16*b+16] != [0 if c is None else c for c in state[b]]:
                raise AssertionError('ROW_STATE_CGRAM_REPLAY')
        trace.append(dict(scanline=y,resident_before=copy.deepcopy(before),
            retained={b:[c for c in before[b] if c is not None and c in state[b]] for b in range(8)},
            evicted=[e['old'] for e in events if e['old'] is not None],
            prefetched=[e for e in events if e['kind']=='prefetch'],updates=events,
            colors_written=len(events),cgram_data_bytes=2*len(events),affected_banks=sorted({e['bank'] for e in events})))
        packets.append(dict(scanline=y,packets=groups,prepared_commit_span=span))
        states.append(state);before=state
    images=[];indices=np.zeros((height,256),dtype=np.uint8)
    for p, colors in zip(schedule['pieces'],pixel_colors):
        image=np.zeros(colors.shape,dtype=np.uint8)
        for ly,lx in zip(*np.where(colors>=0)):
            y,x=int(p['y']+ly),int(p['x']+lx);c=int(colors[ly,lx]);s=states[y][p['bank']].index(c)+1
            image[ly,lx]=s;indices[y,x]=128+16*p['bank']+s
            if states[y][p['bank']][s-1]!=c: raise AssertionError('ROW_STATE_PIXEL_REPLAY')
        flat=image.flatten();images.append(dict(width=p['width'],height=p['height'],packed_nibble_order='low then high',pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex()))
    report.update(status='PHYSICAL_SLOT_PACKETS_AND_PIXEL_IDENTITIES_PROVEN',
        maximum_noninitial_prefetch_latency_lines=latency,pixel_color_identity_verified=True,
        all_packet_cgram_identities_verified=True,peak_prepared_commit_span=max(p['prepared_commit_span'] for p in packets),
        peak_ranges=max(len(p['packets']) for p in packets))
    result=copy.deepcopy(schedule)
    result.update(trace=trace,piece_pixel_masks=images,prepared_dma_packets=packets,physical_slot_layout=report,
        compiled_indices_sha256=hashlib.sha256(indices.tobytes()).hexdigest(),
        peak_scheduled_writes=max(r['colors_written'] for r in trace[1:]),
        peak_cgram_data_bytes=max(r['cgram_data_bytes'] for r in trace[1:]),
        average_writes=float(np.mean([r['colors_written'] for r in trace[1:]])),
        worst_scanline=1+int(np.argmax([r['colors_written'] for r in trace[1:]])),native_presentation_proven=False)
    result.update(write_budget=None,lookahead_lines=lookahead,
        prepared_dma_window_master_clocks=window,prepared_dma_partition_bound_enforced=True,
        prepared_dma_window_is_optimistic_necessary_only=True,
        maximum_noninitial_prefetch_latency_lines=latency,noninitial_prefetch_lookahead_enforced=True,
        noninitial_prefetch_latency_replayed=True,
        schedule_latency_requirement=dict(maximum_noninitial_prefetch_lines=latency,initial_palette_may_preload_entire_frame=True))
    result['compiled_schedule_sha256']=hashlib.sha256(json.dumps(dict(pieces=result['pieces'],pixel_masks=images,trace=trace),sort_keys=True).encode()).hexdigest()
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--window',type=int,default=356);p.add_argument('--lookahead',type=int,default=17)
    p.add_argument('--maximum-ranges',type=int,default=4);p.add_argument('--time-limit',type=float,default=180)
    p.add_argument('--fixed-initial-slots',action='store_true')
    a=p.parse_args();r=optimize(json.loads(a.schedule.read_text()),a.window,a.lookahead,a.maximum_ranges,a.time_limit,a.fixed_initial_slots)
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r.get('physical_slot_layout',r)))


if __name__=='__main__':main()
