"""Authoritative shipped BOR/TMNT stage and character source identities."""
from __future__ import annotations

# Accepted encoded media, in legacy physical order; BOR progression is source-owned.
STAGE_MEDIA_BINDINGS = [
    {"family": "bor-original", "pak": "Beats of Rage Original [v.3.0 Build 4086].pak", "source_level": "DATA\\EASY\\1AEASY.TXT", "bg": "out/bg_stage1a", "frontpanel": "out/fp_stage1a", "spawn": "out/spawn_stage1a/spawn_table.bin"},
    {"family": "bor-original", "pak": "Beats of Rage Original [v.3.0 Build 4086].pak", "source_level": "DATA\\EASY\\1BEASY.TXT", "bg": "out/bg_stage1b", "frontpanel": None, "spawn": "out/spawn_stage1b/spawn_table.bin"},
    {"family": "bor-original", "pak": "Beats of Rage Original [v.3.0 Build 4086].pak", "source_level": "DATA\\EASY\\1CEASY.TXT", "bg": "out/bg_bor_1c", "frontpanel": None, "spawn": "out/spawn_bor_1c/spawn_table.bin"},
    {"family": "tmnt", "pak": "Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak", "source_level": "DATA\\LEVELS\\BEBOP.TXT", "bg": "out/bg_stage2boss", "frontpanel": None, "spawn": "out/spawn_stage2boss/spawn_table.bin"},
    {"family": "tmnt", "pak": "Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak", "source_level": "DATA\\LEVELS\\ROCK.TXT", "bg": "out/bg_stage3rock", "frontpanel": None, "spawn": "out/spawn_stage3rock/spawn_table.bin"},
    {"family": "tmnt", "pak": "Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak", "source_level": "DATA\\LEVELS\\LEATHER.TXT", "bg": "out/bg_stage4leather", "frontpanel": None, "spawn": "out/spawn_stage4leather/spawn_table.bin"},
    {"family": "tmnt", "pak": "Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak", "source_level": "DATA\\LEVELS\\SEWER0.TXT", "bg": "out/bg_stage5sewer0", "frontpanel": None, "spawn": "out/spawn_stage5sewer0/spawn_table.bin"},
    {"family": "tmnt", "pak": "Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak", "source_level": "DATA\\LEVELS\\STREETS.TXT", "bg": "out/bg_stage6streets", "frontpanel": None, "spawn": "out/spawn_stage6streets/spawn_table.bin"},
    {"family": "tmnt", "pak": "Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak", "source_level": "DATA\\LEVELS\\STREETS2.TXT", "bg": "out/bg_stage7streets2", "frontpanel": None, "spawn": "out/spawn_stage7streets2/spawn_table.bin"},
    {"family": "tmnt", "pak": "Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak", "source_level": "DATA\\LEVELS\\SEWER.TXT", "bg": "out/bg_stage8sewer", "frontpanel": None, "spawn": "out/spawn_stage8sewer/spawn_table.bin"},
    {"family": "tmnt", "pak": "Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak", "source_level": "DATA\\LEVELS\\FOOT.TXT", "bg": "out/bg_stage9foot", "frontpanel": None, "spawn": "out/spawn_stage9foot/spawn_table.bin"},
    # Appended after the accepted TMNT/test catalog so physical indices stay
    # stable; BOR campaign resolution is by source identity.
    {"family": "bor-original", "pak": "Beats of Rage Original [v.3.0 Build 4086].pak", "source_level": "DATA\\EASY\\2EASY.TXT", "bg": "out/bg_2easy", "frontpanel": None, "spawn": "out/spawn_2easy/spawn_table.bin"},
    {"family": "bor-original", "pak": "Beats of Rage Original [v.3.0 Build 4086].pak", "source_level": "DATA\\EASY\\3AEASY.TXT", "bg": "out/bg_3easy", "frontpanel": None, "spawn": "out/spawn_3easy/spawn_table.bin"},
    {"family": "bor-original", "pak": "Beats of Rage Original [v.3.0 Build 4086].pak", "source_level": "DATA\\EASY\\3BEASY.TXT", "bg": "out/bg_3beasy", "frontpanel": "out/fp_3beasy", "spawn": "out/spawn_3beasy/spawn_table.bin"},
    {"family": "bor-original", "pak": "Beats of Rage Original [v.3.0 Build 4086].pak", "source_level": "DATA\\EASY\\3CEASY.TXT", "bg": "out/bg_3ceasy", "frontpanel": "out/fp_3ceasy", "spawn": "out/spawn_3ceasy/spawn_table.bin"},
    {"family": "bor-original", "pak": "Beats of Rage Original [v.3.0 Build 4086].pak", "source_level": "DATA\\EASY\\4AEASY.TXT", "bg": "out/bg_4aeasy", "frontpanel": None, "spawn": "out/spawn_4aeasy/spawn_table.bin"},
    {"family": "bor-original", "pak": "Beats of Rage Original [v.3.0 Build 4086].pak", "source_level": "DATA\\EASY\\4BEASY.TXT", "bg": "out/bg_4beasy", "frontpanel": "out/fp_4beasy", "spawn": "out/spawn_4beasy/spawn_table.bin"},
    {"family": "bor-original", "pak": "Beats of Rage Original [v.3.0 Build 4086].pak", "source_level": "DATA\\EASY\\5AEASY.TXT", "bg": "out/bg_5aeasy", "frontpanel": None, "spawn": "out/spawn_5aeasy/spawn_table.bin", "scroll_direction": "down"},
    {"family": "bor-original", "pak": "Beats of Rage Original [v.3.0 Build 4086].pak", "source_level": "DATA\\EASY\\5BEASY.TXT", "bg": "out/bg_5beasy", "frontpanel": None, "spawn": "out/spawn_5beasy/spawn_table.bin"},
    {"family": "bor-original", "pak": "Beats of Rage Original [v.3.0 Build 4086].pak", "source_level": "DATA\\EASY\\6AEASY.TXT", "bg": "out/bg_6aeasy", "frontpanel": "out/fp_6aeasy", "spawn": "out/spawn_6aeasy/spawn_table.bin", "scroll_direction": "left", "source_direction": "left", "source_mirror": True},
    {"family": "bor-original", "pak": "Beats of Rage Original [v.3.0 Build 4086].pak", "source_level": "DATA\\EASY\\6BEASY.TXT", "bg": "out/bg_6beasy", "frontpanel": "out/fp_6beasy", "spawn": "out/spawn_6beasy/spawn_table.bin", "scroll_direction": "left", "source_direction": "left"},
    {"family": "bor-original", "pak": "Beats of Rage Original [v.3.0 Build 4086].pak", "source_level": "DATA\\EASY\\6CEASY.TXT", "bg": "out/bg_6ceasy", "frontpanel": "out/fp_6ceasy", "spawn": "out/spawn_6ceasy/spawn_table.bin"},
]

