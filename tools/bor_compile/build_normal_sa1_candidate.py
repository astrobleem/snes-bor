#!/usr/bin/env python3
"""Build a temporary compiler-owned Normal source image and install SA-1 runtime.

The source-sized S8 image is built under a temporary directory so the retained
artifact is one selectable, persistent-SA-1 candidate. PCM companions remain
hardlinks to distribution media throughout both build stages.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools" / "verify"))
sys.path.insert(0, str(ROOT / "tools" / "bor_compile"))
sys.path.insert(0, str(ROOT / "tools" / "audio"))


def _campaign_inputs(source_set='Normal'):
    from normal_coverage import inventory
    from shipped_content import ROSTER_CONFIGS, normal_player_entries
    coverage = inventory(source_set=source_set)
    normal_player_slots = {slot for slot, _ in normal_player_entries("bor-original")}
    combat_models = []
    for name, binding in sorted(coverage["model_bindings"].items()):
        if binding["source_type"] != "enemy":
            continue
        roster = binding["runtime_slot"]
        combat_models.append(dict(
            name=name,
            source_definition=binding["source_definition"],
            runtime_slot=roster,
            playable=roster in normal_player_slots,
        ))
    # The Normal selector has its own source-authored playable roster. It is
    # not ROSTER_CONFIGS[*].playable (which describes the unrelated legacy
    # Easy selector). Keep all 17 encounter enemies and add exactly the four
    # selected Normal player models as controlled SA-1 records.
    already_bound = {row["runtime_slot"] for row in combat_models}
    for slot, entry in normal_player_entries("bor-original"):
        if slot in already_bound:
            continue
        source_character = entry["source_character"].replace("/", "\\")
        name = source_character.rsplit("\\", 1)[-1].casefold()
        combat_models.append(dict(name=name,
            source_definition=source_character + "\\" + name + ".TXT",
            runtime_slot=slot, playable=True))
    if (sum(not row["playable"] for row in combat_models) != 17 or
            sum(row["playable"] for row in combat_models) != 4):
        raise RuntimeError("NORMAL_COMBAT_ROSTER_SHAPE_DRIFT")
    return coverage, combat_models


def _build_overlay(output: Path, source: Path, *, output_is_source=False, source_set='Normal'):
    from actor_s6_production_world import build as build_world
    from actor_s7_persistent_worker import install
    from actor_s7_production_runtime import source_visual_identity
    from pcm_runtime import assert_no_pcm_copy

    if not output_is_source:
        if output.exists():
            raise FileExistsError(f"refuse to replace existing candidate directory: {output}")
        output.mkdir(parents=True)
        # The compiler MSU is immutable for this overlay. Its PCM companions
        # are linked separately below; neither payload is copied.
        os.link(source / "bor.msu", output / "bor.msu")
    elif not (output / "bor.msu").is_file():
        raise FileNotFoundError("in-place source image has no bor.msu")

    coverage, combat_models = _campaign_inputs(source_set)
    source_rom = source / "bor.sfc"
    if not source_rom.is_file():
        raise FileNotFoundError(f"compiler source ROM missing: {source_rom}")
    source_rom_sha256 = hashlib.sha256(source_rom.read_bytes()).hexdigest()
    source_msu_sha256 = hashlib.sha256((source / "bor.msu").read_bytes()).hexdigest()
    visual = source_visual_identity(source)
    linked = build_world(output, "normal", resident=True,
                         layout_dispatch=True, stream_publisher=True,
                         presentation_divisor=2, base_dir=source,
                         base_rom=source_rom,
                         normal_campaign_models=combat_models)
    worker_symbols = install(output, production_runtime=True)
    manifest = dict(
            status=("OPT_IN_PERSISTENT_SA1_NORMAL_CAMPAIGN_CANDIDATE" if source_set == 'Normal'
                    else "PERSISTENT_SA1_HARD_CAMPAIGN_CANDIDATE"),
            compiler="BYOR — Bring Your Own Rage",
            source_set_id=coverage['source_set_id'],
            selectable_normal=True,
            fallback="unchanged distribution/bor.sfc S-CPU path",
            production_distribution_modified=False,
            source_image=dict(rom_sha256=source_rom_sha256,
                              msu_sha256=source_msu_sha256),
            candidate=dict(rom_sha256=hashlib.sha256(
                               (output / "bor.sfc").read_bytes()).hexdigest(),
                           msu_sha256=hashlib.sha256(
                               (output / "bor.msu").read_bytes()).hexdigest()),
            selectable_hard=source_set == 'Hard',
            workload=dict(campaign=f"BOR {source_set}", logical_entries=len(coverage['entries']),
                          authored_order=[row['source_path'] for row in coverage['entries']],
                          source_clock_hz=200, presentation_hz=30,
                          active_actor_limit=6, combat_models=len(combat_models),
                          playable_rosters=sum(row["playable"] for row in combat_models)),
            campaign_entries=[dict(ordinal=row["ordinal"], kind=row["kind"],
                                   source_path=row["source_path"],
                                   physical_id=row.get("physical_id"),
                                   queue_records=row.get("queue_records"),
                                   packed_sha256=row.get("packed_sha256"),
                                   next_after=row["next_after"])
                              for row in coverage["entries"]],
            runtime=dict(world_owner="persistent SA-1 BW-RAM epoch",
                         per_tick_acquire_release=False,
                         whole_context_round_trip=False,
                         source_sized_visual_catalog=visual,
                         obj_vram_byte_range=[0x8000, 0xC000],
                         obj_vram_bytes=16384,
                         full_visual_presentation_divisor=2,
                         event_protocol="sequenced 16-byte ring; capacity 128; fail closed",
                         normal_model_records=linked["normal_campaign"]["model_records"],
                         compatibility_world_programs=linked["normal_campaign"]["source_combat_models"],
                         bounded_worker_result="PERSISTENT_SA1_PRODUCTION_READY"),
            patches=linked["patches"],
            worker_symbols={key: value for key, value in worker_symbols.items()
                            if key in ("Worker_Gate", "Worker_Execute", "Worker_Complete",
                                       "Relay_Run", "Relay_Flush", "Relay_DrainEvents")},
            pcm_hardlinks=[path.name for path in sorted(source.glob("bor-*.pcm"))],
            build_link=linked,
        )
    (output / "production-runtime.json").write_text(
        json.dumps(manifest, indent=2) + "\n")
    assert_no_pcm_copy(Path("distribution"), output)
    return output, manifest


def build_from_source(output: Path, source_image: Path, *, in_place=False,
                      relink_source=False, source_set='Normal'):
    output = output.resolve()
    source = source_image.resolve()
    if in_place and output != source:
        raise ValueError("IN_PLACE_SOURCE_OUTPUT_MUST_MATCH")
    if not source.is_dir() or not (source / "bor.msu").is_file():
        raise FileNotFoundError(f"compiler source image incomplete: {source}")
    if in_place and (relink_source or not (source / "bor.sfc").is_file()):
        # The source build completed before a later overlay assembly failure.
        # Re-linking the already-generated main.bin is cheap and keeps the
        # expensive media/compiler stage from being repeated.
        import build_rom
        (source / "bor.sfc").write_bytes(build_rom.link_rom())
    return _build_overlay(output, source, output_is_source=in_place, source_set=source_set)


def build(output: Path, reuse_audio_from: str | None = None, *, source_set='Normal'):
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"refuse to replace existing candidate directory: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    import build_rom
    with tempfile.TemporaryDirectory(prefix="normal-source-", dir=ROOT / "out") as temporary:
        source = Path(temporary)
        build_rom.main(reuse_audio_from, normal_candidate=True,
                       source_sized_visual=True, candidate_dir=source,
                       hard_candidate=source_set == 'Hard')
        return _build_overlay(output, source, source_set=source_set)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-set", choices=('Normal', 'Hard'), default='Normal')
    parser.add_argument("--reuse-audio-from",
                        help="reuse pinned unchanged audio inputs from a Git ref")
    parser.add_argument("--source-image", type=Path,
                        help="reuse an already-generated Normal source image directory")
    parser.add_argument("--in-place-source-image", action="store_true",
                        help="finish SA-1 overlay in the source-image directory itself")
    parser.add_argument("--relink-source-image", action="store_true",
                        help="rebuild a clean base ROM from the current main.bin before overlaying")
    args = parser.parse_args()
    if args.in_place_source_image and not args.source_image:
        parser.error("--in-place-source-image requires --source-image")
    if args.relink_source_image and not args.in_place_source_image:
        parser.error("--relink-source-image requires --in-place-source-image")
    if args.source_image:
        candidate, manifest = build_from_source(
            args.output, args.source_image, in_place=args.in_place_source_image,
            relink_source=args.relink_source_image, source_set=args.source_set)
    else:
        candidate, manifest = build(args.output, args.reuse_audio_from, source_set=args.source_set)
    result = {
        "output": str(candidate),
        "status": manifest["status"],
        "rom_sha256": manifest["candidate"]["rom_sha256"],
        "msu_sha256": manifest["candidate"]["msu_sha256"],
        "source_rom_sha256": manifest["source_image"]["rom_sha256"],
        "source_msu_sha256": manifest["source_image"]["msu_sha256"],
        "source_visual_entries": manifest["runtime"]["source_sized_visual_catalog"]["entries"],
        "pcm_hardlinks": manifest["pcm_hardlinks"],
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
