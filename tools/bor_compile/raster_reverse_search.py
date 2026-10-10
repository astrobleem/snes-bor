"""Construct opposite-direction cache candidates, then replay forward time.

Reverse search is a heuristic only. Forward prefetch and physical DMA costs
are recomputed; a reverse-time fit never grants native or forward admission.
"""
import argparse,copy,hashlib,json
from pathlib import Path
import numpy as np
from raster_obj_compact import unpack
from raster_slot_greedy import demand,partition,schedule_slots


def mirror(schedule):
    demand(schedule)
    result=copy.deepcopy(schedule);height=len(schedule['trace']);state={b:[None]*15 for b in range(8)};states=[]
    for row in schedule['trace']:
        for e in row['updates']:state[e['bank']][e['slot']-1]=e['color']
        states.append(copy.deepcopy(state))
    before={b:[None]*15 for b in range(8)};trace=[]
    for y,state in enumerate(reversed(states)):
        events=[dict(bank=b,slot=s+1,old=before[b][s],color=c)for b in range(8)for s,c in enumerate(state[b])if c!=before[b][s]]
        trace.append(dict(scanline=y,resident_before=copy.deepcopy(before),updates=events));before=state
    for p,mask in zip(result['pieces'],result['piece_pixel_masks']):
        p['y']=height-p['y']-p['height']
        image=unpack(mask)[::-1];flat=image.flatten()
        mask['pixels_hex']=(flat[::2]|flat[1::2]<<4).tobytes().hex()
    result['trace']=trace
    return result


