"""Bounded organic fixture recorder. Run only after main grants GUI ownership.

No force-spawn, register injection, engine memory writes, save-state loading,
production build, or exact/full actor certificate. --check-only never launches.
"""
import argparse
import json
from pathlib import Path
import shutil
import struct
import traceback
import subprocess
import time
from types import SimpleNamespace
from unittest.mock import patch

from actor_behavior_fixture import ROOT, file_sha, symbols, offset


def check_fixture(folder):
    manifest = json.loads((folder / 'fixture.json').read_text())
    assert manifest['policy'] == 'EXPERIMENTAL_NONE_WALK'
    assert manifest['compatibility_permission'] is False
    assert manifest['full_actor_certificate'] == 'BLOCKED'
    assert manifest['identity'] != manifest['source_identity']
    assert file_sha(folder / 'bor.sfc') == manifest['fixture_rom_sha256']
    assert file_sha(folder / 'bor.msu') == manifest['fixture_msu_sha256']
    assert file_sha(folder / 'actor.bin') == manifest['actor_sha256']
    syms = symbols(folder / 'bor.sym')
    rom = (folder / 'bor.sfc').read_bytes()
    flags_at = offset(syms['ActorBehavior_ModelFlags'])
    flags = rom[flags_at:flags_at + 256]
    assert flags.count(1) == 1 and sum(flags) == 1
    assert flags[manifest['catalog_slot']] == 1
    assert sum(rom) & 65535 == struct.unpack_from('<H', rom, 0x7FDE)[0]
    with (folder / 'bor.msu').open('rb') as f:
        f.seek(manifest['actor_offset'])
        assert f.read(manifest['actor_size']) == (folder / 'actor.bin').read_bytes()
        f.seek(manifest['queue_offset'])
        assert f.read(30) == (folder / 'spawn_table.bin').read_bytes()
        f.seek(manifest['catalog_record_offset'] + 8)
        assert struct.unpack('<I', f.read(4))[0] == manifest['actor_offset']
        f.seek(manifest['stage_queue_fields'])
        assert struct.unpack('<IH', f.read(6)) == (manifest['queue_offset'], 3)
    return manifest, syms


