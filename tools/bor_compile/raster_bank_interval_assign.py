"""Necessary interval cache search with fixed source-exact pieces and words.

All source rows retain bank capacity constraints. Cache continuity and transfer
constraints apply only inside the requested interval; no full-frame admission.
"""
import argparse,copy,json,time
from pathlib import Path
from raster_slot_greedy import demand
from raster_bank_rebalance import rebalance
from raster_bank_residency import relaxed_bound,constrain_dp,favorable_span,solve_linear


def assign(source,first,last,write_budget=19,lookahead=55,time_limit=30,window=None,fractional_cache=False):
    from ortools.sat.python import cp_model
    required,_,pixels=demand(source)
    if not 0<=first<last<len(required) or write_budget<0 or lookahead<0 or time_limit<=0 or(window is not None and window<1):
        raise ValueError('BANK_INTERVAL_ASSIGN_DOMAIN')
    if fractional_cache and window is not None:raise ValueError('BANK_INTERVAL_FRACTIONAL_PHYSICAL_CONFLICT')
    model=cp_model.CpModel();started=time.monotonic();additive=source.get('color_math','additive')!='precomposited'
    choices={};users={};bank_colors={}
    for i,(p,image)in enumerate(zip(source['pieces'],pixels)):
        allowed=set(range(4*(p['bank']//4),4*(p['bank']//4)+4))if additive else set(range(8))
        allowed.intersection_update(p.get('allowed_banks',range(8)))
        variables=[]
        for b in sorted(allowed):
            v=model.new_bool_var(f'p{i}b{b}');choices[i,b]=v;variables.append(v)
            model.add_hint(v,int(p['bank']==b))
            for ly,row in enumerate(image):
                y=p['y']+ly
                for c in sorted(set(int(c)for c in row if c>=0)):
                    users.setdefault((b,c,y),[]).append(v)
                    if first<=y<=last:bank_colors.setdefault((b,c),set()).add(y)
        model.add(sum(variables)==1)
    needed={};rows={}
    for key,variables in sorted(users.items()):
        b,c,y=key;v=model.new_bool_var(f'need{b}_{c}_{y}')
        for variable in variables:model.add(v>=variable)
        model.add(v<=sum(variables));needed[key]=v;rows.setdefault((b,y),[]).append(v)
        model.add_hint(v,int(c in required[y][b]))
    for variables in rows.values():model.add(sum(variables)<=15)
    symmetry=window is None and all(set(b for ii,b in choices if ii==i)==set(range(4*(p['bank']//4),4*(p['bank']//4)+4)if additive else range(8))for i,p in enumerate(source['pieces']))
    if symmetry:
        for first_bank in((0,4)if additive else(0,)):
            for b in range(first_bank+1,first_bank+(4 if additive else 8)):
                for i in range(len(source['pieces'])):
                    if(i,b)in choices:model.add(choices[i,b]<=sum(v for(j,bb),v in choices.items()if bb==b-1 and j<=i))
    hint_state={b:[None]*15 for b in range(8)};hint_rows=[]
    for row in source['trace']:
        for e in row['updates']:hint_state[e['bank']][e['slot']-1]=e['color']
        hint_rows.append({b:set(c for c in values if c is not None)for b,values in hint_state.items()})
    resident={};writes={};cache_rows={};write_rows={}
    for (b,c),lines in sorted(bank_colors.items()):
        for y in range(first,max(lines)+1):
            v=model.new_bool_var(f'res{b}_{c}_{y}');resident[b,c,y]=v;cache_rows.setdefault((b,y),[]).append(v)
            model.add_hint(v,int(c in hint_rows[y][b]))
            if(b,c,y)in needed:model.add(v>=needed[b,c,y])
            if y>first:
                w=model.new_bool_var(f'write{b}_{c}_{y}');writes[b,c,y]=w;write_rows.setdefault(y,[]).append(w)
                prior=resident[b,c,y-1]
                model.add_hint(w,int(c in hint_rows[y][b]and c not in hint_rows[y-1][b]))
                model.add(w>=v-prior);model.add(w<=v);model.add(w+prior<=1)
                future=[needed[b,c,t]for t in lines if y<=t<=y+lookahead]
                model.add(w<=sum(future))
    for variables in cache_rows.values():model.add(sum(variables)<=15)
    # Redundant interval unions expose the minimum reload demand directly,
    # instead of relying only on many individual residency implications.
    union_cuts=0;union_variables=[]
    for a in range(first,last):
        for z in range(a+1,last+1):
            if fractional_cache and(a,z)!=(first,last):continue
            for b in range(8):
                union=[]
                for bb,c in bank_colors:
                    if bb!=b:continue
                    values=[needed[b,c,y]for y in bank_colors[b,c]if a<=y<=z]
                    if not values:continue
                    q=model.new_bool_var(f'union{b}_{c}_{a}_{z}')
                    union_variables.append(q)
                    for variable in values:model.add(q>=variable)
                    model.add(q<=sum(values));union.append(q)
                if union:
                    model.add(sum(union)<=15+sum(v for(bb,c,y),v in writes.items()if bb==b and a<y<=z));union_cuts+=1
    for y,variables in write_rows.items():
        model.add(sum(variables)<=write_budget)
        if window is not None:
            counts=[];active=[]
            for b in range(8):
                values=[v for(bb,c,yy),v in writes.items()if bb==b and yy==y]
                n=model.new_int_var(0,15,f'count{b}_{y}');model.add(n==sum(values));counts.append(n)
                a=model.new_bool_var(f'active{b}_{y}');model.add(n>=a);model.add(n<=15*a);active.append(a)
            constrain_dp(model,counts,active,window,f'line{y}_')
    model.minimize(sum(writes.values()))
    if fractional_cache:
        # OR indicators remain exactly 0/1 because their piece-bank inputs
        # are integer. Relaxing these derived domains does not change their
        # meaning, and leaves only the actual bank choices for MIP branching.
        value,statistics=solve_linear(model,time_limit,{v.index for v in list(resident.values())+list(writes.values())+list(needed.values())+union_variables})
        statistics['integer_piece_bank_variables']=len(choices)
    else:
        solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit
        solver.parameters.num_search_workers=4;solver.parameters.cp_model_probing_level=0
        status=solver.solve(model);value=solver.value if status in(cp_model.OPTIMAL,cp_model.FEASIBLE)else None
        statistics=dict(message=solver.status_name(status),variables=len(model.proto.variables),constraints=len(model.proto.constraints),
            seconds=solver.wall_time,branches=solver.num_branches,conflicts=solver.num_conflicts)
    report=dict(schema='BYOR_NECESSARY_INTERVAL_BANK_ASSIGNMENT_V1',status='BOUNDED_INTERVAL_BANK_ASSIGNMENT_NO_CANDIDATE',
        interval=[first,last],write_budget=write_budget,lookahead_lines=lookahead,prepared_dma_window=window,
        solver=statistics,fractional_cache=fractional_cache,
        geometry_fixed=True,pixel_words_fixed=True,all_source_rows_bank_capacity_enforced=True,bank_label_symmetry=symmetry,interval_union_cuts=union_cuts,
        initial_interval_palette_free=True,outside_interval_cache_continuity_relaxed=True,
        full_frame_schedule_proven=False,physical_transfer_admitted=False,native_timing_admitted=False,
        universal_raster_rejected=False,no_color_reduction=True)
    result=copy.deepcopy(source)
    if value is not None:
        assignment=[next(b for ii,b in choices if ii==i and value(choices[ii,b]))for i in range(len(source['pieces']))]
        result=rebalance(source,lookahead,maximum_moves=0,maximum_interval=1,initial_assignment=assignment)
        report.update(status='NECESSARY_INTERVAL_BANK_ASSIGNMENT_FOUND',piece_assignment=assignment,
            interval_peak_writes=max((sum(value(v)for v in vs)for vs in write_rows.values()),default=0),
            interval_total_writes=sum(value(v)for v in writes.values()),full_source_pixel_words_replayed=True)
        rebound,_,_=demand(result);interval_trace=[];previous=None
        for y in(()if fractional_cache else range(first,last+1)):
            state={b:sorted(c for bb,c,yy in resident if bb==b and yy==y and value(resident[bb,c,yy]))for b in range(8)}
            if any(len(state[b])>15 or not rebound[y][b].issubset(state[b])for b in range(8)):
                raise AssertionError('BANK_INTERVAL_INDEPENDENT_RESIDENCY')
            updates=[] if previous is None else[dict(bank=b,color=c)for b in range(8)for c in state[b]if c not in previous[b]]
            if previous is not None and(len(updates)>write_budget or len(updates)!=sum(value(v)for v in write_rows.get(y,[]))):
                raise AssertionError('BANK_INTERVAL_INDEPENDENT_WRITES')
            span=favorable_span(updates)
            if window is not None and span>=window:raise AssertionError('BANK_INTERVAL_INDEPENDENT_TRANSFER_BOUND')
            interval_trace.append(dict(scanline=y,resident=state,updates=updates,favorable_commit_span=span));previous=state
        report.update(interval_trace=interval_trace,independent_interval_replay_verified=not fractional_cache,
            integer_interval_schedule_proven=not fractional_cache)
        report['full_frame_cache_lower_bound']=relaxed_bound(result,lookahead,min(10,time_limit),include_dual_pressure=True)
    report['total_seconds']=time.monotonic()-started;result['interval_bank_assignment']=report
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--first',type=int,required=True);p.add_argument('--last',type=int,required=True)
    p.add_argument('--write-budget',type=int,default=19);p.add_argument('--lookahead',type=int,default=55)
    p.add_argument('--time-limit',type=float,default=30);p.add_argument('--prepared-dma-window',type=int)
    p.add_argument('--fractional-cache',action='store_true',help='Search integer piece banks using a necessary fractional cache relaxation; never proves a schedule.')
    a=p.parse_args();r=assign(json.loads(a.schedule.read_text()),a.first,a.last,a.write_budget,a.lookahead,a.time_limit,a.prepared_dma_window,a.fractional_cache)
    a.output.write_text(json.dumps(r,indent=2)+'\n')
    report=r['interval_bank_assignment'];print(json.dumps({k:v for k,v in report.items()if k not in('interval_trace','piece_assignment','full_frame_cache_lower_bound')}|dict(full_frame_cache_lower_bound=report.get('full_frame_cache_lower_bound',{}).get('validated_dual_lower_bound'))))


if __name__=='__main__':main()
