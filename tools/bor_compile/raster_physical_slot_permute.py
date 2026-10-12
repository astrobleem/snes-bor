"""Search fixed opaque-slot permutations without changing any cache lifetime.

Every candidate retains fixed OAM banks and source RGB555 identity. A bounded
heuristic failure cannot reject raster presentation or admit native timing.
"""
import argparse,copy,hashlib,json,math,random,time
from pathlib import Path
import numpy as np
from raster_obj_compact import unpack
from raster_slot_greedy import demand
from raster_slot_refine import verify_packets
from raster_physical_relabel import point_partition


def permute(source,steps=50000,seed=618,time_limit=30,target_window=345):
    if type(steps)is not int or steps<0 or time_limit<=0 or target_window<1:
        raise ValueError('PHYSICAL_SLOT_PERMUTATION_DOMAIN')
    _,_,pixels=demand(source);verify_packets(source)
    rows=[row for row in source['trace'][1:]if row['updates']]
    if not rows:raise ValueError('PHYSICAL_SLOT_PERMUTATION_NO_CHANGES')
    maximum=max(len(row['updates'])for row in rows)
    banks=np.zeros((len(rows),maximum),dtype=np.int16)
    slots=np.zeros_like(banks);valid=np.zeros_like(banks,dtype=bool)
    for y,row in enumerate(rows):
        for i,e in enumerate(row['updates']):
            banks[y,i]=e['bank'];slots[y,i]=e['slot']-1;valid[y,i]=True
    counts=valid.sum(axis=1)
    def costs(mapping):
        addresses=np.where(valid,16*banks+mapping[banks,slots]+1,256)
        addresses.sort(axis=1)
        last=np.take_along_axis(addresses,(counts-1)[:,None],axis=1)[:,0]
        result=16*(last-addresses[:,0]+1)+24
        if maximum>1:
            gaps=addresses[:,1:]-addresses[:,:-1]-1
            gaps=np.where(np.arange(maximum-1)[None,:]<counts[:,None]-1,gaps,0)
            savings=np.maximum(0,16*gaps-24);savings.sort(axis=1)
            result-=savings[:,-3:].sum(axis=1)
        return np.maximum(0,result-40)
    def score(c):return(int(c.max()),int(np.maximum(c-target_window+1,0).sum()),int(c.sum()))
    def energy(v):return v[0]*1000+v[1]*10+v[2]*.01
    mapping=np.tile(np.arange(15,dtype=np.int16),(8,1))
    current=score(costs(mapping));initial=current;best=current;best_mapping=mapping.copy()
    rng=random.Random(seed);started=time.monotonic();accepted=sampled=0
    active=sorted({e['bank']for row in rows for e in row['updates']})
    for step in range(steps):
        if time.monotonic()-started>=time_limit or best[0]<target_window:break
        b=rng.choice(active);a,z=rng.sample(range(15),2)
        mapping[b,a],mapping[b,z]=mapping[b,z],mapping[b,a];sampled+=1
        candidate=score(costs(mapping));temperature=10000*(.0001**(step/max(1,steps)))
        if candidate<current or rng.random()<math.exp(min(0,(energy(current)-energy(candidate))/temperature)):
            current=candidate;accepted+=1
            if current<best:best=current;best_mapping=mapping.copy()
        else:mapping[b,a],mapping[b,z]=mapping[b,z],mapping[b,a]
    result=copy.deepcopy(source)
    def remap(b,values):
        output=[None]*15
        for s,c in enumerate(values):output[int(best_mapping[b,s])]=c
        return output
    for row in result['trace']:
        residents={}
        for key,values in row['resident_before'].items():
            b=int(key);residents[b]=remap(b,values)
        row['resident_before']=residents
        def event(e):return dict(e,slot=int(best_mapping[e['bank'],e['slot']-1])+1)
        row['updates']=[event(e)for e in row['updates']]
        if 'prefetched'in row:row['prefetched']=[event(e)for e in row['prefetched']]
    indices=np.zeros((len(result['trace']),256),dtype=np.uint8)
    for p,mask in zip(result['pieces'],result['piece_pixel_masks']):
        image=unpack(mask);occupied=image!=0
        image[occupied]=best_mapping[p['bank'],image[occupied]-1]+1
        flat=image.flatten();mask['pixels_hex']=(flat[::2]|flat[1::2]<<4).tobytes().hex()
        for y,x in zip(*np.where(occupied)):indices[p['y']+y,p['x']+x]=128+16*p['bank']+image[y,x]
    packets=[];state=[0]*128
    for row in result['trace']:
        for e in row['updates']:state[16*e['bank']+e['slot']]=e['color']
        points=[16*e['bank']+e['slot']for e in row['updates']]if row['scanline']else[]
        span,groups=point_partition(points)
        packets.append(dict(scanline=row['scanline'],prepared_commit_span=span,packets=[dict(cgram_word_address=128+lo,word_count=hi-lo+1,data_hex=b''.join(state[a].to_bytes(2,'little')for a in range(lo,hi+1)).hex())for lo,hi in groups]))
    actual=score(np.array([r['prepared_commit_span']for r in packets]))
    if actual!=best:raise AssertionError('PHYSICAL_SLOT_PERMUTATION_COST_REPLAY')
    result['prepared_dma_packets']=packets
    result.pop('physical_slot_refinement',None)
    result['physical_slot_layout']=dict(schema='BYOR_FIXED_PHYSICAL_SLOT_PERMUTATION_V1',status='PHYSICAL_SLOT_PACKETS_AND_PIXEL_IDENTITIES_PROVEN',initial_score=list(initial),final_score=list(best),seed=seed,steps_requested=steps,proposals_sampled=sampled,moves_accepted=accepted,seconds=time.monotonic()-started,opaque_slot_permutations=(best_mapping+1).tolist(),fixed_piece_bank_assignment=True,cache_lifetimes_and_write_times_unchanged=True,peak_prepared_commit_span=best[0],target_window_master_clocks=target_window,target_window_met_by_all_packets=best[0]<target_window,pixel_color_identity_verified=True,all_packet_cgram_identities_verified=True,native_timing_admitted=False,universal_raster_rejected=False,no_color_reduction=True)
    result['compiled_indices_sha256']=hashlib.sha256(indices.tobytes()).hexdigest()
    payload=dict(pieces=result['pieces'],pixel_masks=result['piece_pixel_masks'],trace=result['trace'])
    if result.get('scanline_math_controls_source_bound'):payload.update(selected_modes=result['selected_modes'],compiled_color_window_descriptors=result['compiled_color_window_descriptors'])
    result['compiled_schedule_sha256']=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    result['compiled_transfer_descriptor_sha256']=hashlib.sha256(json.dumps(packets,sort_keys=True).encode()).hexdigest()
    result['native_presentation_proven']=False
    verify_packets(result)
    if any(not np.array_equal(a,b)for a,b in zip(pixels,demand(result)[2])):raise AssertionError('PHYSICAL_SLOT_PERMUTATION_SOURCE_REPLAY')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--steps',type=int,default=50000);p.add_argument('--seed',type=int,default=618);p.add_argument('--time-limit',type=float,default=30);p.add_argument('--target-window',type=int,default=345)
    a=p.parse_args();result=permute(json.loads(a.schedule.read_text()),a.steps,a.seed,a.time_limit,a.target_window);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['physical_slot_layout']))


if __name__=='__main__':main()
