import re
import unittest
from pathlib import Path
import importlib.util
import ast
import os
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
BRIDGE = ROOT / 'src/core/actor_source_bridge.pasm'
SOURCE_VISUAL = ROOT / 'src/core/source_visual_production.pasm'
NORMAL_RUNTIME = ROOT / 'src/core/actor_s8_normal_sa1_runtime.pasm'
GAME_STATE = ROOT / 'src/core/game_state.pasm'
PLAYER2 = ROOT / 'src/core/player2_context.pasm'
HOST = ROOT / 'src/core/actor_source_host.pasm'
TIMER_HOST = ROOT / 'src/core/stage_timer_host.pasm'
WORLD_FIXTURE = ROOT / 'src/core/actor_s6_world_fixture.pasm'


def round_ratio_away(numerator, denominator):
    sign = -1 if numerator < 0 else 1
    magnitude = abs(numerator)
    return sign * ((magnitude + denominator // 2) // denominator)


class NormalCoordinateBridgeTests(unittest.TestCase):
    def test_source_campaign_accelerator_uses_the_inclusive_left_edge(self):
        fixture_path = ROOT / 'tools/verify/game_s8_normal_campaign.py'
        spec = importlib.util.spec_from_file_location(
            '_s8_normal_left_edge_fixture', fixture_path)
        fixture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture)
        self.assertFalse(hasattr(fixture, '_left_clear_patch_count'))
        self.assertFalse(hasattr(fixture, '_forward_camera_patch_count'))
        source = (ROOT / 'tools/verify/_game_s8_normal_campaign_base.py').read_text()
        module = ast.parse(source)
        run = next(node for node in module.body
                   if isinstance(node, ast.FunctionDef) and node.name == 'run')
        accelerate = next(node for node in ast.walk(run)
                          if isinstance(node, ast.FunctionDef)
                          and node.name == 'accelerate')

        def edge_is_zero(node):
            return (
                isinstance(node, ast.Compare)
                and isinstance(node.left, ast.Name)
                and node.left.id == 'edge'
                and len(node.ops) == 1
                and isinstance(node.ops[0], ast.Eq)
                and len(node.comparators) == 1
                and isinstance(node.comparators[0], ast.Constant)
                and node.comparators[0].value == 0
            )

        zero_edge_checks = [node for node in ast.walk(accelerate)
                            if isinstance(node, ast.If)
                            and edge_is_zero(node.test)]
        self.assertTrue(zero_edge_checks)
        self.assertTrue(any(
            node.body and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Call)
            and isinstance(node.body[0].value.func, ast.Name)
            and node.body[0].value.func.id == 'AssertionError'
            for node in zero_edge_checks
        ))
        self.assertTrue(any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == 'm'
            and node.func.attr == 'write_u16'
            and len(node.args) == 2
            and ast.unparse(node.args[0]) == 'legal.SCREEN_POS_X'
            and isinstance(node.args[1], ast.Name)
            and node.args[1].id == 'edge'
            for node in ast.walk(accelerate)
        ))
        self.assertTrue(any(
            isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == 'button'
                    for target in node.targets)
            and isinstance(node.value, ast.Name)
            and node.value.id == 'traversal_camera_wait_button_value'
            for node in ast.walk(run)
        ))

    def test_empty_combat_lane_advances_camera_to_pending_spawn_trigger(self):
        fixture_path = ROOT / 'tools/verify/game_s8_normal_campaign.py'
        spec = importlib.util.spec_from_file_location(
            '_s8_normal_forward_camera_fixture', fixture_path)
        fixture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture)
        fixture._traversal_combat_modes = {2, 4}
        state = {
            'stage': 22,
            'camera_x': 478,
            'camera_min_x': 0,
            'camera_max_x': 1840,
            'next_trigger': 560,
            'spawn_index': 10,
            'spawn_count': 43,
            'spawn_waiting': 0,
            'npc_slots': [],
        }
        fixture._traversal_terminal_clamp(state)
        self.assertTrue(fixture._traversal_camera_state['forward_pending'])
        self.assertTrue(fixture._traversal_camera_wait(779, 478, 256, 'right'))
        self.assertEqual(fixture._traversal_camera_wait_button(), 0x0090)
        self.assertEqual(fixture._impl.traversal_camera_wait_button_value, 0x0090)
        state['npc_slots'] = [{'hp': 50, 'input': 2}]
        fixture._traversal_terminal_clamp(state)
        self.assertFalse(fixture._traversal_camera_state['forward_pending'])
        self.assertFalse(fixture._traversal_camera_wait(700, 478, 256, 'right'))
        self.assertEqual(fixture._traversal_camera_wait_button(), 0)
        self.assertEqual(fixture._impl.traversal_camera_wait_button_value, 0)

    def test_campaign_fixture_can_select_the_bound_candidate_image(self):
        fixture_path = ROOT / 'tools/verify/game_s8_normal_campaign.py'
        candidate = ROOT / 'build/s8_normal_sa1_rtl_candidate_jump02'
        spec = importlib.util.spec_from_file_location(
            '_s8_normal_candidate_override_fixture', fixture_path)
        fixture = importlib.util.module_from_spec(spec)
        with patch.dict(os.environ, {'S8_NORMAL_CANDIDATE_DIR': str(candidate)}):
            spec.loader.exec_module(fixture)
        self.assertEqual(fixture.CANDIDATE_DIR, candidate.resolve())

    def test_campaign_fixture_can_trace_the_persistent_worker_fault_boundary(self):
        fixture_path = ROOT / 'tools/verify/game_s8_normal_campaign.py'
        source = fixture_path.read_text()
        self.assertIn('S8_NORMAL_WORLD_FAULT_TRACE', source)
        self.assertIn('Worker_FaultWait', source)
        self.assertIn('_s8_fault_word(0x12c66)', source)
        self.assertIn('_s8_fault_word(ctx+0x16)', source)

    def test_campaign_fixture_detects_quantized_left_terminal_clamp(self):
        fixture_path = ROOT / 'tools/verify/game_s8_normal_campaign.py'
        spec = importlib.util.spec_from_file_location(
            '_s8_normal_campaign_fixture', fixture_path)
        fixture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture)
        state = {
            'stage': 33,
            'camera_x': 1000,
            'camera_min_x': 943,
            'camera_max_x': 1840,
            'spawn_waiting': 0,
            'spawn_index': 77,
            'spawn_count': 107,
            'npc_slots': [{'hp': 40, 'input': 2}],
        }
        self.assertTrue(fixture._traversal_terminal_clamp(state))
        state['camera_x'] = 1100
        self.assertTrue(fixture._traversal_terminal_clamp(state))
        state['spawn_index'] = 78
        self.assertFalse(fixture._traversal_terminal_clamp(state))
        fixture._terminal_stall_latch = None
        state['spawn_index'] = 77
        state['camera_x'] = 1008
        self.assertFalse(fixture._traversal_terminal_clamp(state))

    def test_left_queue_stall_latches_after_camera_passes_trigger(self):
        fixture_path = ROOT / 'tools/verify/game_s8_normal_campaign.py'
        spec = importlib.util.spec_from_file_location(
            '_s8_normal_left_queue_stall_fixture', fixture_path)
        fixture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture)
        fixture._traversal_combat_modes = {2, 4}
        fixture._traversal_queue_stall_latched = False
        fixture._traversal_queue_stall_key = None
        fixture._traversal_queue_stall_samples = 0
        fixture._traversal_slot_stall_latched = False
        fixture._traversal_no_progress_latched = False
        state = {
            'stage': 33,
            'camera_x': 256,
            'camera_min_x': 943,
            'camera_max_x': 1840,
            'next_trigger': 760,
            'spawn_waiting': 0,
            'spawn_index': 25,
            'spawn_count': 107,
            'npc_slots': [
                {'hp': 4, 'input': 3}, {'hp': 4, 'input': 3},
                {'hp': 4, 'input': 3}, {'hp': 4, 'input': 3},
                {'hp': 4, 'input': 3},
            ],
        }
        for _ in range(120):
            fixture._traversal_terminal_clamp(state)
        self.assertTrue(fixture._traversal_queue_stall_latched)
        self.assertTrue(fixture._traversal_slot_stall_latched)
        self.assertTrue(fixture._traversal_recovery_latched())

    def test_left_stage_does_not_backtrack_for_a_distant_pickup(self):
        fixture_path = ROOT / 'tools/verify/game_s8_normal_campaign.py'
        spec = importlib.util.spec_from_file_location(
            '_s8_normal_pickup_fixture', fixture_path)
        fixture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture)
        fixture._terminal_stall_latch = None
        fixture._traversal_terminal_clamp({
            'stage': 33,
            'camera_x': 1200,
            'camera_min_x': 943,
            'camera_max_x': 1840,
            'spawn_waiting': 0,
            'spawn_index': 77,
            'spawn_count': 107,
        })
        self.assertEqual(
            fixture._traversal_pickup_action(848, 34, 100),
            ('approach_left', False),
        )

    def test_left_camera_wait_releases_at_the_authored_minimum(self):
        fixture_path = ROOT / 'tools/verify/game_s8_normal_campaign.py'
        spec = importlib.util.spec_from_file_location(
            '_s8_normal_camera_wait_fixture', fixture_path)
        fixture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture)
        state = {
            'stage': 34,
            'camera_x': 0,
            'camera_min_x': 0,
            'camera_max_x': 79,
            'spawn_waiting': 0,
            'spawn_index': 1,
            'spawn_count': 19,
        }
        fixture._traversal_terminal_clamp(state)
        self.assertFalse(fixture._traversal_camera_wait(30, 0, 256, 'left'))
        state['camera_x'] = 40
        fixture._traversal_terminal_clamp(state)
        self.assertTrue(fixture._traversal_camera_wait(30, 40, 256, 'left'))

    def test_left_terminal_latch_releases_after_live_combat_ends(self):
        fixture_path = ROOT / 'tools/verify/game_s8_normal_campaign.py'
        spec = importlib.util.spec_from_file_location(
            '_s8_normal_left_latch_fixture', fixture_path)
        fixture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture)
        fixture._terminal_stall_latch = None
        state = {
            'stage': 34,
            'camera_x': 0,
            'camera_min_x': 0,
            'camera_max_x': 1840,
            'spawn_waiting': 0,
            'spawn_index': 9,
            'spawn_count': 19,
            'npc_slots': [{'hp': 19, 'input': 2}],
        }
        self.assertTrue(fixture._traversal_terminal_clamp(state))
        state['npc_slots'][0]['hp'] = 0
        self.assertFalse(fixture._traversal_terminal_clamp(state))
        self.assertIsNone(fixture._terminal_stall_latch)

    def test_depth_mismatch_keeps_group_gated_enemy_targeted_for_alignment(self):
        fixture_path = ROOT / 'tools/verify/game_s8_normal_campaign.py'
        spec = importlib.util.spec_from_file_location(
            '_s8_normal_depth_target_fixture', fixture_path)
        fixture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture)
        # The target remains selected so the controller can move vertically;
        # suppressing it while |dy| > 8 leaves a group-gated wave inert.
        target = (0, 0, 120, 150, 2, 30, 2, 60, False, False)
        self.assertTrue(fixture._traversal_combat_engagement_needed(
            target, 100, 120, group_gate_blocked=True,
            queue_complete=False, terminal=False, direction='left'))
        self.assertEqual(fixture.traversal_chase_axis(1, 8), 'y')
        self.assertEqual(fixture.traversal_chase_axis(1, 7), 'attack')

    def test_persistent_player_keeps_native_jump_tick_at_actor_boundary(self):
        source = WORLD_FIXTURE.read_text()
        owned = source.split('S6Game_Entity__owned_return:\n', 1)[1]
        owned = owned.split('\nS6Game_Entity__owned_return_path:', 1)[0]
        self.assertIn('cmp #$0A00\n    beq S6Game_Entity__owned_player1', owned)
        self.assertIn('cmp #$0A00+CHAR_ZP_LEN\n    beq S6Game_Entity__owned_player2', owned)
        self.assertIn('jsl Jump_PlayerInputGate', owned)
        self.assertIn('jsl G13_Player2_ContextEnter', owned)
        self.assertIn('jsl G13_Player2_ContextExit', owned)
        self.assertIn('source worker still owns ground movement/combat', owned)

    def test_stage_respawn_clears_full_q8_player_height_state(self):
        p1 = GAME_STATE.read_text().split('Game_State_RespawnPlayer:\n', 1)[1]
        p1 = p1.split('\n; ----------------------------------------------------------------------', 1)[0]
        self.assertIn('sta.l $7E0A00+CHAR_THROW_ZPOS', p1)
        self.assertIn('sta.l $7E0A00+CHAR_THROW_ZVEL', p1)
        p2 = PLAYER2.read_text().split('G13_EnsureP2AfterStage:\n', 1)[1]
        p2 = p2.split('\nG13_EnsureP2AfterStage__done:', 1)[0]
        self.assertIn('sta CHAR_THROW_ZPOS', p2)
        self.assertIn('sta CHAR_THROW_ZVEL', p2)
        respawn = PLAYER2.read_text().split('G13_RespawnP2:\n', 1)[1]
        respawn = respawn.split('\n; Return carry set', 1)[0]
        self.assertIn('rep #$20\n.a16\n    lda #0\n    sta CHAR_THROW_ZPOS', respawn)
        self.assertIn('lda #JUMP_INITIAL_VEL\n    sta CHAR_THROW_ZVEL', respawn)

    def test_normal_low_table_is_nearest_four_fifths(self):
        source = BRIDGE.read_text()
        body = source.split('S6Bridge_ProjectRoundedLow:\n', 1)[1]
        body = body.split('\nS6Bridge_ProjectLow:', 1)[0]
        actual = [int(value, 16) for value in re.findall(r'\$([0-9A-Fa-f]{4})', body)]
        expected = [round_ratio_away(4 * value, 5) for value in range(287)]
        self.assertEqual(actual, expected)

    def test_normal_inverse_and_projection_roundtrip_all_native_coordinates(self):
        for native in range(-6553, 6554):
            source = round_ratio_away(5 * native, 4)
            self.assertEqual(round_ratio_away(4 * source, 5), native)

    def test_normal_bridge_tables_cover_the_expanded_source_world_domain(self):
        source = BRIDGE.read_text()
        high = source.split('S6Bridge_ProjectHigh:\n', 1)[1]
        high = high.split('\nS6Bridge_ProjectRoundedLow:', 1)[0]
        high_values = [int(value, 16) for value in re.findall(
            r'\$([0-9A-Fa-f]{4})', high)]
        self.assertEqual(high_values, [204 * nibble for nibble in range(32)])
        exact = source.split('S6Bridge_ProjectLow:\n', 1)[1]
        exact_values = [int(value, 16) for value in re.findall(
            r'\$([0-9A-Fa-f]{4})', exact)]
        self.assertEqual(len(exact_values), 287)
        self.assertEqual(exact_values, [
            4 * value // 5 if value % 5 == 0 else 0x8000
            for value in range(287)])
        target = (ROOT / 'src/core/actor_source_target.pasm').read_text()
        self.assertIn('adc #8192\n    cmp #16384', target)

    def test_exact_reference_policy_still_fails_closed_off_lattice(self):
        source = BRIDGE.read_text()
        exact = source.split('S6Bridge_Unproject:\n', 1)[1]
        exact = exact.split('\nS6Bridge_Unproject__bad:', 1)[0]
        self.assertIn('and #3', exact)
        self.assertIn('bne S6Bridge_Unproject__bad', exact)
        self.assertIn('S6Bridge_UnprojectPolicy', source)
        self.assertIn('S6Bridge_ProjectPolicy', source)

    def test_only_scpu_player_jump_may_keep_local_vertical_state(self):
        source = BRIDGE.read_text()
        body = source.split('S6Bridge_Import__bound:\n', 1)[1]
        body = body.split('\nS6Bridge_Import__linked:', 1)[0]
        self.assertIn('CHAR_INPUT_DRIVEN,x', body)
        self.assertIn('cmp #1\n    beq S6Bridge_Import__height_input_ok\n    brl S6Bridge_Import__height_bad', body)
        self.assertIn('CHAR_SELECTED,x', body)
        self.assertIn('cmp #CHAR_SELECTED_JUMP\n    beq S6Bridge_Import__height_check_valid\n    brl S6Bridge_Import__height_bad', body)
        self.assertIn('S6Bridge_Import__height_bad:', body)
        self.assertIn('S6Bridge_Import__numeric:', body)
        self.assertIn('deliberately neither imports nor exports player height', body)
        self.assertIn('S6Bridge_Import__height_not_jump:\n    .a8\n    .i16', body)
        self.assertIn('beq S6Bridge_Import__worker_jump_active', body)
        synced = body.split('S6Bridge_Import__height_synced:\n', 1)[1]
        self.assertTrue(synced.lstrip().startswith('; Both branches'))
        self.assertIn('rep #$30\n    .a16\n    .i16\n    lda.l $7E0A00+CHAR_POS_X,x', synced)

    def test_resident_world_selects_persistent_owner_protocol_state(self):
        source = (ROOT / 'tools/verify/actor_s6_production_world.py').read_text()
        self.assertIn('S7Resident_Enabled = {2 if resident else 0}', source)
        self.assertIn('0=disabled/production,', source)
        self.assertIn('2=persistent resident owner', source)

    def test_normal_epoch_clears_only_reserved_source_context_existence(self):
        source = NORMAL_RUNTIME.read_text()
        init = source.split('S6Normal_Init__bridge_done:\n', 1)[1]
        init = init.split('\nS6Normal_Init__return:', 1)[0]
        self.assertIn('sta.l $7E1900,x', init)
        self.assertIn('sta.l $7E19E0,x', init)
        self.assertIn('cpx #$0600', init)
        self.assertIn('S6Bridge_Policy,x', source)

    def test_persistent_player_move_receives_stage_world_bound_at_fence(self):
        runtime = NORMAL_RUNTIME.read_text()
        rebase = runtime.split('S6Normal_RebaseStageClock:\n', 1)[1]
        rebase = rebase.split('\nS6Normal_RebaseStageClock__return:', 1)[0]
        self.assertIn('jsl S7Resident_Flush', rebase)
        self.assertIn('jsl S6Normal_MutationFenceBegin', rebase)
        self.assertIn('lda.l WorldMaxX\n    jsl S6Bridge_UnprojectRounded', rebase)
        self.assertIn('sta.l S6Host_PlayerWorldMaxX', rebase)
        self.assertIn('jsl S6Normal_MutationFenceEnd', rebase)

        host = HOST.read_text()
        move = host.split('S6Host_PlayerMove:\n', 1)[1]
        move = move.split('\nS6_FrameChanged:', 1)[0]
        self.assertIn('cmp #1\n    bne S6Host_PlayerMove__x_bound_done', move)
        self.assertIn('cmp #2\n    bne S6Host_PlayerMove__x_bound_done', move)
        self.assertIn('and #$0200\n    beq S6Host_PlayerMove__x_bound_right', move)
        self.assertIn('bpl S6Host_PlayerMove__x_bound_done\n    stz $14', move)
        self.assertIn('cmp.l S6Host_PlayerWorldMaxX', move)
        self.assertIn('lda.l S6Host_PlayerWorldMaxX\n    sta $14', move)
        self.assertIn('S6Host_PlayerWorldMaxX = $412D06', host)

    def test_normal_worker_world_relationships_are_initialized_and_published(self):
        source = NORMAL_RUNTIME.read_text()
        init = source.split('S6Normal_Init__enabled:\n', 1)[1]
        init = init.split('\nS6Normal_Init__clock_clear:', 1)[0]
        for address in ('$7E1744', '$7E1746', '$7E174E', '$7E1750',
                        '$411744', '$411746', '$41174E', '$411750'):
            self.assertIn(f'sta.l {address}', init)
        sync = source.split('S6Normal_SyncBoundContext:\n', 1)[1]
        sync = sync.split('\n; Restore a player row', 1)[0]
        self.assertIn('lda #$1900\n    sta.l $7E1744', sync)
        self.assertIn('lda #$7900\n    sta.l $411744', sync)
        self.assertIn('lda #$1A00\n    sta.l $7E1746', sync)
        self.assertIn('lda #$7A00\n    sta.l $411746', sync)
        self.assertIn('CHAR_INPUT_DRIVEN', sync)

    def test_source_visual_variable_tile_and_palette_leases_are_bounded(self):
        source = SOURCE_VISUAL.read_text()
        self.assertIn('SourceVisual_State           = $7E4A80 ; 6 * 32-byte actor visual leases', source)
        self.assertIn('SOURCE_VISUAL_TILE_BLOCK_BYTES = 256', source)
        self.assertIn('SOURCE_VISUAL_TILE_BLOCKS = SOURCE_VISUAL_MAX_SHEET / SOURCE_VISUAL_TILE_BLOCK_BYTES', source)
        self.assertIn('SourceVisual_BlockCache      = $7E4C00 ; 64 * 8-byte content-addressed slots', source)
        self.assertIn('SourceVisual_ActorPieceMap   = $7E4E00 ; 6 * 65 one-byte block-slot maps', source)
        self.assertIn('SourceVisual_PaletteCache    = $7E4FA0', source)
        blocks = source.split('SourceVisual_PrepareBlocks:\n', 1)[1]
        blocks = blocks.split('\n; A cache record is', 1)[0]
        self.assertIn('jsr SourceVisual_FindBlock', blocks)
        self.assertIn('jsr SourceVisual_AllocateBlock', blocks)
        self.assertIn('jsr SourceVisual_ApplyMappedPiece', blocks)
        transfer = source.split('SourceVisual_QueueBlockRows:\n', 1)[1]
        transfer = transfer.split('\n; Return the legal 16x32 OBJ tile origin', 1)[0]
        self.assertIn('jsl Core_Dma_Enqueue_Long', transfer)
        self.assertIn('cmp #SOURCE_VISUAL_VRAM_END+1', transfer)
        palettes = source.split('SourceVisual_AllocatePalettes:\n', 1)[1]
        palettes = palettes.split('\nSourceVisual_FindEntry__next:', 1)[0]
        self.assertIn('cmp #9', palettes)
        self.assertIn('SourceVisual_State+14,x', palettes)
        self.assertIn('jsr SourceVisual_AllocatePaletteIdentity', palettes)
        self.assertIn('sta.l SourceVisual_State,x', palettes)
        identities = source.split('SourceVisual_AllocatePaletteIdentity:\n', 1)[1]
        identities = identities.split('\nSourceVisual_MarkPaletteDmaRetired:', 1)[0]
        self.assertIn('cmp.l SourceVisual_PaletteGlobalIndex', identities)
        self.assertIn('SourceVisual_PaletteCache+4,x', identities)
        queue = source.split('SourceVisual_QueuePalettes:\n', 1)[1]
        queue = queue.split('\nSourceVisual_ReadPalettePayload:', 1)[0]
        self.assertIn('SourceVisual_State,x', queue)
        self.assertIn('SourceVisual_PaletteCache+3,x', queue)
        self.assertIn('jsr SourceVisual_PrepareBlocks', source)

    def test_source_visual_empty_authored_frame_is_a_valid_zero_oam_entry(self):
        source = SOURCE_VISUAL.read_text()
        load = source.split('SourceVisual_LoadResources:\n', 1)[1]
        load = load.split('\nSourceVisual_LoadResources__block_path:', 1)[0]
        self.assertIn(
            'sta.l SourceVisual_PieceCount\n'
            '    beq SourceVisual_LoadResources__piece_count_valid',
            load,
        )
        self.assertIn('lda.l SourceVisual_PieceCount\n'
                      '    beq SourceVisual_LoadResources__transparent', load)
        transparent = load.split(
            'SourceVisual_LoadResources__transparent:\n', 1)[1]
        self.assertIn('sta.l SourceVisual_State+6,x', transparent)
        self.assertIn('sec\n    rts', transparent)

    def test_normal_visual_path_never_falls_back_for_an_invalid_identity(self):
        source = TIMER_HOST.read_text()
        body = source.split('StageTimerHost_RenderFrame:\n', 1)[1]
        normal = body.split('StageTimerHost_RenderFrame__normal_campaign:\n', 1)[1]
        normal = normal.split('\nStageTimerHost_RenderFrame__compat:', 1)[0]
        self.assertIn('cmp #3\n    beq StageTimerHost_RenderFrame__normal_campaign', body)
        self.assertIn('lda.l Game_CampaignId\n    and #$00FF\n    cmp #3', body)
        self.assertIn('cmp #SOURCE_VISUAL_ROSTER_COUNT', normal)
        self.assertIn('bcs StageTimerHost_RenderFrame__normal_invalid', normal)
        self.assertIn('cmp #VISUAL_POLICY_SOURCE_SIZED', normal)
        self.assertIn('bne StageTimerHost_RenderFrame__normal_invalid', normal)
        self.assertNotIn('jml Character_RenderFrame', normal)
        invalid = normal.split('StageTimerHost_RenderFrame__normal_invalid:\n', 1)[1]
        self.assertIn('lda #$21', invalid)
        self.assertIn('sta.l SourceVisual_DebugLastError', invalid)
        self.assertIn('jsl Core_Oam_HideRequest', invalid)
        self.assertIn('StageTimerHost_RenderFrame__compat:\n', body)
        self.assertIn('jml Character_RenderFrame', body)

    def test_typed_slot_reuse_retires_only_the_old_bound_worker_row(self):
        source = NORMAL_RUNTIME.read_text()
        fallback = source.split('S6Normal_Bind__fallback:\n', 1)[1]
        fallback = fallback.split('\n; A16 roster id', 1)[0]
        self.assertIn('jsl S6Normal_RetireReplacedBound', fallback)
        retire = source.split('S6Normal_RetireReplacedBound:\n', 1)[1]
        retire = retire.split('\n; A16 roster id', 1)[0]
        self.assertIn('jsl S7Resident_Flush', retire)
        self.assertIn('jsl S6_KillUnlinked', retire)
        self.assertIn('sta.l S6Bridge_Policy,x', retire)
        self.assertIn('jsl S6Normal_SyncBoundContext', retire)
        for host, worker in ((0x1744, 0x411744), (0x1746, 0x411746),
                             (0x174E, 0x41174E), (0x1750, 0x411750)):
            self.assertRegex(
                retire,
                rf'lda\.l \$7E{host:04X}\s+'
                rf'beq S6Normal_RetireReplacedBound__\w+\s+'
                rf'clc\s+adc #\$6000\s+'
                rf'S6Normal_RetireReplacedBound__\w+:\s+'
                rf'sta\.l \${worker:06X}',
            )

    def test_campaign_autofight_resumes_forward_traversal_without_live_targets(self):
        fixture = (ROOT / 'tools/verify/game_s8_normal_campaign.py').read_text()
        branch = fixture.split('            if not targets:\n', 1)[1]
        branch = branch.split('\n            _distance, slot, dx, dy = min(targets)', 1)[0]
        self.assertIn('self.BTN_LEFT if _traversal_direction == "left"', branch)
        self.assertIn('else self.BTN_RIGHT', branch)
        self.assertNotIn('return buttons', branch)

    def test_campaign_autofight_attacks_biker_at_forward_stage_edge(self):
        fixture = (ROOT / 'tools/verify/game_s8_normal_campaign.py').read_text()
        branch = fixture.split('            biker_contact = (\n', 1)[1]
        branch = branch.split('\n            if chase_axis == "x":', 1)[0]
        self.assertIn('bool(native_biker_targets) and not worker_targets', branch)
        self.assertIn('abs(dx) <= 32 and abs(dy) <= 12', branch)
        self.assertIn('None if biker_contact', branch)

    def test_campaign_autofight_run_chase_is_opt_in_real_input(self):
        fixture = (ROOT / 'tools/verify/game_s8_normal_campaign.py').read_text()
        self.assertIn('S8_NORMAL_AUTOFIGHT_RUN_CHASE', fixture)
        self.assertIn(
            'if (_autofight_run_chase and chase_axis is not None', fixture
        )
        self.assertIn('combat_buttons |= self.BTN_B', fixture)
        self.assertIn('and native_biker_targets and not worker_targets', fixture)

    def test_campaign_autofight_closes_horizontally_inside_melee_depth_band(self):
        fixture_path = ROOT / 'tools/verify/game_s8_normal_campaign.py'
        spec = importlib.util.spec_from_file_location(
            '_s8_normal_melee_depth_fixture', fixture_path)
        fixture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture)
        self.assertEqual(fixture._autofight_chase_axis(-141, 9), 'x')
        self.assertEqual(fixture._autofight_chase_axis(-13, 9), 'attack')
        self.assertEqual(fixture._autofight_chase_axis(-24, 12), 'attack')
        self.assertEqual(fixture._autofight_chase_axis(-141, 13), 'y')
        self.assertEqual(fixture._autofight_chase_axis(-20, 13), 'y')

    def test_campaign_autofight_falls_back_to_native_mode2_targets(self):
        fixture_path = ROOT / 'tools/verify/game_s8_normal_campaign.py'
        spec = importlib.util.spec_from_file_location(
            '_s8_normal_native_target_fixture', fixture_path)
        fixture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture)
        worker = [(1, 7, -13, 9)]
        biker = [(2, 4, 50, 0)]
        native_combat = [(3, 2, -100, 8)]
        props = [(4, 3, 0, 0)]
        self.assertEqual(fixture._autofight_select_targets(
            worker, biker, native_combat, props), worker)
        self.assertEqual(fixture._autofight_select_targets(
            [], biker, native_combat, props), biker)
        self.assertEqual(fixture._autofight_select_targets(
            [], [], native_combat, props), native_combat)
        self.assertEqual(fixture._autofight_select_targets(
            [], [], [], props), props)

    def test_campaign_autofight_steers_both_native_player_ports(self):
        fixture = (ROOT / 'tools/verify/game_s8_normal_campaign.py').read_text()
        body = fixture.split('        def _autofight_choose_buttons', 1)[1]
        body = body.split('\n        def _autofight_control_set', 1)[0]
        self.assertIn('if port not in (0, 1)', body)
        self.assertIn('_autofight_context_base + port * 0x100', body)
        self.assertIn('(1 - port) * _autofight_npc_stride', body)
        self.assertIn('_autofight_biker_attack_state[port]', body)
        self.assertIn('_autofight_attack_state[port]', body)
        controls = fixture.split('        def _autofight_control_set', 1)[1]
        controls = controls.split('\n        _session.set_input =', 1)[0]
        self.assertIn('_autofight_two_player = "--two-player" in sys.argv', fixture)
        self.assertIn('player_two = _autofight_choose_buttons(self, 0, 1)', controls)
        self.assertIn('_autofight_base_set_input(\n                        self, player_two, frames, port=1', controls)
        self.assertIn('if game_state == 0:', controls)

    def test_campaign_autofight_preserves_native_out_continue_edges(self):
        fixture = (ROOT / 'tools/verify/game_s8_normal_campaign.py').read_text()
        body = fixture.split('        def _autofight_choose_buttons', 1)[1]
        body = body.split('\n        def _autofight_control_set', 1)[0]
        self.assertIn('_autofight_symbol("G13_P1Out")', fixture)
        self.assertIn('_autofight_symbol("G13_P2Out")', fixture)
        self.assertIn('if buttons & self.BTN_START:', body)
        self.assertIn('if out:', body)
        self.assertIn('return self.BTN_START', body)
        self.assertIn('_autofight_out_addresses[port]', body)
        self.assertLess(body.index('if buttons & self.BTN_START:'),
                        body.index('worker_contexts = self.read_memory('))

    def test_campaign_autofight_does_not_preserve_x_over_live_targets(self):
        fixture = (ROOT / 'tools/verify/game_s8_normal_campaign.py').read_text()
        guard = fixture.split('            if (buttons & self.BTN_X and not worker_targets', 1)[1]
        guard = guard.split('\n            targets =', 1)[0]
        self.assertIn('not native_biker_targets', guard)
        self.assertIn('not native_combat_targets', guard)
        self.assertIn('not native_targets', guard)
        self.assertIn('return buttons', guard)

    def test_worker_absence_does_not_short_circuit_native_player_stock(self):
        source = (ROOT / 'src/core/actor_source_host.pasm').read_text()
        body = source.split('S6Host_RemoveHandle:\n', 1)[1]
        body = body.split('\nS6Host_RemoveHandle__bad:', 1)[0]
        self.assertIn('jsl S6Host_ClearRemovedReferences', body)
        self.assertNotIn('sta.l G13_P1Out', body)
        self.assertNotIn('sta.l G13_P2Out', body)
        self.assertIn('G13_SourcePlayerDeathP1/P2', source)

    def test_world_camera_loss_check_uses_the_actor_inverse_policy(self):
        source = (ROOT / 'src/core/actor_source_host.pasm').read_text()
        body = source.split('S6_WorldLost:\n', 1)[1]
        body = body.split('\nS6_WorldGravity:', 1)[0]
        self.assertLess(body.index('lda.l Screen_PosX'),
                        body.index('jsl S6Bridge_UnprojectPolicy'))
        self.assertNotIn('jsl S6Bridge_Unproject\n', body)

    def test_native_respawn_rebinds_only_a_missing_live_player(self):
        source = NORMAL_RUNTIME.read_text()
        seam = source.split('S6Normal_RenderHook__ready:\n', 1)[1]
        self.assertIn('jsl S6Normal_RebindReturnedPlayers', seam.split(
            '\n; ActorBehavior_Bind entry replacement', 1)[0])
        body = source.split('S6Normal_RebindReturnedPlayer:\n', 1)[1]
        self.assertIn('S6Bridge_Exists,x', body)
        self.assertIn('$7E0A00+CHAR_HP,x', body)
        self.assertIn('$7E0A00+CHAR_INPUT_DRIVEN,x', body)
        self.assertIn('G13_P1Out', body)
        self.assertIn('G13_P2Out', body)
        self.assertIn('jsl S7Resident_Flush', body)
        self.assertIn('jsl S6Host_BindExisting', body)
        self.assertIn('wrong stack', body)
        self.assertIn('jsl S6Normal_SyncBoundContext', body)

    def test_fresh_normal_bind_publishes_existence_before_host_import(self):
        source = NORMAL_RUNTIME.read_text()
        body = source.split('S6Normal_Bind__bind:\n', 1)[1]
        body = body.split('\nS6Normal_Bind__handled:', 1)[0]
        publish = body.index('sta.l S6Bridge_Exists,x')
        bind = body.index('jsl S6Host_BindExisting')
        rollback = body.index('sta.l S6Bridge_Exists,x', bind)
        ready = body.index('S6Normal_Bind__worker_ready:')
        self.assertLess(publish, bind)
        self.assertLess(bind, rollback)
        self.assertLess(rollback, ready)
        self.assertLess(body.rfind('lda #0', bind, rollback), rollback)
        self.assertIn('beq S6Normal_Bind__worker_ready', body)

    def test_remove_handle_clears_actor_scratch_before_unlink_status_checks(self):
        source = HOST.read_text()
        body = source.split('S6Host_RemoveHandle:\n', 1)[1]
        body = body.split('\nS6Host_RemoveHandle__bad:', 1)[0]
        self.assertLess(body.index('stz $FC'), body.index('jsl S6Bridge_Import'))
        self.assertLess(body.index('stz $FC'), body.index('jsl S6_KillUnlinked'))
        self.assertLess(body.index('jsl S6_KillUnlinked'),
                        body.index('jsl S6Bridge_Export'))

    def test_post_load_owner_sweep_admits_late_stage_bootstrap_actors_once(self):
        source = NORMAL_RUNTIME.read_text()
        render = source.split('S6Normal_RenderHook:\n', 1)[1].split(
            'S6Normal_RenderHook__ready:', 1)[0]
        self.assertIn('cmp #2', render)
        self.assertIn('cmp #1', render)
        self.assertIn('cmp #3', render)
        self.assertIn('jsl S6Normal_BindLiveActors', render)
        sweep = source.split('S6Normal_BindLiveActors__slot:\n', 1)[1].split(
            'S6Normal_BindLiveActors__next:', 1)[0]
        self.assertLess(sweep.index('lda.l S6Bridge_Policy,x'),
                        sweep.index('lda CHAR_HP'))
        self.assertIn('bne S6Normal_BindLiveActors__next', sweep)


if __name__ == '__main__':
    unittest.main()
