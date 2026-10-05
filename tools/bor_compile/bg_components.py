"""Lossless RGB555 decomposition for Mode 3/4 BG1+BG2 additive color math.

All five bits of every channel survive: high and low components have disjoint
bits, so native addition reconstructs the original color without clipping.
BG2 uses one 2bpp/4bpp palette; BG1 uses remaining admitted CGRAM entries.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from raster_palette import bounded_schedule


def split_pixels(pixels,bits=(1,1,2)):
    if sum(bits)>4 or any(b<0 or b>5 for b in bits):raise ValueError('LOW_COMPONENT_4BPP_LIMIT')
    r,g,b=bits;mask=((1<<r)-1)|(((1<<g)-1)<<5)|(((1<<b)-1)<<10)
    low=pixels&mask;high=pixels&(~mask&32767)
    indices=(low&31)|(((low>>5)&31)<<r)|(((low>>10)&31)<<(r+g))
    palette=[(i&((1<<r)-1))|(((i>>r)&((1<<g)-1))<<5)|(((i>>(r+g))&((1<<b)-1))<<10)
             for i in range(1<<sum(bits))]
    recovered=high+np.array(palette)[indices]
    if not np.array_equal(pixels,recovered):raise AssertionError('RGB555_COMPONENT_IDENTITY')
    return high,indices.astype(np.uint8),palette


def compile_frame(pixels,bits=(1,1,2),capacity=224,write_budget=1,shared_schedule=None):
    if pixels.shape!=(224,256) or capacity>252 or capacity<1:raise ValueError('BG_COMPONENT_FRAME_CONTRACT')
    high,low_indices,low_palette=split_pixels(pixels,bits)
    if capacity+len(low_palette)>240:raise ValueError('COMPONENT_PALETTE_HUD_RESERVATION_LIMIT')
    colors=sorted(set(map(int,high.flat)))
    if shared_schedule is not None:
        if 'states' not in shared_schedule:raise ValueError('SHARED_COMPONENT_SCHEDULE_UNPROVEN')
        states=shared_schedule['states'];trace=shared_schedule['trace'];initial=states[0][0]
        if len(states)!=224 or len(trace)!=224 or any(len(s[0])!=capacity for s in states):
            raise ValueError('SHARED_COMPONENT_SCHEDULE_CAPACITY')
        if any(t['colors_written']>write_budget for t in trace[1:]):
            raise ValueError('SHARED_COMPONENT_SCHEDULE_WRITE_BUDGET')
        solver={k:v for k,v in shared_schedule.items() if k not in ('states','trace')}
    elif len(colors)<=capacity:
        initial=colors+[None]*(capacity-len(colors));states=[{0:list(initial)} for _ in range(224)]
        trace=[dict(scanline=y,updates=[],colors_written=0,cgram_data_bytes=0) for y in range(224)]
        solver=dict(status='STATIC_COMPONENT_PALETTE_PROVEN')
    else:
        pieces=[dict(rows={y:sorted(set(map(int,row))) for y,row in enumerate(high)})]
        solved=bounded_schedule(pieces,[0],224,capacity,write_budget,lookahead=224)
        if 'states' not in solved:return dict(status='BG_COMPONENT_SCHEDULE_UNPROVEN',solver=solved,
            full_frame_colors=len(set(map(int,pixels.flat))),high_component_colors=len(colors),no_color_reduction=True)
        states=solved['states'];trace=solved['trace'];initial=states[0][0]
        solver={k:v for k,v in solved.items() if k not in ('states','trace')}
    high_indices=np.array([[states[y][0].index(int(c))+1 for c in row] for y,row in enumerate(high)],dtype=np.uint8)
    recovered=np.array([[states[y][0][int(i)-1] for i in row] for y,row in enumerate(high_indices)],dtype=np.uint16)
    recovered=recovered+np.array(low_palette,dtype=np.uint16)[low_indices]
    if not np.array_equal(pixels,recovered):raise AssertionError('BG_COMPONENT_REMAP_IDENTITY')
    def unique_tiles(indices):return len({indices[y:y+8,x:x+8].tobytes() for y in range(0,224,8) for x in range(0,256,8)})
    low_bpp=2 if sum(bits)<=2 else 4
    high_chr=64*unique_tiles(high_indices);low_chr=(8*low_bpp)*unique_tiles(low_indices)
    low_base=((high_chr+8191)//8192)*8192
    offset_map=None
    if low_bpp==2:
        offset_map=next((((first+2047)//2048)*2048 for first,last in
                         ((high_chr,low_base),(low_base+low_chr,0xf000))
                         if ((first+2047)//2048)*2048+2048<=last),None)
    report=dict(status='LOSSLESS_BG_COMPONENT_SCHEDULE_PROVEN',low_bits=list(bits),
        bg_mode=4 if low_bpp==2 else 3,low_bpp=low_bpp,high_palette_start=len(low_palette),
        viewport=[256,224],high_opaque_capacity=capacity,high_component_colors=len(colors),
        full_frame_colors=len(set(map(int,pixels.flat))),low_component_palette=low_palette,
        peak_high_component_scanline_colors=max(len(set(map(int,row))) for row in high),
        solver=solver,trace=trace,peak_hblank_colors_written=max(t['colors_written'] for t in trace[1:]),
        initial=initial,high_chr_bytes=high_chr,low_chr_bytes=low_chr,low_chr_vram_base=low_base,
        tilemap_vram_bases=[0xf000,0xf800],offset_tilemap_vram_base=offset_map,
        vram_admitted=(low_base+low_chr<=0xf000 and (low_bpp!=2 or offset_map is not None)),
        pixel_identity_verified=True,no_color_reduction=True,native_admitted=False,
        expected_rgb555_sha256=hashlib.sha256(pixels.astype('<u2').tobytes()).hexdigest(),
        high_indices_sha256=hashlib.sha256(high_indices.tobytes()).hexdigest(),
        low_indices_sha256=hashlib.sha256(low_indices.tobytes()).hexdigest(),
        math='Each RGB555 channel = disjoint high component + low component, no saturation or rounding.')
    return report,high_indices,low_indices


def schedule_group(canvases,bits,capacity=236,write_budget=7,time_limit=60):
    """One resident schedule for a bounded group; unchanged pixels keep indices.

    Union admission is sufficient, not necessary. Failure does not reject
    per-frame schedules or a renderer with frame-specific palette identities.
    """
    if not canvases or any(p.shape!=(224,256) for p in canvases):
        raise ValueError('BG_COMPONENT_GROUP_CONTRACT')
    highs=[split_pixels(p,bits)[0] for p in canvases]
    rows={y:sorted({int(c) for high in highs for c in high[y]}) for y in range(224)}
    return bounded_schedule([dict(rows=rows)],[0],224,capacity,write_budget,
                            lookahead=224,time_limit=time_limit)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--canvas',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--capacity',type=int,default=224)
    p.add_argument('--write-budget',type=int,default=1);p.add_argument('--bits',default='1,1,2');a=p.parse_args()
    raw=a.canvas.read_bytes();pixels=np.frombuffer(raw,dtype='<u2').reshape(224,256)
    compiled=compile_frame(pixels,tuple(map(int,a.bits.split(','))),a.capacity,a.write_budget)
    if isinstance(compiled,tuple):
        report,high,low=compiled;folder=a.output.with_suffix('');folder.mkdir(parents=True,exist_ok=True)
        (folder/'indices.bin').write_bytes(high.tobytes());(folder/'low_indices.bin').write_bytes(low.tobytes())
        (folder/'expected.rgb555').write_bytes(raw);(folder/'initial.json').write_text(json.dumps(report.pop('initial'))+'\n')
    else:report=compiled
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='trace'}))


if __name__=='__main__':main()
