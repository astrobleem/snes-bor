"""Necessary fixed-bank transfer bound from scanline color-union intervals.

Color residency and physical slots are relaxed. Every interval still needs its
union minus fifteen bank slots written after its first line. General prepared
range partitioning accounts for bank separation and transparent words.
"""
import argparse,json
from pathlib import Path
from raster_slot_greedy import demand
from raster_bank_residency import constrain_dp,favorable_span,solve_linear
from raster_dma_partition import minimum_commit_span


def lower_bound(source,time_limit=30,range_backend='dp',solver_backend='cp-sat'):
    from ortools.sat.python import cp_model
    if time_limit<=0:raise ValueError('BANK_SPAN_BOUND_TIME_LIMIT')
    if range_backend not in('dp','ranges')or solver_backend not in('cp-sat','highs')or solver_backend=='highs'and range_backend!='ranges':raise ValueError('BANK_SPAN_BOUND_BACKEND')
    required,_,_=demand(source);visible=[y for y,row in enumerate(required)if any(row)]
    if not visible:raise ValueError('BANK_SPAN_BOUND_EMPTY')
    first,last=min(visible),max(visible);model=cp_model.CpModel();writes={};prefix={};cuts=0
    state={b:[None]*15 for b in range(8)};hints={};density={}
    for row in source['trace']:
        before={b:state[b].copy()for b in range(8)}
        for e in row['updates']:state[e['bank']][e['slot']-1]=e['color']
        hints[row['scanline']]=[sum((0 if a is None else a)!=(0 if c is None else c)for a,c in zip(before[b],state[b]))for b in range(8)]
    for b in range(8):
        prefix[first,b]=model.new_constant(0)
        prefix_hint=0
        for y in range(first+1,last+1):
            w=model.new_int_var(0,15,f'w{y}_{b}');writes[y,b]=w
            prefix[y,b]=model.new_int_var(0,15*(y-first),f'p{y}_{b}')
            model.add(prefix[y,b]==prefix[y-1,b]+w)
            model.add_hint(w,hints[y][b]);prefix_hint+=hints[y][b];model.add_hint(prefix[y,b],prefix_hint)
        for left in range(first,last+1):
            union=set()
            for right in range(left,last+1):
                union.update(required[right][b])
                if len(union)>15:
                    if sum(hints[y][b]for y in range(left+1,right+1))<len(union)-15:raise AssertionError('BANK_SPAN_BOUND_SOURCE_BANK_HINT_INTERVAL')
                    model.add(prefix[right,b]-prefix[left,b]>=len(union)-15);cuts+=1
                    density[left,right]=density.get((left,right),0)+len(union)-15
    peak=model.new_int_var(0,4096,'peak')
    compulsory_peak=max(((n+right-left-1)//(right-left)for(left,right),n in density.items()),default=0)
    if compulsory_peak:model.add(peak>=minimum_commit_span(compulsory_peak)+40)
    hinted_peak=max((favorable_span([dict(bank=b)for b,n in enumerate(hints[y])for _ in range(n)])for y in range(first+1,last+1)),default=0)
    for(left,right),n in density.items():
        if sum(sum(hints[y])for y in range(left+1,right+1))<n:raise AssertionError('BANK_SPAN_BOUND_SOURCE_HINT_INTERVAL')
    model.add(peak<=hinted_peak+40);model.add_hint(peak,hinted_peak+40)
    for y in range(first+1,last+1):
        counts=[writes[y,b]for b in range(8)];active=[]
        for b,w in enumerate(counts):
            flag=model.new_bool_var(f'a{y}_{b}');active.append(flag)
            model.add_hint(flag,int(hints[y][b]>0))
            model.add(w>=flag);model.add(w<=15*flag)
        if range_backend=='dp':cost=constrain_dp(model,counts,active,4097,f'row{y}',4)
        else:
            ranges={};cost=0
            for lo in range(8):
                for hi in range(lo,8):
                    q=model.new_bool_var(f'range{y}_{lo}_{hi}');t=model.new_int_var(0,15 if lo==hi else 30,f'words{y}_{lo}_{hi}')
                    model.add(q<=active[lo]);model.add(q<=active[hi])
                    endpoint=counts[lo]+(counts[hi]if lo!=hi else 0)
                    model.add(t<=30*q);model.add(t>=endpoint-30*(1-q));model.add(t<=endpoint)
                    ranges[lo,hi]=q;cost+=16*t+(24+(16*(16*(hi-lo-1)+1)if hi!=lo else 0))*q
            model.add(sum(ranges.values())<=4)
            for b in range(8):
                cover=sum(q for(lo,hi),q in ranges.items()if lo<=b<=hi)
                model.add(cover<=1);model.add(cover>=active[b])
        model.add(peak>=cost)
    model.minimize(peak)
    if solver_backend=='highs':
        value,statistics=solve_linear(model,time_limit)
        bound=max(minimum_commit_span(compulsory_peak),int(statistics.get('solver_objective_lower_bound',0))-40)
    else:
        solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit
        solver.parameters.num_search_workers=4;solver.parameters.cp_model_probing_level=0
        status=solver.solve(model);value=solver.value if status in(cp_model.FEASIBLE,cp_model.OPTIMAL)else None
        statistics=dict(solver_status=solver.status_name(status),solver_seconds=solver.wall_time)
        bound=max(0,int(solver.best_objective_bound)-40)
    statistics.pop('solver_backend',None)
    report=dict(schema='BYOR_FIXED_BANK_INTERVAL_SPAN_LOWER_BOUND_V1',**statistics,
        variables=len(model.proto.variables),constraints=len(model.proto.constraints),interval_cuts=cuts,
        range_backend=range_backend,solver_backend=solver_backend,validated_integer_peak_span_lower_bound=bound,
        compulsory_peak_writes_lower_bound=compulsory_peak,source_trace_peak_optimistic_span=hinted_peak,
        fixed_piece_banks=True,initial_palette_may_preload_entire_frame=True,color_residency_relaxed=True,
        physical_endpoint_slots_relaxed=True,general_bank_range_partition=True,schedule_proven=False,
        native_timing_admitted=False,universal_raster_rejected=False,no_color_reduction=True)
    if value is not None:
        counts={y:[value(writes[y,b])for b in range(8)]for y in range(first+1,last+1)}
        replayed=max((favorable_span([dict(bank=b)for b,n in enumerate(row)for _ in range(n)])for row in counts.values()),default=0)
        if replayed>max(0,value(peak)-40)or bound>replayed:raise AssertionError('BANK_SPAN_BOUND_INDEPENDENT_PARTITION')
        report.update(relaxed_aggregate_peak_span=replayed,aggregate_bank_write_counts=counts,independent_partition_replayed=True)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--time-limit',type=float,default=30);p.add_argument('--range-backend',choices=('dp','ranges'),default='dp');p.add_argument('--solver-backend',choices=('cp-sat','highs'),default='cp-sat')
    a=p.parse_args();r=lower_bound(json.loads(a.schedule.read_text()),a.time_limit,a.range_backend,a.solver_backend)
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items()if k!='aggregate_bank_write_counts'}))


if __name__=='__main__':main()
