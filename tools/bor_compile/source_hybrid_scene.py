"""Lossless BG effect/foreground tiles with ordinary opaque actors in OBJ.

Promoted BG tiles contain the final source composition for the entire tile,
including actor pixels outside the effect mask. This avoids tile-priority
holes. OBJ palette entries are excluded from the BG palette scheduler.
This is an explicit-pose offline resource proof, not native admission.
"""
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
import numpy as np
from compiler import Source
import source_scene_bg
from source_bg_feasibility import rgb555
from bg_components import split_pixels
from raster_palette import pieces_for_grid,split_scene_color_masks
from contiguous_palette import attempt


def capture(source,stage,scene):
    original=source_scene_bg.overlay;draws=[]
    def overlay(canvas,indices,rgb,x,y,alpha=0,transparent=True):
        h,w=canvas.shape[:2];ih,iw=indices.shape
        x0=max(0,x);y0=max(0,y);x1=min(w,x+iw);y1=min(h,y+ih)
        mask=np.zeros((h,w),dtype=bool)
        pixels=np.where(indices!=0,rgb555(rgb),-1)
        yy,xx=np.indices(indices.shape)
        pixels=np.where((xx+x>=0)&(xx+x<w)&(yy+y>=0)&(yy+y<h),pixels,-1)
        if x1>x0 and y1>y0:
            mask[y0:y1,x0:x1]=indices[y0-y:y1-y,x0-x:x1-x]!=0 if transparent else True
        draws.append(dict(mask=mask,pixels=pixels,x=x,y=y,alpha=alpha))
        return original(canvas,indices,rgb,x,y,alpha,transparent)
    with patch.object(source_scene_bg,'overlay',overlay): canvas,metadata=source_scene_bg.compose_rgb8(source,stage,scene)
    if canvas.shape!=(224,256,3) or len(draws)!=len(metadata['layers']):raise ValueError('HYBRID_CONTEXT_DOMAIN')
    return canvas,metadata,draws


