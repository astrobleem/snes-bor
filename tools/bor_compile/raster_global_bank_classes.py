"""Joint eligible global-word banks with a shared scanline tile ceiling.

Each word/eligibility domain has one fixed bank for the frame. Rolling unions
are a restricted cache construction. OAM/sprite admission is deferred to legal
geometry compaction; pixel identity and the requested tile ceiling are replayed.
"""
import itertools


def persistent_index_bound(schedule,slots=15,time_limit=10):
    """Color-conflict test for constant word indices under the input banks.

    A failure rejects constant indices for these banks only. Raster pixels may
    still use different indices for equal words on different source rows.
    """
    from ortools.sat.python import cp_model
    from raster_slot_greedy import demand
    if type(slots)is not int or slots<1 or time_limit<=0:raise ValueError('PERSISTENT_INDEX_BOUND_DOMAIN')
    required,uses,_=demand(schedule);reports=[]
    for b in range(8):
        if not uses[b]:continue
        model=cp_model.CpModel();variables={c:model.new_int_var(0,slots-1,f'word{c}')for c in uses[b]}
        anchor=max((row[b]for row in required),key=len)
        for index,c in enumerate(sorted(anchor)):model.add(variables[c]==index)
        seen=set()
        for row in required:
            colors=tuple(sorted(row[b]))
            if len(colors)>1 and colors not in seen:model.add_all_different([variables[c]for c in colors]);seen.add(colors)
        solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit;solver.parameters.num_search_workers=4
        status=solver.solve(model)
        reports.append(dict(bank=b,distinct_words=len(variables),row_conflict_sets=len(seen),status=solver.status_name(status),seconds=solver.wall_time))
    return dict(schema='BYOR_FIXED_BANK_PERSISTENT_INDEX_BOUND_V1',slots_per_bank=slots,banks=reports,
        fixed_word_indices_rejected=any(r['status']=='INFEASIBLE'for r in reports),input_banks_and_pixel_words_fixed=True,
        slot_labels_canonicalized_without_transfer_constraints=True,physical_transfer_admitted=False,
        native_timing_admitted=False,universal_raster_rejected=False,no_color_reduction=True)


def permutation_bound(schedule):
    """Exhaustive favorable transfer bound for eligible fixed bank relabelings."""
    from raster_slot_greedy import demand
    from raster_bank_residency import favorable_span
    demand(schedule);additive=schedule.get('color_math','additive')!='precomposited'
    rows=[r['updates']for r in schedule['trace'][1:]if r['updates']];best=None;checked=0
    candidates=(a+b for a in itertools.permutations(range(4))for b in itertools.permutations(range(4,8)))if additive else itertools.permutations(range(8))
    for mapping in candidates:
        if any(mapping[p['bank']]not in p.get('allowed_banks',range(8))for p in schedule['pieces']):continue
        checked+=1;costs=[favorable_span([dict(e,bank=mapping[e['bank']])for e in row])for row in rows]
        key=(max(costs,default=0),sum(costs),mapping)
        if best is None or key<best:best=key
    return dict(schema='BYOR_ELIGIBLE_FIXED_BANK_PERMUTATION_BOUND_V1',legal_permutations_checked=checked,
        minimum_peak_favorable_span=None if best is None else best[0],sum_favorable_spans=None if best is None else best[1],
        best_bank_mapping=None if best is None else list(best[2]),write_times_and_word_residency_fixed=True,
        math_bank_eligibility_preserved=True,physical_slots_relaxed=True,native_timing_admitted=False,universal_raster_rejected=False)


