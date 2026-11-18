"""Build a lossless six-frame mode-3 OBJ packing input for Normal diagnostics.

The input is deliberately limited to the first confirmed six-actor frame set.
It canonicalizes 4bpp indices by exact RGB555 color, splits 16x32 catalog
pieces into 16x16 objects, and merges compatible adjacent quadrants into
32x32 objects to stay inside the OAM entry limit. This is a probe, not a
production asset generator.
"""
from __future__ import annotations

import argparse
import itertools
import json
import random
from pathlib import Path


DEFAULT_ENTRIES = (835, 833, 776, 2155, 495, 2103)


def _palette_slots(entries, seed=221):
    rng = random.Random(seed)
    palette_rows = {}
    for entry in entries:
        for identity, row in entry["palettes"].items():
            palette_rows[identity] = bytes.fromhex(row["data"])
    colors = sorted({data[offset:offset + 2]
                     for data in palette_rows.values()
                     for offset in range(2, 32, 2)})
    adjacency = {color: set() for color in colors}
    for data in palette_rows.values():
        visible = [data[offset:offset + 2]
                   for offset in range(2, 32, 2)]
        for first, second in itertools.combinations(set(visible), 2):
            adjacency[first].add(second)
            adjacency[second].add(first)
    assigned = {}
    while len(assigned) < len(colors):
        remaining = [color for color in colors if color not in assigned]
        scores = {value: (
            len({assigned[n] for n in adjacency[value] if n in assigned}),
            len(adjacency[value])) for value in remaining}
        best_score = max(scores.values())
        tied = [value for value in remaining if scores[value] == best_score]
        color = rng.choice(tied)
        forbidden = {assigned[n] for n in adjacency[color] if n in assigned}
        available = [index for index in range(1, 16) if index not in forbidden]
        if not available:
            raise ValueError("NORMAL_MODE3_PALETTE_GREEDY_COLORING_FAILED")
        slot = rng.choice(available)
        assigned[color] = slot
    if max(assigned.values(), default=0) > 15:
        raise ValueError("NORMAL_MODE3_PALETTE_SLOT_OVERFLOW")
    maps = {}
    cgram = {}
    for identity, data in palette_rows.items():
        slot_map = [0] * 16
        mapped = bytearray(32)
        mapped[0:2] = data[0:2]
        for old_slot in range(1, 16):
            rgb = data[old_slot * 2:old_slot * 2 + 2]
            new_slot = assigned[rgb]
            slot_map[old_slot] = new_slot
            mapped[new_slot * 2:new_slot * 2 + 2] = rgb
        maps[identity] = slot_map
        cgram[identity] = mapped.hex()
    return maps, cgram, len(set(assigned.values()))


