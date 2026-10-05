"""Lossless RGB555 BG framebuffer feasibility for explicit sampled contexts.

This probes resources, not authored stage placement or native compositing.
Source effect dimensions stay unchanged. No quantization is performed.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import numpy as np
from PIL import Image
from compiler import Source
from source_palette import model_palettes
from source_profile import document,discover
from raster_palette import schedule,bounded_schedule


def decode(source,path,palette=None):
    raw=source.read(source.image_path(path))
    with Image.open(io.BytesIO(raw)) as im:
        if im.mode!='P':raise ValueError('INDEXED_REQUIRED')
        indices=np.array(im)
        rgb=np.array(palette or im.getpalette(),dtype=np.int32).reshape(-1,3)[indices]
    return indices,rgb,hashlib.sha256(raw).hexdigest()


def rgb555(rgb):return (rgb[:,:,0]>>3)|((rgb[:,:,1]>>3)<<5)|((rgb[:,:,2]>>3)<<10)


def probe(source,model,frame,background,position=(80,90),size=(256,224),capacity=175,prefetch_budget=3,bounded=False,export=None):
    alpha=model['properties'].get('alpha',[])
    if not alpha or alpha[-1]['values']!=['1']:
        raise ValueError('SCREEN_BLEND_SOURCE_REQUIRED_FOR_THIS_CONTEXT_PROBE')
    authority=model_palettes(source,model)['base']
    indices,effect,effect_hash=decode(source,frame,authority['rgb8'])
    _,bg,bg_hash=decode(source,background)
    w,h=size;canvas=bg[:h,:w].copy();x,y=position
    eh,ew=indices.shape
    if x<0 or y<0 or x+ew>w or y+eh>h:raise ValueError('EFFECT_CLIPPED_IN_SAMPLE')
    under=canvas[y:y+eh,x:x+ew]
    # Build 4086 pixelformat.c _screen on 8-bit source channels.
    blended=255-((255-effect)*(255-under)//255)
    mask=indices!=0;under[mask]=blended[mask]
    expected=rgb555(canvas)
    lines=[sorted(set(map(int,row))) for row in expected]
    peak=max(map(len,lines)); union=len(set(map(int,expected.flat)))
    result=dict(background=background,background_sha256=bg_hash,effect_frame=frame,
        effect_sha256=effect_hash,position=list(position),effect_dimensions=[ew,eh],viewport=list(size),
        alpha='BOR4086_SCREEN_RGB8_THEN_RGB555_HIGH_BITS',full_frame_colors=union,
        peak_scanline_colors=peak,bg_opaque_slot_capacity=capacity,
        scope='Sampled background plus effect only; panel, frontpanel, actors and HUD not composited.',
        no_color_reduction=True,source_rgb555_sha256=hashlib.sha256(expected.astype('<u2').tobytes()).hexdigest())
    if peak>capacity:
        return dict(result,status='SAMPLE_BG_SCANLINE_CAPACITY_EXCEEDED')
    piece=dict(rows={y:cs for y,cs in enumerate(lines)})
    trace,states=schedule([piece],[0],h,lookahead=h,prefetch_write_budget=prefetch_budget,capacity=capacity)
    if bounded:
        solved=bounded_schedule([piece],[0],h,capacity,prefetch_budget,lookahead=h)
        if 'trace' not in solved:return dict(result,bounded_schedule=solved,status='SAMPLE_BG_BOUNDED_SCHEDULE_UNPROVEN')
        trace,states=solved['trace'],solved['states']
        result['bounded_solver']={k:v for k,v in solved.items() if k not in ('trace','states')}
    remapped=np.zeros(expected.shape,dtype=np.uint8);recovered=np.zeros_like(expected)
    for yy,row in enumerate(expected):
        for xx,c in enumerate(row):
            slot=states[yy][0].index(int(c));remapped[yy,xx]=slot+1;recovered[yy,xx]=states[yy][0][slot]
    if not np.array_equal(expected,recovered):raise AssertionError('BG_PIXEL_IDENTITY_FAULT')
    if export is not None:
        export=Path(export);export.mkdir(parents=True,exist_ok=True)
        (export/'expected.rgb555').write_bytes(expected.astype('<u2').tobytes())
        (export/'indices.bin').write_bytes(remapped.tobytes())
        (export/'initial.json').write_text(json.dumps(states[0][0])+'\n')
    tile_hashes=set()
    for ty in range(0,h,8):
        for tx in range(0,w,8):tile_hashes.add(remapped[ty:ty+8,tx:tx+8].tobytes())
    # Full 8bpp tile framebuffer uses one unique tile per cell, no dedup.
    result.update(status='SAMPLE_BG_PALETTE_SCHEDULE_PROVEN',trace=trace,
        peak_hblank_writes=max(r['colors_written'] for r in trace[1:]),
        peak_hblank_cgram_bytes=max(r['cgram_data_bytes'] for r in trace[1:]),
        frame_chr_bytes=((w+7)//8)*((h+7)//8)*64,
        deduplicated_chr_bytes=64*len(tile_hashes),unique_8bpp_tiles=len(tile_hashes),
        frame_tilemap_bytes=32*32*2,
        effect_dirty_tile_bytes=((ew+7)//8+1)*((eh+7)//8+1)*64,
        pixel_identity_verified=True,indices_sha256=hashlib.sha256(remapped.tobytes()).hexdigest(),
        initial_palette_bytes=trace[0]['cgram_data_bytes'],lookahead_lines=h,
        prefetch_write_budget=prefetch_budget,
        runtime_compositor_proven=False,native_transfer_admitted=False)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--model',required=True)
    p.add_argument('--frame',required=True);p.add_argument('--background',required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--bounded',action='store_true')
    p.add_argument('--capacity',type=int,default=175);p.add_argument('--write-budget',type=int,default=3);args=p.parse_args()
    s=Source(args.source);docs={k:document(s,n) for k,(n,_) in s.index.items() if k.endswith('.txt')}
    model=next(m for m in discover(s,docs)['models'] if m['declaration']==args.model)
    r=probe(s,model,args.frame,args.background,bounded=args.bounded,capacity=args.capacity,prefetch_budget=args.write_budget,export=args.output.with_suffix(''))
    args.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k!='trace'},indent=2))


if __name__=='__main__':main()
