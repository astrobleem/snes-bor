"""Construct class cache lifetimes, then assign real banks and fixed OBJ masks.

The class cache is a necessary relaxation, never a 120-slot OBJ admission.
Bank construction fixes that selected cache; failure does not reject raster.
"""
import copy
from raster_slot_greedy import demand,bank_groups
from raster_obj_geometry import active_on_line,tile_slivers
from raster_bank_residency import constrain_flow,solve_linear
from raster_global_bank_classes import rebuild_schedule
from raster_word_cache_repair import compile_cache_rows


def construct(source,time_limit=30,write_budget=22,window=357,lookahead=224,maximum_oam=128,class_cache_hint=None,class_cache_backend='cp-sat',fix_class_cache_hint=False,cache_objective='loads',geometry_edge_migration=False,migration_stride=0,allow_bank_copies=False,bank_backend='cp-sat',assignment_hint=None,minimize_bank_span=False,bank_repair_interval=None,prefetch_margin=0,bank_search_strategy='portfolio'):
    from ortools.sat.python import cp_model
    if time_limit<=0 or type(write_budget)is not int or not 0<=write_budget<=120 or type(window)is not int or window<1 or type(lookahead)is not int or lookahead<0 or type(maximum_oam)is not int or not 1<=maximum_oam<=128:
        raise ValueError('CACHE_SEGMENT_DOMAIN')
    if class_cache_backend not in('cp-sat','highspy'):raise ValueError('CACHE_SEGMENT_BACKEND')
    if type(fix_class_cache_hint)is not bool or(fix_class_cache_hint and class_cache_hint is None):raise ValueError('CACHE_SEGMENT_FIXED_HINT_DOMAIN')
    if cache_objective not in('loads','resident-lines'):raise ValueError('CACHE_SEGMENT_OBJECTIVE')
    if type(geometry_edge_migration)is not bool:raise ValueError('CACHE_SEGMENT_MIGRATION_DOMAIN')
    if type(migration_stride)is not int or migration_stride<0 or(migration_stride and not geometry_edge_migration):raise ValueError('CACHE_SEGMENT_MIGRATION_STRIDE')
    if type(allow_bank_copies)is not bool:raise ValueError('CACHE_SEGMENT_BANK_COPIES_DOMAIN')
    if bank_backend not in('cp-sat','highspy'):raise ValueError('CACHE_SEGMENT_BANK_BACKEND')
    if type(minimize_bank_span)is not bool or(minimize_bank_span and window>16*128+24*3-16):raise ValueError('CACHE_SEGMENT_SPAN_OBJECTIVE_DOMAIN')
    if type(prefetch_margin)is not int or prefetch_margin<0 or(prefetch_margin and not geometry_edge_migration):raise ValueError('CACHE_SEGMENT_PREFETCH_MARGIN')
    if bank_search_strategy not in('portfolio','lns')or(bank_search_strategy=='lns'and bank_backend!='cp-sat'):raise ValueError('CACHE_SEGMENT_BANK_SEARCH_STRATEGY')
    required,_,images=demand(source);groups=bank_groups(source);height=len(required)
    if bank_repair_interval is not None and(not minimize_bank_span or assignment_hint is None or not isinstance(bank_repair_interval,(list,tuple))or len(bank_repair_interval)!=2 or any(type(y)is not int for y in bank_repair_interval)or not 0<=bank_repair_interval[0]<=bank_repair_interval[1]<height):raise ValueError('CACHE_SEGMENT_REPAIR_INTERVAL')
    rows=[[set().union(*(row[b]for b in group))for group in groups]for row in required]
    uses={}
    for y,row in enumerate(rows):
        for k,words in enumerate(row):
            for c in words:uses.setdefault((k,c),set()).add(y)
    if not uses:raise ValueError('CACHE_SEGMENT_EMPTY')
    first=min(y for lines in uses.values()for y in lines);last=max(y for lines in uses.values()for y in lines)
    reserve=source.get('geometry_reservation',dict(oam_entries=0,sprites_per_line=[0]*height,tile_slivers_per_line=[0]*height))
    if not isinstance(reserve,dict)or set(reserve)!={'oam_entries','sprites_per_line','tile_slivers_per_line'}or type(reserve['oam_entries'])is not int or not 0<=reserve['oam_entries']<=128 or any(not isinstance(reserve[k],list)or len(reserve[k])!=height or any(type(v)is not int or not 0<=v<=limit for v in reserve[k])for k,limit in [('sprites_per_line',32),('tile_slivers_per_line',34)]):raise ValueError('CACHE_SEGMENT_RESERVATION')
    hinted=set()
    if class_cache_hint is not None:
        if not isinstance(class_cache_hint,dict)or not isinstance(class_cache_hint.get('class_cache_lifetimes'),list):raise ValueError('CACHE_SEGMENT_HINT_DOMAIN')
        for s in class_cache_hint['class_cache_lifetimes']:
            if not isinstance(s,dict)or set(s)!={'kind','color','first','last'}or any(type(v)is not int for v in s.values()):raise ValueError('CACHE_SEGMENT_HINT_DOMAIN')
            k,c,a,z=s['kind'],s['color'],s['first'],s['last']
            if (k,c)not in uses or not first<=a<=z<=max(uses[k,c])or(a>first and not any(a<=t<=a+lookahead for t in uses[k,c])):raise ValueError('CACHE_SEGMENT_HINT_LIFETIME')
            for y in range(a,z+1):
                if (k,c,y)in hinted:raise ValueError('CACHE_SEGMENT_HINT_DUPLICATE')
                hinted.add((k,c,y))
        if any((k,c,y)not in hinted for(k,c),lines in uses.items()for y in lines):raise ValueError('CACHE_SEGMENT_HINT_SOURCE_WORD')
        if any(sum(kk==k and yy==y for kk,c,yy in hinted)>15*len(g)for k,g in enumerate(groups)for y in range(first,last+1)):raise ValueError('CACHE_SEGMENT_HINT_CAPACITY')
    model=cp_model.CpModel();resident={};loads={};capacity={};line_loads={}
    for (k,c),lines in sorted(uses.items()):
        for y in range(first,max(lines)+1):
            r=model.new_bool_var(f'r{k}_{c}_{y}');resident[k,c,y]=r;capacity.setdefault((y,k),[]).append(r)
            if class_cache_hint is not None:model.add_hint(r,int((k,c,y)in hinted))
            if fix_class_cache_hint:model.add(r==int((k,c,y)in hinted))
            if y in lines:model.add(r==1)
            if y==first:continue
            previous=resident[k,c,y-1]
            w=model.new_bool_var(f'w{k}_{c}_{y}');loads[k,c,y]=w;line_loads.setdefault(y,[]).append(w)
            model.add(w>=r-previous);model.add(w<=r);model.add(w+previous<=1)
            if class_cache_hint is not None:model.add_hint(w,int((k,c,y)in hinted and(k,c,y-1)not in hinted))
            if not any(y<=t<=y+lookahead for t in lines):model.add(w==0)
    for (y,k),variables in capacity.items():model.add(sum(variables)<=15*len(groups[k]))
    for variables in line_loads.values():model.add(sum(variables)<=write_budget)
    # At least ceil(class loads / 15) banks receive writes. Every additional
    # bank costs either a transparent CGRAM word inside a range (16 clocks)
    # or another setup (24 clocks). Grant adjacent banks, packed slots and one
    # setup, yielding the necessary lower bound 16*loads + 16*banks - 32.
    # Complete range constraints remain in the real bank assignment below.
    for y in range(first+1,last+1):
        minimum_banks=[]
        for k,group in enumerate(groups):
            n=sum(w for(kk,c,yy),w in loads.items()if kk==k and yy==y)
            m=model.new_int_var(0,len(group),f'pooledMinimumBanks{y}_{k}');model.add(n<=15*m);minimum_banks.append(m)
        model.add(16*sum(line_loads.get(y,[]))+16*sum(minimum_banks)-32<window)
    objective=sum(loads.values())
    if cache_objective=='resident-lines':objective+=sum(resident.values())*(write_budget*(last-first)+1)
    model.minimize(objective)
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit;solver.parameters.num_search_workers=4
    solver.parameters.cp_model_probing_level=0;solver.parameters.use_sat_inprocessing=False
    if class_cache_backend=='highspy':
        value,statistics=solve_linear(model,time_limit,native_highs=True)
    else:
        status=solver.solve(model);value=solver.value if status in(cp_model.FEASIBLE,cp_model.OPTIMAL)else None
        statistics=dict(solver_status=solver.status_name(status),solver_seconds=solver.wall_time,solver_branches=solver.num_branches,solver_conflicts=solver.num_conflicts)
    report=dict(schema='BYOR_CLASS_CACHE_SEGMENT_BANK_CONSTRUCTION_V1',status='BOUNDED_CLASS_CACHE_NO_CANDIDATE',
        class_cache_backend=class_cache_backend,class_cache_status=statistics['solver_status'],class_cache_seconds=statistics['solver_seconds'],
        class_cache_objective=cache_objective,
        class_cache_branches=statistics['solver_branches'],class_cache_conflicts=statistics['solver_conflicts'],class_cache_backend_report=statistics,
        class_cache_variables=len(model.proto.variables),class_cache_constraints=len(model.proto.constraints),
        source_words_and_classes_fixed=True,class_capacities=[15*len(g)for g in groups],
        class_load_profile_has_necessary_transfer_bound=True,class_load_banks_are_not_persistent=True,
        class_transfer_bound_is_complete_partition_proof=False,
        validated_class_cache_hint_used=class_cache_hint is not None,class_cache_hints_are_soft=not fix_class_cache_hint,
        class_cache_lifetimes_fixed_to_validated_input=fix_class_cache_hint,
        class_cache_hint_scope='class proposal; bank fragments may drop unused residency'if geometry_edge_migration else'actual class residency',
        bank_stage_may_drop_unused_fragments=geometry_edge_migration,
        one_resident_bank_per_class_word_per_line=not allow_bank_copies,
        bank_word_copies_allowed=allow_bank_copies,
        selected_cache_family_only=True,word_bank_can_change_after_eviction=True,
        fixed_bank_per_compiled_oam_entry=True,physical_transfer_admitted=False,native_timing_admitted=False,
        universal_raster_rejected=False,no_color_reduction=True,write_budget=write_budget,window=window,lookahead=lookahead)
    if value is None:return report
    segments=[];at={};actual_loads={}
    for (k,c),lines in sorted(uses.items()):
        start=None
        for y in range(first,max(lines)+2):
            live=y<=max(lines) and bool(value(resident[k,c,y]))
            if live and start is None:start=y
            if not live and start is not None:
                index=len(segments);segments.append(dict(kind=k,color=c,first=start,last=y-1))
                for yy in range(start,y):at[k,c,yy]=index
                if start>first:actual_loads[start]=actual_loads.get(start,0)+1
                start=None
    for y,row in enumerate(rows):
        for k,words in enumerate(row):
            if any((k,c,y)not in at for c in words):raise AssertionError('CACHE_SEGMENT_REQUIRED_WORD')
            if sum(s['kind']==k and s['first']<=y<=s['last']for s in segments)>15*len(groups[k]):raise AssertionError('CACHE_SEGMENT_CLASS_CAPACITY')
    if max(actual_loads.values(),default=0)>write_budget:raise AssertionError('CACHE_SEGMENT_WRITE_REPLAY')
    report.update(status='CLASS_CACHE_LIFETIMES_ONLY',class_cache_lifetimes=segments,
        class_cache_peak_writes=max(actual_loads.values(),default=0),class_cache_total_writes=sum(actual_loads.values()),
        class_cache_total_resident_lines=sum(s['last']-s['first']+1 for s in segments))
    if prefetch_margin:
        expanded=[]
        for s in segments:
            q=dict(s,first=max(first,s['first']-prefetch_margin))
            if expanded and all(expanded[-1][key]==q[key]for key in ('kind','color'))and q['first']<=expanded[-1]['last']+1:
                expanded[-1]['last']=max(expanded[-1]['last'],q['last'])
            else:expanded.append(q)
        segments=expanded
    previous_fragment={}
    if geometry_edge_migration:
        edges={y for p in source['pieces']for y in (p['y'],p['y']+p['height'])if first<y<=last}
        if migration_stride:edges.update(range(first+migration_stride,last+1,migration_stride))
        fragments=[];at={}
        for s in segments:
            starts=[s['first']]+sorted(y for y in edges if s['first']<y<=s['last'])
            previous=None
            for a,z in zip(starts,starts[1:]+[s['last']+1]):
                index=len(fragments);fragments.append(dict(s,first=a,last=z-1))
                if previous is not None:previous_fragment[index]=previous
                for y in range(a,z):at[s['kind'],s['color'],y]=index
                previous=index
        segments=fragments
    report.update(geometry_edge_bank_migration_allowed=geometry_edge_migration,bank_residency_fragments=len(segments),
        additional_bank_fragment_stride=migration_stride,
        bank_interval_prefetch_margin=prefetch_margin,
        continuous_fragment_migrations_require_cgram_writes=True)
    pieces=copy.deepcopy(source['pieces']);piece_segments={};domains={i:set(groups[s['kind']])for i,s in enumerate(segments)};source_owners={}
    for i,(p,image)in enumerate(zip(pieces,images)):
        kind=next(k for k,g in enumerate(groups)if p['bank']in g)
        p['rows']={p['y']+y:sorted(set(map(int,row[row>=0])))for y,row in enumerate(image)if any(row>=0)}
        ids={at[kind,c,y]for y,cs in p['rows'].items()for c in cs};piece_segments[i]=ids
        for y,cs in p['rows'].items():
            for c in cs:source_owners.setdefault((kind,c,y),set()).add(i)
        if not allow_bank_copies:
            for index in ids:domains[index].intersection_update(p.get('allowed_banks',range(8)))
    if any(not domain for domain in domains.values()):return dict(report,status='SELECTED_CACHE_BANK_DOMAIN_EMPTY')
    hinted_owners={};hinted_residency=[]
    if assignment_hint is not None:
        from raster_piece_bank_cache import validated_assignment_hints
        piece_domains={i:tuple(b for b in next(g for g in groups if p['bank']in g)if b in p.get('allowed_banks',range(8)))for i,p in enumerate(pieces)}
        hints=validated_assignment_hints(source,assignment_hint,images,piece_domains,True,True)
        for i,p in enumerate(pieces):
            kind=next(k for k,g in enumerate(groups)if p['bank']in g)
            for y,cs in p['rows'].items():
                for c in cs:
                    if(i,c,y)in hints:hinted_owners.setdefault((i,at[kind,c,y]),set()).add(hints[i,c,y])
        hinted_owners={key:next(iter(bs))for key,bs in hinted_owners.items()if len(bs)==1}
        if len(assignment_hint['trace'])!=height:raise ValueError('CACHE_SEGMENT_ASSIGNMENT_HINT_HEIGHT')
        _,hint_bank_uses,_=demand(assignment_hint)
        state={b:[None]*15 for b in range(8)}
        for row in assignment_hint['trace']:
            for e in row['updates']:state[e['bank']][e['slot']-1]=e['color']
            hinted_residency.append({b:{c for c in cs if c in hint_bank_uses[b]and row['scanline']<=max(hint_bank_uses[b][c])}for b,cs in state.items()})
    report.update(validated_source_assignment_hint_used=assignment_hint is not None,validated_owner_bank_hint_count=len(hinted_owners),owner_bank_hints_are_soft=True)
    model=cp_model.CpModel();choices={};masks={}
    needed_fragments=set().union(*piece_segments.values())
    for index,domain in domains.items():
        choices[index]={b:model.new_bool_var(f'segment{index}_{b}')for b in sorted(domain)}
        if allow_bank_copies:
            if index in needed_fragments:model.add(sum(choices[index].values())>=1)
        elif geometry_edge_migration and index not in needed_fragments:model.add(sum(choices[index].values())<=1)
        else:model.add(sum(choices[index].values())==1)
    owner_choices={}
    for i,ids in piece_segments.items():
        for index in ids:
            allowed=set(pieces[i].get('allowed_banks',range(8)))&domains[index]
            if not allowed:return dict(report,status='SELECTED_CACHE_OWNER_BANK_DOMAIN_EMPTY')
            if allow_bank_copies:
                owner_choices[i,index]={b:model.new_bool_var(f'owner{i}_{index}_{b}')for b in sorted(allowed)}
                model.add(sum(owner_choices[i,index].values())==1)
                for b,v in owner_choices[i,index].items():model.add(v<=choices[index][b])
            else:owner_choices[i,index]=choices[index]
    hint_values={}
    resident_hint_count=0
    if hinted_residency:
        for index,s in enumerate(segments):
            for b,v in choices[index].items():
                values={int(s['color']in hinted_residency[y][b])for y in range(s['first'],s['last']+1)}
                if len(values)==1:hint_values.setdefault(v.index,set()).update(values);resident_hint_count+=1
    for key,b in hinted_owners.items():
        for bank,v in owner_choices[key].items():hint_values.setdefault(v.index,set()).add(int(bank==b))
    variables_by_index={v.index:v for cs in list(owner_choices.values())+list(choices.values())for v in cs.values()}
    for index,values in hint_values.items():
        if len(values)==1:model.add_hint(variables_by_index[index],next(iter(values)))
    report.update(validated_resident_bank_hint_count=resident_hint_count,all_bank_hints_are_soft=True)
    known_hint={int(i):int(v)for i,v in zip(model.proto.solution_hint.vars,model.proto.solution_hint.values)}
    def hint_variable(v,value):
        if v.index not in known_hint:model.add_hint(v,int(value));known_hint[v.index]=int(value)
    if geometry_edge_migration or allow_bank_copies:
        needed_by_word={}
        for key,cs in owner_choices.items():
            s=segments[key[1]];needed_by_word.setdefault((s['kind'],s['color']),[]).append(cs)
        for index,s in enumerate(segments):
            for b,chosen in choices[index].items():
                model.add(chosen<=sum(cs[b]for cs in needed_by_word[s['kind'],s['color']]if b in cs))
    starts={}
    for index,s in enumerate(segments):
        if s['first']==first:continue
        previous=choices.get(previous_fragment.get(index),{})
        for b,chosen in choices[index].items():
            old=previous.get(b)
            if old is None:starts.setdefault((s['first'],b),[]).append(chosen)
            else:
                w=model.new_bool_var(f'migration{index}_{b}')
                model.add(w>=chosen-old);model.add(w<=chosen);model.add(w+old<=1)
                if chosen.index in known_hint and old.index in known_hint:hint_variable(w,int(known_hint[chosen.index]and not known_hint[old.index]))
                starts.setdefault((s['first'],b),[]).append(w)
            if geometry_edge_migration or allow_bank_copies:
                load=starts[s['first'],b][-1]
                future={(i,at[s['kind'],s['color'],y])for y in uses[s['kind'],s['color']]if s['first']<=y<=s['first']+lookahead for i in source_owners[s['kind'],s['color'],y]}
                model.add(load<=sum(owner_choices[key][b]for key in future if b in owner_choices[key]))
    interchangeable=window>16*128+24*3-16 and all(domains[i]==set(groups[s['kind']])for i,s in enumerate(segments))and all(set(cs)==set(groups[segments[index]['kind']])for(i,index),cs in owner_choices.items())
    if interchangeable:
        for group in groups:
            for previous,b in zip(group,group[1:]):
                for index,cs in choices.items():
                    if b in cs:model.add(cs[b]<=sum(choices[j][previous]for j in range(index+1)if previous in choices[j]))
    for i,ids in piece_segments.items():
        for b in sorted({b for index in ids for b in owner_choices[i,index]}):
            v=model.new_bool_var(f'mask{i}_{b}');masks[i,b]=v
            options=[owner_choices[i,index][b]for index in ids if b in owner_choices[i,index]]
            for option in options:model.add(v>=option)
            model.add(v<=sum(options))
            if all(option.index in known_hint for option in options):hint_variable(v,any(known_hint[option.index]for option in options))
    model.add(sum(masks.values())+reserve['oam_entries']<=maximum_oam)
    peak_span=model.new_int_var(0,window-1,'bankPeakSpan')if minimize_bank_span else None
    hinted_spans=[]
    for y in range(height):
        live=[(i,v)for(i,b),v in masks.items()if active_on_line(pieces[i],y)]
        if live:
            model.add(sum(v for i,v in live)+reserve['sprites_per_line'][y]<=32)
            model.add(sum(v*tile_slivers(pieces[i])for i,v in live)+reserve['tile_slivers_per_line'][y]<=34)
        for b in range(8):
            bank_live=[choices[index][b]for index,s in enumerate(segments)if s['first']<=y<=s['last']and b in domains[index]]
            if bank_live:model.add(sum(bank_live)<=15)
        if not first<y<=last or window>16*128+24*3-16:continue
        counts=[];flags=[]
        hint_counts=[]
        for b in range(8):
            n=model.new_int_var(0,15,f'count{y}_{b}')
            model.add(n==sum(starts.get((y,b),[])));counts.append(n)
            v=model.new_bool_var(f'active{y}_{b}');model.add(n>=v);model.add(n<=15*v);flags.append(v)
            row=starts.get((y,b),[])
            if all(w.index in known_hint for w in row):
                count=sum(known_hint[w.index]for w in row);hint_variable(n,count);hint_variable(v,count>0);hint_counts.append(count)
        model.add(sum(counts)<=write_budget)
        cost=constrain_flow(model,counts,flags,window,f'segment{y}',linear=bank_backend=='highspy',hint_counts=hint_counts if len(hint_counts)==8 else None)
        if peak_span is not None:model.add(cost<=peak_span+40)
        if len(hint_counts)==8:
            from raster_bank_residency import flow_partition_hint
            hinted_spans.append(max(0,flow_partition_hint(hint_counts)[0]-40))
    if window>16*128+24*3-16:
        for y in range(first+1,last+1):
            writes=[w for b in range(8)for w in starts.get((y,b),[])]
            if writes:model.add(sum(writes)<=write_budget)
    if peak_span is not None:
        model.minimize(peak_span)
        if hinted_spans and max(hinted_spans)<window:hint_variable(peak_span,max(hinted_spans))
    complete_hint_values={int(i):int(v)for i,v in zip(model.proto.solution_hint.vars,model.proto.solution_hint.values)}
    hint_violations=[];hint_constraint_details=[];complete_hint=len(complete_hint_values)==len(model.proto.variables)
    if complete_hint:
        for i,v in enumerate(model.proto.variables):
            d=list(v.domain)
            if not any(d[j]<=complete_hint_values[i]<=d[j+1]for j in range(0,len(d),2)):hint_violations.append('variable:'+str(i))
        def literal_value(lit):return bool(complete_hint_values[lit])if lit>=0 else not bool(complete_hint_values[-lit-1])
        for i,c in enumerate(model.proto.constraints):
            if c.enforcement_literal and not all(literal_value(lit)for lit in c.enforcement_literal):continue
            if c.has_linear():
                value=sum(k*complete_hint_values[j]for j,k in zip(c.linear.vars,c.linear.coeffs));d=list(c.linear.domain)
                valid=any(d[j]<=value<=d[j+1]for j in range(0,len(d),2))
            elif c.has_bool_or():valid=any(literal_value(lit)for lit in c.bool_or.literals)
            else:valid=False
            if not valid:
                hint_violations.append('constraint:'+str(i))
                if len(hint_constraint_details)<8 and c.has_linear():
                    hint_constraint_details.append(dict(constraint=i,value=value,domain=d,terms=[dict(name=model.proto.variables[j].name,coefficient=k,value=complete_hint_values[j])for j,k in zip(c.linear.vars,c.linear.coeffs)]))
    report.update(complete_bank_hint_model_verified=complete_hint and not hint_violations,
        bank_hint_variable_count=len(complete_hint_values),bank_hint_violation_count=len(hint_violations),bank_hint_first_violations=hint_violations[:8],bank_hint_first_constraint_details=hint_constraint_details)
    frozen={}
    if bank_repair_interval is not None:
        if not complete_hint or hint_violations:raise ValueError('CACHE_SEGMENT_REPAIR_REQUIRES_VERIFIED_COMPLETE_HINT')
        a,z=bank_repair_interval
        for index,cs in choices.items():
            s=segments[index]
            if s['last']<a or s['first']>z:
                for v in cs.values():frozen[v.index]=v
        for(i,index),cs in owner_choices.items():
            s=segments[index]
            if s['last']<a or s['first']>z:
                for v in cs.values():frozen[v.index]=v
        for(i,b),v in masks.items():
            p=pieces[i]
            if p['y']>z or p['y']+p['height']<=a:frozen[v.index]=v
        for index,v in frozen.items():model.add(v==complete_hint_values[index])
    report.update(bank_repair_interval=bank_repair_interval,bank_repair_fixed_variables=len(frozen),outside_repair_bank_residency_and_owner_choices_fixed=bank_repair_interval is not None)
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit;solver.parameters.num_search_workers=4
    solver.parameters.cp_model_probing_level=0;solver.parameters.use_sat_inprocessing=False;solver.parameters.stop_after_first_solution=not minimize_bank_span
    if bank_search_strategy=='lns':solver.parameters.use_lns_only=True
    if bank_backend=='highspy':value,statistics=solve_linear(model,time_limit,native_highs=True)
    else:
        status=solver.solve(model);value=solver.value if status in(cp_model.FEASIBLE,cp_model.OPTIMAL)else None
        statistics=dict(solver_status=solver.status_name(status),solver_seconds=solver.wall_time,solver_branches=solver.num_branches,solver_conflicts=solver.num_conflicts)
    if minimize_bank_span and bank_backend=='cp-sat':statistics['solver_objective_lower_bound']=float(solver.best_objective_bound)
    report.update(status='BOUNDED_SELECTED_CACHE_BANK_NO_CANDIDATE',bank_status=statistics['solver_status'],bank_seconds=statistics['solver_seconds'],
        bank_backend=bank_backend,bank_backend_report=statistics,
        bank_search_strategy=bank_search_strategy,
        bank_objective='MINIMUM_IDEAL_PEAK_SPAN'if minimize_bank_span else'FEASIBILITY_ONLY',
        interchangeable_segment_bank_first_use_order=interchangeable,
        complete_partition_constraints_provably_redundant=window>16*128+24*3-16,
        bank_branches=statistics['solver_branches'],bank_conflicts=statistics['solver_conflicts'],
        bank_variables=len(model.proto.variables),bank_constraints=len(model.proto.constraints),
        geometry_reservation=reserve,reservation_palette_and_layer_demand_included=False)
    if value is None:return report
    assigned={i:{b for b,v in cs.items()if value(v)}for i,cs in choices.items()}
    owner_assigned={key:next(b for b,v in cs.items()if value(v))for key,cs in owner_choices.items()};expanded=[];banks=[]
    for i,p in enumerate(pieces):
        kind=next(k for k,g in enumerate(groups)if p['bank']in g)
        for b in sorted({owner_assigned[i,index]for index in piece_segments[i]}):
            rr={y:[c for c in cs if owner_assigned[i,at[kind,c,y]]==b]for y,cs in p['rows'].items()}
            if any(rr.values()):expanded.append(dict(p,rows=rr,source_piece=i));banks.append(b)
    frame=rebuild_schedule(source,dict(status='JOINT_GLOBAL_BANK_MASK_WORD_IDENTITIES_PROVEN',pieces=expanded,assignment=banks,pixel_word_identities_replayed=True),lookahead)
    desired={y:{b:set()for b in range(8)}for y in range(first,last+1)}
    for index,s in enumerate(segments):
        for b in assigned[index]:
            for y in range(s['first'],s['last']+1):desired[y][b].add(s['color'])
    report.update(status='CLASS_CACHE_SEGMENTS_AND_FIXED_BANK_MASKS_PROVEN',segment_bank_assignment={i:sorted(bs)for i,bs in assigned.items()},
        continuous_bank_copy_load_events=sum(len(assigned[i]-assigned[j])for i,j in previous_fragment.items()if assigned[j]),
        unused_bank_fragments_dropped=sum(not bs for bs in assigned.values()),
        duplicate_bank_fragment_copies=sum(max(0,len(bs)-1)for bs in assigned.values()),
        class_cache_proposal_may_drop_unused_fragments=geometry_edge_migration,
        one_resident_bank_per_class_word_per_line=not allow_bank_copies)
    result=compile_cache_rows(frame,desired,lookahead,write_budget,window,report,'cache_segment_construction')
    combined=dict(oam_entries=len(result['pieces'])+reserve['oam_entries'],
        peak_sprites=max(sum(active_on_line(p,y)for p in result['pieces'])+reserve['sprites_per_line'][y]for y in range(height)),
        peak_tile_slivers=max(sum(tile_slivers(p)for p in result['pieces']if active_on_line(p,y))+reserve['tile_slivers_per_line'][y]for y in range(height)))
    if combined['oam_entries']>maximum_oam or combined['peak_sprites']>32 or combined['peak_tile_slivers']>34:raise AssertionError('CACHE_SEGMENT_GEOMETRY_REPLAY')
    result.update(geometry_reservation=reserve,combined_reserved_geometry=combined,reservation_palette_and_layer_demand_included=False)
    return result


