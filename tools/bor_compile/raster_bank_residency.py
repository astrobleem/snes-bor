"""Search exact fixed-bank color residency before physical slot placement.

Source pixels and fixed bank assignments are inputs. Prepared-range constraints
grant ideal endpoint packing. A witness still needs physical slots and native
timing; solver infeasibility rejects only this fixed encoding/bank family.
"""
import argparse,copy,hashlib,json,time
from pathlib import Path
import numpy as np
from raster_slot_greedy import demand
from raster_dma_partition import constrain_ranges
from raster_obj_compact import unpack


def restrict_interval(source,first,last):
    """Necessary relaxation retaining only pixel demand inside an interval.

    Original rectangles and bank identities remain fixed. Initial slots may
    contain any interval color. A candidate proves only this restricted demand.
    """
    if not 0<=first<=last<len(source['trace']):raise ValueError('BANK_RESIDENCY_SCANLINE_INTERVAL')
    demand(source)
    result=copy.deepcopy(source);images=[]
    for p,mask in zip(source['pieces'],source['piece_pixel_masks']):
        image=unpack(mask).copy()
        for ly in range(p['height']):
            if not first<=p['y']+ly<=last:image[ly]=0
        flat=image.flatten();images.append(dict(width=p['width'],height=p['height'],packed_nibble_order='low then high',pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex()))
    result['piece_pixel_masks']=images
    result['restricted_scanline_demand_interval']=[first,last]
    result['outside_interval_pixels_relaxed']=True
    result['complete_source_frame_pixel_identity_proven']=False
    result['compiled_pixel_identity_verified']=False
    result['restricted_pixel_identity_verified']=True
    result['status']='RESTRICTED_SCANLINE_DEMAND_ONLY'
    for field in('compiled_indices_sha256','compiled_schedule_sha256','prepared_dma_packets','physical_slot_layout'):result.pop(field,None)
    return result


def relaxed_bound(source,lookahead=17,time_limit=60):
    """Fractional fixed-bank cache lower bound, with independently checked dual."""
    from scipy.optimize import linprog
    from scipy.sparse import coo_matrix
    required,uses,_=demand(source,allow_restricted=True);active=[y for y,row in enumerate(required)if any(row)]
    if not active:raise ValueError('BANK_RESIDENCY_EMPTY')
    first,last=min(active),max(active)
    resident={(b,c,y):i for i,(b,c,y)in enumerate((b,c,y)for b in range(8)for c,lines in sorted(uses[b].items())for y in range(first,max(lines)+1))}
    writes={key:len(resident)+i for i,key in enumerate(key for key in resident if key[2]>first)}
    peak=len(resident)+len(writes);rr=[];cc=[];vv=[];limits=[];bounds=[(0,1)]*peak+[(0,None)]
    def constraint(items,upper):
        row=len(limits)
        for i,v in items:rr.append(row);cc.append(i);vv.append(v)
        limits.append(upper)
    bank_lines={};write_lines={}
    for (b,c,y),v in resident.items():
        bank_lines.setdefault((b,y),[]).append(v)
        if c in required[y][b]:bounds[v]=(1,1)
        if y>first:
            w=writes[b,c,y];constraint([(v,1),(resident[b,c,y-1],-1),(w,-1)],0)
            write_lines.setdefault(y,[]).append(w)
            if not any(y<=t<=y+lookahead for t in uses[b][c]):bounds[w]=(0,0)
    for values in bank_lines.values():constraint([(v,1)for v in values],15)
    for values in write_lines.values():constraint([(v,1)for v in values]+[(peak,-1)],0)
    matrix=coo_matrix((vv,(rr,cc)),shape=(len(limits),peak+1)).tocsc();objective=np.zeros(peak+1);objective[peak]=1
    r=linprog(objective,A_ub=matrix,b_ub=limits,bounds=bounds,method='highs-ipm',options={'time_limit':time_limit})
    report=dict(schema='BYOR_FIXED_BANK_CACHE_LP_BOUND_V1',status='BOUNDED_FIXED_BANK_LP_NO_BOUND',solver_status=int(r.status),message=r.message,
        variables=peak+1,constraints=len(limits),lookahead_lines=lookahead,geometry_and_pixel_choices_fixed=True,
        physical_slots_and_ranges_relaxed=True,initial_residency_optimal=True,native_timing_admitted=False,universal_raster_rejected=False,no_color_reduction=True)
    report.update(restricted_scanline_demand_interval=source.get('restricted_scanline_demand_interval'),outside_interval_pixels_relaxed=source.get('outside_interval_pixels_relaxed',False))
    if r.success:
        lower=np.array([v[0]for v in bounds]);upper=np.array([np.inf if v[1]is None else v[1]for v in bounds])
        violation=max(float(np.max(np.maximum(matrix@r.x-np.array(limits),0))),float(np.max(np.maximum(lower-r.x,0))),float(np.max(np.maximum(r.x-upper,0))))
        dual=float(np.dot(limits,r.ineqlin.marginals)+np.dot(lower,r.lower.marginals)+np.dot(upper[:-1],r.upper.marginals[:-1]))
        residual=float(np.max(np.abs(objective-matrix.T@r.ineqlin.marginals-r.lower.marginals-r.upper.marginals)))
        if violation>1e-6 or residual>1e-6 or abs(dual-r.fun)>1e-6:raise AssertionError('BANK_CACHE_LP_PRIMAL_DUAL_CERTIFICATE')
        report.update(status='FRACTIONAL_FIXED_BANK_CACHE_LOWER_BOUND',peak_write_lower_bound=float(r.fun),validated_dual_lower_bound=dual,
            maximum_primal_violation=violation,maximum_dual_residual=residual)
    return report


