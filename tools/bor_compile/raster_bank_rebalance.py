"""Rebalance fixed piece banks using source-derived interval demand.

Banks remain fixed for each piece and preserve color-math eligibility. A lower
interval demand guides search; it is never a physical or native admission.
"""
import argparse,copy,hashlib,json,time,math,random
from pathlib import Path
import numpy as np
from raster_slot_greedy import demand
from raster_palette import schedule as logical_schedule
from raster_obj_compact import unpack


def subdivide(source,indices):
    """Replace chosen square legal pieces with exact nonempty 8x8 children."""
    _,_,pixels=demand(source);pieces=[];masks=[];selected=set(indices)
    if any(i not in range(len(source['pieces']))for i in selected):raise ValueError('BANK_SUBDIVISION_INDEX')
    for i,(p,m,colors)in enumerate(zip(source['pieces'],source['piece_pixel_masks'],pixels)):
        if i not in selected:pieces.append(copy.deepcopy(p));masks.append(copy.deepcopy(m));continue
        if p['width']not in(8,32)or p['height']!=p['width']:raise ValueError('BANK_SUBDIVISION_OBSEL_8_32_REQUIRED')
        image=unpack(m)
        for y in range(0,p['height'],8):
            for x in range(0,p['width'],8):
                child=image[y:y+8,x:x+8]
                if not np.any(child):continue
                q=dict(p,x=p['x']+x,y=p['y']+y,width=8,height=8)
                for key,offset in (('local_x',x),('local_y',y)):
                    if key in p:q[key]=p[key]+offset
                q['rows']={p['y']+y+ly:sorted(set(map(int,row[row>=0])))for ly,row in enumerate(colors[y:y+8,x:x+8])}
                flat=child.flatten();mask=dict(width=8,height=8,packed_nibble_order='low then high',pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex())
                pieces.append(q);masks.append(mask)
    sizes={p['width']for p in pieces}
    if any(p['width']!=p['height']or p['width']not in(8,16,32)for p in pieces)or sizes=={8,16,32}:
        raise ValueError('BANK_SUBDIVISION_GLOBAL_SIZE_PAIR')
    height=len(source['trace']);clip=source.get('horizontal_clip_limit_counted',False)
    def slivers(p):
        if not clip or p['x']==-256:return p['width']//8
        return sum(p['x']+8*c+8>0 and p['x']+8*c<256 for c in range(p['width']//8))
    geometry=dict(oam_entries=len(pieces),peak_sprites_per_line=max(sum(p['y']<=y<p['y']+p['height']for p in pieces)for y in range(height)),peak_tile_slivers_per_line=max(sum(slivers(p)for p in pieces if p['y']<=y<p['y']+p['height'])for y in range(height)))
    if geometry['oam_entries']>128 or geometry['peak_sprites_per_line']>32 or geometry['peak_tile_slivers_per_line']>34:raise ValueError('BANK_SUBDIVISION_HARDWARE_GEOMETRY_LIMIT')
    result=copy.deepcopy(source);result.update(pieces=pieces,piece_pixel_masks=masks,geometry=geometry,piece_bank_assignment=[p['bank']for p in pieces])
    result.update(mixed_small_size=8,mixed_large_size=16 if 16 in sizes else 32)
    result['bank_subdivision']=dict(selected_input_pieces=sorted(selected),geometry=geometry,pixels_exact=True)
    demand(result)
    return result


def rebalance(source,lookahead=17,maximum_moves=20,maximum_interval=32,anneal_steps=0,seed=221,time_limit=60):
    if lookahead<0 or maximum_moves<0 or maximum_interval<1 or anneal_steps<0 or time_limit<=0:raise ValueError('BANK_REBALANCE_DOMAIN')
    required,_,pixels=demand(source);height=len(required)
    colors=sorted({int(c)for image in pixels for c in image[image>=0]});bits={c:1<<i for i,c in enumerate(colors)}
    piece_rows=[]
    for p,image in zip(source['pieces'],pixels):
        rows={}
        for ly,row in enumerate(image):
            cs=set(map(int,row[row>=0]))
            if cs:rows[p['y']+ly]=(sum(bits[c]for c in cs),sorted(cs))
        piece_rows.append(rows)
    active=[y for y,row in enumerate(required)if any(row)]
    if not active:raise ValueError('BANK_REBALANCE_EMPTY')
    first,last=min(active),max(active)
    intervals=[(a,b)for a in range(first,last)for b in range(a+1,min(last,a+maximum_interval)+1)]
    denominators=np.array([b-a for a,b in intervals],dtype=float)
    assignment=[p['bank']for p in source['pieces']];moves=[];started=time.monotonic()
    additive=source.get('color_math','additive')!='precomposited'
    allowed=[]
    for p in source['pieces']:
        banks=set(range(4*(p['bank']//4),4*(p['bank']//4)+4))if additive else set(range(8))
        banks.intersection_update(p.get('allowed_banks',range(8)));allowed.append(sorted(banks))
    cache={}
    def stats(indices):
        key=tuple(indices)
        if key in cache:return cache[key]
        rows=[0]*height
        for i in indices:
            for y,(mask,cs)in piece_rows[i].items():rows[y]|=mask
        peak=max(v.bit_count()for v in rows)
        if peak>15:cache[key]=None;return None
        excess=[]
        for a,b in intervals:
            union=0
            for y in range(a,b+1):union|=rows[y]
            excess.append(max(0,union.bit_count()-15))
        union=0
        for v in rows:union|=v
        result=(np.array(excess,dtype=np.int16),union.bit_count(),peak)
        cache[key]=result;return result
    def score(values):
        total=sum((v[0]for v in values),np.zeros(len(intervals),dtype=np.int32))
        return(float(np.max(total/denominators))if len(intervals)else 0,int(total.sum()),sum(v[1]for v in values))
    initial=None
    for step in range(maximum_moves+1):
        cache.clear();members=[[i for i,b in enumerate(assignment)if b==bank]for bank in range(8)]
        base=[stats(v)for v in members]
        if any(v is None for v in base):raise AssertionError('BANK_REBALANCE_INPUT_ROW_CAPACITY')
        current=score(base)
        if initial is None:initial=current
        if step==maximum_moves:break
        best=(current,None)
        for i,old in enumerate(assignment):
            for new in allowed[i]:
                if new==old:continue
                a=stats([j for j in members[old]if j!=i]);b=stats(sorted(members[new]+[i]))
                if b is None:continue
                trial=base.copy();trial[old]=a;trial[new]=b;value=score(trial)
                if value<best[0]:best=(value,(i,old,new))
        if best[1]is None:break
        i,old,new=best[1];assignment[i]=new;moves.append(dict(piece=i,old_bank=old,new_bank=new,objective=list(best[0])))
    sampled=accepted=0
    if anneal_steps:
        rng=random.Random(seed);best_assignment=assignment.copy();best_score=current
        def energy(value):return value[0]*10000+value[1]/max(1,len(intervals))*10+value[2]*.01
        for step in range(anneal_steps):
            if time.monotonic()-started>=time_limit:break
            sampled+=1;i=rng.randrange(len(assignment));old=assignment[i]
            choices=[b for b in allowed[i]if b!=old]
            if not choices:continue
            new=rng.choice(choices)
            a=stats([j for j in members[old]if j!=i]);b=stats(sorted(members[new]+[i]))
            if b is None:continue
            trial=base.copy();trial[old]=a;trial[new]=b;value=score(trial)
            temperature=500*(.01**(step/max(1,anneal_steps-1)))
            delta=energy(value)-energy(current)
            if delta<=0 or rng.random()<math.exp(-delta/temperature):
                accepted+=1;assignment[i]=new;members[old].remove(i);members[new].append(i);members[new].sort();base=trial;current=value
                if value<best_score:best_score=value;best_assignment=assignment.copy()
            if len(cache)>2048:cache.clear()
        assignment=best_assignment;members=[[i for i,b in enumerate(assignment)if b==bank]for bank in range(8)]
        base=[stats(v)for v in members];current=score(base)
        moves=[dict(piece=i,old_bank=p['bank'],new_bank=b)for i,(p,b)in enumerate(zip(source['pieces'],assignment))if p['bank']!=b]
    pieces=[]
    for p,rows,b in zip(source['pieces'],piece_rows,assignment):
        pieces.append(dict(p,bank=b,rows={y:cs for y,(mask,cs)in rows.items()}))
    raw_trace,snapshots=logical_schedule(pieces,assignment,height,lookahead)
    trace=[]
    for row in raw_trace:
        before={b:row['resident_before'].get(b,[None]*15)for b in range(8)}
        trace.append(dict(row,resident_before=before))
    images=[]
    for p,colors in zip(pieces,pixels):
        image=np.zeros(colors.shape,dtype=np.uint8)
        for ly,lx in zip(*np.where(colors>=0)):
            y=p['y']+int(ly);c=int(colors[ly,lx]);s=snapshots[y][p['bank']].index(c)
            image[ly,lx]=s+1
            if snapshots[y][p['bank']][s]!=c:raise AssertionError('BANK_REBALANCE_PIXEL_IDENTITY')
        flat=image.flatten();images.append(dict(width=p['width'],height=p['height'],packed_nibble_order='low then high',pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex()))
    result=copy.deepcopy(source)
    result.update(pieces=pieces,piece_pixel_masks=images,trace=trace,piece_bank_assignment=assignment,
        peak_scheduled_writes=max(r['colors_written']for r in trace[1:]),peak_cgram_data_bytes=max(r['cgram_data_bytes']for r in trace[1:]),
        worst_scanline=1+int(np.argmax([r['colors_written']for r in trace[1:]])),average_writes=float(np.mean([r['colors_written']for r in trace[1:]])),
        bank_rebalance=dict(schema='BYOR_FIXED_BANK_REBALANCE_V1',status='REBALANCED_SOURCE_PIXEL_IDENTITIES_PROVEN',seconds=time.monotonic()-started,
            maximum_interval_lines=maximum_interval,initial_objective=list(initial),final_objective=list(current),moves=moves,
            anneal_steps_requested=anneal_steps,anneal_proposals_sampled=sampled,anneal_moves_accepted=accepted,anneal_seed=seed,
            final_bank_distinct_colors=[v[1]for v in base],final_bank_peak_row_colors=[v[2]for v in base],
            fixed_bank_per_piece=True,color_math_classes_preserved=additive,pixel_color_identity_verified=True,
            geometry_unchanged=True,native_timing_admitted=False,universal_raster_rejected=False,no_color_reduction=True))
    for field in ('prepared_dma_packets','physical_slot_layout'):result.pop(field,None)
    result.update(write_budget=None,lookahead_lines=lookahead,prepared_dma_partition_bound_enforced=False,
        prepared_dma_window_master_clocks=None,native_presentation_proven=False)
    result['compiled_schedule_sha256']=hashlib.sha256(json.dumps(dict(pieces=pieces,pixel_masks=images,trace=trace),sort_keys=True).encode()).hexdigest()
    indices=np.zeros((height,256),dtype=np.uint8)
    for p,mask in zip(pieces,images):
        image=unpack(mask)
        for ly,lx in zip(*np.where(image!=0)):indices[p['y']+ly,p['x']+lx]=128+16*p['bank']+int(image[ly,lx])
    result['compiled_indices_sha256']=hashlib.sha256(indices.tobytes()).hexdigest()
    _,_,replayed=demand(result)
    if any(not np.array_equal(a,b)for a,b in zip(pixels,replayed)):raise AssertionError('BANK_REBALANCE_INDEPENDENT_PIXEL_REPLAY')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--lookahead',type=int,default=17);p.add_argument('--maximum-moves',type=int,default=20);p.add_argument('--maximum-interval',type=int,default=32)
    p.add_argument('--anneal-steps',type=int,default=0);p.add_argument('--seed',type=int,default=221);p.add_argument('--time-limit',type=float,default=60)
    a=p.parse_args();r=rebalance(json.loads(a.schedule.read_text()),a.lookahead,a.maximum_moves,a.maximum_interval,a.anneal_steps,a.seed,a.time_limit);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['bank_rebalance']))


if __name__=='__main__':main()