# Legacy physical ABI pins, expressed as source-stage ordinals (scenes do not
# consume catalog slots). The linker appends Normal in source order after the
# accepted Easy/foreign media. These ranges pin IDs, never campaign length.
LEGACY_BOR_STAGE_IDS = {
    "Easy": (0, 1, 2, *range(11, 22)),
    "Normal": tuple(range(22, 32)),
}
LEGACY_FOREIGN_STAGE_IDS = tuple(range(3, 11))
STAGE_CONFIGS = list(STAGE_MEDIA_BINDINGS)

# Only foreign campaigns require explicit bindings here. The compiler creates
# both BOR campaigns, including scene positions and next boundaries, from source.
CAMPAIGN_CONFIGS = {
    "TMNT": {
        "family": "tmnt",
        "source_levels_file": "DATA\\LEVELS00.TXT",
        "source_levels": [
            "DATA\\LEVELS\\SEWER0.TXT",
            "DATA\\LEVELS\\STREETS.TXT",
            "DATA\\LEVELS\\STREETS2.TXT",
            "DATA\\LEVELS\\SEWER.TXT",
        ],
    },
    "STANDALONE_TEST_CONTENT": {
        "family": "standalone",
        "source_levels": [
            "DATA\\LEVELS\\BEBOP.TXT",
            "DATA\\LEVELS\\ROCK.TXT",
            "DATA\\LEVELS\\LEATHER.TXT",
            "DATA\\LEVELS\\FOOT.TXT",
        ],
    },
}

