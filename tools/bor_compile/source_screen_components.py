"""Offline fixed-context SCREEN inputs and checked component remapping.

Native arithmetic supplies the palette lookup key and both component indices.
One SCREEN layer and an immutable composed underlay are admitted here. Moving
world ownership and online palette admission remain separate capabilities.
"""
import hashlib
import struct
from unittest.mock import patch
import numpy as np
import source_scene_bg
from sa1_character_conversion import bitmap_bytes


def projection_tables():
    i=np.arange(65536,dtype=np.uint32)
    value=255-((255-(i&255))*(255-(i>>8))//255)
    return b''.join(a.astype(np.uint8).tobytes() for a in [value>>3,((value>>4)<<5)&255,
        (value>>7)|(((value>>3)&1)<<6),((value>>4)<<1)|(((value>>3)&1)<<7)])


def tile_cache(indices,bpp):
    tiles=[];known={};grid=np.empty((28,32),dtype=np.uint16)
    for y in range(28):
        for x in range(32):
            t=indices[y*8:y*8+8,x*8:x*8+8];raw=t.tobytes()
            if raw not in known:known[raw]=len(tiles);tiles.append(t.copy())
            grid[y,x]=known[raw]
    return bytearray(bitmap_bytes(np.array(tiles),bpp,1)),grid


def derive(source,stage,scene,high_indices,low_indices,expected_rgb555):
    original=source_scene_bg.overlay;captured=[]
    def overlay(canvas,indices,rgb,x,y,alpha=0,transparent=True):
        if alpha==1:
            if captured:raise ValueError('SCREEN_COMPONENT_SEQUENTIAL_LAYERS_UNBOUND')
            h,w=canvas.shape[:2];ih,iw=indices.shape
            x0=max(0,x);y0=max(0,y);x1=min(w,x+iw);y1=min(h,y+ih)
            mask=np.zeros((h,w),dtype=bool);s=np.zeros((h,w,3),dtype=np.uint8);d=canvas.copy()
            if x1>x0 and y1>y0:
                mask[y0:y1,x0:x1]=indices[y0-y:y1-y,x0-x:x1-x]!=0
                s[y0:y1,x0:x1]=rgb[y0-y:y1-y,x0-x:x1-x]
            captured.append((mask,s,d))
        return original(canvas,indices,rgb,x,y,alpha,transparent)
    with patch.object(source_scene_bg,'overlay',overlay):canvas,metadata=source_scene_bg.compose_rgb8(source,stage,scene)
    if len(captured)!=1 or canvas.shape!=(224,256,3):raise ValueError('SCREEN_COMPONENT_CONTEXT_DOMAIN')
    quantized=(canvas[:,:,0].astype(np.uint16)>>3)|((canvas[:,:,1].astype(np.uint16)>>3)<<5)|((canvas[:,:,2].astype(np.uint16)>>3)<<10)
    if not np.array_equal(quantized,expected_rgb555):raise ValueError('SCREEN_COMPONENT_SOURCE_CONTEXT_IDENTITY')
    mask,s,d=captured[0];computed=255-((255-s.astype(np.uint32))*(255-d.astype(np.uint32))//255)
    # Subsequent opaque foreground pixels replace the SCREEN result. Preserve
    # their exact final RGB8 identity through the zero-source SCREEN identity.
    occluded=mask&np.any(computed!=canvas,axis=2)
    s[occluded]=0;d[occluded]=canvas[occluded]
    high,high_map=tile_cache(high_indices,8);low,low_map=tile_cache(low_indices,2)
    key=(quantized&31)|(((quantized>>6)&15)<<5)|(((quantized>>11)&15)<<9)
    lookup=np.zeros((224,8192),dtype=np.uint8)
    for y in range(224):
        for color in set(map(int,key[y])):
            slots=set(map(int,high_indices[y][key[y]==color]))
            if len(slots)!=1:raise ValueError('SCREEN_COMPONENT_AMBIGUOUS_ACTIVE_SLOT')
            slot=slots.pop()
            if not 4<=slot<=239:raise ValueError('SCREEN_COMPONENT_PALETTE_DOMAIN')
            lookup[y,color]=slot
    records=bytearray();high_positions=set();low_positions=set()
    for y,x in zip(*np.nonzero(mask)):
        hi=int(high_map[y//8,x//8])*64+(y%8)*8+x%8
        lo=int(low_map[y//8,x//8])*16+(y%8)*2+(x%8)//4
        shift=(x%4)*2;clear=255^(3<<shift)
        high[hi]=0;low[lo]&=clear
        high_positions.add(hi);low_positions.add(lo)
        pairs=s[y,x].astype(np.uint16)|(d[y,x].astype(np.uint16)<<8)
        pointer=0xc80000+y*8192
        records.extend(struct.pack('<5HBBHBB',*map(int,pairs),hi,lo,shift*2,clear,pointer&65535,pointer>>16,0))
    if not records or len(records)>65536:raise ValueError('SCREEN_COMPONENT_RECORD_BANK_CAPACITY')
    report=dict(schema='BYOR_FIXED_SCREEN_COMPONENT_INPUT_V1',native_pixels=len(records)//16,
                foreground_replaced_pixels=int(np.count_nonzero(occluded)),high_tiles=len(high)//64,low_tiles=len(low)//16,
                distinct_high_bytes_invalidated=len(high_positions),distinct_low_bytes_invalidated=len(low_positions),
                high_bpp=8,low_bpp=2,no_color_reduction=True,source_layers=metadata['layers'],
                expected_rgb555_sha256=hashlib.sha256(expected_rgb555.astype('<u2').tobytes()).hexdigest(),
                scope='One SCREEN layer on an immutable source-derived context. No live underlay or online palette solver.')
    return bytes(records),lookup.tobytes(),bytes(high),bytes(low),report
