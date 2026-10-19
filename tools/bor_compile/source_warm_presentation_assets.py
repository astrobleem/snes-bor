"""Assign lossless warm-frame assets to checked empty ROM, retaining old colors."""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

from source_warm_frame_assets import derive, decode_image, DESC
from source_palette import model_palettes, select_model_palette
from source_profile import document, discover

HEADER = struct.Struct('<4s6H')
META_BANK = 41
CODE_BANK = 43
RENDER_BANK = 46
CONTROL = 0x7e9400
ROW_CACHE = 0x7e8400
RENDER_PIN = 0x7e9600
DISPLAY_PIN = 0x7e9700
TILE_ROWS = 0x7e9800
LEASE_BEGIN = 0x7e8340
LEASE_END = 0x7e9a60


def layout():
    ranges=[('row_cache',ROW_CACHE,ROW_CACHE+8*512),
            ('controls',CONTROL,CONTROL+384),('render_pin',RENDER_PIN,RENDER_PIN+148),
            ('display_pin',DISPLAY_PIN,DISPLAY_PIN+148),('tile_rows',TILE_ROWS,TILE_ROWS+96),
            ('yield_guard_tail',0x7e8340,0x7e83a0),
            ('yield_guard_middle',0x7e9580,0x7e9600),
            ('yield_guard_head',0x7e9860,0x7e9a60)]
    ordered=sorted(ranges,key=lambda r:r[1])
    if any(not LEASE_BEGIN<=a<b<=LEASE_END for _,a,b in ranges):
        raise ValueError('WARM_RAM_EXTENT')
    if any(left[2]>right[1]for left,right in zip(ordered,ordered[1:])):
        raise ValueError('WARM_RAM_OVERLAP')
    return dict(owner='exclusive retired SceneVideo staging after guarded world acquisition',
                begin=LEASE_BEGIN,end=LEASE_END,
                ranges=[dict(name=n,begin=a,end=b)for n,a,b in ranges],
                original_foreground_resumption_allowed=False,production_lease=False)


def scatter_images(rom, blobs, *, reserved_banks=(META_BANK,CODE_BANK,RENDER_BANK)):
    """First-fit decreasing, without crossing a checked zero 32-KiB slot."""
    if len(rom)!=4194304:
        raise ValueError('WARM_ROM_EXTENT')
    slots=[dict(start=bank*32768,used=0)for bank in range(128)
           if bank not in reserved_banks and not any(rom[bank*32768:(bank+1)*32768])]
    addresses=[None]*len(blobs)
    writes=[]
    for index in sorted(range(len(blobs)),key=lambda i:(-len(blobs[i]),i)):
        blob=bytes(blobs[index])
        if not 1<=len(blob)<32768:
            raise ValueError('WARM_SCATTER_IMAGE_EXTENT')
        decode_image(blob)
        slot=next((s for s in slots if ((s['used']+1)&~1)+len(blob)<=32768),None)
        if slot is None:
            raise ValueError('WARM_SCATTER_CAPACITY')
        offset=slot['start']+((slot['used']+1)&~1)
        if any(rom[offset:offset+len(blob)]):
            raise ValueError('WARM_SCATTER_NONEMPTY')
        addresses[index]=0xc00000+offset
        writes.append(dict(offset=offset,data=blob,image=index))
        slot['used']=offset-slot['start']+len(blob)
    return addresses,writes


def palette_extension(initial, original_palette, used_indices):
    """Append only; every already-used color slot and source index is stable."""
    colors=list(initial)
    if len(colors)!=236 or len(original_palette)!=256:
        raise ValueError('WARM_PALETTE_EXTENT')
    used_indices={int(index) for index in used_indices}
    if any(not 1<=index<=255 for index in used_indices):
        raise ValueError('WARM_SOURCE_INDEX')
    existing={value:i for i,value in enumerate(colors)if value is not None}
    missing=sorted({int(original_palette[i])&~0x420 for i in used_indices}-set(existing))
    available=[i for i,value in enumerate(colors)if value is None]
    if len(missing)>len(available):
        raise ValueError('WARM_PALETTE_CAPACITY')
    changes=[]
    for color,slot in zip(missing,available):
        colors[slot]=color;existing[color]=slot
        changes.append(dict(slot=slot,cgram_index=slot+4,color=color))
    lut=[0]*256
    for index in used_indices:
        color=int(original_palette[index])
        lut[index]=existing[color&~0x420]+4+((((color>>5)&1)|(((color>>10)&1)<<1))<<8)
        draw=lut[index]
        reconstructed=colors[(draw&255)-4]+(((draw>>8)&1)<<5)+(((draw>>9)&1)<<10)
        if reconstructed!=color:
            raise ValueError('WARM_COMPONENT_COLOR_LOSS')
    if any(a is not None and a!=b for a,b in zip(initial,colors)):
        raise ValueError('WARM_EXISTING_PALETTE_CHANGED')
    return colors,struct.pack('<256H',*lut),changes