def derive(source,stage,scene,banks,time_limit=20,span=15,first_bank=None):
    if not 1<=banks<=7:raise ValueError('HYBRID_OBJ_BANK_COUNT')
    first_bank=7-banks if first_bank is None else first_bank
    if not 0<=first_bank<=7-banks:raise ValueError('HYBRID_OBJ_BANK_RANGE')
    obj_banks=list(range(first_bank,first_bank+banks))
    canvas,metadata,draws=capture(source,stage,scene)
    empty=deepcopy(scene);empty['actors']=[]
    baseline,_=source_scene_bg.compose_rgb8(source,stage,empty)
    mask=np.zeros((224,256),dtype=bool);pieces=[];ordinary=[]
    for layer,draw in zip(metadata['layers'],draws):
        if layer['alpha']==1 or layer['kind']=='frontpanel':mask|=draw['mask']
        elif layer['kind'].startswith('actor:'):
            if layer['alpha']!=0:raise ValueError('HYBRID_ALPHA_VARIANT_UNBOUND')
            own=pieces_for_grid(draw['pixels'],tuple(scene.get('piece_size',[16,32])))
            for p in own:
                p['x']+=draw['x'];p['y']+=draw['y'];p['actor']=len(ordinary)
                # A single synthetic demand row enforces STATIC residency
                # across the whole frame. Actual rectangles retain hardware
                # OAM and per-line sliver constraints in the solver.
                p['rows']={0:sorted({c for cs in p['rows'].values() for c in cs})}
                p['allowed_banks']=obj_banks
            pieces.extend(own);ordinary.append(dict(layer=layer,draw=draw))
    promoted=mask.reshape(28,8,32,8).any(axis=(1,3))
    roi=np.repeat(np.repeat(promoted,8,axis=0),8,axis=1)
    expected=rgb555(canvas);base=rgb555(baseline);bg=np.where(roi,expected,base)
    predicted=base.copy()
    # Ordinary OBJ are below promoted tiles, above unpromoted BG.
    for actor in ordinary:
        d=actor['draw'];p=d['pixels'];h,w=p.shape
        x0=max(0,d['x']);y0=max(0,d['y']);x1=min(256,d['x']+w);y1=min(224,d['y']+h)
        if x1>x0 and y1>y0:
            part=p[y0-d['y']:y1-d['y'],x0-d['x']:x1-d['x']]
            region=predicted[y0:y1,x0:x1];region[part>=0]=part[part>=0]
    predicted[roi]=bg[roi]
    if not np.array_equal(predicted,expected):raise AssertionError('HYBRID_LAYER_PIXEL_IDENTITY')
    allocated=split_scene_color_masks(pieces,banks=tuple(obj_banks),time_limit=time_limit)
    public={k:v for k,v in allocated.items() if k not in ('pieces','assignment')}
    result=dict(schema='BYOR_HYBRID_EXPLICIT_SCENE_V1',scene=scene,source_layers=metadata['layers'],
        promoted_tiles=int(np.count_nonzero(promoted)),promoted_pixels=int(np.count_nonzero(roi)),
        obj_bank_count=banks,obj_banks=obj_banks,
        obj_palette_cgram_reserved=[128+bank*16+i for bank in obj_banks for i in range(1,16)],
        bg_owned_obj_transparent_entries=[128+bank*16 for bank in obj_banks],
        obj_color_math=False,bg_color_math='BG1 + BG2 disjoint RGB555 components',
        source_rgb555_sha256=hashlib.sha256(expected.astype('<u2').tobytes()).hexdigest(),
        bg_canvas_sha256=hashlib.sha256(bg.astype('<u2').tobytes()).hexdigest(),
        layer_pixel_identity_verified=True,obj_assignment=public,
        no_color_reduction=True,native_admitted=False,motu_gameplay_proven=False,
        scope='Explicit poses, camera zero, no HUD/shadow/quake; assumed Mode4 BG1 high above OBJ priority2, low below it; native priority and full publication budget unproven')
    if 'pieces' not in allocated:return result,None
    expanded=allocated['pieces'];assignment=allocated['assignment']
    palettes=[sorted({c for p,b in zip(expanded,assignment) if b==bank for c in p['rows'][0]}) for bank in obj_banks]
    if any(len(cs)>15 for cs in palettes):raise AssertionError('HYBRID_STATIC_OBJ_PALETTE_OVERFLOW')
    live=[sum(p['y']<=y<p['y']+p['height'] for p in expanded) for y in range(224)]
    slivers=[sum((p['width']+7)//8 for p in expanded if p['y']<=y<p['y']+p['height']) for y in range(224)]
    result.update(obj_geometry=dict(oam_entries=len(expanded),peak_sprites=max(live),peak_slivers=max(slivers)),
                  obj_static_palettes=palettes,obj_piece_banks=assignment,obj_pieces=expanded)
    high,low,low_palette=split_pixels(bg,(0,1,1));fixed=sorted(set(map(int,split_pixels(base,(0,1,1))[0].flat)))
    aliases={}
    obj_palette_words=[]
    for bank,colors in zip(obj_banks,palettes):
        for i,color in enumerate(colors,1):
            slot=128+bank*16+i;obj_palette_words.append(dict(slot=slot,color=color))
            if color in high:aliases.setdefault(color,slot)
    # A BG high component may use an OBJ-owned entry only when the complete
    # RGB555 word is identical. Never mask or alter the OBJ word to obtain it.
    fixed_free=[c for c in fixed if c not in aliases]
    reserved=set(result['obj_palette_cgram_reserved'])
    # OBJ transparency is selected by pixel index zero, independent of that
    # CGRAM entry's contents. Use these isolated entries for fixed BG colours;
    # the combined palette owner must preserve them during OBJ admission.
    special=result['bg_owned_obj_transparent_entries'][:len(fixed_free)]
    physical=special+[i for i in range(4,240) if i not in reserved and i not in special]
    if len(fixed_free)>=len(physical):
        result['bg_schedule']=dict(status='FIXED_BG_PREFIX_CAPACITY_LIMIT',fixed=len(fixed_free),capacity=len(physical));return result,None
    dynamic=physical[len(fixed_free):];breaks=[i for i in range(1,len(dynamic)) if dynamic[i]!=dynamic[i-1]+1]
    lines=[set(map(int,row))-set(fixed)-set(aliases) for row in high];attempts=[];solved=None
    for layout in ('first','persistent','last','frequency'):
        trial=attempt(lines,len(dynamic),span,layout,breaks=breaks)
        attempts.append({k:v for k,v in trial.items() if k not in ('states','trace')})
        if 'states' in trial:solved=trial;break
    result.update(bg_high_palette_capacity=len(physical),fixed_bg_colors=len(fixed),fixed_bg_exclusive_slots=len(fixed_free),
                  bg_exact_obj_palette_aliases=[dict(color=c,slot=slot) for c,slot in sorted(aliases.items())],dynamic_bg_slots=len(dynamic),
                  dynamic_physical_slots=dynamic,physical_burst_breaks=breaks,bg_attempts=attempts)
    if solved is None:result['bg_schedule']=dict(status='CONTIGUOUS_HEURISTIC_LIMIT');return result,None
    indices=np.zeros((224,256),dtype=np.uint8);trace=[];palette=[]
    for y,state in enumerate(solved['states']):
        colors=fixed_free+state;mapping={c:physical[i] for i,c in enumerate(colors) if c is not None};mapping.update(aliases)
        indices[y]=[mapping[int(c)] for c in high[y]]
        reverse={slot:c for c,slot in mapping.items()}
        recovered=np.array([reverse[int(i)] for i in indices[y]],dtype=np.uint16)+np.array(low_palette,dtype=np.uint16)[low[y]]
        if not np.array_equal(recovered,bg[y]):raise AssertionError('HYBRID_BG_PALETTE_IDENTITY')
        entry=solved['trace'][y];start=entry['start_slot']-1
        if y and entry['values']:
            destinations=dynamic[start:start+span]
            if destinations!=list(range(destinations[0],destinations[0]+span)):raise AssertionError('HYBRID_BURST_OBJ_OVERLAP')
            trace.append(dict(scanline=y,cgram_start=destinations[0],values=entry['values'],bytes=len(entry['values'])*2))
        if y==0:palette=[dict(slot=slot,color=c) for slot,c in zip(physical,colors)]+obj_palette_words
    result.update(bg_schedule=dict(status=solved['status'],span=span,peak_bytes=max((t['bytes'] for t in trace),default=0),
        trace=trace,initial=palette),bg_palette_pixel_identity_verified=True)
    # Cull only fully hidden colour-mask objects. Partial objects retain their
    # complete source-derived graphic; promoted BG tiles hide covered pixels.
    graphics=[]
    for q,bank in sorted(zip(expanded,assignment),key=lambda item:-item[0]['actor']):
        if (q['width'],q['height'])!=(16,32):raise ValueError('HYBRID_NATIVE_OBJ_SIZE_UNBOUND')
        d=ordinary[q['actor']]['draw'];pixels=d['pixels'];tile=np.zeros((32,16),dtype=np.uint8)
        colors=palettes[obj_banks.index(bank)];visible=False
        for y in range(32):
            for x in range(16):
                sx=q['x']+x-d['x'];sy=q['y']+y-d['y']
                if 0<=sy<pixels.shape[0] and 0<=sx<pixels.shape[1]:
                    c=int(pixels[sy,sx]);wx=q['x']+x;wy=q['y']+y
                    if c>=0 and c in q['rows'][0]:
                        tile[y,x]=colors.index(c)+1
                        if 0<=wx<256 and 0<=wy<224 and not roi[wy,wx]:visible=True
        if visible:graphics.append((q,bank,tile))
    if len(graphics)>32:raise ValueError('HYBRID_OBJ_FIRST_TABLE_CAPACITY')
    chr_data=bytearray(((len(graphics)+7)//8)*2048);oam=bytearray(544)
    for i in range(128):oam[i*4+1]=224
    for i,(q,bank,tile) in enumerate(graphics):
        base_tile=(i//8)*64+(i%8)*2
        for ty in range(4):
            for tx in range(2):
                number=base_tile+ty*16+tx;part=tile[ty*8:ty*8+8,tx*8:tx*8+8]
                for row in range(8):
                    for plane in range(4):
                        chr_data[number*32+(plane//2)*16+row*2+plane%2]=sum(((int(part[row,col])>>plane)&1)<<(7-col) for col in range(8))
        oam[i*4:i*4+4]=bytes([q['x']&255,q['y']&255,base_tile,0x20|(bank<<1)])
        oam[512+i//4]|=((q['x']>>8)&1)<<((i%4)*2)
    result.update(native_obj_entries=len(graphics),fully_bg_occluded_obj_entries=len(expanded)-len(graphics),
                  obj_chr_bytes=len(chr_data),native_obsel=0xc0)
    return result,dict(high=indices,low=low,bg=bg,expected=expected,promoted=promoted,
        obj_chr=np.frombuffer(chr_data,dtype=np.uint8),oam=np.frombuffer(oam,dtype=np.uint8))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
    p.add_argument('--stage',required=True);p.add_argument('--scene',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--obj-banks',type=int,required=True)
    p.add_argument('--time-limit',type=float,default=20);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    r,assets=derive(Source(a.source),a.stage,json.loads(a.scene.read_text()),a.obj_banks,a.time_limit)
    if assets:
        for name,value in assets.items():
            if name in ('bg','expected'):value=value.astype('<u2')
            (a.output/(name+'.bin')).write_bytes(value.tobytes())
    (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r.get(k) for k in ('obj_assignment','obj_geometry','promoted_tiles','bg_high_palette_capacity','fixed_bg_colors','dynamic_bg_slots')}))
    print(json.dumps({k:v for k,v in r.get('bg_schedule',{}).items() if k not in ('trace','initial')}))


if __name__=='__main__':main()
