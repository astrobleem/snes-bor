"""Joint eligible global-word banks with a shared scanline tile ceiling.

Each word/eligibility domain has one fixed bank for the frame. Rolling unions
are a restricted cache construction. OAM/sprite admission is deferred to legal
geometry compaction; pixel identity and the requested tile ceiling are replayed.
"""
import itertools
from raster_obj_geometry import active_on_line,tile_slivers


def rebuild_schedule(source,search,lookahead=16):
    """Compile admitted masks and replay every input operand/transparency pixel."""
    import copy,hashlib,json
    import numpy as np
    from raster_slot_greedy import demand,bank_groups
    from raster_palette import schedule as logical_schedule
    if search.get('status')!='JOINT_GLOBAL_BANK_MASK_WORD_IDENTITIES_PROVEN' or not search.get('pixel_word_identities_replayed') or lookahead<0:raise ValueError('GLOBAL_BANK_REBUILD_VALIDATED_SEARCH')
    _,_,old_images=demand(source);height=len(source['trace']);pieces=copy.deepcopy(search['pieces']);assignment=search['assignment']
    if len(pieces)!=len(assignment):raise ValueError('GLOBAL_BANK_REBUILD_PIECE_COUNT')
    groups=bank_groups(source);filtered=[];expected={};replayed={}
    fields=('actor','x','y','local_x','local_y','width','height')
    for p,image in zip(source['pieces'],old_images):
        for ly,lx in zip(*np.where(image>=0)):
            key=p['actor'],p['y']+int(ly),p['x']+int(lx)
            if key in expected:raise ValueError('GLOBAL_BANK_REBUILD_INPUT_OVERLAP')
            expected[key]=int(image[ly,lx])
    for p,bank in zip(pieces,assignment):
        i=p['source_piece']
        if type(i)is not int or not 0<=i<len(old_images):raise ValueError('GLOBAL_BANK_REBUILD_SOURCE_PIECE')
        old=source['pieces'][i]
        if any(p.get(f)!=old.get(f)for f in fields):raise ValueError('GLOBAL_BANK_REBUILD_GEOMETRY')
        domain=next(g for g in groups if old['bank']in g)
        if bank not in domain or bank not in old.get('allowed_banks',range(8)):raise ValueError('GLOBAL_BANK_REBUILD_BANK_ELIGIBILITY')
        p['bank']=bank;p['rows']={int(y):list(cs)for y,cs in p['rows'].items()}
        image=np.full(old_images[i].shape,-1,dtype=np.int32)
        for ly,lx in zip(*np.where(old_images[i]>=0)):
            y,x=p['y']+int(ly),p['x']+int(lx);word=int(old_images[i][ly,lx])
            if word not in p['rows'].get(y,[]):continue
            key=p['actor'],y,x
            if key in replayed:raise ValueError('GLOBAL_BANK_REBUILD_OUTPUT_OVERLAP')
            replayed[key]=word;image[ly,lx]=word
        for y,cs in p['rows'].items():
            ly=y-p['y']
            if not 0<=ly<len(image)or set(cs)!=set(map(int,image[ly][image[ly]>=0])):raise ValueError('GLOBAL_BANK_REBUILD_ROW_IDENTITY')
        filtered.append(image)
    if replayed!=expected:raise ValueError('GLOBAL_BANK_REBUILD_SOURCE_PIXEL_IDENTITY')
    geometry=dict(oam_entries=len(pieces),peak_sprites=max(sum(active_on_line(p,y)for p in pieces)for y in range(height)),peak_tile_slivers=max(sum(tile_slivers(p)for p in pieces if active_on_line(p,y))for y in range(height)))
    if geometry['oam_entries']>128 or geometry['peak_sprites']>32 or geometry['peak_tile_slivers']>34:raise ValueError('GLOBAL_BANK_REBUILD_HARDWARE_GEOMETRY')
    trace,states=logical_schedule(pieces,assignment,height,lookahead);masks=[];indices=np.zeros((height,256),dtype=np.uint8)
    for row in trace:row['resident_before']={b:row['resident_before'].get(b,[None]*15)for b in range(8)}
    for p,colors in zip(pieces,filtered):
        image=np.zeros(colors.shape,dtype=np.uint8)
        for ly,lx in zip(*np.where(colors>=0)):
            y,x=p['y']+int(ly),p['x']+int(lx);slot=states[y][p['bank']].index(int(colors[ly,lx]))+1
            image[ly,lx]=slot;indices[y,x]=128+16*p['bank']+slot
        flat=image.flatten();masks.append(dict(width=p['width'],height=p['height'],pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex()))
    result=copy.deepcopy(source)
    for field in('bank_rebalance','bank_search','bank_residency','physical_slot_layout','physical_slot_refinement','optimistic_bank_order','compiled_transfer_descriptor_sha256'):
        if field in result:result['input_'+field]=result.pop(field)
    result.pop('prepared_dma_packets',None)
    result.update(pieces=pieces,piece_pixel_masks=masks,trace=trace,piece_bank_assignment=list(assignment),geometry=geometry,hardware_geometry_admitted=True,native_presentation_proven=False,prepared_dma_partition_bound_enforced=False,prepared_dma_window_master_clocks=None,bank_assignment_authority='global_word_mask_rebuild')
    result['global_word_bank_construction']={k:v for k,v in search.items()if k not in('pieces','assignment')}
    result['global_word_bank_construction'].update(full_input_operand_and_transparency_identity_replayed=True,actual_hardware_geometry_admitted=True,noninitial_lookahead_lines=lookahead)
    peak=max(r['colors_written']for r in trace[1:]);result.update(peak_scheduled_writes=peak,peak_cgram_data_bytes=2*peak,average_writes=float(np.mean([r['colors_written']for r in trace[1:]])),worst_scanline=max(trace[1:],key=lambda r:r['colors_written'])['scanline'],lookahead_lines=lookahead)
    result['input_compiled_schedule_sha256']=source.get('compiled_schedule_sha256');result['compiled_indices_sha256']=hashlib.sha256(indices.tobytes()).hexdigest()
    payload=dict(pieces=pieces,masks=masks,trace=trace,color_math=result.get('color_math','additive'),source_rgb555_sha256=result.get('source_rgb555_sha256'))
    if result.get('scanline_math_controls_source_bound'):payload.update(selected_modes=result['selected_modes'],windows=result['compiled_color_window_descriptors'])
    result['compiled_schedule_sha256']=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    from raster_presentation_identity import refresh_presentation_identity
    refresh_presentation_identity(result)
    _,_,actual=demand(result);verified={}
    for p,image in zip(pieces,actual):
        for ly,lx in zip(*np.where(image>=0)):verified[p['actor'],p['y']+int(ly),p['x']+int(lx)]=int(image[ly,lx])
    if verified!=expected:raise AssertionError('GLOBAL_BANK_REBUILD_INDEPENDENT_OPERAND_REPLAY')
    return result


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
    from raster_slot_greedy import bank_groups
    demand(schedule);groups=bank_groups(schedule)
    rows=[r['updates']for r in schedule['trace'][1:]if r['updates']];best=None;checked=0
    candidates=(tuple(target for group in choices for target in group)for choices in itertools.product(*(itertools.permutations(group)for group in groups)))
    for mapping in candidates:
        if any(mapping[p['bank']]not in p.get('allowed_banks',range(8))for p in schedule['pieces']):continue
        checked+=1;costs=[favorable_span([dict(e,bank=mapping[e['bank']])for e in row])for row in rows]
        key=(max(costs,default=0),sum(costs),mapping)
        if best is None or key<best:best=key
    return dict(schema='BYOR_ELIGIBLE_FIXED_BANK_PERMUTATION_BOUND_V1',legal_permutations_checked=checked,
        minimum_peak_favorable_span=None if best is None else best[0],sum_favorable_spans=None if best is None else best[1],
        best_bank_mapping=None if best is None else list(best[2]),write_times_and_word_residency_fixed=True,
        math_bank_eligibility_preserved=True,physical_slots_relaxed=True,native_timing_admitted=False,universal_raster_rejected=False)