def prepare(source, baseline, *, initial_path=Path('out/byor-motu-online-v3/assets/initial.json')):
    packed=derive(source)
    manifest=packed['manifest'];blobs=packed['image_blobs']
    addresses,writes=scatter_images(baseline,blobs)
    docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')}
    model=next(m for m in discover(source,docs)['models']if m['name']=='He_Man')
    palette,_=select_model_palette(model_palettes(source,model),0)
    used={int(v)for blob in blobs for v in set(decode_image(blob).flat)if v}
    initial=json.loads(initial_path.read_text())
    colors,lut,changes=palette_extension(initial,palette['rgb555'],used)
    poses=manifest['poses'];metadata=bytearray(HEADER.pack(b'WPN1',1,32,len(poses),manifest['model']['model_id'],len(blobs),0))
    groups=[]
    for index,pose in enumerate(poses):
        image=manifest['images'][pose['image_index']]
        if not groups or groups[-1]['handle']!=pose['handle']:
            groups.append(dict(handle=pose['handle'],first=index,count=0))
        if pose['frame']!=groups[-1]['count']:
            raise ValueError('WARM_POSE_FRAME_ORDER')
        groups[-1]['count']+=1
        metadata.extend(DESC.pack(pose['model_id'],pose['handle'],pose['frame'],pose['image_index'],
            pose['width'],pose['height'],*pose['offset'],*pose['bounds'],
            addresses[pose['image_index']],image['image_length'],0))
    lut_offset=(len(metadata)+1)&~1
    metadata.extend(bytes(lut_offset-len(metadata)));metadata.extend(lut)
    from source_warm_color_lut import build_pair_tables
    planes_offset=len(metadata)
    metadata.extend(b''.join(build_pair_tables(lut)))
    if len(metadata)>32768:
        raise ValueError('WARM_META_BANK_EXTENT')
    base=META_BANK*32768
    if any(baseline[base:base+32768]):
        raise ValueError('WARM_META_BANK_NONEMPTY')
    writes.append(dict(offset=base,data=bytes(metadata),reason='warm pose metadata and source-color LUT'))
    # Existing cold setup transfers its static CGRAM image from $E19000.
    for change in changes:
        offset=0x219000+change['cgram_index']*2
        if baseline[offset:offset+2]!=b'\0\0':
            raise ValueError('WARM_UNUSED_PALETTE_SLOT_NONZERO')
        writes.append(dict(offset=offset,data=struct.pack('<H',change['color']),reason='append unused CGRAM color'))
    config=dict(schema='BYOR_WARM_PRESENTATION_ASSETS_V1',
        baseline_rom_sha256=hashlib.sha256(baseline).hexdigest(),
        source_pak_sha256=manifest['source_pak_sha256'],model_id=manifest['model']['model_id'],
        pose_count=len(poses),image_count=len(blobs),image_bytes=sum(map(len,blobs)),
        metadata_cpu=0xc00000+base,metadata_bytes=len(metadata),metadata_header_bytes=HEADER.size,
        lut_cpu=0xc00000+base+lut_offset,groups=groups,
        color_planes_cpu=0xc00000+base+planes_offset,color_planes_bytes=20480,
        image_cpu_addresses=addresses,palette_changes=changes,
        palette_existing_slots_unchanged=True,source_indices_and_all_15_color_bits_preserved=True,
        memory=layout(),control=CONTROL,row_cache=ROW_CACHE,render_pin=RENDER_PIN,
        display_pin=DISPLAY_PIN,tile_rows=TILE_ROWS,code_bank=CODE_BANK,renderer_bank=RENDER_BANK,
        source_manifest=manifest,
        limitations=['opaque He_Man SELECT/IDLE/WALK map0 only','runtime integration and native timing not yet certified'])
    return writes,config
