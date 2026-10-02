#!/usr/bin/env python3
"""Focused R1 SRAM-v2/process-restart gate.

The fixture avoids title/options navigation.  SRAM images are byte-exact
inputs; initialization and migration are performed by production code. The
completion cases enter GAME_STATE_STAGECLEAR with the final imported BOR
ordinal, then let the real completion presentation and campaign-end handler
own the credit and save.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, open_session, pasm_constant_in  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MESEN_EXE = os.environ.get('MESEN_EXE', r'E:\gh\Mesen2\bin\win-x64\Release\Mesen.exe')
SRM = os.path.join(os.path.dirname(MESEN_EXE), 'Saves', 'bor.srm')

STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
STATE_PREV = pasm_constant_in('src/core/game_state.pasm', 'Game_StatePrev')
STAGECLEAR = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_STAGECLEAR')
PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
CAMPAIGN = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignId')
ORDINAL = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignOrdinal')
STAGE = pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')
PENDING = pasm_constant_in('src/core/game_state.pasm', 'Stage_LoadPending')
OAM_NEED = pasm_constant_in('src/core/oam.pasm', 'Oam_NeedFullUpload')
BOR_SET_SELECTED = pasm_constant_in('src/core/game_state.pasm', 'BorSet_Selected')
BOR_SET_ACTIVE = pasm_constant_in('src/core/game_state.pasm', 'BorSet_RunActive')
BOR_SET_CREDITED = pasm_constant_in('src/core/game_state.pasm', 'BorSet_CompletionCredited')
STAGE_COMPLETE_ACTIVE = pasm_constant_in('src/main.pasm', 'StageComplete_Active')
STAGE_COMPLETE_FINISH = pasm_constant_in('src/main.pasm', 'StageComplete_FinishTicks')
STAGE_COMPLETE_P1_CLEAR = pasm_constant_in('src/main.pasm', 'StageComplete_P1Clear')
STAGE_COMPLETE_P1_LIFE = pasm_constant_in('src/main.pasm', 'StageComplete_P1Life')
STAGE_COMPLETE_P2_CLEAR = pasm_constant_in('src/main.pasm', 'StageComplete_P2Clear')
STAGE_COMPLETE_P2_LIFE = pasm_constant_in('src/main.pasm', 'StageComplete_P2Life')
TIMES = pasm_constant_in('src/core/options.pasm', 'Bor_TimesCompleted')
VOLUME = pasm_constant_in('src/core/options.pasm', 'Options_MusicVolume')
VERSION = pasm_constant_in('src/core/options.pasm', 'OPTIONS_VERSION_CURRENT')
DEFAULT_VOLUME = pasm_constant_in('src/core/options.pasm', 'OPTIONS_MUSICVOL_DEFAULT')

MAGIC = bytes((pasm_constant_in('src/core/options.pasm', 'OPTIONS_MAGIC0_VALUE'),
               pasm_constant_in('src/core/options.pasm', 'OPTIONS_MAGIC1_VALUE')))


def u8(m, address):
    return m.read_u8(address)


def u32(m, address):
    return int.from_bytes(m.read_memory('snesMemory', address, 4), 'little')


def write_srm(version, volume, count=0):
    data = bytearray(0x8000)
    data[0:2] = MAGIC
    data[2] = version
    data[3] = volume
    if version >= 2:
        data[4:8] = count.to_bytes(4, 'little')
    with open(SRM, 'wb') as f:
        f.write(data)


def setup_final_clear(m, new_run=True):
    # This is setup only; StageComplete_Dispatch, its presentation, resolver,
    # campaign-end credit, and SRAM save all execute in production.
    m.write_u8(CAMPAIGN, 0)
    m.write_u8(ORDINAL, 15)
    m.write_u16(STAGE, 21)
    m.write_u8(BOR_SET_SELECTED, 0)
    m.write_u8(BOR_SET_ACTIVE, 1)
    if new_run:
        m.write_u8(BOR_SET_CREDITED, 0)
    # Valid completed-presentation state: StageComplete_Dispatch still owns
    # the update, resolver, campaign end, and credit; no menu or direct credit
    # helper is involved, and no lengthy visual count-up is needed here.
    m.write_u8(STAGE_COMPLETE_ACTIVE, 1)
    m.write_u16(STAGE_COMPLETE_FINISH, 0)
    m.write_u16(STAGE_COMPLETE_P1_CLEAR, 0)
    m.write_hex(STAGE_COMPLETE_P1_LIFE, '00000000')
    m.write_u16(STAGE_COMPLETE_P2_CLEAR, 0)
    m.write_hex(STAGE_COMPLETE_P2_LIFE, '00000000')
    m.write_u8(PENDING, 1)
    # Reproduce the state edge that the ordinary PLAYING win path creates.
    m.write_u16(STATE_PREV, PLAYING)
    m.write_u8(OAM_NEED, 0)
    m.write_u16(STATE, STAGECLEAR)
    m.run_frames(600)


def check_loaded(r, m, label, volume, count):
    got_volume = u8(m, VOLUME)
    got_count = u32(m, TIMES)
    r.check(f'{label}: volume preserved ({got_volume})', got_volume == volume)
    r.check(f'{label}: times_completed is {count} ({got_count})', got_count == count)
    return got_volume, got_count


def main():
    r = Reporter('R1-BOR-SRAM-V2', kind='GATE')
    if os.path.isfile(SRM):
        os.remove(SRM)

    # Fresh invalid/blank SRAM: production Options_Init creates v2 defaults.
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(60)
        check_loaded(r, m, 'fresh boot', DEFAULT_VOLUME, 0)
    with open(SRM, 'rb') as f:
        fresh = f.read(8)
    r.check('fresh save writes v2 header and zero count',
            fresh[0:2] == MAGIC and fresh[2] == VERSION and
            fresh[3] == DEFAULT_VOLUME and fresh[4:8] == b'\0\0\0\0')

    # Valid pre-R1 image: production migration retains volume and writes v2.
    migrated_volume = 37
    write_srm(1, migrated_volume)
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(60)
        check_loaded(r, m, 'v1 migration', migrated_volume, 0)
    with open(SRM, 'rb') as f:
        migrated = f.read(8)
    r.check('v1 migration persists v2 count-zero record',
            migrated[2] == VERSION and migrated[3] == migrated_volume and
            migrated[4:8] == b'\0\0\0\0')

    # Process 1: real final campaign-end handler credits 0 -> 1 and saves.
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(60)
        setup_final_clear(m)
        r.check('real BOR campaign end credits once (0 -> 1)',
                u32(m, TIMES) == 1 and u8(m, BOR_SET_CREDITED) == 1)
        before = u32(m, TIMES)
        setup_final_clear(m, new_run=False)
        r.check('repeated campaign-end processing remains exactly once',
                u32(m, TIMES) == before == 1)
    with open(SRM, 'rb') as f:
        credited = f.read(8)
    r.check('SRAM bytes encode count 1 and retain volume',
            credited[3] == migrated_volume and credited[4:8] == b'\x01\0\0\0')

    # Process 2: fresh process reloads the saved count, then a new run's
    # cleared latch allows the genuine production path to credit 1 -> 2.
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(60)
        check_loaded(r, m, 'process restart', migrated_volume, 1)
        r.check('Bonus unlocks from persisted count but remains unavailable',
                u32(m, TIMES) >= 1)
        setup_final_clear(m)
        r.check('new run credits counter 1 -> 2',
                u32(m, TIMES) == 2 and u8(m, BOR_SET_CREDITED) == 1)
    with open(SRM, 'rb') as f:
        final = f.read(8)
    r.check('final SRAM bytes encode count 2 and retain volume',
            final[3] == migrated_volume and final[4:8] == b'\x02\0\0\0')
    r.finish()


if __name__ == '__main__':
    main()
