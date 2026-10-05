"""Lossless palette-bank clustering for unusually wide source sprites.

The ordinary source publisher splits each 16x32 piece into every global
15-colour bank it intersects.  That is safe but can multiply OAM usage when
palette indices are poorly ordered.  This helper chooses the same bounded
number of 15-colour banks by spatial co-occurrence, then minimizes the exact
number of (piece, bank) records.  Pixel indices and source geometry are never
changed.
"""
from __future__ import annotations

import io
import math
from collections import Counter

import numpy as np
from PIL import Image

from source_compact_packing import pack_compact


def palette_banks_for_frames(source, frames, *, colors_per_bank=15,
                             maximum_banks=8, seed=221,
                             piece_size=(16, 32), anneal_restarts=8,
                             anneal_steps=40_000, slot_iterations=12_000,
                             max_frame_pieces=128,
                             collapse_cgram_aliases=False,
                             palette_per_obj_piece=False,
                             allow_color_set_drift=False):
    """Return a deterministic shared color-index partition for source frames.

    The first frame supplies the optimization objective; all frames are
    validated against the resulting bank capacity before it is returned.  It
    is intended for one authored animation whose GIFs retain one palette.
    """
    if not frames:
        raise ValueError("SOURCE_PALETTE_FRAME_SET_EMPTY")
    images = []
    raw_frames = []
    palette = None
    for frame in frames:
        raw = source.read(frame["source_path"])
        image = Image.open(io.BytesIO(raw))
        image.load()
        if image.mode != "P":
            raise ValueError("SOURCE_PALETTE_INDEXED_FRAME_REQUIRED")
        current_palette = tuple(image.getpalette() or ())
        if palette is None:
            palette = current_palette
        elif current_palette != palette:
            raise ValueError("SOURCE_PALETTE_ANIMATION_PALETTE_DRIFT")
        images.append(image)
        raw_frames.append(raw)

    # Source palette indices are identifiers, not CGRAM colors. Some source
    # assets use many indices that collapse to the same RGB555 value after
    # the runtime palette conversion. Counting those aliases as independent
    # colors creates unnecessary palette-split OBJs. Collapse only when the
    # caller explicitly requests hardware-color equivalence.
    aliases = {}
    if collapse_cgram_aliases:
        source_palette = source.read("data/pal.act")
        cgram_representatives = {}
        source_indices = sorted({pixel for image in images for pixel in image.getdata()
                                 if pixel})
        for pixel in source_indices:
            rgb = source_palette[pixel * 3:pixel * 3 + 3]
            if len(rgb) != 3:
                raise ValueError("SOURCE_PALETTE_CGRAM_ALIAS_INDEX")
            cgram = ((rgb[0] >> 3) | ((rgb[1] >> 3) << 5)
                     | ((rgb[2] >> 3) << 10))
            aliases[pixel] = cgram_representatives.setdefault(cgram, pixel)
        images = [Image.frombytes(
            "P", image.size,
            bytes(aliases.get(pixel, 0) for pixel in image.getdata()))
                  for image in images]

    visible = sorted({pixel for image in (images if allow_color_set_drift else images[:1])
                      for pixel in image.getdata() if pixel})
    banks_required = math.ceil(len(visible) / colors_per_bank)
    if not visible or banks_required > maximum_banks:
        raise ValueError(
            f"SOURCE_PALETTE_BANK_CAPACITY: required={banks_required}, "
            f"available={maximum_banks}"
        )
    if not allow_color_set_drift and any({pixel for pixel in image.getdata() if pixel} != set(visible)
           for image in images[1:]):
        raise ValueError("SOURCE_PALETTE_ANIMATION_COLOR_SET_DRIFT")

    # Use one compact cover for the animation when dimensions/offsets are
    # stable. This avoids eight independent MILP solves and guarantees a
    # stable OAM-piece layout across sampled animation frames.
    offsets = [tuple(frame.get("offset", (0, 0))) for frame in frames]
    if len(set(offsets)) == 1 and len({image.size for image in images}) == 1:
        union = np.zeros((images[0].height, images[0].width), dtype=bool)
        for image in images:
            union |= np.asarray(image) != 0
        union_image = Image.new("P", images[0].size, 0)
        union_image.putdata(union.astype(np.uint8).ravel().tolist())
        encoded_union = io.BytesIO()
        union_image.save(encoded_union, format="PNG")
        shared_packed = (pack_compact(encoded_union.getvalue(), offsets[0])
                         if piece_size == (16, 32) else
                         _pack_fixed_obj_grid(union_image, offsets[0], piece_size))
        packed_frames = [shared_packed] * len(images)
    elif piece_size == (16, 32):
        packed_frames = [pack_compact(raw, offset)
                         for raw, offset in zip(raw_frames, offsets)]
    else:
        packed_frames = [_pack_fixed_obj_grid(image, offset, piece_size)
                         for image, offset in zip(images, offsets)]
    if aliases:
        for packed in packed_frames:
            packed["cgram_aliases"] = aliases

    if palette_per_obj_piece:
        if piece_size not in ((16, 32), (32, 64)):
            raise ValueError("SOURCE_OBJ_PIECE_PALETTE_GEOMETRY")
        piece_sets = []
        for image, packed in zip(images, packed_frames):
            frame_sets = []
            for piece in packed["pieces"]:
                x, y = piece["source_xy"]
                width, height = piece["size"]
                colors = frozenset(
                    image.getpixel((px, py))
                    for py in range(y, min(y + height, image.height))
                    for px in range(x, min(x + width, image.width))
                    if image.getpixel((px, py)))
                if len(colors) > colors_per_bank:
                    raise ValueError(
                        "SOURCE_OBJ_PIECE_PALETTE_CAPACITY: required="
                        f"{len(colors)}, available={colors_per_bank}")
                frame_sets.append(colors)
            piece_sets.append(frame_sets)
        if any(len(row) != len(packed_frames[0]["pieces"])
               for row in piece_sets):
            raise ValueError("SOURCE_OBJ_PIECE_LAYOUT_DRIFT")
        color_sets = sorted({colors for row in piece_sets for colors in row
                             if colors},
                            key=lambda colors: (-len(colors), tuple(sorted(colors))))
        palette_sets = []
        piece_palette_ids = {}
        for colors in color_sets:
            candidates = [(len(palette | colors) - len(palette), len(palette), index)
                          for index, palette in enumerate(palette_sets)
                          if len(palette | colors) <= colors_per_bank]
            if candidates:
                index = min(candidates)[2]
                palette_sets[index] = palette_sets[index] | colors
            else:
                index = len(palette_sets)
                palette_sets.append(colors)
            piece_palette_ids[colors] = index
        if len(palette_sets) > maximum_banks:
            raise ValueError(
                "SOURCE_OBJ_PIECE_PALETTE_BANK_CAPACITY: required="
                f"{len(palette_sets)}, available={maximum_banks}")
        for packed, frame_sets in zip(packed_frames, piece_sets):
            packed["piece_palette_banks"] = [
                piece_palette_ids[colors] if colors else 255 for colors in frame_sets]
        counts = [sum(1 for bank in packed["piece_palette_banks"] if bank != 255)
                  for packed in packed_frames]
        frame_palette_counts = [len({bank for bank in packed["piece_palette_banks"]
                                     if bank != 255}) for packed in packed_frames]
        if max(counts) > max_frame_pieces:
            raise ValueError(
                "SOURCE_VISUAL_OAM_CAPACITY: required="
                f"{max(counts)}, available={max_frame_pieces}")
        return [sorted(colors) for colors in palette_sets], packed_frames, dict(
            solver="exact_piece_palette_assignment_v1",
            source_colors=len(visible), palette_count=max(frame_palette_counts),
            palette_identity_count=len(palette_sets),
            cgram_aliases=len(aliases) - len(visible),
            palette_piece_cost=max(counts), frame_piece_counts=counts,
            piece_palette_assignments=[list(packed["piece_palette_banks"])
                                      for packed in packed_frames],
        )

    # Palette order is stable across these frames. Build a compact binary
    # matrix from source pixels covered by the shared authored OBJ pieces.
    # One matrix row is one piece and one column is one source color.
    pieces = packed_frames[0]["pieces"]
    membership = np.zeros((len(pieces), len(visible)), dtype=np.int8)
    color_columns = {color: column for column, color in enumerate(visible)}
    image = images[0]
    for row, piece in enumerate(pieces):
        x, y = piece["source_xy"]
        width, height = piece["size"]
        colors = {
            image.getpixel((px, py))
            for py in range(y, min(y + height, image.height))
            for px in range(x, min(x + width, image.width))
            if image.getpixel((px, py))
        }
        for color in colors:
            membership[row, color_columns[color]] = 1

    bank_count = banks_required
    color_count = len(visible)
    frequency = membership.sum(axis=0)
    cooccurrence = membership.T @ membership
    rng = np.random.default_rng(seed)
    # Represent each color's piece incidence as a Python integer bitset. A
    # palette bank's OAM cost is the sum of popcounts of its color union.
    # This makes swap scoring tiny and deterministic instead of allocating
    # several NumPy arrays on every annealing step.
    color_piece_masks = [
        sum(1 << row for row in range(len(pieces)) if membership[row, column])
        for column in range(color_count)
    ]

    def bank_piece_mask(columns):
        value = 0
        for column in columns:
            value |= color_piece_masks[column]
        return value

    if bank_count == 1:
        result = [visible]
        bank_tables, tile_stats = _optimize_palette_slots(
            images, packed_frames, result, seed=seed, iterations=slot_iterations,
            max_frame_pieces=max_frame_pieces)
        if max(tile_stats["frame_piece_counts"]) > max_frame_pieces:
            raise ValueError(
                "SOURCE_VISUAL_OAM_CAPACITY: required="
                f"{max(tile_stats['frame_piece_counts'])}, available={max_frame_pieces}"
            )
        return bank_tables, packed_frames, dict(
            solver="single_palette_cgram_alias_collapse_v1",
            source_colors=len(visible), palette_count=1,
            cgram_aliases=len(aliases) - len(visible),
            palette_piece_cost=max(tile_stats["frame_piece_counts"]),
            **tile_stats,
        )

    best_cost = math.inf
    best_assignment = None

    # Greedy co-occurrence packing gives useful starts; deterministic
    # annealing swaps colors between full banks without ever exceeding 15.
    if anneal_restarts < 1 or anneal_steps < 1 or slot_iterations < 1:
        raise ValueError("SOURCE_PALETTE_SEARCH_BOUNDS")
    for restart in range(anneal_restarts):
        remaining = list(np.argsort(-frequency))
        remaining = remaining[restart:] + remaining[:restart]
        bins = [[] for _ in range(bank_count)]
        for bank in range(bank_count):
            seed_color = remaining.pop(0)
            bins[bank].append(seed_color)
            while len(bins[bank]) < colors_per_bank and remaining:
                chosen = max(
                    remaining,
                    key=lambda color: (
                        sum(int(cooccurrence[color, other])
                            for other in bins[bank]),
                        int(frequency[color]), -color,
                    ),
                )
                bins[bank].append(chosen)
                remaining.remove(chosen)
        bank_masks = [bank_piece_mask(columns) for columns in bins]
        cost = sum(mask.bit_count() for mask in bank_masks)
        assignment = [-1] * color_count
        for bank, columns in enumerate(bins):
            for column in columns:
                assignment[column] = bank
        for iteration in range(anneal_steps):
            first, second = rng.choice(bank_count, 2, replace=False)
            first = int(first)
            second = int(second)
            first_position = int(rng.integers(len(bins[first])))
            second_position = int(rng.integers(len(bins[second])))
            first_color = bins[first][first_position]
            second_color = bins[second][second_position]
            bins[first][first_position], bins[second][second_position] = (
                bins[second][second_position], bins[first][first_position])
            new_first = bank_piece_mask(bins[first])
            new_second = bank_piece_mask(bins[second])
            delta = (new_first.bit_count() + new_second.bit_count()
                     - bank_masks[first].bit_count() - bank_masks[second].bit_count())
            temperature = 2.5 * (1 - iteration / anneal_steps) + 0.03
            accepted = delta <= 0 or rng.random() < math.exp(-delta / temperature)
            if accepted:
                bank_masks[first] = new_first
                bank_masks[second] = new_second
                cost += delta
                assignment[first_color] = second
                assignment[second_color] = first
            else:
                bins[first][first_position], bins[second][second_position] = (
                    bins[second][second_position], bins[first][first_position])
            if cost < best_cost:
                best_cost = cost
                best_assignment = assignment.copy()

    result = [
        [color for column, color in enumerate(visible)
         if best_assignment[column] == bank]
        for bank in range(bank_count)
    ]
    if any(not bank or len(bank) > colors_per_bank for bank in result):
        raise AssertionError("SOURCE_PALETTE_BANK_PARTITION")

    bank_tables, tile_stats = _optimize_palette_slots(
        images, packed_frames, result, seed=seed, iterations=slot_iterations,
        max_frame_pieces=max_frame_pieces)
    if max(tile_stats["frame_piece_counts"]) > max_frame_pieces:
        raise ValueError(
            "SOURCE_VISUAL_OAM_CAPACITY: required="
            f"{max(tile_stats['frame_piece_counts'])}, available={max_frame_pieces}"
        )
    return bank_tables, packed_frames, dict(
        solver="deterministic_cooccurrence_swap_v1",
        source_colors=len(visible), palette_count=bank_count,
        cgram_aliases=max(0,len(aliases) - len(visible)),
        palette_piece_cost=max(tile_stats["frame_piece_counts"]),
        **tile_stats,
    )


