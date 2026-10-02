"""Production relay must run beyond the bounded fixture without ring aliasing."""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

from actor_s5_entity_fixture import symbols
from actor_s7_persistent_worker import (
    _event_drain, _poll_wrapper_target, _scpu_relay, _snapshot_commit, _worker_gate,
    _worker_snapshot,
)


class ProductionTickRing(unittest.TestCase):
    def test_relink_retains_proven_controller_poll_shim(self):
        self.assertEqual(
            _poll_wrapper_target({'Relay_Poll_P2': 0x248000}, {},
                                 {'Relay_Poll_P2': 0x268000}),
            0x248000)
        self.assertEqual(
            _poll_wrapper_target({}, {'Relay_Poll_P2': 0x258000},
                                 {'Relay_Poll_P2': 0x268000}),
            0x258000)
        self.assertEqual(
            _poll_wrapper_target({}, {}, {'Relay_Poll_P2': 0x268000}),
            0x268000)

    def test_player_snapshot_does_not_republish_worker_ownership(self):
        main = symbols(ROOT / 'src/main.sym')
        commit = _snapshot_commit(
            0x414000, {'S6Bridge_ProjectPolicy': 0x123480}, main, 'A')
        for slot in (0, 1):
            row = slot * main['CHAR_ZP_LEN']
            player_policy_byte = (
                '    sep #$20\n    .a8\n'
                f'    lda.l ${0x414000 + 52 + slot * 36 + 22:06X}\n'
                f'    sta.l ${main["StageEnv_Actors"] + row + 64:06X}\n'
                '    rep #$30\n    .a16\n    .i16'
            )
            self.assertIn(player_policy_byte, commit)
            stale_policy_word = (
                f'    lda.l ${0x414000 + 52 + slot * 36 + 22:06X}\n'
                f'    sta.l ${main["StageEnv_Actors"] + row + 64:06X}'
            )
            self.assertNotIn(stale_policy_word, commit.replace(player_policy_byte, '', 1))
            stale_player_exists = (
                f'lda.l ${0x414000 + 52 + slot * 36 + 34:06X}\n'
                f'    sta.l ${main["StageEnv_Actors"] + row + 65:06X}'
            )
            self.assertNotIn(stale_player_exists, commit)
        npc_exists = (
            f'lda.l ${0x414000 + 52 + 2 * 36 + 34:06X}\n'
            f'    sta.l ${main["StageEnv_Actors"] + 2 * main["CHAR_ZP_LEN"] + 65:06X}'
        )
        self.assertIn(npc_exists, commit)

    def test_snapshot_preserves_native_jump_state_and_source_visual_role(self):
        main = symbols(ROOT / 'src/main.sym')
        world = {'S6Bridge_ProjectPolicy': 0x123480}
        worker = _worker_snapshot(0x414000)
        self.assertIn('lda.l $411914\n    sta.l $414034', worker)
        self.assertIn('lda.l $411A14\n    sta.l $414058', worker)
        self.assertNotIn('lda.l $41190B', worker)
        self.assertNotIn('lda.l $411943', worker)
        self.assertNotIn('lda.l $411945', worker)
        self.assertNotIn('lda.l $411764', worker)

        commit = _snapshot_commit(0x414000, world, main, 'A')
        self.assertNotIn('lda.l $41402C\n    sta.l $7E1764', commit)
        self.assertIn('Relay_ProjectNext_A_0:\n    rep #$30\n    .a16', commit)
        self.assertIn('Relay_ProjectNext_A_5:\n    rep #$30\n    .a16', commit)
        for slot in (0, 1):
            row = slot * main['CHAR_ZP_LEN']
            stale_player_exists = (
                f'lda.l ${0x414000 + 52 + slot * 36 + 34:06X}\n'
                f'    sta.l ${main["StageEnv_Actors"] + row + 65:06X}'
            )
            self.assertNotIn(stale_player_exists, commit)
        npc_exists = (
            f'lda.l ${0x414000 + 52 + 2 * 36 + 34:06X}\n'
            f'    sta.l ${main["StageEnv_Actors"] + 2 * main["CHAR_ZP_LEN"] + 65:06X}'
        )
        self.assertIn(npc_exists, commit)
        self.assertNotIn(f'sta.l ${0x7E0A00 + main["CHAR_SELECTED"]:06X}', commit)
        self.assertNotIn(f'sta.l ${0x7E0A00 + main["CHAR_THROW_ZPOS"]:06X}', commit)
        self.assertNotIn(f'sta.l ${0x7E0A00 + main["CHAR_THROW_ZVEL"]:06X}', commit)
        worker_source = (ROOT / 'tools/verify/actor_s7_persistent_worker.py').read_text()
        self.assertIn("'snapshot_a': [0x14000, 0x14110]", worker_source)
        self.assertIn("'snapshot_b': [0x14110, 0x14220]", worker_source)
        self.assertIn("'snapshot_bytes': 272", worker_source)
        self.assertIn('_worker_snapshot(0x414110)', worker_source)
        worker_generator = (ROOT / 'tools/verify/actor_s7_worker.py').read_text()
        self.assertIn('WHost_Mode=0x411760,WHost_Error=0x411764', worker_generator)
        self.assertIn('S7Resident_Owner=0x41175e', worker_generator)
        visual = (ROOT / 'src/core/source_visual_production.pasm').read_text()
        self.assertIn('cmp #CHAR_SELECTED_JUMP\n    beq SourceVisual_FindEntry__source_jump', visual)
        self.assertIn('lda #7\n    sta.l SourceVisual_Key+1', visual)
        catalog = json.loads(
            (ROOT / 'src/generated/production_source_visual.json').read_text())
        self.assertTrue(any(row['identity'] == 'KULA' and row['role'] == 'jump'
                            and row['runtime_role'] == 7 and row['frame'] == 0
                            and row['map'] == 0 for row in catalog['entries']))

    def test_fixture_remains_bounded_but_production_wraps(self):
        fixture = _worker_gate(production_runtime=False)
        production = _worker_gate(production_runtime=True)
        self.assertIn('cmp #512', fixture)
        self.assertIn('cmp #307', _scpu_relay(
            symbols(ROOT / 'src/main.sym'),
            {'S6Host_RemoveHandle': 0x123456,
             'S7_QueueHitSfxLong': 0x123460,
             'S6Bridge_Project': 0x123470,
             'S6Bridge_ProjectPolicy': 0x123480},
            production_input=False))
        self.assertNotIn('cmp #512', production)
        self.assertNotIn('cmp #307', production)
        self.assertIn('and #$01FF', production)

    def test_production_relay_rejects_full_ring_and_wraps_head(self):
        relay = _scpu_relay(
            symbols(ROOT / 'src/main.sym'),
            {'S6Host_RemoveHandle': 0x123456,
             'S7_QueueHitSfxLong': 0x123460,
             'S6Bridge_Project': 0x123470,
             'S6Bridge_ProjectPolicy': 0x123480},
            production_input=True)
        self.assertNotIn('cmp #307', relay)
        self.assertIn('cmp.l $412004', relay)
        self.assertIn('bne Relay_Queue__head_open\n    jml Relay_Failed', relay)
        self.assertGreaterEqual(relay.count('and #$01FF'), 2)
        self.assertIn('lda.l $7E1774\n    sta.l $413000,x', relay)
        self.assertIn('lda.l $7E1776\n    sta.l $413002,x', relay)
        self.assertIn('sta.l $7E1774\n    bne Relay_Queue__clock_advanced', relay)
        self.assertNotIn('lda.l $7E173C\n    sta.l $413000,x', relay)

    def test_production_unlink_deadline_comparison_wraps_source_tick(self):
        gate = _worker_gate(production_runtime=True)
        apply_remove = gate.split('Worker_ApplyRemove:\n', 1)[1].split(
            'Worker_ApplyRemove__tick_match:', 1)[0]
        self.assertIn('lda.l $41243E\n    sec\n    sbc.l $412446', apply_remove)
        self.assertIn('beq Worker_ApplyRemove__tick_match', apply_remove)
        self.assertIn('bmi Worker_ApplyRemove__done', apply_remove)
        self.assertIn('bra Worker_ApplyRemove__bad', apply_remove)
        self.assertNotIn('cmp.l $412446', apply_remove)

    def test_normal_prop_events_use_native_damage_and_nonblocking_ordered_pump(self):
        main = symbols(ROOT / 'src/main.sym')
        world = {'S6Host_RemoveHandle': 0x123456,
                 'S7_QueueHitSfxLong': 0x123460,
                 'S6Bridge_Project': 0x123470,
                 'S6Bridge_ProjectPolicy': 0x123480}
        drain = _event_drain(world, main, native_prop_events=True)
        self.assertIn('cmp #4\n    bne Relay_DrainEvents__unknown_kind\n'
                      '    jml Relay_DrainEvents__native_prop', drain)
        self.assertIn(
            f"cmp #${main['CHAR_INPUT_DRIVEN_PROP']:02X}\n"
            "    beq Relay_DrainEvents__native_prop_kind_ok\n"
            f"    cmp #${main['CHAR_INPUT_DRIVEN_BIKER']:02X}\n"
            "    beq Relay_DrainEvents__native_prop_kind_ok", drain)
        self.assertIn('jsl $0C997E', drain)  # Character_HitApply_VsEntityGeneric
        self.assertIn(
            f"jsl ${main['Character_HitApply__ScoreAndFinish_Long']:06X}", drain)
        self.assertIn(
            f"jsl ${main['Character_HitApply__RevealOrPickup']:06X}", drain)
        self.assertIn('Relay_DrainEvents__hit_attacker_npc', drain)
        self.assertIn(
            f"jsl ${main['HudOpponent_Target']:06X}", drain)
        self.assertIn(
            f"lda.l ${main['HudOpponentHost_SlotOffsets']:06X},x", drain)
        self.assertIn('cmp.l $7E1766\n    bne Relay_DrainEvents__sequence_retry', drain)
        self.assertIn('sbc #$7900', drain)  # WHost_SlotTable begins at $7900
        self.assertIn('The generic hit routine reads this ABI as a 16-bit table index', drain)
        self.assertIn('sta.l $7FF50C\n    asl a\n    tax', drain)
        self.assertIn('sta $7A\n    lda.l $7E1768\n'
                      '    jsl $123480\n'
                      '    bcc Relay_DrainEvents__native_prop_project_x_ok\n'
                      '    jml Relay_DrainEvents__native_prop_ack', drain)
        self.assertIn('lda.l $7E176A\n    and #$00FF\n'
                      '    jsl $123480\n'
                      '    bcc Relay_DrainEvents__native_prop_project_y_ok\n'
                      '    jml Relay_DrainEvents__native_prop_ack', drain)
        self.assertIn('policy-projected space as render snapshots', drain)
        self.assertIn('raw SA-1 coordinates against projected host coordinates', drain)
        self.assertIn('Relay_DrainEvents__loop:\n    rep #$30', drain)
        self.assertIn('Relay_DrainEvents__ack:\n    ; Event-specific', drain)
        self.assertIn('Relay_DrainEvents__done:\n    rep #$30\n    plb\n    pld', drain)

        relay = _scpu_relay(main, world, production_input=True,
                            native_prop_events=True)
        pump = relay.index('jsl Relay_DrainEvents\n    bra Relay_Queue')
        tick = relay.index('lda.l $7E1774\n    sta.l $413000,x')
        self.assertLess(pump, tick)
        self.assertIn('never wait for an SA-1 tick', relay)

    def test_normal_bind_uses_the_worker_command_epoch(self):
        host = (ROOT / 'src/core/actor_source_host.pasm').read_text()
        self.assertIn('cmp #3\n    bne S6Host_BindExisting__clock_legacy', host)
        self.assertIn('lda.l S6Game_TickCommit\n    sta $D0', host)
        self.assertIn('lda.l S6Game_TickCommit+2\n    sta $D2', host)

    def test_normal_bridge_temporaries_do_not_alias_native_entity_headers(self):
        bridge = (ROOT / 'src/core/actor_source_bridge.pasm').read_text()
        self.assertIn('S6Bridge_Temp78 = $7E17E0', bridge)
        self.assertIn('S6Bridge_Temp86 = $7E17EA', bridge)
        self.assertIn('S6Bridge_Temp88 = $7E17EC', bridge)
        self.assertIn('S6Bridge_Temp8A = $7E17EE', bridge)
        for scratch in ('$78', '$7C', '$80', '$82', '$84', '$86', '$88', '$8A'):
            for opcode in ('sta', 'lda', 'stz', 'inc', 'ldy'):
                self.assertNotIn(f'{opcode} {scratch}\n', bridge)

    def test_worker_clears_battery_backed_protocol_before_first_poll(self):
        gate = _worker_gate(production_runtime=True)
        startup, first_poll = gate.split('Worker_Poll:', 1)
        for address in ('$412002', '$412004', '$412008', '$41200A',
                        '$412006', '$412007', '$412430', '$412432',
                        '$412434', '$412440', '$412442', '$412444',
                        '$412446', '$41200C'):
            self.assertIn(f'sta.l {address}', startup)
        self.assertIn('lda.l $41200A', first_poll)

    def test_worker_parks_before_shared_normal_context_publication(self):
        gate = _worker_gate(production_runtime=True)
        runtime = (ROOT / 'src/core/actor_s8_normal_sa1_runtime.pasm').read_text()
        self.assertIn('Worker_NoMutationFence:', gate)
        self.assertIn('Worker_MutationFenceWait:', gate)
        self.assertIn('sta.l $41200C', gate)
        self.assertLess(gate.index('Worker_NoMutationFence:'),
                        gate.index('lda.l $412434'))
        self.assertIn('S6Normal_MutationFenceBegin:', runtime)
        self.assertIn('S6Normal_MutationFenceEnd:', runtime)

        bind = runtime.split('S6Normal_Bind__bind:\n', 1)[1].split(
            'S6Normal_Bind__handled:', 1)[0]
        self.assertLess(bind.index('jsl S6Normal_MutationFenceBegin'),
                        bind.index('jsl S6Host_BindExisting'))
        self.assertLess(bind.index('jsl S6Normal_SyncBoundContext'),
                        bind.index('jsl S6Normal_MutationFenceEnd'))

        rebind = runtime.split('S6Normal_RebindReturnedPlayer__flush_done:\n', 1)[1].split(
            'S6Normal_RebindReturnedPlayer__done:', 1)[0]
        self.assertLess(rebind.index('jsl S6Normal_MutationFenceBegin'),
                        rebind.index('jsl S6Host_BindExisting'))
        self.assertLess(rebind.index('jsl S6Normal_SyncBoundContext'),
                        rebind.index('jsl S6Normal_MutationFenceEnd'))

    def test_normal_player_motion_consumes_tick_owned_input_on_sa1(self):
        host = (ROOT / 'src/core/actor_source_host.pasm').read_text()
        action = host.split('S6Host_PlayerAction:\n', 1)[1].split(
            'S6Host_PlayerAction__unsupported:', 1)[0]
        attack = host.split('S6Host_PlayerAttack:\n', 1)[1].split(
            'S6Host_PlayerPain:', 1)[0]
        move = host.split('S6Host_PlayerMove:\n', 1)[1].split(
            'S6_FrameChanged:', 1)[0]
        self.assertIn('jsl S6Host_PlayerMove', action)
        self.assertIn('jsl S6Host_PlayerMove', attack)
        self.assertIn('S6Host_InputP1Press = $412020', host)
        self.assertIn('S6Host_InputP2Press = $412024', host)
        self.assertIn('S6Host_InputP1Trigger = $412022', host)
        self.assertIn('S6Host_InputP2Trigger = $412026', host)
        self.assertIn('and #$4000', action)
        self.assertIn('lda $C6', move)
        self.assertEqual(move.count('jsl S6_EnemyApplyAxis'), 2)
        self.assertIn('and #$8000', move)
        self.assertIn('sta $1A', move)

    def test_biker_facing_is_owned_by_its_native_driver(self):
        main = (ROOT / 'src/main.pasm').read_text()
        facing = main.split('Anim_UpdateFacing:\n', 1)[1].split(
            '; Anim_EnqueueTilemapRow', 1)[0]
        self.assertIn('cmp #CHAR_INPUT_DRIVEN_BIKER\n'
                      '    beq Anim_UpdateFacing__done', facing)
        self.assertIn('and #$02                       ; bit9 (Left) of the word = bit1 of this byte\n'
                      '    lsr a\n    sta CHAR_FACING_LEFT', facing)

    def test_initial_think_deadline_is_set_after_source_frame_load(self):
        host = (ROOT / 'src/core/actor_source_host.pasm').read_text()
        bind = host.split('S6Host_BindExisting:\n', 1)[1].split(
            'S6Host_BindExisting__error:', 1)[0]
        role = bind.index('jsl S6_SetRole')
        deadline = bind.index('S6Host_BindExisting__scheduled:')
        self.assertLess(role, deadline)
        self.assertLess(bind.index('lda $D0', role), deadline)
        self.assertLess(role, bind.index('sta $E8'))
        self.assertLess(bind.index('sta $E8'), deadline)
        self.assertLess(bind.index('sta $EA'), deadline)


if __name__ == '__main__':
    unittest.main()
