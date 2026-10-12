"""Choose fixed piece banks with independently certified fractional cache cuts.

The master selects OAM banks; a separate cache LP supplies valid lower bounds.
Optional row-word masks split source pixels into fixed-bank OAM entries and
count every entry's complete hardware rectangle against all three OBJ limits.
A candidate is only a fixed bank assignment. Integer residency, physical slots,
transfer timing and source alpha still require their existing verification.
"""
import copy,hashlib,json,time
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix
from raster_slot_greedy import demand,bank_groups
from raster_global_bank_classes import rebuild_schedule


def nonpositive_solver_dual(values):
    """Clip solver sign noise before strict certificate replay; reject real errors."""
    values=np.asarray(values,dtype=float)
    if values.ndim!=1 or not np.all(np.isfinite(values)) or np.any(values>1e-9):
        raise ValueError('PIECE_CACHE_FRESH_DUAL_SIGN')
    return np.minimum(values,0)


def search(source,iterations=20,time_limit=120,master_seconds=3,maximum_changes=None,objective_kind='writes',write_budget=21,row_word_masks=False,resume_report=None,interval_cut_span=0,geometry_reservation=None):
    from ortools.sat.python import cp_model
    if iterations<1 or time_limit<=0 or master_seconds<=0 or (maximum_changes is not None and maximum_changes<1): raise ValueError('PIECE_CACHE_DECOMPOSITION_DOMAIN')
    if objective_kind not in('writes','dma-window')or type(write_budget)is not int or not 0<=write_budget<=120:raise ValueError('PIECE_CACHE_DECOMPOSITION_OBJECTIVE_DOMAIN')
    if type(interval_cut_span)is not int or not 0<=interval_cut_span<=256:raise ValueError('PIECE_CACHE_INTERVAL_CUT_DOMAIN')
    if any(p['bank']not in p.get('allowed_banks',range(8))for p in source['pieces']):
        raise ValueError('PIECE_CACHE_DECOMPOSITION_SEED_BANK_ELIGIBILITY')
    _,_,images=demand(source); pieces=copy.deepcopy(source['pieces']);groups=bank_groups(source)
    height=len(source['trace'])
    reservation=dict(oam_entries=0,sprites_per_line=[0]*height,tile_slivers_per_line=[0]*height)
    if geometry_reservation is not None:
        if (not row_word_masks or not isinstance(geometry_reservation,dict) or
            set(geometry_reservation)!=set(reservation)):
            raise ValueError('PIECE_CACHE_GEOMETRY_RESERVATION_DOMAIN')
        reservation=copy.deepcopy(geometry_reservation)
        if (type(reservation['oam_entries'])is not int or not 0<=reservation['oam_entries']<=128 or
            any(not isinstance(reservation[k],list)or len(reservation[k])!=height or
                any(type(v)is not int or not 0<=v<=limit for v in reservation[k])
                for k,limit in [('sprites_per_line',32),('tile_slivers_per_line',34)])):
            raise ValueError('PIECE_CACHE_GEOMETRY_RESERVATION_DOMAIN')
    domains=[]; owners={};decision_keys=[];piece_decisions={}
    for i,(p,image) in enumerate(zip(pieces,images)):
        p['rows']={p['y']+y:sorted(set(map(int,row[row>=0]))) for y,row in enumerate(image) if np.any(row>=0)}
        domain=tuple(b for b in next(g for g in groups if p['bank'] in g) if b in p.get('allowed_banks',range(8)))
        if not domain:raise ValueError('PIECE_CACHE_DECOMPOSITION_ELIGIBILITY')
        if p['bank'] not in domain:raise ValueError('PIECE_CACHE_DECOMPOSITION_SEED_BANK_ELIGIBILITY')
        piece_decisions[i]=[]
        keys=[(i,c,y)for y,cs in p['rows'].items()for c in cs]if row_word_masks else [(i,)]
        for key in keys:
            piece_decisions.setdefault(i,[]).append(len(domains));domains.append(domain);decision_keys.append(key)
        decisions={key:j for key,j in zip(keys,piece_decisions[i])}
        for y,cs in p['rows'].items():
            for c in cs:
                for b in domain:owners.setdefault((b,c,y),set()).add(decisions[i,c,y]if row_word_masks else decisions[i,])
    first=min(y for b,c,y in owners);last=max(y for b,c,y in owners)
    uses={}
    for b,c,y in owners:uses.setdefault((b,c),set()).add(y)
    resident={(b,c,y):i for i,(b,c,y) in enumerate((b,c,y) for b,c in sorted(uses) for y in range(first,max(uses[b,c])+1))}
    writes={key:len(resident)+i for i,key in enumerate(key for key in resident if key[2]>first)}
    flag_start=len(resident)+len(writes)
    flags={(b,y):flag_start+i for i,(b,y)in enumerate((b,y)for y in range(first+1,last+1)for b in range(8))}if objective_kind=='dma-window'else{}
    bridge_start=flag_start+len(flags)
    bridges={(b,y):bridge_start+i for i,(b,y)in enumerate((b,y)for y in range(first+1,last+1)for b in range(7))}if flags else{}
    peak=bridge_start+len(bridges); bounds=[(0,1)]*peak+[(0,None)]
    rr=[];cc=[];vv=[];rhs=[];by_bank_line={};by_write_line={};by_bank_write_line={};required_rows={}
    def constraint(items,upper):
        row=len(rhs)
        for col,value in items:rr.append(row);cc.append(col);vv.append(value)
        rhs.append(upper);return row
    for key,index in resident.items():
        b,c,y=key;by_bank_line.setdefault((b,y),[]).append(index)
        if key in owners:required_rows[key]=constraint([(index,-1)],0)
        if y==first:continue
        w=writes[key];constraint([(index,1),(resident[b,c,y-1],-1),(w,-1)],0);by_write_line.setdefault(y,[]).append(w)
        by_bank_write_line.setdefault((b,y),[]).append(w)
    for indices in by_bank_line.values():constraint([(v,1)for v in indices],15)
    for y,indices in by_write_line.items():
        if objective_kind=='writes':constraint([(v,1)for v in indices]+[(peak,-1)],0)
        else:
            constraint([(v,1)for v in indices],write_budget)
            for b in range(8):
                bank_writes=by_bank_write_line.get((b,y),[])
                constraint([(v,1)for v in bank_writes]+[(flags[b,y],-15)],0)
                for v in bank_writes:constraint([(v,1),(flags[b,y],-1)],0)
            for b in range(7):
                constraint([(bridges[b,y],1),(flags[b,y],-1)],0)
                constraint([(bridges[b,y],1),(flags[b+1,y],-1)],0)
            # Grant every adjacent-bank bridge simultaneously. This can save
            # more than a real range partition; it is a necessary relaxation.
            constraint([(v,16)for v in indices]+[(flags[b,y],24)for b in range(8)]+[(bridges[b,y],-8)for b in range(7)]+[(peak,-1)],40)
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
    if row_word_masks:
        masks={}
        for i,indices in piece_decisions.items():
            if not indices:continue
            for b in domains[indices[0]]:
                v=model.new_bool_var(f'pieceMask{i}_{b}')
                model.add_max_equality(v,[selection[j][b]for j in indices]);masks[i,b]=v
        model.add(sum(masks.values())<=128-reservation['oam_entries'])
        for y in range(len(source['trace'])):
            live=[(i,b)for i,b in masks if pieces[i]['y']<=y<pieces[i]['y']+pieces[i]['height']]
            model.add(sum(masks[i,b]for i,b in live)<=32-reservation['sprites_per_line'][y])
            model.add(sum(masks[i,b]*(pieces[i]['width']//8)for i,b in live)<=34-reservation['tile_slivers_per_line'][y])
    # Certified cuts are rounded outward to integers to avoid false rejection.
    scale=1000000;t=model.new_int_var(0,(120 if objective_kind=='writes'else 4096)*scale,'fractionalPeak');model.minimize(t)
    interval_requirements=[]
    if interval_cut_span:
        # A bank starts each interval with at most fifteen resident identities.
        # Count a shared word once by ORing its object selectors. These bounds
        # hold even for fractional cache residency and the optimistic bridges.
        for begin in range(first,last,4):
            for end in range(begin+1,min(last,begin+interval_cut_span)+1):
                union={}
                for (b,c,y),indices in owners.items():
                    if begin<=y<=end:union.setdefault((b,c),set()).update(indices)
                deficits=[]
                for b in range(8):
                    present=[]
                    for (bb,c),indices in union.items():
                        if bb!=b:continue
                        options=[selection[i][b]for i in sorted(indices)]
                        signature=tuple(v.index for v in options)
                        if len(options)==1:v=options[0]
                        else:
                            if signature not in aliases:
                                v=model.new_bool_var(f'intervalAlias{len(aliases)}');model.add_max_equality(v,options);aliases[signature]=v
                            v=aliases[signature]
                        present.append(v)
                    deficit=model.new_int_var(0,len(present),f'intervalDeficit{begin}_{end}_{b}')
                    model.add(deficit>=sum(present)-15);deficits.append(deficit)
                lines=end-begin
                if objective_kind=='writes':model.add(lines*t>=scale*sum(deficits))
                else:
                    # Cost >= 16*w + 16*active - 40; active >= w/15.
                    model.add(15*lines*t>=scale*(256*sum(deficits)-600*lines))
                interval_requirements.append((lines,union))
    basis=dict(source_rgb555_sha256=source.get('source_rgb555_sha256'),
               pieces=[{k:p.get(k)for k in ('actor','x','y','width','height','rows')}for p in pieces],
               domains=domains,decision_keys=decision_keys,objective_kind=objective_kind,
               write_budget=write_budget,row_word_masks=row_word_masks)
    basis_hash=hashlib.sha256(json.dumps(basis,sort_keys=True).encode()).hexdigest()
    cuts=[];evaluated=[];restored=0
    def install_cut(certificate):
        def vector(entries,length):
            result=np.zeros(length);seen=set()
            for i,value in entries:
                if type(i)is not int or not 0<=i<length or i in seen or not np.isfinite(value)or value>0:raise ValueError('PIECE_CACHE_RESUME_DUAL_DOMAIN')
                seen.add(i);result[i]=value
            return result
        q=vector(certificate['inequality_dual'],len(rhs));u=vector(certificate['upper_dual'],peak+1)
        if u[peak]!=0:raise ValueError('PIECE_CACHE_RESUME_UNBOUNDED_PEAK_DUAL')
        lower=objective-matrix.T@q-u
        if float(lower.min()) < -1e-6:raise ValueError('PIECE_CACHE_RESUME_DUAL_STATIONARITY')
        # Normalize the unbounded peak column strictly inward. Finite columns
        # have upper bound one; subtract their aggregate negative residual.
        factor=min(1.,1/(1-float(lower[peak])+1e-12))
        q*=factor;u*=factor;lower=objective-matrix.T@q-u
        base=np.array(rhs,copy=True)
        for row in required_rows.values():base[row]=0
        constant=float(base@q+u.sum()-np.maximum(-lower[:-1],0).sum())
        weights={key:max(0.,-float(q[row]))for key,row in required_rows.items()}
        model.add(t>=sum(int(np.floor(value*scale))*required[key]for key,value in weights.items()if value>1e-9)+int(np.floor(constant*scale)))
        cuts.append(copy.deepcopy(certificate))
    def valid_assignment(a):
        return isinstance(a,list)and len(a)==len(domains)and all(type(b)is int and b in domain for b,domain in zip(a,domains))
    def geometry_fits(a):
        if not row_word_masks:return True
        entries=[i for i,indices in piece_decisions.items()for b in {a[j]for j in indices}]
        return (len(entries)+reservation['oam_entries']<=128 and
                all(sum(pieces[i]['y']<=y<pieces[i]['y']+pieces[i]['height']for i in entries)+reservation['sprites_per_line'][y]<=32 and
                    sum(pieces[i]['width']//8 for i in entries if pieces[i]['y']<=y<pieces[i]['y']+pieces[i]['height'])+reservation['tile_slivers_per_line'][y]<=34
                    for y in range(height)))
    assignment=[pieces[key[0]]['bank'] for key in decision_keys]
    if resume_report is not None:
        if resume_report.get('cache_basis_sha256')!=basis_hash:raise ValueError('PIECE_CACHE_RESUME_SOURCE_BASIS')
        for cut in resume_report['certified_master_cuts']:install_cut(cut)
        restored=len(cuts)
        for a in resume_report['evaluated_assignments']:
            if not valid_assignment(a):raise ValueError('PIECE_CACHE_RESUME_ASSIGNMENT_DOMAIN')
            model.add(sum(selection[i][b]for i,b in enumerate(a))<=len(a)-1);evaluated.append(a.copy())
        assignment=resume_report['best_decision_assignment']
        if not valid_assignment(assignment):raise ValueError('PIECE_CACHE_RESUME_ASSIGNMENT_DOMAIN')
    best=float('inf');best_assignment=None;reports=[];started=time.monotonic()
    for iteration in range(iterations):
        if time.monotonic()-started>time_limit:break
        for key,row in required_rows.items():rhs[row]=-int(any(assignment[i]==key[0] for i in owners[key]))
        solved=linprog(objective,A_ub=matrix,b_ub=rhs,bounds=bounds,method='highs-ipm',options={'time_limit':min(30,time_limit)})
        if not solved.success:
            reports.append(dict(iteration=iteration,objective_kind=objective_kind,
                                cache_lp_status=int(solved.status),message=solved.message,
                                validated_bound_available=False))
            break
        dual=float(rhs@solved.ineqlin.marginals+sum(solved.upper.marginals[:-1]))
        residual=float(np.max(np.abs(objective-matrix.T@solved.ineqlin.marginals-solved.lower.marginals-solved.upper.marginals)))
        violation=float(np.max(np.maximum(matrix@solved.x-rhs,0)))
        if abs(dual-solved.fun)>1e-6 or residual>1e-6 or violation>1e-6:raise AssertionError('PIECE_CACHE_DECOMPOSITION_DUAL')
        interval_bound=0.
        for lines,union in interval_requirements:
            counts=[0]*8
            for (b,c),indices in union.items():
                if any(assignment[i]==b for i in indices):counts[b]+=1
            loads=sum(max(0,n-15)for n in counts)
            bound=loads/lines if objective_kind=='writes'else 256*loads/(15*lines)-40
            interval_bound=max(interval_bound,bound)
        if interval_bound>solved.fun+1e-6:raise AssertionError('PIECE_CACHE_INTERVAL_BOUND_REPLAY')
        report=dict(iteration=iteration,objective_kind=objective_kind,validated_dual_lower_bound=dual,maximum_dual_residual=residual,maximum_primal_violation=violation)
        report['independently_replayed_interval_lower_bound']=interval_bound
        report['peak_write_lower_bound'if objective_kind=='writes'else'peak_dma_span_lower_bound']=float(solved.fun)
        reports.append(report)
        report['reserved_geometry_admitted']=geometry_fits(assignment)
        if report['reserved_geometry_admitted']and solved.fun<best:best=float(solved.fun);best_assignment=assignment.copy()
        inequality_dual=nonpositive_solver_dual(solved.ineqlin.marginals)
        upper_dual=nonpositive_solver_dual(solved.upper.marginals)
        report['fresh_dual_positive_roundoff_values_clipped']=int(np.count_nonzero(solved.ineqlin.marginals>0)+np.count_nonzero(solved.upper.marginals>0))
        install_cut(dict(inequality_dual=[[i,float(v)]for i,v in enumerate(inequality_dual)if v],
                         upper_dual=[[i,float(v)]for i,v in enumerate(upper_dual)if v]))
        # Exclude an evaluated assignment so a rounded tie cannot stall search.
        model.add(sum(selection[i][b]for i,b in enumerate(assignment))<=len(assignment)-1)
        if assignment not in evaluated:evaluated.append(assignment.copy())
        model.clear_hints()
        incumbent=best_assignment if best_assignment is not None else assignment
        for i,b in enumerate(incumbent):
            for bb,v in selection[i].items():model.add_hint(v,int(bb==b))
        master=model.clone()
        if maximum_changes is not None:
            master.add(sum(selection[i][b]for i,b in enumerate(incumbent))>=len(selection)-maximum_changes)
        solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=master_seconds;solver.parameters.num_search_workers=4
        status=solver.solve(master);report.update(master_status=solver.status_name(status),master_seconds=solver.wall_time,master_lower_bound=float(solver.best_objective_bound)/scale)
        if status not in(cp_model.FEASIBLE,cp_model.OPTIMAL):break
        assignment=[next(b for b,v in choices.items()if solver.value(v))for choices in selection]
    report=dict(schema='BYOR_FIXED_PIECE_CACHE_DECOMPOSITION_V1',iterations=reports,seconds=time.monotonic()-started,maximum_changed_pieces_per_master=maximum_changes,
        objective_kind=objective_kind,row_word_masks=row_word_masks,write_budget=write_budget if objective_kind=='dma-window'else None,alias_aware=True,initial_residency_optimal=True,
        interval_cut_span=interval_cut_span,interval_cut_count=len(interval_requirements),
        geometry_reservation=reservation,reservation_proves_concurrent_palette_or_layer_admission=False,
        cache_basis_sha256=basis_hash,certified_master_cuts=cuts,restored_certified_cuts=restored,
        cache_lp_variables=peak+1,cache_lp_constraints=len(rhs),
        evaluated_assignments=evaluated,best_decision_assignment=best_assignment,
        fractional_residency_only=True,physical_transfer_admitted=False,native_timing_admitted=False,universal_raster_rejected=False,no_color_reduction=True)
    report['best_fractional_cache_bound'if objective_kind=='writes'else'best_fractional_dma_span_bound']=best if best_assignment is not None else None
    if best_assignment is None:return report
    expanded=[];banks=[]
    if row_word_masks:
        for i,p in enumerate(pieces):
            if not piece_decisions[i]:continue
            for b in domains[piece_decisions[i][0]]:
                rows={y:[]for y in p['rows']}
                for j in piece_decisions[i]:
                    if best_assignment[j]==b:rows[decision_keys[j][2]].append(decision_keys[j][1])
                if any(rows.values()):expanded.append(dict(p,source_piece=i,rows=rows));banks.append(b)
    else:expanded=[dict(p,source_piece=i)for i,p in enumerate(pieces)];banks=best_assignment
    rebuilt=rebuild_schedule(source,dict(status='JOINT_GLOBAL_BANK_MASK_WORD_IDENTITIES_PROVEN',pieces=expanded,assignment=banks,pixel_word_identities_replayed=True),last-first)
    rebuilt['piece_cache_decomposition']=report
    return rebuilt


def main():
    import argparse,json
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schedule',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--iterations',type=int,default=20);parser.add_argument('--time-limit',type=float,default=120)
    parser.add_argument('--master-seconds',type=float,default=3);parser.add_argument('--maximum-changes',type=int)
    parser.add_argument('--objective',choices=('writes','dma-window'),default='writes');parser.add_argument('--write-budget',type=int,default=21)
    parser.add_argument('--row-word-masks',action='store_true')
    parser.add_argument('--resume-report',type=Path)
    parser.add_argument('--interval-cut-span',type=int,default=0)
    parser.add_argument('--geometry-reservation',type=Path,help='JSON with other actors OAM count and sprites/tile slivers per line. Geometry only; concurrent palette and layer admission remain separate.')
    args=parser.parse_args();resume=json.loads(args.resume_report.read_text())if args.resume_report else None
    if resume is not None:resume=resume.get('piece_cache_decomposition',resume)
    result=search(json.loads(args.schedule.read_text()),args.iterations,args.time_limit,args.master_seconds,args.maximum_changes,args.objective,args.write_budget,args.row_word_masks,resume,args.interval_cut_span,json.loads(args.geometry_reservation.read_text())if args.geometry_reservation else None)
    args.output.write_text(json.dumps(result,indent=2)+'\n');report=result.get('piece_cache_decomposition',result)
    print(json.dumps(dict({k:v for k,v in report.items()if k not in('iterations','certified_master_cuts','evaluated_assignments','best_decision_assignment','geometry_reservation')},iterations_completed=len(report['iterations']))))


if __name__=='__main__':main()
