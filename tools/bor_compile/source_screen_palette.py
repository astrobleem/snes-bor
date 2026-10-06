"""Cache source RGB8 pairs and bind a compiled CGRAM schedule to native values.

This is an immutable-underlay capability. Geometry and low-component indices
come from the source-exact compiled frame; every native cached RGB555 word is
verified before this bounded proof is admitted. No actor-name branch exists.
"""
import hashlib
import struct
import numpy as np


def projection_tables():
    i=np.arange(65536,dtype=np.uint32)
    v=(255-((255-(i&255))*(255-(i>>8))//255))>>3
    return b''.join(a.astype(np.uint8).tobytes() for a in [v,(v<<5)&255,v>>3,v<<2])


def derive(records,report,initial):
    if len(records)%16:raise ValueError('SCREEN_PALETTE_RECORD_ALIGNMENT')
    if len(initial)!=236:raise ValueError('SCREEN_PALETTE_INITIAL_SIZE')
    if len(report['trace'])!=len(report['contiguous_bursts']):raise ValueError('SCREEN_PALETTE_ROW_COUNT')
    if report['low_component_palette']!=[0,32,1024,1056]:raise ValueError('SCREEN_PALETTE_COMPONENT_POLICY')
    unique={};pairs=[]
    for at in range(0,len(records),16):
        raw=records[at:at+6]
        if raw not in unique:unique[raw]=len(pairs);pairs.append(struct.unpack('<3H',raw))
    if not pairs:raise ValueError('SCREEN_PALETTE_EMPTY_INPUT')
    packed=np.array(pairs,dtype=np.uint16)
    rgb8=255-((255-(packed.astype(np.uint32)&255))*(255-(packed.astype(np.uint32)>>8))//255)
    rgb5=rgb8>>3;words=(rgb5[:,0]|(rgb5[:,1]<<5)|(rgb5[:,2]<<10)).astype('<u2')
    colors={}
    for i,c in enumerate(words):colors.setdefault(int(c)&0xfbdf,i)
    palette=[*report['low_component_palette'],*[c or 0 for c in initial],*range(0x1234,0x1244)]
    if len(palette)!=256:raise ValueError('SCREEN_PALETTE_INITIAL_SIZE')
    payload=[];state=list(initial)
    for row,burst in zip(report['trace'],report['contiguous_bursts']):
        if row['scanline']:
            for e in row['updates']:state[e['slot']-1]=e['color']
        slot=burst['start_slot']
        if slot<1 or slot+report['span']-1>len(state):raise ValueError('SCREEN_PALETTE_BURST_RANGE')
        payload.extend(c or 0 for c in state[slot-1:slot-1+report['span']])
    bindings=bytearray();native_bindings=0
    for color in [*palette,*payload]:
        if color in colors:
            bindings.extend(struct.pack('<HH',colors[color]*2,1));native_bindings+=1
        else:bindings.extend(struct.pack('<HH',color,0))
    if len(bindings)>32768 or packed.nbytes>32768:raise ValueError('SCREEN_PALETTE_ROM_BANK_CAPACITY')
    metadata=dict(schema='BYOR_CACHED_SCREEN_PALETTE_V1',unique_rgb8_pairs=len(pairs),source_pixels=len(records)//16,
                  cgram_words=len(bindings)//4,native_screen_bound_words=native_bindings,
                  source_constant_words=len(bindings)//4-native_bindings,payload_bytes=len(payload)*2,
                  native_cache_bytes=words.nbytes,native_colour_workspace_bytes=words.nbytes+512+len(payload)*2,
                  native_cache_expected_sha256=hashlib.sha256(words.tobytes()).hexdigest(),
                  compiled_bindings_sha256=hashlib.sha256(bindings).hexdigest(),no_color_reduction=True,
                  scope='Source-derived immutable context, color-pair cache and native CGRAM binding. No moving-world underlay admission.')
    return packed.astype('<u2').tobytes(),bytes(bindings),words.tobytes(),metadata
