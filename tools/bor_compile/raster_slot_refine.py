"""Bounded local refinement of validated physical raster palettes.

Every accepted state retains all source pixels and fixed OAM banks. Search
failure never rejects raster, and meeting an offline target is not native
timing admission. Only the best complete schedule and bounded trial metadata
are retained.
"""
import argparse,copy,json
from pathlib import Path
from raster_row_slot_permutations import optimize
from raster_slot_greedy import demand


def score(schedule):
    spans=[row['prepared_commit_span']for row in schedule['prepared_dma_packets']]
    return max(spans),sum(spans)


def verify_packets(schedule):
    rows=schedule['prepared_dma_packets']
    if len(rows)!=len(schedule['trace']):raise ValueError('SLOT_REFINEMENT_PACKET_HEIGHT')
    state=[[None]*15 for _ in range(8)];physical=[0]*128
    for y,(row,trace)in enumerate(zip(rows,schedule['trace'])):
        if row['scanline']!=y:raise ValueError('SLOT_REFINEMENT_PACKET_ORDER')
        for event in trace['updates']:state[event['bank']][event['slot']-1]=event['color']
        if y==0:
            for b in range(8):physical[16*b+1:16*b+16]=[0 if c is None else c for c in state[b]]
        for packet in row['packets']:
            lo=packet['cgram_word_address']-128;count=packet['word_count'];raw=bytes.fromhex(packet['data_hex'])
            if count<1 or lo<0 or lo+count>128 or len(raw)!=2*count:raise ValueError('SLOT_REFINEMENT_PACKET_DOMAIN')
            physical[lo:lo+count]=[int.from_bytes(raw[2*i:2*i+2],'little')for i in range(count)]
        if any(physical[16*b]!=0 or physical[16*b+1:16*b+16]!=[0 if c is None else c for c in state[b]]for b in range(8)):
            raise ValueError('SLOT_REFINEMENT_PACKET_IDENTITY')
        span=max(0,sum(16*p['word_count']+24 for p in row['packets'])-40)
        if span!=row['prepared_commit_span']:raise ValueError('SLOT_REFINEMENT_PACKET_SPAN')


