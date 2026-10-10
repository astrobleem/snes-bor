"""Compile physical OBJ slot updates to exact contiguous CGRAM packets.

This is an offline descriptor planner, not native timing admission. Color-zero
slots are never touched. Bridging a gap rewrites only known resident identities.
"""
import argparse
import hashlib
import json
from pathlib import Path


def optimistic_dma_span(updates):
    """Necessary first-to-last data-write span for a prepared DMA chain.

    SNES DMA costs eight clocks per byte and per channel. A further data range
    needs an address byte and two channel starts: 24 clocks. This bound freely
    rearranges slots and permits rewriting every intervening word, including
    transparent zeros. It ignores CPU setup, contention and channel scarcity.
    It applies to this bank-update set, not every possible palette schedule.
    """
    counts={b:0 for b in range(8)}
    for e in updates:counts[e['bank']]+=1
    banks=[b for b in range(8)if counts[b]]
    best=[(0,0,[])]+[None]*len(banks)
    for end in range(1,len(banks)+1):
        for start in range(end):
            first,last=banks[start],banks[end-1]
            words=counts[first] if first==last else counts[first]+counts[last]+16*(last-first-1)+1
            cost,n,groups=best[start]
            candidate=(cost+16*words+24,n+1,groups+[(first,last,words)])
            if best[end] is None or candidate[:2]<best[end][:2]:best[end]=candidate
    cost,n,groups=best[-1]
    # Even more favorable lower bound: grant every adjacent occupied-bank
    # bridge simultaneously, without charging unused intermediate slots.
    # Each bridge writes at least a zero word (16 clocks), saves one range
    # switch (24 clocks), and can therefore save at most eight clocks.
    bridges=sum(counts[b]>0 and counts[b+1]>0 for b in range(7))
    lower=max(0,16*sum(counts.values())+24*len(banks)-32-8*bridges) if banks else 0
    return dict(first_to_last_data_write_master_clocks=lower,
                first_to_last_cgram_commit_master_clocks=max(0,lower-8),
                first_low_byte_prefetch_granted=True,
                best_partition_span_master_clocks=max(0,cost-32),
                best_partition_range_count=n,best_partition_chain_dma_channels=2*n-1 if n else 0,
                ranges=[dict(first_bank=a,last_bank=b,data_words=w)for a,b,w in groups],
                favorable_slot_reordering_and_transparent_zero_rewrites=True,
                cpu_setup_contention_and_channel_scarcity_excluded=True)


def packetize_row(row, address_cost=1):
    """Minimize data bytes plus configurable cost per destination write.

    Each packet is confined to one bank's 15 opaque slots. Dynamic programming
    tests every partition of sorted updates, including unchanged known slots
    within a range. The default cost counts a one-byte CGADD transfer, excluding
    channel setup and CPU instruction costs.
    """
    if not isinstance(address_cost, int) or address_cost < 0:
        raise ValueError('CGRAM_ADDRESS_COST_DOMAIN')
    before={int(b):list(v) for b,v in row['resident_before'].items()}
    if set(before)!=set(range(8)) or any(len(v)!=15 for v in before.values()):
        raise ValueError('CGRAM_SLOT_STATE_DOMAIN')
    if any(c is not None and (not isinstance(c,int) or not 0<=c<=32767) for v in before.values() for c in v):
        raise ValueError('CGRAM_RESIDENT_COLOR_DOMAIN')
    after={b:list(v) for b,v in before.items()};changed={b:[] for b in before}
    for e in row['updates']:
        b,s,c=e['bank'],e['slot'],e['color']
        if b not in after or not 1<=s<=15 or not isinstance(c,int) or not 0<=c<=32767:
            raise ValueError('CGRAM_UPDATE_DOMAIN')
        if s in changed[b] or before[b][s-1]!=e['old']:
            raise ValueError('CGRAM_UPDATE_IDENTITY')
        after[b][s-1]=c;changed[b].append(s)
    packets=[]
    for b in range(8):
        slots=sorted(changed[b]);count=len(slots)
        # Tuple order gives deterministic minimal bytes, then packet count.
        best=[(0,0,[])]+[None]*count
        for end in range(1,count+1):
            for start in range(end):
                lo,hi=slots[start],slots[end-1]
                colors=after[b][lo-1:hi]
                if any(c is None for c in colors):continue
                cost,number,previous=best[start]
                candidate=(cost+2*len(colors)+address_cost,number+1,previous+[(lo,hi)])
                if best[end] is None or candidate[:2]<best[end][:2]:best[end]=candidate
        for lo,hi in best[count][2]:
            colors=after[b][lo-1:hi]
            data=b''.join(c.to_bytes(2,'little') for c in colors)
            packets.append(dict(cgram_word_address=128+b*16+lo,bank=b,first_slot=lo,
                                word_count=len(colors),data_hex=data.hex(),data_bytes=len(data),
                                bridged_unchanged_slots=[s for s in range(lo,hi+1)if s not in changed[b]]))
    # Independent destination/payload replay includes every resident slot.
    replay={b:list(v)for b,v in before.items()}
    for p in packets:
        data=bytes.fromhex(p['data_hex'])
        for i in range(p['word_count']):
            replay[p['bank']][p['first_slot']-1+i]=int.from_bytes(data[2*i:2*i+2],'little')
    if replay!=after:raise AssertionError('CGRAM_PACKET_SLOT_IDENTITY_FAULT')
    return dict(scanline=row['scanline'],packets=packets,colors_changed=len(row['updates']),
                packet_count=len(packets),cgram_data_bytes=sum(p['data_bytes']for p in packets),
                cgram_address_bytes=len(packets),
                transfer_bytes=sum(p['data_bytes']for p in packets)+len(packets),
                weighted_cost=sum(p['data_bytes']for p in packets)+address_cost*len(packets),
                optimistic_prepared_dma_span=optimistic_dma_span(row['updates']),
                slot_identity_verified=True)


