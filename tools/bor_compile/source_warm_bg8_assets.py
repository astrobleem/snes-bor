"""Source-derived BG8 replacement payload for the existing warm renderer.

This builds data only.  It does not change the publisher, PPU registers, or
runtime admission.  The result retains the old cold map and CGRAM and adds a
new BG8 character catalog plus an exact RGB555 palette in the checked warm
metadata bank.
"""
from __future__ import annotations

import hashlib
import struct
import numpy as np

from source_warm_frame_assets import derive, decode_image, DESC as POSE_DESC
from source_warm_color_lut import build_pair_tables
from source_palette import model_palettes, select_model_palette
from source_profile import document, discover
from source_warm_presentation_assets import HEADER as WARM_HEADER

ROM_SIZE = 4 * 1024 * 1024
ROM_BASE = 0xC00000
META_BANK = 41
META_OFFSET = META_BANK * 32768
HIGH_OFFSET = 0x200000
LOW_OFFSET = 0x210000
MAP_OFFSET = 0x218000
OLD_CGRAM_OFFSET = 0x219000
BG8_OFFSET = 0x330000
BG8_TILE_COUNT = 596
BG8_TILE_BYTES = 80
BG8_BYTES = BG8_TILE_COUNT * BG8_TILE_BYTES
PALETTE_BYTES = 512


def _rgb555_canvas(rgb):
    rgb = np.asarray(rgb, dtype=np.int32)
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError('BG8_SOURCE_CANVAS_SHAPE')
    return ((rgb[:, :, 0] >> 3) | ((rgb[:, :, 1] >> 3) << 5) |
            ((rgb[:, :, 2] >> 3) << 10)).astype(np.uint16)


def _decode_planar(raw, bpp):
    raw = bytes(raw)
    if bpp not in (2, 8) or len(raw) != 8 * bpp:
        raise ValueError('BG8_OLD_TILE_EXTENT')
    out = np.zeros((8, 8), dtype=np.uint8)
    for y in range(8):
        for plane in range(bpp):
            pair = plane // 2
            off = pair * 16 + y * 2 + (plane & 1)
            byte = raw[off]
            for x in range(8):
                out[y, x] |= ((byte >> (7 - x)) & 1) << plane
    return out


def _encode_bg8_row_interleaved(pixels):
    """Encode one tile as 8 rows of four BG8 plane pairs plus a zero pair."""
    a = np.asarray(pixels)
    if a.shape != (8, 8) or np.any(a < 0) or np.any(a > 255):
        raise ValueError('BG8_TILE_GEOMETRY_OR_INDEX')
    out = bytearray()
    for y in range(8):
        for pair in range(4):
            even = odd = 0
            for x in range(8):
                bit = 0x80 >> x
                value = int(a[y, x])
                if value & (1 << (pair * 2)):
                    even |= bit
                if value & (1 << (pair * 2 + 1)):
                    odd |= bit
            out.extend((even, odd))
        out.extend((0, 0))
    return bytes(out)


def _decode_bg8_row_interleaved(raw):
    raw = bytes(raw)
    if len(raw) != BG8_TILE_BYTES:
        raise ValueError('BG8_ENCODED_TILE_EXTENT')
    out = np.zeros((8, 8), dtype=np.uint8)
    for y in range(8):
        row = raw[y * 10:(y + 1) * 10]
        if row[8:] != b'\0\0':
            raise ValueError('BG8_RESERVED_PAIR_NONZERO')
        for pair in range(4):
            even, odd = row[pair * 2:pair * 2 + 2]
            for x in range(8):
                bit = 0x80 >> x
                out[y, x] |= ((even & bit) != 0) << (pair * 2)
                out[y, x] |= ((odd & bit) != 0) << (pair * 2 + 1)
    return out


