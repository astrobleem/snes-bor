"""Compiler-owned source-sized visual catalog for the production roster.

This module deliberately does not alter gameplay lowering.  It turns the
already parsed BOR ModelIR into a runtime lookup catalog whose keys are
roster/role/frame/map.  The native S7 consumer owns publication and fences;
this catalog owns source geometry and immutable resource identity.
"""
from __future__ import annotations

import hashlib
import io
import json
import struct
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "bor_compile"))

from compiler import Source  # noqa: E402
from model_ir import parse_model  # noqa: E402
from source_actor_raster import compile_animation, encode_tile  # noqa: E402
from source_compact_packing import pack_compact  # noqa: E402
from source_obj_atlas import place_full_obj  # noqa: E402

VISUAL_POLICY_LEGACY_FIXED = 0
VISUAL_POLICY_SOURCE_SIZED = 1

RUNTIME_CATALOG_MAGIC = b"SVIS1\0"

# Presentation keys mirror the accepted actor's selected animation family;
# they do not select or advance gameplay state.
RUNTIME_ROLE_IDLE = 0
RUNTIME_ROLE_WALK = 1
RUNTIME_ROLE_ATTACK1 = 2
RUNTIME_ROLE_ATTACK2 = 3
RUNTIME_ROLE_FALL = 4
RUNTIME_ROLE_RISE = 5
RUNTIME_ROLE_SPECIAL = 6
RUNTIME_ROLE_UNSUPPORTED = 255


def runtime_role_key(role):
    name = str(role).lower()
    if name in ("idle", "waiting"):
        return RUNTIME_ROLE_IDLE
    if name in ("walk", "walking"):
        return RUNTIME_ROLE_WALK
    if name in ("attack", "attack1"):
        return RUNTIME_ROLE_ATTACK1
    if name in ("attack2", "attacktwo"):
        return RUNTIME_ROLE_ATTACK2
    if name in ("fall", "knockdown", "lie"):
        return RUNTIME_ROLE_FALL
    if name in ("rise", "getup", "get"):
        return RUNTIME_ROLE_RISE
    if name in ("special", "freespecial"):
        return RUNTIME_ROLE_SPECIAL
    return RUNTIME_ROLE_UNSUPPORTED


def _remap_palette_overrides(source, model):
    """Derive indexed palette substitutions from authored remap images."""
    overrides = []
    for remap in model.remaps:
        base_raw = source.read(remap["assets"][0]["source_path"])
        alt_raw = source.read(remap["assets"][1]["source_path"])
        base = Image.open(io.BytesIO(base_raw)).convert("P")
        alt = Image.open(io.BytesIO(alt_raw)).convert("P")
        alt_rgb = alt.getpalette() or []
        candidates = {}
        for y in range(min(base.height, alt.height)):
            for x in range(min(base.width, alt.width)):
                index = int(base.getpixel((x, y)))
                if not index:
                    continue
                remapped = int(alt.getpixel((x, y)))
                rgb = alt_rgb[remapped * 3:remapped * 3 + 3]
                if len(rgb) != 3:
                    continue
                value = (rgb[0] >> 3) | ((rgb[1] >> 3) << 5) | ((rgb[2] >> 3) << 10)
                candidates.setdefault(index, []).append(value)
        # BOR's converter uses the most common replacement when a shared
        # indexed source color is rendered with small anti-aliased variants.
        # Keep the choice deterministic and retain the source map as the
        # authoritative visual policy rather than rejecting the whole model.
        overrides.append({index: Counter(values).most_common(1)[0][0]
                          for index, values in candidates.items()})
    return overrides


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _model_path(identity: str) -> str:
    normalized = identity.replace("\\", "/").strip("/").lower()
    # BOR's MISC objects keep their definition beside the image; regular
    # actors use the conventional DATA/CHARS/<name>/<name>.TXT layout.
    if normalized.startswith("misc/"):
        return f"data/chars/{normalized}.txt"
    leaf = normalized.split("/")[-1]
    return f"data/chars/{normalized}/{leaf}.txt"


