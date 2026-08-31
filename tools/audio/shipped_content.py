"""Authoritative shipped BOR/TMNT stage and character source identities."""
from __future__ import annotations

STAGE_CONFIGS = [
    {"family": "bor-original", "pak": "Beats of Rage Original [v.3.0 Build 4086].pak", "source_level": "DATA\\EASY\\1BEASY.TXT", "bg": "out/bg_stage1b", "frontpanel": None, "spawn": "out/spawn_stage1b/spawn_table.bin"},
    {"family": "bor-original", "pak": "Beats of Rage Original [v.3.0 Build 4086].pak", "source_level": "DATA\\EASY\\1AEASY.TXT", "bg": "out/bg_stage1a", "frontpanel": "out/fp_stage1a", "spawn": "out/spawn_stage1a/spawn_table.bin"},
    {"family": "tmnt", "pak": "Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak", "source_level": "DATA\\LEVELS\\BEBOP.TXT", "bg": "out/bg_stage2boss", "frontpanel": None, "spawn": "out/spawn_stage2boss/spawn_table.bin"},
    {"family": "tmnt", "pak": "Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak", "source_level": "DATA\\LEVELS\\ROCK.TXT", "bg": "out/bg_stage3rock", "frontpanel": None, "spawn": "out/spawn_stage3rock/spawn_table.bin"},
    {"family": "tmnt", "pak": "Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak", "source_level": "DATA\\LEVELS\\LEATHER.TXT", "bg": "out/bg_stage4leather", "frontpanel": None, "spawn": "out/spawn_stage4leather/spawn_table.bin"},
    {"family": "tmnt", "pak": "Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak", "source_level": "DATA\\LEVELS\\SEWER0.TXT", "bg": "out/bg_stage5sewer0", "frontpanel": None, "spawn": "out/spawn_stage5sewer0/spawn_table.bin"},
    {"family": "tmnt", "pak": "Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak", "source_level": "DATA\\LEVELS\\STREETS.TXT", "bg": "out/bg_stage6streets", "frontpanel": None, "spawn": "out/spawn_stage6streets/spawn_table.bin"},
    {"family": "tmnt", "pak": "Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak", "source_level": "DATA\\LEVELS\\STREETS2.TXT", "bg": "out/bg_stage7streets2", "frontpanel": None, "spawn": "out/spawn_stage7streets2/spawn_table.bin"},
    {"family": "tmnt", "pak": "Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak", "source_level": "DATA\\LEVELS\\SEWER.TXT", "bg": "out/bg_stage8sewer", "frontpanel": None, "spawn": "out/spawn_stage8sewer/spawn_table.bin"},
    {"family": "tmnt", "pak": "Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak", "source_level": "DATA\\LEVELS\\FOOT.TXT", "bg": "out/bg_stage9foot", "frontpanel": None, "spawn": "out/spawn_stage9foot/spawn_table.bin"},
]

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
    {"family": "bor-original", "source_character": "DATA\\CHARS\\MISC\\APPLE", "converted_prefix": "out/apple", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\MISC\\MONEY", "converted_prefix": "out/money", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\MISC\\MEAT", "converted_prefix": "out/meat", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\MISC\\1UP", "converted_prefix": "out/1up", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\MISC\\GOLD", "converted_prefix": "out/gold", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\MISC\\TRASH", "converted_prefix": "out/trash", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\MISC\\CHAIR", "converted_prefix": "out/chair", "playable": False},
    {"family": "bor-original", "source_character": "DATA\\CHARS\\MISC\\TABLE", "converted_prefix": "out/table", "playable": False},
]

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
