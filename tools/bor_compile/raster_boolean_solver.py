"""Optional CP-SAT backend for exact bounded-integer raster constraints.

Variables default to 0/1; transfer word counts may have explicit integer bounds.
Floating LP relaxations
are intentionally excluded. Consumers independently replay every incumbent.
"""
from types import SimpleNamespace
from collections import deque
import numpy as np


def solve(matrix, lower, upper, objective, time_limit=45, workers=4, hint=None, variable_upper=None,search_strategy='portfolio'):
    from ortools.sat.python import cp_model
    if search_strategy not in ('portfolio','sat','sat-repair'):raise ValueError('BOOLEAN_SEARCH_STRATEGY')
    model=cp_model.CpModel()
    domains=np.ones(matrix.shape[1]) if variable_upper is None else np.asarray(variable_upper)
    if domains.shape!=(matrix.shape[1],) or any(not np.isfinite(v) or v<0 or float(v)!=int(v) for v in domains):raise ValueError('INTEGER_VARIABLE_UPPER_DOMAIN')
    variables=[model.new_bool_var('v'+str(i)) if limit==1 else model.new_int_var(0,int(limit),'v'+str(i)) for i,limit in enumerate(domains)]
    if hint:
        for index,value in hint.items():
            if not 0<=index<len(variables)or not isinstance(value,(int,np.integer))or not 0<=value<=domains[index]:raise ValueError('BOOLEAN_HINT_DOMAIN')
            model.add_hint(variables[index],value)
    rows=matrix.tocsr()
    for row in range(matrix.shape[0]):
        start,end=rows.indptr[row:row+2]
        indices=rows.indices[start:end];coefficients=rows.data[start:end]
        if any(float(v)!=int(v) for v in coefficients):raise ValueError('BOOLEAN_MATRIX_NONINTEGER_COEFFICIENT')
        expression=cp_model.LinearExpr.weighted_sum([variables[int(i)] for i in indices],[int(v) for v in coefficients])
        lo,hi=lower[row],upper[row]
        for bound in (lo,hi):
            if np.isfinite(bound) and float(bound)!=int(bound):raise ValueError('BOOLEAN_MATRIX_NONINTEGER_BOUND')
        if lo==hi:model.add(expression==int(lo))
        else:
            if np.isfinite(lo):model.add(expression>=int(lo))
            if np.isfinite(hi):model.add(expression<=int(hi))
    weights=np.rint(np.asarray(objective)*1000).astype(int)
    if np.any(np.abs(weights/1000-objective)>1e-9):raise ValueError('BOOLEAN_OBJECTIVE_PRECISION')
    if np.any(weights):model.minimize(cp_model.LinearExpr.weighted_sum(variables,weights.tolist()))
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit
    solver.parameters.num_search_workers=workers
    # The full raster graph has many equivalent implications; exhaustive
    # pre-search probing consumed the initial bounded trial without conflicts.
    solver.parameters.cp_model_probing_level=0
    solver.parameters.use_sat_inprocessing=False
    if search_strategy in ('sat','sat-repair'):
        solver.parameters.subsolvers.append('no_lp');solver.parameters.num_full_subsolvers=1
        solver.parameters.linearization_level=0
    if search_strategy=='sat-repair':
        solver.parameters.repair_hint=True;solver.parameters.hint_conflict_limit=50000
    solver.parameters.log_search_progress=True;solver.parameters.log_to_stdout=False
    log=deque(maxlen=64);log_lines=0
    def capture(message):
        nonlocal log_lines
        for line in message.splitlines():
            log_lines+=1;log.append(line[:512])
    solver.log_callback=capture
    status=solver.solve(model)
    feasible=status in (cp_model.OPTIMAL,cp_model.FEASIBLE)
    values=np.array([solver.value(v) for v in variables],dtype=float) if feasible else None
    return SimpleNamespace(x=values,status=0 if feasible else 2 if status==cp_model.INFEASIBLE else 1,
                           message=solver.status_name(status),mip_node_count=None,mip_gap=None,
                           bounded_log=list(log),boolean_stats=dict(nonboolean_integer_variables=int(np.count_nonzero(domains>1)),hint_variables=len(hint or {}),hint_is_soft=True,log_lines=log_lines,sat_inprocessing=False,branches=solver.num_branches,conflicts=solver.num_conflicts,wall_seconds=solver.wall_time,probing_level=0,workers=workers,search_strategy=search_strategy,optimal=status==cp_model.OPTIMAL))
