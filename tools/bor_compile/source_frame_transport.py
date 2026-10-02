"""Physical SMALL-OBJ cache placement for opt-in native transport.

One 8KiB name table,32 addressable16x32 footprints. A transfer's lease names
the earliest *consumed* frame that permits overwriting its old contents.
Logical frame callbacks and pending OAM do not satisfy that lease.
No timing certification is inferred from placement.
"""
import hashlib
import io
from PIL import Image
from frame_packing import pack_image
from source_actor_raster import encode_tile


def compile_frames(source, manifest, *, group_future=False, compact=False):
    future=[]
    if group_future:
        baseline=compile_frames(source,manifest,compact=compact)
        image=bytearray(8192)
        for f in baseline['frames']:
            for w in f['writes']:
                at=w['destination']-0x8000;image[at:at+len(w['payload'])]=w['payload']
            future.append({b''.join(image[(c['tile']+row*16)*32:(c['tile']+row*16)*32+64]
                                    for row in range(4)) for c in f['chunks']})
    mapping={original:local for local,original in enumerate(manifest['source_palette_indices'])}
    cache={};last_use={};previous=set();history=[];frames=[];entry=bytearray(8192)
    for index,frame in enumerate(manifest['frames']):
        raw=source.read(frame['source_path'])
        if hashlib.sha256(raw).hexdigest()!=frame['asset_sha256']:
            raise ValueError('SOURCE_ASSET_HASH')
        if compact:
            from source_compact_packing import pack_compact
            packed=pack_compact(raw,frame['offset'])
        else:packed=pack_image(raw,frame['offset'])
        with Image.open(io.BytesIO(raw)) as original:
            original.load();image=original.copy()
        blocks=[]
        for piece in packed['pieces']:
            px,py=piece['source_xy'];w,h=piece['size']
            for dy in range(0,h,32):
                for dx in range(0,w,16):
                    x,y=px+dx,py+dy
                    cell=image.crop((x,y,x+16,y+32))
                    data=b''.join(encode_tile(bytes(mapping[cell.getpixel((tx+xx,ty+yy))]
                        for yy in range(8) for xx in range(8)))
                        for ty in range(0,32,8) for tx in (0,8))
                    blocks.append((x,y,data))
        required={data for _,_,data in blocks}
        if len(required|previous)>32:
            raise ValueError(f'VRAM_TRANSITION_WORKING_SET: frame={index}, '
                             f'blocks={len(required|previous)}, limit=32')
        retained=set(previous)
        if compact:
            # Preserve additional older footprints when they fit alongside the
            # required transition. This lowers overwrite leases for staggered
            # consumers; it never discards the mandatory previous-frame lease.
            for older in reversed(history[:-1]):
                if len(required|retained|older)>32:break
                retained.update(older)
        assigned={};writes=[]
        def ordering(data):
            return (tuple(data in s for s in future[index+1:]),data) if group_future else data
        for data in sorted(required,key=ordering):
            matches=[slot for slot,value in cache.items() if value==data]
            if matches:
                slot=min(matches)
            else:
                choices=[slot for slot in range(32) if slot not in assigned.values()
                         and cache.get(slot) not in retained and cache.get(slot) not in required]
                if not choices:raise ValueError('VRAM_PHYSICAL_PLACEMENT')
                slot=min(choices,key=lambda s:(s in cache,s))
                # The previous payload must no longer be referenced by hardware.
                lease=last_use.get(slot,-1)+1
                tile=(slot//8)*64+(slot%8)*2
                for row in range(4):
                    destination=0x8000+(tile+row*16)*32 # DMA ABI BYTE address
                    payload=data[row*64:(row+1)*64]
                    writes.append(dict(destination=destination,payload=payload,
                                       consumed_frame_at_least=lease,slot=slot))
                    if index==0:entry[destination-0x8000:destination-0x8000+64]=payload
                cache[slot]=data
            assigned[data]=slot
        chunks=[];ox,oy=frame['offset']
        for x,y,data in blocks:
            slot=assigned[data];tile=(slot//8)*64+(slot%8)*2
            chunks.append(dict(right_xy=[x-ox,y-oy],left_xy=[ox-x-15,y-oy],tile=tile))
            last_use[slot]=index
        # Coalesce only physically adjacent rows with the SAME overwrite lease.
        segments=[]
        for write in sorted(writes,key=lambda w:(w['consumed_frame_at_least'],w['destination'])):
            if (segments and segments[-1]['consumed_frame_at_least']==write['consumed_frame_at_least']
                    and segments[-1]['destination']+len(segments[-1]['payload'])==write['destination']):
                segments[-1]['payload']+=write['payload']
            else:segments.append({k:write[k] for k in ('destination','payload','consumed_frame_at_least')})
        frames.append(dict(index=index,chunks=chunks,writes=segments,
            required_slots=sorted(set(assigned.values())),new_bytes=sum(len(w['payload']) for w in segments),
            slot_resources={slot:hashlib.sha256(data).hexdigest() for data,slot in assigned.items()},
            source=frame,ready=False))
        previous=required
        history.append(required)
    return dict(entry_image=bytes(entry),frames=frames,vram_byte_range=(0x8000,0xA000),
                native_fences_connected=False,deadline_certified=False)


def retained_working_set(plan, displayed, pending):
    """Resource demand, not a claim of hardware completion or minimum packing.

    Duplicate instances are consumers of the same immutable encoded block.
    Both currently displayed and pending snapshots retain their references.
    A different palette/encoding must use a separately linked resource identity.
    """
    resources=set();placements={};conflicts=[]
    for frame in sorted(set(displayed)|set(pending)):
        for slot,resource in plan['frames'][frame]['slot_resources'].items():
            resources.add(resource)
            if slot in placements and placements[slot]!=resource:conflicts.append(slot)
            placements[slot]=resource
    size=len(resources)*256
    return dict(encoded_blocks=len(resources),bytes=size,available_bytes=8192,
                layout_conflicts=sorted(set(conflicts)),
                status='VRAM_WORKING_SET_BLOCKED' if size>8192 else
                       'STATIC_LAYOUT_CONFLICT' if conflicts else 'FITS_STATIC_LAYOUT',
                hardware_ready=False)
