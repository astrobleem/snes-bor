"""Exact physical slot permutations for fixed per-row palette resident sets.

Live colors may move between slots; all resulting writes are charged. This is
one restricted residency family, not universal raster feasibility. Native
transfer timing and shared-resource admission remain separate.
"""
import argparse,copy,hashlib,json
from pathlib import Path
import numpy as np
from raster_slot_greedy import demand
from raster_physical_ranges import constrain


def optimize(source,window=332,time_limit=60,free_residency=False):
    from ortools.sat.python import cp_model
    if window<1 or time_limit<=0:raise ValueError('ROW_SLOT_PERMUTATION_DOMAIN')
    required,uses,pixels=demand(source);height=len(required)
    visible=[y for y,row in enumerate(required)if any(row)]
    if not visible:raise ValueError('ROW_SLOT_VISIBLE_SOURCE_REQUIRED')
    first,last=min(visible),max(visible)
    original=[];state={b:[None]*15 for b in range(8)}
    for row in source['trace']:
        for e in row['updates']:state[e['bank']][e['slot']-1]=e['color']
        original.append(copy.deepcopy(state))
    model=cp_model.CpModel();values={};flags={};slot_constants={}
    for b in range(8):
        for s in range(15):slot_constants[b*15+s]=model.new_constant(s)
    for y in range(first,last+1):
        for b in range(8):
            colors=[0 if c is None else c for c in original[y][b]]
            ranks=[];domain=sorted(set(uses[b])|{0})if free_residency else sorted(set(colors))
            for s in range(15):
                if not free_residency:rank=model.new_int_var(0,14,f'rank{y}_{b}_{s}')
                value=model.new_int_var_from_domain(cp_model.Domain.from_values(domain),f'word{y}_{b}_{s}')
                if not free_residency:model.add_element(rank,colors,value);model.add_hint(rank,s)
                model.add_hint(value,colors[s])
                if not free_residency:ranks.append(rank)
                values[y,b,s]=value
                if y>first:
                    changed=model.new_bool_var(f'changed{y}_{b}_{s}')
                    model.add(value!=values[y-1,b,s]).only_enforce_if(changed)
                    model.add(value==values[y-1,b,s]).only_enforce_if(changed.Not())
                    model.add_hint(changed,int(colors[s]!=(0 if original[y-1][b][s] is None else original[y-1][b][s])))
                    flags.setdefault((y,b),[]).append((b*15+s,changed))
            if free_residency:
                for c in sorted(required[y][b]):
                    index=model.new_int_var(0,14,f'requiredIndex{y}_{b}_{c}')
                    model.add_element(index,[values[y,b,s]for s in range(15)],c)
                    model.add_hint(index,colors.index(c))
            else:model.add_all_different(ranks)
    ranges,peak=constrain(model,flags,slot_constants,height,4,window)
    model.minimize(peak)
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit;solver.parameters.num_search_workers=4
    status=solver.solve(model)
    report=dict(schema='BYOR_ROW_SLOT_PERMUTATION_V1',status='BOUNDED_ROW_SLOT_PERMUTATION_NO_CANDIDATE',
        solver_status=solver.status_name(status),solver_seconds=solver.wall_time,
        solver_model_variables=len(model.proto.variables),solver_model_constraints=len(model.proto.constraints),
        solver_branches=solver.num_branches,solver_conflicts=solver.num_conflicts,
        window_master_clocks=window,fixed_resident_sets=not free_residency,live_slot_moves_allowed=True,free_residency=free_residency,
        lookahead_lines=last-first,noninitial_dead_word_writes_charged=True,
        visible_interval=[first,last],initial_palette_may_preload_entire_frame=True,
        universal_raster_rejected=False,native_timing_admitted=False,no_color_reduction=True)
    if status not in(cp_model.FEASIBLE,cp_model.OPTIMAL):return report
    states=[]
    for y in range(height):
        line=max(first,min(last,y))
        states.append({b:[solver.value(values[line,b,s])for s in range(15)]for b in range(8)})
    trace=[];packets=[];physical=[0]*128;before={b:[None]*15 for b in range(8)}
    for y,state in enumerate(states):
        events=[]
        for b in range(8):
            for s,c in enumerate(state[b]):
                if before[b][s]!=c:events.append(dict(bank=b,slot=s+1,old=before[b][s],color=c,kind='required'if c in required[y][b]else'slot_move_or_prefetch'))
        groups=[]
        if y:
            for (line,r),(active,begin,end,length)in ranges.items():
                if line!=y or not solver.value(active):continue
                lo,hi=solver.value(begin),solver.value(end);data=bytearray()
                for address in range(lo,hi+1):
                    b,s=divmod(address,16);data.extend((state[b][s-1]if s else 0).to_bytes(2,'little'))
                groups.append(dict(cgram_word_address=128+lo,word_count=hi-lo+1,data_hex=data.hex()))
        else:
            for e in events:physical[16*e['bank']+e['slot']]=e['color']
        for packet in groups:
            raw=bytes.fromhex(packet['data_hex']);lo=packet['cgram_word_address']-128
            for i in range(packet['word_count']):physical[lo+i]=int.from_bytes(raw[2*i:2*i+2],'little')
        if any(physical[16*b]!=0 or physical[16*b+1:16*b+16]!=state[b]for b in range(8)):raise AssertionError('ROW_SLOT_PACKET_IDENTITY')
        if any(not required[y][b].issubset(state[b])for b in range(8)):raise AssertionError('ROW_SLOT_REQUIRED_WORD_IDENTITY')
        span=max(0,sum(16*p['word_count']+24 for p in groups)-40)
        if span>=window:raise AssertionError('ROW_SLOT_PHYSICAL_WINDOW')
        packets.append(dict(scanline=y,packets=groups,prepared_commit_span=span))
        trace.append(dict(scanline=y,resident_before=copy.deepcopy(before),updates=events,
            retained={b:[c for c in before[b]if c is not None and c in state[b]]for b in range(8)},
            evicted=[e['old']for e in events if e['old']is not None],prefetched=[e for e in events if e['kind']!='required'],
            colors_written=len(events),cgram_data_bytes=2*len(events),affected_banks=sorted({e['bank']for e in events})))
        before=state
    masks=[];indices=np.zeros((height,256),dtype=np.uint8)
    for piece,colors in zip(source['pieces'],pixels):
        image=np.zeros(colors.shape,dtype=np.uint8)
        for ly,lx in zip(*np.where(colors>=0)):
            y,x=int(piece['y']+ly),int(piece['x']+lx);c=int(colors[ly,lx]);slot=states[y][piece['bank']].index(c)+1
            image[ly,lx]=slot;indices[y,x]=128+16*piece['bank']+slot
        flat=image.flatten();masks.append(dict(width=piece['width'],height=piece['height'],packed_nibble_order='low then high',pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex()))
    result=copy.deepcopy(source)
    report.update(status='PHYSICAL_SLOT_PACKETS_AND_PIXEL_IDENTITIES_PROVEN',
        peak_prepared_commit_span=max(p['prepared_commit_span']for p in packets),peak_ranges=max(len(p['packets'])for p in packets),
        pixel_color_identity_verified=True,all_packet_cgram_identities_verified=True,fixed_piece_bank_permutation={b:b for b in range(8)})
    result.update(input_compiled_schedule_sha256=source.get('compiled_schedule_sha256'),write_budget=None,native_presentation_proven=False,trace=trace,piece_pixel_masks=masks,prepared_dma_packets=packets,physical_slot_layout=report,
        compiled_indices_sha256=hashlib.sha256(indices.tobytes()).hexdigest(),
        peak_scheduled_writes=max(row['colors_written']for row in trace[1:]),peak_cgram_data_bytes=2*max(row['colors_written']for row in trace[1:]),
        worst_scanline=1+int(np.argmax([row['colors_written']for row in trace[1:]])),average_writes=float(np.mean([row['colors_written']for row in trace[1:]])))
    payload=dict(pieces=result['pieces'],pixel_masks=masks,trace=trace)
    if result.get('scanline_math_controls_source_bound'):
        payload.update(selected_modes=result['selected_modes'],compiled_color_window_descriptors=result['compiled_color_window_descriptors'])
    result['compiled_transfer_descriptor_sha256']=hashlib.sha256(json.dumps(packets,sort_keys=True).encode()).hexdigest()
    result['compiled_schedule_sha256']=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    _,_,replayed=demand(result)
    if any(not np.array_equal(a,b)for a,b in zip(pixels,replayed)):raise AssertionError('ROW_SLOT_SOURCE_PIXEL_REPLAY')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--free-residency',action='store_true',help='Allow any required bank word to occupy a slot, with every physical change charged; prefetch is bounded by the full visible source interval.')
    p.add_argument('--window',type=int,default=332);p.add_argument('--time-limit',type=float,default=60)
    a=p.parse_args();r=optimize(json.loads(a.schedule.read_text()),a.window,a.time_limit,a.free_residency);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r.get('physical_slot_layout',r)))


if __name__=='__main__':main()
