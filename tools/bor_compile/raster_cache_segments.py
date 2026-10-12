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


def construct(source,time_limit=30,write_budget=22,window=357,lookahead=224,maximum_oam=128,class_cache_hint=None,class_cache_backend='cp-sat',fix_class_cache_hint=False):
    from ortools.sat.python import cp_model
    if time_limit<=0 or type(write_budget)is not int or not 0<=write_budget<=120 or type(window)is not int or window<1 or type(lookahead)is not int or lookahead<0 or type(maximum_oam)is not int or not 1<=maximum_oam<=128:
        raise ValueError('CACHE_SEGMENT_DOMAIN')
    if class_cache_backend not in('cp-sat','highspy'):raise ValueError('CACHE_SEGMENT_BACKEND')
    if type(fix_class_cache_hint)is not bool or(fix_class_cache_hint and class_cache_hint is None):raise ValueError('CACHE_SEGMENT_FIXED_HINT_DOMAIN')
    required,_,images=demand(source);groups=bank_groups(source);height=len(required)
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
    model.minimize(sum(loads.values()))
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit;solver.parameters.num_search_workers=4
    solver.parameters.cp_model_probing_level=0;solver.parameters.use_sat_inprocessing=False
    if class_cache_backend=='highspy':
        value,statistics=solve_linear(model,time_limit,native_highs=True)
    else:
        status=solver.solve(model);value=solver.value if status in(cp_model.FEASIBLE,cp_model.OPTIMAL)else None
        statistics=dict(solver_status=solver.status_name(status),solver_seconds=solver.wall_time,solver_branches=solver.num_branches,solver_conflicts=solver.num_conflicts)
    report=dict(schema='BYOR_CLASS_CACHE_SEGMENT_BANK_CONSTRUCTION_V1',status='BOUNDED_CLASS_CACHE_NO_CANDIDATE',
        class_cache_backend=class_cache_backend,class_cache_status=statistics['solver_status'],class_cache_seconds=statistics['solver_seconds'],
        class_cache_branches=statistics['solver_branches'],class_cache_conflicts=statistics['solver_conflicts'],class_cache_backend_report=statistics,
        class_cache_variables=len(model.proto.variables),class_cache_constraints=len(model.proto.constraints),
        source_words_and_classes_fixed=True,class_capacities=[15*len(g)for g in groups],
        class_load_profile_has_necessary_transfer_bound=True,class_load_banks_are_not_persistent=True,
        class_transfer_bound_is_complete_partition_proof=False,
        validated_class_cache_hint_used=class_cache_hint is not None,class_cache_hints_are_soft=not fix_class_cache_hint,
        class_cache_lifetimes_fixed_to_validated_input=fix_class_cache_hint,
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
        class_cache_peak_writes=max(actual_loads.values(),default=0),class_cache_total_writes=sum(actual_loads.values()))
    pieces=copy.deepcopy(source['pieces']);piece_segments={};domains={i:set(groups[s['kind']])for i,s in enumerate(segments)}
    for i,(p,image)in enumerate(zip(pieces,images)):
        kind=next(k for k,g in enumerate(groups)if p['bank']in g)
        p['rows']={p['y']+y:sorted(set(map(int,row[row>=0])))for y,row in enumerate(image)if any(row>=0)}
        ids={at[kind,c,y]for y,cs in p['rows'].items()for c in cs};piece_segments[i]=ids
        for index in ids:domains[index].intersection_update(p.get('allowed_banks',range(8)))
    if any(not domain for domain in domains.values()):return dict(report,status='SELECTED_CACHE_BANK_DOMAIN_EMPTY')
    model=cp_model.CpModel();choices={};masks={}
    for index,domain in domains.items():
        choices[index]={b:model.new_bool_var(f'segment{index}_{b}')for b in sorted(domain)}
        model.add_exactly_one(list(choices[index].values()))
    interchangeable=window>16*128+24*3-16 and all(domains[i]==set(groups[s['kind']])for i,s in enumerate(segments))
    if interchangeable:
        for group in groups:
            for previous,b in zip(group,group[1:]):
                for index,cs in choices.items():
                    if b in cs:model.add(cs[b]<=sum(choices[j][previous]for j in range(index+1)if previous in choices[j]))
    for i,ids in piece_segments.items():
        for b in sorted({b for index in ids for b in domains[index]}):
            v=model.new_bool_var(f'mask{i}_{b}');masks[i,b]=v
            model.add_max_equality(v,[choices[index][b]for index in ids if b in domains[index]])
    model.add(sum(masks.values())+reserve['oam_entries']<=maximum_oam)
    for y in range(height):
        live=[(i,v)for(i,b),v in masks.items()if active_on_line(pieces[i],y)]
        model.add(sum(v for i,v in live)+reserve['sprites_per_line'][y]<=32)
        model.add(sum(v*tile_slivers(pieces[i])for i,v in live)+reserve['tile_slivers_per_line'][y]<=34)
        for b in range(8):
            model.add(sum(choices[index][b]for index,s in enumerate(segments)if s['first']<=y<=s['last']and b in domains[index])<=15)
        if not first<y<=last or window>16*128+24*3-16:continue
        counts=[];flags=[]
        for b in range(8):
            n=model.new_int_var(0,15,f'count{y}_{b}')
            model.add(n==sum(choices[index][b]for index,s in enumerate(segments)if s['first']==y and b in domains[index]));counts.append(n)
            v=model.new_bool_var(f'active{y}_{b}');model.add(n>=v);model.add(n<=15*v);flags.append(v)
        constrain_flow(model,counts,flags,window,f'segment{y}')
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit;solver.parameters.num_search_workers=4
    solver.parameters.cp_model_probing_level=0;solver.parameters.use_sat_inprocessing=False;solver.parameters.stop_after_first_solution=True
    status=solver.solve(model)
    report.update(status='BOUNDED_SELECTED_CACHE_BANK_NO_CANDIDATE',bank_status=solver.status_name(status),bank_seconds=solver.wall_time,
        interchangeable_segment_bank_first_use_order=interchangeable,
        complete_partition_constraints_provably_redundant=window>16*128+24*3-16,
        bank_branches=solver.num_branches,bank_conflicts=solver.num_conflicts,
        bank_variables=len(model.proto.variables),bank_constraints=len(model.proto.constraints),
        geometry_reservation=reserve,reservation_palette_and_layer_demand_included=False)
    if status not in(cp_model.FEASIBLE,cp_model.OPTIMAL):return report
    assigned={i:next(b for b,v in cs.items()if solver.value(v))for i,cs in choices.items()};expanded=[];banks=[]
    for i,p in enumerate(pieces):
        kind=next(k for k,g in enumerate(groups)if p['bank']in g)
        for b in sorted({assigned[index]for index in piece_segments[i]}):
            rr={y:[c for c in cs if assigned[at[kind,c,y]]==b]for y,cs in p['rows'].items()}
            if any(rr.values()):expanded.append(dict(p,rows=rr,source_piece=i));banks.append(b)
    frame=rebuild_schedule(source,dict(status='JOINT_GLOBAL_BANK_MASK_WORD_IDENTITIES_PROVEN',pieces=expanded,assignment=banks,pixel_word_identities_replayed=True),lookahead)
    desired={y:{b:set()for b in range(8)}for y in range(first,last+1)}
    for index,s in enumerate(segments):
        for y in range(s['first'],s['last']+1):desired[y][assigned[index]].add(s['color'])
    report.update(status='CLASS_CACHE_SEGMENTS_AND_FIXED_BANK_MASKS_PROVEN',segment_bank_assignment=assigned)
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
    a=p.parse_args();raw=a.schedule.read_bytes();source=json.loads(raw.decode('utf-8'))
    hint=json.loads(a.class_cache_hint.read_text(encoding='utf-8'))if a.class_cache_hint else None
    if hint is not None and hint.get('source_input_sha256')!=hashlib.sha256(raw).hexdigest():raise ValueError('CACHE_SEGMENT_HINT_INPUT_HASH')
    result=construct(source,a.time_limit,a.write_budget,a.window,a.lookahead,class_cache_hint=hint,class_cache_backend=a.class_cache_backend,fix_class_cache_hint=a.fix_class_cache_hint)
    result.update(source_input_sha256=hashlib.sha256(raw).hexdigest(),source_input_path=str(a.schedule),source_rgb555_sha256=source.get('source_rgb555_sha256'),source_pak_sha256=source.get('source_pak_sha256'))
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    r=result.get('cache_segment_construction',result);print(json.dumps({k:v for k,v in r.items()if k not in('class_cache_lifetimes','segment_bank_assignment','geometry_reservation')}))


if __name__=='__main__':main()
