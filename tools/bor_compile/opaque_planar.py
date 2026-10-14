"""Lossless, source-relative opaque 8bpp+2bpp mask blitting.

These are actor assets, not complete pictures keyed by player position.
Eight horizontal phases cover all integer X positions. Y is a row address;
there is no eightfold vertical-phase table. Transparency is SOURCE INDEX 0,
not RGB black. Only immutable component-palette identities are admitted.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import struct
from typing import Iterable
import numpy as np


def encode_pair(packed: np.ndarray) -> bytes:
    """Independent scalar planar encoder; 8 HIGH planes then 2 LOW planes."""
    a = np.asarray(packed)
    if a.shape != (8, 8) or a.dtype.kind not in 'ui' or np.any(a > 1023):
        raise ValueError('PACKED_COMPONENT_TILE_DOMAIN')
    out = bytearray(80)
    for y in range(8):
        for x in range(8):
            value = int(a[y, x])
            for bit in range(10):
                offset = ((bit // 2) * 16 + y * 2 + bit % 2)
                out[offset] |= ((value >> bit) & 1) << (7 - x)
    return bytes(out)


def decode_pair(raw: bytes) -> np.ndarray:
    if len(raw) != 80:
        raise ValueError('PLANAR_PAIR_LENGTH')
    out = np.zeros((8, 8), dtype=np.uint16)
    for bit in range(10):
        for y in range(8):
            byte = raw[(bit // 2) * 16 + y * 2 + bit % 2]
            for x in range(8):
                out[y, x] |= ((byte >> (7 - x)) & 1) << bit
    return out


def tile_to_rows(raw: bytes) -> np.ndarray:
    """8 rows x 5 plane-pair words; independent of target pointer placement."""
    if len(raw) != 80:
        raise ValueError('PLANAR_PAIR_LENGTH')
    a = np.frombuffer(raw, dtype='<u2').reshape(5, 8)
    return a.T.copy()


def rows_to_tile(rows: np.ndarray) -> bytes:
    a = np.asarray(rows)
    if a.shape != (8, 5) or a.dtype.kind not in 'ui' or np.any(a > 65535):
        raise ValueError('ROW_WORD_DOMAIN')
    return a.T.astype('<u2').tobytes()


def coverage_masks(foreground: np.ndarray) -> np.ndarray:
    a = np.asarray(foreground, dtype=bool)
    if a.shape != (224, 256):
        raise ValueError('FOREGROUND_DOMAIN')
    # [tileY, tileX, row] -- bit 7 is the leftmost pixel.
    return np.packbits(a.reshape(28, 8, 32, 8).transpose(0, 2, 1, 3),
                       axis=3, bitorder='big')[..., 0]


@dataclass(frozen=True)
class PhaseAtlas:
    crop_x: int
    crop_y: int
    width: int
    height: int
    original_width: int
    original_height: int
    source_sha256: str
    lookup_sha256: str
    # [sourceY, sourceXChunk, (duplicated coverage, 5 plane-pair words)]
    phases: tuple[np.ndarray, ...]

    @property
    def asset_bytes(self) -> int:
        return sum(a.nbytes for a in self.phases)

    def save(self, folder, stem: str) -> dict:
        from pathlib import Path
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        entries = []
        for phase, array in enumerate(self.phases):
            data = array.astype('<u2').tobytes()
            name = f'{stem}-phase-{phase}.bin'
            (folder / name).write_bytes(data)
            entries.append(dict(phase=phase, path=name, bytes=len(data),
                                row_stride=array.shape[1] * 12,
                                row_count=array.shape[0],
                                sha256=hashlib.sha256(data).hexdigest()))
        return dict(crop_x=self.crop_x, crop_y=self.crop_y,
                    width=self.width, height=self.height,
                    original_width=self.original_width,
                    original_height=self.original_height,
                    source_sha256=self.source_sha256,
                    lookup_sha256=self.lookup_sha256,
                    bytes=self.asset_bytes, record_bytes=12, phases=entries)


def compile_atlas(indices: np.ndarray, lookup: np.ndarray) -> PhaseAtlas:
    src = np.asarray(indices)
    lut = np.asarray(lookup)
    if (src.ndim != 2 or src.dtype.kind not in 'ui' or np.any(src > 255)
            or not src.size or lut.shape != (256,) or lut.dtype.kind not in 'ui'
            or np.any(lut > 1023)):
        raise ValueError('OPAQUE_ATLAS_DOMAIN')
    ys, xs = np.nonzero(src)
    if len(xs):
        bx, by, ex, ey = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
    else:
        bx = by = ex = ey = 0
    cut = src[by:ey, bx:ex].astype(np.uint8)
    phases = []
    for phase in range(8):
        cols = (cut.shape[1] + phase + 7) // 8 if cut.size else 0
        words = np.zeros((cut.shape[0], cols, 6), dtype='<u2')
        for y in range(cut.shape[0]):
            vis = np.zeros(cols * 8, dtype=np.uint8)
            values = np.zeros(cols * 8, dtype=np.uint16)
            vis[phase:phase + cut.shape[1]] = cut[y] != 0
            values[phase:phase + cut.shape[1]] = np.where(cut[y] != 0, lut[cut[y]], 0)
            masks = np.packbits(vis, bitorder='big')
            words[y, :, 0] = masks.astype(np.uint16) * 257
            for bit in range(10):
                plane = np.packbits(((values >> bit) & 1).astype(np.uint8), bitorder='big')
                words[y, :, 1 + bit // 2] |= plane.astype(np.uint16) << (8 * (bit % 2))
        words.flags.writeable = False
        phases.append(words)
    return PhaseAtlas(bx, by, ex - bx, ey - by, src.shape[1], src.shape[0],
                      hashlib.sha256(src.astype(np.uint8).tobytes()).hexdigest(),
                      hashlib.sha256(lut.astype('<u2').tobytes()).hexdigest(), tuple(phases))


def compose_patch(backdrop_tiles: list[bytes], backdrop_map: np.ndarray,
                  foreground_masks: np.ndarray, atlas: PhaseAtlas,
                  left: int, top: int) -> tuple[dict[int, bytes], dict]:
    """Reference implementation of the native tile/row job construction.

    left/top locate the ORIGINAL source raster, before transparent-edge cropping.
    Cropping is only a storage optimization; it never scales or moves artwork.
    Returned cell -> 80-byte pairs differ from the immutable backdrop. Old actor
    coverage not in this patch must revert via actual resident identity, not by
    assuming that an old backdrop slot still contains its original bytes.
    """
    if type(left) is not int or type(top) is not int:
        raise ValueError('PROJECTED_COORDINATES_REQUIRED')
    bm = np.asarray(backdrop_map)
    if bm.shape not in ((28, 32), (32, 32)) or np.asarray(foreground_masks).shape != (28, 32, 8):
        raise ValueError('SCENE_MAP_DOMAIN')
    if np.any(bm[:28] < 0) or np.any(bm[:28] >= len(backdrop_tiles)):
        raise ValueError('BACKDROP_IDENTITY_DOMAIN')
    origin_x = left + atlas.crop_x
    origin_y = top + atlas.crop_y
    phase = origin_x % 8
    first_col = origin_x // 8
    record = atlas.phases[phase]
    counts = dict(candidate_tiles=0, retained_backdrop_tiles=0, composed_tiles=0,
                  copy_back_rows=0, copy_source_rows=0, mixed_rows=0,
                  uploaded_tile_bytes=0, source_asset_bytes=atlas.asset_bytes)
    result = {}
    if not atlas.width or not atlas.height:
        return result, counts
    y0, y1 = max(0, origin_y // 8), min(27, (origin_y + atlas.height - 1) // 8)
    x0, x1 = max(0, first_col), min(31, first_col + record.shape[1] - 1)
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            counts['candidate_tiles'] += 1
            masks = np.zeros(8, dtype=np.uint16)
            src_words = np.zeros((8, 5), dtype=np.uint16)
            for ry in range(8):
                sy = ty * 8 + ry - origin_y
                if 0 <= sy < atlas.height:
                    row = record[sy, tx - first_col]
                    masks[ry] = int(row[0]) & (65535 ^ (int(foreground_masks[ty, tx, ry]) * 257))
                    src_words[ry] = row[1:]
            if not np.any(masks):
                counts['retained_backdrop_tiles'] += 1
                continue
            bg = backdrop_tiles[int(bm[ty, tx])]
            rows = tile_to_rows(bg)
            counts['copy_back_rows'] += int(np.count_nonzero(masks == 0))
            counts['copy_source_rows'] += int(np.count_nonzero(masks == 65535))
            counts['mixed_rows'] += int(np.count_nonzero((masks != 0) & (masks != 65535)))
            # The same five-word operation used by the emitted 65816 row kernel.
            rows ^= (rows ^ src_words) & masks[:, None]
            encoded = rows_to_tile(rows)
            if encoded == bg:
                counts['retained_backdrop_tiles'] += 1
                continue
            result[ty * 32 + tx] = encoded
    counts['composed_tiles'] = len(result)
    counts['uploaded_tile_bytes'] = len(result) * 80  # not a claim about cache misses
    return result, counts


def visual_key(*, model: int, frame: int, direction: int, palette: str,
               stage: str, underlay_generation: int, x_q16: int, z_q16: int,
               offset_x: int, offset_y: int, camera_x: int = 0,
               camera_y: int = 0, altitude_q16: int = 0) -> tuple:
    """Bounded positive-ground adapter used by this proof, NOT all BOR geometry.

    Validate supported model/direction/frame/leases before comparing this key.
    Snapshot epoch and invisible fractional motion intentionally are not keys.
    World update and snapshot acknowledgement still happen on a render no-op.
    """
    if (x_q16 < 0 or z_q16 < 0 or altitude_q16 != 0
            or direction != 1 or camera_x != 0 or camera_y != 0):
        raise ValueError('BOUNDED_VISUAL_CAPABILITY')
    return (model, frame, direction, palette, stage, underlay_generation,
            (x_q16 >> 16) - offset_x, (z_q16 >> 16) - offset_y)
