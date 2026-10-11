"""Exact fixed-bank slot allocation with two source-derived color windows.

Shared row math modes remain fixed. Upper-bank pixels may use their literal
output outside the windows or an exact operand inside them. This is a bounded
encoding family; no result admits native timing or rejects raster universally.
"""
import argparse,copy,hashlib,json
from pathlib import Path
import numpy as np
from raster_slot_greedy import demand
from raster_math_windows import evaluate,compile_sparse_mask
from raster_obj_math_cover import apply_math
from raster_physical_ranges import constrain_fixed_addresses
from raster_physical_relabel import point_partition
from raster_slot_refine import verify_packets


def derive(source,background,expected):
    background=np.asarray(background);expected=np.asarray(expected)
    if any(a.dtype.kind not in'ui' or np.any(a<0)or np.any(a>32767)for a in(background,expected)):raise ValueError('WINDOW_SLOT_RGB555_DOMAIN')
    background=background.astype(np.uint16);expected=expected.astype(np.uint16)
    if source.get('color_math')!='additive' or not source.get('scanline_math_controls_source_bound'):raise ValueError('WINDOW_SLOT_SOURCE_CONTROLS_REQUIRED')
    required,uses,pixels=demand(source);height=len(required)
    if background.shape!=(height,256) or expected.shape!=background.shape or hashlib.sha256(expected.astype('<u2').tobytes()).hexdigest()!=source['source_rgb555_sha256']:raise ValueError('WINDOW_SLOT_CONTEXT_IDENTITY')
    points=[];rows={};tables=[{0}for b in range(8)];replay=background.copy();cache={}
    for i,(piece,image)in enumerate(zip(source['pieces'],pixels)):
        bank=piece['bank']
        if bank not in piece.get('allowed_banks',range(8)):raise ValueError('WINDOW_SLOT_FIXED_BANK_ELIGIBILITY')
        for ly,lx in zip(*np.where(image>=0)):
            y,x=int(piece['y']+ly),int(piece['x']+lx);old=int(image[ly,lx]);out=int(expected[y,x]);bg=int(background[y,x])
            mode=source['selected_modes'][str(y)];gate=bank>=4 and evaluate(source['compiled_color_window_descriptors'][str(y)],x)
            value=apply_math(old,bg,mode)if gate else old;replay[y,x]=value
            if value!=out:raise ValueError('WINDOW_SLOT_INPUT_PIXEL_MATH_IDENTITY')
            operand=None
            if bank>=4:
                if apply_math(old,bg,mode)==out:operand=old
                else:
                    operand=0
                    for shift in(0,5,10):
                        target=out>>shift&31;under=bg>>shift&31;key=mode,target,under
                        if key not in cache:cache[key]=[c for c in range(32)if apply_math(c,under,mode)&31==target]
                        if not cache[key]:operand=None;break
                        operand|=min(cache[key])<<shift
                if operand is not None and apply_math(operand,bg,mode)!=out:raise AssertionError('WINDOW_SLOT_DERIVED_OPERAND')
            point=dict(piece=i,ly=int(ly),lx=int(lx),y=y,x=x,bank=bank,output=out,operand=operand,old_word=old,old_gate=gate)
            points.append(point);rows.setdefault(y,[]).append(point);tables[bank].add(out)
            if operand is not None:tables[bank].add(operand)
    if not np.array_equal(replay,expected):raise ValueError('WINDOW_SLOT_COMPLETE_INPUT_FRAME_IDENTITY')
    state={b:[None]*15 for b in range(8)};hint=[]
    for row in source['trace']:
        for e in row['updates']:state[e['bank']][e['slot']-1]=e['color']
        hint.append(copy.deepcopy(state))
        for b in range(8):tables[b].update(c for c in state[b]if c is not None)
    return points,rows,[sorted(v)for v in tables],hint


