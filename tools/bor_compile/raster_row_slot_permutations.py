"""Exact physical slot permutations for fixed per-row palette resident sets.

Live colors may move between slots; all resulting writes are charged. This is
one restricted residency family, not universal raster feasibility. Native
transfer timing and shared-resource admission remain separate.
"""
import argparse,copy,hashlib,json,math
from pathlib import Path
import numpy as np
from raster_slot_greedy import demand,partition
from raster_physical_ranges import constrain,constrain_fixed_addresses


def optimize(source,window=332,time_limit=60,free_residency=False,layout_hint=None,repair_interval=None,maximum_writes=None,search_strategy='portfolio',range_encoding='intervals'):
    from ortools.sat.python import cp_model
    if window<1 or time_limit<=0:raise ValueError('ROW_SLOT_PERMUTATION_DOMAIN')
    if search_strategy not in('portfolio','lns'):raise ValueError('ROW_SLOT_SEARCH_STRATEGY')
    if range_encoding not in('intervals','coverage'):raise ValueError('ROW_SLOT_RANGE_ENCODING')
    if maximum_writes is not None and(type(maximum_writes)is not int or not 0<=maximum_writes<=120):raise ValueError('ROW_SLOT_WRITE_BUDGET_DOMAIN')
    restricted=source.get('status')=='RESTRICTED_SCANLINE_DEMAND_ONLY'
    required,uses,pixels=demand(source,allow_restricted=True);height=len(required)
    visible=[y for y,row in enumerate(required)if any(row)]
    if not visible:raise ValueError('ROW_SLOT_VISIBLE_SOURCE_REQUIRED')
    first,last=min(visible),max(visible)
    original=[];state={b:[None]*15 for b in range(8)}
    for row in source['trace']:
        for e in row['updates']:state[e['bank']][e['slot']-1]=e['color']
        original.append(copy.deepcopy(state))
    hinted=original;packet_hints=None
    if layout_hint is not None:
        if layout_hint.get('pieces')!=source['pieces'] or layout_hint.get('source_rgb555_sha256')!=source.get('source_rgb555_sha256') or not layout_hint.get('physical_slot_layout',{}).get('pixel_color_identity_verified'):raise ValueError('ROW_SLOT_HINT_IDENTITY')
        _,_,hint_pixels=demand(layout_hint,allow_restricted=True)
        if any(not np.array_equal(a,b)for a,b in zip(pixels,hint_pixels)):raise ValueError('ROW_SLOT_HINT_SOURCE_WORDS')
        hinted=[];state={b:[None]*15 for b in range(8)}
        for row in layout_hint['trace']:
            for e in row['updates']:state[e['bank']][e['slot']-1]=e['color']
            hinted.append(copy.deepcopy(state))
        if len(hinted)!=height:raise ValueError('ROW_SLOT_HINT_HEIGHT')
        packet_hints={row['scanline']:sorted((p['cgram_word_address']-128,p['cgram_word_address']-128+p['word_count']-1)for p in row['packets'])for row in layout_hint['prepared_dma_packets']}
    if repair_interval is not None and(not free_residency or layout_hint is None or len(repair_interval)!=2 or not first<=repair_interval[0]<=repair_interval[1]<=last):raise ValueError('ROW_SLOT_REPAIR_DOMAIN')
    line_windows=None;transfer_interval=None
    if repair_interval is not None:
        transfer_interval=(repair_interval[0],min(last,repair_interval[1]+1))
        line_windows={row['scanline']:window if transfer_interval[0]<=row['scanline']<=transfer_interval[1] else max(window,row['prepared_commit_span']+1)for row in layout_hint['prepared_dma_packets']}
    word_tables={b:sorted(set(uses[b])|{0}|{c for rows in (original,hinted) for row in rows for c in row[b] if c is not None})for b in range(8)}
    word_codes={b:{c:i for i,c in enumerate(table)}for b,table in word_tables.items()}
    repair_domains={}
    if repair_interval is not None:
        left,right=repair_interval
        for b in range(8):
            relevant={0}
            for y in range(left,right+1):relevant.update(required[y][b])
            for y in(max(0,left-1),min(height-1,right+1)):
                relevant.update(c for c in hinted[y][b]if c is not None)
            repair_domains[b]=sorted(word_codes[b][c]for c in relevant)
    model=cp_model.CpModel();values={};flags={};slot_constants={};value_hints={};change_hints={};used_rank_hints={}
    for b in range(8):
        for s in range(15):slot_constants[b*15+s]=model.new_constant(s)
    for y in range(first,last+1):
        for b in range(8):
            colors=[word_codes[b][0 if c is None else c]for c in original[y][b]]
            hint_colors=[word_codes[b][0 if c is None else c]for c in hinted[y][b]]
            ranks=[];domain=sorted(word_codes[b][c]for c in set(uses[b])|{0})if free_residency and restricted else list(range(len(word_tables[b])))if free_residency else sorted(set(colors))
            if repair_interval is not None and repair_interval[0]<=y<=repair_interval[1]:domain=repair_domains[b]
            for s in range(15):
                if repair_interval is not None and not repair_interval[0]<=y<=repair_interval[1]:
                    values[y,b,s]=model.new_constant(hint_colors[s])
                    value_hints[y,b,s]=hint_colors[s]
                    if y>first:
                        if transfer_interval[0]<=y<=transfer_interval[1]:
                            changed=model.new_bool_var(f'changed{y}_{b}_{s}')
                            model.add(values[y,b,s]!=values[y-1,b,s]).only_enforce_if(changed)
                            model.add(values[y,b,s]==values[y-1,b,s]).only_enforce_if(changed.Not())
                        else:changed=int(hint_colors[s]!=word_codes[b][0 if hinted[y-1][b][s] is None else hinted[y-1][b][s]])
                        flags.setdefault((y,b),[]).append((b*15+s,changed))
                        change_hints[y,b*15+s,b]=(16*b+s+1,int(hint_colors[s]!=value_hints[y-1,b,s]))
                    continue
                if not free_residency:rank=model.new_int_var(0,14,f'rank{y}_{b}_{s}')
                value=model.new_int_var_from_domain(cp_model.Domain.from_values(domain),f'word{y}_{b}_{s}')
                hint_value=hint_colors[s]if hint_colors[s]in domain else colors[s]if colors[s]in domain else domain[0]
                if not free_residency:
                    model.add_element(rank,colors,value)
                    spent=used_rank_hints.setdefault((y,b),set())
                    choices=[i for i,c in enumerate(colors)if c==hint_value and i not in spent]
                    rank_hint=choices[0]if choices else next(i for i in range(15)if i not in spent)
                    spent.add(rank_hint);hint_value=colors[rank_hint];model.add_hint(rank,rank_hint)
                model.add_hint(value,hint_value)
                value_hints[y,b,s]=hint_value
                if not free_residency:ranks.append(rank)
                values[y,b,s]=value
                if y>first:
                    changed=model.new_bool_var(f'changed{y}_{b}_{s}')
                    model.add(value!=values[y-1,b,s]).only_enforce_if(changed)
                    model.add(value==values[y-1,b,s]).only_enforce_if(changed.Not())
                    changed_hint=int(hint_value!=value_hints[y-1,b,s])
                    model.add_hint(changed,changed_hint)
                    change_hints[y,b*15+s,b]=(16*b+s+1,changed_hint)
                    flags.setdefault((y,b),[]).append((b*15+s,changed))
            if repair_interval is not None and not repair_interval[0]<=y<=repair_interval[1]:continue
            if free_residency:
                for word in sorted(required[y][b]):
                    c=word_codes[b][word]
                    index=model.new_int_var(0,14,f'requiredIndex{y}_{b}_{c}')
                    model.add_element(index,[values[y,b,s]for s in range(15)],c)
                    model.add_hint(index,(hint_colors if c in hint_colors else colors).index(c))
            else:model.add_all_different(ranks)
    prefixes={};interval_cuts=0;prefix_hints={}
    for b in range(8):
        prefixes[first,b]=model.new_constant(0)
        prefix_hints[first,b]=0
        for y in range(first+1,last+1):
            total=model.new_int_var(0,15*(y-first),f'bankWrites{y}_{b}');prefixes[y,b]=total
            model.add(total==prefixes[y-1,b]+sum(flag for i,flag in flags[y,b]))
            prefix_hints[y,b]=prefix_hints[y-1,b]+sum(change_hints[y,i,b][1]for i,flag in flags[y,b])
            model.add_hint(total,prefix_hints[y,b])
        for left in range(first,last+1):
            union=set()
            for right in range(left,last+1):
                union.update(required[right][b])
                if len(union)>15:
                    model.add(prefixes[right,b]-prefixes[left,b]>=len(union)-15);interval_cuts+=1
    transfer_flags={key:value for key,value in flags.items()if transfer_interval is None or transfer_interval[0]<=key[0]<=transfer_interval[1]}
    if maximum_writes is not None:
        for y in range(first+1,last+1):
            if transfer_interval is None or transfer_interval[0]<=y<=transfer_interval[1]:
                model.add(sum(flag for(line,b),events in transfer_flags.items()if line==y for i,flag in events)<=maximum_writes)
    if range_encoding=='coverage':
        ranges,peak=constrain_fixed_addresses(model,transfer_flags,height,4,window,packet_hints=packet_hints,line_windows=line_windows)
    else:
        ranges,peak=constrain(model,transfer_flags,slot_constants,height,4,window,packet_hints=packet_hints,line_windows=line_windows,fixed_address_change_hints=change_hints)
    if packet_hints is not None:
        hinted_cost=max((sum(24+16*(hi-lo+1)for lo,hi in row)for y,row in packet_hints.items()if y>first and(transfer_interval is None or transfer_interval[0]<=y<=transfer_interval[1])),default=0)
        model.add_hint(peak,hinted_cost)
    objective_scale=1
    if repair_interval is None:model.minimize(peak)
    else:
        repair_peak=model.new_int_var(0,4096,'repairPeak');costs=[]
        for y in range(transfer_interval[0],transfer_interval[1]+1):
            cost=sum(24*active+16*length for(line,r),(active,begin,end,length)in ranges.items()if line==y)
            model.add(repair_peak>=cost);costs.append(cost)
        objective_scale=4096*len(costs)+1
        model.minimize(objective_scale*repair_peak+sum(costs))
        if packet_hints is not None:model.add_hint(repair_peak,hinted_cost)
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit;solver.parameters.num_search_workers=4
    if search_strategy=='lns':solver.parameters.use_lns_only=True
    status=solver.solve(model)
    report=dict(schema='BYOR_ROW_SLOT_PERMUTATION_V1',status='BOUNDED_ROW_SLOT_PERMUTATION_NO_CANDIDATE',
        solver_status=solver.status_name(status),solver_seconds=solver.wall_time,
        solver_search_strategy=search_strategy,
        physical_range_encoding=range_encoding,
        solver_model_variables=len(model.proto.variables),solver_model_constraints=len(model.proto.constraints),
        solver_branches=solver.num_branches,solver_conflicts=solver.num_conflicts,
        solver_objective_lower_bound=solver.best_objective_bound,
        maximum_physical_writes_per_transfer_row=maximum_writes,
        full_frame_write_budget_enforced=maximum_writes is not None and repair_interval is None and not restricted,
        objective_peak_scale=objective_scale,
        peak_commit_span_lower_bound_for_this_restricted_model=max(0,math.floor(solver.best_objective_bound/objective_scale)-40),
        outside_interval_pixels_relaxed=restricted,complete_source_frame_pixel_identity_proven=False,
        window_master_clocks=max((line_windows or {}).values(),default=window),requested_repair_window_master_clocks=window if repair_interval is not None else None,
        physical_repair_interval=list(repair_interval)if repair_interval is not None else None,
        physical_repair_transfer_interval=list(transfer_interval)if transfer_interval is not None else None,full_frame_transfer_window_enforced=repair_interval is None and not restricted,
        physical_layout_hint_used=layout_hint is not None,fixed_resident_sets=not free_residency,live_slot_moves_allowed=True,free_residency=free_residency,
        physical_change_and_range_membership_hints_coherent=True,
        repair_color_domain_pruned_to_demands_and_boundary_residents=repair_interval is not None,
        bank_interval_liveness_cuts=interval_cuts,palette_word_domain_dense_identity_codes=True,
        lookahead_lines=last-first,noninitial_dead_word_writes_charged=True,
        visible_interval=[first,last],initial_palette_may_preload_entire_frame=True,
        universal_raster_rejected=False,native_timing_admitted=False,no_color_reduction=True)
    if status not in(cp_model.FEASIBLE,cp_model.OPTIMAL):return report
    states=[]
    for y in range(height):
        line=max(first,min(last,y))
        states.append({b:[word_tables[b][solver.value(values[line,b,s])]for s in range(15)]for b in range(8)})
    trace=[];packets=[];physical=[0]*128;before={b:[None]*15 for b in range(8)}
    for y,state in enumerate(states):
        events=[]
        for b in range(8):
            for s,c in enumerate(state[b]):
                if before[b][s]!=c:events.append(dict(bank=b,slot=s+1,old=before[b][s],color=c,kind='required'if c in required[y][b]else'slot_move_or_prefetch'))
        groups=[]
        if y:
            _,bounds=partition([(16*e['bank']+e['slot'],16*e['bank']+e['slot'])for e in events])
            for lo,hi in bounds:
                data=bytearray()
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
        if span>=(line_windows or {}).get(y,window):raise AssertionError('ROW_SLOT_PHYSICAL_WINDOW')
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
        complete_source_frame_pixel_identity_proven=not restricted,
        packet_ranges_independently_minimized=True,
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
    _,_,replayed=demand(result,allow_restricted=True)
    if any(not np.array_equal(a,b)for a,b in zip(pixels,replayed)):raise AssertionError('ROW_SLOT_SOURCE_PIXEL_REPLAY')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--layout-hint',type=Path)
    p.add_argument('--maximum-writes',type=int,help='Bound every changed physical word, including live moves and prefetch; local repairs enforce this only inside their transfer interval.')
    p.add_argument('--scanline-interval',type=int,nargs=2,metavar=('FIRST','LAST'),help='Explicit restricted-pixel proof with free interval initialization; never complete frame admission.')
    p.add_argument('--repair-interval',type=int,nargs=2,metavar=('FIRST','LAST'))
    p.add_argument('--free-residency',action='store_true',help='Allow any required bank word to occupy a slot, with every physical change charged; prefetch is bounded by the full visible source interval.')
    p.add_argument('--search-strategy',choices=('portfolio','lns'),default='portfolio')
    p.add_argument('--range-encoding',choices=('intervals','coverage'),default='intervals')
    p.add_argument('--window',type=int,default=332);p.add_argument('--time-limit',type=float,default=60)
    a=p.parse_args();source=json.loads(a.schedule.read_text())
    if a.scanline_interval:
        from raster_bank_residency import restrict_interval
        source=restrict_interval(source,*a.scanline_interval)
    r=optimize(source,a.window,a.time_limit,a.free_residency,json.loads(a.layout_hint.read_text())if a.layout_hint else None,a.repair_interval,a.maximum_writes,a.search_strategy,a.range_encoding);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r.get('physical_slot_layout',r)))


if __name__=='__main__':main()