def _pack_fixed_obj_grid(image, offset, piece_size):
    """Cover an exact source raster with native-size OBJ rectangles."""
    width, height = piece_size
    if piece_size not in ((16, 32), (32, 64)):
        raise ValueError("SOURCE_OBJ_GRID_SIZE")
    ox, oy = offset
    pieces = []
    for y in range(0, image.height, height):
        for x in range(0, image.width, width):
            if not image.crop((x, y, min(x + width, image.width),
                               min(y + height, image.height))).getbbox():
                continue
            pieces.append(dict(
                source_xy=[x, y], size=[width, height],
                right_xy=[x - ox, y - oy],
                left_xy=[ox - x - width + 1, y - oy],
            ))
    return dict(pieces=pieces, overlap_is_identical_source_pixels=True,
                solver_status="exact_source_obj_grid")


def _optimize_palette_slots(images, packed_frames, initial_banks, *, seed,
                            iterations, max_frame_pieces):
    """Choose lossless palette-bank/local-index assignments for tile sharing."""
    bank_count = len(initial_banks)
    visible = sorted({color for image in images for color in image.getdata() if color})
    occupants = [list(bank) + [0] * (15 - len(bank)) for bank in initial_banks]
    locations = {}
    for bank, colors in enumerate(occupants):
        for slot, color in enumerate(colors):
            if color:
                locations[color] = (bank, slot)

    tile_pixels = []
    color_tiles = {color: set() for color in visible}
    for image in images:
        for tile_y in range(0, image.height, 8):
            for tile_x in range(0, image.width, 8):
                masks = {}
                for y in range(8):
                    for x in range(8):
                        px, py = tile_x + x, tile_y + y
                        color = (image.getpixel((px, py))
                                 if px < image.width and py < image.height else 0)
                        if color:
                            masks[color] = masks.get(color, 0) | (1 << (y * 8 + x))
                tile_index = len(tile_pixels)
                tile_pixels.append(masks)
                for color in masks:
                    color_tiles[color].add(tile_index)

    def signature(tile, bank):
        planes = [0, 0, 0, 0]
        for color, mask in tile_pixels[tile].items():
            place = locations.get(color)
            if place is None or place[0] != bank:
                continue
            local = place[1] + 1
            for plane in range(4):
                if local & (1 << plane):
                    planes[plane] |= mask
        return tuple(planes)

    piece_colors = []
    for image, packed in zip(images, packed_frames):
        rows = []
        for piece in packed["pieces"]:
            x, y = piece["source_xy"]
            width, height = piece["size"]
            rows.append({
                image.getpixel((px, py))
                for py in range(y, min(y + height, image.height))
                for px in range(x, min(x + width, image.width))
                if image.getpixel((px, py))
            })
        piece_colors.append(rows)

    def frame_piece_counts():
        bank_colors = [
            {color for color, (assigned_bank, _) in locations.items()
             if assigned_bank == bank}
            for bank in range(bank_count)
        ]
        return [sum(sum(bool(colors.intersection(bank)) for bank in bank_colors)
                     for colors in frame)
                for frame in piece_colors]

    signatures = [[signature(tile, bank) for bank in range(bank_count)]
                  for tile in range(len(tile_pixels))]
    counts = Counter(value for row in signatures for value in row)
    rng = np.random.default_rng(seed + 1)
    current_unique = len(counts)
    current_piece_counts = frame_piece_counts()
    current_cost = max(current_piece_counts)

    def score(unique, pieces):
        return (unique + max(0, pieces - max_frame_pieces) * 1000 +
                pieces * 0.02)

    current_score = score(current_unique, current_cost)
    best_unique, best_piece_cost = current_unique, current_cost
    best_occupants = [row.copy() for row in occupants]
    for iteration in range(iterations):
        first = int(rng.integers(bank_count * 15))
        second = int(rng.integers(bank_count * 15))
        if first == second:
            continue
        first_bank, first_slot = divmod(first, 15)
        second_bank, second_slot = divmod(second, 15)
        first_color = occupants[first_bank][first_slot]
        second_color = occupants[second_bank][second_slot]
        if not first_color and not second_color:
            continue
        affected_colors = {color for color in (first_color, second_color) if color}
        affected_tiles = set().union(*(color_tiles[color] for color in affected_colors))
        affected_banks = {first_bank, second_bank}
        old_values = {}
        for tile in affected_tiles:
            for bank in affected_banks:
                old = signatures[tile][bank]
                old_values[tile, bank] = old
                counts[old] -= 1
                if not counts[old]:
                    del counts[old]

        occupants[first_bank][first_slot], occupants[second_bank][second_slot] = (
            second_color, first_color)
        if first_color:
            locations[first_color] = (second_bank, second_slot)
        if second_color:
            locations[second_color] = (first_bank, first_slot)

        for tile in affected_tiles:
            for bank in affected_banks:
                new = signature(tile, bank)
                signatures[tile][bank] = new
                counts[new] += 1

        new_unique = len(counts)
        new_piece_counts = frame_piece_counts()
        new_piece_cost = max(new_piece_counts)
        new_score = score(new_unique, new_piece_cost)
        temperature = 2.0 * (1 - iteration / iterations) + 0.02
        accept = (new_score <= current_score or
                  rng.random() < math.exp((current_score - new_score) / temperature))
        if accept:
            current_unique = new_unique
            current_piece_counts = new_piece_counts
            current_piece_cost = new_piece_cost
            current_score = new_score
            if (new_piece_cost <= max_frame_pieces and
                    (new_unique < best_unique or
                     (new_unique == best_unique and new_piece_cost < best_piece_cost))):
                best_unique = new_unique
                best_piece_cost = new_piece_cost
                best_occupants = [row.copy() for row in occupants]
        else:
            occupants[first_bank][first_slot], occupants[second_bank][second_slot] = (
                first_color, second_color)
            if first_color:
                locations[first_color] = (first_bank, first_slot)
            if second_color:
                locations[second_color] = (second_bank, second_slot)
            for (tile, bank), old in old_values.items():
                new = signatures[tile][bank]
                counts[new] -= 1
                if not counts[new]:
                    del counts[new]
                signatures[tile][bank] = old
                counts[old] += 1

    bank_tables = best_occupants
    best_locations = {
        color: (bank, slot)
        for bank, colors in enumerate(bank_tables)
        for slot, color in enumerate(colors) if color
    }
    locations.clear()
    locations.update(best_locations)
    # Re-evaluate a stable counter from the selected mapping for diagnostics.
    final_counts = [sum(sum(bool(colors.intersection(
        {color for color, (assigned_bank, _) in locations.items()
         if assigned_bank == bank})) for bank in range(bank_count))
                        for colors in frame)
                    for frame in piece_colors]
    return bank_tables, dict(
        frame_piece_counts=final_counts,
        unique_tile_patterns=best_unique,
        slot_search_iterations=iterations,
    )
