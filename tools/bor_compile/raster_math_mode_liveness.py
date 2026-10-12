"""Necessary palette liveness bound with one shared color-math mode per line.

Individual banks, slot integrality and geometry are relaxed. Mode integrality
can be enforced separately; a feasible result never proves a palette schedule.
"""
import numpy as np
import time
import itertools
from scipy.optimize import linprog,milp,Bounds,LinearConstraint
from scipy.sparse import coo_matrix
from types import SimpleNamespace


def verify_integer_pool(report,rows,capacities=(60,60),window_pixels=None,maximum_window_transitions=4):
    """Independent residency, control and source-coverage replay; no bank proof."""
    active=[y for y,row in enumerate(rows)if any(row.values())]
    states={int(y):{int(k):set(colors)for k,colors in state.items()}for y,state in report['selected_palette_residency'].items()}
    modes={int(y):m for y,m in report['selected_modes'].items()}
    masks={int(y):{int(x):v for x,v in mask.items()}for y,mask in report.get('selected_window_eligibility',{}).items()}
    first,last=min(active),max(active);peak=0
    if set(states)!=set(range(first,last+1)):raise ValueError('MODE_INTEGER_POOL_STATE_DOMAIN')
    if report.get('fixed_initial_palette_state')is not None and states[first]!={int(k):set(cs)for k,cs in report['fixed_initial_palette_state'].items()}:raise AssertionError('MODE_INTEGER_POOL_INITIAL_STATE_REPLAY')
    for y,state in states.items():
        if set(state)!={0,1}or any(not isinstance(c,(int,np.integer))or not 0<=c<32768 for colors in state.values()for c in colors):raise ValueError('MODE_INTEGER_POOL_COLOR_DOMAIN')
        if any(len(state[k])>capacities[k]for k in range(2)):raise AssertionError('MODE_INTEGER_POOL_CAPACITY_REPLAY')
        if not set(report.get('reserved_normal_colors',())).issubset(state[0]):raise AssertionError('MODE_INTEGER_POOL_STATIC_RESERVATION_REPLAY')
        if not {int(yy):set(cs)for yy,cs in report.get('required_normal_rows',{}).items()}.get(y,set()).issubset(state[0]):raise AssertionError('MODE_INTEGER_POOL_NORMAL_ROW_REPLAY')
        if y>first:
            class_writes=[len(state[k]-states[y-1][k])for k in range(2)]
            line_writes=sum(class_writes);peak=max(peak,line_writes)
            transfer_window=report.get('necessary_minimum_transfer_window')
            if transfer_window is not None:
                banks=sum((n+14)//15 for n in class_writes)
                if max(0,16*(line_writes+banks-2))>=transfer_window:raise AssertionError('MODE_INTEGER_POOL_MINIMUM_TRANSFER_REPLAY')
            limit={int(yy):n for yy,n in report.get('scanline_write_limits',{}).items()}.get(y)
            if limit is not None and line_writes>limit:raise AssertionError('MODE_INTEGER_POOL_SCANLINE_WRITE_LIMIT_REPLAY')
        if y not in active:continue
        mode=modes[y]
        if mode not in rows[y]:raise ValueError('MODE_INTEGER_POOL_MODE_DOMAIN')
        if window_pixels is None:
            requirements=rows[y][mode]
        else:
            mask=masks[y];xs=sorted(mask)
            if any(v not in(0,1)for v in mask.values()):raise ValueError('MODE_INTEGER_POOL_WINDOW_DOMAIN')
            if sum(mask[a]!=mask[b]for a,b in zip(xs,xs[1:]))>maximum_window_transitions:raise AssertionError('MODE_INTEGER_POOL_WINDOW_REPLAY')
            requirements=[(p['output'],p['modes'][mode]if mask[p['x']]else(p['output'],))for p in window_pixels[y]]
        for out,choices in requirements:
            if out not in state[0]and not set(choices)&state[1]:raise AssertionError('MODE_INTEGER_POOL_PIXEL_REPLAY')
    if peak>report['peak_write_objective']:raise AssertionError('MODE_INTEGER_POOL_WRITE_REPLAY')
    report.update(integer_pool_pixel_coverage_verified=True,integer_pool_residency_capacity_verified=True,peak_replayed_pool_writes=peak)
    return report


def lower_bound(rows,capacities=(60,60),time_limit=60,integer_modes=False,write_budget=None,solver_method='highs-ipm',union_rows=None,window_pixels=None,integer_windows=False,maximum_window_transitions=4,pin_lp_controls=False,positive_windows_only=False,subset_mode_cuts=False,integer_palette=False,integer_backend='highs',lp_hint=False,residency_hint=None,reserved_normal_colors=(),scanline_write_limits=None,required_normal_rows=None,initial_state=None,controls_hint=None,minimum_transfer_window=None):
    reserved_normal_colors=tuple(sorted(set(reserved_normal_colors)))
    if any(type(c)is not int or not 0<=c<32768 for c in reserved_normal_colors):raise ValueError('MODE_LIVENESS_STATIC_RESERVATION_DOMAIN')
    scanline_write_limits=dict(scanline_write_limits or {})
    if any(type(y)is not int or not 0<=y<len(rows) or type(n)is not int or not 0<=n<=120 for y,n in scanline_write_limits.items()):raise ValueError('MODE_LIVENESS_SCANLINE_WRITE_LIMIT_DOMAIN')
    required_normal_rows={y:set(cs)for y,cs in (required_normal_rows or {}).items()}
    if any(type(y)is not int or not 0<=y<len(rows)or any(type(c)is not int or not 0<=c<32768 for c in cs)for y,cs in required_normal_rows.items()):raise ValueError('MODE_LIVENESS_REQUIRED_NORMAL_ROW_DOMAIN')
    if required_normal_rows:
        names={m for row in rows for m in row}
        if not names:raise ValueError('MODE_LIVENESS_NORMAL_ROW_REQUIRES_MODE_DOMAIN')
        rows=[{m:set(reqs)for m,reqs in row.items()}for row in rows]
        for y,cs in required_normal_rows.items():
            for m in rows[y]or names:rows[y].setdefault(m,set()).update((c,())for c in cs)
    if len(capacities)!=2 or any(not isinstance(c,int)or c<0 for c in capacities)or not sum(capacities):raise ValueError('MODE_LIVENESS_CAPACITY')
    if minimum_transfer_window is not None and(type(minimum_transfer_window)is not int or minimum_transfer_window<1 or any(c>60 for c in capacities)):raise ValueError('MODE_LIVENESS_TRANSFER_WINDOW_REQUIRES_DISJOINT_FOUR_BANK_CLASSES')
    if initial_state is not None:
        initial_state={int(k):set(cs)for k,cs in initial_state.items()}
        if set(initial_state)!={0,1}or any(len(cs)>capacities[k]or any(type(c)is not int or not 0<=c<32768 for c in cs)for k,cs in initial_state.items()):raise ValueError('MODE_LIVENESS_INITIAL_STATE_DOMAIN')
    if write_budget is not None and(not isinstance(write_budget,int)or write_budget<0):raise ValueError('MODE_LIVENESS_WRITE_BUDGET')
    if solver_method not in ('highs-ipm','highs-ds'):raise ValueError('MODE_LIVENESS_LP_METHOD')
    if union_rows is not None and len(union_rows)!=len(rows):raise ValueError('MODE_LIVENESS_UNION_ROW_COUNT')
    if window_pixels is not None and len(window_pixels)!=len(rows):raise ValueError('MODE_LIVENESS_WINDOW_ROW_COUNT')
    if integer_windows and window_pixels is None:raise ValueError('MODE_LIVENESS_WINDOW_PIXELS_REQUIRED')
    if pin_lp_controls and not(integer_modes or integer_windows):raise ValueError('MODE_LIVENESS_INTEGER_CONTROLS_REQUIRED')
    if positive_windows_only and window_pixels is None:raise ValueError('MODE_LIVENESS_WINDOW_PIXELS_REQUIRED')
    if subset_mode_cuts and window_pixels is None:raise ValueError('MODE_LIVENESS_WINDOW_PIXELS_REQUIRED')
    if not isinstance(maximum_window_transitions,int)or maximum_window_transitions<0:raise ValueError('MODE_LIVENESS_WINDOW_TRANSITIONS')
    if integer_backend not in('highs','cp-sat')or(integer_backend=='cp-sat'and not integer_palette):raise ValueError('MODE_LIVENESS_INTEGER_BACKEND')
    if integer_palette and(not integer_modes or window_pixels is not None and not integer_windows):raise ValueError('MODE_LIVENESS_INTEGER_PALETTE_CONTROLS')
    if lp_hint and integer_backend!='cp-sat':raise ValueError('MODE_LIVENESS_LP_HINT_REQUIRES_CP_SAT')
    if residency_hint is not None and(not integer_palette or integer_backend!='cp-sat' or lp_hint):raise ValueError('MODE_LIVENESS_RESIDENCY_HINT_REQUIRES_CP_SAT_WITHOUT_LP_HINT')
    if residency_hint is not None:verify_integer_pool(residency_hint,rows,capacities,window_pixels,maximum_window_transitions)
    if controls_hint is not None and(not integer_palette or integer_backend!='cp-sat' or residency_hint is not None or lp_hint):raise ValueError('MODE_LIVENESS_CONTROLS_HINT_POLICY')
    hinted_modes={int(y):m for y,m in controls_hint.get('selected_modes',{}).items()}if controls_hint is not None else{}
    hinted_masks={int(y):{int(x):v for x,v in mask.items()}for y,mask in controls_hint.get('selected_window_eligibility',{}).items()}if controls_hint is not None else{}
    if any(not 0<=y<len(rows)or m not in rows[y]for y,m in hinted_modes.items())or any(not 0<=y<len(rows)or any(not 0<=x<256 or type(v)is not int or v not in(0,1)for x,v in mask.items())for y,mask in hinted_masks.items()):raise ValueError('MODE_LIVENESS_CONTROLS_HINT_DOMAIN')
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
    first=min(active);uses={(0,c):set(range(first,max(active)+1))for c in reserved_normal_colors}
    if initial_state is not None:
        for kind,colors in initial_state.items():
            for c in colors:uses.setdefault((kind,c),set()).add(first)
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
            if positive_windows_only:coordinates=sorted(set(coordinates)|{0,255})
            for x in coordinates:enabled[y,x]=count;count+=1
            for left,right in zip(coordinates,coordinates[1:]):transitions[y,left,right]=count;count+=1
    minimum_banks={}
    if minimum_transfer_window is not None:
        for y in range(first+1,max(active)+1):
            for kind in (0,1):minimum_banks[y,kind]=count;count+=1
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
            if positive_windows_only:
                constraint([(enabled[y,0],1)],0);constraint([(enabled[y,255],1)],0)
            for pixel in window_pixels[y]:
                normal=pixel['output'];e=enabled[y,pixel['x']]
                constraint([(resident[0,normal,y],-1),(resident[1,normal,y],-1),(e,-1)],-1)
                for mode,choices in pixel['modes'].items():
                    constraint([(resident[0,normal,y],-1)]+[(resident[1,c,y],-1)for c in choices]+[(modes[y,mode],1),(e,1)],1)
                    # Valid for both window states, and stronger when their
                    # eligibility is fractional: selected mode needs either
                    # its math operand or the upper-bank literal bypass.
                    constraint([(resident[0,normal,y],-1)]+[(resident[1,c,y],-1)for c in set(choices)|{normal}]+[(modes[y,mode],1)],0)
                if subset_mode_cuts:
                    names=sorted(pixel['modes'])
                    for size in range(2,len(names)+1):
                        for subset in itertools.combinations(names,size):
                            colors={c for mode in subset for c in pixel['modes'][mode]}
                            selected=[(modes[y,mode],1)for mode in subset]
                            constraint([(resident[0,normal,y],-1)]+[(resident[1,c,y],-1)for c in colors]+selected+[(e,1)],1)
                            if size<len(names):
                                constraint([(resident[0,normal,y],-1)]+[(resident[1,c,y],-1)for c in colors|{normal}]+selected,0)
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
    for y,variables in write_lines.items():
        constraint([(v,1)for v in variables]+[(peak,-1)],0)
        if y in scanline_write_limits:constraint([(v,1)for v in variables],scanline_write_limits[y])
        if minimum_transfer_window is not None:
            for kind in (0,1):
                constraint([(v,1)for(k,c,yy),v in writes.items()if k==kind and yy==y]+[(minimum_banks[y,kind],-15)],0)
            # Grant adjacent banks, ideal endpoint slots and one setup. The
            # actual partition cannot beat 16*(loads + minimum banks - 2).
            constraint([(v,16)for v in variables]+[(minimum_banks[y,k],16)for k in (0,1)],minimum_transfer_window+31)
    matrix=coo_matrix((vv,(rr,cc)),shape=(len(limits),peak+1)).tocsc()
    objective=np.zeros(peak+1);objective[peak]=1
    lower=np.zeros(peak+1);upper=np.ones(peak+1);upper[peak]=np.inf if write_budget is None else write_budget
    for variable in minimum_banks.values():upper[variable]=4
    for c in reserved_normal_colors:
        for y in range(first,max(active)+1):lower[resident[0,c,y]]=1
    for y,cs in required_normal_rows.items():
        for c in cs:lower[resident[0,c,y]]=1
    if initial_state is not None:
        for (kind,c,y),v in resident.items():
            if y==first:lower[v]=upper[v]=int(c in initial_state[kind])
        if not set(reserved_normal_colors).issubset(initial_state[0])or not required_normal_rows.get(first,set()).issubset(initial_state[0]):
            return dict(status='FIXED_INITIAL_PALETTE_REQUIRED_NORMAL_MISSING',schedule_proven=False,universal_raster_rejected=False,no_color_reduction=True)
    started=time.perf_counter()
    mixed_integer=integer_modes or integer_windows
    pinned_control_report=None
    if pin_lp_controls:
        relaxation=linprog(objective,A_ub=matrix,b_ub=limits,bounds=list(zip(lower,upper)),method=solver_method,options={'time_limit':time_limit})
        pinned_control_report=dict(status=int(relaxation.status),message=relaxation.message,pinned_variables=0,restricted_family_only=True)
        if relaxation.success:
            violation=max(float(np.max(np.maximum(matrix@relaxation.x-np.array(limits),0))),float(np.max(np.maximum(lower-relaxation.x,0))),float(np.max(np.maximum(relaxation.x-upper,0))))
            if violation>1e-6:raise AssertionError('MODE_LIVENESS_CONTROL_HINT_PRIMAL_RESIDUAL')
            controls=([*modes.values()]if integer_modes else[])+([*enabled.values()]if integer_windows else[])
            for variable in controls:
                value=relaxation.x[variable]
                if value<1e-7:upper[variable]=0;pinned_control_report['pinned_variables']+=1
                elif value>1-1e-7:lower[variable]=1;pinned_control_report['pinned_variables']+=1
            pinned_control_report.update(relaxed_objective=float(relaxation.fun),maximum_primal_violation=violation)
    boolean_statistics=None;lp_hint_report=None
    if integer_palette and integer_backend=='cp-sat':
        from raster_boolean_solver import solve
        from scipy.sparse import vstack
        fixed=np.flatnonzero(lower>0)
        extra=coo_matrix((np.ones(len(fixed)),(np.arange(len(fixed)),fixed)),shape=(len(fixed),peak+1)).tocsc()
        all_rows=vstack((matrix,extra)).tocsc()
        all_lower=np.concatenate((np.full(len(limits),-np.inf),lower[fixed]))
        all_upper=np.concatenate((np.asarray(limits),lower[fixed]))
        domains=upper.copy();domains[peak]=sum(capacities)if write_budget is None else write_budget
        hint=None
        if lp_hint:
            relaxed=linprog(objective,A_ub=matrix,b_ub=limits,bounds=list(zip(lower,domains)),method=solver_method,options={'time_limit':min(15,time_limit)})
            lp_hint_report=dict(status=int(relaxed.status),message=relaxed.message,hint_is_soft=True,pinned_variables=0)
            if relaxed.success:
                violation=max(float(np.max(np.maximum(matrix@relaxed.x-np.asarray(limits),0))),float(np.max(np.maximum(lower-relaxed.x,0))),float(np.max(np.maximum(relaxed.x-domains,0))))
                if violation>1e-6:raise AssertionError('MODE_LIVENESS_LP_HINT_PRIMAL_RESIDUAL')
                hint={i:int(round(v))for i,v in enumerate(relaxed.x)if i==peak or v<1e-7 or v>1-1e-7}
                lp_hint_report.update(relaxed_objective=float(relaxed.fun),hint_variables=len(hint),maximum_primal_violation=violation)
        if residency_hint is not None:
            states={int(y):{int(k):set(colors)for k,colors in state.items()}for y,state in residency_hint['selected_palette_residency'].items()}
            chosen_modes={int(y):m for y,m in residency_hint['selected_modes'].items()}
            masks={int(y):{int(x):v for x,v in mask.items()}for y,mask in residency_hint.get('selected_window_eligibility',{}).items()}
            hint={v:int(c in states[y][k])for (k,c,y),v in resident.items()}
            hint.update({v:int(c in states[y][k]and c not in states[y-1][k])for (k,c,y),v in writes.items()})
            hint.update({v:int(chosen_modes[y]==mode)for (y,mode),v in modes.items()})
            hint.update({v:int(masks[y].get(x,0))for (y,x),v in enabled.items()})
            hint.update({v:int(masks[y].get(left,0)!=masks[y].get(right,0))for (y,left,right),v in transitions.items()})
        if controls_hint is not None:
            hint={v:int(hinted_modes[y]==mode)for (y,mode),v in modes.items()if y in hinted_modes}
            hint.update({v:hinted_masks[y][x]for(y,x),v in enabled.items()if y in hinted_masks and x in hinted_masks[y]})
            hint.update({v:int(hinted_masks[y][left]!=hinted_masks[y][right])for(y,left,right),v in transitions.items()if y in hinted_masks and left in hinted_masks[y]and right in hinted_masks[y]})
        solved=solve(all_rows,all_lower,all_upper,objective,time_limit,variable_upper=domains,hint=hint)
        boolean_statistics=solved.boolean_stats
        result=SimpleNamespace(status=solved.status,message=solved.message,x=solved.x,
                               fun=float(objective@solved.x)if solved.x is not None else None)
    elif mixed_integer:
        integrality=np.zeros(peak+1)
        if integer_palette:integrality[:]=1
        if integer_modes:
            for variable in modes.values():integrality[variable]=1
        if integer_windows:
            for variable in enabled.values():integrality[variable]=1
        result=milp(objective,integrality=integrality,bounds=Bounds(lower,upper),constraints=LinearConstraint(matrix,-np.inf,limits),options={'time_limit':time_limit})
    else:
        result=linprog(objective,A_ub=matrix,b_ub=limits,bounds=list(zip(lower,upper)),method=solver_method,options={'time_limit':time_limit})
    report=dict(status='RELAXED_MODE_LIVENESS_INFEASIBLE'if result.status==2 else'BOUNDED_MODE_LIVENESS_NO_CANDIDATE',solver_status=int(result.status),message=result.message,
                variables=peak+1,constraints=len(limits),mode_variables=len(modes),integer_modes=integer_modes,write_budget=write_budget,
        palette_residency_integrality_relaxed=not integer_palette,geometry_and_bank_assignment_relaxed=True,
                optimal_initial_residency_allowed=initial_state is None,fixed_initial_palette_state=None if initial_state is None else{k:sorted(cs)for k,cs in initial_state.items()},unbounded_preloading_allowed=True,schedule_proven=False,no_color_reduction=True)
    report['forced_opaque_modes_pruned']=pruned
    report['necessary_minimum_transfer_window']=minimum_transfer_window
    report['minimum_transfer_bound_is_complete_partition_proof']=False
    report['minimum_transfer_bank_classes_disjoint']=minimum_transfer_window is not None
    report['reserved_normal_colors']=list(reserved_normal_colors)
    report['static_normal_residency_fixed_for_complete_interval']=bool(reserved_normal_colors)
    report['scanline_write_limits']=scanline_write_limits
    report['required_normal_rows']={y:sorted(cs)for y,cs in required_normal_rows.items()}
    if pinned_control_report is not None:
        report['pinned_lp_control_family']=pinned_control_report
        if result.status==2:report['status']='PINNED_MODE_CONTROL_FAMILY_INFEASIBLE'
    report.update(solver_seconds=time.perf_counter()-started,solver_method='cp-sat'if boolean_statistics is not None else'highs-mip'if mixed_integer else solver_method,
                  integer_palette=integer_palette,
                  hardware_window_masks_modeled=window_pixels is not None,integer_windows=integer_windows,
                  window_transition_superset_only=window_pixels is not None,window_register_schedule_proven=False,
                  positive_union_with_disabled_edges_only=positive_windows_only,
                  subset_mode_cover_cuts=subset_mode_cuts,
                  window_eligibility_variables=len(enabled),maximum_window_transitions=maximum_window_transitions if window_pixels is not None else None)
    if boolean_statistics is not None:report['boolean_stats']=boolean_statistics
    if controls_hint is not None:report['source_controls_hint']=dict(hint_is_soft=True,pinned_variables=0,palette_residency_hinted=False,hint_variables=boolean_statistics['hint_variables'])
    if lp_hint_report is not None:report['lp_residency_hint']=lp_hint_report
    if residency_hint is not None:report['source_residency_hint']=dict(hint_is_soft=True,pinned_variables=0,input_peak_replayed_writes=residency_hint['peak_replayed_pool_writes'])
    if result.x is not None:
        violation=max(float(np.max(np.maximum(matrix@result.x-np.array(limits),0))),float(np.max(np.maximum(lower-result.x,0))),float(np.max(np.maximum(result.x-upper,0))))
        if violation>1e-6:raise AssertionError('MODE_LIVENESS_PRIMAL_RESIDUAL')
        report.update(status='RELAXED_MODE_LIVENESS_CANDIDATE',peak_write_objective=float(result.fun),maximum_primal_violation=violation)
        if mixed_integer:
            integer_variables=list(range(peak+1))if integer_palette else([*modes.values()]if integer_modes else[])+([*enabled.values()]if integer_windows else[])
            residual=max(abs(result.x[v]-round(result.x[v]))for v in integer_variables)
            if residual>1e-6:raise AssertionError('MODE_LIVENESS_INTEGER_MODE_RESIDUAL')
            report.update(maximum_integer_control_residual=residual)
            if boolean_statistics is not None:report['boolean_stats']=boolean_statistics
            else:report.update(mip_dual_bound=float(result.mip_dual_bound),mip_gap=float(result.mip_gap),nodes=int(result.mip_node_count))
            if integer_modes:report['selected_modes']={y:next(m for (yy,m),v in modes.items()if yy==y and result.x[v]>.5)for y in active}
            if integer_windows:report['selected_window_eligibility']={y:{x:int(round(result.x[v]))for (yy,x),v in enabled.items()if yy==y}for y in active}
            if integer_palette:
                states={y:{kind:{c for (k,c,yy),v in resident.items()if k==kind and yy==y and result.x[v]>.5}for kind in range(2)}for y in range(first,max(active)+1)}
                report['selected_palette_residency']={y:{kind:sorted(colors)for kind,colors in state.items()}for y,state in states.items()}
                verify_integer_pool(report,rows,capacities,window_pixels,maximum_window_transitions)
        elif result.success:
            dual=float(np.dot(limits,result.ineqlin.marginals)+np.dot(lower,result.lower.marginals)+np.dot(np.where(np.isfinite(upper),upper,0),result.upper.marginals))
            residual=float(np.max(np.abs(objective-matrix.T@result.ineqlin.marginals-result.lower.marginals-result.upper.marginals)))
            if residual>1e-6 or abs(dual-result.fun)>1e-6:raise AssertionError('MODE_LIVENESS_DUAL_RESIDUAL')
            report.update(status='FRACTIONAL_MODE_LIVENESS_LOWER_BOUND',validated_dual_lower_bound=dual,maximum_dual_residual=residual)
    return report