def optimize(source,background,expected,window=337,time_limit=45,maximum_writes=21,necessary_bank_window=None,search_strategy='portfolio',reuse_exact_operands=False,repair_interval=None,complete_exact_operands=False):
    from ortools.sat.python import cp_model
    if window<1 or time_limit<=0 or type(maximum_writes)is not int or not 0<=maximum_writes<=120:raise ValueError('WINDOW_SLOT_DOMAIN')
    if search_strategy not in('portfolio','lns'):raise ValueError('WINDOW_SLOT_SEARCH_STRATEGY')
    if necessary_bank_window is not None and(type(necessary_bank_window)is not int or necessary_bank_window<1):raise ValueError('WINDOW_SLOT_BANK_WINDOW_DOMAIN')
    points,rows,tables,hint=derive(source,background,expected);first,last=min(rows),max(rows);height=len(source['trace'])
    if repair_interval is not None and(len(repair_interval)!=2 or not first<=repair_interval[0]<=repair_interval[1]<=last):raise ValueError('WINDOW_SLOT_REPAIR_INTERVAL')
    complete_options={};cover_reports={}
    if complete_exact_operands:
        from raster_obj_math_cover import complete_math_cover
        for b in range(4,8):
            items=[p for p in points if p['bank']==b]
            if not items:continue
            requirements={(p['output'],int(background[p['y'],p['x']]))for p in items}
            modes=tuple(sorted({source['selected_modes'][str(p['y'])]for p in items}))
            options,cover_reports[b]=complete_math_cover(requirements,modes=modes,tag_modes=True,retained_operands=tables[b])
            complete_options[b]=options;tables[b]=sorted(set(tables[b])|{word for choices in options.values()for word in choices})
    codes=[{word:i for i,word in enumerate(table)}for table in tables]
    model=cp_model.CpModel();values={};flags={};gates={};selected_indices={};presence={};hint_values={};mandatory={};pixel_reads={}
    alternative_pixels=0
    for p in points:
        choices=[p['operand']]if p['operand']is not None else[]
        if complete_exact_operands and p['bank']>=4:
            choices=complete_options[p['bank']][source['selected_modes'][str(p['y'])],p['output'],int(background[p['y'],p['x']])]
        elif reuse_exact_operands and p['bank']>=4:
            choices=[word for word in tables[p['bank']]if apply_math(word,int(background[p['y'],p['x']]),source['selected_modes'][str(p['y'])])==p['output']]
        p['operand_choices']=choices;alternative_pixels+=len(choices)>1
    for y,items in rows.items():
        for p in items:
            if p['bank']<4 or not p['operand_choices']or set(p['operand_choices'])=={p['output']}:
                mandatory.setdefault((y,p['bank']),set()).add(p['output'])
    for y in range(first,last+1):
        for b in range(8):
            for s in range(15):
                value=model.new_int_var(0,len(tables[b])-1,f'word{y}_{b}_{s}');values[y,b,s]=value
                h=codes[b][0 if hint[y][b][s]is None else hint[y][b][s]];model.add_hint(value,h);hint_values[y,b,s]=h
                if repair_interval is not None and not repair_interval[0]<=y<=repair_interval[1]:model.add(value==h)
                if y>first:
                    changed=model.new_bool_var(f'changed{y}_{b}_{s}')
                    model.add(value!=values[y-1,b,s]).only_enforce_if(changed);model.add(value==values[y-1,b,s]).only_enforce_if(changed.Not())
                    model.add_hint(changed,int(h!=hint_values[y-1,b,s]));flags.setdefault((y,b),[]).append((15*b+s,changed))
        coordinates=sorted({p['x']for p in rows.get(y,[])if p['bank']>=4});starts=[];negative_starts=[];previous=model.new_constant(0);previous_negative=model.new_constant(0)
        for x in coordinates:
            gate=model.new_bool_var(f'gate{y}_{x}');gates[y,x]=gate
            old=evaluate(source['compiled_color_window_descriptors'][str(y)],x);model.add_hint(gate,int(old))
            if repair_interval is not None and not repair_interval[0]<=y<=repair_interval[1]:model.add(gate==int(old))
            start=model.new_bool_var(f'windowStart{y}_{x}');model.add(start<=gate);model.add(start<=1-previous);model.add(start>=gate-previous)
            starts.append(start);previous=gate
            negative_start=model.new_bool_var(f'negativeWindowStart{y}_{x}');negative=gate.Not()
            model.add(negative_start<=negative);model.add(negative_start<=1-previous_negative);model.add(negative_start>=negative-previous_negative)
            negative_starts.append(negative_start);previous_negative=negative
        if starts:
            inverted=model.new_bool_var(f'windowUnionInverted{y}')
            model.add(sum(starts)<=2).only_enforce_if(inverted.Not());model.add(sum(negative_starts)<=2).only_enforce_if(inverted)
            model.add_hint(inverted,int(bool(source['compiled_color_window_descriptors'][str(y)]['wobjsel_color_bits']&0x50)))
        needed={}
        for p in rows.get(y,[]):
            b=p['bank'];out=p['output'];operand=p['operand']
            if len(p['operand_choices'])>1:
                key=p['piece'],p['ly'],p['lx'];index=model.new_int_var(0,14,f'alternativeIndex{key}')
                read=model.new_int_var(0,len(tables[b])-1,f'alternativeRead{key}');pixel_reads[key]=read
                model.add_element(index,[values[y,b,s]for s in range(15)],read)
                model.add_allowed_assignments([gates[y,p['x']],read],[(0,codes[b][out])]+[(1,codes[b][word])for word in p['operand_choices']])
                old_word=p['old_word'];hv=[0 if c is None else c for c in hint[y][b]]
                model.add_hint(index,hv.index(old_word));model.add_hint(read,codes[b][old_word])
                continue
            if b<4:needed.setdefault((b,out),[]).append(model.new_constant(1))
            else:
                gate=gates[y,p['x']]
                needed.setdefault((b,out),[]).append(gate.Not())
                if operand is None:model.add(gate==0)
                else:needed.setdefault((b,operand),[]).append(gate)
        for (b,word),requirements in needed.items():
            active=model.new_bool_var(f'need{y}_{b}_{word}');model.add_max_equality(active,requirements);presence[y,b,word]=active
            index=model.new_int_var(0,14,f'index{y}_{b}_{word}');selected_indices[y,b,word]=index
            read=model.new_int_var(0,len(tables[b])-1,f'read{y}_{b}_{word}')
            model.add_element(index,[values[y,b,s]for s in range(15)],read);model.add(read==codes[b][word]).only_enforce_if(active)
            hv=[0 if c is None else c for c in hint[y][b]];model.add_hint(index,hv.index(word)if word in hv else 0)
            model.add_hint(read,codes[b][word]if word in hv else hint_values[y,b,0])
            old_active=any(p['bank']==b and p['old_word']==word for p in rows.get(y,[]));model.add_hint(active,int(old_active))
    for (y,b),words in mandatory.items():
        indexes=[selected_indices[y,b,word]for word in sorted(words)]
        if len(indexes)>1:model.add_all_different(indexes)
        if len(words)==15:
            model.add_all_different([values[y,b,s]for s in range(15)])
            for s in range(15):model.add_allowed_assignments([values[y,b,s]],[(codes[b][word],)for word in sorted(words)])
    interval_cuts=0
    for b in range(8):
        prefix={first:model.new_constant(0)}
        for y in range(first+1,last+1):
            prefix[y]=model.new_int_var(0,15*(y-first),f'mandatoryPrefix{y}_{b}')
            model.add(prefix[y]==prefix[y-1]+sum(flag for i,flag in flags[y,b]))
        for left in range(first,last):
            union=set()
            for right in range(left,last+1):
                union.update(mandatory.get((right,b),set()))
                if len(union)>15:
                    model.add(prefix[right]-prefix[left]>=len(union)-15);interval_cuts+=1
    for y in range(first+1,last+1):
        model.add(sum(flag for(line,b),events in flags.items()if line==y for i,flag in events)<=maximum_writes)
        if necessary_bank_window is not None:
            from raster_bank_residency import constrain_dp
            counts=[];active=[]
            for b in range(8):
                n=model.new_int_var(0,15,f'count{y}_{b}');model.add(n==sum(flag for i,flag in flags[y,b]));counts.append(n)
                a=model.new_bool_var(f'activeBank{y}_{b}');model.add(n>=a);model.add(n<=15*a);active.append(a)
            constrain_dp(model,counts,active,necessary_bank_window,f'windowBank{y}',4)
    packet_hints={r['scanline']:sorted((p['cgram_word_address']-128,p['cgram_word_address']-129+p['word_count'])for p in r['packets'])for r in source.get('prepared_dma_packets',[])}
    line_windows=None
    if repair_interval is not None:
        line_windows={r['scanline']:window if repair_interval[0]<=r['scanline']<=min(last,repair_interval[1]+1)else max(window,r['prepared_commit_span']+1)for r in source['prepared_dma_packets']}
    ranges,peak=constrain_fixed_addresses(model,flags,height,4,window,packet_hints=packet_hints or None,line_windows=line_windows)
    costs=[sum(24*a+16*n for(line,r),(a,begin,end,n)in ranges.items()if line==y)for y in range(first+1,last+1)]
    model.minimize(peak*(4096*len(costs)+1)+sum(costs))
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit;solver.parameters.num_search_workers=4
    if search_strategy=='lns':solver.parameters.use_lns_only=True
    status=solver.solve(model)
    report=dict(schema='BYOR_FIXED_BANK_WINDOW_SLOT_SCHEDULE_V1',solver_status=solver.status_name(status),solver_seconds=solver.wall_time,
        solver_model_variables=len(model.proto.variables),solver_model_constraints=len(model.proto.constraints),solver_search_strategy=search_strategy,
        shared_row_math_modes_unchanged=True,two_color_windows_with_polarity_choice_enforced=True,fixed_piece_banks_unchanged=True,
        maximum_physical_writes=maximum_writes,necessary_bank_window_master_clocks=necessary_bank_window,physical_window_master_clocks=window,
        mandatory_identity_bank_interval_cuts=interval_cuts,
        resident_exact_operand_reuse_enabled=reuse_exact_operands,pixels_with_multiple_exact_operand_choices=alternative_pixels,
        complete_rgb555_operand_covers=cover_reports,
        repair_interval=repair_interval,
        native_timing_admitted=False,universal_raster_rejected=False,no_color_reduction=True)
    if status not in(cp_model.FEASIBLE,cp_model.OPTIMAL):return dict(report,status='BOUNDED_WINDOW_SLOT_NO_CANDIDATE')
    states=[];trace=[];packets=[];old={b:[None]*15 for b in range(8)};windows=copy.deepcopy(source['compiled_color_window_descriptors'])
    selected_uses=[{}for b in range(8)];selected_required={};latency=dead_writes=0
    def selected_word(p,enabled):
        read=pixel_reads.get((p['piece'],p['ly'],p['lx']))
        return tables[p['bank']][solver.value(read)]if read is not None else p['operand']if enabled else p['output']
    for p in points:
        enabled=p['bank']>=4 and solver.value(gates[p['y'],p['x']]);word=selected_word(p,enabled)
        selected_uses[p['bank']].setdefault(word,[]).append(p['y']);selected_required.setdefault((p['y'],p['bank']),set()).add(word)
    for y in range(height):
        line=max(first,min(last,y));state={b:[tables[b][solver.value(values[line,b,s])]for s in range(15)]for b in range(8)}
        events=[dict(bank=b,slot=s+1,old=old[b][s],color=c,kind='context_palette')for b in range(8)for s,c in enumerate(state[b])if c!=old[b][s]]
        for e in events:
            future=[t for t in selected_uses[e['bank']].get(e['color'],[])if t>=y]
            e['kind']='required'if e['color']in selected_required.get((y,e['bank']),set())else'prefetch'if future else'unused_initial'if y==0 else'dead_palette_write'
            e['next_source_use_scanline']=min(future)if future else None
            if y and future:latency=max(latency,min(future)-y)
            if y and not future:dead_writes+=1
        trace.append(dict(scanline=y,resident_before=copy.deepcopy(old),retained={b:[c for c in old[b]if c is not None and c in state[b]]for b in range(8)},
            evicted=[e['old']for e in events if e['old']is not None],prefetched=[e for e in events if e['kind']=='prefetch'],updates=events,
            colors_written=len(events),cgram_data_bytes=2*len(events),affected_banks=sorted({e['bank']for e in events})))
        span,groups=point_partition([16*e['bank']+e['slot']for e in events]if y else[])
        physical=[0 if s==0 else state[b][s-1]for b in range(8)for s in range(16)]
        packets.append(dict(scanline=y,prepared_commit_span=span,packets=[dict(cgram_word_address=128+lo,word_count=hi-lo+1,data_hex=b''.join(physical[a].to_bytes(2,'little')for a in range(lo,hi+1)).hex())for lo,hi in groups]))
        if any(line==y for line,x in gates):windows[str(y)]=compile_sparse_mask({x:solver.value(gate)for(line,x),gate in gates.items()if line==y})
        states.append(state);old=state
    images=[np.zeros((p['height'],p['width']),dtype=np.uint8)for p in source['pieces']];replay=np.asarray(background,dtype=np.uint16).copy();indices=np.zeros((height,256),dtype=np.uint8);changed_operands=changed_gates=0
    for p in points:
        y,x,b=p['y'],p['x'],p['bank'];enabled=b>=4 and evaluate(windows[str(y)],x);word=selected_word(p,enabled)
        if word is None:raise AssertionError('WINDOW_SLOT_SELECTED_MATH_UNREPRESENTABLE')
        changed_operands+=word!=p['old_word'];changed_gates+=enabled!=p['old_gate']
        slot=states[y][b].index(word)+1;images[p['piece']][p['ly'],p['lx']]=slot;indices[y,x]=128+16*b+slot
        replay[y,x]=apply_math(word,int(background[y,x]),source['selected_modes'][str(y)])if enabled else word
    if not np.array_equal(replay,expected):raise AssertionError('WINDOW_SLOT_COMPLETE_OUTPUT_FRAME_REPLAY')
    result=copy.deepcopy(source);masks=[]
    for image in images:
        flat=image.flatten();masks.append(dict(width=image.shape[1],height=image.shape[0],pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex(),packed_nibble_order='low then high'))
    for key in('bank_residency','physical_slot_layout','physical_slot_refinement','optimistic_bank_order'):
        if key in result:result['input_'+key]=result.pop(key)
    result.update(trace=trace,piece_pixel_masks=masks,compiled_color_window_descriptors=windows,prepared_dma_packets=packets,native_presentation_proven=False)
    for p,image in zip(result['pieces'],images):
        p['rows']={p['y']+ly:sorted({states[p['y']+ly][p['bank']][int(s)-1]for s in row if s})for ly,row in enumerate(image)if np.any(row)}
    verify_packets(result)
    if any(r['prepared_commit_span']>=(line_windows or{}).get(r['scanline'],window)for r in packets)or max(len(r['updates'])for r in trace[1:])>maximum_writes:raise AssertionError('WINDOW_SLOT_FULL_FRAME_PHYSICAL_WINDOW')
    if necessary_bank_window is not None:
        from raster_bank_residency import favorable_span
        if any(favorable_span(r['updates'])>=necessary_bank_window for r in trace[1:]):raise AssertionError('WINDOW_SLOT_BANK_PARTITION_REPLAY')
    demand(result)
    report.update(status='SOURCE_EXACT_WINDOW_SLOT_PACKETS_PROVEN',peak_prepared_commit_span=max(r['prepared_commit_span']for r in packets),
        peak_actual_palette_writes=max(len(r['updates'])for r in trace[1:]),complete_source_frame_pixel_identity_proven=True,
        pixel_color_identity_verified=True,all_packet_cgram_identities_verified=True,palette_operand_encoding_unchanged=changed_operands==0,
        changed_exact_pixel_operands=changed_operands,changed_observed_pixel_window_gates=changed_gates,
        peak_packet_data_bytes=max(sum(2*p['word_count']for p in r['packets'])for r in packets),
        peak_dma_chain_channels=max(max(0,2*len(r['packets'])-1)for r in packets),
        maximum_noninitial_prefetch_latency_lines=latency,noninitial_dead_palette_writes=dead_writes,
        initial_palette_may_preload_entire_frame=True)
    peak_writes=max(len(r['updates'])for r in trace[1:])
    result.update(peak_scheduled_writes=peak_writes,peak_cgram_data_bytes=2*peak_writes,average_writes=float(np.mean([len(r['updates'])for r in trace[1:]])),
        worst_scanline=max(trace[1:],key=lambda r:len(r['updates']))['scanline'],prepared_dma_window_master_clocks=window,
        prepared_dma_partition_bound_enforced=True,prepared_dma_window_is_optimistic_necessary_only=True,
        maximum_noninitial_prefetch_latency_lines=latency,lookahead_lines=last-first,write_budget=maximum_writes,
        schedule_latency_requirement=dict(maximum_noninitial_prefetch_lines=latency,initial_palette_may_preload_entire_frame=True),
        palette_encoding_authority='source_exact_window_slot_schedule')
    result.update(physical_slot_layout=report,compiled_indices_sha256=hashlib.sha256(indices.tobytes()).hexdigest(),
        input_compiled_schedule_sha256=source.get('compiled_schedule_sha256'),compiled_schedule_sha256=hashlib.sha256(json.dumps(dict(pieces=result['pieces'],pixel_masks=masks,trace=trace,selected_modes=result['selected_modes'],compiled_color_window_descriptors=windows),sort_keys=True).encode()).hexdigest(),
        compiled_transfer_descriptor_sha256=hashlib.sha256(json.dumps(packets,sort_keys=True).encode()).hexdigest())
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in('source','stage','scene','schedule','output'):p.add_argument('--'+name,required=True)
    p.add_argument('--window',type=int,default=337);p.add_argument('--time-limit',type=float,default=45);p.add_argument('--maximum-writes',type=int,default=21)
    p.add_argument('--necessary-bank-window',type=int);p.add_argument('--search-strategy',choices=('portfolio','lns'),default='portfolio')
    p.add_argument('--reuse-exact-operands',action='store_true')
    p.add_argument('--repair-interval',type=int,nargs=2)
    p.add_argument('--complete-exact-operands',action='store_true')
    a=p.parse_args()
    from compiler import Source
    from source_scene_obj_raster import prepare
    from source_scene_bg import compose_rgb8
    from source_bg_feasibility import rgb555
    source=Source(a.source);scene=json.loads(Path(a.scene).read_text());schedule=json.loads(Path(a.schedule).read_text())
    _,metadata,expected=prepare(source,a.stage,scene)
    if schedule['metadata']!=metadata:raise ValueError('WINDOW_SLOT_SOURCE_METADATA_IDENTITY')
    background=rgb555(compose_rgb8(source,a.stage,dict(scene,actors=[]))[0])
    result=optimize(schedule,background,rgb555(expected),a.window,a.time_limit,a.maximum_writes,a.necessary_bank_window,a.search_strategy,a.reuse_exact_operands,a.repair_interval,a.complete_exact_operands)
    Path(a.output).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result.get('physical_slot_layout',result)))


if __name__=='__main__':main()