def refine(source,hint,target_window=348,iterations=6,radius=6,time_limit=20,maximum_writes=None,search_strategy='portfolio',range_encoding='intervals',necessary_bank_window=None):
    if target_window<1 or iterations<1 or radius<1 or time_limit<=0:
        raise ValueError('SLOT_REFINEMENT_DOMAIN')
    if search_strategy not in('portfolio','lns')or range_encoding not in('intervals','coverage'):
        raise ValueError('SLOT_REFINEMENT_SEARCH_DOMAIN')
    required,_,pixels=demand(source);_,_,hint_pixels=demand(hint)
    import numpy as np
    if source['pieces']!=hint['pieces']or any(not np.array_equal(a,b)for a,b in zip(pixels,hint_pixels)):
        raise ValueError('SLOT_REFINEMENT_HINT_IDENTITY')
    if not hint.get('physical_slot_layout',{}).get('all_packet_cgram_identities_verified'):
        raise ValueError('SLOT_REFINEMENT_PHYSICAL_HINT_REQUIRED')
    verify_packets(hint)
    if necessary_bank_window is None:necessary_bank_window=hint['physical_slot_layout'].get('necessary_bank_window_master_clocks')
    if necessary_bank_window is not None:
        from raster_bank_residency import favorable_span
        if type(necessary_bank_window)is not int or necessary_bank_window<1:raise ValueError('SLOT_REFINEMENT_NECESSARY_BANK_DOMAIN')
        if any(favorable_span(row['updates'])>=necessary_bank_window for row in hint['trace'][1:]):raise ValueError('SLOT_REFINEMENT_HINT_NECESSARY_BANK_WINDOW')
    if maximum_writes is not None:
        if not 0<=maximum_writes<=120:raise ValueError('SLOT_REFINEMENT_WRITE_BUDGET_DOMAIN')
        if any(len(row['updates'])>maximum_writes for row in hint['trace'][1:]):
            raise ValueError('SLOT_REFINEMENT_HINT_WRITE_BUDGET')
    visible=[y for y,row in enumerate(required)if any(row)]
    first,last=min(visible),max(visible)
    best=copy.deepcopy(hint);trials=[];visited={}
    for iteration in range(iterations):
        if score(best)[0]<target_window:break
        ordered=sorted(best['prepared_dma_packets'],key=lambda row:(-row['prepared_commit_span'],visited.get(row['scanline'],0),row['scanline']))
        peak=ordered[0]['prepared_commit_span']
        candidates=[row for row in ordered if row['prepared_commit_span']==peak]
        row=min(candidates,key=lambda row:(visited.get(row['scanline'],0),row['scanline']))['scanline']
        visited[row]=visited.get(row,0)+1
        reach=radius+(visited[row]-1)*2
        interval=(max(first,row-reach),min(last,row+reach))
        before=score(best)
        result=optimize(source,max(target_window,before[0]+1),time_limit,True,best,interval,maximum_writes,search_strategy,range_encoding,necessary_bank_window=necessary_bank_window)
        report=result.get('physical_slot_layout',result)
        accepted=False;after=None
        if 'prepared_dma_packets'in result:
            verify_packets(result)
            if maximum_writes is not None and any(len(r['updates'])>maximum_writes for r in result['trace'][1:]):
                raise AssertionError('SLOT_REFINEMENT_GLOBAL_WRITE_BUDGET')
            if necessary_bank_window is not None and any(favorable_span(r['updates'])>=necessary_bank_window for r in result['trace'][1:]):raise AssertionError('SLOT_REFINEMENT_GLOBAL_NECESSARY_BANK_WINDOW')
            after=score(result)
            if after<before:best=result;accepted=True
        trial=dict(iteration=iteration,interval=list(interval),solver_status=report['solver_status'],
            solver_search_strategy=search_strategy,physical_range_encoding=range_encoding,
            solver_seconds=report['solver_seconds'],model_variables=report['solver_model_variables'],
            restricted_model_peak_span_lower_bound=report['peak_commit_span_lower_bound_for_this_restricted_model'],
            before=list(before),candidate=list(after)if after else None,accepted=accepted)
        trials.append(trial)
        print(json.dumps(trial),flush=True)
    best['physical_slot_refinement']=dict(schema='BYOR_BOUNDED_PHYSICAL_SLOT_REFINEMENT_V1',
        target_window_master_clocks=target_window,target_window_met_by_all_packets=score(best)[0]<target_window,
        complete_source_frame_pixel_identity_proven=True,universal_raster_rejected=False,
        native_timing_admitted=False,no_color_reduction=True,trials=trials)
    best['physical_slot_refinement']['maximum_physical_writes_per_transfer_row']=maximum_writes
    best['physical_slot_refinement']['full_frame_write_budget_verified']=maximum_writes is not None
    best['physical_slot_refinement']['necessary_bank_window_master_clocks']=necessary_bank_window
    best['physical_slot_refinement']['full_frame_necessary_bank_window_verified']=necessary_bank_window is not None
    best['native_presentation_proven']=False
    return best


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--schedule',type=Path,required=True);p.add_argument('--layout-hint',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--target-window',type=int,default=348)
    p.add_argument('--iterations',type=int,default=6);p.add_argument('--radius',type=int,default=6)
    p.add_argument('--time-limit',type=float,default=20)
    p.add_argument('--maximum-writes',type=int,help='Preserve a verified full-frame physical write cap during every local repair.')
    p.add_argument('--necessary-bank-window',type=int,help='Preserve an ideal bank partition bound for all actual changes; defaults to the hint bound when present.')
    p.add_argument('--search-strategy',choices=('portfolio','lns'),default='portfolio')
    p.add_argument('--range-encoding',choices=('intervals','coverage'),default='intervals')
    a=p.parse_args()
    result=refine(json.loads(a.schedule.read_text()),json.loads(a.layout_hint.read_text()),a.target_window,a.iterations,a.radius,a.time_limit,a.maximum_writes,a.search_strategy,a.range_encoding,a.necessary_bank_window)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['physical_slot_refinement']))


if __name__=='__main__':main()
