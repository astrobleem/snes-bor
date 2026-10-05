"""Bounded shared tile-cache admission and full-row tilemap DMA transitions."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def cache_plane(frames,bpp):
    lookup={};tiles=[];maps=[]
    for frame in frames:
        tilemap=np.zeros((32,32),dtype='<u2')
        for y in range(28):
            for x in range(32):
                tile=frame[y*8:y*8+8,x*8:x*8+8];key=tile.tobytes()
                if key not in lookup:
                    if len(tiles)>=1024:raise ValueError('BG_TILE_INDEX_CAPACITY')
                    encoded=bytearray(8*bpp)
                    for row in range(8):
                        for plane in range(bpp):
                            encoded[(plane//2)*16+row*2+plane%2]=sum(
                                ((int(tile[row,col])>>plane)&1)<<(7-col) for col in range(8))
                    lookup[key]=len(tiles);tiles.append(bytes(encoded))
                tilemap[y,x]=lookup[key]
        maps.append(tilemap)
    return b''.join(tiles),maps


def row_transfer(before,after,vram_base):
    rows=np.where(np.any(before!=after,axis=1))[0]
    if not len(rows):return None
    first,last=int(rows.min()),int(rows.max())
    raw=after[first:last+1].tobytes()
    return dict(vram_byte_address=vram_base+first*64,source_byte_offset=first*64,
                first_tile_row=first,last_tile_row=last,bytes=len(raw),
                sha256=hashlib.sha256(raw).hexdigest())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--frame',type=Path,action='append',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    high=[np.fromfile(f/'indices.bin',dtype=np.uint8).reshape(224,256)+3 for f in a.frame]
    low=[np.fromfile(f/'low_indices.bin',dtype=np.uint8).reshape(224,256) for f in a.frame]
    hchr,hmaps=cache_plane(high,8);lchr,lmaps=cache_plane(low,2)
    lowbase=((len(hchr)+8191)//8192)*8192
    offsetmap=next((((first+2047)//2048)*2048 for first,last in
                    ((len(hchr),lowbase),(lowbase+len(lchr),0xf000))
                    if ((first+2047)//2048)*2048+2048<=last),None)
    folder=a.output.with_suffix('');folder.mkdir(exist_ok=True)
    (folder/'high.chr').write_bytes(hchr);(folder/'low.chr').write_bytes(lchr)
    for i,(h,l) in enumerate(zip(hmaps,lmaps)):
        (folder/f'{i}-high.map').write_bytes(h.tobytes());(folder/f'{i}-low.map').write_bytes(l.tobytes())
    transitions=[]
    for i in range(1,len(a.frame)):
        transfers=[t for t in (row_transfer(hmaps[i-1],hmaps[i],0xf000),
                              row_transfer(lmaps[i-1],lmaps[i],0xf800)) if t]
        transitions.append(dict(from_frame=i-1,to_frame=i,transfers=transfers,
            tilemap_bytes=sum(t['bytes'] for t in transfers),chr_bytes=0,
            palette_restore_bytes=472,descriptors=len(transfers)))
    report=dict(status='BOUNDED_COMPONENT_TILE_CACHE',frames=[str(f) for f in a.frame],
        high_chr_bytes=len(hchr),low_chr_bytes=len(lchr),low_chr_vram_base=lowbase,
        offset_tilemap_vram_base=offsetmap,vram_admitted=(lowbase+len(lchr)<=0xf000 and offsetmap is not None),
        transitions=transitions,no_color_reduction=True,native_animation_admitted=False,
        scope='Offline cache and descriptor accounting; no preload, next-frame refill or production timing admission.')
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