def assign_masks(pieces,time_limit=30,residency_window_lines=None,maximum_tile_slivers=34,persistent_word_indices=False,maximum_oam_entries=None,prepared_dma_window=None,write_budget=21,word_epoch_lines=None,word_bank_hint=None,search_strategy='portfolio',obj_size_mode=None):
    from ortools.sat.python import cp_model
    if obj_size_mode is not None and(type(obj_size_mode)is not int or obj_size_mode!=6):raise ValueError('JOINT_GLOBAL_BANK_CLASS_OBJ_SIZE_MODE')
    legal_shapes=((16,32),(32,64))if obj_size_mode==6 else((8,8),(16,16),(32,32))
    if search_strategy not in ('portfolio','sat'):raise ValueError('JOINT_GLOBAL_BANK_CLASS_SEARCH_STRATEGY')
    if time_limit<=0 or not 1<=maximum_tile_slivers<=34 or(residency_window_lines is not None and(type(residency_window_lines)is not int or residency_window_lines<1)):
        raise ValueError('JOINT_GLOBAL_BANK_CLASS_DOMAIN')
    if maximum_oam_entries is not None and(type(maximum_oam_entries)is not int or not 1<=maximum_oam_entries<=128):raise ValueError('JOINT_GLOBAL_BANK_CLASS_OAM_DOMAIN')
    if prepared_dma_window is not None and(type(prepared_dma_window)is not int or prepared_dma_window<1 or type(write_budget)is not int or not 0<=write_budget<=120):raise ValueError('JOINT_GLOBAL_BANK_CLASS_TRANSFER_DOMAIN')
    if word_epoch_lines is not None and(type(word_epoch_lines)is not int or word_epoch_lines<1 or persistent_word_indices or residency_window_lines):raise ValueError('JOINT_GLOBAL_BANK_CLASS_WORD_EPOCH_POLICY')
    def word_key(domain,color,y):return(domain,color,int(y)//word_epoch_lines)if word_epoch_lines else(domain,color)
    model=cp_model.CpModel();masks={};words={};users={};domains={}
    for i,p in enumerate(pieces):
        allowed=tuple(sorted(set(p.get('allowed_banks',range(8)))))
        if not allowed or any(type(b)is not int or not 0<=b<8 for b in allowed):raise ValueError('JOINT_GLOBAL_BANK_CLASS_ELIGIBILITY')
        if (p['width'],p['height'])not in legal_shapes:raise ValueError('JOINT_GLOBAL_BANK_CLASS_GEOMETRY')
        domains[i]=allowed
        for b in allowed:masks[i,b]=model.new_bool_var(f'mask{i}_{b}')
        for y,colors in p['rows'].items():
            for c in colors:
                if type(c)is not int or not 0<=c<32768:raise ValueError('JOINT_GLOBAL_BANK_CLASS_WORD')
                key=word_key(allowed,c,y)
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
    if maximum_oam_entries is not None:model.add(sum(masks.values())<=maximum_oam_entries)
    if word_bank_hint is not None:
        if any(type(c)is not int or not 0<=c<32768 or type(b)is not int or not 0<=b<8 for c,b in word_bank_hint.items()):raise ValueError('JOINT_GLOBAL_BANK_CLASS_HINT_DOMAIN')
        for key,variables in words.items():
            if key[1]not in word_bank_hint:continue
            target=word_bank_hint[key[1]]
            if target not in variables:raise ValueError('JOINT_GLOBAL_BANK_CLASS_HINT_ELIGIBILITY')
            for b,v in variables.items():model.add_hint(v,int(b==target))
        for(i,b),v in masks.items():model.add_hint(v,int(any(word_bank_hint.get(c)==b for cs in pieces[i]['rows'].values()for c in cs)))
    height=224 if obj_size_mode==6 else max((p['y']+p['height']for p in pieces),default=0)
    for y in range(height):
        live=[(i,b)for i,p in enumerate(pieces)if active_on_line(p,y)for b in domains[i]]
        model.add(sum(masks[i,b]*tile_slivers(pieces[i])for i,b in live)<=maximum_tile_slivers)
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
    interval_transfer_cuts=0;peak_transfer_cost=None
    if prepared_dma_window is not None:
        # Disjoint eligibility classes cannot duplicate a word in one bank.
        # Overlapping classes need alias-aware per-row capacity accounting too.
        distinct_domains=set(domains.values())
        if any(set(a)&set(b)for a in distinct_domains for b in distinct_domains if a!=b):
            raise ValueError('JOINT_GLOBAL_BANK_CLASS_TRANSFER_OVERLAPPING_DOMAINS')
        from raster_bank_residency import constrain_flow
        if not active_rows:raise ValueError('JOINT_GLOBAL_BANK_CLASS_TRANSFER_EMPTY')
        first,last=min(active_rows),max(active_rows);counts={};prefix={};costs=[]
        peak_transfer_cost=model.new_int_var(0,4096,'peakTransferCost')
        for b in range(8):prefix[first,b]=model.new_constant(0)
        for y in range(first+1,last+1):
            row=[];active=[]
            for b in range(8):
                n=model.new_int_var(0,15,f'commits{y}_{b}');counts[y,b]=n;row.append(n)
                flag=model.new_bool_var(f'commitBank{y}_{b}');model.add(n>=flag);model.add(n<=15*flag);active.append(flag)
                prefix[y,b]=model.new_int_var(0,15*(y-first),f'commitPrefix{y}_{b}');model.add(prefix[y,b]==prefix[y-1,b]+n)
            model.add(sum(row)<=write_budget)
            cost=constrain_flow(model,row,active,prepared_dma_window,f'geometryTransfer{y}');model.add(peak_transfer_cost>=cost);costs.append(cost)
        row_keys={y:{key for yy,key in users if yy==y}for y in active_rows};union_aliases={}
        def identity_variables(keys,bank):
            by_color={}
            for key in keys:
                if bank in words[key]:by_color.setdefault(key[1],[]).append(words[key][bank])
            result=[]
            for color,options in by_color.items():
                if len(options)==1:result.append(options[0]);continue
                signature=bank,tuple(sorted(v.index for v in options))
                if signature not in union_aliases:
                    alias=model.new_bool_var(f'intervalAlias{len(union_aliases)}');union_aliases[signature]=alias
                    for v in options:model.add(alias>=v)
                    model.add(alias<=sum(options))
                result.append(union_aliases[signature])
            return result
        for begin in range(first,last):
            union=set()
            for end in range(begin,last+1):
                union.update(row_keys.get(end,set()))
                if end==begin:continue
                for b in range(8):
                    identity_count=sum(identity_variables(union,b))
                    model.add(prefix[end,b]-prefix[begin,b]>=identity_count-15);interval_transfer_cuts+=1
        model.minimize(peak_transfer_cost*(len(masks)+1)+sum(masks.values()))
    else:model.minimize(sum(masks.values()))
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit;solver.parameters.num_search_workers=4
    solver.parameters.cp_model_probing_level=0;solver.parameters.use_sat_inprocessing=False
    if search_strategy=='sat':
        solver.parameters.subsolvers.append('no_lp');solver.parameters.num_full_subsolvers=1
        solver.parameters.linearization_level=0
    status=solver.solve(model)
    result=dict(schema='BYOR_JOINT_GLOBAL_WORD_BANK_CLASSES_V1',status='BOUNDED_JOINT_GLOBAL_BANK_CLASSES_NO_CANDIDATE',
        solver_status=solver.status_name(status),solver_seconds=solver.wall_time,solver_variables=len(model.proto.variables),
        solver_constraints=len(model.proto.constraints),solver_branches=solver.num_branches,solver_conflicts=solver.num_conflicts,
        maximum_tile_slivers=maximum_tile_slivers,obj_size_mode=obj_size_mode,legal_obj_shapes=[list(shape)for shape in legal_shapes],residency_window_lines=residency_window_lines,
        maximum_oam_entries=maximum_oam_entries,
        prepared_dma_window=prepared_dma_window,aggregate_bank_transfer_interval_cuts=interval_transfer_cuts,palette_residency_and_physical_slots_relaxed=prepared_dma_window is not None,
        global_word_bank_identity_restricted=word_epoch_lines is None,word_epoch_lines=word_epoch_lines,oam_and_sprite_admission_deferred=True,
        soft_word_bank_hint_colors=len(word_bank_hint or{}),
        search_strategy=search_strategy,
        persistent_word_indices=persistent_word_indices,persistent_slot_symmetry_anchor_words=len(anchor),
        persistent_slot_symmetry_excludes_transfer_constraints=True,
        physical_transfer_admitted=False,native_timing_admitted=False,universal_raster_rejected=False,no_color_reduction=True)
    if status not in(cp_model.OPTIMAL,cp_model.FEASIBLE):return result
    expanded=[];assignment=[]
    for i,p in enumerate(pieces):
        for b in domains[i]:
            rows={int(y):[c for c in colors if solver.value(words[word_key(domains[i],c,y)][b])]for y,colors in p['rows'].items()}
            if any(rows.values()):expanded.append(dict(p,rows=rows,source_piece=i));assignment.append(b)
    for i,p in enumerate(pieces):
        for y,colors in p['rows'].items():
            recovered=[c for q in expanded if q['source_piece']==i for c in q['rows'].get(int(y),[])]
            if sorted(recovered)!=sorted(colors):raise AssertionError('JOINT_GLOBAL_BANK_CLASS_PIXEL_WORDS')
    peak_tiles=max((sum(tile_slivers(p)for p in expanded if active_on_line(p,y))for y in range(height)),default=0)
    if peak_tiles>maximum_tile_slivers:raise AssertionError('JOINT_GLOBAL_BANK_CLASS_TILE_CEILING')
    if maximum_oam_entries is not None and len(expanded)>maximum_oam_entries:raise AssertionError('JOINT_GLOBAL_BANK_CLASS_OAM_CEILING')
    for y in active_rows:
        for b in range(8):
            colors={c for p,bank in zip(expanded,assignment)if bank==b for yy,cs in p['rows'].items()if y<=yy<y+window for c in cs}
            if len(colors)>15:raise AssertionError('JOINT_GLOBAL_BANK_CLASS_WINDOW_CAPACITY')
    result.update(status='JOINT_GLOBAL_BANK_MASK_WORD_IDENTITIES_PROVEN',pieces=expanded,assignment=assignment,
        objective=float(solver.objective_value),lower_bound=float(solver.best_objective_bound),peak_tile_slivers=peak_tiles,
        oam_entries=len(expanded),peak_sprites=max((sum(active_on_line(p,y)for p in expanded)for y in range(height)),default=0),
        pixel_word_identities_replayed=True)
    if peak_transfer_cost is not None:
        from raster_bank_residency import favorable_span
        committed={y:[solver.value(counts[y,b])for b in range(8)]for y in range(first+1,last+1)}
        if any(sum(row)>write_budget or favorable_span([dict(bank=b)for b,n in enumerate(row)for _ in range(n)])>=prepared_dma_window for row in committed.values()):raise AssertionError('JOINT_GLOBAL_BANK_CLASS_TRANSFER_PARTITION_REPLAY')
        for begin in range(first,last):
            union=set()
            for end in range(begin,last+1):
                union.update(row_keys.get(end,set()))
                if end==begin:continue
                for b in range(8):
                    identities=len({key[1]for key in union if b in words[key]and solver.value(words[key][b])})
                    if sum(committed[y][b]for y in range(begin+1,end+1))<identities-15:raise AssertionError('JOINT_GLOBAL_BANK_CLASS_TRANSFER_UNION_REPLAY')
        result.update(aggregate_transfer_span=max(0,solver.value(peak_transfer_cost)-40),aggregate_bank_write_counts=committed,aggregate_transfer_intervals_and_partitions_replayed=True,objective_basis='PEAK_IDEAL_TRANSFER_THEN_OAM_MASKS')
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
