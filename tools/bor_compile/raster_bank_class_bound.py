"""Validated cache lower bound with banks pooled inside encoding classes.

All input pixel words and their encoding classes remain fixed. OAM geometry,
bank assignment within each class and physical slots are relaxed. This bound
can reject that fixed encoding, never all possible source raster encodings.
"""
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix
from raster_slot_greedy import demand,bank_groups


def lower_bound(source,lookahead=55,time_limit=15):
    if lookahead<0 or time_limit<=0:raise ValueError('BANK_CLASS_BOUND_DOMAIN')
    required,_,_=demand(source);groups=bank_groups(source)
    rows=[[set.union(*(row[b]for b in group))for group in groups]for row in required]
    active=[y for y,row in enumerate(rows)if any(row)]
    if not active:raise ValueError('BANK_CLASS_BOUND_EMPTY')
    first,last=min(active),max(active);uses={}
    for y,row in enumerate(rows):
        for k,cs in enumerate(row):
            for c in cs:uses.setdefault((k,c),[]).append(y)
    resident={(k,c,y):i for i,(k,c,y)in enumerate((k,c,y)for k,c in sorted(uses)for y in range(first,max(uses[k,c])+1))}
    writes={key:len(resident)+i for i,key in enumerate(key for key in resident if key[2]>first)};peak=len(resident)+len(writes)
    rr=[];cc=[];vv=[];limits=[];bounds=[(0,1)]*peak+[(0,None)];by_line={};write_lines={}
    def constraint(items,upper):
        row=len(limits)
        for index,value in items:rr.append(row);cc.append(index);vv.append(value)
        limits.append(upper)
    for(k,c,y),index in resident.items():
        by_line.setdefault((y,k),[]).append(index)
        if c in rows[y][k]:bounds[index]=(1,1)
        if y==first:continue
        w=writes[k,c,y];constraint([(index,1),(resident[k,c,y-1],-1),(w,-1)],0);write_lines.setdefault(y,[]).append(w)
        if not any(y<=t<=y+lookahead for t in uses[k,c]):bounds[w]=(0,0)
    for(y,k),indices in by_line.items():constraint([(v,1)for v in indices],15*len(groups[k]))
    for y,indices in write_lines.items():constraint([(v,1)for v in indices]+[(peak,-1)],0)
    matrix=coo_matrix((vv,(rr,cc)),shape=(len(limits),peak+1)).tocsc();objective=np.zeros(peak+1);objective[peak]=1
    solved=linprog(objective,A_ub=matrix,b_ub=limits,bounds=bounds,method='highs-ipm',options={'time_limit':time_limit})
    report=dict(schema='BYOR_FIXED_ENCODING_BANK_CLASS_CACHE_BOUND_V1',status='BOUNDED_ENCODING_CLASS_CACHE_NO_BOUND',solver_status=int(solved.status),message=solved.message,
        variables=peak+1,constraints=len(limits),bank_classes=groups,opaque_class_capacities=[15*len(g)for g in groups],lookahead=lookahead,
        source_pixel_words_and_encoding_class_fixed=True,geometry_and_bank_assignment_relaxed=True,explicit_piece_bank_restrictions_relaxed=True,
        physical_slots_relaxed=True,initial_residency_optimal=True,physical_transfer_admitted=False,native_timing_admitted=False,universal_raster_rejected=False,no_color_reduction=True)
    if solved.success:
        low=np.array([v[0]for v in bounds]);upper=np.array([np.inf if v[1]is None else v[1]for v in bounds])
        violation=max(float(np.max(np.maximum(matrix@solved.x-limits,0))),float(np.max(np.maximum(low-solved.x,0))),float(np.max(np.maximum(solved.x-upper,0))))
        dual=float(np.dot(limits,solved.ineqlin.marginals)+np.dot(low,solved.lower.marginals)+np.dot(upper[:-1],solved.upper.marginals[:-1]))
        residual=float(np.max(np.abs(objective-matrix.T@solved.ineqlin.marginals-solved.lower.marginals-solved.upper.marginals)))
        if violation>1e-6 or residual>1e-6 or abs(dual-solved.fun)>1e-6:raise AssertionError('BANK_CLASS_BOUND_PRIMAL_DUAL_CERTIFICATE')
        report.update(status='FRACTIONAL_FIXED_ENCODING_CLASS_CACHE_LOWER_BOUND',peak_write_lower_bound=float(solved.fun),validated_dual_lower_bound=dual,maximum_primal_violation=violation,maximum_dual_residual=residual)
    return report


def main():
    import argparse,json
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schedule',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--lookahead',type=int,default=55);parser.add_argument('--time-limit',type=float,default=15)
    args=parser.parse_args();result=lower_bound(json.loads(args.schedule.read_text()),args.lookahead,args.time_limit)
    args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
