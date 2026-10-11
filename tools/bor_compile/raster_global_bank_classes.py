"""Joint eligible global-word banks with a shared scanline tile ceiling.

Each word/eligibility domain has one fixed bank for the frame. Rolling unions
are a restricted cache construction. OAM/sprite admission is deferred to legal
geometry compaction; pixel identity and the requested tile ceiling are replayed.
"""
import itertools


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


def assign_masks(pieces,time_limit=30,residency_window_lines=None,maximum_tile_slivers=34):
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
    for y in active_rows:
        needed={key for yy,key in users if y<=yy<y+window}
        for b in range(8):
            variables=[words[key][b]for key in needed if b in words[key]]
            if variables:model.add(sum(variables)<=15)
    model.minimize(sum(masks.values()))
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit;solver.parameters.num_search_workers=4
    solver.parameters.cp_model_probing_level=0;solver.parameters.use_sat_inprocessing=False
    status=solver.solve(model)
    result=dict(schema='BYOR_JOINT_GLOBAL_WORD_BANK_CLASSES_V1',status='BOUNDED_JOINT_GLOBAL_BANK_CLASSES_NO_CANDIDATE',
        solver_status=solver.status_name(status),solver_seconds=solver.wall_time,solver_variables=len(model.proto.variables),
        solver_constraints=len(model.proto.constraints),solver_branches=solver.num_branches,solver_conflicts=solver.num_conflicts,
        maximum_tile_slivers=maximum_tile_slivers,residency_window_lines=residency_window_lines,
        global_word_bank_identity_restricted=True,oam_and_sprite_admission_deferred=True,
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
    return result
