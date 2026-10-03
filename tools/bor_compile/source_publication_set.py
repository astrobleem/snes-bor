"""Content-addressed, pinned multi-model publication sets in the legal OBJ window.

Admission is explicit: a resident set is not a claim that all of its frames
must coexist. Oversize pinned sets are policy limits, not hardware lower bounds.
Runtime frame lookup must fail closed outside the admitted keys.
"""
import hashlib
import io
import struct
from PIL import Image
from source_actor_raster import compile_animation, encode_tile
from source_compact_packing import pack_compact


class PublicationResourceBlocked(ValueError):
    def __init__(self,message,details):
        super().__init__(message)
        self.details=details


def compile_set(source, requests, *, _inventory_only=False, packet_palettes=False, reserved_slots=()):
    reserved_slots=sorted(set(reserved_slots))
    if any(not isinstance(slot,int) or not 0<=slot<64 for slot in reserved_slots):
        raise ValueError('OBJ_RESERVED_SLOT_RANGE')
    available_slots=[slot for slot in range(64) if slot not in reserved_slots]
    blocks={};frames=[];palettes={}
    for request in requests:
        if not 0<=request['runtime_id']<=255:raise ValueError('RUNTIME_MODEL_ID_WIDTH')
        model=request['model'];role=request['role']
        raster=compile_animation(source,model,role,color_adapter='SNES_RGB555_TRUNCATE')
        indices=raster['manifest']['source_palette_indices']
        mapping={v:i for i,v in enumerate(indices)}
        palette=source.read('data/pal.act')
        for selector in request.get('maps',[0]):
            if not 0<=selector<=255:raise ValueError('SOURCE_MAP_SELECTOR_WIDTH')
            if not 0<=selector<=len(model.remaps):raise ValueError('SOURCE_MAP_UNAVAILABLE')
            remap={i:i for i in range(256)}
            if selector:
                pair=[a['source_path'] for a in model.remaps[selector-1]['assets']]
                a=Image.open(io.BytesIO(source.read(pair[0])))
                b=Image.open(io.BytesIO(source.read(pair[1])))
                if a.mode!='P' or b.mode!='P':raise ValueError('REMAP_INDEX_GEOMETRY')
                # Pinned BOR.C load_colourmap(): row-major last assignment wins
                # over the common rectangle; untouched indices remain identity.
                for y in range(min(a.height,b.height)):
                    for x in range(min(a.width,b.width)):
                        remap[a.getpixel((x,y))]=b.getpixel((x,y))
            colors=bytearray()
            for index in indices:
                rgb=palette[remap[index]*3:remap[index]*3+3]
                if len(rgb)!=3:raise ValueError('PALETTE_INDEX_EXTENT')
                r,g,b=rgb;colors+=struct.pack('<H',(r>>3)|((g>>3)<<5)|((b>>3)<<10))
            colors=bytes(colors).ljust(32,b'\0')
            pkey=hashlib.sha256(colors).hexdigest();palettes[pkey]=colors
            for i in request['frames']:
                if not 0<=i<len(raster['manifest']['frames']):raise ValueError('SOURCE_FRAME_UNAVAILABLE')
                f=raster['manifest']['frames'][i];raw=source.read(f['source_path'])
                image=Image.open(io.BytesIO(raw));image.load()
                pieces=[]
                for p in pack_compact(raw,f['offset'])['pieces']:
                    x,y=p['source_xy'];cell=image.crop((x,y,x+16,y+32))
                    data=b''.join(encode_tile(bytes(mapping[cell.getpixel((tx+dx,ty+dy))]
                        for dy in range(8) for dx in range(8))) for ty in range(0,32,8) for tx in (0,8))
                    key=hashlib.sha256(data).hexdigest();blocks[key]=data
                    pieces.append(dict(p,resource=key))
                frames.append(dict(model=request['runtime_id'],source_identity=model.declaration,
                    role=request['role_id'],frame=i,map=selector,palette=pkey,pieces=pieces,source=f,
                    source_palette_indices=indices))
    unique_frames={}
    for f in frames:
        key=(f['model'],f['role'],f['frame'],f['map'])
        if key in unique_frames and unique_frames[key]!=f:raise ValueError('RUNTIME_PUBLICATION_ID_COLLISION')
        unique_frames[key]=f
    frames=list(unique_frames.values())
    if _inventory_only:
        return dict(blocks=blocks,frames=frames,palettes=palettes)
    # Only OBJ palettes6/7 are admitted by this opt-in allocation. Do not
    # overwrite accepted actors' other palette allocations.
    if len(palettes)>2 and not packet_palettes:raise PublicationResourceBlocked(f'PINNED_PALETTE_SET_BLOCKED: required={len(palettes)}, available=2',
        dict(capability='RESOURCE_BLOCKED',resource='PINNED_CGRAM_SLOTS',required=len(palettes),available=2,
             identities=sorted(palettes),simultaneous_requirement_proven=False))
    if len(blocks)>len(available_slots):
        ledger=[dict(sha256=key,size=256,allocation_shape='4x64-byte rows, 512-byte stride',
            references=[dict(model=f['model'],role=f['role'],frame=f['frame'],map=f['map']) for f in frames if any(p['resource']==key for p in f['pieces'])]) for key in sorted(blocks)]
        raise PublicationResourceBlocked(f'PINNED_VRAM_SET_BLOCKED: required={len(blocks)*256}, available={len(available_slots)*256}; not a simultaneous-live-set lower bound',
            dict(capability='RESOURCE_BLOCKED',resource='PINNED_COMPILED_BLOCK_SET',required_bytes=len(blocks)*256,
                 available_bytes=len(available_slots)*256,reserved_slots=reserved_slots,blocks=ledger,fragmentation_bytes=0,
                 minimum_for_emitted_indivisible_block_abi=len(blocks)*256,
                 unique_8x8_encoded_bytes=len({data[i:i+32] for data in blocks.values() for i in range(0,256,32)})*32,
                 source_pixel_global_minimum_proven=False,simultaneous_requirement_proven=False))
    placement={key:slot for key,slot in zip(sorted(blocks),available_slots)}
    # Packet mode assigns physical slots to simultaneous instances at capture;
    # immutable palette identity remains independent of that temporary binding.
    palette_slots={} if packet_palettes else {key:6+i for i,key in enumerate(sorted(palettes))}
    tiles=bytearray(16384)
    for key,slot in placement.items():
        tile=(slot//8)*64+(slot%8)*2
        for row in range(4):tiles[(tile+16*row)*32:(tile+16*row)*32+64]=blocks[key][64*row:64*row+64]
    for f in frames:
        f['palette_slot']=6 if packet_palettes else palette_slots[f['palette']]
        for p in f['pieces']:
            slot=placement[p['resource']];p['tile']=(slot//8)*64+(slot%8)*2
    return dict(frames=frames,tiles=bytes(tiles),palettes=palettes,palette_slots=palette_slots,
        blocks={key:dict(size=256,slot=placement[key]) for key in blocks},
        required_bytes=len(blocks)*256,available_bytes=len(available_slots)*256,reserved_slots=reserved_slots,
        ownership='PINNED_ADMITTED_SET_UNTIL_WORLD_PUBLICATION_TEARDOWN',hardware_ready=False,
        palette_ownership='IMMUTABLE_PUBLICATION_PACKET' if packet_palettes else 'PINNED_ADMITTED_SET')


def live_set_report(source, publications, *, atomic_palette_packets=False):
    """Exact union for emitted indivisible blocks, not an artwork optimum.

    Caller supplies physically displayed/queued/new packet references, not a
    whole animation's speculative future. Each frame is explicit. Retention
    and prefetch are listed but excluded from the mandatory union. Runtime
    completion evidence must justify the caller's ownership classification.
    """
    mandatory={'displayed','queued','new_packet','in_flight'}
    optional={'prefetch','unreferenced'}
    ledger={};palette_refs={};packet_palette_slots=[]
    for packet in publications:
        if packet['ownership'] not in mandatory|optional:raise ValueError('UNKNOWN_PUBLICATION_OWNERSHIP')
        for r in packet['requests']:
            if len(r['frames'])!=1 or len(r.get('maps',[0]))!=1:
                raise ValueError('LIVE_PACKET_REQUIRES_EXPLICIT_FRAME_AND_MAP')
        inv=compile_set(source,packet['requests'],_inventory_only=True)
        if packet['ownership'] in mandatory:
            packet_palette_slots.append(len(packet['requests']))
        for f in inv['frames']:
            ref=dict(packet=packet['identity'],ownership=packet['ownership'],model=f['model'],
                     role=f['role'],frame=f['frame'],map=f['map'])
            for p in f['pieces']:
                record=ledger.setdefault(p['resource'],dict(sha256=p['resource'],size=256,
                    shape='4x64-byte rows at 512-byte stride',references=[]))
                if ref not in record['references']:record['references'].append(ref)
            palette_refs.setdefault(f['palette'],[]).append(ref)
    live=[b for b in ledger.values() if any(r['ownership'] in mandatory for r in b['references'])]
    palette_live=[k for k,refs in palette_refs.items() if any(r['ownership'] in mandatory for r in refs)]
    palette_required=max(packet_palette_slots,default=0) if atomic_palette_packets else len(palette_live)
    required=sum(b['size'] for b in live)
    # Fixed equal-size footprints: any free slot satisfies any block. This is
    # not a claim that a different sprite decomposition could never be smaller.
    return dict(status='RESOURCE_BLOCKED' if required>16384 or palette_required>2 else 'REPRESENTABLE_EMITTED_ABI',
        required_bytes=required,available_bytes=16384,fragmentation_bytes=0,
        required_palette_slots=palette_required,available_palette_slots=2,
        palette_lifetime_policy='ATOMIC_CGRAM_OAM_PACKET' if atomic_palette_packets else 'SIMULTANEOUS_PINNED_IDENTITIES',
        referenced_palette_identities=len(palette_live),
        optional_only_bytes=sum(b['size'] for b in ledger.values() if b not in live),
        blocks=sorted(ledger.values(),key=lambda b:b['sha256']),palettes=palette_refs,
        minimum_for_emitted_indivisible_block_abi=required,
        source_pixel_global_minimum_proven=False,hardware_ownership_evidence='CALLER_REQUIRED')


def oam_resource_report(pieces):
    """Conservative scanline admission for the emitted SMALL16x32 ABI."""
    visible=[p for p in pieces if -16<p['x']<256 and -32<p['y']<224]
    lines=[sum(p['y']<=y<p['y']+32 for p in visible) for y in range(224)]
    count=max(lines,default=0)
    return dict(status='RESOURCE_BLOCKED' if len(visible)>128 or count>32 or count*2>34 else 'PASS',
        total_oam=len(visible),maximum_scanline_objs=count,maximum_scanline_slivers=count*2,
        limits=dict(total_oam=128,scanline_objs=32,scanline_slivers=34),
        bound='CONSERVATIVE_FOR_EMITTED_SMALL_PIECES_NOT_MINIMUM_SOURCE_ARTWORK')
