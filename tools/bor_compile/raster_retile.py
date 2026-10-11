"""Retile exact source operands into legal small OBJ masks before bank assignment.

Grouping crosses earlier bank boundaries but preserves color-math eligibility.
Bank and row capacity, complete source operands and hardware geometry are replayed.
This offline construction does not admit native transfer timing.
"""
import argparse,copy,hashlib,json
from pathlib import Path
import numpy as np
from raster_slot_greedy import demand
from raster_palette import assign_banks,schedule as logical_schedule


def retile(source,origin=(0,0),lookahead=55,time_limit=30):
    if len(origin)!=2 or any(type(v)is not int or not 0<=v<8 for v in origin)or lookahead<0 or time_limit<=0:
        raise ValueError('RETILE_DOMAIN')
    _,_,images=demand(source);height=len(source['trace']);additive=source.get('color_math','additive')!='precomposited'
    groups={};original={};screen_points=set();ox,oy=origin
    for p,image in zip(source['pieces'],images):
        kind=p['bank']//4 if additive else 0
        allowed=set(p.get('allowed_banks',range(8)))&set(range(kind*4,kind*4+4)if additive else range(8))
        for ly,lx in zip(*np.where(image>=0)):
            ax,ay=int(p['local_x']+lx),int(p['local_y']+ly);sx,sy=int(p['x']+lx),int(p['y']+ly)
            point=p['actor'],ax,ay
            if point in original or(sy,sx)in screen_points:raise ValueError('RETILE_SOURCE_PIXEL_OVERLAP')
            original[point]=(int(image[ly,lx]),kind);screen_points.add((sy,sx))
            gx,gy=(ax-ox)//8*8+ox,(ay-oy)//8*8+oy
            key=p['actor'],kind,gx,gy,sx-ax,sy-ay
            if key not in groups:groups[key]=(np.full((8,8),-1,dtype=np.int32),allowed.copy())
            words,banks=groups[key];words[ay-gy,ax-gx]=int(image[ly,lx]);banks.intersection_update(allowed)
    pieces=[];words=[]
    for(actor,kind,gx,gy,left,top),(image,banks)in sorted(groups.items()):
        if not banks:raise ValueError('RETILE_NO_COMPATIBLE_BANK')
        pieces.append(dict(actor=actor,local_x=gx,local_y=gy,x=gx+left,y=gy+top,width=8,height=8,
            allowed_banks=sorted(banks),rows={gy+top+ly:sorted(set(map(int,row[row>=0])))for ly,row in enumerate(image)if np.any(row>=0)}))
        words.append(image)
    clip=source.get('horizontal_clip_limit_counted',False)
    def slivers(p):return int(not clip or p['x']==-256 or p['x']+8>0 and p['x']<256)
    geometry=dict(oam_entries=len(pieces),peak_sprites=max((sum(p['y']<=y<p['y']+8 for p in pieces)for y in range(height)),default=0),
        peak_tile_slivers=max((sum(slivers(p)for p in pieces if p['y']<=y<p['y']+8)for y in range(height)),default=0))
    report=dict(schema='BYOR_EXACT_OPERAND_RETILE_V1',origin=list(origin),geometry=geometry,
        input_geometry=source.get('geometry'),source_pixels=len(original),no_color_reduction=True,
        universal_raster_rejected=False,native_timing_admitted=False,solver_time_limit_per_class=time_limit)
    if geometry['oam_entries']>128 or geometry['peak_sprites']>32 or geometry['peak_tile_slivers']>34:
        return dict(report,status='RETILE_HARDWARE_GEOMETRY_LIMIT')
    assignment=[None]*len(pieces);solvers=[]
    for kind in(range(2)if additive else range(1)):
        indices=[i for i,p in enumerate(pieces)if p['allowed_banks'][0]//4==kind or not additive]
        if not indices:continue
        solved=assign_banks([pieces[i]for i in indices],list(range(4*kind,4*kind+4)if additive else range(8)),time_limit)
        solvers.append(solved)
        if solved['status']!='FIXED_BANK_ASSIGNMENT_PROVEN':return dict(report,status='RETILE_BANK_ASSIGNMENT_NO_CANDIDATE',solvers=solvers)
        for i,b in zip(indices,solved['assignment']):assignment[i]=b;pieces[i]['bank']=b
    trace,snapshots=logical_schedule(pieces,assignment,height,lookahead)
    state={b:[None]*15 for b in range(8)}
    for row in trace:
        row['resident_before']=copy.deepcopy(state)
        for b in range(8):row['retained'].setdefault(b,[])
        for e in row['updates']:state[e['bank']][e['slot']-1]=e['color']
    masks=[];indices=np.zeros((height,256),dtype=np.uint8)
    for p,image in zip(pieces,words):
        encoded=np.zeros((8,8),dtype=np.uint8)
        for ly,lx in zip(*np.where(image>=0)):
            y,x=p['y']+int(ly),p['x']+int(lx)
            slot=snapshots[y][p['bank']].index(int(image[ly,lx]))+1
            encoded[ly,lx]=slot;indices[y,x]=128+16*p['bank']+slot
        flat=encoded.flatten();masks.append(dict(width=8,height=8,packed_nibble_order='low then high',pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex()))
    result=copy.deepcopy(source)
    for key in('physical_slot_layout','prepared_dma_packets','bank_residency','bank_rebalance','bank_search','physical_slot_refinement','schedule_latency_requirement','geometry_compaction','bank_subdivision','bounded_subdivision_search','bank_lp_refinement'):result.pop(key,None)
    result.update(pieces=pieces,piece_pixel_masks=masks,trace=trace,geometry=geometry,piece_bank_assignment=assignment,
        mixed_small_size=8,mixed_large_size=16,obsel_mode=0,geometry_mode='SOURCE_EXACT_OPERAND_8X8_RETILE',
        write_budget=None,lookahead_lines=lookahead,prepared_dma_window_master_clocks=None,prepared_dma_partition_bound_enforced=False,
        native_presentation_proven=False,hardware_geometry_admitted=True,prepared_dma_window_is_optimistic_necessary_only=False,
        bank_assignment_authority='operand_retile',peak_scheduled_writes=max((r['colors_written']for r in trace[1:]),default=0),
        peak_cgram_data_bytes=max((r['cgram_data_bytes']for r in trace[1:]),default=0),average_writes=float(np.mean([r['colors_written']for r in trace[1:]])),
        compiled_indices_sha256=hashlib.sha256(indices.tobytes()).hexdigest())
    replay={}
    _,uses,replayed=demand(result)
    for p,image in zip(pieces,replayed):
        for ly,lx in zip(*np.where(image>=0)):replay[p['actor'],p['local_x']+int(lx),p['local_y']+int(ly)]=(int(image[ly,lx]),p['bank']//4 if additive else 0)
    if original!=replay:raise AssertionError('RETILE_INDEPENDENT_SOURCE_OPERAND_REPLAY')
    latency=max((min(t-row['scanline']for t in uses[e['bank']][e['color']]if t>=row['scanline'])for row in trace[1:]for e in row['updates']),default=0)
    if latency>lookahead:raise AssertionError('RETILE_PREFETCH_LATENCY')
    result.update(worst_scanline=1+int(np.argmax([r['colors_written']for r in trace[1:]])),maximum_noninitial_prefetch_latency_lines=latency,
        noninitial_prefetch_lookahead_enforced=True,noninitial_prefetch_latency_replayed=True,initial_palette_may_preload_entire_frame=True,
        schedule_latency_requirement=dict(maximum_noninitial_prefetch_lines=latency,initial_palette_may_preload_entire_frame=True))
    report.update(status='RETILED_FIXED_BANK_SOURCE_OPERANDS_PROVEN',solvers=solvers,source_operand_identity_verified=True,color_math_eligibility_verified=True,
        fixed_bank_per_piece=True,transparent_index_zero=True,opaque_words_use_nonzero_indices=True)
    result['operand_retile']=report
    payload=dict(pieces=pieces,pixel_masks=masks,trace=trace)
    if result.get('scanline_math_controls_source_bound'):payload.update(selected_modes=result['selected_modes'],compiled_color_window_descriptors=result['compiled_color_window_descriptors'])
    result['compiled_schedule_sha256']=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--origin',type=int,nargs=2,default=(0,0));p.add_argument('--lookahead',type=int,default=55);p.add_argument('--time-limit',type=float,default=30)
    a=p.parse_args();r=retile(json.loads(a.schedule.read_text()),a.origin,a.lookahead,a.time_limit);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r.get('operand_retile',r)))


if __name__=='__main__':main()
