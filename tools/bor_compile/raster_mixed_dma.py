"""Offline lossless three-range mode-2 plus sparse mode-3 CGRAM planning.

Mode 3 at $2121 repeats CGADD twice, then writes the color's two bytes.
One sparse channel dominates splitting sparse words between channels.
The first-to-last high-byte cost excludes the first write's setup; native
first-write alignment, register preparation and contention remain unproven.
"""
import argparse,copy,hashlib,json,time
from pathlib import Path
import numpy as np
from raster_physical_relabel import point_partition
from raster_slot_refine import verify_packets


def partition(points,subset_limit=21):
    if type(subset_limit)is not int or not 0<=subset_limit<=21:raise ValueError('MIXED_DMA_SUBSET_DOMAIN')
    points=sorted(set(points));n=len(points)
    if n>subset_limit:raise ValueError('MIXED_DMA_BOUNDED_SUBSET_LIMIT')
    if not n:return 0,[],[]
    # Every subset selects sparse words; partition its complement optimally
    # into at most three contiguous ranges, charging all padding words.
    masks=np.arange(1<<n,dtype=np.uint32);bits=((masks[:,None]>>np.arange(n,dtype=np.uint32))&1).astype(bool)
    sparse=bits.sum(axis=1);counts=n-sparse
    addresses=np.where(~bits,np.array(points,dtype=np.int16),256);addresses.sort(axis=1)
    last=np.take_along_axis(addresses,np.maximum(counts-1,0)[:,None],axis=1)[:,0]
    cost=16*(last-addresses[:,0]+1)+24
    if n>1:
        gaps=addresses[:,1:]-addresses[:,:-1]-1
        gaps=np.where(np.arange(n-1)[None,:]<counts[:,None]-1,gaps,0)
        savings=np.maximum(0,16*gaps-24);savings.sort(axis=1);cost-=savings[:,-2:].sum(axis=1)
    cost=np.where(counts,cost,0)+np.where(sparse,32*sparse+8,0)-40
    cost=np.maximum(cost,0);index=int(np.argmin(cost));chosen=[p for i,p in enumerate(points)if bits[index,i]]
    _,ranges=point_partition([p for p in points if p not in chosen],maximum_ranges=3)
    actual=max(0,sum(16*(hi-lo+1)+24 for lo,hi in ranges)+(8+32*len(chosen)if chosen else 0)-40)
    if actual!=int(cost[index]):raise AssertionError('MIXED_DMA_PARTITION_REPLAY')
    ordinary,ranges4=point_partition(points)
    if ordinary<=actual:return ordinary,ranges4,[]
    return actual,ranges,chosen


def compile(source,target_window=345,subset_limit=21):
    if type(target_window)is not int or target_window<1:raise ValueError('MIXED_DMA_WINDOW_DOMAIN')
    verify_packets(source);result=copy.deepcopy(source);state=[0]*128;rows=[];started=time.monotonic()
    for row in source['trace']:
        y=row['scanline']
        for e in row['updates']:state[16*e['bank']+e['slot']]=e['color']
        points=[16*e['bank']+e['slot']for e in row['updates']]if y else []
        span,ranges,sparse=partition(points,subset_limit)
        packets=[];replay=state.copy()
        for lo,hi in ranges:
            packets.append(dict(mode=2,b_bus_register=0x22,cgram_word_address=128+lo,word_count=hi-lo+1,data_hex=b''.join(state[a].to_bytes(2,'little')for a in range(lo,hi+1)).hex()))
        if sparse:
            data=b''.join(bytes([128+a,128+a])+state[a].to_bytes(2,'little')for a in sparse)
            packets.append(dict(mode=3,b_bus_register=0x21,cgram_word_addresses=[128+a for a in sparse],data_hex=data.hex()))
        # Decode B-bus operations, not descriptor color identities, to prove
        # every scheduled write's actual address and high-byte latch.
        physical=[0]*128 if y==0 else rows[-1]['_physical'].copy()
        if y==0:physical=state.copy()
        for p in packets:
            raw=bytes.fromhex(p['data_hex'])
            if p['mode']==2:
                lo=p['cgram_word_address']-128
                for i in range(p['word_count']):physical[lo+i]=int.from_bytes(raw[2*i:2*i+2],'little')
            else:
                for i in range(0,len(raw),4):
                    if raw[i]!=raw[i+1]:raise AssertionError('MIXED_DMA_CGADD_DUPLICATE')
                    physical[raw[i+1]-128]=int.from_bytes(raw[i+2:i+4],'little')
        if physical!=replay:raise AssertionError('MIXED_DMA_CGRAM_IDENTITY')
        channels=2*len(ranges)-int(bool(ranges))+int(bool(sparse))
        if channels>7:raise AssertionError('MIXED_DMA_CHANNEL_BUDGET')
        rows.append(dict(scanline=y,packets=packets,prepared_commit_span=span,channels_required=channels,cgram_word_writes=sum(hi-lo+1 for lo,hi in ranges)+len(sparse),dma_stream_bytes=sum(len(bytes.fromhex(p['data_hex']))for p in packets),_physical=physical))
    for row in rows:row.pop('_physical')
    report=dict(schema='BYOR_MIXED_MODE2_MODE3_CGRAM_V1',status='MIXED_DMA_CGRAM_WORD_IDENTITIES_PROVEN',seconds=time.monotonic()-started,peak_prepared_commit_span=max(r['prepared_commit_span']for r in rows),target_window_met_by_all_packets=all(r['prepared_commit_span']<target_window for r in rows),maximum_channels=max(r['channels_required']for r in rows),channel_zero_unused=True,fixed_pixel_indices=True,fixed_piece_banks=True,source_words_unchanged=True,mode3_cgadd_writes_per_color=2,per_line_channel_modes_may_change=True,descriptor_register_preparation_and_first_high_alignment_native_admitted=False,native_timing_admitted=False,universal_raster_rejected=False,no_color_reduction=True)
    result['mixed_dma_transport']=report;result['prepared_mixed_dma_packets']=rows
    result['compiled_mixed_transfer_descriptor_sha256']=hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()
    result['native_presentation_proven']=False
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--target-window',type=int,default=345);p.add_argument('--subset-limit',type=int,default=21)
    a=p.parse_args();result=compile(json.loads(a.schedule.read_text()),a.target_window,a.subset_limit)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['mixed_dma_transport']))


if __name__=='__main__':main()
