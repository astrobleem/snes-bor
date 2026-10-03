"""S8 source/table and assembled-code checks. Does not start an emulator.

Run: python -m unittest discover -s tools/verify -p test_hud_opponent.py -v
Generated assembly fixtures live only in a temporary directory. The existing
main.sym supplies external ABI constants. The full Normal table is generated
in isolation; missing shared spawn files get size-only queue stubs for the
generator's alignment check. These stubs are NOT spawn/runtime validation.
"""
import os
import ast
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/bor_compile'), str(ROOT / 'tools/audio')]
from compiler import Source, model_catalog, key, project, stage
from shipped_content import ROSTER_CONFIGS, STAGE_CONFIGS
from generate_environment import generate
from queue_abi import RECORD_SIZE
from generate_hud_names import render as render_names, family_sources


def symbols(path):
    return {name: int(bank + addr, 16) for bank, addr, name in
            re.findall(r'^([0-9A-Fa-f]{2}):([0-9A-Fa-f]{4,6}) (\S+)$',
                       path.read_text(), re.M)}


def pc(address):
    return (address >> 16) * 0x8000 + (address & 0x7fff)


class OpponentHudTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='bor-s8-hud-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.folder = Path(cls.temp.name)
        cls.boss = (ROOT / 'src/core/hud_boss.pasm').read_text()
        # Text relocation has its own equivalence/ABI test; not this fixture.
        cls.boss = cls.boss.replace('.include "hud_text_banked.pasm"', '')
        cls.opponent = (ROOT / 'src/core/hud_opponent.pasm').read_text()
        cls.names, cls.name_rows = render_names(ROSTER_CONFIGS, family_sources(STAGE_CONFIGS))
        cls.host = (ROOT / 'src/core/hud_opponent_host.pasm').read_text()
        cls.opponent = cls.opponent.replace(
            '.include "../generated/hud_opponent_names.pasm"', cls.names).replace(
            '.include "hud_opponent_host.pasm"', cls.host)
        cls.source = Source(ROOT / 'Beats of Rage Original [v.3.0 Build 4086].pak')
        configs = []
        for index, config in enumerate(STAGE_CONFIGS):
            config = dict(config)
            if not (ROOT / config['spawn']).exists():
                ir = stage(cls.source, config['source_level'])
                stub = cls.folder / f'queue-shape-only-{index}.bin'
                stub.write_bytes(bytes((len(ir.queue) + len(ir.environment.get('hole', [])))
                                       * RECORD_SIZE))
                config['spawn'] = str(stub)
            configs.append(config)
        generated = cls.folder / 'full-normal-aliases.pasm'
        generate(configs, generated)
        cls.aliases = generated.read_text()
        cls.rom, cls.sym = cls.assemble('current', cls.boss.replace(
            '.include "hud_opponent.pasm"', cls.opponent))

    @classmethod
    def assemble(cls, name, body, origin=0x8000):
        fixture = cls.folder / (name + '.pasm')
        texts = body + '\n' + cls.aliases
        definitions = set(re.findall(r'^(\w+)\s*[:=]', texts, re.M))
        tokens = set(re.findall(r'\b[A-Za-z_]\w*\b', texts))
        externals = symbols(ROOT / 'src/main.sym')
        prelude = '.snes\n' + '\n'.join(
            f'{name} = ${value:X}' for name, value in externals.items()
            if name not in definitions and name in tokens)
        fixture.write_text(prelude + f'\n.bank 5\n.org ${origin:X}\n' + body
                           + '\n.bank 13\n.org $8000\n' + cls.aliases, encoding='utf-8')
        binary, sym = fixture.with_suffix('.bin'), fixture.with_suffix('.sym')
        dll = os.environ.get('POPPY_DLL',
            'E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll')
        result = subprocess.run([os.environ.get('DOTNET', 'dotnet'), dll, str(fixture),
                                 '-o', str(binary), '-s', str(sym), '--no-pansy'],
                                capture_output=True, text=True)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        return binary.read_bytes(), symbols(sym)

    def cstring(self, address):
        start = pc(address)
        return self.rom[start:self.rom.index(0, start)].decode('latin1')

    def test_all_bor_model_fallbacks_match_source_and_runtime_indices(self):
        catalog = model_catalog(self.source)
        self.assertEqual(self.sym['HudOpponent_ModelCount'], len(ROSTER_CONFIGS))
        for index, config in enumerate(ROSTER_CONFIGS):
            if config['family'] != 'bor-original':
                continue
            prefix = key(config['source_character'])
            matches = [m for m in catalog.values()
                       if key(m['source_path']).removesuffix('.txt') == prefix
                       or key(m['source_path']).rsplit('/', 1)[0] == prefix]
            self.assertEqual(len(matches), 1, config)
            ptr = pc(self.sym['HudOpponent_ModelPtrs']) + index * 2
            address = 0x050000 | int.from_bytes(self.rom[ptr:ptr+2], 'little')
            self.assertEqual(self.cstring(address), matches[0]['entity']['name'][:20])

    def test_normal_100_alias_assignments_reach_actual_rom_strings(self):
        normal = next(s for s in project(self.source).sets if s.name == 'Normal')
        authored = []
        # StageEnv records key physical stage plus full queue ordinal.
        record = pc(self.sym['StageEnv_AliasRecords'])
        table = {}
        for i in range(self.sym['StageEnv_AliasRecordCount']):
            row = self.rom[record+i*4:record+i*4+4]
            table[tuple(row[:2])] = int.from_bytes(row[2:], 'little')
        for config_index, config in enumerate(STAGE_CONFIGS):
            if config['family'] != 'bor-original':
                continue
            if not any(key(e.source_path) == key(config['source_level']) for e in normal.entries
                       if e.kind == 'STAGE'):
                continue
            ir = stage(self.source, config['source_level'])
            prefix = len(ir.environment.get('hole', []))
            for queue_index, event in enumerate(ir.queue):
                if event.kind != 'spawn' or not event.alias:
                    continue
                alias_id = table[config_index, queue_index + prefix]
                ptr = pc(self.sym['StageEnv_AliasNamePtrs']) + alias_id * 2
                address = 0x0D0000 | int.from_bytes(self.rom[ptr:ptr+2], 'little')
                self.assertEqual(self.cstring(address), event.alias[:20])
                authored.append(event.alias)
        self.assertEqual(len(authored), 100)

    def test_long_reads_dma_addresses_and_rom_budget(self):
        code = self.rom[pc(self.sym['HudOpponent_Row']):pc(self.sym['HudOpponent_ModelPtrs'])]
        for address in (0x0D0000, 0x050000, self.sym['StageEnv_AliasId'],
                        self.sym['StageEnv_AliasNamePtrs'], self.sym['HudOpponent_ModelPtrs'],
                        0x7E0A00 + self.sym['CHAR_ROSTER_INDEX']):
            self.assertIn(b'\xbf' + address.to_bytes(3, 'little'), code)
        self.assertIn(b'\x69\x10\x5a', code)  # low-word staging address immediate
        self.assertLess(self.sym['HudOpponentHost_End'] & 0xffff, 0x10000)
        self.assertEqual(self.sym['HudOpponent_Rows'], 0x7E5A10)
        self.assertEqual(self.sym['HudOpponent_End'], 0x7E5AD0)
        # Every alias can be addressed: the bound is derived from the linked
        # table, including its null entry, rather than an 8-bit/hardcoded cap.
        count = (self.sym['StageEnv_AliasName1'] - self.sym['StageEnv_AliasNamePtrs']) // 2
        self.assertIn(b'\xc9' + count.to_bytes(2, 'little'), code)

    def test_generated_names_reproduce_and_follow_roster_reordering(self):
        self.assertEqual((ROOT / 'src/generated/hud_opponent_names.pasm').read_text(), self.names)
        _, reversed_rows = render_names(list(reversed(ROSTER_CONFIGS)), family_sources(STAGE_CONFIGS))
        self.assertEqual([r['display_name'] for r in reversed_rows],
                         [r['display_name'] for r in reversed(self.name_rows)])
        with self.assertRaisesRegex(ValueError, 'HUD_NAME_IDENTITY'):
            render_names([dict(ROSTER_CONFIGS[0], source_character='missing/model')],
                         family_sources(STAGE_CONFIGS))
        with self.assertRaisesRegex(ValueError, 'HUD_NAME_ROSTER_CAPACITY'):
            render_names(ROSTER_CONFIGS * 6, family_sources(STAGE_CONFIGS))

    def test_native_hook_contracts_are_connected_and_store_is_same_size(self):
        main = (ROOT / 'src/main.pasm').read_text()
        native = (ROOT / 'src/core/vm/vm_native_engine.pasm').read_text()
        actor = (ROOT / 'src/core/actor_behavior.pasm').read_text()
        self.assertIn('Character_HitApply_VsPlayer__hp_ok:\n    jsl HudOpponentHost_StorePlayerHp', main)
        self.assertIn('Character_HitApply__ApplyDamage:\n.a16\n.i16\n    jsl HudOpponentHost_VictimX', native)
        self.assertIn('Character_HitApply__TryGrab__do:\n.a8\n    jsl HudOpponentHost_Grab', native)
        self.assertIn('Spawn_ResetKnockdownFall:\n.a16\n.i16\n    jsl HudOpponentHost_RetireX', native)
        self.assertIn('ActorBehavior_RestoreRoster:\n    jsl HudOpponent_Reset', actor)
        self.assertIn('    jsl HudOpponentHost_RetireX\nActorBehavior_Save__alive:', actor)
        start = pc(self.sym['HudOpponentHost_StorePlayerHp'])
        self.assertEqual(self.rom[start:start+4],
                         b'\x9f' + self.sym['PlayerEntity_Hp'].to_bytes(3, 'little'))
        self.assertEqual(self.rom[start+4:start+8],
                         b'\x5c' + self.sym['HudOpponentHost_VictimX'].to_bytes(3, 'little'))
        # The actual P2 bridge aliases standalone globals, not the actor DP.
        bridge = (ROOT / 'src/core/player2_context.pasm').read_text().split(
            'G13_Player2_ContextEnter:', 1)[1].split('G13_Player2_ContextExit:', 1)[0]
        instructions = '\n'.join(line.split(';')[0] for line in bridge.splitlines())
        self.assertNotRegex(instructions, r'\b(?:tcd|pld)\b')
        offsets = pc(self.sym['HudOpponentHost_SlotOffsets'])
        self.assertEqual([int.from_bytes(self.rom[offsets+i*2:offsets+i*2+2], 'little')
                          for i in range(6)], [i*self.sym['CHAR_ZP_LEN'] for i in range(6)])

    def test_native_callbacks_assemble_against_real_host_labels(self):
        native = (ROOT / 'src/core/vm/vm_native_engine.pasm').read_text()
        body = self.boss.replace('.include "hud_opponent.pasm"', self.opponent)
        rom, sym = self.assemble('native_hooks', body + '\n.bank 12\n.org $8000\n'
                                 + native + '\nHudNativeFixture_End:\n')
        for caller, target in [('Character_HitApply__ApplyDamage', 'HudOpponentHost_VictimX'),
                               ('Character_HitApply__TryGrab__do', 'HudOpponentHost_Grab'),
                               ('Spawn_ResetKnockdownFall', 'HudOpponentHost_RetireX')]:
            start = pc(sym[caller])
            self.assertEqual(rom[start:start+4], b'\x22' + sym[target].to_bytes(3, 'little'))
        self.assertEqual(sym['HudNativeFixture_End'] >> 16, 12)

    def test_prepared_probe_symbol_contract_and_write_boundary(self):
        import game_s8_opponent_hud as probe
        tree = ast.parse((ROOT / 'tools/verify/game_s8_opponent_hud.py').read_text())
        required = {n.slice.value for n in ast.walk(tree) if isinstance(n, ast.Subscript)
                    and isinstance(n.value, ast.Name) and n.value.id in ('s', 'sym')
                    and isinstance(n.slice, ast.Constant) and isinstance(n.slice.value, str)
                    and n.slice.value[0].isupper()}
        from _harness import pasm_constant_in
        all_symbols = symbols(ROOT / 'src/main.sym') | self.sym
        for name in ('S6Host_HitEvents', 'S6Host_FrameEvents'):
            all_symbols[name] = pasm_constant_in('src/core/actor_source_host.pasm', name)
        self.assertFalse(required - all_symbols.keys(), required - all_symbols.keys())
        class NoWrites:
            def write_u8(self, *args):
                raise AssertionError('unexpected emulator write')
            write_u16 = write_u8
        p = probe.Probe(NoWrites(), all_symbols, {}, dict(fixture_writes=[]))
        for address in (self.sym['PlayerEntity_Hp'], self.sym['HudOpponent_Targets'],
                        self.sym['StageEnv_AliasId'], all_symbols['Game_CampaignId'],
                        all_symbols['Game_CampaignOrdinal'], all_symbols['Stage_LoadPending']):
            with self.assertRaisesRegex(AssertionError, 'non-fixture write'):
                p.fixture_write(address, 0, 1, 'must reject')
        for name in ('Game_State', 'Game_StatePrev'):
            with self.assertRaisesRegex(AssertionError, 'non-fixture write'):
                p.fixture_write(all_symbols[name], 0, 2, 'must reject')

    def test_probe_candidate_paths_never_fall_back_to_distribution(self):
        import game_s8_opponent_hud as probe
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, 'explicit BOR_TEST_ROM'):
                probe.candidate_paths(ROOT / 'src/main.sym')
        # Real harness resolver, temporary artifacts, no emulator session.
        rom = self.folder / 'candidate.sfc'
        msu = rom.with_suffix('.msu')
        rom.write_bytes(b'candidate rom')
        msu.write_bytes(b'candidate msu')
        with patch.dict(os.environ, {'BOR_TEST_ROM': str(rom)}):
            paths = probe.candidate_paths(ROOT / 'src/main.sym')
        self.assertEqual(paths['rom'], rom.resolve())
        self.assertEqual(paths['msu'], msu.resolve())
        self.assertEqual(probe.sha(paths['rom']), probe.sha(rom))

    def test_probe_death_attempt_preserves_phase_and_total_deadline(self):
        import game_s8_opponent_hud as probe
        class Controls:
            BTN_RIGHT, BTN_Y = 1, 2
        for start, expected_end in ((550, 850), (1108, 1158)):
            p = probe.Probe(Controls(), {'CHAR_ZP_LEN': 133, 'GET_MOVE_VARIANT': 10},
                            {}, {'samples': []})
            p.frame, p.combat_deadline, p.slot = start, 1158, 3
            observed = []
            def snapshot():
                snap = {'actors': [dict(hp=8, hit_stun=0, grabbed_by=255,
                                       grab_target=255, selected=0, attack_variant=0,
                                       facing_left=0)]*6,
                        'targets': [400, 400],
                        'inputs': [dict(press=0, trigger=0x4000)]*2}
                p.report['samples'].append(snap)
                return snap
            def step(buttons=0, port=0):
                self.assertLess(p.frame, p.combat_deadline)
                p.frame += 1
                observed.append((p.frame, buttons, port))
                return snapshot()
            p.snapshot, p.step = snapshot, step
            p.isolate = lambda *args, **kwargs: None
            p.require_identity = lambda snap: None
            with self.assertRaisesRegex(AssertionError,
                    'native_death_p2_attempt_1: P2 no additional native damage'):
                p.hit_and_name(1, budget=300, phase='native_death_p2_attempt_1')
            self.assertEqual(p.frame, expected_end)
            self.assertEqual(p.phase, 'native_death_p2_attempt_1')
            self.assertEqual(p.combat_deadline, 1158)
            self.assertTrue(all(port == 1 for _, buttons, port in observed if buttons))
        with self.assertRaisesRegex(AssertionError, 'no remaining native combat budget'):
            p.hit_and_name(1, phase='native_death_p2_attempt_2')

    def test_probe_holds_until_game_samples_edge_not_just_one_field(self):
        import game_s8_opponent_hud as probe
        p = probe.Probe(None, {}, {}, {})
        delivered = []
        def step(buttons=0, port=0):
            p.frame += 1
            delivered.append((buttons, port))
            return {'inputs': [dict(press=0, trigger=0),
                               dict(press=0x4000 if p.frame >= 4 else 0,
                                    trigger=0x4000 if p.frame == 4 else 0)]}
        p.step = step
        snap = p.observed_press(1, 2048, 0x4000, 10)
        self.assertEqual(p.frame, 4)
        self.assertEqual(delivered, [(2048, 1)] * 4)
        self.assertEqual(snap['inputs'][1]['trigger'], 0x4000)

    def test_probe_font_requires_live_vram_and_cgram_match_candidate(self):
        import game_s8_opponent_hud as probe
        sym = dict(FONT_TILES_VRAM_WORD=0x5900, Font_TilesData=0x8000,
                   FONT_TILE_BYTES=32, FONT_CGRAM_BYTE_ADDR=8,
                   Font_PaletteData=0x8020, FONT_PALETTE_BYTES=8)
        rom = bytes(range(40))
        p = probe.Probe(None, sym, {}, {})
        reads = []
        def read(address, length, kind):
            reads.append((address, length, kind))
            return rom[:32] if kind == 'snesVideoRam' else rom[32:]
        p.read = read
        p.verify_font(rom)
        self.assertEqual(reads, [(0xB200, 32, 'snesVideoRam'), (8, 8, 'snesCgRam')])
        p.read = lambda address, length, kind: rom[:32] if kind == 'snesVideoRam' else bytes(8)
        with self.assertRaisesRegex(AssertionError, 'live font_palette differs'):
            p.verify_font(rom)

    def test_probe_retirement_waits_for_terminal_unlink_and_real_rows(self):
        import game_s8_opponent_hud as probe
        for mode in ('normal', 'stall', 'uncleared'):
            p = probe.Probe(None, {'DEATH_BLINK_FRAMES': 120}, {}, {})
            p.slot = 0
            p.isolate = lambda: None
            p.require_identity = lambda snap: None
            def snapshot():
                f = p.frame if mode != 'stall' else 0
                timer = 0 if f < 200 else (121-(f-200)//2 if f < 442 else 255)
                actor = dict(hp=0, fall_count=5, fall_delay=20, fall_timer=timer,
                             animation_frame=min(4, f//40), tick_counter=20-(f//2)%20)
                return dict(actors=[actor], targets=[0, 0] if f >= 444 else [1, 1],
                            vram=[[0]*32]*2 if f >= 446 and mode != 'uncleared' else [[1]*32]*2)
            def step():
                p.frame += 1
                return snapshot()
            p.snapshot, p.step = snapshot, step
            if mode == 'normal':
                result = p.await_retirement()
                self.assertEqual(p.frame, 446)
                self.assertEqual(result['actors'][0]['fall_timer'], 255)
                self.assertEqual(result['targets'], [0, 0])
            elif mode == 'stall':
                with self.assertRaisesRegex(AssertionError, 'native_removal_fall: native progress deadline'):
                    p.await_retirement()
                self.assertEqual(p.frame, 64)
            else:
                with self.assertRaisesRegex(AssertionError, 'terminal FF reached but handles/VRAM not cleared'):
                    p.await_retirement()
                self.assertEqual(p.frame, 506)

    def test_easy_body_is_byte_identical_after_relocation(self):
        old = subprocess.run(['git', 'show', 'HEAD:src/core/hud_boss.pasm'],
                             cwd=ROOT, capture_output=True, text=True, check=True).stdout
        # Align the old first boss lookup with the unchanged legacy branch.
        origin = (self.sym['Hud_Play__boss_bar_legacy'] & 0xffff) - 2
        rom, sym = self.assemble('easy_baseline', old, origin)
        start = pc(sym['Hud_Play__boss_bar']) + 2
        end = pc(self.sym['HudOpponent_Reset'])
        self.assertEqual(rom[start:end], self.rom[start:end])


if __name__ == '__main__':
    unittest.main()
