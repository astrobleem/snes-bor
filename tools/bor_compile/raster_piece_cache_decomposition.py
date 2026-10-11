"""Choose fixed piece banks with independently certified fractional cache cuts.

The master selects OAM banks; a separate cache LP supplies valid lower bounds.
A candidate is only a fixed bank assignment. Integer residency, physical slots,
transfer timing and source alpha still require their existing verification.
"""
import copy,time
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix
from raster_slot_greedy import demand,bank_groups
from raster_global_bank_classes import rebuild_schedule


def search(source,iterations=20,time_limit=120,master_seconds=3,maximum_changes=None):
    from ortools.sat.python import cp_model
    if iterations<1 or time_limit<=0 or master_seconds<=0 or (maximum_changes is not None and maximum_changes<1): raise ValueError('PIECE_CACHE_DECOMPOSITION_DOMAIN')
    _,_,images=demand(source); pieces=copy.deepcopy(source['pieces']);groups=bank_groups(source)
    domains=[]; owners={}
    for i,(p,image) in enumerate(zip(pieces,images)):
        p['rows']={p['y']+y:sorted(set(map(int,row[row>=0]))) for y,row in enumerate(image) if np.any(row>=0)}
        domains.append(tuple(b for b in next(g for g in groups if p['bank'] in g) if b in p.get('allowed_banks',range(8))))
        if not domains[-1]:raise ValueError('PIECE_CACHE_DECOMPOSITION_ELIGIBILITY')
        for y,cs in p['rows'].items():
            for c in cs:
                for b in domains[-1]:owners.setdefault((b,c,y),set()).add(i)
    first=min(y for b,c,y in owners);last=max(y for b,c,y in owners)
    uses={}
    for b,c,y in owners:uses.setdefault((b,c),set()).add(y)
    resident={(b,c,y):i for i,(b,c,y) in enumerate((b,c,y) for b,c in sorted(uses) for y in range(first,max(uses[b,c])+1))}
    writes={key:len(resident)+i for i,key in enumerate(key for key in resident if key[2]>first)}
    peak=len(resident)+len(writes); bounds=[(0,1)]*peak+[(0,None)]
    rr=[];cc=[];vv=[];rhs=[];by_bank_line={};by_write_line={};required_rows={}
    def constraint(items,upper):
        row=len(rhs)
        for col,value in items:rr.append(row);cc.append(col);vv.append(value)
        rhs.append(upper);return row
    for key,index in resident.items():
        b,c,y=key;by_bank_line.setdefault((b,y),[]).append(index)
        if key in owners:required_rows[key]=constraint([(index,-1)],0)
        if y==first:continue
        w=writes[key];constraint([(index,1),(resident[b,c,y-1],-1),(w,-1)],0);by_write_line.setdefault(y,[]).append(w)
    for indices in by_bank_line.values():constraint([(v,1)for v in indices],15)
    for indices in by_write_line.values():constraint([(v,1)for v in indices]+[(peak,-1)],0)
    matrix=coo_matrix((vv,(rr,cc)),shape=(len(rhs),peak+1)).tocsc();rhs=np.array(rhs,dtype=float)
    objective=np.zeros(peak+1);objective[peak]=1
    model=cp_model.CpModel();selection=[]
    for i,domain in enumerate(domains):
        choices={b:model.new_bool_var(f'piece{i}_{b}') for b in domain};model.add_exactly_one(list(choices.values()));selection.append(choices)
    aliases={};required={}
    for key,indices in owners.items():
        b,c,y=key;options=[selection[i][b]for i in sorted(indices)]
        signature=tuple(v.index for v in options)
        if len(options)==1:required[key]=options[0]
        else:
            if signature not in aliases:
                v=model.new_bool_var(f'alias{len(aliases)}');model.add_max_equality(v,options);aliases[signature]=v
            required[key]=aliases[signature]
    for b in range(8):
        for y in range(first,last+1):model.add(sum(v for (bb,c,yy),v in required.items() if bb==b and yy==y)<=15)
    # Certified cuts are rounded outward to integers to avoid false rejection.
    scale=1000000;t=model.new_int_var(0,120*scale,'fractionalPeak');model.minimize(t)
    assignment=[p['bank'] for p in pieces];best=120.;best_assignment=None;reports=[];started=time.monotonic()
    for iteration in range(iterations):
        if time.monotonic()-started>time_limit:break
        for key,row in required_rows.items():rhs[row]=-int(any(assignment[i]==key[0] for i in owners[key]))
        solved=linprog(objective,A_ub=matrix,b_ub=rhs,bounds=bounds,method='highs-ipm',options={'time_limit':min(30,time_limit)})
        if not solved.success:break
        dual=float(rhs@solved.ineqlin.marginals+sum(solved.upper.marginals[:-1]))
        residual=float(np.max(np.abs(objective-matrix.T@solved.ineqlin.marginals-solved.lower.marginals-solved.upper.marginals)))
        violation=float(np.max(np.maximum(matrix@solved.x-rhs,0)))
        if abs(dual-solved.fun)>1e-6 or residual>1e-6 or violation>1e-6:raise AssertionError('PIECE_CACHE_DECOMPOSITION_DUAL')
        report=dict(iteration=iteration,peak_write_lower_bound=float(solved.fun),validated_dual_lower_bound=dual,maximum_dual_residual=residual,maximum_primal_violation=violation)
        reports.append(report)
        if solved.fun<best:best=float(solved.fun);best_assignment=assignment.copy()
        weights={key:max(0.,-float(solved.ineqlin.marginals[row]))for key,row in required_rows.items()}
        constant=dual-sum(weights[key] for key in weights if rhs[required_rows[key]]==-1)
        terms=[int(np.floor(value*scale))*required[key] for key,value in weights.items() if value>1e-9]
        model.add(t>=sum(terms)+int(np.floor(constant*scale)))
        # Exclude an evaluated assignment so a rounded tie cannot stall search.
        model.add(sum(selection[i][b]for i,b in enumerate(assignment))<=len(assignment)-1)
        model.clear_hints()
        for i,b in enumerate(best_assignment):
            for bb,v in selection[i].items():model.add_hint(v,int(bb==b))
        master=model.clone()
        if maximum_changes is not None:
            master.add(sum(selection[i][b]for i,b in enumerate(best_assignment))>=len(pieces)-maximum_changes)
        solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=master_seconds;solver.parameters.num_search_workers=4
        status=solver.solve(master);report.update(master_status=solver.status_name(status),master_seconds=solver.wall_time,master_lower_bound=float(solver.best_objective_bound)/scale)
        if status not in(cp_model.FEASIBLE,cp_model.OPTIMAL):break
        assignment=[next(b for b,v in choices.items()if solver.value(v))for choices in selection]
    report=dict(schema='BYOR_FIXED_PIECE_CACHE_DECOMPOSITION_V1',iterations=reports,seconds=time.monotonic()-started,maximum_changed_pieces_per_master=maximum_changes,
        best_fractional_cache_bound=best,alias_aware=True,initial_residency_optimal=True,
        fractional_residency_only=True,physical_transfer_admitted=False,native_timing_admitted=False,universal_raster_rejected=False,no_color_reduction=True)
    if best_assignment is None:return report
    rebuilt=rebuild_schedule(source,dict(status='JOINT_GLOBAL_BANK_MASK_WORD_IDENTITIES_PROVEN',pieces=[dict(p,source_piece=i)for i,p in enumerate(pieces)],assignment=best_assignment,pixel_word_identities_replayed=True),last-first)
    rebuilt['piece_cache_decomposition']=report
    return rebuilt


def main():
    import argparse,json
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schedule',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--iterations',type=int,default=20);parser.add_argument('--time-limit',type=float,default=120)
    parser.add_argument('--master-seconds',type=float,default=3);parser.add_argument('--maximum-changes',type=int)
    args=parser.parse_args();result=search(json.loads(args.schedule.read_text()),args.iterations,args.time_limit,args.master_seconds,args.maximum_changes)
    args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result.get('piece_cache_decomposition',result)))


if __name__=='__main__':main()
