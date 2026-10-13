"""Compile exact 8/16/32 OBJ masks to legal SNES size pairs and tile footprints.

Greedy aligned placement is a constructive proof only. Failure does not prove
VRAM infeasibility; overlapping or alternative placements may still work.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from raster_obj_compact import unpack


def encode(tile):
    data=bytearray(32)
    for y in range(8):
        for plane in range(4):data[(plane//2)*16+y*2+plane%2]=sum(((int(tile[y,x])>>plane)&1)<<(7-x)for x in range(8))
    return bytes(data)


def decode(data):
    return np.array([[sum(((data[(p//2)*16+y*2+p%2]>>(7-x))&1)<<p for p in range(4))for x in range(8)]for y in range(8)],dtype=np.uint8)


def compile(schedule,reserved=()):
    if schedule.get('status')!='JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN' or not schedule.get('compiled_pixel_identity_verified'):
        raise ValueError('OBJ_CHR_VALIDATED_SCHEDULE_REQUIRED')
    pieces=schedule['pieces'];images=[unpack(m)for m in schedule['piece_pixel_masks']]
    if len(pieces)!=len(images)or len(pieces)>128:raise ValueError('OBJ_CHR_OAM_CAPACITY')
    sizes={p['width']for p in pieces}
    if 8 in sizes and 16 in sizes and 32 in sizes:raise ValueError('OBJ_CHR_INCOMPATIBLE_GLOBAL_SIZE_PAIR')
    if schedule.get('obsel_mode')==6:
        small,big,mode=(16,32),(32,64),6
    elif schedule.get('mixed_large_size')==16:
        if schedule.get('mixed_small_size',8)!=8:raise ValueError('OBJ_CHR_INCOMPATIBLE_GLOBAL_SIZE_PAIR')
        small,big,mode=8,16,0
    elif schedule.get('mixed_small_size')==16:small,big,mode=16,32,3
    elif 16 in sizes:
        small,big,mode=(16,32,3)if 32 in sizes else(8,16,0)
    else:small,big,mode=8,32,1
    small_shape=small if isinstance(small,tuple)else(small,small)
    big_shape=big if isinstance(big,tuple)else(big,big)
    reserved=set(reserved)
    if any(not isinstance(c,int)or not 0<=c<512 for c in reserved):raise ValueError('OBJ_CHR_RESERVED_CELLS')
    blocks=[]
    for p,image in zip(pieces,images):
        if (p['width'],p['height'])not in(small_shape,big_shape)or image.shape!=(p['height'],p['width']):raise ValueError('OBJ_CHR_SIZE_PAIR_GEOMETRY')
        nw,nh=p['width']//8,p['height']//8;blocks.append([encode(image[y*8:y*8+8,x*8:x*8+8])for y in range(nh)for x in range(nw)])
    grid={};origins={};large={}
    for i in sorted(range(len(blocks)),key=lambda i:-len(blocks[i])):
        block=blocks[i]
        if len(block)==1:continue
        nw,nh=pieces[i]['width']//8,pieces[i]['height']//8
        key=(nw,nh,b''.join(block))
        if key in large:origins[i]=large[key];continue
        for page in range(2):
            for y in range(0,16,nh):
                for x in range(0,16,nw):
                    cells=[page*256+(y+dy)*16+x+dx for dy in range(nh)for dx in range(nw)]
                    if any(c in reserved or c in grid and grid[c]!=tile for c,tile in zip(cells,block)):continue
                    origin=page*256+y*16+x
                    for c,tile in zip(cells,block):grid[c]=tile
                    origins[i]=origin;large[key]=origin;break
                if i in origins:break
            if i in origins:break
        if i not in origins:raise ValueError('OBJ_CHR_ALIGNED_PLACEMENT_EXHAUSTED_NOT_INFEASIBILITY')
    vocabulary={tile:cell for cell,tile in sorted(grid.items(),reverse=True)}
    for i,block in enumerate(blocks):
        if len(block)!=1:continue
        tile=block[0]
        if tile in vocabulary:origins[i]=vocabulary[tile];continue
        cell=next((c for c in range(512)if c not in grid and c not in reserved),None)
        if cell is None:raise ValueError('OBJ_CHR_ALIGNED_PLACEMENT_EXHAUSTED_NOT_INFEASIBILITY')
        grid[cell]=tile;vocabulary[tile]=cell;origins[i]=cell
    oam=bytearray(544)
    for i in range(128):
        oam[4*i]=0xc0;oam[4*i+1]=240
        oam[512+i//4]|=1<<(2*(i%4))
    for i,p in enumerate(pieces):
        if not 0<=p['bank']<8 or not -256<=p['x']<256 or not -256<=p['y']<256:raise ValueError('OBJ_CHR_OAM_ATTRIBUTE_DOMAIN')
        tile=origins[i];x=p['x']&511;large_bit=2 if(p['width'],p['height'])==big_shape else 0
        oam[4*i:4*i+4]=bytes([x&255,p['y']&255,tile&255,0x30|p['bank']<<1|tile>>8])
        shift=2*(i%4)
        oam[512+i//4]=(oam[512+i//4]&~(3<<shift))|((x>>8)|large_bit)<<shift
    data=bytearray((max(grid,default=-1)+1)*32)
    for cell,tile in grid.items():data[cell*32:cell*32+32]=tile
    # Decode from emitted OAM and CHR, not the planner's origin dictionary.
    for i,(p,image)in enumerate(zip(pieces,images)):
        attr=oam[4*i+3];origin=oam[4*i+2]+((attr&1)<<8);shape=big_shape if(oam[512+i//4]>>(2*(i%4)))&2 else small_shape
        nw,nh=shape[0]//8,shape[1]//8
        replay=np.zeros((nh*8,nw*8),dtype=np.uint8)
        for y in range(nh):
            for x in range(nw):
                cell=(origin&256)+((origin&255)+y*16+x)
                replay[y*8:y*8+8,x*8:x*8+8]=decode(data[cell*32:cell*32+32])
        if not np.array_equal(replay,image)or(attr>>1)&7!=p['bank']:raise AssertionError('OBJ_CHR_OAM_PIXEL_IDENTITY')
    from raster_obj_geometry import active_on_line,tile_slivers
    emitted=[]
    for i in range(128):
        high=(oam[512+i//4]>>(2*(i%4)))&3
        x=oam[4*i]+((high&1)<<8);x=x-512 if x>=256 else x
        shape=big_shape if high&2 else small_shape
        emitted.append(dict(x=x,y=oam[4*i+1],width=shape[0],height=shape[1]))
    sprite_rows=[sum(active_on_line(p,y)for p in emitted)for y in range(224)]
    tile_rows=[sum(tile_slivers(p)for p in emitted if active_on_line(p,y))for y in range(224)]
    if sprite_rows!=[sum(active_on_line(p,y)for p in pieces)for y in range(224)]or tile_rows!=[sum(tile_slivers(p)for p in pieces if active_on_line(p,y))for y in range(224)]:raise AssertionError('OBJ_CHR_EMITTED_GEOMETRY_REPLAY')
    report=dict(schema='BYOR_RASTER_OBJ_CHR_V1',status=f'LEGAL_MODE{mode}_CHR_OAM_CONSTRUCTIVE_PROOF',
                obj_size_mode=mode,obj_size_pair=[list(small),list(big)]if mode==6 else[small,big],oam_entries=len(pieces),obj_chr_bytes=len(data),occupied_tile_cells=len(grid),
                unique_tiles=len(set(grid.values())),reserved_tile_cells=sorted(reserved),
                chr_sha256=hashlib.sha256(data).hexdigest(),oam_sha256=hashlib.sha256(oam).hexdigest(),
                emitted_oam_chr_pixel_indices_verified=True,native_render_proven=False,no_color_reduction=True)
    report.update(emitted_oam_geometry_replayed=True,peak_sprites_per_line=max(sprite_rows),peak_tile_slivers_per_line=max(tile_rows),unused_oam_hidden_x=-64)
    report['hardware_scanline_geometry_admitted']=max(sprite_rows)<=32 and max(tile_rows)<=34
    if not report['hardware_scanline_geometry_admitted']:report['status']='CHR_OAM_INDICES_PROVEN_SCANLINE_GEOMETRY_OVERFLOW'
    return report,bytes(data),bytes(oam)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);report,data,oam=compile(json.loads(a.schedule.read_text()))
    (a.output/'obj.chr').write_bytes(data);(a.output/'oam.bin').write_bytes(oam)
    report['input_schedule_sha256']=hashlib.sha256(a.schedule.read_bytes()).hexdigest()
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