def _old_backdrop(rom):
    if len(rom) != ROM_SIZE:
        raise ValueError('BG8_BASELINE_ROM_EXTENT')
    high = rom[HIGH_OFFSET:HIGH_OFFSET + BG8_TILE_COUNT * 64]
    low = rom[LOW_OFFSET:LOW_OFFSET + BG8_TILE_COUNT * 16]
    maps = rom[MAP_OFFSET:MAP_OFFSET + 2048]
    cgram_raw = rom[OLD_CGRAM_OFFSET:OLD_CGRAM_OFFSET + PALETTE_BYTES]
    if len(high) != BG8_TILE_COUNT * 64 or len(low) != BG8_TILE_COUNT * 16 or len(maps) != 2048:
        raise ValueError('BG8_OLD_ASSET_EXTENT')
    cgram = struct.unpack('<256H', cgram_raw)
    tiles = []
    for tile_id in range(BG8_TILE_COUNT):
        hi = _decode_planar(high[tile_id * 64:(tile_id + 1) * 64], 8)
        lo = _decode_planar(low[tile_id * 16:(tile_id + 1) * 16], 2)
        rgb = np.empty((8, 8), dtype=np.uint16)
        for y in range(8):
            for x in range(8):
                color = int(cgram[int(hi[y, x])]) + int(cgram[int(lo[y, x])])
                if not 0 <= color <= 0x7fff:
                    raise ValueError('BG8_OLD_COLOR_OUT_OF_RGB555')
                rgb[y, x] = color
        tiles.append(rgb)
    return tiles, maps, cgram_raw


def _old_f3_catalog(rom):
    """Recreate the existing F3 catalog's exact 10-byte interleaved rows."""
    high = rom[HIGH_OFFSET:HIGH_OFFSET + BG8_TILE_COUNT * 64]
    low = rom[LOW_OFFSET:LOW_OFFSET + BG8_TILE_COUNT * 16]
    if len(high) != BG8_TILE_COUNT * 64 or len(low) != BG8_TILE_COUNT * 16:
        raise ValueError('BG8_OLD_F3_COMPONENT_EXTENT')
    out = bytearray()
    for tile_id in range(BG8_TILE_COUNT):
        h = high[tile_id * 64:(tile_id + 1) * 64]
        l = low[tile_id * 16:(tile_id + 1) * 16]
        for y in range(8):
            for pair in range(4):
                out.extend(h[pair * 16 + y * 2:pair * 16 + y * 2 + 2])
            out.extend(l[y * 2:y * 2 + 2])
    if len(out) != BG8_BYTES:
        raise AssertionError('BG8_OLD_F3_CATALOG_EXTENT')
    return bytes(out)


def _used_actor_colors(source, manifest, image_blobs):
    docs = {k: document(source, n) for k, (n, _) in source.index.items() if k.endswith('.txt')}
    models = discover(source, docs)['models']
    model = next((m for m in models if m['name'] == 'He_Man'), None)
    if model is None or int(manifest['model']['model_id']) != 3:
        raise ValueError('BG8_EXPECTED_HEMAN_PROFILE')
    palette, selected_map = select_model_palette(model_palettes(source, model), 0)
    if selected_map != 0 or palette is None:
        raise ValueError('BG8_ACTOR_PALETTE_MAP')
    used = set()
    for blob in image_blobs:
        image = decode_image(blob)
        used.update(map(int, np.unique(image)))
    used.discard(0)
    return {int(palette['rgb555'][i]) for i in used}, used, palette


def _stage_canvas(source):
    # Use the actual repository compositor and its real dependency bindings.
    from source_scene_bg import compose_rgb8
    stage_path = next((n for k, (n, _) in source.index.items()
                       if k == 'data/levels/guile2.txt'), None)
    if stage_path is None:
        raise ValueError('BG8_GUILE2_SOURCE_MISSING')
    rgb, meta = compose_rgb8(source, stage_path,
        dict(camera=[0, 0], viewport=[256, 224], quake=[0, 0], actors=[]))
    return _rgb555_canvas(rgb), meta


