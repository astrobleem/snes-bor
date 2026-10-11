"""Compile a source-exact static Mode 3 BG1 underlay for OBJ math probes.

BG uses nonzero lower-half CGRAM indices; OBJ retains all upper-half words.
This offline asset proof grants no native math routing or streaming lease.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from compiler import Source
from source_scene_bg import compose_rgb8
from source_bg_feasibility import rgb555


def encode8(tile):
    data=bytearray(64)
    for plane in range(8):
        for y in range(8):
            data[16*(plane//2)+2*y+plane%2]=sum(((int(tile[y,x])>>plane)&1)<<(7-x)for x in range(8))
    return bytes(data)


def decode8(data):
    if len(data)!=64:raise ValueError('UNDERLAY_TILE_BYTE_COUNT')
    result=np.zeros((8,8),dtype=np.uint8)
    for y in range(8):
        for x in range(8):
            result[y,x]=sum(((data[16*(p//2)+2*y+p%2]>>(7-x))&1)<<p for p in range(8))
    return result


def compile_underlay(pixels):
    pixels=np.asarray(pixels)
    if pixels.ndim!=2 or pixels.dtype.kind not in 'ui' or np.any(pixels<0)or np.any(pixels>32767):raise ValueError('UNDERLAY_RGB555_DOMAIN')
    height,width=pixels.shape
    if not height or not width or width%8 or height%8 or width>256 or height>224:raise ValueError('UNDERLAY_VIEWPORT_DOMAIN')
    colors=np.unique(pixels)
    if len(colors)>127:raise ValueError('UNDERLAY_LOWER_CGRAM_CAPACITY')
    indices=np.searchsorted(colors,pixels).astype(np.uint8)+1
    lookup={};tiles=[];mapping=np.zeros((32,32),dtype='<u2')
    for y in range(0,height,8):
        for x in range(0,width,8):
            tile=encode8(indices[y:y+8,x:x+8])
            if tile not in lookup:lookup[tile]=len(tiles);tiles.append(tile)
            mapping[y//8,x//8]=lookup[tile]
    if len(tiles)>704:raise ValueError('UNDERLAY_BG1_CHR_VRAM_CAPACITY')
    palette=np.zeros(128,dtype='<u2');palette[1:len(colors)+1]=colors
    replay=np.zeros_like(pixels)
    for y in range(0,height,8):
        for x in range(0,width,8):
            decoded=decode8(tiles[int(mapping[y//8,x//8])])
            if np.any(decoded==0):raise AssertionError('UNDERLAY_VISIBLE_BACKDROP_INDEX')
            replay[y:y+8,x:x+8]=palette[decoded]
    if not np.array_equal(replay,pixels):raise AssertionError('UNDERLAY_CHR_MAP_PALETTE_SOURCE_REPLAY')
    data=b''.join(tiles);map_bytes=mapping.tobytes();palette_bytes=palette.tobytes()
    report=dict(schema='BYOR_STATIC_OBJ_MATH_UNDERLAY_V1',status='OFFLINE_BG1_CHR_MAP_PALETTE_SOURCE_IDENTITY_PROVEN',
        viewport=[width,height],colors=len(colors),unique_8x8_tiles=len(tiles),chr_bytes=len(data),map_bytes=len(map_bytes),palette_bytes=len(palette_bytes),
        bg_mode=3,bg1_chr_byte_range=[0,0xb000],bg1_map_byte_range=[0xb000,0xb800],obj_chr_byte_range=[0xc000,0x10000],
        bg_palette_word_range=[1,len(colors)],obj_palette_word_range=[128,255],visible_nonzero_bg_indices_verified=True,
        source_rgb555_sha256=hashlib.sha256(pixels.astype('<u2').tobytes()).hexdigest(),
        chr_sha256=hashlib.sha256(data).hexdigest(),map_sha256=hashlib.sha256(map_bytes).hexdigest(),palette_sha256=hashlib.sha256(palette_bytes).hexdigest(),
        source_pixel_identity_verified=True,no_color_reduction=True,native_presentation_proven=False,source_alpha_math_routing_proven=False,
        scope='One actor-free static source viewport. No native routing, front-layer ownership, background streaming or joint runtime budget proof.')
    return report,data,map_bytes,palette_bytes


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--stage',required=True)
    p.add_argument('--scene',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();scene=dict(json.loads(a.scene.read_text()),actors=[])
    pixels,metadata=compose_rgb8(Source(a.source),a.stage,scene)
    report,data,mapping,palette=compile_underlay(rgb555(pixels))
    report.update(metadata=metadata,source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest())
    a.output.mkdir(parents=True,exist_ok=True)
    for name,blob in (('bg1.chr',data),('bg1.map',mapping),('bg-lower.pal',palette)):(a.output/name).write_bytes(blob)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k!='metadata'}))


if __name__=='__main__':main()