ROSTER_CONFIGS = [
    {"family": "bor-original", "source_character": "DATA\\CHARS\\RALF", "converted_prefix": "out/ralf", "playable": True},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\JHUN", "converted_prefix": "out/jhun", "playable": True},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\JOE", "converted_prefix": "out/joe", "playable": True},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\YASHIRO", "converted_prefix": "out/yashiro", "playable": True},
    {"family": "tmnt", "source_character": "DATA\\CHARS\\MOUSER", "converted_prefix": "out/mouser", "playable": True},
    {"family": "tmnt", "source_character": "DATA\\CHARS\\FOOT01", "converted_prefix": "out/foot01", "playable": True},
    {"family": "tmnt", "source_character": "DATA\\CHARS\\ROCK", "converted_prefix": "out/rock", "playable": True},
    {"family": "tmnt", "source_character": "DATA\\CHARS\\LEATHER", "converted_prefix": "out/leather", "playable": True},
    {"family": "tmnt", "source_character": "DATA\\CHARS\\BEBOP", "converted_prefix": "out/bebop", "playable": True},
    {"family": "tmnt", "source_character": "DATA\\CHARS\\FOOT02", "converted_prefix": "out/foot02", "playable": True},
    {"family": "tmnt", "source_character": "DATA\\CHARS\\FOOT03", "converted_prefix": "out/foot03", "playable": True},
    {"family": "tmnt", "source_character": "DATA\\CHARS\\FOOT04", "converted_prefix": "out/foot04", "playable": True},
    {"family": "tmnt", "source_character": "DATA\\CHARS\\LEO", "converted_prefix": "out/leo", "playable": True},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\YAMAZAKI", "converted_prefix": "out/yamazaki", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\MISC\\APPLE", "converted_prefix": "out/apple", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\MISC\\MONEY", "converted_prefix": "out/money", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\MISC\\MEAT", "converted_prefix": "out/meat", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\MISC\\1UP", "converted_prefix": "out/1up", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\MISC\\GOLD", "converted_prefix": "out/gold", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\MISC\\TRASH", "converted_prefix": "out/trash", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\MISC\\CHAIR", "converted_prefix": "out/chair", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\MISC\\TABLE", "converted_prefix": "out/table", "playable": False},
    # Source-normal BOR players are appended so existing runtime roster and
    # embedded spawn indices remain stable.  Player selection uses the
    # explicit source mapping below, not the legacy playable prefix.
    {"family": "bor-original", "source_character": "DATA\\CHARS\\KULA", "converted_prefix": "out/kula", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\MAXIMA", "converted_prefix": "out/maxima", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\MARY", "converted_prefix": "out/mary", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\MIGHTY", "converted_prefix": "out/mighty", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\HEAVY", "converted_prefix": "out/heavy", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\MISC\\FENCE", "converted_prefix": "out/fence", "playable": False},
    # Original BOR subtype biker. Runtime-only; never part of normal player
    # selection. Its sparse idle/pain model is consumed by the biker state
    # machine rather than by the ordinary walk/attack animation path.
    {"family": "bor-original", "source_character": "DATA\\CHARS\\BIKER-K", "converted_prefix": "out/biker_k", "playable": False,
     "source_visual_layout": "model-shared-lossless"},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\ANGEL", "converted_prefix": "out/angel", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\SHERMIE", "converted_prefix": "out/shermie", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\K", "converted_prefix": "out/k_prime", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\BILLY", "converted_prefix": "out/billy", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\MISC\\BOX", "converted_prefix": "out/box", "playable": False},
    # G15-E 3CEASY-only runtime identities; appended to preserve prior indices.
    {"family": "bor-original", "source_character": "DATA\\CHARS\\MISC\\FURNACE", "converted_prefix": "out/furnace", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\MISC\\STEAMER", "converted_prefix": "out/steamer", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\MISC\\CRATE", "converted_prefix": "out/crate", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\ROBERT", "converted_prefix": "out/robert", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\MISC\\STEAM", "converted_prefix": "out/steam", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\MISC\\DRUM", "converted_prefix": "out/drum", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\K9999", "converted_prefix": "out/k9999", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\EIJI", "converted_prefix": "out/eiji", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\MRBIG", "converted_prefix": "out/mrbig", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\MISC\\TROLLY", "converted_prefix": "out/trolly", "playable": False},
    # G15-M 6CEASY runtime-only boss identity; never selectable.
    {"family": "bor-original", "source_character": "DATA\\CHARS\\RUGAL", "converted_prefix": "out/rugal", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\RAMON", "converted_prefix": "out/ramon", "playable": False,
     "pak": "Beats of Rage Original [v.3.0 Build 4086].pak", "source_definition": "DATA\\CHARS\\RAMON\\RAMON.TXT", "source_defaults": True, "runtime_binding_sets": (1, 2, 3), "accepted_legacy_unbound_sets": (0,)},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\MISC\\TIME", "converted_prefix": "out/time", "playable": False,
     "pak": "Beats of Rage Original [v.3.0 Build 4086].pak", "source_definition": "DATA\\CHARS\\MISC\\TIME.TXT", "source_defaults": True, "runtime_binding_sets": (1, 2, 3), "accepted_legacy_unbound_sets": (0,)},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\CRAB", "converted_prefix": "out/crab", "playable": False,
     "pak": "Beats of Rage Original [v.3.0 Build 4086].pak", "source_definition": "DATA\\CHARS\\CRAB\\CRAB.TXT", "source_defaults": True, "runtime_binding_sets": (3,)},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\LOBSTER", "converted_prefix": "out/lobster", "playable": False,
     "pak": "Beats of Rage Original [v.3.0 Build 4086].pak", "source_definition": "DATA\\CHARS\\LOBSTER\\LOBSTER.TXT", "source_defaults": True, "runtime_binding_sets": (3,)},
]