def _validate_prepared_warm_input(rom, warm_config, manifest, blobs):
    """Recognize the ordinary warm builder's output without trusting its label."""
    try:
        base = int(warm_config['metadata_cpu']) - ROM_BASE
        size = int(warm_config['metadata_bytes'])
        header = WARM_HEADER.pack(b'WPN1', 1, 32, len(manifest['poses']),
                                  int(manifest['model']['model_id']), len(blobs), 0)
        if rom[base:base + WARM_HEADER.size] != header:
            return False
        addresses = warm_config['image_cpu_addresses']
        if len(addresses) != len(blobs):
            return False
        desc_start = WARM_HEADER.size
        for i, pose in enumerate(manifest['poses']):
            image = manifest['images'][pose['image_index']]
            expected = POSE_DESC.pack(
                pose['model_id'], pose['handle'], pose['frame'], pose['image_index'],
                pose['width'], pose['height'], *pose['offset'], *pose['bounds'],
                addresses[pose['image_index']], image['image_length'], 0)
            start = base + desc_start + i * POSE_DESC.size
            if rom[start:start + POSE_DESC.size] != expected:
                return False
        if desc_start + len(manifest['poses']) * POSE_DESC.size > size:
            return False
        for cpu, blob in zip(addresses, blobs):
            offset = int(cpu) - ROM_BASE
            if offset < 0 or offset + len(blob) > len(rom) or rom[offset:offset + len(blob)] != blob:
                return False
        for change in warm_config.get('palette_changes', []):
            offset = 0x219000 + 2 * int(change['cgram_index'])
            if struct.unpack_from('<H', rom, offset)[0] != int(change['color']):
                return False
        return True
    except (KeyError, IndexError, TypeError, ValueError, struct.error):
        return False


