"""Combine partial bank classes with complete source and transfer replay.

Only this combined result can prove a complete offline frame. Native timing,
production resource leases and gameplay admission remain separate.
"""
import argparse,copy,hashlib,json
from pathlib import Path
import numpy as np
from raster_window_slot_schedule import derive
from raster_slot_greedy import demand
from raster_slot_refine import verify_packets
from raster_physical_relabel import point_partition
from raster_math_windows import evaluate
from raster_obj_math_cover import apply_math
from raster_obj_compact import unpack


def combine(source,parts,background,expected,window=337):
    derive(source,background,expected)
    if len(parts)!=2 or window<1:raise ValueError('CLASS_COMBINE_DOMAIN')
    states=[];required={};uses={}
    for group,part in enumerate(parts):
        if part.get('status')!='RESTRICTED_BANK_CLASS_PALETTE_SCHEDULE'or part.get('bank_class_scope')!=group or part.get('source_rgb555_sha256')!=source['source_rgb555_sha256']or part.get('metadata')!=source.get('metadata')or part.get('input_compiled_schedule_sha256')!=source.get('compiled_schedule_sha256'):raise ValueError('CLASS_COMBINE_SOURCE_IDENTITY')
        if part.get('compiled_pixel_identity_verified')or part.get('complete_source_frame_pixel_identity_proven'):raise ValueError('CLASS_COMBINE_PARTIAL_SCOPE_REQUIRED')
        verify_packets(part);part_required,part_uses,_=demand(part,allow_restricted=True)
        for y,row in enumerate(part_required):
            for b in range(4*group,4*group+4):required[y,b]=set(row[b])
        for b in range(4*group,4*group+4):uses[b]=part_uses[b]
        if len(part['pieces'])!=len(source['pieces'])or len(part['trace'])!=len(source['trace'])or part['selected_modes']!=source['selected_modes']:raise ValueError('CLASS_COMBINE_GEOMETRY_OR_MODES')
        if any(np.any(unpack(mask))for p,mask in zip(source['pieces'],part['piece_pixel_masks'])if p['bank']//4!=group):raise ValueError('CLASS_COMBINE_EXCLUDED_PIXEL_DEMAND')
        state={b:[None]*15 for b in range(8)};rows=[]
        for row in part['trace']:
            for e in row['updates']:state[e['bank']][e['slot']-1]=e['color']
            rows.append(copy.deepcopy(state))
        states.append(rows)
    result=copy.deepcopy(source);result['piece_pixel_masks']=[]
    for i,original in enumerate(source['pieces']):
        group=original['bank']//4;part=parts[group];piece=part['pieces'][i]
        if {k:v for k,v in original.items()if k not in('rows','bank')}!={k:v for k,v in piece.items()if k not in('rows','bank')}or piece['bank']//4!=group or piece['bank']not in original.get('allowed_banks',range(8)):raise ValueError('CLASS_COMBINE_FIXED_PIECE_ELIGIBILITY')
        result['pieces'][i]=copy.deepcopy(piece);result['piece_pixel_masks'].append(copy.deepcopy(part['piece_pixel_masks'][i]))
    for key in('bank_residency','physical_slot_layout','physical_slot_refinement','optimistic_bank_order'):
        if key in result:result['input_'+key]=result.pop(key)
    trace=[];packets=[];before={b:[None]*15 for b in range(8)};latency=dead_writes=0
    for y in range(len(source['trace'])):
        state={b:states[b//4][y][b]for b in range(8)}
        events=[dict(bank=b,slot=s+1,old=before[b][s],color=c,kind='combined_class_palette')for b in range(8)for s,c in enumerate(state[b])if before[b][s]!=c]
        for e in events:
            future=[t for t in uses[e['bank']].get(e['color'],[])if t>=y]
            e['kind']='required'if e['color']in required.get((y,e['bank']),set())else'prefetch'if future else'unused_initial'if y==0 else'dead_palette_write'
            e['next_source_use_scanline']=min(future)if future else None
            if y and future:latency=max(latency,min(future)-y)
            if y and not future:dead_writes+=1
        trace.append(dict(scanline=y,resident_before=copy.deepcopy(before),retained={b:[c for c in before[b]if c is not None and c in state[b]]for b in range(8)},evicted=[e['old']for e in events if e['old']is not None],prefetched=[e for e in events if e['kind']=='prefetch'],updates=events,colors_written=len(events),cgram_data_bytes=2*len(events),affected_banks=sorted({e['bank']for e in events})))
        physical=[0 if s==0 else state[b][s-1]for b in range(8)for s in range(16)]
        span,groups=point_partition([16*e['bank']+e['slot']for e in events]if y else[])
        packets.append(dict(scanline=y,prepared_commit_span=span,packets=[dict(cgram_word_address=128+lo,word_count=hi-lo+1,data_hex=b''.join(physical[a].to_bytes(2,'little')for a in range(lo,hi+1)).hex())for lo,hi in groups]));before=state
    result.update(trace=trace,prepared_dma_packets=packets,compiled_color_window_descriptors=copy.deepcopy(parts[1]['compiled_color_window_descriptors']),piece_bank_assignment=[p['bank']for p in result['pieces']],native_presentation_proven=False)
    verify_packets(result);_,_,images=demand(result);original_images=demand(source)[2];replay=np.asarray(background,dtype=np.uint16).copy();indices=np.zeros_like(replay,dtype=np.uint8)
    for p,words,mask,old in zip(result['pieces'],images,result['piece_pixel_masks'],original_images):
        if not np.array_equal(words>=0,old>=0):raise AssertionError('CLASS_COMBINE_SOURCE_TRANSPARENCY')
        slots=unpack(mask)
        for ly,lx in zip(*np.where(words>=0)):
            y,x=p['y']+int(ly),p['x']+int(lx);word=int(words[ly,lx]);gate=p['bank']>=4 and evaluate(result['compiled_color_window_descriptors'][str(y)],x)
            replay[y,x]=apply_math(word,int(background[y,x]),result['selected_modes'][str(y)])if gate else word
            indices[y,x]=128+16*p['bank']+int(slots[ly,lx])
    if not np.array_equal(replay,expected):raise AssertionError('CLASS_COMBINE_COMPLETE_SOURCE_FRAME_REPLAY')
    peak=max(r['prepared_commit_span']for r in packets);writes=max(len(r['updates'])for r in trace[1:])
    result.update(peak_scheduled_writes=writes,peak_cgram_data_bytes=2*writes,average_writes=float(np.mean([len(r['updates'])for r in trace[1:]])),
                  worst_scanline=max(trace[1:],key=lambda r:len(r['updates']))['scanline'],input_compiled_schedule_sha256=source.get('compiled_schedule_sha256'),maximum_noninitial_prefetch_latency_lines=latency,schedule_latency_requirement=dict(maximum_noninitial_prefetch_lines=latency,initial_palette_may_preload_entire_frame=True))
    result['physical_slot_layout']=dict(schema='BYOR_BANK_CLASS_COMBINED_SCHEDULE_V1',status='SOURCE_EXACT_COMBINED_CLASS_PACKETS_PROVEN',
        complete_source_frame_pixel_identity_proven=True,pixel_color_identity_verified=True,all_packet_cgram_identities_verified=True,
        peak_prepared_commit_span=peak,peak_actual_palette_writes=writes,requested_window=window,target_window_met_by_all_packets=peak<window,
        peak_packet_data_bytes=max(sum(2*p['word_count']for p in r['packets'])for r in packets),peak_dma_chain_channels=max(max(0,2*len(r['packets'])-1)for r in packets),maximum_noninitial_prefetch_latency_lines=latency,noninitial_dead_palette_writes=dead_writes,native_timing_admitted=False,universal_raster_rejected=False,no_color_reduction=True)
    result['compiled_schedule_sha256']=hashlib.sha256(json.dumps(dict(pieces=result['pieces'],pixel_masks=result['piece_pixel_masks'],trace=trace,selected_modes=result['selected_modes'],compiled_color_window_descriptors=result['compiled_color_window_descriptors']),sort_keys=True).encode()).hexdigest()
    result['compiled_transfer_descriptor_sha256']=hashlib.sha256(json.dumps(packets,sort_keys=True).encode()).hexdigest()
    result['compiled_indices_sha256']=hashlib.sha256(indices.tobytes()).hexdigest()
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in('source','stage','scene','schedule','lower','upper','output'):p.add_argument('--'+name,required=True)
    p.add_argument('--window',type=int,default=337);a=p.parse_args()
    from compiler import Source
    from source_scene_obj_raster import prepare
    from source_scene_bg import compose_rgb8
    from source_bg_feasibility import rgb555
    source=Source(a.source);scene=json.loads(Path(a.scene).read_text());schedule=json.loads(Path(a.schedule).read_text())
    _,metadata,expected=prepare(source,a.stage,scene)
    if metadata!=schedule['metadata']:raise ValueError('CLASS_COMBINE_AUTHORED_METADATA')
    bg=rgb555(compose_rgb8(source,a.stage,dict(scene,actors=[]))[0]);parts=[json.loads(Path(path).read_text())for path in(a.lower,a.upper)]
    result=combine(schedule,parts,bg,rgb555(expected),a.window);Path(a.output).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['physical_slot_layout']))


if __name__=='__main__':main()
