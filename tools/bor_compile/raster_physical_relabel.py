"""Lossless fixed bank relabeling and slot reflection of physical schedules.

Eligible banks are permuted and each bank's fifteen opaque slots may be
reversed for the whole frame. This bounded family preserves source words,
geometry and math eligibility. It never rejects raster universally.
"""
import argparse,copy,hashlib,itertools,json,time
from pathlib import Path
import numpy as np
from raster_obj_compact import unpack
from raster_slot_greedy import demand,partition
from raster_slot_refine import verify_packets
from raster_dma_partition import minimum_commit_span


def point_partition(points):
    points=sorted(set(points))
    if not points:return 0,[]
    gaps=[(points[i+1]-points[i]-1,i)for i in range(len(points)-1)]
    cuts=sorted(i for gap,i in sorted(gaps,reverse=True)[:3]if gap>=2)
    groups=[];start=0
    for cut in cuts+[len(points)-1]:
        groups.append((points[start],points[cut]));start=cut+1
    return max(0,sum(16*(hi-lo+1)+24 for lo,hi in groups)-40),groups


def relabel(source,time_limit=30):
    if time_limit<=0:raise ValueError('PHYSICAL_RELABEL_TIME_DOMAIN')
    _,_,pixels=demand(source);verify_packets(source)
    started=time.monotonic();height=len(source['trace'])
    rows=[row for row in source['trace'][1:]if row['updates']]
    maximum=max((len(row['updates'])for row in rows),default=0)
    if not maximum:raise ValueError('PHYSICAL_RELABEL_NO_RASTER_WRITES')
    banks=np.zeros((len(rows),maximum),dtype=np.int16)
    slots=np.zeros_like(banks);valid=np.zeros_like(banks,dtype=bool)
    for y,row in enumerate(rows):
        for i,event in enumerate(row['updates']):
            banks[y,i]=event['bank'];slots[y,i]=event['slot'];valid[y,i]=True
    reflections=((np.arange(256)[:,None]>>np.arange(8))&1).astype(bool)
    pools=[range(8)]if source.get('color_math')=='precomposited'else[range(4),range(4,8)]
    choices=[list(itertools.permutations(pool))for pool in pools]
    best=None;best_mapping=None;best_reflection=None;trials=0;exhaustive=True
    for permutation in itertools.product(*choices):
        if trials and time.monotonic()-started>=time_limit:exhaustive=False;break
        mapping=np.array([bank for group in permutation for bank in group],dtype=np.int16)
        if any(int(mapping[p['bank']])not in p.get('allowed_banks',range(8))for p in source['pieces']):continue
        addresses=16*mapping[banks][None,:,:]+np.where(reflections[:,banks],16-slots[None,:,:],slots[None,:,:])
        addresses=np.where(valid[None,:,:],addresses,256)
        addresses.sort(axis=2)
        counts=valid.sum(axis=1)
        last=np.take_along_axis(addresses,(counts-1)[None,:,None].repeat(256,axis=0),axis=2)[:,:,0]
        costs=16*(last-addresses[:,:,0]+1)+24
        if maximum>1:
            gaps=addresses[:,:,1:]-addresses[:,:,:-1]-1
            gaps=np.where(np.arange(maximum-1)[None,None,:]<counts[None,:,None]-1,gaps,0)
            savings=np.maximum(0,16*gaps-24)
            savings.sort(axis=2)
            costs-=savings[:,:,-3:].sum(axis=2)
        costs=np.maximum(0,costs-40)
        peaks=costs.max(axis=1);totals=costs.sum(axis=1)
        index=min(range(256),key=lambda i:(int(peaks[i]),int(totals[i]),i))
        score=(int(peaks[index]),int(totals[index]))
        if best is None or score<best:
            best=score;best_mapping=list(map(int,mapping));best_reflection=list(map(bool,reflections[index]))
        trials+=1
    if best is None:raise ValueError('PHYSICAL_RELABEL_NO_ELIGIBLE_MAPPING')
    result=copy.deepcopy(source)
    def bank_dict(values,reverse=False):
        return{best_mapping[int(b)]:list(reversed(v))if reverse and best_reflection[int(b)]else copy.deepcopy(v)for b,v in values.items()}
    def event(e):
        return dict(e,bank=best_mapping[e['bank']],slot=16-e['slot']if best_reflection[e['bank']]else e['slot'])
    for row in result['trace']:
        row['resident_before']=bank_dict(row['resident_before'],True)
        row['updates']=sorted((event(e)for e in row['updates']),key=lambda e:(e['bank'],e['slot']))
        if 'retained'in row:row['retained']=bank_dict(row['retained'])
        if 'prefetched'in row:row['prefetched']=[event(e)for e in row['prefetched']]
        if 'affected_banks'in row:row['affected_banks']=sorted(best_mapping[b]for b in row['affected_banks'])
    indices=np.zeros((height,256),dtype=np.uint8)
    for piece,mask in zip(result['pieces'],result['piece_pixel_masks']):
        old_bank=piece['bank'];piece['bank']=best_mapping[old_bank]
        image=unpack(mask)
        if best_reflection[old_bank]:image=np.where(image,16-image,0).astype(np.uint8)
        flat=image.flatten();mask['pixels_hex']=(flat[::2]|flat[1::2]<<4).tobytes().hex()
        for ly,lx in zip(*np.where(image)):
            indices[piece['y']+ly,piece['x']+lx]=128+16*piece['bank']+image[ly,lx]
    packets=[];state=[0]*128
    for row in result['trace']:
        for e in row['updates']:state[16*e['bank']+e['slot']]=e['color']
        points=[16*e['bank']+e['slot']for e in row['updates']]if row['scanline']else[]
        span,groups=point_partition(points)
        if partition([(a,a)for a in points])[0]!=span:raise AssertionError('PHYSICAL_RELABEL_PARTITION_REPLAY')
        packets.append(dict(scanline=row['scanline'],prepared_commit_span=span,packets=[dict(
            cgram_word_address=128+lo,word_count=hi-lo+1,
            data_hex=b''.join(state[a].to_bytes(2,'little')for a in range(lo,hi+1)).hex())for lo,hi in groups]))
    if(max(r['prepared_commit_span']for r in packets),sum(r['prepared_commit_span']for r in packets))!=best:
        raise AssertionError('PHYSICAL_RELABEL_VECTOR_COST_IDENTITY')
    report=dict(schema='BYOR_PHYSICAL_BANK_REFLECTION_SEARCH_V1',status='PHYSICAL_SLOT_PACKETS_AND_PIXEL_IDENTITIES_PROVEN',
        seconds=time.monotonic()-started,eligible_permutations_tested=trials,slot_reflections_per_permutation=256,
        eligible_permutation_family_exhaustive=exhaustive,fixed_piece_bank_permutation=best_mapping,
        reversed_original_banks=[b for b,flip in enumerate(best_reflection)if flip],peak_prepared_commit_span=best[0],
        aggregate_commit_span=best[1],geometry_unchanged=True,math_eligibility_preserved=True,
        peak_changed_physical_words=max(len(row['updates'])for row in source['trace'][1:]),
        necessary_span_from_changed_word_count=max(minimum_commit_span(len(row['updates']))for row in source['trace'][1:]),
        pixel_color_identity_verified=True,all_packet_cgram_identities_verified=True,
        native_timing_admitted=False,universal_raster_rejected=False,no_color_reduction=True)
    result.update(physical_slot_layout=report,prepared_dma_packets=packets,native_presentation_proven=False,
        compiled_indices_sha256=hashlib.sha256(indices.tobytes()).hexdigest(),
        input_compiled_schedule_sha256=source.get('compiled_schedule_sha256'))
    payload=dict(pieces=result['pieces'],pixel_masks=result['piece_pixel_masks'],trace=result['trace'])
    if result.get('scanline_math_controls_source_bound'):
        payload.update(selected_modes=result['selected_modes'],compiled_color_window_descriptors=result['compiled_color_window_descriptors'])
    result['compiled_schedule_sha256']=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    result['compiled_transfer_descriptor_sha256']=hashlib.sha256(json.dumps(packets,sort_keys=True).encode()).hexdigest()
    verify_packets(result);_,_,replayed=demand(result)
    if any(not np.array_equal(a,b)for a,b in zip(pixels,replayed)):raise AssertionError('PHYSICAL_RELABEL_SOURCE_PIXEL_IDENTITY')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--time-limit',type=float,default=30);a=p.parse_args()
    result=relabel(json.loads(a.schedule.read_text()),a.time_limit)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['physical_slot_layout']))


if __name__=='__main__':main()
