"""Necessary palette liveness bound with one shared color-math mode per line.

Individual banks, slot integrality and geometry are relaxed. Mode integrality
can be enforced separately; a feasible result never proves a palette schedule.
"""
import numpy as np
import time
from scipy.optimize import linprog,milp,Bounds,LinearConstraint
from scipy.sparse import coo_matrix


def lower_bound(rows,capacities=(60,60),time_limit=60,integer_modes=False,write_budget=None,solver_method='highs-ipm',union_rows=None,window_pixels=None,integer_windows=False,maximum_window_transitions=4):
    if len(capacities)!=2 or any(not isinstance(c,int)or c<0 for c in capacities)or not sum(capacities):raise ValueError('MODE_LIVENESS_CAPACITY')
    if write_budget is not None and(not isinstance(write_budget,int)or write_budget<0):raise ValueError('MODE_LIVENESS_WRITE_BUDGET')
    if solver_method not in ('highs-ipm','highs-ds'):raise ValueError('MODE_LIVENESS_LP_METHOD')
    if union_rows is not None and len(union_rows)!=len(rows):raise ValueError('MODE_LIVENESS_UNION_ROW_COUNT')
    if window_pixels is not None and len(window_pixels)!=len(rows):raise ValueError('MODE_LIVENESS_WINDOW_ROW_COUNT')
    if integer_windows and window_pixels is None:raise ValueError('MODE_LIVENESS_WINDOW_PIXELS_REQUIRED')
    if not isinstance(maximum_window_transitions,int)or maximum_window_transitions<0:raise ValueError('MODE_LIVENESS_WINDOW_TRANSITIONS')
    pruned=[];filtered=[]
    for y,row in enumerate(rows):
        admitted={}
        for mode,requirements in row.items():
            forced={normal for normal,choices in requirements if not choices}
            if window_pixels is None and len(forced)>capacities[0]:pruned.append(dict(scanline=y,mode=mode,forced_opaque_colors=len(forced)))
            else:admitted[mode]=requirements
        if any(row.values())and not admitted:
            return dict(status='ALL_MODES_FORCED_OPAQUE_CAPACITY_INFEASIBLE',scanline=y,forced_opaque_modes_pruned=pruned,schedule_proven=False,no_color_reduction=True)
        filtered.append(admitted)
    rows=filtered
    active=[y for y,row in enumerate(rows)if any(row.values())]
    if not active:return dict(status='EMPTY_MODE_DEMAND',schedule_proven=False)
    first=min(active);uses={}
    for y in active:
        for requirements in rows[y].values():
            for normal,choices in requirements:
                uses.setdefault((0,normal),set()).add(y)
                for color in choices:uses.setdefault((1,color),set()).add(y)
        if window_pixels is not None:
            for pixel in window_pixels[y]:uses.setdefault((1,pixel['output']),set()).add(y)
    resident={(kind,color,y):i for i,(kind,color,y)in enumerate((kind,color,y)for kind,color in sorted(uses)for y in range(first,max(uses[kind,color])+1))}
    count=len(resident)
    writes={key:count+i for i,key in enumerate(key for key in resident if key[2]>first)}
    count+=len(writes)
    modes={(y,mode):count+i for i,(y,mode)in enumerate((y,mode)for y in active for mode in sorted(rows[y]))}
    count+=len(modes);enabled={};transitions={}
    if window_pixels is not None:
        for y in active:
            coordinates=sorted({pixel['x']for pixel in window_pixels[y]})
            for x in coordinates:enabled[y,x]=count;count+=1
            for left,right in zip(coordinates,coordinates[1:]):transitions[y,left,right]=count;count+=1
    peak=count;rr=[];cc=[];vv=[];limits=[]
    def constraint(items,upper):
        index=len(limits)
        for variable,value in items:rr.append(index);cc.append(variable);vv.append(value)
        limits.append(upper)
    for y in active:
        admitted_colors={c for requirements in rows[y].values()for normal,choices in requirements for c in choices}
        if window_pixels is not None:admitted_colors.update(pixel['output']for pixel in window_pixels[y])
        if union_rows is None:
            combined={}
            for requirements in rows[y].values():
                for normal,choices in requirements:combined.setdefault(normal,set()).update(choices)
            if window_pixels is not None:
                for pixel in window_pixels[y]:combined.setdefault(pixel['output'],set()).add(pixel['output'])
            union_requirements=combined.items()
        else:union_requirements=union_rows[y]
        for normal,choices in union_requirements:
            # An exact output is required regardless of fractional mode weights.
            constraint([(resident[0,normal,y],-1)]+[(resident[1,c,y],-1)for c in choices if c in admitted_colors],-1)
        selection=[(modes[y,mode],1)for mode in sorted(rows[y])]
        constraint(selection,1);constraint([(v,-c)for v,c in selection],-1)
        if window_pixels is None:
            for mode,requirements in rows[y].items():
                for normal,choices in requirements:
                    constraint([(modes[y,mode],1),(resident[0,normal,y],-1)]+[(resident[1,c,y],-1)for c in choices],0)
        else:
            for pixel in window_pixels[y]:
                normal=pixel['output'];e=enabled[y,pixel['x']]
                constraint([(resident[0,normal,y],-1),(resident[1,normal,y],-1),(e,-1)],-1)
                for mode,choices in pixel['modes'].items():
                    constraint([(resident[0,normal,y],-1)]+[(resident[1,c,y],-1)for c in choices]+[(modes[y,mode],1),(e,1)],1)
                    # Valid for both window states, and stronger when their
                    # eligibility is fractional: selected mode needs either
                    # its math operand or the upper-bank literal bypass.
                    constraint([(resident[0,normal,y],-1)]+[(resident[1,c,y],-1)for c in set(choices)|{normal}]+[(modes[y,mode],1)],0)
            variables=[]
            for (yy,left,right),variable in transitions.items():
                if yy!=y:continue
                constraint([(enabled[y,left],1),(enabled[y,right],-1),(variable,-1)],0)
                constraint([(enabled[y,right],1),(enabled[y,left],-1),(variable,-1)],0)
                variables.append(variable)
            constraint([(v,1)for v in variables],maximum_window_transitions)
    pool_lines={};write_lines={}
    for (kind,color,y),variable in resident.items():
        pool_lines.setdefault((kind,y),[]).append(variable)
        if y>first:
            constraint([(variable,1),(resident[kind,color,y-1],-1),(writes[kind,color,y],-1)],0)
            write_lines.setdefault(y,[]).append(writes[kind,color,y])
    for (kind,y),variables in pool_lines.items():constraint([(v,1)for v in variables],capacities[kind])
    for variables in write_lines.values():constraint([(v,1)for v in variables]+[(peak,-1)],0)
    matrix=coo_matrix((vv,(rr,cc)),shape=(len(limits),peak+1)).tocsc()
    objective=np.zeros(peak+1);objective[peak]=1
    lower=np.zeros(peak+1);upper=np.ones(peak+1);upper[peak]=np.inf if write_budget is None else write_budget
    started=time.perf_counter()
    mixed_integer=integer_modes or integer_windows
    if mixed_integer:
        integrality=np.zeros(peak+1)
        if integer_modes:
            for variable in modes.values():integrality[variable]=1
        if integer_windows:
            for variable in enabled.values():integrality[variable]=1
        result=milp(objective,integrality=integrality,bounds=Bounds(lower,upper),constraints=LinearConstraint(matrix,-np.inf,limits),options={'time_limit':time_limit})
    else:
        result=linprog(objective,A_ub=matrix,b_ub=limits,bounds=list(zip(lower,upper)),method=solver_method,options={'time_limit':time_limit})
    report=dict(status='RELAXED_MODE_LIVENESS_INFEASIBLE'if result.status==2 else'BOUNDED_MODE_LIVENESS_NO_CANDIDATE',solver_status=int(result.status),message=result.message,
                variables=peak+1,constraints=len(limits),mode_variables=len(modes),integer_modes=integer_modes,write_budget=write_budget,
                palette_residency_integrality_relaxed=True,geometry_and_bank_assignment_relaxed=True,
                optimal_initial_residency_allowed=True,unbounded_preloading_allowed=True,schedule_proven=False,no_color_reduction=True)
    report['forced_opaque_modes_pruned']=pruned
    report.update(solver_seconds=time.perf_counter()-started,solver_method='highs-mip'if mixed_integer else solver_method,
                  hardware_window_masks_modeled=window_pixels is not None,integer_windows=integer_windows,
                  window_transition_superset_only=window_pixels is not None,window_register_schedule_proven=False,
                  window_eligibility_variables=len(enabled),maximum_window_transitions=maximum_window_transitions if window_pixels is not None else None)
    if result.x is not None:
        violation=max(float(np.max(np.maximum(matrix@result.x-np.array(limits),0))),float(np.max(np.maximum(lower-result.x,0))),float(np.max(np.maximum(result.x-upper,0))))
        if violation>1e-6:raise AssertionError('MODE_LIVENESS_PRIMAL_RESIDUAL')
        report.update(status='RELAXED_MODE_LIVENESS_CANDIDATE',peak_write_objective=float(result.fun),maximum_primal_violation=violation)
        if mixed_integer:
            integer_variables=([*modes.values()]if integer_modes else[])+([*enabled.values()]if integer_windows else[])
            residual=max(abs(result.x[v]-round(result.x[v]))for v in integer_variables)
            if residual>1e-6:raise AssertionError('MODE_LIVENESS_INTEGER_MODE_RESIDUAL')
            report.update(maximum_integer_control_residual=residual,mip_dual_bound=float(result.mip_dual_bound),mip_gap=float(result.mip_gap),nodes=int(result.mip_node_count))
            if integer_modes:report['selected_modes']={y:next(m for (yy,m),v in modes.items()if yy==y and result.x[v]>.5)for y in active}
            if integer_windows:report['selected_window_eligibility']={y:{x:int(round(result.x[v]))for (yy,x),v in enabled.items()if yy==y}for y in active}
        elif result.success:
            dual=float(np.dot(limits,result.ineqlin.marginals)+np.dot(np.where(np.isfinite(upper),upper,0),result.upper.marginals))
            residual=float(np.max(np.abs(objective-matrix.T@result.ineqlin.marginals-result.lower.marginals-result.upper.marginals)))
            if residual>1e-6 or abs(dual-result.fun)>1e-6:raise AssertionError('MODE_LIVENESS_DUAL_RESIDUAL')
            report.update(status='FRACTIONAL_MODE_LIVENESS_LOWER_BOUND',validated_dual_lower_bound=dual,maximum_dual_residual=residual)
    return report
