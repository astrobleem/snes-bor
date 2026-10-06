"""Offline lossless BG tile residency with preload and commit classification.

Tiles used by the displayed frame stay pinned during preload. Writes replacing
those tiles are classified as commit traffic. Every compiled map is replayed
against complete resident tile identities, not just tile-count estimates.
"""
import argparse
from bisect import bisect_right
import hashlib
import json
from pathlib import Path
import numpy as np
from bg_component_cache import row_transfer


def encode(tile,bpp):
    data=bytearray(8*bpp)
    for row in range(8):
        for plane in range(bpp):
            data[(plane//2)*16+row*2+plane%2]=sum(((int(tile[row,col])>>plane)&1)<<(7-col) for col in range(8))
    return bytes(data)


def plan_plane(frames,bpp,capacity):
    if not 1<=capacity<=1024:raise ValueError('COMPONENT_RESIDENT_TILE_CAPACITY')
    unique={};tiles=[];ids=[];uses={}
    for index,frame in enumerate(frames):
        if frame.shape!=(224,256):raise ValueError('COMPONENT_RESIDENT_VIEWPORT')
        grid=np.zeros((28,32),dtype=np.int32)
        for y in range(28):
            for x in range(32):
                tile=frame[y*8:y*8+8,x*8:x*8+8];raw=tile.tobytes()
                if raw not in unique:unique[raw]=len(tiles);tiles.append(tile.copy())
                grid[y,x]=unique[raw]
        required=set(map(int,grid.flat))
        if len(required)>capacity:raise ValueError('COMPONENT_SINGLE_FRAME_TILE_CAPACITY:'+str(index)+':'+str(len(required)))
        for tile in required:uses.setdefault(tile,[]).append(index)
        ids.append(grid)
    resident=[None]*capacity;previous=set();plans=[];maps=[]
    def next_use(tile,index):
        if tile is None:return len(frames)+1
        sequence=uses[tile];position=bisect_right(sequence,index)
        return sequence[position] if position<len(sequence) else len(frames)+1
    for index,grid in enumerate(ids):
        required=set(map(int,grid.flat));present={tile:slot for slot,tile in enumerate(resident) if tile is not None}
        missing=sorted(required-set(present));writes=[]
        victims=sorted((slot for slot,tile in enumerate(resident) if tile not in required),
                       key=lambda slot:(resident[slot] in previous,-next_use(resident[slot],index),slot))
        if len(victims)<len(missing):raise AssertionError('COMPONENT_RESIDENCY_ALLOCATION')
        for tile,slot in zip(missing,victims):
            old=resident[slot]
            phase='BOOT' if index==0 else 'COMMIT' if old in previous else 'PRELOAD'
            writes.append(dict(slot=slot,tile=tile,old_tile=old,phase=phase,bytes=8*bpp))
            resident[slot]=tile;present[tile]=slot
        tilemap=np.zeros((32,32),dtype='<u2')
        for y in range(28):
            for x in range(32):tilemap[y,x]=present[int(grid[y,x])]
        recovered=np.empty_like(frames[index])
        for y in range(28):
            for x in range(32):
                tile=resident[int(tilemap[y,x])]
                if tile!=int(grid[y,x]):raise AssertionError('COMPONENT_STALE_TILE_IDENTITY')
                recovered[y*8:y*8+8,x*8:x*8+8]=tiles[tile]
        if not np.array_equal(recovered,frames[index]):raise AssertionError('COMPONENT_PIXEL_INDEX_IDENTITY')
        plans.append(dict(index=index,required_tiles=len(required),writes=writes,
                          preload_bytes=sum(w['bytes'] for w in writes if w['phase']=='PRELOAD'),
                          commit_bytes=sum(w['bytes'] for w in writes if w['phase']=='COMMIT'),
                          boot_bytes=sum(w['bytes'] for w in writes if w['phase']=='BOOT'),
                          pixel_index_identity_verified=True))
        maps.append(tilemap);previous=required
    return dict(capacity=capacity,bpp=bpp,unique_sequence_tiles=len(tiles),frames=plans),maps,b''.join(encode(tile,bpp) for tile in tiles)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--sequence',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--share-offset-map',action='store_true',help='Alias Mode4 disabled offset-control words with unflipped BG1 tilemap')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    sequence=json.loads((a.sequence/'report.json').read_text());frames=[Path(f['report']).parent for f in sequence['frames']]
    if not sequence['all_offline_schedules_proven']:raise ValueError('COMPONENT_UNPROVEN_SEQUENCE')
    high=[np.fromfile(f/'indices.bin',dtype=np.uint8).reshape(224,256)+3 for f in frames]
    low=[np.fromfile(f/'low_indices.bin',dtype=np.uint8).reshape(224,256) for f in frames]
    high_plan,high_maps,high_chr=plan_plane(high,8,768 if a.share_offset_map else 736);low_plan,low_maps,low_chr=plan_plane(low,2,768)
    if a.share_offset_map and any(np.any(m&0x6000) for m in high_maps):raise ValueError('COMPONENT_OFFSET_ALIAS_ENABLE_BITS')
    (a.output/'high-tiles.chr').write_bytes(high_chr);(a.output/'low-tiles.chr').write_bytes(low_chr)
    for index,(h,l) in enumerate(zip(high_maps,low_maps)):
        (a.output/f'{index:02d}-high.map').write_bytes(h.tobytes());(a.output/f'{index:02d}-low.map').write_bytes(l.tobytes())
    transitions=[]
    for index in range(1,len(frames)):
        transfers=[t for t in (row_transfer(high_maps[index-1],high_maps[index],0xf000),
                              row_transfer(low_maps[index-1],low_maps[index],0xf800)) if t]
        preload=high_plan['frames'][index]['preload_bytes']+low_plan['frames'][index]['preload_bytes']
        commit=high_plan['frames'][index]['commit_bytes']+low_plan['frames'][index]['commit_bytes']
        map_bytes=sum(t['bytes'] for t in transfers)
        transitions.append(dict(from_frame=index-1,to_frame=index,preload_chr_bytes=preload,
                                commit_chr_bytes=commit,tilemap_bytes=map_bytes,palette_restore_bytes=472,
                                total_transition_bytes=preload+commit+map_bytes+472,
                                commit_transfer_bytes=commit+map_bytes+472,tilemap_transfers=transfers))
    result=dict(schema='BYOR_COMPONENT_RESIDENCY_SEQUENCE_V1',high=high_plan,low=low_plan,transitions=transitions,
                allocation=dict(high_chr=[0,49152 if a.share_offset_map else 47104],zero_offset_map=[61440,63488] if a.share_offset_map else [47104,49152],low_chr=[49152,61440],
                                high_map=[61440,63488],low_map=[63488,65536]),
                offset_map_aliases_bg1=a.share_offset_map,
                peak_preload_chr_bytes=max(t['preload_chr_bytes'] for t in transitions),
                peak_commit_transfer_bytes=max(t['commit_transfer_bytes'] for t in transitions),
                peak_total_transition_bytes=max(t['total_transition_bytes'] for t in transitions),
                sequence_tiles_sha256=dict(high=hashlib.sha256(high_chr).hexdigest(),low=hashlib.sha256(low_chr).hexdigest()),
                no_color_reduction=True,all_pixel_index_identities_verified=True,native_refill_admitted=False,
                scope='Offline fixed-pose sequence residency; no online compositing, source cadence or production DMA admission.')
    (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('high','low','transitions')}))


if __name__=='__main__':main()
