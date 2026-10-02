#!/usr/bin/env python3
"""Focused G15-R11 Normal 5A source, catalog, and vertical-stage gate."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
from _harness import Reporter, exact_input_edge, open_session, pasm_constant_in, poll_until, read_block
import game_bor_startup_select as startup

sys.path.insert(0, ROOT)
sys.path[:0] = [os.path.join(ROOT, "tools", "bg_converter"),
               os.path.join(ROOT, "tools", "bor_converter")]
import build_rom
from bor_levels import parse_levels_from_pak
from level_parse import parse_level
from pak_extract import extract
from spawn_parse import GroupEvent, SpawnEvent, parse_spawns

PAK = os.path.join(ROOT, "Beats of Rage Original [v.3.0 Build 4086].pak")
EASY = r"DATA\EASY\5AEASY.TXT"
NORMAL = r"DATA\NORMAL\5A.TXT"
STATE = pasm_constant_in("src/core/game_state.pasm", "Game_State")
PLAYING = pasm_constant_in("src/core/game_state.pasm", "GAME_STATE_PLAYING")
STAGECLEAR = pasm_constant_in("src/core/game_state.pasm", "GAME_STATE_STAGECLEAR")
TITLE = pasm_constant_in("src/core/game_state.pasm", "GAME_STATE_TITLE")
CAMPAIGN = pasm_constant_in("src/core/game_state.pasm", "Game_CampaignId")
ORDINAL = pasm_constant_in("src/core/game_state.pasm", "Game_CampaignOrdinal")
STAGE = pasm_constant_in("src/core/game_state.pasm", "Game_StageIndex")
PENDING = pasm_constant_in("src/core/game_state.pasm", "Stage_LoadPending")
TIMES = pasm_constant_in("src/core/options.pasm", "Bor_TimesCompleted")
ACTIVE = pasm_constant_in("src/main.pasm", "StageComplete_Active")
MUSIC = pasm_constant_in("src/main.pasm", "Music_LastTrack")
SPAWN_INDEX = pasm_constant_in("src/core/spawn.pasm", "Spawn_Index")
SPAWN_COUNT = pasm_constant_in("src/core/spawn.pasm", "Spawn_Count")
SCREEN_POS_Y = 0x7E1604
SCREEN_TARGET_Y = 0x7E1618
SCREEN_MAX_Y = 0x7E1610


def u8(m, address):
    return read_block(m, address, 32)[0]


def u16(m, address):
    b = read_block(m, address, 32)
    return b[0] | (b[1] << 8)


def source_gate(r):
    texts = {p: extract(PAK, p).decode("latin1") for p in (EASY, NORMAL)}
    levels = {p: parse_level(texts[p], p) for p in texts}
    events = {p: parse_spawns(texts[p]) for p in texts}
    n, e = levels[NORMAL], levels[EASY]
    ns = [x for x in events[NORMAL] if isinstance(x, SpawnEvent)]
    es = [x for x in events[EASY] if isinstance(x, SpawnEvent)]
    r.check("authoritative Normal 5A source", NORMAL in texts)
    r.check("Elevator presentation reused", (n.background, n.frontpanel, n.panels, n.order) ==
            (e.background, e.frontpanel, e.panels, e.order))
    r.check("source direction is down", "direction\tdown" in texts[NORMAL].lower())
    r.check("source music is reused", "music\t\tdata/music/supertb.bor" in texts[NORMAL].lower())
    r.check("authored queue is 64 / 55 spawns / 9 groups",
            len(events[NORMAL]) == 64 and len(ns) == 55 and
            sum(isinstance(x, GroupEvent) for x in events[NORMAL]) == 9)
    r.check("Easy comparison is 54 / 45 spawns / 9 groups",
            len(events[EASY]) == 54 and len(es) == 45 and
            sum(isinstance(x, GroupEvent) for x in events[EASY]) == 9)
    r.check("endhole and no unsupported hole/blocked", "endhole\t\t1" in texts[NORMAL].lower()
            and "\nhole" not in texts[NORMAL].lower()
            and "\nblocked" not in texts[NORMAL].lower())
    r.check("Normal encounter deltas are preserved",
            any(x.character.lower() == "shermie" and x.health == 100 for x in ns)
            and any(x.character.lower() == "billy" and x.health == 120 for x in ns)
            and any(x.character.lower() == "ramon" for x in ns)
            and any(x.character.lower() == "jhun" for x in ns))
    r.check("authored items and 2pitem preserved",
            sum(bool(x.item) for x in ns) == 2 and sum(x.if2p for x in ns) == 1)
    r.check("identities are packed roster identities",
            {x.character.lower() for x in ns} <=
            {"drum", "time", "shermie", "yashiro", "ramon", "ralf", "k'", "billy", "angel", "joe", "jhun"})
    normal_set = next(s for s in parse_levels_from_pak(PAK) if s.name == "Normal")
    idx = [i for i, item in enumerate(normal_set.entries)
           if item[1].replace("/", "\\").upper() == NORMAL]
    r.check("LEVELS has 4B next then 5A", normal_set.entries[idx[0] - 1][0] == "next"
            and normal_set.entries[idx[0]][0] == "file"
            and normal_set.entries[idx[0] + 1][0] == "file")


def catalog_gate(r):
    matches = [(i, s) for i, s in enumerate(build_rom.STAGE_CONFIGS)
               if s["source_level"].upper() == NORMAL]
    r.check("Normal 5A is physical tail index 31",
            len(matches) == 1 and matches[0][0] == len(build_rom.STAGE_CONFIGS) - 1 == 31)
    if matches:
        stage = matches[0][1]
        r.check("packed queue is 64 records", os.path.getsize(os.path.join(ROOT, stage["spawn"])) == 640)
        manifest = json.load(open(os.path.join(ROOT, stage["bg"], "manifest.json"), encoding="utf-8"))
        r.check("vertical packed geometry is 256x224",
                manifest["width_px"] == 256 and manifest["height_px"] == 224)
    r.check("Normal map is 22..31",
            build_rom.CAMPAIGN_STAGE_MAPS["BOR_NORMAL_1A_INTERNAL"] == list(range(22, 32)))
    generated = open(os.path.join(ROOT, "tools", "audio", "campaign_config.pasm"), encoding="ascii").read()
    r.check("boundary flags are 0,0,1,1,0,0,1,0,1,0",
            ".db 0, 0, 1, 1, 0, 0, 1, 0, 1, 0" in generated)
    r.check("Normal remains unavailable", "BorSet_ContentAvailable:\n    .db 1, 0, 0, 0" in generated)
    music = open(os.path.join(ROOT, "tools", "audio", "audio_music_ids.pasm"), encoding="ascii").read()
    r.check("stage music table has 32 entries", "Music_StageTrackCount = 32" in music)
    return matches[0][0] if matches else -1


def load_5a(m, ordinal):
    startup.cold_to_title(m, Reporter("startup", kind="SUB"))
    startup.select_case(m, Reporter("select", kind="SUB"), "KULA")
    m.run_frames(60)
    m.write_u8(CAMPAIGN, 3)
    m.write_u8(ORDINAL, ordinal)
    m.write_u8(PENDING, 1)
    m.write_u16(STATE, STAGECLEAR)
    return poll_until(m, lambda s: u16(s, STATE) == PLAYING, max_frames=900)


def runtime_gate(r, stage):
    with open_session(__file__) as m:
        # The real authored 4B next boundary resolves to 5A after completion.
        startup.cold_to_title(m, Reporter("startup", kind="SUB"))
        startup.select_case(m, Reporter("select", kind="SUB"), "KULA")
        m.run_frames(60)
        m.write_u8(CAMPAIGN, 3)
        m.write_u8(ORDINAL, 8)
        m.write_u8(PENDING, 1)
        m.write_u16(STATE, STAGECLEAR)
        r.check("4B -> 5A direct typed handoff",
                poll_until(m, lambda s: u16(s, STAGE) == stage and u16(s, STATE) == PLAYING,
                            max_frames=900))
        r.check("4B -> 5A has no completion presenter", u8(m, ACTIVE) == 0)
        r.check("5A selects SCROLL_DOWN and starts its music",
                u8(m, MUSIC) == 13 and u16(m, STAGE) == stage)
        start_y = u16(m, SCREEN_POS_Y)
        start_target = u16(m, SCREEN_TARGET_Y)
        m.run_frames(120)
        end_y = u16(m, SCREEN_POS_Y)
        r.check("vertical camera progresses from clean state", end_y != start_y or u16(m, SCREEN_TARGET_Y) != start_target)
        r.check("queue is runtime-loaded, not manually indexed",
                u8(m, SPAWN_COUNT) == 64 and u8(m, SPAWN_INDEX) > 0)
        before = u8(m, TIMES)
        m.write_u8(PENDING, 1)
        m.write_u16(STATE, STAGECLEAR)
        r.check("5A no-next skips showcomplete", poll_until(m, lambda s: u16(s, STATE) == TITLE, max_frames=240)
                and u8(m, ACTIVE) == 0 and u8(m, TIMES) == before and u8(m, MUSIC) != 3)


def main():
    r = Reporter("G15-BATCH-R11-NORMAL-5A", kind="GATE")
    source_gate(r)
    stage = catalog_gate(r)
    runtime_gate(r, stage)
    r.finish()


if __name__ == "__main__":
    main()