def _palette_bytes(source, colors, palette_override=None):
    palette = source.read("data/pal.act")
    out = bytearray()
    for index in colors:
        if palette_override and index in palette_override:
            out += struct.pack("<H", palette_override[index])
        else:
            rgb = palette[index * 3:index * 3 + 3]
            if len(rgb) != 3:
                raise ValueError(f"PALETTE_INDEX_EXTENT: {index}")
            r, g, b = rgb
            out += struct.pack("<H", (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10))
    return bytes(out).ljust(32, b"\0")


def _partition_frame(source, frame, palette_override=None, *, allow_full_obj_pack=False):
    """Return lossless masked OBJ pieces and content-addressed resources.

    Each emitted piece contains only pixels belonging to its palette bank;
    the other pixels are transparent.  Overlapping pieces therefore preserve
    the complete source image while every individual OBJ uses <=15 colors.
    """
    raw = source.read(frame["source_path"])
    image = Image.open(io.BytesIO(raw))
    image.load()
    packed = pack_compact(raw, frame["offset"])
    visible = sorted({p for p in image.getdata() if p})
    if not visible:
        return packed, [], {}, {}, ("0" * 64, b"")
    banks = [visible[i:i + 15] for i in range(0, len(visible), 15)]
    if len(banks) > 8:
        raise ValueError(f"OBJ_PALETTE_SLOT_CAPACITY: required={len(banks)}, available=8")
    palettes = {}
    blocks = {}
    rows = []
    for piece in packed["pieces"]:
        px, py = piece["source_xy"]
        w, h = piece["size"]
        colors = {image.getpixel((x, y)) for y in range(py, min(py + h, image.height))
                  for x in range(px, min(px + w, image.width)) if image.getpixel((x, y))}
        for bank_id, bank in enumerate(banks):
            local_colors = colors.intersection(bank)
            if not local_colors:
                continue
            palette = [0, *bank]
            mapping = {value: i for i, value in enumerate(palette)}
            palette_data = _palette_bytes(source, palette, palette_override)
            palette_id = _sha(palette_data)
            palettes[palette_id] = dict(bank=bank_id, colors=palette,
                                        data=palette_data.hex())
            pixels = []
            for y in range(py, py + h):
                for x in range(px, px + w):
                    value = image.getpixel((x, y)) if x < image.width and y < image.height else 0
                    pixels.append(mapping.get(value, 0))
            encoded = bytearray()
            for ty in range(0, h, 8):
                for tx in (0, 8):
                    tile = bytes(pixels[(ty + yy) * w + tx + xx]
                                 for yy in range(8) for xx in range(8))
                    encoded += encode_tile(tile)
            block_id = _sha(bytes(encoded))
            blocks[block_id] = dict(size=len(encoded), data=bytes(encoded).hex())
            rows.append({
                "source_xy": piece["source_xy"],
                "size": piece["size"],
                "right_xy": piece["right_xy"],
                "left_xy": piece["left_xy"],
                "palette": palette_id,
                "palette_bank": bank_id,
                "resource": block_id,
                "source_colors": sorted(local_colors),
            })
    # Give every emitted (possibly palette-masked) piece a deterministic
    # location in a 16-tile-wide OBJ sheet.  The sheet layout matches the
    # SNES sprite row stride; the native publisher can therefore transfer one
    # contiguous frame sheet instead of issuing four DMA requests per piece.
    for index, row in enumerate(rows):
        sheet_col = (index % 8) * 2
        sheet_row = (index // 8) * 4
        row["sheet_tile"] = sheet_row * 16 + sheet_col
    sheet_rows = ((len(rows) + 7) // 8) * 4
    sheet_data = bytearray(sheet_rows * 16 * 32)
    for index, row in enumerate(rows):
        encoded = bytes.fromhex(blocks[row["resource"]]["data"])
        col = (row["sheet_tile"] % 16) * 32
        row_base = (row["sheet_tile"] // 16) * 32 * 16
        for tile_row in range(4):
            src = tile_row * 64
            dst = row_base + tile_row * 16 * 32 + col
            sheet_data[dst:dst + 64] = encoded[src:src + 64]
    if len(sheet_data) > 16384 and allow_full_obj_pack:
        origins, tile_grid = place_full_obj(
            bytes.fromhex(value["data"]) for value in blocks.values())
        last_cell = max(tile_grid)
        sheet_data = bytearray((last_cell // 16 + 1) * 16 * 32)
        for cell, tile in tile_grid.items():
            sheet_data[cell * 32:cell * 32 + 32] = tile
        for row in rows:
            block = bytes.fromhex(blocks[row["resource"]]["data"])
            row["sheet_tile"] = origins[block]
        packed["solver_status"] = "lossless_full_obj_overlap_16k"
    sheet_id = _sha(bytes(sheet_data))
    return packed, rows, palettes, blocks, (sheet_id, bytes(sheet_data))


def build_catalog(roster_configs, *, pak_root=None, include_non_bor=False):
    """Build a source-sized catalog and explicit blockers.

    The function returns data only; it does not write build outputs.  A model
    with an unsupported role/resource is retained as a diagnostic record so
    a production build cannot silently fall back to 32x48 art.
    """
    result = {
        "format": "BOR_SOURCE_VISUAL_CATALOG_V1",
        "visual_policies": {
            "LEGACY_FIXED": VISUAL_POLICY_LEGACY_FIXED,
            "SOURCE_SIZED": VISUAL_POLICY_SOURCE_SIZED,
        },
        "source_pipeline": "ModelIR -> source_actor_raster -> source_compact_packing",
        "entries": [],
        "blockers": [],
    }
    sources = {}
    for roster_id, cfg in enumerate(roster_configs):
        if cfg.get("family") != "bor-original" and not include_non_bor:
            continue
        pak = Path(pak_root or cfg.get("pak") or "Beats of Rage Original [v.3.0 Build 4086].pak")
        if not pak.is_absolute():
            pak = ROOT / pak
        if not pak.exists():
            result["blockers"].append({"roster": roster_id, "identity": cfg["source_character"],
                                       "capability": "SOURCE_MEDIA", "reason": "PAK_MISSING",
                                       "path": str(pak)})
            continue
        source = sources.setdefault(str(pak), Source(pak))
        identity = cfg["source_character"].split("\\CHARS\\", 1)[-1].replace("\\", "/")
        model_path = cfg.get("source_definition") or _model_path(identity)
        try:
            model = parse_model(source, model_path, identity.split("/")[-1],
                                "production-source-visual", "historical-bor")
        except Exception as exc:  # preserve the exact blocker, fail closed
            result["blockers"].append({"roster": roster_id, "identity": identity,
                                       "capability": "MODEL_PARSE", "reason": str(exc)})
            continue
        for animation in model.animations:
            try:
                raster = compile_animation(source, model, animation.role,
                                           color_adapter="SNES_RGB555_TRUNCATE")
            except ValueError as error:
                # The one-palette raster compiler is intentionally strict, but
                # source-sized production publication may use multiple OBJ
                # palettes. Re-enter only for the specific color-capacity
                # failure; all other source errors remain blockers.
                if not (str(error).startswith("OBJ_PALETTE_CAPACITY:") or
                        str(error).startswith("GLOBAL_PALETTE_SCOPE:")):
                    raise
                raster = {"manifest": {"frames": [
                    {"source_path": f.source_path, "asset_sha256": f.asset_sha256,
                     "dimensions": f.dimensions, "offset": f.state["offset"],
                     "source_delay": f.state["delay"]}
                    for f in animation.frames]}}
            except Exception as exc:
                result["blockers"].append({"roster": roster_id, "identity": identity,
                                           "role": animation.role,
                                           "capability": "SOURCE_FRAME", "reason": str(exc)})
                continue
            try:
                remap_overrides = [{}] + _remap_palette_overrides(source, model)
            except Exception as exc:
                result["blockers"].append({"roster": roster_id, "identity": identity,
                                           "role": animation.role,
                                           "capability": "SOURCE_REMAP", "reason": str(exc)})
                remap_overrides = [{}]
            for frame_index, frame in enumerate(raster["manifest"]["frames"]):
                for map_index, palette_override in enumerate(remap_overrides):
                    try:
                        normal_required_large_pose = (
                            identity.split("/")[-1].upper() == "K9999"
                            and animation.role in ("special", "upper"))
                        packed, pieces, palettes, blocks, sheet = _partition_frame(
                            source, frame, palette_override,
                            allow_full_obj_pack=normal_required_large_pose)
                    except Exception as exc:
                        result["blockers"].append({"roster": roster_id, "identity": identity,
                                                   "role": animation.role, "frame": frame_index,
                                                   "map": map_index, "capability": "SOURCE_PACKING",
                                                   "reason": str(exc)})
                        continue
                    if len(palettes) > 8:
                        result["blockers"].append({
                            "roster": roster_id, "identity": identity,
                            "role": animation.role, "frame": frame_index,
                            "map": map_index,
                            "capability": "VISUAL_PALETTE_RESOURCE",
                            "reason": "frame requires more than eight SNES OBJ palettes",
                            "required_obj_palettes": len(palettes),
                            "available_obj_palettes": 8,
                        })
                        continue
                    palette_slots = {key: slot for slot, key in enumerate(sorted(palettes))}
                    for piece in pieces:
                        piece["palette_slot"] = palette_slots[piece["palette"]]
                    result["entries"].append({
                    "roster": roster_id,
                    "identity": identity,
                    "role": animation.role,
                    "frame": frame_index,
                    "map": map_index,
                    "visual_policy": "SOURCE_SIZED",
                    "source_path": frame["source_path"],
                    "asset_sha256": frame["asset_sha256"],
                    "dimensions": frame["dimensions"],
                    "offset": frame["offset"],
                    "pieces": pieces,
                    "piece_count": len(pieces),
                    "tile_bytes": len(sheet[1]),
                    "palette_count": len(palettes),
                    "palette_identities": sorted(palettes),
                    "palettes": palettes,
                    "blocks": blocks,
                    "sheet": sheet[0],
                    "sheet_data": sheet[1].hex(),
                    "sheet_bytes": len(sheet[1]),
                    "source_palette_indices": sorted({c for p in pieces for c in p["source_colors"]}),
                    "source_delay": frame["source_delay"],
                    "packed_solver_status": packed.get("solver_status", "source_compact_packing"),
                    })
    result["entries"].sort(key=lambda e: (e["roster"], e["role"], e["frame"], e["map"]))
    role_ids = {}
    for entry in result["entries"]:
        key = (entry["identity"], entry["role"])
        role_ids.setdefault(key, len([k for k in role_ids if k[0] == entry["identity"]]))
        entry["role_id"] = role_ids[key]
    result["summary"] = {
        "roster_count": sum(1 for c in roster_configs
                             if c.get("family") == "bor-original" or include_non_bor),
        "entry_count": len(result["entries"]),
        "blocker_count": len(result["blockers"]),
        "source_sized_entries": len(result["entries"]),
        "legacy_fixed_entries": 0,
    }
    for entry in result["entries"]:
        entry["runtime_role"] = runtime_role_key(entry["role"])
    return result


def pack_runtime_catalog(catalog):
    """Pack a deduplicated native lookup/resource catalog.

    Header: magic, entry count, piece count, block count, palette count;
    followed by fixed-size entry/piece/block/palette tables and immutable
    256-byte tile blocks / 32-byte OBJ palettes.  Offsets are relative to the
    beginning of the blob so the MSU loader does not depend on Python object
    layout or JSON.
    """
    entries = catalog["entries"]
    blocks = {}
    palettes = {}
    sheets = {}
    pieces = []
    entry_rows = []
    for entry in entries:
        first_piece = len(pieces)
        for piece in entry["pieces"]:
            blocks.setdefault(piece["resource"], entry["blocks"][piece["resource"]])
            palettes.setdefault(piece["palette"], entry["palettes"][piece["palette"]])
            pieces.append((piece, entry))
        sheets.setdefault(entry["sheet"], bytes.fromhex(entry["sheet_data"]))
        entry_rows.append((entry, first_piece, len(entry["pieces"])))
    block_ids = sorted(blocks)
    palette_ids = sorted(palettes)
    block_index = {key: i for i, key in enumerate(block_ids)}
    palette_index = {key: i for i, key in enumerate(palette_ids)}
    header_bytes = struct.calcsize("<6sHHHHHH")
    entry_bytes = 24
    piece_bytes = 16
    block_row_bytes = 42
    palette_row_bytes = 42
    entry_offset = header_bytes
    piece_offset = entry_offset + len(entry_rows) * entry_bytes
    block_offset = piece_offset + len(pieces) * piece_bytes
    palette_offset = block_offset + len(block_ids) * block_row_bytes
    sheet_ids = sorted(sheets)
    sheet_index = {key: i for i, key in enumerate(sheet_ids)}
    sheet_offset = palette_offset + len(palette_ids) * palette_row_bytes
    data_offset = sheet_offset + len(sheet_ids) * 42
    out = bytearray(struct.pack("<6sHHHHHH", RUNTIME_CATALOG_MAGIC, len(entries),
                                len(pieces), len(block_ids), len(palette_ids),
                                len(sheet_ids), entry_bytes))
    for entry, first, count in entry_rows:
        out += struct.pack("<BBBBHHhhHHII", entry["roster"], entry["runtime_role"],
                           entry["frame"], entry["map"], entry["dimensions"][0],
                           entry["dimensions"][1], entry["offset"][0], entry["offset"][1],
                           count, entry["palette_count"], first,
                           sheet_index[entry["sheet"]])
    for piece, entry in pieces:
        out += struct.pack("<hhhhBBHHH", piece["right_xy"][0], piece["right_xy"][1],
                           piece["left_xy"][0], piece["left_xy"][1],
                           piece["palette_slot"], entry["map"],
                           palette_index[piece["palette"]], block_index[piece["resource"]],
                           piece["sheet_tile"])
    block_payload = bytearray()
    for key in block_ids:
        payload = bytes.fromhex(blocks[key]["data"])
        if len(payload) != 256:
            raise ValueError("SOURCE_VISUAL_BLOCK_SIZE")
        row = data_offset + len(block_payload)
        out += struct.pack("<32sHII", bytes.fromhex(key), 256, row, len(payload))
        block_payload += payload
    palette_payload = bytearray()
    for key in palette_ids:
        payload = bytes.fromhex(palettes[key]["data"])
        if len(payload) != 32:
            raise ValueError("SOURCE_VISUAL_PALETTE_SIZE")
        row = data_offset + len(block_ids) * 256 + len(palette_payload)
        out += struct.pack("<32sHII", bytes.fromhex(key), 32, row, len(payload))
        palette_payload += payload
    for key in sheet_ids:
        payload = sheets[key]
        row = data_offset + len(block_payload) + len(palette_payload)
        out += struct.pack("<32sHII", bytes.fromhex(key), len(payload), row, len(payload))
        palette_payload += payload
    # The table offsets above intentionally point into the final immutable
    # payload area.  Keep the payload order deterministic and assert offsets.
    out += block_payload + palette_payload
    if len(out) != data_offset + len(block_ids) * 256 + len(palette_ids) * 32 + sum(len(sheets[k]) for k in sheet_ids):
        raise ValueError("SOURCE_VISUAL_CATALOG_SIZE")
    return bytes(out)


def emit_policy_include(catalog, path, *, enabled=False, msu_offset=None,
                        msu_size=None, key_path=None):
    """Emit policy metadata and, optionally, the large native key table.

    The policy/constants are small and may live with the bank-0 include.  A
    complete production catalog has thousands of keys, so callers can place
    that table in a dedicated ROM bank without perturbing the reset/runtime
    bank layout.
    """
    entries = catalog["entries"]
    max_roster = max((e["roster"] for e in entries), default=-1)
    unique_blocks = {p["resource"] for e in entries for p in e["pieces"]}
    unique_palettes = {p["palette"] for e in entries for p in e["pieces"]}
    unique_sheets = {e["sheet"] for e in entries}
    piece_count = sum(len(e["pieces"]) for e in entries)
    piece_offset = 18 + len(entries) * 24
    block_offset = piece_offset + piece_count * 16
    palette_offset = block_offset + len(unique_blocks) * 42
    sheet_offset = palette_offset + len(unique_palettes) * 42
    rows = [
        "; Generated from production_source_publication.py; do not edit.",
        "VISUAL_POLICY_LEGACY_FIXED = 0",
        "VISUAL_POLICY_SOURCE_SIZED = 1",
        f"SOURCE_VISUAL_BUILD_ENABLED = {1 if enabled else 0}",
        f"SOURCE_VISUAL_CATALOG_COUNT = {len(entries)}",
        f"SOURCE_VISUAL_ROSTER_COUNT = {max_roster + 1}",
        f"SOURCE_VISUAL_MSU_OFFSET = ${int(msu_offset or 0):08X}",
        f"SOURCE_VISUAL_MSU_SIZE = {int(msu_size or 0)}",
        f"SOURCE_VISUAL_ENTRY_KEY_COUNT = {len(entries)}",
        f"SOURCE_VISUAL_PIECE_OFFSET = {piece_offset}",
        f"SOURCE_VISUAL_BLOCK_OFFSET = {block_offset}",
        f"SOURCE_VISUAL_PALETTE_OFFSET = {palette_offset}",
        f"SOURCE_VISUAL_SHEET_OFFSET = {sheet_offset}",
        f"SOURCE_VISUAL_BLOCK_COUNT = {len(unique_blocks)}",
        f"SOURCE_VISUAL_PALETTE_COUNT = {len(unique_palettes)}",
        f"SOURCE_VISUAL_SHEET_COUNT = {len(unique_sheets)}",
        "; Bank 19 ($13:8000) is reserved for the large native key table.",
        "SOURCE_VISUAL_KEY_BASE = $138000",
        "SourceVisual_RosterPolicy:",
    ]
    policies = ["VISUAL_POLICY_SOURCE_SIZED" for _ in range(max_roster + 1)]
    rows.append("    .db " + ", ".join(policies or ["VISUAL_POLICY_LEGACY_FIXED"]))
    roster_start = [None] * (max_roster + 1)
    roster_end = [None] * (max_roster + 1)
    for index, entry in enumerate(entries):
        roster = entry["roster"]
        if roster_start[roster] is None:
            roster_start[roster] = index * 6
        roster_end[roster] = (index + 1) * 6
    rows.append("SourceVisual_RosterKeyStart:")
    rows.append("    .dw " + ", ".join(str(v or 0) for v in roster_start))
    rows.append("SourceVisual_RosterKeyEnd:")
    rows.append("    .dw " + ", ".join(str(v or 0) for v in roster_end))
    key_rows = ["; Generated from production_source_publication.py; do not edit.",
                "SourceVisual_EntryKeys:"]
    # Store an entry index, not a byte offset: the entry table can exceed
    # 64 KiB once the complete BOR roster and authored maps are linked.
    # Native code derives 18 + index * 24 without truncating the catalog
    # address.
    for index, entry in enumerate(entries):
        key_rows.append(f"    .db {entry['roster']},{entry['runtime_role']},"
                        f"{entry['frame']},{entry['map']}")
        key_rows.append(f"    .dw {index}")
    if key_path:
        Path(key_path).write_text("\n".join(key_rows) + "\n",
                                  encoding="ascii", newline="\n")
    else:
        rows.extend(key_rows)
    Path(path).write_text("\n".join(rows) + "\n", encoding="ascii", newline="\n")


def write_catalog(roster_configs, json_path, include_path=None):
    catalog = build_catalog(roster_configs)
    Path(json_path).write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n",
                               encoding="utf-8", newline="\n")
    Path(json_path).with_suffix(".bin").write_bytes(pack_runtime_catalog(catalog))
    if include_path:
        emit_policy_include(catalog, include_path)
    return catalog
