"""Fixed OAM bank/geometry search with compact per-pixel word-option clauses.

Palette capacities are separate for each bank on every row. A selected OAM
mask keeps one bank throughout its complete legal rectangle. Palette liveness,
physical slots and transfers are deferred; a witness is not native admission.
"""


def subdivided_candidates(rectangles,pixel_options,small_size=8):
    """Keep parent geometry and add source-pixel-exact legal smaller masks."""
    if small_size not in(8,16):raise ValueError('FRAME_BANK_GEOMETRY_SUBDIVISION_SIZE')
    candidates={}
    for parent in rectangles:
        choices=[dict(parent)]
        if parent['width']>small_size:
            for dy in range(0,parent['height'],small_size):
                for dx in range(0,parent['width'],small_size):
                    p=dict(parent,x=parent['x']+dx,y=parent['y']+dy,width=small_size,height=small_size)
                    if 'local_x'in p:p['local_x']+=dx
                    if 'local_y'in p:p['local_y']+=dy
                    choices.append(p)
        for p in choices:
            if not any(p['y']<=y<p['y']+p['height']and p['x']<=x<p['x']+p['width']for y,x in pixel_options):continue
            key=(p.get('actor',0),p['x'],p['y'],p['width'],p['height'],tuple(sorted(p.get('allowed_banks',range(8)))))
            candidates[key]=p
    return list(candidates.values())


