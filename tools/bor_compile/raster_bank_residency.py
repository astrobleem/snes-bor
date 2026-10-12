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


def relaxed_bound(source,lookahead=17,time_limit=60,include_dual_pressure=False):
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
    capacity_rows={};write_rows={}
    for key,values in bank_lines.items():
        capacity_rows[key]=len(limits);constraint([(v,1)for v in values],15)
    for y,values in write_lines.items():
        write_rows[y]=len(limits);constraint([(v,1)for v in values]+[(peak,-1)],0)
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
        if include_dual_pressure:
            report['dual_active_bank_capacity']=[dict(bank=b,scanline=y,marginal=float(r.ineqlin.marginals[row]))for (b,y),row in capacity_rows.items()if abs(r.ineqlin.marginals[row])>1e-8]
            report['dual_active_write_limits']=[dict(scanline=y,marginal=float(r.ineqlin.marginals[row]))for y,row in write_rows.items()if abs(r.ineqlin.marginals[row])>1e-8]
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


def bridge_relaxed_span(updates):
    """Necessary cost granting all adjacent bridges, including overlapping ones."""
    counts=[sum(e['bank']==b for e in updates)for b in range(8)]
    active=[int(n>0)for n in counts]
    return max(0,16*sum(counts)+24*sum(active)-8*sum(a*b for a,b in zip(active,active[1:]))-40)


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
    return dp[maximum_ranges,8]


def flow_partition_hint(counts,maximum_ranges=4):
    """Exact ideal endpoint partition for a concrete eight-bank write row."""
    if len(counts)!=8 or any(type(n)is not int or not 0<=n<=15 for n in counts):raise ValueError('FLOW_PARTITION_HINT_COUNTS')
    if type(maximum_ranges)is not int or not 1<=maximum_ranges<=4:raise ValueError('FLOW_PARTITION_HINT_RANGES')
    banks=[b for b,n in enumerate(counts)if n]
    if not banks:return 0,[]
    best=None
    for mask in range(1<<(len(banks)-1)):
        groups=[];start=0
        for i in range(len(banks)):
            if i==len(banks)-1 or mask&(1<<i):groups.append((banks[start],banks[i]));start=i+1
        if len(groups)>maximum_ranges:continue
        cost=sum(24+16*(counts[a]if a==b else counts[a]+counts[b]+16*(b-a-1)+1)for a,b in groups)
        if best is None or cost<best[0]:best=cost,groups
    return best


def constrain_flow(model,counts,active,window,tag,maximum_ranges=4,linear=False,hint_counts=None):
    """Equivalent favorable bank partition using disjoint selected intervals.

    Endpoint words pack freely; every intervening bank is transferred in full.
    Empty intervening banks remain legal. This grants the same ideal geometry
    as constrain_dp, without constructing its nested minimum expressions.
    """
    choices=[];costs=[];coverage=[[]for b in range(8)]
    hint=None
    if hint_counts is not None:
        cost,groups=flow_partition_hint(hint_counts,maximum_ranges)
        if cost<=window+39:hint=set(groups)
    for a in range(8):
        for b in range(a,8):
            overhead=24+(16*(16*(b-a-1)+1)if b!=a else 0)
            if overhead+16*(1 if a==b else 2)>window+39:continue
            chosen=model.new_bool_var(f'{tag}interval{a}_{b}')
            model.add(chosen<=active[a]);model.add(chosen<=active[b]);choices.append(chosen)
            for k in range(a,b+1):coverage[k].append(chosen)
            cost=model.new_int_var(0,window+39,f'{tag}cost{a}_{b}')
            expression=16*(counts[a]+(counts[b]if a!=b else 0))+overhead
            if linear:
                maximum=16*(15+(15 if a!=b else 0))+overhead
                model.add(cost<=maximum*chosen);model.add(cost<=expression);model.add(cost>=expression-maximum*(1-chosen))
            else:
                model.add(cost==expression).only_enforce_if(chosen);model.add(cost==0).only_enforce_if(chosen.Not())
            costs.append(cost)
            if hint is not None:
                selected=(a,b)in hint
                model.add_hint(chosen,int(selected))
                model.add_hint(cost,16*(hint_counts[a]+(hint_counts[b]if a!=b else 0))+overhead if selected else 0)
    for b in range(8):
        model.add(sum(coverage[b])>=active[b]);model.add(sum(coverage[b])<=1)
    model.add(sum(choices)<=maximum_ranges);model.add(sum(costs)<=window+39)
    # Each partition covers every write and crosses at least one transparent
    # word between active banks in the same interval. Unlike a twenty-clock
    # per-bank shortcut, this also holds when a whole middle bank is written.
    model.add(sum(costs)>=16*sum(counts)+16*sum(active)+8*sum(choices))
    return sum(costs)


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
    pair_count=model.new_int_var(0,4,tag+'pairCount')
    pair_table=[]
    for value in range(256):
        pairs=0;b=0
        while b<7:
            if value&(1<<b)and value&(1<<(b+1)):pairs+=1;b+=2
            else:b+=1
        pair_table.append((value,pairs))
    model.add_allowed_assignments([mask,pair_count],pair_table)
    return 16*total+24*sum(active)-8*pair_count


