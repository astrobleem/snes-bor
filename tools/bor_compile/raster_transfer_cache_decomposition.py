"""Choose integer bank transfer budgets using certified cache-feasibility cuts.

The master grants free physical endpoint packing. The cache subproblem is
fractional, so its feasibility never compiles pixels or admits hardware.
Positive subproblem deficits supply independently checked dual cuts.
"""
import argparse,hashlib,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix
from raster_slot_greedy import demand
from raster_bank_residency import favorable_span,constrain_flow,constrain_adjacent,solve_linear


def cache_cut(matrix,objective,rhs,upper,capacity_rows,lp,plan):
    """Outward-rounded necessary cut from a validated cache LP dual."""
    deficit=len(objective)-1
    q=lp.ineqlin.marginals.copy();u=lp.upper.marginals.copy()
    if np.any(q>0)or np.any(u>0)or u[deficit]!=0:raise ValueError('TRANSFER_CACHE_CUT_DUAL_DOMAIN')
    lower=objective-matrix.T@q-u
    if lower[deficit]<-1e-8:raise ValueError('TRANSFER_CACHE_CUT_UNBOUNDED_RESIDUAL')
    factor=min(1.,1/(1-float(lower[deficit])+1e-12));q*=factor;u*=factor
    lower=objective-matrix.T@q-u
    base=rhs.copy()
    for index in capacity_rows.values():base[index]=0
    constant=float(base@q+upper@u[:-1]-np.maximum(-lower[:-1],0)@upper)
    weights={key:-float(q[index])for key,index in capacity_rows.items()if q[index]<0}
    scale=1000000
    coefficients={key:int(np.ceil(value*scale))for key,value in weights.items()}
    cut_rhs=int(np.floor(constant*scale))
    certificate=dict(capacity_weights=[[y,b,weights[y,b]]for y,b in weights],constant=constant,
        inequality_dual=[[i,float(v)]for i,v in enumerate(q)if v],
        upper_dual=[[i,float(v)]for i,v in enumerate(u)if v],
        rejected_plan={y:[plan.get((y,b),0)for b in range(8)]for y in sorted({y for y,b in plan})},
        rounded_rhs=cut_rhs)
    return coefficients,cut_rhs,certificate


