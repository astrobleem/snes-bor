#!/usr/bin/env python3
"""Generate the pinned lossless large-OBJ layout for Normal source props.

OR-Tools is needed only for this offline regeneration tool. Production catalog
builds verify and consume the checked-in content-addressed result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "bor_compile"))
sys.path.insert(0, str(ROOT / "tools" / "audio"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ortools-path", type=Path,
                        help="temporary/local OR-Tools wheel target for regeneration")
    parser.add_argument("--time-limit", type=int, default=180,
                        help="per-frame CP-SAT limit in seconds")
    parser.add_argument("--palette-restarts", type=int, default=3)
    parser.add_argument("--palette-steps", type=int, default=2500)
    parser.add_argument("--palette-slot-steps", type=int, default=1800)
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).with_name("source_obj_atlas_manifest.json"))
    args = parser.parse_args()
    if args.ortools_path:
        sys.path.insert(0, str(args.ortools_path.resolve()))

    import production_source_publication as publication
    from shipped_content import ROSTER_CONFIGS

    publication.SOURCE_OBJ_LAYOUT_GENERATION = True
    publication.SOURCE_OBJ_LAYOUT_RESULTS.clear()
    original_palette_pack = publication.palette_banks_for_frames
    def bounded_palette_pack(source, frames, **kwargs):
        return original_palette_pack(
            source, frames, anneal_restarts=args.palette_restarts,
            anneal_steps=args.palette_steps,
            slot_iterations=args.palette_slot_steps, **kwargs)
    publication.palette_banks_for_frames = bounded_palette_pack
    # The source frames use native 32x64 OAM rectangles. The catalog builder
    # records the exact bounded large-rectangle placement per frame.
    config = next(row for row in ROSTER_CONFIGS
                  if row["source_character"].replace("\\", "/").upper()
                  .endswith("/MISC/FURNACE"))
    catalog = publication.build_catalog([config])
    entries = [row for row in catalog["entries"]
               if row["identity"].upper() == "MISC/FURNACE"
               and row["role"].lower() in ("idle", "waiting") and row["map"] == 0]
    entries.sort(key=lambda row: row["frame"])
    if len(entries) != 8 or catalog["blockers"]:
        raise RuntimeError(("NORMAL_FURNACE_LAYOUT_SHAPE", len(entries),
                            catalog["blockers"]))

    frames = {}
    for entry in entries:
        key = (entry["identity"].replace("\\", "/").upper(),
               entry["role"].lower(), str(entry["frame"]))
        layout = publication.SOURCE_OBJ_LAYOUT_RESULTS.get(key)
        expected = set(entry["blocks"])
        if layout is None or set(layout["origins"]) != expected:
            raise RuntimeError(("NORMAL_FURNACE_LAYOUT_BLOCK_BINDING",
                                entry["frame"],
                                0 if layout is None else len(layout["origins"]),
                                len(expected)))
        if layout["sheet_sha256"] != entry["sheet"]:
            raise RuntimeError(("NORMAL_FURNACE_LAYOUT_SHEET_BINDING",
                                entry["frame"], layout["sheet_sha256"],
                                entry["sheet"]))
        frames.setdefault(entry["identity"], {}).setdefault(entry["role"], {})[
            str(entry["frame"])] = dict(
                source_asset_sha256=entry["asset_sha256"],
                piece_size=[32, 64],
                sheet_sha256=layout["sheet_sha256"],
                blocks=layout["origins"],
            )

    manifest = dict(format="BOR_SOURCE_OBJ_ATLAS_LAYOUT_V1",
                    solver="OR-Tools CP-SAT; pinned generated placement",
                    obj_size=[32, 64], frames=frames)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    print(json.dumps(dict(path=str(output), frames=len(entries),
                          block_placements=sum(len(row["blocks"])
                                               for models in frames.values()
                                               for roles in models.values()
                                               for row in roles.values()),
                          source_assets=sorted({row["asset_sha256"] for row in entries}),
                          manifest_sha256=hashlib.sha256(output.read_bytes()).hexdigest()),
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