def solve_linear(model,time_limit,continuous_variables=None,native_highs=False):
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
    continuous=set(continuous_variables or ());integrality=np.ones(n)
    if any(type(i)is not int or not 0<=i<n for i in continuous):raise ValueError('BANK_RESIDENCY_CONTINUOUS_DOMAIN')
    for i in continuous:integrality[i]=0
    started=time.monotonic()
    if native_highs:
        try:import highspy
        except ImportError as error:raise ValueError('BANK_RESIDENCY_HIGHSPY_NOT_INSTALLED')from error
        from types import SimpleNamespace
        engine=highspy.Highs()
        def checked(status,operation):
            if status==highspy.HighsStatus.kError:raise ValueError('BANK_RESIDENCY_HIGHSPY_'+operation)
        for name,value in [('output_flag',False),('time_limit',float(time_limit)),('mip_rel_gap',0.),('threads',4)]:
            checked(engine.setOptionValue(name,value),'OPTION')
        lp=highspy.HighsLp();lp.num_col_=n;lp.num_row_=len(lower)
        lp.col_cost_=objective;lp.col_lower_=bounds.lb;lp.col_upper_=bounds.ub
        lp.row_lower_=lower;lp.row_upper_=upper
        lp.integrality_=[highspy.HighsVarType.kInteger if integer else highspy.HighsVarType.kContinuous for integer in integrality]
        lp.a_matrix_.format_=highspy.MatrixFormat.kColwise
        lp.a_matrix_.start_=matrix.indptr.astype(np.int32);lp.a_matrix_.index_=matrix.indices.astype(np.int32);lp.a_matrix_.value_=matrix.data
        checked(engine.passModel(lp),'MODEL')
        supplied={}
        for i,value in zip(proto.solution_hint.vars,proto.solution_hint.values):
            if not 0<=i<n or not bounds.lb[i]<=value<=bounds.ub[i] or i in supplied and supplied[i]!=value:
                raise ValueError('BANK_RESIDENCY_HIGHSPY_HINT_DOMAIN')
            supplied[i]=value
        if supplied:checked(engine.setSolution(len(supplied),np.array(list(supplied),dtype=np.int32),np.array(list(supplied.values()),dtype=float)),'HINT')
        checked(engine.run(),'RUN');info=engine.getInfo();solution=engine.getSolution();status=engine.getModelStatus()
        feasible=info.primal_solution_status==highspy.SolutionStatus.kSolutionStatusFeasible and solution.value_valid
        r=SimpleNamespace(x=np.array(solution.col_value)if feasible else None,mip_dual_bound=info.mip_dual_bound)
        report=dict(solver_backend='highspy',solver_version=engine.version(),solver_status='OPTIMAL'if status==highspy.HighsModelStatus.kOptimal else'INFEASIBLE'if status==highspy.HighsModelStatus.kInfeasible else'FEASIBLE'if feasible else'UNKNOWN',
            solver_seconds=time.monotonic()-started,solver_model_variables=n,solver_model_constraints=len(lower),solver_branches=info.mip_node_count,solver_conflicts=None,
            solver_message=engine.modelStatusToString(status),native_mip_start_variable_count=len(supplied),native_mip_start_is_soft=True)
    else:
        r=milp(objective,integrality=integrality,bounds=bounds,constraints=LinearConstraint(matrix,lower,upper),options={'time_limit':time_limit,'mip_rel_gap':0})
        report=dict(solver_backend='highs',solver_status=('OPTIMAL'if r.status==0 else'INFEASIBLE'if r.status==2 else'FEASIBLE'if r.x is not None else'UNKNOWN'),
            solver_seconds=time.monotonic()-started,solver_model_variables=n,solver_model_constraints=len(lower),solver_branches=getattr(r,'mip_node_count',None),solver_conflicts=None,
            solver_message=r.message)
    dual=getattr(r,'mip_dual_bound',None)
    if dual is not None and np.isfinite(dual):report['solver_objective_lower_bound']=float(dual)
    if r.x is None:return None,report
    if not np.all(np.isfinite(r.x)):raise AssertionError('BANK_RESIDENCY_MILP_NONFINITE_SOLUTION')
    values=np.where(integrality,np.rint(r.x),r.x);lhs=matrix@values
    violation=max(float(np.max(np.maximum(np.array(lower)-lhs,0))),float(np.max(np.maximum(lhs-np.array(upper),0))),
        float(np.max(np.maximum(bounds.lb-values,0))),float(np.max(np.maximum(values-bounds.ub,0))),float(np.max(np.abs(values-r.x))))
    if violation>1e-6:raise AssertionError('BANK_RESIDENCY_MILP_INTEGER_REPLAY')
    report['maximum_integer_constraint_violation']=violation
    report['fractional_cache_variables']=len(continuous)
    return lambda variable:float(values[variable.index])if variable.index in continuous else int(values[variable.index]),report


