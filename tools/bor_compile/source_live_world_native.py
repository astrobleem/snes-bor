"""Real clock/input/entity traversal for the first persistent player slice.

The caller supplies a completed real constructor and the exclusive foreign
canvas lease. New persistent fields occupy retired scene-video WRAM, never
the renderer's BW-RAM maps/references/queues. No pending service commits time.
"""
from __future__ import annotations

from pathlib import Path
import re

WORK = 0x7e7700
HEALTH = 0x7e7680
LATEST = 0x7e7800
BINDING = 0x7e7a00
FLAT = 0x7e8080
GENERATION = 1
MAGIC = 0xb6d0


def emit(sy, old, player, source_path):
    from compiler import Source, key
    from source_foreign_state_layout import layout
    from source_foreign_slot_tail import derive_plan
    from source_pending_jump_layout import rehost as jumps
    from source_hit_state_layout import rehost as hits
    from source_hit_state_native import emit as hit_native
    from source_move_contact_layout import rehost as moves
    from source_check_move_callback_native import emit as move_native
    from source_trymove_requirements import derive as try_requirements
    from source_player_spawn_inputs import derive as spawn_inputs
    from source_empty_init_environment import derive as empty_inputs
    from source_animation_step import derive as timing_inputs, pack as timing_pack
    from source_update_animation_inputs import derive as prefix_inputs, pack as prefix_pack
    from source_animation_physics_4086 import derive as physics_inputs, pack as physics_pack
    from source_animation_ids import configure, role_id
    from source_profile import discover, document
    from source_timed_world_geometry_native import emit as timed_geometry
    from source_live_world_dispatch_native import emit as dispatcher
    from source_check_attack_native import emit as attack_native
    from source_live_health_native import emit_normal_zero_mp, authored_model_inputs
    from source_live_ground_post_native import emit as post_native
    from source_damage_inputs_4086 import derive as damage_inputs, pack as damage_pack
    from source_animation_energy_4086 import derive as energy_inputs, pack as energy_pack
    from source_attack_body_profile import derive as body_inputs, pack_runtime as body_pack
    from source_live_player_controls_native import emit as player_controls

    source = Source(source_path)
    arena = {r['name']: r['address'] for r in layout(0x7fa000,6400)['regions']}
    tail = derive_plan(source)
    jp, hp, mp = jumps(), hits(), moves()
    tr = try_requirements(source)
    if not tr['admitted']: raise ValueError('LIVE_WORLD_FLAT_MOVEMENT_UNBOUND')
    placement = next(s for s in spawn_inputs(source)['stages']
                     if key(s['source_path']) == key('DATA/LEVELS/GUILE2.TXT'))
    env = empty_inputs(source)
    stage = next(s for s in env['stages'] if s['stage_id'] == placement['stage_id'])
    if not env['platform_query_admitted'] or not stage['admitted']:
        raise ValueError('LIVE_WORLD_EMPTY_STAGE_UNBOUND')
    docs = {k: document(source,n) for k,(n,_) in source.index.items() if k.endswith('.txt')}
    structure = discover(source,docs)
    config = configure(docs[key(structure['models_path'])]['directives'])
    health_profile = authored_model_inputs(source)
    timing = timing_pack(timing_inputs(source))
    prefix = prefix_pack(prefix_inputs(source))
    physics = physics_pack(physics_inputs(source))
    damage = damage_pack(damage_inputs(source))
    energy = energy_pack(energy_inputs(source))
    body = body_pack(body_inputs(source))
    body_offset = (len(energy)+1)&~1
    table_rows = [(49,'timing',timing),(50,'prefix',prefix),(52,'physics',physics),
                  (53,'damage',damage)]
    lines = ['.snes','.bank 48','.org $8000']

    def put(s): lines.extend(s.strip().splitlines())
    def label(name): put(name+':\n.a16\n.i16')
    def store(at,value): put(f' lda #{value&65535}\n sta.l {at}')
    def store32(at,value): store(at,value);store(at+2,value>>16)
    def settings(items):
        for name,value in items.items(): store(sy[name],value)
    def guard(at,value): put(f' lda.l {at}\n cmp #{value}\n bne LiveWorld_Fault')
    def generation(): put(' ldx #1\n ldy #0')
    def native_call(name): put(f' jsl {sy[name]}\n bcs LiveWorld_Fault')

    # Fixed entry used by the separately assembled player birth bridge.
    label('LiveWorld_HitBirth')
    put(f''' php
 rep #$38
 phx
 phy
 cmp #0
 bne LiveWorld_HealthBirthDone
 lda #0
 sta.l {HEALTH}+16
 sta.l {HEALTH}+18
 sta.l {HEALTH}+20
 sta.l {HEALTH}+22
 sta.l {HEALTH}+24
 sta.l {HEALTH}+26
 lda #$B6D2
 sta.l {HEALTH}+28
 lda #0
LiveWorld_HealthBirthDone:
.a16
.i16
 sta.l {hp['controls']}+4
 sta.l {mp['controls']}+4
 asl a
 asl a
 tax
 lda #0
 sta.l {BINDING},x
 sta.l {BINDING}+2,x
 ldx #1
 ldy #0
 jsl HitState_ClearBirth
 bcs LiveWorld_HitBirthBad
 jsl MoveContact_ClearBirth
 bcs LiveWorld_HitBirthBad
 ply
 plx
 plp
 clc
 rtl''')
    label('LiveWorld_HitBirthBad');put(' ply\n plx\n plp\n sec\n rtl')

    # This entry precedes the retained Lua immutable-input installation.
    # No overlay has been touched: let the existing NMI drain its own valid
    # queue while the foreground is suspended and cannot submit more work.
    label('LiveWorld_WaitLegacy')
    for name in ('StageWater_Held','SceneVideo_TestActive','SceneVideo_TestRequest',
                 'SceneVideo_PlayState','SceneVideo_SequenceActive','SceneVideo_SkipPending',
                 'StageFp_BG2Booting'):
        put(f' lda.l {sy[name]}\n and #255\n bne LiveWorld_AcquireRejected')
    put(f' sep #$20\n.a8\n lda #0\n sta.l {sy["Nmi_FrameBusy"]}\n lda #$81\n sta.l $004200\n rep #$20\n.a16')
    label('LiveWorld_WaitLegacyScan');put(' ldx #0')
    label('LiveWorld_WaitLegacySlot')
    put(f' lda.l {sy["DmaQueue"]}+4,x\n and #{sy["DMA_OPT_ACTIVE"]}\n bne LiveWorld_WaitLegacyField\n txa\n clc\n adc #8\n tax\n cpx #64\n bcc LiveWorld_WaitLegacySlot')
    label('LiveWorld_LegacyDrained')
    put(f' sep #$20\n.a8\n lda #0\n jml {old["LiveGroundAcquire"]+4}')
    label('LiveWorld_WaitLegacyField');put(' wai\n jmp LiveWorld_WaitLegacyScan')

    # Source callbacks re-enter Vm_SourceFrameGate. Once this foreground owns
    # execution, run that real gate directly rather than re-entering the outer
    # fixture activation/return wrapper. Preserve its exact displaced prologue.
    label('LiveWorld_VmGate')
    put(f''' php
 rep #$38
 pha
 lda.l $7FFB88
 cmp #{MAGIC}
 beq LiveWorld_VmGateOwned
 pla
 plp
 php
 rep #$38
 phx
 phy
 jml {old['CallbackFixture_Gate']+5}
LiveWorld_VmGateOwned:
.a16
.i16
 pla
 plp
 php
 rep #$31
 phx
 phy
 jml {sy['Vm_SourceFrameGate']+5}''')

    label('LiveWorld_PreConstructor')
    # This is the only acquisition point. The S-CPU is already inside the
    # foreign foreground call, so an inactive scene loader cannot start while
    # these predicates are checked. There is no return to Game_State_Play after
    # the lease is published, including faults and unfinished services.
    for name in ('SceneVideo_TestActive','SceneVideo_TestRequest','SceneVideo_PlayState',
                 'SceneVideo_SequenceActive','SceneVideo_SkipPending',
                 'StageFp_BG2DmaPending','StageFp_BG2Booting',
                 'StreamScrollFp_ColPending','StageWater_Pending','StageWater_Held',
                 'Msu1_StreamBusy'):
        put(f' lda.l {sy[name]}\n and #255\n bne LiveWorld_AcquireRejected')
    put(' ldx #0')
    label('LiveWorld_DrainCheck')
    put(f' lda.l {sy["DmaQueue"]}+4,x\n and #{sy["DMA_OPT_ACTIVE"]}\n bne LiveWorld_AcquireRejected\n txa\n clc\n adc #8\n tax\n cpx #64\n bcc LiveWorld_DrainCheck')
    # Loaded/Active/Enabled describe a retained picture, not work in flight.
    # The actual loader and DMA predicates above must already be idle. NMI is
    # disabled by the original acquisition entry, and this foreground never
    # resumes. Retire the old producers synchronously; their latched VRAM
    # picture can remain until the unchanged cold publisher takes the PPU.
    put(' sep #$20\n.a8\n lda #0')
    for name in ('StageFp_BG2Loaded','StageFp_BG2Active','StreamScrollFp_Enabled',
                 'StageWater_Enabled'):
        put(f' sta.l {sy[name]}')
    put(' rep #$20\n.a16')
    store(sy['SourceClock4086_Ready'],0)
    # Retire all original visual NMI writers; its existing counter-only path
    # still observes every hardware field once SourceClock is started.
    put(f' sep #$20\n.a8\n lda #1\n sta.l {sy["Nmi_FrameBusy"]}\n lda #0\n sta.l {sy["Nmi_HdmaEnableCurrent"]}\n sta.l {sy["Nmi_HdmaEnable"]}\n sta.l $00420C\n rep #$20\n.a16')
    store(0x7ffb88,MAGIC)
    put(' lda #0\n ldx #0')
    label('LiveWorld_ClearRetiredVideo')
    put(' sta.l $7E6200,x\n inx\n inx\n cpx #$1F00\n bcc LiveWorld_ClearRetiredVideo')
    store(WORK,MAGIC);store32(WORK+4,1)
    # The accepted BG owner is not the Mode-4 canvas. A distinct private lease
    # retains the existing nonzero generation, complete clear and DMA checks,
    # using the permanently retired foreground/NMI owner proved above.
    generation();put(' jsl LiveWork_Init\n bcs LiveWorld_Fault')
    # Capture hooks for RUN and pending jumps execute during the constructor;
    # scratch tags must exist before those real model-copy/birth hooks run.
    put(' jsl LivePlayerControls_Initialize\n bcs LiveWorld_Fault')
    store32(arena['player_state_controls']+8,1)
    put(f' nop\n jsl {old["SourcePlayerState_Init"]}\n bcs LiveWorld_Fault')
    for plan,magic in ((hp,0xb6a0),(mp,0)):
        w=plan['controls']
        for off,val in ((0,magic),(8,1),(10,0),(16,plan['base']&65535),
                        (18,plan['base']>>16),(20,0xd800),(22,128)):store(w+off,val)
    generation();put(' jsl MoveContact_Initialize\n bcs LiveWorld_Fault')
    pending=arena['pending_jump_controls']
    for off,value in ((0,0xb691),(8,1),(10,0),(12,1),(14,0),
                      (16,jp['base']&65535),(18,jp['base']>>16),(20,0xd800),(22,16)):
        store(pending+off,value)
    settings(dict(SourceFreeze4086_Ready=0xb5df,SourcePhysicsState4086_Ready=0xb61c,
                  SourceDamageEffectsState4086_Ready=0xb62f,
                  SourceLandingDrop4086_Ready=0xb62e,SourceLandingDrop4086_Base=0x8000,
                  SourceLandingDrop4086_Bank=53,SourceLandingDrop4086_Bytes=len(damage),
                  SourceLandingDrop4086_Models=16,
                  SourceAttackBody4086_Ready=0xb605,SourceAttackBody4086_Status=0,
                  SourceAttackBody4086_Bank=58,SourceAttackBody4086_Base=0x8000+body_offset,
                  SourceAttackBody4086_Bytes=len(body),
                  SourceAutokillState4086_Ready=0xb60e,SourceAttackCostState4086_Ready=0xb609,
                  SourceMovementState4086_Ready=0xb60b))
    # Publish the compiler-proved empty stage/registry capability, using the
    # selected authored stage identity. This is environment configuration,
    # independent of the world tick's phase, pending flag and logical time.
    settings(dict(VmSourceWorld_Level=1,SourceEmptyInitEnvironment4086_Ready=0xb504,
                  SourceEmptyInitEnvironment4086_Models=len(env['models']),
                  SourceEmptyInitEnvironment4086_Stage=stage['stage_id'],
                  SourceEmptyInitEnvironment4086_Status=0,SourceEnvironment4086_Ready=0xb4d1,
                  SourceEnvironment4086_Stage=stage['stage_id'],SourceEnvironment4086_WallCount=0))
    put(f' jml {old["CallbackFixture_Init"]+5}')

    # A failed constructor must never re-enter the retired foreground writer.
    # The inactive path preserves the displaced original return instructions.
    label('LiveWorld_ReturnGate')
    put(f' rep #$38\n lda.l $7FFB88\n cmp #{MAGIC}\n beq LiveWorld_Fault\n sep #$20\n.a8\n lda #$81\n jml {old["CallbackFixture_Return"]+4}')
    label('LiveWorld_AcquireRejected')
    put(' sep #$20\n.a8\n lda #0\n sta.l $004200\n rep #$20\n.a16')
    store(0x7ffb84,0xb6d1)
    put(' jmp LiveWorld_Stop')

    # Replace the old operation fixture boot, which installed test-only phase
    # controls. Publish the actual constructor result before starting the clock.
    label('LiveWorld_Boot')
    guard(WORK,MAGIC)
    settings(dict(SourceWorldTick4086_Ready=0xb4d5,SourceSelf4086_Ready=0xb4f6,
                  SourceSelf4086_Active=0,SourceSelf4086_Fault=0))
    for address,size,target in ((0x414000,80,0x7fba00),(0x416800,64,0x7fba50)):
        name=f'LiveWorld_ColdCopy{address:x}'
        put(' ldx #0');label(name)
        put(f' lda.l {address},x\n sta.l {target},x\n inx\n inx\n cpx #{size}\n bcc {name}')
    store(0x7fba90,0)
    # The accepted cold image predates the optional physics row capability.
    # Its public guard expects that descriptor disabled. Rows remain intact;
    # restore their readiness before any tick or source provider can execute.
    store(sy['SourcePhysicsState4086_Ready'],0)
    put(' jsl $398000\n bcs LiveWorld_ColdFailed')
    store(sy['SourcePhysicsState4086_Ready'],0xb61c)
    label('LiveWorld_ColdPublished');put(' nop\n jmp LiveWorld_Start')
    label('LiveWorld_ColdFailed')
    store(sy['SourcePhysicsState4086_Ready'],0xb61c)
    put(' jmp LiveWorld_Fault')

    # The inherited constructor unit fixture acknowledged event 9 without an
    # audio owner. A live join may not silently consume He-Man's authored entry
    # WAV. Preserve its real frame/effect continuation and stop visibly pending
    # until an actual source audio backend can service the requested sample.
    label('LiveWorld_ConstructorAudio')
    store(WORK+12,9);store(WORK+2,2)
    label('LiveWorld_ConstructorAudioPending');put(' wai\n jmp LiveWorld_ConstructorAudioPending')

    label('LiveWorld_Start')
    guard(WORK,MAGIC)
    generation();native_call('SourceForeignWork_Check')
    native_call('SourceClock4086_Start')
    # A logical epoch is distinct from elapsed physical time. It matches the
    # real constructor's inherited epoch, and advances only at actual Commit.
    for off in (0,2):
        put(f' lda.l {sy["VmSourceWorld_Time"]+off}\n sta.l {sy["SourceClock4086_TimeLo"]+off}')
    settings(dict(SourceWorldTick4086_Ready=0xb4d5,SourceWorldTick4086_State=0,
                  SourceWorldTick4086_Pending=0,SourceWorldTick4086_Phase=0,SourceWorldTick4086_Fault=0,
                  SourceUpdateScript4086_Ready=0xb5e1,SourceUpdateScript4086_Status=0,
                  SourceAI4086_Ready=0xb5e2,SourceAI4086_State=0,SourceAI4086_Endgame=0,
                  SourceAI4086_SpawnID=role_id(config,'spawn'),SourceAI4086_RespawnID=role_id(config,'respawn'),
                  SourceAIRun4086_Ready=0xb5e6,SourceAIRun4086_State=0,
                  SourceLost4086_Ready=0xb5e0,SourceLost4086_Status=0,
                  SourceLost4086_HRes=placement['source_width'],SourceLost4086_VRes=240,
                  SourceLost4086_Direction=2,SourceVelocity4086_Ready=0xb5de,
                  SourceUpdateAnimation4086_Ready=0xb60f,SourceUpdateAnimation4086_State=0,
                  SourceUpdateAnimation4086_Base=0x8000,SourceUpdateAnimation4086_Bank=49,
                  SourceUpdateAnimation4086_Bytes=len(timing),
                  SourceUpdateAnimationPrefix4086_Ready=0xb60d,SourceUpdateAnimationPrefix4086_Status=0,
                  SourceUpdateAnimationPrefix4086_Base=0x8000,SourceUpdateAnimationPrefix4086_Bank=50,
                  SourceUpdateAnimationPrefix4086_Bytes=len(prefix),SourceUpdateAnimationPrefix4086_Models=16,
                  SourceUpdateAnimationPrefix4086_SleepID=role_id(config,'sleep'),
                  SourceAnimationPhysics4086_Ready=0xb61b,SourceAnimationPhysics4086_Base=0x8000,
                  SourceAnimationPhysics4086_Bank=52,SourceAnimationPhysics4086_Bytes=len(physics),
                  SourceAnimationPhysics4086_Animations=80,SourceAdjustBaseEmpty4086_Ready=0xb620,
                  SourceCheckMove4086_Ready=0xb617,SourcePostStationary4086_Ready=0xb61a,
                  SourcePostStationary4086_Status=0,
                  SourcePostAir4086_Ready=0,SourceGravityIdle4086_Ready=0xb618,
                  SourcePhysicsState4086_Ready=0xb61c,SourceCameraMotion4086_Ready=0xb5db,
                  SourceCameraMotion4086_HRes=placement['source_width'],
                  SourceCRandom4086_Ready=0xb5ea,SourceCRandom4086_Profile=1,
                  SourceCRandom4086_SeedLo=1,SourceCRandom4086_SeedHi=0,
                  SourceCRandom4086_CallsLo=0,SourceCRandom4086_CallsHi=0,SourceCRandom4086_Busy=0))
    for name,val in (('SourceCameraMotion4086_MinZ',placement['minimum_z']<<16),
                     ('SourceCameraMotion4086_MaxZ',placement['maximum_z']<<16),
                     ('SourceLost4086_DefaultOffscreenKill',3000),('SourceLost4086_OffscreenKill',0)):
        store32(sy[name],val)
    for off,value in ((0,0xb6a5),(6,stage['stage_id']),(8,16),(12,1),(14,0),(16,0),(18,0)):
        store(FLAT+off,value)
    for off,value in ((0,0xb6d1),(4,1),(6,0),(8,0x4000),(10,0x41),(12,0),(14,0)):
        store(HEALTH+off,value)
    store(0x7ffb88,MAGIC)
    store(WORK+2,1)
    put(' sep #$20\n.a8\n lda #$81\n sta.l $004200\n rep #$20\n.a16')
    label('LiveWorld_Outer')
    store(WORK+6,0)
    put(' lda #1');native_call('SourceClock4086_Observe')
    put(' cmp #0\n bne LiveWorld_Input\n wai\n jmp LiveWorld_Outer')
    label('LiveWorld_Input')
    put(f' lda.l {sy["SourceClock4086_TimeLo"]}\n tax\n lda.l {sy["SourceClock4086_TimeHi"]}\n tay\n lda #1')
    native_call('SourceInputController_Refresh')
    # One outer input snapshot remains immutable over all catch-up ticks.
    for off in range(0,20,2):put(f' lda.l {sy["VmSourceInput_Ready"]+off}\n sta.l {arena["input_snapshot"]+off}')
    put(f' jsl {player["PlayerHistory_Refresh"]}\n bcs LiveWorld_Fault')
    label('LiveWorld_BeginTick')
    native_call('SourceWorldTick4086_Begin')
    label('LiveWorld_TickStarted');put(' nop')
    label('LiveWorld_ResumeTick')
    generation();put(' jsl LiveWorldDispatch_Run\n bcs LiveWorld_Fault\n cmp #0\n beq LiveWorld_Commit')
    put(f' sta.l {WORK+6}');store(WORK+2,2)
    label('LiveWorld_Pending');put(' wai\n jmp LiveWorld_ResumeTick')
    label('LiveWorld_Commit')
    native_call('SourceWorldTick4086_Commit')
    label('LiveWorld_TickCommitted');put(' nop')
    put(f' lda.l {WORK+8}\n inc a\n sta.l {WORK+8}\n bne LiveWorld_Seal\n lda.l {WORK+10}\n inc a\n sta.l {WORK+10}')
    label('LiveWorld_Seal')
    for address,size,target in ((0x414000,80,LATEST),(0x416800,64,LATEST+80)):
        name=f'LiveWorld_Copy{address:x}'
        put(' ldx #0');label(name)
        put(f' lda.l {address},x\n sta.l {target},x\n inx\n inx\n cpx #{size}\n bcc {name}')
    put(f' lda.l {WORK+8}\n sta.l {LATEST+144}')
    label('LiveWorld_SnapshotSealed');put(' nop')
    store(WORK+2,1)
    put(f' lda.l {sy["SourceClock4086_Due"]}\n beq LiveWorld_Outer\n jmp LiveWorld_BeginTick')
    label('LiveWorld_Fault')
    store(WORK+2,3)
    label('LiveWorld_Stop');put(' wai\n jmp LiveWorld_Stop')

    # The accepted publisher's owned NMI intentionally only acknowledges NMI.
    # A real clock must observe every physical field while retaining that
    # no-visual-writes behavior. This vector owner preserves all registers and
    # delegates unchanged to the accepted NMI whenever the lease is inactive.
    label('LiveWorld_Nmi')
    put(f''' php
 rep #$30
 pha
 lda.l $7FFB88
 cmp #{MAGIC}
 beq LiveWorld_NmiOwned
 pla
 plp
 jml {player['_accepted_nmi']}
LiveWorld_NmiOwned:
.a16
.i16
 lda.l {sy['SourceClock4086_Ready']}
 cmp #$B4C5
 bne LiveWorld_NmiAck
 jsl {sy['SourceClock4086_NmiGate']}
LiveWorld_NmiAck:
.a16
.i16
 lda.l $004210
 pla
 plp
 rti''')

    # Thin adapters normalize real provider result conventions. Unsupported
    # tickets remain visible at WORK+12 and do not reach dispatcher Ack.
    for label_name,target in (('LiveWorld_Freeze','SourceFreeze4086_Execute'),
                              ('LiveWorld_Script','SourceUpdateScript4086_Execute'),
                              ('LiveWorld_Velocity','SourceVelocity4086_Apply'),
                              ('LiveWorld_ClearMove','SourceVelocity4086_Clear')):
        label(label_name);put(f' jsl {sy[target]}\n bcs LiveWorld_ProviderFault\n lda #0\n clc\n rtl')
    label('LiveWorld_Lost')
    put(f' jsl {sy["SourceLost4086_Begin"]}\n bcs LiveWorld_ProviderFault\n lda.l {sy["SourceLost4086_Status"]}\n cmp #2\n beq LiveWorld_ProviderComplete\n jmp LiveWorld_ProviderPending')
    label('LiveWorld_AI')
    put(f' lda.l {sy["SourceAIRun4086_State"]}\n beq LiveWorld_AIBegin\n cmp #1\n beq LiveWorld_AIFrame\n cmp #2\n beq LiveWorld_ProviderComplete\n jmp LiveWorld_ProviderPending')
    label('LiveWorld_AIBegin');put(f' jsl {player["ForeignAIRun_Begin"]}\n bcs LiveWorld_ProviderFault\n cmp #0\n beq LiveWorld_ProviderComplete\n cmp #1\n beq LiveWorld_AIFrame\n sta.l {WORK+12}\n jmp LiveWorld_ProviderPending')
    label('LiveWorld_AIFrame')
    put(f' lda.l {sy["SourceAnimationInit4086_Issued"]}\n cmp #1\n beq LiveWorld_AIFrameRun\n jsl {sy["SourceAnimationInit4086_StartFrame"]}\n bcs LiveWorld_ProviderFault')
    label('LiveWorld_AIFrameRun')
    put(f' jsl {sy["SourceFrameOwner4086_Run"]}\n bcs LiveWorld_ProviderFault\n cmp #$8001\n beq LiveWorld_AIFrameRun\n cmp #0\n bne LiveWorld_ExternalFrame')
    put(f' jsl {player["ForeignAIRun_Continue"]}\n bcs LiveWorld_ProviderFault\n cmp #0\n beq LiveWorld_ProviderComplete\n jmp LiveWorld_ProviderPending')
    label('LiveWorld_Animation')
    put(f' lda.l {sy["SourceUpdateAnimation4086_State"]}\n cmp #2\n beq LiveWorld_ProviderComplete\n cmp #1\n beq LiveWorld_AnimationFrame\n jsl TimedWorldGeometry_Begin\n bcs LiveWorld_ProviderFault\n cmp #0\n beq LiveWorld_ProviderComplete\n cmp #1\n bne LiveWorld_ProviderFault')
    label('LiveWorld_AnimationFrame')
    put(f' jsl {sy["SourceFrameOwner4086_Run"]}\n bcs LiveWorld_ProviderFault\n cmp #$8001\n beq LiveWorld_AnimationFrame\n cmp #0\n bne LiveWorld_ExternalFrame\n jsl TimedWorldGeometry_Continue\n bcs LiveWorld_ProviderFault\n jmp LiveWorld_ProviderComplete')
    label('LiveWorld_ExternalFrame');put(f' sta.l {WORK+12}\n jmp LiveWorld_ProviderPending')
    label('LiveWorld_Attack');put(' jsl CheckAttack_Run\n bcs LiveWorld_ProviderFault')
    put(f' lda.l {hp["controls"]+24}\n beq LiveWorld_ProviderComplete\n sta.l {WORK+12}\n jmp LiveWorld_ProviderPending')
    # Native fresh-birth fields are canonical extensions, not inferred from
    # scratch clearing. This closed single-actor chain admits no damage/DOT
    # writer: phase 8 remains pending whenever a real collision is requested.
    label('LiveWorld_Health')
    put(f' lda.l {HEALTH}+28\n cmp #$B6D2\n bne LiveWorld_ProviderPending\n lda.l {sy["SourceWorldTick4086_Maximum"]}\n cmp #1\n bne LiveWorld_ProviderPending\n jsl LiveHealth_Run\n rtl')
    label('LiveWorld_ProviderComplete');put(' lda #0\n clc\n rtl')
    label('LiveWorld_ProviderPending');put(' lda #1\n clc\n rtl')
    label('LiveWorld_ProviderFault');put(' sec\n rtl')
    # Resolve only compiler-owned Source/Vm symbols. Local and provider labels
    # remain for the real assembler, including all real continuation calls.
    text='\n'.join(lines)+'\n'
    serial=[0]
    def relax(m):
        serial[0]+=1;name='LiveWorld_Guard'+str(serial[0]);inv={'bne':'beq','beq':'bne','bcs':'bcc','bcc':'bcs'}[m[1]]
        return f' {inv} {name}\n jmp {m[2]}\n{name}:\n.a16\n.i16'
    text=re.sub(r'^ (bne|beq|bcs|bcc) (LiveWorld_\w+)$',relax,text,flags=re.M)
    text+=dispatcher(sy,{1:'LiveWorld_Freeze',2:'LiveWorld_Lost',3:'LiveWorld_Freeze',4:'LiveWorld_Freeze',
                        5:'LiveWorld_Script',6:'LiveWorld_AI',7:'LiveWorld_Animation',8:'LiveWorld_Attack',
                        9:'LiveWorld_Health',10:'LiveWorld_Velocity',11:'LiveGroundPost_Run',12:'LiveWorld_ClearMove'})
    text+=timed_geometry(sy)
    text+=attack_native(hp,sy)
    text+=move_native(tr,mp,sy,flat_work=FLAT,include_identities=False)
    text+=hit_native(hp,sy)
    text+=emit_normal_zero_mp(HEALTH,sy,charging_address=tail['base'],model_id=health_profile['model_id'])
    text+=post_native(sy,binding_base=BINDING,check_move_label='CallbackCheckMove_Execute')
    text+=player_controls(sy,layout(0x7fa000,6400))
    # Preserve the existing foreign arena's initialization/generation service;
    # only its owner-specific predicate differs for this private BG runtime.
    foreign=Path('src/core/source_foreign_workspace.pasm').read_text()
    foreign=foreign[foreign.index('SourceForeignWork_Init:'):foreign.index('SourceForeignWork_CheckCanvas:')]
    names=set(re.findall(r'^(SourceForeignWork_\w+):',foreign,re.M))|{'SourceForeignWork_CheckCanvas'}
    for name in sorted(names,key=len,reverse=True):
        foreign=re.sub(r'\b'+name+r'\b',name.replace('SourceForeignWork_','LiveWork_'),foreign)
    foreign+='''LiveWork_CheckCanvas:
.a16
.i16
 php
 rep #$31
 pha
 phx
 lda.l $7FFB88
 cmp #$B6D0
 bne LiveWork_OwnerBad
 lda.l $7E7700
 cmp #$B6D0
 bne LiveWork_OwnerBad
 lda.l Nmi_FrameBusy
 and #255
 cmp #1
 bne LiveWork_OwnerBad
 lda.l Nmi_HdmaEnableCurrent
 and #255
 bne LiveWork_OwnerBad
 ldx #0
LiveWork_OwnerQueue:
.a16
.i16
 lda.l DmaQueue+4,x
 and #DMA_OPT_ACTIVE
 bne LiveWork_OwnerBad
 txa
 clc
 adc #8
 tax
 cpx #64
 bcc LiveWork_OwnerQueue
 plx
 pla
 plp
 clc
 rtl
LiveWork_OwnerBad:
.a16
.i16
 plx
 pla
 plp
 sec
 rtl
'''
    for name in sorted(sy,key=len,reverse=True):
        if name.startswith(('SourceForeignWork_','SOURCE_FOREIGN_WORK_','Nmi_','DmaQueue','DMA_')):
            foreign=re.sub(r'\b'+name+r'\b',str(sy[name]),foreign)
    text+=foreign
    text+='\nLiveWorld_CodeEnd:\n.a16\n.i16\n'
    for bank,name,data in table_rows:
        text+=f'.bank {bank}\n.org $8000\nLiveWorld_Table_{name}:\n'
        text+='\n'.join(' .db '+','.join(f'${b:02X}' for b in data[i:i+24]) for i in range(0,len(data),24))+'\n'
    return text,dict(work=WORK,health=HEALTH,latest_snapshot=LATEST,binding=BINDING,flat_work=FLAT,
                     generation=GENERATION,retired_scene_video=[0x7e6200,0x7e8100],
                     pending_jump=jp,hit_identity=hp,movement_contact=mp,
                     table_rows=[dict(bank=b,name=n,bytes=len(d))for b,n,d in table_rows],
                     source_stage=placement,health_profile=health_profile,
                     health_birth_marker=0xb6d2,
                     health_scope='fresh native slot-0 birth; one He_Man; oldhealth/oldmp/DOT absence canonical extension; phase-8 damage remains unadmitted; no DOT-capable source callback',
                     constructor_audio_bound=False,
                     complete_engine_update_not_claimed=True,renderer_selected=False)
