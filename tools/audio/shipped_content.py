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

SHIPPED_CHARACTERS = {
    "bor-original": {"RALF", "JHUN", "JOE", "YASHIRO", "MISC\\TRASH", "MISC\\CHAIR", "MISC\\TABLE"},
    "tmnt": {"BEBOP", "FOOT01", "FOOT02", "FOOT03", "FOOT04", "LEATHER", "LEO", "MOUSER", "ROCK"},
}


def shipped_levels(family: str) -> set[str]:
    return {stage["source_level"].split("\\")[-1] for stage in STAGE_CONFIGS if stage["family"] == family}
