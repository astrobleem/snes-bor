"""Greedy row-boundary slot swaps with all live relocation writes charged.

Piece geometry and OAM banks remain fixed. Pixel indices after each boundary
are remapped offline and every RGB555 source word is independently replayed.
"""
import argparse,copy,hashlib,json,time,math,random
from pathlib import Path
import numpy as np
from raster_obj_compact import unpack
from raster_slot_greedy import demand
from raster_slot_refine import verify_packets
from raster_physical_relabel import point_partition


def reindex(source,time_limit=30,iterations=20,radius=3,target_window=345,anneal_steps=0,seed=630):
    if time_limit<=0 or iterations<1 or radius<0 or target_window<1 or anneal_steps<0:raise ValueError('SUFFIX_REINDEX_DOMAIN')
    required,uses,pixels=demand(source);verify_packets(source)
    height=len(source['trace']);state=[[None]*15 for _ in range(8)];states=[]
    for row in source['trace']:
        for e in row['updates']:state[e['bank']][e['slot']-1]=e['color']
        states.append([[0 if c is None else c for c in bank]for bank in state])
    states=np.array(states,dtype=np.int32);images=[unpack(m)for m in source['piece_pixel_masks']]
    addresses=np.arange(128,dtype=np.int16)
    def dirty(values):
        flags=np.zeros((height,128),dtype=bool)
        for b in range(8):flags[1:,16*b+1:16*b+16]=values[1:,b]!=values[:-1,b]
        return flags
    def costs(flags):
        points=np.where(flags,addresses,256);points.sort(axis=1);counts=flags.sum(axis=1)
        last=np.take_along_axis(points,np.maximum(counts-1,0)[:,None],axis=1)[:,0]
        cost=16*(last-points[:,0]+1)+24
        gaps=points[:,1:]-points[:,:-1]-1
        gaps=np.where(np.arange(127)[None,:]<counts[:,None]-1,gaps,0)
        savings=np.maximum(0,16*gaps-24);savings.sort(axis=1);cost-=savings[:,-3:].sum(axis=1)
        return np.where(counts,np.maximum(0,cost-40),0)
    def score(v):return(int(v.max()),int(np.maximum(v-target_window+1,0).sum()),int(v.sum()))
    flags=dirty(states);current=costs(flags);initial_score=score(current);started=time.monotonic();moves=[];proposals=0
    for _ in range(iterations):
        if time.monotonic()-started>=time_limit or score(current)[0]<target_window:break
        critical=np.where(current>=target_window)[0];boundaries={0}
        for y in critical:boundaries.update(range(max(1,int(y)-radius),int(y)+1))
        best=None;before=score(current)
        for boundary in sorted(boundaries):
            if time.monotonic()-started>=time_limit:break
            for b in range(8):
                if not any(flags[y,16*b+1:16*b+16].any()for y in critical if y>=boundary):continue
                for a in range(15):
                    for z in range(a+1,15):
                        if time.monotonic()-started>=time_limit:break
                        trial=flags.copy();trial[boundary:,16*b+a+1]=flags[boundary:,16*b+z+1];trial[boundary:,16*b+z+1]=flags[boundary:,16*b+a+1]
                        if boundary:
                            trial[boundary,16*b+a+1]=states[boundary,b,z]!=states[boundary-1,b,a]
                            trial[boundary,16*b+z+1]=states[boundary,b,a]!=states[boundary-1,b,z]
                        values=costs(trial);value=score(values);proposals+=1
                        if value<before and(best is None or(value,boundary,b,a,z)<best[:5]):best=(value,boundary,b,a,z,trial,values)
        if best is None:break
        value,boundary,b,a,z,flags,current=best
        temporary=states[boundary:,b,a].copy();states[boundary:,b,a]=states[boundary:,b,z];states[boundary:,b,z]=temporary
        for p,image in zip(source['pieces'],images):
            if p['bank']!=b:continue
            for y in range(max(0,boundary-p['y']),p['height']):
                row=image[y];old=row.copy();row[old==a+1]=z+1;row[old==z+1]=a+1
        moves.append(dict(scanline=boundary,bank=b,opaque_slots=[a+1,z+1],score=list(value)))
    # Keep only the best complete state. Temporary uphill moves carry their
    # live relocation writes exactly like greedy moves and cannot be emitted
    # unless the complete result improves the retained score.
    anneal_started=time.monotonic();anneal_proposals=0;anneal_accepted=0
    if anneal_steps:
        rng=random.Random(seed);best_score=score(current)
        best_states=states.copy();best_images=[v.copy()for v in images];best_moves=copy.deepcopy(moves)
        def energy(v):return v[0]*1000+v[1]*10+v[2]*.01
        for step in range(anneal_steps):
            if time.monotonic()-anneal_started>=time_limit or best_score[0]<target_window:break
            critical=np.where(current>=target_window)[0]
            if not len(critical):break
            line=int(rng.choice(critical));boundary=max(0,line-rng.randrange(radius+1))if rng.random()<.8 else 0
            dirty_banks=[b for b in range(8)if flags[line,16*b+1:16*b+16].any()]
            b=rng.choice(dirty_banks)if dirty_banks and rng.random()<.8 else rng.randrange(8)
            dirty_slots=np.where(flags[line,16*b+1:16*b+16])[0].tolist()
            a=rng.choice(dirty_slots)if dirty_slots and rng.random()<.8 else rng.randrange(15)
            z=rng.choice([s for s in range(15)if s!=a])
            trial=flags.copy();trial[boundary:,16*b+a+1]=flags[boundary:,16*b+z+1];trial[boundary:,16*b+z+1]=flags[boundary:,16*b+a+1]
            if boundary:
                trial[boundary,16*b+a+1]=states[boundary,b,z]!=states[boundary-1,b,a]
                trial[boundary,16*b+z+1]=states[boundary,b,a]!=states[boundary-1,b,z]
            values=costs(trial);value=score(values);anneal_proposals+=1
            temperature=2000*(.0001**(step/max(1,anneal_steps)))
            if value>=score(current)and rng.random()>=math.exp(min(0,(energy(score(current))-energy(value))/temperature)):continue
            flags,current=trial,values;anneal_accepted+=1
            temporary=states[boundary:,b,a].copy();states[boundary:,b,a]=states[boundary:,b,z];states[boundary:,b,z]=temporary
            for p,image in zip(source['pieces'],images):
                if p['bank']!=b:continue
                for y in range(max(0,boundary-p['y']),p['height']):
                    row=image[y];old=row.copy();row[old==a+1]=z+1;row[old==z+1]=a+1
            moves.append(dict(scanline=boundary,bank=b,opaque_slots=[a+1,z+1],score=list(value)))
            if value<best_score:
                best_score=value;best_states=states.copy();best_images=[v.copy()for v in images];best_moves=copy.deepcopy(moves)
        states,images,moves=best_states,best_images,best_moves;flags=dirty(states);current=costs(flags)
    result=copy.deepcopy(source);trace=[];packets=[];before={b:[None]*15 for b in range(8)};latency=0
    for y,values in enumerate(states):
        state={b:list(map(int,values[b]))for b in range(8)};events=[]
        for b in range(8):
            for s,c in enumerate(state[b]):
                if c==before[b][s]:continue
                kind='required'if c in required[y][b]else'slot_move'if c in before[b]else'prefetch'
                if y and kind=='prefetch' and c in uses[b]:
                    future=[t-y for t in uses[b][c]if t>=y]
                    if future:latency=max(latency,min(future))
                events.append(dict(bank=b,slot=s+1,old=before[b][s],color=c,kind=kind))
        trace.append(dict(scanline=y,resident_before=copy.deepcopy(before),updates=events,retained={b:[c for c in before[b]if c is not None and c in state[b]]for b in range(8)},evicted=[e['old']for e in events if e['old']is not None],prefetched=[e for e in events if e['kind']=='prefetch'],slot_moves=[e for e in events if e['kind']=='slot_move'],colors_written=len(events),cgram_data_bytes=2*len(events),affected_banks=sorted({e['bank']for e in events})))
        span,bounds=point_partition([16*e['bank']+e['slot']for e in events]if y else[])
        packets.append(dict(scanline=y,prepared_commit_span=span,packets=[dict(cgram_word_address=128+lo,word_count=hi-lo+1,data_hex=b''.join((0 if address%16==0 else state[address//16][address%16-1]).to_bytes(2,'little')for address in range(lo,hi+1)).hex())for lo,hi in bounds]))
        before=state
    if score(np.array([r['prepared_commit_span']for r in packets]))!=score(current):raise AssertionError('SUFFIX_REINDEX_COST_REPLAY')
    masks=[];indices=np.zeros((height,256),dtype=np.uint8)
    for p,old,image in zip(source['pieces'],source['piece_pixel_masks'],images):
        flat=image.flatten();masks.append(dict(old,pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex()))
        for y,x in zip(*np.where(image)):indices[p['y']+y,p['x']+x]=128+16*p['bank']+image[y,x]
    for key in('bank_residency','physical_slot_refinement'):
        if key in result:result['input_'+key]=result.pop(key)
    report=dict(schema='BYOR_ROW_BOUNDARY_SLOT_REINDEX_V1',status='PHYSICAL_SLOT_PACKETS_AND_PIXEL_IDENTITIES_PROVEN',initial_score=list(initial_score),final_score=list(score(current)),moves=moves,proposals=proposals,seconds=time.monotonic()-started,all_live_slot_relocation_writes_charged=True,fixed_piece_bank_assignment=True,source_geometry_unchanged=True,maximum_noninitial_prefetch_latency_lines=latency,initial_palette_may_preload_entire_frame=True,peak_prepared_commit_span=score(current)[0],target_window_met_by_all_packets=score(current)[0]<target_window,pixel_color_identity_verified=True,all_packet_cgram_identities_verified=True,native_timing_admitted=False,universal_raster_rejected=False,no_color_reduction=True)
    report.update(anneal_steps_requested=anneal_steps,anneal_proposals=anneal_proposals,anneal_accepted=anneal_accepted,anneal_seed=seed,best_complete_state_retained=True)
    result.update(trace=trace,piece_pixel_masks=masks,prepared_dma_packets=packets,physical_slot_layout=report,native_presentation_proven=False,compiled_indices_sha256=hashlib.sha256(indices.tobytes()).hexdigest(),peak_scheduled_writes=max(r['colors_written']for r in trace[1:]),peak_cgram_data_bytes=max(r['cgram_data_bytes']for r in trace[1:]),average_writes=float(np.mean([r['colors_written']for r in trace[1:]])),worst_scanline=max(range(1,height),key=lambda y:trace[y]['colors_written']))
    result['maximum_noninitial_prefetch_latency_lines']=latency
    result['schedule_latency_requirement']=dict(maximum_noninitial_prefetch_lines=latency,initial_palette_may_preload_entire_frame=True)
    payload=dict(pieces=result['pieces'],pixel_masks=masks,trace=trace)
    if result.get('scanline_math_controls_source_bound'):payload.update(selected_modes=result['selected_modes'],compiled_color_window_descriptors=result['compiled_color_window_descriptors'])
    result['compiled_schedule_sha256']=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest();result['compiled_transfer_descriptor_sha256']=hashlib.sha256(json.dumps(packets,sort_keys=True).encode()).hexdigest()
    verify_packets(result)
    if any(not np.array_equal(a,b)for a,b in zip(pixels,demand(result)[2])):raise AssertionError('SUFFIX_REINDEX_SOURCE_PIXEL_REPLAY')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--time-limit',type=float,default=30);p.add_argument('--iterations',type=int,default=20);p.add_argument('--radius',type=int,default=3);p.add_argument('--target-window',type=int,default=345)
    p.add_argument('--anneal-steps',type=int,default=0);p.add_argument('--seed',type=int,default=630)
    a=p.parse_args();result=reindex(json.loads(a.schedule.read_text()),a.time_limit,a.iterations,a.radius,a.target_window,a.anneal_steps,a.seed);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result['physical_slot_layout'].items()if k!='moves'}))


if __name__=='__main__':main()
