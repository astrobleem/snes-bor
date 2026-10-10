"""Bounded physical raster scheduling with eviction/reload between color uses.

Fixed pieces and banks are retained. No fixed lifetime grouping is imposed.
Every successful construction is independently replayed at CGRAM and pixel
level. Failure of this heuristic never rejects raster or admits native timing.
"""
import argparse,bisect,copy,hashlib,json,random
from pathlib import Path
import numpy as np
from raster_obj_compact import unpack


def partition(bounds,maximum_ranges=4):
    """Exact cheapest grouping of ordered physical dirty intervals."""
    bounds=sorted(bounds)
    if not bounds:return 0,[]
    best={(0,0):(0,[])}
    for end in range(1,len(bounds)+1):
        for count in range(1,min(end,maximum_ranges)+1):
            choices=[]
            for start in range(count-1,end):
                if(start,count-1)not in best:continue
                cost,groups=best[start,count-1];lo,hi=bounds[start][0],bounds[end-1][1]
                choices.append((cost+16*(hi-lo+1)+24,groups+[(lo,hi)]))
            if choices:best[end,count]=min(choices)
    cost,groups=min(best[len(bounds),count]for count in range(1,min(len(bounds),maximum_ranges)+1))
    return max(0,cost-40),groups


def demand(schedule):
    if schedule.get('status')!='JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN'or not schedule.get('compiled_pixel_identity_verified'):
        raise ValueError('GREEDY_VALIDATED_SOURCE_SCHEDULE_REQUIRED')
    height=len(schedule['trace']);state={b:[None]*15 for b in range(8)};original=[]
    for y,row in enumerate(schedule['trace']):
        if row['scanline']!=y or {int(b):v for b,v in row['resident_before'].items()}!=state:raise ValueError('GREEDY_SOURCE_TRACE_CONTINUITY')
        for e in row['updates']:
            if state[e['bank']][e['slot']-1]!=e['old']:raise ValueError('GREEDY_SOURCE_UPDATE_IDENTITY')
            state[e['bank']][e['slot']-1]=e['color']
        original.append(copy.deepcopy(state))
    if len(schedule['pieces'])!=len(schedule['piece_pixel_masks']):raise ValueError('GREEDY_PIECE_MASK_COUNT')
    required=[[set()for b in range(8)]for y in range(height)];pixels=[]
    for p,mask in zip(schedule['pieces'],schedule['piece_pixel_masks']):
        image=unpack(mask);colors=np.full(image.shape,-1,dtype=np.int32)
        if image.shape!=(p['height'],p['width'])or not 0<=p['bank']<8:raise ValueError('GREEDY_PIECE_DOMAIN')
        for ly,lx in zip(*np.where(image!=0)):
            y,x=int(p['y']+ly),int(p['x']+lx)
            if not 0<=y<height or not 0<=x<256:raise ValueError('GREEDY_VISIBLE_PIXEL_DOMAIN')
            color=original[y][p['bank']][int(image[ly,lx])-1]
            if color is None:raise ValueError('GREEDY_SOURCE_PIXEL_WITHOUT_RESIDENT_COLOR')
            colors[ly,lx]=color;required[y][p['bank']].add(color)
        pixels.append(colors)
    if any(len(colors)>15 for row in required for colors in row):raise ValueError('GREEDY_BANK_ROW_CAPACITY')
    uses=[{}for b in range(8)]
    for y,row in enumerate(required):
        for b,colors in enumerate(row):
            for c in colors:uses[b].setdefault(c,[]).append(y)
    return required,uses,pixels