def favorable_span(updates,maximum_ranges=4):
    """Independent exact DP with freely packed bank endpoint slots."""
    counts=[sum(e['bank']==b for e in updates)for b in range(8)]
    banks=[b for b,n in enumerate(counts)if n]
    if not banks:return 0
    best={(0,0):0}
    for end in range(1,len(banks)+1):
        for count in range(1,min(end,maximum_ranges)+1):
            values=[]
            for start in range(count-1,end):
                if(start,count-1)not in best:continue
                a,b=banks[start],banks[end-1]
                words=counts[a]if a==b else counts[a]+counts[b]+16*(b-a-1)+1
                values.append(best[start,count-1]+16*words+24)
            if values:best[end,count]=min(values)
    return max(0,min(best[len(banks),n]for n in range(1,min(len(banks),maximum_ranges)+1))-40)


def constrain_dp(model,counts,active,window,tag,maximum_ranges=4):
    """Favorable bank partition as a computed minimum, without free range bits."""
    infinity=4096;edges={}
    for a in range(8):
        for b in range(a,8):
            overhead=24+(16*(16*(b-a-1)+1)if b!=a else 0)
            if overhead+16*(1 if a==b else 2)>window+39:continue
            enabled=active[a]
            if a!=b:
                enabled=model.new_bool_var(f'{tag}edgeOn{a}_{b}')
                model.add(enabled<=active[a]);model.add(enabled<=active[b]);model.add(enabled>=active[a]+active[b]-1)
            cost=model.new_int_var(0,infinity,f'{tag}edge{a}_{b}')
            expression=16*(counts[a]+(counts[b]if a!=b else 0))+overhead
            model.add(cost==expression).only_enforce_if(enabled);model.add(cost==infinity).only_enforce_if(enabled.Not())
            edges[a,b]=cost
    dp={(n,0):model.new_constant(0)for n in range(maximum_ranges+1)}
    for k in range(1,9):
        any_active=model.new_bool_var(f'{tag}prefix{k}');model.add_max_equality(any_active,active[:k])
        dp[0,k]=model.new_int_var(0,infinity,f'{tag}zero{k}');model.add(dp[0,k]==infinity*any_active)
    for n in range(1,maximum_ranges+1):
        for k in range(1,9):
            skip=model.new_int_var(0,infinity,f'{tag}skip{n}_{k}')
            model.add(skip==dp[n,k-1]).only_enforce_if(active[k-1].Not());model.add(skip==infinity).only_enforce_if(active[k-1])
            candidates=[skip]+[dp[n-1,j]+edges[j,k-1]for j in range(k)if(j,k-1)in edges]
            dp[n,k]=model.new_int_var(0,infinity,f'{tag}dp{n}_{k}');model.add_min_equality(dp[n,k],candidates)
    model.add(dp[maximum_ranges,8]<=window+39)


