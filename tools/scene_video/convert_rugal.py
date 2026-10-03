#!/usr/bin/env python3
"""Deterministic offline conversion of the original BOR Rugal animation.

This module intentionally emits only the relocatable frame stream consumed by
BORVID1. It does not decode GIF at runtime and has no MSU/audio dependencies.
"""
import io
import struct
import sys

import numpy as np
from PIL import Image

ROOT = __import__('os').path.dirname(__import__('os').path.dirname(__file__))
sys.path.insert(0, __import__('os').path.join(ROOT, 'bor_converter'))
from pak_extract import extract  # noqa: E402

SOURCE_PATH = r"DATA\SCENES\RUGAL.GIF"
SOURCE_WIDTH = 320
SOURCE_HEIGHT = 240
SOURCE_DURATION_MS = 40
SOURCE_FRAMES = 126
RUGAL_SCENE_ID = 1
WIDTH = 256
HEIGHT = 192
TILE_W = 32
TILE_H = 24
TILEMAP_BYTES = TILE_W * TILE_H * 2
MAX_TILES = 384
BYTES_PER_TILE = 32


def source_frames(pak_path):
    data = extract(pak_path, SOURCE_PATH)
    image = Image.open(io.BytesIO(data))
    if image.size != (SOURCE_WIDTH, SOURCE_HEIGHT):
        raise ValueError(f"Rugal GIF dimensions changed: {image.size}")
    frames = []
    durations = []
    for index in range(SOURCE_FRAMES):
        image.seek(index)
        durations.append(image.info.get("duration"))
        frames.append(image.convert("RGB").copy())
    try:
        image.seek(SOURCE_FRAMES)
        raise ValueError("Rugal GIF contains more than 126 frames")
    except EOFError:
        pass
    if len(frames) != SOURCE_FRAMES or any(d != SOURCE_DURATION_MS for d in durations):
        raise ValueError(f"unexpected Rugal frame timing: {durations}")
    return data, frames, durations


def scaled_frames(frames):
    return [frame.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
            for frame in frames]


def shared_palettes(frames):
    # A single stable 32-colour quantizer over the complete clip avoids
    # frame-to-frame palette swimming. Pillow's MEDIANCUT is deterministic for
    # this fixed RGB input and no dithering is used here; the tile converter's
    # bounded local nearest-colour step handles the two 4BPP banks.
    rows = np.concatenate([np.asarray(frame, dtype=np.uint8) for frame in frames], axis=0)
    sheet = Image.fromarray(rows, "RGB")
    quantized = sheet.quantize(colors=32, method=Image.Quantize.MEDIANCUT,
                               dither=Image.Dither.NONE)
    palette = quantized.getpalette()[:32 * 3]
    colors = np.asarray(palette, dtype=np.uint8).reshape(32, 3)
    return colors[:16].astype(np.int16), colors[16:32].astype(np.int16)


def encode_tile(pixels):
    encoded = bytearray(BYTES_PER_TILE)
    for row in range(8):
        planes = [0, 0, 0, 0]
        for col in range(8):
            value = int(pixels[row, col])
            bit = 7 - col
            for plane in range(4):
                planes[plane] |= ((value >> plane) & 1) << bit
        encoded[2 * row] = planes[0]
        encoded[2 * row + 1] = planes[1]
        encoded[16 + 2 * row] = planes[2]
        encoded[16 + 2 * row + 1] = planes[3]
    return bytes(encoded)


def _reduce_tiles(tile_list, tilemap, tile_palettes, palettes):
    if len(tile_list) <= MAX_TILES:
        return tile_list, tilemap, False
    raw = np.frombuffer(b"".join(tile_list), dtype=np.uint8).reshape(len(tile_list), BYTES_PER_TILE)
    kept = list(range(MAX_TILES))
    kept_raw = raw[:MAX_TILES]
    mapping = np.arange(len(tile_list), dtype=np.uint16)
    for index in range(MAX_TILES, len(tile_list)):
        candidates = [k for k in kept if tile_palettes[k] == tile_palettes[index]]
        if not candidates:
            candidates = kept
        distances = np.sum((kept_raw[candidates].astype(np.int16)
                             - raw[index].astype(np.int16)) ** 2, axis=1)
        mapping[index] = candidates[int(np.argmin(distances))]
    reduced_map = [int(mapping[value]) for value in tilemap]
    remap = {old: new for new, old in enumerate(kept)}
    reduced_map = [remap.get(value, 0) for value in reduced_map]
    return [tile_list[index] for index in kept], reduced_map, True