def run(folder, frames, runtime_name='runtime', diagnostic_objsel=False):
    manifest, syms = check_fixture(folder)
    # Importing the established helpers does not open any session. This sole
    # constructor uses the exact fixture ROM and a dedicated port.
    from _harness import (McpSession, MESEN_EXE, _free_tcp_port, read_block,
                          run_frames_exact, exact_input_edge, Reporter)
    from game_bor_startup_select import cold_to_title, title_to_charselect, wait_state, PLAYING
    assert Path(runtime_name).name == runtime_name, 'runtime name must be one directory component'
    out = folder / runtime_name
    assert not out.exists(), 'preserve prior runtime evidence; use a fresh fixture copy'
    out.mkdir()
    ranges = [(syms['OopObjRam'], 6 * syms['CHAR_ZP_LEN']),
              (syms['StageEnv_Actors'], 6 * syms['CHAR_ZP_LEN']),
              (syms['Game_StageIndex'], 2), (syms['Spawn_Index'], 2),
              (syms['Screen_PosX'], 2), (syms['Nmi_FrameCounter'], 2),
              (syms['Nmi_ObjSel'], 1)]
    lua = out / 'commit.lua'
    template = Path(__file__).with_name('actor_behavior_commit.lua').read_text()
    lua.write_text(template.replace('@DIAGNOSTIC_OBJSEL@', 'true' if diagnostic_objsel else 'false')
        .replace('@NMI_FRAME@', str(syms['Nmi_FrameCounter']))
        .replace('@OBJ_SHADOW_OFFSET@', str(syms['Nmi_ObjSel'] - 0x7E0000))
        .replace('@DONE_OFFSET@', str(offset(syms['Core_Oop_Play__done']))).replace(
        '@RANGES@', ','.join('{%d,%d}' % r for r in ranges)))

    class CommitSession(McpSession):
        def __enter__(self):
            # Session has no extra-CLI-arguments option. Locally adapt only its
            # launcher; retain its validation, connection, stderr drain, teardown.
            import mesen_mcp.session as session_module
            def launch(argv, **kwargs):
                return subprocess.Popen([*argv, str(lua)], **kwargs)
            proxy = SimpleNamespace(Popen=launch, DEVNULL=subprocess.DEVNULL,
                                    PIPE=subprocess.PIPE)
            with patch.object(session_module, 'subprocess', proxy):
                return super().__enter__()

    def latest_commit(m):
        # Callback emits a whole line synchronously; transport is asynchronous.
        # This wait drains host output only, never advances emulated time.
        deadline = time.monotonic() + 0.25
        while True:
            lines = [line for line in list(m._stderr_lines) if line.startswith(b'S5COMMIT|')]
            if lines:
                parts = lines[-1].decode('ascii').strip().split('|')
                assert len(parts) == 4 + len(ranges)
                # Callback matches physical ROM, independent of CPU bank mirrors.
                assert offset(int(parts[2])) == offset(syms['Core_Oop_Play__done'])
                ram = bytearray(0x6000)
                for (address, length), data in zip(ranges, parts[3:]):
                    block = bytes.fromhex(data)
                    assert len(block) == length
                    p = address - 0x7E0000
                    assert 0 <= p <= len(ram) - length
                    ram[p:p + length] = block
                ppu_registers = dict(item.split('=', 1) for item in parts[-1].split(';') if item)
                assert ppu_registers, 'Lua serialized PPU diagnostic keys absent'
                return int(parts[1]), bytes(ram), ppu_registers
            if time.monotonic() >= deadline:
                return None
            time.sleep(0.005)
    report = {'status': 'FAIL', 'scope': 'organic parameterized driver only',
              'full_actor_certificate': 'BLOCKED', 'blocked': manifest['blocked'],
              'rom_sha256': manifest['fixture_rom_sha256'],
              'msu_sha256': manifest['fixture_msu_sha256'],
              'checks': [], 'trace': [], 'screenshots': []}

    def require(name, condition):
        report['checks'].append({'name': name, 'passed': bool(condition)})
        if not condition:
            raise AssertionError(name)

    def screenshot(m, name):
        result = m.take_screenshot()
        report['screenshots'].append({'name': name, 'result': result})
        for key in ('path', 'filePath', 'file_path'):
            path = result.get(key) if isinstance(result, dict) else None
            if path and Path(path).is_file():
                shutil.copyfile(path, out / (name + '.png'))
                break

    try:
        with CommitSession(rom=str(folder / 'bor.sfc'), mesen=MESEN_EXE,
                        boot_wait=2.0, port=_free_tcp_port(), stderr_log=out / 'mesen-stderr.log') as m:
            startup = Reporter('ORGANIC-DRIFT-STARTUP', kind='EXPERIMENT')
            # CLI LoadRom already cold-boots a new process. A second power
            # cycle destroys the CLI-loaded Lua debugger context in Mesen.
            # Reuse all startup assertions/input, but retain that initial load.
            with patch.object(m, 'reset_emulator', lambda: {'reset': False, 'fresh_process_load': True}):
                cold_to_title(m, startup)
            report['startup_policy'] = 'fresh CLI cold ROM load; no second power cycle that discards Lua'
            require('cold startup uses real intro/title', all(ok for _, ok in startup.results))
            title_to_charselect(m, False)
            exact_input_edge(m, m.BTN_START, 1, port=0)
            require('normal 1P/Easy/default selection reaches PLAYING', wait_state(m, PLAYING, 300))
            # Read the immutable loaded queue independently of actor counters.
            queue_ram = read_block(m, syms['SpawnTable_Wram'], 64)
            require('Stage_Load/Spawn_Init loaded exact fixture queue',
                    bytes(queue_ram[:30]) == (folder / 'spawn_table.bin').read_bytes())
            seen = {}
            transitions = 0
            signs = set()
            screenshot_taken = False
            uploaded_screenshot_taken = False
            actor_blob = (folder / 'actor.bin').read_bytes()
            # Fresh source encoding: palette32 + one idle768 + eight walk768.
            walk_tiles = [actor_blob[800 + i * 768:800 + (i + 1) * 768] for i in range(8)]
            assert all(len(tile) == 768 for tile in walk_tiles)
            last_sequence = 0
            stale_frames = 0
            for frame in range(frames):
                # Installed Mesen lacks get_cpu_state. Optional asynchronous
                # CPU diagnostics are omitted; all semantic reads still come
                # exclusively from the mandatory synchronous Lua callback.
                commit = latest_commit(m)
                if commit is None or commit[0] == last_sequence:
                    stale_frames += 1
                    require('synchronous commit snapshot progresses within four frames', stale_frames <= 4)
                    run_frames_exact(m, 1)
                    continue
                sequence, ram, ppu_registers = commit
                require('monotonic synchronous callback sequence', sequence > last_sequence)
                last_sequence, stale_frames = sequence, 0
                def integer(address, size=1, signed=False):
                    p = address - 0x7E0000
                    assert 0 <= p <= len(ram) - size
                    return int.from_bytes(ram[p:p + size], 'little', signed=signed)
                def named(name, size=1):
                    return integer(syms[name], size)
                require('fixture stage remains loaded', named('Game_StageIndex') == manifest['stage_index'])
                require('future queue record keeps scene open', named('Spawn_Index') <= 2 and named('Spawn_Count') == 3)
                camera = named('Screen_PosX', 2)
                require('bounded camera held at source origin', camera == 0)
                rows = []
                # Append before assertions so the failing actor is evidence too.
                report['trace'].append({'frame': frame, 'nmi': named('Nmi_FrameCounter', 2),
                                        'queue_index': named('Spawn_Index'),
                                        'snapshot_phase': 'synchronous Core_Oop_Play__done Lua callback',
                                        'serialized_ppu_registers': ppu_registers,
                                        'nmi_objsel_shadow': named('Nmi_ObjSel'),
                                        'sequence': sequence, 'actors': rows})
                for slot in range(1, 6):
                    stride = syms['CHAR_ZP_LEN'] * slot
                    dp = syms['OopObjRam'] + stride
                    if integer(dp + syms['CHAR_INPUT_DRIVEN']) != 7:
                        continue
                    state = syms['ActorBehavior_State'] + stride
                    row = {'slot': slot, 'observed_nmi': named('Nmi_FrameCounter', 2), 'x': integer(state, 4, True),
                           'velocity': integer(state + 4, 4, True),
                           'advancex': integer(state + 8, 4, True),
                           'authored_x': integer(state + 16, 2, True),
                           'alive': integer(syms['ActorBehavior_Alive'] + stride, 2),
                           'ticks200': integer(syms['ActorBehavior_Ticks'] + stride, 4),
                           'sample': integer(state + 30, 2),
                           'sample_count': integer(syms['ActorBehavior_Samples'] + stride, 2),
                           'source_health': integer(syms['ActorBehavior_SourceHealth'] + stride, 2),
                           'fault': integer(syms['ActorBehavior_Fault'] + stride, 2),
                           'target_x': integer(dp + syms['CHAR_POS_X'], 2, True),
                           'facing_left': integer(dp + syms['CHAR_FACING_LEFT']),
                           'legacy_hp': integer(dp + syms['CHAR_HP']),
                           'pickup': integer(dp + syms['CHAR_PICKUP_TYPE']),
                           'stun': integer(dp + syms['CHAR_HIT_STUN']),
                           'selected': integer(dp + syms['CHAR_SELECTED']),
                           'frame_index': integer(dp + syms['CHAR_FRAME_INDEX']),
                           'tile_column': integer(dp + syms['CHAR_TILE_COLUMN']),
                           'palette_slot': integer(dp + syms['CHAR_PALETTE_SLOT']),
                           'roster': integer(dp + syms['CHAR_ROSTER_INDEX'])}
                    rows.append(row)
                    require('real catalog identity bound', row['roster'] == manifest['catalog_slot'])
                    require('source health retained separately', row['source_health'] == manifest['source_health'])
                    require('combat/pickup/stun exclusion and valid binding',
                            row['legacy_hp'] == row['pickup'] == row['stun'] == row['fault'] == 0)
                    require('one speed sample per organic spawn', row['sample_count'] == 1)
                    require('documented experimental random domain', 0 <= row['sample'] < 7680 and row['sample'] % 30 == 0)
                    magnitude = manifest['speed_units'] + row['sample']
                    sign = 1 if row['authored_x'] < 160 else -1
                    signs.add(sign)
                    require('authored X selects velocity sign', row['velocity'] == sign * magnitude)
                    require('flip is independent of velocity', row['facing_left'] == (1 if sign == 1 else 0))
                    require('fraction retained and projected by signed floor', row['target_x'] == row['x'] // 3200)
                    require('walk selected by semantic driver', row['selected'] == 1)
                    previous = seen.get(slot)
                    if previous:
                        require('sample/velocity stable across ticks',
                                row['sample'] == previous['sample'] and row['velocity'] == previous['velocity'])
                        elapsed = (row['observed_nmi'] - previous['observed_nmi']) & 65535
                        require('bounded completed-update observation gap', elapsed <= 8)
                        require('monotonic bounded source scheduler',
                                0 <= row['ticks200'] - previous['ticks200'] <= 4 * elapsed + 4)
                        x, alive = previous['x'], bool(previous['alive'])
                        for tick in range(previous['ticks200'] + 1, row['ticks200'] + 1):
                            if tick % 2 or not alive:
                                continue
                            if x < row['advancex'] - 80 * 2560 or x > row['advancex'] + 400 * 2560:
                                alive = False
                            else:
                                x += previous['velocity']
                        require('source bounds precede parameterized motion', x == row['x'] and int(alive) == row['alive'])
                        transitions += row['x'] != previous['x']
                    seen[slot] = row
                if len(seen) == 2 and not screenshot_taken:
                    screenshot(m, 'organic-spawn')
                    screenshot_taken = True
                if (frame >= 20 and not uploaded_screenshot_taken and len(rows) == 2
                        and all(r['alive'] and 0 <= r['target_x'] < 256
                                and r['frame_index'] != 255 for r in rows)):
                    # Hardware VRAM evidence, independent of animation counters.
                    # Matching any authored walk frame proves upload, not exact
                    # pose timing/alignment with the earlier committed CPU row.
                    vram = bytes(read_block(m, 0x8000, 0x2000, mem_type='snesVideoRam'))
                    matches = []
                    for r in rows:
                        column = r['tile_column'] * 128
                        tiles = b''.join(vram[column + y * 512:column + y * 512 + 128]
                                         for y in range(6))
                        matches.append([i for i, expected in enumerate(walk_tiles) if tiles == expected])
                    report['upload_probe'] = {'frame': frame, 'matching_source_walk_frames': matches}
                    if all(matches):
                        require('later active actors retain own fixture catalog identity',
                                all(r['roster'] == manifest['catalog_slot'] for r in rows))
                        oam = bytes(read_block(m, 0, 544, mem_type='snesSpriteRam'))
                        cgram = bytes(read_block(m, 0, 512, mem_type='snesCgRam'))
                        # Preserve hardware evidence before optional SDK calls.
                        (out / 'active-upload-oam.bin').write_bytes(oam)
                        (out / 'active-upload-vram.bin').write_bytes(vram)
                        (out / 'active-upload-cgram.bin').write_bytes(cgram)
                        try:
                            # McpSession.call returns the full JSON-RPC envelope;
                            # only McpSession.tool unwraps result/content.
                            catalog = m.call('tools/list', {})
                            report['diagnostic_tool_catalog'] = catalog
                            available = {tool['name'] for tool in catalog['result']['tools']}
                            ppu = (m.tool('get_ppu_state', {}) if 'get_ppu_state' in available
                                   else {'unavailable': 'get_ppu_state', 'get_state': m.get_state()})
                        except Exception:
                            ppu = {'diagnostic_status': 'BLOCKED', 'error': traceback.format_exc()}
                        report['active_upload_evidence'] = {
                            'frame': frame, 'committed_actors': rows,
                            'matching_source_walk_frames': matches,
                            'hardware_oam_hex': oam.hex(),
                            'ppu_state': ppu,
                            'serialized_ppu_registers_at_commit': ppu_registers,
                            'nmi_objsel_shadow_at_commit': named('Nmi_ObjSel'),
                            'palette_bindings': [
                                {'slot': r['slot'], 'palette_slot': r['palette_slot'],
                                 'expected_base_hex': actor_blob[:32].hex(),
                                 'actual_hex': cgram[256 + r['palette_slot'] * 32:
                                                     288 + r['palette_slot'] * 32].hex(),
                                 'matches_encoded_base': cgram[256 + r['palette_slot'] * 32:
                                                               288 + r['palette_slot'] * 32] == actor_blob[:32]}
                                for r in rows],
                            'oam_entries': [list(oam[i:i + 4]) for i in range(0, 512, 4)],
                            'alignment': 'hardware captured at paused frame; CPU rows at preceding OOP commit; exact alignment unproven'}
                        screenshot(m, 'organic-active-uploaded')
                        uploaded_screenshot_taken = True
                        if diagnostic_objsel:
                            # Explicit opt-in causal experiment only. Never a
                            # production fix or unmodified-fixture acceptance.
                            report['scope'] = 'diagnostic hardware OBSEL override, not final acceptance'
                            report['objsel_ab'] = {'before_registers': ppu_registers,
                                'write_address': 0x2101, 'write_value': 0xC2,
                                'write_mechanism': 'Lua side-effect-enabled bus write at NMI>=190'}
                            require('before capture precedes diagnostic override',
                                    ppu_registers.get('ppu.oamBaseAddress') == '0')
                            for _ in range(40):
                                run_frames_exact(m, 1)
                                after = latest_commit(m)
                                if after and after[2].get('ppu.oamBaseAddress') == '16384':
                                    break
                            require('hardware OBSEL override observed', after is not None
                                    and after[2].get('ppu.oamBaseAddress') == '16384'
                                    and after[2].get('ppu.oamMode') == '6')
                            run_frames_exact(m, 2)
                            after = latest_commit(m)
                            require('post-OBSEL causal probe has synchronous snapshot', after is not None)
                            report['objsel_ab']['after_registers'] = after[2]
                            after_oam = bytes(read_block(m, 0, 544, mem_type='snesSpriteRam'))
                            (out / 'objsel-after-oam.bin').write_bytes(after_oam)
                            report['objsel_ab']['after_oam_hex'] = after_oam.hex()
                            screenshot(m, 'objsel-after-two-frames')
                            report['status'] = 'DIAGNOSTIC_OBSEL_AB_CAPTURED_NOT_ACCEPTANCE'
                            report['manual_visual_acceptance'] = 'PENDING'
                            return
                if len(seen) == 2 and all(not r['alive'] for r in seen.values()):
                    screenshot(m, 'after-removal')
                    break
                run_frames_exact(m, 1)
            require('two organically spawned directions observed', len(seen) == 2 and signs == {-1, 1})
            require('live movement measured', transitions >= 10)
            require('both source actors retire outside bounds', all(not r['alive'] for r in seen.values()))
            report['status'] = 'PASS_BOUNDED_ORGANIC_PARAMETERIZED_DRIVER'
            if diagnostic_objsel:
                require('requested OBSEL diagnostic executed', 'objsel_ab' in report)
                report['status'] = 'DIAGNOSTIC_OBSEL_AB_CAPTURED_NOT_ACCEPTANCE'
            report['resolved_scoped_proof'] = ['organic Stage_Load/queue spawn',
                'parameterized movement and signed-floor projection', 'bounds-before-motion retirement',
                'independent facing', 'one experimental speed sample', 'source health10 sidecar']
            report['blocked'] = [b for b in manifest['blocked']
                                 if b != 'runtime organic spawn/movement/removal and visual proof']
            report['blocked'] += ['exact render/CPU frame alignment', 'manual visual acceptance']
            report['active_upload_capture'] = 'CAPTURED' if uploaded_screenshot_taken else 'BLOCKED_NOT_OBSERVED'
            report['manual_visual_acceptance'] = 'PENDING'
    except Exception:
        report['error'] = traceback.format_exc()
        raise
    finally:
        (out / 'proof.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({k: report[k] for k in ('status', 'scope', 'full_actor_certificate')}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--frames', type=int, default=900)
    parser.add_argument('--runtime-name', default='runtime')
    parser.add_argument('--diagnostic-objsel-c2', action='store_true')
    args = parser.parse_args()
    folder = args.fixture.resolve()
    if args.check_only:
        check_fixture(folder)
        print('PASS_FIXTURE_BYTES_AND_BINDING; runtime NOT RUN; full actor BLOCKED')
    else:
        run(folder, args.frames, args.runtime_name, args.diagnostic_objsel_c2)


if __name__ == '__main__':
    main()
