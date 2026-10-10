"""Necessary fractional liveness bound for two exact pixel encodings.

Geometry/banks within each eligibility pool are relaxed. A feasible LP is never
a palette schedule. Initial residency is optimal at the first visible line.
"""
import numpy as np
from scipy.optimize import linprog, milp, Bounds, LinearConstraint
from scipy.sparse import coo_matrix


def lower_bound(rows, capacities=(60,60), time_limit=45, include_solution=False, integer_budget=None,solver_method='highs-ipm'):
    if len(capacities)!=2 or any(not isinstance(c,int)or c<0 for c in capacities)or not sum(capacities):raise ValueError('COVER_POOL_CAPACITY')
    if integer_budget is not None and (not isinstance(integer_budget,int)or integer_budget<0):raise ValueError('COVER_INTEGER_WRITE_BUDGET')
    if solver_method not in ('highs-ipm','highs-ds'):raise ValueError('COVER_LP_SOLVER_METHOD')
    # Each pixel may admit several exact saturated additive operands.
    rows=[{(normal,() if additive is None else tuple(sorted(set(additive))) if isinstance(additive,(tuple,list)) else (additive,)) for normal,additive in row} for row in rows]
    active=[y for y,row in enumerate(rows) if row]
    if not active:return dict(status='EMPTY_COVER_DEMAND',peak_write_lower_bound=0,schedule_proven=False)
    first,last=min(active),max(active);uses={}
    for y,row in enumerate(rows):
        for normal,additive in row:
            uses.setdefault((0,normal),set()).add(y)
            for color in additive:uses.setdefault((1,color),set()).add(y)
    resident={(kind,color,y):i for i,(kind,color,y) in enumerate((kind,color,y) for kind,color in sorted(uses) for y in range(first,max(uses[kind,color])+1))}
    count=len(resident);writes={key:count+i for i,key in enumerate(key for key in resident if key[2]>first)};peak=count+len(writes)
    rr=[];cc=[];vv=[];limits=[]
    def constraint(items,upper):
        row=len(limits)
        for variable,value in items:rr.append(row);cc.append(variable);vv.append(value)
        limits.append(upper)
    for y,row in enumerate(rows):
        for normal,additive in sorted(row):
            items=[(resident[0,normal,y],-1)]
            items.extend((resident[1,color,y],-1) for color in additive)
            constraint(items,-1)
    pool_lines={};write_lines={}
    for (kind,color,y),variable in resident.items():
        pool_lines.setdefault((kind,y),[]).append(variable)
        if y>first:
            constraint([(variable,1),(resident[kind,color,y-1],-1),(writes[kind,color,y],-1)],0)
            write_lines.setdefault(y,[]).append(writes[kind,color,y])
    for (kind,y),variables in pool_lines.items():constraint([(v,1)for v in variables],capacities[kind])
    for variables in write_lines.values():constraint([(v,1)for v in variables]+[(peak,-1)],0)
    matrix=coo_matrix((vv,(rr,cc)),shape=(len(limits),peak+1)).tocsc();objective=np.zeros(peak+1);objective[peak]=1
    result=linprog(objective,A_ub=matrix,b_ub=limits,bounds=[(0,1)]*peak+[(0,None)],method=solver_method,options={'time_limit':time_limit})
    report=dict(status='RELAXED_COVER_INFEASIBLE'if result.status==2 else'RELAXED_COVER_SOLVER_LIMIT',solver_status=int(result.status),message=result.message,variables=peak+1,constraints=len(limits),schedule_proven=False,geometry_and_bank_assignment_relaxed=True,unbounded_preloading_allowed=True,initial_residency_optimal=True)
    report['solver_method']=solver_method
    if result.success:
        violation=max(float(np.max(np.maximum(matrix@result.x-np.array(limits),0))),float(np.max(np.maximum(-result.x,0))),float(np.max(np.maximum(result.x[:peak]-1,0))))
        if violation>1e-6:raise AssertionError('COVER_LIVENESS_LP_PRIMAL_RESIDUAL')
        dual=float(np.dot(limits,result.ineqlin.marginals)+np.sum(result.upper.marginals[:peak]))
        dual_residual=float(np.max(np.abs(objective-matrix.T@result.ineqlin.marginals-result.lower.marginals-result.upper.marginals)))
        if dual_residual>1e-6 or abs(dual-result.fun)>1e-6:raise AssertionError('COVER_LIVENESS_LP_DUAL_RESIDUAL')
        report.update(status='FRACTIONAL_COVER_LIVENESS_LOWER_BOUND',peak_write_lower_bound=float(result.fun),validated_dual_lower_bound=dual,maximum_primal_violation=violation,maximum_dual_residual=dual_residual)
        if integer_budget is not None:
            lower=np.zeros(peak+1);upper=np.ones(peak+1);upper[peak]=integer_budget;integrality=np.zeros(peak+1)
            for variable in resident.values():
                integrality[variable]=1
                if result.x[variable]<1e-7:upper[variable]=0
                elif result.x[variable]>1-1e-7:lower[variable]=1
            integer=milp(objective,integrality=integrality,bounds=Bounds(lower,upper),constraints=LinearConstraint(matrix,-np.inf,limits),options={'time_limit':time_limit})
            report['pinned_integer_solver']=dict(status=int(integer.status),message=integer.message,write_budget=integer_budget,lp_integral_residencies_pinned=True,universal_infeasibility_proven=False)
            if integer.x is None:
                report['status']='PINNED_POOL_INTEGER_SOLVER_NO_CANDIDATE'
                return report
            result=integer
            if np.max(np.maximum(matrix@result.x-np.array(limits),0))>1e-6 or any(abs(result.x[v]-round(result.x[v]))>1e-6 for v in resident.values()):raise AssertionError('PINNED_POOL_INTEGER_RESIDENCY_FAULT')
            exact_writes={y:0 for y in write_lines}
            for (kind,color,y),v in resident.items():
                if y>first and result.x[v]>.5 and result.x[resident[kind,color,y-1]]<=.5:exact_writes[y]+=1
            exact_peak=max(exact_writes.values(),default=0)
            if exact_peak>integer_budget:raise AssertionError('PINNED_POOL_EXACT_WRITE_BUDGET_FAULT')
            report.update(status='POOLED_INTEGER_RESIDENCY_CANDIDATE',candidate_peak_writes=exact_peak,integer_solver_objective=float(result.fun),exact_new_colors_by_scanline=exact_writes,schedule_proven=False)
        if include_solution:report['fractional_residency']=[dict(kind=kind,color=color,line=y,value=float(result.x[variable]))for (kind,color,y),variable in resident.items()if result.x[variable]>1e-7]
    return report