def _remap_tile(tile: bytes, slots: list[int]) -> bytes:
    out = bytearray(32)
    for y in range(8):
        for x in range(8):
            bit = 7 - x
            value = sum(((tile[(plane // 2) * 16 + y * 2 + plane % 2]
                          >> bit) & 1) << plane for plane in range(4))
            replacement = slots[value]
            for plane in range(4):
                if replacement & (1 << plane):
                    out[(plane // 2) * 16 + y * 2 + plane % 2] |= 1 << bit
    return bytes(out)


def _palette_conflict_groups(halves):
    by_frame_palette = {}
    for index, half in enumerate(halves):
        key = (half["entry_index"], half["cgram"])
        by_frame_palette.setdefault(key, {}).setdefault(
            (half["x"], half["y"]), []).append(index)
    groups = []
    for positions in by_frame_palette.values():
        for (x, y), tl in positions.items():
            corners = ((x, y), (x + 16, y), (x, y + 16), (x + 16, y + 16))
            if any(corner not in positions for corner in corners[1:]):
                continue
            for choice in itertools.product(*(positions[corner] for corner in corners)):
                if len(set(choice)) == 4:
                    groups.append(tuple(choice))
    return sorted(set(groups))


def _select_groups(groups, count, merge_count=None, seed=221):
    if not groups:
        return []
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import csr_matrix, lil_matrix, vstack

    matrix = lil_matrix((count, len(groups)), dtype=np.float64)
    for column, group in enumerate(groups):
        for row in group:
            matrix[row, column] = 1
    rows = [matrix.tocsc()]
    lower = [np.full(count, -np.inf)]
    upper = [np.ones(count)]
    if merge_count is not None:
        rows.append(csr_matrix(np.ones((1, len(groups)))))
        lower.append(np.asarray([merge_count], dtype=np.float64))
        upper.append(np.asarray([merge_count], dtype=np.float64))
    rng = np.random.default_rng(seed)
    costs = rng.random(len(groups))
    if merge_count is None:
        costs -= 1000.0
    result = milp(costs, integrality=np.ones(len(groups)),
                  bounds=Bounds(0, 1),
                  constraints=LinearConstraint(
                      vstack(rows).tocsc(),
                      np.concatenate(lower), np.concatenate(upper)),
                  options={"time_limit": 30})
    if result.x is None:
        raise ValueError("NORMAL_MODE3_GROUP_SELECTION_TIMEOUT")
    return [groups[index] for index, chosen in enumerate(result.x)
            if chosen > 0.5]


def build(catalog_path: Path, output: Path, indices=DEFAULT_ENTRIES,
          merge_count=None, palette_seed=221, raw_palette_slots=False,
          group_seed=221):
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    entries = catalog["entries"]
    selected = [entries[index] for index in indices]
    palette_ids = sorted({identity for entry in selected
                          for identity in entry["palettes"]})
    palette_index = {identity: index for index, identity in enumerate(palette_ids)}
    if raw_palette_slots:
        slot_maps = {identity: list(range(16)) for identity in palette_ids}
        cgram = {identity: bytes.fromhex(next(
            entry["palettes"][identity]["data"] for entry in selected
            if identity in entry["palettes"])).hex()
                 for identity in palette_ids}
        palette_colors = []
        for identity in palette_ids:
            data = bytes.fromhex(next(entry["palettes"][identity]["data"]
                                      for entry in selected
                                      if identity in entry["palettes"]))
            palette_colors.append([
                int.from_bytes(data[offset:offset + 2], "little")
                for offset in range(2, 32, 2)])
        color_slots = None
    else:
        slot_maps, cgram, color_slots = _palette_slots(selected, palette_seed)
        palette_colors = None
    halves = []
    for entry_index, entry in zip(indices, selected):
        for piece in entry["pieces"]:
            raw = bytes.fromhex(entry["blocks"][piece["resource"]]["data"])
            palette = piece["palette"]
            remapped = b"".join(
                _remap_tile(raw[offset:offset + 32], slot_maps[palette])
                for offset in range(0, len(raw), 32))
            for half_index in range(2):
                data = remapped[half_index * 128:(half_index + 1) * 128]
                halves.append({
                    "entry_index": entry_index,
                    "identity": entry["identity"], "role": entry["role"],
                    "frame": entry["frame"],
                    "palette": palette, "cgram": cgram[palette],
                    "x": int(piece["right_xy"][0]),
                    "y": int(piece["right_xy"][1]) + 16 * half_index,
                    "data": data,
                })
    groups = _palette_conflict_groups(halves)
    chosen = _select_groups(groups, len(halves), merge_count, group_seed)
    consumed = {index for group in chosen for index in group}
    objects = []
    for group in chosen:
        rows = [halves[index] for index in group]
        x0 = min(row["x"] for row in rows)
        y0 = min(row["y"] for row in rows)
        tiles = [None] * 16
        for row in rows:
            qx = (row["x"] - x0) // 16
            qy = (row["y"] - y0) // 16
            for tile_index in range(4):
                ty, tx = divmod(tile_index, 2)
                tiles[(qy * 2 + ty) * 4 + qx * 2 + tx] = (
                    row["data"][tile_index * 32:(tile_index + 1) * 32])
        if any(tile is None for tile in tiles):
            raise AssertionError("NORMAL_MODE3_GROUP_TILE_HOLE")
        objects.append({
            "width": 4, "data": b"".join(tiles),
            "identity": rows[0]["identity"], "role": rows[0]["role"],
            "frame": rows[0]["frame"], "x": x0, "y": y0,
            "coords": [[x0, y0], [x0 + 16, y0],
                       [x0, y0 + 16], [x0 + 16, y0 + 16]],
            "palette": (palette_index[rows[0]["palette"]]
                        if raw_palette_slots else rows[0]["cgram"]),
            "source_halves": list(group),
        })
    for index, row in enumerate(halves):
        if index in consumed:
            continue
        objects.append({
            "width": 2, "data": row["data"],
            "identity": row["identity"], "role": row["role"],
            "frame": row["frame"], "x": row["x"], "y": row["y"],
            "coords": [[row["x"], row["y"]]],
            "palette": (palette_index[row["palette"]]
                        if raw_palette_slots else row["cgram"]),
            "source_halves": [index],
        })
    oam_instances = len(objects)
    result = {
        "format": "S8_NORMAL_LIVE_MODE3_OBJECTS_DIAGNOSTIC_V1",
        "selected_entry_indices": list(indices),
        "palette_seed": palette_seed,
        "group_seed": group_seed,
        "palette_slot_maps": slot_maps,
        "palette_cgram": cgram,
        "palette_colors": palette_colors,
        "global_color_slots": color_slots,
        "half_objects_before_merge": len(halves),
        "compatible_merge_candidates": len(groups),
        "selected_32x32_merges": len(chosen),
        "oam_object_instances": oam_instances,
        "palette_objects": [{
            **{key: value for key, value in row.items()
               if key not in ("data", "source_halves")},
            "data": row["data"].hex(),
            "coords": row["coords"],
        } for row in objects],
        "exact_source_indices_remapped_by_rgb555": True,
    }
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path,
                        default=Path("src/generated/production_source_visual.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--entries", type=int, nargs="*", default=DEFAULT_ENTRIES)
    parser.add_argument("--merge-count", type=int)
    parser.add_argument("--palette-seed", type=int, default=221)
    parser.add_argument("--raw-palette-slots", action="store_true")
    parser.add_argument("--group-seed", type=int, default=221)
    args = parser.parse_args()
    result = build(args.catalog, args.output, args.entries,
                   args.merge_count, args.palette_seed,
                   args.raw_palette_slots, args.group_seed)
    print(json.dumps({key: result[key] for key in (
        "selected_entry_indices", "global_color_slots",
        "half_objects_before_merge", "compatible_merge_candidates",
        "selected_32x32_merges", "oam_object_instances")}, indent=2))


if __name__ == "__main__":
    main()
