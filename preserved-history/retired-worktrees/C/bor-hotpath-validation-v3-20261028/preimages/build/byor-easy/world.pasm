.snes
CHAR_INPUT_DRIVEN_AI = $2
CHAR_INPUT_DRIVEN_PROP = $3
VMSTAT_DONE = $4
CHAR_POS_X = $4
CHAR_INPUT_DRIVEN_BIKER = $4
CHAR_SELECTED_JUMP = $5
CHAR_POS_Y = $6
CHAR_INPUT_DRIVEN_NONCOMBAT = $7
CHAR_FACING_LEFT = $8
CHAR_SELECTED = $B
CHAR_ROSTER_INDEX = $C
CHAR_INPUT_DRIVEN = $F
CHAR_HIT_APPLIED = $22
CHAR_HP = $23
CHAR_FALL_STATE_TIMER = $30
CHAR_GRAB_TARGET = $3F
CHAR_GRABBED_BY = $40
CHAR_GRAB_TIMER = $41
CHAR_THROW_ZPOS = $43
CHAR_THROW_ZVEL = $45
CHAR_PICKUP_TYPE = $7F
CHAR_ZP_LEN = $85
StageEnv_ActorRowsBytes = $31E
StageBounds_Row = $F8000
Character_RenderPass = $9810D
G13_Player2_ContextEnter = $78221
G13_Player2_ContextExit = $7835E
Jump_PlayerInputGate = $8853F
G13_PlayerLifecycleIsOut = $785E6
G13_HandleP2Death = $78616
G13_SourcePlayerDeathP1 = $78631
StageEnv_ResetActors = $D91C4
SourceVisual_QueueRetireEntityOffset = $10962C
ActorBehavior_EntityAlive__source = $D9BEE
S5_LoadFrame = $DA0DA
S5_ActivateAttack = $DA135
S5_CheckCollision = $DA1A4
Game_Campaign_ResolveNext = $CA8FE
SourceVisual_CompletedInit = $10B036
Stage_LoadAndRespawn_Long = $E8FA
CharacterEntity_Play__no_context_exit = $EAF1
PlayerEntity_Hp = $7E0A23
Screen_PosX = $7E1601
WorldMaxX = $7E2597
Bg_LoadScene_StageIndex = $7E268E
G13_TwoPlayerEnabled = $7E26BD
G13_P1Out = $7E26CD
G13_P2Out = $7E26CE
Game_StageIndex = $7E2758
Game_CampaignId = $7E275E
SourceVisual_RetireEntityOffset = $7E4BB0
SourceVisual_ServiceField = $7E4BB4
SourceVisual_LatchedInput = $7E4BB6
SourceVisual_ServiceCount = $7E4BB8
SourceVisual_FieldPress1 = $7E4BBA
SourceVisual_FieldPress2 = $7E4BC0
SourceVisual_LatchedInput2 = $7E4BC6
SourceVisual_InputSampleField = $7E4BCC
Nmi_FrameCounter = $7E5023
StageEnv_Actors = $7E550F
StageEnv_BaseFraction = $7E550F
StageEnv_BaseInteger = $7E5511
StageDrop_State = $7E5575
Entity1_ItemRosterIdx = $7E58AB
Entity2_ItemRosterIdx = $7E58AC
Entity3_ItemRosterIdx = $7E58AD
Actor_InvulnFrames = $7E58B0
Entity4_ItemRosterIdx = $7E58B8
Entity5_ItemRosterIdx = $7E58B9
VmState_Status = $7FE090
S7_QueueHitSfxLong = $00B160
S6Host_ModelTable = $23FAD0
S6Host_ModelCount = 22
S6Host_SlotTable = $23FD90
S6Host_ModelRecordSize = 32
.bank 30
.org $8000
S6Game_Stage = 0
S6Game_PresentationDivisor = 2
S6Game_Player2X = 32
S6Game_ExpectedBirths = 1
S7Resident_Enabled = 2
S6Game_EnemyRoster = 28
S6Game_InitialAction = 65535
S6Game_PlayerFacing = 0
S6Game_Profile = 1
S6Game_ControlPlacement = 0
S6Game_StopSlot = 2
S6Game_StopDriver = 65535
S6Game_EntityResume = $EA81
S6Game_BindResume = $D9D35
S6Normal_BindResume = $D9D35
S6Game_AliveResume = $D9BEB
S6Game_SlotBusyResume = $D9C21
.include "E:/gh/snes-bor/src/core/actor_source_scheduler.pasm"
.include "E:/gh/snes-bor/src/core/actor_source_damage.pasm"
.include "E:/gh/snes-bor/src/core/actor_source_hit.pasm"
.include "E:/gh/snes-bor/src/core/actor_source_rng.pasm"
.include "E:/gh/snes-bor/src/core/actor_source_target.pasm"
.include "E:/gh/snes-bor/src/core/actor_source_lifecycle.pasm"
; Opt-in source world pass coordinator; not linked into shipped production.
; D = aligned world context in bank0 WRAM mirror, DBR0, A16/I16, decimal clear.
; 30 slot pointer-table24 (u16 actor DP per source slot; zero = empty slot).
; 34 source slot count <=150,36 current slot,38 pass,3A error,
; 3C/3E absolute source tick32,40 level-present,42 saved world DP.
; RNG/attack counter occupy00..22 independently. Actor36 receives world DP.
; Slot ordinal, NOT dense active index, owns collision parity.
; Actor context is256 bytes, page aligned $0100..$1E00, distinct from world.
; Linker must prove table immutability, unique actor contexts and no overlap
; with stack/other allocations. This bank0 ABI is NOT a150-live-actor claim.
; All bound actor policies are checked before any execution pass.
; Errors:1 policy,9 slot/layout, other actor error propagated. No fallback.
;
; Required host hooks (D=actor, world pointer36, preserve D/width/DBR):
; S6_WorldLost, S6_WorldGravity, S6_WorldAttack, S6_WorldHealth.
; These must implement source world/numeric/effect semantics or set actorFC.
; Missing hooks are link errors. No no-op production defaults are supplied.
; Gravity includes hole/pit processing; world attack owns whole target scan.
; S6_ThinkPass / AnimationPass consume their existing required hooks.
; Callback death is observed by every following pass and later slot visit.
; Time D0/D2 and world36 are immutable tick inputs, installed on the first
; enabled pass. An in-pass birth must install those inputs at bind time.
; Host supplies source time, does not advance it here, and owns pause/cap100.

; Bound entry is available only after a successful checked pass and while the
; host holds the immutable slot-table/count/policy/context-layout lease. It does
; NOT cache existence, health, target, callback errors, time or parity. Release,
; bind/respawn, table/count/policy mutation invalidate that lease. D/DBR and
; M/X entry contract is identical; both entries return with identical stack.
S6_UpdateWorldBound:
    rep #$30
    .a16
    .i16
    stz $3A
    jmp S6_UpdateWorld__start

S6_UpdateWorld:
    rep #$30
    .a16
    .i16
    tdc
    sta $42
    and #$00FF
    bne S6_UpdateWorld__bad
    tdc
    beq S6_UpdateWorld__bad
    cmp #$1F00
    bcs S6_UpdateWorld__bad
    lda $34
    cmp #151
    bcs S6_UpdateWorld__bad
    stz $3A
    stz $36
S6_UpdateWorld__preflight:
    .a16
    .i16
    lda $36
    cmp $34
    bcs S6_UpdateWorld__start
    asl a
    tay
    lda [$30],y
    beq S6_UpdateWorld__next_check
    tax
    and #$00FF
    bne S6_UpdateWorld__bad
    txa
    cmp #$1F00
    bcs S6_UpdateWorld__bad
    cmp $42
    beq S6_UpdateWorld__bad
    lda.l $7E00E0,x
    cmp #1
    bne S6_UpdateWorld__policy
S6_UpdateWorld__next_check:
    .a16
    .i16
    inc $36
    bra S6_UpdateWorld__preflight
S6_UpdateWorld__bad:
    .a16
    .i16
    lda #9
    sta $3A
    rtl
S6_UpdateWorld__policy:
    .a16
    .i16
    lda #1
    sta $3A
    rtl
S6_UpdateWorld__start:
; Generated fixed layout traversal, not model or replay specialization.
S6_Layout_P0:
    .a16
    .i16
    lda #0
    sta $38
    stz $36
    lda $40
    bne S6_Layout_P0_enabled
    jmp S6_Layout_P0_end
S6_Layout_P0_enabled:
    .a16
    .i16
S6_Layout_P0_S0:
    .a16
    .i16
    lda #0
    sta $36
    lda.l $7E19F6
    beq S6_Layout_P0_S0_next
    lda.l $7E19FC
    beq S6_Layout_P0_S0_call
    sta $3A
    rtl
S6_Layout_P0_S0_call:
    .a16
    .i16
    lda $3C
    sta.l $7E19D0
    lda $3E
    sta.l $7E19D2
    lda $42
    sta.l $7E1936
S6_Layout_P0_S0_ready:
    .a16
    .i16
    phd
    lda #$1900
    tcd
    jsl S6_WorldLost
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P0_S0_next
    sta $3A
    rtl
S6_Layout_P0_S0_next:
    .a16
    .i16
S6_Layout_P0_S1:
    .a16
    .i16
    lda #1
    sta $36
    lda.l $7E1AF6
    beq S6_Layout_P0_S1_next
    lda.l $7E1AFC
    beq S6_Layout_P0_S1_call
    sta $3A
    rtl
S6_Layout_P0_S1_call:
    .a16
    .i16
    lda $3C
    sta.l $7E1AD0
    lda $3E
    sta.l $7E1AD2
    lda $42
    sta.l $7E1A36
S6_Layout_P0_S1_ready:
    .a16
    .i16
    phd
    lda #$1A00
    tcd
    jsl S6_WorldLost
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P0_S1_next
    sta $3A
    rtl
S6_Layout_P0_S1_next:
    .a16
    .i16
S6_Layout_P0_S2:
    .a16
    .i16
    lda #2
    sta $36
    lda.l $7E1BF6
    beq S6_Layout_P0_S2_next
    lda.l $7E1BFC
    beq S6_Layout_P0_S2_call
    sta $3A
    rtl
S6_Layout_P0_S2_call:
    .a16
    .i16
    lda $3C
    sta.l $7E1BD0
    lda $3E
    sta.l $7E1BD2
    lda $42
    sta.l $7E1B36
S6_Layout_P0_S2_ready:
    .a16
    .i16
    phd
    lda #$1B00
    tcd
    jsl S6_WorldLost
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P0_S2_next
    sta $3A
    rtl
S6_Layout_P0_S2_next:
    .a16
    .i16
S6_Layout_P0_S3:
    .a16
    .i16
    lda #3
    sta $36
    lda.l $7E1CF6
    beq S6_Layout_P0_S3_next
    lda.l $7E1CFC
    beq S6_Layout_P0_S3_call
    sta $3A
    rtl
S6_Layout_P0_S3_call:
    .a16
    .i16
    lda $3C
    sta.l $7E1CD0
    lda $3E
    sta.l $7E1CD2
    lda $42
    sta.l $7E1C36
S6_Layout_P0_S3_ready:
    .a16
    .i16
    phd
    lda #$1C00
    tcd
    jsl S6_WorldLost
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P0_S3_next
    sta $3A
    rtl
S6_Layout_P0_S3_next:
    .a16
    .i16
S6_Layout_P0_S4:
    .a16
    .i16
    lda #4
    sta $36
    lda.l $7E1DF6
    beq S6_Layout_P0_S4_next
    lda.l $7E1DFC
    beq S6_Layout_P0_S4_call
    sta $3A
    rtl
S6_Layout_P0_S4_call:
    .a16
    .i16
    lda $3C
    sta.l $7E1DD0
    lda $3E
    sta.l $7E1DD2
    lda $42
    sta.l $7E1D36
S6_Layout_P0_S4_ready:
    .a16
    .i16
    phd
    lda #$1D00
    tcd
    jsl S6_WorldLost
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P0_S4_next
    sta $3A
    rtl
S6_Layout_P0_S4_next:
    .a16
    .i16
S6_Layout_P0_S5:
    .a16
    .i16
    lda #5
    sta $36
    lda.l $7E1EF6
    beq S6_Layout_P0_S5_next
    lda.l $7E1EFC
    beq S6_Layout_P0_S5_call
    sta $3A
    rtl
S6_Layout_P0_S5_call:
    .a16
    .i16
    lda $3C
    sta.l $7E1ED0
    lda $3E
    sta.l $7E1ED2
    lda $42
    sta.l $7E1E36
S6_Layout_P0_S5_ready:
    .a16
    .i16
    phd
    lda #$1E00
    tcd
    jsl S6_WorldLost
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P0_S5_next
    sta $3A
    rtl
S6_Layout_P0_S5_next:
    .a16
    .i16
    lda #6
    sta $36
S6_Layout_P0_end:
    .a16
    .i16
S6_Layout_P1:
    .a16
    .i16
    lda #1
    sta $38
    stz $36
    lda $40
    bne S6_Layout_P1_enabled
    jmp S6_Layout_P1_end
S6_Layout_P1_enabled:
    .a16
    .i16
S6_Layout_P1_S0:
    .a16
    .i16
    lda #0
    sta $36
    lda.l $7E19F6
    beq S6_Layout_P1_S0_next
    lda.l $7E19FC
    beq S6_Layout_P1_S0_call
    sta $3A
    rtl
S6_Layout_P1_S0_call:
    .a16
    .i16
S6_Layout_P1_S0_ready:
    .a16
    .i16
    phd
    lda #$1900
    tcd
    jsl S6_WorldGravity
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P1_S0_next
    sta $3A
    rtl
S6_Layout_P1_S0_next:
    .a16
    .i16
S6_Layout_P1_S1:
    .a16
    .i16
    lda #1
    sta $36
    lda.l $7E1AF6
    beq S6_Layout_P1_S1_next
    lda.l $7E1AFC
    beq S6_Layout_P1_S1_call
    sta $3A
    rtl
S6_Layout_P1_S1_call:
    .a16
    .i16
S6_Layout_P1_S1_ready:
    .a16
    .i16
    phd
    lda #$1A00
    tcd
    jsl S6_WorldGravity
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P1_S1_next
    sta $3A
    rtl
S6_Layout_P1_S1_next:
    .a16
    .i16
S6_Layout_P1_S2:
    .a16
    .i16
    lda #2
    sta $36
    lda.l $7E1BF6
    beq S6_Layout_P1_S2_next
    lda.l $7E1BFC
    beq S6_Layout_P1_S2_call
    sta $3A
    rtl
S6_Layout_P1_S2_call:
    .a16
    .i16
S6_Layout_P1_S2_ready:
    .a16
    .i16
    phd
    lda #$1B00
    tcd
    jsl S6_WorldGravity
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P1_S2_next
    sta $3A
    rtl
S6_Layout_P1_S2_next:
    .a16
    .i16
S6_Layout_P1_S3:
    .a16
    .i16
    lda #3
    sta $36
    lda.l $7E1CF6
    beq S6_Layout_P1_S3_next
    lda.l $7E1CFC
    beq S6_Layout_P1_S3_call
    sta $3A
    rtl
S6_Layout_P1_S3_call:
    .a16
    .i16
S6_Layout_P1_S3_ready:
    .a16
    .i16
    phd
    lda #$1C00
    tcd
    jsl S6_WorldGravity
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P1_S3_next
    sta $3A
    rtl
S6_Layout_P1_S3_next:
    .a16
    .i16
S6_Layout_P1_S4:
    .a16
    .i16
    lda #4
    sta $36
    lda.l $7E1DF6
    beq S6_Layout_P1_S4_next
    lda.l $7E1DFC
    beq S6_Layout_P1_S4_call
    sta $3A
    rtl
S6_Layout_P1_S4_call:
    .a16
    .i16
S6_Layout_P1_S4_ready:
    .a16
    .i16
    phd
    lda #$1D00
    tcd
    jsl S6_WorldGravity
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P1_S4_next
    sta $3A
    rtl
S6_Layout_P1_S4_next:
    .a16
    .i16
S6_Layout_P1_S5:
    .a16
    .i16
    lda #5
    sta $36
    lda.l $7E1EF6
    beq S6_Layout_P1_S5_next
    lda.l $7E1EFC
    beq S6_Layout_P1_S5_call
    sta $3A
    rtl
S6_Layout_P1_S5_call:
    .a16
    .i16
S6_Layout_P1_S5_ready:
    .a16
    .i16
    phd
    lda #$1E00
    tcd
    jsl S6_WorldGravity
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P1_S5_next
    sta $3A
    rtl
S6_Layout_P1_S5_next:
    .a16
    .i16
    lda #6
    sta $36
S6_Layout_P1_end:
    .a16
    .i16
S6_Layout_P2:
    .a16
    .i16
    lda #2
    sta $38
    stz $36
S6_Layout_P2_S0:
    .a16
    .i16
    lda #0
    sta $36
    lda.l $7E19F6
    beq S6_Layout_P2_S0_next
    lda.l $7E19FC
    beq S6_Layout_P2_S0_call
    sta $3A
    rtl
S6_Layout_P2_S0_call:
    .a16
    .i16
    lda $40
    bne S6_Layout_P2_S0_ready
    lda $3C
    sta.l $7E19D0
    lda $3E
    sta.l $7E19D2
    lda $42
    sta.l $7E1936
S6_Layout_P2_S0_ready:
    .a16
    .i16
    phd
    lda #$1900
    tcd
    jsl S6_ThinkPass
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P2_S0_next
    sta $3A
    rtl
S6_Layout_P2_S0_next:
    .a16
    .i16
S6_Layout_P2_S1:
    .a16
    .i16
    lda #1
    sta $36
    lda.l $7E1AF6
    beq S6_Layout_P2_S1_next
    lda.l $7E1AFC
    beq S6_Layout_P2_S1_call
    sta $3A
    rtl
S6_Layout_P2_S1_call:
    .a16
    .i16
    lda $40
    bne S6_Layout_P2_S1_ready
    lda $3C
    sta.l $7E1AD0
    lda $3E
    sta.l $7E1AD2
    lda $42
    sta.l $7E1A36
S6_Layout_P2_S1_ready:
    .a16
    .i16
    phd
    lda #$1A00
    tcd
    jsl S6_ThinkPass
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P2_S1_next
    sta $3A
    rtl
S6_Layout_P2_S1_next:
    .a16
    .i16
S6_Layout_P2_S2:
    .a16
    .i16
    lda #2
    sta $36
    lda.l $7E1BF6
    beq S6_Layout_P2_S2_next
    lda.l $7E1BFC
    beq S6_Layout_P2_S2_call
    sta $3A
    rtl
S6_Layout_P2_S2_call:
    .a16
    .i16
    lda $40
    bne S6_Layout_P2_S2_ready
    lda $3C
    sta.l $7E1BD0
    lda $3E
    sta.l $7E1BD2
    lda $42
    sta.l $7E1B36
S6_Layout_P2_S2_ready:
    .a16
    .i16
    phd
    lda #$1B00
    tcd
    jsl S6_ThinkPass
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P2_S2_next
    sta $3A
    rtl
S6_Layout_P2_S2_next:
    .a16
    .i16
S6_Layout_P2_S3:
    .a16
    .i16
    lda #3
    sta $36
    lda.l $7E1CF6
    beq S6_Layout_P2_S3_next
    lda.l $7E1CFC
    beq S6_Layout_P2_S3_call
    sta $3A
    rtl
S6_Layout_P2_S3_call:
    .a16
    .i16
    lda $40
    bne S6_Layout_P2_S3_ready
    lda $3C
    sta.l $7E1CD0
    lda $3E
    sta.l $7E1CD2
    lda $42
    sta.l $7E1C36
S6_Layout_P2_S3_ready:
    .a16
    .i16
    phd
    lda #$1C00
    tcd
    jsl S6_ThinkPass
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P2_S3_next
    sta $3A
    rtl
S6_Layout_P2_S3_next:
    .a16
    .i16
S6_Layout_P2_S4:
    .a16
    .i16
    lda #4
    sta $36
    lda.l $7E1DF6
    beq S6_Layout_P2_S4_next
    lda.l $7E1DFC
    beq S6_Layout_P2_S4_call
    sta $3A
    rtl
S6_Layout_P2_S4_call:
    .a16
    .i16
    lda $40
    bne S6_Layout_P2_S4_ready
    lda $3C
    sta.l $7E1DD0
    lda $3E
    sta.l $7E1DD2
    lda $42
    sta.l $7E1D36
S6_Layout_P2_S4_ready:
    .a16
    .i16
    phd
    lda #$1D00
    tcd
    jsl S6_ThinkPass
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P2_S4_next
    sta $3A
    rtl
S6_Layout_P2_S4_next:
    .a16
    .i16
S6_Layout_P2_S5:
    .a16
    .i16
    lda #5
    sta $36
    lda.l $7E1EF6
    beq S6_Layout_P2_S5_next
    lda.l $7E1EFC
    beq S6_Layout_P2_S5_call
    sta $3A
    rtl
S6_Layout_P2_S5_call:
    .a16
    .i16
    lda $40
    bne S6_Layout_P2_S5_ready
    lda $3C
    sta.l $7E1ED0
    lda $3E
    sta.l $7E1ED2
    lda $42
    sta.l $7E1E36
S6_Layout_P2_S5_ready:
    .a16
    .i16
    phd
    lda #$1E00
    tcd
    jsl S6_ThinkPass
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P2_S5_next
    sta $3A
    rtl
S6_Layout_P2_S5_next:
    .a16
    .i16
    lda #6
    sta $36
S6_Layout_P2_end:
    .a16
    .i16
S6_Layout_P3:
    .a16
    .i16
    lda #3
    sta $38
    stz $36
S6_Layout_P3_S0:
    .a16
    .i16
    lda #0
    sta $36
    lda.l $7E19F6
    beq S6_Layout_P3_S0_next
    lda.l $7E19FC
    beq S6_Layout_P3_S0_call
    sta $3A
    rtl
S6_Layout_P3_S0_call:
    .a16
    .i16
S6_Layout_P3_S0_ready:
    .a16
    .i16
    phd
    lda #$1900
    tcd
    jsl S6_AnimationPass
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P3_S0_next
    sta $3A
    rtl
S6_Layout_P3_S0_next:
    .a16
    .i16
S6_Layout_P3_S1:
    .a16
    .i16
    lda #1
    sta $36
    lda.l $7E1AF6
    beq S6_Layout_P3_S1_next
    lda.l $7E1AFC
    beq S6_Layout_P3_S1_call
    sta $3A
    rtl
S6_Layout_P3_S1_call:
    .a16
    .i16
S6_Layout_P3_S1_ready:
    .a16
    .i16
    phd
    lda #$1A00
    tcd
    jsl S6_AnimationPass
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P3_S1_next
    sta $3A
    rtl
S6_Layout_P3_S1_next:
    .a16
    .i16
S6_Layout_P3_S2:
    .a16
    .i16
    lda #2
    sta $36
    lda.l $7E1BF6
    beq S6_Layout_P3_S2_next
    lda.l $7E1BFC
    beq S6_Layout_P3_S2_call
    sta $3A
    rtl
S6_Layout_P3_S2_call:
    .a16
    .i16
S6_Layout_P3_S2_ready:
    .a16
    .i16
    phd
    lda #$1B00
    tcd
    jsl S6_AnimationPass
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P3_S2_next
    sta $3A
    rtl
S6_Layout_P3_S2_next:
    .a16
    .i16
S6_Layout_P3_S3:
    .a16
    .i16
    lda #3
    sta $36
    lda.l $7E1CF6
    beq S6_Layout_P3_S3_next
    lda.l $7E1CFC
    beq S6_Layout_P3_S3_call
    sta $3A
    rtl
S6_Layout_P3_S3_call:
    .a16
    .i16
S6_Layout_P3_S3_ready:
    .a16
    .i16
    phd
    lda #$1C00
    tcd
    jsl S6_AnimationPass
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P3_S3_next
    sta $3A
    rtl
S6_Layout_P3_S3_next:
    .a16
    .i16
S6_Layout_P3_S4:
    .a16
    .i16
    lda #4
    sta $36
    lda.l $7E1DF6
    beq S6_Layout_P3_S4_next
    lda.l $7E1DFC
    beq S6_Layout_P3_S4_call
    sta $3A
    rtl
S6_Layout_P3_S4_call:
    .a16
    .i16
S6_Layout_P3_S4_ready:
    .a16
    .i16
    phd
    lda #$1D00
    tcd
    jsl S6_AnimationPass
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P3_S4_next
    sta $3A
    rtl
S6_Layout_P3_S4_next:
    .a16
    .i16
S6_Layout_P3_S5:
    .a16
    .i16
    lda #5
    sta $36
    lda.l $7E1EF6
    beq S6_Layout_P3_S5_next
    lda.l $7E1EFC
    beq S6_Layout_P3_S5_call
    sta $3A
    rtl
S6_Layout_P3_S5_call:
    .a16
    .i16
S6_Layout_P3_S5_ready:
    .a16
    .i16
    phd
    lda #$1E00
    tcd
    jsl S6_AnimationPass
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P3_S5_next
    sta $3A
    rtl
S6_Layout_P3_S5_next:
    .a16
    .i16
    lda #6
    sta $36
S6_Layout_P3_end:
    .a16
    .i16
S6_Layout_P4:
    .a16
    .i16
    lda #4
    sta $38
    stz $36
S6_Layout_P4_S0:
    .a16
    .i16
    lda #0
    sta $36
    eor $3C
    and #1
    bne S6_Layout_P4_S0_next
    lda.l $7E19F6
    beq S6_Layout_P4_S0_next
    lda.l $7E19FC
    beq S6_Layout_P4_S0_call
    sta $3A
    rtl
S6_Layout_P4_S0_call:
    .a16
    .i16
S6_Layout_P4_S0_ready:
    .a16
    .i16
    phd
    lda #$1900
    tcd
    jsl S6_WorldAttack
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P4_S0_next
    sta $3A
    rtl
S6_Layout_P4_S0_next:
    .a16
    .i16
S6_Layout_P4_S1:
    .a16
    .i16
    lda #1
    sta $36
    eor $3C
    and #1
    bne S6_Layout_P4_S1_next
    lda.l $7E1AF6
    beq S6_Layout_P4_S1_next
    lda.l $7E1AFC
    beq S6_Layout_P4_S1_call
    sta $3A
    rtl
S6_Layout_P4_S1_call:
    .a16
    .i16
S6_Layout_P4_S1_ready:
    .a16
    .i16
    phd
    lda #$1A00
    tcd
    jsl S6_WorldAttack
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P4_S1_next
    sta $3A
    rtl
S6_Layout_P4_S1_next:
    .a16
    .i16
S6_Layout_P4_S2:
    .a16
    .i16
    lda #2
    sta $36
    eor $3C
    and #1
    bne S6_Layout_P4_S2_next
    lda.l $7E1BF6
    beq S6_Layout_P4_S2_next
    lda.l $7E1BFC
    beq S6_Layout_P4_S2_call
    sta $3A
    rtl
S6_Layout_P4_S2_call:
    .a16
    .i16
S6_Layout_P4_S2_ready:
    .a16
    .i16
    phd
    lda #$1B00
    tcd
    jsl S6_WorldAttack
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P4_S2_next
    sta $3A
    rtl
S6_Layout_P4_S2_next:
    .a16
    .i16
S6_Layout_P4_S3:
    .a16
    .i16
    lda #3
    sta $36
    eor $3C
    and #1
    bne S6_Layout_P4_S3_next
    lda.l $7E1CF6
    beq S6_Layout_P4_S3_next
    lda.l $7E1CFC
    beq S6_Layout_P4_S3_call
    sta $3A
    rtl
S6_Layout_P4_S3_call:
    .a16
    .i16
S6_Layout_P4_S3_ready:
    .a16
    .i16
    phd
    lda #$1C00
    tcd
    jsl S6_WorldAttack
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P4_S3_next
    sta $3A
    rtl
S6_Layout_P4_S3_next:
    .a16
    .i16
S6_Layout_P4_S4:
    .a16
    .i16
    lda #4
    sta $36
    eor $3C
    and #1
    bne S6_Layout_P4_S4_next
    lda.l $7E1DF6
    beq S6_Layout_P4_S4_next
    lda.l $7E1DFC
    beq S6_Layout_P4_S4_call
    sta $3A
    rtl
S6_Layout_P4_S4_call:
    .a16
    .i16
S6_Layout_P4_S4_ready:
    .a16
    .i16
    phd
    lda #$1D00
    tcd
    jsl S6_WorldAttack
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P4_S4_next
    sta $3A
    rtl
S6_Layout_P4_S4_next:
    .a16
    .i16
S6_Layout_P4_S5:
    .a16
    .i16
    lda #5
    sta $36
    eor $3C
    and #1
    bne S6_Layout_P4_S5_next
    lda.l $7E1EF6
    beq S6_Layout_P4_S5_next
    lda.l $7E1EFC
    beq S6_Layout_P4_S5_call
    sta $3A
    rtl
S6_Layout_P4_S5_call:
    .a16
    .i16
S6_Layout_P4_S5_ready:
    .a16
    .i16
    phd
    lda #$1E00
    tcd
    jsl S6_WorldAttack
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P4_S5_next
    sta $3A
    rtl
S6_Layout_P4_S5_next:
    .a16
    .i16
    lda #6
    sta $36
S6_Layout_P4_end:
    .a16
    .i16
S6_Layout_P5:
    .a16
    .i16
    lda #5
    sta $38
    stz $36
S6_Layout_P5_S0:
    .a16
    .i16
    lda #0
    sta $36
    lda.l $7E19F6
    beq S6_Layout_P5_S0_next
    lda.l $7E19FC
    beq S6_Layout_P5_S0_call
    sta $3A
    rtl
S6_Layout_P5_S0_call:
    .a16
    .i16
S6_Layout_P5_S0_ready:
    .a16
    .i16
    phd
    lda #$1900
    tcd
    jsl S6_WorldHealth
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P5_S0_next
    sta $3A
    rtl
S6_Layout_P5_S0_next:
    .a16
    .i16
S6_Layout_P5_S1:
    .a16
    .i16
    lda #1
    sta $36
    lda.l $7E1AF6
    beq S6_Layout_P5_S1_next
    lda.l $7E1AFC
    beq S6_Layout_P5_S1_call
    sta $3A
    rtl
S6_Layout_P5_S1_call:
    .a16
    .i16
S6_Layout_P5_S1_ready:
    .a16
    .i16
    phd
    lda #$1A00
    tcd
    jsl S6_WorldHealth
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P5_S1_next
    sta $3A
    rtl
S6_Layout_P5_S1_next:
    .a16
    .i16
S6_Layout_P5_S2:
    .a16
    .i16
    lda #2
    sta $36
    lda.l $7E1BF6
    beq S6_Layout_P5_S2_next
    lda.l $7E1BFC
    beq S6_Layout_P5_S2_call
    sta $3A
    rtl
S6_Layout_P5_S2_call:
    .a16
    .i16
S6_Layout_P5_S2_ready:
    .a16
    .i16
    phd
    lda #$1B00
    tcd
    jsl S6_WorldHealth
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P5_S2_next
    sta $3A
    rtl
S6_Layout_P5_S2_next:
    .a16
    .i16
S6_Layout_P5_S3:
    .a16
    .i16
    lda #3
    sta $36
    lda.l $7E1CF6
    beq S6_Layout_P5_S3_next
    lda.l $7E1CFC
    beq S6_Layout_P5_S3_call
    sta $3A
    rtl
S6_Layout_P5_S3_call:
    .a16
    .i16
S6_Layout_P5_S3_ready:
    .a16
    .i16
    phd
    lda #$1C00
    tcd
    jsl S6_WorldHealth
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P5_S3_next
    sta $3A
    rtl
S6_Layout_P5_S3_next:
    .a16
    .i16
S6_Layout_P5_S4:
    .a16
    .i16
    lda #4
    sta $36
    lda.l $7E1DF6
    beq S6_Layout_P5_S4_next
    lda.l $7E1DFC
    beq S6_Layout_P5_S4_call
    sta $3A
    rtl
S6_Layout_P5_S4_call:
    .a16
    .i16
S6_Layout_P5_S4_ready:
    .a16
    .i16
    phd
    lda #$1D00
    tcd
    jsl S6_WorldHealth
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P5_S4_next
    sta $3A
    rtl
S6_Layout_P5_S4_next:
    .a16
    .i16
S6_Layout_P5_S5:
    .a16
    .i16
    lda #5
    sta $36
    lda.l $7E1EF6
    beq S6_Layout_P5_S5_next
    lda.l $7E1EFC
    beq S6_Layout_P5_S5_call
    sta $3A
    rtl
S6_Layout_P5_S5_call:
    .a16
    .i16
S6_Layout_P5_S5_ready:
    .a16
    .i16
    phd
    lda #$1E00
    tcd
    jsl S6_WorldHealth
    lda $FC
    pld
    cmp #0
    beq S6_Layout_P5_S5_next
    sta $3A
    rtl
S6_Layout_P5_S5_next:
    .a16
    .i16
    lda #6
    sta $36
S6_Layout_P5_end:
    .a16
    .i16
    jmp S6_UpdateWorld__done
S6_UpdateWorld__done:
    .a16
    .i16
    lda #6
    sta $38
    rtl

S6_UpdateWorldDispatch:
    rep #$30
    .a16
    .i16
    cpy #0
    bne S6_UpdateWorldDispatch__gravity
    jsl S6_WorldLost
    rtl
S6_UpdateWorldDispatch__gravity:
    .a16
    .i16
    cpy #1
    bne S6_UpdateWorldDispatch__think
    jsl S6_WorldGravity
    rtl
S6_UpdateWorldDispatch__think:
    .a16
    .i16
    cpy #2
    bne S6_UpdateWorldDispatch__animation
    jsl S6_ThinkPass
    rtl
S6_UpdateWorldDispatch__animation:
    .a16
    .i16
    cpy #3
    bne S6_UpdateWorldDispatch__attack
    jsl S6_AnimationPass
    rtl
S6_UpdateWorldDispatch__attack:
    .a16
    .i16
    cpy #4
    bne S6_UpdateWorldDispatch__health
    jsl S6_WorldAttack
    rtl
S6_UpdateWorldDispatch__health:
    .a16
    .i16
    jsl S6_WorldHealth
    rtl

.include "E:/gh/snes-bor/src/core/actor_source_ai.pasm"
.include "E:/gh/snes-bor/src/core/actor_source_bridge.pasm"
; SOURCE_EXACT production-slot host. Opt-in build integration only.
; Six working contexts are views of the six existing production slots.
; No allocator, second entity list or independent world-coordinate owner.
; World page1700; contexts1900..1E00; clock1780; zero-velocity blocks17B0..17DF.
; Callers/linker must reserve those ranges and provide immutable SlotTable.
; All required live actors must be bound; mixed unbound interactions fault14.
; Rendering/media publication is a separate consumer, not inferred from frames.
S6Host_World = $1700
S6Host_Mode = $7E1760
S6Host_Error = $7E1764
S6Host_FrameEvents = $7E176C
S6Host_HitEvents = $7E176E
S6Host_Action = StageEnv_Actors+74
S6Host_Frame = StageEnv_Actors+84
S6Host_Role = StageEnv_Actors+86
; Normal's stage-boundary command, projected into source coordinates once per
; physical stage. This follows the six-byte native-target mask at $412D00.
S6Host_PlayerWorldMaxX = $412D06
; Persistent production input record for the source tick currently executing.
; Relay publishes these words from the sequenced 8-byte-per-tick input ring.
S6Host_InputP1Press = $412020
S6Host_InputP1Trigger = $412022
S6Host_InputP2Press = $412024
S6Host_InputP2Trigger = $412026
; Private opt-in catch-up transaction: 0=production owner, 1=acquire on tick,
; 2=resident source owner. World $5E is reserved; not an actor-context offset.
; Caller must flush before any outside-world consumer or mutation.
S7Resident_Owner = $7E175E

; Bind an EXISTING production slot. Caller owns normal spawn/respawn and must
; have a compiler-approved source spawn record (in particular no random drop).
; ModelTable records32: roster,type,health,flags,roleptr low/high,count,
; idle,pain,rise,attack1,walk,range low/high,unsupported features,speed20.
; flags1=grounded single-attack opponent,2=controlled source player action.
; No model-name selection, no slot allocation. Failure never delegates.
S6Host_BindExisting:
    php
    rep #$30
    .a16
    .i16
    phx
    phy
    phb
    phd
    sep #$20
    .a8
    lda #0
    pha
    plb
    rep #$30
    .a16
    .i16
    tdc
    sec
    sbc #$0A00
    sta.l $7E1752
    ldy #$1900
S6Host_BindExisting__slot:
    .a16
    .i16
    cmp #0
    beq S6Host_BindExisting__slot_found
    sec
    sbc #CHAR_ZP_LEN
    bcc S6Host_BindExisting__bad_slot
    pha
    tya
    clc
    adc #$100
    tay
    pla
    cpy #$1F00
    bcc S6Host_BindExisting__slot
S6Host_BindExisting__bad_slot:
    .a16
    .i16
    lda #14
    jmp S6Host_BindExisting__error
S6Host_BindExisting__slot_found:
    .a16
    .i16
    tya
    sta.l $7E1754
    lda CHAR_ROSTER_INDEX
    and #$00FF
    sta.l $7E1758
    ldx #0
S6Host_BindExisting__model:
    .a16
    .i16
    cpx #S6Host_ModelCount*32
    bcs S6Host_BindExisting__bad_slot
    lda.l S6Host_ModelTable,x
    cmp.l $7E1758
    bne S6Host_BindExisting__model_next
    lda CHAR_INPUT_DRIVEN
    and #$00FF
    cmp.l S6Host_ModelTable+2,x
    beq S6Host_BindExisting__model_found
S6Host_BindExisting__model_next:
    txa
    clc
    adc #32
    tax
    bra S6Host_BindExisting__model
S6Host_BindExisting__model_found:
    .a16
    .i16
    txa
    sta.l $7E1756
    lda.l S6Host_ModelTable+4,x
    cmp #$FFFF
    beq S6Normal_BindExisting__keep_health
    cmp #256
    bcs S6Host_BindExisting__bad_slot
S6Normal_BindExisting__keep_health:
    lda.l S6Host_ModelTable+2,x
    cmp #1
    beq S6Host_BindExisting__player_policy
    cmp #2
    bne S6Host_BindExisting__bad_slot
    lda.l S6Host_ModelTable+6,x
    and #$FFFB
    cmp #1
    bne S6Host_BindExisting__bad_slot
    lda.l S6Host_ModelTable+4,x
    cmp #$FFFF
    beq S6Normal_BindExisting__health_ready
    sep #$20
    .a8
    sta CHAR_HP
    rep #$30
    .a16
    .i16
S6Normal_BindExisting__health_ready:
    bra S6Host_BindExisting__player
S6Host_BindExisting__player_policy:
    .a16
    .i16
    lda.l S6Host_ModelTable+6,x
    and #$FFFB
    cmp #2
    beq S6Host_BindExisting__player_policy_valid
    jmp S6Host_BindExisting__bad_slot
S6Host_BindExisting__player_policy_valid:
S6Host_BindExisting__player:
    .a16
    .i16
    lda.l $7E1754
    tcd
    ldx #254
    lda #0
S6Host_BindExisting__clear:
    .a16
    .i16
    sta $00,x
    dex
    dex
    bpl S6Host_BindExisting__clear
    lda.l $7E1752
    sta $7A
    tax
    lda.l $7E1754
    sta.l S6Bridge_Context,x
    ; Model flag bit 2 selects the Normal compiler's rounded 4/5 XY bridge.
    ; Existing measured/reference model records retain exact policy 1.
    lda.l $7E1756
    tax
    lda.l S6Host_ModelTable+6,x
    and #4
    beq S6Host_BindExisting__exact_bridge
    lda #$0102
    bra S6Host_BindExisting__bridge_policy
S6Host_BindExisting__exact_bridge:
    lda #$0101
S6Host_BindExisting__bridge_policy:
    ldx $7A
    sta.l S6Bridge_Policy,x
    lda #$FFFF
    sta.l S6Host_Action,x
    lda #0
    sta.l S6Bridge_TargetHandle,x
    lda.l $7E0A00+CHAR_HP,x
    and #$00FF
    sta.l S6Bridge_DisplayedHealth,x
    lda #1
    sta $E0
    lda #S6Host_World
    sta $36
    lda.l $7E1754
    sec
    sbc #$1900
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    clc
    adc #$17B0
    sta $B0
    jsl S6_StopMovement
    ; Normal's sequenced worker ring owns a zero-based 32-bit tick epoch.
    ; S6Host_Mode changes from the bind barrier (3) to active owner (1), so
    ; it cannot select the clock domain. Use the ring producer's committed
    ; timestamp for every Normal bind; the legacy fallback uses caller time.
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    bne S6Host_BindExisting__clock_legacy
    lda.l S6Game_TickCommit
    sta $D0
    lda.l S6Game_TickCommit+2
    sta $D2
    bra S6Host_BindExisting__clock_ready
S6Host_BindExisting__clock_legacy:
    .a16
    .i16
    lda.l $7E173C
    sta $D0
    lda.l $7E173E
    sta $D2
S6Host_BindExisting__clock_ready:
    .a16
    .i16
    ldx $7A
    jsl S6Bridge_Import
    lda $FC
    beq S6Host_BindExisting__bridge_ok
    jmp S6Host_BindExisting__error
S6Host_BindExisting__bridge_ok:
    lda.l $7E1756
    tax
    lda.l S6Host_ModelTable+8,x
    sta $C8
    lda.l S6Host_ModelTable+10,x
    sta $CA
    lda.l S6Host_ModelTable+12,x
    sta $CC
    lda.l S6Host_ModelTable+14,x
    sta $38
    lda.l S6Host_ModelTable+16,x
    sta $3A
    lda.l S6Host_ModelTable+18,x
    sta $3C
    lda.l S6Host_ModelTable+20,x
    sta $A0
    lda.l S6Host_ModelTable+22,x
    sta $A6
    lda.l S6Host_ModelTable+24,x
    sta $A2
    lda.l S6Host_ModelTable+26,x
    sta $A4
    lda.l S6Host_ModelTable+28,x
    sta $A8
    lda.l S6Host_ModelTable+30,x
    sta $C6
    lda.l S6Host_ModelTable+2,x
    sta $F2
    cmp #1
    beq S6Host_BindExisting__player_driver
    lda #6
    bra S6Host_BindExisting__driver
S6Host_BindExisting__player_driver:
    .a16
    .i16
    lda #8
S6Host_BindExisting__driver:
    .a16
    .i16
    sta $E6
    lda #$FFFF
    sta $E4
    sta $F4
    lda $38
    jsl S6_SetRole
    lda $FC
    bne S6Host_BindExisting__error
    ; S5_LoadFrame uses E8/EA as scratch while S6_SetRole enters the initial
    ; authored frame. Set the first think deadline after that transaction so
    ; the scheduler fields cannot be clobbered by frame preparation.
    lda $D0
    clc
    adc #1
    sta $E8
    lda $D2
    adc #0
    sta $EA
S6Host_BindExisting__scheduled:
    bra S6Host_BindExisting__return
S6Host_BindExisting__error:
    .a16
    .i16
    sta.l S6Host_Error
S6Host_BindExisting__return:
    rep #$30
    .a16
    .i16
    pld
    plb
    ply
    plx
    plp
    rtl

; Public tick. D/DBR/P/X/Y preserved. World3C is supplied source time.
; Default: each tick imports production fields then exports the transaction.
; Opt-in resident window: acquire once; shared contexts own mutable state until
; flush. No outside simulation consumer may execute while that owner is held.
S6Host_Tick:
    php
    rep #$30
    .a16
    .i16
    phx
    phy
    phb
    phd
    sep #$20
    .a8
    lda #0
    pha
    plb
    rep #$30
    .a16
    .i16
    lda #S6Host_World
    tcd
    lda $60
    cmp #1
    beq S6Host_Tick__enabled
    jmp S6Host_Tick__return
S6Host_Tick__enabled:
    .a16
    .i16
    lda $64
    beq S6Host_Tick__ready
    jmp S6Host_Tick__return
S6Host_Tick__ready:
    .a16
    .i16
    lda $5E
    cmp #2
    bne S6Host_Tick__acquire
    jmp S6Host_Tick__resident_execute
S6Host_Tick__acquire:
    .a16
    .i16
    stz $44
    stz $46
    stz $52                  ; production row byte offset
    lda #$1900
    sta $54                  ; paired scheduler working page
S6Host_Tick__import:
    .a16
    .i16
    ldx $52
    lda.l S6Bridge_Policy,x
    and #$00FF
    cmp #1
    beq S6Host_Tick__bound
    cmp #2
    beq S6Host_Tick__bound
    cpx #CHAR_ZP_LEN
    bne S6Host_Tick__unbound_health
    lda.l G13_TwoPlayerEnabled
    and #255
    beq S6Host_Tick__empty
S6Host_Tick__unbound_health:
    .a16
    .i16
    lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
    and #$00FF
    cmp #1
    beq S6Normal_Tick__check_unbound_roster
    cmp #2
    bne S6Host_Tick__empty
S6Normal_Tick__check_unbound_roster:
    lda.l $7E0A00+CHAR_HP,x
    and #$00FF
    beq S6Host_Tick__empty
    lda.l $7E0A00+CHAR_ROSTER_INDEX,x
    and #$00FF
    cmp #28
    beq S6Host_Tick__empty
    jsl S6Normal_IsRosterBound
    bcs S6Normal_Tick__catalogued_unbound
    jmp S6Host_Tick__empty
S6Normal_Tick__catalogued_unbound:
    jmp S6Host_Tick__unbound
S6Host_Tick__empty:
    .a16
    .i16
    ldx $54
    lda #1
    sta.l $7E00E0,x
    lda #0
    sta.l $7E00F6,x
    bra S6Host_Tick__next_import
S6Host_Tick__bound:
    .a16
    .i16
    phd
    lda $54
    tcd
    jsl S6Bridge_Import
    lda $FC
    pld
    cmp #0
    beq S6Host_Tick__imported
    jmp S6Host_Tick__fault
S6Host_Tick__imported:
    .a16
    .i16
    ldx $54
    lda.l $7E00F6,x
    beq S6Host_Tick__next_import
    lda.l $7E00F2,x
    cmp #1
    bne S6Host_Tick__next_import
    lda $52
    beq S6Host_Tick__player0
    cmp #CHAR_ZP_LEN
    beq S6Host_Tick__player1_slot
    jmp S6Host_Tick__unbound
S6Host_Tick__player1_slot:
    lda.l G13_TwoPlayerEnabled
    and #$00FF
    bne S6Host_Tick__player1_enabled
    jmp S6Host_Tick__unbound
S6Host_Tick__player1_enabled:
    lda $54
    sta $46
    bra S6Host_Tick__next_import
S6Host_Tick__player0:
    .a16
    .i16
    lda $54
    sta $44
S6Host_Tick__next_import:
    .a16
    .i16
    jsl S6Host_NextRow
    bcs S6Normal_Tick__import_done
    brl S6Host_Tick__import
S6Normal_Tick__import_done:
    lda $5E
    beq S6Host_Tick__execute
    lda #2
    sta $5E
S6Host_Tick__execute:
    .a16
    .i16
    jsl S6_UpdateWorld
    bra S6Host_Tick__world_done
S6Host_Tick__resident_execute:
    .a16
    .i16
    ; Source slot layout/policies were validated by this batch's first pass.
    ; No external bind or layout mutation is allowed while contexts own state.
    ; Mutable same-pass checks remain in the generated traversal.
    jsl S6_UpdateWorldBound
S6Host_Tick__world_done:
    .a16
    .i16
    ; In the persistent SA-1 runtime, S6Host_Tick__resident_execute has
    ; already queued the tick and deliberately did not mutate the S-CPU
    ; world error/context mirrors.  Return to the source clock here: the
    ; coherent snapshot is exported once at the presentation boundary by
    ; S7Resident_Flush.  Running the synchronous error/export tail against
    ; stale S-CPU contexts both consumed per-tick CPU and could mistake the
    ; untouched $3A scratch for a world callback failure.
    lda $5E
    cmp #2
    beq S6Host_Tick__return
    lda $3A
    bne S6Host_Tick__fault
S6Host_Tick__export_all:
    .a16
    .i16
    stz $52
    lda #$1900
    sta $54
S6Host_Tick__export:
    .a16
    .i16
    ldx $52
    lda.l S6Bridge_Policy,x
    and #$00FF
    cmp #1
    beq S6Host_Tick__export_bound
    cmp #2
    bne S6Host_Tick__next_export
S6Host_Tick__export_bound:
    phd
    lda $54
    tcd
    ; Native autokill/removal must perform the source cleanup, not just hide.
    lda $F6
    beq S6Host_Tick__remove_actor
    lda.l S7Resident_Owner
    cmp #2
    bne S6Host_Tick__commit_actor
    bra S6Host_Tick__actor_committed
S6Host_Tick__remove_actor:
    .a16
    .i16
    jsl S6_KillUnlinked
S6Host_Tick__commit_actor:
    .a16
    .i16
    jsl S6Bridge_Export
    lda $FC
    bne S6Host_Tick__actor_committed
    lda $F6
    bne S6Host_Tick__actor_committed
    jsl S6Host_ClearRemovedReferences
S6Host_Tick__actor_committed:
    .a16
    .i16
    lda $FC
    pld
    cmp #0
    bne S6Host_Tick__fault
S6Host_Tick__next_export:
    .a16
    .i16
    jsl S6Host_NextRow
    bcc S6Host_Tick__export
    bra S6Host_Tick__return
S6Host_Tick__unbound:
    .a16
    .i16
    lda #14
S6Host_Tick__fault:
    .a16
    .i16
    sta $64
S6Host_Tick__return:
    rep #$30
    .a16
    .i16
    pld
    plb
    ply
    plx
    plp
    rtl

S6Host_NextRow:
    .a16
    .i16
    lda $54
    clc
    adc #$100
    sta $54
    lda $52
    clc
    adc #CHAR_ZP_LEN
    sta $52
    cmp #CHAR_ZP_LEN*6
    rtl

; Release resident ownership, publishing all scalar fields before returning.
; No source tick, no re-import. Preserve the host tick's caller ABI exactly.
S7Resident_Flush:
    php
    rep #$30
    .a16
    .i16
    phx
    phy
    phb
    phd
    sep #$20
    .a8
    lda #0
    pha
    plb
    rep #$30
    .a16
    .i16
    lda #S6Host_World
    tcd
    lda $5E
    stz $5E
    cmp #2
    beq S7Resident_Flush__publish
    jmp S6Host_Tick__return
S7Resident_Flush__publish:
    .a16
    .i16
    jmp S6Host_Tick__export_all

; Remove an actual production handle (A=entity DP). Source kill owns this
; operation; it does not free/move the persistent OOP character allocation.
; Player life stock and OUT remain owned by G13_SourcePlayerDeathP1/P2 after
; this bridge publishes HP=0. Worker absence is not equivalent to exhausted
; stock and must not short-circuit BOR's native fall/decrement/respawn path.
S6Host_RemoveHandle:
    php
    rep #$30
    .a16
    .i16
    phx
    phy
    phb
    phd
    sec
    sbc #$0A00
    tax
    txa
    sta.l SourceVisual_RetireEntityOffset
    ldy #6
S6Host_RemoveHandle__validate:
    .a16
    .i16
    cmp #0
    beq S6Host_RemoveHandle__valid
    sec
    sbc #CHAR_ZP_LEN
    bcc S6Host_RemoveHandle__bad
    dey
    bne S6Host_RemoveHandle__validate
    bra S6Host_RemoveHandle__bad
S6Host_RemoveHandle__valid:
    .a16
    .i16
    sep #$20
    .a8
    lda #0
    pha
    plb
    rep #$30
    .a16
    .i16
    lda.l S6Bridge_Context,x
    beq S6Host_RemoveHandle__bad
    tcd
    ; $FC is actor scratch as well as this transaction's status word. The
    ; resident worker intentionally does not import/export the whole context
    ; for unlink, so initialize the return status before either path.
    stz $FC
    lda.l S7Resident_Owner
    cmp #2
    beq S6Host_RemoveHandle__resident
    jsl S6Bridge_Import
    lda $FC
    bne S6Host_RemoveHandle__error
    bra S6Host_RemoveHandle__temporary
S6Host_RemoveHandle__resident:
    .a16
    .i16
    ; The ordered unlink came from SA-1 after it already ran
    ; S6_KillUnlinked against canonical state. The S-CPU actor page is only
    ; a sampled mirror and can have an older environment base; replaying
    ; kill/export here duplicates lifecycle and can reject a valid unlink on
    ; that stale projection. Publish only the native-slot consequences.
    ldx $7A
    lda #0
    sta.l S6Bridge_DisplayedHealth,x
    sep #$20
    .a8
    sta.l S6Bridge_Exists,x
    sta.l $7E0A00+CHAR_HP,x
    rep #$30
    .a16
    .i16
    jsl S6Host_ClearRemovedReferences
    lda.l SourceVisual_RetireEntityOffset
    tax
    jsl SourceVisual_QueueRetireEntityOffset
    bra S6Host_RemoveHandle__return
S6Host_RemoveHandle__temporary:
    .a16
    .i16
    jsl S6_KillUnlinked
    jsl S6Bridge_Export
    lda $FC
    bne S6Host_RemoveHandle__error
    jsl S6Host_ClearRemovedReferences
    lda.l SourceVisual_RetireEntityOffset
    tax
    jsl SourceVisual_QueueRetireEntityOffset
    bra S6Host_RemoveHandle__return
S6Host_RemoveHandle__bad:
    rep #$30
    .a16
    .i16
    lda #14
S6Host_RemoveHandle__error:
    .a16
    .i16
    sta.l S6Host_Error
S6Host_RemoveHandle__return:
    rep #$30
    .a16
    .i16
    pld
    plb
    ply
    plx
    plp
    rtl

; Source host callbacks. No accepted-compat execution fallback.
S6_Think:
    rep #$30
    .a16
    .i16
    lda $E6
    cmp #2
    beq S6Host_Recovery
    cmp #3
    beq S6Host_Recovery
    cmp #4
    beq S6Host_Lifecycle
    cmp #5
    beq S6Host_Lifecycle
    cmp #6
    beq S6Host_Lifecycle
    cmp #7
    bne S6_Think__not_pain
    jml S6Host_PlayerPain
S6_Think__not_pain:
    .a16
    .i16
    cmp #8
    beq S6Host_PlayerAction
    cmp #9
    bne S6_Think__enemy
    jml S6Host_PlayerAttack
S6_Think__enemy:
    .a16
    .i16
    jsl S6_EnemyDecision
    jsl S6Host_PublishTarget
    rtl
S6Host_Recovery:
    .a16
    .i16
    jml S6_RecoveryThink
S6Host_Lifecycle:
    .a16
    .i16
    jml S6_GroundLifecycle

; Target publication is a real production-slot handle, not a context address.
; Selection itself remains the already-proven S6_SelectTarget implementation.
S6Host_PublishTarget:
    .a16
    .i16
    lda $34
    beq S6Host_PublishTarget__none
    tax
    lda.l $7E00F6,x
    beq S6Host_PublishTarget__none
    lda.l $7E007A,x
    clc
    adc #$0A00
    bra S6Host_PublishTarget__store
S6Host_PublishTarget__none:
    .a16
    .i16
    lda #0
S6Host_PublishTarget__store:
    .a16
    .i16
    ldx $7A
    sta.l S6Bridge_TargetHandle,x
    rtl

S6Host_ClearRemovedReferences:
    .a16
    .i16
    lda $7A
    clc
    adc #$0A00
    sta $AA
    ldx #0
S6Host_ClearRemovedReferences__slot:
    .a16
    .i16
    lda.l S6Bridge_TargetHandle,x
    cmp $AA
    bne S6Host_ClearRemovedReferences__next
    lda #0
    sta.l S6Bridge_TargetHandle,x
S6Host_ClearRemovedReferences__next:
    .a16
    .i16
    txa
    clc
    adc #CHAR_ZP_LEN
    tax
    cpx #CHAR_ZP_LEN*6
    bcc S6Host_ClearRemovedReferences__slot
    rtl

; Normal's persistent player controller consumes only the current worker-tick
; input words. Held directions advance the canonical source position at the
; model's authored speed20, using the same twentieth-pixel accumulator as the
; source enemy driver. Attack remains an edge from that same tick record.
S6Host_PlayerAction:
    sep #$20
    .a8
    lda CHAR_SELECTED
    cmp #CHAR_SELECTED_JUMP
    bne S6Host_PlayerAction__grounded
    ; BOR's Jump_PlayerTick remains the sole owner of the existing 60-Hz
    ; airborne X/Z transition. Do not apply the persistent 200-Hz grounded
    ; controller while that native substate is active.
    jml S6Host_PlayerAction__done
S6Host_PlayerAction__grounded:
    rep #$30
    .a16
    .i16
    jsl S6Host_PlayerMove
    jsl S6Host_PlayerInputTrigger
    and #$4000
    bne S6Host_PlayerAction__attack
S6Host_PlayerAction__ordinary:
    .a16
    .i16
    ldx $7A
    lda.l S6Host_Action,x
    cmp #$FFFF
    beq S6Host_PlayerAction__locomotion
    cmp $A0
    beq S6Host_PlayerAction__attack
    jml S6Host_PlayerAction__unsupported
S6Host_PlayerAction__attack:
    ldx $7A
    lda #$FFFF
    sta.l S6Host_Action,x
    stz $FA
    lda $A0
    jsl S6_SetRole
    lda $08
    ora #1
    sta $08
    lda #9
    sta $E6
    rtl
S6Host_PlayerAction__locomotion:
    jsl S6Host_PlayerInputHeld
    and #$0F00
    beq S6Host_PlayerAction__idle
    lda $A6
    bra S6Host_PlayerAction__set_locomotion
S6Host_PlayerAction__idle:
    lda $38
S6Host_PlayerAction__set_locomotion:
    stz $FA
    jsl S6_SetRole
    lda #8
    sta $E6
S6Host_PlayerAction__done:
    .a16
    .i16
    rtl
S6Host_PlayerAction__unsupported:
    .a16
    .i16
    lda #15
    sta $FC
    rtl
S6Host_PlayerAttack:
    .a16
    .i16
    jsl S6Host_PlayerMove
    lda $10
    bne S6Host_PlayerAction__done
    lda $08
    and #$FFFE
    sta $08
    bra S6Host_PlayerIdle
S6Host_PlayerPain:
    .a16
    .i16
    ; No special-input/grab fallback. Controlled fixture supplies no input.
    lda $C4
    bne S6Host_PlayerAction__unsupported
    lda $10
    bne S6Host_PlayerAction__done
S6Host_PlayerIdle:
    .a16
    .i16
    stz $FA
    lda $38
    jsl S6_SetRole
    lda #8
    sta $E6
    rtl

; Return the per-tick held or edge word for the currently bound player.
; Production P1/P2 occupy physical context rows 0 and CHAR_ZP_LEN.
S6Host_PlayerInputHeld:
    .a16
    .i16
    lda $7A
    cmp #CHAR_ZP_LEN
    beq S6Host_PlayerInputHeld__p2
    lda.l S6Host_InputP1Press
    rtl
S6Host_PlayerInputHeld__p2:
    lda.l S6Host_InputP2Press
    rtl

S6Host_PlayerInputTrigger:
    .a16
    .i16
    lda $7A
    cmp #CHAR_ZP_LEN
    beq S6Host_PlayerInputTrigger__p2
    lda.l S6Host_InputP1Trigger
    rtl
S6Host_PlayerInputTrigger__p2:
    lda.l S6Host_InputP2Trigger
    rtl

; Move the player in SOURCE_EXACT coordinates. The PAK-derived model speed is
; stored in twentieths; S6_EnemyApplyAxis retains signed twentieth-pixel
; remainders in this actor context, so 0.9/1.2 authored speeds do not drift.
; Left wins over right and up wins over down, matching Character_PlayFrame.
; B doubles speed. Direction/role and coordinates all belong to this one SA-1
; pass; the S-CPU consumes only the next coherent snapshot.
S6Host_PlayerMove:
    .a16
    .i16
    jsl S6Host_PlayerInputHeld
    sta $B4
    and #$0300
    beq S6Host_PlayerMove__x_stop
    and #$0200
    beq S6Host_PlayerMove__x_right
    lda $C6
    eor #$FFFF
    inc a
    bra S6Host_PlayerMove__x_speed
S6Host_PlayerMove__x_right:
    lda $C6
S6Host_PlayerMove__x_speed:
    sta $B6
    lda $B4
    and #$8000
    beq S6Host_PlayerMove__x_load
    lda $B6
    asl a
    sta $B6
S6Host_PlayerMove__x_load:
    lda $B6
    bra S6Host_PlayerMove__x_store
S6Host_PlayerMove__x_stop:
    lda #0
    sta $B6
S6Host_PlayerMove__x_store:
    ldx $B0
    sta.l $7E0000,x
    stz $90
    stz $92
    stz $94
    jsl S6_EnemyApplyAxis
    ; The S-CPU's Character_PlayFrame clamps player X to WorldMaxX after a
    ; horizontal step. Persistent ownership must preserve that stage-local
    ; rule too; otherwise an actor carried from a wider previous stage can
    ; walk past the new stage and eventually exceed the snapshot bridge's
    ; admitted source-coordinate domain. Left wins over right, and only the
    ; selected direction's native clamp is applied.
    lda.l S6Host_Mode
    cmp #1
    bne S6Host_PlayerMove__x_bound_done
    lda.l S7Resident_Owner
    cmp #2
    bne S6Host_PlayerMove__x_bound_done
    lda $B4
    and #$0300
    beq S6Host_PlayerMove__x_bound_done
    and #$0200
    beq S6Host_PlayerMove__x_bound_right
    lda $14
    bpl S6Host_PlayerMove__x_bound_done
    stz $14
    bra S6Host_PlayerMove__x_bound_done
S6Host_PlayerMove__x_bound_right:
    .a16
    .i16
    lda $14
    ; A signed negative position is below a nonnegative upper bound.
    ; Keep the existing directional contract; never map it to the far edge.
    bmi S6Host_PlayerMove__x_bound_done
    cmp.l S6Host_PlayerWorldMaxX
    bcc S6Host_PlayerMove__x_bound_done
    lda.l S6Host_PlayerWorldMaxX
    sta $14
S6Host_PlayerMove__x_bound_done:

    lda $B4
    and #$0C00
    beq S6Host_PlayerMove__y_stop
    and #$0800
    beq S6Host_PlayerMove__y_down
    lda $C6
    eor #$FFFF
    inc a
    bra S6Host_PlayerMove__y_speed
S6Host_PlayerMove__y_down:
    lda $C6
S6Host_PlayerMove__y_speed:
    sta $B6
    lda $B4
    and #$8000
    beq S6Host_PlayerMove__y_load
    lda $B6
    asl a
    sta $B6
S6Host_PlayerMove__y_load:
    lda $B6
    bra S6Host_PlayerMove__y_store
S6Host_PlayerMove__y_stop:
    lda #0
    sta $B6
S6Host_PlayerMove__y_store:
    sta $B6
    ldx $B0
    txa
    clc
    adc #4
    tax
    lda $B6
    sta.l $7E0000,x
    lda #2
    sta $90
    sta $92
    lda #4
    sta $94
    jsl S6_EnemyApplyAxis

    lda $B4
    and #$0300
    beq S6Host_PlayerMove__done
    and #$0200
    bne S6Host_PlayerMove__left
    lda #1
    sta $1A
    rtl
S6Host_PlayerMove__left:
    lda #0
    sta $1A
S6Host_PlayerMove__done:
    rtl

S6_FrameChanged:
    rep #$30
    .a16
    .i16
    ldx $7A
    lda $06
    sta.l S6Host_Frame,x
    lda $E4
    cmp $38
    beq S6_FrameChanged__idle
    cmp $A6
    beq S6_FrameChanged__walk
    cmp $A0
    beq S6_FrameChanged__attack
    cmp $3A
    beq S6_FrameChanged__pain
    cmp $3C
    beq S6_FrameChanged__rise
    lda $A8
    and #$00FF
    cmp $E4
    beq S6_FrameChanged__jump
    lda #$00FF
    bra S6_FrameChanged__store_role
S6_FrameChanged__idle:
    lda #0
    bra S6_FrameChanged__store_role
S6_FrameChanged__walk:
    lda #1
    bra S6_FrameChanged__store_role
S6_FrameChanged__attack:
    lda #2
    bra S6_FrameChanged__store_role
S6_FrameChanged__rise:
    lda #5
    bra S6_FrameChanged__store_role
S6_FrameChanged__jump:
    lda #7
    bra S6_FrameChanged__store_role
S6_FrameChanged__pain:
    lda #8
S6_FrameChanged__store_role:
    sta.l S6Host_Role,x
    lda.l S6Host_FrameEvents
    inc a
    sta.l S6Host_FrameEvents
    rtl

S6_WorldHealth:
    rep #$30
    .a16
    .i16
    jml S6_DisplayHealth

S6_WorldLost:
    rep #$30
    .a16
    .i16
    lda.l Screen_PosX
    ; The display camera need not land on the exact 4-pixel source lattice.
    ; Use each bound actor's compiler-selected inverse policy, just like
    ; bridge import; Normal's 5/4 projection is intentionally rounded.
    jsl S6Bridge_UnprojectPolicy
    bcs S6Host_EnvironmentBlocked
    sec
    sbc #1000
    sta $AA
    lda $14
    sec
    sbc $AA
    bmi S6Host_LostRemove
    lda $18
    eor #$8000
    cmp #$7E0C                ; source a < PIT_DEPTH*2 (-500)
    bcc S6Host_LostRemove
    rtl
S6Host_LostRemove:
    .a16
    .i16
    jml S6_KillUnlinked
S6Host_EnvironmentBlocked:
    ; Projection failure from S6_WorldLost is still fail-closed. Gravity no
    ; longer branches here because its former $C2 test read actor scratch.
    .a16
    .i16
    lda #10
    sta $FC
    rtl

S6_WorldGravity:
    rep #$30
    .a16
    .i16
    ; This pass has no source actor-local gravity state to apply. $C2 is
    ; scratch beyond CharacterEntity's 133-byte contract (e.g. DriftTick's
    ; signed-bound temporary), not a gravity/hole certificate; treating a
    ; stale nonzero value as fatal faulted ordinary Normal actors. Authored
    ; stage hazards are serviced by StageBoundsHost_Physics/Enter on the
    ; gameplay path before the resident-world tick.
    rtl

S6_WorldAttack:
    rep #$30
    .a16
    .i16
    ; BOR.C gates the entire target scan on this source frame's attack.
    ; An inactive frame resets attack_id once, even with no live targets.
    ; Do not repeatedly decode the identical inactive frame for each target.
    jsl S6_CheckPolicy
    bcs S6_WorldAttack__done
    jsl S5_ActivateAttack
    lda $0A
    bne S6_WorldAttack__active
    stz $DC
    stz $DE
    rtl
S6_WorldAttack__active:
    .a16
    .i16
    ; Scan stable source slot order, not just the selected AI target.
    stz $AC
S6_WorldAttack__slot:
    .a16
    .i16
    lda $AC
    asl a
    tax
    lda.l S6Host_SlotTable,x
    sta $34
    tax
    lda.l $7E00F6,x
    beq S6_WorldAttack__next
    jsl S6_TryHitOne
    lda $FC
    bne S6_WorldAttack__done
S6_WorldAttack__next:
    .a16
    .i16
    inc $AC
    lda $AC
    cmp #6
    bcc S6_WorldAttack__slot
S6_WorldAttack__done:
    .a16
    .i16
    rtl

S6_HitEffects:
    rep #$30
    .a16
    .i16
    ; This publication is NOT a complete flash/audio/combo/effects binding.
    ; Keep the full effect category un-certified until its consumers exist.
    lda.l S6Host_HitEvents
    inc a
    sta.l S6Host_HitEvents
    sep #$20
    .a8
    jsl S7_QueueHitSfxLong
    rep #$30
    .a16
    .i16
    rtl

; Private production-image hooks. No production include/default policy change.
; Command1 loads the selected real stage; its one retained authored queue record
; remains owned by normal Spawn_Play. Player positions are fixture preconditions.
; StageTimer_FieldCounter is the unconditional-NMI field clock. Unlike
; Nmi_FrameCounter it includes busy/skipped visual commits and is therefore
; the correct source-time input for an elapsed-field catch-up batch.
StageTimer_FieldCounter = $7E5914
S6Game_Command = $7E1770
S6Game_LastField = $7E1772
S6Game_TickCommit = $7E1774
S6Game_BirthCount = $7E177E ; fixture-owned, cleared by whole world-context reset
; The source host's direct page is the physical $7E1700 WRAM mirror. Keep
; catch-up scratch outside that world/scheduler page: $7A/$7C are live host
; scratch, so using $177A/$177C corrupts the batch across source ticks.
S6Game_BatchCount = $7E5922
S6Game_BatchParity = $7E5924

S6Game_Entity:
    php
    rep #$30
    .a16
    .i16
    phx
    tdc
    sec
    sbc #$0A00
    tax
    lda.l S6Bridge_Policy,x
    and #$00FF
    cmp #1
    beq S6Game_Entity__exact
    ; The production Normal bridge uses policy 2 for its compiler-approved
    ; rounded source/native coordinate projection. It still has one
    ; canonical actor world: dispatching those rows through the legacy
    ; per-field CharacterEntity_Play path would independently mutate AI,
    ; hits, grabs and animation between SA-1 snapshots.
    cmp #2
    beq S6Game_Entity__normal_gate
    plx
    plp
    rep #$31
    .a16
    .i16
    phd
    jsl G13_PlayerLifecycleIsOut
    jml S6Game_EntityResume
S6Game_Entity__exact:
    .a16
    .i16
    plx
    plp
    jml CharacterEntity_Play__no_context_exit
S6Game_Entity__normal_gate:
    ; Before the persistent owner epoch has actually been acquired (and
    ; during the bounded bootstrap windows that park it), policy-2 rows must
    ; retain the ordinary actor path. A policy byte by itself is not proof
    ; that SA-1 owns their canonical state.
    lda.l S7Resident_Owner
    cmp #2
    beq S6Game_Entity__normal
    plx
    plp
    rep #$31
    .a16
    .i16
    phd
    jsl G13_PlayerLifecycleIsOut
    jml S6Game_EntityResume
S6Game_Entity__normal:
    ; A player retired by the source worker still needs BOR's existing
    ; S-CPU fall animation/stock/respawn service. Only that absent player
    ; incarnation re-enters CharacterEntity_Play; live rows and retired
    ; opponents remain SA-1-only. The respawn seam rebinds one new row.
    lda.l S6Bridge_Exists,x
    and #$00FF
    bne S6Game_Entity__owned_return
    tdc
    cmp #$0A00
    beq S6Game_Entity__player_lifecycle
    cmp #$0A00+CHAR_ZP_LEN
    bne S6Game_Entity__owned_return
    sep #$20
    .a8
    lda.l G13_TwoPlayerEnabled
    beq S6Game_Entity__owned_return
    rep #$30
    .a16
    .i16
S6Game_Entity__player_lifecycle:
    plx
    plp
    rep #$31
    .a16
    .i16
    phd
    jsl G13_PlayerLifecycleIsOut
    jml S6Game_EntityResume
S6Game_Entity__owned_return:
    ; Persistent Normal rows bypass CharacterEntity_Play, but BOR's existing
    ; player jump is an S-CPU 60-Hz substate (Jump_PlayerTick owns its Z
    ; integration and the source bridge intentionally leaves those fields
    ; native). Keep that narrow action seam live at the same per-field actor
    ; boundary; the source worker still owns ground movement/combat and sees
    ; the jump discriminator at the next committed input boundary.
    tdc
    cmp #$0A00
    beq S6Game_Entity__owned_player1
    cmp #$0A00+CHAR_ZP_LEN
    beq S6Game_Entity__owned_player2
    bra S6Game_Entity__owned_return_path
S6Game_Entity__owned_player1:
    sep #$20
    .a8
    jsl Jump_PlayerInputGate
    rep #$30
    .a16
    .i16
    bra S6Game_Entity__owned_return_path
S6Game_Entity__owned_player2:
    lda.l G13_TwoPlayerEnabled
    and #$00FF
    beq S6Game_Entity__owned_return_path
    jsl G13_Player2_ContextEnter
    sep #$20
    .a8
    jsl Jump_PlayerInputGate
    rep #$30
    .a16
    .i16
    jsl G13_Player2_ContextExit
S6Game_Entity__owned_return_path:
    plx
    plp
    rep #$31
    .a16
    .i16
    ; CharacterEntity_Play is installed as a JML into bank $1E, while its
    ; caller is Core_Oop_Play's bank-0 indirect JSR. RTS would pop the
    ; caller's 16-bit address but leave PBR=$1E, fetching the return site
    ; from the worker bank. Rebuild that JSR frame as the equivalent RTL
    ; frame. Core_Oop_Play reloads OopObjIndex after dispatch, so X is safe
    ; as the temporary return-PC register here.
    pla
    tax
    sep #$20
    .a8
    lda #0
    pha
    rep #$30
    .a16
    .i16
    txa
    pha
    lda #0
    rtl

S6Game_Bind:
    php
    rep #$30
    .a16
    .i16
    lda.l S6Host_Mode
    cmp #2
    beq S6Game_Bind__exact
    plp
    php
    rep #$31
    .a16
    .i16
    phx
    jml S6Game_BindResume
S6Game_Bind__exact:
    .a16
    .i16
    lda #S6Game_Profile
    beq S6Game_Bind__placed
    jsl S6Host_BindExisting
    lda.l S6Host_Error
    bne S6Game_Bind__done
S6Game_Bind__placed:
    .a16
    .i16
    lda #S6Game_ControlPlacement
    beq S6Game_Bind__ready
    ; Same bounded Kula control geometry under both explicit policies.
    ; These are post-birth fixture preconditions, NOT source movement proof.
    lda #124
    sta CHAR_POS_X
    lda #100
    sta.l $7E0A00+CHAR_POS_X
    sep #$20
    .a8
    lda #100
    sta CHAR_HP
    rep #$30
    .a16
    .i16
S6Game_Bind__ready:
    .a16
    .i16
    lda.l S6Game_BirthCount
    inc a
    sta.l S6Game_BirthCount
    cmp #S6Game_ExpectedBirths
    bcc S6Game_Bind__done
    lda #3                   ; bound, await first complete world-pass boundary
    sta.l S6Host_Mode
    lda #S6Game_InitialAction
    sta.l S6Host_Action
    lda.l StageTimer_FieldCounter
    sta.l S6Game_LastField
S6Game_Bind__done:
    .a16
    .i16
    plp
    rtl

; Called at the existing post-OOP/pre-render seam. Preserve all renderer inputs.
S6Game_PlayRender:
    php
    rep #$30
    .a16
    .i16
    phx
    phy
    phb
    phd
    sep #$20
    .a8
    lda #0
    pha
    plb
    rep #$30
    .a16
    .i16
    lda #0
    tcd
    lda.l S6Game_Command
    cmp #1
    beq S6Game_PlayRender__load
    jmp S6Game_PlayRender__tick
S6Game_PlayRender__load:
    .a16
    .i16
    lda #0
    sta.l S6Game_Command
    sta.l S6Host_Mode
    ; Controlled teardown of the startup stage. Stage_Load normally assumes
    ; its preceding stage has cleared; do not carry its NPCs into this fixture.
    sep #$20
    .a8
    lda #VMSTAT_DONE          ; bounded stage fixture has no startup VM script
    sta.l VmState_Status
    ldx #CHAR_ZP_LEN*2
S6Game_PlayRender__clear_old:
    .a8
    .i16
    lda #0
    sta.l $7E0A00+CHAR_HP,x
    rep #$20
    .a16
    txa
    clc
    adc #CHAR_ZP_LEN
    tax
    sep #$20
    .a8
    cpx #CHAR_ZP_LEN*6
    bcc S6Game_PlayRender__clear_old
    rep #$30
    .a16
    .i16
    lda #S6Game_Stage
    sta.l Game_StageIndex
    sep #$20
    .a8
    sta.l Bg_LoadScene_StageIndex
    rep #$30
    .a16
    .i16
    jsl Stage_LoadAndRespawn_Long
    sep #$20
    .a8
    lda #0
    ldx #5
S6Game_PlayRender__clear_grace:
    .a8
    .i16
    sta.l Actor_InvulnFrames,x
    dex
    bpl S6Game_PlayRender__clear_grace
    rep #$30
    .a16
    .i16
    lda #$1700
    tcd
    lda #0
    ldx #$FE
S6Game_PlayRender__clear:
    .a16
    .i16
    sta $00,x
    dex
    dex
    bpl S6Game_PlayRender__clear
    lda #$02D2
    sta $00
    lda #$4996
    sta $02
    lda #S6Host_SlotTable&$FFFF
    sta $30
    lda #S6Host_SlotTable>>16
    sta $32
    lda #6
    sta $34
    rep #$30
    .a16
    .i16
    lda #1
    sta $40
    ; S6Clock_ClockAdvance uses the dedicated D=$1780 context.  Initialize
    ; its 32-bit NTSC rate there, not in the actor context that is about to be
    ; selected below.  21,477,270 = $0147B796 master clocks/second.
    lda #$1780
    tcd
    lda #$B796
    sta $08
    lda #$0147
    sta $0A
    lda #$0A00
    tcd
    lda #16
    sta CHAR_POS_X
    lda #176
    sta CHAR_POS_Y
    sep #$20
    .a8
    lda #S6Game_PlayerFacing
    sta CHAR_FACING_LEFT
    rep #$30
    .a16
    .i16
    lda #S6Game_Profile
    beq S6Game_PlayRender__p2
    jsl S6Host_BindExisting
S6Game_PlayRender__p2:
    .a16
    .i16
    lda.l G13_TwoPlayerEnabled
    and #255
    beq S6Game_PlayRender__await_spawn
    lda #$0A00+CHAR_ZP_LEN
    tcd
    lda #S6Game_Player2X
    sta CHAR_POS_X
    lda #176
    sta CHAR_POS_Y
    lda #S6Game_Profile
    beq S6Game_PlayRender__await_spawn
    jsl S6Host_BindExisting
S6Game_PlayRender__await_spawn:
    .a16
    .i16
    lda #S6Game_ExpectedBirths
    cmp #1
    beq S6Game_PlayRender__catalog_ready
    ; CPU-only concurrency fixture: choose the preloaded catalog identity
    ; for inactive slots. HP/existence and birth remain Spawn_Play-owned.
    ; This is NOT a media/residency or original stage-order certificate.
    ldx #CHAR_ZP_LEN*2
    sep #$20
    .a8
    lda #S6Game_EnemyRoster
S6Game_PlayRender__catalog_slot:
    .a8
    .i16
    sta.l $7E0A00+CHAR_ROSTER_INDEX,x
    rep #$20
    .a16
    txa
    clc
    adc #CHAR_ZP_LEN
    tax
    sep #$20
    .a8
    lda #S6Game_EnemyRoster
    cpx #CHAR_ZP_LEN*6
    bcc S6Game_PlayRender__catalog_slot
    rep #$20
    .a16
S6Game_PlayRender__catalog_ready:
    ; The bounded actor fixture uses the source-valid zero-base environment.
    ; Clear per-slot base fractions left by the real stage loader so the
    ; bridge does not reject those slots as unsupported fractional altitude.
    rep #$30
    .a16
    .i16
    ldx #0
S6Game_PlayRender__clear_base_fraction:
    lda #0
    sta.l StageEnv_BaseFraction,x
    txa
    clc
    adc #CHAR_ZP_LEN
    tax
    cpx #CHAR_ZP_LEN*6
    bcc S6Game_PlayRender__clear_base_fraction
    .a16
    .i16
    lda #2
    sta.l S6Host_Mode
    jmp S6Game_PlayRender__return
S6Game_PlayRender__tick:
    .a16
    .i16
    lda.l S6Game_Command
    cmp #2
    bne S6Game_PlayRender__no_remove
    lda #0
    sta.l S6Game_Command
    lda.l $7E1776
    jsl S6Host_RemoveHandle
S6Game_PlayRender__no_remove:
    .a16
    .i16
    lda.l S6Host_Mode
    cmp #3
    bne S6Game_PlayRender__running
    lda.l StageTimer_FieldCounter
    sta.l S6Game_LastField
    lda #S6Game_Profile
    bne S6Game_PlayRender__exact_start
    lda #5                   ; compatibility control: no source actor ticking
    bra S6Game_PlayRender__start_mode
S6Game_PlayRender__exact_start:
    .a16
    .i16
    lda #1
S6Game_PlayRender__start_mode:
    .a16
    .i16
    sta.l S6Host_Mode
    jmp S6Game_PlayRender__return
S6Game_PlayRender__running:
    .a16
    .i16
    cmp #1
    beq S6Game_PlayRender__check_error
    jmp S6Game_PlayRender__return
S6Game_PlayRender__check_error:
    .a16
    .i16
    lda.l S6Host_Error
    beq S6Game_PlayRender__measure
    jmp S6Game_PlayRender__return
S6Game_PlayRender__measure:
    ; Render-loop passes may repeat within one physical field. Advance source
    ; time for every physical field, including busy/skipped NMI commits. The
    ; StageTimer counter is NMI-owned and advances before that skip decision;
    ; Nmi_FrameCounter intentionally excludes skipped presentation commits.
    .a16
    .i16
    lda.l StageTimer_FieldCounter
    sec
    sbc.l S6Game_LastField
    ; The physical field counter is a 16-bit word. Preserve the full interval:
    ; source-sized MSU sheet/piece reads can keep the pre-render path busy for
    ; more than 30 physical fields, but every field still has to reach the
    ; source clock in order.
    bne S6Game_PlayRender__has_elapsed
    jmp S6Game_PlayRender__return
S6Game_PlayRender__has_elapsed:
    .a16
    .i16
    ; A gap of half the 16-bit physical-field domain is ambiguous.
    cmp #$8000
    bcc S6Game_PlayRender__delta_valid
    lda #16                  ; fail closed only for genuinely ambiguous time
    sta.l S6Host_Error
    jmp S6Game_PlayRender__return
S6Game_PlayRender__delta_valid:
    ; Process at most 120 physical fields per render pass. Keep the parity of
    ; the oldest pending field from the FULL elapsed gap before bounding this
    ; batch; any remaining backlog is consumed by the following pass.
    pha
    dec a
    and #1
    xba
    lsr a
    sta.l S6Game_BatchParity
    sep #$20
    .a8
    lda $213F
    and #$80
    eor.l S6Game_BatchParity
    sta.l S6Game_BatchParity
    rep #$30
    .a16
    .i16
    pla
    ; One bounded production visual admission is a 1-KiB sheet chunk plus at
    ; most 65 sixteen-byte piece rows. A slow display pass may accrue more
    ; than 120 fields; chunk rather than discard or fault that source debt.
    cmp #120
    bcc S6Game_PlayRender__field
    lda #120
S6Game_PlayRender__field:
    .a16
    .i16
    sta.l S6Game_BatchCount
    lda #S7Resident_Enabled
    sta.l S7Resident_Owner
    ; Advance only by this chunk. If more elapsed fields remain, the next
    ; render pass starts at this exact source-time boundary.
    lda.l S6Game_LastField
    clc
    adc.l S6Game_BatchCount
    sta.l S6Game_LastField
S6Game_PlayRender__elapsed_field:
    .a16
    .i16
    lda #$1780
    tcd
    lda #$99C0
    sta $00
    lda #$0442
    sta $02
    sep #$20
    .a8
    lda.l S6Game_BatchParity
    and #$80
    beq S6Game_PlayRender__clock
    rep #$20
    .a16
    lda $00
    sec
    sbc #800
    sta $00
    lda $02
    sbc #0
    sta $02
S6Game_PlayRender__clock:
    rep #$30
    .a16
    .i16
    jsl S6Clock_ClockAdvance
S6Game_PlayRender__clock_returned:
    lda.l S6Game_BatchParity
    eor #$80
    sta.l S6Game_BatchParity
    lda.l S6Game_BatchCount
    dec a
    sta.l S6Game_BatchCount
    bne S6Game_PlayRender__elapsed_field
S6Game_PlayRender__flush:
    jsl S7Resident_Flush
S6Game_PlayRender__post_flush:
S6Game_PlayRender__return:
    rep #$30
    .a16
    .i16
    jsr S6Game_ShouldPresent
    bcc S6Game_PlayRender__skip_present
    pld
    plb
    ply
    plx
    plp
    jml Character_RenderPass
S6Game_PlayRender__skip_present:
    pld
    plb
    ply
    plx
    plp
    rtl

S6Clock_HostSourceTick:
    .a16
    .i16
    lda.l S6Host_Mode
    cmp #1
    beq S6Clock_HostSourceTick__running
    brl S6Clock_HostSourceTick__done
S6Clock_HostSourceTick__running:
    lda $0C
    sta.l $7E173C
    lda $0E
    sta.l $7E173E
    jsl S6Host_Tick
    lda $0C
    sta.l S6Game_TickCommit
    ; Observer-only bounded stop, after the complete shared world pass.
    ; The source transition executes first; no actor state is manufactured.
    lda.l S6Host_HitEvents
    beq S6Clock_HostSourceTick__done
    lda.l $7E19E6+S6Game_StopSlot*256
    cmp #S6Game_StopDriver
    bne S6Clock_HostSourceTick__done
    lda #1
    sta.l S6Host_Mode
S6Clock_HostSourceTick__done:
    .a16
    .i16
    rtl

; Deterministic existence consumer, same real row as scheduler bridge.
S6Game_Alive:
    .a8
    .i16
    pha
    rep #$20
    .a16
    phx
    tdc
    sec
    sbc #$0A00
    tax
    sep #$20
    .a8
    lda.l S6Bridge_Policy,x
    cmp #1
    beq S6Game_Alive__exact
    plx
    pla
    cmp #CHAR_INPUT_DRIVEN_NONCOMBAT
    beq S6Game_Alive__legacy_source
    jml S6Game_AliveResume
S6Game_Alive__legacy_source:
    .a8
    .i16
    jml ActorBehavior_EntityAlive__source
S6Game_Alive__exact:
    .a8
    .i16
    plx
    pla
    rep #$20
    .a16
    phx
    tdc
    sec
    sbc #$0A00
    tax
    sep #$20
    .a8
    lda.l S6Bridge_Exists,x
    plx
    ora #0
    rtl

; X already selects an actual production row; original callers saved X.
S6Game_SlotBusy:
    .a8
    .i16
    lda.l S6Bridge_Policy,x
    cmp #1
    beq S6Game_SlotBusy__exact
    lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
    jml S6Game_SlotBusyResume
S6Game_SlotBusy__exact:
    .a8
    .i16
    lda.l S6Bridge_Exists,x
    plx
    ora #0
    rtl

S6Game_CountSlot1:
    .a8
    .i16
    phx
    ldx #CHAR_ZP_LEN
    bra S6Game_CountSlot
S6Game_CountSlot2:
    .a8
    .i16
    phx
    ldx #CHAR_ZP_LEN*2
    bra S6Game_CountSlot
S6Game_CountSlot3:
    .a8
    .i16
    phx
    ldx #CHAR_ZP_LEN*3
    bra S6Game_CountSlot
S6Game_CountSlot4:
    .a8
    .i16
    phx
    ldx #CHAR_ZP_LEN*4
    bra S6Game_CountSlot
S6Game_CountSlot5:
    .a8
    .i16
    phx
    ldx #CHAR_ZP_LEN*5
S6Game_CountSlot:
    .a8
    .i16
    lda.l S6Bridge_Policy,x
    cmp #1
    beq S6Game_SlotBusy__exact
    lda.l $7E0A00+CHAR_HP,x
    plx
    ora #0
    rtl

S6Game_HudHealth:
    .a8
    .i16
    lda.l S6Bridge_Policy
    cmp #1
    bne S6Game_HudHealth__compat
    lda.l S6Bridge_Exists
    beq S6Game_HudHealth__done
    lda.l S6Bridge_DisplayedHealth
S6Game_HudHealth__done:
    .a8
    .i16
    rtl
S6Game_HudHealth__compat:
    .a8
    .i16
    lda.l PlayerEntity_Hp
    rtl

; Exact actors own their lifecycle in the shared source pass. Running the
; compatibility death service as well would stop the entire world when one
; player is OUT, or revive an exact absent slot before retargeting.
S6Game_DeathService:
    php
    rep #$30
    .a16
    .i16
    lda.l S6Bridge_Policy
    and #$00FF
    cmp #1
    bne S6Game_DeathService__compat
    lda.l S6Bridge_Policy+CHAR_ZP_LEN
    and #$00FF
    cmp #1
    bne S6Game_DeathService__compat
    plp
    clc
    rtl
S6Game_DeathService__compat:
    .a16
    .i16
    plp
    jml G13_HandleP2Death

; The hooked CharacterEntity_Play is entered from Core_Oop_Play's bank-0
; indirect JSR but its original body resides in bank $1E. Native lifecycle
; returns (notably player fall/respawn after a worker unlink) therefore need
; the same explicit 24-bit return-frame conversion as the worker-owned path.
S6Game_Entity__native_return:
    pla
    tax
    sep #$20
    .a8
    lda #0
    pha
    rep #$30
    .a16
    .i16
    txa
    pha
    lda #0
    rtl

S6Game_ShouldPresent:
    rep #$30
.a16
.i16
    lda #S6Game_PresentationDivisor
    cmp #1
    beq S6Game_ShouldPresent__yes
    lda.l StageTimer_FieldCounter
    sec
    sbc.l S6Normal_LastPresentationField
    cmp #S6Game_PresentationDivisor
    bcc S6Game_ShouldPresent__no
    lda.l StageTimer_FieldCounter
    sta.l S6Normal_LastPresentationField
S6Game_ShouldPresent__yes:
    sec
    rts
S6Game_ShouldPresent__no:
    clc
    rts

; Opt-in Normal-campaign adapter for the accepted persistent SA-1 owner.
; Combat actors bind to the source-world contexts; props, pickups, steamers
; and the special Biker driver remain on their existing typed S-CPU services.
; Spawn/respawn is a true dependency boundary: drain queued ticks, bind one
; production slot, then publish only that context and its 133-byte metadata row.
S6Normal_LastStage = $7E1762
; Physical-field publication stamp, after catch-up scratch $5922..$5925.
S6Normal_LastPresentationField = $7E5926
; Spawn_Play can reassign an allocated actor row without invoking the
; behavior binder again. Track the roster represented by each live source
; context so the render-boundary ownership sweep can safely rebind it.
; Reserve $17A0..$17A9 between clock $1780..$179F and zero-velocity
; blocks $17B0..$17DF. Bridge scratch begins at $17E0.
S6Normal_BoundRoster = $7E17A0
S6Normal_BindLiveActors__slot_index = $7E17A6
S6Normal_BindLiveActors__worker_context = $7E17A8
; Six-byte shared target-type directory for the persistent worker's ordered
; world-attack pass. Only native breakable props are marked; HP,
; invulnerability, rewards and lifecycle remain S-CPU-owned typed state.
S6Normal_NativePropMask = $412D00
S6Normal_NativePropRecordOffset = $7E1766
S6Normal_NativePropAttackX = $7E1768
S6Normal_NativePropTargetYSlot = $7E176A

S6Normal_BeginResolve:
    jsl S6Normal_Init
    jsl Game_Campaign_ResolveNext
    rtl

S6Normal_Init:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    phb
    phd
    sep #$20
    .a8
    lda #0
    pha
    plb
    rep #$30
    .a16
    .i16
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq S6Normal_Init__enabled
    lda #0
    sta.l S6Host_Mode
    sta.l $7E175C
    sta.l $7E175E
    sta.l $7E175A
    jmp S6Normal_Init__return
S6Normal_Init__enabled:
    lda #0
    sta.l $7E175C
    sta.l $7E175E
    sta.l $7E175A
    sta.l S6Host_Error
    sta.l S6Game_Command
    sta.l S6Game_TickCommit
    sta.l S6Game_TickCommit+2
    sta.l S6Normal_LastPresentationField
    sta.l $7E4BB4 ; SourceVisual_ServiceField
    sta.l $7E4BB6 ; SourceVisual_LatchedInput
    sta.l $7E4BB8 ; SourceVisual_ServiceCount
    sta.l $7E4BBA ; SourceVisual_FieldPress1
    sta.l $7E4BC0 ; SourceVisual_FieldPress2
    sta.l $7E4BC6 ; SourceVisual_LatchedInput2
    sta.l $7E4BCC ; SourceVisual_InputSampleField
    jsl SourceVisual_CompletedInit
    ; Stage/bootstrap WRAM is not a zeroed worker-world image. Initialize the
    ; four source relationship pointers before the first persistent tick;
    ; stale values here are consumed by S6_SelectTarget as actor DPs.
    sta.l $7E1744
    sta.l $7E1746
    sta.l $7E174E
    sta.l $7E1750
    sta.l $411744
    sta.l $411746
    sta.l $41174E
    sta.l $411750
    ldx #0
S6Normal_Init__bound_roster_clear:
    sep #$20
    .a8
    lda #0
    sta.l S6Normal_BoundRoster,x
    rep #$30
    .a16
    .i16
    inx
    cpx #6
    bcc S6Normal_Init__bound_roster_clear
    ldx #0
S6Normal_Init__native_prop_clear:
    sta.l S6Normal_NativePropMask,x
    inx
    cpx #6
    bcc S6Normal_Init__native_prop_clear
    lda #$FFFF
    sta.l S6Normal_LastStage
    lda.l StageTimer_FieldCounter
    sta.l S6Game_LastField
    ; Clear the six bridge rows only. Spawn_Play remains the sole owner of
    ; actor allocation, authored instance HP, aliases and slot reuse.
    ldx #0
    lda #0
S6Normal_Init__bridge:
    sta.l S6Bridge_Policy,x
    sta.l S6Bridge_Exists,x
    sta.l S6Bridge_DisplayedHealth,x
    sta.l S6Bridge_Context,x
    sta.l S6Bridge_TargetHandle,x
    txa
    clc
    adc #CHAR_ZP_LEN
    tax
    cpx #CHAR_ZP_LEN*6
    bcs S6Normal_Init__bridge_done
    lda #0
    bra S6Normal_Init__bridge
S6Normal_Init__bridge_done:
    ; The persistent worker's immutable slot table spans all six reserved
    ; source-context pages. Production OOP slots are not zero-filled, while
    ; world preflight validates E0 policy on every table pointer before it
    ; examines F6 existence. Initialize only these reserved source-world
    ; pages as valid empty contexts; Spawn_Play still owns every production
    ; allocation and S6Host_BindExisting fills each admitted actor later.
    ldx #0
S6Normal_Init__context_clear:
    lda #0
    sta.l $7E1900,x
    inx
    inx
    cpx #$0600
    bcc S6Normal_Init__context_clear
    ldx #0
S6Normal_Init__context_policy:
    lda #1
    sta.l $7E19E0,x
    txa
    clc
    adc #$0100
    tax
    cpx #$0600
    bcc S6Normal_Init__context_policy
    ; Fixed six production-slot table, same page-aligned resident ABI as the
    ; measured worker. No synthetic stage or duplicate actor list is created.
    lda #$02D2
    sta.l S6Host_World
    lda #$4996
    sta.l S6Host_World+2
    lda #S6Host_SlotTable&$FFFF
    sta.l S6Host_World+48
    lda #S6Host_SlotTable>>16
    sta.l S6Host_World+50
    lda #6
    sta.l S6Host_World+52
    lda #1
    sta.l S6Host_World+64
    ; Reset the rational 200-Hz source clock at a new Normal run boundary.
    lda #$1780
    tcd
    ldx #0
    lda #0
S6Normal_Init__clock_clear:
    sta $00,x
    inx
    inx
    cpx #32
    bcc S6Normal_Init__clock_clear
    lda #$B796
    sta $08
    lda #$0147
    sta $0A
    lda #$1700
    tcd
    lda #2
    sta.l S6Host_Mode
S6Normal_Init__return:
    pld
    plb
    ply
    plx
    pla
    plp
    rtl

; StageEnv_ResetActors runs at the authored physical-stage boundary. Flush all
; ordered events while their old bridge identities still exist, park the
; persistent owner, then retire the six fixed source contexts before the
; production rows are cleared/reused. The world/RNG epoch remains resident;
; only actors and their stage-local relationship/admission rows reset.
S6Normal_ResetStageWorld:
    php
    rep #$30
    .a16
    .i16
    phx
    phy
    phb
    phd
    sep #$20
    .a8
    lda #0
    pha
    plb
    rep #$30
    .a16
    .i16
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq S6Normal_ResetStageWorld__campaign
    jml S6Normal_ResetStageWorld__return
S6Normal_ResetStageWorld__campaign:
    lda.l S6Host_Mode
    cmp #1
    beq S6Normal_ResetStageWorld__mode
    cmp #3
    beq S6Normal_ResetStageWorld__mode
    jml S6Normal_ResetStageWorld__return
S6Normal_ResetStageWorld__mode:
    lda.l $7E175E
    cmp #2
    beq S6Normal_ResetStageWorld__owned
    jml S6Normal_ResetStageWorld__return
S6Normal_ResetStageWorld__owned:
    ; Relay_Flush drains every event through the old S-CPU mapping before the
    ; following mutation fence makes the bulk stage reset atomic to SA-1.
    jsl S7Resident_Flush
    jsl S6Normal_MutationFenceBegin
    ; BOR.C playlevel kills every old level entity before loading the next.
    ; Typed native props are outside the six source contexts. In particular,
    ; a hidden collected Time can still have HP while its suicide is pending;
    ; StartLevel clears that countdown, so leaving its native row occupied
    ; would strand it permanently in the next level.
    jsl S6Normal_RetireStageNpcs
    ldx #0
    lda #0
S6Normal_ResetStageWorld__native_prop_clear:
    sta.l S6Normal_NativePropMask,x
    inx
    cpx #6
    bcc S6Normal_ResetStageWorld__native_prop_clear
    ldx #0
S6Normal_ResetStageWorld__bound_roster_clear:
    sep #$20
    .a8
    lda #0
    sta.l S6Normal_BoundRoster,x
    rep #$30
    .a16
    .i16
    inx
    cpx #6
    bcc S6Normal_ResetStageWorld__bound_roster_clear
    lda #0
    sta.l $7E1744
    sta.l $7E1746
    sta.l $7E174E
    sta.l $7E1750
    sta.l $411744
    sta.l $411746
    sta.l $41174E
    sta.l $411750
    lda #0
    sta.l $7E1752
    lda #$1900
    sta.l $7E1754
S6Normal_ResetStageWorld__slot:
    ; Source lifecycle references are stage-local. Clearing F6 prevents a
    ; removed stage actor from generating a later unresolvable unlink event.
    lda.l $7E1754
    tcd
    stz $44
    stz $46
    stz $4E
    stz $50
    stz $F6
    lda.l $7E1754
    sec
    sbc #$1900
    tax
    ldy #0
S6Normal_ResetStageWorld__context:
    lda.l $7E1900,x
    sta.l $411900,x
    inx
    inx
    iny
    iny
    cpy #$0100
    bcc S6Normal_ResetStageWorld__context
    ; Worker metadata is six packed 133-byte sidecar rows, not six 36-byte
    ; actor-DP strides. Clear the complete shared mirror before the S-CPU
    ; StageEnv_ResetActors loop retires the corresponding host rows.
    ldx #0
    ldy #0
    lda #0
S6Normal_ResetStageWorld__metadata:
    sta.l $412100,x
    inx
    inx
    iny
    iny
    cpy #StageEnv_ActorRowsBytes
    bcc S6Normal_ResetStageWorld__metadata
    rep #$30
    .a16
    .i16
    lda.l $7E1752
    clc
    adc #CHAR_ZP_LEN
    sta.l $7E1752
    lda.l $7E1754
    clc
    adc #$0100
    sta.l $7E1754
    cmp #$1F00
    bcc S6Normal_ResetStageWorld__slot
    jsl S6Normal_MutationFenceEnd
S6Normal_ResetStageWorld__return:
    rep #$30
    .a16
    .i16
    pld
    plb
    ply
    plx
    plp
    rtl

; Retire old stage NPC state while the resident worker is parked. The fixed
; OOP slot handles remain allocated for Spawn_Play's existing reuse ABI.
; Player stock/health and the reserved co-op player row are preserved.
S6Normal_RetireStageNpcs:
    php
    rep #$30
    .a16
    .i16
    phx
    ldx #CHAR_ZP_LEN
S6Normal_RetireStageNpcs__row:
    cpx #CHAR_ZP_LEN
    bne S6Normal_RetireStageNpcs__clear
    lda.l G13_TwoPlayerEnabled
    and #$00FF
    bne S6Normal_RetireStageNpcs__next
S6Normal_RetireStageNpcs__clear:
    sep #$20
    .a8
    lda #0
    sta.l $7E0A00+CHAR_HP,x
    sta.l $7E0A00+CHAR_INPUT_DRIVEN,x
    sta.l $7E0A00+CHAR_PICKUP_TYPE,x
    sta.l $7E0A00+CHAR_SELECTED,x
    sta.l $7E0A00+CHAR_HIT_APPLIED,x
    sta.l $7E0A00+CHAR_FALL_STATE_TIMER,x
    sta.l $7E0A00+CHAR_GRAB_TIMER,x
    lda #$FF
    sta.l $7E0A00+CHAR_GRAB_TARGET,x
    sta.l $7E0A00+CHAR_GRABBED_BY,x
    rep #$30
    .a16
    .i16
    lda #0
    sta.l $7E0A00+CHAR_THROW_ZPOS,x
    sta.l $7E0A00+CHAR_THROW_ZVEL,x
S6Normal_RetireStageNpcs__next:
    rep #$30
    .a16
    .i16
    txa
    clc
    adc #CHAR_ZP_LEN
    tax
    cpx #CHAR_ZP_LEN*6
    bcc S6Normal_RetireStageNpcs__row
    sep #$20
    .a8
    lda #0
    sta.l Entity1_ItemRosterIdx
    sta.l Entity2_ItemRosterIdx
    sta.l Entity3_ItemRosterIdx
    sta.l Entity4_ItemRosterIdx
    sta.l Entity5_ItemRosterIdx
    rep #$30
    .a16
    .i16
    plx
    plp
    rtl

; Called at the real post-OOP/pre-render seam. The fixture's elapsed-time
; accumulator is reused unchanged; its synthetic command remains zero.
S6Normal_RenderHook:
    rep #$30
    .a16
    .i16
    lda.l S6Host_Mode
    cmp #2
    bne S6Normal_RenderHook__bind_if_ready
    lda #3
    sta.l S6Host_Mode
S6Normal_RenderHook__bind_if_ready:
    lda.l S6Host_Mode
    cmp #1
    beq S6Normal_RenderHook__bind_live
    cmp #3
    bne S6Normal_RenderHook__ready
S6Normal_RenderHook__bind_live:
    jsl S6Normal_RebaseStageClock
    ; Player/source entities can be created while Stage_Load is still
    ; materializing per-actor environment rows. Reconcile unowned live rows
    ; at every real post-load render seam before the next catch-up batch. Some
    ; stage-start actors are installed by the native stage bootstrap rather
    ; than ActorBehavior_Bind; the first sweep can precede their allocation.
    ; S6Normal_BindLiveActors skips existing bridge owners, so this does not
    ; reinitialize resident state or exchange whole contexts.
    jsl S6Normal_BindLiveActors
S6Normal_RenderHook__ready:
    ; A source-world player can be retired at zero HP before BOR's native
    ; stock/fall service runs. Once that service respawns a live player,
    ; restore only the missing persistent row at this existing dependency
    ; seam; never rebind an active row or an exhausted player.
    jsl S6Normal_RebindReturnedPlayers
    jml S6Game_PlayRender

; Campaign transitions can spend many physical fields in showcomplete and
; stage bootstrap while the persistent source world is intentionally parked.
; Rebase the source-field epoch exactly once when the authored physical stage
; changes, before the next catch-up pass. Do not interpret that non-gameplay
; time as a lost or oversized visual transaction.
S6Normal_RebaseStageClock:
    php
    rep #$30
    .a16
    .i16
    pha
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    bne S6Normal_RebaseStageClock__return
    lda.l Game_StageIndex
    cmp.l S6Normal_LastStage
    beq S6Normal_RebaseStageClock__return
    ; WorldMaxX is a native-coordinate stage input. Drain the previous
    ; epoch and park SA-1 while publishing its exact Normal-policy inverse;
    ; player movement then applies BOR's existing per-stage right bound.
    lda #0
    sta.l S6Host_Error
    jsl S7Resident_Flush
    jsl S6Normal_MutationFenceBegin
    lda.l WorldMaxX
    jsl S6Bridge_UnprojectRounded
    bcs S6Normal_RebaseStageClock__bad_limit
    sta.l S6Host_PlayerWorldMaxX
    bra S6Normal_RebaseStageClock__release
S6Normal_RebaseStageClock__bad_limit:
    lda #10
    sta.l S6Host_Error
S6Normal_RebaseStageClock__release:
    jsl S6Normal_MutationFenceEnd
    lda.l S6Host_Error
    bne S6Normal_RebaseStageClock__return
    lda.l Game_StageIndex
    sta.l S6Normal_LastStage
    lda.l StageTimer_FieldCounter
    sta.l S6Game_LastField
    lda #0
    sta.l S6Host_Error
S6Normal_RebaseStageClock__return:
    pla
    plp
    rtl

; ActorBehavior_Bind entry replacement. Only real players and ordinary
; source AI actors enter the SA-1 world. Every other typed entity retains its
; existing S-CPU-owned runtime and cannot poison the combat-world preflight.
S6Normal_Bind:
    php
    rep #$30
    .a16
    .i16
    phx
    phy
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq S6Normal_Bind__normal_campaign
    jmp S6Normal_Bind__fallback
S6Normal_Bind__normal_campaign:
    lda.l S6Host_Mode
    cmp #1
    beq S6Normal_Bind__active
    cmp #3
    beq S6Normal_Bind__active
    jmp S6Normal_Bind__fallback
S6Normal_Bind__active:
    sep #$20
    .a8
    ; Biker-K' uses the existing special S-CPU vehicle controller. The
    ; ordinary grounded source-world adapter must not steal that identity.
    lda CHAR_ROSTER_INDEX
    cmp #28
    bne S6Normal_Bind__ordinary_roster
    brl S6Normal_Bind__fallback
S6Normal_Bind__ordinary_roster:
    lda CHAR_INPUT_DRIVEN
    cmp #1
    beq S6Normal_Bind__source_input_ok
    cmp #2
    beq S6Normal_Bind__source_input_ok
    brl S6Normal_Bind__fallback
S6Normal_Bind__source_input_ok:
    ; Vertical source drops remain under the existing native throw/drop
    ; service until they land. Their nonzero CHAR_THROW_ZPOS is real source
    ; state, not a malformed grounded actor for S6Bridge_Import.
    lda CHAR_INPUT_DRIVEN
    cmp #CHAR_INPUT_DRIVEN_AI
    bne S6Normal_Bind__source_drop_ready
    rep #$30
    .a16
    .i16
    ; Spawn binding can run before StageBoundsHost_ResetSpawn marks a
    ; down-scroll drop. Never import an airborne AI incarnation as grounded;
    ; fallback retires any previous occupant of this physical slot, and the
    ; native drop path hands it back only once both height terms settle.
    lda CHAR_THROW_ZPOS
    ora CHAR_THROW_ZVEL
    beq S6Normal_Bind__source_height_grounded
    brl S6Normal_Bind__fallback
S6Normal_Bind__source_height_grounded:
    jsl StageBounds_Row
    lda.l StageDrop_State,x
    beq S6Normal_Bind__source_drop_ready
    brl S6Normal_Bind__fallback
S6Normal_Bind__source_drop_ready:
    rep #$30
    .a16
    .i16
    ; The production binder also sees items and typed scenery. Only combat
    ; models present in the compiler-owned worker table enter this world.
    lda CHAR_ROSTER_INDEX
    and #$00FF
    jsl S6Normal_IsRosterBound
    bcs S6Normal_Bind__combat
    brl S6Normal_Bind__fallback
S6Normal_Bind__combat:
    rep #$30
    .a16
    .i16
    lda.l $7E175C
    beq S6Normal_Bind__bind
    ; Worker owns the old incarnation until this acknowledged release point.
    ; The spawn hook runs after native allocation has initialized the reused
    ; production slot, so preserve only those scalar birth values that the
    ; old snapshot is allowed to mirror back before the new bind.
    lda CHAR_POS_X
    pha
    lda CHAR_POS_Y
    pha
    sep #$20
    .a8
    lda CHAR_HP
    pha
    lda CHAR_FACING_LEFT
    pha
    rep #$30
    .a16
    .i16
    jsl S7Resident_Flush
    sep #$20
    .a8
    pla
    sta CHAR_FACING_LEFT
    pla
    sta CHAR_HP
    rep #$30
    .a16
    .i16
    pla
    sta CHAR_POS_Y
    pla
    sta CHAR_POS_X
S6Normal_Bind__bind:
    ; Publish the new incarnation only while the worker is parked at a
    ; source-tick boundary. The native binder remains S-CPU local.
    jsl S6Normal_MutationFenceBegin
    jsl S6Normal_UpdateNativePropFenced
    ; The host imports this bit as the source-world alive state. Publish it
    ; before the import so the first worker snapshot owns a live incarnation;
    ; the returned-player path follows the same ordering below.
    sep #$20
    .a8
    lda #1
    sta.l S6Bridge_Exists,x
    rep #$30
    .a16
    .i16
    jsl S6Host_BindExisting
    lda.l S6Host_Error
    beq S6Normal_Bind__worker_ready
    lda.l $7E1754
    sec
    sbc #$1900
    xba
    and #$00FF
    tax
    sep #$20
    .a8
    lda #0
    sta.l S6Normal_BoundRoster,x
    rep #$30
    .a16
    .i16
    ; S6Host_BindExisting may have published a bridge row before a later
    ; import/role validation failed. Clear that exact 133-byte production
    ; row, not the small worker-context index held in X above.
    lda.l $7E1752
    tax
    lda #0
    sta.l S6Bridge_Policy,x
    sta.l S6Bridge_Exists,x
    sta.l S6Bridge_DisplayedHealth,x
    sta.l S6Bridge_Context,x
    sta.l S6Bridge_TargetHandle,x
    sta.l S6Host_Action,x
    sta.l S6Host_Frame,x
    sta.l S6Host_Role,x
    sep #$20
    .a8
    bra S6Normal_Bind__fenced_done
S6Normal_Bind__worker_ready:
    lda.l $7E1754
    sec
    sbc #$1900
    xba
    and #$00FF
    tax
    sep #$20
    .a8
    lda CHAR_ROSTER_INDEX
    sta.l S6Normal_BoundRoster,x
    rep #$30
    .a16
    .i16
    lda.l $7E175C
    beq S6Normal_Bind__fenced_done
    jsl S6Normal_SyncBoundContext
S6Normal_Bind__fenced_done:
    jsl S6Normal_MutationFenceEnd
S6Normal_Bind__handled:
    rep #$30
    .a16
    .i16
    ply
    plx
    plp
    rtl
S6Normal_Bind__fallback:
    jsl S6Normal_RetireReplacedBound
    ; The old incarnation is now retired and all earlier worker events have
    ; been drained; publish the new native target kind only at this boundary.
    jsl S6Normal_UpdateNativeProp
    ply
    plx
    plp
    php
    rep #$31
    .a16
    .i16
    phx
    jml S6Normal_BindResume

; A newly allocated typed S-CPU entity can reuse a slot whose previous
; incarnation was owned by the resident source world. Fence and retire only
; that old worker row before the new entity continues through its native
; binder. The flush may project the old actor into the just-created slot, so
; preserve the four fields S6Bridge_Export can modify.
S6Normal_RetireReplacedBound:
    php
    rep #$30
    .a16
    .i16
    phx
    phy
    phb
    phd
    sep #$20
    .a8
    lda #0
    pha
    plb
    rep #$30
    .a16
    .i16
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq S6Normal_RetireReplacedBound__campaign
    jmp S6Normal_RetireReplacedBound__return
S6Normal_RetireReplacedBound__campaign:
    lda.l S6Host_Mode
    cmp #1
    beq S6Normal_RetireReplacedBound__mode
    cmp #3
    beq S6Normal_RetireReplacedBound__mode
    jmp S6Normal_RetireReplacedBound__return
S6Normal_RetireReplacedBound__mode:
    tdc
    sec
    sbc #$0A00
    tax
    cpx #CHAR_ZP_LEN*6
    bcc S6Normal_RetireReplacedBound__row
    jmp S6Normal_RetireReplacedBound__return
S6Normal_RetireReplacedBound__row:
    txa
    sta.l $7E1752
    lda.l S6Bridge_Policy,x
    and #$00FF
    cmp #1
    beq S6Normal_RetireReplacedBound__owned
    cmp #2
    beq S6Normal_RetireReplacedBound__owned
    jmp S6Normal_RetireReplacedBound__return
S6Normal_RetireReplacedBound__owned:
    lda CHAR_POS_X
    pha
    lda CHAR_POS_Y
    pha
    sep #$20
    .a8
    lda CHAR_HP
    pha
    lda CHAR_FACING_LEFT
    pha
    rep #$30
    .a16
    .i16
    jsl S7Resident_Flush
    sep #$20
    .a8
    pla
    sta CHAR_FACING_LEFT
    pla
    sta CHAR_HP
    rep #$30
    .a16
    .i16
    pla
    sta CHAR_POS_Y
    pla
    sta CHAR_POS_X
    ; Resolve the paired persistent actor page from the production slot row.
    lda.l $7E1752
    tax
    ldy #$1900
S6Normal_RetireReplacedBound__context:
    cpx #0
    beq S6Normal_RetireReplacedBound__context_ready
    txa
    sec
    sbc #CHAR_ZP_LEN
    bcs S6Normal_RetireReplacedBound__context_advance
    brl S6Normal_RetireReplacedBound__fault
S6Normal_RetireReplacedBound__context_advance:
    tax
    tya
    clc
    adc #$0100
    tay
    cpy #$1F00
    bcc S6Normal_RetireReplacedBound__context
    brl S6Normal_RetireReplacedBound__fault
S6Normal_RetireReplacedBound__context_ready:
    tya
    sta.l $7E1754
    tya
    tcd
    ; A fallback/replacement ends this source actor incarnation. Park the
    ; worker before touching its canonical context; otherwise the old row can
    ; keep simulating after its S-CPU bridge mapping is cleared and later emit
    ; an unlink event that aliases a future occupant of the reused slot.
    jsl S6Normal_MutationFenceBegin
    ; The source worker may already have applied the ordered unlink and
    ; cleared F6 while the fixed context reservation and stale native bridge
    ; row remain. In that case only retire the projection; do not run
    ; KillUnlinked a second time against the detached context.
    lda $F6
    beq S6Normal_RetireReplacedBound__already_unlinked
    brl S6Normal_RetireReplacedBound__kill_live
S6Normal_RetireReplacedBound__already_unlinked:
    brl S6Normal_RetireReplacedBound__unlinked
S6Normal_RetireReplacedBound__kill_live:
    stz $FC
    jsl S6_KillUnlinked
    lda $FC
    beq S6Normal_RetireReplacedBound__unlinked
    jsl S6Normal_MutationFenceEnd
    bra S6Normal_RetireReplacedBound__fault
S6Normal_RetireReplacedBound__unlinked:
    ; KillUnlinked clears the source relationships; retire the actor itself
    ; before publishing the detached bridge row. This prevents future worker
    ; passes from running an actor whose native slot now belongs to fallback.
    stz $F6
    ; Publish the relationship fields, but not the stale S-CPU world clock.
    ; The host world stores context DPs in the $1900 window, while SA-1
    ; target traversal dereferences the corresponding $7900 BW-RAM aliases.
    ; Copying these words raw here leaves targeting pointed into the world
    ; header after any typed-slot retirement/rebind.
    lda.l $7E1744
    beq S6Normal_RetireReplacedBound__p0_ready
    clc
    adc #$6000
S6Normal_RetireReplacedBound__p0_ready:
    sta.l $411744
    lda.l $7E1746
    beq S6Normal_RetireReplacedBound__p1_ready
    clc
    adc #$6000
S6Normal_RetireReplacedBound__p1_ready:
    sta.l $411746
    lda.l $7E174E
    beq S6Normal_RetireReplacedBound__op0_ready
    clc
    adc #$6000
S6Normal_RetireReplacedBound__op0_ready:
    sta.l $41174E
    lda.l $7E1750
    beq S6Normal_RetireReplacedBound__op1_ready
    clc
    adc #$6000
S6Normal_RetireReplacedBound__op1_ready:
    sta.l $411750
    ; Remove this slot from the bridge admission table, retaining unrelated
    ; StageEnv fields (base, alias, and scene metadata) for the new entity.
    lda.l $7E1752
    tax
    lda #0
    sta.l S6Bridge_Policy,x
    sta.l S6Bridge_DisplayedHealth,x
    sta.l S6Bridge_Context,x
    sta.l S6Bridge_TargetHandle,x
    sta.l S6Host_Action,x
    sta.l S6Host_Frame,x
    sta.l S6Host_Role,x
    jsl S6Normal_SyncBoundContext
    lda.l $7E1754
    sec
    sbc #$1900
    xba
    and #$00FF
    tax
    sep #$20
    .a8
    lda #0
    sta.l S6Normal_BoundRoster,x
    rep #$30
    .a16
    .i16
    jsl S6Normal_MutationFenceEnd
    bra S6Normal_RetireReplacedBound__return
S6Normal_RetireReplacedBound__fault:
    rep #$30
    .a16
    .i16
    lda #10
    sta.l S6Host_Error
S6Normal_RetireReplacedBound__return:
    rep #$30
    .a16
    .i16
    pld
    plb
    ply
    plx
    plp
    rtl

; A16 roster id in A. Carry is set only for a model admitted to this Normal
; worker image. Bind and tick preflight share this predicate: typed
; noncombat entities retain their S-CPU services; a missing combat binding
; remains a fail-closed worker error.
S6Normal_IsRosterBound:
    php
    rep #$30
    .a16
    .i16
    phx
    sta.l $7E1758
    ldx #0
S6Normal_IsRosterBound__scan:
    cpx #S6Host_ModelCount*32
    bcs S6Normal_IsRosterBound__no
    lda.l S6Host_ModelTable,x
    cmp.l $7E1758
    beq S6Normal_IsRosterBound__yes
    txa
    clc
    adc #32
    tax
    bra S6Normal_IsRosterBound__scan
S6Normal_IsRosterBound__yes:
    plx
    plp
    sec
    rtl
S6Normal_IsRosterBound__no:
    plx
    plp
    clc
    rtl

; First-stage handoff. The native actor contexts are the same six physical
; slots already used by Spawn_Play; do not allocate or duplicate them. Only
; live player/AI rows are considered, and S6Normal_Bind's source roster table
; keeps items/scenery on their existing typed runtime.
S6Normal_BindLiveActors:
    php
    rep #$30
    .a16
    .i16
    phx
    phy
    phd
    ldx #0
    ldy #0
    lda #0
    sta.l S6Normal_BindLiveActors__slot_index
S6Normal_BindLiveActors__slot:
    txa
    clc
    adc #$0A00
    tcd
    jsl S6Normal_UpdateNativeProp
    sep #$20
    .a8
    lda.l S6Bridge_Policy,x
    bne S6Normal_BindLiveActors__policy_nonzero
    brl S6Normal_BindLiveActors__check_live
S6Normal_BindLiveActors__policy_nonzero:
    cmp #2
    beq S6Normal_BindLiveActors__policy_two
    brl S6Normal_BindLiveActors__next
S6Normal_BindLiveActors__policy_two:
    ; Bridge policy is only the S-CPU projection. Require the matching live
    ; BW-RAM sidecar before treating it as persistent ownership.
    rep #$30
    .a16
    .i16
    lda.l S6Bridge_Policy,x
    and #$00FF
    cmp #2
    beq S6Normal_BindLiveActors__bridge_policy_valid
    brl S6Normal_BindLiveActors__ownership_fault
S6Normal_BindLiveActors__bridge_policy_valid:
    phx
    tya
    tax
    lda.l $412140,x
    plx
    and #$FF00
    cmp #$0100
    beq S6Normal_BindLiveActors__worker_present
    brl S6Normal_BindLiveActors__needs_bind
S6Normal_BindLiveActors__worker_present:
    phx
    tya
    tax
    lda.l $412140,x
    plx
    cmp #$0102
    beq S6Normal_BindLiveActors__worker_status_valid
    brl S6Normal_BindLiveActors__ownership_fault
S6Normal_BindLiveActors__worker_status_valid:
    phx
    tya
    tax
    lda.l $412144,x
    sta.l S6Normal_BindLiveActors__worker_context
    plx
    lda.l S6Bridge_Context,x
    cmp.l S6Normal_BindLiveActors__worker_context
    beq S6Normal_BindLiveActors__worker_context_matches
    brl S6Normal_BindLiveActors__ownership_fault
S6Normal_BindLiveActors__worker_context_matches:
    ; Exists=2 is an ordered removal still crossing the event ring. Leave its
    ; incarnation alone until that event is projected. Exists=0 with a
    ; matching resident slot is different: the worker has already unlinked
    ; the actor and F6 is clear, while the fixed context reservation remains
    ; $0102. Retire only the stale bridge projection, never KillUnlinked twice.
    sep #$20
    .a8
    lda.l S6Bridge_Exists,x
    cmp #1
    beq S6Normal_BindLiveActors__worker_actor_live
    cmp #2
    beq S6Normal_BindLiveActors__worker_unlink_pending
    cmp #0
    beq S6Normal_BindLiveActors__worker_unlinked
    brl S6Normal_BindLiveActors__ownership_fault
S6Normal_BindLiveActors__worker_unlinked:
    rep #$30
    .a16
    .i16
    phx
    lda.l S6Normal_BindLiveActors__worker_context
    sec
    sbc #$1900
    tax
    sep #$20
    .a8
    lda.l $4119F6,x
    bne S6Normal_BindLiveActors__worker_context_live
    rep #$30
    .a16
    .i16
    plx
    ; Reuse the established fenced retirement path. It clears the stale bridge
    ; mapping and skips KillUnlinked when the worker context is already empty.
    ; Then the current native actor is admitted through the ordinary binder.
    lda #0
    sta.l S6Host_Error
    jsl S6Normal_RetireReplacedBound
    lda.l S6Host_Error
    beq S6Normal_BindLiveActors__worker_retired
    brl S6Normal_BindLiveActors__next
S6Normal_BindLiveActors__worker_retired:
    ; Retirement returns in A16. Re-enter through needs_bind so its SEP sets
    ; the native actor-check width before any byte-sized direct-page reads.
    brl S6Normal_BindLiveActors__needs_bind
S6Normal_BindLiveActors__worker_context_live:
    rep #$30
    .a16
    .i16
    plx
    brl S6Normal_BindLiveActors__ownership_fault
S6Normal_BindLiveActors__worker_unlink_pending:
    rep #$30
    .a16
    .i16
    brl S6Normal_BindLiveActors__next
S6Normal_BindLiveActors__worker_actor_live:
    rep #$30
    .a16
    .i16
    ; A live SA-1 context can still describe the previous roster if the
    ; spawn path reused this native slot without calling ActorBehavior_Bind.
    phx
    lda.l S6Normal_BindLiveActors__slot_index
    tax
    sep #$20
    .a8
    lda.l S6Normal_BoundRoster,x
    cmp CHAR_ROSTER_INDEX
    rep #$30
    .a16
    .i16
    beq S6Normal_BindLiveActors__roster_matches
    plx
    bra S6Normal_BindLiveActors__roster_changed
S6Normal_BindLiveActors__roster_matches:
    .a16
    .i16
    plx
    brl S6Normal_BindLiveActors__next
S6Normal_BindLiveActors__roster_changed:
    lda #0
    sta.l S6Host_Error
    jsl S6Normal_RetireReplacedBound
    lda.l S6Host_Error
    beq S6Normal_BindLiveActors__replacement_ready
    brl S6Normal_BindLiveActors__next
S6Normal_BindLiveActors__replacement_ready:
    jsl S6Normal_Bind
    brl S6Normal_BindLiveActors__next
S6Normal_BindLiveActors__ownership_fault:
    ; A different live source context must never be overwritten implicitly.
    rep #$30
    .a16
    .i16
    lda #10
    sta.l S6Host_Error
    brl S6Normal_BindLiveActors__next
S6Normal_BindLiveActors__needs_bind:
    sep #$20
    .a8
S6Normal_BindLiveActors__check_live:
    lda CHAR_HP
    beq S6Normal_BindLiveActors__next
    lda CHAR_INPUT_DRIVEN
    cmp #1
    beq S6Normal_BindLiveActors__bind
    cmp #2
    bne S6Normal_BindLiveActors__next
    ; The source vertical-drop adapter owns this actor until landing. Do not
    ; repeatedly attempt a grounded worker bind while its native throw
    ; state is still active; StageDrop_BeforeActor performs the handoff.
    rep #$30
    .a16
    .i16
    jsl StageBounds_Row
    lda.l StageDrop_State,x
    bne S6Normal_BindLiveActors__next
    lda CHAR_THROW_ZPOS
    ora CHAR_THROW_ZVEL
    bne S6Normal_BindLiveActors__next
    sep #$20
    .a8
S6Normal_BindLiveActors__bind:
    rep #$30
    .a16
    .i16
    ; A worker-side unlink can leave only the S-CPU bridge policy behind.
    ; Rebind catalogued combat at this real boundary; typed entities such as
    ; Biker-K' instead shed only the stale bridge, without killing an empty
    ; worker context.
    sep #$20
    .a8
    lda CHAR_ROSTER_INDEX
    cmp #28
    beq S6Normal_BindLiveActors__detach_stale
    rep #$30
    .a16
    .i16
    lda CHAR_ROSTER_INDEX
    and #$00FF
    jsl S6Normal_IsRosterBound
    bcs S6Normal_BindLiveActors__try_bind
    bra S6Normal_BindLiveActors__detach_stale
S6Normal_BindLiveActors__try_bind:
    jsl S6Normal_Bind
    bra S6Normal_BindLiveActors__next
S6Normal_BindLiveActors__detach_stale:
    rep #$30
    .a16
    .i16
    phx
    lda.l S6Normal_BindLiveActors__slot_index
    tax
    sep #$20
    .a8
    lda #0
    sta.l S6Normal_BoundRoster,x
    rep #$30
    .a16
    .i16
    plx
    lda #0
    sta.l S6Bridge_Policy,x
    sta.l S6Bridge_DisplayedHealth,x
    sta.l S6Bridge_Context,x
    sta.l S6Bridge_TargetHandle,x
    sta.l S6Host_Action,x
    sta.l S6Host_Frame,x
    sta.l S6Host_Role,x
S6Normal_BindLiveActors__next:
    rep #$30
    .a16
    .i16
    txa
    clc
    adc #CHAR_ZP_LEN
    tax
    tya
    clc
    adc #133
    tay
    lda.l S6Normal_BindLiveActors__slot_index
    inc a
    sta.l S6Normal_BindLiveActors__slot_index
    cpx #CHAR_ZP_LEN*6
    bcs S6Normal_BindLiveActors__done
    brl S6Normal_BindLiveActors__slot
S6Normal_BindLiveActors__done:
    pld
    ply
    plx
    plp
    rtl

; Called only by the source-drop landing seam patched into the opt-in Normal
; image. D still identifies the physical actor row. Bind a grounded,
; compiler-admitted enemy here and return carry set to consume this actor pass;
; unsupported/native actors keep the base drop service's ordinary path.
S6Normal_DropHandoff:
    php
    rep #$30
    .a16
    .i16
    phx
    phy
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    bne S6Normal_DropHandoff__no
    lda.l S6Host_Mode
    cmp #1
    beq S6Normal_DropHandoff__active
    cmp #3
    bne S6Normal_DropHandoff__no
S6Normal_DropHandoff__active:
    sep #$20
    .a8
    lda CHAR_HP
    beq S6Normal_DropHandoff__no
    lda CHAR_INPUT_DRIVEN
    cmp #CHAR_INPUT_DRIVEN_AI
    bne S6Normal_DropHandoff__no
    rep #$30
    .a16
    .i16
    lda CHAR_ROSTER_INDEX
    and #$00FF
    jsl S6Normal_IsRosterBound
    bcc S6Normal_DropHandoff__no
    lda CHAR_THROW_ZPOS
    ora CHAR_THROW_ZVEL
    bne S6Normal_DropHandoff__no
    lda.l S6Host_Error
    bne S6Normal_DropHandoff__owned
    jsl S6Normal_Bind
    lda.l S6Host_Error
    bne S6Normal_DropHandoff__owned
    jsl StageBounds_Row
    sep #$20
    .a8
    lda.l S6Bridge_Policy,x
    cmp #2
    bne S6Normal_DropHandoff__fault
    lda.l S6Bridge_Exists,x
    cmp #1
    beq S6Normal_DropHandoff__owned
S6Normal_DropHandoff__fault:
    rep #$30
    .a16
    .i16
    lda #10
    sta.l S6Host_Error
S6Normal_DropHandoff__owned:
    rep #$30
    .a16
    .i16
    ply
    plx
    plp
    sec
    rtl
S6Normal_DropHandoff__no:
    rep #$30
    .a16
    .i16
    ply
    plx
    plp
    clc
    rtl

; Publish whether this existing physical actor row is a native S-CPU-owned
; combat target (currently props and the special Biker driver). A changed
; marker is written at a worker poll fence so the six-row ordered attack scan
; cannot observe a torn slot-type transition on reuse.
S6Normal_UpdateNativeProp:
    php
    rep #$30
    .a16
    .i16
    phx
    tdc
    sec
    sbc #$0A00
    ldx #0
S6Normal_UpdateNativeProp__slot:
    cmp #0
    beq S6Normal_UpdateNativeProp__found
    sec
    sbc #CHAR_ZP_LEN
    bcc S6Normal_UpdateNativeProp__return
    inx
    cpx #6
    bcc S6Normal_UpdateNativeProp__slot
    bra S6Normal_UpdateNativeProp__return
S6Normal_UpdateNativeProp__found:
    sep #$20
    .a8
    lda CHAR_INPUT_DRIVEN
    cmp #CHAR_INPUT_DRIVEN_PROP
    beq S6Normal_UpdateNativeProp__want_prop
    cmp #CHAR_INPUT_DRIVEN_BIKER
    beq S6Normal_UpdateNativeProp__want_prop
    lda.l S6Normal_NativePropMask,x
    beq S6Normal_UpdateNativeProp__return
    bra S6Normal_UpdateNativeProp__fence
S6Normal_UpdateNativeProp__want_prop:
    lda.l S6Normal_NativePropMask,x
    bne S6Normal_UpdateNativeProp__return
S6Normal_UpdateNativeProp__fence:
    rep #$30
    .a16
    .i16
    jsl S7Resident_Flush
    jsl S6Normal_MutationFenceBegin
    jsl S6Normal_UpdateNativeProp__write
    jsl S6Normal_MutationFenceEnd
S6Normal_UpdateNativeProp__return:
    rep #$30
    .a16
    .i16
    plx
    plp
    rtl

; Caller already owns the poll fence (the combat actor bind path).
S6Normal_UpdateNativePropFenced:
    php
    rep #$30
    .a16
    .i16
    phx
    tdc
    sec
    sbc #$0A00
    ldx #0
S6Normal_UpdateNativePropFenced__slot:
    cmp #0
    beq S6Normal_UpdateNativePropFenced__found
    sec
    sbc #CHAR_ZP_LEN
    bcc S6Normal_UpdateNativePropFenced__return
    inx
    cpx #6
    bcc S6Normal_UpdateNativePropFenced__slot
    bra S6Normal_UpdateNativePropFenced__return
S6Normal_UpdateNativePropFenced__found:
    jsl S6Normal_UpdateNativeProp__write
S6Normal_UpdateNativePropFenced__return:
    rep #$30
    .a16
    .i16
    plx
    plp
    rtl

; X is the six-row physical entity slot. Both wrappers above call this tiny
; writer only while the worker is parked or before its epoch starts.
S6Normal_UpdateNativeProp__write:
    sep #$20
    .a8
    lda CHAR_INPUT_DRIVEN
    cmp #CHAR_INPUT_DRIVEN_PROP
    beq S6Normal_UpdateNativeProp__write_target
    cmp #CHAR_INPUT_DRIVEN_BIKER
    bne S6Normal_UpdateNativeProp__write_clear
S6Normal_UpdateNativeProp__write_target:
    lda #1
    sta.l S6Normal_NativePropMask,x
    rtl
S6Normal_UpdateNativeProp__write_clear:
    lda #0
    sta.l S6Normal_NativePropMask,x
    rtl

; Reconcile exactly the actor whose context was just rebound. Relay_Flush
; fences the worker; this is not a per-source-tick full-context transfer.
S6Normal_SyncBoundContext:
    php
    rep #$30
    .a16
    .i16
    phx
    phy
    lda.l $7E1754
    sec
    sbc #$1900
    tax
    ldy #0
S6Normal_SyncBoundContext__context:
    lda.l $7E1900,x
    sta.l $411900,x
    inx
    inx
    iny
    iny
    cpy #$0100
    bcc S6Normal_SyncBoundContext__context
    ; New births occur after Relay_Acquire. Convert only this context's
    ; S-CPU pointers to the SA-1 $6000 window before publishing it.
    lda.l $7E1754
    sec
    sbc #$1900
    tax
    lda.l $411934,x
    beq S6Normal_SyncBoundContext__relocate_36
    clc
    adc #$6000
    sta.l $411934,x
S6Normal_SyncBoundContext__relocate_36:
    .a16
    .i16
    lda.l $411936,x
    beq S6Normal_SyncBoundContext__relocate_B0
    clc
    adc #$6000
    sta.l $411936,x
S6Normal_SyncBoundContext__relocate_B0:
    .a16
    .i16
    lda.l $4119B0,x
    beq S6Normal_SyncBoundContext__metadata_start
    clc
    adc #$6000
    sta.l $4119B0,x
S6Normal_SyncBoundContext__metadata_start:
    .a16
    .i16
    lda.l $7E1752
    tax
    ldy #0
S6Normal_SyncBoundContext__metadata:
    lda.l StageEnv_Actors,x
    sta.l $412100,x
    inx
    inx
    iny
    iny
    cpy #132
    bcc S6Normal_SyncBoundContext__metadata
    ; X now points at this row's final metadata byte (row stride is 133).
    ; Keep the full-width index produced by the word-copy loop; rebuilding
    ; it in A8 would truncate slot offsets and inherit A's stale high byte.
    sep #$20
    .a8
    lda.l StageEnv_Actors,x
    sta.l $412100,x
    rep #$30
    .a16
    .i16
    ; S6_SelectTarget reads the canonical player DPs from world $44/$46.
    ; Keep the S-CPU fallback pointers in bank-0 WRAM and the persistent
    ; worker's corresponding $6000-window pointers in shared BW-RAM.
    lda.l $7E1752
    beq S6Normal_SyncBoundContext__player0
    cmp #CHAR_ZP_LEN
    beq S6Normal_SyncBoundContext__player1
    bra S6Normal_SyncBoundContext__done
S6Normal_SyncBoundContext__player0:
    sep #$20
    .a8
    lda.l $7E0A00+CHAR_INPUT_DRIVEN
    cmp #1
    bne S6Normal_SyncBoundContext__done
    rep #$30
    .a16
    .i16
    lda #$1900
    sta.l $7E1744
    lda #$7900
    sta.l $411744
    bra S6Normal_SyncBoundContext__done
S6Normal_SyncBoundContext__player1:
    sep #$20
    .a8
    lda.l $7E0A00+CHAR_INPUT_DRIVEN+CHAR_ZP_LEN
    cmp #1
    bne S6Normal_SyncBoundContext__done
    rep #$30
    .a16
    .i16
    lda #$1A00
    sta.l $7E1746
    lda #$7A00
    sta.l $411746
S6Normal_SyncBoundContext__done:
    ply
    plx
    plp
    rtl

; Player stock/fall remains BOR's S-CPU lifecycle, but a dead player row must
; first leave the persistent source world. Queue the normal sequenced worker
; unlink once at HP=0; the ordered unlink event clears S6Bridge_Exists, after
; which CharacterEntity_Play runs only the native player's fall/respawn path.
; Exists=2 is the pending fence and prevents duplicate remove requests while
; the worker command/event crosses the next source boundary.
S6Normal_DeathService:
    php
    rep #$30
    .a16
    .i16
    phx
    phy
    phb
    phd
    sep #$20
    .a8
    lda #0
    pha
    plb
    rep #$30
    .a16
    .i16
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    bne S6Normal_DeathService__done
    lda.l S7Resident_Owner
    cmp #2
    bne S6Normal_DeathService__done
    ldx #0
    jsl S6Normal_QueueDeadPlayer
    lda.l G13_TwoPlayerEnabled
    and #$00FF
    beq S6Normal_DeathService__done
    ldx #CHAR_ZP_LEN
    jsl S6Normal_QueueDeadPlayer
S6Normal_DeathService__done:
    pld
    plb
    ply
    plx
    plp
    ; Retain the native stock, OUT, and fall-animation semantics and return
    ; their exact carry result to StageTimerHost_ServiceDeaths.
    jml G13_HandleP2Death

; X=production row byte offset, P1/P2 only. A failed/full remove ring keeps
; ownership on SA-1 and retries at the next native death-service boundary.
S6Normal_QueueDeadPlayer:
    php
    rep #$30
    .a16
    .i16
    phx
    sep #$20
    .a8
    lda.l S6Bridge_Policy,x
    cmp #2
    bne S6Normal_QueueDeadPlayer__done
    lda.l S6Bridge_Exists,x
    cmp #1
    bne S6Normal_QueueDeadPlayer__done
    lda.l $7E0A00+CHAR_HP,x
    bne S6Normal_QueueDeadPlayer__done
    rep #$30
    .a16
    .i16
    lda #0
    sta.l S6Host_Error
    txa
    clc
    adc #$0A00
    ; The production worker installer rewrites this call to Relay_QueueRemove.
    jsl S6Host_RemoveHandle
    lda.l S6Host_Error
    beq S6Normal_QueueDeadPlayer__accepted
    ; The one-entry sequenced removal mailbox can be occupied by the other
    ; player's simultaneous death. Relay_QueueRemove reports that retryable
    ; condition as 24 in the shared host status cell; do not leave it latched
    ; as a fatal world error, or the queued first removal can never be
    ; acknowledged and neither player can progress through native lifecycle.
    cmp #24
    bne S6Normal_QueueDeadPlayer__done
    lda #0
    sta.l S6Host_Error
    bra S6Normal_QueueDeadPlayer__done
S6Normal_QueueDeadPlayer__accepted:
    sep #$20
    .a8
    lda #2
    sta.l S6Bridge_Exists,x
S6Normal_QueueDeadPlayer__done:
    rep #$30
    .a16
    .i16
    plx
    plp
    rtl

; Restore a player row after the S-CPU's existing death/respawn service. A=0
; / CHAR_ZP_LEN in the helper. This is a single-slot birth transfer, not a
; per-tick ownership exchange; all live gameplay state remains on the worker.
S6Normal_RebindReturnedPlayers:
    php
    rep #$30
    .a16
    .i16
    phx
    phy
    phb
    phd
    sep #$20
    .a8
    lda #0
    pha
    plb
    rep #$30
    .a16
    .i16
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    bne S6Normal_RebindReturnedPlayers__done
    lda.l S6Host_Mode
    cmp #1
    beq S6Normal_RebindReturnedPlayers__active
    cmp #3
    bne S6Normal_RebindReturnedPlayers__done
S6Normal_RebindReturnedPlayers__active:
    ldx #0
    jsl S6Normal_RebindReturnedPlayer
    ldx #CHAR_ZP_LEN
    jsl S6Normal_RebindReturnedPlayer
S6Normal_RebindReturnedPlayers__done:
    pld
    plb
    ply
    plx
    plp
    rtl

; X=production row byte offset. A row is eligible only after the native
; player service has restored HP and cleared OUT. The existing compiler-bound
; model policy is retained, and context+metadata are synchronized once after
; the bind so the SA-1 alias sees the new incarnation before its next tick.
S6Normal_RebindReturnedPlayer:
    php
    rep #$30
    .a16
    .i16
    phx
    phy
    phb
    phd
    sep #$20
    .a8
    lda #0
    pha
    plb
    rep #$30
    .a16
    .i16
    lda.l S6Bridge_Policy,x
    and #$00FF
    cmp #1
    beq S6Normal_RebindReturnedPlayer__owned
    cmp #2
    bne S6Normal_RebindReturnedPlayer__done
S6Normal_RebindReturnedPlayer__owned:
    lda.l S6Bridge_Exists,x
    and #$00FF
    bne S6Normal_RebindReturnedPlayer__done
    sep #$20
    .a8
    lda.l $7E0A00+CHAR_HP,x
    beq S6Normal_RebindReturnedPlayer__done
    lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
    cmp #1
    bne S6Normal_RebindReturnedPlayer__done
    cpx #0
    bne S6Normal_RebindReturnedPlayer__p2
    lda.l G13_P1Out
    bne S6Normal_RebindReturnedPlayer__done
    bra S6Normal_RebindReturnedPlayer__ready
S6Normal_RebindReturnedPlayer__p2:
    lda.l G13_TwoPlayerEnabled
    beq S6Normal_RebindReturnedPlayer__done
    lda.l G13_P2Out
    bne S6Normal_RebindReturnedPlayer__done
S6Normal_RebindReturnedPlayer__ready:
    rep #$30
    .a16
    .i16
    lda.l S7Resident_Owner
    cmp #2
    bne S6Normal_RebindReturnedPlayer__flush_done
    jsl S7Resident_Flush
S6Normal_RebindReturnedPlayer__flush_done:
    jsl S6Normal_MutationFenceBegin
S6Normal_RebindReturnedPlayer__bind:
    .a16
    .i16
    sep #$20
    .a8
    lda #1
    sta.l S6Bridge_Exists,x
    rep #$30
    .a16
    .i16
    txa
    clc
    adc #$0A00
    tcd
    ; This row already passed the Normal source-model admission check when
    ; first bound. Re-entry here is a native respawn dependency boundary,
    ; not an ActorBehavior_Bind hook call: its unbound fallback tail-jumps to
    ; the generic actor continuation and would return through the wrong stack.
    ; Reinitialize this known slot directly and fail closed in the host binder.
    jsl S6Host_BindExisting
    lda.l S6Host_Error
    bne S6Normal_RebindReturnedPlayer__fenced_done
    jsl S6Normal_SyncBoundContext
S6Normal_RebindReturnedPlayer__fenced_done:
    jsl S6Normal_MutationFenceEnd
S6Normal_RebindReturnedPlayer__done:
    pld
    plb
    ply
    plx
    plp
    rtl

; Actor-context and StageEnv publication is rare and occurs only at true
; production birth/retire boundaries. Park the persistent worker at its poll
; safepoint while those shared BW-RAM rows are updated; normal source ticks
; remain asynchronous and perform no ownership transfer.
S6Normal_MutationFenceBegin:
    php
    rep #$30
    .a16
    .i16
    phx
    phy
    lda.l $7E175C
    beq S6Normal_MutationFenceBegin__return
    sep #$20
    .a8
    lda #1
    sta.l $41200C
    rep #$30
    .a16
    .i16
    ldy #$FFFF
S6Normal_MutationFenceBegin__wait:
    sep #$20
    .a8
    lda.l $41200A
    bne S6Normal_MutationFenceBegin__fault
    lda.l $41200C
    cmp #2
    beq S6Normal_MutationFenceBegin__return
    rep #$30
    .a16
    .i16
    dey
    bne S6Normal_MutationFenceBegin__wait
S6Normal_MutationFenceBegin__fault:
    rep #$30
    .a16
    .i16
    lda #21
    sta.l S6Host_Error
    stp
S6Normal_MutationFenceBegin__return:
    rep #$30
    .a16
    .i16
    ply
    plx
    plp
    rtl

S6Normal_MutationFenceEnd:
    php
    rep #$30
    .a16
    .i16
    phx
    lda.l $7E175C
    beq S6Normal_MutationFenceEnd__return
    sep #$20
    .a8
    lda #0
    sta.l $41200C
S6Normal_MutationFenceEnd__return:
    rep #$30
    .a16
    .i16
    plx
    plp
    rtl

; S5 rational 200Hz clock, isolated host ABI. D is a separate zeroed clock
; context, DBR=0, native, decimal clear. Public JSL/RTL, A/X/Y/P clobbered.
; 00/02 elapsed master clocks * 200 (u32), 04/06 remainder (u32),
; 08/0A master clock rate (u32), 0C/0E emitted source tick count (u32).
; 16 status: 0 success, 1 invalid rate/remainder, 2 elapsed overflow;
; 1A/1C scratch. Invalid calls leave remainder/count unchanged.
; Input rate >0, remainder < rate, elapsed*200 + remainder must fit u32.
; Host supplies measured/platform-defined elapsed time, never nominal 60Hz.
; Callback S6Clock_HostSourceTick must preserve D/DBR and return A16/I16.
; Callback sees incremented source count and runs one 200Hz update. Dispatch
; drift every second source tick. Scheduling can batch updates at vblank;
; this does not mean physical CPU callbacks are spaced exactly 5ms apart.
S6Clock_ClockAdvance:
    rep #$30
    .a16
    .i16
    stz $16
    lda $08
    ora $0A
    beq S6Clock_ClockAdvance__invalid
    lda $06
    cmp $0A
    bcc S6Clock_ClockAdvance__add
    bne S6Clock_ClockAdvance__invalid
    lda $04
    cmp $08
    bcs S6Clock_ClockAdvance__invalid
S6Clock_ClockAdvance__add:
    .a16
    .i16
    lda $04
    clc
    adc $00
    sta $1A
    lda $06
    adc $02
    bcs S6Clock_ClockAdvance__overflow
    sta $06
    lda $1A
    sta $04
S6Clock_ClockAdvance__next:
    .a16
    .i16
    lda $06
    cmp $0A
    bcc S6Clock_ClockAdvance__done
    bne S6Clock_ClockAdvance__emit
    lda $04
    cmp $08
    bcc S6Clock_ClockAdvance__done
S6Clock_ClockAdvance__emit:
    .a16
    .i16
    lda $04
    sec
    sbc $08
    sta $04
    lda $06
    sbc $0A
    sta $06
    inc $0C
    bne S6Clock_ClockAdvance__callback
    inc $0E
S6Clock_ClockAdvance__callback:
    .a16
    .i16
    jsl S6Clock_HostSourceTick
    bra S6Clock_ClockAdvance__next
S6Clock_ClockAdvance__done:
    .a16
    .i16
    rtl
S6Clock_ClockAdvance__invalid:
    .a16
    .i16
    lda #1
    sta $16
    rtl
S6Clock_ClockAdvance__overflow:
    .a16
    .i16
    lda #2
    sta $16
    rtl

.bank 34
.org $8000
    .db 8,0,1,0,248,255,155,255,11,0,254,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    .db 8,0,1,0,247,255,160,255,10,0,254,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,10,0,1,0
    .db 8,0,1,0,254,255,162,255,14,0,254,255,5,0,0,0
    .db 0,0,16,0,174,255,55,0,190,255,0,0,10,0,2,0
    .db 8,0,1,0,254,255,162,255,14,0,254,255,5,0,0,0
    .db 0,0,16,0,174,255,55,0,190,255,0,0,0,0,3,0
    .db 4,0,1,0,2,0,160,255,21,0,254,255,0,0,0,0
    .db 0,0,223,255,155,255,223,255,155,255,0,0,246,255,4,0
    .db 4,0,1,0,12,0,160,255,31,0,254,255,0,0,0,0
    .db 0,0,233,255,155,255,233,255,155,255,0,0,246,255,5,0
    .db 8,0,1,0,243,255,159,255,17,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,6,0
    .db 8,0,1,0,244,255,171,255,12,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,5,0,7,0
    .db 8,0,1,0,251,255,180,255,24,0,1,0,10,0,0,0
    .db 0,0,22,0,191,255,81,0,221,255,0,0,5,0,8,0
    .db 8,0,1,0,251,255,180,255,24,0,1,0,10,0,0,0
    .db 0,0,22,0,191,255,81,0,221,255,0,0,0,0,9,0
    .db 8,0,1,0,251,255,180,255,24,0,1,0,10,0,0,0
    .db 0,0,22,0,191,255,81,0,221,255,0,0,0,0,10,0
    .db 8,0,1,0,233,255,159,255,7,0,0,0,0,0,0,0
    .db 0,0,214,255,152,255,214,255,152,255,0,0,0,0,11,0
    .db 8,0,1,0,243,255,159,255,17,0,0,0,0,0,0,0
    .db 0,0,224,255,152,255,224,255,152,255,0,0,246,255,12,0
    .db 12,0,1,0,254,255,157,255,19,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,13,0
    .db 12,0,1,0,255,255,161,255,15,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,10,0,14,0
    .db 12,0,1,0,245,255,161,255,5,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,10,0,15,0
    .db 12,0,1,0,0,0,161,255,10,0,1,0,15,0,1,0
    .db 0,0,12,0,134,255,60,0,233,255,0,0,0,0,16,0
    .db 12,0,1,0,0,0,161,255,10,0,1,0,15,0,1,0
    .db 0,0,253,255,133,255,18,0,148,255,0,0,0,0,17,0
    .db 12,0,1,0,0,0,161,255,10,0,1,0,0,0,0,0
    .db 0,0,221,255,133,255,221,255,133,255,0,0,0,0,18,0
    .db 12,0,1,0,245,255,161,255,5,0,2,0,0,0,0,0
    .db 0,0,221,255,133,255,221,255,133,255,0,0,0,0,19,0
    .db 12,0,1,0,255,255,161,255,15,0,2,0,0,0,0,0
    .db 0,0,231,255,133,255,231,255,133,255,0,0,246,255,20,0
    .db 12,0,1,0,254,255,157,255,19,0,1,0,0,0,0,0
    .db 0,0,241,255,133,255,241,255,133,255,0,0,246,255,21,0
    .db 16,0,0,0,205,255,161,255,205,255,161,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,22,0
    .db 16,0,0,0,205,255,161,255,205,255,161,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,23,0
    .db 16,0,0,0,205,255,161,255,205,255,161,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,24,0
    .db 16,0,0,0,205,255,161,255,205,255,161,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,25,0
    .db 16,0,0,0,205,255,161,255,205,255,161,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,26,0
    .db 10,0,1,0,253,255,156,255,16,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,27,0
    .db 10,0,1,0,253,255,156,255,16,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,28,0
    .db 10,0,1,0,253,255,156,255,16,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,29,0
    .db 10,0,1,0,253,255,156,255,16,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,30,0
    .db 10,0,1,0,253,255,156,255,16,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,31,0
    .db 10,0,1,0,253,255,156,255,16,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,32,0
    .db 10,0,1,0,253,255,156,255,16,0,2,0,20,0,1,0
    .db 0,0,15,0,169,255,51,0,184,255,0,0,0,0,33,0
    .db 10,0,1,0,253,255,156,255,16,0,2,0,20,0,1,0
    .db 0,0,15,0,170,255,59,0,193,255,0,0,0,0,34,0
    .db 10,0,1,0,253,255,156,255,16,0,2,0,20,0,1,0
    .db 0,0,26,0,175,255,101,0,211,255,0,0,0,0,35,0
    .db 10,0,1,0,253,255,156,255,16,0,2,0,20,0,1,0
    .db 0,0,27,0,174,255,131,0,227,255,0,0,0,0,36,0
    .db 10,0,1,0,253,255,156,255,16,0,2,0,20,0,1,0
    .db 0,0,26,0,176,255,138,0,234,255,0,0,0,0,37,0
    .db 10,0,1,0,253,255,156,255,16,0,2,0,20,0,1,0
    .db 0,0,26,0,176,255,143,0,234,255,0,0,0,0,38,0
    .db 10,0,1,0,253,255,156,255,16,0,2,0,20,0,1,0
    .db 0,0,26,0,176,255,148,0,234,255,0,0,0,0,39,0
    .db 10,0,1,0,253,255,156,255,16,0,2,0,20,0,1,0
    .db 0,0,26,0,176,255,148,0,234,255,0,0,0,0,40,0
    .db 10,0,1,0,253,255,156,255,16,0,2,0,20,0,1,0
    .db 0,0,26,0,176,255,148,0,234,255,0,0,0,0,41,0
    .db 10,0,1,0,253,255,156,255,16,0,2,0,0,0,0,0
    .db 0,0,215,255,141,255,215,255,141,255,0,0,0,0,42,0
    .db 10,0,1,0,253,255,156,255,16,0,2,0,0,0,0,0
    .db 0,0,215,255,141,255,215,255,141,255,0,0,0,0,43,0
    .db 10,0,1,0,253,255,156,255,16,0,2,0,0,0,0,0
    .db 0,0,215,255,141,255,215,255,141,255,0,0,0,0,44,0
    .db 10,0,1,0,253,255,156,255,16,0,2,0,0,0,0,0
    .db 0,0,215,255,141,255,215,255,141,255,0,0,0,0,45,0
    .db 10,0,1,0,253,255,156,255,16,0,2,0,0,0,0,0
    .db 0,0,215,255,141,255,215,255,141,255,0,0,0,0,46,0
    .db 10,0,1,0,253,255,156,255,16,0,2,0,0,0,0,0
    .db 0,0,215,255,141,255,215,255,141,255,0,0,0,0,47,0
    .db 10,0,1,0,253,255,156,255,16,0,2,0,0,0,0,0
    .db 0,0,215,255,141,255,215,255,141,255,0,0,0,0,48,0
    .db 10,0,1,0,253,255,156,255,16,0,2,0,0,0,0,0
    .db 0,0,215,255,141,255,215,255,141,255,0,0,0,0,49,0
    .db 10,0,0,0,215,255,161,255,215,255,161,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,50,0
    .db 10,0,0,0,215,255,161,255,215,255,161,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,51,0
    .db 60,0,0,0,215,255,161,255,215,255,161,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,52,0
    .db 10,0,0,0,215,255,161,255,215,255,161,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,53,0
    .db 10,0,0,0,215,255,161,255,215,255,161,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,54,0
    .db 208,7,1,0,250,255,187,255,27,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,55,0
    .db 8,0,1,0,254,255,165,255,17,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,56,0
    .db 8,0,1,0,254,255,165,255,17,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,57,0
    .db 40,0,1,0,254,255,165,255,17,0,2,0,6,0,0,0
    .db 0,0,12,0,191,255,46,0,217,255,0,0,0,0,58,0
    .db 8,0,1,0,254,255,165,255,17,0,2,0,0,0,0,0
    .db 0,0,220,255,156,255,220,255,156,255,0,0,0,0,59,0
    .db 8,0,1,0,254,255,165,255,17,0,2,0,0,0,0,0
    .db 0,0,220,255,156,255,220,255,156,255,0,0,0,0,60,0
    .db 10,0,1,0,250,255,160,255,19,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,61,0
    .db 10,0,1,0,250,255,160,255,19,0,4,0,8,0,0,0
    .db 0,0,11,0,139,255,38,0,190,255,0,0,0,0,62,0
    .db 10,0,1,0,253,255,160,255,22,0,4,0,8,0,0,0
    .db 0,0,11,0,139,255,38,0,190,255,0,0,0,0,63,0
    .db 10,0,1,0,253,255,160,255,22,0,4,0,0,0,0,0
    .db 0,0,216,255,135,255,216,255,135,255,0,0,0,0,64,0
    .db 10,0,1,0,0,0,160,255,25,0,4,0,0,0,0,0
    .db 0,0,216,255,135,255,216,255,135,255,0,0,0,0,65,0
    .db 10,0,1,0,1,0,166,255,27,0,3,0,10,0,1,0
    .db 0,0,17,0,172,255,44,0,207,255,0,0,0,0,66,0
    .db 10,0,1,0,1,0,166,255,27,0,3,0,10,0,1,0
    .db 0,0,17,0,172,255,44,0,207,255,0,0,0,0,67,0
    .db 10,0,1,0,1,0,166,255,27,0,3,0,0,0,0,0
    .db 0,0,216,255,135,255,216,255,135,255,0,0,0,0,68,0
    .db 10,0,1,0,1,0,166,255,27,0,3,0,0,0,0,0
    .db 0,0,216,255,135,255,216,255,135,255,0,0,0,0,69,0
    .db 10,0,1,0,242,255,157,255,10,0,3,0,0,0,0,0
    .db 0,0,216,255,135,255,216,255,135,255,0,0,0,0,70,0
    .db 20,0,1,0,247,255,159,255,13,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,71,0
    .db 20,0,1,0,247,255,159,255,13,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,72,0
    .db 20,0,1,0,247,255,159,255,13,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,73,0
    .db 20,0,1,0,247,255,159,255,13,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,74,0
    .db 20,0,1,0,247,255,159,255,13,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,75,0
    .db 20,0,1,0,247,255,159,255,13,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,76,0
    .db 20,0,1,0,247,255,159,255,13,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,77,0
    .db 20,0,1,0,247,255,159,255,13,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,78,0
    .db 20,0,1,0,247,255,159,255,13,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,79,0
    .db 20,0,1,0,247,255,159,255,13,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,80,0
    .db 20,0,1,0,247,255,159,255,13,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,81,0
    .db 20,0,1,0,247,255,159,255,13,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,82,0
    .db 20,0,1,0,247,255,159,255,13,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,83,0
    .db 20,0,1,0,247,255,159,255,13,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,84,0
    .db 20,0,1,0,247,255,159,255,13,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,85,0
    .db 20,0,1,0,247,255,159,255,13,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,86,0
    .db 20,0,1,0,247,255,159,255,13,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,87,0
    .db 20,0,1,0,247,255,159,255,13,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,88,0
    .db 14,0,1,0,246,255,185,255,7,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,89,0
    .db 14,0,1,0,250,255,170,255,8,0,7,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,90,0
    .db 14,0,1,0,244,255,172,255,255,255,234,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,91,0
    .db 14,0,1,0,242,255,170,255,14,0,215,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,92,0
    .db 14,0,1,0,247,255,173,255,9,0,225,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,93,0
    .db 208,7,1,0,247,255,169,255,12,0,223,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,94,0
    .db 14,0,1,0,248,255,166,255,10,0,231,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,95,0
    .db 208,7,1,0,248,255,166,255,10,0,231,255,6,0,1,0
    .db 0,0,37,0,217,255,69,0,244,255,0,0,0,0,96,0
    .db 14,0,1,0,239,255,190,255,16,0,243,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,97,0
    .db 14,0,1,0,239,255,196,255,16,0,240,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,98,0
    .db 14,0,1,0,236,255,186,255,14,0,221,255,6,0,0,0
    .db 0,0,1,0,215,255,29,0,247,255,0,0,0,0,99,0
    .db 208,7,1,0,236,255,186,255,14,0,221,255,6,0,0,0
    .db 0,0,1,0,216,255,29,0,249,255,0,0,0,0,100,0
    .db 50,0,1,0,246,255,185,255,7,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,101,0
    .db 16,0,1,0,237,255,167,255,17,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,102,0
    .db 100,0,1,0,237,255,167,255,17,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,103,0
    .db 16,0,1,0,237,255,167,255,17,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,104,0
    .db 20,0,0,0,224,255,162,255,224,255,162,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,105,0
    .db 20,0,0,0,224,255,162,255,224,255,162,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,106,0
    .db 20,0,0,0,224,255,162,255,224,255,162,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,107,0
    .db 20,0,0,0,224,255,162,255,224,255,162,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,108,0
    .db 6,0,0,0,180,255,123,255,180,255,123,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,109,0
    .db 6,0,0,0,180,255,123,255,180,255,123,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,110,0
    .db 6,0,0,0,180,255,123,255,180,255,123,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,111,0
    .db 6,0,0,0,180,255,123,255,180,255,123,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,112,0
    .db 6,0,0,0,180,255,123,255,180,255,123,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,113,0
    .db 6,0,0,0,180,255,123,255,180,255,123,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,114,0
    .db 6,0,0,0,180,255,123,255,180,255,123,255,20,0,1,0
    .db 1,0,185,255,173,255,249,255,2,0,0,0,0,0,115,0
    .db 6,0,0,0,180,255,123,255,180,255,123,255,20,0,1,0
    .db 1,0,185,255,173,255,249,255,54,0,0,0,0,0,116,0
    .db 6,0,0,0,180,255,123,255,180,255,123,255,20,0,1,0
    .db 1,0,249,255,173,255,57,0,245,255,0,0,0,0,117,0
    .db 6,0,0,0,180,255,123,255,180,255,123,255,0,0,1,0
    .db 1,0,180,255,123,255,180,255,123,255,0,0,0,0,118,0
    .db 6,0,0,0,180,255,123,255,180,255,123,255,20,0,1,0
    .db 1,0,180,255,190,255,40,0,2,0,0,0,0,0,119,0
    .db 6,0,0,0,180,255,123,255,180,255,123,255,20,0,1,0
    .db 1,0,183,255,180,255,255,255,0,0,0,0,0,0,120,0
    .db 6,0,0,0,180,255,123,255,180,255,123,255,20,0,1,0
    .db 1,0,246,255,175,255,42,0,2,0,0,0,0,0,121,0
    .db 6,0,0,0,180,255,123,255,180,255,123,255,0,0,1,0
    .db 1,0,180,255,123,255,180,255,123,255,0,0,0,0,122,0
    .db 6,0,0,0,180,255,123,255,180,255,123,255,0,0,1,0
    .db 1,0,180,255,123,255,180,255,123,255,0,0,0,0,123,0
    .db 6,0,0,0,180,255,123,255,180,255,123,255,0,0,1,0
    .db 1,0,180,255,123,255,180,255,123,255,0,0,0,0,124,0
    .db 6,0,0,0,180,255,123,255,180,255,123,255,0,0,1,0
    .db 1,0,180,255,123,255,180,255,123,255,0,0,0,0,125,0
    .db 6,0,0,0,180,255,123,255,180,255,123,255,0,0,1,0
    .db 1,0,180,255,123,255,180,255,123,255,0,0,0,0,126,0
    .db 6,0,0,0,180,255,123,255,180,255,123,255,0,0,1,0
    .db 1,0,180,255,123,255,180,255,123,255,0,0,0,0,127,0
    .db 20,0,0,0,216,255,196,255,216,255,196,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,128,0
    .db 60,0,0,0,216,255,196,255,216,255,196,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,129,0
    .db 20,0,0,0,216,255,196,255,216,255,196,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,130,0
    .db 14,0,1,0,249,255,155,255,8,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,131,0
    .db 14,0,1,0,249,255,155,255,8,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,132,0
    .db 14,0,1,0,249,255,155,255,8,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,133,0
    .db 14,0,1,0,249,255,155,255,8,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,134,0
    .db 14,0,1,0,249,255,155,255,8,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,135,0
    .db 14,0,1,0,249,255,155,255,8,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,136,0
    .db 14,0,1,0,249,255,155,255,8,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,137,0
    .db 14,0,1,0,249,255,155,255,8,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,138,0
    .db 14,0,1,0,249,255,155,255,8,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,139,0
    .db 14,0,1,0,249,255,155,255,8,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,140,0
    .db 0,0,6,0,0,128,34,0,0,0,0,0,0,0,0,0
    .db 1,0,7,0,192,128,34,0,0,0,0,0,0,0,0,0
    .db 2,0,9,0,160,129,34,0,0,0,0,0,0,0,0,0
    .db 3,0,5,0,192,130,34,0,0,0,0,0,0,0,0,0
    .db 4,0,23,0,96,131,34,0,0,0,0,0,0,0,0,0
    .db 5,0,5,0,64,134,34,0,0,0,0,0,0,0,0,0
    .db 6,0,1,0,224,134,34,0,0,0,0,0,0,0,0,0
    .db 7,0,5,0,0,135,34,0,0,0,0,0,0,0,0,0
    .db 8,0,10,0,160,135,34,0,0,0,0,0,0,0,0,0
    .db 9,0,18,0,224,136,34,1,0,0,0,0,0,0,0,0
    .db 10,0,6,0,32,139,34,0,0,0,0,0,0,0,0,0
    .db 11,0,2,0,224,139,34,0,0,0,0,0,0,0,0,0
    .db 12,0,4,0,32,140,34,0,0,0,0,0,0,0,0,0
    .db 13,0,1,0,160,140,34,0,0,0,0,0,0,0,0,0
    .db 14,0,3,0,192,140,34,0,0,0,0,0,0,0,0,0
    .db 15,0,4,0,32,141,34,0,0,0,0,0,0,0,0,0
    .db 16,0,19,0,160,141,34,0,0,0,0,0,0,0,0,0
    .db 17,0,3,0,0,144,34,0,0,0,0,0,0,0,0,0
    .db 18,0,10,0,96,144,34,1,0,0,0,0,0,0,0,0
    .db 10,0,1,0,232,255,139,255,21,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    .db 10,0,1,0,232,255,139,255,21,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0
    .db 10,0,1,0,242,255,143,255,37,0,3,0,7,0,0,0
    .db 0,0,31,0,158,255,73,0,197,255,0,0,0,0,2,0
    .db 10,0,1,0,242,255,143,255,37,0,3,0,7,0,0,0
    .db 0,0,31,0,158,255,73,0,197,255,0,0,0,0,3,0
    .db 10,0,1,0,242,255,142,255,36,0,2,0,0,0,0,0
    .db 0,0,211,255,137,255,211,255,137,255,0,0,0,0,4,0
    .db 12,0,1,0,241,255,143,255,30,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,5,0
    .db 12,0,1,0,239,255,143,255,28,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,2,0,6,0
    .db 12,0,1,0,237,255,143,255,26,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,2,0,7,0
    .db 12,0,1,0,235,255,143,255,24,0,1,0,14,0,0,0
    .db 0,0,5,0,171,255,69,0,203,255,0,0,2,0,8,0
    .db 12,0,1,0,233,255,143,255,22,0,1,0,14,0,0,0
    .db 0,0,3,0,171,255,67,0,203,255,0,0,2,0,9,0
    .db 12,0,1,0,231,255,143,255,20,0,1,0,0,0,0,0
    .db 0,0,198,255,140,255,198,255,140,255,0,0,2,0,10,0
    .db 12,0,1,0,231,255,143,255,20,0,1,0,0,0,0,0
    .db 0,0,198,255,140,255,198,255,140,255,0,0,0,0,11,0
    .db 6,0,1,0,243,255,143,255,25,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,12,0
    .db 6,0,1,0,243,255,143,255,25,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,13,0
    .db 6,0,1,0,239,255,143,255,21,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,14,0
    .db 10,0,1,0,239,255,143,255,21,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,15,0
    .db 10,0,1,0,236,255,143,255,18,0,2,0,20,0,1,0
    .db 0,0,216,255,131,255,241,255,173,255,0,0,0,0,16,0
    .db 10,0,1,0,244,255,143,255,26,0,2,0,20,0,1,0
    .db 0,0,210,255,142,255,248,255,181,255,0,0,0,0,17,0
    .db 10,0,1,0,3,0,152,255,41,0,2,0,20,0,1,0
    .db 0,0,222,255,170,255,15,0,212,255,0,0,0,0,18,0
    .db 10,0,1,0,25,0,152,255,58,0,2,0,20,0,1,0
    .db 0,0,245,255,173,255,95,0,228,255,0,0,0,0,19,0
    .db 10,0,1,0,13,0,151,255,46,0,1,0,20,0,1,0
    .db 0,0,44,0,118,255,83,0,208,255,0,0,0,0,20,0
    .db 10,0,1,0,11,0,141,255,44,0,1,0,20,0,1,0
    .db 0,0,23,0,118,255,58,0,145,255,0,0,0,0,21,0
    .db 10,0,1,0,16,0,141,255,46,0,1,0,20,0,1,0
    .db 0,0,23,0,118,255,58,0,145,255,0,0,0,0,22,0
    .db 10,0,1,0,16,0,141,255,46,0,1,0,20,0,1,0
    .db 0,0,23,0,118,255,58,0,145,255,0,0,0,0,23,0
    .db 40,0,0,0,189,255,189,255,189,255,189,255,17,0,1,0
    .db 0,0,227,255,205,255,15,0,254,255,0,0,0,0,24,0
    .db 40,0,0,0,189,255,189,255,189,255,189,255,17,0,1,0
    .db 0,0,202,255,237,255,53,0,7,0,0,0,0,0,25,0
    .db 8,0,1,0,247,255,152,255,35,0,255,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,26,0
    .db 8,0,1,0,252,255,149,255,38,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,27,0
    .db 8,0,1,0,252,255,143,255,29,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,20,0,28,0
    .db 8,0,1,0,232,255,150,255,21,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,50,0,29,0
    .db 8,0,1,0,232,255,150,255,21,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,30,0
    .db 8,0,1,0,232,255,150,255,21,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,31,0
    .db 8,0,1,0,243,255,156,255,32,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,32,0
    .db 8,0,1,0,243,255,156,255,32,0,1,0,24,0,1,0
    .db 0,0,15,0,160,255,120,0,196,255,0,0,0,0,33,0
    .db 8,0,1,0,246,255,163,255,33,0,2,0,24,0,1,0
    .db 0,0,15,0,160,255,120,0,196,255,0,0,0,0,34,0
    .db 8,0,1,0,246,255,163,255,33,0,2,0,24,0,1,0
    .db 0,0,15,0,160,255,120,0,196,255,0,0,0,0,35,0
    .db 8,0,1,0,246,255,163,255,33,0,2,0,24,0,1,0
    .db 0,0,15,0,160,255,120,0,196,255,0,0,0,0,36,0
    .db 8,0,1,0,246,255,163,255,33,0,2,0,24,0,1,0
    .db 0,0,15,0,160,255,120,0,196,255,0,0,0,0,37,0
    .db 8,0,1,0,246,255,163,255,33,0,2,0,24,0,1,0
    .db 0,0,15,0,160,255,120,0,196,255,0,0,0,0,38,0
    .db 8,0,1,0,246,255,163,255,33,0,2,0,24,0,1,0
    .db 0,0,15,0,160,255,120,0,196,255,0,0,0,0,39,0
    .db 8,0,1,0,246,255,163,255,33,0,2,0,24,0,1,0
    .db 0,0,15,0,160,255,120,0,196,255,0,0,0,0,40,0
    .db 8,0,1,0,246,255,163,255,33,0,2,0,0,0,0,0
    .db 0,0,152,255,131,255,152,255,131,255,0,0,0,0,41,0
    .db 8,0,1,0,246,255,163,255,33,0,2,0,0,0,0,0
    .db 0,0,152,255,131,255,152,255,131,255,0,0,0,0,42,0
    .db 8,0,1,0,246,255,163,255,33,0,2,0,0,0,0,0
    .db 0,0,152,255,131,255,152,255,131,255,0,0,0,0,43,0
    .db 8,0,1,0,246,255,163,255,33,0,2,0,0,0,0,0
    .db 0,0,152,255,131,255,152,255,131,255,0,0,0,0,44,0
    .db 8,0,1,0,246,255,163,255,33,0,2,0,0,0,0,0
    .db 0,0,152,255,131,255,152,255,131,255,0,0,0,0,45,0
    .db 8,0,1,0,246,255,163,255,33,0,2,0,0,0,0,0
    .db 0,0,152,255,131,255,152,255,131,255,0,0,0,0,46,0
    .db 8,0,1,0,246,255,163,255,33,0,2,0,0,0,0,0
    .db 0,0,152,255,131,255,152,255,131,255,0,0,0,0,47,0
    .db 8,0,1,0,240,255,153,255,25,0,1,0,0,0,0,0
    .db 0,0,166,255,131,255,166,255,131,255,0,0,242,255,48,0
    .db 8,0,1,0,238,255,146,255,25,0,2,0,0,0,0,0
    .db 0,0,191,255,131,255,191,255,131,255,0,0,231,255,49,0
    .db 8,0,1,0,241,255,145,255,25,0,1,0,0,0,0,0
    .db 0,0,202,255,131,255,202,255,131,255,0,0,245,255,50,0
    .db 8,0,1,0,245,255,149,255,36,0,254,255,0,0,0,0
    .db 0,0,222,255,131,255,222,255,131,255,0,0,236,255,51,0
    .db 10,0,0,0,222,255,139,255,222,255,139,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,52,0
    .db 10,0,0,0,222,255,139,255,222,255,139,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,53,0
    .db 60,0,0,0,222,255,139,255,222,255,139,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,54,0
    .db 10,0,0,0,222,255,139,255,222,255,139,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,55,0
    .db 10,0,0,0,222,255,139,255,222,255,139,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,56,0
    .db 10,0,0,0,222,255,139,255,222,255,139,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,57,0
    .db 10,0,0,0,222,255,139,255,222,255,139,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,58,0
    .db 200,0,1,0,245,255,151,255,24,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,59,0
    .db 70,0,1,0,252,255,147,255,30,0,14,0,10,0,0,0
    .db 0,0,7,0,191,255,38,0,232,255,0,0,0,0,60,0
    .db 32,0,1,0,238,255,139,255,35,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,61,0
    .db 32,0,1,0,238,255,139,255,35,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,62,0
    .db 32,0,1,0,238,255,139,255,35,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,63,0
    .db 32,0,1,0,238,255,139,255,35,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,64,0
    .db 32,0,1,0,238,255,139,255,35,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,65,0
    .db 32,0,1,0,238,255,139,255,35,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,66,0
    .db 32,0,1,0,238,255,139,255,35,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,67,0
    .db 32,0,1,0,238,255,139,255,35,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,68,0
    .db 32,0,1,0,238,255,139,255,35,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,69,0
    .db 32,0,1,0,238,255,139,255,35,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,70,0
    .db 20,0,1,0,243,255,141,255,42,0,6,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,71,0
    .db 20,0,1,0,242,255,139,255,44,0,244,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,72,0
    .db 20,0,1,0,246,255,141,255,44,0,232,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,73,0
    .db 20,0,1,0,240,255,144,255,51,0,218,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,74,0
    .db 20,0,1,0,246,255,141,255,44,0,232,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,75,0
    .db 20,0,1,0,242,255,139,255,44,0,244,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,76,0
    .db 20,0,1,0,243,255,141,255,42,0,6,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,77,0
    .db 14,0,1,0,226,255,155,255,13,0,247,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,78,0
    .db 14,0,1,0,226,255,155,255,13,0,247,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,79,0
    .db 14,0,1,0,226,255,155,255,13,0,247,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,80,0
    .db 14,0,1,0,226,255,155,255,23,0,236,255,7,0,1,0
    .db 0,0,0,0,187,255,72,0,216,255,0,0,0,0,81,0
    .db 14,0,1,0,226,255,155,255,23,0,236,255,7,0,1,0
    .db 0,0,0,0,187,255,72,0,216,255,0,0,0,0,82,0
    .db 14,0,1,0,235,255,149,255,19,0,236,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,83,0
    .db 14,0,1,0,213,255,152,255,23,0,239,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,84,0
    .db 14,0,1,0,216,255,153,255,18,0,237,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,85,0
    .db 14,0,1,0,209,255,154,255,30,0,216,255,7,0,0,0
    .db 0,0,9,0,160,255,32,0,203,255,0,0,0,0,86,0
    .db 50,0,1,0,231,255,176,255,27,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,87,0
    .db 16,0,1,0,237,255,151,255,18,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,88,0
    .db 72,0,1,0,237,255,151,255,18,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,89,0
    .db 12,0,1,0,237,255,151,255,18,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,90,0
    .db 12,0,1,0,237,255,151,255,18,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,91,0
    .db 12,0,1,0,237,255,151,255,18,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,92,0
    .db 20,0,0,0,200,255,153,255,200,255,153,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,93,0
    .db 20,0,0,0,200,255,153,255,200,255,153,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,94,0
    .db 20,0,0,0,200,255,153,255,200,255,153,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,95,0
    .db 20,0,0,0,200,255,153,255,200,255,153,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,96,0
    .db 20,0,0,0,200,255,153,255,200,255,153,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,97,0
    .db 16,0,0,0,175,255,44,255,175,255,44,255,20,0,1,0
    .db 1,0,185,255,160,255,69,0,2,0,0,0,0,0,98,0
    .db 16,0,0,0,175,255,44,255,175,255,44,255,20,0,1,0
    .db 1,0,185,255,160,255,69,0,2,0,0,0,0,0,99,0
    .db 16,0,0,0,175,255,44,255,175,255,44,255,20,0,1,0
    .db 1,0,185,255,160,255,69,0,2,0,0,0,0,0,100,0
    .db 16,0,0,0,175,255,44,255,175,255,44,255,20,0,1,0
    .db 1,0,185,255,160,255,69,0,2,0,0,0,0,0,101,0
    .db 16,0,0,0,175,255,44,255,175,255,44,255,20,0,1,0
    .db 1,0,185,255,160,255,69,0,2,0,0,0,0,0,102,0
    .db 16,0,0,0,175,255,44,255,175,255,44,255,0,0,0,0
    .db 0,0,175,255,44,255,175,255,44,255,0,0,0,0,103,0
    .db 16,0,0,0,175,255,44,255,175,255,44,255,0,0,0,0
    .db 0,0,175,255,44,255,175,255,44,255,0,0,0,0,104,0
    .db 16,0,0,0,175,255,44,255,175,255,44,255,0,0,0,0
    .db 0,0,175,255,44,255,175,255,44,255,0,0,0,0,105,0
    .db 14,0,0,0,174,255,141,255,174,255,141,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,106,0
    .db 14,0,0,0,174,255,141,255,174,255,141,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,107,0
    .db 14,0,0,0,174,255,141,255,174,255,141,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,108,0
    .db 14,0,0,0,174,255,141,255,174,255,141,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,109,0
    .db 14,0,0,0,174,255,141,255,174,255,141,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,110,0
    .db 14,0,0,0,174,255,141,255,174,255,141,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,111,0
    .db 14,0,0,0,174,255,141,255,174,255,141,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,112,0
    .db 14,0,0,0,174,255,141,255,174,255,141,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,113,0
    .db 28,0,1,0,234,255,134,255,20,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,114,0
    .db 28,0,1,0,234,255,134,255,20,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,115,0
    .db 28,0,1,0,234,255,134,255,20,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,116,0
    .db 28,0,1,0,234,255,134,255,20,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,117,0
    .db 28,0,1,0,234,255,134,255,20,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,118,0
    .db 28,0,1,0,234,255,134,255,20,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,119,0
    .db 28,0,1,0,234,255,134,255,20,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,120,0
    .db 28,0,1,0,234,255,134,255,20,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,121,0
    .db 0,0,5,0,208,146,34,0,0,0,0,0,0,0,0,0
    .db 1,0,7,0,112,147,34,0,0,0,0,0,0,0,0,0
    .db 2,0,12,0,80,148,34,0,0,0,0,0,0,0,0,0
    .db 3,0,2,0,208,149,34,0,0,0,0,0,0,0,0,0
    .db 4,0,26,0,16,150,34,0,0,0,0,0,0,0,0,0
    .db 5,0,7,0,80,153,34,0,0,0,0,0,0,0,0,0
    .db 6,0,1,0,48,154,34,0,0,0,0,0,0,0,0,0
    .db 7,0,1,0,80,154,34,0,0,0,0,0,0,0,0,0
    .db 8,0,10,0,112,154,34,1,0,0,0,0,0,0,0,0
    .db 9,0,7,0,176,155,34,0,0,0,0,0,0,0,0,0
    .db 10,0,5,0,144,156,34,0,0,0,0,0,0,0,0,0
    .db 11,0,4,0,48,157,34,0,0,0,0,0,0,0,0,0
    .db 12,0,1,0,176,157,34,0,0,0,0,0,0,0,0,0
    .db 13,0,5,0,208,157,34,0,0,0,0,0,0,0,0,0
    .db 14,0,5,0,112,158,34,0,0,0,0,0,0,0,0,0
    .db 15,0,8,0,16,159,34,0,0,0,0,0,0,0,0,0
    .db 16,0,8,0,16,160,34,0,0,0,0,0,0,0,0,0
    .db 17,0,8,0,16,161,34,1,0,0,0,0,0,0,0,0
    .db 8,0,1,0,240,255,162,255,15,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    .db 8,0,1,0,244,255,162,255,19,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0
    .db 8,0,1,0,244,255,162,255,19,0,4,0,5,0,0,0
    .db 0,0,12,0,170,255,40,0,195,255,0,0,0,0,2,0
    .db 8,0,1,0,244,255,162,255,19,0,4,0,5,0,0,0
    .db 0,0,12,0,170,255,55,0,195,255,0,0,0,0,3,0
    .db 4,0,1,0,244,255,162,255,19,0,4,0,0,0,0,0
    .db 0,0,227,255,160,255,227,255,160,255,0,0,0,0,4,0
    .db 4,0,1,0,244,255,162,255,19,0,4,0,0,0,0,0
    .db 0,0,227,255,160,255,227,255,160,255,0,0,0,0,5,0
    .db 10,0,1,0,234,255,164,255,10,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,6,0
    .db 10,0,1,0,240,255,168,255,16,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,5,0,7,0
    .db 10,0,1,0,238,255,168,255,14,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,20,0,8,0
    .db 16,0,1,0,240,255,168,255,20,0,4,0,10,0,0,0
    .db 0,0,5,0,176,255,35,0,205,255,0,0,0,0,9,0
    .db 16,0,1,0,238,255,168,255,14,0,3,0,0,0,0,0
    .db 0,0,200,255,161,255,200,255,161,255,0,0,0,0,10,0
    .db 16,0,1,0,237,255,168,255,17,0,4,0,0,0,0,0
    .db 0,0,217,255,161,255,217,255,161,255,0,0,231,255,11,0
    .db 12,0,0,0,223,255,159,255,223,255,159,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,12,0
    .db 12,0,0,0,223,255,159,255,223,255,159,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,13,0
    .db 12,0,0,0,223,255,159,255,223,255,159,255,0,0,0,0
    .db 0,0,9,0,195,255,45,0,236,255,0,0,0,0,14,0
    .db 16,0,0,0,223,255,159,255,223,255,159,255,15,0,1,0
    .db 0,0,15,0,193,255,80,0,231,255,0,0,0,0,15,0
    .db 16,0,0,0,223,255,159,255,223,255,159,255,15,0,1,0
    .db 0,0,15,0,193,255,80,0,231,255,0,0,0,0,16,0
    .db 16,0,0,0,223,255,159,255,223,255,159,255,0,0,0,0
    .db 0,0,223,255,159,255,223,255,159,255,0,0,0,0,17,0
    .db 16,0,1,0,247,255,177,255,25,0,2,0,0,0,0,0
    .db 0,0,223,255,159,255,223,255,159,255,0,0,0,0,18,0
    .db 16,0,1,0,247,255,177,255,25,0,2,0,0,0,0,0
    .db 0,0,223,255,159,255,223,255,159,255,0,0,0,0,19,0
    .db 16,0,1,0,245,255,163,255,23,0,244,255,0,0,0,0
    .db 0,0,223,255,159,255,223,255,159,255,0,0,0,0,20,0
    .db 16,0,0,0,199,255,198,255,199,255,198,255,10,0,1,0
    .db 0,0,231,255,220,255,14,0,5,0,0,0,0,0,21,0
    .db 16,0,0,0,199,255,198,255,199,255,198,255,10,0,1,0
    .db 0,0,209,255,234,255,15,0,6,0,0,0,0,0,22,0
    .db 16,0,0,0,199,255,198,255,199,255,198,255,10,0,1,0
    .db 0,0,210,255,233,255,28,0,0,0,0,0,0,0,23,0
    .db 16,0,0,0,199,255,198,255,199,255,198,255,10,0,1,0
    .db 0,0,218,255,228,255,11,0,4,0,0,0,0,0,24,0
    .db 16,0,0,0,199,255,198,255,199,255,198,255,10,0,1,0
    .db 0,0,207,255,242,255,50,0,2,0,0,0,0,0,25,0
    .db 10,0,1,0,240,255,179,255,21,0,240,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,26,0
    .db 10,0,1,0,247,255,194,255,30,0,244,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,27,0
    .db 10,0,1,0,233,255,194,255,16,0,244,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,28,0
    .db 10,0,1,0,233,255,194,255,16,0,244,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,29,0
    .db 16,0,1,0,232,255,183,255,5,0,243,255,20,0,1,0
    .db 0,0,249,255,185,255,50,0,234,255,0,0,0,0,30,0
    .db 16,0,1,0,232,255,183,255,5,0,243,255,20,0,1,0
    .db 0,0,249,255,185,255,50,0,234,255,0,0,0,0,31,0
    .db 16,0,1,0,240,255,169,255,11,0,222,255,20,0,1,0
    .db 0,0,249,255,185,255,50,0,234,255,0,0,0,0,32,0
    .db 30,0,1,0,240,255,204,255,11,0,1,0,0,0,0,0
    .db 0,0,211,255,163,255,211,255,163,255,0,0,0,0,33,0
    .db 16,0,1,0,242,255,185,255,17,0,254,255,0,0,0,0
    .db 0,0,211,255,163,255,211,255,163,255,0,0,0,0,34,0
    .db 10,0,0,0,215,255,161,255,215,255,161,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,35,0
    .db 10,0,0,0,215,255,161,255,215,255,161,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,36,0
    .db 10,0,0,0,215,255,161,255,215,255,161,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,37,0
    .db 60,0,0,0,215,255,161,255,215,255,161,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,38,0
    .db 10,0,0,0,215,255,161,255,215,255,161,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,39,0
    .db 10,0,0,0,215,255,161,255,215,255,161,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,40,0
    .db 10,0,0,0,215,255,161,255,215,255,161,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,41,0
    .db 208,7,1,0,249,255,179,255,20,0,250,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,42,0
    .db 12,0,1,0,1,0,182,255,20,0,19,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,43,0
    .db 40,0,1,0,1,0,182,255,20,0,19,0,6,0,0,0
    .db 0,0,14,0,200,255,44,0,231,255,0,0,0,0,44,0
    .db 12,0,1,0,1,0,182,255,20,0,19,0,0,0,0,0
    .db 0,0,223,255,158,255,223,255,158,255,0,0,0,0,45,0
    .db 10,0,1,0,253,255,167,255,21,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,46,0
    .db 10,0,1,0,253,255,167,255,21,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,47,0
    .db 10,0,1,0,253,255,167,255,21,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,48,0
    .db 10,0,1,0,253,255,167,255,21,0,2,0,16,0,1,0
    .db 0,0,17,0,180,255,61,0,210,255,0,0,0,0,49,0
    .db 10,0,1,0,253,255,167,255,21,0,2,0,16,0,1,0
    .db 0,0,14,0,148,255,60,0,189,255,0,0,0,0,50,0
    .db 10,0,1,0,253,255,167,255,21,0,2,0,16,0,1,0
    .db 0,0,14,0,148,255,60,0,189,255,0,0,0,0,51,0
    .db 10,0,1,0,253,255,167,255,21,0,2,0,16,0,1,0
    .db 0,0,14,0,148,255,60,0,189,255,0,0,0,0,52,0
    .db 10,0,1,0,253,255,167,255,21,0,2,0,0,0,0,0
    .db 0,0,223,255,139,255,223,255,139,255,0,0,0,0,53,0
    .db 10,0,1,0,253,255,167,255,21,0,2,0,0,0,0,0
    .db 0,0,223,255,139,255,223,255,139,255,0,0,0,0,54,0
    .db 10,0,1,0,253,255,167,255,21,0,2,0,0,0,0,0
    .db 0,0,223,255,139,255,223,255,139,255,0,0,0,0,55,0
    .db 10,0,1,0,253,255,167,255,21,0,2,0,0,0,0,0
    .db 0,0,223,255,139,255,223,255,139,255,0,0,0,0,56,0
    .db 10,0,1,0,253,255,167,255,21,0,2,0,0,0,0,0
    .db 0,0,223,255,139,255,223,255,139,255,0,0,0,0,57,0
    .db 20,0,1,0,239,255,166,255,17,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,58,0
    .db 20,0,1,0,239,255,166,255,17,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,59,0
    .db 20,0,1,0,239,255,166,255,17,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,60,0
    .db 20,0,1,0,239,255,166,255,17,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,61,0
    .db 20,0,1,0,239,255,166,255,17,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,62,0
    .db 20,0,1,0,239,255,166,255,17,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,63,0
    .db 20,0,1,0,239,255,166,255,17,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,64,0
    .db 12,0,1,0,243,255,174,255,20,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,65,0
    .db 12,0,1,0,240,255,159,255,18,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,66,0
    .db 12,0,1,0,240,255,159,255,18,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,67,0
    .db 12,0,1,0,240,255,159,255,18,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,68,0
    .db 12,0,1,0,241,255,164,255,19,0,246,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,69,0
    .db 12,0,1,0,240,255,173,255,18,0,242,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,70,0
    .db 12,0,1,0,240,255,173,255,18,0,242,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,71,0
    .db 12,0,1,0,240,255,173,255,18,0,242,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,72,0
    .db 12,0,1,0,240,255,173,255,18,0,242,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,73,0
    .db 12,0,1,0,240,255,165,255,18,0,253,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,74,0
    .db 208,7,1,0,9,0,171,255,30,0,225,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,75,0
    .db 14,0,1,0,237,255,189,255,13,0,243,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,76,0
    .db 14,0,1,0,237,255,189,255,13,0,243,255,6,0,1,0
    .db 0,0,5,0,217,255,39,0,249,255,0,0,0,0,77,0
    .db 208,7,1,0,236,255,189,255,7,0,243,255,6,0,1,0
    .db 0,0,254,255,216,255,60,0,6,0,0,0,0,0,78,0
    .db 12,0,1,0,236,255,189,255,7,0,243,255,0,0,0,0
    .db 0,0,224,255,186,255,224,255,186,255,0,0,0,0,79,0
    .db 14,0,1,0,244,255,195,255,16,0,248,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,80,0
    .db 208,7,1,0,244,255,195,255,16,0,248,255,6,0,0,0
    .db 0,0,11,0,206,255,43,0,243,255,0,0,0,0,81,0
    .db 208,7,1,0,244,255,195,255,16,0,248,255,0,0,0,0
    .db 0,0,234,255,190,255,234,255,190,255,0,0,0,0,82,0
    .db 50,0,1,0,243,255,174,255,20,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,83,0
    .db 16,0,1,0,239,255,169,255,9,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,84,0
    .db 100,0,1,0,232,255,169,255,2,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,85,0
    .db 16,0,1,0,239,255,169,255,9,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,86,0
    .db 20,0,0,0,214,255,192,255,214,255,192,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,87,0
    .db 20,0,0,0,214,255,192,255,214,255,192,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,88,0
    .db 20,0,0,0,214,255,192,255,214,255,192,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,89,0
    .db 20,0,0,0,214,255,192,255,214,255,192,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,90,0
    .db 10,0,0,0,149,255,53,255,149,255,53,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,91,0
    .db 10,0,0,0,149,255,53,255,149,255,53,255,20,0,1,0
    .db 1,0,218,255,148,255,42,0,2,0,0,0,0,0,92,0
    .db 10,0,0,0,149,255,53,255,149,255,53,255,20,0,1,0
    .db 1,0,218,255,148,255,42,0,2,0,0,0,0,0,93,0
    .db 10,0,0,0,149,255,53,255,149,255,53,255,20,0,1,0
    .db 1,0,208,255,148,255,52,0,2,0,0,0,0,0,94,0
    .db 10,0,0,0,149,255,53,255,149,255,53,255,20,0,1,0
    .db 1,0,208,255,148,255,52,0,2,0,0,0,0,0,95,0
    .db 10,0,0,0,149,255,53,255,149,255,53,255,20,0,1,0
    .db 1,0,198,255,148,255,62,0,2,0,0,0,0,0,96,0
    .db 10,0,0,0,149,255,53,255,149,255,53,255,20,0,1,0
    .db 1,0,198,255,148,255,62,0,2,0,0,0,0,0,97,0
    .db 10,0,0,0,149,255,53,255,149,255,53,255,0,0,1,0
    .db 1,0,149,255,53,255,149,255,53,255,0,0,0,0,98,0
    .db 10,0,0,0,149,255,53,255,149,255,53,255,0,0,1,0
    .db 1,0,149,255,53,255,149,255,53,255,0,0,0,0,99,0
    .db 10,0,0,0,192,255,178,255,192,255,178,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,100,0
    .db 10,0,0,0,192,255,178,255,192,255,178,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,101,0
    .db 10,0,0,0,192,255,178,255,192,255,178,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,102,0
    .db 10,0,0,0,192,255,178,255,192,255,178,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,103,0
    .db 10,0,0,0,192,255,178,255,192,255,178,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,104,0
    .db 10,0,0,0,192,255,178,255,192,255,178,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,105,0
    .db 10,0,0,0,192,255,178,255,192,255,178,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,106,0
    .db 10,0,0,0,214,255,192,255,214,255,192,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,107,0
    .db 10,0,0,0,214,255,192,255,214,255,192,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,108,0
    .db 10,0,0,0,214,255,192,255,214,255,192,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,109,0
    .db 10,0,0,0,214,255,192,255,214,255,192,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,110,0
    .db 14,0,1,0,239,255,160,255,12,0,253,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,111,0
    .db 14,0,1,0,239,255,160,255,12,0,253,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,112,0
    .db 14,0,1,0,239,255,160,255,12,0,253,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,113,0
    .db 14,0,1,0,239,255,160,255,12,0,253,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,114,0
    .db 14,0,1,0,239,255,160,255,12,0,253,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,115,0
    .db 14,0,1,0,239,255,160,255,12,0,253,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,116,0
    .db 14,0,1,0,239,255,160,255,12,0,253,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,117,0
    .db 14,0,1,0,239,255,160,255,12,0,253,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,118,0
    .db 14,0,1,0,239,255,160,255,12,0,253,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,119,0
    .db 14,0,1,0,239,255,160,255,12,0,253,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,120,0
    .db 0,0,6,0,48,163,34,0,0,0,0,0,0,0,0,0
    .db 1,0,6,0,240,163,34,0,0,0,0,0,0,0,0,0
    .db 2,0,9,0,176,164,34,0,0,0,0,0,0,0,0,0
    .db 3,0,5,0,208,165,34,0,0,0,0,0,0,0,0,0
    .db 4,0,9,0,112,166,34,0,0,0,0,0,0,0,0,0
    .db 5,0,7,0,144,167,34,0,0,0,0,0,0,0,0,0
    .db 6,0,1,0,112,168,34,0,0,0,0,0,0,0,0,0
    .db 7,0,3,0,144,168,34,0,0,0,0,0,0,0,0,0
    .db 8,0,12,0,240,168,34,0,0,0,0,0,0,0,0,0
    .db 9,0,7,0,112,170,34,1,0,0,0,0,0,0,0,0
    .db 10,0,11,0,80,171,34,0,0,0,0,0,0,0,0,0
    .db 11,0,4,0,176,172,34,0,0,0,0,0,0,0,0,0
    .db 12,0,3,0,48,173,34,0,0,0,0,0,0,0,0,0
    .db 13,0,1,0,144,173,34,0,0,0,0,0,0,0,0,0
    .db 14,0,3,0,176,173,34,0,0,0,0,0,0,0,0,0
    .db 15,0,4,0,16,174,34,0,0,0,0,0,0,0,0,0
    .db 16,0,9,0,144,174,34,0,0,0,0,0,0,0,0,0
    .db 17,0,11,0,176,175,34,0,0,0,0,0,0,0,0,0
    .db 18,0,10,0,16,177,34,1,0,0,0,0,0,0,0,0
    .db 2,0,0,0,233,255,228,255,233,255,228,255,15,0,1,0
    .db 0,0,240,255,232,255,15,0,0,0,0,0,0,0,0,0
    .db 80,0,0,0,241,255,230,255,241,255,230,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0
    .db 208,7,1,0,254,255,223,255,24,0,253,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0
    .db 88,2,1,0,244,255,220,255,10,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,0
    .db 40,0,1,0,244,255,220,255,10,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,4,0
    .db 40,0,1,0,244,255,220,255,10,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,5,0
    .db 40,0,1,0,244,255,220,255,10,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,6,0
    .db 40,0,1,0,244,255,220,255,10,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,7,0
    .db 40,0,1,0,244,255,220,255,10,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,8,0
    .db 40,0,1,0,244,255,220,255,10,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,9,0
    .db 40,0,1,0,244,255,220,255,10,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,10,0
    .db 40,0,1,0,244,255,220,255,10,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,11,0
    .db 40,0,1,0,244,255,220,255,10,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,12,0
    .db 6,0,0,0,243,255,230,255,243,255,230,255,15,0,1,0
    .db 0,0,244,255,231,255,14,0,1,0,0,0,0,0,13,0
    .db 6,0,0,0,243,255,230,255,243,255,230,255,15,0,1,0
    .db 0,0,244,255,231,255,14,0,1,0,0,0,0,0,14,0
    .db 6,0,0,0,243,255,230,255,243,255,230,255,15,0,1,0
    .db 0,0,244,255,231,255,14,0,1,0,0,0,0,0,15,0
    .db 6,0,0,0,243,255,230,255,243,255,230,255,15,0,1,0
    .db 0,0,244,255,231,255,14,0,1,0,0,0,0,0,16,0
    .db 6,0,0,0,243,255,230,255,243,255,230,255,15,0,1,0
    .db 0,0,244,255,231,255,14,0,1,0,0,0,0,0,17,0
    .db 6,0,0,0,243,255,230,255,243,255,230,255,15,0,1,0
    .db 0,0,244,255,231,255,14,0,1,0,0,0,0,0,18,0
    .db 6,0,0,0,243,255,230,255,243,255,230,255,15,0,1,0
    .db 0,0,244,255,231,255,14,0,1,0,0,0,0,0,19,0
    .db 6,0,0,0,243,255,230,255,243,255,230,255,15,0,1,0
    .db 0,0,244,255,231,255,14,0,1,0,0,0,0,0,20,0
    .db 50,0,1,0,248,255,222,255,12,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,21,0
    .db 2,0,1,0,240,255,232,255,15,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,22,0
    .db 2,0,0,0,233,255,228,255,233,255,228,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,23,0
    .db 80,0,0,0,240,255,228,255,240,255,228,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,24,0
    .db 14,0,1,0,246,255,221,255,11,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,25,0
    .db 14,0,1,0,246,255,221,255,11,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,26,0
    .db 14,0,1,0,246,255,221,255,11,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,27,0
    .db 14,0,1,0,246,255,221,255,11,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,28,0
    .db 14,0,1,0,246,255,221,255,11,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,29,0
    .db 14,0,1,0,246,255,221,255,11,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,30,0
    .db 0,0,1,0,128,179,34,0,0,0,0,0,0,0,0,0
    .db 1,0,1,0,160,179,34,0,0,0,0,0,0,0,0,0
    .db 2,0,1,0,192,179,34,0,0,0,0,0,0,0,0,0
    .db 3,0,10,0,224,179,34,1,0,0,0,0,0,0,0,0
    .db 4,0,8,0,32,181,34,1,0,0,0,0,0,0,0,0
    .db 5,0,1,0,32,182,34,0,0,0,0,0,0,0,0,0
    .db 6,0,1,0,64,182,34,0,0,0,0,0,0,0,0,0
    .db 7,0,1,0,96,182,34,0,0,0,0,0,0,0,0,0
    .db 8,0,1,0,128,182,34,0,0,0,0,0,0,0,0,0
    .db 9,0,6,0,160,182,34,1,0,0,0,0,0,0,0,0
.bank 35
.org $8000
    .db 8,0,1,0,242,255,161,255,16,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    .db 8,0,1,0,242,255,182,255,16,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0
    .db 8,0,1,0,242,255,193,255,16,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0
    .db 8,0,1,0,242,255,193,255,16,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,0
    .db 8,0,1,0,242,255,195,255,16,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,4,0
    .db 8,0,1,0,242,255,207,255,16,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,5,0
    .db 8,0,1,0,242,255,207,255,16,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,6,0
    .db 8,0,1,0,242,255,207,255,16,0,0,0,15,0,1,0
    .db 0,0,12,0,224,255,66,0,250,255,0,0,0,0,7,0
    .db 8,0,1,0,242,255,207,255,16,0,0,0,15,0,1,0
    .db 0,0,12,0,224,255,74,0,250,255,0,0,0,0,8,0
    .db 8,0,1,0,242,255,207,255,16,0,0,0,15,0,1,0
    .db 0,0,12,0,224,255,76,0,250,255,0,0,0,0,9,0
    .db 8,0,1,0,242,255,207,255,16,0,0,0,15,0,1,0
    .db 0,0,12,0,224,255,82,0,250,255,0,0,0,0,10,0
    .db 8,0,1,0,242,255,207,255,16,0,0,0,0,0,0,0
    .db 0,0,208,255,131,255,208,255,131,255,0,0,0,0,11,0
    .db 8,0,1,0,242,255,207,255,16,0,0,0,0,0,0,0
    .db 0,0,208,255,131,255,208,255,131,255,0,0,0,0,12,0
    .db 8,0,1,0,242,255,207,255,16,0,0,0,0,0,0,0
    .db 0,0,208,255,131,255,208,255,131,255,0,0,0,0,13,0
    .db 8,0,1,0,242,255,207,255,16,0,0,0,0,0,0,0
    .db 0,0,208,255,131,255,208,255,131,255,0,0,0,0,14,0
    .db 12,0,1,0,242,255,193,255,16,0,0,0,0,0,0,0
    .db 0,0,208,255,131,255,208,255,131,255,0,0,0,0,15,0
    .db 12,0,1,0,242,255,182,255,16,0,0,0,0,0,0,0
    .db 0,0,208,255,131,255,208,255,131,255,0,0,0,0,16,0
    .db 12,0,1,0,242,255,161,255,16,0,0,0,0,0,0,0
    .db 0,0,208,255,131,255,208,255,131,255,0,0,0,0,17,0
    .db 40,0,0,0,200,255,151,255,200,255,151,255,12,0,1,0
    .db 0,0,241,255,169,255,19,0,253,255,0,0,0,0,18,0
    .db 40,0,0,0,200,255,151,255,200,255,151,255,12,0,1,0
    .db 0,0,230,255,194,255,33,0,232,255,0,0,0,0,19,0
    .db 40,0,0,0,200,255,151,255,200,255,151,255,12,0,1,0
    .db 0,0,219,255,218,255,57,0,238,255,0,0,0,0,20,0
    .db 40,0,0,0,200,255,151,255,200,255,151,255,12,0,1,0
    .db 0,0,217,255,234,255,55,0,254,255,0,0,0,0,21,0
    .db 20,0,1,0,243,255,150,255,15,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,22,0
    .db 20,0,1,0,243,255,150,255,15,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,23,0
    .db 20,0,1,0,243,255,150,255,15,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,24,0
    .db 20,0,1,0,243,255,150,255,15,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,25,0
    .db 20,0,1,0,243,255,150,255,15,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,26,0
    .db 20,0,1,0,243,255,150,255,15,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,27,0
    .db 20,0,1,0,243,255,150,255,15,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,28,0
    .db 20,0,1,0,243,255,150,255,15,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,29,0
    .db 24,0,1,0,239,255,151,255,13,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,30,0
    .db 100,0,1,0,239,255,151,255,13,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,31,0
    .db 24,0,1,0,239,255,151,255,13,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,32,0
    .db 30,0,0,0,220,255,157,255,220,255,157,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,33,0
    .db 30,0,0,0,220,255,157,255,220,255,157,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,34,0
    .db 30,0,0,0,220,255,157,255,220,255,157,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,35,0
    .db 30,0,0,0,220,255,157,255,220,255,157,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,36,0
    .db 20,0,0,0,214,255,175,255,214,255,175,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,37,0
    .db 20,0,0,0,214,255,175,255,214,255,175,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,38,0
    .db 20,0,0,0,214,255,175,255,214,255,175,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,39,0
    .db 20,0,0,0,214,255,175,255,214,255,175,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,40,0
    .db 20,0,0,0,214,255,175,255,214,255,175,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,41,0
    .db 20,0,0,0,214,255,175,255,214,255,175,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,42,0
    .db 20,0,1,0,251,255,154,255,15,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,43,0
    .db 20,0,1,0,251,255,154,255,15,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,44,0
    .db 20,0,1,0,251,255,154,255,15,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,45,0
    .db 20,0,1,0,251,255,154,255,15,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,46,0
    .db 20,0,1,0,251,255,154,255,15,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,47,0
    .db 20,0,1,0,251,255,154,255,15,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,48,0
    .db 20,0,1,0,251,255,154,255,15,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,49,0
    .db 20,0,1,0,251,255,154,255,15,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,50,0
    .db 20,0,1,0,251,255,154,255,15,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,51,0
    .db 20,0,1,0,251,255,154,255,15,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,52,0
    .db 20,0,1,0,251,255,154,255,15,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,53,0
    .db 0,0,18,0,0,128,35,0,0,0,0,0,0,0,0,0
    .db 1,0,4,0,64,130,35,0,0,0,0,0,0,0,0,0
    .db 2,0,8,0,192,130,35,1,0,0,0,0,0,0,0,0
    .db 3,0,3,0,192,131,35,0,0,0,0,0,0,0,0,0
    .db 4,0,4,0,32,132,35,0,0,0,0,0,0,0,0,0
    .db 5,0,6,0,160,132,35,0,0,0,0,0,0,0,0,0
    .db 6,0,11,0,96,133,35,1,0,0,0,0,0,0,0,0
    .db 200,0,1,0,229,255,159,255,9,0,207,255,10,0,1,0
    .db 0,0,30,0,217,255,67,0,1,0,0,0,0,0,0,0
    .db 10,0,0,0,185,255,156,255,185,255,156,255,10,0,1,0
    .db 0,0,30,0,217,255,67,0,1,0,0,0,0,0,1,0
    .db 0,0,1,0,48,135,35,1,0,0,0,0,0,0,0,0
    .db 1,0,1,0,80,135,35,1,0,0,0,0,0,0,0,0
    .db 12,0,1,0,233,255,172,255,13,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    .db 12,0,1,0,231,255,172,255,11,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0
    .db 12,0,1,0,0,0,172,255,36,0,1,0,15,0,1,0
    .db 0,0,195,255,200,255,10,0,242,255,0,0,0,0,2,0
    .db 12,0,1,0,254,255,178,255,48,0,2,0,15,0,1,0
    .db 0,0,18,0,178,255,129,0,249,255,0,0,0,0,3,0
    .db 12,0,1,0,254,255,178,255,48,0,2,0,15,0,1,0
    .db 0,0,48,0,175,255,132,0,190,255,0,0,0,0,4,0
    .db 12,0,1,0,254,255,178,255,48,0,2,0,15,0,1,0
    .db 0,0,22,0,144,255,83,0,189,255,0,0,0,0,5,0
    .db 12,0,1,0,254,255,178,255,48,0,2,0,10,0,0,0
    .db 0,0,204,255,146,255,34,0,189,255,0,0,0,0,6,0
    .db 12,0,1,0,254,255,178,255,48,0,2,0,6,0,0,0
    .db 0,0,206,255,151,255,245,255,191,255,0,0,0,0,7,0
    .db 12,0,1,0,254,255,178,255,48,0,2,0,6,0,0,0
    .db 0,0,206,255,151,255,245,255,191,255,0,0,0,0,8,0
    .db 40,0,0,0,190,255,153,255,190,255,153,255,12,0,1,0
    .db 0,0,237,255,169,255,31,0,254,255,0,0,0,0,9,0
    .db 40,0,0,0,190,255,153,255,190,255,153,255,12,0,1,0
    .db 0,0,223,255,173,255,29,0,247,255,0,0,0,0,10,0
    .db 40,0,0,0,190,255,153,255,190,255,153,255,12,0,1,0
    .db 0,0,208,255,216,255,6,0,249,255,0,0,0,0,11,0
    .db 40,0,0,0,190,255,153,255,190,255,153,255,12,0,1,0
    .db 0,0,207,255,240,255,43,0,7,0,0,0,0,0,12,0
    .db 20,0,1,0,238,255,167,255,23,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,13,0
    .db 20,0,1,0,238,255,167,255,23,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,14,0
    .db 20,0,1,0,238,255,167,255,23,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,15,0
    .db 20,0,1,0,238,255,167,255,23,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,16,0
    .db 20,0,1,0,238,255,167,255,23,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,17,0
    .db 20,0,1,0,238,255,167,255,23,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,18,0
    .db 20,0,1,0,238,255,167,255,23,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,19,0
    .db 20,0,1,0,238,255,167,255,23,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,20,0
    .db 20,0,1,0,238,255,167,255,23,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,21,0
    .db 12,0,1,0,230,255,161,255,9,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,22,0
    .db 12,0,1,0,230,255,161,255,9,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,23,0
    .db 92,0,1,0,230,255,161,255,9,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,24,0
    .db 20,0,1,0,230,255,161,255,9,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,25,0
    .db 20,0,1,0,230,255,161,255,9,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,26,0
    .db 30,0,0,0,203,255,176,255,203,255,176,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,27,0
    .db 30,0,0,0,203,255,176,255,203,255,176,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,28,0
    .db 30,0,0,0,203,255,176,255,203,255,176,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,29,0
    .db 30,0,0,0,203,255,176,255,203,255,176,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,30,0
    .db 30,0,0,0,203,255,176,255,203,255,176,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,31,0
    .db 20,0,1,0,240,255,157,255,20,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,32,0
    .db 20,0,1,0,240,255,157,255,20,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,33,0
    .db 20,0,1,0,240,255,157,255,20,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,34,0
    .db 20,0,1,0,240,255,157,255,20,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,35,0
    .db 20,0,1,0,240,255,157,255,20,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,36,0
    .db 20,0,1,0,240,255,157,255,20,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,37,0
    .db 0,0,9,0,144,135,35,0,0,0,0,0,0,0,0,0
    .db 1,0,4,0,176,136,35,0,0,0,0,0,0,0,0,0
    .db 2,0,9,0,48,137,35,1,0,0,0,0,0,0,0,0
    .db 3,0,5,0,80,138,35,0,0,0,0,0,0,0,0,0
    .db 4,0,5,0,240,138,35,0,0,0,0,0,0,0,0,0
    .db 5,0,6,0,144,139,35,1,0,0,0,0,0,0,0,0
    .db 14,0,1,0,248,255,171,255,20,0,255,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    .db 14,0,1,0,248,255,171,255,20,0,255,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0
    .db 14,0,1,0,248,255,171,255,20,0,255,255,10,0,0,0
    .db 0,0,22,0,172,255,68,0,185,255,0,0,0,0,2,0
    .db 14,0,1,0,248,255,171,255,20,0,255,255,10,0,0,0
    .db 0,0,22,0,172,255,68,0,185,255,0,0,0,0,3,0
    .db 14,0,1,0,248,255,171,255,20,0,255,255,0,0,0,0
    .db 0,0,223,255,158,255,223,255,158,255,0,0,0,0,4,0
    .db 14,0,1,0,248,255,171,255,20,0,255,255,0,0,0,0
    .db 0,0,223,255,158,255,223,255,158,255,0,0,0,0,5,0
    .db 40,0,0,0,198,255,174,255,198,255,174,255,15,0,1,0
    .db 0,0,237,255,181,255,11,0,238,255,0,0,0,0,6,0
    .db 40,0,0,0,198,255,174,255,198,255,174,255,15,0,1,0
    .db 0,0,214,255,210,255,27,0,236,255,0,0,0,0,7,0
    .db 40,0,0,0,198,255,174,255,198,255,174,255,15,0,1,0
    .db 0,0,208,255,221,255,21,0,247,255,0,0,0,0,8,0
    .db 40,0,0,0,198,255,174,255,198,255,174,255,15,0,1,0
    .db 0,0,211,255,233,255,24,0,3,0,0,0,0,0,9,0
    .db 20,0,1,0,243,255,175,255,19,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,10,0
    .db 20,0,1,0,243,255,175,255,19,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,11,0
    .db 20,0,1,0,243,255,175,255,19,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,12,0
    .db 20,0,1,0,243,255,175,255,19,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,13,0
    .db 20,0,1,0,243,255,175,255,19,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,14,0
    .db 20,0,1,0,243,255,175,255,19,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,15,0
    .db 14,0,1,0,246,255,140,255,28,0,232,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,16,0
    .db 14,0,1,0,246,255,140,255,28,0,232,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,17,0
    .db 14,0,1,0,246,255,140,255,28,0,232,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,18,0
    .db 14,0,1,0,246,255,145,255,30,0,219,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,19,0
    .db 14,0,1,0,246,255,148,255,32,0,219,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,20,0
    .db 20,0,1,0,242,255,148,255,28,0,219,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,21,0
    .db 40,0,1,0,242,255,148,255,28,0,219,255,10,0,1,0
    .db 0,0,22,0,167,255,58,0,195,255,0,0,0,0,22,0
    .db 14,0,1,0,246,255,148,255,32,0,219,255,10,0,1,0
    .db 0,0,22,0,167,255,58,0,195,255,0,0,0,0,23,0
    .db 14,0,1,0,246,255,145,255,30,0,219,255,10,0,1,0
    .db 0,0,22,0,167,255,58,0,195,255,0,0,0,0,24,0
    .db 14,0,1,0,246,255,140,255,28,0,232,255,10,0,1,0
    .db 0,0,22,0,167,255,58,0,195,255,0,0,0,0,25,0
    .db 14,0,1,0,246,255,140,255,28,0,232,255,10,0,1,0
    .db 0,0,22,0,167,255,58,0,195,255,0,0,0,0,26,0
    .db 14,0,1,0,246,255,140,255,28,0,232,255,10,0,1,0
    .db 0,0,22,0,167,255,58,0,195,255,0,0,0,0,27,0
    .db 14,0,1,0,246,255,140,255,28,0,232,255,10,0,1,0
    .db 0,0,22,0,167,255,58,0,195,255,0,0,0,0,28,0
    .db 14,0,1,0,246,255,140,255,28,0,232,255,10,0,1,0
    .db 0,0,22,0,167,255,58,0,195,255,0,0,0,0,29,0
    .db 14,0,1,0,246,255,140,255,28,0,232,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,30,0
    .db 14,0,1,0,246,255,140,255,28,0,232,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,31,0
    .db 14,0,1,0,246,255,140,255,28,0,232,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,32,0
    .db 14,0,1,0,246,255,145,255,30,0,219,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,33,0
    .db 14,0,1,0,246,255,148,255,32,0,219,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,34,0
    .db 20,0,1,0,242,255,148,255,28,0,219,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,35,0
    .db 40,0,1,0,242,255,148,255,28,0,219,255,10,0,1,0
    .db 0,0,22,0,167,255,58,0,195,255,0,0,0,0,36,0
    .db 14,0,1,0,246,255,148,255,32,0,219,255,10,0,1,0
    .db 0,0,22,0,167,255,58,0,195,255,0,0,0,0,37,0
    .db 14,0,1,0,246,255,145,255,30,0,219,255,10,0,1,0
    .db 0,0,22,0,167,255,58,0,195,255,0,0,0,0,38,0
    .db 14,0,1,0,246,255,140,255,28,0,232,255,10,0,1,0
    .db 0,0,22,0,167,255,58,0,195,255,0,0,0,0,39,0
    .db 14,0,1,0,246,255,140,255,28,0,232,255,10,0,1,0
    .db 0,0,22,0,167,255,58,0,195,255,0,0,0,0,40,0
    .db 14,0,1,0,246,255,140,255,28,0,232,255,10,0,1,0
    .db 0,0,22,0,167,255,58,0,195,255,0,0,0,0,41,0
    .db 14,0,1,0,246,255,140,255,28,0,232,255,10,0,1,0
    .db 0,0,22,0,167,255,58,0,195,255,0,0,0,0,42,0
    .db 14,0,1,0,246,255,140,255,28,0,232,255,10,0,1,0
    .db 0,0,22,0,167,255,58,0,195,255,0,0,0,0,43,0
    .db 24,0,1,0,234,255,174,255,18,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,44,0
    .db 90,0,1,0,234,255,174,255,18,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,45,0
    .db 24,0,1,0,234,255,174,255,18,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,46,0
    .db 30,0,0,0,215,255,173,255,215,255,173,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,47,0
    .db 30,0,0,0,215,255,173,255,215,255,173,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,48,0
    .db 30,0,0,0,215,255,173,255,215,255,173,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,49,0
    .db 14,0,1,0,243,255,169,255,15,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,50,0
    .db 14,0,1,0,243,255,169,255,15,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,51,0
    .db 14,0,1,0,243,255,169,255,15,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,52,0
    .db 14,0,1,0,243,255,169,255,15,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,53,0
    .db 14,0,1,0,243,255,169,255,15,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,54,0
    .db 14,0,1,0,243,255,169,255,15,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,55,0
    .db 0,0,6,0,176,140,35,0,0,0,0,0,0,0,0,0
    .db 1,0,4,0,112,141,35,0,0,0,0,0,0,0,0,0
    .db 2,0,6,0,240,141,35,1,0,0,0,0,0,0,0,0
    .db 3,0,14,0,176,142,35,0,0,0,0,0,0,0,0,0
    .db 4,0,14,0,112,144,35,0,0,0,0,0,0,0,0,0
    .db 5,0,3,0,48,146,35,0,0,0,0,0,0,0,0,0
    .db 6,0,3,0,144,146,35,0,0,0,0,0,0,0,0,0
    .db 7,0,6,0,240,146,35,1,0,0,0,0,0,0,0,0
    .db 8,0,1,0,238,255,148,255,24,0,255,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    .db 8,0,1,0,238,255,148,255,24,0,255,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0
    .db 8,0,1,0,238,255,148,255,24,0,255,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0
    .db 8,0,1,0,238,255,148,255,24,0,255,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,0
    .db 8,0,1,0,2,0,148,255,44,0,255,255,20,0,1,0
    .db 0,0,41,0,161,255,98,0,198,255,0,0,0,0,4,0
    .db 8,0,1,0,2,0,148,255,44,0,255,255,20,0,1,0
    .db 0,0,41,0,161,255,98,0,198,255,0,0,0,0,5,0
    .db 8,0,1,0,2,0,148,255,44,0,255,255,20,0,1,0
    .db 0,0,41,0,161,255,98,0,198,255,0,0,0,0,6,0
    .db 8,0,1,0,248,255,148,255,40,0,255,255,0,0,0,0
    .db 0,0,208,255,141,255,208,255,141,255,0,0,0,0,7,0
    .db 8,0,1,0,248,255,148,255,40,0,255,255,0,0,0,0
    .db 0,0,208,255,141,255,208,255,141,255,0,0,0,0,8,0
    .db 8,0,1,0,238,255,148,255,24,0,255,255,0,0,0,0
    .db 0,0,208,255,141,255,208,255,141,255,0,0,0,0,9,0
    .db 20,0,0,0,178,255,139,255,178,255,139,255,15,0,1,0
    .db 0,0,237,255,175,255,6,0,235,255,0,0,0,0,10,0
    .db 20,0,0,0,178,255,139,255,178,255,139,255,15,0,1,0
    .db 0,0,236,255,182,255,5,0,213,255,0,0,0,0,11,0
    .db 20,0,0,0,178,255,139,255,178,255,139,255,15,0,1,0
    .db 0,0,224,255,191,255,11,0,215,255,0,0,0,0,12,0
    .db 20,0,0,0,178,255,139,255,178,255,139,255,15,0,1,0
    .db 0,0,216,255,203,255,27,0,217,255,0,0,0,0,13,0
    .db 24,0,1,0,239,255,153,255,22,0,252,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,14,0
    .db 24,0,1,0,239,255,153,255,22,0,252,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,15,0
    .db 24,0,1,0,239,255,153,255,22,0,252,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,16,0
    .db 24,0,1,0,239,255,153,255,22,0,252,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,17,0
    .db 24,0,1,0,239,255,153,255,22,0,252,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,18,0
    .db 24,0,1,0,239,255,153,255,22,0,252,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,19,0
    .db 24,0,1,0,239,255,153,255,22,0,252,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,20,0
    .db 6,0,1,0,231,255,142,255,18,0,6,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,21,0
    .db 6,0,1,0,231,255,142,255,18,0,6,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,22,0
    .db 6,0,1,0,231,255,142,255,18,0,6,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,23,0
    .db 20,0,0,0,194,255,152,255,194,255,152,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,24,0
    .db 20,0,0,0,194,255,152,255,194,255,152,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,25,0
    .db 20,0,0,0,194,255,152,255,194,255,152,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,26,0
    .db 20,0,0,0,194,255,152,255,194,255,152,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,27,0
    .db 20,0,0,0,194,255,152,255,194,255,152,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,28,0
    .db 20,0,0,0,194,255,152,255,194,255,152,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,29,0
    .db 20,0,0,0,194,255,152,255,194,255,152,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,30,0
    .db 8,0,0,0,187,255,90,255,187,255,90,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,31,0
    .db 8,0,0,0,187,255,90,255,187,255,90,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,32,0
    .db 8,0,0,0,187,255,90,255,187,255,90,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,33,0
    .db 8,0,0,0,187,255,90,255,187,255,90,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,34,0
    .db 8,0,0,0,187,255,90,255,187,255,90,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,35,0
    .db 8,0,0,0,187,255,90,255,187,255,90,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,36,0
    .db 8,0,0,0,187,255,90,255,187,255,90,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,37,0
    .db 8,0,0,0,187,255,90,255,187,255,90,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,38,0
    .db 8,0,0,0,187,255,90,255,187,255,90,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,39,0
    .db 8,0,0,0,187,255,90,255,187,255,90,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,40,0
    .db 10,0,0,0,187,255,90,255,187,255,90,255,12,0,1,0
    .db 0,0,207,255,125,255,47,0,3,0,0,0,0,0,41,0
    .db 10,0,0,0,187,255,90,255,187,255,90,255,12,0,1,0
    .db 0,0,197,255,125,255,56,0,8,0,0,0,0,0,42,0
    .db 10,0,0,0,187,255,90,255,187,255,90,255,12,0,1,0
    .db 0,0,197,255,125,255,56,0,8,0,0,0,0,0,43,0
    .db 10,0,0,0,187,255,90,255,187,255,90,255,12,0,1,0
    .db 0,0,197,255,125,255,56,0,8,0,0,0,0,0,44,0
    .db 10,0,0,0,187,255,90,255,187,255,90,255,12,0,1,0
    .db 0,0,197,255,125,255,56,0,8,0,0,0,0,0,45,0
    .db 10,0,0,0,187,255,90,255,187,255,90,255,0,0,0,0
    .db 0,0,187,255,90,255,187,255,90,255,0,0,0,0,46,0
    .db 10,0,0,0,187,255,90,255,187,255,90,255,0,0,0,0
    .db 0,0,187,255,90,255,187,255,90,255,0,0,0,0,47,0
    .db 10,0,0,0,187,255,90,255,187,255,90,255,0,0,0,0
    .db 0,0,187,255,90,255,187,255,90,255,0,0,0,0,48,0
    .db 10,0,0,0,187,255,90,255,187,255,90,255,0,0,0,0
    .db 0,0,187,255,90,255,187,255,90,255,0,0,0,0,49,0
    .db 12,0,1,0,231,255,159,255,19,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,50,0
    .db 12,0,1,0,244,255,159,255,32,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,51,0
    .db 12,0,1,0,244,255,159,255,32,0,0,0,15,0,0,0
    .db 0,0,22,0,156,255,55,0,194,255,0,0,0,0,52,0
    .db 12,0,1,0,252,255,137,255,28,0,254,255,15,0,1,0
    .db 0,0,230,255,113,255,10,0,183,255,0,0,0,0,53,0
    .db 40,0,1,0,252,255,137,255,28,0,254,255,15,0,1,0
    .db 0,0,230,255,113,255,10,0,183,255,0,0,0,0,54,0
    .db 20,0,1,0,252,255,137,255,28,0,254,255,15,0,1,0
    .db 0,0,230,255,113,255,10,0,183,255,0,0,0,0,55,0
    .db 20,0,1,0,252,255,137,255,28,0,254,255,15,0,1,0
    .db 0,0,230,255,113,255,10,0,183,255,0,0,0,0,56,0
    .db 20,0,1,0,240,255,145,255,17,0,3,0,0,0,0,0
    .db 0,0,203,255,113,255,203,255,113,255,0,0,0,0,57,0
    .db 16,0,1,0,246,255,148,255,26,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,58,0
    .db 16,0,1,0,246,255,148,255,26,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,59,0
    .db 16,0,1,0,246,255,148,255,26,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,60,0
    .db 16,0,1,0,246,255,148,255,26,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,61,0
    .db 16,0,1,0,246,255,148,255,26,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,62,0
    .db 16,0,1,0,246,255,148,255,26,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,63,0
    .db 16,0,1,0,246,255,148,255,26,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,64,0
    .db 16,0,1,0,246,255,148,255,26,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,65,0
    .db 16,0,1,0,246,255,148,255,26,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,66,0
    .db 16,0,1,0,246,255,148,255,26,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,67,0
    .db 16,0,1,0,246,255,148,255,26,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,68,0
    .db 16,0,1,0,246,255,148,255,26,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,69,0
    .db 0,0,10,0,48,148,35,0,0,0,0,0,0,0,0,0
    .db 1,0,4,0,112,149,35,0,0,0,0,0,0,0,0,0
    .db 2,0,7,0,240,149,35,1,0,0,0,0,0,0,0,0
    .db 3,0,3,0,208,150,35,0,0,0,0,0,0,0,0,0
    .db 4,0,7,0,48,151,35,0,0,0,0,0,0,0,0,0
    .db 5,0,19,0,16,152,35,0,0,0,0,0,0,0,0,0
    .db 6,0,8,0,112,154,35,0,0,0,0,0,0,0,0,0
    .db 7,0,12,0,112,155,35,1,0,0,0,0,0,0,0,0
    .db 14,0,1,0,234,255,150,255,16,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    .db 14,0,1,0,234,255,155,255,16,0,2,0,10,0,0,0
    .db 0,0,0,0,180,255,33,0,216,255,0,0,0,0,1,0
    .db 30,0,1,0,224,255,155,255,6,0,2,0,10,0,0,0
    .db 0,0,3,0,176,255,72,0,195,255,0,0,0,0,2,0
    .db 14,0,1,0,234,255,155,255,16,0,2,0,0,0,0,0
    .db 0,0,209,255,146,255,209,255,146,255,0,0,0,0,3,0
    .db 14,0,1,0,234,255,150,255,16,0,2,0,0,0,0,0
    .db 0,0,209,255,146,255,209,255,146,255,0,0,0,0,4,0
    .db 40,0,0,0,202,255,161,255,202,255,161,255,12,0,1,0
    .db 0,0,234,255,168,255,50,0,250,255,0,0,0,0,5,0
    .db 40,0,0,0,202,255,161,255,202,255,161,255,12,0,1,0
    .db 0,0,220,255,192,255,57,0,249,255,0,0,0,0,6,0
    .db 40,0,0,0,202,255,161,255,202,255,161,255,12,0,1,0
    .db 0,0,216,255,196,255,55,0,246,255,0,0,0,0,7,0
    .db 40,0,0,0,202,255,161,255,202,255,161,255,12,0,1,0
    .db 0,0,207,255,238,255,64,0,255,255,0,0,0,0,8,0
    .db 40,0,1,0,245,255,143,255,18,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,9,0
    .db 40,0,1,0,245,255,143,255,18,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,10,0
    .db 40,0,1,0,245,255,143,255,18,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,11,0
    .db 40,0,1,0,245,255,143,255,18,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,12,0
    .db 40,0,1,0,245,255,143,255,18,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,13,0
    .db 40,0,1,0,245,255,143,255,18,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,14,0
    .db 20,0,1,0,243,255,142,255,21,0,6,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,15,0
    .db 20,0,1,0,247,255,152,255,21,0,237,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,16,0
    .db 20,0,1,0,246,255,163,255,24,0,223,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,17,0
    .db 20,0,1,0,246,255,163,255,24,0,223,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,18,0
    .db 20,0,1,0,246,255,163,255,24,0,223,255,12,0,1,0
    .db 0,0,16,0,196,255,83,0,231,255,0,0,0,0,19,0
    .db 20,0,1,0,240,255,148,255,15,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,20,0
    .db 50,0,1,0,223,255,156,255,11,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,21,0
    .db 20,0,1,0,240,255,148,255,15,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,22,0
    .db 30,0,0,0,202,255,141,255,202,255,141,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,23,0
    .db 30,0,0,0,202,255,141,255,202,255,141,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,24,0
    .db 30,0,0,0,202,255,141,255,202,255,141,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,25,0
    .db 30,0,0,0,202,255,141,255,202,255,141,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,26,0
    .db 30,0,0,0,202,255,141,255,202,255,141,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,27,0
    .db 30,0,0,0,202,255,141,255,202,255,141,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,28,0
    .db 18,0,1,0,239,255,141,255,21,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,29,0
    .db 18,0,1,0,239,255,141,255,21,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,30,0
    .db 18,0,1,0,239,255,141,255,21,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,31,0
    .db 18,0,1,0,239,255,141,255,21,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,32,0
    .db 18,0,1,0,239,255,141,255,21,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,33,0
    .db 18,0,1,0,239,255,141,255,21,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,34,0
    .db 18,0,1,0,239,255,141,255,21,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,35,0
    .db 18,0,1,0,239,255,141,255,21,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,36,0
    .db 0,0,5,0,112,157,35,0,0,0,0,0,0,0,0,0
    .db 1,0,4,0,16,158,35,0,0,0,0,0,0,0,0,0
    .db 2,0,6,0,144,158,35,1,0,0,0,0,0,0,0,0
    .db 3,0,5,0,80,159,35,0,0,0,0,0,0,0,0,0
    .db 4,0,3,0,240,159,35,0,0,0,0,0,0,0,0,0
    .db 5,0,6,0,80,160,35,0,0,0,0,0,0,0,0,0
    .db 6,0,8,0,16,161,35,1,0,0,0,0,0,0,0,0
    .db 10,0,1,0,9,0,162,255,34,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    .db 10,0,1,0,9,0,162,255,34,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0
    .db 10,0,1,0,9,0,162,255,34,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0
    .db 10,0,1,0,9,0,162,255,34,0,1,0,18,0,0,0
    .db 0,0,45,0,172,255,107,0,201,255,0,0,0,0,3,0
    .db 10,0,1,0,18,0,150,255,43,0,1,0,18,0,0,0
    .db 0,0,45,0,172,255,107,0,201,255,0,0,0,0,4,0
    .db 10,0,1,0,18,0,150,255,43,0,1,0,0,0,0,0
    .db 0,0,218,255,139,255,218,255,139,255,0,0,0,0,5,0
    .db 10,0,1,0,28,0,154,255,53,0,1,0,0,0,0,0
    .db 0,0,218,255,139,255,218,255,139,255,0,0,0,0,6,0
    .db 10,0,1,0,28,0,154,255,53,0,1,0,0,0,0,0
    .db 0,0,218,255,139,255,218,255,139,255,0,0,0,0,7,0
    .db 10,0,1,0,28,0,154,255,53,0,1,0,0,0,0,0
    .db 0,0,218,255,139,255,218,255,139,255,0,0,0,0,8,0
    .db 10,0,1,0,12,0,154,255,37,0,1,0,0,0,0,0
    .db 0,0,218,255,139,255,218,255,139,255,0,0,0,0,9,0
    .db 10,0,1,0,0,0,154,255,25,0,1,0,0,0,0,0
    .db 0,0,218,255,139,255,218,255,139,255,0,0,0,0,10,0
    .db 20,0,0,0,187,255,162,255,187,255,162,255,15,0,1,0
    .db 0,0,238,255,171,255,26,0,220,255,0,0,0,0,11,0
    .db 20,0,0,0,187,255,162,255,187,255,162,255,15,0,1,0
    .db 0,0,229,255,179,255,27,0,213,255,0,0,0,0,12,0
    .db 20,0,0,0,187,255,162,255,187,255,162,255,15,0,1,0
    .db 0,0,219,255,212,255,41,0,242,255,0,0,0,0,13,0
    .db 20,0,0,0,187,255,162,255,187,255,162,255,15,0,1,0
    .db 0,0,217,255,238,255,39,0,6,0,0,0,0,0,14,0
    .db 24,0,1,0,255,255,155,255,20,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,15,0
    .db 24,0,1,0,255,255,155,255,20,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,16,0
    .db 24,0,1,0,255,255,155,255,20,0,1,0,2,0,0,0
    .db 0,0,28,0,175,255,61,0,208,255,0,0,0,0,17,0
    .db 24,0,1,0,255,255,155,255,20,0,1,0,0,0,0,0
    .db 0,0,216,255,135,255,216,255,135,255,0,0,0,0,18,0
    .db 24,0,1,0,255,255,155,255,20,0,1,0,0,0,0,0
    .db 0,0,216,255,135,255,216,255,135,255,0,0,0,0,19,0
    .db 24,0,1,0,255,255,155,255,20,0,1,0,0,0,0,0
    .db 0,0,216,255,135,255,216,255,135,255,0,0,0,0,20,0
    .db 24,0,1,0,255,255,155,255,20,0,1,0,4,0,0,0
    .db 0,0,28,0,175,255,61,0,208,255,0,0,0,0,21,0
    .db 24,0,1,0,255,255,155,255,20,0,1,0,0,0,0,0
    .db 0,0,216,255,135,255,216,255,135,255,0,0,0,0,22,0
    .db 24,0,1,0,255,255,155,255,20,0,1,0,0,0,0,0
    .db 0,0,216,255,135,255,216,255,135,255,0,0,0,0,23,0
    .db 24,0,1,0,255,255,155,255,20,0,1,0,0,0,0,0
    .db 0,0,216,255,135,255,216,255,135,255,0,0,0,0,24,0
    .db 24,0,1,0,255,255,155,255,20,0,1,0,8,0,0,0
    .db 0,0,28,0,175,255,61,0,208,255,0,0,0,0,25,0
    .db 24,0,1,0,255,255,155,255,20,0,1,0,0,0,0,0
    .db 0,0,216,255,135,255,216,255,135,255,0,0,0,0,26,0
    .db 24,0,1,0,255,255,155,255,20,0,1,0,0,0,0,0
    .db 0,0,216,255,135,255,216,255,135,255,0,0,0,0,27,0
    .db 40,0,1,0,255,255,155,255,20,0,1,0,0,0,0,0
    .db 0,0,216,255,135,255,216,255,135,255,0,0,0,0,28,0
    .db 24,0,1,0,4,0,148,255,32,0,2,0,12,0,1,0
    .db 0,0,23,0,167,255,56,0,200,255,0,0,0,0,29,0
    .db 24,0,1,0,4,0,148,255,32,0,2,0,12,0,1,0
    .db 0,0,23,0,167,255,56,0,200,255,0,0,0,0,30,0
    .db 24,0,1,0,252,255,148,255,24,0,2,0,0,0,0,0
    .db 0,0,216,255,135,255,216,255,135,255,0,0,0,0,31,0
    .db 20,0,1,0,241,255,156,255,11,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,32,0
    .db 20,0,1,0,241,255,156,255,11,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,33,0
    .db 20,0,1,0,241,255,156,255,11,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,34,0
    .db 20,0,1,0,241,255,156,255,11,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,35,0
    .db 20,0,1,0,241,255,156,255,11,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,36,0
    .db 20,0,1,0,241,255,156,255,11,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,37,0
    .db 20,0,1,0,241,255,156,255,11,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,38,0
    .db 20,0,1,0,241,255,156,255,11,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,39,0
    .db 20,0,1,0,241,255,156,255,11,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,40,0
    .db 20,0,1,0,241,255,156,255,11,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,41,0
    .db 10,0,1,0,233,255,158,255,16,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,42,0
    .db 10,0,1,0,233,255,158,255,16,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,43,0
    .db 80,0,1,0,233,255,158,255,16,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,44,0
    .db 10,0,1,0,233,255,158,255,16,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,45,0
    .db 10,0,1,0,233,255,158,255,16,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,46,0
    .db 40,0,0,0,194,255,159,255,194,255,159,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,47,0
    .db 40,0,0,0,194,255,159,255,194,255,159,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,48,0
    .db 40,0,0,0,194,255,159,255,194,255,159,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,49,0
    .db 40,0,0,0,194,255,159,255,194,255,159,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,50,0
    .db 40,0,0,0,194,255,159,255,194,255,159,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,51,0
    .db 20,0,1,0,240,255,153,255,14,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,52,0
    .db 20,0,1,0,240,255,153,255,14,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,53,0
    .db 20,0,1,0,240,255,153,255,14,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,54,0
    .db 20,0,1,0,240,255,153,255,14,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,55,0
    .db 20,0,1,0,240,255,153,255,14,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,56,0
    .db 20,0,1,0,240,255,153,255,14,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,57,0
    .db 20,0,1,0,240,255,153,255,14,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,58,0
    .db 0,0,11,0,128,162,35,0,0,0,0,0,0,0,0,0
    .db 1,0,4,0,224,163,35,0,0,0,0,0,0,0,0,0
    .db 2,0,17,0,96,164,35,0,0,0,0,0,0,0,0,0
    .db 3,0,10,0,128,166,35,1,0,0,0,0,0,0,0,0
    .db 4,0,5,0,192,167,35,0,0,0,0,0,0,0,0,0
    .db 5,0,5,0,96,168,35,0,0,0,0,0,0,0,0,0
    .db 6,0,7,0,0,169,35,1,0,0,0,0,0,0,0,0
    .db 14,0,1,0,246,255,161,255,21,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    .db 14,0,1,0,246,255,161,255,21,0,0,0,12,0,0,0
    .db 0,0,20,0,160,255,63,0,175,255,0,0,0,0,1,0
    .db 14,0,1,0,246,255,161,255,21,0,0,0,12,0,0,0
    .db 0,0,20,0,160,255,63,0,175,255,0,0,0,0,2,0
    .db 14,0,1,0,246,255,161,255,21,0,0,0,0,0,0,0
    .db 0,0,219,255,79,255,219,255,79,255,0,0,0,0,3,0
    .db 14,0,1,0,246,255,161,255,21,0,0,0,0,0,0,0
    .db 0,0,219,255,79,255,219,255,79,255,0,0,0,0,4,0
    .db 14,0,1,0,246,255,161,255,21,0,0,0,0,0,0,0
    .db 0,0,219,255,79,255,219,255,79,255,0,0,0,0,5,0
    .db 40,0,0,0,211,255,86,255,211,255,86,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,6,0
    .db 40,0,0,0,211,255,86,255,211,255,86,255,15,0,1,0
    .db 0,0,226,255,246,255,53,0,10,0,0,0,0,0,7,0
    .db 60,0,1,0,228,255,156,255,23,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,8,0
    .db 60,0,1,0,228,255,156,255,23,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,9,0
    .db 60,0,1,0,228,255,156,255,23,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,10,0
    .db 144,1,1,0,228,255,156,255,23,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,11,0
    .db 20,0,1,0,237,255,156,255,32,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,12,0
    .db 60,0,1,0,237,255,156,255,32,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,13,0
    .db 20,0,1,0,237,255,156,255,32,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,14,0
    .db 80,0,0,0,215,255,80,255,215,255,80,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,15,0
    .db 14,0,1,0,245,255,161,255,16,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,16,0
    .db 14,0,1,0,245,255,161,255,16,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,17,0
    .db 14,0,1,0,245,255,161,255,16,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,18,0
    .db 14,0,1,0,245,255,161,255,16,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,19,0
    .db 14,0,1,0,245,255,161,255,16,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,20,0
    .db 14,0,1,0,245,255,161,255,16,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,21,0
    .db 14,0,1,0,245,255,161,255,16,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,22,0
    .db 14,0,1,0,245,255,161,255,16,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,23,0
    .db 14,0,1,0,245,255,161,255,16,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,24,0
    .db 14,0,1,0,245,255,161,255,16,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,25,0
    .db 14,0,1,0,245,255,161,255,16,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,26,0
    .db 14,0,1,0,245,255,161,255,16,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,27,0
    .db 0,0,6,0,80,170,35,0,0,0,0,0,0,0,0,0
    .db 1,0,2,0,16,171,35,0,0,0,0,0,0,0,0,0
    .db 2,0,4,0,80,171,35,1,0,0,0,0,0,0,0,0
    .db 3,0,3,0,208,171,35,0,0,0,0,0,0,0,0,0
    .db 4,0,1,0,48,172,35,0,0,0,0,0,0,0,0,0
    .db 5,0,12,0,80,172,35,1,0,0,0,0,0,0,0,0
    .db 8,0,0,0,219,255,146,255,219,255,146,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    .db 8,0,0,0,219,255,146,255,219,255,146,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0
    .db 8,0,0,0,219,255,146,255,219,255,146,255,20,0,0,0
    .db 0,0,236,255,171,255,43,0,181,255,0,0,0,0,2,0
    .db 8,0,0,0,219,255,146,255,219,255,146,255,20,0,0,0
    .db 0,0,236,255,171,255,43,0,181,255,0,0,0,0,3,0
    .db 8,0,1,0,249,255,180,255,28,0,2,0,20,0,0,0
    .db 0,0,236,255,171,255,43,0,181,255,0,0,0,0,4,0
    .db 8,0,1,0,249,255,180,255,28,0,2,0,20,0,0,0
    .db 0,0,236,255,171,255,43,0,181,255,0,0,0,0,5,0
    .db 8,0,1,0,249,255,180,255,28,0,2,0,20,0,0,0
    .db 0,0,236,255,171,255,43,0,181,255,0,0,0,0,6,0
    .db 8,0,1,0,249,255,180,255,28,0,2,0,20,0,0,0
    .db 0,0,236,255,171,255,43,0,181,255,0,0,0,0,7,0
    .db 8,0,1,0,249,255,180,255,28,0,2,0,20,0,0,0
    .db 0,0,236,255,171,255,43,0,181,255,0,0,0,0,8,0
    .db 8,0,1,0,249,255,180,255,28,0,2,0,20,0,0,0
    .db 0,0,236,255,171,255,43,0,181,255,0,0,0,0,9,0
    .db 8,0,1,0,249,255,168,255,28,0,2,0,0,0,0,0
    .db 0,0,219,255,146,255,219,255,146,255,0,0,0,0,10,0
    .db 8,0,1,0,243,255,162,255,18,0,2,0,0,0,0,0
    .db 0,0,219,255,146,255,219,255,146,255,0,0,0,0,11,0
    .db 20,0,0,0,204,255,160,255,204,255,160,255,15,0,1,0
    .db 0,0,241,255,169,255,28,0,233,255,0,0,0,0,12,0
    .db 20,0,0,0,204,255,160,255,204,255,160,255,15,0,1,0
    .db 0,0,226,255,198,255,34,0,232,255,0,0,0,0,13,0
    .db 20,0,0,0,204,255,160,255,204,255,160,255,15,0,1,0
    .db 0,0,219,255,223,255,39,0,2,0,0,0,0,0,14,0
    .db 20,0,0,0,204,255,160,255,204,255,160,255,15,0,1,0
    .db 0,0,207,255,241,255,51,0,6,0,0,0,0,0,15,0
    .db 24,0,1,0,246,255,149,255,14,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,16,0
    .db 24,0,1,0,246,255,149,255,14,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,17,0
    .db 24,0,1,0,246,255,149,255,14,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,18,0
    .db 24,0,1,0,246,255,149,255,14,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,19,0
    .db 24,0,1,0,246,255,149,255,14,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,20,0
    .db 24,0,1,0,246,255,149,255,14,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,21,0
    .db 24,0,1,0,246,255,149,255,14,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,22,0
    .db 24,0,1,0,246,255,149,255,14,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,23,0
    .db 24,0,1,0,246,255,149,255,14,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,24,0
    .db 24,0,1,0,246,255,149,255,14,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,25,0
    .db 8,0,1,0,239,255,152,255,30,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,26,0
    .db 32,0,1,0,239,255,152,255,30,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,27,0
    .db 16,0,1,0,239,255,152,255,30,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,28,0
    .db 24,0,0,0,204,255,160,255,204,255,160,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,29,0
    .db 24,0,0,0,204,255,160,255,204,255,160,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,30,0
    .db 24,0,0,0,204,255,160,255,204,255,160,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,31,0
    .db 24,0,0,0,204,255,160,255,204,255,160,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,32,0
    .db 8,0,0,0,183,255,69,255,183,255,69,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,33,0
    .db 8,0,0,0,183,255,69,255,183,255,69,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,34,0
    .db 8,0,0,0,183,255,69,255,183,255,69,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,35,0
    .db 8,0,0,0,183,255,69,255,183,255,69,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,36,0
    .db 8,0,0,0,183,255,69,255,183,255,69,255,28,0,1,0
    .db 1,0,193,255,86,255,129,0,8,0,0,0,0,0,37,0
    .db 8,0,0,0,183,255,69,255,183,255,69,255,28,0,1,0
    .db 1,0,193,255,86,255,129,0,8,0,0,0,0,0,38,0
    .db 8,0,0,0,183,255,69,255,183,255,69,255,28,0,1,0
    .db 1,0,193,255,86,255,129,0,8,0,0,0,0,0,39,0
    .db 8,0,0,0,183,255,69,255,183,255,69,255,28,0,1,0
    .db 1,0,193,255,86,255,129,0,8,0,0,0,0,0,40,0
    .db 8,0,0,0,183,255,69,255,183,255,69,255,28,0,1,0
    .db 1,0,193,255,86,255,129,0,8,0,0,0,0,0,41,0
    .db 8,0,0,0,183,255,69,255,183,255,69,255,28,0,1,0
    .db 1,0,193,255,86,255,129,0,8,0,0,0,0,0,42,0
    .db 8,0,0,0,183,255,69,255,183,255,69,255,28,0,1,0
    .db 1,0,193,255,86,255,129,0,8,0,0,0,0,0,43,0
    .db 8,0,0,0,183,255,69,255,183,255,69,255,28,0,1,0
    .db 1,0,193,255,86,255,129,0,8,0,0,0,0,0,44,0
    .db 8,0,0,0,183,255,69,255,183,255,69,255,28,0,1,0
    .db 1,0,193,255,86,255,129,0,8,0,0,0,0,0,45,0
    .db 8,0,0,0,183,255,69,255,183,255,69,255,28,0,1,0
    .db 1,0,193,255,86,255,129,0,8,0,0,0,0,0,46,0
    .db 8,0,0,0,183,255,69,255,183,255,69,255,28,0,1,0
    .db 1,0,193,255,86,255,129,0,8,0,0,0,0,0,47,0
    .db 8,0,0,0,183,255,69,255,183,255,69,255,28,0,1,0
    .db 1,0,193,255,86,255,129,0,8,0,0,0,0,0,48,0
    .db 8,0,0,0,183,255,69,255,183,255,69,255,28,0,1,0
    .db 1,0,193,255,86,255,129,0,8,0,0,0,0,0,49,0
    .db 8,0,0,0,183,255,69,255,183,255,69,255,0,0,0,0
    .db 0,0,183,255,69,255,183,255,69,255,0,0,0,0,50,0
    .db 8,0,0,0,183,255,69,255,183,255,69,255,0,0,0,0
    .db 0,0,183,255,69,255,183,255,69,255,0,0,0,0,51,0
    .db 8,0,0,0,183,255,69,255,183,255,69,255,0,0,0,0
    .db 0,0,183,255,69,255,183,255,69,255,0,0,0,0,52,0
    .db 8,0,0,0,183,255,69,255,183,255,69,255,0,0,0,0
    .db 0,0,183,255,69,255,183,255,69,255,0,0,0,0,53,0
    .db 8,0,0,0,183,255,69,255,183,255,69,255,0,0,0,0
    .db 0,0,183,255,69,255,183,255,69,255,0,0,0,0,54,0
    .db 8,0,0,0,183,255,69,255,183,255,69,255,0,0,0,0
    .db 0,0,183,255,69,255,183,255,69,255,0,0,0,0,55,0
    .db 8,0,0,0,183,255,69,255,183,255,69,255,0,0,0,0
    .db 0,0,183,255,69,255,183,255,69,255,0,0,0,0,56,0
    .db 8,0,0,0,183,255,69,255,183,255,69,255,0,0,0,0
    .db 0,0,183,255,69,255,183,255,69,255,0,0,0,0,57,0
    .db 6,0,1,0,10,0,149,255,37,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,58,0
    .db 6,0,1,0,10,0,149,255,37,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,59,0
    .db 6,0,1,0,10,0,149,255,37,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,60,0
    .db 6,0,1,0,0,0,174,255,29,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,61,0
    .db 6,0,1,0,234,255,187,255,23,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,62,0
    .db 10,0,1,0,225,255,196,255,5,0,3,0,16,0,1,0
    .db 2,0,240,255,169,255,50,0,236,255,0,0,0,0,63,0
    .db 10,0,1,0,225,255,196,255,5,0,3,0,16,0,1,0
    .db 2,0,236,255,160,255,66,0,240,255,0,0,0,0,64,0
    .db 10,0,1,0,225,255,196,255,5,0,3,0,16,0,1,0
    .db 2,0,234,255,149,255,80,0,229,255,0,0,0,0,65,0
    .db 10,0,1,0,225,255,196,255,5,0,3,0,16,0,1,0
    .db 2,0,234,255,140,255,80,0,220,255,0,0,0,0,66,0
    .db 10,0,1,0,225,255,196,255,5,0,3,0,16,0,1,0
    .db 2,0,234,255,140,255,80,0,220,255,0,0,0,0,67,0
    .db 10,0,1,0,225,255,196,255,5,0,3,0,16,0,1,0
    .db 2,0,234,255,140,255,80,0,220,255,0,0,0,0,68,0
    .db 10,0,1,0,225,255,196,255,5,0,3,0,0,0,0,0
    .db 0,0,203,255,126,255,203,255,126,255,0,0,0,0,69,0
    .db 10,0,1,0,225,255,196,255,5,0,3,0,0,0,0,0
    .db 0,0,203,255,126,255,203,255,126,255,0,0,0,0,70,0
    .db 10,0,1,0,240,255,190,255,20,0,2,0,0,0,0,0
    .db 0,0,203,255,126,255,203,255,126,255,0,0,0,0,71,0
    .db 10,0,1,0,240,255,190,255,20,0,2,0,0,0,0,0
    .db 0,0,203,255,126,255,203,255,126,255,0,0,0,0,72,0
    .db 10,0,1,0,244,255,180,255,26,0,2,0,0,0,0,0
    .db 0,0,203,255,126,255,203,255,126,255,0,0,0,0,73,0
    .db 10,0,1,0,0,0,162,255,31,0,2,0,0,0,0,0
    .db 0,0,203,255,126,255,203,255,126,255,0,0,0,0,74,0
    .db 16,0,1,0,247,255,149,255,13,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,75,0
    .db 16,0,1,0,247,255,149,255,13,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,76,0
    .db 16,0,1,0,247,255,149,255,13,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,77,0
    .db 16,0,1,0,247,255,149,255,13,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,78,0
    .db 16,0,1,0,247,255,149,255,13,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,79,0
    .db 16,0,1,0,247,255,149,255,13,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,80,0
    .db 16,0,1,0,247,255,149,255,13,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,81,0
    .db 16,0,1,0,247,255,149,255,13,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,82,0
    .db 16,0,1,0,247,255,149,255,13,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,83,0
    .db 16,0,1,0,247,255,149,255,13,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,84,0
    .db 16,0,1,0,247,255,149,255,13,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,85,0
    .db 16,0,1,0,247,255,149,255,13,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,86,0
    .db 16,0,1,0,247,255,149,255,13,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,87,0
    .db 16,0,1,0,247,255,149,255,13,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,88,0
    .db 0,0,12,0,48,174,35,0,0,0,0,0,0,0,0,0
    .db 1,0,4,0,176,175,35,0,0,0,0,0,0,0,0,0
    .db 2,0,10,0,48,176,35,1,0,0,0,0,0,0,0,0
    .db 3,0,3,0,112,177,35,0,0,0,0,0,0,0,0,0
    .db 4,0,4,0,208,177,35,0,0,0,0,0,0,0,0,0
    .db 5,0,25,0,80,178,35,0,0,0,0,0,0,0,0,0
    .db 6,0,17,0,112,181,35,0,0,0,0,0,0,0,0,0
    .db 7,0,14,0,144,183,35,1,0,0,0,0,0,0,0,0
    .db 8,0,1,0,221,255,172,255,19,0,255,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    .db 8,0,1,0,221,255,172,255,19,0,255,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0
    .db 8,0,1,0,221,255,172,255,19,0,255,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0
    .db 8,0,1,0,221,255,172,255,19,0,255,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,0
    .db 8,0,1,0,221,255,172,255,19,0,255,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,4,0
    .db 8,0,1,0,221,255,172,255,19,0,255,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,5,0
    .db 8,0,1,0,221,255,172,255,19,0,255,255,14,0,1,0
    .db 0,0,216,255,144,255,19,0,171,255,0,0,0,0,6,0
    .db 8,0,1,0,226,255,172,255,28,0,255,255,14,0,1,0
    .db 0,0,3,0,138,255,61,0,184,255,0,0,0,0,7,0
    .db 8,0,1,0,226,255,172,255,28,0,255,255,14,0,1,0
    .db 0,0,38,0,142,255,83,0,210,255,0,0,0,0,8,0
    .db 8,0,1,0,226,255,172,255,28,0,255,255,14,0,1,0
    .db 0,0,43,0,181,255,93,0,1,0,0,0,0,0,9,0
    .db 14,0,1,0,226,255,172,255,28,0,255,255,0,0,0,0
    .db 0,0,175,255,136,255,175,255,136,255,0,0,0,0,10,0
    .db 14,0,1,0,226,255,172,255,28,0,255,255,0,0,0,0
    .db 0,0,175,255,136,255,175,255,136,255,0,0,0,0,11,0
    .db 14,0,1,0,226,255,172,255,28,0,255,255,0,0,0,0
    .db 0,0,175,255,136,255,175,255,136,255,0,0,0,0,12,0
    .db 14,0,1,0,226,255,172,255,28,0,255,255,0,0,0,0
    .db 0,0,175,255,136,255,175,255,136,255,0,0,0,0,13,0
    .db 8,0,1,0,221,255,179,255,27,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,14,0
    .db 8,0,1,0,221,255,179,255,27,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,15,0
    .db 8,0,1,0,221,255,179,255,27,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,16,0
    .db 6,0,1,0,221,255,179,255,27,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,17,0
    .db 6,0,1,0,221,255,179,255,27,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,18,0
    .db 6,0,1,0,221,255,179,255,27,0,2,0,8,0,0,0
    .db 0,0,21,0,184,255,60,0,237,255,0,0,0,0,19,0
    .db 6,0,1,0,221,255,179,255,27,0,2,0,8,0,0,0
    .db 0,0,29,0,202,255,85,0,3,0,0,0,0,0,20,0
    .db 10,0,1,0,221,255,179,255,27,0,2,0,8,0,0,0
    .db 0,0,29,0,202,255,85,0,3,0,0,0,0,0,21,0
    .db 10,0,1,0,221,255,179,255,27,0,2,0,0,0,0,0
    .db 0,0,207,255,164,255,207,255,164,255,0,0,0,0,22,0
    .db 10,0,1,0,221,255,179,255,27,0,2,0,0,0,0,0
    .db 0,0,207,255,164,255,207,255,164,255,0,0,0,0,23,0
    .db 8,0,1,0,221,255,179,255,27,0,2,0,0,0,0,0
    .db 0,0,207,255,164,255,207,255,164,255,0,0,0,0,24,0
    .db 8,0,1,0,221,255,179,255,27,0,2,0,0,0,0,0
    .db 0,0,207,255,164,255,207,255,164,255,0,0,0,0,25,0
    .db 8,0,1,0,221,255,179,255,27,0,2,0,0,0,0,0
    .db 0,0,207,255,164,255,207,255,164,255,0,0,0,0,26,0
    .db 6,0,1,0,221,255,179,255,27,0,2,0,0,0,0,0
    .db 0,0,207,255,164,255,207,255,164,255,0,0,0,0,27,0
    .db 6,0,1,0,221,255,179,255,27,0,2,0,0,0,0,0
    .db 0,0,207,255,164,255,207,255,164,255,0,0,0,0,28,0
    .db 6,0,1,0,221,255,179,255,27,0,2,0,8,0,0,0
    .db 0,0,21,0,184,255,60,0,237,255,0,0,0,0,29,0
    .db 6,0,1,0,221,255,179,255,27,0,2,0,8,0,0,0
    .db 0,0,29,0,202,255,85,0,3,0,0,0,0,0,30,0
    .db 6,0,1,0,221,255,179,255,27,0,2,0,8,0,0,0
    .db 0,0,29,0,202,255,85,0,3,0,0,0,0,0,31,0
    .db 6,0,1,0,221,255,179,255,27,0,2,0,0,0,0,0
    .db 0,0,207,255,164,255,207,255,164,255,0,0,0,0,32,0
    .db 6,0,1,0,221,255,179,255,27,0,2,0,0,0,0,0
    .db 0,0,207,255,164,255,207,255,164,255,0,0,0,0,33,0
    .db 50,0,0,0,202,255,164,255,202,255,164,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,34,0
    .db 50,0,0,0,202,255,164,255,202,255,164,255,15,0,1,0
    .db 0,0,227,255,209,255,28,0,229,255,0,0,0,0,35,0
    .db 50,0,0,0,202,255,164,255,202,255,164,255,15,0,1,0
    .db 0,0,227,255,209,255,28,0,229,255,0,0,0,0,36,0
    .db 50,0,0,0,202,255,164,255,202,255,164,255,15,0,1,0
    .db 0,0,227,255,209,255,28,0,229,255,0,0,0,0,37,0
    .db 50,0,0,0,202,255,164,255,202,255,164,255,15,0,1,0
    .db 0,0,227,255,209,255,28,0,229,255,0,0,0,0,38,0
    .db 50,0,0,0,202,255,164,255,202,255,164,255,15,0,1,0
    .db 0,0,227,255,209,255,28,0,229,255,0,0,0,0,39,0
    .db 50,0,0,0,202,255,164,255,202,255,164,255,15,0,1,0
    .db 0,0,227,255,209,255,28,0,229,255,0,0,0,0,40,0
    .db 18,0,0,0,202,255,164,255,202,255,164,255,15,0,1,0
    .db 0,0,227,255,209,255,28,0,229,255,0,0,0,0,41,0
    .db 18,0,0,0,202,255,164,255,202,255,164,255,15,0,1,0
    .db 0,0,227,255,209,255,28,0,229,255,0,0,0,0,42,0
    .db 18,0,0,0,202,255,164,255,202,255,164,255,15,0,1,0
    .db 0,0,227,255,209,255,28,0,229,255,0,0,0,0,43,0
    .db 18,0,0,0,202,255,164,255,202,255,164,255,15,0,1,0
    .db 0,0,227,255,209,255,28,0,229,255,0,0,0,0,44,0
    .db 18,0,0,0,202,255,164,255,202,255,164,255,15,0,1,0
    .db 0,0,227,255,209,255,28,0,229,255,0,0,0,0,45,0
    .db 18,0,0,0,202,255,164,255,202,255,164,255,15,0,1,0
    .db 0,0,227,255,209,255,28,0,229,255,0,0,0,0,46,0
    .db 18,0,0,0,202,255,164,255,202,255,164,255,15,0,1,0
    .db 0,0,227,255,209,255,28,0,229,255,0,0,0,0,47,0
    .db 18,0,0,0,202,255,164,255,202,255,164,255,15,0,1,0
    .db 0,0,227,255,209,255,28,0,229,255,0,0,0,0,48,0
    .db 18,0,0,0,202,255,164,255,202,255,164,255,15,0,1,0
    .db 0,0,227,255,209,255,28,0,229,255,0,0,0,0,49,0
    .db 18,0,0,0,202,255,164,255,202,255,164,255,15,0,1,0
    .db 0,0,227,255,209,255,28,0,229,255,0,0,0,0,50,0
    .db 18,0,0,0,202,255,164,255,202,255,164,255,15,0,1,0
    .db 0,0,227,255,209,255,28,0,229,255,0,0,0,0,51,0
    .db 18,0,0,0,202,255,164,255,202,255,164,255,15,0,1,0
    .db 0,0,227,255,209,255,28,0,229,255,0,0,0,0,52,0
    .db 18,0,0,0,202,255,164,255,202,255,164,255,15,0,1,0
    .db 0,0,227,255,209,255,28,0,229,255,0,0,0,0,53,0
    .db 18,0,0,0,202,255,164,255,202,255,164,255,15,0,1,0
    .db 0,0,227,255,209,255,28,0,229,255,0,0,0,0,54,0
    .db 18,0,0,0,202,255,164,255,202,255,164,255,15,0,1,0
    .db 0,0,227,255,209,255,28,0,229,255,0,0,0,0,55,0
    .db 18,0,0,0,202,255,164,255,202,255,164,255,15,0,1,0
    .db 0,0,227,255,209,255,28,0,229,255,0,0,0,0,56,0
    .db 18,0,0,0,202,255,164,255,202,255,164,255,15,0,1,0
    .db 0,0,227,255,209,255,28,0,229,255,0,0,0,0,57,0
    .db 18,0,0,0,202,255,164,255,202,255,164,255,15,0,1,0
    .db 0,0,227,255,209,255,28,0,229,255,0,0,0,0,58,0
    .db 20,0,1,0,226,255,181,255,36,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,59,0
    .db 20,0,1,0,226,255,181,255,36,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,60,0
    .db 20,0,1,0,226,255,181,255,36,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,61,0
    .db 20,0,1,0,226,255,181,255,36,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,62,0
    .db 20,0,1,0,226,255,181,255,36,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,63,0
    .db 20,0,1,0,235,255,171,255,36,0,255,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,64,0
    .db 60,0,1,0,235,255,171,255,36,0,255,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,65,0
    .db 20,0,1,0,235,255,171,255,36,0,255,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,66,0
    .db 30,0,0,0,196,255,163,255,196,255,163,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,67,0
    .db 30,0,0,0,196,255,163,255,196,255,163,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,68,0
    .db 30,0,0,0,196,255,163,255,196,255,163,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,69,0
    .db 30,0,0,0,196,255,163,255,196,255,163,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,70,0
    .db 30,0,0,0,196,255,163,255,196,255,163,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,71,0
    .db 14,0,1,0,223,255,179,255,31,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,72,0
    .db 14,0,1,0,223,255,179,255,31,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,73,0
    .db 14,0,1,0,223,255,179,255,31,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,74,0
    .db 14,0,1,0,223,255,179,255,31,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,75,0
    .db 14,0,1,0,223,255,179,255,31,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,76,0
    .db 14,0,1,0,223,255,179,255,31,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,77,0
    .db 14,0,1,0,223,255,179,255,31,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,78,0
    .db 14,0,1,0,223,255,179,255,31,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,79,0
    .db 14,0,1,0,223,255,179,255,31,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,80,0
    .db 14,0,1,0,223,255,179,255,31,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,81,0
    .db 14,0,1,0,223,255,179,255,31,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,82,0
    .db 14,0,1,0,223,255,179,255,31,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,83,0
    .db 0,0,14,0,208,185,35,0,0,0,0,0,0,0,0,0
    .db 1,0,20,0,144,187,35,0,0,0,0,0,0,0,0,0
    .db 2,0,25,0,16,190,35,0,0,0,0,0,0,0,0,0
    .db 3,0,5,0,48,193,35,1,0,0,0,0,0,0,0,0
    .db 4,0,3,0,208,193,35,0,0,0,0,0,0,0,0,0
    .db 5,0,5,0,48,194,35,0,0,0,0,0,0,0,0,0
    .db 6,0,12,0,208,194,35,1,0,0,0,0,0,0,0,0
    .db 10,0,1,0,228,255,135,255,28,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    .db 10,0,1,0,231,255,120,255,17,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0
    .db 10,0,1,0,231,255,120,255,17,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0
    .db 10,0,1,0,231,255,120,255,17,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,0
    .db 10,0,1,0,213,255,151,255,16,0,2,0,20,0,1,0
    .db 0,0,196,255,115,255,211,255,184,255,0,0,0,0,4,0
    .db 10,0,1,0,207,255,161,255,250,255,255,255,20,0,1,0
    .db 0,0,181,255,159,255,245,255,197,255,0,0,0,0,5,0
    .db 10,0,1,0,233,255,154,255,33,0,0,0,20,0,1,0
    .db 0,0,34,0,165,255,116,0,203,255,0,0,0,0,6,0
    .db 10,0,1,0,233,255,154,255,33,0,0,0,20,0,1,0
    .db 0,0,34,0,165,255,116,0,203,255,0,0,0,0,7,0
    .db 10,0,1,0,233,255,154,255,33,0,0,0,20,0,1,0
    .db 0,0,34,0,165,255,116,0,203,255,0,0,0,0,8,0
    .db 10,0,1,0,236,255,149,255,29,0,1,0,0,0,0,0
    .db 0,0,166,255,77,255,166,255,77,255,0,0,0,0,9,0
    .db 10,0,1,0,236,255,149,255,29,0,1,0,0,0,0,0
    .db 0,0,166,255,77,255,166,255,77,255,0,0,0,0,10,0
    .db 10,0,1,0,236,255,149,255,29,0,1,0,0,0,0,0
    .db 0,0,166,255,77,255,166,255,77,255,0,0,0,0,11,0
    .db 10,0,1,0,236,255,149,255,29,0,1,0,0,0,0,0
    .db 0,0,166,255,77,255,166,255,77,255,0,0,0,0,12,0
    .db 10,0,1,0,236,255,149,255,29,0,1,0,0,0,0,0
    .db 0,0,166,255,77,255,166,255,77,255,0,0,0,0,13,0
    .db 10,0,1,0,241,255,132,255,25,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,14,0
    .db 10,0,1,0,241,255,132,255,25,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,15,0
    .db 10,0,1,0,241,255,132,255,25,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,16,0
    .db 10,0,1,0,241,255,132,255,25,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,17,0
    .db 10,0,1,0,241,255,132,255,25,0,2,0,14,0,0,0
    .db 0,0,229,255,133,255,69,0,169,255,0,0,0,0,18,0
    .db 10,0,1,0,241,255,132,255,25,0,2,0,0,0,0,0
    .db 0,0,178,255,85,255,178,255,85,255,0,0,0,0,19,0
    .db 10,0,1,0,241,255,132,255,25,0,2,0,14,0,0,0
    .db 0,0,181,255,139,255,30,0,175,255,0,0,0,0,20,0
    .db 10,0,1,0,241,255,132,255,25,0,2,0,0,0,0,0
    .db 0,0,178,255,85,255,178,255,85,255,0,0,0,0,21,0
    .db 10,0,1,0,241,255,132,255,25,0,2,0,14,0,0,0
    .db 0,0,218,255,140,255,83,0,176,255,0,0,0,0,22,0
    .db 10,0,1,0,241,255,132,255,25,0,2,0,0,0,0,0
    .db 0,0,178,255,85,255,178,255,85,255,0,0,0,0,23,0
    .db 10,0,1,0,241,255,132,255,25,0,2,0,14,0,0,0
    .db 0,0,181,255,139,255,30,0,175,255,0,0,0,0,24,0
    .db 10,0,1,0,241,255,132,255,25,0,2,0,0,0,0,0
    .db 0,0,178,255,85,255,178,255,85,255,0,0,0,0,25,0
    .db 10,0,1,0,241,255,132,255,25,0,2,0,14,0,1,0
    .db 0,0,218,255,140,255,83,0,176,255,0,0,0,0,26,0
    .db 10,0,1,0,241,255,132,255,25,0,2,0,14,0,1,0
    .db 0,0,218,255,140,255,83,0,176,255,0,0,0,0,27,0
    .db 10,0,1,0,241,255,132,255,25,0,2,0,0,0,0,0
    .db 0,0,178,255,85,255,178,255,85,255,0,0,0,0,28,0
    .db 10,0,1,0,241,255,151,255,50,0,2,0,0,0,0,0
    .db 0,0,178,255,85,255,178,255,85,255,0,0,0,0,29,0
    .db 10,0,1,0,241,255,151,255,50,0,2,0,0,0,0,0
    .db 0,0,178,255,85,255,178,255,85,255,0,0,0,0,30,0
    .db 10,0,1,0,232,255,153,255,34,0,3,0,0,0,0,0
    .db 0,0,178,255,85,255,178,255,85,255,0,0,0,0,31,0
    .db 10,0,1,0,232,255,153,255,34,0,3,0,0,0,0,0
    .db 0,0,178,255,85,255,178,255,85,255,0,0,0,0,32,0
    .db 10,0,1,0,232,255,153,255,34,0,3,0,0,0,0,0
    .db 0,0,178,255,85,255,178,255,85,255,0,0,0,0,33,0
    .db 10,0,1,0,232,255,153,255,34,0,3,0,0,0,0,0
    .db 0,0,178,255,85,255,178,255,85,255,0,0,0,0,34,0
    .db 40,0,0,0,206,255,126,255,206,255,126,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,35,0
    .db 40,0,0,0,206,255,126,255,206,255,126,255,15,0,1,0
    .db 0,0,235,255,160,255,48,0,218,255,0,0,0,0,36,0
    .db 40,0,0,0,206,255,126,255,206,255,126,255,15,0,1,0
    .db 0,0,241,255,224,255,83,0,2,0,0,0,0,0,37,0
    .db 40,0,0,0,206,255,126,255,206,255,126,255,15,0,1,0
    .db 0,0,241,255,224,255,83,0,2,0,0,0,0,0,38,0
    .db 18,0,1,0,230,255,151,255,25,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,39,0
    .db 18,0,1,0,230,255,151,255,25,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,40,0
    .db 18,0,1,0,230,255,151,255,25,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,41,0
    .db 18,0,1,0,230,255,151,255,25,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,42,0
    .db 18,0,1,0,230,255,151,255,25,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,43,0
    .db 18,0,1,0,230,255,151,255,25,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,44,0
    .db 18,0,1,0,230,255,151,255,25,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,45,0
    .db 18,0,1,0,230,255,151,255,25,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,46,0
    .db 24,0,1,0,232,255,156,255,27,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,47,0
    .db 100,0,1,0,232,255,156,255,27,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,48,0
    .db 24,0,1,0,232,255,156,255,27,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,49,0
    .db 20,0,0,0,201,255,147,255,201,255,147,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,50,0
    .db 20,0,0,0,201,255,147,255,201,255,147,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,51,0
    .db 20,0,0,0,201,255,147,255,201,255,147,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,52,0
    .db 20,0,0,0,201,255,147,255,201,255,147,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,53,0
    .db 20,0,0,0,201,255,147,255,201,255,147,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,54,0
    .db 18,0,1,0,244,255,139,255,17,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,55,0
    .db 18,0,1,0,244,255,139,255,17,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,56,0
    .db 18,0,1,0,244,255,139,255,17,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,57,0
    .db 18,0,1,0,244,255,139,255,17,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,58,0
    .db 18,0,1,0,244,255,139,255,17,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,59,0
    .db 18,0,1,0,244,255,139,255,17,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,60,0
    .db 18,0,1,0,244,255,139,255,17,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,61,0
    .db 18,0,1,0,244,255,139,255,17,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,62,0
    .db 0,0,14,0,192,196,35,0,0,0,0,0,0,0,0,0
    .db 1,0,21,0,128,198,35,0,0,0,0,0,0,0,0,0
    .db 2,0,4,0,32,201,35,0,0,0,0,0,0,0,0,0
    .db 3,0,8,0,160,201,35,1,0,0,0,0,0,0,0,0
    .db 4,0,3,0,160,202,35,0,0,0,0,0,0,0,0,0
    .db 5,0,5,0,0,203,35,0,0,0,0,0,0,0,0,0
    .db 6,0,8,0,160,203,35,1,0,0,0,0,0,0,0,0
    .db 14,0,1,0,244,255,154,255,17,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    .db 14,0,1,0,244,255,154,255,17,0,0,0,10,0,0,0
    .db 0,0,17,0,162,255,64,0,183,255,0,0,0,0,1,0
    .db 40,0,1,0,244,255,154,255,17,0,0,0,10,0,0,0
    .db 0,0,17,0,162,255,64,0,183,255,0,0,0,0,2,0
    .db 20,0,1,0,244,255,154,255,17,0,0,0,0,0,0,0
    .db 0,0,217,255,145,255,217,255,145,255,0,0,0,0,3,0
    .db 20,0,1,0,244,255,154,255,17,0,0,0,0,0,0,0
    .db 0,0,217,255,145,255,217,255,145,255,0,0,0,0,4,0
    .db 40,0,0,0,192,255,168,255,192,255,168,255,15,0,1,0
    .db 0,0,240,255,182,255,9,0,244,255,0,0,0,0,5,0
    .db 40,0,0,0,192,255,168,255,192,255,168,255,15,0,1,0
    .db 0,0,239,255,189,255,13,0,240,255,0,0,0,0,6,0
    .db 40,0,0,0,192,255,168,255,192,255,168,255,15,0,1,0
    .db 0,0,217,255,226,255,38,0,246,255,0,0,0,0,7,0
    .db 40,0,0,0,192,255,168,255,192,255,168,255,15,0,1,0
    .db 0,0,210,255,238,255,59,0,3,0,0,0,0,0,8,0
    .db 20,0,1,0,239,255,158,255,17,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,9,0
    .db 20,0,1,0,239,255,158,255,17,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,10,0
    .db 20,0,1,0,239,255,158,255,17,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,11,0
    .db 20,0,1,0,239,255,158,255,17,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,12,0
    .db 20,0,1,0,239,255,158,255,17,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,13,0
    .db 20,0,1,0,239,255,158,255,17,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,14,0
    .db 24,0,1,0,235,255,162,255,12,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,15,0
    .db 100,0,1,0,235,255,162,255,12,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,16,0
    .db 24,0,1,0,235,255,162,255,12,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,17,0
    .db 30,0,0,0,191,255,176,255,191,255,176,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,18,0
    .db 30,0,0,0,181,255,176,255,181,255,176,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,10,0,19,0
    .db 30,0,0,0,171,255,176,255,171,255,176,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,10,0,20,0
    .db 20,0,1,0,225,255,165,255,253,255,4,0,15,0,0,0
    .db 0,0,248,255,185,255,17,0,204,255,0,0,30,0,21,0
    .db 20,0,1,0,229,255,160,255,1,0,4,0,15,0,1,0
    .db 0,0,253,255,161,255,15,0,200,255,0,0,0,0,22,0
    .db 20,0,1,0,241,255,157,255,15,0,1,0,15,0,1,0
    .db 0,0,238,255,139,255,14,0,176,255,0,0,0,0,23,0
    .db 100,0,1,0,241,255,157,255,15,0,1,0,0,0,0,0
    .db 0,0,198,255,131,255,198,255,131,255,0,0,0,0,24,0
    .db 16,0,1,0,243,255,149,255,12,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,25,0
    .db 16,0,1,0,243,255,149,255,12,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,26,0
    .db 16,0,1,0,243,255,149,255,12,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,27,0
    .db 16,0,1,0,243,255,149,255,12,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,28,0
    .db 16,0,1,0,243,255,149,255,12,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,29,0
    .db 16,0,1,0,243,255,149,255,12,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,30,0
    .db 16,0,1,0,243,255,149,255,12,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,31,0
    .db 16,0,1,0,243,255,149,255,12,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,32,0
    .db 0,0,5,0,16,205,35,0,0,0,0,0,0,0,0,0
    .db 1,0,4,0,176,205,35,0,0,0,0,0,0,0,0,0
    .db 2,0,6,0,48,206,35,1,0,0,0,0,0,0,0,0
    .db 3,0,3,0,240,206,35,0,0,0,0,0,0,0,0,0
    .db 4,0,3,0,80,207,35,0,0,0,0,0,0,0,0,0
    .db 5,0,4,0,176,207,35,0,0,0,0,0,0,0,0,0
    .db 6,0,8,0,48,208,35,1,0,0,0,0,0,0,0,0
    .db 0,0,0,0,231,255,176,255,231,255,176,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    .db 0,0,0,0,231,255,176,255,231,255,176,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0
    .db 0,0,0,0,231,255,176,255,231,255,176,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0
    .db 0,0,0,0,231,255,176,255,231,255,176,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,0
    .db 0,0,1,0,160,209,35,0,0,0,0,0,0,0,0,0
    .db 1,0,1,0,192,209,35,0,0,0,0,0,0,0,0,0
    .db 2,0,1,0,224,209,35,0,0,0,0,0,0,0,0,0
    .db 3,0,1,0,0,210,35,0,0,0,0,0,0,0,0,0
    .db 14,0,1,0,235,255,153,255,22,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    .db 14,0,1,0,235,255,153,255,22,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0
    .db 14,0,1,0,235,255,153,255,22,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0
    .db 14,0,1,0,235,255,153,255,22,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,0
    .db 14,0,1,0,222,255,165,255,19,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,4,0
    .db 14,0,1,0,215,255,174,255,16,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,5,0
    .db 14,0,1,0,215,255,174,255,16,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,6,0
    .db 14,0,1,0,215,255,174,255,16,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,7,0
    .db 14,0,1,0,215,255,174,255,16,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,8,0
    .db 14,0,1,0,228,255,172,255,24,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,9,0
    .db 14,0,1,0,239,255,165,255,30,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,10,0
    .db 14,0,1,0,252,255,166,255,50,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,11,0
    .db 14,0,1,0,252,255,166,255,50,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,12,0
    .db 14,0,1,0,252,255,166,255,50,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,13,0
    .db 14,0,1,0,252,255,166,255,50,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,14,0
    .db 14,0,1,0,252,255,166,255,50,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,15,0
    .db 14,0,1,0,244,255,156,255,31,0,5,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,16,0
    .db 14,0,1,0,235,255,155,255,15,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,17,0
    .db 14,0,1,0,235,255,173,255,15,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,18,0
    .db 14,0,1,0,235,255,173,255,15,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,19,0
    .db 14,0,1,0,245,255,173,255,25,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,20,0
    .db 14,0,1,0,231,255,173,255,11,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,21,0
    .db 14,0,1,0,239,255,175,255,25,0,14,0,15,0,1,0
    .db 0,0,26,0,154,255,88,0,199,255,0,0,0,0,22,0
    .db 14,0,1,0,239,255,175,255,25,0,14,0,15,0,1,0
    .db 0,0,26,0,154,255,88,0,199,255,0,0,0,0,23,0
    .db 14,0,1,0,239,255,175,255,25,0,14,0,15,0,1,0
    .db 0,0,16,0,188,255,73,0,221,255,0,0,0,0,24,0
    .db 14,0,1,0,233,255,149,255,20,0,3,0,0,0,0,0
    .db 0,0,196,255,143,255,196,255,143,255,0,0,0,0,25,0
    .db 14,0,1,0,233,255,149,255,20,0,3,0,0,0,0,0
    .db 0,0,196,255,143,255,196,255,143,255,0,0,0,0,26,0
    .db 14,0,0,0,219,255,140,255,219,255,140,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,27,0
    .db 14,0,0,0,219,255,140,255,219,255,140,255,15,0,1,0
    .db 0,0,20,0,168,255,56,0,204,255,0,0,0,0,28,0
    .db 14,0,0,0,219,255,140,255,219,255,140,255,15,0,1,0
    .db 0,0,27,0,147,255,64,0,188,255,0,0,0,0,29,0
    .db 14,0,0,0,219,255,140,255,219,255,140,255,15,0,1,0
    .db 0,0,27,0,147,255,64,0,188,255,0,0,0,0,30,0
    .db 14,0,0,0,219,255,140,255,219,255,140,255,15,0,1,0
    .db 0,0,27,0,147,255,64,0,188,255,0,0,0,0,31,0
    .db 14,0,0,0,219,255,140,255,219,255,140,255,15,0,1,0
    .db 0,0,20,0,168,255,56,0,204,255,0,0,0,0,32,0
    .db 14,0,0,0,219,255,140,255,219,255,140,255,0,0,0,0
    .db 0,0,219,255,140,255,219,255,140,255,0,0,0,0,33,0
    .db 40,0,0,0,201,255,151,255,201,255,151,255,15,0,1,0
    .db 0,0,230,255,189,255,19,0,217,255,0,0,0,0,34,0
    .db 40,0,0,0,201,255,176,255,201,255,176,255,15,0,1,0
    .db 0,0,218,255,227,255,17,0,246,255,0,0,0,0,35,0
    .db 40,0,0,0,201,255,182,255,201,255,182,255,15,0,1,0
    .db 0,0,218,255,233,255,17,0,252,255,0,0,0,0,36,0
    .db 40,0,0,0,201,255,184,255,201,255,184,255,15,0,1,0
    .db 0,0,215,255,241,255,39,0,0,0,0,0,0,0,37,0
    .db 20,0,1,0,235,255,153,255,24,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,38,0
    .db 20,0,1,0,235,255,153,255,24,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,39,0
    .db 20,0,1,0,235,255,153,255,24,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,40,0
    .db 20,0,1,0,235,255,153,255,24,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,41,0
    .db 20,0,1,0,240,255,151,255,29,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,42,0
    .db 20,0,1,0,240,255,151,255,29,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,43,0
    .db 20,0,1,0,240,255,151,255,29,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,44,0
    .db 20,0,1,0,240,255,151,255,29,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,45,0
    .db 20,0,1,0,240,255,151,255,29,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,46,0
    .db 20,0,1,0,240,255,151,255,29,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,47,0
    .db 24,0,1,0,232,255,162,255,14,0,5,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,48,0
    .db 100,0,1,0,232,255,162,255,14,0,5,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,49,0
    .db 24,0,1,0,232,255,162,255,14,0,5,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,50,0
    .db 30,0,0,0,209,255,147,255,209,255,147,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,51,0
    .db 20,0,0,0,209,255,147,255,209,255,147,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,52,0
    .db 20,0,0,0,209,255,147,255,209,255,147,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,53,0
    .db 20,0,1,0,240,255,173,255,27,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,5,0,54,0
    .db 20,0,1,0,246,255,167,255,32,0,6,0,15,0,1,0
    .db 0,0,24,0,170,255,59,0,217,255,0,0,5,0,55,0
    .db 30,0,1,0,239,255,162,255,21,0,12,0,15,0,1,0
    .db 0,0,239,255,129,255,27,0,200,255,0,0,0,0,56,0
    .db 30,0,1,0,239,255,162,255,14,0,12,0,15,0,1,0
    .db 0,0,239,255,129,255,27,0,200,255,0,0,0,0,57,0
    .db 30,0,1,0,239,255,162,255,14,0,12,0,15,0,1,0
    .db 0,0,239,255,129,255,27,0,200,255,0,0,0,0,58,0
    .db 30,0,1,0,239,255,162,255,14,0,12,0,15,0,1,0
    .db 0,0,239,255,129,255,27,0,200,255,0,0,0,0,59,0
    .db 60,0,1,0,245,255,173,255,24,0,18,0,0,0,0,0
    .db 0,0,206,255,118,255,206,255,118,255,0,0,0,0,60,0
    .db 20,0,1,0,247,255,189,255,29,0,22,0,0,0,0,0
    .db 0,0,206,255,118,255,206,255,118,255,0,0,0,0,61,0
    .db 20,0,1,0,243,255,175,255,27,0,17,0,0,0,0,0
    .db 0,0,206,255,118,255,206,255,118,255,0,0,0,0,62,0
    .db 16,0,1,0,237,255,153,255,22,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,63,0
    .db 16,0,1,0,237,255,153,255,22,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,64,0
    .db 16,0,1,0,237,255,153,255,22,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,65,0
    .db 16,0,1,0,237,255,153,255,22,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,66,0
    .db 16,0,1,0,237,255,153,255,22,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,67,0
    .db 0,0,17,0,96,210,35,0,0,0,0,0,0,0,0,0
    .db 1,0,10,0,128,212,35,0,0,0,0,0,0,0,0,0
    .db 2,0,7,0,192,213,35,0,0,0,0,0,0,0,0,0
    .db 3,0,4,0,160,214,35,0,0,0,0,0,0,0,0,0
    .db 4,0,10,0,32,215,35,1,0,0,0,0,0,0,0,0
    .db 5,0,3,0,96,216,35,0,0,0,0,0,0,0,0,0
    .db 6,0,3,0,192,216,35,0,0,0,0,0,0,0,0,0
    .db 7,0,9,0,32,217,35,0,0,0,0,0,0,0,0,0
    .db 8,0,5,0,64,218,35,1,0,0,0,0,0,0,0,0
    .db 10,0,1,0,244,255,159,255,13,0,6,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    .db 10,0,1,0,244,255,159,255,13,0,6,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0
    .db 10,0,1,0,244,255,159,255,13,0,6,0,20,0,1,0
    .db 0,0,8,0,193,255,42,0,237,255,0,0,0,0,2,0
    .db 10,0,1,0,234,255,151,255,7,0,3,0,20,0,1,0
    .db 0,0,8,0,192,255,88,0,250,255,0,0,0,0,3,0
    .db 10,0,1,0,234,255,151,255,7,0,3,0,20,0,1,0
    .db 0,0,255,255,182,255,63,0,237,255,0,0,0,0,4,0
    .db 10,0,1,0,226,255,140,255,252,255,1,0,20,0,1,0
    .db 0,0,218,255,164,255,27,0,215,255,0,0,0,0,5,0
    .db 10,0,1,0,226,255,140,255,252,255,1,0,20,0,1,0
    .db 0,0,218,255,164,255,27,0,215,255,0,0,0,0,6,0
    .db 10,0,1,0,226,255,140,255,252,255,1,0,0,0,0,0
    .db 0,0,204,255,127,255,204,255,127,255,0,0,0,0,7,0
    .db 10,0,1,0,237,255,140,255,7,0,1,0,0,0,0,0
    .db 0,0,204,255,127,255,204,255,127,255,0,0,0,0,8,0
    .db 14,0,1,0,241,255,139,255,15,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,9,0
    .db 14,0,1,0,236,255,139,255,10,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,10,0
    .db 14,0,1,0,236,255,139,255,10,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,11,0
    .db 14,0,1,0,241,255,139,255,15,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,12,0
    .db 14,0,1,0,245,255,155,255,25,0,255,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,13,0
    .db 14,0,1,0,252,255,137,255,29,0,255,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,14,0
    .db 14,0,1,0,252,255,137,255,29,0,255,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,15,0
    .db 14,0,1,0,252,255,137,255,29,0,255,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,16,0
    .db 14,0,1,0,252,255,137,255,29,0,255,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,17,0
    .db 14,0,1,0,252,255,137,255,29,0,255,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,18,0
    .db 14,0,1,0,252,255,137,255,29,0,255,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,19,0
    .db 14,0,1,0,252,255,137,255,29,0,255,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,20,0
    .db 20,0,0,0,187,255,177,255,187,255,177,255,15,0,1,0
    .db 0,0,237,255,213,255,4,0,245,255,0,0,0,0,21,0
    .db 20,0,0,0,187,255,177,255,187,255,177,255,15,0,1,0
    .db 0,0,214,255,236,255,3,0,247,255,0,0,0,0,22,0
    .db 20,0,0,0,187,255,177,255,187,255,177,255,15,0,1,0
    .db 0,0,208,255,237,255,17,0,247,255,0,0,0,0,23,0
    .db 20,0,0,0,187,255,177,255,187,255,177,255,15,0,1,0
    .db 0,0,208,255,237,255,17,0,247,255,0,0,0,0,24,0
    .db 20,0,0,0,187,255,177,255,187,255,177,255,15,0,1,0
    .db 0,0,208,255,237,255,17,0,247,255,0,0,0,0,25,0
    .db 24,0,1,0,238,255,137,255,18,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,26,0
    .db 24,0,1,0,238,255,137,255,18,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,27,0
    .db 24,0,1,0,238,255,137,255,18,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,28,0
    .db 24,0,1,0,238,255,137,255,18,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,29,0
    .db 24,0,1,0,238,255,137,255,18,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,30,0
    .db 24,0,1,0,238,255,137,255,18,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,31,0
    .db 12,0,1,0,239,255,125,255,21,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,32,0
    .db 12,0,1,0,239,255,125,255,21,0,231,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,33,0
    .db 12,0,1,0,236,255,140,255,30,0,216,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,34,0
    .db 12,0,1,0,237,255,132,255,35,0,197,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,35,0
    .db 12,0,1,0,231,255,132,255,29,0,197,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,36,0
    .db 12,0,1,0,231,255,140,255,18,0,193,255,14,0,1,0
    .db 0,0,9,0,166,255,91,0,224,255,0,0,0,0,37,0
    .db 6,0,1,0,234,255,143,255,13,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,38,0
    .db 6,0,1,0,234,255,143,255,13,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,39,0
    .db 6,0,1,0,234,255,143,255,13,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,40,0
    .db 20,0,0,0,213,255,127,255,213,255,127,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,41,0
    .db 20,0,0,0,213,255,127,255,213,255,127,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,42,0
    .db 20,0,0,0,213,255,127,255,213,255,127,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,43,0
    .db 20,0,0,0,213,255,127,255,213,255,127,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,44,0
    .db 20,0,0,0,213,255,127,255,213,255,127,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,45,0
    .db 20,0,0,0,213,255,127,255,213,255,127,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,46,0
    .db 20,0,0,0,213,255,127,255,213,255,127,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,47,0
    .db 6,0,0,0,187,255,59,255,187,255,59,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,48,0
    .db 6,0,0,0,187,255,59,255,187,255,59,255,12,0,1,0
    .db 0,0,28,0,142,255,86,0,12,0,0,0,0,0,49,0
    .db 6,0,0,0,187,255,59,255,187,255,59,255,12,0,1,0
    .db 0,0,28,0,142,255,93,0,12,0,0,0,0,0,50,0
    .db 6,0,0,0,187,255,59,255,187,255,59,255,12,0,1,0
    .db 0,0,240,255,94,255,94,0,12,0,0,0,0,0,51,0
    .db 6,0,0,0,187,255,59,255,187,255,59,255,12,0,1,0
    .db 0,0,240,255,94,255,94,0,12,0,0,0,0,0,52,0
    .db 6,0,0,0,187,255,59,255,187,255,59,255,12,0,1,0
    .db 0,0,196,255,92,255,94,0,13,0,0,0,0,0,53,0
    .db 6,0,0,0,187,255,59,255,187,255,59,255,12,0,1,0
    .db 0,0,196,255,92,255,94,0,13,0,0,0,0,0,54,0
    .db 6,0,0,0,187,255,59,255,187,255,59,255,12,0,1,0
    .db 0,0,187,255,87,255,94,0,238,255,0,0,0,0,55,0
    .db 6,0,0,0,187,255,59,255,187,255,59,255,12,0,1,0
    .db 0,0,187,255,87,255,94,0,238,255,0,0,0,0,56,0
    .db 6,0,0,0,187,255,59,255,187,255,59,255,12,0,1,0
    .db 0,0,187,255,87,255,94,0,238,255,0,0,0,0,57,0
    .db 6,0,0,0,187,255,59,255,187,255,59,255,12,0,1,0
    .db 0,0,187,255,79,255,94,0,219,255,0,0,0,0,58,0
    .db 6,0,0,0,187,255,59,255,187,255,59,255,12,0,1,0
    .db 0,0,187,255,75,255,94,0,196,255,0,0,0,0,59,0
    .db 6,0,0,0,187,255,59,255,187,255,59,255,12,0,1,0
    .db 0,0,187,255,75,255,94,0,196,255,0,0,0,0,60,0
    .db 6,0,0,0,187,255,59,255,187,255,59,255,12,0,1,0
    .db 0,0,187,255,75,255,94,0,196,255,0,0,0,0,61,0
    .db 6,0,0,0,187,255,59,255,187,255,59,255,12,0,1,0
    .db 0,0,187,255,75,255,94,0,196,255,0,0,0,0,62,0
    .db 6,0,0,0,187,255,59,255,187,255,59,255,12,0,1,0
    .db 0,0,187,255,75,255,94,0,196,255,0,0,0,0,63,0
    .db 6,0,0,0,187,255,59,255,187,255,59,255,12,0,1,0
    .db 0,0,187,255,75,255,94,0,196,255,0,0,0,0,64,0
    .db 10,0,0,0,187,255,59,255,187,255,59,255,0,0,0,0
    .db 0,0,187,255,59,255,187,255,59,255,0,0,0,0,65,0
    .db 10,0,0,0,187,255,59,255,187,255,59,255,0,0,0,0
    .db 0,0,187,255,59,255,187,255,59,255,0,0,0,0,66,0
    .db 10,0,0,0,187,255,59,255,187,255,59,255,0,0,0,0
    .db 0,0,187,255,59,255,187,255,59,255,0,0,0,0,67,0
    .db 10,0,0,0,187,255,59,255,187,255,59,255,0,0,0,0
    .db 0,0,187,255,59,255,187,255,59,255,0,0,0,0,68,0
    .db 10,0,0,0,187,255,59,255,187,255,59,255,0,0,0,0
    .db 0,0,187,255,59,255,187,255,59,255,0,0,0,0,69,0
    .db 10,0,0,0,187,255,59,255,187,255,59,255,0,0,0,0
    .db 0,0,187,255,59,255,187,255,59,255,0,0,0,0,70,0
    .db 10,0,0,0,187,255,59,255,187,255,59,255,0,0,0,0
    .db 0,0,187,255,59,255,187,255,59,255,0,0,0,0,71,0
    .db 16,0,1,0,238,255,135,255,17,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,72,0
    .db 16,0,1,0,238,255,135,255,17,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,73,0
    .db 16,0,1,0,238,255,135,255,17,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,74,0
    .db 16,0,1,0,238,255,135,255,17,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,75,0
    .db 16,0,1,0,238,255,135,255,17,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,76,0
    .db 16,0,1,0,238,255,135,255,17,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,77,0
    .db 16,0,1,0,238,255,135,255,17,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,78,0
    .db 16,0,1,0,238,255,135,255,17,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,79,0
    .db 0,0,9,0,112,219,35,0,0,0,0,0,0,0,0,0
    .db 1,0,12,0,144,220,35,0,0,0,0,0,0,0,0,0
    .db 2,0,5,0,16,222,35,0,0,0,0,0,0,0,0,0
    .db 3,0,6,0,176,222,35,1,0,0,0,0,0,0,0,0
    .db 4,0,6,0,112,223,35,0,0,0,0,0,0,0,0,0
    .db 5,0,3,0,48,224,35,0,0,0,0,0,0,0,0,0
    .db 6,0,7,0,144,224,35,0,0,0,0,0,0,0,0,0
    .db 7,0,24,0,112,225,35,0,0,0,0,0,0,0,0,0
    .db 8,0,8,0,112,228,35,1,0,0,0,0,0,0,0,0
    .db 14,0,1,0,243,255,148,255,20,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,10,0,0,0
    .db 14,0,1,0,243,255,148,255,20,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,10,0,1,0
    .db 14,0,1,0,243,255,148,255,20,0,3,0,15,0,0,0
    .db 0,0,15,0,154,255,52,0,189,255,0,0,0,0,2,0
    .db 14,0,1,0,243,255,148,255,20,0,3,0,15,0,0,0
    .db 0,0,15,0,152,255,43,0,184,255,0,0,0,0,3,0
    .db 14,0,1,0,243,255,148,255,20,0,3,0,15,0,0,0
    .db 0,0,15,0,152,255,43,0,184,255,0,0,0,0,4,0
    .db 14,0,1,0,243,255,148,255,20,0,3,0,0,0,0,0
    .db 0,0,210,255,137,255,210,255,137,255,0,0,0,0,5,0
    .db 10,0,1,0,239,255,185,255,35,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,20,0,6,0
    .db 10,0,1,0,229,255,185,255,25,0,2,0,10,0,0,0
    .db 0,0,189,255,197,255,239,255,219,255,0,0,10,0,7,0
    .db 10,0,1,0,246,255,183,255,22,0,2,0,10,0,0,0
    .db 0,0,192,255,157,255,234,255,187,255,0,0,3,0,8,0
    .db 10,0,1,0,243,255,183,255,19,0,2,0,10,0,0,0
    .db 0,0,190,255,186,255,248,255,211,255,0,0,3,0,9,0
    .db 10,0,1,0,243,255,183,255,19,0,2,0,10,0,0,0
    .db 0,0,204,255,153,255,62,0,191,255,0,0,7,0,10,0
    .db 10,0,1,0,230,255,192,255,10,0,2,0,10,0,0,0
    .db 0,0,7,0,136,255,54,0,255,255,0,0,10,0,11,0
    .db 10,0,1,0,240,255,183,255,33,0,2,0,10,0,0,0
    .db 0,0,25,0,183,255,86,0,205,255,0,0,20,0,12,0
    .db 10,0,1,0,231,255,172,255,18,0,212,255,10,0,0,0
    .db 0,0,15,0,187,255,76,0,209,255,0,0,10,0,13,0
    .db 10,0,1,0,240,255,162,255,19,0,2,0,10,0,0,0
    .db 0,0,7,0,193,255,68,0,220,255,0,0,4,0,14,0
    .db 10,0,1,0,243,255,148,255,15,0,2,0,3,0,0,0
    .db 0,0,3,0,193,255,64,0,220,255,0,0,4,0,15,0
    .db 10,0,1,0,246,255,148,255,19,0,2,0,3,0,0,0
    .db 0,0,251,255,193,255,56,0,220,255,0,0,18,0,16,0
    .db 10,0,1,0,186,255,183,255,218,255,2,0,3,0,0,0
    .db 0,0,251,255,193,255,56,0,220,255,0,0,18,0,17,0
    .db 40,0,0,0,176,255,173,255,176,255,173,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,18,0
    .db 40,0,0,0,176,255,173,255,176,255,173,255,12,0,1,0
    .db 0,0,230,255,242,255,32,0,1,0,0,0,0,0,19,0
    .db 40,0,0,0,176,255,173,255,176,255,173,255,12,0,1,0
    .db 0,0,230,255,242,255,32,0,1,0,0,0,0,0,20,0
    .db 40,0,0,0,176,255,173,255,176,255,173,255,12,0,1,0
    .db 0,0,220,255,237,255,29,0,252,255,0,0,0,0,21,0
    .db 40,0,0,0,176,255,173,255,176,255,173,255,12,0,1,0
    .db 0,0,220,255,237,255,29,0,252,255,0,0,0,0,22,0
    .db 20,0,1,0,243,255,149,255,20,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,23,0
    .db 20,0,1,0,243,255,149,255,20,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,24,0
    .db 20,0,1,0,243,255,149,255,20,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,25,0
    .db 20,0,1,0,243,255,149,255,20,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,26,0
    .db 20,0,1,0,243,255,149,255,20,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,27,0
    .db 20,0,1,0,243,255,149,255,20,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,28,0
    .db 20,0,1,0,243,255,149,255,20,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,29,0
    .db 20,0,1,0,243,255,149,255,20,0,3,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,30,0
    .db 24,0,1,0,240,255,149,255,18,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,31,0
    .db 100,0,1,0,240,255,149,255,18,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,32,0
    .db 24,0,1,0,240,255,149,255,18,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,33,0
    .db 30,0,0,0,200,255,139,255,200,255,139,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,34,0
    .db 30,0,0,0,200,255,139,255,200,255,139,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,35,0
    .db 30,0,0,0,200,255,139,255,200,255,139,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,36,0
    .db 30,0,0,0,200,255,139,255,200,255,139,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,37,0
    .db 30,0,0,0,200,255,139,255,200,255,139,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,38,0
    .db 30,0,0,0,200,255,139,255,200,255,139,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,39,0
    .db 14,0,1,0,243,255,148,255,12,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,40,0
    .db 14,0,1,0,243,255,148,255,12,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,41,0
    .db 14,0,1,0,243,255,148,255,12,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,42,0
    .db 14,0,1,0,243,255,148,255,12,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,43,0
    .db 14,0,1,0,243,255,148,255,12,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,44,0
    .db 14,0,1,0,243,255,148,255,12,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,45,0
    .db 14,0,1,0,243,255,148,255,12,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,46,0
    .db 14,0,1,0,243,255,148,255,12,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,47,0
    .db 14,0,1,0,243,255,148,255,12,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,48,0
    .db 14,0,1,0,243,255,148,255,12,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,49,0
    .db 14,0,1,0,243,255,148,255,12,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,50,0
    .db 14,0,1,0,243,255,148,255,12,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,51,0
    .db 0,0,6,0,0,230,35,0,0,0,0,0,0,0,0,0
    .db 1,0,12,0,192,230,35,0,0,0,0,0,0,0,0,0
    .db 2,0,5,0,64,232,35,0,0,0,0,0,0,0,0,0
    .db 3,0,8,0,224,232,35,1,0,0,0,0,0,0,0,0
    .db 4,0,3,0,224,233,35,0,0,0,0,0,0,0,0,0
    .db 5,0,6,0,64,234,35,0,0,0,0,0,0,0,0,0
    .db 6,0,12,0,0,235,35,1,0,0,0,0,0,0,0,0
    .db 16,0,1,0,232,255,139,255,4,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    .db 16,0,1,0,221,255,141,255,249,255,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0
    .db 16,0,1,0,221,255,141,255,249,255,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0
    .db 16,0,1,0,221,255,141,255,249,255,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,0
    .db 16,0,1,0,16,0,169,255,56,0,0,0,20,0,1,0
    .db 0,0,42,0,163,255,69,0,204,255,0,0,0,0,4,0
    .db 16,0,1,0,24,0,164,255,59,0,255,255,20,0,1,0
    .db 0,0,52,0,163,255,79,0,204,255,0,0,0,0,5,0
    .db 16,0,1,0,24,0,156,255,58,0,255,255,0,0,0,0
    .db 0,0,204,255,132,255,204,255,132,255,0,0,0,0,6,0
    .db 16,0,1,0,2,0,147,255,37,0,254,255,0,0,0,0
    .db 0,0,204,255,132,255,204,255,132,255,0,0,0,0,7,0
    .db 16,0,1,0,244,255,140,255,20,0,254,255,0,0,0,0
    .db 0,0,204,255,132,255,204,255,132,255,0,0,0,0,8,0
    .db 12,0,1,0,240,255,140,255,19,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,9,0
    .db 12,0,1,0,241,255,145,255,20,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,3,0,10,0
    .db 12,0,1,0,245,255,153,255,24,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,4,0,11,0
    .db 12,0,1,0,245,255,153,255,24,0,4,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,10,0,12,0
    .db 12,0,1,0,241,255,159,255,20,0,4,0,12,0,0,0
    .db 0,0,255,255,170,255,52,0,199,255,0,0,8,0,13,0
    .db 12,0,1,0,240,255,166,255,21,0,4,0,0,0,0,0
    .db 0,0,156,255,134,255,156,255,134,255,0,0,8,0,14,0
    .db 12,0,1,0,238,255,171,255,19,0,4,0,0,0,0,0
    .db 0,0,148,255,134,255,148,255,134,255,0,0,8,0,15,0
    .db 12,0,1,0,245,255,167,255,25,0,2,0,0,0,0,0
    .db 0,0,160,255,134,255,160,255,134,255,0,0,244,255,16,0
    .db 12,0,1,0,243,255,165,255,23,0,2,0,12,0,1,0
    .db 0,0,18,0,171,255,68,0,186,255,0,0,250,255,17,0
    .db 12,0,1,0,239,255,157,255,20,0,3,0,12,0,1,0
    .db 0,0,209,255,166,255,50,0,183,255,0,0,0,0,18,0
    .db 12,0,1,0,239,255,157,255,20,0,3,0,12,0,1,0
    .db 0,0,168,255,161,255,244,255,175,255,0,0,0,0,19,0
    .db 12,0,1,0,233,255,157,255,14,0,3,0,0,0,0,0
    .db 0,0,166,255,134,255,166,255,134,255,0,0,0,0,20,0
    .db 12,0,1,0,241,255,157,255,22,0,3,0,0,0,0,0
    .db 0,0,166,255,134,255,166,255,134,255,0,0,0,0,21,0
    .db 12,0,1,0,240,255,149,255,22,0,2,0,0,0,0,0
    .db 0,0,156,255,134,255,156,255,134,255,0,0,10,0,22,0
    .db 12,0,1,0,241,255,141,255,19,0,1,0,0,0,0,0
    .db 0,0,150,255,134,255,150,255,134,255,0,0,6,0,23,0
    .db 12,0,1,0,241,255,141,255,19,0,1,0,0,0,0,0
    .db 0,0,150,255,134,255,150,255,134,255,0,0,0,0,24,0
    .db 12,0,1,0,241,255,141,255,19,0,1,0,0,0,0,0
    .db 0,0,150,255,134,255,150,255,134,255,0,0,0,0,25,0
    .db 12,0,1,0,241,255,141,255,19,0,1,0,0,0,0,0
    .db 0,0,150,255,134,255,150,255,134,255,0,0,0,0,26,0
    .db 6,0,1,0,244,255,147,255,30,0,254,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,27,0
    .db 6,0,1,0,244,255,147,255,30,0,254,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,28,0
    .db 6,0,1,0,6,0,139,255,42,0,1,0,7,0,1,0
    .db 0,0,38,0,147,255,110,0,207,255,0,0,0,0,29,0
    .db 6,0,1,0,6,0,139,255,42,0,1,0,7,0,1,0
    .db 0,0,38,0,147,255,110,0,207,255,0,0,0,0,30,0
    .db 6,0,1,0,6,0,139,255,42,0,1,0,7,0,1,0
    .db 0,0,38,0,143,255,175,0,181,255,0,0,0,0,31,0
    .db 6,0,1,0,6,0,139,255,42,0,1,0,7,0,1,0
    .db 0,0,38,0,143,255,175,0,181,255,0,0,0,0,32,0
    .db 6,0,1,0,6,0,139,255,42,0,1,0,7,0,1,0
    .db 0,0,41,0,141,255,138,0,176,255,0,0,0,0,33,0
    .db 6,0,1,0,244,255,147,255,30,0,254,255,7,0,1,0
    .db 0,0,41,0,141,255,138,0,176,255,0,0,0,0,34,0
    .db 6,0,1,0,244,255,147,255,30,0,254,255,7,0,1,0
    .db 0,0,29,0,137,255,82,0,185,255,0,0,0,0,35,0
    .db 6,0,1,0,244,255,147,255,30,0,254,255,0,0,0,0
    .db 0,0,226,255,134,255,226,255,134,255,0,0,0,0,36,0
    .db 16,0,1,0,244,255,147,255,30,0,254,255,0,0,0,0
    .db 0,0,226,255,134,255,226,255,134,255,0,0,0,0,37,0
    .db 16,0,1,0,244,255,147,255,30,0,254,255,0,0,0,0
    .db 0,0,226,255,134,255,226,255,134,255,0,0,0,0,38,0
    .db 16,0,1,0,244,255,147,255,30,0,254,255,0,0,0,0
    .db 0,0,226,255,134,255,226,255,134,255,0,0,0,0,39,0
    .db 16,0,1,0,244,255,147,255,30,0,254,255,0,0,0,0
    .db 0,0,226,255,134,255,226,255,134,255,0,0,0,0,40,0
    .db 20,0,0,0,184,255,170,255,184,255,170,255,15,0,1,0
    .db 0,0,229,255,181,255,19,0,232,255,0,0,0,0,41,0
    .db 20,0,0,0,184,255,170,255,184,255,170,255,15,0,1,0
    .db 0,0,214,255,209,255,49,0,240,255,0,0,0,0,42,0
    .db 20,0,0,0,184,255,170,255,184,255,170,255,15,0,1,0
    .db 0,0,207,255,229,255,54,0,253,255,0,0,0,0,43,0
    .db 20,0,0,0,184,255,170,255,184,255,170,255,15,0,1,0
    .db 0,0,202,255,237,255,56,0,1,0,0,0,0,0,44,0
    .db 24,0,1,0,245,255,138,255,21,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,45,0
    .db 24,0,1,0,245,255,138,255,21,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,46,0
    .db 24,0,1,0,245,255,138,255,21,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,47,0
    .db 24,0,1,0,245,255,138,255,21,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,48,0
    .db 24,0,1,0,245,255,138,255,21,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,49,0
    .db 24,0,1,0,245,255,138,255,21,0,2,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,50,0
    .db 16,0,1,0,231,255,139,255,2,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,51,0
    .db 60,0,1,0,231,255,139,255,2,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,52,0
    .db 16,0,1,0,231,255,139,255,2,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,53,0
    .db 40,0,0,0,211,255,143,255,211,255,143,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,54,0
    .db 40,0,0,0,211,255,143,255,211,255,143,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,55,0
    .db 40,0,0,0,211,255,143,255,211,255,143,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,56,0
    .db 20,0,1,0,247,255,137,255,13,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,57,0
    .db 20,0,1,0,247,255,137,255,13,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,58,0
    .db 20,0,1,0,247,255,137,255,13,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,59,0
    .db 20,0,1,0,247,255,137,255,13,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,60,0
    .db 20,0,1,0,247,255,137,255,13,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,61,0
    .db 20,0,1,0,247,255,137,255,13,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,62,0
    .db 20,0,1,0,247,255,137,255,13,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,63,0
    .db 20,0,1,0,247,255,137,255,13,0,0,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,64,0
    .db 0,0,9,0,240,236,35,0,0,0,0,0,0,0,0,0
    .db 1,0,18,0,16,238,35,0,0,0,0,0,0,0,0,0
    .db 2,0,14,0,80,240,35,0,0,0,0,0,0,0,0,0
    .db 3,0,4,0,16,242,35,0,0,0,0,0,0,0,0,0
    .db 4,0,6,0,144,242,35,1,0,0,0,0,0,0,0,0
    .db 5,0,3,0,80,243,35,0,0,0,0,0,0,0,0,0
    .db 6,0,3,0,176,243,35,0,0,0,0,0,0,0,0,0
    .db 7,0,8,0,16,244,35,1,0,0,0,0,0,0,0,0
    .db 14,0,1,0,234,255,155,255,22,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    .db 14,0,1,0,234,255,155,255,22,0,1,0,10,0,0,0
    .db 0,0,17,0,169,255,71,0,194,255,0,0,0,0,1,0
    .db 14,0,1,0,234,255,155,255,22,0,1,0,0,0,0,0
    .db 0,0,211,255,143,255,211,255,143,255,0,0,0,0,2,0
    .db 40,0,1,0,234,255,155,255,22,0,1,0,0,0,0,0
    .db 0,0,211,255,143,255,211,255,143,255,0,0,0,0,3,0
    .db 40,0,0,0,211,255,86,255,211,255,86,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,4,0
    .db 40,0,0,0,211,255,86,255,211,255,86,255,15,0,1,0
    .db 0,0,252,255,185,255,43,0,233,255,0,0,0,0,5,0
    .db 40,0,0,0,211,255,86,255,211,255,86,255,15,0,1,0
    .db 0,0,229,255,236,255,55,0,7,0,0,0,0,0,6,0
    .db 14,0,1,0,228,255,156,255,23,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,7,0
    .db 14,0,1,0,228,255,156,255,23,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,8,0
    .db 14,0,1,0,228,255,156,255,23,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,9,0
    .db 14,0,1,0,228,255,156,255,23,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,10,0
    .db 14,0,1,0,228,255,156,255,23,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,11,0
    .db 14,0,1,0,228,255,156,255,23,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,12,0
    .db 14,0,1,0,228,255,156,255,23,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,13,0
    .db 14,0,1,0,228,255,156,255,23,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,14,0
    .db 14,0,1,0,228,255,156,255,23,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,15,0
    .db 14,0,1,0,228,255,156,255,23,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,16,0
    .db 14,0,1,0,228,255,156,255,23,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,17,0
    .db 14,0,1,0,228,255,156,255,23,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,18,0
    .db 14,0,1,0,228,255,156,255,23,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,19,0
    .db 14,0,1,0,228,255,156,255,23,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,20,0
    .db 14,0,1,0,228,255,156,255,23,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,21,0
    .db 14,0,1,0,228,255,156,255,23,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,22,0
    .db 24,0,1,0,228,255,156,255,23,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,23,0
    .db 100,0,1,0,228,255,156,255,23,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,24,0
    .db 24,0,1,0,228,255,156,255,23,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,25,0
    .db 20,0,0,0,206,255,147,255,206,255,147,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,26,0
    .db 20,0,0,0,206,255,147,255,206,255,147,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,27,0
    .db 20,0,0,0,206,255,147,255,206,255,147,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,28,0
    .db 20,0,0,0,206,255,147,255,206,255,147,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,29,0
    .db 20,0,0,0,206,255,147,255,206,255,147,255,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,30,0
    .db 14,0,1,0,228,255,156,255,23,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,31,0
    .db 14,0,1,0,228,255,156,255,23,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,32,0
    .db 14,0,1,0,228,255,156,255,23,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,33,0
    .db 14,0,1,0,228,255,156,255,23,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,34,0
    .db 14,0,1,0,228,255,156,255,23,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,35,0
    .db 14,0,1,0,228,255,156,255,23,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,36,0
    .db 14,0,1,0,228,255,156,255,23,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,37,0
    .db 14,0,1,0,228,255,156,255,23,0,1,0,0,0,0,0
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,38,0
    .db 0,0,4,0,144,245,35,0,0,0,0,0,0,0,0,0
    .db 1,0,3,0,16,246,35,0,0,0,0,0,0,0,0,0
    .db 2,0,16,0,112,246,35,1,0,0,0,0,0,0,0,0
    .db 3,0,3,0,112,248,35,0,0,0,0,0,0,0,0,0
    .db 4,0,5,0,208,248,35,0,0,0,0,0,0,0,0,0
    .db 5,0,8,0,112,249,35,1,0,0,0,0,0,0,0,0
    .db 29,0,2,0,255,255,5,0,192,134,35,0,7,0,2,0
    .db 3,0,4,0,0,0,6,0,20,0,90,0,0,128,18,0
    .db 28,0,2,0,255,255,5,0,112,135,35,0,2,0,0,0
    .db 1,0,0,0,0,0,0,0,246,255,80,0,0,128,20,0
    .db 32,0,2,0,255,255,5,0,80,140,35,0,6,0,2,0
    .db 3,0,4,0,0,0,5,0,0,0,130,0,0,128,18,0
    .db 41,0,2,0,255,255,5,0,176,147,35,0,8,0,2,0
    .db 5,0,6,0,0,0,7,0,246,255,80,0,0,128,24,0
    .db 26,0,2,0,255,255,5,0,240,156,35,0,8,0,2,0
    .db 3,0,4,0,0,0,7,0,1,0,90,0,0,128,20,0
    .db 1,0,2,0,255,255,5,0,16,162,35,0,7,0,2,0
    .db 4,0,5,0,0,0,6,0,10,0,90,0,0,128,22,0
    .db 2,0,2,0,255,255,5,0,224,169,35,0,7,0,3,0
    .db 4,0,5,0,0,0,6,0,246,255,80,0,0,128,24,0
    .db 31,0,2,0,255,255,5,0,208,173,35,0,6,0,2,0
    .db 3,0,4,0,0,0,5,0,10,0,70,0,0,128,20,0
    .db 40,0,2,0,255,255,5,0,80,185,35,0,8,0,2,0
    .db 3,0,4,0,0,0,7,0,1,0,90,0,0,128,20,0
    .db 48,0,2,0,255,255,5,0,80,196,35,0,7,0,3,0
    .db 4,0,5,0,0,0,6,0,20,0,100,0,0,128,20,0
    .db 42,0,2,0,255,255,5,0,160,204,35,0,7,0,3,0
    .db 4,0,5,0,0,0,6,0,10,0,120,0,0,128,16,0
    .db 0,0,2,0,255,255,5,0,48,209,35,0,7,0,2,0
    .db 3,0,4,0,0,0,6,0,0,0,70,0,0,128,14,0
    .db 45,0,2,0,255,255,5,0,32,210,35,0,4,0,1,0
    .db 2,0,1,0,1,0,3,0,246,255,80,0,0,128,10,0
    .db 37,0,2,0,255,255,5,0,224,218,35,0,9,0,4,0
    .db 5,0,6,0,0,0,8,0,180,0,44,1,0,128,14,0
    .db 44,0,2,0,255,255,5,0,112,229,35,0,9,0,3,0
    .db 5,0,6,0,0,0,8,0,1,0,100,0,0,128,20,0
    .db 30,0,2,0,255,255,5,0,128,236,35,0,7,0,3,0
    .db 4,0,5,0,0,0,6,0,0,0,60,0,0,128,16,0
    .db 13,0,2,0,255,255,5,0,16,245,35,0,8,0,4,0
    .db 5,0,6,0,0,0,7,0,10,0,70,0,0,128,20,0
    .db 3,0,2,0,255,255,5,0,112,250,35,0,6,0,2,0
    .db 3,0,4,0,0,0,5,0,10,0,80,0,0,128,16,0
    .db 22,0,1,0,255,255,6,0,160,145,34,0,19,0,9,0
    .db 14,0,15,0,0,0,18,0,246,255,80,0,0,128,18,0
    .db 23,0,1,0,255,255,6,0,16,162,34,0,18,0,8,0
    .db 13,0,14,0,0,0,17,0,246,255,80,0,0,128,14,0
    .db 24,0,1,0,255,255,6,0,80,178,34,0,19,0,9,0
    .db 14,0,15,0,0,0,18,0,246,255,80,0,0,128,18,0
    .db 25,0,1,0,255,255,6,0,96,183,34,0,10,0,3,0
    .db 6,0,7,0,3,0,9,0,246,255,80,0,0,128,24,0
    .db 0,25,0,26,0,27,0,28,0,29,0,30