def assign_masks(pieces,time_limit=30,residency_window_lines=None,maximum_tile_slivers=34,persistent_word_indices=False):
    from ortools.sat.python import cp_model
    if time_limit<=0 or not 1<=maximum_tile_slivers<=34 or(residency_window_lines is not None and(type(residency_window_lines)is not int or residency_window_lines<1)):
        raise ValueError('JOINT_GLOBAL_BANK_CLASS_DOMAIN')
    model=cp_model.CpModel();masks={};words={};users={};domains={}
    for i,p in enumerate(pieces):
        allowed=tuple(sorted(set(p.get('allowed_banks',range(8)))))
        if not allowed or any(type(b)is not int or not 0<=b<8 for b in allowed):raise ValueError('JOINT_GLOBAL_BANK_CLASS_ELIGIBILITY')
        if p['width']not in(8,16,32)or p['height']!=p['width']:raise ValueError('JOINT_GLOBAL_BANK_CLASS_GEOMETRY')
        domains[i]=allowed
        for b in allowed:masks[i,b]=model.new_bool_var(f'mask{i}_{b}')
        for y,colors in p['rows'].items():
            for c in colors:
                if type(c)is not int or not 0<=c<32768:raise ValueError('JOINT_GLOBAL_BANK_CLASS_WORD')
                key=allowed,c
                if key not in words:
                    words[key]={b:model.new_bool_var(f'word{len(words)}_{b}')for b in allowed}
                    model.add_exactly_one(list(words[key].values()))
                users.setdefault((int(y),key),set()).add(i)
    by_mask={key:[]for key in masks}
    for(y,key),indices in users.items():
        for i in indices:
            for b,v in words[key].items():
                model.add(masks[i,b]>=v);by_mask[i,b].append(v)
    for key,variables in by_mask.items():model.add(masks[key]<=sum(set(variables)))
    height=max((p['y']+p['height']for p in pieces),default=0)
    for y in range(height):
        live=[(i,b)for i,p in enumerate(pieces)if p['y']<=y<p['y']+p['height']for b in domains[i]]
        model.add(sum(masks[i,b]*(pieces[i]['width']//8)for i,b in live)<=maximum_tile_slivers)
    active_rows=sorted({y for y,key in users});window=residency_window_lines or 1
    anchor=set()
    indices={}
    if persistent_word_indices:
        for key,variables in words.items():
            index=model.new_int_var_from_domain(cp_model.Domain.from_values([16*b+s for b in variables for s in range(1,16)]),f'index{len(indices)}')
            indices[key]=index
            for b,v in variables.items():
                model.add(index>=16*b+1).only_enforce_if(v);model.add(index<=16*b+15).only_enforce_if(v)
    for y in active_rows:
        needed={key for yy,key in users if y<=yy<y+window}
        if indices:
            model.add_all_different([indices[key]for key in needed])
            if len(needed)>len(anchor):anchor=needed
        for b in range(8):
            variables=[words[key][b]for key in needed if b in words[key]]
            if variables:model.add(sum(variables)<=15)
    # Slot labels have no transfer cost in this geometry-only constructor.
    # A co-live clique has distinct slots in each chosen bank, so sort just
    # those slots within each bank to remove equivalent label permutations.
    if indices:
        preceding=[]
        for key in sorted(anchor):
            for b,v in words[key].items():
                rank=sum(words[old][b]for old in preceding if b in words[old])
                model.add(indices[key]==16*b+1+rank).only_enforce_if(v)
            preceding.append(key)
    model.minimize(sum(masks.values()))
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit;solver.parameters.num_search_workers=4
    solver.parameters.cp_model_probing_level=0;solver.parameters.use_sat_inprocessing=False
    status=solver.solve(model)
    result=dict(schema='BYOR_JOINT_GLOBAL_WORD_BANK_CLASSES_V1',status='BOUNDED_JOINT_GLOBAL_BANK_CLASSES_NO_CANDIDATE',
        solver_status=solver.status_name(status),solver_seconds=solver.wall_time,solver_variables=len(model.proto.variables),
        solver_constraints=len(model.proto.constraints),solver_branches=solver.num_branches,solver_conflicts=solver.num_conflicts,
        maximum_tile_slivers=maximum_tile_slivers,residency_window_lines=residency_window_lines,
        global_word_bank_identity_restricted=True,oam_and_sprite_admission_deferred=True,
        persistent_word_indices=persistent_word_indices,persistent_slot_symmetry_anchor_words=len(anchor),
        persistent_slot_symmetry_excludes_transfer_constraints=True,
        physical_transfer_admitted=False,native_timing_admitted=False,universal_raster_rejected=False,no_color_reduction=True)
    if status not in(cp_model.OPTIMAL,cp_model.FEASIBLE):return result
    expanded=[];assignment=[]
    for i,p in enumerate(pieces):
        for b in domains[i]:
            rows={int(y):[c for c in colors if solver.value(words[domains[i],c][b])]for y,colors in p['rows'].items()}
            if any(rows.values()):expanded.append(dict(p,rows=rows,source_piece=i));assignment.append(b)
    for i,p in enumerate(pieces):
        for y,colors in p['rows'].items():
            recovered=[c for q in expanded if q['source_piece']==i for c in q['rows'].get(int(y),[])]
            if sorted(recovered)!=sorted(colors):raise AssertionError('JOINT_GLOBAL_BANK_CLASS_PIXEL_WORDS')
    peak_tiles=max((sum(p['width']//8 for p in expanded if p['y']<=y<p['y']+p['height'])for y in range(height)),default=0)
    if peak_tiles>maximum_tile_slivers:raise AssertionError('JOINT_GLOBAL_BANK_CLASS_TILE_CEILING')
    for y in active_rows:
        for b in range(8):
            colors={c for p,bank in zip(expanded,assignment)if bank==b for yy,cs in p['rows'].items()if y<=yy<y+window for c in cs}
            if len(colors)>15:raise AssertionError('JOINT_GLOBAL_BANK_CLASS_WINDOW_CAPACITY')
    result.update(status='JOINT_GLOBAL_BANK_MASK_WORD_IDENTITIES_PROVEN',pieces=expanded,assignment=assignment,
        objective=float(solver.objective_value),lower_bound=float(solver.best_objective_bound),peak_tile_slivers=peak_tiles,
        oam_entries=len(expanded),peak_sprites=max((sum(p['y']<=y<p['y']+p['height']for p in expanded)for y in range(height)),default=0),
        pixel_word_identities_replayed=True)
    if indices:
        result['word_slot_indices']=[dict(allowed_banks=list(key[0]),color=key[1],obj_palette_word_offset=solver.value(v))for key,v in sorted(indices.items())]
    return result


def fixed_slot_schedule(pieces,assignment,word_slot_indices,height):
    """Timing-free exact fixed-word index template for later liveness search."""
    import copy
    indices={(tuple(v['allowed_banks']),v['color']):v['obj_palette_word_offset']for v in word_slot_indices}
    wanted=[{}for _ in range(height)]
    for p,b in zip(pieces,assignment):
        for y,colors in p['rows'].items():
            for c in colors:
                address=indices[tuple(p['allowed_banks']),c];bank,slot=divmod(address,16)
                if bank!=b or not 1<=slot<=15:raise AssertionError('FIXED_WORD_SLOT_BANK_IDENTITY')
                if address in wanted[int(y)]and wanted[int(y)][address]!=c:raise AssertionError('FIXED_WORD_SLOT_ROW_CONFLICT')
                wanted[int(y)][address]=c
    initial={}
    for row in wanted:
        for address,c in row.items():initial.setdefault(address,c)
    state={b:[None]*15 for b in range(8)};trace=[];snapshots=[]
    for y,row in enumerate(wanted):
        before=copy.deepcopy(state);events=[]
        for address,c in sorted((initial if y==0 else row).items()):
            b,slot=divmod(address,16)
            if state[b][slot-1]!=c:
                events.append(dict(bank=b,slot=slot,old=state[b][slot-1],color=c,kind='required'if row.get(address)==c else'prefetch'));state[b][slot-1]=c
        if any(state[address//16][address%16-1]!=c for address,c in row.items()):raise AssertionError('FIXED_WORD_SLOT_TEMPLATE_REPLAY')
        trace.append(dict(scanline=y,resident_before=before,updates=events,colors_written=len(events),cgram_data_bytes=2*len(events),affected_banks=sorted({e['bank']for e in events})))
        snapshots.append(copy.deepcopy(state))
    return trace,snapshots
