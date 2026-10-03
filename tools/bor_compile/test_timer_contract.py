"""Focused S8 source/ABI/assembly checks. Never starts an emulator.

Assembler fixtures use sentinel host addresses, not claimed implementations.
They verify the real module's encoding/link requirements, not host behavior.
"""
import copy
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

import timer_contract as t

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / 'src/core/stage_timer.pasm'
HOST = ROOT / 'src/core/stage_timer_host.pasm'


class TimerContractTests(unittest.TestCase):
    def test_nominal_field_clock_partition_stalls_and_pause(self):
        clock = t.FieldClockReference()
        self.assertEqual([clock.sample(i) for i in (1, 2, 3)], [3, 3, 4])
        self.assertEqual(clock.take_gravity(), 5)
        self.assertEqual(clock.take_gravity(), 0)
        # A main-loop stall of 60 fields still accrues a whole second.
        self.assertEqual(clock.sample(63), 200)
        self.assertEqual(clock.take_gravity(), 100)
        self.assertEqual(clock.sample(123, running=False), 0)
        self.assertEqual(clock.sample(124), 3)
        self.assertEqual(clock.sample(124), 0)
        # Partition does not change either clock's cumulative result.
        for step in (1, 2, 7, 60, 1000):
            c = t.FieldClockReference()
            total = sum(c.sample(field) for field in range(step, 6001, step))
            if 6000 % step:
                total += c.sample(6000)
            self.assertEqual((total, c.take_gravity()), (20000, 10000))

    def test_field_wrap_and_fail_closed_domains(self):
        c = t.FieldClockReference(last=65534)
        self.assertEqual(c.sample(1), 10)
        self.assertEqual(c.take_gravity(), 5)
        with self.assertRaisesRegex(ValueError, 'AMBIGUOUS'):
            c.sample(32769)
        c = t.FieldClockReference(gravity_due=65535)
        with self.assertRaisesRegex(ValueError, 'OVERFLOW'):
            c.sample(1)

    def test_timer_stall_catchup_does_not_replay_actors(self):
        clock = t.FieldClockReference()
        timer = t.TimerReference(left=7)
        self.assertTrue(timer.collect(6, 3))
        ticks = clock.sample(180)  # nominal3 seconds, no intermediate services
        self.assertEqual(ticks, 600)
        retired = []
        for _ in range(ticks):
            retired += timer.begin_tick()
            timer.end_tick()
        self.assertEqual(retired, [3])
        self.assertEqual(timer.left, 39400)
        self.assertEqual(clock.take_gravity(), 300)

    def test_pinned_source_and_reset_lifecycle(self):
        source = ROOT / 'out/bor_compile_s6/BOR.C'
        self.assertEqual(t.verify_source(source), t.SOURCE_SHA256)
        text = source.read_text()
        self.assertRegex(text, r'#define\s+GAME_SPEED\s+200')
        self.assertRegex(text, r'#define\s+COUNTER_SPEED\s+\(GAME_SPEED\*2\)')
        self.assertIn('if(timeleft>0) --timeleft;\n\t\t\telse time_over();', text)
        self.assertIn('if(pause) newtime = time;', text)
        self.assertIn('if(newtime > time+100) newtime = time+100;', text)
        self.assertIn('if(!player[0].ent && !player[0].ent) endgame = 1;', text)
        self.assertIn('self->takedamage(self, 1000, 1, 0);', text)
        self.assertIn('if(other->type==TYPE_PLAYER) force /= 2;', text)
        self.assertIn('other->nextthink = time + GAME_SPEED * 3;', text)
        self.assertIn('other->z = 100000;', text)
        self.assertEqual(text.count('timeleft = 100 * COUNTER_SPEED;'), 7)
        self.assertIn('timeleft = 10 * COUNTER_SPEED;', text)
        self.assertIn('if(credits<1) timeleft = COUNTER_SPEED/2;', text)

    def test_timeout_edge_and_damage_dispatch(self):
        r = t.TimerReference(left=1)
        r.begin_tick()
        self.assertEqual(r.end_tick(), [])
        self.assertEqual(r.left, 0)
        r.begin_tick()
        self.assertEqual(r.end_tick(), [('damage', 0, 1000, 1, 0, 'self'),
                                       ('damage', 1, 1000, 1, 0, 'self'),
                                       ('sound', 'timeover')])
        self.assertEqual(r.left, 40000)
        self.assertTrue(r.show_timeover)

    def test_presence_callback_filters_and_pinned_p1_typo(self):
        for present in range(4):
            for callbacks in range(4):
                r = t.TimerReference(left=0)
                r.begin_tick()
                events = r.end_tick(present=present, damage_callbacks=callbacks)
                self.assertEqual(('endgame',) in events, not bool(present & 1))
                damage = [event[1] for event in events if event[0] == 'damage']
                self.assertEqual(damage, [p for p in range(2) if present & callbacks & (1 << p)])

    def test_no_countdown_outside_ingame_and_no_pause_catchup_in_core(self):
        r = t.TimerReference(left=1234)
        r.begin_tick()
        r.end_tick(ingame=False)
        self.assertEqual(r.left, 1234)
        # Paused display calls never produce simulation ticks.
        for _ in range(60):
            r.display()
        self.assertEqual(r.left, 1234)

    def test_full_duration_is_40000_ticks_plus_zero_observation(self):
        r = t.TimerReference()
        for _ in range(40000):
            r.begin_tick()
            self.assertEqual(r.end_tick(), [])
        self.assertEqual(r.left, 0)
        r.begin_tick()
        self.assertTrue(r.end_tick())

    def test_source_600_tick_pickup_and_duplicate_rejection(self):
        r = t.TimerReference(left=123)
        r.begin_tick()
        self.assertTrue(r.collect(6, 4))
        self.assertFalse(r.collect(6, 4))
        r.end_tick()
        self.assertEqual(r.left, 39999)
        for _ in range(599):
            self.assertEqual(r.begin_tick(), [])
            r.end_tick()
        self.assertEqual(r.pending[4], 1)
        self.assertEqual(r.begin_tick(), [4])
        r.end_tick()
        self.assertTrue(r.collect(6, 4))

    def test_reset_ownership_and_absent_grace(self):
        r = t.TimerReference(left=0, show_timeover=True)
        r.pending[2] = 123
        r.reset()
        self.assertEqual((r.left, r.pending[2], r.show_timeover), (40000, 123, True))
        r.absent(1)
        self.assertEqual(r.left, 4000)
        r.absent(0)
        self.assertEqual(r.left, 200)
        r.begin_tick()
        r.reset()  # wait release/update_scroller before decrement
        r.end_tick()
        self.assertEqual(r.left, 39999)

    def test_display_truncation_and_one_last_message_frame(self):
        for left, expected in ((40000, 99), (39600, 99), (39599, 98), (400, 1), (399, 0), (0, 0)):
            r = t.TimerReference(left=left, show_timeover=True)
            self.assertEqual(r.display(), (expected, True))
            self.assertEqual(r.show_timeover, expected == 99)

    def test_easy_and_other_campaigns_cannot_mutate_timer(self):
        for campaign in (0, 1, 2, 4, 255):
            r = t.TimerReference(campaign_id=campaign, left=123)
            before = copy.deepcopy(r)
            r.reset()
            r.absent(0)
            self.assertFalse(r.collect(6, 1))
            self.assertEqual(r.begin_tick(), [])
            self.assertEqual(r.end_tick(), [])
            self.assertEqual(r, before)
            with self.assertRaisesRegex(ValueError, 'OPT_IN'):
                t.emit_effect_metadata([], campaign_id=campaign)

    def test_tick_pair_contract(self):
        r = t.TimerReference()
        with self.assertRaisesRegex(ValueError, 'TICK_PAIR'):
            r.end_tick()
        r.begin_tick()
        with self.assertRaisesRegex(ValueError, 'TICK_PAIR'):
            r.begin_tick()

    def test_real_time_model_metadata_and_no_actor_id_special_case(self):
        from compiler import Source
        from model_ir import parse_model
        from actor_lowering import lower_model
        source = Source(ROOT / 'Beats of Rage Original [v.3.0 Build 4086].pak')
        ir = parse_model(source, 'DATA/CHARS/MISC/TIME.TXT', 'Time',
                         'test-project', 'historical-bor')
        actor = lower_model(ir, runtime_id=46)
        metadata = t.emit_effect_metadata([actor], campaign_id=3)
        self.assertEqual(metadata['table'][46], 6)
        self.assertEqual(sum(metadata['table']), 6)
        self.assertFalse(metadata['target_bound'])
        self.assertIn('StageTimer_ModelEffects:', t.emit_effect_include(metadata))
        actor['runtime_id'] = 93
        actor['display_alias'] = 'Apple'
        self.assertEqual(t.emit_effect_metadata([actor], campaign_id=3)['table'][93], 6)
        for stat in ('health', 'score'):
            changed = copy.deepcopy(actor)
            changed['stats'][stat] = 1
            with self.assertRaisesRegex(ValueError, 'PRECEDENCE'):
                t.emit_effect_metadata([changed], campaign_id=3)
        actor['runtime_id'] = None
        with self.assertRaisesRegex(ValueError, 'UNBOUND_RUNTIME_ID'):
            t.emit_effect_metadata([actor], campaign_id=3)

    def test_wram_allocation_and_module_abi(self):
        module = MODULE.read_text()
        addresses = {name: int(value, 16) for name, value in re.findall(
            r'(?m)^(StageTimer_\w+)\s*=\s*\$([0-9A-Fa-f]+)', module)}
        self.assertEqual(min(addresses.values()), t.WRAM_START)
        self.assertEqual(max(addresses.values()) + 1, t.WRAM_END)
        # Symbol starts throughout source, plus explicit neighboring arena
        # extents below, are independent of this module's declarations.
        for path in (ROOT / 'src').rglob('*.pasm'):
            if path == MODULE:
                continue
            code = '\n'.join(line.split(';', 1)[0] for line in path.read_text(errors='replace').splitlines())
            if path == ROOT / 'src/core/actor_s6_world_fixture.pasm':
                # The standalone production-world fixture needs the same
                # imported NMI field-counter symbol, but does not include the
                # timer module that owns its allocation. This is an alias to
                # the symbol inside StageTimer's declared arena, not another
                # allocation or a conflicting consumer.
                alias = re.compile(r'(?m)^StageTimer_FieldCounter\s*=\s*\$7E5914\s*$')
                self.assertEqual(len(alias.findall(code)), 1)
                code = alias.sub('', code)
            for match in re.finditer(r'\$(7[Ee][0-9A-Fa-f]{4})(?![0-9A-Fa-f])', code):
                self.assertFalse(t.WRAM_START <= int(match[1], 16) <= t.WRAM_END,
                                 f'WRAM reference collision: {path}:{match[0]}')
        self.assertLess(0x7E2000 + 48 * 256 - 1, t.WRAM_START)
        self.assertLess(0x7E550F + 6 * 133 - 1, t.WRAM_START)
        self.assertLess(0x7E58FF, t.WRAM_START)
        self.assertLess(t.WRAM_END, 0x7E5A00)  # concurrent S8 opponent HUD arena
        self.assertLess(t.WRAM_END, 0x7E6000)
        self.assertRegex(module, r'STAGE_TIMER_EFFECT_RESET = 6\b')
        self.assertNotRegex(module, r'(?m)^StageTimerHost_\w+:')

    def test_concrete_host_and_shared_integration(self):
        host = HOST.read_text()
        for name in t.HOST_CONTRACT:
            self.assertIn(name + ':', host)
        self.assertIn('jsl G13_SourcePlayerDeathP1', host)
        self.assertIn('jsl G13_SourcePlayerDeathP2', host)
        self.assertIn('jsl HudOpponent_Remove', host)
        self.assertIn('jsl Audio_QueueResidentSemantic', host)
        self.assertIn('ldx #STAGE_TIMER_TIMEOVER_SFX_ID', host)
        collect = host.split('StageTimerHost_Collect:', 1)[1].split('StageTimerHost_Retire:', 1)[0]
        self.assertNotIn('CHAR_HP', collect)  # no premature soft kill
        for n in range(1, 6):
            jump = (ROOT / 'src/core/jump.pasm').read_text()
            branch = jump.split(f'Character_Pickup_CheckOverlap__vs{n}_dy_ok:', 1)[1].split('rts', 1)[0]
            self.assertLess(branch.index(f'jsl StageTimerHost_CollectSlot{n}'),
                            branch.index('jsr Character_Pickup_CheckOverlap__TriggerGet'))
            self.assertLess(branch.index(f'bcs Character_Pickup_CheckOverlap__vs{n}_no'),
                            branch.index(f'jsl HudOpponentHost_Collect{n}'))
            self.assertLess(branch.index(f'jsl HudOpponentHost_Collect{n}'),
                            branch.index('jsr Character_Pickup_CheckOverlap__TriggerGet'))
            spawn = (ROOT / 'src/core/spawn.pasm').read_text()
            self.assertIn(f'jsl StageTimerHost_Slot{n}Busy', spawn)
        state = (ROOT / 'src/core/game_state.pasm').read_text()
        self.assertIn('jsl StageTimerHost_FrameService', state)
        self.assertIn('jsl StageTimerHost_ServiceDeaths', state)
        self.assertIn('jsl StageTimer_StartLevel', state)
        nmi = (ROOT / 'src/core/nmi.pasm').read_text().split('Core_Nmi_Play:', 1)[1]
        self.assertLess(nmi.index('jsl StageTimer_NmiField'), nmi.index('lda.l Nmi_FrameBusy'))
        self.assertEqual(nmi.count('jsl StageTimer_NmiField'), 1)

    def test_time_input_gate_and_handled_denial(self):
        host = HOST.read_text()
        gate = host.split('StageTimerHost_CollectFromOverlap:', 1)[1].split('StageTimerHost_IsPendingOffset:', 1)[0]
        self.assertLess(gate.index('jsl StageTimerHost_IsPendingOffset'), gate.index('CHAR_PICKUP_TYPE'))
        self.assertIn('jmp StageTimerHost_CollectFromOverlap__handled_offset', gate)
        self.assertIn('lda.l Input_trigger_Addr', gate)
        self.assertIn('lda.l Input2_trigger_Addr', gate)
        self.assertLess(gate.index('and #ANIM_ATTACK_BUTTON_MASK << 8'), gate.index('jsl StageTimer_ApplyEffect'))
        self.assertIn('beq StageTimerHost_CollectFromOverlap__handled', gate)
        self.assertIn('bcc StageTimerHost_CollectFromOverlap__handled', gate)
        self.assertRegex(gate, r'__handled:\s*\.a16\s*\.i16\s*ply\s*plx\s*plp\s*sec\s*rtl')
        self.assertLess(gate.index('jsl StageTimer_ApplyEffect'), gate.index('sta.l Input_trigger_Addr'))
        self.assertLess(gate.index('jsl StageTimer_ApplyEffect'), gate.index('sta.l Input2_trigger_Addr'))
        source = (ROOT / 'out/bor_compile_s6/BOR.C').read_text()
        attack = source.index('if(player[self->playerindex].playkeys & FLAG_ATTACK){', source.index('// Use stalltime') - 200)
        self.assertLess(attack, source.index('if(other = find_ent_here(self, self->x, self->z, TYPE_ITEM))', attack))


