"""Lossless fixed-index slot-liveness prefetch repair of complete OBJ schedules.

Only invisible-slot loads are retimed. Pixel indices, geometry and OAM banks
stay fixed. Failure of this bounded greedy search never rejects raster.
"""
import argparse,copy,hashlib,json,time
from pathlib import Path
import numpy as np
from raster_obj_compact import unpack
from raster_slot_greedy import demand
from raster_physical_relabel import point_partition
from raster_slot_refine import verify_packets


def shift(source,lookahead=55,iterations=200,time_limit=30,target_window=345):
    if type(lookahead)is not int or lookahead<0 or type(iterations)is not int or iterations<0 or time_limit<=0 or target_window<1:
        raise ValueError('WRITE_SHIFT_DOMAIN')
    _,_,pixels=demand(source);verify_packets(source)
    height=len(source['trace']);references={};initial={};events=[]
    for p,mask,words in zip(source['pieces'],source['piece_pixel_masks'],pixels):
        image=unpack(mask)
        for y,x in zip(*np.where(image)):
            key=p['bank'],int(image[y,x]);line=p['y']+int(y);word=int(words[y,x])
            old=references.setdefault(key,{}).setdefault(line,word)
            if old!=word:raise ValueError('WRITE_SHIFT_SLOT_SOURCE_COLLISION')
    for row in source['trace']:
        for e in row['updates']:
            key=e['bank'],e['slot']
            if row['scanline']==0:initial[key]=e['color']
            else:events.append(dict(bank=e['bank'],slot=e['slot'],color=e['color'],line=row['scanline']))
    rows=[set()for _ in range(height)]
    for i,e in enumerate(events):rows[e['line']].add(i)
    def cost(line):return point_partition([16*events[i]['bank']+events[i]['slot']for i in rows[line]])[0]if line else 0
    costs=np.array([cost(y)for y in range(height)],dtype=np.int64)
    def score(v):return(int(v.max()),int(np.maximum(v-target_window+1,0).sum()),int(v.sum()))
    initial_score=score(costs);started=time.monotonic();moves=[]
    for _ in range(iterations):
        if time.monotonic()-started>=time_limit or score(costs)[0]<target_window:break
        before=score(costs);best=None
        critical=[y for y in range(1,height)if costs[y]>=target_window]
        for line in sorted(critical,key=lambda y:-costs[y]):
            for i in sorted(rows[line]):
                e=events[i];key=e['bank'],e['slot'];refs=references.get(key,{})
                previous=max((v['line']for j,v in enumerate(events)if j!=i and(v['bank'],v['slot'])==key and v['line']<line),default=0)
                last_ref=max((y for y in refs if y<line),default=-1)
                following=min((v['line']for j,v in enumerate(events)if j!=i and(v['bank'],v['slot'])==key and v['line']>line),default=height)
                first_use=min((y for y,c in refs.items()if line<=y<following and c==e['color']),default=following-1)
                earliest=max(previous+1,last_ref+1,first_use-lookahead)
                destinations=[y for y in range(earliest,min(first_use,following-1)+1)if y!=line]
                if previous==0 and last_ref<0:destinations.insert(0,0)
                for destination in destinations:
                    if time.monotonic()-started>=time_limit:break
                    rows[line].remove(i)
                    if destination:rows[destination].add(i)
                    candidate=costs.copy();candidate[line]=cost(line)
                    if destination:candidate[destination]=cost(destination)
                    value=score(candidate)
                    rows[line].add(i)
                    if destination:rows[destination].remove(i)
                    if value<before and(best is None or(value,destination,i)<best[:3]):best=(value,destination,i,candidate)
        if best is None:break
        value,destination,i,costs=best;e=events[i];old=e['line'];rows[old].remove(i)
        if destination:rows[destination].add(i)
        else:initial[e['bank'],e['slot']]=e['color']
        e['line']=destination
        moves.append(dict(bank=e['bank'],slot=e['slot'],color=e['color'],from_scanline=old,to_scanline=destination,score=list(value)))
    result=copy.deepcopy(source);state={b:[None]*15 for b in range(8)};trace=[];packets=[];physical=[0]*128;latency=0
    for y in range(height):
        before=copy.deepcopy(state);updates=[]
        values=[dict(bank=b,slot=s,color=c)for(b,s),c in sorted(initial.items())]if y==0 else [events[i]for i in sorted(rows[y])]
        for e in values:
            b,s,c=e['bank'],e['slot'],e['color'];refs=references.get((b,s),{})
            first_use=min((t for t,v in refs.items()if t>=y and v==c),default=height)
            kind='required'if refs.get(y)==c else'prefetch'
            if y and first_use<height:latency=max(latency,first_use-y)
            updates.append(dict(bank=b,slot=s,old=state[b][s-1],color=c,kind=kind));state[b][s-1]=c
        trace.append(dict(scanline=y,resident_before=before,updates=updates,retained={b:[c for c in before[b]if c is not None and c in state[b]]for b in range(8)},evicted=[e['old']for e in updates if e['old']is not None],prefetched=[e for e in updates if e['kind']=='prefetch'],colors_written=len(updates),cgram_data_bytes=2*len(updates),affected_banks=sorted({e['bank']for e in updates})))
        for(b,s),refs in references.items():
            if y in refs and state[b][s-1]!=refs[y]:raise AssertionError('WRITE_SHIFT_REQUIRED_SLOT_IDENTITY')
        if y==0:
            for b in range(8):physical[16*b+1:16*b+16]=[0 if c is None else c for c in state[b]]
        span,bounds=point_partition([16*e['bank']+e['slot']for e in updates]if y else[])
        groups=[]
        for lo,hi in bounds:
            data=b''.join((0 if a%16==0 or state[a//16][a%16-1]is None else state[a//16][a%16-1]).to_bytes(2,'little')for a in range(lo,hi+1))
            groups.append(dict(cgram_word_address=128+lo,word_count=hi-lo+1,data_hex=data.hex()))
        packets.append(dict(scanline=y,packets=groups,prepared_commit_span=span))
    if score(np.array([r['prepared_commit_span']for r in packets]))!=score(costs):raise AssertionError('WRITE_SHIFT_COST_REPLAY')
    if latency>lookahead:raise ValueError('WRITE_SHIFT_INPUT_PREFETCH_LATENCY_EXCEEDS_BOUND')
    for key in('physical_slot_refinement','bank_residency'):
        if key in result:result['input_'+key]=result.pop(key)
    report=dict(schema='BYOR_FIXED_INDEX_SLOT_LIVENESS_PREFETCH_V1',status='PHYSICAL_SLOT_PACKETS_AND_PIXEL_IDENTITIES_PROVEN',initial_score=list(initial_score),final_score=list(score(costs)),moves=moves,seconds=time.monotonic()-started,lookahead_lines=lookahead,maximum_noninitial_prefetch_latency_lines=latency,initial_palette_may_preload_entire_frame=True,fixed_pixel_indices=True,fixed_piece_bank_assignment=True,target_window_met_by_all_packets=score(costs)[0]<target_window,peak_prepared_commit_span=score(costs)[0],pixel_color_identity_verified=True,all_packet_cgram_identities_verified=True,native_timing_admitted=False,universal_raster_rejected=False,no_color_reduction=True)
    result.update(trace=trace,prepared_dma_packets=packets,physical_slot_layout=report,native_presentation_proven=False,peak_scheduled_writes=max(len(r['updates'])for r in trace[1:]),peak_cgram_data_bytes=max(r['cgram_data_bytes']for r in trace[1:]),average_writes=float(np.mean([r['colors_written']for r in trace[1:]])),worst_scanline=max(range(1,height),key=lambda y:len(trace[y]['updates'])),maximum_noninitial_prefetch_latency_lines=latency)
    result['maximum_noninitial_prefetch_latency_lines']=latency
    result['schedule_latency_requirement']=dict(maximum_noninitial_prefetch_lines=latency,initial_palette_may_preload_entire_frame=True)
    payload=dict(pieces=result['pieces'],pixel_masks=result['piece_pixel_masks'],trace=trace)
    if result.get('scanline_math_controls_source_bound'):payload.update(selected_modes=result['selected_modes'],compiled_color_window_descriptors=result['compiled_color_window_descriptors'])
    result['compiled_schedule_sha256']=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    result['compiled_transfer_descriptor_sha256']=hashlib.sha256(json.dumps(packets,sort_keys=True).encode()).hexdigest()
    verify_packets(result)
    if any(not np.array_equal(a,b)for a,b in zip(pixels,demand(result)[2])):raise AssertionError('WRITE_SHIFT_SOURCE_PIXEL_REPLAY')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--lookahead',type=int,default=55);p.add_argument('--iterations',type=int,default=200);p.add_argument('--time-limit',type=float,default=30);p.add_argument('--target-window',type=int,default=345)
    a=p.parse_args();result=shift(json.loads(a.schedule.read_text()),a.lookahead,a.iterations,a.time_limit,a.target_window);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['physical_slot_layout']))


if __name__=='__main__':main()
