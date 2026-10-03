import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class NormalWorkerEnvironmentTests(unittest.TestCase):
    def test_resident_unlink_publishes_only_native_slot_effects(self):
        host = (ROOT / 'src/core/actor_source_host.pasm').read_text()
        remove = host.split('S6Host_RemoveHandle:\n', 1)[1]
        remove = remove.split('\n; Source host callbacks.', 1)[0]
        resident = remove.split('S6Host_RemoveHandle__resident:\n', 1)[1]
        resident = resident.split('\nS6Host_RemoveHandle__temporary:', 1)[0]
        self.assertIn('lda #0\n    sta.l S6Bridge_DisplayedHealth,x', resident)
        self.assertIn('sta.l S6Bridge_Exists,x', resident)
        self.assertIn('sta.l $7E0A00+CHAR_HP,x', resident)
        self.assertIn('jsl S6Host_ClearRemovedReferences', resident)
        self.assertNotIn('jsl S6_KillUnlinked', resident)
        self.assertNotIn('jsl S6Bridge_Export', resident)
        self.assertIn('jsl S6_KillUnlinked', remove.split(
            'S6Host_RemoveHandle__temporary:\n', 1)[1])

    def test_authored_hole_count_does_not_fault_ground_actor_preflight(self):
        host = (ROOT / 'src/core/actor_source_host.pasm').read_text()
        start = host.index('S6_WorldGravity:')
        end = host.index('\nS6_WorldAttack:', start)
        gravity = host[start:end]
        self.assertIn('S6_WorldGravity:', gravity)
        self.assertIn('    rtl', gravity)
        self.assertNotIn('S6Host_EnvironmentBlocked', gravity)
        self.assertNotIn('Spawn_HoleCount', gravity)
        lost = host.split('S6_WorldLost:\n', 1)[1]
        lost = lost.split('\nS6Host_LostRemove:', 1)[0]
        self.assertIn('bcs S6Host_EnvironmentBlocked', lost)

    def test_normal_pit_physics_remains_on_the_gameplay_path(self):
        state = (ROOT / 'src/core/game_state.pasm').read_text()
        start = state.index('Game_State_Play__stage_no_win:')
        end = state.index('jsr Core_Screen_Play', start)
        gameplay = state[start:end]
        self.assertLess(gameplay.index('jsl StageBoundsHost_Physics'),
                        gameplay.index('jsr Core_Oop_Play'))

    def test_normal_vertical_enemy_drop_hands_off_only_after_landing(self):
        runtime = (ROOT / 'src/core/actor_s8_normal_sa1_runtime.pasm').read_text()
        bind = runtime.split('S6Normal_Bind__source_input_ok:\n', 1)[1]
        bind = bind.split('\nS6Normal_Bind__combat:', 1)[0]
        self.assertIn('cmp #CHAR_INPUT_DRIVEN_AI', bind)
        self.assertIn('jsl StageBounds_Row\n    lda.l StageDrop_State,x\n'
                      '    beq S6Normal_Bind__source_drop_ready\n'
                      '    brl S6Normal_Bind__fallback', bind)
        self.assertIn('lda CHAR_THROW_ZPOS\n    ora CHAR_THROW_ZVEL\n'
                      '    beq S6Normal_Bind__source_height_grounded\n'
                      '    brl S6Normal_Bind__fallback', bind)

        live = runtime.split('S6Normal_BindLiveActors__check_live:\n', 1)[1]
        live = live.split('\nS6Normal_BindLiveActors__bind:', 1)[0]
        self.assertIn('jsl StageBounds_Row\n    lda.l StageDrop_State,x\n'
                      '    bne S6Normal_BindLiveActors__next', live)
        self.assertIn('lda CHAR_THROW_ZPOS\n    ora CHAR_THROW_ZVEL\n'
                      '    bne S6Normal_BindLiveActors__next', live)

        drop = (ROOT / 'src/core/stage_drop_host.pasm').read_text()
        landing = drop.split('StageDrop_BeforeActor__ground_ready:\n', 1)[1]
        landing = landing.split('\n; Hide unpublished', 1)[0]
        self.assertLess(landing.index('sta.l StageDrop_State,x'),
                        landing.index('jsl StageDrop_PersistentHandoff'))
        physics = drop.split('StageDrop_BeforeActor__physics:\n', 1)[1]
        physics = physics.split('\nStageDrop_BeforeActor__ground:', 1)[0]
        self.assertIn('lda CHAR_THROW_ZPOS\n    beq StageDrop_BeforeActor__ground', physics)
        self.assertIn('StageDrop_PersistentHandoff:\n    clc\n    rtl\n    nop\n    nop', drop)
        handoff = runtime.split('S6Normal_DropHandoff:\n', 1)[1]
        self.assertLess(handoff.index('jsl S6Normal_IsRosterBound'),
                        handoff.index('jsl S6Normal_Bind'))
        self.assertIn('lda CHAR_THROW_ZPOS\n    ora CHAR_THROW_ZVEL\n'
                      '    bne S6Normal_DropHandoff__no', handoff)
        self.assertIn('S6Normal_DropHandoff__owned:\n', handoff)
        linker = (ROOT / 'tools/verify/actor_s6_production_world.py').read_text()
        self.assertIn("patch(sym['StageDrop_PersistentHandoff'], bytes.fromhex('18 6B EA EA'),\n"
                      "              'S6Normal_DropHandoff', 0x5C)", linker)

    def test_failed_normal_bind_clears_the_exact_production_bridge_row(self):
        runtime = (ROOT / 'src/core/actor_s8_normal_sa1_runtime.pasm').read_text()
        failure = runtime.split('S6Normal_Bind__bind:', 1)[1]
        failure = failure.split('\nS6Normal_Bind__worker_ready:', 1)[0]
        self.assertIn('lda.l $7E1752\n    tax', failure)
        for field in ('S6Bridge_Policy', 'S6Bridge_Exists',
                      'S6Bridge_DisplayedHealth', 'S6Bridge_Context',
                      'S6Bridge_TargetHandle'):
            self.assertIn(f'sta.l {field},x', failure)
        self.assertIn('lda #0\n    sta.l S6Bridge_Policy,x', failure)
        self.assertNotIn('stz.l S6Bridge_', failure)

    def test_normal_rounded_owner_skips_legacy_actor_mutation(self):
        fixture = (ROOT / 'src/core/actor_s6_world_fixture.pasm').read_text()
        start = fixture.index('S6Game_Entity:')
        end = fixture.index('\nS6Game_Bind:', start)
        dispatch = fixture[start:end]
        self.assertIn('cmp #1\n    beq S6Game_Entity__exact', dispatch)
        self.assertIn('cmp #2\n    beq S6Game_Entity__normal_gate', dispatch)
        exact = dispatch[dispatch.index('S6Game_Entity__exact:'):]
        fallback = dispatch[:dispatch.index('S6Game_Entity__exact:')]
        self.assertIn('jml CharacterEntity_Play__no_context_exit', exact)
        self.assertIn('G13_PlayerLifecycleIsOut', fallback)
        self.assertIn('jml S6Game_EntityResume', fallback)
        normal_gate = dispatch[dispatch.index('S6Game_Entity__normal_gate:'):
                               dispatch.index('S6Game_Entity__normal:')]
        self.assertIn('lda.l S7Resident_Owner\n    cmp #2', normal_gate)
        self.assertIn('jml S6Game_EntityResume', normal_gate)
        normal = dispatch[dispatch.index('S6Game_Entity__normal:'):]
        self.assertIn('lda.l S6Bridge_Exists,x', normal)
        self.assertIn('cmp #$0A00+CHAR_ZP_LEN', normal)
        self.assertIn('jml S6Game_EntityResume', normal)
        self.assertIn('S6Game_Entity__owned_return:', normal)
        owned_return = normal[normal.index('S6Game_Entity__owned_return:'):]
        self.assertIn('pla\n    tax\n    sep #$20', owned_return)
        self.assertIn('lda #0\n    pha\n    rep #$30', owned_return)
        self.assertIn('txa\n    pha\n    lda #0\n    rtl', owned_return)
        self.assertIn('lda #0\n    rtl', normal)

    def test_normal_player_death_queues_one_worker_unlink_before_native_fall(self):
        runtime = (ROOT / 'src/core/actor_s8_normal_sa1_runtime.pasm').read_text()
        fixture = (ROOT / 'src/core/actor_s6_world_fixture.pasm').read_text()
        native_return = fixture.split('S6Game_Entity__native_return:\n', 1)[1]
        self.assertIn('pla\n    tax\n    sep #$20', native_return)
        self.assertIn('txa\n    pha\n    lda #0\n    rtl', native_return)
        death = runtime.split('S6Normal_DeathService:\n', 1)[1]
        death = death.split('\nS6Normal_QueueDeadPlayer:', 1)[0]
        self.assertIn('lda.l S7Resident_Owner\n    cmp #2', death)
        self.assertEqual(death.count('jsl S6Normal_QueueDeadPlayer'), 2)
        self.assertIn('jml G13_HandleP2Death', death)
        queue = runtime.split('S6Normal_QueueDeadPlayer:\n', 1)[1]
        queue = queue.split('\nS6Normal_RebindReturnedPlayers:', 1)[0]
        self.assertIn('lda.l S6Bridge_Policy,x\n    cmp #2', queue)
        self.assertIn('lda.l S6Bridge_Exists,x\n    cmp #1', queue)
        self.assertIn('lda.l $7E0A00+CHAR_HP,x\n    bne S6Normal_QueueDeadPlayer__done', queue)
        self.assertIn('jsl S6Host_RemoveHandle', queue)
        self.assertIn('cmp #24\n    bne S6Normal_QueueDeadPlayer__done\n    lda #0\n    sta.l S6Host_Error', queue)
        self.assertIn('S6Normal_QueueDeadPlayer__accepted:\n    sep #$20', queue)
        self.assertIn('lda #2\n    sta.l S6Bridge_Exists,x', queue)
        production_world = (ROOT / 'tools/verify/actor_s6_production_world.py').read_text()
        self.assertIn("sym['CharacterEntity_Play__no_context_exit']+2", production_world)
        self.assertIn("'S6Game_Entity__native_return',0x5C", production_world)
        normal_hook = production_world.split('if normal_runtime:\n        # Current gameplay routes', 1)[1]
        normal_hook = normal_hook.split('\n    else:\n        start=sym[\'Game_State_Play__no_pause_press\']', 1)[0]
        self.assertIn("sym['StageTimerHost_ServiceDeaths__normal']", normal_hook)
        self.assertIn("sym['StageTimerHost_ServiceDeaths__restore']", normal_hook)
        self.assertIn("'S6Normal_DeathService'", normal_hook)
        installer = (ROOT / 'tools/verify/actor_s7_persistent_worker.py').read_text()
        self.assertIn("('Relay_QueueRemove','S6Host_RemoveHandle'", installer)

    def test_replaced_normal_actor_is_retired_before_bridge_mapping_is_cleared(self):
        runtime = (ROOT / 'src/core/actor_s8_normal_sa1_runtime.pasm').read_text()
        retire_modes = runtime.split('S6Normal_RetireReplacedBound__campaign:\n', 1)[1]
        retire_modes = retire_modes.split('S6Normal_RetireReplacedBound__mode:', 1)[0]
        self.assertIn('cmp #1\n    beq S6Normal_RetireReplacedBound__mode', retire_modes)
        self.assertIn('cmp #3\n    beq S6Normal_RetireReplacedBound__mode', retire_modes)
        retire = runtime.split('S6Normal_RetireReplacedBound__context_ready:\n', 1)[1]
        retire = retire.split('\nS6Normal_RetireReplacedBound__fault:', 1)[0]
        self.assertLess(retire.index('jsl S6Normal_MutationFenceBegin'),
                        retire.index('jsl S6_KillUnlinked'))
        self.assertIn('stz $F6', retire)
        self.assertLess(retire.index('stz $F6'),
                        retire.index('sta.l S6Bridge_Context,x'))
        self.assertIn('jsl S6Normal_MutationFenceEnd', retire)

    def test_stage_reset_drains_and_retires_the_resident_world_before_row_reuse(self):
        environment = (ROOT / 'src/core/stage_environment.pasm').read_text()
        self.assertIn('StageEnv_ActorRowsBytes = 798', environment)
        reset = environment.split('StageEnv_ResetActors:\n', 1)[1]
        self.assertIn('StageEnv_ResetActors__worker_call:\n', reset)
        self.assertIn('jsl StageEnv_ResetActors__worker_hook', reset)
        self.assertIn('cpx #StageEnv_ActorRowsBytes', reset)
        runtime = (ROOT / 'src/core/actor_s8_normal_sa1_runtime.pasm').read_text()
        reset_world = runtime.split('S6Normal_ResetStageWorld:\n', 1)[1]
        reset_world = reset_world.split('\nS6Normal_ResetStageWorld__return:', 1)[0]
        reset_modes = reset_world.split('S6Normal_ResetStageWorld__campaign:\n', 1)[1]
        reset_modes = reset_modes.split('S6Normal_ResetStageWorld__mode:', 1)[0]
        self.assertIn('cmp #1\n    beq S6Normal_ResetStageWorld__mode', reset_modes)
        self.assertIn('cmp #3\n    beq S6Normal_ResetStageWorld__mode', reset_modes)
        self.assertIn('jsl S7Resident_Flush', reset_world)
        self.assertIn('jsl S6Normal_MutationFenceBegin', reset_world)
        self.assertIn('stz $F6', reset_world)
        self.assertIn('cpy #StageEnv_ActorRowsBytes', reset_world)
        self.assertIn('sta.l $412100,x', reset_world)
        self.assertIn('cmp #$1F00', reset_world)
        linker = (ROOT / 'tools/verify/actor_s6_production_world.py').read_text()
        self.assertIn("'StageEnv_ResetActors__worker_call'", linker)
        self.assertIn("'S6Normal_ResetStageWorld'", linker)


if __name__ == '__main__':
    unittest.main()
