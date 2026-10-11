"""Optimize fixed lifetime slot permutations without adding palette writes."""
import argparse,copy,hashlib,json
from pathlib import Path
import numpy as np
from raster_physical_ranges import constrain
from raster_physical_relabel import point_partition
from raster_slot_greedy import demand
from raster_slot_refine import verify_packets
from raster_slot_layout import unpack


def optimize(source,time_limit=30,permute_banks=False):
    from ortools.sat.python import cp_model
    if time_limit<=0:raise ValueError('FIXED_PERMUTATION_TIME_DOMAIN')
    _,_,pixels=demand(source);verify_packets(source)
    model=cp_model.CpModel();slots={};destinations={}
    if permute_banks:
        for b in range(8):
            eligible=set(range(8)if source.get('color_math')=='precomposited'else range(0,4)if b<4 else range(4,8))
            for piece in source['pieces']:
                if piece['bank']==b:eligible.intersection_update(piece.get('allowed_banks',range(8)))
            if not eligible:raise ValueError('FIXED_PERMUTATION_BANK_ELIGIBILITY')
            destinations[b]=model.new_int_var_from_domain(cp_model.Domain.from_values(sorted(eligible)),f'bank{b}')
            model.add_hint(destinations[b],b)
        model.add_all_different(list(destinations.values()))
    for b in range(8):
        for s in range(15):
            slots[15*b+s]=model.new_int_var(0,14,f'slot{b}_{s}')
            model.add_hint(slots[15*b+s],s)
        model.add_all_different([slots[15*b+s]for s in range(15)])
    flags={};packet_hints={};change_hints={}
    for row in source['trace'][1:]:
        y=row['scanline']
        for e in row['updates']:
            i=15*e['bank']+e['slot']-1
            flags.setdefault((y,e['bank']),[]).append((i,model.new_constant(1)))
            change_hints[y,i,e['bank']]=(16*e['bank']+e['slot'],True)
        packet_hints[y]=[(p['cgram_word_address']-128,p['cgram_word_address']-129+p['word_count'])for p in source['prepared_dma_packets'][y]['packets']]
    ranges,peak=constrain(model,flags,slots,len(source['trace']),4,3001,bank_destinations=destinations,
        packet_hints=packet_hints,fixed_address_change_hints=change_hints)
    model.add_hint(peak,max(r['prepared_commit_span']for r in source['prepared_dma_packets'])+40)
    model.minimize(peak)
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit;solver.parameters.num_search_workers=4
    status=solver.solve(model)
    report=dict(schema='BYOR_FIXED_LIFETIME_SLOT_PERMUTATION_V1',solver_status=solver.status_name(status),
        solver_seconds=solver.wall_time,restricted_family_lower_bound=max(0,int(solver.best_objective_bound)-40),
        native_timing_admitted=False,universal_raster_rejected=False,no_color_reduction=True)
    if status not in(cp_model.FEASIBLE,cp_model.OPTIMAL):return report
    mapping={b:[0]+[solver.value(slots[15*b+s])+1 for s in range(15)]for b in range(8)}
    banks={b:solver.value(destinations[b])if permute_banks else b for b in range(8)}
    result=copy.deepcopy(source)
    def event(e):return dict(e,bank=banks[e['bank']],slot=mapping[e['bank']][e['slot']])
    for row in result['trace']:
        resident={}
        for key,values in list(row['resident_before'].items()):
            b=int(key);out=[None]*15
            for s,c in enumerate(values,1):out[mapping[b][s]-1]=c
            resident[banks[b]]=out
        row['resident_before']=resident
        row['updates']=sorted(map(event,row['updates']),key=lambda e:(e['bank'],e['slot']))
        if 'prefetched'in row:row['prefetched']=list(map(event,row['prefetched']))
        if 'retained'in row:row['retained']={banks[int(b)]:v for b,v in row['retained'].items()}
        if 'affected_banks'in row:row['affected_banks']=sorted(banks[b]for b in row['affected_banks'])
    indices=np.zeros((len(source['trace']),256),dtype=np.uint8)
    for piece,mask in zip(result['pieces'],result['piece_pixel_masks']):
        image=np.asarray(mapping[piece['bank']],dtype=np.uint8)[unpack(mask)]
        piece['bank']=banks[piece['bank']]
        flat=image.flatten();mask['pixels_hex']=(flat[::2]|flat[1::2]<<4).tobytes().hex()
        for ly,lx in zip(*np.where(image)):indices[piece['y']+ly,piece['x']+lx]=128+16*piece['bank']+image[ly,lx]
    packets=[];state=[0]*128
    for row in result['trace']:
        for e in row['updates']:state[16*e['bank']+e['slot']]=e['color']
        span,groups=point_partition([16*e['bank']+e['slot']for e in row['updates']]if row['scanline']else[])
        packets.append(dict(scanline=row['scanline'],prepared_commit_span=span,packets=[dict(cgram_word_address=128+lo,
            word_count=hi-lo+1,data_hex=b''.join(state[a].to_bytes(2,'little')for a in range(lo,hi+1)).hex())for lo,hi in groups]))
    verify_packets(dict(result,prepared_dma_packets=packets));_,_,replayed=demand(result)
    if any(not np.array_equal(a,b)for a,b in zip(pixels,replayed)):raise AssertionError('FIXED_PERMUTATION_PIXEL_IDENTITY')
    report.update(status='PHYSICAL_SLOT_PACKETS_AND_PIXEL_IDENTITIES_PROVEN',slot_permutations=mapping,
        peak_prepared_commit_span=max(r['prepared_commit_span']for r in packets),aggregate_commit_span=sum(r['prepared_commit_span']for r in packets),
        peak_changed_physical_words=max(len(r['updates'])for r in result['trace'][1:]),
        all_packet_cgram_identities_verified=True,pixel_color_identity_verified=True,
        fixed_piece_banks_unchanged=not permute_banks,fixed_piece_bank_permutation=banks,
        math_eligibility_preserved=True,palette_write_lifetimes_unchanged=True)
    payload=dict(pieces=result['pieces'],pixel_masks=result['piece_pixel_masks'],trace=result['trace'])
    if result.get('scanline_math_controls_source_bound'):payload.update(selected_modes=result['selected_modes'],compiled_color_window_descriptors=result['compiled_color_window_descriptors'])
    result.update(physical_slot_layout=report,prepared_dma_packets=packets,native_presentation_proven=False,
        input_compiled_schedule_sha256=source.get('compiled_schedule_sha256'),
        compiled_schedule_sha256=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest(),
        compiled_indices_sha256=hashlib.sha256(indices.tobytes()).hexdigest(),
        compiled_transfer_descriptor_sha256=hashlib.sha256(json.dumps(packets,sort_keys=True).encode()).hexdigest())
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--schedule',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--time-limit',type=float,default=30)
    p.add_argument('--permute-banks',action='store_true',help='Jointly permute fixed banks within source color-math eligibility.')
    a=p.parse_args();result=optimize(json.loads(a.schedule.read_text()),a.time_limit,a.permute_banks)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result.get('physical_slot_layout',result)))


if __name__=='__main__':main()
