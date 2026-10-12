"""Compile fixed-bank geometry witnesses into exact indexed masks and cache demand.

Compilation proves color and geometry identity, not transfer feasibility. A
restricted scanline witness remains restricted after compilation.
"""
import copy,hashlib,json
import numpy as np
from raster_palette import schedule
from raster_slot_greedy import demand
from raster_obj_math_cover import apply_math
from raster_math_windows import evaluate


def compile_witness(source,witness,background,expected,lookahead=16):
    if witness.get('status')!='FIXED_FRAME_BANK_GEOMETRY_AND_WORD_OPTIONS_PROVEN' or witness.get('source_rgb555_sha256')!=source.get('source_rgb555_sha256'):
        raise ValueError('FRAME_COMPILE_SOURCE_WITNESS')
    bg=np.asarray(background);gold=np.asarray(expected)
    if any(a.shape!=(224,256)or a.dtype.kind not in 'ui'or np.any(a>32767)for a in (bg,gold)):
        raise ValueError('FRAME_COMPILE_RGB555_CONTEXT')
    if hashlib.sha256(gold.astype('<u2').tobytes()).hexdigest()!=source['source_rgb555_sha256']:
        raise ValueError('FRAME_COMPILE_SOURCE_HASH')
    if source.get('color_math')!='additive'or not source.get('scanline_math_controls_source_bound'):
        raise ValueError('FRAME_COMPILE_SOURCE_CONTROLS')
    replay=source
    if source.get('status')=='POOL_CONSTRUCTION_FIXED_SMALL_GEOMETRY_OVERFLOW':
        if not source.get('compiled_pixel_identity_verified')or source.get('hardware_geometry_admitted'):
            raise ValueError('FRAME_COMPILE_OVERFLOW_IDENTITY')
        replay=dict(source,status='JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN')
    _,_,input_colors=demand(replay)
    first,last=witness.get('scanline_interval',[0,224])
    if type(first)is not int or type(last)is not int or not 0<=first<last<=224:
        raise ValueError('FRAME_COMPILE_INTERVAL')
    pieces=copy.deepcopy(witness['pieces']);seen=set();actual=bg.copy();colors=[]
    if not pieces or len(pieces)>128:raise ValueError('FRAME_COMPILE_OAM')
    sizes=set()
    for p in pieces:
        if any(type(p.get(k))is not int for k in ('x','y','width','height','bank'))or not 0<=p['bank']<8 or p['width']!=p['height']or p['width']not in(8,16,32)or not -256<=p['x']<256 or not -256<=p['y']<256:
            raise ValueError('FRAME_COMPILE_PIECE')
        sizes.add(p['width']);p['rows']={};colors.append(np.full((p['height'],p['width']),-1,dtype=np.int32))
        if p['bank']not in p.get('allowed_banks',range(8)):raise ValueError('FRAME_COMPILE_BANK_ELIGIBILITY')
    if sizes not in({8},{16},{32},{8,16},{8,32},{16,32}):raise ValueError('FRAME_COMPILE_OBSEL_PAIR')
    for q in witness['pixels']:
        y,x,b,c,i=(q[k]for k in ('y','x','bank','color','piece'))
        if any(type(v)is not int for v in (y,x,b,c,i))or not first<=y<last or not 0<=x<256 or not 0<=c<32768 or not 0<=i<len(pieces)or(y,x)in seen:
            raise ValueError('FRAME_COMPILE_PIXEL')
        p=pieces[i]
        if p['bank']!=b or not p['y']<=y<p['y']+p['height']or not p['x']<=x<p['x']+p['width']:
            raise ValueError('FRAME_COMPILE_FIXED_OWNER')
        seen.add((y,x));colors[i][y-p['y'],x-p['x']]=c;p['rows'].setdefault(y,set()).add(c)
        actual[y,x]=apply_math(c,int(bg[y,x]),source['selected_modes'][str(y)])if b>=4 and evaluate(source['compiled_color_window_descriptors'][str(y)],x)else c
    expected_points={(int(p['y']+y),int(p['x']+x))for p,image in zip(source['pieces'],input_colors)for y,x in zip(*np.where(image>=0))if first<=p['y']+y<last}
    if seen!=expected_points:raise ValueError('FRAME_COMPILE_OPAQUE_OWNERSHIP')
    if not np.array_equal(actual[first:last],gold[first:last]):raise ValueError('FRAME_COMPILE_SOURCE_OUTPUT_REPLAY')
    geometry=dict(oam_entries=len(pieces),peak_sprites=max(sum(p['y']<=y<p['y']+p['height']for p in pieces)for y in range(224)),
        peak_tile_slivers=max(sum(p['width']//8 for p in pieces if p['y']<=y<p['y']+p['height'])for y in range(224)))
    if geometry['peak_sprites']>32 or geometry['peak_tile_slivers']>34:raise ValueError('FRAME_COMPILE_HARDWARE_OVERFLOW')
    reservation=witness.get('geometry_reservation');combined=geometry.copy()
    if reservation is not None:
        if not isinstance(reservation,dict)or type(reservation.get('oam_entries'))is not int or not 0<=reservation['oam_entries']<=128 or any(not isinstance(reservation.get(k),list)or len(reservation[k])!=224 or any(type(v)is not int or not 0<=v<=limit for v in reservation[k])for k,limit in [('sprites_per_line',32),('tile_slivers_per_line',34)]):
            raise ValueError('FRAME_COMPILE_RESERVATION_DOMAIN')
        combined=dict(oam_entries=len(pieces)+reservation['oam_entries'],
            peak_sprites=max(sum(p['y']<=y<p['y']+p['height']for p in pieces)+reservation['sprites_per_line'][y]for y in range(224)),
            peak_tile_slivers=max(sum(p['width']//8 for p in pieces if p['y']<=y<p['y']+p['height'])+reservation['tile_slivers_per_line'][y]for y in range(224)))
        if combined['oam_entries']>128 or combined['peak_sprites']>32 or combined['peak_tile_slivers']>34:raise ValueError('FRAME_COMPILE_RESERVED_HARDWARE_OVERFLOW')
    for p in pieces:p['rows']={y:sorted(cs)for y,cs in p['rows'].items()}
    if 'joint_cache_trace'in witness:
        cache=witness['joint_cache_trace'];wanted_rows={}
        if not cache:raise ValueError('FRAME_COMPILE_CACHE_INTERVAL')
        cache_first,cache_last=cache[0]['scanline'],cache[-1]['scanline']
        if type(cache_first)is not int or type(cache_last)is not int or not first<=cache_first<=cache_last<last or [r['scanline']for r in cache]!=list(range(cache_first,cache_last+1))or any(not cache_first<=q['y']<=cache_last for q in witness['pixels']):
            raise ValueError('FRAME_COMPILE_CACHE_INTERVAL')
        for row in cache:
            wanted={int(b):set(cs)for b,cs in row['resident_colors'].items()}
            if set(wanted)!=set(range(8))or any(len(cs)>15 or any(type(c)is not int or not 0<=c<32768 for c in cs)for cs in wanted.values()):
                raise ValueError('FRAME_COMPILE_CACHE_CAPACITY')
            wanted_rows[row['scanline']]=wanted
        trace=[];states=[];slots={b:[None]*15 for b in range(8)}
        for y in range(224):
            wanted=wanted_rows[min(max(y,cache_first),cache_last)];before=copy.deepcopy(slots);events=[]
            for b in range(8):
                for c in sorted(wanted[b]-set(slots[b])):
                    slot=next(s for s,old in enumerate(slots[b])if old not in wanted[b])
                    events.append(dict(bank=b,slot=slot+1,old=slots[b][slot],color=c,
                        kind='required'if any(c in p['rows'].get(y,[])for p in pieces if p['bank']==b)else'prefetch'))
                    slots[b][slot]=c
            states.append(copy.deepcopy(slots))
            trace.append(dict(scanline=y,resident_before=before,retained={b:[c for c in before[b]if c is not None and c in slots[b]]for b in range(8)},
                evicted=[e['old']for e in events if e['old']is not None],prefetched=[e for e in events if e['kind']=='prefetch'],
                updates=events,colors_written=len(events),cgram_data_bytes=2*len(events),affected_banks=sorted({e['bank']for e in events})))
        if any(q['color']not in states[q['y']][q['bank']]for q in witness['pixels']):raise ValueError('FRAME_COMPILE_CACHE_PIXEL_IDENTITY')
    else:trace,states=schedule(pieces,[p['bank']for p in pieces],224,lookahead)
    for row in trace:row['resident_before']={b:row['resident_before'].get(b,[None]*15)for b in range(8)}
    uses={}
    for q in witness['pixels']:uses.setdefault((q['bank'],q['color']),set()).add(q['y'])
    latency=max((min((y for y in uses.get((e['bank'],e['color']),[])if y>=row['scanline']),default=row['scanline'])-row['scanline']
        for row in trace[1:]for e in row['updates']),default=0)
    masks=[]
    for p,image in zip(pieces,colors):
        indexed=np.zeros(image.shape,dtype=np.uint8)
        for ly,lx in zip(*np.where(image>=0)):indexed[ly,lx]=states[p['y']+int(ly)][p['bank']].index(int(image[ly,lx]))+1
        flat=indexed.flatten();masks.append(dict(width=p['width'],height=p['height'],pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex()))
    complete=(first,last)==(0,224)
    result={k:copy.deepcopy(source[k])for k in ('metadata','source_rgb555_sha256','selected_modes','compiled_color_window_descriptors','color_math','scanline_math_controls_source_bound','source_alpha_policy','alpha_compatibility_policy_selected')if k in source}
    result.update(status='JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN'if complete else'RESTRICTED_SCANLINE_DEMAND_ONLY',
        pieces=pieces,piece_pixel_masks=masks,trace=trace,geometry=geometry,hardware_geometry_admitted=True,
        compiled_pixel_identity_verified=complete,restricted_pixel_identity_verified=not complete,
        complete_source_frame_pixel_identity_proven=complete,outside_interval_pixels_relaxed=not complete,
        restricted_scanline_demand_interval=[first,last-1],source_output_pixels_replayed=(last-first)*256,
        peak_scheduled_writes=max(r['colors_written']for r in trace[1:]),lookahead_lines=None if 'joint_cache_trace'in witness else lookahead,
        maximum_noninitial_prefetch_latency_lines=latency,initial_palette_may_preload_entire_frame=True,
        supplied_joint_cache_residency_compiled='joint_cache_trace'in witness,
        source_underlay_rgb555_sha256=hashlib.sha256(bg.astype('<u2').tobytes()).hexdigest(),
        geometry_reservation=copy.deepcopy(reservation),combined_reserved_geometry=combined,reservation_palette_and_layer_demand_included=False,
        physical_transfer_and_native_timing_admitted=False,native_presentation_proven=False,no_color_reduction=True)
    _,_,replayed=demand(result,allow_restricted=True)
    if any(not np.array_equal(a,b)for a,b in zip(colors,replayed)):raise AssertionError('FRAME_COMPILE_INDEXED_PALETTE_REPLAY')
    result['compiled_indices_sha256']=hashlib.sha256(json.dumps(masks,sort_keys=True).encode()).hexdigest()
    result['compiled_schedule_sha256']=hashlib.sha256(json.dumps(dict(pieces=pieces,masks=masks,trace=trace),sort_keys=True).encode()).hexdigest()
    return result


def main():
    import argparse
    from pathlib import Path
    from compiler import Source
    from source_scene_obj_raster import prepare
    from source_scene_bg import compose_rgb8
    from source_bg_feasibility import rgb555
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('schedule','witness','source','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--stage',required=True);p.add_argument('--lookahead',type=int,default=16)
    a=p.parse_args();frame=json.loads(a.schedule.read_text(encoding='utf-8'));witness=json.loads(a.witness.read_text(encoding='utf-8'))
    if witness.get('source_input_sha256')!=hashlib.sha256(a.schedule.read_bytes()).hexdigest():raise ValueError('FRAME_COMPILE_INPUT_IDENTITY')
    source=Source(a.source);scene=frame['metadata']['scene'];_,metadata,expected=prepare(source,a.stage,scene)
    if metadata!=frame['metadata']:raise ValueError('FRAME_COMPILE_SOURCE_METADATA')
    background=rgb555(compose_rgb8(source,a.stage,dict(scene,actors=[]))[0])
    result=compile_witness(frame,witness,background,rgb555(expected),a.lookahead)
    result['source_pak_sha256']=hashlib.sha256(a.source.read_bytes()).hexdigest()
    result['input_geometry_witness_sha256']=hashlib.sha256(a.witness.read_bytes()).hexdigest()
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k]for k in ('status','geometry','source_output_pixels_replayed','peak_scheduled_writes','maximum_noninitial_prefetch_latency_lines','compiled_schedule_sha256')}))


if __name__=='__main__':main()