def constrain_adjacent(model,counts,active,window,tag,write_budget,maximum_ranges=4):
    """Sufficient packet bound restricted to singles and adjacent-bank pairs.

    Each adjacent merge transfers one transparent bridge word and saves one
    range setup: eight master clocks net. Maximum path matching gives the best
    disjoint-pair partition. Wider ranges are deliberately excluded.
    """
    mask=model.new_int_var(0,255,tag+'mask');model.add(mask==sum((1<<b)*active[b]for b in range(8)))
    total=model.new_int_var(0,write_budget,tag+'total');model.add(total==sum(counts))
    # Redundant linear relaxation helps propagate before the mask is fixed.
    # A disjoint adjacent pair saves eight clocks, at most four per active bank.
    model.add(16*total+20*sum(active)<=window+39)
    allowed=[]
    for value in range(256):
        occupied=[bool(value&(1<<b))for b in range(8)];banks=sum(occupied);pairs=0;b=0
        while b<7:
            if occupied[b]and occupied[b+1]:pairs+=1;b+=2
            else:b+=1
        if banks-pairs>maximum_ranges:continue
        for words in range(banks,min(write_budget,15*banks)+1):
            span=max(0,16*words+24*banks-8*pairs-40)
            if span<window:allowed.append((value,words))
    model.add_allowed_assignments([mask,total],allowed)


def solve_linear(model,time_limit):
    """Independent MILP backend for the same explicit integer linear model."""
    from scipy.optimize import milp,Bounds,LinearConstraint
    from scipy.sparse import coo_matrix
    proto=model.proto;n=len(proto.variables);rr=[];cc=[];vv=[];lower=[];upper=[]
    for row,c in enumerate(proto.constraints):
        if not c.has_linear() or c.enforcement_literal:raise ValueError('BANK_RESIDENCY_MILP_REQUIRES_LINEAR_MODEL')
        if len(c.linear.domain)!=2:raise ValueError('BANK_RESIDENCY_MILP_NONCONVEX_DOMAIN')
        for i,v in zip(c.linear.vars,c.linear.coeffs):rr.append(row);cc.append(i);vv.append(v)
        lo,hi=c.linear.domain;lower.append(-np.inf if lo<=-(1<<62)else lo);upper.append(np.inf if hi>=(1<<62)else hi)
    matrix=coo_matrix((vv,(rr,cc)),shape=(len(lower),n)).tocsc()
    # The installed OR-Tools repeated-field wrapper does not support negative
    # indexing like a Python list. Materialize domains before taking the end.
    domains=[list(v.domain)for v in proto.variables]
    bounds=Bounds([d[0]for d in domains],[d[-1]for d in domains])
    objective=np.zeros(n)
    for i,c in zip(proto.objective.vars,proto.objective.coeffs):objective[i]=c
    started=time.monotonic();r=milp(objective,integrality=np.ones(n),bounds=bounds,constraints=LinearConstraint(matrix,lower,upper),options={'time_limit':time_limit,'mip_rel_gap':0})
    report=dict(solver_backend='highs',solver_status=('OPTIMAL'if r.status==0 else'INFEASIBLE'if r.status==2 else'FEASIBLE'if r.x is not None else'UNKNOWN'),
        solver_seconds=time.monotonic()-started,solver_model_variables=n,solver_model_constraints=len(lower),solver_branches=getattr(r,'mip_node_count',None),solver_conflicts=None,
        solver_message=r.message)
    if r.x is None:return None,report
    values=np.rint(r.x);lhs=matrix@values
    violation=max(float(np.max(np.maximum(np.array(lower)-lhs,0))),float(np.max(np.maximum(lhs-np.array(upper),0))),
        float(np.max(np.maximum(bounds.lb-values,0))),float(np.max(np.maximum(values-bounds.ub,0))),float(np.max(np.abs(values-r.x))))
    if violation>1e-6:raise AssertionError('BANK_RESIDENCY_MILP_INTEGER_REPLAY')
    report['maximum_integer_constraint_violation']=violation
    return lambda variable:int(values[variable.index]),report


