"""Lossless mode-6 packing analysis. Heuristic upper bounds, never minimum claims.

Use SMALL cells, then merge fully occupied 2x2 cells into LARGE pieces without
increasing tile bytes. Candidate grids retain source coordinates and offsets.
Index-zero transparency must be validated by the caller's source dialect.
"""
import hashlib
import io
from PIL import Image


def digest(data):
    return hashlib.sha256(data).hexdigest()


def tile_rows(image):
    width,height=image.size
    return [image.crop((x,y,x+8,y+8)).tobytes()
            for y in range(0,height,8) for x in range(0,width,8)]


def pack_image(raw, offset=(0,0)):
    with Image.open(io.BytesIO(raw)) as original:
        if original.mode!='P' or getattr(original,'n_frames',1)!=1:
            raise ValueError('INDEXED_SINGLE_FRAME_REQUIRED')
        original.load();image=original.copy()
    bbox=image.getbbox()
    if bbox is None:
        return dict(dimensions=list(image.size),bbox=None,pieces=[],tile_bytes=0,
                    nonempty_tiles=0,padding_tiles=0,small_blocks={},tile_ids=[])
    ox,oy=offset
    grids={(0,0),(bbox[0]%16,bbox[1]%32),(ox%16,oy%32)}
    candidates=[]
    for gx,gy in sorted(grids):
        startx=(bbox[0]-gx)//16*16+gx
        starty=(bbox[1]-gy)//32*32+gy
        cells={}
        for y in range(starty,bbox[3],32):
            for x in range(startx,bbox[2],16):
                cell=image.crop((x,y,x+16,y+32))
                if cell.getbbox() is not None:cells[(x,y)]=cell
        for phase_x in (0,1):
            for phase_y in (0,1):
                remaining=set(cells);pieces=[]
                for x,y in sorted(cells,key=lambda p:(p[1],p[0])):
                    if ((x-startx)//16)%2!=phase_x or ((y-starty)//32)%2!=phase_y:
                        continue
                    group={(x,y),(x+16,y),(x,y+32),(x+16,y+32)}
                    if group<=remaining:
                        pieces.append((x,y,32,64));remaining-=group
                pieces.extend((x,y,16,32) for x,y in sorted(remaining,key=lambda p:(p[1],p[0])))
                candidates.append((len(cells)*256,len(pieces),(gx,gy),pieces,cells))
    _,_,grid,pieces,cells=min(candidates,key=lambda c:(c[0],c[1],c[2],c[3]))
    result=[];tiles=[];blocks={};nonempty=0
    for (x,y),cell in sorted(cells.items()):
        payload=cell.tobytes();block_id=digest(payload)
        blocks[block_id]=dict(x=x,y=y,source_indices_hex=payload.hex())
        for tile in tile_rows(cell):
            tiles.append(digest(tile));nonempty+=bool(any(tile))
    for x,y,w,h in pieces:
        result.append(dict(source_xy=[x,y],size=[w,h],right_xy=[x-ox,y-oy],
                           left_xy=[ox-x-w+1,y-oy]))
    return dict(dimensions=list(image.size),bbox=list(bbox),grid=list(grid),pieces=result,
        tile_bytes=len(cells)*256,nonempty_tiles=nonempty,
        padding_tiles=len(cells)*8-nonempty,small_blocks=blocks,tile_ids=tiles,
        total_oam_entries=len(result),geometry_certified=False,
        note='Lossless candidate packing, not VRAM placement or live publication proof')


def transition_delta(previous,current):
    old=set(previous['small_blocks']) if previous else set()
    new=set(current['small_blocks'])
    return dict(retained_blocks=len(old&new),new_blocks=len(new-old),
                released_blocks=len(old-new),new_bytes=256*len(new-old),
                tile_content_delta_bytes=32*len(set(current['tile_ids'])-
                    (set(previous['tile_ids']) if previous else set())),
                physical_placement_proven=False)


def reconstruct(raw, packed):
    """Independent pixel coverage check including offsets outside the canvas."""
    with Image.open(io.BytesIO(raw)) as source:
        source.load();expected=source.tobytes()
        canvas=Image.new('P',source.size)
        for piece in packed['pieces']:
            x,y=piece['source_xy'];w,h=piece['size']
            canvas.paste(source.crop((x,y,x+w,y+h)),(x,y))
        return canvas.tobytes()==expected


def viewport_resources(packed, origin=(0,0)):
    """Geometric viewport upper bounds; not OAM timing or hardware lower bounds.

    Count intersecting tile slivers, including transparent padding inside OBJs.
    Fully offscreen pieces are omitted rather than emitted at X=-256.
    """
    rows=[0]*224;slivers=[0]*224;visible=[]
    for piece in packed['pieces']:
        px,py=piece['source_xy'];w,h=piece['size']
        x,y=px+origin[0],py+origin[1]
        if x+w<=0 or x>=256 or y+h<=0 or y>=224:continue
        visible.append(piece)
        count=sum(-8<x+dx<256 for dx in range(0,w,8))
        for line in range(max(0,y),min(224,y+h)):
            rows[line]+=1;slivers[line]+=count
    return dict(viewport=[256,224],origin=list(origin),oam_entries=len(visible),
        scanline_objs=max(rows),scanline_slivers=max(slivers),
        limit_oam=128,limit_scanline_objs=32,limit_slivers=34,
        fits=len(visible)<=128 and max(rows)<=32 and max(slivers)<=34,
        hardware_verified=False)
