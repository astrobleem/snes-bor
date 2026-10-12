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


def search(rectangles,pixel_options,height=224,time_limit=30,bank_symmetry=False):
    from ortools.sat.python import cp_model
    if type(height)is not int or not 1<=height<=256 or time_limit<=0 or not rectangles or not pixel_options:
        raise ValueError('FRAME_BANK_GEOMETRY_DOMAIN')
    if type(bank_symmetry)is not bool:raise ValueError('FRAME_BANK_GEOMETRY_SYMMETRY_DOMAIN')
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
                model.add(v<=sum(palette[y,b,c]for c in pixel_options[y,x][b]))
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
    model.minimize(sum(masks.values()))
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit;solver.parameters.num_search_workers=4
    status=solver.solve(model)
    report=dict(schema='BYOR_FIXED_FRAME_BANK_GEOMETRY_V1',status='BOUNDED_FRAME_BANK_GEOMETRY_NO_WITNESS',
        solver_status=solver.status_name(status),solver_seconds=solver.wall_time,solver_objective_lower_bound=solver.best_objective_bound,
        model_variables=len(model.proto.variables),model_constraints=len(model.proto.constraints),candidate_rectangles=len(rectangles),
        source_pixel_count=len(pixel_options),bank_count=8,opaque_slots_per_bank=15,fixed_bank_for_entire_oam_rectangle=True,
        equivalent_pixel_decision_atoms=len(atoms),equivalent_pixel_decisions_coalesced=len(pixel_options)-len(atoms),
        safe_class_bank_label_symmetry=bank_symmetry,bank_order_timing_not_modeled=True,
        full_rectangle_padding_counted=True,palette_liveness_and_transfer_cost_relaxed=True,native_presentation_proven=False,
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
    report.update(status='FIXED_FRAME_BANK_GEOMETRY_AND_WORD_OPTIONS_PROVEN',pieces=pieces,pixels=pixels,geometry=geometry,
        declared_word_options_and_fixed_bank_geometry_replayed=True)
    return report
