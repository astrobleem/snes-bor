"""Exhaustive eligible bank ordering for a fixed lossless palette write trace.

The objective grants ideal endpoint slots. Emitted physical packets preserve
the input slot layout; they may exceed the optimistic bound and native budget.
"""
import argparse,copy,hashlib,itertools,json
from pathlib import Path
import numpy as np
from raster_slot_greedy import demand,bank_groups
from raster_bank_residency import favorable_span
from raster_physical_relabel import point_partition
from raster_slot_refine import verify_packets


def optimize(source):
    _,_,pixels=demand(source);pools=bank_groups(source)
    best=None;mapping=None;trials=0
    for groups in itertools.product(*(itertools.permutations(p)for p in pools)):
        candidate=tuple(b for group in groups for b in group)
        if any(candidate[p['bank']]not in p.get('allowed_banks',range(8))for p in source['pieces']):continue
        costs=[favorable_span([dict(e,bank=candidate[e['bank']])for e in row['updates']])for row in source['trace'][1:]]
        score=max(costs,default=0),sum(costs);trials+=1
        if best is None or score<best:best=score;mapping=candidate
    if mapping is None:raise ValueError('BANK_ORDER_NO_ELIGIBLE_PERMUTATION')
    result=copy.deepcopy(source)
    for key in('bank_residency','bank_rebalance','bank_search'):
        if key in result:result['input_'+key]=result.pop(key)
    for key in('prepared_dma_packets','physical_slot_layout','physical_slot_refinement'):result.pop(key,None)
    for p in result['pieces']:p['bank']=mapping[p['bank']]
    def remap(values):return{mapping[int(b)]:copy.deepcopy(v)for b,v in values.items()}
    for row in result['trace']:
        row['resident_before']=remap(row['resident_before'])
        if 'retained'in row:row['retained']=remap(row['retained'])
        for field in('updates','prefetched'):
            row[field]=[dict(e,bank=mapping[e['bank']])for e in row.get(field,[])]
        row['affected_banks']=sorted({e['bank']for e in row['updates']})
    state=[0]*128;packets=[]
    for row in result['trace']:
        for e in row['updates']:state[16*e['bank']+e['slot']]=e['color']
        span,ranges=point_partition([16*e['bank']+e['slot']for e in row['updates']]if row['scanline']else[])
        packets.append(dict(scanline=row['scanline'],prepared_commit_span=span,packets=[dict(cgram_word_address=128+lo,word_count=hi-lo+1,
            data_hex=b''.join(state[i].to_bytes(2,'little')for i in range(lo,hi+1)).hex())for lo,hi in ranges]))
    result.update(prepared_dma_packets=packets,piece_bank_assignment=[p['bank']for p in result['pieces']],native_presentation_proven=False,
        prepared_dma_window_master_clocks=None,prepared_dma_partition_bound_enforced=False,bank_assignment_authority='optimistic_bank_order')
    verify_packets(result);_,_,replayed=demand(result)
    if any(not np.array_equal(a,b)for a,b in zip(pixels,replayed)):raise AssertionError('BANK_ORDER_SOURCE_OPERAND_REPLAY')
    indices=np.zeros((len(source['trace']),256),dtype=np.uint8)
    from raster_obj_compact import unpack
    for p,m in zip(result['pieces'],result['piece_pixel_masks']):
        image=unpack(m)
        for ly,lx in zip(*np.where(image)):indices[p['y']+ly,p['x']+lx]=128+16*p['bank']+image[ly,lx]
    peak=max(r['prepared_commit_span']for r in packets)
    result['optimistic_bank_order']=dict(schema='BYOR_FIXED_TRACE_BANK_ORDER_V1',permutations_evaluated=trials,eligible_family_exhaustive=True,
        minimum_optimistic_peak_span=best[0],aggregate_optimistic_span=best[1],bank_mapping=list(mapping),
        emitted_physical_peak_span=peak,source_operands_replayed=True,fixed_bank_per_piece=True,palette_write_lifetimes_unchanged=True,
        math_eligibility_preserved=True,native_timing_admitted=False,universal_raster_rejected=False,no_color_reduction=True)
    result['physical_slot_layout']=dict(schema='BYOR_BANK_ORDER_UNCHANGED_SLOT_PHYSICAL_WITNESS_V1',
        peak_prepared_commit_span=peak,pixel_color_identity_verified=True,all_packet_cgram_identities_verified=True,
        native_timing_admitted=False,universal_raster_rejected=False,no_color_reduction=True)
    payload=dict(pieces=result['pieces'],pixel_masks=result['piece_pixel_masks'],trace=result['trace'])
    if result.get('scanline_math_controls_source_bound'):payload.update(selected_modes=result['selected_modes'],compiled_color_window_descriptors=result['compiled_color_window_descriptors'])
    result.update(compiled_schedule_sha256=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest(),
        compiled_indices_sha256=hashlib.sha256(indices.tobytes()).hexdigest(),
        compiled_transfer_descriptor_sha256=hashlib.sha256(json.dumps(packets,sort_keys=True).encode()).hexdigest())
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=optimize(json.loads(a.schedule.read_text()));a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['optimistic_bank_order']))


if __name__=='__main__':main()