def compile_packets(schedule, address_cost=1):
    valid_status={'JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN':'compiled_pixel_identity_verified',
                  'JOINT_CONTEXT_SLOT_SCHEDULE_PROVEN':'actor_pixel_identity_verified'}
    if not schedule.get(valid_status.get(schedule.get('status'),''),False) or not schedule.get('no_color_reduction'):
        raise ValueError('CGRAM_VALIDATED_JOINT_SCHEDULE_REQUIRED')
    rows=[];previous=None
    for y,row in enumerate(schedule['trace']):
        before={int(b):list(v)for b,v in row['resident_before'].items()}
        if row['scanline']!=y or previous is not None and before!=previous:
            raise ValueError('CGRAM_SCANLINE_STATE_CONTINUITY')
        rows.append(packetize_row(row,address_cost))
        previous=before
        for e in row['updates']:previous[e['bank']][e['slot']-1]=e['color']
    if not rows:raise ValueError('CGRAM_EMPTY_SCHEDULE')
    raster=[row for row in rows if row['scanline']>0]
    worst=max(raster,key=lambda row:row['transfer_bytes'],default=None)
    result=dict(schema='BYOR_OBJ_CGRAM_PACKETS_V1',status='EXACT_SLOT_PACKETS_COMPILED',
                source_rgb555_sha256=schedule.get('source_rgb555_sha256',schedule.get('source_context_rgb555_sha256')),
                input_schedule_sha256=hashlib.sha256(json.dumps(schedule,sort_keys=True).encode()).hexdigest(),
                address_cost=address_cost,rows=rows,initial_vblank=rows[0],
                peak_packet_count=max((r['packet_count']for r in raster),default=0),
                peak_transfer_bytes=max((r['transfer_bytes']for r in raster),default=0),
                peak_data_bytes=max((r['cgram_data_bytes']for r in raster),default=0),
                peak_optimistic_prepared_dma_span_master_clocks=max((r['optimistic_prepared_dma_span']['first_to_last_data_write_master_clocks']for r in raster),default=0),
                peak_optimistic_prepared_dma_commit_span_master_clocks=max((r['optimistic_prepared_dma_span']['first_to_last_cgram_commit_master_clocks']for r in raster),default=0),
                worst_scanline=worst['scanline']if worst else None,
                all_slot_identities_verified=True,no_color_reduction=True,
                native_timing_admitted=False,
                scope='Destination and data bytes only. CPU, DMA channel setup, HDMA/NMI contention and actual transfer deadlines remain unproven.')
    result['compiled_packets_sha256']=hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--address-cost',type=int,default=1)
    a=p.parse_args();r=compile_packets(json.loads(a.schedule.read_text()),a.address_cost)
    a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r[k]for k in ('status','peak_packet_count','peak_transfer_bytes','worst_scanline')}))


if __name__=='__main__':main()