# Scene identities bind authored ordered clips through production transport.
SCENE_CONFIGS = [
    {"scene_id": "RUGAL", "runtime_id": 1,
     "source_scene": "DATA\\SCENES\\RUGAL.TXT"},
    {"scene_id": "ENDING", "runtime_id": 2,
     "source_scene": "DATA\\SCENES\\ENDING.TXT"},
    {"scene_id": "SEWER", "runtime_id": 3, "source_scene": "DATA\\SCENES\\SEWER.TXT"},
]

# BOR.C showcomplete() is an authored, non-looping completion presentation
# between every `gonext` level, including 6CEASY before ENDING.  Keep this
# source-backed declaration separate from campaign scenes: it is completion
# presentation audio, not a campaign entry.
BOR_COMPLETION_MUSIC = {
    "family": "bor-original",
    "source_path": "DATA\\MUSIC\\COMPLETE.BOR",
    "source_file": "BOR.C:showcomplete()",
    "loop_argument": "0",
}

# Source authority is the PAK's MODELS.TXT plus each referenced model's
# `type` directive.  The existing runtime roster is broader than normal source
# player selection because it also contains identities needed for AI spawn and
# reassignment proofs.  Keep those runtime entries, but do not let them define
# canonical player/stage capacity contexts.
SOURCE_PLAYER_SELECTION = {
    "bor-original": {
        "normal": {"KULA", "MAXIMA", "MARY", "MIGHTY"},
        "source_order": ["KULA", "MAXIMA", "MARY", "MIGHTY"],
        "source_names": {"KULA": "KULA", "MAX": "MAXIMA", "MANDY": "MARY", "MIGHTY": "MIGHTY"},
        "commented_player": set(),
        "evidence": "DATA\\MODELS.TXT: uncommented load entries whose model TXT declares type player",
    },
    "tmnt": {
        "normal": {"LEO"},
        "commented_player": {"DON", "MIKE"},
        "evidence": "data\\MODELS.TXT: leo is uncommented; don and mike are commented load entries",
    },
}

