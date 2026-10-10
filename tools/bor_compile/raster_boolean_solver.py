"""Optional CP-SAT backend for exact Boolean raster constraint matrices.

All variables are 0/1, including new-write indicators. Floating LP relaxations
are intentionally excluded. Consumers independently replay every incumbent.
"""
from types import SimpleNamespace
from collections import deque
import numpy as np


def solve(matrix, lower, upper, objective, time_limit=45, workers=4):
    from ortools.sat.python import cp_model
    model=cp_model.CpModel()
    variables=[model.new_bool_var('v'+str(i)) for i in range(matrix.shape[1])]
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
                           bounded_log=list(log),boolean_stats=dict(log_lines=log_lines,sat_inprocessing=False,branches=solver.num_branches,conflicts=solver.num_conflicts,wall_seconds=solver.wall_time,probing_level=0,workers=workers,optimal=status==cp_model.OPTIMAL))