def search(source,window=345,write_budget=21,lookahead=90,time_limit=120,iterations=20,master_seconds=5,range_backend='flow',master_backend='cp-sat',budget_hint=None,budget_repair_interval=None):
    from ortools.sat.python import cp_model
    if (type(window)is not int or window<1 or type(write_budget)is not int or not 0<=write_budget<=120 or
        type(lookahead)is not int or lookahead<0 or time_limit<=0 or iterations<1 or master_seconds<=0):
        raise ValueError('TRANSFER_CACHE_DECOMPOSITION_DOMAIN')
    if range_backend not in('flow','adjacent'):raise ValueError('TRANSFER_CACHE_RANGE_BACKEND')
    if master_backend not in('cp-sat','highs')or(master_backend=='highs'and range_backend!='flow'):raise ValueError('TRANSFER_CACHE_MASTER_BACKEND')
    required,uses,_=demand(source);height=len(required)
    visible=[y for y,row in enumerate(required)if any(row)]
    if not visible:raise ValueError('TRANSFER_CACHE_EMPTY_DEMAND')
    first,last=min(visible),max(visible)
    if budget_hint is not None:
        if not isinstance(budget_hint,dict):raise ValueError('TRANSFER_CACHE_BUDGET_HINT_DOMAIN')
        budget_hint={int(y):row for y,row in budget_hint.items()}
        if (set(budget_hint)!=set(range(first+1,last+1))or
            any(not isinstance(row,list)or len(row)!=8 or any(type(n)is not int or not 0<=n<=15 for n in row)or sum(row)>write_budget for row in budget_hint.values())):
            raise ValueError('TRANSFER_CACHE_BUDGET_HINT_DOMAIN')
    if budget_repair_interval is not None and(budget_hint is None or len(budget_repair_interval)!=2 or
        any(type(y)is not int for y in budget_repair_interval)or not first<budget_repair_interval[0]<=budget_repair_interval[1]<=last):
        raise ValueError('TRANSFER_CACHE_BUDGET_REPAIR_DOMAIN')
    resident={(b,c,y):i for i,(b,c,y)in enumerate((b,c,y)for b in range(8)for c,lines in sorted(uses[b].items())for y in range(first,max(lines)+1))}
    writes={key:len(resident)+i for i,key in enumerate(key for key in resident if key[2]>first)}
    deficit=len(resident)+len(writes);bounds=[(0,1)]*deficit+[(0,None)]
    rr=[];cc=[];vv=[];rhs=[];bank_rows={};write_rows={};capacity_rows={}
    def constraint(items,upper):
        index=len(rhs)
        for col,value in items:rr.append(index);cc.append(col);vv.append(value)
        rhs.append(upper);return index
    for (b,c,y),r in resident.items():
        bank_rows.setdefault((y,b),[]).append(r)
        if c in required[y][b]:constraint([(r,-1)],-1)
        if y==first:continue
        w=writes[b,c,y];constraint([(r,1),(resident[b,c,y-1],-1),(w,-1)],0)
        write_rows.setdefault((y,b),[]).append(w)
        if not any(y<=t<=y+lookahead for t in uses[b][c]):bounds[w]=(0,0)
    for indices in bank_rows.values():constraint([(i,1)for i in indices],15)
    for y in range(first+1,last+1):
        for b in range(8):capacity_rows[y,b]=constraint([(i,1)for i in write_rows.get((y,b),[])]+[(deficit,-1)],0)
    matrix=coo_matrix((vv,(rr,cc)),shape=(len(rhs),deficit+1)).tocsc();rhs=np.array(rhs,dtype=float)
    objective=np.zeros(deficit+1);objective[deficit]=1
    model=cp_model.CpModel();counts={};prefix={};flags={};hint={}
    for y in range(first+1,last+1):
        hint[y]=budget_hint[y]if budget_hint is not None else[sum(e['bank']==b for e in source['trace'][y]['updates'])for b in range(8)]
        for b in range(8):
            w=model.new_int_var(0,15,f'count{y}_{b}');counts[y,b]=w
            a=model.new_bool_var(f'active{y}_{b}');flags[y,b]=a
            model.add(w<=15*a);model.add(w>=a)
            model.add_hint(w,hint[y][b]);model.add_hint(a,int(hint[y][b]>0))
            if budget_repair_interval is not None and not budget_repair_interval[0]<=y<=budget_repair_interval[1]:model.add(w==hint[y][b])
        model.add(sum(counts[y,b]for b in range(8))<=write_budget)
        if range_backend=='flow':constrain_flow(model,[counts[y,b]for b in range(8)],[flags[y,b]for b in range(8)],window,f'line{y}',linear=master_backend=='highs',hint_counts=hint[y])
        else:constrain_adjacent(model,[counts[y,b]for b in range(8)],[flags[y,b]for b in range(8)],window,f'line{y}',write_budget)
    interval_cuts=0
    for b in range(8):
        prefix[first,b]=model.new_constant(0)
        for y in range(first+1,last+1):
            prefix[y,b]=model.new_int_var(0,15*(y-first),f'prefix{y}_{b}')
            model.add(prefix[y,b]==prefix[y-1,b]+counts[y,b])
        for left in range(first,last):
            union=set(required[left][b])
            for right in range(left+1,last+1):
                union.update(required[right][b])
                if len(union)>15:
                    model.add(prefix[right,b]-prefix[left,b]>=len(union)-15);interval_cuts+=1
    rows=[];certificates=[];started=time.monotonic();candidate=None;master_status=None
    while len(rows)<iterations and time.monotonic()-started<time_limit:
        duration=min(master_seconds,time_limit-(time.monotonic()-started))
        if master_backend=='highs':
            value,statistics=solve_linear(model,duration)
            master_status=statistics['solver_status'];elapsed=statistics['solver_seconds']
        else:
            solver=cp_model.CpSolver();solver.parameters.num_search_workers=4
            solver.parameters.max_time_in_seconds=duration
            solver.parameters.cp_model_probing_level=0
            status=solver.solve(model);master_status=solver.status_name(status)
            value=solver.value if status in(cp_model.FEASIBLE,cp_model.OPTIMAL)else None
            elapsed=solver.wall_time
        report=dict(iteration=len(rows),master_status=master_status,master_seconds=elapsed)
        rows.append(report)
        if value is None:break
        plan={key:value(v)for key,v in counts.items()}
        for key,index in capacity_rows.items():rhs[index]=plan[key]
        lp=linprog(objective,A_ub=matrix,b_ub=rhs,bounds=bounds,method='highs-ipm',options={'time_limit':30})
        if not lp.success:
            report.update(cache_lp_status=int(lp.status),cache_lp_message=lp.message);break
        upper=np.array([v[1]for v in bounds[:-1]])
        dual=float(rhs@lp.ineqlin.marginals+upper@lp.upper.marginals[:-1])
        residual=float(np.max(np.abs(objective-matrix.T@lp.ineqlin.marginals-lp.lower.marginals-lp.upper.marginals)))
        violation=max(float(np.max(np.maximum(matrix@lp.x-rhs,0))),float(np.max(np.maximum(-lp.x,0))),float(np.max(np.maximum(lp.x[:-1]-upper,0))))
        if abs(dual-lp.fun)>1e-6 or residual>1e-6 or violation>1e-6:raise AssertionError('TRANSFER_CACHE_PRIMAL_DUAL')
        report.update(cache_fractional_deficit=float(lp.fun),validated_dual_deficit=dual,maximum_dual_residual=residual,maximum_primal_violation=violation)
        if lp.fun<=1e-8:
            candidate={y:[plan[y,b]for b in range(8)]for y in range(first+1,last+1)}
            break
        coefficients,cut_rhs,certificate=cache_cut(matrix,objective,rhs,upper,capacity_rows,lp,plan)
        # Round outward: larger nonnegative coefficients and smaller RHS keep
        # every truly feasible integer budget plan. Replay the rejected plan.
        if sum(coefficients[key]*plan[key]for key in coefficients)>=cut_rhs:
            report['rounded_cut_too_weak']=True;break
        model.add(sum(value*counts[key]for key,value in coefficients.items())>=cut_rhs)
        certificates.append(certificate)
    report=dict(schema='BYOR_TRANSFER_CACHE_DECOMPOSITION_V1',status='BOUNDED_TRANSFER_CACHE_NO_CANDIDATE',
        source_rgb555_sha256=source.get('source_rgb555_sha256'),
        cache_basis_sha256=hashlib.sha256(json.dumps(dict(required=[[sorted(cs)for cs in row]for row in required],lookahead=lookahead),sort_keys=True).encode()).hexdigest(),
        input_schedule_sha256=source.get('compiled_schedule_sha256'),
        window_master_clocks=window,write_budget=write_budget,lookahead_lines=lookahead,
        seconds=time.monotonic()-started,iterations=rows,certified_cuts=certificates,
        interval_cuts=interval_cuts,cache_lp_variables=deficit+1,cache_lp_constraints=len(rhs),
        integer_bank_transfer_budgets=True,fractional_cache_only=True,
        range_backend=range_backend,master_backend=master_backend,budget_hint_supplied=budget_hint is not None,budget_repair_interval=budget_repair_interval,ranges_restricted_to_single_or_adjacent_pair=range_backend=='adjacent',
        physical_slot_schedule_proven=False,compiled_pixel_identity_verified=False,
        native_timing_admitted=False,universal_raster_rejected=False,no_color_reduction=True)
    if candidate is not None:
        costs={y:favorable_span([dict(bank=b)for b,n in enumerate(values)for _ in range(n)])for y,values in candidate.items()}
        if max(costs.values())>=window:raise AssertionError('TRANSFER_CACHE_INDEPENDENT_PARTITION')
        report.update(status='INTEGER_BANK_BUDGET_FRACTIONAL_CACHE_CANDIDATE',bank_write_caps=candidate,
            peak_optimistic_span=max(costs.values()),peak_bank_write_cap=sum(max(candidate.values(),key=sum)))
    report['fixed_bank_transfer_family_rejected']=master_status=='INFEASIBLE'and budget_repair_interval is None
    report['fixed_budget_repair_family_rejected']=master_status=='INFEASIBLE'and budget_repair_interval is not None
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--window',type=int,default=345);p.add_argument('--write-budget',type=int,default=21)
    p.add_argument('--lookahead',type=int,default=90);p.add_argument('--time-limit',type=float,default=120)
    p.add_argument('--iterations',type=int,default=20);p.add_argument('--master-seconds',type=float,default=5)
    p.add_argument('--range-backend',choices=('flow','adjacent'),default='flow')
    p.add_argument('--master-backend',choices=('cp-sat','highs'),default='cp-sat')
    p.add_argument('--budget-hint',type=Path,help='Per-line eight-bank budgets, or an object containing bank_write_caps; hints grant no cache admission.')
    p.add_argument('--budget-repair-interval',type=int,nargs=2,help='Fix hinted budgets outside these rows; all cache pixels and lifetimes remain modeled.')
    a=p.parse_args();hint=json.loads(a.budget_hint.read_text())if a.budget_hint else None
    if hint is not None:hint=hint.get('bank_write_caps',hint)
    r=search(json.loads(a.schedule.read_text()),a.window,a.write_budget,a.lookahead,a.time_limit,a.iterations,a.master_seconds,a.range_backend,a.master_backend,hint,a.budget_repair_interval)
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items()if k not in('iterations','certified_cuts','bank_write_caps')}))


if __name__=='__main__':main()
