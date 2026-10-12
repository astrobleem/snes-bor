"""Alias-aware necessary bank assignment without full cache state variables.

Aggregate interval loads grant independently optimal initial bank contents.
They do not establish liveness, physical slots or a native schedule.
"""
import copy,hashlib,json
from pathlib import Path
from raster_slot_greedy import demand,bank_groups
from raster_bank_rebalance import rebalance
from raster_bank_residency import constrain_flow,favorable_span,solve_linear,flow_partition_hint
from raster_obj_geometry import active_on_line,tile_slivers


def search(source,time_limit=30,window=357,write_budget=22,interval_stride=4,solver_backend='cp-sat',fractional_loads=False,hint_input_schedule=False,minimize_span=False):
    from ortools.sat.python import cp_model
    if time_limit<=0 or type(window)is not int or window<1 or type(write_budget)is not int or not 0<=write_budget<=120 or type(interval_stride)is not int or interval_stride<1:
        raise ValueError('PIECE_INTERVAL_MASTER_DOMAIN')
    if solver_backend not in('cp-sat','highspy'):raise ValueError('PIECE_INTERVAL_MASTER_BACKEND')
    if type(fractional_loads)is not bool or(fractional_loads and solver_backend!='highspy'):raise ValueError('PIECE_INTERVAL_MASTER_FRACTIONAL_BACKEND')
    if type(hint_input_schedule)is not bool or type(minimize_span)is not bool:raise ValueError('PIECE_INTERVAL_MASTER_HINT_OBJECTIVE')
    required,_,images=demand(source);height=len(required);pieces=source['pieces'];groups=bank_groups(source)
    reserve=source.get('geometry_reservation')
    if reserve is None:reserve=dict(oam_entries=0,sprites_per_line=[0]*height,tile_slivers_per_line=[0]*height)
    if not isinstance(reserve,dict)or set(reserve)!={'oam_entries','sprites_per_line','tile_slivers_per_line'}or type(reserve['oam_entries'])is not int or not 0<=reserve['oam_entries']<=128 or any(not isinstance(reserve[k],list)or len(reserve[k])!=height or any(type(v)is not int or not 0<=v<=limit for v in reserve[k])for k,limit in [('sprites_per_line',32),('tile_slivers_per_line',34)]):raise ValueError('PIECE_INTERVAL_MASTER_RESERVATION')
    combined=dict(oam_entries=len(pieces)+reserve['oam_entries'],
        peak_sprites=max(sum(active_on_line(p,y)for p in pieces)+reserve['sprites_per_line'][y]for y in range(height)),
        peak_tile_slivers=max(sum(tile_slivers(p)for p in pieces if active_on_line(p,y))+reserve['tile_slivers_per_line'][y]for y in range(height)))
    base=dict(schema='BYOR_NECESSARY_PIECE_INTERVAL_MASTER_V1',combined_reserved_geometry=combined,
        palette_cache_continuity_relaxed=True,initial_contents_free_for_each_interval=True,
        physical_slots_relaxed=True,physical_transfer_admitted=False,native_timing_admitted=False,
        full_frame_schedule_proven=False,universal_raster_rejected=False,no_color_reduction=True,
        geometry_fixed=True,pixel_words_fixed=True,fixed_bank_per_oam_piece=True,
        concurrent_palette_and_layer_admitted=False,window=window,write_budget=write_budget,
        fractional_aggregate_loads=fractional_loads)
    if combined['oam_entries']>128 or combined['peak_sprites']>32 or combined['peak_tile_slivers']>34:
        return dict(base,status='FIXED_INPUT_GEOMETRY_OVERFLOW')
    rows={};domains={};active=[]
    for i,(p,image)in enumerate(zip(pieces,images)):
        domains[i]=tuple(b for b in next(g for g in groups if p['bank']in g)if b in p.get('allowed_banks',range(8)))
        if not domains[i]:raise ValueError('PIECE_INTERVAL_MASTER_BANK_DOMAIN')
        for ly,row in enumerate(image):
            y=p['y']+ly
            for c in set(map(int,row[row>=0])):rows.setdefault((y,c),set()).add(i);active.append(y)
    if not active:raise ValueError('PIECE_INTERVAL_MASTER_EMPTY')
    first,last=min(active),max(active)
    intervals={(a,min(last,a+span))for a in range(first,last,interval_stride)for span in(4,8,16,32)if a<min(last,a+span)}
    intervals.add((first,last))
    pressure=[]
    for a in range(first,last):
        for span in(2,4,8,16,32):
            z=min(last,a+span)
            unions=[set().union(*(required[y][b]for y in range(a,z+1)))for b in range(8)]
            pressure.append((sum(max(0,len(cs)-15)for cs in unions)/(z-a),a,z))
    intervals.update((a,z)for score,a,z in sorted(pressure,reverse=True)[:32])
    model=cp_model.CpModel();choices={};aliases={}
    for i,p in enumerate(pieces):
        variables=[]
        for b in domains[i]:
            v=model.new_bool_var(f'piece{i}_{b}');choices[i,b]=v;variables.append(v);model.add_hint(v,int(b==p['bank']))
        model.add(sum(variables)==1)
    def alias(bank,indices):
        vs=[choices[i,bank]for i in sorted(indices)if(i,bank)in choices]
        if not vs:return None
        if len(vs)==1:return vs[0]
        key=bank,tuple(v.index for v in vs)
        if key not in aliases:
            q=model.new_bool_var(f'alias{len(aliases)}')
            for v in vs:model.add(q>=v)
            model.add(q<=sum(vs));aliases[key]=q
        return aliases[key]
    for y in range(first,last+1):
        for b in range(8):
            vs=[alias(b,indices)for(yy,c),indices in rows.items()if yy==y]
            vs=[v for v in vs if v is not None]
            if vs:model.add(sum(vs)<=15)
    counts={};prefix={};active_flags={};costs={}
    peak=model.new_int_var(0,window+39,'aggregatePeakCost')if minimize_span else None
    for b in range(8):prefix[first,b]=model.new_constant(0)
    for y in range(first+1,last+1):
        ns=[];flags=[]
        for b in range(8):
            n=model.new_int_var(0,15,f'loads{y}_{b}');counts[y,b]=n;ns.append(n)
            f=model.new_bool_var(f'active{y}_{b}');flags.append(f);model.add(n>=f);model.add(n<=15*f)
            active_flags[y,b]=f
            p=model.new_int_var(0,15*(y-first),f'prefix{y}_{b}');prefix[y,b]=p;model.add(p==prefix[y-1,b]+n)
        model.add(sum(ns)<=write_budget);costs[y]=constrain_flow(model,ns,flags,window,f'master{y}',4,linear=solver_backend=='highspy')
        if peak is not None:model.add(peak>=costs[y])
    for a,z in sorted(intervals):
        users={}
        for(y,c),indices in rows.items():
            if a<=y<=z:users.setdefault(c,set()).update(indices)
        for b in range(8):
            vs=[alias(b,indices)for indices in users.values()]
            vs=[v for v in vs if v is not None]
            if vs:model.add(sum(vs)<=15+prefix[z,b]-prefix[a,b])
    if peak is not None:model.minimize(peak)
    hint_violations=[];full_hint=False
    if hint_input_schedule:
        import re
        values={i:list(v.domain)[0]for i,v in enumerate(model.proto.variables)}
        for(i,b),v in choices.items():values[v.index]=int(pieces[i]['bank']==b)
        for key,v in aliases.items():values[v.index]=int(any(values[i]for i in key[1]))
        saved=source.get('piece_interval_master',{}).get('aggregate_load_counts')
        loads={y:(saved.get(str(y),saved.get(y))if saved is not None else[sum(e['bank']==b for e in source['trace'][y]['updates'])for b in range(8)])for y in range(first+1,last+1)}
        if any(not isinstance(ns,list)or len(ns)!=8 or any(type(n)is not int or not 0<=n<=15 for n in ns)for ns in loads.values()):raise ValueError('PIECE_INTERVAL_MASTER_INTEGER_HINT_COUNTS')
        running=[0]*8;partitions={};line_costs={}
        for y,ns in loads.items():
            line_costs[y],partitions[y]=flow_partition_hint(ns)
            for b,n in enumerate(ns):
                running[b]+=n;values[counts[y,b].index]=n;values[prefix[y,b].index]=running[b];values[active_flags[y,b].index]=int(n>0)
        for i,v in enumerate(model.proto.variables):
            match=re.fullmatch(r'master(\d+)(interval|cost)(\d+)_(\d+)',v.name)
            if match:
                y,kind,a,z=int(match[1]),match[2],int(match[3]),int(match[4]);selected=(a,z)in partitions[y]
                values[i]=int(selected)if kind=='interval'else(24+16*(loads[y][a]if a==z else loads[y][a]+loads[y][z]+16*(z-a-1)+1)if selected else 0)
        if peak is not None:values[peak.index]=max(line_costs.values(),default=0)
        literal=lambda n:bool(values[n]if n>=0 else 1-values[-n-1])
        for i,v in enumerate(model.proto.variables):
            d=list(v.domain)
            if not any(d[j]<=values[i]<=d[j+1]for j in range(0,len(d),2)):hint_violations.append('variable:'+v.name)
        for i,c in enumerate(model.proto.constraints):
            if not all(literal(n)for n in c.enforcement_literal):continue
            if c.has_linear():
                value=sum(values[n]*coefficient for n,coefficient in zip(c.linear.vars,c.linear.coeffs));d=list(c.linear.domain)
                valid=any(d[j]<=value<=d[j+1]for j in range(0,len(d),2))
            elif c.has_bool_or():valid=any(literal(n)for n in c.bool_or.literals)
            else:raise ValueError('PIECE_INTERVAL_MASTER_HINT_CONSTRAINT')
            if not valid:hint_violations.append('constraint:'+str(i))
        if not hint_violations:
            full_hint=True;model.clear_hints()
            for i,value in values.items():model.add_hint(model.get_int_var_from_proto_index(i),value)
    backend_report={}
    if solver_backend=='highspy':
        from types import SimpleNamespace
        continuous={v.index for v in aliases.values()}
        if fractional_loads:continuous.update(v.index for v in [*counts.values(),*prefix.values()])
        value,backend_report=solve_linear(model,time_limit,continuous,native_highs=True)
        status={'OPTIMAL':cp_model.OPTIMAL,'FEASIBLE':cp_model.FEASIBLE,'INFEASIBLE':cp_model.INFEASIBLE}.get(backend_report['solver_status'],cp_model.UNKNOWN)
        solver=SimpleNamespace(value=value,wall_time=backend_report['solver_seconds'],status_name=lambda s:backend_report['solver_status'],num_branches=backend_report['solver_branches'],num_conflicts=None)
    else:
        solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit;solver.parameters.num_search_workers=4
        solver.parameters.cp_model_probing_level=0;solver.parameters.stop_after_first_solution=not minimize_span
        status=solver.solve(model)
    report=dict(base,status='BOUNDED_INTERVAL_MASTER_NO_ASSIGNMENT',solver_status=solver.status_name(status),solver_backend=solver_backend,
        solver_seconds=solver.wall_time,variables=len(model.proto.variables),constraints=len(model.proto.constraints),
        interval_count=len(intervals),selected_source_intervals=[list(pair)for pair in sorted(intervals)],alias_variables=len(aliases),branches=solver.num_branches,conflicts=solver.num_conflicts)
    report.update(backend_report)
    report.update(aggregate_peak_cost_objective=minimize_span,complete_input_aggregate_hint_model_verified=full_hint,
        complete_hint_violation_count=len(hint_violations),complete_hint_first_violations=hint_violations[:8])
    if status not in(cp_model.OPTIMAL,cp_model.FEASIBLE):return report
    assignment=[next(b for b in domains[i]if solver.value(choices[i,b]))for i in range(len(pieces))]
    actual=[{b:set()for b in range(8)}for y in range(height)]
    for(y,c),indices in rows.items():
        for i in indices:actual[y][assignment[i]].add(c)
    if any(len(cs)>15 for row in actual for cs in row.values()):raise AssertionError('PIECE_INTERVAL_MASTER_ROW_CAPACITY')
    loads={y:[solver.value(counts[y,b])for b in range(8)]for y in range(first+1,last+1)}
    for a,z in intervals:
        for b in range(8):
            union=set().union(*(actual[y][b]for y in range(a,z+1)))
            if len(union)>15+sum(loads[y][b]for y in range(a+1,z+1))+1e-6:raise AssertionError('PIECE_INTERVAL_MASTER_UNION_REPLAY')
    for ns in loads.values():
        if sum(ns)>write_budget+1e-6:raise AssertionError('PIECE_INTERVAL_MASTER_WRITE_BUDGET_REPLAY')
        if not fractional_loads and favorable_span([dict(bank=b)for b,n in enumerate(ns)for _ in range(int(round(n)))])>=window:raise AssertionError('PIECE_INTERVAL_MASTER_PARTITION_REPLAY')
    result=rebalance(source,lookahead=height,maximum_moves=0,maximum_interval=1,initial_assignment=assignment)
    report.update(status='NECESSARY_INTERVAL_BANK_ASSIGNMENT_FOUND',assignment=assignment,
        aggregate_load_counts=loads,independent_row_interval_and_partition_replay=not fractional_loads,
        independent_source_rows_and_interval_inequalities_replayed=True)
    if not fractional_loads:report['integer_aggregate_peak_ideal_span']=max((favorable_span([dict(bank=b)for b,n in enumerate(ns)for _ in range(int(round(n)))])for ns in loads.values()),default=0)
    result['piece_interval_master']=report
    return result


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--time-limit',type=float,default=30);p.add_argument('--window',type=int,default=357);p.add_argument('--write-budget',type=int,default=22)
    p.add_argument('--solver-backend',choices=('cp-sat','highspy'),default='cp-sat')
    p.add_argument('--fractional-loads',action='store_true',help='HiGHS necessary relaxation only: permit fractional interval load counts while retaining integer piece banks and range selectors.')
    p.add_argument('--hint-input-schedule',action='store_true');p.add_argument('--minimize-span',action='store_true')
    a=p.parse_args();raw=a.schedule.read_bytes();source=json.loads(raw.decode('utf-8'))
    result=search(source,a.time_limit,a.window,a.write_budget,solver_backend=a.solver_backend,fractional_loads=a.fractional_loads,hint_input_schedule=a.hint_input_schedule,minimize_span=a.minimize_span)
    result.update(source_input_sha256=hashlib.sha256(raw).hexdigest(),source_input_path=str(a.schedule),source_rgb555_sha256=source.get('source_rgb555_sha256'),source_pak_sha256=source.get('source_pak_sha256'))
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    report=result.get('piece_interval_master',result)
    print(json.dumps({k:v for k,v in report.items()if k not in('aggregate_load_counts','assignment')}))


if __name__=='__main__':main()
