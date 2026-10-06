"""Lossless fixed-context hybrid tile residency and transfer deadline candidate."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from bg_component_residency import plan_plane
from bg_component_cache import row_transfer,sparse_transfers
from bg_component_deadlines import derive_jobs,schedule,replay


def static_obj_atlas(folders,reports):
    if len({r['static_obj_assignment_sha256'] for r in reports})!=1:
        raise ValueError('HYBRID_STATIC_POSES_CHANGED')
    if any(r['obj_static_palettes']!=reports[0]['obj_static_palettes'] for r in reports):
        raise ValueError('HYBRID_OBJ_PALETTE_IDENTITY_CHANGED')
    keys=[];edges={};per_frame=[]
    for folder,r in zip(folders,reports):
        oam=(folder/'oam.bin').read_bytes();data=(folder/'obj_chr.bin').read_bytes();frame=[]
        for i in range(r['native_obj_entries']):
            q=bytearray(oam[i*4:i*4+4]);base=q[2];q[2]=0
            xhigh=(oam[512+i//4]>>((i%4)*2))&1
            raw=b''.join(data[(base+ty*16+tx)*32:(base+ty*16+tx+1)*32]
                         for ty in range(4) for tx in range(2))
            key=(bytes(q),xhigh,raw)
            if key not in edges:keys.append(key);edges[key]=set()
            frame.append(key)
        for i,key in enumerate(frame):edges[key].update(frame[i+1:])
        per_frame.append(frame)
    order=[];pending=list(keys)
    while pending:
        available=[k for k in pending if not any(k in edges[p] for p in pending)]
        if not available:raise ValueError('HYBRID_STATIC_OAM_ORDER_CYCLE')
        key=available[0];pending.remove(key);order.append(key)
    if len(order)>32:raise ValueError('HYBRID_STATIC_OBJ_ATLAS_CAPACITY')
    atlas=bytearray(((len(order)+7)//8)*2048);oam=bytearray(544)
    for i in range(128):oam[i*4+1]=224
    for i,(q,xhigh,raw) in enumerate(order):
        base=(i//8)*64+(i%8)*2;record=bytearray(q);record[2]=base
        oam[i*4:i*4+4]=record;oam[512+i//4]|=xhigh<<((i%4)*2)
        for ty in range(4):
            for tx in range(2):
                start=(base+ty*16+tx)*32;part=(ty*2+tx)*32
                atlas[start:start+32]=raw[part:part+32]
    # An object omitted by per-frame culling is safe to retain only when every
    # one of its opaque on-screen pixels is hidden by a promoted BG tile.
    for folder,frame in zip(folders,per_frame):
        promoted=np.fromfile(folder/'promoted.bin',dtype=np.bool_).reshape(28,32)
        for q,xhigh,raw in set(order)-set(frame):
            x=q[0]+256*xhigh;x=x if x<256 else x-512;y=q[1]
            for yy in range(32):
                for xx in range(16):
                    wx=x+xx;wy=y+yy
                    if not 0<=wx<256 or not 0<=wy<224:continue
                    tile=(yy//8*2+xx//8)*32;index=0
                    for plane in range(4):
                        value=raw[tile+(plane//2)*16+(yy%8)*2+plane%2]
                        index|=((value>>(7-xx%8))&1)<<plane
                    if index and not promoted[wy//8,wx//8]:
                        raise AssertionError('HYBRID_RETAINED_OBJ_PIXEL_EXPOSED')
    return bytes(atlas),bytes(oam),len(order)


def subdivide_static_obj(atlas,oam,count):
    """Legal OBSEL 0: dense 16x16 objects plus nonempty 8x8 pieces."""
    objects=[];large=[];small=[]
    for i in range(count):
        q=oam[i*4:i*4+4];base=q[2];xh=(oam[512+i//4]>>((i%4)*2))&1
        x=q[0]+256*xh;x=x if x<256 else x-512
        for half in range(2):
            tiles=[atlas[(base+(half*2+ty)*16+tx)*32:(base+(half*2+ty)*16+tx+1)*32]
                   for ty in range(2) for tx in range(2)]
            if all(any(t) for t in tiles):
                item=dict(x=x,y=q[1]+half*16,attr=q[3],large=True,tiles=tiles)
                large.append(item);objects.append(item)
            else:
                for j,tile in enumerate(tiles):
                    if any(tile):
                        item=dict(x=x+(j%2)*8,y=q[1]+half*16+(j//2)*8,
                            attr=q[3],large=False,tiles=[tile])
                        small.append(item);objects.append(item)
    data=bytearray(4096);used=set()
    for item in large:
        pos=next((n for n in range(112) if n%16<15 and not {n,n+1,n+16,n+17}&used),None)
        if pos is None:raise ValueError('HYBRID_SUBDIVIDED_ATLAS_CAPACITY')
        slots=[pos,pos+1,pos+16,pos+17];item['tile']=pos;used.update(slots)
        for slot,tile in zip(slots,item['tiles']):data[slot*32:(slot+1)*32]=tile
    for item in small:
        pos=next((n for n in range(128) if n not in used),None)
        if pos is None:raise ValueError('HYBRID_SUBDIVIDED_ATLAS_CAPACITY')
        item['tile']=pos;used.add(pos);data[pos*32:(pos+1)*32]=item['tiles'][0]
    if len(objects)>128:raise ValueError('HYBRID_SUBDIVIDED_OAM_CAPACITY')
    target=bytearray(544)
    for i in range(128):target[i*4+1]=224
    for i,item in enumerate(objects):
        target[i*4:i*4+4]=bytes([item['x']&255,item['y']&255,item['tile'],item['attr']])
        target[512+i//4]|=(((item['x']>>8)&1)|(2 if item['large'] else 0))<<((i%4)*2)
    sprites=[];slivers=[]
    for y in range(224):
        active=[item for item in objects if item['y']<=y<item['y']+(16 if item['large'] else 8)]
        sprites.append(len(active));slivers.append(sum(2 if item['large'] else 1 for item in active))
    if max(sprites)>32 or max(slivers)>34:raise ValueError('HYBRID_SUBDIVIDED_SCANLINE_CAPACITY')
    return bytes(data),bytes(target),dict(entries=len(objects),large_entries=len(large),small_entries=len(small),
        peak_sprites=max(sprites),peak_slivers=max(slivers),occupied_tiles=len(used),obsel=0)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sequence',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--window-master-clocks',type=int,default=45000)
    p.add_argument('--packet-setup-master-clocks',type=int,default=336)
    p.add_argument('--palette-allowance-master-clocks',type=int,default=5000)
    p.add_argument('--subdivide-static-obj',action='store_true')
    p.add_argument('--tile-layout',choices=('first','frequency'),default='first')
    p.add_argument('--share-low-offset-map',action='store_true')
    p.add_argument('--sparse-maps',action='store_true')
    p.add_argument('--low-slots',type=int,default=640)
    a=p.parse_args();inventory=json.loads((a.sequence/'report.json').read_text())
    if not inventory['complete'] or not inventory['all_frames_compiled']:
        raise ValueError('HYBRID_RESIDENCY_INCOMPLETE_INVENTORY')
    folders=[a.sequence/('frame-%02d'%r['frame']) for r in inventory['rows']]
    reports=[json.loads((f/'report.json').read_text()) for f in folders]
    a.output.mkdir(parents=True,exist_ok=True)
    atlas,oam,entries=static_obj_atlas(folders,reports)
    subdivision=None
    if a.subdivide_static_obj:
        atlas,oam,subdivision=subdivide_static_obj(atlas,oam,entries);entries=subdivision['entries']
    high_start=4096 if subdivision else 8192
    if not 1<=a.low_slots<=640:raise ValueError('HYBRID_LOW_TILE_CAPACITY')
    low_end=49152+a.low_slots*16
    high_capacity=(49152-high_start)//64
    high_slots=list(range(high_capacity))
    if a.share_low_offset_map:high_slots+=list(range((low_end-high_start+63)//64,(61440-high_start)//64))
    planes={};maps={};published={}
    for name,bpp,base in [('high',8,high_start),('low',2,49152)]:
        frames=[np.fromfile(f/(name+'.bin'),dtype=np.uint8).reshape(224,256) for f in folders]
        planes[name],maps[name],data=plan_plane(frames,bpp,len(high_slots) if name=='high' else a.low_slots,
            physical_slots=high_slots if name=='high' else None,initial_layout=a.tile_layout)
        (a.output/(name+'-tiles.chr')).write_bytes(data)
        published[name]=[]
        for i,m in enumerate(maps[name]):
            target=m.copy()
            if name=='high':
                if subdivision:target+=64
                mask=np.fromfile(folders[i]/'promoted.bin',dtype=np.bool_).reshape(28,32)
                target[:28]|=mask.astype(np.uint16)*0x2000
            published[name].append(target)
            (a.output/('%02d-%s.map'%(i,name))).write_bytes(target.tobytes())
    (a.output/'obj.chr').write_bytes(atlas);(a.output/'oam.bin').write_bytes(oam)
    starts=[(r['start_source_tick']*60+199)//200 for r in inventory['rows']]
    if any(b<=c for c,b in zip(starts,starts[1:])):raise ValueError('HYBRID_MULTIPLE_POSES_PER_FIELD')
    transitions=[];mandatory={}
    for i in range(1,len(folders)):
        if a.sparse_maps:
            transfers=[]
            for name,base in [('high',61440),('low',63488)]:
                transfers+=sparse_transfers(published[name][i-1],published[name][i],base,a.packet_setup_master_clocks)
        else:
            transfers=[t for t in [row_transfer(published['high'][i-1],published['high'][i],61440),
                row_transfer(published['low'][i-1],published['low'][i],63488)] if t]
        mandatory[starts[i]]=[dict(address=t['vram_byte_address'],bytes=t['bytes'],kind='tilemap') for t in transfers]
        transitions.append(dict(to_frame=i,tilemap_transfers=transfers,
            commit_chr_bytes=sum(planes[n]['frames'][i]['commit_bytes'] for n in planes),
            preload_chr_bytes=sum(planes[n]['frames'][i]['preload_bytes'] for n in planes)))
    jobs=derive_jobs(planes,maps,starts,bases={'high':high_start,'low':49152})
    fields,passed=schedule(jobs,mandatory,starts[-1],a.window_master_clocks,
        a.packet_setup_master_clocks,a.palette_allowance_master_clocks)
    identity=replay(fields,planes,maps,starts) if passed else False
    report=dict(schema='BYOR_HYBRID_FIXED_CONTEXT_RESIDENCY_V1',high=planes['high'],low=planes['low'],
        allocation=dict(obj_chr=[0,high_start],high_chr=[high_start,49152],low_chr=[49152,low_end],
            high_tail_chr=[(low_end+63)//64*64,61440] if a.share_low_offset_map else None,
            zero_offset_map=None if a.share_low_offset_map else [59392,61440],
            offset_control_map=[63488,65536] if a.share_low_offset_map else [59392,61440],
            high_map=[61440,63488],low_map=[63488,65536]),
        static_obj_entries=entries,static_obj_chr_bytes=len(atlas),static_obj_retention_verified=True,
        static_obj_subdivision=subdivision,
        initial_tile_layout=a.tile_layout,
        offset_map_aliases_bg2=a.share_low_offset_map,
        sparse_tilemap_transfers=a.sparse_maps,
        static_obj_chr_sha256=hashlib.sha256(atlas).hexdigest(),oam_sha256=hashlib.sha256(oam).hexdigest(),
        transitions=transitions,jobs=jobs,fields=fields,source_frame_start_fields=starts,
        source_clock_hypothesis=[200,60],window_master_clocks=a.window_master_clocks,
        packet_setup_master_clocks=a.packet_setup_master_clocks,palette_allowance_master_clocks=a.palette_allowance_master_clocks,
        resident_identity_replay=identity,status='OFFLINE_DEADLINE_CANDIDATE' if identity else 'GREEDY_DEADLINE_HEURISTIC_LIMIT',
        no_color_reduction=True,native_sequence_proven=False,live_world_bound=False,
        scope='Explicit fixed concurrent poses; rational display clock assumption and estimated transfer cost, no production deadline admission')
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','static_obj_entries','static_obj_chr_bytes','resident_identity_replay')}))
    if not identity:
        print(json.dumps(dict(first_failed_field=fields[-1]['field'],
            missed_jobs=len(fields[-1]['missed_deadline_jobs']),estimated_master_clocks=fields[-1]['estimated_master_clocks'])))


if __name__=='__main__':main()
