"""Lossless indexed raster lowering from the existing ModelIR, not another parser.

Mode 6 small OBJs are 16x32. Original canvas, source palette indices and
offsets survive; only transparent index-zero padding is introduced. Scheduler,
DMA admission and activation are consumers, not implemented by this compiler.
No hardware color rounding, remapping policy, or model-name branches exist.
"""
from __future__ import annotations

import hashlib
import io
import struct

from PIL import Image


def sha(data):
    return hashlib.sha256(data).hexdigest()


def exact_cgram(colors):
    """RGB8 exact under the conventional 5-to-8 bit replication definition.

    This is deliberately NOT nearest-color conversion. Analog display matching
    is outside this definition; original RGB triplets remain authoritative.
    """
    levels = {(v << 3) | (v >> 2): v for v in range(32)}
    result = bytearray(2)  # transparent index zero
    for index, rgb in colors:
        if any(c not in levels for c in rgb):
            raise ValueError(f'COLOR_PRECISION: source_index={index}, rgb={tuple(rgb)}, '
                             'required=RGB8, available=BGR555; no quantization authorized')
        r, g, b = (levels[c] for c in rgb)
        result.extend(struct.pack('<H', r | g << 5 | b << 10))
    return bytes(result).ljust(32, b'\0')


def encode_tile(pixels):
    if len(pixels) != 64 or any(p > 15 for p in pixels):
        raise ValueError('TILE_4BPP_INPUT')
    out = bytearray(32)
    for y in range(8):
        for x in range(8):
            for plane in range(4):
                out[(plane // 2) * 16 + y * 2 + plane % 2] |= (
                    (pixels[y * 8 + x] >> plane) & 1) << (7 - x)
    return bytes(out)


def compile_animation(source, model, role, *, palette_path='data/pal.act', color_adapter='RGB8_EXACT'):
    """Return target packets + manifest; all names are source metadata only.

    Each frame uses <=32 small OBJs in one 8KiB OBJ name table. Two name
    tables fit the 16KiB window at VRAM word $4000. Packets contain scatter
    writes, not a false contiguous sprite-tile layout. No transfer deadline
    or visible-frame alignment is inferred from a successful compilation.
    """
    context = f'project={model.project_id}, model={model.declaration}, role={role}'
    if model.dialect != 'historical-bor':
        raise ValueError(f'RASTER_DIALECT: {context}, dialect={model.dialect}')
    matches = [a for a in model.animations if a.role == role]
    if len(matches) != 1 or not matches[0].frames:
        raise ValueError(f'RASTER_ROLE: {context}')
    palette = source.read(palette_path)
    if len(palette) < 128 * 3:
        raise ValueError(f'PALETTE_EXTENT: {context}, required_bytes=384, available_bytes={len(palette)}')
    decoded = []
    used = set()
    for frame in matches[0].frames:
        raw = source.read(frame.source_path)
        if sha(raw) != frame.asset_sha256:
            raise ValueError(f'ASSET_HASH: {context}, asset={frame.source_path}')
        with Image.open(io.BytesIO(raw)) as image:
            if image.mode != 'P' or getattr(image, 'n_frames', 1) != 1:
                raise ValueError(f'INDEXED_SINGLE_IMAGE: {context}, asset={frame.source_path}')
            w, h = image.size
            if [w, h] != frame.dimensions or not (0 < w <= 512 and 0 < h <= 512):
                raise ValueError(f'CANVAS_EXTENT: {context}, dimensions={(w, h)}, available=(512,512)')
            pixels = image.tobytes()
        used.update(set(pixels) - {0})
        decoded.append((frame, w, h, pixels))
    if any(i >= 128 for i in used):
        raise ValueError(f'GLOBAL_PALETTE_SCOPE: {context}, indices={sorted(used)}')
    if len(used) > 15:
        raise ValueError(f'OBJ_PALETTE_CAPACITY: {context}, required_colors={len(used)}, available_colors=15')
    indices = [0, *sorted(used)]
    mapping = {original: local for local, original in enumerate(indices)}
    colors = [(i, tuple(palette[3*i:3*i+3])) for i in indices[1:]]
    pool = bytearray()
    unique = {}
    packets = bytearray()
    frames = []
    for frame, w, h, pixels in decoded:
        chunks = []
        ox, oy = frame.state['offset']
        for cy in range(0, h, 32):
            for cx in range(0, w, 16):
                block = bytes(mapping[pixels[y*w+x]] if x < w and y < h else 0
                              for y in range(cy, cy+32) for x in range(cx, cx+16))
                if not any(block):
                    continue
                tile_bytes = b''.join(encode_tile(bytes(block[(ty+y)*16+tx+x]
                                     for y in range(8) for x in range(8)))
                                     for ty in range(0, 32, 8) for tx in (0, 8))
                if tile_bytes not in unique:
                    unique[tile_bytes] = len(pool) // 256
                    pool.extend(tile_bytes)
                chunks.append(dict(canvas_xy=[cx, cy], right_xy=[cx-ox, cy-oy],
                                   left_xy=[ox-cx-15, cy-oy], chunk_id=unique[tile_bytes]))
        if len(chunks) > 32:
            raise ValueError(f'FRAME_OBJ_EXTENT: {context}, asset={frame.source_path}, '
                             f'required_chunks={len(chunks)}, available_chunks=32')
        # OAM positions stay relative to source x-advancex,z-a+gfx_y_offset.
        # Caller must clip signed screen positions, never blindly wrap OAM Y.
        writes = []
        for slot, chunk in enumerate(chunks):
            tile = (slot // 8) * 64 + (slot % 8) * 2
            chunk['tile'] = tile
            data = pool[chunk['chunk_id']*256:(chunk['chunk_id']+1)*256]
            for row in range(4):
                writes.append(dict(vram_word_offset=(tile+16*row)*16,
                                   packet_offset=len(packets), size=64))
                packets.extend(data[row*64:(row+1)*64])
        # OAM grid rows are contiguous in VRAM even though source chunks are
        # scattered. Reorder only transfer packets, then coalesce adjacent rows.
        # Pixel/tile identity does not change; fewer DMA setups improve admission.
        segments=[]
        for write in sorted(writes,key=lambda w:w['vram_word_offset']):
            payload=bytes(packets[write['packet_offset']:write['packet_offset']+write['size']])
            if segments and segments[-1][0]+len(segments[-1][1])//2==write['vram_word_offset']:
                segments[-1][1].extend(payload)
            else:segments.append([write['vram_word_offset'],bytearray(payload)])
        # Remove this frame's old transfer copy, retaining prior frames.
        if writes:del packets[min(w['packet_offset'] for w in writes):]
        writes=[]
        for destination,payload in segments:
            writes.append(dict(vram_word_offset=destination,packet_offset=len(packets),size=len(payload)))
            packets.extend(payload)
        frames.append(dict(source_path=frame.source_path, asset_sha256=frame.asset_sha256,
                           dimensions=[w,h], offset=[ox,oy], source_delay=frame.state['delay'],
                           delay_ticks_200hz=frame.state['delay']*2, chunks=chunks,
                           writes=writes, dma_bytes=len(chunks)*256,
                           source_indices_sha256=sha(pixels)))
    if color_adapter not in ('RGB8_EXACT', 'SNES_RGB555_TRUNCATE'):
        raise ValueError(f'COLOR_ADAPTER: {color_adapter}')
    try:
        cgram = exact_cgram(colors)
        color_status = dict(status='PASS', contract='RGB8 bit-replication exact')
    except ValueError as error:
        cgram = None
        color_status = dict(status='BLOCK', reason=str(error))
    if color_adapter == 'SNES_RGB555_TRUNCATE':
        words = [(r>>3) | (g>>3)<<5 | (b>>3)<<10 for _, (r,g,b) in colors]
        if len(set(words)) != len(words):
            raise ValueError(f'COLOR_MAPPING_MERGE: {context}')
        cgram = struct.pack('<16H', 0, *words, *([0]*(15-len(words))))
        color_status = dict(status='ADAPTED', adapter=color_adapter,
                            distinct_mappings=len(words), exact_rgb8=False, palette_reduction=False)
    manifest = dict(format='SOURCE_INDEXED_RASTER_V1', profile='SOURCE_EXACT',
                    project_id=model.project_id, source_identity=list(model.identity),
                    source_model_sha256=model.source_sha256, role=role,
                    palette_path=palette_path, palette_sha256=sha(palette),
                    source_palette_indices=indices, source_rgb=colors,
                    transparent_source_index=0, obj_mode=6, obj_size=[16,32],
                    obj_vram_word=0x4000, buffer_word_offsets=[0,0x1000],
                    unique_chunks=len(unique), preload_bytes=len(pool),
                    preload_capacity_bytes=16384, preload_fits=len(pool)<=16384,
                    color_encoding=color_status, frames=frames,
                    publication_allowed=False, live_render_proven=False,
                    deadline_proven=False, scheduler_owned_by_consumer=True)
    return dict(manifest=manifest, chunk_pool=bytes(pool), packets=bytes(packets), cgram=cgram)
