"""Bounded legal lifetime recoloring for lossless physical OBJ palette packing.

Single lifetime moves and paired exchanges retain fixed banks/write times.
All overlapping lifetimes occupy distinct slots. Search failure does not
reject raster; emitted words, bitplanes and packets are independently replayed.
"""
import argparse,copy,hashlib,json,math,random,time
from pathlib import Path
import numpy as np
from raster_obj_compact import unpack
from raster_slot_greedy import demand
from raster_slot_refine import verify_packets
from raster_physical_relabel import point_partition


def optimize(source,steps=100000,time_limit=30,seed=635,target_window=345,kempe_probability=0):
    if steps<0 or time_limit<=0 or target_window<1:raise ValueError('LIFETIME_RECOLOR_DOMAIN')
    if isinstance(kempe_probability,bool)or not isinstance(kempe_probability,(int,float))or not math.isfinite(kempe_probability)or not 0<=kempe_probability<=1:raise ValueError('LIFETIME_KEMPE_DOMAIN')
    required,_,pixels=demand(source);verify_packets(source);height=len(source['trace'])
    active=np.full((height,8,15),-1,dtype=np.int32);state=np.full((8,15),-1,dtype=np.int32);lifes=[]
    for row in source['trace']:
        y=row['scanline']
        for e in row['updates']:
            i=len(lifes);lifes.append(dict(bank=e['bank'],old_slot=e['slot']-1,color=e['color'],first=y,last=-1,first_use=height));state[e['bank'],e['slot']-1]=i
        active[y]=state
    pixel_lives=[]
    for p,mask in zip(source['pieces'],source['piece_pixel_masks']):
        image=unpack(mask);ids=np.full_like(image,-1,dtype=np.int32)
        for y,x in zip(*np.where(image)):
            line=int(p['y']+y);i=int(active[line,p['bank'],image[y,x]-1])
            if i<0:raise ValueError('LIFETIME_RECOLOR_UNINITIALIZED_PIXEL')
            ids[y,x]=i;lifes[i]['last']=max(lifes[i]['last'],line);lifes[i]['first_use']=min(lifes[i]['first_use'],line)
        pixel_lives.append(ids)
    used=[i for i,l in enumerate(lifes)if l['last']>=l['first']];mapping={old:new for new,old in enumerate(used)}
    lifes=[lifes[i]for i in used];n=len(lifes)
    if not n:raise ValueError('LIFETIME_RECOLOR_EMPTY')
    for ids in pixel_lives:
        for old in np.unique(ids[ids>=0]):ids[ids==old]=-(mapping[int(old)]+2)
        ids[ids<-1]=-ids[ids<-1]-2
    banks=np.array([l['bank']for l in lifes]);starts=np.array([l['first']for l in lifes]);ends=np.array([l['last']for l in lifes]);assignment=np.array([l['old_slot']for l in lifes],dtype=np.int16)
    conflicts=(banks[:,None]==banks[None,:])&(starts[:,None]<=ends[None,:])&(starts[None,:]<=ends[:,None]);np.fill_diagonal(conflicts,False)
    rows=[[i for i,l in enumerate(lifes)if l['first']==y]for y in range(1,height)];rows=[r for r in rows if r]
    width=max(map(len,rows),default=0)
    if not width:raise ValueError('LIFETIME_RECOLOR_NO_CHANGES')
    ids=np.zeros((len(rows),width),dtype=np.int32);valid=np.zeros_like(ids,dtype=bool)
    for y,row in enumerate(rows):ids[y,:len(row)]=row;valid[y,:len(row)]=True
    counts=valid.sum(axis=1)
    def costs(slots):
        addresses=np.where(valid,16*banks[ids]+slots[ids]+1,256);addresses.sort(axis=1)
        last=np.take_along_axis(addresses,(counts-1)[:,None],axis=1)[:,0];result=16*(last-addresses[:,0]+1)+24
        if width>1:
            gaps=addresses[:,1:]-addresses[:,:-1]-1;gaps=np.where(np.arange(width-1)[None,:]<counts[:,None]-1,gaps,0)
            savings=np.maximum(0,16*gaps-24);savings.sort(axis=1);result-=savings[:,-3:].sum(axis=1)
        return np.maximum(0,result-40)
    def score(v):return(int(v.max()),int(np.maximum(v-target_window+1,0).sum()),int(v.sum()))
    def energy(v):return v[0]*1000+v[1]*10+v[2]*.01
    current=initial=best=score(costs(assignment));best_assignment=assignment.copy();rng=random.Random(seed);started=time.monotonic();accepted=proposed=swaps=chains=max_chain=0
    for step in range(steps):
        if time.monotonic()-started>=time_limit or best[0]<target_window:break
        i=rng.randrange(n);old=int(assignment[i]);dest=rng.randrange(15)
        if dest==old:continue
        chain_move=kempe_probability and rng.random()<kempe_probability
        if chain_move:
            eligible=((assignment==old)|(assignment==dest))&(banks==banks[i])
            reached=np.zeros(n,dtype=bool);reached[i]=True;frontier=reached.copy()
            while frontier.any():
                following=np.any(conflicts[frontier],axis=0)&eligible&~reached
                reached|=following;frontier=following
            changed=np.where(reached)[0];saved=assignment[changed].copy()
            assignment[changed]=np.where(saved==old,dest,old)
        else:
            collisions=np.where(conflicts[i]&(assignment==dest))[0]
            if len(collisions)>1:continue
            j=int(collisions[0])if len(collisions)else None
            if j is not None and np.any(conflicts[j]&(assignment==old)&(np.arange(n)!=i)):continue
            changed=np.array([i]if j is None else[i,j]);saved=assignment[changed].copy()
            assignment[i]=dest
            if j is not None:assignment[j]=old
        proposed+=1;value=score(costs(assignment));temperature=3000*(.0001**(step/max(1,steps)))
        if value<current or rng.random()<math.exp(min(0,(energy(current)-energy(value))/temperature)):
            current=value;accepted+=1;swaps+=int(not chain_move and len(changed)==2);chains+=int(bool(chain_move))
            if chain_move:max_chain=max(max_chain,len(changed))
            if value<best:best=value;best_assignment=assignment.copy()
        else:
            assignment[changed]=saved
    assignment=best_assignment
    if np.any(conflicts&(assignment[:,None]==assignment[None,:])):raise AssertionError('LIFETIME_RECOLOR_OVERLAP')
    result=copy.deepcopy(source);palette=[[0]*15 for _ in range(8)];states=[];trace=[];packets=[];latency=0
    for y in range(height):
        before=copy.deepcopy(palette);events=[]
        for i,l in enumerate(lifes):
            if l['first']!=y:continue
            b,s,c=l['bank'],int(assignment[i]),l['color']
            if palette[b][s]!=c:
                events.append(dict(bank=b,slot=s+1,old=palette[b][s],color=c,kind='required'if c in required[y][b]else'prefetch'));palette[b][s]=c
                if y:latency=max(latency,l['first_use']-y)
        if y==0:events=[dict(bank=b,slot=s+1,old=None,color=palette[b][s],kind='initial')for b in range(8)for s in range(15)]
        states.append(copy.deepcopy(palette))
        trace.append(dict(scanline=y,resident_before={b:[None]*15 for b in range(8)}if y==0 else{b:before[b]for b in range(8)},updates=events,retained={b:[c for c in before[b]if c in palette[b]]for b in range(8)},evicted=[e['old']for e in events if e['old']is not None],prefetched=[e for e in events if e['kind']=='prefetch'],colors_written=len(events),cgram_data_bytes=2*len(events),affected_banks=sorted({e['bank']for e in events})))
        span,ranges=point_partition([16*e['bank']+e['slot']for e in events]if y else[])
        packets.append(dict(scanline=y,prepared_commit_span=span,packets=[dict(cgram_word_address=128+lo,word_count=hi-lo+1,data_hex=b''.join((0 if a%16==0 else palette[a//16][a%16-1]).to_bytes(2,'little')for a in range(lo,hi+1)).hex())for lo,hi in ranges]))
    masks=[];indices=np.zeros((height,256),dtype=np.uint8)
    for p,old,ids,words in zip(source['pieces'],source['piece_pixel_masks'],pixel_lives,pixels):
        image=np.zeros_like(ids,dtype=np.uint8)
        for y,x in zip(*np.where(ids>=0)):
            i=int(ids[y,x]);s=int(assignment[i]);line=int(p['y']+y)
            if states[line][p['bank']][s]!=int(words[y,x]):raise AssertionError('LIFETIME_RECOLOR_PIXEL_WORD')
            image[y,x]=s+1;indices[line,p['x']+x]=128+16*p['bank']+s+1
        flat=image.flatten();masks.append(dict(old,pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex()))
    actual=score(np.array([r['prepared_commit_span']for r in packets]));report=dict(schema='BYOR_LIFETIME_SLOT_RECOLOR_V1',status='PHYSICAL_SLOT_PACKETS_AND_PIXEL_IDENTITIES_PROVEN',initial_upper_score=list(initial),best_upper_score=list(best),actual_score=list(actual),peak_prepared_commit_span=actual[0],target_window_met_by_all_packets=actual[0]<target_window,seconds=time.monotonic()-started,lifetime_count=n,proposals=proposed,accepted=accepted,paired_exchanges=swaps,seed=seed,overlap_constraints_verified=True,write_times_fixed=True,fixed_piece_bank_assignment=True,pixel_color_identity_verified=True,all_packet_cgram_identities_verified=True,native_timing_admitted=False,universal_raster_rejected=False,no_color_reduction=True)
    if any(a>b for a,b in zip(actual,best)):raise AssertionError('LIFETIME_RECOLOR_ACTUAL_COST_UPPER_BOUND')
    report['maximum_noninitial_prefetch_latency_lines']=latency
    report.update(kempe_probability=kempe_probability,kempe_chain_exchanges=chains,maximum_accepted_kempe_component_size=max_chain)
    for key in('bank_residency','physical_slot_refinement'):
        if key in result:result['input_'+key]=result.pop(key)
    result.update(trace=trace,piece_pixel_masks=masks,prepared_dma_packets=packets,physical_slot_layout=report,native_presentation_proven=False,compiled_indices_sha256=hashlib.sha256(indices.tobytes()).hexdigest(),peak_scheduled_writes=max(len(r['updates'])for r in trace[1:]),peak_cgram_data_bytes=max(r['cgram_data_bytes']for r in trace[1:]),average_writes=float(np.mean([r['colors_written']for r in trace[1:]])))
    result['maximum_noninitial_prefetch_latency_lines']=latency
    result['schedule_latency_requirement']=dict(maximum_noninitial_prefetch_lines=latency,initial_palette_may_preload_entire_frame=True)
    result['worst_scanline']=max(range(1,height),key=lambda y:trace[y]['colors_written'])
    payload=dict(pieces=result['pieces'],pixel_masks=masks,trace=trace)
    if result.get('scanline_math_controls_source_bound'):payload.update(selected_modes=result['selected_modes'],compiled_color_window_descriptors=result['compiled_color_window_descriptors'])
    result['compiled_schedule_sha256']=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    result['compiled_transfer_descriptor_sha256']=hashlib.sha256(json.dumps(packets,sort_keys=True).encode()).hexdigest()
    verify_packets(result)
    if any(not np.array_equal(a,b)for a,b in zip(pixels,demand(result)[2])):raise AssertionError('LIFETIME_RECOLOR_SOURCE_REPLAY')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--steps',type=int,default=100000);p.add_argument('--time-limit',type=float,default=30);p.add_argument('--seed',type=int,default=635);p.add_argument('--target-window',type=int,default=345)
    p.add_argument('--kempe-probability',type=float,default=0,help='Swap connected two-slot lifetime components while preserving every overlap constraint.')
    a=p.parse_args();result=optimize(json.loads(a.schedule.read_text()),a.steps,a.time_limit,a.seed,a.target_window,a.kempe_probability);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['physical_slot_layout']))


if __name__=='__main__':main()