def convert_frame(frame, palettes):
    rgb = np.asarray(frame, dtype=np.int16)
    tile_list = []
    tile_lookup = {}
    tilemap = []
    tile_palettes = []
    before = 0
    for tile_y in range(TILE_H):
        for tile_x in range(TILE_W):
            block = rgb[tile_y * 8:(tile_y + 1) * 8,
                        tile_x * 8:(tile_x + 1) * 8]
            errors = [np.sum((block[:, :, None, :] - palette[None, None, :, :]) ** 2,
                             axis=(0, 1, 3)) for palette in palettes]
            palette_index = int(np.argmin([int(error.sum()) for error in errors]))
            palette = palettes[palette_index]
            indices = np.argmin(np.sum((block[:, :, None, :] - palette[None, None, :, :]) ** 2,
                                       axis=3), axis=2).astype(np.uint8)
            encoded = encode_tile(indices)
            if encoded not in tile_lookup:
                tile_lookup[encoded] = len(tile_list)
                tile_list.append(encoded)
                tile_palettes.append(palette_index)
            tilemap.append(tile_lookup[encoded] | (palette_index << 10))
    before = len(tile_list)
    tile_list, reduced_indices, reduced = _reduce_tiles(
        tile_list, [value & 0x3FF for value in tilemap], tile_palettes, palettes)
    tilemap = [index | (tilemap[pos] & 0xFC00)
               for pos, index in enumerate(reduced_indices)]
    palette_bytes = bytearray()
    for palette in palettes:
        for red, green, blue in palette:
            value = (int(red) >> 3) | ((int(green) >> 3) << 5) | ((int(blue) >> 3) << 10)
            palette_bytes += struct.pack("<H", value)
    return (b"".join(tile_list), struct.pack("<" + "H" * len(tilemap), *tilemap),
            bytes(palette_bytes), before, len(tile_list), reduced)


def build_payload(pak_path):
    source_data, original, durations = source_frames(pak_path)
    frames = scaled_frames(original)
    palettes = shared_palettes(frames)
    converted = [convert_frame(frame, palettes) for frame in frames]
    records = []
    for frame_id, (tiles, tilemap, palette, before, after, reduced) in enumerate(converted):
        if len(tilemap) != TILEMAP_BYTES or len(tiles) > MAX_TILES * BYTES_PER_TILE:
            raise ValueError("Rugal frame exceeds BOR scene-video bounds")
        length_header = ((len(tilemap) // 2) & 0x7FF
                         | (((len(tiles) // BYTES_PER_TILE) & 0x7FF) << 11)
                         | (((len(palette) // 2) & 0xFF) << 22))
        records.append(struct.pack("<HI", frame_id, length_header)
                       + tilemap + tiles + palette)
    pointer_table_size = 4 + SOURCE_FRAMES * 4
    cursor = pointer_table_size
    pointers = []
    for record in records:
        pointers.append(cursor)
        cursor += len(record)
    payload = struct.pack("<I", SOURCE_FRAMES)
    payload += struct.pack("<" + "I" * len(pointers), *pointers)
    payload += b"".join(records)
    stats = {
        "source_sha256": __import__('hashlib').sha256(source_data).hexdigest(),
        "source_width": SOURCE_WIDTH, "source_height": SOURCE_HEIGHT,
        "source_frame_count": len(original), "source_durations_ms": durations,
        "width": WIDTH, "height": HEIGHT, "tilemap_bytes": TILEMAP_BYTES,
        "min_unique_tiles_before": min(item[3] for item in converted),
        "avg_unique_tiles_before": sum(item[3] for item in converted) / len(converted),
        "max_unique_tiles_before": max(item[3] for item in converted),
        "min_unique_tiles": min(item[4] for item in converted),
        "avg_unique_tiles": sum(item[4] for item in converted) / len(converted),
        "max_unique_tiles": max(item[4] for item in converted),
        "frames_reduced": sum(item[5] for item in converted),
        "max_tile_bytes": max(len(item[0]) for item in converted),
        "palette_bytes": len(converted[0][2]),
        "max_frame_record_bytes": max(len(record) for record in records),
        "payload_size": len(payload),
    }
    return payload, stats
