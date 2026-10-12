"""Fixed OAM bank/geometry search with compact per-pixel word-option clauses.

Palette capacities are separate for each bank on every row. A selected OAM
mask keeps one bank throughout its complete legal rectangle. Palette liveness,
physical slots and transfers are deferred; a witness is not native admission.
"""
from raster_obj_geometry import active_on_line,tile_slivers


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


def search(rectangles,pixel_options,height=224,time_limit=30,bank_symmetry=False,feasibility_only=False,geometry_hint=None,cache_window=None,geometry_reservation=None,solver_backend='cp-sat',minimize_cache_span=False,search_strategy='portfolio',repair_interval=None,mode_word_options=None,literal_window_outputs=None,pixel_actors=None,minimize_row_palette_words=False,minimize_frame_palette_words=False,single_bank_per_rectangle=False,required_math_mode=None,all_source_math_gates=False):
    from ortools.sat.python import cp_model
    if type(height)is not int or not 1<=height<=256 or time_limit<=0 or not rectangles or not pixel_options:
        raise ValueError('FRAME_BANK_GEOMETRY_DOMAIN')
    if type(bank_symmetry)is not bool:raise ValueError('FRAME_BANK_GEOMETRY_SYMMETRY_DOMAIN')
    if type(feasibility_only)is not bool:raise ValueError('FRAME_BANK_GEOMETRY_FEASIBILITY_DOMAIN')
    if type(single_bank_per_rectangle)is not bool or type(all_source_math_gates)is not bool:raise ValueError('FRAME_BANK_GEOMETRY_BANK_GATE_RESTRICTION')
    if required_math_mode is not None:
        from raster_obj_math_cover import MODES
        if required_math_mode not in MODES or mode_word_options is None:raise ValueError('FRAME_BANK_GEOMETRY_REQUIRED_MODE')
    if all_source_math_gates and literal_window_outputs is None:raise ValueError('FRAME_BANK_GEOMETRY_REQUIRED_GATES')
    if type(minimize_row_palette_words)is not bool or(minimize_row_palette_words and(cache_window is not None or feasibility_only)):
        raise ValueError('FRAME_BANK_GEOMETRY_ROW_WORD_OBJECTIVE_DOMAIN')
    if type(minimize_frame_palette_words)is not bool or(minimize_frame_palette_words and(cache_window is not None or feasibility_only or minimize_row_palette_words)):
        raise ValueError('FRAME_BANK_GEOMETRY_FRAME_WORD_OBJECTIVE_DOMAIN')
    if solver_backend not in('cp-sat','highspy'):raise ValueError('FRAME_BANK_GEOMETRY_SOLVER_BACKEND')
    if search_strategy not in('portfolio','lns')or(search_strategy=='lns'and solver_backend!='cp-sat'):raise ValueError('FRAME_BANK_GEOMETRY_SEARCH_STRATEGY')
    if repair_interval is not None and(not minimize_cache_span or geometry_hint is None or not isinstance(repair_interval,(list,tuple))or len(repair_interval)!=2 or any(type(y)is not int for y in repair_interval)or not 0<=repair_interval[0]<=repair_interval[1]<height):
        raise ValueError('FRAME_BANK_GEOMETRY_REPAIR_INTERVAL')
    if type(minimize_cache_span)is not bool or(minimize_cache_span and(cache_window is None or feasibility_only)):
        raise ValueError('FRAME_BANK_GEOMETRY_CACHE_OBJECTIVE_DOMAIN')
    if cache_window is not None and(type(cache_window)is not int or cache_window<1 or bank_symmetry):
        raise ValueError('FRAME_BANK_GEOMETRY_CACHE_WINDOW_DOMAIN')
    reservation=dict(oam_entries=0,sprites_per_line=[0]*height,tile_slivers_per_line=[0]*height)
    if geometry_reservation is not None:
        if not isinstance(geometry_reservation,dict)or set(geometry_reservation)!=set(reservation)or type(geometry_reservation['oam_entries'])is not int or not 0<=geometry_reservation['oam_entries']<=128 or any(not isinstance(geometry_reservation[k],list)or len(geometry_reservation[k])!=height or any(type(v)is not int or not 0<=v<=limit for v in geometry_reservation[k])for k,limit in [('sprites_per_line',32),('tile_slivers_per_line',34)]):
            raise ValueError('FRAME_BANK_GEOMETRY_RESERVATION_DOMAIN')
        reservation=geometry_reservation
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
    row_modes={}
    if literal_window_outputs is not None:
        if mode_word_options is None or not isinstance(literal_window_outputs,dict)or set(literal_window_outputs)!=set(pixel_options)or any(type(c)is not int or not 0<=c<32768 for c in literal_window_outputs.values()):raise ValueError('FRAME_BANK_GEOMETRY_WINDOW_OPTIONS')
        if any(c not in pixel_options[point][b]for point,c in literal_window_outputs.items()for b in pixel_options[point]if b>=4):raise ValueError('FRAME_BANK_GEOMETRY_WINDOW_LITERAL')
    if pixel_actors is not None and(not isinstance(pixel_actors,dict)or set(pixel_actors)!=set(pixel_options)or any(type(i)is not int or i<0 for i in pixel_actors.values())or any(type(p.get('actor',0))is not int or p.get('actor',0)<0 for p in rectangles)):
        raise ValueError('FRAME_BANK_GEOMETRY_PIXEL_ACTORS')
    if mode_word_options is not None:
        from raster_obj_math_cover import MODES
        if bank_symmetry or not isinstance(mode_word_options,dict)or set(mode_word_options)!=set(pixel_options):raise ValueError('FRAME_BANK_GEOMETRY_MODE_OPTIONS')
        for point,modes in mode_word_options.items():
            if not isinstance(modes,dict)or not modes or any(m not in MODES for m in modes):raise ValueError('FRAME_BANK_GEOMETRY_MODE_OPTIONS')
            if point[0]in row_modes and set(modes)!=row_modes[point[0]]:raise ValueError('FRAME_BANK_GEOMETRY_SHARED_MODE_DOMAIN')
            row_modes[point[0]]=set(modes)
            union={}
            for banks in modes.values():
                if not isinstance(banks,dict):raise ValueError('FRAME_BANK_GEOMETRY_MODE_OPTIONS')
                for b,cs in banks.items():
                    if type(b)is not int or b not in pixel_options[point]or not isinstance(cs,(list,set,tuple))or any(type(c)is not int or c not in pixel_options[point][b]for c in cs):raise ValueError('FRAME_BANK_GEOMETRY_MODE_WORD')
                    union.setdefault(b,set()).update(cs)
            if literal_window_outputs is not None:
                for b in pixel_options[point]:
                    if b>=4:union.setdefault(b,set()).add(literal_window_outputs[point])
            if {b:cs for b,cs in union.items()if cs}!={b:set(cs)for b,cs in pixel_options[point].items()}:raise ValueError('FRAME_BANK_GEOMETRY_MODE_UNION')
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
        points=[point for point in pixel_options if p['y']<=point[0]<p['y']+p['height']and p['x']<=point[1]<p['x']+p['width']and(pixel_actors is None or pixel_actors[point]==p.get('actor',0))]
        for point in points:coverage[point].append(i)
    atoms={}
    for (y,x),banks in pixel_options.items():
        if not coverage[y,x]:raise ValueError('FRAME_BANK_GEOMETRY_UNCOVERED_PIXEL')
        # Identical row word domains and candidate owners can share a decision:
        # any one selected owner/word serving one point can serve every point.
        # This cannot increase palette demand, OAM or padded hardware row costs.
        key=(y,tuple(coverage[y,x]),tuple((b,tuple(sorted(set(cs))))for b,cs in sorted(banks.items())))
        if mode_word_options is not None:key+=tuple((mode,tuple((b,tuple(sorted(set(cs))))for b,cs in sorted(values.items())))for mode,values in sorted(mode_word_options[y,x].items())),
        if literal_window_outputs is not None:key+=(x,literal_window_outputs[y,x])
        atoms.setdefault(key,[]).append((y,x))
    atoms=list(atoms.items());candidate_atoms={i:[]for i in range(len(rectangles))}
    mode_sensitive={}
    for j,(key,points)in enumerate(atoms):
        for i in key[1]:candidate_atoms[i].append(j)
        if mode_word_options is not None:
            point=points[0]
            mode_sensitive[j]={b for b,cs in pixel_options[point].items()if any(set(banks.get(b,[]))!=set(cs)for banks in mode_word_options[point].values())}
    model=cp_model.CpModel();palette={};masks={};owners={j:[]for j in range(len(atoms))};assignments=[];rows={}
    mode_choices={}
    for y,modes in row_modes.items():
        choices=[]
        for mode in sorted(modes):
            v=model.new_bool_var(f'rowMode{y}_{mode}');mode_choices[y,mode]=v;choices.append(v)
        model.add(sum(choices)==1)
        if required_math_mode is not None:
            if required_math_mode not in modes:raise ValueError('FRAME_BANK_GEOMETRY_REQUIRED_MODE_UNAVAILABLE')
            model.add(mode_choices[y,required_math_mode]==1)
    gates={};start_relations=[];inverted_rows={}
    if literal_window_outputs is not None:
        for y in sorted(row_modes):
            xs=sorted(x for yy,x in pixel_options if yy==y and any(b>=4 for b in pixel_options[yy,x]))
            positive=[];negative=[];previous=model.new_constant(0);previous_negative=model.new_constant(0)
            for x in xs:
                gate=model.new_bool_var(f'windowGate{y}_{x}');gates[y,x]=gate
                if all_source_math_gates:model.add(gate==1)
                for current,old,collection in((gate,previous,positive),(gate.Not(),previous_negative,negative)):
                    start=model.new_bool_var(f'windowStart{y}_{x}_{len(collection)}_{len(positive)}')
                    model.add(start<=current);model.add(start<=1-old);model.add(start>=current-old);collection.append(start);start_relations.append((start,current,old))
                previous=gate;previous_negative=gate.Not()
            if xs:
                inverted=model.new_bool_var(f'windowInverted{y}');model.add(sum(positive)<=2+len(xs)*inverted);model.add(sum(negative)<=2+len(xs)*(1-inverted))
                inverted_rows[y]=(inverted,positive,negative)
    for (y,x),banks in pixel_options.items():
        for b,colors in banks.items():
            for c in colors:
                if (y,b,c)not in palette:
                    v=model.new_bool_var(f'color{y}_{b}_{c}');palette[y,b,c]=v;rows.setdefault((y,b),[]).append(v)
    cache_loads={};cache_load_vars={};cache_counts={};cache_active={};initial_cache_row=min(y for y,x in pixel_options)
    cache_peak=model.new_int_var(0,cache_window+39,'jointCachePeakCost')if minimize_cache_span else None
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
                    cache_load_vars[y,b,c]=load
                previous=v
        for y in range(initial_cache_row+1,max(y for y,x in pixel_options)+1):
            counts=[];active=[]
            for b in range(8):
                count=model.new_int_var(0,15,f'loadCount{y}_{b}');model.add(count==sum(cache_loads.get((y,b),[])))
                flag=model.new_bool_var(f'loadActive{y}_{b}');model.add(count>=flag);model.add(count<=15*flag)
                counts.append(count);active.append(flag)
                cache_counts[y,b]=count;cache_active[y,b]=flag
            cost=constrain_flow(model,counts,active,cache_window,f'frameCache{y}',4,linear=solver_backend=='highspy')
            if minimize_cache_span and(repair_interval is None or repair_interval[0]<=y<=repair_interval[1]):model.add(cache_peak>=cost)
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
                if solver_backend=='highspy':model.add(v<=sum(palette[y,b,c]for c in pixel_options[y,x][b]))
                else:model.add_bool_or([v.Not()]+[palette[y,b,c]for c in pixel_options[y,x][b]])
                if literal_window_outputs is not None and b>=4:
                    gate=gates[y,x];model.add(palette[y,b,literal_window_outputs[y,x]]>=v-gate)
                    if b in mode_sensitive[j]:
                        for mode,banks in mode_word_options[y,x].items():model.add(sum(palette[y,b,c]for c in banks.get(b,[]))>=v+mode_choices[y,mode]+gate-2)
                elif mode_word_options is not None and b in mode_sensitive[j]:
                    for mode,banks in mode_word_options[y,x].items():
                        model.add(sum(palette[y,b,c]for c in banks.get(b,[]))>=v+mode_choices[y,mode]-1)
                owners[j].append(v);assignments.append((i,b,j,v))
    for values in owners.values():
        if not values:raise ValueError('FRAME_BANK_GEOMETRY_UNCOVERED_PIXEL')
        if solver_backend=='highspy':model.add(sum(values)==1)
        else:model.add_exactly_one(values)
    if single_bank_per_rectangle:
        for i in range(len(rectangles)):model.add(sum(v for(ii,b),v in masks.items()if ii==i)<=1)
    # Distinct compulsory singleton words selected anywhere in an interval
    # need either an initially resident slot or a subsequent load. Choose one
    # representative atom per word, rather than counting repeated pixels or
    # aliases as additional colours. This is implied by exact cache liveness,
    # but exposes source ownership directly to bank/geometry decisions.
    singleton_interval_cuts=0;singleton_class_interval_cuts=0
    if cache_window is not None:
        groups=[(b,)for b in range(8)]+[tuple(range(4)),tuple(range(4,8)),tuple(range(8))]
        singleton_owners={group:{}for group in groups};atom_assignments={}
        for i,b,j,v in assignments:
            atom_assignments.setdefault(j,{}).setdefault(b,[]).append(v)
        for j,banks in atom_assignments.items():
            y,x=atoms[j][1][0]
            for group in groups:
                eligible=set(group)&set(banks)
                words={c for b in eligible for c in pixel_options[y,x][b]}
                if len(words)==1:
                    c=next(iter(words));singleton_owners[group][c,y,j]=[v for b in sorted(eligible)for v in banks[b]]
        last_row=max(y for y,x in pixel_options)
        for begin in range(initial_cache_row,last_row):
            for span in (4,8,16):
                end=min(last_row,begin+span)
                if end<begin+span and span!=4:continue
                for group in groups:
                    representatives={}
                    for (c,y,j),vs in singleton_owners[group].items():
                        if begin<=y<=end:
                            # Prefer the point with the fewest alternative
                            # banks. Any one representative is a valid cut.
                            rank=len(pixel_options[atoms[j][1][0]]),y,j
                            if c not in representatives or rank<representatives[c][0]:representatives[c]=(rank,vs)
                    capacity=15*len(group)
                    if len(representatives)<=capacity:continue
                    selected=[v for rank,vs in representatives.values()for v in vs]
                    model.add(sum(selected)<=capacity+sum(cache_counts[y,b]for y in range(begin+1,end+1)for b in group))
                    singleton_interval_cuts+=1
                    singleton_class_interval_cuts+=int(len(group)>1)
    # A bank cannot benefit from caching a word unless a selected compatible
    # rectangle can display that word somewhere in the frame. Removing words
    # unused by every selected mask preserves capacity and cannot add writes.
    residency_mask_links=0
    if cache_window is not None:
        possible={};residencies={}
        for(y,x),banks in pixel_options.items():
            for b,cs in banks.items():
                compatible={(i,b)for i in coverage[y,x]if(i,b)in masks}
                for c in cs:possible.setdefault((b,c),set()).update(compatible)
        for(y,b,c),v in palette.items():residencies.setdefault((b,c),[]).append(v)
        for key,values in residencies.items():
            model.add(sum(values)<=len(values)*sum(masks[i,b]for i,b in possible.get(key,set())))
            residency_mask_links+=1
    # Required word coverage does not depend on which compatible rectangle
    # owns a pixel. Expose this implication directly rather than relying on
    # a long owner/mask chain, and avoid duplicate clauses for the same domain.
    pool_clauses=set()
    mode_pool_clauses=0
    for(key,points)in atoms:
        y,x=points[0]
        words=tuple(sorted({(b,c)for b,cs in pixel_options[y,x].items()for c in cs if any((i,b)in masks for i in coverage[y,x])}))
        if(y,words)in pool_clauses:continue
        pool_clauses.add((y,words));values=[palette[y,b,c]for b,c in words]
        if solver_backend=='highspy':model.add(sum(values)>=1)
        else:model.add_bool_or(values)
    if mode_word_options is not None:
        # Expose compatible coverage independently of an owner/mask chain.
        # Resident words for another mode cannot satisfy a selected row mode.
        for(key,points)in atoms:
            y,x=points[0];eligible_banks={b for b in pixel_options[y,x]if any((i,b)in masks for i in coverage[y,x])}
            for mode,banks in mode_word_options[y,x].items():
                compatible=[palette[y,b,c]for b,cs in banks.items()if b in eligible_banks for c in cs]
                if literal_window_outputs is None:
                    model.add(sum(compatible)>=mode_choices[y,mode]);mode_pool_clauses+=1
                else:
                    gate=gates.get((y,x))
                    if gate is None:model.add(sum(compatible)>=mode_choices[y,mode]);mode_pool_clauses+=1;continue
                    off=[palette[y,b,c]for b in eligible_banks for c in([literal_window_outputs[y,x]]if b>=4 else banks.get(b,[]))]
                    model.add(sum(compatible)>=mode_choices[y,mode]+gate-1)
                    model.add(sum(off)>=mode_choices[y,mode]-gate);mode_pool_clauses+=2
    model.add(sum(masks.values())<=128-reservation['oam_entries'])
    if bank_symmetry:
        counts={b:sum(v for(i,bb),v in masks.items()if bb==b)for b in range(8)}
        for group in(range(4),range(4,8)):
            for a,b in zip(group,list(group)[1:]):model.add(counts[a]>=counts[b])
    for y in range(height):
        live=[(i,b,v)for(i,b),v in masks.items()if active_on_line(rectangles[i],y)]
        if not live:continue
        model.add(sum(v for i,b,v in live)<=32-reservation['sprites_per_line'][y])
        model.add(sum(v*tile_slivers(rectangles[i])for i,b,v in live)<=34-reservation['tile_slivers_per_line'][y])
    frame_words={}
    if minimize_frame_palette_words:
        by_word={}
        for(y,b,c),v in palette.items():by_word.setdefault((b,c),[]).append(v)
        for(b,c),vs in by_word.items():
            used=model.new_bool_var(f'frameWord{b}_{c}');frame_words[b,c]=used
            for v in vs:model.add(v<=used)
            model.add(used<=sum(vs))
        # Exact lexicographic weights: a single frame identity dominates
        # all possible row word and OAM costs under the hardware limits.
        model.minimize((129*height*120+129)*sum(frame_words.values())+129*sum(palette.values())+sum(masks.values()))
    elif minimize_cache_span:model.minimize(cache_peak)
    elif minimize_row_palette_words:model.minimize(129*sum(palette.values())+sum(masks.values()))
    elif not feasibility_only:model.minimize(sum(masks.values()))
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
        for(y,mode),v in mode_choices.items():
            selected=geometry_hint.get('selected_modes',{}).get(str(y))
            if selected is not None and selected not in row_modes[y]:raise ValueError('FRAME_BANK_GEOMETRY_HINT_MODE')
            if selected==mode:add_hint(v)
        from raster_math_windows import evaluate
        for(y,x),v in gates.items():
            if str(y)in geometry_hint.get('compiled_color_window_descriptors',{}):model.add_hint(v,int(evaluate(geometry_hint['compiled_color_window_descriptors'][str(y)],x)));hinted.add(v.index)
        for p in geometry_hint['pixels']:
            point=(p.get('y'),p.get('x'));bank=p.get('bank');color=p.get('color');piece=p.get('piece')
            if point not in pixel_options or bank not in pixel_options[point]or color not in pixel_options[point][bank]or piece not in matched or matched[piece][1]!=bank or point in hinted_points:
                raise ValueError('FRAME_BANK_GEOMETRY_HINT_PIXEL')
            i,_=matched[piece]
            if i not in coverage[point]:raise ValueError('FRAME_BANK_GEOMETRY_HINT_OWNER')
            hinted_points[point]=(i,bank);add_hint(palette[point[0],bank,color])
        for i,b,j,v in assignments:
            if all(hinted_points.get(point)==(i,b)for point in atoms[j][1]):add_hint(v)
        if cache_window is not None:
            for y,banks in geometry_hint.get('cache_resident_colors',{}).items():
                y=int(y)
                if not 0<=y<height or not isinstance(banks,dict):raise ValueError('FRAME_BANK_GEOMETRY_HINT_CACHE_DOMAIN')
                for b,cs in banks.items():
                    b=int(b)
                    if not 0<=b<8 or not isinstance(cs,list)or len(cs)>15 or any(type(c)is not int or not 0<=c<32768 for c in cs):
                        raise ValueError('FRAME_BANK_GEOMETRY_HINT_CACHE_DOMAIN')
                    for c in cs:
                        if(y,b,c)in palette:add_hint(palette[y,b,c])
    complete_hint_verified=False;complete_hint_violations=[]
    if cache_window is not None and geometry_hint is not None and set(hinted_points)==set(pixel_options):
        import re
        cache_hint={int(y):{int(b):set(cs)for b,cs in banks.items()}for y,banks in geometry_hint.get('cache_resident_colors',{}).items()}
        last_cache_row=max(y for y,x in pixel_options)
        if all(y in cache_hint and set(cache_hint[y])==set(range(8))for y in range(initial_cache_row,last_cache_row+1)):
            from raster_bank_residency import flow_partition_hint
            values={i:list(v.domain)[0]for i,v in enumerate(model.proto.variables)}
            selected_hint_masks=set(matched.values())
            for(y,b,c),v in palette.items():values[v.index]=int(c in cache_hint.get(y,{}).get(b,set())and bool(possible.get((b,c),set())&selected_hint_masks))
            for(y,mode),v in mode_choices.items():values[v.index]=int(mode==geometry_hint.get('selected_modes',{}).get(str(y)))
            for(y,x),v in gates.items():
                descriptor=geometry_hint.get('compiled_color_window_descriptors',{}).get(str(y))
                values[v.index]=int(evaluate(descriptor,x))if descriptor is not None else 0
            literal_var=lambda v:values[v.index]if v.index>=0 else 1-values[-v.index-1]
            for v,current,old in start_relations:values[v.index]=int(literal_var(current)and not literal_var(old))
            for y,(v,positive,negative)in inverted_rows.items():values[v.index]=int(sum(values[q.index]for q in positive)>2)
            for(y,b,c),v in cache_load_vars.items():values[v.index]=int(values[palette[y,b,c].index]and not values[palette[y-1,b,c].index])
            for(i,b),v in masks.items():values[v.index]=int((i,b)in set(matched.values()))
            choices={j:hinted_points[points[0]]for j,(key,points)in enumerate(atoms)}
            for i,b,j,v in assignments:values[v.index]=int(choices[j]==(i,b))
            line_counts={y:[sum(values[v.index]for v in cache_loads.get((y,b),[]))for b in range(8)]for y in range(initial_cache_row+1,last_cache_row+1)}
            groups={};costs={}
            for y,counts in line_counts.items():
                costs[y],groups[y]=flow_partition_hint(counts)
                for b,n in enumerate(counts):values[cache_counts[y,b].index]=n;values[cache_active[y,b].index]=int(n>0)
            for i,v in enumerate(model.proto.variables):
                match=re.fullmatch(r'frameCache(\d+)(interval|cost)(\d+)_(\d+)',v.name)
                if match:
                    y,kind,a,b=int(match[1]),match[2],int(match[3]),int(match[4]);selected=(a,b)in groups[y]
                    values[i]=int(selected)if kind=='interval'else(24+16*(line_counts[y][a]if a==b else line_counts[y][a]+line_counts[y][b]+16*(b-a-1)+1)if selected else 0)
            if cache_peak is not None:values[cache_peak.index]=max((cost for y,cost in costs.items()if repair_interval is None or repair_interval[0]<=y<=repair_interval[1]),default=0)
            literal=lambda n:bool(values[n]if n>=0 else 1-values[-n-1])
            for i,v in enumerate(model.proto.variables):
                d=list(v.domain)
                if not any(d[j]<=values[i]<=d[j+1]for j in range(0,len(d),2)):complete_hint_violations.append('variable:'+v.name)
            for i,c in enumerate(model.proto.constraints):
                if not all(literal(n)for n in c.enforcement_literal):continue
                if c.has_linear():
                    value=sum(values[n]*coefficient for n,coefficient in zip(c.linear.vars,c.linear.coeffs));d=list(c.linear.domain)
                    valid=any(d[j]<=value<=d[j+1]for j in range(0,len(d),2))
                elif c.has_bool_or():valid=any(literal(n)for n in c.bool_or.literals)
                elif c.has_exactly_one():valid=sum(literal(n)for n in c.exactly_one.literals)==1
                else:raise ValueError('FRAME_BANK_GEOMETRY_COMPLETE_HINT_CONSTRAINT_KIND')
                if not valid:complete_hint_violations.append('constraint:'+str(i))
            complete_hint_verified=not complete_hint_violations
            if complete_hint_verified:
                model.clear_hints();hinted=set(values)
                for i,value in values.items():model.add_hint(model.get_int_var_from_proto_index(i),value)
    repair_fixed_variables=0
    if repair_interval is not None:
        if not complete_hint_verified:raise ValueError('FRAME_BANK_GEOMETRY_REPAIR_REQUIRES_VERIFIED_COMPLETE_HINT')
        first,last=repair_interval;fixed={}
        for(y,b,c),v in list(palette.items())+list(cache_load_vars.items()):
            if not first<=y<=last:fixed[v.index]=v
        for(y,mode),v in mode_choices.items():
            if not first<=y<=last:fixed[v.index]=v
        for(y,x),v in gates.items():
            if not first<=y<=last:fixed[v.index]=v
        for i,b,j,v in assignments:
            if not first<=atoms[j][1][0][0]<=last:fixed[v.index]=v
        for(i,b),v in masks.items():
            p=rectangles[i]
            if p['y']>last or p['y']+p['height']<=first:fixed[v.index]=v
        for i,v in fixed.items():model.add(v==values[i])
        repair_fixed_variables=len(fixed)
    backend_report={}
    if solver_backend=='highspy':
        from raster_bank_residency import solve_linear
        from types import SimpleNamespace
        values,backend_report=solve_linear(model,time_limit,native_highs=True)
        status={'OPTIMAL':cp_model.OPTIMAL,'FEASIBLE':cp_model.FEASIBLE,'INFEASIBLE':cp_model.INFEASIBLE}.get(backend_report['solver_status'],cp_model.UNKNOWN)
        solver=SimpleNamespace(value=values,wall_time=backend_report['solver_seconds'],
            best_objective_bound=backend_report.get('solver_objective_lower_bound'),status_name=lambda s:backend_report['solver_status'])
    else:
        solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit;solver.parameters.num_search_workers=4
        if search_strategy=='lns':solver.parameters.use_lns_only=True
        status=solver.solve(model)
    report=dict(schema='BYOR_FIXED_FRAME_BANK_GEOMETRY_V1',status='BOUNDED_FRAME_BANK_GEOMETRY_NO_WITNESS',
        solver_status=solver.status_name(status),solver_seconds=solver.wall_time,solver_objective_lower_bound=solver.best_objective_bound,
        model_variables=len(model.proto.variables),model_constraints=len(model.proto.constraints),candidate_rectangles=len(rectangles),
        source_pixel_count=len(pixel_options),bank_count=8,opaque_slots_per_bank=15,fixed_bank_for_entire_oam_rectangle=True,
        equivalent_pixel_decision_atoms=len(atoms),equivalent_pixel_decisions_coalesced=len(pixel_options)-len(atoms),
        independent_required_word_coverage_clauses=len(pool_clauses),
        safe_class_bank_label_symmetry=bank_symmetry,bank_order_timing_not_modeled=cache_window is None,
        solver_objective='MINIMUM_FRAME_BANK_WORD_IDENTITIES_THEN_ROW_WORDS_THEN_OAM'if minimize_frame_palette_words else'MINIMUM_IDEAL_CACHE_PEAK_SPAN'if minimize_cache_span else'MINIMUM_ROW_PALETTE_WORDS_THEN_OAM'if minimize_row_palette_words else'FEASIBILITY_ONLY'if feasibility_only else'MINIMUM_OAM_ENTRIES',
        solver_search_strategy=search_strategy,
        repair_interval=list(repair_interval)if repair_interval is not None else None,
        outside_repair_cache_and_pixel_owners_fixed=repair_interval is not None,repair_fixed_variables=repair_fixed_variables,
        soft_geometry_hint_variables=len(hinted),
        complete_source_witness_hint_model_verified=complete_hint_verified,
        complete_source_witness_hint_violation_count=len(complete_hint_violations),
        complete_source_witness_hint_first_violations=complete_hint_violations[:8],
        ideal_cache_partition_window_master_clocks=cache_window,
        joint_cache_residency_enforced=cache_window is not None,
        initial_cache_row_relaxed_to_free_vblank=initial_cache_row if cache_window is not None else None,
        full_rectangle_padding_counted=True,oam_y_wrap_counted=True,fully_offscreen_tile_slivers_skipped=True,palette_liveness_and_transfer_cost_relaxed=cache_window is None,
        physical_slots_and_transfer_cost_relaxed=True,native_presentation_proven=False,
        geometry_reservation=reservation if geometry_reservation is not None else None,
        reservation_palette_and_layer_demand_included=False,
        universal_raster_rejected=False,no_color_reduction=True)
    report['shared_scanline_math_modes_searched']=mode_word_options is not None
    report['source_pixel_actor_assignment_enforced']=pixel_actors is not None
    report.update(single_bank_per_candidate_rectangle=single_bank_per_rectangle,required_shared_math_mode=required_math_mode,all_source_math_gates_required=all_source_math_gates)
    report['independent_mode_window_coverage_clauses']=mode_pool_clauses
    report['compatible_selected_mask_residency_links']=residency_mask_links
    report['distinct_singleton_source_word_interval_cuts']=singleton_interval_cuts
    report['pooled_class_singleton_word_interval_cuts']=singleton_class_interval_cuts
    report['outside_repair_math_modes_fixed']=repair_interval is not None and mode_word_options is not None
    report.update(source_exact_color_windows_searched=literal_window_outputs is not None,
        outside_repair_pixel_window_gates_fixed=repair_interval is not None and literal_window_outputs is not None)
    report.update(backend_report);report['solver_backend']=solver_backend
    report['independent_linear_integer_model_verified']=solver_backend=='highspy'and status in(cp_model.FEASIBLE,cp_model.OPTIMAL)
    if status not in(cp_model.FEASIBLE,cp_model.OPTIMAL):return report
    pieces=[];selected={}
    selected_modes={str(y):next(mode for mode in sorted(modes)if solver.value(mode_choices[y,mode]))for y,modes in row_modes.items()}
    if minimize_row_palette_words or minimize_frame_palette_words:report['selected_row_palette_word_count']=sum(solver.value(v)for v in palette.values())
    if minimize_frame_palette_words:report['selected_frame_bank_word_identity_count']=sum(solver.value(v)for v in frame_words.values())
    for (i,b),v in masks.items():
        if solver.value(v):selected[i,b]=len(pieces);pieces.append(dict(rectangles[i],bank=b))
    pixels=[];row_colors={};seen=set()
    for i,b,j,v in assignments:
        if not solver.value(v):continue
        y,x=atoms[j][1][0]
        if literal_window_outputs is not None and b>=4 and not solver.value(gates[y,x]):eligible=[literal_window_outputs[y,x]]
        else:eligible=mode_word_options[y,x][selected_modes[str(y)]].get(b,[])if mode_word_options is not None else pixel_options[y,x][b]
        colors=[c for c in eligible if solver.value(palette[y,b,c])]
        if not colors:raise AssertionError('FRAME_BANK_GEOMETRY_WORD_REPLAY')
        c=min(colors)
        for y,x in atoms[j][1]:
            if(y,x)in seen or(i,b)not in selected:raise AssertionError('FRAME_BANK_GEOMETRY_OWNER_REPLAY')
            if pixel_actors is not None and pixel_actors[y,x]!=rectangles[i].get('actor',0):raise AssertionError('FRAME_BANK_GEOMETRY_ACTOR_IDENTITY_REPLAY')
            seen.add((y,x));pixels.append(dict(piece=selected[i,b],y=y,x=x,bank=b,color=c));row_colors.setdefault((y,b),set()).add(c)
    if seen!=set(pixel_options)or any(len(cs)>15 for cs in row_colors.values()):raise AssertionError('FRAME_BANK_GEOMETRY_CAPACITY_REPLAY')
    if mode_word_options is not None:report.update(selected_modes=selected_modes,shared_row_mode_word_compatibility_replayed=True)
    if literal_window_outputs is not None:
        from raster_math_windows import compile_sparse_mask,evaluate
        descriptors={str(y):compile_sparse_mask({x:solver.value(v)for(yy,x),v in gates.items()if yy==y})for y in inverted_rows}
        for q in pixels:
            if q['bank']<4:continue
            enabled=evaluate(descriptors[str(q['y'])],q['x'])
            eligible=mode_word_options[q['y'],q['x']][selected_modes[str(q['y'])]].get(q['bank'],[])if enabled else[literal_window_outputs[q['y'],q['x']]]
            if q['color']not in eligible:raise AssertionError('FRAME_BANK_GEOMETRY_WINDOW_WORD_REPLAY')
        report.update(compiled_color_window_descriptors=descriptors,hardware_two_color_windows_replayed=True)
    geometry=dict(oam_entries=len(pieces),peak_sprites=max(sum(active_on_line(p,y)for p in pieces)for y in range(height)),
        peak_tile_slivers=max(sum(tile_slivers(p)for p in pieces if active_on_line(p,y))for y in range(height)))
    if geometry['oam_entries']>128 or geometry['peak_sprites']>32 or geometry['peak_tile_slivers']>34:raise AssertionError('FRAME_BANK_GEOMETRY_HARDWARE_REPLAY')
    combined=dict(oam_entries=len(pieces)+reservation['oam_entries'],
        peak_sprites=max(sum(active_on_line(p,y)for p in pieces)+reservation['sprites_per_line'][y]for y in range(height)),
        peak_tile_slivers=max(sum(tile_slivers(p)for p in pieces if active_on_line(p,y))+reservation['tile_slivers_per_line'][y]for y in range(height)))
    if combined['oam_entries']>128 or combined['peak_sprites']>32 or combined['peak_tile_slivers']>34:raise AssertionError('FRAME_BANK_GEOMETRY_RESERVED_HARDWARE_REPLAY')
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
        if repair_interval is not None:report['repair_interval_peak_joint_cache_ideal_span']=max((r['ideal_prepared_commit_span']for r in cache if repair_interval[0]<=r['scanline']<=repair_interval[1]),default=0)
    report.update(status='FIXED_FRAME_BANK_GEOMETRY_AND_WORD_OPTIONS_PROVEN',pieces=pieces,pixels=pixels,geometry=geometry,combined_reserved_geometry=combined,
        declared_word_options_and_fixed_bank_geometry_replayed=True)
    return report


