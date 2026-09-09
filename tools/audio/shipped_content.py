"""Authoritative shipped BOR/TMNT stage and character source identities."""
from __future__ import annotations

STAGE_CONFIGS = [
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
]

# Logical authored campaigns are deliberately separate from STAGE_CONFIGS.
# STAGE_CONFIGS is the physical MSU asset catalog; these source identities
# come from each pak's LEVELS file and are resolved to physical indices by
# build_rom.py. Keep incomplete BOR coverage explicit rather than allowing
# the packed catalog tail to become an accidental campaign continuation.
CAMPAIGN_CONFIGS = {
    "BOR_ORIGINAL": {
        "family": "bor-original",
        "source_levels_file": "DATA\\LEVELS.TXT",
        "source_levels": [
            "DATA\\EASY\\1AEASY.TXT",
            "DATA\\EASY\\1BEASY.TXT",
            "DATA\\EASY\\1CEASY.TXT",
        ],
        "incomplete_boundary": "TITLE",
    },
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
]

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