def optimize(source,write_budget=18,lookahead=17,window=344,time_limit=180,range_backend='dp',repair_interval=None,solver_backend='cp-sat',residency_hint=None,minimize_writes=False):
    from ortools.sat.python import cp_model
    if write_budget<0 or lookahead<0 or(window is not None and window<1):raise ValueError('BANK_RESIDENCY_DOMAIN')
    if range_backend not in('dp','ranges','adjacent'):raise ValueError('BANK_RESIDENCY_RANGE_BACKEND')
    if solver_backend not in('cp-sat','highs')or(solver_backend=='highs'and window is not None and range_backend!='ranges'):raise ValueError('BANK_RESIDENCY_SOLVER_BACKEND')
    if repair_interval is not None and (len(repair_interval)!=2 or repair_interval[0]<0 or repair_interval[1]<repair_interval[0]):raise ValueError('BANK_RESIDENCY_REPAIR_INTERVAL')
    required,uses,pixels=demand(source,allow_restricted=True);height=len(required)
    active=[y for y,row in enumerate(required)if any(row)]
    if not active:raise ValueError('BANK_RESIDENCY_EMPTY')
    first,last=min(active),max(active);model=cp_model.CpModel();resident={};writes={};variables=[]
    before={b:[None]*15 for b in range(8)};hints=[]
    for row in source['trace']:
        for e in row['updates']:before[e['bank']][e['slot']-1]=e['color']
        hints.append({b:set(c for c in values if c is not None)for b,values in before.items()})
    hint_interval=None
    if residency_hint is not None:
        _,_,hint_pixels=demand(residency_hint,allow_restricted=True)
        hint_interval=residency_hint.get('restricted_scanline_demand_interval',[0,height-1])
        if len(hint_interval)!=2 or not 0<=hint_interval[0]<=hint_interval[1]<height:raise ValueError('BANK_RESIDENCY_HINT_INTERVAL')
        if residency_hint['pieces']!=source['pieces']or len(residency_hint['trace'])!=height:raise ValueError('BANK_RESIDENCY_HINT_GEOMETRY')
        for p,a,b in zip(source['pieces'],pixels,hint_pixels):
            for ly in range(p['height']):
                if hint_interval[0]<=p['y']+ly<=hint_interval[1]and not np.array_equal(a[ly],b[ly]):raise ValueError('BANK_RESIDENCY_HINT_PIXEL_IDENTITY')
        hint_state={b:[None]*15 for b in range(8)}
        for y,row in enumerate(residency_hint['trace']):
            for e in row['updates']:hint_state[e['bank']][e['slot']-1]=e['color']
            if hint_interval[0]<=y<=hint_interval[1]:hints[y]={b:set(c for c in values if c is not None)for b,values in hint_state.items()}
    by_line={};write_lines={}
    for b in range(8):
        for c,lines in sorted(uses[b].items()):
            for y in range(first,max(lines)+1):
                r=model.new_bool_var(f'r{b}_{c}_{y}');resident[b,c,y]=r;by_line.setdefault((b,y),[]).append(r)
                if len(uses[b])<=15:model.add(r==1)
                model.add_hint(r,int(c in hints[y][b]))
                if repair_interval is not None and not repair_interval[0]<=y<=repair_interval[1] and len(uses[b])>15:model.add(r==int(c in hints[y][b]))
                if c in required[y][b]:model.add(r==1)
                if y==first:continue
                previous=resident[b,c,y-1]
                if not any(y<=t<=y+lookahead for t in lines):model.add(r<=previous);continue
                w=model.new_bool_var(f'w{b}_{c}_{y}');writes[b,c,y]=w
                model.add(w>=r-previous);model.add(w<=r);model.add(w+previous<=1)
                model.add_hint(w,int(c in hints[y][b]and c not in hints[y-1][b]))
                index=len(variables);variables.append(w);write_lines.setdefault((b,y),[]).append(index)
    for values in by_line.values():model.add(sum(values)<=15)
    # A bank begins any interval with at most fifteen resident identities.
    # Each other distinct demanded identity needs a write after its first row.
    # These valid aggregate cuts expose compulsory loads before branching on
    # individual cache lifetimes. Limit interval length to bound model growth.
    interval_cuts=0
    for b in range(8):
        for begin in range(first,last):
            colors=set(required[begin][b]);indices=[]
            for end in range(begin+1,min(last,begin+32)+1):
                colors.update(required[end][b]);indices.extend(write_lines.get((b,end),[]))
                compulsory=len(colors)-15
                if compulsory>0:
                    model.add(sum(variables[i]for i in indices)>=compulsory);interval_cuts+=1
    def allocate():
        index=len(variables);variables.append(model.new_int_var(0,30,'range'+str(index)));return index
    def constraint(items,lo,hi):
        expression=sum(variables[i]*v for i,v in items)
        if np.isfinite(lo):model.add(expression>=int(lo))
        if np.isfinite(hi):model.add(expression<=int(hi))
    for y in range(first+1,last+1):
        line={b:write_lines.get((b,y),[])for b in range(8)}
        model.add(sum(variables[i]for values in line.values()for i in values)<=write_budget)
        if window is None:continue
        active_flags={}
        for b,values in line.items():
            index=len(variables);flag=model.new_bool_var(f'active{b}_{y}');variables.append(flag);active_flags[b]=index
            if values:
                for i in values:model.add(flag>=variables[i])
                model.add(flag<=sum(variables[i]for i in values))
            else:model.add(flag==0)
        if range_backend in('dp','adjacent'):
            counts=[]
            for b in range(8):
                count=model.new_int_var(0,15,f'count{b}_{y}');model.add(count==sum(variables[i]for i in line[b]));counts.append(count)
            if range_backend=='dp':constrain_dp(model,counts,[variables[active_flags[b]]for b in range(8)],window,f'line{y}')
            else:constrain_adjacent(model,counts,[variables[active_flags[b]]for b in range(8)],window,f'line{y}',write_budget)
        else:constrain_ranges(line,active_flags,allocate,constraint,window,maximum_ranges=4)
    if minimize_writes:model.minimize(sum(writes.values()))
    if solver_backend=='highs':value,statistics=solve_linear(model,time_limit)
    else:
        solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit;solver.parameters.num_search_workers=4
        solver.parameters.cp_model_probing_level=0;solver.parameters.use_sat_inprocessing=False
        solver.parameters.stop_after_first_solution=not minimize_writes
        status=solver.solve(model);value=solver.value if status in(cp_model.FEASIBLE,cp_model.OPTIMAL)else None
        statistics=dict(solver_backend='cp-sat',solver_status=solver.status_name(status),solver_seconds=solver.wall_time,
            solver_model_variables=len(model.proto.variables),solver_model_constraints=len(model.proto.constraints),solver_branches=solver.num_branches,solver_conflicts=solver.num_conflicts)
    report=dict(schema='BYOR_FIXED_BANK_RESIDENCY_V1',status='BOUNDED_FIXED_BANK_RESIDENCY_NO_CANDIDATE',**statistics,write_budget=write_budget,lookahead_lines=lookahead,
        prepared_window_master_clocks=window,range_backend=range_backend,static_bank_dominance_enforced=True,initial_residency_optimal=True,initial_palette_may_preload_entire_frame=True,
        physical_endpoint_slots_relaxed=True,physical_slot_schedule_proven=False,native_timing_admitted=False,
        universal_raster_rejected=False,no_color_reduction=True)
    report['fixed_outside_repair_interval']=repair_interval
    report['ranges_restricted_to_single_or_adjacent_pair']=range_backend=='adjacent' and window is not None
    report['restricted_scanline_demand_interval']=source.get('restricted_scanline_demand_interval')
    report['outside_interval_pixels_relaxed']=source.get('outside_interval_pixels_relaxed',False)
    report['complete_source_frame_pixel_identity_proven']=False
    report['compulsory_bank_interval_cuts']=interval_cuts
    report['soft_residency_hint_interval']=hint_interval
    report['total_noninitial_writes_objective']=minimize_writes
    if value is None:return report
    planned={y:{b:set()for b in range(8)}for y in range(first,last+1)}
    for (b,c,y),r in resident.items():
        if value(r):planned[y][b].add(c)
    state={b:[None]*15 for b in range(8)};states=[];trace=[];latency=0
    initial=planned[first]
    for y in range(height):
        wanted=initial if y<first else planned[y]if y<=last else {b:set()for b in range(8)}
        before=copy.deepcopy(state);events=[]
        for b in range(8):
            missing=sorted(wanted[b]-set(state[b]))
            free=[s for s,c in enumerate(state[b])if c not in wanted[b]]
            if len(free)<len(missing):raise AssertionError('BANK_RESIDENCY_SLOT_CAPACITY')
            if missing:
                k=len(missing);selected=min((free[i:i+k]for i in range(len(free)-k+1)),key=lambda v:(v[-1]-v[0],v[0]))
                for s,c in zip(selected,missing):
                    lead=next(t-y for t in uses[b][c]if t>=y)
                    if y and lead>lookahead:raise AssertionError('BANK_RESIDENCY_PREFETCH_BOUND')
                    if y:latency=max(latency,lead)
                    events.append(dict(bank=b,slot=s+1,old=state[b][s],color=c,kind='required'if c in required[y][b]else'prefetch'));state[b][s]=c
        if y and len(events)>write_budget:raise AssertionError('BANK_RESIDENCY_EXACT_WRITE_COUNT')
        if y and window is not None and favorable_span(events)>=window:raise AssertionError('BANK_RESIDENCY_INDEPENDENT_PREPARED_BOUND')
        trace.append(dict(scanline=y,resident_before=before,retained={b:[c for c in before[b]if c is not None and c in state[b]]for b in range(8)},evicted=[e['old']for e in events if e['old']is not None],prefetched=[e for e in events if e['kind']=='prefetch'],updates=events,colors_written=len(events),cgram_data_bytes=2*len(events),affected_banks=sorted({e['bank']for e in events})))
        states.append(copy.deepcopy(state))
    images=[];indices=np.zeros((height,256),dtype=np.uint8)
    for p,colors in zip(source['pieces'],pixels):
        image=np.zeros(colors.shape,dtype=np.uint8)
        for ly,lx in zip(*np.where(colors>=0)):
            y,x=p['y']+int(ly),p['x']+int(lx);c=int(colors[ly,lx]);s=states[y][p['bank']].index(c)+1
            image[ly,lx]=s;indices[y,x]=128+16*p['bank']+s
            if states[y][p['bank']][s-1]!=c:raise AssertionError('BANK_RESIDENCY_PIXEL_REPLAY')
        flat=image.flatten();images.append(dict(width=p['width'],height=p['height'],packed_nibble_order='low then high',pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex()))
    report.update(status='FIXED_BANK_RESIDENCY_AND_PIXEL_IDENTITIES_PROVEN',peak_scheduled_writes=max(r['colors_written']for r in trace[1:]),
        maximum_noninitial_prefetch_latency_lines=latency,pixel_color_identity_verified=True,
        independent_prepared_partition_bound_verified=window is not None,peak_optimistic_prepared_span=max(favorable_span(r['updates'])for r in trace[1:]))
    report['complete_source_frame_pixel_identity_proven']=not report['outside_interval_pixels_relaxed']
    report['total_noninitial_scheduled_writes']=sum(r['colors_written']for r in trace[1:])
    result=copy.deepcopy(source)
    for key in('physical_slot_layout','prepared_dma_packets'):result.pop(key,None)
    result.update(trace=trace,piece_pixel_masks=images,bank_residency=report,write_budget=write_budget,lookahead_lines=lookahead,
        prepared_dma_window_master_clocks=window,prepared_dma_partition_bound_enforced=window is not None,prepared_dma_window_is_optimistic_necessary_only=True,
        maximum_noninitial_prefetch_latency_lines=latency,noninitial_prefetch_lookahead_enforced=True,noninitial_prefetch_latency_replayed=True,
        schedule_latency_requirement=dict(maximum_noninitial_prefetch_lines=latency,initial_palette_may_preload_entire_frame=True),
        peak_scheduled_writes=report['peak_scheduled_writes'],peak_cgram_data_bytes=max(r['cgram_data_bytes']for r in trace[1:]),
        average_writes=float(np.mean([r['colors_written']for r in trace[1:]])),worst_scanline=1+int(np.argmax([r['colors_written']for r in trace[1:]])),
        compiled_indices_sha256=hashlib.sha256(indices.tobytes()).hexdigest(),native_presentation_proven=False)
    payload=dict(pieces=result['pieces'],pixel_masks=images,trace=trace)
    if result.get('scanline_math_controls_source_bound'):
        payload.update(selected_modes=result['selected_modes'],compiled_color_window_descriptors=result['compiled_color_window_descriptors'])
    result['compiled_schedule_sha256']=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    _,_,replay=demand(result,allow_restricted=True)
    if any(not np.array_equal(a,b)for a,b in zip(pixels,replay)):raise AssertionError('BANK_RESIDENCY_INDEPENDENT_PIXEL_REPLAY')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--write-budget',type=int,default=18);p.add_argument('--lookahead',type=int,default=17);p.add_argument('--window',type=int,default=344);p.add_argument('--time-limit',type=float,default=180)
    p.add_argument('--relaxed-bound',action='store_true')
    p.add_argument('--no-prepared-range-bound',action='store_true')
    p.add_argument('--range-backend',choices=('dp','ranges','adjacent'),default='dp')
    p.add_argument('--repair-interval',type=int,nargs=2,metavar=('FIRST','LAST'))
    p.add_argument('--solver-backend',choices=('cp-sat','highs'),default='cp-sat')
    p.add_argument('--scanline-interval',type=int,nargs=2,metavar=('FIRST','LAST'))
    p.add_argument('--residency-hint',type=Path)
    p.add_argument('--minimize-writes',action='store_true')
    a=p.parse_args();source=json.loads(a.schedule.read_text())
    if a.scanline_interval:source=restrict_interval(source,*a.scanline_interval)
    r=relaxed_bound(source,a.lookahead,a.time_limit)if a.relaxed_bound else optimize(source,a.write_budget,a.lookahead,None if a.no_prepared_range_bound else a.window,a.time_limit,a.range_backend,a.repair_interval,a.solver_backend,json.loads(a.residency_hint.read_text())if a.residency_hint else None,a.minimize_writes);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r.get('bank_residency',r)))


if __name__=='__main__':main()