def forward_candidate(original,backward,window=356,lookahead=17,maximum_ranges=4):
    # Restore original geometry, retaining the backwards search's physical indices.
    candidate=mirror(backward)
    if candidate['pieces']!=original['pieces']:raise AssertionError('REVERSE_FIXED_PIECE_BANK_GEOMETRY')
    expected,_,source_pixels=demand(original);height=len(expected)
    target={b:[None]*15 for b in range(8)};targets=[]
    for row in candidate['trace']:
        for e in row['updates']:target[e['bank']][e['slot']-1]=e['color']
        targets.append(copy.deepcopy(target))
    used={}
    for p,mask,colors in zip(candidate['pieces'],candidate['piece_pixel_masks'],source_pixels):
        image=unpack(mask)
        for ly,lx in zip(*np.where(image!=0)):
            y=int(p['y']+ly);s=int(image[ly,lx])-1;b=p['bank'];c=int(colors[ly,lx])
            if targets[y][b][s]!=c:raise AssertionError('REVERSE_TARGET_PIXEL_IDENTITY')
            used.setdefault((b,s),{})[y]=c
    # Fold each slot's first actual pixel use into VBlank. Subsequent phases
    # may write only within lookahead, after the previous phase ends.
    writes={};initial={b:[None]*15 for b in range(8)}
    for (b,s),lines in used.items():
        starts=[0]+[y for y in range(1,height)if targets[y][b][s]!=targets[y-1][b][s]]
        first=True
        for begin,end in zip(starts,starts[1:]+[height]):
            uses=[y for y in lines if begin<=y<end]
            if not uses:continue
            color=targets[begin][b][s]
            if color is None:raise AssertionError('REVERSE_USED_EMPTY_SLOT')
            if first:initial[b][s]=color;first=False
            else:writes.setdefault(max(begin,min(uses)-lookahead),[]).append((b,s,color))
    state={b:[None]*15 for b in range(8)};physical=[0]*128;states=[];trace=[];packets=[];latency=0
    for y in range(height):
        before=copy.deepcopy(state);events=[]
        values=[(b,s,c)for b in range(8)for s,c in enumerate(initial[b])if c is not None]if y==0 else writes.get(y,[])
        for b,s,c in values:
            if state[b][s]==c:continue
            old=state[b][s];state[b][s]=c
            lead=min(t-y for t,value in used[b,s].items()if t>=y and value==c)
            if y and lead>lookahead:raise AssertionError('REVERSE_FORWARD_PREFETCH_BOUND')
            if y:latency=max(latency,lead)
            events.append(dict(bank=b,slot=s+1,old=old,color=c,kind='required'if c in expected[y][b]else'prefetch'))
        if y==0:
            for e in events:physical[16*e['bank']+e['slot']]=e['color']
            span=0;groups=[]
        else:span,groups=partition([(16*e['bank']+e['slot'],16*e['bank']+e['slot'])for e in events],maximum_ranges)
        data_groups=[]
        for begin,end in groups:
            data=bytearray()
            for address in range(begin,end+1):
                b,s=divmod(address,16);c=0 if not s else state[b][s-1]
                data.extend((0 if c is None else c).to_bytes(2,'little'))
            data_groups.append(dict(cgram_word_address=128+begin,word_count=end-begin+1,data_hex=data.hex()))
            for i in range(end-begin+1):physical[begin+i]=int.from_bytes(data[2*i:2*i+2],'little')
        for b in range(8):
            if physical[16*b]!=0 or physical[16*b+1:16*b+16]!=[0 if c is None else c for c in state[b]]:raise AssertionError('REVERSE_CGRAM_REPLAY')
        for (b,s),lines in used.items():
            if y in lines and state[b][s]!=lines[y]:raise AssertionError('REVERSE_FORWARD_PIXEL_REPLAY')
        trace.append(dict(scanline=y,resident_before=before,retained={b:[c for c in before[b]if c is not None and c in state[b]]for b in range(8)},evicted=[e['old']for e in events if e['old']is not None],prefetched=[e for e in events if e['kind']=='prefetch'],updates=events,colors_written=len(events),cgram_data_bytes=2*len(events),affected_banks=sorted({e['bank']for e in events})))
        packets.append(dict(scanline=y,packets=data_groups,prepared_commit_span=span));states.append(copy.deepcopy(state))
    peak=max(p['prepared_commit_span']for p in packets)
    report=dict(schema='BYOR_REVERSE_CACHE_FORWARD_REPLAY_V1',status='PHYSICAL_SLOT_PACKETS_AND_PIXEL_IDENTITIES_PROVEN'if peak<window else'FORWARD_PHYSICAL_PACKET_WINDOW_EXCEEDED',peak_prepared_commit_span=peak,window_master_clocks=window,lookahead_lines=lookahead,maximum_noninitial_prefetch_latency_lines=latency,peak_ranges=max(len(r['packets'])for r in packets),pixel_color_identity_verified=True,all_packet_cgram_identities_verified=True,fixed_piece_bank_permutation={b:b for b in range(8)},initial_palette_may_preload_entire_frame=True,universal_raster_rejected=False,native_timing_admitted=False,no_color_reduction=True)
    result=copy.deepcopy(original);result.update(trace=trace,piece_pixel_masks=candidate['piece_pixel_masks'],prepared_dma_packets=packets,physical_slot_layout=report,peak_scheduled_writes=max(r['colors_written']for r in trace[1:]),peak_cgram_data_bytes=max(r['cgram_data_bytes']for r in trace[1:]),average_writes=float(np.mean([r['colors_written']for r in trace[1:]])),worst_scanline=1+int(np.argmax([r['colors_written']for r in trace[1:]])),native_presentation_proven=False)
    result.update(write_budget=None,lookahead_lines=lookahead,prepared_dma_window_master_clocks=window,
        prepared_dma_partition_bound_enforced=peak<window,prepared_dma_window_is_optimistic_necessary_only=True,
        maximum_noninitial_prefetch_latency_lines=latency,noninitial_prefetch_lookahead_enforced=True,
        noninitial_prefetch_latency_replayed=True,
        schedule_latency_requirement=dict(maximum_noninitial_prefetch_lines=latency,initial_palette_may_preload_entire_frame=True))
    indices=np.zeros((height,256),dtype=np.uint8)
    for p,mask in zip(result['pieces'],result['piece_pixel_masks']):
        image=unpack(mask)
        for ly,lx in zip(*np.where(image!=0)):
            indices[p['y']+ly,p['x']+lx]=128+16*p['bank']+int(image[ly,lx])
    result['compiled_indices_sha256']=hashlib.sha256(indices.tobytes()).hexdigest()
    result['compiled_schedule_sha256']=hashlib.sha256(json.dumps(dict(pieces=result['pieces'],pixel_masks=result['piece_pixel_masks'],trace=trace),sort_keys=True).encode()).hexdigest()
    return result


def search(schedule,window=356,lookahead=17,maximum_ranges=4,seed=0,beam=16,repack=False,global_beam=1):
    backward=schedule_slots(mirror(schedule),window,lookahead,maximum_ranges,seed,beam,repack,False,global_beam)
    if backward.get('status')=='BOUNDED_GREEDY_NO_CANDIDATE':
        backward['search_time_direction']='reverse';return backward
    result=forward_candidate(schedule,backward,window,lookahead,maximum_ranges)
    result['physical_slot_layout'].update(seed=seed,beam=beam,repack=repack,global_beam=global_beam)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--window',type=int,default=356);p.add_argument('--lookahead',type=int,default=17);p.add_argument('--maximum-ranges',type=int,default=4);p.add_argument('--seed',type=int,default=0);p.add_argument('--beam',type=int,default=16);p.add_argument('--repack',action='store_true')
    p.add_argument('--global-beam',type=int,default=1)
    a=p.parse_args();r=search(json.loads(a.schedule.read_text()),a.window,a.lookahead,a.maximum_ranges,a.seed,a.beam,a.repack,a.global_beam);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r.get('physical_slot_layout',r)))


if __name__=='__main__':main()