def main():
    import argparse,hashlib,json
    from pathlib import Path
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--time-limit',type=float,default=30);p.add_argument('--write-budget',type=int,default=22)
    p.add_argument('--window',type=int,default=357);p.add_argument('--lookahead',type=int,default=224)
    p.add_argument('--class-cache-hint',type=Path)
    p.add_argument('--class-cache-backend',choices=('cp-sat','highspy'),default='cp-sat')
    p.add_argument('--fix-class-cache-hint',action='store_true',help='Restrict bank diagnosis to exactly the validated input cache lifetimes.')
    p.add_argument('--cache-objective',choices=('loads','resident-lines'),default='loads')
    p.add_argument('--geometry-edge-migration',action='store_true',help='Permit continuous cached words to move banks at geometry boundaries; every new bank copy is charged as a CGRAM write.')
    p.add_argument('--migration-stride',type=int,default=0,help='Additional bank/liveness boundaries within pieces; requires geometry-edge migration. OAM bank masks still retain full padded lifetimes.')
    p.add_argument('--allow-bank-copies',action='store_true',help='Source pieces may select separate resident copies of the same class word. Each bank copy consumes a slot and every new copy is charged.')
    p.add_argument('--bank-backend',choices=('cp-sat','highspy'),default='cp-sat')
    p.add_argument('--assignment-hint',type=Path)
    p.add_argument('--minimize-bank-span',action='store_true')
    p.add_argument('--bank-repair-interval',type=int,nargs=2,metavar=('FIRST','LAST'))
    p.add_argument('--prefetch-margin',type=int,default=0,help='Expand candidate bank-residency intervals earlier; actual bank capacities and compatible lookahead remain enforced.')
    p.add_argument('--bank-search-strategy',choices=('portfolio','lns'),default='portfolio')
    a=p.parse_args();raw=a.schedule.read_bytes();source=json.loads(raw.decode('utf-8'))
    hint=json.loads(a.class_cache_hint.read_text(encoding='utf-8'))if a.class_cache_hint else None
    if hint is not None and hint.get('source_input_sha256')!=hashlib.sha256(raw).hexdigest():raise ValueError('CACHE_SEGMENT_HINT_INPUT_HASH')
    result=construct(source,a.time_limit,a.write_budget,a.window,a.lookahead,class_cache_hint=hint,class_cache_backend=a.class_cache_backend,fix_class_cache_hint=a.fix_class_cache_hint,cache_objective=a.cache_objective,geometry_edge_migration=a.geometry_edge_migration,migration_stride=a.migration_stride,allow_bank_copies=a.allow_bank_copies,bank_backend=a.bank_backend,assignment_hint=json.loads(a.assignment_hint.read_text(encoding='utf-8'))if a.assignment_hint else None,minimize_bank_span=a.minimize_bank_span,bank_repair_interval=a.bank_repair_interval,prefetch_margin=a.prefetch_margin,bank_search_strategy=a.bank_search_strategy)
    result.update(source_input_sha256=hashlib.sha256(raw).hexdigest(),source_input_path=str(a.schedule),source_rgb555_sha256=source.get('source_rgb555_sha256'),source_pak_sha256=source.get('source_pak_sha256'))
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    r=result.get('cache_segment_construction',result);print(json.dumps({k:v for k,v in r.items()if k not in('class_cache_lifetimes','segment_bank_assignment','geometry_reservation')}))


if __name__=='__main__':main()
