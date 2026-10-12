"""Joint fixed word-bank repair and exact palette cache liveness.

Geometry masks have immutable OAM banks. The transfer bound grants favorable
physical endpoint slots; a witness still requires physical slot and native
timing admission. Failure covers only the supplied word-bank alternatives.
"""
import copy,hashlib,json
import numpy as np
from raster_global_bank_classes import rebuild_schedule
from raster_slot_greedy import demand,bank_groups
from raster_bank_residency import constrain_flow,favorable_span


def repair(source,initial,alternatives,time_limit=45,write_budget=21,window=345,lookahead=55,maximum_oam=128,maximum_sprites=32,maximum_tiles=34,residency_hint=None):
    from ortools.sat.python import cp_model
    if time_limit<=0 or not 0<=write_budget<=120 or window<1 or lookahead<0 or not 1<=maximum_oam<=128 or not 1<=maximum_sprites<=32 or not 1<=maximum_tiles<=34:raise ValueError('WORD_CACHE_REPAIR_DOMAIN')
    baseline=rebuild_schedule(source,initial,lookahead)
    pieces=copy.deepcopy(source['pieces']);domains=[]
    for p,image in zip(pieces,demand(source)[2]):
        p['rows']={p['y']+y:sorted(set(map(int,row[row>=0])))for y,row in enumerate(image)if np.any(row>=0)}
        domains.append(tuple(b for b in next(g for g in bank_groups(source)if p['bank']in g)if b in p.get('allowed_banks',range(8))))
    if len(set(domains))!=1:raise ValueError('WORD_CACHE_REPAIR_UNIFORM_ELIGIBILITY_REQUIRED')
    allowed=domains[0];old={};uses={}
    for p,b in zip(initial['pieces'],initial['assignment']):
        for cs in p['rows'].values():
            for c in cs:
                if c in old and old[c]!=b:raise ValueError('WORD_CACHE_REPAIR_GLOBAL_WORD_BANK_REQUIRED')
                old[c]=b
    for i,p in enumerate(pieces):
        for y,cs in p['rows'].items():
            for c in cs:uses.setdefault(c,set()).add(y)
    if not uses:raise ValueError('WORD_CACHE_REPAIR_EMPTY')
    if any(c not in uses or not bs or any(type(b)is not int or b not in allowed for b in bs)for c,bs in alternatives.items()):raise ValueError('WORD_CACHE_REPAIR_ALTERNATIVES')
    choices={c:tuple(sorted(set(alternatives.get(c,[old[c]]))))for c in uses}
    first=min(y for lines in uses.values()for y in lines);last=max(y for lines in uses.values()for y in lines)
    hint=residency_hint or baseline
    if residency_hint is not None:
        if json.loads(json.dumps(hint['pieces']))!=json.loads(json.dumps(baseline['pieces']))or any(not np.array_equal(a,b)for a,b in zip(demand(hint)[2],demand(baseline)[2])):raise ValueError('WORD_CACHE_REPAIR_HINT_IDENTITY')
    hint_state={b:[None]*15 for b in range(8)};hint_sets=[]
    for row in hint['trace']:
        for e in row['updates']:hint_state[e['bank']][e['slot']-1]=e['color']
        hint_sets.append({b:set(c for c in cs if c is not None)for b,cs in hint_state.items()})
    model=cp_model.CpModel();banks={};resident={};writes={};row_resident={};row_writes={};masks={}
    for c,bs in choices.items():
        selected={b:model.new_bool_var(f'bank{c}_{b}')for b in bs};banks[c]=selected;model.add_exactly_one(list(selected.values()))
        for b,chosen in selected.items():
            model.add_hint(chosen,int(b==old[c]))
            for y in range(first,max(uses[c])+1):
                r=model.new_bool_var(f'r{c}_{b}_{y}');resident[c,b,y]=r;row_resident.setdefault((y,b),[]).append(r)
                model.add(r<=chosen)
                if y in uses[c]:model.add(r==chosen)
                model.add_hint(r,int(c in hint_sets[y][b]))
                if y==first:continue
                previous=resident[c,b,y-1]
                if not any(y<=t<=y+lookahead for t in uses[c]):model.add(r<=previous);continue
                w=model.new_bool_var(f'w{c}_{b}_{y}');writes[c,b,y]=w;row_writes.setdefault((y,b),[]).append(w)
                model.add(w>=r-previous);model.add(w<=r);model.add(w+previous<=1)
                model.add_hint(w,int(c in hint_sets[y][b]and c not in hint_sets[y-1][b]))
    for i,p in enumerate(pieces):
        colors={c for cs in p['rows'].values()for c in cs}
        for b in allowed:
            options=[banks[c][b]for c in colors if b in banks[c]]
            if not options:continue
            flag=model.new_bool_var(f'mask{i}_{b}');masks[i,b]=flag;model.add_max_equality(flag,options)
            model.add_hint(flag,int(any(old[c]==b for c in colors)))
    model.add(sum(masks.values())<=maximum_oam)
    for y in range(first,last+1):
        live=[(i,b,v)for(i,b),v in masks.items()if pieces[i]['y']<=y<pieces[i]['y']+pieces[i]['height']]
        model.add(sum(v for i,b,v in live)<=maximum_sprites)
        model.add(sum(v*(pieces[i]['width']//8)for i,b,v in live)<=maximum_tiles)
        for b in range(8):model.add(sum(row_resident.get((y,b),[]))<=15)
        if y==first:continue
        counts=[];active=[]
        for b in range(8):
            values=row_writes.get((y,b),[]);n=model.new_int_var(0,15,f'count{y}_{b}');model.add(n==sum(values));counts.append(n)
            flag=model.new_bool_var(f'active{y}_{b}');model.add(n>=flag);model.add(n<=15*flag);active.append(flag)
        model.add(sum(counts)<=write_budget);constrain_flow(model,counts,active,window,f'repair{y}')
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit;solver.parameters.num_search_workers=4
    solver.parameters.cp_model_probing_level=0;solver.parameters.use_sat_inprocessing=False;solver.parameters.stop_after_first_solution=True
    status=solver.solve(model)
    report=dict(schema='BYOR_JOINT_WORD_BANK_CACHE_REPAIR_V1',status='BOUNDED_WORD_BANK_CACHE_REPAIR_NO_CANDIDATE',solver_status=solver.status_name(status),solver_seconds=solver.wall_time,
        variables=len(model.proto.variables),constraints=len(model.proto.constraints),branches=solver.num_branches,conflicts=solver.num_conflicts,
        movable_words=sum(len(bs)>1 for bs in choices.values()),word_bank_choices={c:list(bs)for c,bs in choices.items()if len(bs)>1},write_budget=write_budget,lookahead=lookahead,window=window,
        maximum_oam=maximum_oam,maximum_sprites=maximum_sprites,maximum_tiles=maximum_tiles,whole_frame_word_bank_identity_restricted=True,
        physical_endpoint_slots_relaxed=True,physical_transfer_admitted=False,native_timing_admitted=False,universal_raster_rejected=False,no_color_reduction=True)
    if status not in(cp_model.OPTIMAL,cp_model.FEASIBLE):return report
    chosen={c:next(b for b,v in selected.items()if solver.value(v))for c,selected in banks.items()};expanded=[];assignment=[]
    for i,p in enumerate(pieces):
        for b in allowed:
            rows={y:[c for c in cs if chosen[c]==b]for y,cs in p['rows'].items()}
            if any(rows.values()):expanded.append(dict(p,rows=rows,source_piece=i));assignment.append(b)
    search=dict(status='JOINT_GLOBAL_BANK_MASK_WORD_IDENTITIES_PROVEN',pieces=expanded,assignment=assignment,pixel_word_identities_replayed=True)
    result=rebuild_schedule(source,search,lookahead)
    desired_rows={y:{b:set()for b in range(8)}for y in range(first,last+1)}
    for(c,b,y),v in resident.items():
        if solver.value(v):desired_rows[y][b].add(c)
    report.update(status='JOINT_WORD_BANK_CACHE_AND_OPERAND_IDENTITIES_PROVEN',changed_word_banks=sum(chosen[c]!=old[c]for c in chosen))
    return compile_cache_rows(result,desired_rows,lookahead,write_budget,window,report,'joint_word_cache_repair')


def compile_cache_rows(frame,desired_rows,lookahead,write_budget,window,report,report_key):
    """Materialize a cache witness, replaying pixels, writes and future uses."""
    result=copy.deepcopy(frame);required,uses,images=demand(result);height=len(result['trace'])
    result.pop('prepared_dma_packets',None)
    for key in('physical_slot_layout','physical_slot_refinement','optimistic_bank_order','compiled_transfer_descriptor_sha256'):
        if key in result:result['input_'+key]=result.pop(key)
    result['native_presentation_proven']=False
    active=[y for y,row in enumerate(required)if any(row)];first,last=min(active),max(active)
    if any(type(y)is not int or not first<=y<=last or set(row)!=set(range(8))or any(len(cs)>15 or any(type(c)is not int or c not in uses[b]for c in cs)for b,cs in row.items())for y,row in desired_rows.items()):raise ValueError('CACHE_WITNESS_ROW_DOMAIN')
    state={b:[None]*15 for b in range(8)};states=[];trace=[]
    latency=0
    for y in range(height):
        target=first if y==0 else y
        desired=desired_rows.get(target,{b:set()for b in range(8)})if y==0 or first<=y<=last else {b:set()for b in range(8)}
        before=copy.deepcopy(state);events=[]
        for b in range(8):
            for c in sorted(desired[b]-set(state[b])):
                slot=next(s for s,oldword in enumerate(state[b])if oldword not in desired[b])
                events.append(dict(bank=b,slot=slot+1,old=state[b][slot],color=c,kind='required'if c in required[y][b]else'prefetch'))
                if y:
                    future=[t-y for t in uses[b][c]if t>=y]
                    if not future:raise AssertionError('WORD_CACHE_REPAIR_DEAD_PREFETCH')
                    wait=min(future)
                    if wait>lookahead:raise AssertionError('WORD_CACHE_REPAIR_PREFETCH_LATENCY')
                    latency=max(latency,wait)
                state[b][slot]=c
        if any(not required[y][b].issubset(state[b])for b in range(8)):raise AssertionError('WORD_CACHE_REPAIR_ROW_RESIDENCY')
        if y and(len(events)>write_budget or favorable_span(events)>=window):raise AssertionError('WORD_CACHE_REPAIR_TRANSFER_REPLAY')
        trace.append(dict(scanline=y,resident_before=before,retained={b:[c for c in before[b]if c is not None and c in state[b]]for b in range(8)},updates=events,prefetched=[e for e in events if e['kind']=='prefetch'],evicted=[e['old']for e in events if e['old']is not None],colors_written=len(events),cgram_data_bytes=2*len(events),affected_banks=sorted({e['bank']for e in events})))
        states.append(copy.deepcopy(state))
    masks=[];indices=np.zeros((height,256),dtype=np.uint8)
    for p,image in zip(result['pieces'],images):
        indexed=np.zeros(image.shape,dtype=np.uint8)
        for ly,lx in zip(*np.where(image>=0)):
            y,x=p['y']+int(ly),p['x']+int(lx);indexed[ly,lx]=states[y][p['bank']].index(int(image[ly,lx]))+1
            indices[y,x]=128+16*p['bank']+indexed[ly,lx]
        flat=indexed.flatten();masks.append(dict(width=p['width'],height=p['height'],pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex()))
    report=copy.deepcopy(report);report.update(peak_scheduled_writes=max(len(r['updates'])for r in trace[1:]),peak_optimistic_span=max(favorable_span(r['updates'])for r in trace[1:]),independent_cache_and_partition_replay=True)
    result[report_key]=report
    result.update(trace=trace,piece_pixel_masks=masks,peak_scheduled_writes=report['peak_scheduled_writes'],peak_cgram_data_bytes=2*report['peak_scheduled_writes'],prepared_dma_window_master_clocks=window,prepared_dma_partition_bound_enforced=True,prepared_dma_window_is_optimistic_necessary_only=True,
        compiled_indices_sha256=hashlib.sha256(indices.tobytes()).hexdigest(),maximum_noninitial_prefetch_latency_lines=latency,noninitial_prefetch_lookahead_enforced=True,noninitial_prefetch_latency_replayed=True,
        lookahead_lines=lookahead,write_budget=write_budget,average_writes=float(np.mean([len(r['updates'])for r in trace[1:]])),worst_scanline=max(trace[1:],key=lambda r:len(r['updates']))['scanline'],
        schedule_latency_requirement=dict(maximum_noninitial_prefetch_lines=latency,initial_palette_may_preload_entire_frame=True))
    payload=dict(pieces=result['pieces'],masks=masks,trace=trace,color_math=result.get('color_math'),source_rgb555_sha256=result.get('source_rgb555_sha256'))
    if result.get('scanline_math_controls_source_bound'):payload.update(selected_modes=result['selected_modes'],windows=result['compiled_color_window_descriptors'])
    result['compiled_schedule_sha256']=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    from raster_presentation_identity import refresh_presentation_identity
    refresh_presentation_identity(result)
    if any(not np.array_equal(a,b)for a,b in zip(images,demand(result)[2])):raise AssertionError('WORD_CACHE_REPAIR_SOURCE_OPERAND_REPLAY')
    return result


def main():
    import argparse
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__)
    for name in('schedule','initial-search','alternatives','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--residency-hint',type=Path);parser.add_argument('--time-limit',type=float,default=45)
    parser.add_argument('--write-budget',type=int,default=21);parser.add_argument('--window',type=int,default=345);parser.add_argument('--lookahead',type=int,default=55)
    parser.add_argument('--maximum-oam',type=int,default=128);parser.add_argument('--maximum-sprites',type=int,default=32);parser.add_argument('--maximum-tiles',type=int,default=34)
    args=parser.parse_args()
    result=repair(json.loads(args.schedule.read_text()),json.loads(args.initial_search.read_text()),{int(c):bs for c,bs in json.loads(args.alternatives.read_text()).items()},args.time_limit,args.write_budget,args.window,args.lookahead,args.maximum_oam,args.maximum_sprites,args.maximum_tiles,json.loads(args.residency_hint.read_text())if args.residency_hint else None)
    args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result.get('joint_word_cache_repair',result)))


if __name__=='__main__':main()