def prepare_bg8(source, baseline, warm_config):
    """Return exact source-derived patch writes and configuration.

    `warm_config` is the result of ``source_warm_presentation_assets.prepare``.
    The caller applies these writes after its ordinary warm payload; all CPU
    addresses in the returned config use the existing full-bank HiROM alias.
    """
    rom = bytes(baseline)
    if len(rom) != ROM_SIZE:
        raise ValueError('BG8_BASELINE_ROM_EXTENT')
    input_sha = hashlib.sha256(rom).hexdigest()
    if warm_config.get('schema') != 'BYOR_WARM_PRESENTATION_ASSETS_V1':
        raise ValueError('BG8_WARM_CONFIG_SCHEMA')
    if warm_config.get('model_id') != 3 or warm_config.get('pose_count') != 149 or warm_config.get('image_count') != 71:
        raise ValueError('BG8_WARM_ASSET_DOMAIN')
    packed = derive(source)
    manifest = packed['manifest']
    if manifest['source_pak_sha256'] != warm_config.get('source_pak_sha256'):
        raise ValueError('BG8_SOURCE_HASH_MISMATCH')
    if manifest['pose_count'] != 149 or len(manifest['images']) != 71:
        raise ValueError('BG8_SOURCE_ASSET_COUNTS')
    if warm_config.get('baseline_rom_sha256') == input_sha:
        input_mode = 'original_baseline'
    elif _validate_prepared_warm_input(rom, warm_config, manifest, packed['image_blobs']):
        input_mode = 'prepared_warm_rom'
    else:
        raise ValueError('BG8_BASELINE_HASH_OR_PREPARED_WARM_MISMATCH')
    actor_colors, used_actor_indices, actor_palette = _used_actor_colors(source, manifest, packed['image_blobs'])
    old_tiles, maps, old_cgram = _old_backdrop(rom)
    old_colors = {int(v) for tile in old_tiles for v in tile.flat}
    stage, stage_meta = _stage_canvas(source)
    if stage.shape != (224, 256):
        raise ValueError('BG8_STAGE_CANVAS_SHAPE')
    stage_colors = {int(v) for v in np.unique(stage)}
    if not old_colors.issubset(stage_colors):
        raise ValueError('BG8_IMMUTABLE_CATALOG_HAS_COLOR_OUTSIDE_VISIBLE_STAGE_PALETTE')
    palette_values = sorted(actor_colors | stage_colors)
    if len(palette_values) > 256 or 0 not in palette_values:
        raise ValueError('BG8_PALETTE_CAPACITY')
    # Reserve code zero for transparent source pixels and fixed black.
    palette = [0] + [c for c in palette_values if c != 0]
    # The existing opaque actor tile helper treats LUT code zero as transparent.
    # If an authored nonzero source index is black, add a second black entry so
    # its opaque source pixels remain drawable without changing RGB555 output.
    opaque_black = any(int(actor_palette['rgb555'][i]) == 0 for i in used_actor_indices)
    if opaque_black:
        palette.append(0)
    if len(palette) > 256 or (len(set(palette)) != len(palette) and not (opaque_black and palette.count(0) == 2)):
        raise ValueError('BG8_PALETTE_INVALID')
    color_to_index = {c: i for i, c in enumerate(palette)}
    opaque_black_index = len(palette) - 1 if opaque_black else 0
    lut = [0] * 256
    source_rgb = actor_palette['rgb555']
    for index in used_actor_indices:
        value = int(source_rgb[index])
        if value not in color_to_index:
            raise ValueError('BG8_ACTOR_COLOR_UNMAPPED')
        lut[index] = opaque_black_index if value == 0 else color_to_index[value]
        if lut[index] == 0:
            raise ValueError('BG8_OPAQUE_ACTOR_MAPS_TRANSPARENT')
    lut_raw = struct.pack('<256H', *lut)
    if any(value > 255 for value in lut):
        raise AssertionError('BG8_LUT_CODE_RANGE')
    plane_tables = build_pair_tables(lut_raw)
    if any(plane_tables[4]):
        raise AssertionError('BG8_UNUSED_TENTH_PLANE_NONZERO')

    # Rebuild one 80-byte interleaved tile for every immutable source home.
    catalog = bytearray()
    new_tiles = []
    for tile in old_tiles:
        try:
            indexed = np.vectorize(color_to_index.__getitem__, otypes=[np.uint8])(tile)
        except KeyError as exc:
            raise ValueError('BG8_BACKDROP_COLOR_UNMAPPED') from exc
        encoded = _encode_bg8_row_interleaved(indexed)
        decoded = _decode_bg8_row_interleaved(encoded)
        reconstructed = np.asarray(palette, dtype=np.uint16)[decoded]
        if not np.array_equal(reconstructed, tile):
            raise ValueError('BG8_BACKDROP_TILE_ROUNDTRIP')
        catalog.extend(encoded)
        new_tiles.append(reconstructed)

    # Validate the ROM map reconstruction against the independently composed
    # pinned source stage, including the 4 offscreen map rows only as storage.
    reconstructed_canvas = np.empty((224, 256), dtype=np.uint16)
    for y in range(224):
        for x in range(256):
            map_index = (y // 8) * 32 + (x // 8)
            tile_id = struct.unpack_from('<H', maps, map_index * 2)[0] & 0x03ff
            if tile_id >= BG8_TILE_COUNT:
                raise ValueError('BG8_MAP_TILE_OUT_OF_RANGE')
            reconstructed_canvas[y, x] = new_tiles[tile_id][y & 7, x & 7]
    if not np.array_equal(reconstructed_canvas, stage):
        raise ValueError('BG8_SOURCE_STAGE_RECONSTRUCTION_MISMATCH')

    meta_cpu = int(warm_config['metadata_cpu'])
    meta_len = int(warm_config['metadata_bytes'])
    if meta_cpu < ROM_BASE or meta_cpu - ROM_BASE != META_OFFSET or meta_len < 1 or meta_len > 32768:
        raise ValueError('BG8_METADATA_BANK_BINDING')
    lut_cpu = int(warm_config['lut_cpu'])
    planes_cpu = int(warm_config['color_planes_cpu'])
    lut_offset = lut_cpu - ROM_BASE
    planes_offset = planes_cpu - ROM_BASE
    if lut_offset < META_OFFSET or lut_offset + 512 > META_OFFSET + meta_len:
        raise ValueError('BG8_LUT_OUTSIDE_METADATA')
    if planes_offset < META_OFFSET or planes_offset + 20480 > META_OFFSET + meta_len:
        raise ValueError('BG8_PLANES_OUTSIDE_METADATA')
    cgram_offset = (META_OFFSET + meta_len + 1) & ~1
    if cgram_offset + PALETTE_BYTES > META_OFFSET + 32768:
        raise ValueError('BG8_CGRAM_METADATA_BANK_CAPACITY')
    if any(rom[cgram_offset:cgram_offset + PALETTE_BYTES]):
        raise ValueError('BG8_CGRAM_DESTINATION_NONEMPTY')
    old_f3 = _old_f3_catalog(rom)
    if rom[BG8_OFFSET:BG8_OFFSET + BG8_BYTES] != old_f3:
        raise ValueError('BG8_EXISTING_F3_CATALOG_MISMATCH')
    # Applying the replacement LUT/tables requires patching existing warm data;
    # don't overlap the image metadata or the appended palette block.
    writes = [
        dict(offset=lut_offset, data=lut_raw, reason='BG8 source-index to exact RGB555 palette LUT'),
        dict(offset=planes_offset, data=b''.join(plane_tables), reason='BG8 four active source tile planes plus zero fifth pair'),
        dict(offset=cgram_offset, data=struct.pack('<256H', *(palette + [0] * (256-len(palette)))), reason='BG8 exact RGB555 palette; cold CGRAM retained'),
        dict(offset=BG8_OFFSET, data=bytes(catalog), reason='BG8 interleaved 10-byte-row immutable backdrop catalog'),
    ]
    ordered = sorted(writes, key=lambda w: w['offset'])
    for a, b in zip(ordered, ordered[1:]):
        if a['offset'] + len(a['data']) > b['offset']:
            raise ValueError('BG8_PATCH_WRITE_OVERLAP')
    forbidden = [(OLD_CGRAM_OFFSET, OLD_CGRAM_OFFSET + 512), (MAP_OFFSET, MAP_OFFSET + 2048)]
    if any(a['offset'] < hi and a['offset'] + len(a['data']) > lo for a in writes for lo, hi in forbidden):
        raise ValueError('BG8_COLD_ASSET_OVERWRITE')
    if any(w['offset'] == 0xE18000 or w['offset'] == 0xF40000 for w in writes):
        raise ValueError('BG8_FORBIDDEN_MAP_OR_MASK_WRITE')
    config = dict(schema='BYOR_WARM_BG8_ASSETS_V1',
        source_pak_sha256=manifest['source_pak_sha256'],
        baseline_rom_sha256=warm_config['baseline_rom_sha256'],
        input_rom_sha256=input_sha, input_rom_mode=input_mode,
        source_manifest=manifest, source_pose_count=len(manifest['poses']),
        source_image_count=len(manifest['images']), actor_palette_path=actor_palette['source_path'],
        actor_palette_sha256=actor_palette['asset_sha256'],
        used_actor_source_indices=sorted(used_actor_indices), palette_rgb555=palette,
        stage_palette_color_count=len(stage_colors), actor_palette_color_count=len(actor_colors),
        exact_source_palette_union_count=len(actor_colors | stage_colors),
        palette_count=len(palette), palette_cpu=ROM_BASE+cgram_offset,
        palette_rom_offset=cgram_offset, palette_bytes=PALETTE_BYTES,
        lut_cpu=lut_cpu, lut_bytes=len(lut_raw), color_planes_cpu=planes_cpu,
        color_planes_bytes=sum(map(len, plane_tables)), active_plane_pairs=4,
        fifth_pair_all_zero=True, bg8_catalog_cpu=ROM_BASE+BG8_OFFSET,
        bg8_catalog_rom_offset=BG8_OFFSET, bg8_tile_count=BG8_TILE_COUNT,
        bg8_tile_stride=BG8_TILE_BYTES, bg8_catalog_bytes=len(catalog),
        bg8_catalog_sha256=hashlib.sha256(catalog).hexdigest(),
        old_high_rom_offset=HIGH_OFFSET, old_low_rom_offset=LOW_OFFSET,
        old_cgram_rom_offset=OLD_CGRAM_OFFSET, old_cgram_sha256=hashlib.sha256(old_cgram).hexdigest(),
        old_f3_catalog_sha256=hashlib.sha256(old_f3).hexdigest(),
        f3_replacement_validated_against_source_components=True,
        cold_map_rom_offset=MAP_OFFSET, cold_map_sha256=hashlib.sha256(maps).hexdigest(),
        stage=stage_meta, stage_rgb555_sha256=hashlib.sha256(stage.astype('<u2').tobytes()).hexdigest(),
        reconstruction_matches_source=True,
        writes=[dict(offset=w['offset'], length=len(w['data']), reason=w['reason'],
                     sha256=hashlib.sha256(w['data']).hexdigest()) for w in writes],
        integration=dict(apply_warm_asset_metadata_and_image_writes=True,
                         omit_legacy_palette_changes=True,
                         omitted_legacy_palette_change_offsets=[0x219000 + 2 * int(c['cgram_index'])
                                                               for c in warm_config.get('palette_changes', [])],
                         preserve_old_cgram_until_cold_activation=True),
        limitations=['data preparation only; no native runtime admission or PPU setup claim',
                     'GUILE2 camera zero actors empty for backdrop verification',
                     'opaque He_Man SELECT/IDLE/WALK map 0 actor domain only',
                     'full adjust-bind service remains unimplemented'])
    return writes, config