def search(rectangles,pixel_options,height=224,time_limit=30,bank_symmetry=False,feasibility_only=False,geometry_hint=None,cache_window=None):
    from ortools.sat.python import cp_model
    if type(height)is not int or not 1<=height<=256 or time_limit<=0 or not rectangles or not pixel_options:
        raise ValueError('FRAME_BANK_GEOMETRY_DOMAIN')
    if type(bank_symmetry)is not bool:raise ValueError('FRAME_BANK_GEOMETRY_SYMMETRY_DOMAIN')
    if type(feasibility_only)is not bool:raise ValueError('FRAME_BANK_GEOMETRY_FEASIBILITY_DOMAIN')
    if cache_window is not None and(type(cache_window)is not int or cache_window<1 or bank_symmetry):
        raise ValueError('FRAME_BANK_GEOMETRY_CACHE_WINDOW_DOMAIN')
    sizes=set()
    for p in rectangles:
        if any(type(p.get(k))is not int for k in ('x','y','width','height'))or p['width']!=p['height']or p['width']not in(8,16,32)or not -256<=p['x']<256 or not -256<=p['y']<256:
            raise ValueError('FRAME_BANK_GEOMETRY_RECTANGLE')
        sizes.add(p['width'])
    if sizes not in({8},{16},{32},{8,16},{8,32},{16,32}):raise ValueError('FRAME_BANK_GEOMETRY_OBSEL_PAIR')
    for point,banks in pixel_options.items():
        if not isinstance(point,tuple)or len(point)!=2 or any(type(v)is not int for v in point)or not 0<=point[0]<height or not 0<=point[1]<256 or not isinstance(banks,dict)or not banks:
            raise ValueError('FRAME_BANK_GEOMETRY_PIXEL')
        if any(type(b)is not int or not 0<=b<8 or not isinstance(cs,(list,set,tuple))or not cs or any(type(c)is not int or not 0<=c<32768 for c in cs)for b,cs in banks.items()):
            raise ValueError('FRAME_BANK_GEOMETRY_WORD_DOMAIN')
    if bank_symmetry:
        for group in(range(4),range(4,8)):
            for banks in pixel_options.values():
                values=[None if b not in banks else set(banks[b])for b in group]
                if any(v!=values[0]for v in values):raise ValueError('FRAME_BANK_GEOMETRY_UNSAFE_SYMMETRY')
            for p in rectangles:
                allowed=set(p.get('allowed_banks',range(8)));included=[b in allowed for b in group]
                if any(v!=included[0]for v in included):raise ValueError('FRAME_BANK_GEOMETRY_UNSAFE_SYMMETRY')
    coverage={point:[]for point in pixel_options}
    for i,p in enumerate(rectangles):
        points=[point for point in pixel_options if p['y']<=point[0]<p['y']+p['height']and p['x']<=point[1]<p['x']+p['width']]
        for point in points:coverage[point].append(i)
    atoms={}
    for (y,x),banks in pixel_options.items():
        if not coverage[y,x]:raise ValueError('FRAME_BANK_GEOMETRY_UNCOVERED_PIXEL')
        # Identical row word domains and candidate owners can share a decision:
        # any one selected owner/word serving one point can serve every point.
        # This cannot increase palette demand, OAM or padded hardware row costs.
        key=(y,tuple(coverage[y,x]),tuple((b,tuple(sorted(set(cs))))for b,cs in sorted(banks.items())))
        atoms.setdefault(key,[]).append((y,x))
    atoms=list(atoms.items());candidate_atoms={i:[]for i in range(len(rectangles))}
    for j,(key,points)in enumerate(atoms):
        for i in key[1]:candidate_atoms[i].append(j)
    model=cp_model.CpModel();palette={};masks={};owners={j:[]for j in range(len(atoms))};assignments=[];rows={}
    for (y,x),banks in pixel_options.items():
        for b,colors in banks.items():
            for c in colors:
                if (y,b,c)not in palette:
                    v=model.new_bool_var(f'color{y}_{b}_{c}');palette[y,b,c]=v;rows.setdefault((y,b),[]).append(v)
    cache_loads={};initial_cache_row=min(y for y,x in pixel_options)
    if cache_window is not None:
        from raster_bank_residency import constrain_flow
        last_possible={}
        for y,b,c in palette:last_possible[b,c]=max(y,last_possible.get((b,c),y))
        for(b,c),last in last_possible.items():
            previous=None
            for y in range(initial_cache_row,last+1):
                if(y,b,c)not in palette:
                    v=model.new_bool_var(f'cache{y}_{b}_{c}');palette[y,b,c]=v;rows.setdefault((y,b),[]).append(v)
                v=palette[y,b,c]
                if previous is not None:
                    load=model.new_bool_var(f'load{y}_{b}_{c}')
                    model.add(load<=v);model.add(load+previous<=1);model.add(load>=v-previous)
                    cache_loads.setdefault((y,b),[]).append(load)
                previous=v
        for y in range(initial_cache_row+1,max(y for y,x in pixel_options)+1):
            counts=[];active=[]
            for b in range(8):
                count=model.new_int_var(0,15,f'loadCount{y}_{b}');model.add(count==sum(cache_loads.get((y,b),[])))
                flag=model.new_bool_var(f'loadActive{y}_{b}');model.add(count>=flag);model.add(count<=15*flag)
                counts.append(count);active.append(flag)
            constrain_flow(model,counts,active,cache_window,f'frameCache{y}',4)
    for values in rows.values():model.add(sum(values)<=15)
    for i,p in enumerate(rectangles):
        allowed=p.get('allowed_banks',list(range(8)))
        if not allowed or any(type(b)is not int or not 0<=b<8 for b in allowed):raise ValueError('FRAME_BANK_GEOMETRY_BANK_DOMAIN')
        for b in sorted(set(allowed)):
            eligible=[j for j in candidate_atoms[i]if b in pixel_options[atoms[j][1][0]]]
            if not eligible:continue
            mask=model.new_bool_var(f'piece{i}_{b}');masks[i,b]=mask
            for j in eligible:
                y,x=atoms[j][1][0];v=model.new_bool_var(f'atom{i}_{b}_{j}');model.add(v<=mask)
                model.add_bool_or([v.Not()]+[palette[y,b,c]for c in pixel_options[y,x][b]])
                owners[j].append(v);assignments.append((i,b,j,v))
    for values in owners.values():
        if not values:raise ValueError('FRAME_BANK_GEOMETRY_UNCOVERED_PIXEL')
        model.add_exactly_one(values)
    model.add(sum(masks.values())<=128)
    if bank_symmetry:
        counts={b:sum(v for(i,bb),v in masks.items()if bb==b)for b in range(8)}
        for group in(range(4),range(4,8)):
            for a,b in zip(group,list(group)[1:]):model.add(counts[a]>=counts[b])
    for y in range(height):
        live=[(i,b,v)for(i,b),v in masks.items()if rectangles[i]['y']<=y<rectangles[i]['y']+rectangles[i]['height']]
        model.add(sum(v for i,b,v in live)<=32)
        model.add(sum(v*(rectangles[i]['width']//8)for i,b,v in live)<=34)
    if not feasibility_only:model.minimize(sum(masks.values()))
    hinted=set()
    if geometry_hint is not None:
        if not isinstance(geometry_hint,dict)or not isinstance(geometry_hint.get('pieces'),list)or not isinstance(geometry_hint.get('pixels'),list):
            raise ValueError('FRAME_BANK_GEOMETRY_HINT_DOMAIN')
        def add_hint(v):
            if v.index not in hinted:model.add_hint(v,1);hinted.add(v.index)
        matched={}
        for j,p in enumerate(geometry_hint['pieces']):
            keys=('x','y','width','height');bank=p.get('bank')
            match=next((i for i,q in enumerate(rectangles)if all(p.get(k)==q[k]for k in keys)and(i,bank)in masks),None)
            if match is None:raise ValueError('FRAME_BANK_GEOMETRY_HINT_RECTANGLE')
            matched[j]=(match,bank);add_hint(masks[match,bank])
        hinted_points={}
        for p in geometry_hint['pixels']:
            point=(p.get('y'),p.get('x'));bank=p.get('bank');color=p.get('color');piece=p.get('piece')
            if point not in pixel_options or bank not in pixel_options[point]or color not in pixel_options[point][bank]or piece not in matched or matched[piece][1]!=bank or point in hinted_points:
                raise ValueError('FRAME_BANK_GEOMETRY_HINT_PIXEL')
            i,_=matched[piece]
            if i not in coverage[point]:raise ValueError('FRAME_BANK_GEOMETRY_HINT_OWNER')
            hinted_points[point]=(i,bank);add_hint(palette[point[0],bank,color])
        for i,b,j,v in assignments:
            if all(hinted_points.get(point)==(i,b)for point in atoms[j][1]):add_hint(v)
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit;solver.parameters.num_search_workers=4
    status=solver.solve(model)
    report=dict(schema='BYOR_FIXED_FRAME_BANK_GEOMETRY_V1',status='BOUNDED_FRAME_BANK_GEOMETRY_NO_WITNESS',
        solver_status=solver.status_name(status),solver_seconds=solver.wall_time,solver_objective_lower_bound=solver.best_objective_bound,
        model_variables=len(model.proto.variables),model_constraints=len(model.proto.constraints),candidate_rectangles=len(rectangles),
        source_pixel_count=len(pixel_options),bank_count=8,opaque_slots_per_bank=15,fixed_bank_for_entire_oam_rectangle=True,
        equivalent_pixel_decision_atoms=len(atoms),equivalent_pixel_decisions_coalesced=len(pixel_options)-len(atoms),
        safe_class_bank_label_symmetry=bank_symmetry,bank_order_timing_not_modeled=cache_window is None,
        solver_objective='FEASIBILITY_ONLY'if feasibility_only else'MINIMUM_OAM_ENTRIES',
        soft_geometry_hint_variables=len(hinted),
        ideal_cache_partition_window_master_clocks=cache_window,
        joint_cache_residency_enforced=cache_window is not None,
        initial_cache_row_relaxed_to_free_vblank=initial_cache_row if cache_window is not None else None,
        full_rectangle_padding_counted=True,palette_liveness_and_transfer_cost_relaxed=cache_window is None,
        physical_slots_and_transfer_cost_relaxed=True,native_presentation_proven=False,
        universal_raster_rejected=False,no_color_reduction=True)
    if status not in(cp_model.FEASIBLE,cp_model.OPTIMAL):return report
    pieces=[];selected={}
    for (i,b),v in masks.items():
        if solver.value(v):selected[i,b]=len(pieces);pieces.append(dict(rectangles[i],bank=b))
    pixels=[];row_colors={};seen=set()
    for i,b,j,v in assignments:
        if not solver.value(v):continue
        y,x=atoms[j][1][0];colors=[c for c in pixel_options[y,x][b]if solver.value(palette[y,b,c])]
        if not colors:raise AssertionError('FRAME_BANK_GEOMETRY_WORD_REPLAY')
        c=min(colors)
        for y,x in atoms[j][1]:
            if(y,x)in seen or(i,b)not in selected:raise AssertionError('FRAME_BANK_GEOMETRY_OWNER_REPLAY')
            seen.add((y,x));pixels.append(dict(piece=selected[i,b],y=y,x=x,bank=b,color=c));row_colors.setdefault((y,b),set()).add(c)
    if seen!=set(pixel_options)or any(len(cs)>15 for cs in row_colors.values()):raise AssertionError('FRAME_BANK_GEOMETRY_CAPACITY_REPLAY')
    geometry=dict(oam_entries=len(pieces),peak_sprites=max(sum(p['y']<=y<p['y']+p['height']for p in pieces)for y in range(height)),
        peak_tile_slivers=max(sum(p['width']//8 for p in pieces if p['y']<=y<p['y']+p['height'])for y in range(height)))
    if geometry['oam_entries']>128 or geometry['peak_sprites']>32 or geometry['peak_tile_slivers']>34:raise AssertionError('FRAME_BANK_GEOMETRY_HARDWARE_REPLAY')
    if cache_window is not None:
        from raster_bank_residency import favorable_span
        states={};previous={b:set()for b in range(8)};cache=[]
        for y in range(initial_cache_row,max(y for y,x in pixel_options)+1):
            current={b:{c for(yy,bb,c),v in palette.items()if yy==y and bb==b and solver.value(v)}for b in range(8)}
            if any(len(cs)>15 for cs in current.values()):raise AssertionError('FRAME_BANK_CACHE_CAPACITY_REPLAY')
            updates=[dict(bank=b,color=c)for b in range(8)for c in sorted(current[b]-previous[b])]
            cost=0 if y==initial_cache_row else favorable_span(updates)
            if cost>=cache_window:raise AssertionError('FRAME_BANK_CACHE_PARTITION_REPLAY')
            cache.append(dict(scanline=y,resident_colors={b:sorted(cs)for b,cs in current.items()},colors_written=len(updates),
                updates=updates,ideal_prepared_commit_span=cost,vblank_initialization_relaxed=y==initial_cache_row))
            states[y]=current;previous=current
        if any(p['color']not in states[p['y']][p['bank']]for p in pixels):raise AssertionError('FRAME_BANK_CACHE_PIXEL_REPLAY')
        report.update(joint_cache_trace=cache,independent_integer_cache_and_ideal_partition_replayed=True,
            peak_joint_cache_writes=max((r['colors_written']for r in cache[1:]),default=0),
            peak_joint_cache_ideal_span=max(r['ideal_prepared_commit_span']for r in cache))
    report.update(status='FIXED_FRAME_BANK_GEOMETRY_AND_WORD_OPTIONS_PROVEN',pieces=pieces,pixels=pixels,geometry=geometry,
        declared_word_options_and_fixed_bank_geometry_replayed=True)
    return report


def main():
    import argparse,hashlib,json
    from pathlib import Path
    from compiler import Source
    from source_scene_obj_raster import prepare
    from source_scene_bg import compose_rgb8
    from source_bg_feasibility import rgb555
    from raster_slot_greedy import demand
    from raster_scanline_bank_geometry import exact_row_word_options
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--schedule',type=Path,required=True)
    p.add_argument('--geometry',type=Path,required=True,help='JSON containing source_rectangle_cover.')
    p.add_argument('--exact-source',type=Path,required=True);p.add_argument('--stage',required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--time-limit',type=float,default=30)
    p.add_argument('--scanline-start',type=int,default=0);p.add_argument('--scanline-end',type=int,default=224)
    p.add_argument('--subdivide',action='store_true');p.add_argument('--bank-symmetry',action='store_true')
    p.add_argument('--feasibility-only',action='store_true')
    p.add_argument('--geometry-hint',type=Path,help='Soft source-exact geometry witness from a subset of the requested interval.')
    p.add_argument('--cache-window',type=int,help='Joint integer color residency with ideal bank partitions; physical slots remain relaxed.')
    a=p.parse_args()
    if not 0<=a.scanline_start<a.scanline_end<=224:p.error('scanline interval must be within [0,224)')
    frame=json.loads(a.schedule.read_text(encoding='utf-8'))
    geometry=json.loads(a.geometry.read_text(encoding='utf-8'));rectangles=geometry['source_rectangle_cover']['rectangles']
    if geometry.get('source_rgb555_sha256')!=frame['source_rgb555_sha256']:
        raise ValueError('FRAME_BANK_GEOMETRY_COVER_SOURCE_IDENTITY')
    source=Source(a.exact_source);scene=frame['metadata']['scene']
    _,metadata,expected=prepare(source,a.stage,scene);expected=rgb555(expected)
    if metadata!=frame['metadata']or hashlib.sha256(expected.astype('<u2').tobytes()).hexdigest()!=frame['source_rgb555_sha256']:
        raise ValueError('FRAME_BANK_GEOMETRY_SOURCE_ARCHIVE_IDENTITY')
    background=rgb555(compose_rgb8(source,a.stage,dict(scene,actors=[]))[0])
    replay=frame
    if frame.get('status')=='POOL_CONSTRUCTION_FIXED_SMALL_GEOMETRY_OVERFLOW':
        if not frame.get('compiled_pixel_identity_verified')or frame.get('hardware_geometry_admitted'):
            raise ValueError('FRAME_BANK_GEOMETRY_OVERFLOW_IDENTITY')
        replay=dict(frame,status='JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN')
    required,_,_=demand(replay)
    options={};proofs={}
    for y in range(a.scanline_start,a.scanline_end):
        if not any(required[y]):continue
        row,proof=exact_row_word_options(frame,y,background[y],expected[y]);proofs[str(y)]=proof
        options.update({(y,x):banks for x,banks in row.items()})
    if a.subdivide:rectangles=subdivided_candidates(rectangles,options)
    print(json.dumps(dict(candidate_rectangles=len(rectangles),source_pixels=len(options))),flush=True)
    hint=json.loads(a.geometry_hint.read_text(encoding='utf-8'))if a.geometry_hint else None
    if hint is not None and hint.get('source_rgb555_sha256')!=frame['source_rgb555_sha256']:
        raise ValueError('FRAME_BANK_GEOMETRY_HINT_SOURCE_IDENTITY')
    report=search(rectangles,options,time_limit=a.time_limit,bank_symmetry=a.bank_symmetry,feasibility_only=a.feasibility_only,geometry_hint=hint,cache_window=a.cache_window)
    report.update(source_rgb555_sha256=frame['source_rgb555_sha256'],source_input_sha256=hashlib.sha256(a.schedule.read_bytes()).hexdigest(),
        source_pak_sha256=hashlib.sha256(a.exact_source.read_bytes()).hexdigest(),source_row_context_proofs=proofs,
        source_rectangle_cover=geometry['source_rectangle_cover'],scanline_interval=[a.scanline_start,a.scanline_end],
        outside_interval_demand_relaxed=(a.scanline_start,a.scanline_end)!=(0,224),
        source_alpha_policy='EXACT_SOURCE_OUTPUT_OPERANDS',alpha_compatibility_policy_selected=False)
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items()if k not in('pixels','pieces','source_rectangle_cover','source_row_context_proofs','joint_cache_trace')}))


if __name__=='__main__':main()
