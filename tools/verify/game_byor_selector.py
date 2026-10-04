"""Bounded real-selector/first-entry smoke for a BYOR source-world candidate."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools/audio')]


def run(candidate, player_ordinal=0, only_set=None, combat_fields=0, screenshot=None):
    import build_rom
    import _harness as h
    import game_bor_startup_select as startup
    sym = build_rom._load_poppy_symbols(str(ROOT / 'src/main.sym'))
    sym.update(build_rom._load_poppy_symbols(str(candidate / 'world.sym')))
    h.rom_path = lambda _: str(candidate / 'bor.sfc')
    # Each case starts a fresh Mesen process, matching the accepted campaign
    # harness's fresh-power-on fixture rather than issuing a second soft reset.
    h.McpSession.reset_emulator = lambda self: None
    rows = []
    for source_set, cid, source_id in (
            ('Easy', 'BOR_ORIGINAL', 0), ('Normal', 'BOR_NORMAL_1A_INTERNAL', 1),
            ('Hard', 'BOR_HARD', 2)):
        if only_set and source_set != only_set:
            continue
        row = dict(source_set=source_set, verdict='FAIL')
        rows.append(row)
        with h.open_session(__file__) as m:
            def u8(name):
                return h.read_block(m, sym[name], 32)[0]
            def u16(name):
                return int.from_bytes(bytes(h.read_block(m, sym[name], 32)[:2]), 'little')
            def wait(predicate, limit):
                for _ in range(limit):
                    if predicate():
                        return
                    h.run_frames_exact(m, 1)
                raise AssertionError('selector/first-entry timeout: ' + source_set
                    + str(dict(state=u16('Game_State'), selected=u8('BorSet_Selected'),
                               difficulty=u8('BorDifficulty_Chosen'), step=u8('CharSelect_Step'))))
            r = h.Reporter('BYOR-' + source_set, kind='GATE')
            startup.cold_to_title(m, r)
            assert all(ok for _, ok in r.results)
            h.exact_input_edge(m, m.BTN_START, 1)
            wait(lambda: u16('Game_State') == startup.CHARSELECT and u8('BorDifficulty_Chosen') == 1, 360)
            for selected in range(1, source_id + 1):
                h.run_frames_exact(m, 2)
                h.exact_input_edge(m, m.BTN_RIGHT, 1)
                wait(lambda: u8('BorSet_Selected') == selected, 120)
            h.exact_input_edge(m, m.BTN_START, 1)
            wait(lambda: u8('BorDifficulty_Chosen') == 3 and u8('CharSelect_Step') == 3, 360)
            assert u8('BorSet_Selected') == source_id
            for _ in range(player_ordinal):
                h.run_frames_exact(m, 2)
                h.exact_input_edge(m, m.BTN_RIGHT, 1)
            h.exact_input_edge(m, m.BTN_START, 1)
            wait(lambda: u16('Game_State') == startup.PLAYING, 600)
            first = build_rom.CAMPAIGN_ENTRY_MAPS[cid][0]
            assert first[0] == 'stage'
            assert u8('Game_CampaignId') == (0 if source_id == 0 else 3)
            assert u8('Game_CampaignOrdinal') == 0
            assert u16('Game_StageIndex') == first[1]
            h.run_frames_exact(m, 30)
            if combat_fields and source_id:
                samples = []
                def actors():
                    rows = []
                    for slot in range(6):
                        base = 0x7E0000 + sym['PlayerEntity_DpBase'] + slot * sym['CHAR_ZP_LEN']
                        raw = bytes(h.read_block(m, base, sym['CHAR_ZP_LEN']))
                        rows.append(dict(slot=slot, hp=raw[sym['CHAR_HP']],
                            roster=raw[sym['CHAR_ROSTER_INDEX']],
                            object_num=int.from_bytes(raw[1:3], 'little'),
                            mode=raw[sym['CHAR_INPUT_DRIVEN']],
                            x=int.from_bytes(raw[4:6], 'little', signed=True), y=raw[6]))
                    return rows
                samples.append(dict(field=-1, actors=actors()))
                for field in range(combat_fields):
                    m.hold_input(m.BTN_RIGHT | (m.BTN_Y if field % 16 < 8 else 0))
                    h.run_frames_exact(m, 1)
                    if field % 30 == 0:
                        samples.append(dict(field=field, ticks=u16('S6Game_TickCommit'),
                                            error=u16('S6Host_Error'), actors=actors(),
                                            visual_error=u8('SourceVisual_Error'),
                                            obj_status=bytes(h.read_snes_bus_block(m, 0x00213E, 32))[0]))
                m.release_input()
                row['combat_samples'] = samples
                history = {}
                damage = []
                for sample in samples:
                    for actor in sample['actors'][1:]:
                        if actor['mode'] not in (2, 4):
                            continue
                        key = (actor['slot'], actor['object_num'], actor['roster'])
                        before = history.get(key)
                        if before is not None and actor['hp'] < before:
                            damage.append(dict(field=sample['field'], identity=key,
                                               before_hp=before, after_hp=actor['hp']))
                        history[key] = actor['hp']
                row['combat_damage'] = damage
                assert damage, 'bounded attack input produced no observed enemy HP decrease'
                assert all(s.get('error', 0) == 0 for s in samples)
                if screenshot:
                    import shutil
                    # Observe a published source packet, after its shared
                    # stream fence, rather than photographing cold admission.
                    warm = 0
                    while warm < 900:
                        lease = bytes(h.read_block(m, sym['SourceVisual_State'], 192))
                        if lease[28] == 1:
                            break
                        h.run_frames_exact(m, 1)
                        warm += 1
                    row['visual_warm_fields'] = warm
                    row['visual_lease'] = lease.hex()
                    row['visual_last_error'] = u8('SourceVisual_DebugLastError')
                    row['oam_cursor'] = int.from_bytes(h.read_block(m, 0x7E53A0, 32)[:2], 'little')
                    assert lease[28] == 1, 'player source packet never became presentable'
                    h.run_frames_exact(m, 4)
                    row['oam_shadow'] = bytes(h.read_block(m, sym['Oam_Buffer'], 544)).hex()
                    row['emit_debug'] = bytes(h.read_block(m, sym['SourceVisual_DebugEmitPiece'], 64)).hex()
                    row['palette_cache'] = bytes(h.read_block(m, sym['SourceVisual_PaletteCache'], 64)).hex()
                    row['cgram'] = bytes(m.read_memory('snesCgram', 0, 512)).hex()
                    import struct
                    metadata = json.loads((candidate / 'production-runtime.json').read_text())
                    catalog_info = metadata['runtime']['source_sized_visual_catalog']
                    catalog = (candidate / 'bor.msu').read_bytes()[catalog_info['msu_offset']:]
                    _, entries, pieces, blocks, palettes, sheets, entry_bytes = struct.unpack_from('<6s6H', catalog)
                    block_table = 18 + entries * entry_bytes + pieces * 16
                    cache = bytes(h.read_block(m, sym['SourceVisual_BlockCache'], 512))
                    vram = bytes(m.read_memory('snesVideoRam', 0x8000, 16384))
                    mismatches = []
                    checked = 0
                    for slot in range(64):
                        block_id, state = struct.unpack_from('<HH', cache, slot * 8)
                        if state != 2 or not cache[slot * 8 + 4]:
                            continue
                        _, size, offset, _ = struct.unpack_from('<32sHII', catalog, block_table + block_id * 42)
                        tile = (slot // 32) * 256 + (slot % 8) * 2 + ((slot % 32) // 8) * 64
                        actual = b''.join(vram[tile * 32 + y * 512:tile * 32 + y * 512 + 64] for y in range(4))
                        checked += 1
                        if actual != catalog[offset:offset + size]:
                            mismatches.append(dict(slot=slot, block_id=block_id, size=size))
                    row['resident_block_check'] = dict(checked=checked, mismatches=mismatches)
                    assert checked and not mismatches, 'resident source blocks differ from the source catalog'
                    palette_table = block_table + blocks * 42
                    palette_cache = bytes.fromhex(row['palette_cache'])
                    cgram = bytes.fromhex(row['cgram'])
                    palette_mismatches = []
                    palette_checked = 0
                    for slot in range(8):
                        if not palette_cache[slot * 8 + 4] or not palette_cache[slot * 8 + 3]:
                            continue
                        palette_id = struct.unpack_from('<H', palette_cache, slot * 8)[0]
                        _, size, offset, _ = struct.unpack_from('<32sHII', catalog, palette_table + palette_id * 42)
                        palette_checked += 1
                        if cgram[256 + slot * 32:288 + slot * 32] != catalog[offset:offset + size]:
                            palette_mismatches.append(dict(slot=slot, palette_id=palette_id))
                    row['resident_palette_check'] = dict(checked=palette_checked, mismatches=palette_mismatches)
                    assert palette_checked and not palette_mismatches, 'resident OBJ palettes differ from the source catalog'
                    shot = m.take_screenshot()
                    screenshot.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(shot['path'], screenshot)
                    row['screenshot'] = str(screenshot)
            row.update(physical_stage=first[1], source_path=first[2],
                       selected_source_set=u8('BorSet_Selected'),
                       player_roster=h.read_block(m, sym['PlayerEntity_DpBase'] + 0x7E0000
                                                   + sym['CHAR_ROSTER_INDEX'], 32)[0],
                       host_mode=u16('S6Host_Mode'), host_error=u16('S6Host_Error'),
                       source_ticks=u16('S6Game_TickCommit'),
                       times_completed=int.from_bytes(bytes(h.read_block(m, sym['Bor_TimesCompleted'], 32)[:4]), 'little'))
            if source_id:
                assert row['host_mode'] == 1 and row['host_error'] == 0
                assert row['source_ticks'] > 0
            else:
                row.update(host_error=None, source_ticks=None)
            row['verdict'] = 'PASS'
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--player-ordinal', type=int, choices=range(4), default=0)
    parser.add_argument('--source-set', choices=('Easy', 'Normal', 'Hard'))
    parser.add_argument('--combat-fields', type=int, default=0)
    parser.add_argument('--screenshot', type=Path)
    args = parser.parse_args()
    report = dict(verdict='FAIL', scope='real selector and bounded first-entry source-world smoke')
    try:
        report['rows'] = run(args.candidate.resolve(), args.player_ordinal, args.source_set,
                             args.combat_fields, args.screenshot)
        report['rom_sha256'] = hashlib.sha256((args.candidate / 'bor.sfc').read_bytes()).hexdigest()
        report['verdict'] = 'PASS'
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    return int(report['verdict'] != 'PASS')


if __name__ == '__main__':
    raise SystemExit(main())