def schedule_slots(schedule,window=356,lookahead=17,maximum_ranges=4,seed=0,beam=16,repack=False,permute_banks=False,global_beam=1):
    if not isinstance(lookahead,int)or lookahead<0 or window<1 or not 1<=maximum_ranges<=4 or beam<1 or global_beam<1:raise ValueError('GREEDY_SCHEDULER_DOMAIN')
    required,uses,pixel_colors=demand(schedule);height=len(required);rng=random.Random(seed)
    bank_mapping={b:b for b in range(8)}
    if permute_banks:
        schedule=copy.deepcopy(schedule)
        pools=[list(range(8))]if schedule.get('color_math','additive')=='precomposited'else[list(range(4)),list(range(4,8))]
        for pool in pools:
            shuffled=pool.copy();rng.shuffle(shuffled);bank_mapping.update(zip(pool,shuffled))
        inverse={v:k for k,v in bank_mapping.items()}
        required=[[row[inverse[b]]for b in range(8)]for row in required]
        uses=[uses[inverse[b]]for b in range(8)]
        for piece in schedule['pieces']:piece['bank']=bank_mapping[piece['bank']]
    def next_use(b,c,y):
        if c is None:return height+1
        lines=uses[b][c];i=bisect.bisect_left(lines,y)
        return lines[i]if i<len(lines)else height+1
    tie={(b,c):rng.random()for b in range(8)for c in sorted(uses[b])}
    state=[]
    for b in range(8):
        colors=sorted(uses[b],key=lambda c:(uses[b][c][0],tie[b,c]))[:15]
        colors.sort(key=lambda c:(uses[b][c][-1],tie[b,c]))
        values=colors+[None]*(15-len(colors))
        if seed%4==1 or seed%4==2 and b%2==0 or seed%4==3 and b%2==1:values.reverse()
        state.append(tuple(values))
    states=[copy.deepcopy(state)];packets=[dict(scanline=0,packets=[],prepared_commit_span=0)]
    initial_events=[dict(bank=b,slot=s+1,old=None,color=c,kind='required'if c in required[0][b]else'prefetch')for b in range(8)for s,c in enumerate(state[b])if c is not None]
    trace=[dict(scanline=0,resident_before={b:[None]*15 for b in range(8)},retained={b:[]for b in range(8)},evicted=[],prefetched=[e for e in initial_events if e['kind']=='prefetch'],updates=initial_events,colors_written=len(initial_events),cgram_data_bytes=2*len(initial_events),affected_banks=sorted({e['bank']for e in initial_events}))]
    if any(not required[0][b].issubset(state[b])for b in range(8)):raise AssertionError('GREEDY_INITIAL_ROW_DEMAND')
    physical=[0]*128
    for e in initial_events:physical[16*e['bank']+e['slot']]=e['color']
    latency=0;reloads=0;ever=[set(c for c in values if c is not None)for values in state]
    def options(b,y):
        old=state[b];need=required[y][b];future={c:next_use(b,c,y)for c in uses[b]}
        urgency={c:(lookahead+1-(t-y))**2 for c,t in future.items()if y<t<=y+lookahead}
        def score(values):return sum(w for c,w in urgency.items()if c not in values)
        choices={}
        if need.issubset(old):choices[old]=(score(old),None)
        missing=need-set(old)
        for lo in range(15):
            for hi in range(lo,15):
                outside=set(old[:lo]+old[hi+1:]);uncovered=need-outside
                if len(uncovered)>hi-lo+1:continue
                values=list(old)
                free=sorted((s for s in range(lo,hi+1)if values[s]not in need),key=lambda s:(-next_use(b,values[s],y),s))
                additions=sorted(missing,key=lambda c:(uses[b][c][-1],tie[b,c]))
                if len(free)<len(additions):continue
                for s,c in zip(free,additions):values[s]=c
                for prefetch in (False,True):
                    trial=list(values)
                    if prefetch:
                        for c in sorted(urgency,key=lambda c:(future[c],tie[b,c])):
                            if c in trial:continue
                            free=[s for s in range(lo,hi+1)if trial[s]not in need]
                            if not free:break
                            s=max(free,key=lambda s:(next_use(b,trial[s],y+1),-s))
                            if future[c]>=next_use(b,trial[s],y+1):continue
                            trial[s]=c
                    layouts=[tuple(trial)]
                    if repack:
                        # Rows are reindexed offline. A transferred interval may
                        # rearrange live colors without altering the fixed OAM bank.
                        # Leave distant unused residents fixed to bound prefetch.
                        slots=[s for s in range(lo,hi+1)if trial[s] is not None and next_use(b,trial[s],y)<=y+lookahead]
                        for key in (lambda c:(next_use(b,c,y),tie[b,c]),lambda c:(uses[b][c][-1],tie[b,c])):
                            ordered=sorted((trial[s]for s in slots),key=key)
                            for reverse in (False,True):
                                packed=list(trial)
                                for s,c in zip(slots,ordered[::-1]if reverse else ordered):packed[s]=c
                                layouts.append(tuple(packed))
                    for layout in layouts:
                        if not need.issubset(layout):raise AssertionError('GREEDY_OPTION_DROPS_CURRENT_DEMAND')
                        dirty=[s for s,(a,c)in enumerate(zip(old,layout))if a!=c]
                        bound=(16*b+min(dirty)+1,16*b+max(dirty)+1)if dirty else None
                        rank=score(layout)+(0 if bound is None else 5*(bound[1]-bound[0]+1)+8)
                        if layout not in choices or rank<choices[layout][0]:choices[layout]=(rank,bound)
        ranked=sorted(((rank,values,bound)for values,(rank,bound)in choices.items()),key=lambda v:(v[0],str(v[1])))
        # Keep a cheapest compulsory option as well as the urgency choices.
        cheap=min(ranked,key=lambda v:(0 if v[2]is None else v[2][1]-v[2][0]+1,v[0]))
        return list(dict.fromkeys([cheap,*ranked[:4]]))
    planned=None
    if global_beam>1:
        paths=[(0,[copy.deepcopy(state)])]
        for y in range(1,height):
            complete=[];cache={}
            for accumulated,history in paths:
                state=history[-1];frontier=[(0,[],[])]
                for b in range(8):
                    key=(b,tuple(state[b]))
                    if key not in cache:cache[key]=options(b,y)
                    expanded=[]
                    for rank,values,bounds in frontier:
                        for penalty,local,bound in cache[key]:
                            new_bounds=bounds+([bound]if bound else[])
                            if partition(new_bounds,maximum_ranges)[0]<window:expanded.append((rank+penalty,values+[local],new_bounds))
                    if not expanded:break
                    frontier=sorted(expanded,key=lambda v:(v[0],str(v[1])))[:beam]
                else:
                    complete.extend((accumulated+rank,history+[values])for rank,values,bounds in frontier)
            if not complete:
                return dict(schema='BYOR_GREEDY_PHYSICAL_RASTER_SCHEDULER_V1',status='BOUNDED_GREEDY_NO_CANDIDATE',failed_scanline=y,seed=seed,beam=beam,global_beam=global_beam,lookahead_lines=lookahead,window_master_clocks=window,universal_raster_rejected=False,native_timing_admitted=False,no_color_reduction=True)
            unique={}
            for rank,history in sorted(complete,key=lambda v:(v[0],str(v[1][-1]))):
                key=tuple(tuple(bank)for bank in history[-1])
                if key not in unique:unique[key]=(rank,history)
                if len(unique)>=global_beam:break
            paths=list(unique.values())
        planned=min(paths,key=lambda v:v[0])[1]
        state=planned[0]
    for y in range(1,height):
        before=copy.deepcopy(state);frontier=[(0,[],[])]
        if planned is None:
            for b in range(8):
                local_options=options(b,y)
                expanded=[]
                for rank,values,bounds in frontier:
                    for penalty,local,bound in local_options:
                        new_bounds=bounds+([bound]if bound else[]);span,groups=partition(new_bounds,maximum_ranges)
                        if span<window:expanded.append((rank+penalty,values+[local],new_bounds))
                if not expanded:
                    return dict(schema='BYOR_GREEDY_PHYSICAL_RASTER_SCHEDULER_V1',status='BOUNDED_GREEDY_NO_CANDIDATE',failed_scanline=y,failed_bank=b,seed=seed,beam=beam,lookahead_lines=lookahead,window_master_clocks=window,universal_raster_rejected=False,native_timing_admitted=False,no_color_reduction=True)
                ranked=sorted(expanded,key=lambda v:(v[0],str(v[1])))
                cheap=min(expanded,key=lambda v:(partition(v[2],maximum_ranges)[0],v[0]))
                frontier=ranked[:max(0,beam-1)]
                if cheap not in frontier:frontier.append(cheap)
        if planned is None:
            rank,state,bounds=min(frontier,key=lambda v:v[0])
        else:
            state=planned[y];bounds=[]
            for b in range(8):
                dirty=[s for s,(a,c)in enumerate(zip(before[b],state[b]))if a!=c]
                if dirty:bounds.append((16*b+min(dirty)+1,16*b+max(dirty)+1))
        span,groups=partition(bounds,maximum_ranges)
        events=[]
        for b in range(8):
            for s,(old,c)in enumerate(zip(before[b],state[b])):
                if old==c:continue
                if c is None:raise AssertionError('GREEDY_UNUSED_SLOT_WAS_WRITTEN')
                kind='required'if c in required[y][b]else'prefetch'
                lead=next_use(b,c,y)-y
                if not 0<=lead<=lookahead:raise AssertionError('GREEDY_PREFETCH_LATENCY')
                latency=max(latency,lead);reloads+=int(c in ever[b] and c not in before[b]);ever[b].add(c)
                events.append(dict(bank=b,slot=s+1,old=old,color=c,kind=kind))
        data_groups=[]
        for begin,end in groups:
            data=bytearray()
            for address in range(begin,end+1):
                b,s=divmod(address,16);c=0 if not s else state[b][s-1]
                data.extend((0 if c is None else c).to_bytes(2,'little'))
            data_groups.append(dict(cgram_word_address=128+begin,word_count=end-begin+1,data_hex=data.hex()))
            for i in range(end-begin+1):physical[begin+i]=int.from_bytes(data[2*i:2*i+2],'little')
        for b in range(8):
            if not required[y][b].issubset(state[b])or physical[16*b]!=0 or physical[16*b+1:16*b+16]!=[0 if c is None else c for c in state[b]]:raise AssertionError('GREEDY_CGRAM_STATE_REPLAY')
        trace.append(dict(scanline=y,resident_before={b:list(v)for b,v in enumerate(before)},retained={b:[c for c in before[b]if c is not None and c in state[b]]for b in range(8)},evicted=[e['old']for e in events if e['old']is not None],prefetched=[e for e in events if e['kind']=='prefetch'],updates=events,colors_written=len(events),cgram_data_bytes=2*len(events),affected_banks=sorted({e['bank']for e in events})))
        states.append(copy.deepcopy(state));packets.append(dict(scanline=y,packets=data_groups,prepared_commit_span=span))
    images=[];indices=np.zeros((height,256),dtype=np.uint8)
    for p,colors in zip(schedule['pieces'],pixel_colors):
        image=np.zeros(colors.shape,dtype=np.uint8)
        for ly,lx in zip(*np.where(colors>=0)):
            y,x=int(p['y']+ly),int(p['x']+lx);slot=states[y][p['bank']].index(int(colors[ly,lx]))+1
            image[ly,lx]=slot;indices[y,x]=128+16*p['bank']+slot
            if states[y][p['bank']][slot-1]!=colors[ly,lx]:raise AssertionError('GREEDY_PIXEL_COLOR_REPLAY')
        flat=image.flatten();images.append(dict(width=p['width'],height=p['height'],packed_nibble_order='low then high',pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex()))
    result=copy.deepcopy(schedule);physical_report=dict(schema='BYOR_GREEDY_PHYSICAL_RASTER_SCHEDULER_V1',status='PHYSICAL_SLOT_PACKETS_AND_PIXEL_IDENTITIES_PROVEN',seed=seed,beam=beam,lookahead_lines=lookahead,window_master_clocks=window,peak_prepared_commit_span=max(p['prepared_commit_span']for p in packets),peak_ranges=max(len(p['packets'])for p in packets),maximum_noninitial_prefetch_latency_lines=latency,initial_palette_may_preload_entire_frame=True,color_reload_events=reloads,pixel_color_identity_verified=True,all_packet_cgram_identities_verified=True,fixed_piece_bank_permutation={b:b for b in range(8)},universal_raster_rejected=False,native_timing_admitted=False,no_color_reduction=True)
    physical_report.update(global_beam=global_beam,fixed_piece_bank_permutation=bank_mapping,interval_repacking_enabled=repack,peak_packet_data_bytes=max(sum(2*p['word_count']for p in row['packets'])for row in packets),peak_dma_chain_channels=max(max(0,2*len(row['packets'])-1)for row in packets))
    result.update(trace=trace,piece_pixel_masks=images,compiled_indices_sha256=hashlib.sha256(indices.tobytes()).hexdigest(),physical_slot_layout=physical_report,prepared_dma_packets=packets,peak_scheduled_writes=max(r['colors_written']for r in trace[1:]),peak_cgram_data_bytes=2*max(r['colors_written']for r in trace[1:]),average_writes=float(np.mean([r['colors_written']for r in trace[1:]])),worst_scanline=1+int(np.argmax([r['colors_written']for r in trace[1:]])),maximum_noninitial_prefetch_latency_lines=latency,noninitial_prefetch_lookahead_enforced=True,noninitial_prefetch_latency_replayed=True,initial_palette_may_preload_entire_frame=True)
    result.update(input_compiled_schedule_sha256=schedule.get('compiled_schedule_sha256'),
                  write_budget=None,lookahead_lines=lookahead,prepared_dma_window_master_clocks=window,
                  prepared_dma_partition_bound_enforced=True,prepared_dma_window_is_optimistic_necessary_only=True,
                  native_presentation_proven=False,schedule_latency_requirement=dict(maximum_noninitial_prefetch_lines=latency,initial_palette_may_preload_entire_frame=True))
    result['compiled_schedule_sha256']=hashlib.sha256(json.dumps(dict(pieces=result['pieces'],pixel_masks=images,trace=trace),sort_keys=True).encode()).hexdigest()
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--window',type=int,default=356);p.add_argument('--lookahead',type=int,default=17);p.add_argument('--maximum-ranges',type=int,default=4);p.add_argument('--seed',type=int,default=0);p.add_argument('--beam',type=int,default=16)
    p.add_argument('--repack',action='store_true');p.add_argument('--permute-banks',action='store_true');p.add_argument('--global-beam',type=int,default=1);a=p.parse_args()
    r=schedule_slots(json.loads(a.schedule.read_text()),a.window,a.lookahead,a.maximum_ranges,a.seed,a.beam,a.repack,a.permute_banks,a.global_beam);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r.get('physical_slot_layout',r)))


if __name__=='__main__':main()
