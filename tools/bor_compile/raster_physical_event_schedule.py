"""Exact fixed-index load-time scheduling with physical four-range DMA costs.

Slots and piece banks stay fixed. Every event may move between its preceding
old-color use and following new-color use, while preserving slot event order.
This restricted family cannot establish universal raster infeasibility.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from ortools.sat.python import cp_model
from raster_obj_compact import unpack
from raster_slot_greedy import demand
from raster_slot_refine import verify_packets
from raster_physical_ranges import constrain_fixed_addresses
from raster_physical_write_shift import shift


def optimize(source,window=345,time_limit=60,lookahead=55):
    if window<1 or time_limit<=0 or lookahead<0:raise ValueError('EVENT_SCHEDULE_DOMAIN')
    _,_,pixels=demand(source);verify_packets(source)
    height=len(source['trace']);references={};events=[];by_slot={}
    for p,mask,words in zip(source['pieces'],source['piece_pixel_masks'],pixels):
        image=unpack(mask)
        for y,x in zip(*np.where(image)):
            key=p['bank'],int(image[y,x]);line=p['y']+int(y);color=int(words[y,x])
            if references.setdefault(key,{}).setdefault(line,color)!=color:raise ValueError('EVENT_SCHEDULE_SLOT_COLLISION')
    for row in source['trace'][1:]:
        for e in row['updates']:
            i=len(events);events.append(dict(e,line=row['scanline']))
            by_slot.setdefault((e['bank'],e['slot']),[]).append(i)
    model=cp_model.CpModel();times=[];flags={};bounds=[]
    for i,e in enumerate(events):
        key=e['bank'],e['slot'];indices=by_slot[key];position=indices.index(i)
        previous=events[indices[position-1]]['line']if position else 0
        following=events[indices[position+1]]['line']if position+1<len(indices)else height
        refs=references.get(key,{})
        last_old=max((y for y in refs if previous<=y<e['line']),default=0)
        first_new=min((y for y in refs if e['line']<=y<following),default=following-1)
        lo=max(1,last_old+1,first_new-lookahead);hi=first_new
        if not lo<=e['line']<=hi:raise ValueError('EVENT_SCHEDULE_INPUT_LOOKAHEAD')
        t=model.new_int_var(lo,hi,f'loadTime{i}');times.append(t);bounds.append([lo,hi]);model.add_hint(t,e['line'])
        selections=[]
        for y in range(lo,hi+1):
            flag=model.new_bool_var(f'loadAt{i}_{y}');model.add(t==y).only_enforce_if(flag)
            model.add(t!=y).only_enforce_if(flag.Not());model.add_hint(flag,int(y==e['line']));selections.append(flag)
            flags.setdefault((y,e['bank']),[]).append((15*e['bank']+e['slot']-1,flag))
        model.add_exactly_one(selections)
    for indices in by_slot.values():
        for a,b in zip(indices,indices[1:]):model.add(times[a]<times[b])
    # A slot can have several candidate loads on a line, but ordering permits
    # only one. Merge their flags before passing fixed addresses to coverage.
    merged={}
    for key,values in flags.items():
        slots={}
        for slot,flag in values:slots.setdefault(slot,[]).append(flag)
        merged[key]=[]
        for slot,choices in slots.items():
            flag=model.new_bool_var(f'dirty{key}_{slot}');model.add_max_equality(flag,choices);merged[key].append((slot,flag))
    _,peak=constrain_fixed_addresses(model,merged,height,4,window)
    model.minimize(peak)
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit;solver.parameters.num_search_workers=8
    started=time.monotonic();status=solver.solve(model)
    report=dict(schema='BYOR_FIXED_INDEX_EVENT_TIME_SCHEDULE_V1',solver_status=solver.status_name(status),solver_seconds=time.monotonic()-started,event_count=len(events),model_variables=len(model.proto.variables),model_constraints=len(model.proto.constraints),window_master_clocks=window,lookahead_lines=lookahead,restricted_model_peak_span_lower_bound=max(0,solver.best_objective_bound-40),fixed_initial_palette=True,fixed_per_slot_event_sequence=True,event_removal_and_slot_relocation_not_modeled=True,fixed_pixel_indices=True,fixed_piece_bank_assignment=True,universal_raster_rejected=False,native_timing_admitted=False,no_color_reduction=True)
    if status not in(cp_model.FEASIBLE,cp_model.OPTIMAL):return report
    result=shift(source,lookahead=lookahead,iterations=0,event_lines=[solver.value(t)for t in times])
    if result['physical_slot_layout']['peak_prepared_commit_span']>=window:raise AssertionError('EVENT_SCHEDULE_PHYSICAL_WINDOW_REPLAY')
    report['retimed_events']=[dict(bank=e['bank'],slot=e['slot'],color=e['color'],from_scanline=e['line'],to_scanline=solver.value(t))for e,t in zip(events,times)if e['line']!=solver.value(t)]
    report.update(peak_prepared_commit_span=result['physical_slot_layout']['peak_prepared_commit_span'],pixel_color_identity_verified=True,all_packet_cgram_identities_verified=True)
    result['physical_event_schedule']=report
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--window',type=int,default=345);p.add_argument('--time-limit',type=float,default=60);p.add_argument('--lookahead',type=int,default=55)
    a=p.parse_args();result=optimize(json.loads(a.schedule.read_text()),a.window,a.time_limit,a.lookahead)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result.get('physical_event_schedule',result)))


if __name__=='__main__':main()