def optimize(source,write_budget=18,lookahead=17,window=344,time_limit=180,range_backend='dp',repair_interval=None,solver_backend='cp-sat',residency_hint=None,minimize_writes=False,minimize_span=False,search_strategy='portfolio',relax_cache=False,maximum_active_banks=None,bank_write_caps=None,collapse_bank_idle_prefix=False):
    from ortools.sat.python import cp_model
    if write_budget<0 or lookahead<0 or(window is not None and window<1):raise ValueError('BANK_RESIDENCY_DOMAIN')
    if range_backend not in('dp','ranges','adjacent','flow','bridge-relaxation'):raise ValueError('BANK_RESIDENCY_RANGE_BACKEND')
    if solver_backend not in('cp-sat','highs','highspy')or(solver_backend in('highs','highspy')and window is not None and range_backend not in('ranges','flow','bridge-relaxation')):raise ValueError('BANK_RESIDENCY_SOLVER_BACKEND')
    if relax_cache and solver_backend not in('highs','highspy'):raise ValueError('BANK_RESIDENCY_RELAXED_CACHE_BACKEND')
    if search_strategy not in('portfolio','lns')or(search_strategy=='lns'and solver_backend!='cp-sat'):raise ValueError('BANK_RESIDENCY_SEARCH_STRATEGY')
    if minimize_span and(window is None or minimize_writes):raise ValueError('BANK_RESIDENCY_SPAN_OBJECTIVE_DOMAIN')
    if maximum_active_banks is not None and(type(maximum_active_banks)is not int or not 1<=maximum_active_banks<=8):raise ValueError('BANK_RESIDENCY_ACTIVE_BANK_DOMAIN')
    if repair_interval is not None and (len(repair_interval)!=2 or repair_interval[0]<0 or repair_interval[1]<repair_interval[0]):raise ValueError('BANK_RESIDENCY_REPAIR_INTERVAL')
    if type(collapse_bank_idle_prefix)is not bool or(collapse_bank_idle_prefix and repair_interval is not None):raise ValueError('BANK_RESIDENCY_IDLE_PREFIX_DOMAIN')
    required,uses,pixels=demand(source,allow_restricted=True);height=len(required)
    active=[y for y,row in enumerate(required)if any(row)]
    if not active:raise ValueError('BANK_RESIDENCY_EMPTY')
    first,last=min(active),max(active);model=cp_model.CpModel();resident={};writes={};variables=[]
    if bank_write_caps is not None:
        if not isinstance(bank_write_caps,dict):raise ValueError('BANK_RESIDENCY_WRITE_CAPS_DOMAIN')
        bank_write_caps={int(y):row for y,row in bank_write_caps.items()}
        if (set(bank_write_caps)!=set(range(first+1,last+1))or
            any(not isinstance(row,list)or len(row)!=8 or any(type(n)is not int or not 0<=n<=15 for n in row)for row in bank_write_caps.values())):
            raise ValueError('BANK_RESIDENCY_WRITE_CAPS_DOMAIN')
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
    bank_first={b:min((y for lines in uses[b].values()for y in lines),default=first)for b in range(8)}
    collapsed_prefix_variables=0
    by_line={};write_lines={}
    for b in range(8):
        for c,lines in sorted(uses[b].items()):
            for y in range(first,max(lines)+1):
                if collapse_bank_idle_prefix and first<y<=bank_first[b]:
                    r=resident[b,c,first];resident[b,c,y]=r;by_line.setdefault((b,y),[]).append(r)
                    if c in required[y][b]:model.add(r==1)
                    collapsed_prefix_variables+=1
                    continue
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
    peak_span_cost=model.new_int_var(0,4096,'favorablePeakCost')if minimize_span else None
    peak_cost_index=None
    if minimize_span and range_backend=='ranges':
        peak_cost_index=len(variables);variables.append(peak_span_cost)
    for y in range(first+1,last+1):
        line={b:write_lines.get((b,y),[])for b in range(8)}
        model.add(sum(variables[i]for values in line.values()for i in values)<=write_budget)
        if bank_write_caps is not None:
            for b,indices in line.items():
                if indices:model.add(sum(variables[i]for i in indices)<=bank_write_caps[y][b])
        if window is None and maximum_active_banks is None:continue
        active_flags={}
        for b,values in line.items():
            index=len(variables);flag=model.new_bool_var(f'active{b}_{y}');variables.append(flag);active_flags[b]=index
            if values:
                if window is None:model.add(sum(variables[i]for i in values)<=15*flag)
                else:
                    for i in values:model.add(flag>=variables[i])
                model.add(flag<=sum(variables[i]for i in values))
            else:model.add(flag==0)
            model.add_hint(flag,int(any(c in hints[y][b]and c not in hints[y-1][b]for c in uses[b])))
        if maximum_active_banks is not None:model.add(sum(variables[i]for i in active_flags.values())<=maximum_active_banks)
        if window is None:continue
        if range_backend=='bridge-relaxation':
            flags=[variables[active_flags[b]]for b in range(8)];bridges=[]
            for b in range(7):
                bridge=model.new_bool_var(f'optimisticBridge{b}_{y}');bridges.append(bridge)
                model.add(bridge<=flags[b]);model.add(bridge<=flags[b+1]);model.add(bridge>=flags[b]+flags[b+1]-1)
            cost=16*sum(variables[i]for indices in line.values()for i in indices)+24*sum(flags)-8*sum(bridges)
            model.add(cost<=window+39)
            if minimize_span:model.add(peak_span_cost>=cost)
            continue
        if range_backend in('dp','adjacent','flow'):
            counts=[]
            for b in range(8):
                count=model.new_int_var(0,15,f'count{b}_{y}');model.add(count==sum(variables[i]for i in line[b]));counts.append(count)
                model.add_hint(count,sum(c in hints[y][b]and c not in hints[y-1][b]for c in uses[b]))
            if range_backend=='dp':cost=constrain_dp(model,counts,[variables[active_flags[b]]for b in range(8)],window,f'line{y}')
            elif range_backend=='adjacent':cost=constrain_adjacent(model,counts,[variables[active_flags[b]]for b in range(8)],window,f'line{y}',write_budget)
            else:cost=constrain_flow(model,counts,[variables[active_flags[b]]for b in range(8)],window,f'line{y}',linear=solver_backend in('highs','highspy'),
                hint_counts=[sum(c in hints[y][b]and c not in hints[y-1][b]for c in uses[b])for b in range(8)])
            if minimize_span:model.add(peak_span_cost>=cost)
        else:constrain_ranges(line,active_flags,allocate,constraint,window,maximum_ranges=4,peak_cost_index=peak_cost_index)
    if minimize_span:
        model.minimize(peak_span_cost)
        hint_peak=max(favorable_span([dict(bank=b)for b in range(8)for c in hints[y][b]-hints[y-1][b]])for y in range(1,height))
        model.add_hint(peak_span_cost,hint_peak+40)
    elif minimize_writes:model.minimize(sum(writes.values()))
    if solver_backend in('highs','highspy'):value,statistics=solve_linear(model,time_limit,
        {v.index for v in [*resident.values(),*writes.values()]}if relax_cache else None,native_highs=solver_backend=='highspy')
    else:
        solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit;solver.parameters.num_search_workers=4
        if search_strategy=='lns':solver.parameters.use_lns_only=True
        solver.parameters.cp_model_probing_level=0;solver.parameters.use_sat_inprocessing=False
        solver.parameters.stop_after_first_solution=not(minimize_writes or minimize_span)
        status=solver.solve(model);value=solver.value if status in(cp_model.FEASIBLE,cp_model.OPTIMAL)else None
        statistics=dict(solver_backend='cp-sat',solver_status=solver.status_name(status),solver_seconds=solver.wall_time,
            solver_model_variables=len(model.proto.variables),solver_model_constraints=len(model.proto.constraints),solver_branches=solver.num_branches,solver_conflicts=solver.num_conflicts)
    report=dict(schema='BYOR_FIXED_BANK_RESIDENCY_V1',status='BOUNDED_FIXED_BANK_RESIDENCY_NO_CANDIDATE',**statistics,write_budget=write_budget,lookahead_lines=lookahead,
        prepared_window_master_clocks=window,range_backend=range_backend,static_bank_dominance_enforced=True,initial_residency_optimal=True,initial_palette_may_preload_entire_frame=True,
        physical_endpoint_slots_relaxed=True,physical_slot_schedule_proven=False,native_timing_admitted=False,
        universal_raster_rejected=False,no_color_reduction=True)
    report['fixed_outside_repair_interval']=repair_interval
    report['ranges_restricted_to_single_or_adjacent_pair']=range_backend=='adjacent' and window is not None
    report['overlapping_adjacent_bridge_cost_relaxation']=range_backend=='bridge-relaxation' and window is not None
    report['restricted_scanline_demand_interval']=source.get('restricted_scanline_demand_interval')
    report['outside_interval_pixels_relaxed']=source.get('outside_interval_pixels_relaxed',False)
    report['complete_source_frame_pixel_identity_proven']=False
    report['compulsory_bank_interval_cuts']=interval_cuts
    report['soft_residency_hint_interval']=hint_interval
    report['solver_consumes_soft_hints']=solver_backend in('cp-sat','highspy')
    report['supplied_residency_hint_used_by_solver']=hint_interval is not None and solver_backend in('cp-sat','highspy')
    report['collapse_bank_idle_prefix']=collapse_bank_idle_prefix
    report['bank_first_visible_rows']=bank_first if collapse_bank_idle_prefix else None
    report['bank_idle_prefix_resident_variables_collapsed']=collapsed_prefix_variables
    report['total_noninitial_writes_objective']=minimize_writes
    report['peak_optimistic_prepared_span_objective']=minimize_span
    report['solver_search_strategy']=search_strategy
    report['palette_residency_integrality_relaxed']=relax_cache
    report['maximum_active_banks_per_line']=maximum_active_banks
    report['per_bank_write_caps_enforced']=bank_write_caps is not None
    if bank_write_caps is not None:report['per_bank_write_caps_sha256']=hashlib.sha256(json.dumps(bank_write_caps,sort_keys=True).encode()).hexdigest()
    if minimize_span:
        bound=statistics.get('solver_objective_lower_bound',0)if solver_backend in('highs','highspy')else solver.best_objective_bound
        report['peak_optimistic_span_lower_bound_for_this_fixed_bank_family']=max(0,int(bound)-40)
    if value is None:return report
    if relax_cache:
        # Integer range activation with fractional slots is only a necessary
        # transfer-family test. Never compile fractional contents into tiles.
        report.update(status='FRACTIONAL_CACHE_INTEGER_TRANSFER_CANDIDATE',
                      integer_palette_schedule_proven=False,
                      compiled_pixel_identity_verified=False)
        return report
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
        if y and window is not None:
            actual_bound=bridge_relaxed_span(events)if range_backend=='bridge-relaxation'else favorable_span(events)
            if actual_bound>=window:raise AssertionError('BANK_RESIDENCY_INDEPENDENT_PREPARED_BOUND')
        trace.append(dict(scanline=y,resident_before=before,retained={b:[c for c in before[b]if c is not None and c in state[b]]for b in range(8)},evicted=[e['old']for e in events if e['old']is not None],prefetched=[e for e in events if e['kind']=='prefetch'],updates=events,colors_written=len(events),cgram_data_bytes=2*len(events),affected_banks=sorted({e['bank']for e in events})))
        if y and maximum_active_banks is not None and len(trace[-1]['affected_banks'])>maximum_active_banks:raise AssertionError('BANK_RESIDENCY_ACTIVE_BANK_REPLAY')
        if first<y<=last and bank_write_caps is not None and any(sum(e['bank']==b for e in events)>bank_write_caps[y][b]for b in range(8)):raise AssertionError('BANK_RESIDENCY_WRITE_CAPS_REPLAY')
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
        independent_prepared_partition_bound_verified=window is not None and range_backend!='bridge-relaxation',peak_optimistic_prepared_span=max(favorable_span(r['updates'])for r in trace[1:]))
    if range_backend=='bridge-relaxation':
        report.update(peak_bridge_relaxed_span=max(bridge_relaxed_span(r['updates'])for r in trace[1:]),
            independent_bridge_cost_bound_verified=window is not None)
    report['complete_source_frame_pixel_identity_proven']=not report['outside_interval_pixels_relaxed']
    report['total_noninitial_scheduled_writes']=sum(r['colors_written']for r in trace[1:])
    report['peak_noninitial_active_banks']=max(len(r['affected_banks'])for r in trace[1:])
    result=copy.deepcopy(source)
    result.pop('prepared_dma_packets',None)
    for key in('physical_slot_layout','physical_slot_refinement','optimistic_bank_order','compiled_transfer_descriptor_sha256'):
        if key in result:result['input_'+key]=result.pop(key)
    result.update(trace=trace,piece_pixel_masks=images,bank_residency=report,write_budget=write_budget,lookahead_lines=lookahead,
        prepared_dma_window_master_clocks=window if range_backend!='bridge-relaxation'else None,
        prepared_dma_partition_bound_enforced=window is not None and range_backend!='bridge-relaxation',prepared_dma_window_is_optimistic_necessary_only=True,
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
    p.add_argument('--range-backend',choices=('dp','ranges','adjacent','flow','bridge-relaxation'),default='dp')
    p.add_argument('--repair-interval',type=int,nargs=2,metavar=('FIRST','LAST'))
    p.add_argument('--solver-backend',choices=('cp-sat','highs','highspy'),default='cp-sat')
    p.add_argument('--scanline-interval',type=int,nargs=2,metavar=('FIRST','LAST'))
    p.add_argument('--residency-hint',type=Path)
    p.add_argument('--minimize-writes',action='store_true')
    p.add_argument('--minimize-span',action='store_true',help='Minimize the optimistic peak bank-partition cost; physical slot admission still required. HiGHS requires ranges or flow.')
    p.add_argument('--search-strategy',choices=('portfolio','lns'),default='portfolio')
    p.add_argument('--relax-cache',action='store_true',help='HiGHS necessary relaxation: keep integer transfer decisions but allow fractional cache residency; never emits a palette schedule.')
    p.add_argument('--maximum-active-banks',type=int,help='Restricted cache family limiting banks receiving writes on each noninitial scanline; physical slot admission remains separate.')
    p.add_argument('--bank-write-caps',type=Path,help='Per-line eight-bank upper bounds; compile only after integer residency and independent cap replay.')
    p.add_argument('--collapse-bank-idle-prefix',action='store_true',help='Choose each bank first visible residency in VBlank and retain it through its invisible prefix; no source demand or subsequent load is relaxed.')
    a=p.parse_args();source=json.loads(a.schedule.read_text())
    caps=json.loads(a.bank_write_caps.read_text())if a.bank_write_caps else None
    if caps is not None:caps=caps.get('bank_write_caps',caps)
    if a.scanline_interval:source=restrict_interval(source,*a.scanline_interval)
    r=relaxed_bound(source,a.lookahead,a.time_limit)if a.relaxed_bound else optimize(source,a.write_budget,a.lookahead,None if a.no_prepared_range_bound else a.window,a.time_limit,a.range_backend,a.repair_interval,a.solver_backend,json.loads(a.residency_hint.read_text())if a.residency_hint else None,a.minimize_writes,a.minimize_span,a.search_strategy,a.relax_cache,a.maximum_active_banks,caps,a.collapse_bank_idle_prefix);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r.get('bank_residency',r)))


if __name__=='__main__':main()
