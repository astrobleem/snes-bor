"""Compact fixed-OAM-bank cache search with bounded reload intervals.

Optional intervals count one resident RGB555 identity per bank. This avoids a
Boolean residency variable at every scanline. Load-count bounds restrict the
family; a witness is logical and still needs physical transfer admission.
"""
import copy
import numpy as np
from raster_slot_greedy import demand,bank_groups
from raster_global_bank_classes import rebuild_schedule
from raster_word_cache_repair import compile_cache_rows


def optimize(source,time_limit=120,write_budget=21,lookahead=55,maximum_loads=2):
    from ortools.sat.python import cp_model
    if time_limit<=0 or not 0<=write_budget<=120 or lookahead<0 or not 1<=maximum_loads<=8:raise ValueError('INTERVAL_PIECE_CACHE_DOMAIN')
    _,_,images=demand(source);pieces=copy.deepcopy(source['pieces']);groups=bank_groups(source);owners={};domains=[]
    for i,(p,image)in enumerate(zip(pieces,images)):
        p['rows']={p['y']+y:sorted(set(map(int,row[row>=0])))for y,row in enumerate(image)if np.any(row>=0)}
        domains.append(tuple(b for b in next(g for g in groups if p['bank']in g)if b in p.get('allowed_banks',range(8))))
        if not domains[-1]:raise ValueError('INTERVAL_PIECE_CACHE_ELIGIBILITY')
        for y,cs in p['rows'].items():
            for c in cs:
                for b in domains[-1]:owners.setdefault((c,b,y),set()).add(i)
    first=min(y for c,b,y in owners);last=max(y for c,b,y in owners);height=last-first+1
    model=cp_model.CpModel();selection=[];required={};color_uses={};aliases={}
    for i,p in enumerate(pieces):
        choices={b:model.new_bool_var(f'piece{i}_{b}')for b in domains[i]};model.add_exactly_one(list(choices.values()));selection.append(choices)
        for b,v in choices.items():model.add_hint(v,int(b==p['bank']))
    canonical_groups=[]
    # These labels are interchangeable only because this model has no physical
    # address or DMA range constraints. Explicit narrower domains disable it.
    for group in groups:
        if any(set(domain)&set(group) and set(domain)!=set(group)for domain in domains):continue
        indices=[i for i,domain in enumerate(domains)if set(domain)==set(group)]
        if not indices:continue
        canonical_groups.append(group)
        for position,i in enumerate(indices):
            for left,right in zip(group,group[1:]):model.add(selection[i][right]<=sum(selection[j][left]for j in indices[:position]))
    for(c,b,y),indices in owners.items():
        options=[selection[i][b]for i in sorted(indices)];signature=tuple(v.index for v in options)
        if len(options)==1:r=options[0]
        else:
            if signature not in aliases:
                r=model.new_bool_var(f'ownerAlias{len(aliases)}');model.add_max_equality(r,options);aliases[signature]=r
            r=aliases[signature]
        required[c,b,y-first]=r;color_uses.setdefault((c,b),[]).append(y-first)
    by_bank_line={}
    for(c,b,y),r in required.items():by_bank_line.setdefault((b,y),[]).append(r)
    for row in by_bank_line.values():model.add(sum(row)<=15)
    bank_intervals={b:[]for b in range(8)};write_intervals=[];loads={};write_flags=[]
    for(c,b),uses in color_uses.items():
        uses=sorted(uses);intervals=[];coverage={y:[]for y in uses};loads[c,b]=[]
        for k in range(maximum_loads):
            present=model.new_bool_var(f'cache{c}_{b}_{k}');start=model.new_int_var(-1,max(uses),f'start{c}_{b}_{k}')
            end=model.new_int_var(1,max(uses)+1,f'end{c}_{b}_{k}');duration=model.new_int_var(0,height+1,f'duration{c}_{b}_{k}')
            interval=model.new_optional_interval_var(start,duration,end,present,f'interval{c}_{b}_{k}')
            intervals.append(interval);bank_intervals[b].append(interval);loads[c,b].append((present,start,end))
            initial=model.new_bool_var(f'initial{c}_{b}_{k}');model.add(start==-1).only_enforce_if(initial);model.add(start>=0).only_enforce_if(initial.Not())
            write=model.new_bool_var(f'write{c}_{b}_{k}');model.add(write<=present);model.add(write+initial<=1);model.add(write>=present-initial)
            write_intervals.append(model.new_optional_fixed_size_interval_var(start,1,write,f'load{c}_{b}_{k}'));write_flags.append(write)
            witnesses=[]
            for y in uses:
                cover=model.new_bool_var(f'cover{c}_{b}_{k}_{y}');coverage[y].append(cover)
                model.add(cover<=present);model.add(start<=y).only_enforce_if(cover);model.add(end>=y+1).only_enforce_if(cover)
                witness=model.new_bool_var(f'future{c}_{b}_{k}_{y}');model.add(witness<=cover);model.add(witness<=required[c,b,y])
                model.add(start>=y-lookahead).only_enforce_if([witness,initial.Not()]);witnesses.append(witness)
            model.add(sum(witnesses)>=present)
            if k:
                previous=loads[c,b][k-1];model.add(present<=previous[0]);model.add(start>=previous[2]).only_enforce_if(present)
        model.add_no_overlap(intervals)
        for y,options in coverage.items():model.add(sum(options)>=required[c,b,y])
    for intervals in bank_intervals.values():model.add_cumulative(intervals,[1]*len(intervals),15)
    model.add_cumulative(write_intervals,[1]*len(write_intervals),write_budget)
    model.minimize(sum(write_flags))
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit;solver.parameters.num_search_workers=4
    solver.parameters.cp_model_probing_level=0;solver.parameters.use_sat_inprocessing=False
    status=solver.solve(model)
    report=dict(schema='BYOR_BOUNDED_RELOAD_INTERVAL_PIECE_CACHE_V1',status='BOUNDED_INTERVAL_CACHE_NO_CANDIDATE',solver_status=solver.status_name(status),
        solver_seconds=solver.wall_time,branches=solver.num_branches,conflicts=solver.num_conflicts,variables=len(model.proto.variables),constraints=len(model.proto.constraints),
        maximum_loads_per_word_bank=maximum_loads,write_budget=write_budget,lookahead=lookahead,source_piece_geometry_and_encoding_class_fixed=True,
        bank_labels_canonicalized_without_transfer_constraints=canonical_groups,
        word_bank_copies_allowed=True,shared_color_residency_counted_once_per_bank=True,physical_transfer_admitted=False,native_timing_admitted=False,universal_raster_rejected=False,no_color_reduction=True)
    if status not in(cp_model.FEASIBLE,cp_model.OPTIMAL):return report
    assignment=[next(b for b,v in choices.items()if solver.value(v))for choices in selection]
    frame=rebuild_schedule(source,dict(status='JOINT_GLOBAL_BANK_MASK_WORD_IDENTITIES_PROVEN',pieces=[dict(p,source_piece=i)for i,p in enumerate(pieces)],assignment=assignment,pixel_word_identities_replayed=True),lookahead)
    rows={y:{b:set()for b in range(8)}for y in range(first,last+1)}
    for(c,b),segments in loads.items():
        for present,start,end in segments:
            if not solver.value(present):continue
            for relative_y in range(max(0,solver.value(start)),solver.value(end)):rows[first+relative_y][b].add(c)
    report.update(status='LOGICAL_INTERVAL_CACHE_AND_FIXED_BANK_IDENTITIES_PROVEN',total_solver_palette_loads=int(solver.objective_value),objective_bound=solver.best_objective_bound)
    result=compile_cache_rows(frame,rows,lookahead,write_budget,9999,report,'interval_piece_cache')
    result['prepared_dma_partition_bound_enforced']=False;result['prepared_dma_window_master_clocks']=None
    return result


def main():
    import argparse,json
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schedule',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--time-limit',type=float,default=120);parser.add_argument('--write-budget',type=int,default=21)
    parser.add_argument('--lookahead',type=int,default=55);parser.add_argument('--maximum-loads',type=int,default=2)
    args=parser.parse_args();result=optimize(json.loads(args.schedule.read_text()),args.time_limit,args.write_budget,args.lookahead,args.maximum_loads)
    args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result.get('interval_piece_cache',result)))


if __name__=='__main__':main()