class TimerAssemblyTests(unittest.TestCase):
    def test_pending_render_wrapper_skips_before_oam(self):
        wrapper = HOST.read_text().split('StageTimerHost_RenderFrame:', 1)[1].split('StageTimerHost_Offsets:', 1)[0]
        self.assertIn('tdc', wrapper)
        self.assertIn('sbc #$0A00', wrapper)
        self.assertIn('jsl StageTimerHost_IsPendingOffset', wrapper)
        self.assertIn('bcs StageTimerHost_RenderFrame__skip', wrapper)
        self.assertIn('jml Character_RenderFrame', wrapper)
        skipped = wrapper.split('StageTimerHost_RenderFrame__skip:', 1)[1]
        self.assertNotIn('Character_RenderFrame', skipped)
        self.assertNotIn('Core_Oam', skipped)
        self.assertIn('rtl', skipped)

    def test_timer_row_ownership_allocation_and_exit_retry(self):
        host = HOST.read_text()
        self.assertRegex(host, r'(?m)^StageTimerHost_RowOwned = \$7E5920\b')
        for path in (ROOT / 'src').rglob('*.pasm'):
            if path == HOST:
                continue
            code = '\n'.join(line.split(';', 1)[0] for line in path.read_text(errors='replace').splitlines())
            self.assertNotRegex(code, r'\$7[Ee]592[01](?![0-9A-Fa-f])', str(path))
        cleanup = host.split('StageTimerHost_DrawTimer__cleanup:', 1)[1].split('StageTimerHost_QueueRow:', 1)[0]
        self.assertIn('lda.l StageTimerHost_RowOwned', cleanup)
        self.assertIn('beq StageTimerHost_DrawTimer__done', cleanup)
        self.assertLess(cleanup.index('bcc StageTimerHost_DrawTimer__done'), cleanup.index('sta.l StageTimerHost_RowOwned'))
        self.assertNotIn('ShowTimeOver', cleanup)
        self.assertNotIn('Game_CampaignId', cleanup)
        self.assertIn('StageTimerHost_BlankRow:\n    .dw 0,0,0,0,0,0,0,0,0', host)
        init = MODULE.read_text().split('StageTimer_StartLevel:', 1)[1].split('StageTimer_Reset100:', 1)[0]
        self.assertNotIn('StageTimerHost_RowOwned', init)
        self.assertIn('ldx #30', init)

    def test_timer_row_waits_for_pending_destination_before_redraw(self):
        host = HOST.read_text()
        draw = host.split('StageTimerHost_DrawTimer:', 1)[1].split('StageTimerHost_TimerRows:', 1)[0]
        self.assertLess(draw.index('lda.l DmaQueue+4,x'), draw.index('jsl StageTimer_Display'))
        self.assertIn('and #DMA_OPT_ACTIVE', draw)
        self.assertIn('lda.l DmaQueue+2,x', draw)
        self.assertIn('cpx #DMA_QUEUE_SLOTS*DMA_QUEUE_SLOT_SIZE', draw)
        self.assertIn('cmp #GAME_STATE_INTRO', draw)
        self.assertLess(draw.index('cmp #GAME_STATE_INTRO'), draw.index('lda.l Game_CampaignId'))

    def test_visible_timer_rom_rows_and_safe_queue(self):
        host = HOST.read_text()
        rows = host.split('StageTimerHost_TimerRows:', 1)[1].split('StageTimerHost_TimeOverRow:', 1)[0]
        entries = re.findall(r'(?m)^    \.dw (.*)$', rows)
        self.assertEqual(len(entries), 100)
        for value, row in enumerate(entries):
            glyphs = re.findall(r'FONT_TILE_INDEX_BASE\+(\d+)\+\(\(HUD_ENTRY_HIGH\*\$100\)\|\(FONT_CGRAM_PAL_ID\*\$0400\)\)', row)
            self.assertEqual(''.join(chr(int(n) + 32) for n in glyphs), f'TIME {value:02d}  ')
        timeout = host.split('StageTimerHost_TimeOverRow:', 1)[1]
        self.assertEqual(''.join(chr(int(n) + 32) for n in re.findall(
            r'FONT_TILE_INDEX_BASE\+(\d+)\+\(\(HUD_ENTRY_HIGH\*\$100\)\|\(FONT_CGRAM_PAL_ID\*\$0400\)\)', timeout)), 'TIME OVER')
        self.assertNotIn('$2400', rows + timeout)
        main = (ROOT / 'src/main.pasm').read_text()
        self.assertRegex(main, r'(?m)^HUD_ENTRY_HIGH\s*=\s*\$20\b')
        text_owner = (ROOT / 'src/core/text.pasm').read_text()
        self.assertRegex(text_owner, r'(?m)^FONT_CGRAM_PAL_ID\s*=\s*1\b')
        self.assertIn('ora #(HUD_ENTRY_HIGH * $100)', text_owner)
        self.assertIn('ora #(FONT_CGRAM_PAL_ID * $0400)', text_owner)
        draw = host.split('StageTimerHost_DrawTimer:', 1)[1].split('StageTimerHost_TimerRows:', 1)[0]
        self.assertIn('jsl StageTimer_Display', draw)
        self.assertIn('jsl Core_Dma_Enqueue_Long', draw)
        self.assertIn('11*TEXT_ROW_ENTRIES + 11', draw)
        self.assertIn('lda #18', draw)
        self.assertNotIn('TextStaging', draw)
        self.assertIn('sta.l StageTimer_ShowTimeOver', draw)  # failed enqueue retries snapshot

    def test_level_reset_does_not_write_nmi_owned_counter(self):
        code = MODULE.read_text().split('StageTimer_StartLevel:', 1)[1].split('StageTimer_Reset100:', 1)[0]
        self.assertRegex(code, r'cpx #20\s+beq StageTimer_StartLevel__next\s+sta.l StageTimer_Left,x')
        self.assertIn('lda.l StageTimer_FieldCounter\n    sta.l StageTimer_LastField', code)
        self.assertNotIn('sta.l StageTimer_FieldCounter', code)

    def test_concrete_host_assembles_against_real_compat_symbols(self):
        dotnet = os.environ.get('DOTNET', r'C:\Users\chad\.dotnet\dotnet.exe')
        poppy = os.environ.get('POPPY_DLL', r'E:\gh\poppy-astrobleem\src\Poppy.CLI\bin\Release\net10.0\poppy.dll')
        if not Path(dotnet).exists() or not Path(poppy).exists():
            self.skipTest('Poppy/.NET unavailable')
        code = MODULE.read_text() + '\n' + HOST.read_text()
        defined = set(re.findall(r'(?m)^(\w+)\s*(?::|=)', code))
        referenced = set(re.findall(r'\b[A-Za-z_]\w*\b', code))
        symbols = {}
        for bank, address, name in re.findall(r'(?m)^([0-9A-Fa-f]+):([0-9A-Fa-f]+)\s+(\w+)',
                                              (ROOT / 'src/main.sym').read_text()):
            if name in referenced and name not in defined:
                symbols[name] = (int(bank, 16) << 16) | int(address, 16)
        # HUD fallbacks are compilation-only until the combined link exists.
        symbols.setdefault('HudOpponent_Target', 0x058100)
        symbols.setdefault('HudOpponent_Remove', 0x058110)
        # Volta owns actual audio binding: use current source, not stale sym.
        main = (ROOT / 'src/main.pasm').read_text()
        for name in ('STAGE_TIMER_TIMEOVER_SFX_ID', 'AUDIO_SEMANTIC_TIMEOVER', 'HUD_ENTRY_HIGH'):
            value = re.search(rf'(?m)^{name}\s*=\s*(\$[0-9A-Fa-f]+|\d+)', main)
            self.assertIsNotNone(value, f'missing production audio constant {name}')
            token = value[1]
            symbols[name] = int(token[1:], 16) if token.startswith('$') else int(token)
        text_owner = (ROOT / 'src/core/text.pasm').read_text()
        symbols['FONT_CGRAM_PAL_ID'] = int(re.search(
            r'(?m)^FONT_CGRAM_PAL_ID\s*=\s*(\d+)', text_owner)[1])
        header = '.snes\n.bank 16\n.org $8000\n' + ''.join(
            f'{name} = ${value:X}\n' for name, value in sorted(symbols.items()))
        with tempfile.TemporaryDirectory(prefix='bor-s8-host-') as directory:
            fixture = Path(directory) / 'host.pasm'
            fixture.write_text(header + code)
            result = subprocess.run([dotnet, poppy, str(fixture), '-o', str(Path(directory) / 'host.bin')],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            # Verify actual assembled glyph words against owner-derived flags,
            # not merely textual expressions or a duplicated palette fixture.
            data = (Path(directory) / 'host.bin').read_bytes()
            for label in ('TIME 00  ', 'TIME 99  ', 'TIME OVER'):
                expected = b''.join((symbols['FONT_TILE_INDEX_BASE'] + ord(c) - 32
                                     + ((symbols['HUD_ENTRY_HIGH'] * 256)
                                        | (symbols['FONT_CGRAM_PAL_ID'] * 1024))).to_bytes(2, 'little') for c in label)
                self.assertIn(expected, data)

    def test_actual_module_assembles_with_required_host_symbols(self):
        dotnet = os.environ.get('DOTNET', r'C:\Users\chad\.dotnet\dotnet.exe')
        poppy = os.environ.get('POPPY_DLL', r'E:\gh\poppy-astrobleem\src\Poppy.CLI\bin\Release\net10.0\poppy.dll')
        if not Path(dotnet).exists() or not Path(poppy).exists():
            self.skipTest('Poppy/.NET unavailable; assembly remains unverified')
        header = '.snes\n.bank 13\n.org $8000\nGame_CampaignId = $7E275E\n'
        # Cross-bank sentinel destinations prove JSL encodes bank and address.
        hosts = ''.join(f'{name} = ${0x028100 + i * 16:06X}\n'
                        for i, name in enumerate(t.HOST_CONTRACT))
        with tempfile.TemporaryDirectory(prefix='bor-s8-timer-') as directory:
            fixture = Path(directory) / 'timer.pasm'
            binary = Path(directory) / 'timer.bin'
            symbols = Path(directory) / 'timer.sym'
            fixture.write_text(header + hosts + MODULE.read_text())
            result = subprocess.run([dotnet, poppy, str(fixture), '-o', str(binary), '-s', str(symbols)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            data = binary.read_bytes()
            for i in range(len(t.HOST_CONTRACT)):
                self.assertIn(b'\x22' + (0x028100+i*16).to_bytes(3, 'little'), data)
            self.assertIn(b'\xA9\x40\x9C', data)  # A16 40000
            self.assertIn(b'\xA9\x58\x02', data)  # A16 600
            self.assertIn(b'\xA9\xE8\x03', data)  # damage callback 1000
            # Production must fail to link without real host implementations.
            fixture.write_text(header + MODULE.read_text())
            rejected = subprocess.run([dotnet, poppy, str(fixture), '-o', str(binary)],
                                      capture_output=True, text=True)
            self.assertNotEqual(rejected.returncode, 0)


if __name__ == '__main__':
    unittest.main()
