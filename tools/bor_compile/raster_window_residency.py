"""Exact source color-window choices with bank-specific cache residency.

Color residency precedes physical slot placement. The bank transfer DP grants
ideal endpoint packing; its bound alone never admits native presentation.
Every emitted full witness independently replays pixels and physical packets.
"""
import argparse,copy,hashlib,json
from pathlib import Path
import numpy as np
from raster_window_slot_schedule import derive
from raster_bank_residency import constrain_flow,favorable_span
from raster_physical_relabel import point_partition
from raster_math_windows import evaluate,compile_sparse_mask
from raster_obj_math_cover import apply_math,MODES
from raster_slot_greedy import demand
from raster_slot_refine import verify_packets


def optimize(source,background,expected,window=337,time_limit=45,maximum_writes=21,lookahead=16,solver_backend='cp-sat',movable_math_modes=False,feasibility_only=False,complete_operands=False,repair_interval=None):
    from ortools.sat.python import cp_model
    if window<1 or time_limit<=0 or type(maximum_writes)is not int or not 0<=maximum_writes<=120 or type(lookahead)is not int or lookahead<0:raise ValueError('WINDOW_RESIDENCY_DOMAIN')
    if solver_backend not in('cp-sat','highs'):raise ValueError('WINDOW_RESIDENCY_BACKEND')
    if type(feasibility_only)is not bool:raise ValueError('WINDOW_RESIDENCY_FEASIBILITY_POLICY')
    points,rows,tables,hint=derive(source,background,expected);first,last=min(rows),max(rows);height=len(source['trace'])
    if repair_interval is not None and(feasibility_only or not isinstance(repair_interval,(list,tuple))or len(repair_interval)!=2 or any(type(y)is not int for y in repair_interval)or not first<=repair_interval[0]<=repair_interval[1]<=last):
        raise ValueError('WINDOW_RESIDENCY_REPAIR_INTERVAL')
    if type(movable_math_modes)is not bool:raise ValueError('WINDOW_RESIDENCY_MODE_POLICY')
    if type(complete_operands)is not bool:raise ValueError('WINDOW_RESIDENCY_OPERAND_POLICY')
    complete_options=None;operand_proof=None
    if complete_operands:
        from raster_obj_math_cover import complete_math_cover
        contexts={(p['output'],int(background[p['y'],p['x']]),gate)for p in points if p['bank']>=4 for gate in(False,True)}
        complete_options,operand_proof=complete_math_cover(contexts,
            modes=MODES if movable_math_modes else tuple(dict.fromkeys(source['selected_modes'][str(p['y'])]for p in points)),
            tag_modes=True,fixed_window_context=True,retained_operands={p['old_word']for p in points if p['bank']>=4})
    potential={};inverse={}
    modes=MODES if movable_math_modes else ()
    for p in points:
        p['operands']={source['selected_modes'][str(p['y'])]:p['operand']}
        if movable_math_modes and p['bank']>=4:
            for mode in modes:
                operand=0
                for shift in(0,5,10):
                    target=p['output']>>shift&31;under=int(background[p['y'],p['x']])>>shift&31;key=mode,target,under
                    if key not in inverse:inverse[key]=next((c for c in range(32)if apply_math(c,under,mode)&31==target),None)
                    if inverse[key]is None:operand=None;break
                    operand|=inverse[key]<<shift
                if operand is not None and apply_math(operand,int(background[p['y'],p['x']]),mode)!=p['output']:raise AssertionError('WINDOW_RESIDENCY_MODE_INVERSE')
                p['operands'][mode]=operand
        p['mode_operands']={mode:tuple(sorted({c for c in(operand,p['old_word']if movable_math_modes and apply_math(p['old_word'],int(background[p['y'],p['x']]),mode)==p['output']else None)if c is not None}))for mode,operand in p['operands'].items()}
        if complete_options is not None and p['bank']>=4:
            p['mode_operands']={mode:tuple(complete_options[mode,p['output'],int(background[p['y'],p['x']]),True])for mode in p['operands']}
        for c in ([p['output']]if p['bank']<4 else[p['output'],*(c for choices in p['mode_operands'].values()for c in choices)]):
            if c is not None:potential.setdefault((p['bank'],c),set()).add(p['y'])
    tables=[sorted(c for bank,c in potential if bank==b)for b in range(8)]
    model=cp_model.CpModel();resident={};writes={};gates={};mode_choices={};peak=model.new_int_var(0,4096,'idealPeak');costs=[];bank_counts={};start_relations=[];inverted_rows={};prefix_variables={}
    for y in range(first,last+1):
        if movable_math_modes:
            for mode in modes:
                choice=model.new_bool_var(f'mode{y}_{mode}');mode_choices[y,mode]=choice
                model.add_hint(choice,int(mode==source['selected_modes'][str(y)]))
            model.add(sum(mode_choices[y,mode]for mode in modes)==1)
        for b in range(8):
            for c in tables[b]:
                if y>max(potential[b,c]):
                    resident[y,b,c]=model.new_constant(0)
                    if y>first:writes[y,b,c]=model.new_constant(0)
                    continue
                r=model.new_bool_var(f'resident{y}_{b}_{c}');resident[y,b,c]=r;model.add_hint(r,int(c in hint[y][b]))
                if y>first:
                    w=model.new_bool_var(f'new{y}_{b}_{c}');writes[y,b,c]=w
                    old=resident[y-1,b,c];model.add(w<=r);model.add(w<=1-old);model.add(w>=r-old)
                    model.add_hint(w,int(c in hint[y][b]and c not in hint[y-1][b]))
                    if not any(y<=t<=y+lookahead for t in potential[b,c]):model.add(w==0)
            if tables[b]:model.add(sum(resident[y,b,c]for c in tables[b])<=15)
        xs=sorted({p['x']for p in rows.get(y,[])if p['bank']>=4});starts=[];negative_starts=[];previous=model.new_constant(0);previous_negative=model.new_constant(0)
        for x in xs:
            gate=model.new_bool_var(f'gate{y}_{x}');gates[y,x]=gate;model.add_hint(gate,int(evaluate(source['compiled_color_window_descriptors'][str(y)],x)))
            for value,old,collection in((gate,previous,starts),(gate.Not(),previous_negative,negative_starts)):
                start=model.new_bool_var(f'start{y}_{x}_{len(collection)}_{len(starts)}');model.add(start<=value);model.add(start<=1-old);model.add(start>=value-old);collection.append(start)
                start_relations.append((start,value,old))
            previous=gate;previous_negative=gate.Not()
        if xs:
            inverted=model.new_bool_var(f'inverted{y}');model.add(sum(starts)<=2+len(xs)*inverted);model.add(sum(negative_starts)<=2+len(xs)*(1-inverted))
            model.add_hint(inverted,int(bool(source['compiled_color_window_descriptors'][str(y)]['wobjsel_color_bits']&0x50)))
            inverted_rows[y]=(inverted,starts,negative_starts)
        for p in rows.get(y,[]):
            b=p['bank'];out=p['output'];operand=p['operand']
            if b<4:model.add(resident[y,b,out]==1)
            else:
                gate=gates[y,p['x']];model.add(resident[y,b,out]>=1-gate)
                if movable_math_modes:
                    for mode in modes:
                        choice=mode_choices[y,mode];choices=p['mode_operands'][mode]
                        if not choices:model.add(choice+gate<=1)
                        else:model.add(sum(resident[y,b,word]for word in choices)>=choice+gate-1)
                elif not p['mode_operands'][source['selected_modes'][str(y)]]:model.add(gate==0)
                else:model.add(sum(resident[y,b,c]for c in p['mode_operands'][source['selected_modes'][str(y)]])>=gate)
        if y>first:
            counts=[];active=[]
            for b in range(8):
                n=model.new_int_var(0,15,f'count{y}_{b}');model.add(n==sum(writes[y,b,c]for c in tables[b]));counts.append(n)
                bank_counts[y,b]=n
                a=model.new_bool_var(f'active{y}_{b}');model.add(n>=a);model.add(n<=15*a);active.append(a)
            model.add(sum(counts)<=maximum_writes)
            cost=constrain_flow(model,counts,active,window,f'row{y}',linear=True)
            if repair_interval is None or repair_interval[0]<=y<=repair_interval[1]:model.add(peak>=cost)
            costs.append(cost)
    mandatory={}
    for p in points:
        if p['bank']<4 or all(c==p['output']for choices in p['mode_operands'].values()for c in choices):mandatory.setdefault((p['y'],p['bank']),set()).add(p['output'])
    cuts=0
    for b in range(8):
        prefix={first:model.new_constant(0)}
        for y in range(first+1,last+1):
            prefix[y]=model.new_int_var(0,15*(y-first),f'prefix{y}_{b}');model.add(prefix[y]==prefix[y-1]+bank_counts[y,b])
            prefix_variables[y,b]=prefix[y]
        for left in range(first,last):
            union=set()
            for right in range(left,last+1):
                union.update(mandatory.get((right,b),set()))
                if len(union)>15:model.add(prefix[right]-prefix[left]>=len(union)-15);cuts+=1
    factor=4096*len(costs)+1
    if not feasibility_only:model.minimize(peak*factor+sum(costs))
    # A source schedule supplies a concrete feasible start whenever its cache
    # fits this model's window/corpus. Check every variable and constraint before
    # replacing partial hints; a too-tight start never becomes hard evidence.
    import re
    from raster_bank_residency import flow_partition_hint
    values={i:list(v.domain)[0]for i,v in enumerate(model.proto.variables)}
    for(y,b,c),v in resident.items():
        domain=list(v.proto.domain)
        if domain[0]!=domain[-1]:values[v.index]=int(c in hint[y][b])
    for(y,b,c),v in writes.items():
        domain=list(v.proto.domain)
        if domain[0]!=domain[-1]:values[v.index]=int(values[resident[y,b,c].index]and not values[resident[y-1,b,c].index])
    for(y,x),v in gates.items():values[v.index]=int(evaluate(source['compiled_color_window_descriptors'][str(y)],x))
    for(y,mode),v in mode_choices.items():values[v.index]=int(mode==source['selected_modes'][str(y)])
    literal=lambda v:values[v.index]if v.index>=0 else 1-values[-v.index-1]
    for v,current,previous in start_relations:values[v.index]=int(literal(current)and not literal(previous))
    for y,(v,positive,negative)in inverted_rows.items():values[v.index]=int(sum(values[q.index]for q in positive)>2)
    counts_by_line={y:[sum(values[writes[y,b,c].index]for c in tables[b])for b in range(8)]for y in range(first+1,last+1)}
    groups={};line_costs={}
    for y,counts in counts_by_line.items():
        line_costs[y],groups[y]=flow_partition_hint(counts)
        for b,n in enumerate(counts):values[bank_counts[y,b].index]=n
    for(y,b),v in prefix_variables.items():values[v.index]=sum(counts_by_line[t][b]for t in range(first+1,y+1))
    for i,v in enumerate(model.proto.variables):
        match=re.fullmatch(r'active(\d+)_(\d+)',v.name)
        if match:values[i]=int(counts_by_line[int(match[1])][int(match[2])]>0)
        match=re.fullmatch(r'row(\d+)(interval|cost)(\d+)_(\d+)',v.name)
        if match:
            y,kind,a,b=int(match[1]),match[2],int(match[3]),int(match[4]);selected=(a,b)in groups[y]
            values[i]=int(selected)if kind=='interval'else(24+16*(counts_by_line[y][a]if a==b else counts_by_line[y][a]+counts_by_line[y][b]+16*(b-a-1)+1)if selected else 0)
    values[peak.index]=max((cost for y,cost in line_costs.items()if repair_interval is None or repair_interval[0]<=y<=repair_interval[1]),default=0)
    violations=[]
    for i,v in enumerate(model.proto.variables):
        d=list(v.domain)
        if not any(d[j]<=values[i]<=d[j+1]for j in range(0,len(d),2)):violations.append('variable:'+v.name)
    for i,c in enumerate(model.proto.constraints):
        if not all(values[n]if n>=0 else 1-values[-n-1]for n in c.enforcement_literal):continue
        if not c.has_linear():raise ValueError('WINDOW_RESIDENCY_COMPLETE_HINT_CONSTRAINT_KIND')
        total=sum(values[n]*k for n,k in zip(c.linear.vars,c.linear.coeffs));d=list(c.linear.domain)
        if not any(d[j]<=total<=d[j+1]for j in range(0,len(d),2)):violations.append('constraint:'+str(i))
    if not violations:
        model.clear_hints()
        for i,v in values.items():model.add_hint(model.get_int_var_from_proto_index(i),v)
    repair_fixed={}
    if repair_interval is not None:
        if violations:raise ValueError('WINDOW_RESIDENCY_REPAIR_REQUIRES_VERIFIED_COMPLETE_HINT')
        for key,v in list(resident.items())+list(writes.items())+list(gates.items())+list(mode_choices.items()):
            if not repair_interval[0]<=key[0]<=repair_interval[1]:repair_fixed[v.index]=v
        for i,v in repair_fixed.items():model.add(v==values[i])
    if solver_backend=='highs':
        from raster_bank_residency import solve_linear
        value,details=solve_linear(model,time_limit);bound=details.get('solver_objective_lower_bound',0)
    else:
        solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit;solver.parameters.num_search_workers=4;solver.parameters.cp_model_probing_level=0
        status=solver.solve(model);value=solver.value if status in(cp_model.FEASIBLE,cp_model.OPTIMAL)else None;bound=solver.best_objective_bound
        details=dict(solver_backend='cp-sat',solver_status=solver.status_name(status),solver_seconds=solver.wall_time,solver_branches=solver.num_branches,solver_conflicts=solver.num_conflicts,solver_model_variables=len(model.proto.variables),solver_model_constraints=len(model.proto.constraints))
    report=dict(schema='BYOR_WINDOW_BANK_RESIDENCY_V1',status='BOUNDED_WINDOW_BANK_RESIDENCY_NO_CANDIDATE',**details,requested_ideal_window=window,bounded_noninitial_lookahead_lines=lookahead,initial_palette_may_preload_entire_frame=True,ideal_endpoint_slot_packing_relaxed=True,fixed_piece_banks_unchanged=True,piece_banks_fixed_across_all_scanlines=True,restricted_family_ideal_prepared_span_lower_bound=max(0,int(bound//factor)-40),native_timing_admitted=False,universal_raster_rejected=False,no_color_reduction=True)
    report['mandatory_identity_bank_interval_cuts']=cuts
    report.update(complete_source_hint_model_verified=not violations,complete_source_hint_variables=len(values),
        complete_source_hint_violation_count=len(violations),complete_source_hint_first_violations=violations[:8])
    report.update(repair_interval=repair_interval,repair_fixed_variables=len(repair_fixed),
        outside_repair_cache_modes_and_pixel_gates_fixed=repair_interval is not None,
        objective_bound_scope='REPAIR_INTERVAL_WITH_FIXED_EXTERIOR'if repair_interval is not None else'FULL_FIXED_GEOMETRY_FRAME')
    report['search_objective']='FEASIBILITY_ONLY'if feasibility_only else'PEAK_THEN_TOTAL_IDEAL_DMA_COST'
    report['maximum_writes_per_line']=maximum_writes
    if feasibility_only:report['restricted_family_ideal_prepared_span_lower_bound']=0
    report.update(shared_scanline_math_mode_search=movable_math_modes,math_operand_family='CANONICAL_EXACT_INVERSE_AND_INPUT_WORD'if movable_math_modes else'INPUT_MODE_WITH_CANONICAL_EXACT_INVERSE')
    if complete_operands:
        report.update(math_operand_family='COMPLETE_FRAME_GLOBAL_MODE_AND_WINDOW_CONTEXT_COVER',operand_cover=operand_proof,
            cross_scanline_operand_identity_reuse_preserved=True,input_upper_bank_operand_identities_retained=True)
    if value is None:return report
    selected_modes=copy.deepcopy(source['selected_modes'])
    if movable_math_modes:
        for y in range(first,last+1):selected_modes[str(y)]=next(mode for mode in modes if value(mode_choices[y,mode]))
    report['changed_scanline_math_modes']=sum(selected_modes[y]!=mode for y,mode in source['selected_modes'].items())
    selected_required={};uses={b:{}for b in range(8)}
    for p in points:
        enabled=p['bank']>=4 and value(gates[p['y'],p['x']])
        word=next(c for c in p['mode_operands'][selected_modes[str(p['y'])]]if value(resident[p['y'],p['bank'],c]))if enabled else p['output']
        p['selected_word']=word
        selected_required.setdefault((p['y'],p['bank']),set()).add(word);uses[p['bank']].setdefault(word,[]).append(p['y'])
    state={b:[None]*15 for b in range(8)};states=[];trace=[];packets=[];windows=copy.deepcopy(source['compiled_color_window_descriptors']);latency=dead_writes=0
    for y in range(height):
        line=max(first,min(last,y));before=copy.deepcopy(state);events=[]
        for b in range(8):
            members={c for c in tables[b]if value(resident[line,b,c])}
            if y==0:
                state[b]=sorted(members)+[0]*(15-len(members))
            else:
                missing=sorted(members-set(state[b]));available=[s for s,c in enumerate(state[b])if c not in members]
                # Duplicate resident words occupy only one required slot.
                seen=set()
                for s,c in enumerate(state[b]):
                    if c in members:
                        if c in seen:available.append(s)
                        seen.add(c)
                if len(available)<len(missing):raise AssertionError('WINDOW_RESIDENCY_SLOT_CAPACITY')
                for s,c in zip(sorted(available),missing):state[b][s]=c
            events.extend(dict(bank=b,slot=s+1,old=before[b][s],color=c,kind='residency_palette')for s,c in enumerate(state[b])if c!=before[b][s])
        for e in events:
            future=[t for t in uses[e['bank']].get(e['color'],[])if t>=y]
            e['kind']='required'if e['color']in selected_required.get((y,e['bank']),set())else'prefetch'if future else'unused_initial'if y==0 else'dead_palette_write'
            e['next_source_use_scanline']=min(future)if future else None
            if y and future:latency=max(latency,min(future)-y)
            if y and not future:dead_writes+=1
        trace.append(dict(scanline=y,resident_before=before,retained={b:[c for c in before[b]if c is not None and c in state[b]]for b in range(8)},evicted=[e['old']for e in events if e['old']is not None],prefetched=[e for e in events if e['kind']=='prefetch'],updates=events,colors_written=len(events),cgram_data_bytes=2*len(events),affected_banks=sorted({e['bank']for e in events})))
        physical=[0 if s==0 else state[b][s-1]for b in range(8)for s in range(16)];span,ranges=point_partition([16*e['bank']+e['slot']for e in events]if y else[])
        packets.append(dict(scanline=y,prepared_commit_span=span,packets=[dict(cgram_word_address=128+lo,word_count=hi-lo+1,data_hex=b''.join(physical[a].to_bytes(2,'little')for a in range(lo,hi+1)).hex())for lo,hi in ranges]))
        line_gates={x:value(gate)for(line,x),gate in gates.items()if line==y}
        if line_gates:windows[str(y)]=compile_sparse_mask(line_gates)
        states.append(copy.deepcopy(state))
    images=[np.zeros((p['height'],p['width']),dtype=np.uint8)for p in source['pieces']];replay=np.asarray(background,dtype=np.uint16).copy();indices=np.zeros_like(replay,dtype=np.uint8)
    for p in points:
        y,x,b=p['y'],p['x'],p['bank'];gate=b>=4 and evaluate(windows[str(y)],x);word=p['selected_word']
        slot=states[y][b].index(word)+1;images[p['piece']][p['ly'],p['lx']]=slot;indices[y,x]=128+16*b+slot
        replay[y,x]=apply_math(word,int(background[y,x]),selected_modes[str(y)])if gate else word
    if not np.array_equal(replay,expected):raise AssertionError('WINDOW_RESIDENCY_COMPLETE_FRAME_REPLAY')
    result=copy.deepcopy(source);masks=[]
    for p,image in zip(result['pieces'],images):
        flat=image.flatten();masks.append(dict(width=p['width'],height=p['height'],pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex()))
        p['rows']={p['y']+ly:sorted({states[p['y']+ly][p['bank']][int(s)-1]for s in row if s})for ly,row in enumerate(image)if np.any(row)}
    for name in('physical_slot_layout','bank_residency','physical_slot_refinement','optimistic_bank_order'):
        if name in result:result['input_'+name]=result.pop(name)
    if any(favorable_span(r['updates'])>=window for r in trace[1:])or any(len(r['updates'])>maximum_writes for r in trace[1:]):raise AssertionError('WINDOW_RESIDENCY_INDEPENDENT_BANK_BOUND')
    peak_writes=max(len(r['updates'])for r in trace[1:])
    if repair_interval is not None:report['repair_interval_ideal_peak_prepared_commit_span']=max(favorable_span(r['updates'])for r in trace[1:]if repair_interval[0]<=r['scanline']<=repair_interval[1])
    report.update(status='SOURCE_EXACT_WINDOW_BANK_RESIDENCY_PROVEN',complete_source_frame_pixel_identity_proven=True,ideal_peak_prepared_commit_span=max(favorable_span(r['updates'])for r in trace[1:]),peak_emitted_prepared_commit_span=max(r['prepared_commit_span']for r in packets),peak_actual_palette_writes=peak_writes,all_packet_cgram_identities_verified=True,physical_slot_window_admitted=False,maximum_noninitial_prefetch_latency_lines=latency,noninitial_dead_palette_writes=dead_writes,peak_packet_data_bytes=max(sum(2*p['word_count']for p in r['packets'])for r in packets))
    result.update(trace=trace,piece_pixel_masks=masks,prepared_dma_packets=packets,compiled_color_window_descriptors=windows,selected_modes=selected_modes,bank_residency=report,native_presentation_proven=False)
    result.update(peak_scheduled_writes=peak_writes,peak_cgram_data_bytes=2*peak_writes,average_writes=float(np.mean([len(r['updates'])for r in trace[1:]])),worst_scanline=max(trace[1:],key=lambda r:len(r['updates']))['scanline'],prepared_dma_partition_bound_enforced=False,prepared_dma_window_is_optimistic_necessary_only=True,maximum_noninitial_prefetch_latency_lines=latency,schedule_latency_requirement=dict(maximum_noninitial_prefetch_lines=latency,initial_palette_may_preload_entire_frame=True))
    verify_packets(result);demand(result)
    result['compiled_indices_sha256']=hashlib.sha256(indices.tobytes()).hexdigest();result['input_compiled_schedule_sha256']=source.get('compiled_schedule_sha256')
    result['compiled_schedule_sha256']=hashlib.sha256(json.dumps(dict(pieces=result['pieces'],pixel_masks=masks,trace=trace,windows=windows,selected_modes=result['selected_modes'],source_rgb555_sha256=result['source_rgb555_sha256']),sort_keys=True).encode()).hexdigest();result['compiled_transfer_descriptor_sha256']=hashlib.sha256(json.dumps(packets,sort_keys=True).encode()).hexdigest()
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in('source','stage','scene','schedule','output'):p.add_argument('--'+name,required=True)
    p.add_argument('--window',type=int,default=337);p.add_argument('--time-limit',type=float,default=45);p.add_argument('--solver-backend',choices=('cp-sat','highs'),default='cp-sat');p.add_argument('--movable-math-modes',action='store_true');p.add_argument('--lookahead',type=int,default=16);p.add_argument('--feasibility-only',action='store_true');p.add_argument('--maximum-writes',type=int,default=21);p.add_argument('--complete-operands',action='store_true');p.add_argument('--repair-interval',type=int,nargs=2);a=p.parse_args()
    from compiler import Source
    from source_scene_obj_raster import prepare
    from source_scene_bg import compose_rgb8
    from source_bg_feasibility import rgb555
    source=Source(a.source);scene=json.loads(Path(a.scene).read_text(encoding='utf-8'));schedule=json.loads(Path(a.schedule).read_text(encoding='utf-8'));_,metadata,expected=prepare(source,a.stage,scene)
    if metadata!=schedule['metadata']:raise ValueError('WINDOW_RESIDENCY_AUTHORED_METADATA')
    result=optimize(schedule,rgb555(compose_rgb8(source,a.stage,dict(scene,actors=[]))[0]),rgb555(expected),a.window,a.time_limit,maximum_writes=a.maximum_writes,lookahead=a.lookahead,solver_backend=a.solver_backend,movable_math_modes=a.movable_math_modes,feasibility_only=a.feasibility_only,complete_operands=a.complete_operands,repair_interval=a.repair_interval)
    result.update(source_pak_sha256=hashlib.sha256(Path(a.source).read_bytes()).hexdigest(),
        source_input_sha256=hashlib.sha256(Path(a.schedule).read_bytes()).hexdigest(),source_input_path=a.schedule)
    Path(a.output).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result.get('bank_residency',result)))


if __name__=='__main__':main()