for _entry in ROSTER_CONFIGS:
    _identity = _entry["source_character"].split("\\CHARS\\", 1)[1].upper()
    _source = SOURCE_PLAYER_SELECTION[_entry["family"]]
    _is_prop = _identity.startswith("MISC\\")
    _entry["runtime_roster_member"] = True
    _entry["normal_player_selectable"] = _identity in _source["normal"]
    _entry["ai_spawnable"] = not _is_prop
    _entry["optional_bonus_player"] = not _is_prop and not _entry["normal_player_selectable"]


def normal_player_entries(family: str | None = None):
    """Return only source-normal players represented by the current runtime."""
    result = []
    families = [family] if family else list(SOURCE_PLAYER_SELECTION)
    for selected_family in families:
        source = SOURCE_PLAYER_SELECTION[selected_family]
        for identity in source.get("source_order", sorted(source["normal"])):
            matches = [(i, e) for i, e in enumerate(ROSTER_CONFIGS)
                       if e["family"] == selected_family
                       and e["source_character"].split("\\CHARS\\", 1)[1].upper() == identity]
            if len(matches) != 1:
                raise ValueError(f"source-normal player {selected_family}:{identity} resolves to {len(matches)} runtime entries")
            result.extend(matches)
    return result

ROSTER_PREFIXES = [entry["converted_prefix"] for entry in ROSTER_CONFIGS]
PLAYABLE_ROSTER_COUNT = sum(entry["playable"] for entry in ROSTER_CONFIGS)


def source_character_identity(family: str, source_file: str) -> str | None:
    """Resolve a PAK character file to the longest authoritative roster identity."""
    source = source_file.replace("/", "\\").upper().strip("\\")
    marker = "DATA\\CHARS\\"
    if marker not in source:
        return None
    relative = source.split(marker, 1)[1]
    candidates = []
    for entry in ROSTER_CONFIGS:
        if entry["family"] != family:
            continue
        identity = entry["source_character"].split("\\CHARS\\", 1)[1].upper().strip("\\")
        if relative == identity + ".TXT" or relative.startswith(identity + "\\"):
            candidates.append(identity)
    return max(candidates, key=len) if candidates else None


def shipped_characters() -> dict[str, set[str]]:
    return {
        family: {entry["source_character"].split("\\CHARS\\", 1)[1] for entry in ROSTER_CONFIGS if entry["family"] == family}
        for family in {entry["family"] for entry in ROSTER_CONFIGS}
    }


def shipped_levels(family: str) -> set[str]:
    return {stage["source_level"].split("\\")[-1] for stage in STAGE_CONFIGS if stage["family"] == family}


# Additional source presentation binding. It is allocated after all legacy
# stages by the linker; conversion uses the shared streaming BG encoder.
STAGE_MEDIA_BINDINGS.append(dict(family='bor-original',
    pak='Beats of Rage Original [v.3.0 Build 4086].pak',
    source_level='DATA\\EXTRA.TXT', bg='out/bg_source_extra', frontpanel=None,
    spawn='out/compiler_campaign/data/extra/spawn_table.bin', source_media=True))

# Source owns the complete selected campaigns. The preceding records are
# accepted encoded-media/physical-ID bindings, not logical progression.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / 'bor_compile'))
from production_campaign import link_campaigns as _link_campaigns
STAGE_CONFIGS, CAMPAIGN_CONFIGS, COMPILER_CAMPAIGN_COVERAGE = _link_campaigns(
    STAGE_CONFIGS, CAMPAIGN_CONFIGS, SCENE_CONFIGS,
    media_bindings=STAGE_MEDIA_BINDINGS, legacy_stage_ids=LEGACY_BOR_STAGE_IDS)
