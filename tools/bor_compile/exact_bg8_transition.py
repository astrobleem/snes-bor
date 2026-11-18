"""Exact-content planner for one SNES 8bpp BG map transition.

This is a deterministic offline plan, not a hardware timing or native admission
claim. Inputs are complete 256x224 RGB555 canvases. The plan reserves the final
2,048-byte 32x32 map at VRAM byte 63,488 and uses the preceding 63,488 bytes for
992 unique 64-byte tiles.
"""
from __future__ import annotations

import hashlib
from numbers import Integral
from typing import Sequence

WIDTH = 256
HEIGHT = 224
TILE = 8
TILE_BYTES = 64
MAP_BYTES = 2048
VRAM_BYTES = 65536
MAP_OFFSET = 63488
TILE_SLOTS = MAP_OFFSET // TILE_BYTES
VISIBLE_MAP_ROWS = HEIGHT // TILE
VISIBLE_MAP_CELLS = (WIDTH // TILE) * VISIBLE_MAP_ROWS


def _pixels(rgb555: Sequence[Sequence[int]]) -> tuple[tuple[int, ...], ...]:
    if len(rgb555) != HEIGHT:
        raise ValueError("RGB555_HEIGHT")
    rows: list[tuple[int, ...]] = []
    for row in rgb555:
        if len(row) != WIDTH:
            raise ValueError("RGB555_WIDTH")
        cooked = []
        for value in row:
            if isinstance(value, bool) or not isinstance(value, Integral) or not 0 <= value <= 0x7FFF:
                raise ValueError("RGB555_VALUE")
            cooked.append(int(value))
        rows.append(tuple(cooked))
    return tuple(rows)


def _palette_for_validated(canvases: Sequence[tuple[tuple[int, ...], ...]]) -> tuple[int, ...]:
    colors = {color for canvas in canvases for row in canvas for color in row}
    colors.discard(0)
    if len(colors) + 1 > 256:
        raise ValueError("RGB555_PALETTE_OVERFLOW")
    return (0, *sorted(colors))


def stable_palette(*canvases: Sequence[Sequence[int]]) -> tuple[int, ...]:
    """Return a validated exact shared palette with RGB555 black at index zero."""
    if not canvases:
        raise ValueError("PALETTE_REQUIRES_CANVAS")
    return _palette_for_validated(tuple(_pixels(canvas) for canvas in canvases))


def _validated_palette(palette: Sequence[int],
                       canvases: Sequence[tuple[tuple[int, ...], ...]]) -> tuple[int, ...]:
    if not palette or len(palette) > 256:
        raise ValueError("RGB555_PALETTE_EXTENT")
    values = []
    for color in palette:
        if isinstance(color, bool) or not isinstance(color, Integral) or not 0 <= color <= 0x7FFF:
            raise ValueError("RGB555_PALETTE_VALUE")
        values.append(int(color))
    if values[0] != 0:
        raise ValueError("RGB555_BLACK_MUST_BE_INDEX_ZERO")
    if len(set(values)) != len(values):
        raise ValueError("RGB555_PALETTE_DUPLICATE")
    available = set(values)
    if any(color not in available for canvas in canvases for row in canvas for color in row):
        raise ValueError("RGB555_PALETTE_MISSING_COLOR")
    return tuple(values)


def encode_tile(indices: Sequence[Sequence[int]]) -> bytes:
    """Encode an 8x8 palette-index tile in SNES 8bpp planar order."""
    if len(indices) != 8 or any(len(row) != 8 for row in indices):
        raise ValueError("TILE_EXTENT")
    output = bytearray()
    for pair in range(4):
        for row in indices:
            lo = hi = 0
            for x, value in enumerate(row):
                if isinstance(value, bool) or not isinstance(value, Integral) or not 0 <= value <= 255:
                    raise ValueError("PALETTE_INDEX")
                mask = 0x80 >> x
                if value & (1 << (pair * 2)):
                    lo |= mask
                if value & (1 << (pair * 2 + 1)):
                    hi |= mask
            output.extend((lo, hi))
    return bytes(output)


def decode_tile(data: bytes | bytearray | memoryview) -> tuple[tuple[int, ...], ...]:
    if len(data) != TILE_BYTES:
        raise ValueError("TILE_DATA_EXTENT")
    rows = [[0] * 8 for _ in range(8)]
    cursor = 0
    for pair in range(4):
        for y in range(8):
            lo, hi = data[cursor], data[cursor + 1]
            cursor += 2
            for x in range(8):
                mask = 0x80 >> x
                if lo & mask:
                    rows[y][x] |= 1 << (pair * 2)
                if hi & mask:
                    rows[y][x] |= 1 << (pair * 2 + 1)
    return tuple(tuple(row) for row in rows)


def _encode_with_palette(canvas: tuple[tuple[int, ...], ...], palette: tuple[int, ...]) -> dict:
    palette_index = {color: index for index, color in enumerate(palette)}
    indexed = bytes(palette_index[color] for row in canvas for color in row)
    by_content: dict[bytes, int] = {}
    tiles: list[bytes] = []
    tilemap = []
    for ty in range(VISIBLE_MAP_ROWS):
        for tx in range(WIDTH // TILE):
            block = tuple(tuple(indexed[(ty * TILE + y) * WIDTH + tx * TILE + x]
                                for x in range(TILE)) for y in range(TILE))
            encoded = encode_tile(block)
            tile_id = by_content.get(encoded)
            if tile_id is None:
                tile_id = len(tiles)
                by_content[encoded] = tile_id
                tiles.append(encoded)
            tilemap.append(tile_id)
    return dict(width=WIDTH, height=HEIGHT, palette=palette, indices=indexed,
        tiles=tuple(tiles), visible_tilemap=tuple(tilemap),
        rgb555_sha256=hashlib.sha256(b"".join(
            value.to_bytes(2, "little") for row in canvas for value in row)).hexdigest())


def encode_image(rgb555: Sequence[Sequence[int]], *, palette: Sequence[int] | None = None) -> dict:
    canvas = _pixels(rgb555)
    palette = (_palette_for_validated((canvas,)) if palette is None
               else _validated_palette(palette, (canvas,)))
    image = _encode_with_palette(canvas, palette)
    if len(image["tiles"]) > TILE_SLOTS:
        raise ValueError("SINGLE_IMAGE_TILE_CAPACITY")
    return image


def _map_bytes(visible_slots: Sequence[int]) -> bytes:
    if len(visible_slots) != VISIBLE_MAP_CELLS:
        raise ValueError("VISIBLE_MAP_EXTENT")
    words = list(visible_slots) + [0] * ((32 - VISIBLE_MAP_ROWS) * 32)
    output = bytearray()
    for slot in words:
        if not 0 <= slot < TILE_SLOTS:
            raise ValueError("MAP_TILE_SLOT")
        output.extend((slot & 0xFF, (slot >> 8) & 0x03))
    if len(output) != MAP_BYTES:
        raise AssertionError("internal map size error")
    return bytes(output)


def plan_transition(old_rgb555: Sequence[Sequence[int]],
                    target_rgb555: Sequence[Sequence[int]], *,
                    palette: Sequence[int] | None = None) -> dict:
    """Plan pre-stage and final atomic writes while preserving old pixels.

    New target contents first consume unused resident slots. Any remaining new
    contents are assigned to old-only slots and written in the atomic phase.
    The returned byte counts describe payload only; no budget is inferred.
    """
    old_canvas = _pixels(old_rgb555)
    target_canvas = _pixels(target_rgb555)
    palette = (_palette_for_validated((old_canvas, target_canvas)) if palette is None
               else _validated_palette(palette, (old_canvas, target_canvas)))
    old = _encode_with_palette(old_canvas, palette)
    target = _encode_with_palette(target_canvas, palette)
    if len(old["tiles"]) > TILE_SLOTS or len(target["tiles"]) > TILE_SLOTS:
        raise ValueError("SINGLE_IMAGE_TILE_CAPACITY")

    old_slots = {tile: slot for slot, tile in enumerate(old["tiles"])}
    old_used = set(old_slots.values())
    target_tiles = target["tiles"]
    shared = set(old_slots).intersection(target_tiles)
    new_tiles = [tile for tile in target_tiles if tile not in old_slots]
    free_slots = [slot for slot in range(TILE_SLOTS) if slot not in old_used]
    old_only_slots = [old_slots[tile] for tile in old["tiles"] if tile not in set(target_tiles)]

    pre_count = min(len(new_tiles), len(free_slots))
    pre_stage = [(free_slots[i], new_tiles[i]) for i in range(pre_count)]
    remaining = new_tiles[pre_count:]
    if len(remaining) > len(old_only_slots):
        raise ValueError("TRANSITION_TILE_CAPACITY")
    atomic_tile_writes = [(old_only_slots[i], tile) for i, tile in enumerate(remaining)]

    assigned = dict(old_slots)
    assigned.update({tile: slot for slot, tile in pre_stage})
    assigned.update({tile: slot for slot, tile in atomic_tile_writes})
    target_slots = [assigned[target_tiles[tile_id]] for tile_id in target["visible_tilemap"]]
    old_visible_slots = [old_slots[tile] for tile in _visible_tile_contents(old_canvas, palette)]
    target_map = _map_bytes(target_slots)
    old_map = _map_bytes(old_visible_slots)

    return dict(schema="EXACT_SNES_BG8_TRANSITION_PLAN_V1", palette=palette,
        assumptions=dict(old_image_already_installed_under_this_palette=True,
            old_residency_model="Deterministic first-occurrence unique-tile assignment for this standalone plan; actual VRAM residency is not observed.",
            not_a_chainable_residency_receipt=True,
            no_gpu_register_or_mode_setup_claim=True),
        constants=dict(vram_bytes=VRAM_BYTES, map_offset=MAP_OFFSET, map_bytes=MAP_BYTES,
            tile_bytes=TILE_BYTES, tile_slots=TILE_SLOTS, visible_map_cells=VISIBLE_MAP_CELLS),
        old=dict(rgb555_sha256=old["rgb555_sha256"], unique_tiles=len(old["tiles"]),
            map_bytes=old_map, resident_tiles=tuple((slot, tile) for tile, slot in old_slots.items())),
        target=dict(rgb555_sha256=target["rgb555_sha256"], unique_tiles=len(target_tiles),
            map_bytes=target_map),
        shared_tiles=len(shared), new_target_tiles=len(new_tiles),
        free_slot_count=len(free_slots), old_only_slot_count=len(old_only_slots),
        prestage_writes=tuple(pre_stage), atomic_tile_writes=tuple(atomic_tile_writes),
        prestage_payload_bytes=sum(len(tile) for _, tile in pre_stage),
        atomic_tile_payload_bytes=sum(len(tile) for _, tile in atomic_tile_writes),
        final_map_payload_bytes=MAP_BYTES,
        atomic_payload_bytes=sum(len(tile) for _, tile in atomic_tile_writes) + MAP_BYTES,
        metadata=dict(plan_only=True, timing_or_native_admission=False))


def _visible_tile_contents(canvas: tuple[tuple[int, ...], ...], palette: tuple[int, ...]) -> list[bytes]:
    palette_index = {color: index for index, color in enumerate(palette)}
    indexed = [[palette_index[color] for color in row] for row in canvas]
    result = []
    for ty in range(VISIBLE_MAP_ROWS):
        for tx in range(WIDTH // TILE):
            result.append(encode_tile(tuple(tuple(indexed[ty * TILE + y][tx * TILE:tx * TILE + TILE])
                                             for y in range(TILE))))
    return result


def _decode_vram(vram: bytes | bytearray, map_bytes: bytes,
                 palette: Sequence[int]) -> tuple[tuple[int, ...], ...]:
    if len(vram) != VRAM_BYTES or len(map_bytes) != MAP_BYTES:
        raise ValueError("VRAM_EXTENT")
    rows = [[0] * WIDTH for _ in range(HEIGHT)]
    for ty in range(VISIBLE_MAP_ROWS):
        for tx in range(WIDTH // TILE):
            cell = ty * 32 + tx
            slot = map_bytes[cell * 2] | ((map_bytes[cell * 2 + 1] & 0x03) << 8)
            if slot >= TILE_SLOTS:
                raise ValueError("MAP_SLOT_OUT_OF_RANGE")
            offset = slot * TILE_BYTES
            if offset + TILE_BYTES > MAP_OFFSET:
                raise ValueError("TILE_MAP_OVERLAP")
            decoded = decode_tile(vram[offset:offset + TILE_BYTES])
            for y in range(TILE):
                for x in range(TILE):
                    palette_idx = decoded[y][x]
                    if palette_idx >= len(palette):
                        raise ValueError("PALETTE_INDEX_OUT_OF_RANGE")
                    rows[ty * TILE + y][tx * TILE + x] = palette[palette_idx]
    return tuple(tuple(row) for row in rows)


def _same_typed_value(actual, expected):
    # bool/int and float/int compare equal in Python but make different claims
    # in a serialized receipt. Retain the complete expected structure and types.
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return (actual.keys() == expected.keys()
                and all(_same_typed_value(actual[key], value)
                        for key, value in expected.items()))
    if isinstance(expected, (tuple, list)):
        return (len(actual) == len(expected)
                and all(_same_typed_value(left, right)
                        for left, right in zip(actual, expected)))
    return actual == expected


def verify_transition(old_rgb555: Sequence[Sequence[int]],
                      target_rgb555: Sequence[Sequence[int]], plan: dict, *,
                      palette: Sequence[int] | None = None) -> dict:
    """Replay plan bytes and verify exact old-frame preservation then target pixels."""
    chosen_palette = plan.get("palette") if palette is None else palette
    expected = plan_transition(old_rgb555, target_rgb555, palette=chosen_palette)
    # A verified plan includes its reported counts and admission boundaries,
    # not just the bytes that happen to reach the replay below.
    if not _same_typed_value(plan, expected):
        raise ValueError("PLAN_MISMATCH")
    vram = bytearray(VRAM_BYTES)
    for slot, tile in plan["old"]["resident_tiles"]:
        if not (0 <= slot < TILE_SLOTS) or len(tile) != TILE_BYTES:
            raise ValueError("OLD_RESIDENT_RANGE")
        start = slot * TILE_BYTES
        if start + TILE_BYTES > MAP_OFFSET:
            raise ValueError("TILE_WRITE_MAP_OVERLAP")
        vram[start:start + TILE_BYTES] = tile
    vram[MAP_OFFSET:MAP_OFFSET + MAP_BYTES] = plan["old"]["map_bytes"]
    original = _pixels(old_rgb555)
    desired = _pixels(target_rgb555)

    def apply_tile_writes(writes):
        seen = set()
        for slot, tile in writes:
            if slot in seen:
                raise ValueError("DUPLICATE_WRITE_SLOT")
            seen.add(slot)
            if not (0 <= slot < TILE_SLOTS) or len(tile) != TILE_BYTES:
                raise ValueError("TILE_WRITE_RANGE")
            start = slot * TILE_BYTES
            if start + TILE_BYTES > MAP_OFFSET:
                raise ValueError("TILE_WRITE_MAP_OVERLAP")
            vram[start:start + TILE_BYTES] = tile

    old_slots = {slot for slot, _ in plan["old"]["resident_tiles"]}
    prestage_slots = set()
    for slot, tile in plan["prestage_writes"]:
        if slot in old_slots:
            raise ValueError("PRESTAGE_OVERWRITES_OLD_RESIDENT")
        if slot in prestage_slots:
            raise ValueError("DUPLICATE_PRESTAGE_SLOT")
        prestage_slots.add(slot)
        apply_tile_writes(((slot, tile),))
        # Each prefix leaves the old map byte-for-byte unchanged and writes only
        # a tile slot unreachable by any old map cell.
        if bytes(vram[MAP_OFFSET:MAP_OFFSET + MAP_BYTES]) != plan["old"]["map_bytes"]:
            raise ValueError("PRESTAGE_CHANGED_OLD_MAP")
    after_prestage = _decode_vram(vram, bytes(vram[MAP_OFFSET:]), plan["palette"])
    if after_prestage != original:
        raise ValueError("PRESTAGE_CHANGED_OLD_PIXELS")

    for slot, tile in plan["atomic_tile_writes"]:
        if slot not in old_slots:
            raise ValueError("ATOMIC_SPILL_NOT_OLD_ONLY")
        apply_tile_writes(((slot, tile),))
    vram[MAP_OFFSET:MAP_OFFSET + MAP_BYTES] = plan["target"]["map_bytes"]
    after_atomic = _decode_vram(vram, bytes(vram[MAP_OFFSET:]), plan["palette"])
    if after_atomic != desired:
        raise ValueError("ATOMIC_RESULT_MISMATCH")
    return dict(old_preserved_after_prestage=True, target_exact_after_atomic=True,
        prestage_writes=len(plan["prestage_writes"]), atomic_tile_writes=len(plan["atomic_tile_writes"]),
        atomic_payload_bytes=plan["atomic_payload_bytes"])
