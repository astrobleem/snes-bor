"""Replay hybrid CHR/map transfers against the exact compiled pixel indices.

An atlas can be mathematically valid yet belong to a different palette-index
assignment. Validate the emitted presentation inputs, not only tile IDs.
"""
import hashlib,json
from pathlib import Path
import numpy as np


def decode_plane(vram,map_base,chr_base,bpp):
    words=np.frombuffer(vram[map_base:map_base+2048],dtype='<u2').reshape(32,32)[:28]
    tiles=np.empty((28,32,8,8),dtype=np.uint8)
    shifts=np.arange(7,-1,-1,dtype=np.uint8)
    for y,x in np.ndindex(28,32):
        word=int(words[y,x]);address=chr_base+(word&1023)*bpp*8
        raw=np.frombuffer(vram[address:address+bpp*8],dtype=np.uint8)
        if len(raw)!=bpp*8:raise ValueError('HYBRID_IDENTITY_CHR_RANGE')
        pixel=np.zeros((8,8),dtype=np.uint8)
        for bit in range(bpp):
            rows=raw[(bit//2)*16+(bit%2): (bit//2)*16+16:2]
            pixel|=((rows[:,None]>>shifts)&1)<<bit
        if word&0x4000:pixel=pixel[:,::-1]
        if word&0x8000:pixel=pixel[::-1]
        tiles[y,x]=pixel
    return tiles.transpose(0,2,1,3).reshape(224,256)


def replay(residency,plan,schedule,assets,cache):
    vram=bytearray(65536)
    high_base=plan['allocation']['high_chr'][0]
    for name,base in [('high',high_base),('low',49152)]:
        raw=(cache/f'{name}.chr').read_bytes();vram[base:base+len(raw)]=raw
    for name,base in [('high',61440),('low',63488)]:
        vram[base:base+2048]=(cache/f'0-{name}.map').read_bytes()
    chr_data={name:(residency/f'{name}-tiles.chr').read_bytes()for name in ('high','low')}
    starts=schedule['source_frame_start_fields'];frame=0;checked=set();identities=[]
    for row in schedule['fields']:
        while frame+1<len(starts)and starts[frame+1]<=row['field']:frame+=1
        if row['field']:
            for job in row['jobs']:
                size=job['bytes'];data=chr_data[job['plane']][job['tile']*size:(job['tile']+1)*size]
                if len(data)!=size:raise ValueError('HYBRID_IDENTITY_TRANSFER_LENGTH')
                vram[job['address']:job['address']+size]=data
            for job in row['mandatory']:
                name='high' if job['address']<63488 else 'low';base=61440 if name=='high' else 63488
                data=(residency/f'{frame:02d}-{name}.map').read_bytes()
                start=job['address']-base;size=job['bytes']
                vram[job['address']:job['address']+size]=data[start:start+size]
        # Future jobs can evict a tile during the last field of a pose.
        # Check every displayed field, not just the initial pose boundary.
        for name,map_base,chr_base,bpp in [('high',61440,0 if plan['static_obj_subdivision'] else high_base,8),('low',63488,49152,2)]:
            expected=np.fromfile(assets[frame]/('indices.bin'if name=='high'else'low_indices.bin'),dtype=np.uint8).reshape(224,256)
            if name=='high':expected=expected+3
            actual=decode_plane(vram,map_base,chr_base,bpp)
            mismatch=np.argwhere(actual!=expected)
            if len(mismatch):
                y,x=map(int,mismatch[0])
                raise ValueError(f'HYBRID_RESIDENCY_PIXEL_IDENTITY:field={row["field"]},frame={frame},plane={name},pixels={len(mismatch)},first={x},{y}')
            identities.append(dict(field=row['field'],frame=frame,plane=name,sha256=hashlib.sha256(actual.tobytes()).hexdigest()))
        checked.add(frame)
    if checked!=set(range(len(assets))):raise ValueError('HYBRID_IDENTITY_INCOMPLETE_FRAMES')
    return dict(schema='BYOR_HYBRID_RESIDENCY_PIXEL_IDENTITY_V1',status='PASS',frames=len(checked),fields=len(schedule['fields']),pixels_checked=len(identities)*224*256,identities=identities)
