"""Exact explicit-scene OBJ demand input, not a native presentation verdict.

Literal final RGB555 words are banked fifteen at a time per row. Separate
eight-pixel masks retain a fixed OAM bank even when row membership changes.
This constructive input may exceed OAM/sprite/tile limits. Later geometry,
math/window and cache solvers must independently establish admissibility.
"""
import argparse,copy,hashlib,json
from pathlib import Path
import numpy as np
from raster_math_windows import compile_mask
from raster_obj_geometry import active_on_line,tile_slivers
from raster_slot_greedy import demand


def build(actors,metadata,background,expected):
    bg=np.asarray(background);gold=np.asarray(expected)
    if any(a.shape!=(224,256)or a.dtype.kind not in'ui'or np.any(a<0)or np.any(a>32767)for a in(bg,gold)):raise ValueError('LITERAL_DEMAND_RGB555_CONTEXT')
    coordinates={};sets=[set()for _ in range(224)]
    for i,a in enumerate(actors):
        pixels=np.asarray(a['pixels'])
        if pixels.ndim!=2 or pixels.dtype.kind not in'iu'or np.any(pixels<-1)or np.any(pixels>32767)or any(type(a[k])is not int for k in('left','top')):raise ValueError('LITERAL_DEMAND_ACTOR_PIXEL_DOMAIN')
        for ly,lx in np.argwhere(a['pixels']>=0):
            y,x=a['top']+int(ly),a['left']+int(lx);c=int(a['pixels'][ly,lx])
            if not 0<=y<224 or not 0<=x<256 or not 0<=c<32768 or(y,x)in coordinates:raise ValueError('LITERAL_DEMAND_PIXEL_OWNER')
            coordinates[y,x]=(i,c);sets[y].add(c)
    if not coordinates:raise ValueError('LITERAL_DEMAND_EMPTY_CONTEXT')
    if max(map(len,sets))>120:raise ValueError('LITERAL_DEMAND_CONSTRUCTION_ROW_CAPACITY_NOT_UNIVERSAL_REJECTION')
    state={b:[None]*15 for b in range(8)};trace=[];locations={};masks={}
    for y,cs in enumerate(sets):
        before=copy.deepcopy(state);events=[]
        for index,c in enumerate(sorted(cs)):
            b,s=divmod(index,15);locations[y,c]=(b,s+1)
            if state[b][s]!=c:
                events.append(dict(bank=b,slot=s+1,old=state[b][s],color=c,kind='literal_context_word'));state[b][s]=c
        trace.append(dict(scanline=y,resident_before=before,updates=events,colors_written=len(events),cgram_data_bytes=2*len(events),affected_banks=sorted({e['bank']for e in events})))
    for(y,x),(i,c)in coordinates.items():
        b,s=locations[y,c];gx=x//8*8;gy=y//8*8
        masks.setdefault((i,gx,gy,b),np.zeros((8,8),dtype=np.uint8))[y-gy,x-gx]=s
    pieces=[];packed=[]
    for(i,x,y,b),image in sorted(masks.items()):
        a=actors[i];pieces.append(dict(actor=i,x=x,y=y,local_x=x-a['left'],local_y=y-a['top'],width=8,height=8,bank=b))
        flat=image.flatten();packed.append(dict(width=8,height=8,pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex()))
    geometry=dict(oam_entries=len(pieces),peak_sprites=max(sum(active_on_line(p,y)for p in pieces)for y in range(224)),
        peak_tile_slivers=max(sum(tile_slivers(p)for p in pieces if active_on_line(p,y))for y in range(224)))
    admitted=geometry['oam_entries']<=128 and geometry['peak_sprites']<=32 and geometry['peak_tile_slivers']<=34
    windows={str(y):compile_mask([False]*256)for y in range(224)}
    r=dict(schema='BYOR_SOURCE_LITERAL_OBJ_DEMAND_V1',status='JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN',metadata=metadata,
        source_rgb555_sha256=hashlib.sha256(gold.astype('<u2').tobytes()).hexdigest(),pieces=pieces,piece_pixel_masks=packed,trace=trace,
        compiled_pixel_identity_verified=True,hardware_geometry_admitted=admitted,geometry=geometry,color_math='additive',
        selected_modes={str(y):'add'for y in range(224)},compiled_color_window_descriptors=windows,scanline_math_controls_source_bound=True,
        source_alpha_policy='EXACT_SOURCE_CONTEXT_PRECOMPOSITED_RGB555',alpha_compatibility_policy_selected=False,
        all_actor_visible_pixels_included=True,static_actor_palettes_reserved=False,source_visible_pixels=len(coordinates),
        foreground_full_frame_rgb555_colors=len(set().union(*sets)),foreground_peak_scanline_rgb555_colors=max(map(len,sets)),
        row_colors=[sorted(cs)for cs in sets],native_presentation_proven=False,live_compositor_admitted=False,universal_raster_rejected=False,no_color_reduction=True)
    _,_,decoded=demand(r);actual=bg.copy();seen=set()
    for p,image in zip(pieces,decoded):
        for ly,lx in np.argwhere(image>=0):
            y,x=p['y']+int(ly),p['x']+int(lx)
            if(y,x)in seen:raise AssertionError('LITERAL_DEMAND_REPLAY_OVERLAP')
            seen.add((y,x));actual[y,x]=image[ly,lx]
    if seen!=set(coordinates)or not np.array_equal(actual,gold):raise ValueError('LITERAL_DEMAND_SOURCE_OUTPUT_REPLAY')
    r['compiled_schedule_sha256']=hashlib.sha256(json.dumps(dict(pieces=pieces,masks=packed,trace=trace),sort_keys=True).encode()).hexdigest()
    r['source_output_pixels_replayed']=int(gold.size)
    r['input_construction_peak_writes']=max(row['colors_written']for row in trace[1:])
    r['input_construction_peak_cgram_bytes']=2*r['input_construction_peak_writes']
    r['construction_is_not_a_minimum_bandwidth_bound']=True
    r['actor_visible_context_demand']=[dict(actor=i,visible_pixels=sum(owner==i for owner,c in coordinates.values()),
        full_frame_rgb555_colors=len({c for owner,c in coordinates.values()if owner==i}),
        peak_scanline_rgb555_colors=max(len({c for(yy,x),(owner,c)in coordinates.items()if yy==y and owner==i})for y in range(224)))for i in range(len(actors))]
    r['color_lifetimes']=[dict(rgb555=c,required_scanlines=[y for y,cs in enumerate(sets)if c in cs])for c in sorted(set().union(*sets))]
    if not admitted:r['status']='POOL_CONSTRUCTION_FIXED_SMALL_GEOMETRY_OVERFLOW'
    return r


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in('source','stage','scene','output'):p.add_argument('--'+name,required=True)
    a=p.parse_args()
    from compiler import Source
    from source_scene_obj_raster import prepare
    from source_scene_bg import compose_rgb8
    from source_bg_feasibility import rgb555
    source=Source(a.source);scene=json.loads(Path(a.scene).read_text(encoding='utf-8'));actors,metadata,expected=prepare(source,a.stage,scene)
    r=build(actors,metadata,rgb555(compose_rgb8(source,a.stage,dict(scene,actors=[]))[0]),rgb555(expected))
    r.update(source_pak_sha256=hashlib.sha256(Path(a.source).read_bytes()).hexdigest(),source_scene_sha256=hashlib.sha256(Path(a.scene).read_bytes()).hexdigest())
    Path(a.output).write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:r[k]for k in('status','geometry','foreground_full_frame_rgb555_colors','foreground_peak_scanline_rgb555_colors','source_visible_pixels','source_rgb555_sha256','source_output_pixels_replayed')}))


if __name__=='__main__':main()
