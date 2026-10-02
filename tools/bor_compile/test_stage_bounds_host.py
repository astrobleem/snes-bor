"""Isolated host integration assembly/static checks. No emulator or ROM build.

External engine services are link addresses, not fake implementations. The
actual pit callback and complete bounds/host modules are assembled together.
"""
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

from compiler import ROOT
from stage_bounds import Bounds, emit_pasm


HOST = ROOT/'src/core/stage_bounds_host.pasm'


class BoundsHostTests(unittest.TestCase):
    def test_drop_entry_publication_and_completion_are_distinct(self):
        text=(ROOT/'src/core/stage_drop_host.pasm').read_text()
        self.assertIn('StageDrop_State = StageEnv_Actors+102',text)
        self.assertIn('cmp #STAGE_SCROLL_DOWN',text)
        self.assertIn('cmp #CHAR_INPUT_DRIVEN_AI',text)
        self.assertIn('lda CHAR_IDLE_BASE_LO',text)
        self.assertNotIn('CHAR_FALL_BASE',text)
        self.assertNotIn('Ramon',text)
        self.assertIn('jsl Msu1_LoadFrame_Long',text)
        self.assertIn('jsl Character_Throw_Play',text)
        self.assertLess(text.index('lda.l Msu1_StreamBusy'),text.index('jsl Msu1_LoadFrame_Long'))
        self.assertIn('lda #2\n    sta.l StageDrop_State,x',text)
        self.assertIn('lda #3\n    sta.l StageDrop_State,x',text)
        self.assertLess(text.index('sta.l StageDrop_State,x', text.index('StageDrop_BeforeActor__retire:')),
                        text.index('jsl StageDrop_PersistentHandoff'))
        self.assertIn('StageDrop_PersistentHandoff:\n    clc\n    rtl\n    nop\n    nop', text)
        self.assertIn('StageDrop_BeforeActor__owned:\n    sec\n    rts', text)
        render=text.split('StageDrop_Render:',1)[1]
        self.assertIn('cmp #3',render)
        self.assertIn('sta.l OamSetSprite_Y',render)

    def test_live_hook_order_and_physical_slots(self):
        main = (ROOT/'src/main.pasm').read_text()
        actor = main.split('CharacterEntity_Play:', 1)[1].split('CharacterEntity_Play__no_context_exit:', 1)[0]
        self.assertLess(actor.index('jsl StageBoundsHost_BeforeActor'), actor.index('jsl G13_Player2_ContextEnter'))
        self.assertIn('pld\n    brl CharacterEntity_Play__no_context_exit', actor)
        move = main.split('Character_PlayFrame:', 1)[1].split('Character_RenderFrame:', 1)[0]
        self.assertLess(move.index('StageBoundsHost_BeforeActor'), move.index('jsl Spawn_CheckHole'))
        self.assertIn('sta CHAR_POS_Y\n    jsl StageBoundsHost_Clamp', move)
        render = main.split('Character_RenderFrame:', 1)[1].split('G13_Core_Math_Div_Long:', 1)[0]
        self.assertRegex(render, r'jsl StageBoundsHost_Render\s+php\s+jsr Core_Oam_SetSprite[^\n]*\n\s+plp\s+bcs Character_RenderFrame__bounds_done')
        game = (ROOT/'src/core/game_state.pasm').read_text()
        self.assertIn('jsl StageBoundsHost_Physics\n    jsr Core_Oop_Play', game)
        spawn = (ROOT/'src/core/spawn.pasm').read_text()
        self.assertIn('Spawn_Play__environment_base:\n    jsl StageBoundsHost_ResetSpawn\n    jsl StageEnv_ApplySpawnBase', spawn)

    def test_canonical_death_and_no_item_award(self):
        text = HOST.read_text()
        callback = text.split('StageBounds_ApplyPitDamage_Long:', 1)[1]
        for target in ('HudOpponent_Remove', 'StageTimer_CancelSlot',
                       'G13_SourcePlayerDeathP1', 'G13_SourcePlayerDeathP2'):
            self.assertIn('jsl '+target, callback)
        self.assertIn('stz CHAR_HP', callback)
        self.assertIn('sta CHAR_FALL_STATE_TIMER', callback)
        self.assertNotIn('ApplyPickup', callback)
        self.assertNotIn('Game_Score', callback)
        self.assertNotIn('RevealPendingItems', callback)
        self.assertNotRegex(text, r'^\w+\s*=\s*\$7[Ee]', 'host must not allocate globals')

    def test_preserved_timer_flags_are_not_used_as_result(self):
        timer = (ROOT/'src/core/stage_timer.pasm').read_text().split('StageTimer_TakeGravityTicks:', 1)[1]
        self.assertIn('plp', timer)
        self.assertRegex(HOST.read_text(), r'jsl StageTimer_TakeGravityTicks\s+cmp #0')

    def test_isolated_host_width_check(self):
        sys.path.insert(0, str(ROOT/'tools/rom_audit'))
        from check_width_directives import flatten, scan
        violations, count = scan(flatten(str(HOST)))
        self.assertGreater(count, 20)
        self.assertEqual(violations, [])

    def test_actual_host_assembles_without_callback_stub(self):
        dotnet = os.environ.get('DOTNET', r'C:\Users\chad\.dotnet\dotnet.exe')
        poppy = os.environ.get('POPPY_DLL', r'E:\gh\poppy-astrobleem\src\Poppy.CLI\bin\Release\net10.0\poppy.dll')
        if not Path(dotnet).is_file() or not Path(poppy).is_file():
            self.skipTest('Poppy unavailable')
        sources = ['src/main.pasm', 'src/core/game_state.pasm', 'src/core/oam.pasm', 'src/core/stage_scroll.pasm',
                   'src/core/stage_environment.pasm', 'src/core/spawn.pasm', 'src/core/stage_timer.pasm',
                   'tools/audio/stage_scroll_config.pasm']
        texts = '\n'.join((ROOT/p).read_text() for p in sources)
        names = ('CHAR_POS_X CHAR_POS_Y CHAR_THROW_ZPOS CHAR_THROW_ZVEL CHAR_GRAB_TARGET '
                 'CHAR_GRABBED_BY CHAR_ZP_LEN CHAR_HP CHAR_PICKUP_TYPE CHAR_INPUT_DRIVEN '
                 'CHAR_INPUT_DRIVEN_AI CHAR_INPUT_DRIVEN_NONCOMBAT CHAR_ROSTER_INDEX CHAR_SELECTED '
                 'CHAR_SELECTED_FALL CHAR_FALL_STATE_TIMER CHAR_HIT_APPLIED '
                 'Game_CampaignId Game_StageIndex G13_TwoPlayerEnabled OamSetSprite_Y '
                 'OamSetSprite_Attr StageEnv_Actors StageEnv_BaseFraction StageEnv_BaseInteger '
                 'Spawn_ScratchSlotOfs StageTimer_Pending Entity1_ItemRosterIdx Entity4_ItemRosterIdx '
                 'Stage_ScrollDirection STAGE_SCROLL_DOWN CHAR_SELECTED_THROWN CHAR_IDLE_FCOUNT '
                 'CHAR_IDLE_BASE_LO CHAR_IDLE_BASE_HI CHAR_FRAME_INDEX CHAR_TICK_COUNTER '
                 'Msu1_StreamBusy AnimHeaderStaging').split()
        definitions = [re.search(r'^'+name+r'\s*=.*$', texts, re.M)[0] for name in names]
        imports = ('HudOpponent_Remove StageTimer_TakeGravityTicks StageTimer_CancelSlot '
                   'G13_SourcePlayerDeathP1 G13_SourcePlayerDeathP2 G13_PlayerLifecycleIsOut '
                   'Msu1_LoadFrame_Long Character_Throw_Play '
                   'S6Normal_IsRosterBound S6Normal_Bind').split()
        definitions += ['S6Host_Mode = $7E1760', 'S6Host_Error = $7E1764',
                        'S6Bridge_Policy = StageEnv_Actors+64',
                        'S6Bridge_Exists = StageEnv_Actors+65']
        # Link-only engine APIs in a different ROM bank. No fake RTL bodies.
        definitions += [f'{name} = ${0x0b9000+i*0x100:06X}' for i, name in enumerate(imports)]
        fixture = '\n'.join(['.snes', '.bank 13', '.org $8000', *definitions,
                             emit_pasm([None, Bounds(640, True), Bounds(320, endhole=True)], bank=13),
                             'EntityDpBaseTable:', '    .dw $0A00, $0A85, $0B0A, $0B8F, $0C14, $0C99',
                             '.bank 15', '.org $8000',
                             f'.include "{(ROOT/"src/core/stage_bounds.pasm").as_posix()}"',
                             f'.include "{HOST.as_posix()}"'])
        with tempfile.TemporaryDirectory(prefix='s8_bounds_host_') as tmp:
            src = Path(tmp)/'host.pasm'
            src.write_text(fixture)
            output = Path(tmp)/'host.bin'
            run = subprocess.run([dotnet, poppy, str(src), '-o', str(output)],
                                 capture_output=True, text=True, cwd=tmp, timeout=60)
            self.assertEqual(run.returncode, 0, run.stdout+run.stderr)
            data = output.read_bytes()
            self.assertIn(bytes.fromhex('2200930b'), data)  # actual host -> P1 death
            self.assertIn(bytes.fromhex('2200940b'), data)  # actual host -> P2 death


if __name__ == '__main__':
    unittest.main()
