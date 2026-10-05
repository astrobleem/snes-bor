"""Offline traversal contract tests. No emulator or generated queue artifacts."""
import ast
from copy import deepcopy
import dis
from pathlib import Path
import re
import struct
import sys
import types
import unittest

import game_s8_normal_campaign as harness

sys.path.insert(0, str(harness.ROOT))
import build_rom as build
import actor_s7_persistent_worker as persistent_worker


def retained_code_objects(function):
    """Walk the source-lost verifier's retained CPython code tree."""
    pending = [function.__code__]
    seen = set()
    while pending:
        code = pending.pop()
        if code in seen:
            continue
        seen.add(code)
        yield code
        pending.extend(
            value for value in code.co_consts
            if isinstance(value, types.CodeType)
        )


def retained_inventory(*functions):
    codes = [code for function in functions
             for code in retained_code_objects(function)]
    names = set().union(*(
        set(code.co_names) | set(code.co_varnames) for code in codes
    ))
    strings = {
        value for code in codes for value in code.co_consts
        if isinstance(value, str)
    }
    return names, strings


def retained_child(function, name):
    return next(code for code in retained_code_objects(function)
                if code.co_name == name)


class TraversalTests(unittest.TestCase):
    def test_left_stall_uses_authored_level_progress(self):
        state=dict(stage=19,spawn_index=72,spawn_count=92,next_trigger=2240,
                   stage_true_max_x=3903,camera_x=1952,camera_min_x=943,
                   camera_max_x=1840,spawn_waiting=0,npc_slots=[])
        for _ in range(121):
            harness._traversal_terminal_clamp(state)
        self.assertFalse(harness._traversal_queue_stall_latched)
        state['camera_x']=1663
        for _ in range(121):
            harness._traversal_terminal_clamp(state)
        self.assertTrue(harness._traversal_queue_stall_latched)
        # Reset shared fixture latches so independent contracts stay isolated.
        harness._traversal_terminal_clamp(dict(state,spawn_index=73,next_trigger=3000))


    def test_continue_input_requires_out_player_and_credit(self):
        # Start pauses a live player; credits alone must never trigger it.
        from _game_s8_normal_campaign_base import traversal_continue_needed
        self.assertFalse(traversal_continue_needed(False, 5))
        self.assertFalse(traversal_continue_needed(True, 0))
        self.assertTrue(traversal_continue_needed(True, 5))

    @classmethod
    def setUpClass(cls):
        cls.plan = harness.traversal_plan(build, build.CAMPAIGN_ENTRY_MAPS['BOR_NORMAL_1A_INTERNAL'])

    def setUp(self):
        self._controller_state = {
            name: getattr(harness, name)
            for name in (
                '_traversal_direction', '_traversal_no_progress_latched',
                '_traversal_no_progress_key', '_traversal_group_gate_latched',
                '_traversal_group_gate_stage', '_terminal_stall_latch',
            )
        }
        harness._traversal_direction = 'right'
        harness._traversal_no_progress_latched = False
        harness._traversal_no_progress_key = None
        harness._traversal_group_gate_latched = False
        harness._traversal_group_gate_stage = None
        harness._terminal_stall_latch = None

    def tearDown(self):
        for name, value in self._controller_state.items():
            setattr(harness, name, value)

    def test_sa1_player_observer_uses_context_identity_and_normal_projection(self):
        project = harness.normal_project_worker_coordinate
        self.assertEqual(project(3544), 2835)
        self.assertEqual(project(-3544), -2835)
        self.assertEqual(project(190), 152)
        self.assertEqual(project(-190), -152)
        for native in range(-2000, 2001):
            worker = (abs(native) * 5 + 2) // 4
            worker = -worker if native < 0 else worker
            self.assertEqual(project(worker), native)
        source = (harness.ROOT / 'tools/verify/game_s8_normal_campaign.py').read_text()
        observer = source.split('if os.environ.get("S8_NORMAL_CANONICAL_P1_CONTROLLER")', 1)[1]
        self.assertIn('worker_driver in (8, 9)', observer)
        self.assertIn('worker_type == 1', observer)
        self.assertIn('normal_project_worker_coordinate(source_value)', observer)
        self.assertNotIn('worker_roster == host_roster', observer)

    def test_autofight_projects_canonical_player_before_native_prop_steering(self):
        project = harness.normal_project_worker_coordinate
        canonical_x = project(5150)
        stale_mirror_x = 843
        prop_x = 3152
        self.assertEqual(canonical_x, 4120)
        self.assertGreater(prop_x - stale_mirror_x, 0)
        self.assertLess(prop_x - canonical_x, 0)

        source = (harness.ROOT / 'tools/verify/game_s8_normal_campaign.py').read_text()
        autofight = source.split('def _autofight_choose_buttons', 1)[1].split(
            'def _autofight_control_set', 1)[0]
        self.assertIn(
            'native_player_x = normal_project_worker_coordinate(player_x)',
            autofight,
        )
        self.assertIn(
            'native_player_y = normal_project_worker_coordinate(player_y)',
            autofight,
        )
        self.assertIn('native_player_mirror_x', autofight)
        self.assertIn('native_player_mirror_y', autofight)
        self.assertIn(
            'active_worker_rows = traversal_active_worker_context_rows(',
            autofight,
        )
        self.assertIn('row not in active_worker_rows', autofight)
        self.assertIn('else _autofight_chase_axis(dx, dy)', autofight)
        self.assertIn('if chase_axis == "x":', autofight)
        self.assertIn('elif chase_axis == "y":', autofight)
        self.assertIn('combat_buttons = self.BTN_Y', autofight)

    def test_native_combat_rows_use_native_player_coordinate_domain(self):
        delta = harness.native_combat_target_delta
        self.assertEqual(delta(38, 176, 14, 150), (24, 26))
        self.assertEqual(delta(38, 128, 14, 150), (24, -22))

        source = (harness.ROOT / 'tools/verify/game_s8_normal_campaign.py').read_text()
        autofight = source.split('def _autofight_choose_buttons', 1)[1].split(
            'def _autofight_control_set', 1)[0]
        self.assertIn('if mode == 2:', autofight)
        self.assertIn('native_combat_target_delta(', autofight)

    def test_trailing_player_catches_camera_before_pending_queue(self):
        catchup = harness.traversal_camera_catchup_required
        self.assertTrue(catchup(2533, 2094, True, 'right'))
        self.assertFalse(catchup(3000, 2094, True, 'right'))
        self.assertFalse(catchup(2533, 2094, False, 'right'))
        self.assertFalse(catchup(2533, 2094, True, 'left'))

        source = (harness.ROOT / 'tools/verify/game_s8_normal_campaign.py').read_text()
        autofight = source.split('def _autofight_choose_buttons', 1)[1].split(
            'def _autofight_control_set', 1)[0]
        self.assertIn('traversal_camera_catchup_required(', autofight)

    def test_pending_queue_ignores_props_behind_scroll_direction(self):
        behind_left = (45, 2, 45, 12)
        ahead_left = (60, 3, -60, 8)
        behind_right = (45, 2, -45, 12)
        ahead_right = (60, 3, 60, 8)
        self.assertEqual(harness.traversal_forward_props(
            [behind_left, ahead_left], 'left', True, False), [ahead_left])
        self.assertEqual(harness.traversal_forward_props(
            [behind_right, ahead_right], 'right', True, False), [ahead_right])
        self.assertEqual(harness.traversal_forward_props(
            [behind_left], 'left', False, False), [behind_left])
        self.assertEqual(harness.traversal_forward_props(
            [behind_left], 'left', True, True), [])
        self.assertEqual(harness.traversal_forward_props(
            [behind_left], 'left', True, True, slot_pressure=False), [])
        self.assertEqual(harness.traversal_forward_props(
            [behind_right], 'right', True, True, slot_pressure=False), [])
        self.assertEqual(harness.traversal_forward_props(
            [behind_right], 'right', True, False, slot_pressure=True),
            [behind_right])

        source = (harness.ROOT / 'tools/verify/game_s8_normal_campaign.py').read_text()
        autofight = source.split('def _autofight_choose_buttons', 1)[1].split(
            'def _autofight_control_set', 1)[0]
        self.assertIn('traversal_forward_props(', autofight)
        self.assertIn('occupied_native_slots += 1', autofight)
        self.assertIn('occupied_native_slots >= 5', autofight)
        self.assertIn('self.BTN_LEFT if _traversal_direction == "left"', autofight)

    def test_autofight_turns_toward_close_target_before_attacking(self):
        self.assertEqual(harness.traversal_facing_action(8, True), 'right')
        self.assertEqual(harness.traversal_facing_action(-8, False), 'left')
        self.assertIsNone(harness.traversal_facing_action(8, False))
        self.assertIsNone(harness.traversal_facing_action(-8, True))
        self.assertEqual(harness.traversal_close_facing_action(
            -30, 0, False), 'left')
        self.assertEqual(harness.traversal_close_facing_action(
            30, 0, True), 'right')
        self.assertIsNone(harness.traversal_close_facing_action(
            -33, 0, False))
        self.assertIsNone(harness.traversal_close_facing_action(
            -30, 13, False))
        self.assertEqual(harness.traversal_close_facing_action(
            0, 0, False, last_dx=-8), 'left')
        self.assertEqual(harness.traversal_close_facing_action(
            0, 0, True, last_dx=8), 'right')
        self.assertIsNone(harness.traversal_close_facing_action(
            0, 0, False))

        source = (harness.ROOT / 'tools/verify/game_s8_normal_campaign.py').read_text()
        autofight = source.split('def _autofight_choose_buttons', 1)[1].split(
            'def _autofight_control_set', 1)[0]
        self.assertIn('worker_contexts[player_context + 8]', autofight)
        self.assertIn('traversal_close_facing_action(', autofight)
        self.assertIn('if chase_axis in (None, "attack"):', autofight)
        self.assertIn('previous_target[0] == slot', autofight)
        self.assertIn('return self.BTN_LEFT', autofight)
        self.assertIn('return self.BTN_RIGHT', autofight)

    def test_autofight_ignores_unlinked_worker_contexts(self):
        stride = 133
        bridge = bytearray(5 * stride + 70)

        def set_bridge(slot, policy, exists, context):
            base = slot * stride
            bridge[base + 64] = policy
            bridge[base + 65] = exists
            bridge[base + 68:base + 70] = context.to_bytes(2, 'little')

        set_bridge(0, 2, 1, 0x1900)  # live player binding
        set_bridge(1, 2, 1, 0x1B00)  # live source actor bound to worker row 2
        set_bridge(2, 2, 0, 0x1A00)  # unlinked actor; stale worker row 1
        set_bridge(3, 1, 1, 0x1C00)  # compatibility actor, not source-owned

        self.assertEqual(
            harness.traversal_active_worker_context_rows(
                bridge, stride, 0x1900
            ),
            {0, 2},
        )

    def test_attack_controller_emits_real_repeated_press_edges(self):
        pulse = harness.traversal_pulse_attack
        phase = 0
        held = []
        for _ in range(9):
            buttons, phase = pulse(0x880, phase, 0x800, 8)
            held.append(bool(buttons & 0x800))
        self.assertEqual(held, [True, True, True, True, True, True, False, True, True])
        self.assertEqual(pulse(0x80, phase, 0x800), (0x80, phase))
        self.assertEqual(pulse(0x880, phase, 0x800, 1), (0x880, phase))
        source = (harness.ROOT / 'tools/verify/game_s8_normal_campaign.py').read_text()
        self.assertIn('if os.environ.get("S8_NORMAL_PULSE_ATTACK") == "1"', source)
        self.assertIn('buttons &= ~attack_mask', source)

    def test_autofight_melee_range_clears_native_collision_standoff(self):
        # Native movement stops at a measured 27px separation from the Biker
        # blocker in stage 2; 24px caused the fixture to push into collision
        # forever instead of issuing a real attack.
        self.assertEqual(harness._autofight_chase_axis(27, 2), "attack")
        self.assertEqual(harness._autofight_chase_axis(-27, -2), "attack")

    def test_fixture_stock_seed_is_one_shot_and_normal_play_only(self):
        due = harness.traversal_campaign_stock_seed_due
        self.assertTrue(due(0, 3, False))
        self.assertFalse(due(0, 3, True))
        self.assertFalse(due(0, 2, False))
        self.assertFalse(due(1, 3, False))

    def test_all_source_spawns_and_control_order(self):
        self.assertEqual(sum(row['spawn'] for row in self.plan), 614)
        self.assertEqual(len({row['stage'] for row in self.plan}), 14)
        self.assertGreater(len(self.plan), 614)
        for physical in {row['stage'] for row in self.plan}:
            rows = [row for row in self.plan if row['stage'] == physical]
            self.assertEqual([row['index'] for row in rows], list(range(len(rows))))
            for row in rows:
                self.assertEqual(len(bytes.fromhex(row['record'])), 10)
                if row['spawn']:
                    self.assertTrue(row['source_definition'])
                    self.assertTrue(row['source_model'])
                    self.assertEqual(bytes.fromhex(row['record'])[9], row['roster'])

    def test_camera_hold_uses_greatest_authored_trigger(self):
        stage_3a = [row for row in self.plan if row['stage'] == 26]
        triggers = [struct.unpack_from('<H', bytes.fromhex(row['record']))[0]
                    for row in stage_3a]
        self.assertGreater(max(triggers), triggers[-1],
                           'Normal 3A must retain its non-monotonic authored queue regression')

        spawn = (harness.ROOT / 'src/core/spawn.pasm').read_text()
        scan = spawn.split('Spawn_Init__max_trigger:', 1)[1].split(
            '; Spawn_Play --', 1)[0]
        for instruction in ('lda.l SpawnTable_Wram,x',
                            'cmp.l Spawn_LastTriggerX',
                            'sta.l Spawn_LastTriggerX',
                            'adc #10',
                            'cmp.l Spawn_CountX8',
                            'bcc Spawn_Init__max_trigger'):
            self.assertIn(instruction, scan)

    def test_diagnostic_stage_entry_retries_a_real_showcomplete_action_edge(self):
        # The source-backed verifier no longer needs a bytecode patch;
        # retain the actual action-edge contract.
        instructions = list(dis.get_instructions(harness._impl.run.__code__))
        anchor = next(i for i, item in enumerate(instructions)
                      if item.opname == 'STORE_FAST'
                      and item.argval == 'start_advance_before')
        action = next(item for item in instructions[anchor + 1:]
                      if item.opname == 'LOAD_ATTR'
                      and item.argval in ('BTN_A', 'BTN_START'))
        self.assertEqual(action.argval, 'BTN_A')

    def test_stage_entry_releases_prior_real_traversal_input(self):
        names, strings = retained_inventory(harness._impl.run)
        tick = retained_child(harness._impl.run, 'tick')
        self.assertIn('release_input', names)
        self.assertIn('hold_input', tick.co_names)
        self.assertIn('run_frames_exact', names)
        self.assertIn('stage', strings)

    def test_resident_world_gravity_does_not_treat_scratch_as_hazard(self):
        host = (harness.ROOT / 'src/core/actor_source_host.pasm').read_text()
        gravity = host.split('S6_WorldGravity:', 1)[1].split('S6_WorldAttack:', 1)[0]
        self.assertIn('StageBoundsHost_Physics/Enter', gravity)
        self.assertNotIn('lda $C2', gravity)
        self.assertNotIn('S6Host_EnvironmentBlocked', gravity)
        game = (harness.ROOT / 'src/core/game_state.pasm').read_text()
        self.assertIn('jsl StageBoundsHost_Physics', game)

    def test_spawn_stall_watchdog_restarts_at_each_stage(self):
        self.assertEqual(harness.observer_stale_fields(25, 24, 2400, 1700), 0)
        self.assertEqual(harness.observer_stale_fields(25, 25, 181, 100), 81)
        self.assertTrue(harness.observer_spawn_watchdog_due(21, 22, 120, 120))
        self.assertFalse(harness.observer_spawn_watchdog_due(22, 22, 120, 120))
        self.assertEqual(harness.TRAVERSAL_STALL_LIMIT_FIELDS, 1800)
        self.assertFalse(harness.observer_spawn_watchdog_due(
            83, 84, 600, harness.TRAVERSAL_STALL_LIMIT_FIELDS))
        self.assertTrue(harness.observer_spawn_watchdog_due(
            83, 84, 1800, harness.TRAVERSAL_STALL_LIMIT_FIELDS))

    def test_damage_retirement_filters_only_the_matching_initial_ai(self):
        manifest = (
            '27 1 133 1 2 2\n'
            '27 2 389 2 3 2\n'
            '27 -1\n'
            '28 1 133 1 2 2\n'
            '28 -1\n'
        )
        damaged = {(27, 1, 1, 2)}
        self.assertEqual(
            harness._filter_damaged_initial_ai_rows(manifest, damaged),
            '27 2 389 2 3 2\n27 -1\n28 1 133 1 2 2\n28 -1\n',
        )
        self.assertEqual(
            harness._filter_damaged_initial_ai_rows(manifest, set()), manifest
        )

    def test_normal_source_clock_counts_busy_physical_fields(self):
        root = harness.ROOT
        fixture = (root / 'src/core/actor_s6_world_fixture.pasm').read_text()
        runtime = (root / 'src/core/actor_s8_normal_sa1_runtime.pasm').read_text()
        clock_body = fixture.split('S6Game_PlayRender__measure:', 1)[1].split(
            'S6Game_PlayRender__return:', 1)[0]
        self.assertIn('lda.l StageTimer_FieldCounter', clock_body)
        self.assertNotIn('lda.l Nmi_FrameCounter', clock_body)
        self.assertIn('cmp #$8000', clock_body)
        self.assertIn('lda #120', clock_body)
        self.assertIn('S6Game_BatchCount = $7E5922', fixture)
        self.assertIn('adc.l S6Game_BatchCount', clock_body)
        self.assertIn('S6Game_BatchParity = $7E5924', fixture)
        self.assertNotIn('$7E177A', clock_body)
        self.assertNotIn('$7E177C', clock_body)
        self.assertNotIn('sta.l S6Host_Error',
                         clock_body.split('S6Game_PlayRender__delta_valid:', 1)[1])
        self.assertIn('lda.l StageTimer_FieldCounter', runtime)
        self.assertIn('Nmi_FrameCounter intentionally excludes skipped presentation commits',
                      clock_body)

    def test_normal_actor_bind_uses_the_worker_tick_epoch(self):
        host = (harness.ROOT / 'src/core/actor_source_host.pasm').read_text()
        clock_start = 'lda.l Game_CampaignId\n    and #$00FF\n    cmp #3'
        clock = clock_start + host.split(clock_start, 1)[1].split(
            '\nS6Host_BindExisting__clock_legacy:', 1)[0]
        self.assertIn('lda.l Game_CampaignId', clock)
        self.assertIn('cmp #3', clock)
        self.assertIn('lda.l S6Game_TickCommit', clock)
        self.assertIn('lda.l S6Game_TickCommit+2', clock)
        self.assertIn('S6Host_BindExisting__clock_legacy', clock)
        legacy = host.split('\nS6Host_BindExisting__clock_legacy:', 1)[1].split(
            'S6Host_BindExisting__clock_ready:', 1)[0]
        self.assertIn('lda.l $7E173C', legacy)
        self.assertNotIn('lda.l S6Host_Mode', clock)

    def test_blocker_targeting_prefers_forward_props(self):
        behind = (1, 128, 184, 2, 21, 3, 4)
        ahead = (2, 881, 184, 3, 21, 3, 4)
        self.assertLess(harness.traversal_target_key(ahead, 295, 184, 'right'),
                        harness.traversal_target_key(behind, 295, 184, 'right'))
        self.assertLess(harness.traversal_target_key(behind, 700, 184, 'left'),
                        harness.traversal_target_key(ahead, 700, 184, 'left'))
        self.assertLess(harness.traversal_target_key((1, 700, 120, 2, 21, 3, 4),
                                                     700, 184, 'up'),
                        harness.traversal_target_key((2, 700, 220, 3, 21, 3, 4),
                                                     700, 184, 'up'))
        self.assertLess(harness.traversal_target_key((1, 700, 220, 2, 21, 3, 4),
                                                     700, 184, 'down'),
                        harness.traversal_target_key((2, 700, 120, 3, 21, 3, 4),
                                                     700, 184, 'down'))

    def test_terminal_full_slot_stall_can_reach_authored_destructible_prop(self):
        near = (1, 900, 150, 2, 21, 3, 4)
        far = (2, 1200, 190, 3, 20, 3, 4)
        diagonal_blocker = (4, 328, 140, 5, 19, 3, 4)
        nondestructible = (3, 880, 150, 4, 22, 5, 4)
        self.assertEqual(harness.traversal_blocking_props(
            [near, far, nondestructible], 850, 150, 3, False), [near])
        self.assertEqual(harness.traversal_blocking_props(
            [diagonal_blocker], 231, 172, 3, False), [diagonal_blocker])
        self.assertEqual(harness.traversal_blocking_props(
            [far, nondestructible], 850, 21, 3, False), [])
        self.assertEqual(harness.traversal_blocking_props(
            [far, nondestructible], 850, 21, 3, True), [far])
        self.assertEqual(harness.traversal_blocking_props(
            [nondestructible], 850, 21, 3, True), [])

    def test_terminal_stall_clears_props_even_if_hp_mirror_sees_a_free_slot(self):
        self.assertTrue(harness.traversal_terminal_prop_clear_required(
            False, True, True))
        self.assertFalse(harness.traversal_terminal_prop_clear_required(
            False, True, False))
        self.assertFalse(harness.traversal_terminal_prop_clear_required(
            False, False, True))
        self.assertTrue(harness.traversal_terminal_prop_clear_required(
            True, False, False))

    def test_grounded_prop_bypass_uses_depth_lane_and_forward_motion(self):
        self.assertEqual(harness.traversal_prop_bypass_action(0), 'depth_down')
        self.assertEqual(harness.traversal_prop_bypass_action(48), 'depth_up')
        self.assertEqual(harness.traversal_prop_bypass_action(49), 'forward')
        self.assertEqual(harness.traversal_prop_bypass_action(-48), 'depth_down')
        self.assertEqual(harness.traversal_prop_bypass_action(-49), 'forward')

    def test_stalled_queue_does_not_chase_nonblocking_enemy_behind_camera(self):
        behind = (100, 1, 54, 150, 2, 21, 2, 64, True, False)
        blocking = (20, 1, 180, 178, 2, 21, 2, 64, True, False)
        diagonal_blocking = (20, 1, 296, 128, 2, 21, 2, 64, True, False)
        self.assertFalse(harness.traversal_combat_target_blocks(
            behind, 209, 188, False, False))
        self.assertTrue(harness.traversal_combat_target_blocks(
            blocking, 209, 188, False, False))
        self.assertTrue(harness.traversal_combat_target_blocks(
            diagonal_blocking, 212, 77, False, False))
        vertical_behind = (20, 1, 16, 144, 2, 21, 2, 64, False, False)
        vertical_forward = (20, 1, 40, 250, 2, 21, 2, 64, False, False)
        self.assertFalse(harness.traversal_combat_target_blocks(
            vertical_behind, 3, 207, False, False, 'down'))
        self.assertTrue(harness.traversal_combat_target_blocks(
            vertical_forward, 3, 207, False, False, 'down'))
        forward_contact = (155, 1, 312, 128, 2, 21, 2, 64, False, False)
        self.assertTrue(harness.traversal_combat_target_blocks(
            forward_contact, 155, 137, False, False, 'right'))
        start_lane_blocker = (98, 1, 312, 160, 2, 29, 2, 64, False, False)
        self.assertTrue(harness.traversal_combat_target_blocks(
            start_lane_blocker, 214, 4, False, False, 'right'))
        self.assertTrue(harness.traversal_combat_target_blocks(
            behind, 209, 188, False, True))
        self.assertTrue(harness.traversal_combat_target_blocks(
            behind, 209, 188, True, False))

    def test_stalled_queue_reacquires_behind_enemy_using_input_mode_field(self):
        # The fifth tuple field is object_num (5 here); input mode is field 6.
        # This reproduces the 4A stall where the player had passed a live
        # opponent and the old fixture filter mistook object_num for its mode.
        behind = (74, 4, 2508, 184, 5, 31, 2, 58, False, False)
        old_no_progress = harness._traversal_no_progress_latched
        old_group_gate = harness._traversal_group_gate_latched
        try:
            harness._traversal_no_progress_latched = False
            harness._traversal_group_gate_latched = False
            self.assertFalse(harness.traversal_combat_target_blocks(
                behind, 3270, 6, False, False, 'right'))

            harness._traversal_no_progress_latched = True
            self.assertTrue(harness.traversal_combat_target_blocks(
                behind, 3270, 6, False, False, 'right'))
            self.assertTrue(harness.traversal_combat_engagement_needed(
                behind, 3270, 6, direction='right'))
        finally:
            harness._traversal_no_progress_latched = old_no_progress
            harness._traversal_group_gate_latched = old_group_gate

    def test_forward_combat_blocker_is_engaged_during_transit(self):
        forward = (155, 1, 312, 128, 2, 21, 2, 64, False, False)
        distant = (500, 1, 900, 400, 2, 21, 2, 64, False, False)
        self.assertTrue(harness.traversal_combat_engagement_needed(
            forward, 155, 137, direction='right'))
        self.assertFalse(harness.traversal_combat_engagement_needed(
            distant, 155, 137, direction='right'))
        self.assertTrue(harness.traversal_combat_engagement_needed(
            distant, 155, 137, group_gate_blocked=True, direction='right'))

    def test_traversal_engagement_is_not_limited_to_spawn_stalls(self):
        target = (155, 1, 312, 128, 2, 21, 2, 64, False, False)
        distant = (500, 1, 900, 400, 2, 21, 2, 64, False, False)
        self.assertTrue(harness.traversal_combat_engagement_needed(
            target, 155, 137, direction='right'))
        self.assertFalse(harness.traversal_combat_engagement_needed(
            distant, 155, 137, direction='right'))
        names, _ = retained_inventory(harness._impl.run)
        self.assertIn('traversal_combat_engagement_needed', names)

    def test_authored_group_gate_chases_enough_live_enemies(self):
        self.assertTrue(harness.traversal_group_gate_blocks_spawn(2, 2))
        self.assertFalse(harness.traversal_group_gate_blocks_spawn(1, 2))
        self.assertFalse(harness.traversal_group_gate_blocks_spawn(2, 100))
        self.assertFalse(harness.traversal_group_gate_blocks_spawn(0, 0))

    def test_combat_chase_aligns_lane_before_contact_standoff(self):
        self.assertEqual(harness.traversal_chase_axis(-415, -13), 'x')
        self.assertEqual(harness.traversal_chase_axis(98, 156), 'y')
        self.assertEqual(harness.traversal_chase_axis(129, 156), 'y')
        self.assertEqual(harness.traversal_chase_axis(161, 156), 'x')
        self.assertEqual(harness.traversal_chase_axis(32, 27), 'y')
        self.assertEqual(harness.traversal_chase_axis(-18, 6), 'attack')
        self.assertEqual(harness._autofight_chase_axis(32, 27), 'y')
        self.assertEqual(harness._autofight_chase_axis(26, 8), 'attack')
        self.assertEqual(harness._autofight_chase_axis(24, 12), 'attack')
        self.assertFalse(harness.traversal_combat_attack_opportunity(158, 14))
        self.assertFalse(harness.traversal_combat_attack_opportunity(193, 14))
        self.assertFalse(harness.traversal_combat_attack_opportunity(158, 33))

    def test_authored_wait_is_terminal_even_before_camera_max(self):
        self.assertTrue(harness.traversal_terminal_clamp(dict(
            spawn_waiting=1, camera_x=231, camera_min_x=0, camera_max_x=232)))
        self.assertTrue(harness.traversal_terminal_clamp(dict(
            spawn_waiting=0, camera_x=232, camera_min_x=0, camera_max_x=232)))
        self.assertFalse(harness.traversal_terminal_clamp(dict(
            spawn_waiting=0, camera_x=231, camera_min_x=0, camera_max_x=232)))

    def test_traversal_waits_for_sampled_camera_when_player_runs_ahead(self):
        self.assertFalse(harness.traversal_camera_wait(350, 200, 256, 'right'))
        self.assertTrue(harness.traversal_camera_wait(500, 200, 256, 'right'))
        self.assertTrue(harness.traversal_camera_wait(2400, 2500, 256, 'left'))
        self.assertFalse(harness.traversal_camera_wait(2700, 2500, 256, 'left'))

    def test_biker_attack_alternation_uses_both_real_attack_buttons(self):
        self.assertEqual(harness.traversal_biker_attack_mask(0, 0x40, 0x04), 0x40)
        self.assertEqual(harness.traversal_biker_attack_mask(4, 0x40, 0x04), 0x04)
        self.assertEqual(harness.traversal_biker_attack_mask(8, 0x40, 0x04), 0x40)

    def test_biker_drive_clamps_before_reversing_at_world_edges(self):
        source = (harness.ROOT / 'src/core/jump.pasm').read_text()
        drive = source.split('Anim_BikerDrive:', 1)[1].split(
            'Anim_EnterHole:', 1)[0]
        self.assertIn('cmp.l WorldMaxX', drive)
        self.assertIn('lda.l WorldMaxX\n    sta CHAR_POS_X', drive)
        self.assertIn('cmp #2\n    bcc Anim_BikerDrive__left_clamp', drive)
        self.assertIn('Anim_BikerDrive__left_clamp:\n    lda #0\n'
                      '    sta CHAR_POS_X', drive)
        self.assertNotIn('bpl Anim_BikerDrive__done', drive)

    def test_authored_prop_lane_and_collision_standoff_actions(self):
        self.assertEqual(harness.traversal_prop_chase_action(118, -22, False), 'bypass')
        self.assertEqual(harness.traversal_prop_chase_action(92, 0, False), 'bypass')
        self.assertEqual(harness.traversal_prop_chase_action(118, -22, True), 'approach')
        self.assertIsNone(harness.traversal_prop_chase_action(118, 5, True))
        self.assertEqual(harness.traversal_prop_chase_action(144, -22, True), 'approach')
        self.assertEqual(harness.traversal_prop_chase_action(54, 5, True), 'detour')
        self.assertEqual(harness.traversal_prop_chase_action(54, -24, True), 'approach')
        self.assertEqual(harness.traversal_prop_chase_action(24, -24, True), 'lane')
        self.assertEqual(harness.traversal_prop_chase_action(24, 5, True), 'attack')
        self.assertEqual(harness.traversal_prop_chase_action(54, 5, False), 'bypass')
        self.assertIsNone(harness.traversal_prop_chase_action(200, 22, False))
        self.assertEqual(harness.traversal_prop_chase_action(930, -6, True), 'approach')
        self.assertFalse(harness.traversal_prop_bypass_complete(100, 132, -1))
        self.assertTrue(harness.traversal_prop_bypass_complete(80, 132, -1))
        self.assertTrue(harness.traversal_prop_bypass_complete(190, 132, 1))

    def test_traversal_collects_real_survival_pickups(self):
        self.assertTrue(harness.traversal_pickup_needed(4, 64, 64))
        self.assertTrue(harness.traversal_pickup_needed(1, 20, 64))
        self.assertTrue(harness.traversal_pickup_needed(2, 20, 64))
        self.assertFalse(harness.traversal_pickup_needed(1, 64, 64))
        self.assertFalse(harness.traversal_pickup_needed(3, 20, 64))
        self.assertEqual(harness.traversal_pickup_action(80, 2, 0),
                         ('approach_right', False))
        old_direction = harness._traversal_direction
        old_stalled = harness._traversal_no_progress_latched
        try:
            harness._traversal_direction = 'right'
            harness._traversal_no_progress_latched = False
            self.assertEqual(harness.traversal_pickup_action(-10, 20, 0),
                             ('depth_down', False))
            self.assertEqual(harness.traversal_pickup_action(-10, 2, 0),
                             ('collect', True))
        finally:
            harness._traversal_direction = old_direction
            harness._traversal_no_progress_latched = old_stalled
        oneups = [row for row in self.plan
                  if row['stage'] == 28 and row['source_model'] == '1up']
        self.assertTrue(oneups, 'Normal 3C authors a real 1UP that traversal must collect')
        names, strings = retained_inventory(harness._impl.run)
        self.assertIn('traversal_pickup_action', names)
        self.assertIn('traversal_pickup_needed', names)
        self.assertIn('pickup_interactions', strings)

    def test_prop_bypass_stays_grounded_and_slotfull_props_are_cleared(self):
        self.assertTrue(harness.traversal_jump_held(0))
        self.assertTrue(harness.traversal_jump_held(5))
        self.assertFalse(harness.traversal_jump_held(6))
        self.assertFalse(harness.traversal_jump_held(11))
        self.assertEqual(harness.traversal_prop_bypass_action(4), 'depth_up')
        self.assertEqual(harness.traversal_prop_bypass_action(-4), 'depth_down')
        self.assertEqual(harness.traversal_prop_bypass_action(60), 'forward')
        names, strings = retained_inventory(harness._impl.run)
        self.assertIn('traversal_prop_bypass_action', names)
        self.assertIn('traversal_terminal_prop_clear_required', names)
        self.assertIn('traversal_jump_held', names)
        self.assertIn('prop_interactions', strings)
        self.assertIn('hold_input', names)

    def test_event_relay_cannot_overwrite_asynchronous_producer_scratch(self):
        drain = persistent_worker._event_drain(
            {'S6Host_RemoveHandle': 0x018000, 'S7_QueueHitSfxLong': 0x008000},
            {'StageEnv_Actors': 0x7E4000, 'CHAR_ZP_LEN': 0x85})
        producer_private = set(range(0x412436, 0x412440))
        stores = {int(address, 16) for address in
                  re.findall(r'\b(?:sta|stx|sty)\.l \$([0-9A-F]{6})', drain)}
        self.assertFalse(stores & producer_private)
        unlink = drain.split('Relay_DrainEvents__unlink:', 1)[1]
        address = int(re.search(r'sbc #\$6000\s+;[^\n]*\n(?:\s*;[^\n]*\n)*\s*sta\.l \$([0-9A-F]{6})', unlink).group(1), 16)
        # Reproduce the observed interleave: SA-1 saves the attacking player
        # D, S-CPU handles the prior unlink, then SA-1 copies D into its row.
        memory = {0x41243C: 0x7900}
        memory[address] = 0x7E00 - 0x6000
        self.assertEqual(memory[0x41243C], 0x7900)

    def test_event_unlink_defers_on_busy_removal_mailbox_without_ack(self):
        drain = persistent_worker._event_drain(
            {'S6Host_RemoveHandle': 0x018000,
             'S7_QueueHitSfxLong': 0x008000},
            {'StageEnv_Actors': 0x7E4000, 'CHAR_ZP_LEN': 0x85})
        busy = drain.index('cmp #24')
        defer = drain.index('jml Relay_DrainEvents__done', busy)
        ack = drain.index('Relay_DrainEvents__ack:')
        tail_advance = drain.index('inc a', ack)
        self.assertLess(busy, defer)
        self.assertLess(defer, ack)
        self.assertLess(ack, tail_advance)
        self.assertIn('sta.l $7E1764\n    jml Relay_DrainEvents__done', drain[busy:ack])
        self.assertIn('Relay_DrainEvents__unlink_fault:\n    jml Relay_DrainEvents__fault', drain)

    def test_unlink_for_already_retired_bridge_is_acknowledged_safely(self):
        drain = persistent_worker._event_drain(
            {'S6Host_RemoveHandle': 0x018000,
             'S7_QueueHitSfxLong': 0x008000},
            {'StageEnv_Actors': 0x7E4000, 'CHAR_ZP_LEN': 0x85})
        unlink = drain.index('Relay_DrainEvents__unlink:')
        find = drain.index('Relay_DrainEvents__find:', unlink)
        miss = drain.index('Relay_DrainEvents__stale_unlink:', find)
        ack = drain.index('Relay_DrainEvents__ack:', miss)
        self.assertIn('cmp #$1900\n    bcc Relay_DrainEvents__fault', drain[unlink:find])
        self.assertIn('cmp #$1F00\n    bcs Relay_DrainEvents__fault', drain[unlink:find])
        self.assertIn('and #$00FF\n    bne Relay_DrainEvents__fault', drain[unlink:find])
        self.assertLess(find, miss)
        self.assertIn('jml Relay_DrainEvents__ack', drain[miss:ack])
        self.assertNotIn('S6Host_RemoveHandle', drain[miss:ack])

    def test_queue_capacity_matches_native_slot_busy_policy(self):
        rows = [dict(hp=0 if slot < 4 else 4, input=2, object_live=True)
                for slot in range(5)]
        self.assertFalse(harness.traversal_slots_full(rows, 7))
        rows = [dict(hp=4, input=3, object_live=True) for _ in range(5)]
        self.assertTrue(harness.traversal_slots_full(rows, 7))
        rows[2].update(hp=0, input=2)
        self.assertFalse(harness.traversal_slots_full(rows, 7))
        rows[2].update(hp=0, input=7, object_live=True)
        self.assertTrue(harness.traversal_slots_full(rows, 7))

    def test_worker_retirement_requires_live_source_exact_bridge(self):
        self.assertTrue(harness.bridge_owns_source_actor(2, 1, 0x1900, 2, 1, 0x1900))
        self.assertTrue(harness.bridge_owns_source_actor(2, 1, 0x1E00, 2, 1, 0x1E00))
        self.assertFalse(harness.bridge_owns_source_actor(0, 1, 0x1900, 2, 1, 0x1900))
        self.assertFalse(harness.bridge_owns_source_actor(2, 0, 0x1900, 2, 1, 0x1900))
        self.assertFalse(harness.bridge_owns_source_actor(2, 1, 0, 2, 1, 0))
        self.assertFalse(harness.bridge_owns_source_actor(2, 1, 0x1901, 2, 1, 0x1901))
        self.assertFalse(harness.bridge_owns_source_actor(2, 1, 0x1900, 0, 0, 0))
        self.assertFalse(harness.bridge_owns_source_actor(2, 1, 0x1900, 2, 0, 0x1900))
        self.assertFalse(harness.bridge_owns_source_actor(2, 1, 0x1900, 2, 1, 0x1A00))

    def test_native_biker_target_uses_native_actor_and_player_coordinates(self):
        source = (1061, 160)
        native = (1164, 132)
        self.assertEqual(harness.traversal_actor_coordinates(4, False, 2, source, native),
                         native)
        # A stale worker row must not take over the special native Biker path.
        self.assertEqual(harness.traversal_actor_coordinates(4, True, 2, source, native),
                         native)
        self.assertEqual(harness.traversal_actor_coordinates(2, True, 2, source, native),
                         source)
        self.assertEqual(harness.traversal_actor_coordinates(2, False, 2, source, native),
                         native)
        self.assertEqual(harness.traversal_signed16(0xFFF0), -16)
        self.assertEqual(harness.traversal_signed16(0x0010), 16)
        self.assertTrue(harness.traversal_biker_approaches(625, -16, False))
        self.assertFalse(harness.traversal_biker_approaches(625, -16, True))
        self.assertTrue(harness.traversal_biker_approaches(-16, 625, True))
        self.assertFalse(harness.traversal_biker_approaches(-16, 625, False))

    def test_biker_pursuit_closes_distance_before_real_melee(self):
        self.assertEqual(harness.traversal_biker_action(-794, -66, 0),
                         'approach_left')
        self.assertFalse(harness.traversal_biker_attack_window(-80, 12))
        self.assertTrue(harness.traversal_biker_attack_window(-20, 12))
        self.assertFalse(harness.traversal_biker_attack_window(-20, 17))
        self.assertFalse(harness.traversal_biker_attack_window(-40, 12))
        self.assertEqual(harness.traversal_biker_action(24, -13, 0), 'depth_up')
        self.assertEqual(harness.traversal_biker_action(24, 4, 0), 'attack_right')
        self.assertEqual(harness.traversal_biker_action(-24, 4, 6), 'face_left')
        self.assertEqual(harness.traversal_biker_action(-40, 4, 0), 'approach_left')
        self.assertEqual(harness.traversal_biker_action(-80, 4, 0), 'approach_left')
        self.assertEqual(harness.traversal_biker_action(-80, 4, 0, mobile=False),
                         'approach_left')
        self.assertEqual(harness.traversal_biker_action(
            -65, 4, 0, mobile=True, approaching=False), 'approach_left')
        self.assertEqual(harness.traversal_biker_action(
            -65, 12, 0, mobile=True, approaching=False), 'depth_down')
        self.assertEqual(harness.traversal_biker_action(80, 4, 0, mobile=False),
                         'approach_right')
        self.assertEqual(harness.traversal_biker_action(-180, 4, 0),
                         'approach_left')

    def test_live_actor_sweep_reconciles_reassigned_worker_ownership(self):
        runtime = (harness.ROOT / 'src/core/actor_s8_normal_sa1_runtime.pasm').read_text()
        sweep = runtime.split('S6Normal_BindLiveActors:', 1)[1].split(
            'S6Normal_UpdateNativeProp:', 1)[0]
        self.assertIn('S6Normal_BoundRoster = $7E17C0', runtime)
        self.assertIn('S6Normal_BindLiveActors__slot_index = $7E17C6', runtime)
        self.assertIn('lda.l $412140,x', sweep)
        self.assertIn('lda.l $412144,x', sweep)
        self.assertIn('cmp.l S6Normal_BindLiveActors__worker_context', sweep)
        self.assertIn('and #$00FF\n    cmp #2', sweep)
        self.assertIn('lda.l S6Bridge_Exists,x\n    cmp #1', sweep)
        self.assertIn('S6Normal_BindLiveActors__worker_unlink_pending', sweep)
        self.assertIn('lda.l $4119F6,x', sweep)
        self.assertIn('S6Normal_BindLiveActors__worker_retired:\n'
                      '    ; Retirement returns in A16. Re-enter through needs_bind', sweep)
        self.assertIn('brl S6Normal_BindLiveActors__needs_bind', sweep)
        retired = runtime.split('S6Normal_RetireReplacedBound__context_ready:', 1)[1].split(
            'S6Normal_RetireReplacedBound__unlinked:', 1)[0]
        self.assertIn('lda $F6\n    beq S6Normal_RetireReplacedBound__already_unlinked\n'
                      '    brl S6Normal_RetireReplacedBound__kill_live', retired)
        self.assertIn('S6Normal_RetireReplacedBound__already_unlinked:\n    brl '
                      'S6Normal_RetireReplacedBound__unlinked', retired)
        self.assertIn('S6Normal_BoundRoster,x', sweep)
        self.assertIn('jsl S6Normal_RetireReplacedBound', sweep)
        self.assertIn('jsl S6Normal_Bind', sweep)
        self.assertIn('S6Normal_BindLiveActors__detach_stale', sweep)
        bind = runtime.split('S6Normal_Bind__worker_ready:', 1)[1].split(
            'S6Normal_Bind__fenced_done:', 1)[0]
        self.assertIn('sta.l S6Normal_BoundRoster,x', bind)

    def test_dead_player_releases_controls_until_native_out_continue(self):
        self.assertIsNone(harness.traversal_lifecycle_input(0x892, 0, False))
        self.assertEqual(harness.traversal_lifecycle_input(0x892, 64, False), 0x892)
        self.assertEqual(harness.traversal_lifecycle_input(0x008, 0, True), 0x008)

    def test_attack_pulse_spans_hardware_input_poll_window(self):
        self.assertTrue(harness.traversal_attack_held(0))
        self.assertTrue(harness.traversal_attack_held(1))
        self.assertFalse(harness.traversal_attack_held(2))
        self.assertFalse(harness.traversal_attack_held(3))
        self.assertTrue(harness.traversal_attack_held(4))

    def receipt(self):
        expected = next(row for row in self.plan if row['spawn'])
        actual = dict(campaign=3, stage=expected['stage'], index=expected['index'],
                      record=expected['record'], exists=1,
                      hp=4 if expected['source_type'] == 'item' else 64,
                      mode=3 if expected['source_type'] == 'item' else 2,
                      roster=expected['roster'],
                      idle_frames=3, load_result=1, boss=int(expected['boss']))
        return actual, expected

    def test_valid_initialized_identity(self):
        actual, expected = self.receipt()
        harness.validate_admission(actual, expected)

    def test_steamer_uses_its_native_emitter_mode_not_combat_mode(self):
        expected = dict(stage=28, index=1, record='00005c00c101e1400023',
                        spawn=True, source_type='steamer', boss=False, roster=35)
        actual = dict(campaign=3, stage=28, index=1, record=expected['record'],
                      exists=1, hp=4, mode=5, roster=35, idle_frames=1,
                      load_result=1, boss=0)
        harness.validate_admission(actual, expected)
        for field, value in [('mode', 2), ('mode', 4), ('hp', 0)]:
            bad = deepcopy(actual)
            bad[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(AssertionError):
                harness.validate_admission(bad, expected)

    def test_wrong_order_model_uninitialized_or_missing_actor_rejected(self):
        actual, expected = self.receipt()
        wrong_hp = 0
        wrong_mode = 2 if expected['source_type'] == 'item' else 3
        for field, value in [('campaign', 0), ('stage', 999), ('index', 999), ('record', '00' * 10),
                             ('boss', 1 - actual['boss']),
                             ('roster', 255), ('exists', 0), ('hp', wrong_hp), ('mode', wrong_mode),
                             ('idle_frames', 0), ('load_result', 0)]:
            bad = deepcopy(actual)
            bad[field] = value
            with self.subTest(field=field), self.assertRaises(AssertionError):
                harness.validate_admission(bad, expected)

    def test_observer_read_only_and_control_records_retained(self):
        syms = build._load_poppy_symbols(str(harness.ROOT / 'src/main.sym'))
        lua = harness.traversal_script(syms, Path('synthetic-journal'))
        from game_s8_stage_bounds import admission_script
        observer = admission_script(syms, Path('synthetic-journal'),
            include_controls=True, traversal_fields=True,
            status_path=Path('synthetic-journal').with_suffix('.status'), heartbeat_symbol='Spawn_Play')
        self.assertIn("heartbeat=heartbeat+1", observer)
        self.assertIn("status(string.format('TICK %d %d %d'", observer)
        self.assertEqual(lua.count('emu.addMemoryCallback('), 3)
        self.assertIn('emu.callbackType.write,0x0a85,0x0a88', lua)
        self.assertIn('_s8_initial_ai_seen', lua)
        self.assertNotIn('bind-trace.txt', lua)
        traced = harness.traversal_script(syms, Path('synthetic-journal'), trace_runtime=True)
        self.assertGreaterEqual(traced.count('emu.addMemoryCallback('), lua.count('emu.addMemoryCallback(') + 20)
        self.assertIn('emu.eventType.endFrame', traced)
        self.assertIn("_s8_spawn_mark('Spawn_Play__triggered')", traced)
        self.assertIn("_s8_spawn_mark('Spawn_Play__find_slot_none')", traced)
        self.assertIn("_s8_boundary_mark('Character_PlayFrame__dpad_x')", traced)
        self.assertIn("_s8_boundary_mark('G13_RespawnP1')", traced)
        self.assertIn('if _s8_frames>400 and nmi>250 and not _s8_fault_dumped', traced)
        self.assertIn('(stage==22 and index>=20 and index<=27)', traced)
        self.assertIn('(stage==23 and index<=2)', traced)
        self.assertIn("s['cpu.pc']", traced)
        self.assertIn("_s8_rd(0x12002,2,emu.memType.snesSaveRam)", traced)
        self.assertIn(str(syms['SourceVisual_Error']), traced)
        self.assertIn("s['cpu.sp']", traced)
        self.assertIn('if kind==255 then return end', lua)
        self.assertNotRegex(lua, r'kind==(?:2|3|6)\b')
        self.assertNotIn('emu.write', lua)
        self.assertNotIn('breakExecution', lua)
        bind_symbols = {
            'S6Normal_Init__enabled': 0x1EA00,
            'S6Normal_BindLiveActors__bind': 0x1EA10,
            'S6Normal_Bind__fallback': 0x1EA20,
            'S6Host_BindExisting': 0x1EA30,
            'S6Host_BindExisting__bad_slot': 0x1E9A10,
            'S6Host_BindExisting__error': 0x1E9BA0,
            'S6Host_BindExisting__scheduled': 0x1E9B90,
            'S6Normal_SyncBoundContext__done': 0x1E9C20,
            'S6Host_Tick__unbound': 0x1E9D08,
            'S6Host_PlayerAction__attack': 0x1E9D20,
            'Relay_Poll_P2__owned': 0x1B8011,
            'Relay_Queue': 0x1B80AB,
            'WHost_PlayerAction': 0x1C911B,
            'WHost_PlayerInputTrigger': 0x1C91AE,
            'WHost_PlayerAction__attack': 0x1C9137,
            'WHost_PlayerAttack': 0x1C9176,
            'W6_UpdateWorld': 0x1C8A04,
            'W6_UpdateWorld_P0__call': 0x1C8A85,
            'W6_UpdateWorld_P2__call': 0x1C8B1C,
            'W6_UpdateWorldDispatch': 0x1C8C15,
            'W6_ThinkPass': 0x1C8381,
            'Worker_Execute': 0x1CA32E,
            'Relay_Queued': 0x1B812D,
            'S6Host_ModelTable': 0x23EFE0,
            'S6Bridge_Policy': 0x7E554F,
        }
        bind_trace = harness.traversal_script(syms, Path('synthetic-journal'),
                                              trace_bind=True, world_symbols=bind_symbols)
        self.assertIn('synthetic-journal.bind-trace.txt', bind_trace)
        self.assertIn('S6Host_BindExisting__bad_slot', bind_trace)
        self.assertIn('S6Host_BindExisting__error', bind_trace)
        self.assertIn('S6Host_BindExisting__scheduled', bind_trace)
        self.assertIn('S6Normal_SyncBoundContext__done', bind_trace)
        self.assertIn('S6Host_Tick__unbound', bind_trace)
        self.assertIn('S6Host_PlayerAction__attack', bind_trace)
        self.assertIn('WHost_PlayerAction__attack', bind_trace)
        self.assertIn('WHost_PlayerAttack', bind_trace)
        self.assertIn('W6_UpdateWorld_P2__call', bind_trace)
        self.assertIn('Worker_Execute', bind_trace)
        self.assertIn('emu.cpuType.sa1', bind_trace)
        self.assertIn("s['cart.coprocessor.cpu.d']", bind_trace)
        self.assertIn('emu.memType.sa1Memory', bind_trace)
        self.assertIn('emu.memType.snesSaveRam', bind_trace)
        self.assertIn('_s8_bind_rd(0x415002+x,2)', bind_trace)
        self.assertIn('_s8_bind_rd(worker_bus_context+0xD0,2)', bind_trace)
        self.assertIn('_s8_bind_rd(0x40A0773C,2)', bind_trace)
        self.assertIn('_s8_bw_rd(0x13000+worker_tick_index*8,4)', bind_trace)
        self.assertIn('_s8_player_attack_hits>64', bind_trace)
        self.assertIn('actor_dp~=0x7900 and actor_dp~=0x7A00', bind_trace)
        self.assertIn('_s8_worker_think_hits>512', bind_trace)
        self.assertIn('Relay_Poll_P2__owned', bind_trace)
        self.assertIn('Relay_Queue', bind_trace)
        self.assertIn(str(syms['Input_trigger']), bind_trace)
        self.assertIn('_s8_bind_last_p1', bind_trace)
        self.assertIn('_s8_bind_rd(0x7E0414,2)', bind_trace)
        self.assertIn('_s8_bind_rd(0x7E041C,2)', bind_trace)
        self.assertIn('S6Normal_BindLiveActors__bind', bind_trace)
        self.assertIn('S6Normal_Bind__fallback', bind_trace)
        self.assertIn(f"_s8_bind_rd({bind_symbols['S6Bridge_Policy']}+x,1)", bind_trace)
        self.assertNotIn('emu.write', bind_trace)
        session_source = Path(harness.__file__).read_text()
        self.assertIn('if trace_ownership and world_symbols is None:', session_source)
        self.assertIn('CANDIDATE_DIR / "world.sym"', session_source)
        self.assertIn('trace_ownership=trace_ownership', session_source)
        def rom_offset(name):
            address = syms[name]
            return ((address >> 16) & 0x7F) * 0x8000 + (address & 0x7FFF)
        self.assertIn(str(rom_offset('StageTimerHost_ServiceDeaths')), traced)
        self.assertIn(f"emu.callbackType.exec,{rom_offset('Spawn_Play__environment_done')},{rom_offset('Spawn_Play__environment_done')},emu.cpuType.snes,emu.memType.snesPrgRom", lua)
        self.assertIn(str(syms['CHAR_IDLE_FCOUNT']), lua)
        self.assertIn("status('READY')", lua)
        self.assertIn('pcall(admission)', lua)
        self.assertIn("status('ERROR '..tostring(err))", lua)
        self.assertIn(f"emu.callbackType.exec,{rom_offset('Spawn_Play')},{rom_offset('Spawn_Play')},emu.cpuType.snes,emu.memType.snesPrgRom", lua)

    def test_missing_observer_and_premature_title_have_explicit_failures(self):
        names, strings = retained_inventory(
            harness._impl.run, harness._original_traversal_script
        )
        self.assertIn('observer_spawn_watchdog_due', names)
        self.assertIn('TRAVERSAL_STALL_LIMIT_FIELDS', names)
        self.assertTrue(any('Spawn_Play heartbeat stopped changing for '
                            in value for value in strings))
        self.assertTrue(any('premature TITLE, not campaign progression'
                            in value for value in strings))
        self.assertIn('cold_to_title', names)

    def test_traversal_never_injects_player_camera_or_queue_state(self):
        accelerate = retained_child(harness._impl.run, 'accelerate')
        instructions = list(dis.get_instructions(accelerate))
        traversal_exit = next(
            item.argval for item in instructions
            if item.opname == 'POP_JUMP_IF_FALSE' and item.offset == 4
        )
        write_offsets = [
            item.offset for item in instructions
            if item.opname in ('LOAD_METHOD', 'LOAD_ATTR')
            and str(item.argval).startswith('write_u')
        ]
        self.assertTrue(write_offsets)
        self.assertTrue(all(offset >= traversal_exit for offset in write_offsets))
        unlink = retained_child(harness._impl.run, 'queue_source_unlink')
        constants = set(value for value in unlink.co_consts
                        if isinstance(value, int))
        self.assertTrue({74816, 74820, 74822}.issubset(constants))

    def test_campaign_lifecycle_trace_is_opt_in(self):
        tree = ast.parse(Path(harness.__file__).read_text())
        wrapper = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                       and n.name == '_traversal_script_with_camera_state')
        lifecycle_assignments = [n for n in wrapper.body if isinstance(n, ast.Assign)
                                 and any(isinstance(t, ast.Name)
                                         and t.id == 'trace_player_lifecycle'
                                         for t in n.targets)]
        self.assertTrue(lifecycle_assignments)
        self.assertIn('S8_NORMAL_TRACE_PLAYER_LIFECYCLE',
                      ast.unparse(lifecycle_assignments[0]))
        original_call = next(n for n in ast.walk(wrapper) if isinstance(n, ast.Call)
                             and isinstance(n.func, ast.Name)
                             and n.func.id == '_original_traversal_script')
        passed_value = next(k.value for k in original_call.keywords
                            if k.arg == 'trace_player_lifecycle')
        self.assertEqual(ast.unparse(passed_value), 'trace_player_lifecycle')
        self.assertIn('if not trace_player_lifecycle:',
                      ast.unparse(wrapper))

    def test_traversal_unlink_uses_sequenced_worker_control_record(self):
        helper = retained_child(harness._impl.run, 'queue_source_unlink')
        self.assertIn('write_u16', helper.co_names)
        self.assertIn('sequenced_worker_remove', helper.co_consts)
        constants = set(value for value in helper.co_consts
                        if isinstance(value, int))
        self.assertTrue({74816, 74820, 74822, 8263516, 8263518}
                        .issubset(constants))
        self.assertNotIn('CHAR_HP', helper.co_names)

    def test_initial_live_ai_remains_on_real_combat_lifecycle(self):
        names, strings = retained_inventory(harness._impl.run)
        for name in (
            'hold_input', 'release_input', 'traversal_attack_held',
            'traversal_lifecycle_input', 'traversal_blocking_props',
            'traversal_combat_engagement_needed',
            'traversal_group_gate_blocks_spawn', 'traversal_biker_action',
            'traversal_prop_chase_action',
            'traversal_prop_bypass_action', 'traversal_pickup_action',
            'traversal_slots_full', 'bridge_owns_source_actor',
        ):
            self.assertIn(name, names)
        self.assertIn('sequenced_worker_remove', strings)
        self.assertIn('real player input and native lifecycle', strings)
        self.assertIn('initial_ai', strings)
        self.assertIn('combat_interactions', strings)
        self.assertIn('worker_player', names)
        self.assertNotIn('initial_ai_scanned_stages', names | strings)


if __name__ == '__main__':
    unittest.main()