def main():
    import argparse,hashlib,json
    import numpy as np
    from pathlib import Path
    from compiler import Source
    from source_scene_obj_raster import prepare
    from source_scene_bg import compose_rgb8
    from source_bg_feasibility import rgb555
    from raster_slot_greedy import demand
    from raster_scanline_bank_geometry import exact_row_word_options,exact_frame_word_options,exact_frame_mode_word_options
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--schedule',type=Path,required=True)
    p.add_argument('--geometry',type=Path,required=True,help='JSON containing source_rectangle_cover.')
    p.add_argument('--exact-source',type=Path,required=True);p.add_argument('--stage',required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--time-limit',type=float,default=30)
    p.add_argument('--scanline-start',type=int,default=0);p.add_argument('--scanline-end',type=int,default=224)
    p.add_argument('--subdivide',action='store_true');p.add_argument('--bank-symmetry',action='store_true')
    p.add_argument('--feasibility-only',action='store_true')
    p.add_argument('--minimize-row-palette-words',action='store_true',help='Without cache timing, minimize row word demand before OAM count; liveness remains unproved.')
    p.add_argument('--minimize-frame-palette-words',action='store_true',help='Without cache timing, minimize distinct bank words across the frame, then row words and OAM; liveness remains unproved.')
    p.add_argument('--single-bank-per-rectangle',action='store_true',help='Restricted family: prohibit overlapping palette masks within one candidate rectangle.')
    p.add_argument('--required-math-mode',choices=('add','half-add','subtract','half-subtract'))
    p.add_argument('--all-source-math-gates',action='store_true')
    p.add_argument('--movable-math-modes',action='store_true',help='Joint shared row modes with complete exact frame operand domains; source output/windows remain fixed.')
    p.add_argument('--movable-color-windows',action='store_true',help='Joint exact literal/math gates representable by two hardware windows; requires --movable-math-modes.')
    p.add_argument('--geometry-hint',type=Path,help='Soft source-exact geometry witness from a subset of the requested interval.')
    p.add_argument('--cache-window',type=int,help='Joint integer color residency with ideal bank partitions; physical slots remain relaxed.')
    p.add_argument('--geometry-reservation',type=Path,help='Full padded concurrent geometry only; its palette/layer demand is not included.')
    p.add_argument('--hint-input-schedule',action='store_true',help='Soft hints from the independently source-replayed input; dominated row operands are omitted.')
    p.add_argument('--solver-backend',choices=('cp-sat','highspy'),default='cp-sat')
    p.add_argument('--minimize-cache-span',action='store_true',help='Optimize ideal cache span while retaining all geometry and bank constraints.')
    p.add_argument('--search-strategy',choices=('portfolio','lns'),default='portfolio')
    p.add_argument('--repair-interval',nargs=2,type=int,help='Inclusive cache/pixel ownership neighborhood; requires a verified complete input hint.')
    a=p.parse_args()
    if a.movable_color_windows and not a.movable_math_modes:p.error('--movable-color-windows requires --movable-math-modes')
    if not 0<=a.scanline_start<a.scanline_end<=224:p.error('scanline interval must be within [0,224)')
    input_bytes=a.schedule.read_bytes()
    frame=json.loads(input_bytes.decode('utf-8'))
    geometry=json.loads(a.geometry.read_text(encoding='utf-8'));rectangles=geometry['source_rectangle_cover']['rectangles']
    if geometry.get('source_rgb555_sha256')!=frame['source_rgb555_sha256']:
        raise ValueError('FRAME_BANK_GEOMETRY_COVER_SOURCE_IDENTITY')
    source=Source(a.exact_source);scene=frame['metadata']['scene']
    source_actors,metadata,expected=prepare(source,a.stage,scene);expected=rgb555(expected)
    if metadata!=frame['metadata']or hashlib.sha256(expected.astype('<u2').tobytes()).hexdigest()!=frame['source_rgb555_sha256']:
        raise ValueError('FRAME_BANK_GEOMETRY_SOURCE_ARCHIVE_IDENTITY')
    background=rgb555(compose_rgb8(source,a.stage,dict(scene,actors=[]))[0])
    replay=frame
    if frame.get('status')=='POOL_CONSTRUCTION_FIXED_SMALL_GEOMETRY_OVERFLOW':
        if not frame.get('compiled_pixel_identity_verified')or frame.get('hardware_geometry_admitted'):
            raise ValueError('FRAME_BANK_GEOMETRY_OVERFLOW_IDENTITY')
        replay=dict(frame,status='JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN')
    required,_,input_images=demand(replay)
    options={};proofs={};frame_cover=None;mode_options=None;literal_outputs=None
    if a.movable_math_modes:
        options,mode_options,proofs,frame_cover=exact_frame_mode_word_options(frame,background,expected,a.scanline_start,a.scanline_end,a.movable_color_windows)
        literal_outputs=frame_cover.pop('literal_window_outputs')
    elif a.cache_window is not None:
        options,proofs,frame_cover=exact_frame_word_options(frame,background,expected,a.scanline_start,a.scanline_end)
    else:
        for y in range(a.scanline_start,a.scanline_end):
            if not any(required[y]):continue
            row,proof=exact_row_word_options(frame,y,background[y],expected[y]);proofs[str(y)]=proof
            options.update({(y,x):banks for x,banks in row.items()})
    if a.subdivide:rectangles=subdivided_candidates(rectangles,options)
    pixel_actors={}
    if 'source_visible_composite_geometry'in frame:
        from source_visible_obj_composite import merge_visible_actors
        source_actors,composite_proof=merge_visible_actors(source_actors,expected.shape)
        if composite_proof!=frame['source_visible_composite_geometry']:raise ValueError('FRAME_BANK_GEOMETRY_SOURCE_COMPOSITE_IDENTITY')
    authoritative_actors={(actor['top']+int(y),actor['left']+int(x)):i for i,actor in enumerate(source_actors)for y,x in np.argwhere(actor['pixels']>=0)}
    for piece,image in zip(frame['pieces'],input_images):
        for ly,lx in np.argwhere(image>=0):
            point=piece['y']+int(ly),piece['x']+int(lx)
            if point not in options:continue
            if point in pixel_actors:raise ValueError('FRAME_BANK_GEOMETRY_SOURCE_OWNER_OVERLAP')
            if authoritative_actors.get(point)!=piece.get('actor',0):raise ValueError('FRAME_BANK_GEOMETRY_SOURCE_ACTOR_BINDING')
            pixel_actors[point]=piece.get('actor',0)
    print(json.dumps(dict(candidate_rectangles=len(rectangles),source_pixels=len(options))),flush=True)
    hint=json.loads(a.geometry_hint.read_text(encoding='utf-8'))if a.geometry_hint else None
    if a.hint_input_schedule:
        if hint is not None:p.error('--hint-input-schedule and --geometry-hint are mutually exclusive')
        hint=dict(pieces=frame['pieces'],pixels=[],source_rgb555_sha256=frame['source_rgb555_sha256'],cache_resident_colors={},selected_modes=frame['selected_modes'],compiled_color_window_descriptors=frame['compiled_color_window_descriptors'])
        for i,(piece,image)in enumerate(zip(frame['pieces'],input_images)):
            for ly,lx in np.argwhere(image>=0):
                y,x=piece['y']+int(ly),piece['x']+int(lx);b=piece['bank'];c=int(image[ly,lx])
                if (y,x)in options and c in options[y,x].get(b,[]):hint['pixels'].append(dict(piece=i,y=y,x=x,bank=b,color=c))
        state={b:[None]*15 for b in range(8)}
        for row in frame['trace']:
            for e in row['updates']:state[e['bank']][e['slot']-1]=e['color']
            hint['cache_resident_colors'][row['scanline']]={b:[c for c in cs if c is not None]for b,cs in state.items()}
    if hint is not None and hint.get('source_rgb555_sha256')!=frame['source_rgb555_sha256']:
        raise ValueError('FRAME_BANK_GEOMETRY_HINT_SOURCE_IDENTITY')
    reservation=json.loads(a.geometry_reservation.read_text(encoding='utf-8'))if a.geometry_reservation else None
    report=search(rectangles,options,time_limit=a.time_limit,bank_symmetry=a.bank_symmetry,feasibility_only=a.feasibility_only,geometry_hint=hint,cache_window=a.cache_window,geometry_reservation=reservation,solver_backend=a.solver_backend,minimize_cache_span=a.minimize_cache_span,search_strategy=a.search_strategy,repair_interval=a.repair_interval,mode_word_options=mode_options,literal_window_outputs=literal_outputs,pixel_actors=pixel_actors,minimize_row_palette_words=a.minimize_row_palette_words,minimize_frame_palette_words=a.minimize_frame_palette_words,single_bank_per_rectangle=a.single_bank_per_rectangle,required_math_mode=a.required_math_mode,all_source_math_gates=a.all_source_math_gates)
    report.update(source_rgb555_sha256=frame['source_rgb555_sha256'],source_input_sha256=hashlib.sha256(input_bytes).hexdigest(),source_input_path=str(a.schedule),
        source_pak_sha256=hashlib.sha256(a.exact_source.read_bytes()).hexdigest(),source_row_context_proofs=proofs,
        source_rectangle_cover=geometry['source_rectangle_cover'],scanline_interval=[a.scanline_start,a.scanline_end],
        outside_interval_demand_relaxed=(a.scanline_start,a.scanline_end)!=(0,224),
        source_alpha_policy='EXACT_SOURCE_OUTPUT_OPERANDS',alpha_compatibility_policy_selected=False)
    report['source_archive_actor_identity_verified']=True
    if frame_cover is not None:report['frame_operand_identity_cover']=frame_cover
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items()if k not in('pixels','pieces','source_rectangle_cover','source_row_context_proofs','joint_cache_trace','geometry_reservation','compiled_color_window_descriptors')}))


if __name__=='__main__':main()
