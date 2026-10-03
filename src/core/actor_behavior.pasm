; Generic live source NONE+WALK adapter. Bank 13; fixture-only activation.
; Zero model flags delegate to the immutable accepted runtime. Flag 1 means
; EXPERIMENTAL_NONE_WALK, NOT a source certificate. Unknown flags or missing spawn provenance
; retire the exact actor with a fault; they NEVER fall back to compatibility.
;
; Fixture patch ABI v1 (ROM labels, never hardcoded file offsets):
; ModelFlags[256] bytes; ModelSpeed[256] u32 in units of 1/2560 source pixel.
; ModelHealth[256] u16: preserved source model health, NOT legacy combat HP.
; SpawnCount u16 <=64; SpawnRecords[64] = stage u8, queue u8, authored X s16.
; The generator must bind a distinct fixture-project catalog identity, its
; own packed blob and directory record, and matching source metadata.
; No runtime model-name, project-name, accepted-ID or visual-alias tests.
;
; Queue lowering: build_spawn_table.py SCALE=256/320, round(worldX*SCALE).
; Keep that quantized initial target position exactly: source X=targetX*3200
; in /2560 units. Source camera uses the same inverse scale. Subsequent
; projection floors signed source X/3200, retaining ALL fractional state.
; Authored X comes from the sidecar, NOT world position or CHAR_FACING_LEFT.
; The S5 primitive owns sign (<160), bounds-before-motion and lifetime.
; Source speed .9 is exactly 2304 units; one PRNG byte gives random*30
; units, i.e. 3*k/256 source pixels. This is a discrete RNG adaptation,
; not a claim of BOR IEEE-float or PRNG bit identity. Motion leaves facing
; independent; experimental bind restores authored queue facing after loading.
;
; Clock: Sagan's rational 200Hz primitive, drift every second tick. Feed
; NTSC noninterlace 357368/357364-master-clock frame intervals selected by
; live STAT78 parity, with Mesen's 21477270 master-clock rate. Pause does not
; accrue simulation time; duplicate committed-frame calls are ignored.
; The host feed has NOT been runtime validated and does NOT catch up missed
; commits. Exact cadence is BLOCKED, as is exact source RNG. Capabilities
; remain PARTIAL; neither this flag nor the primitive's policy selector is
; a SOURCE_CERT, full Crab certificate or production activation authority.
;
; WRAM: per-actor +6..+63 inside the existing 133-byte StageEnv rows;
; row+0..5 remains base/alias state. Shared $7E1800..18FF is serialized
; scratch: above Screen's $162A end, outside OOP $0A00..15FF, below stack.
; It is not interrupt-owned. S5 D=$1800, DBR=0; preserve caller D/DBR/X/Y/P.
; Include the existing Sagan primitive, do not implement a second drift.

ActorBehavior_Start:
ActorBehavior_ModelFlags:
    .fill 256, 0
ActorBehavior_ModelSpeed:
    .fill 1024, 0
ActorBehavior_ModelHealth:
    .fill 512, 0
ActorBehavior_SpawnCount:
    .dw 0
ActorBehavior_SpawnRecords:
    .fill 256, 0
ActorBehavior_ClockLongNumerator:
    .dw $99C0, $0442 ; 357368 * 200
ActorBehavior_ClockShortNumerator:
    .dw $96A0, $0442 ; 357364 * 200
ActorBehavior_ClockDenominator:
    .dw $B796, $0147 ; 21477270 (Poppy .dd is 24-bit, not u32)

ActorBehavior_State = StageEnv_Actors+6       ; 40 bytes: S5 A0..C7
ActorBehavior_Alive = StageEnv_Actors+28      ; S5 B6, word
ActorBehavior_Remainder = StageEnv_Actors+46  ; u32
ActorBehavior_Ticks = StageEnv_Actors+50      ; u32, observed logical ticks
ActorBehavior_LastFrame = StageEnv_Actors+54 ; u16
ActorBehavior_Fault = StageEnv_Actors+56     ; 0 or 1 invalid binding
ActorBehavior_Samples = StageEnv_Actors+58   ; u16 (one on successful bind)
ActorBehavior_SourceHealth = StageEnv_Actors+60 ; preserved u16 model stat
ActorBehavior_CompatRoster = StageEnv_Actors+62 ; valid bit $100 + prior ID
ActorBehavior_Context = $1800
ActorBehavior_Row = $7E1812

; A8/I16. The only two bank-0 life gates use these, preserving their
; different player/static exemptions. Return A8/Z, preserve X/Y/D/DBR.
ActorBehavior_AnimationAlive:
    sep #$20
.a8
    lda CHAR_INPUT_DRIVEN
    cmp #2
    bcc ActorBehavior_AliveExempt
    jml ActorBehavior_EntityAlive
ActorBehavior_RenderAlive:
    sep #$20
.a8
    lda CHAR_INPUT_DRIVEN
    cmp #1
    bcc ActorBehavior_AliveExempt
    jml ActorBehavior_EntityAlive
ActorBehavior_AliveExempt:
    .a8
    lda #1
    rtl
ActorBehavior_EntityAlive:
    .a8
.i16
    cmp #CHAR_INPUT_DRIVEN_NONCOMBAT
    beq ActorBehavior_EntityAlive__source
    lda CHAR_HP
    rtl
ActorBehavior_EntityAlive__source:
    rep #$20
.a16
    phx
    tdc
    sec
    sbc #$0A00
    tax
    sep #$20
.a8
    lda.l ActorBehavior_Alive,x
    plx
    ora #0
    rtl

; Queue allocation needs occupancy, not health. Other health consumers
; deliberately continue seeing zero (damage, grabs, score, enemy counts).
ActorBehavior_Slot1Busy:
    .a8
.i16
    phx
    ldx #CHAR_ZP_LEN
    bra ActorBehavior_SlotBusy
ActorBehavior_Slot2Busy:
    .a8
.i16
    phx
    ldx #CHAR_ZP_LEN*2
    bra ActorBehavior_SlotBusy
ActorBehavior_Slot3Busy:
    .a8
.i16
    phx
    ldx #CHAR_ZP_LEN*3
    bra ActorBehavior_SlotBusy
ActorBehavior_Slot4Busy:
    .a8
.i16
    phx
    ldx #CHAR_ZP_LEN*4
    bra ActorBehavior_SlotBusy
ActorBehavior_Slot5Busy:
    .a8
.i16
    phx
    ldx #CHAR_ZP_LEN*5
ActorBehavior_SlotBusy:
    .a8
.i16
    lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
    cmp #CHAR_INPUT_DRIVEN_NONCOMBAT
    bne ActorBehavior_SlotBusy__hp
    lda.l ActorBehavior_Alive,x
    bne ActorBehavior_SlotBusy__done
    ; Reuse can need a catalog restore even for an ordinary enemy record.
    lda.l Msu1_StreamBusy
    bra ActorBehavior_SlotBusy__done
ActorBehavior_SlotBusy__hp:
    .a8
    lda.l $7E0A00+CHAR_HP,x
ActorBehavior_SlotBusy__done:
    .a8
    plx
    ora #0
    rtl

; Capture the prior compatibility identity before an experimental load.
; No model identity is inferred from an actor number or an asset alias.
ActorBehavior_CaptureRoster:
    php
    rep #$30
.a16
.i16
    phx
    lda.l Spawn_ScratchRosterIdx
    and #$00FF
    tax
    sep #$20
.a8
    lda.l ActorBehavior_ModelFlags,x
    beq ActorBehavior_CaptureRoster__done
    rep #$20
.a16
    lda CHAR_ROSTER_INDEX
    and #$00FF
    tax
    sep #$20
.a8
    lda.l ActorBehavior_ModelFlags,x
    bne ActorBehavior_CaptureRoster__done
    rep #$20
.a16
    txa
    ora #$0100
    pha
    tdc
    sec
    sbc #$0A00
    tax
    pla
    sta.l ActorBehavior_CompatRoster,x
ActorBehavior_CaptureRoster__done:
    rep #$30
.a16
.i16
    plx
    plp
    rtl

; Stage resets clear environmental state but must not lose the catalog
; backup of a source occupant. $18E8..18F3 is synchronous reset scratch.
ActorBehavior_PreserveRoster:
    php
    rep #$30
.a16
.i16
    phx
    phy
    phb
    sep #$20
.a8
    lda #0
    pha
    plb
    rep #$30
.a16
.i16
    ldx #0
    ldy #0
ActorBehavior_PreserveRoster__loop:
    .a16
.i16
    lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
    and #$00FF
    cmp #CHAR_INPUT_DRIVEN_NONCOMBAT
    beq ActorBehavior_PreserveRoster__source
    lda #0
    bra ActorBehavior_PreserveRoster__store
ActorBehavior_PreserveRoster__source:
    .a16
    lda.l ActorBehavior_CompatRoster,x
ActorBehavior_PreserveRoster__store:
    .a16
.i16
    sta $18E8,y
    iny
    iny
    txa
    clc
    adc #CHAR_ZP_LEN
    tax
    cpx #CHAR_ZP_LEN*6
    bcc ActorBehavior_PreserveRoster__loop
    plb
    ply
    plx
    plp
    rtl
ActorBehavior_RestoreRoster:
    jsl HudOpponent_Reset
    php
    rep #$30
.a16
.i16
    phx
    phy
    phb
    sep #$20
.a8
    lda #0
    pha
    plb
    rep #$30
.a16
.i16
    ldx #0
    ldy #0
ActorBehavior_RestoreRoster__loop:
    .a16
.i16
    lda $18E8,y
    sta.l ActorBehavior_CompatRoster,x
    iny
    iny
    txa
    clc
    adc #CHAR_ZP_LEN
    tax
    cpx #CHAR_ZP_LEN*6
    bcc ActorBehavior_RestoreRoster__loop
    plb
    ply
    plx
    plp
    rtl

; Slots 4/5 can retain old art on ordinary spawns. If it is fixture art,
; restore the captured catalog before palette binding. Other slots already
; perform their legacy restore; their actual catalog flag is now zero.
ActorBehavior_RestoreCompat:
    php
    rep #$31
.a16
.i16
    phx
    phy
    lda.l Spawn_B2Roster
    and #$00FF
    tax
    sep #$20
.a8
    lda.l ActorBehavior_ModelFlags,x
    bne ActorBehavior_RestoreCompat__done
    rep #$20
.a16
    lda CHAR_ROSTER_INDEX
    and #$00FF
    tax
    sep #$20
.a8
    lda.l ActorBehavior_ModelFlags,x
    beq ActorBehavior_RestoreCompat__done
    rep #$20
.a16
    tdc
    sec
    sbc #$0A00
    tax
    lda.l ActorBehavior_CompatRoster,x
    and #$0100
    bne ActorBehavior_RestoreCompat__valid
    ; Missing provenance cannot choose a guessed compatibility identity.
    jsl Queue_CapacityFault
ActorBehavior_RestoreCompat__valid:
    sep #$20
.a8
    lda.l ActorBehavior_CompatRoster,x
    sta.l Spawn_ScratchRosterIdx
    jsl Spawn_DoRosterReassign_Long
ActorBehavior_RestoreCompat__done:
    rep #$30
.a16
.i16
    ply
    plx
    plp
    rtl

; Called after final catalog load and map application, D=spawned actor.
ActorBehavior_Bind:
    php
    rep #$31
.a16
.i16
    phx
    phy
    phb
    phd
    tdc
    sec
    sbc #$0A00
    tax
    lda #0
    sta.l ActorBehavior_Alive,x
    sta.l ActorBehavior_Fault,x
    sta.l ActorBehavior_Samples,x
    sta.l ActorBehavior_SourceHealth,x
    lda.l Spawn_B2Roster
    and #$00FF
    tax
    sep #$20
.a8
    lda.l ActorBehavior_ModelFlags,x
    bne ActorBehavior_Bind__exact
    brl ActorBehavior_Return
ActorBehavior_Bind__exact:
    .a8
    ; CHAR_HP is only the legacy combat/clear counter here. Source health
    ; lives in ActorBehavior_SourceHealth; preserving this one stat does
    ; not certify full STATS/defaults/health-override semantics.
    pha
    lda #CHAR_INPUT_DRIVEN_NONCOMBAT
    sta CHAR_INPUT_DRIVEN
    stz CHAR_HP
    stz CHAR_PICKUP_TYPE
    stz CHAR_HIT_STUN
    stz CHAR_HIT_APPLIED
    stz CHAR_SELECTED
    rep #$20
.a16
    stz CHAR_THROW_ZPOS
    stz CHAR_THROW_ZVEL
    sep #$20
.a8
    pla
    cmp #1
    beq ActorBehavior_Bind__flag_ok
    brl ActorBehavior_Bind__bad_actor
ActorBehavior_Bind__flag_ok:
    .a8
    lda CHAR_ROSTER_INDEX
    cmp.l Spawn_B2Roster
    beq ActorBehavior_Bind__identity_ok
    brl ActorBehavior_Bind__bad_actor
ActorBehavior_Bind__identity_ok:
    .a8
    lda CHAR_WALK_FCOUNT
    bne ActorBehavior_Bind__walk_ok
    brl ActorBehavior_Bind__bad_actor
ActorBehavior_Bind__walk_ok:
    .a8
    ; Catalog loading resets facing after Spawn_Play stamped the queue value.
    ; Restore it only for this validated experimental binding. Velocity sign
    ; still comes exclusively from authored source X; zero flags skip this.
    lda.l Spawn_ScratchFacing
    sta CHAR_FACING_LEFT
    lda #1
    sta CHAR_SELECTED
    lda #$FF
    sta CHAR_FRAME_INDEX
    lda #1
    sta CHAR_TICK_COUNTER
    rep #$30
.a16
.i16
    tdc
    sec
    sbc #$0A00
    sta.l ActorBehavior_Row
    lda CHAR_POS_X
    sta.l $7E1814
    lda CHAR_ROSTER_INDEX
    and #$00FF
    asl a
    tax
    lda.l ActorBehavior_ModelHealth,x
    pha
    lda.l ActorBehavior_Row
    tax
    pla
    sta.l ActorBehavior_SourceHealth,x
    lda CHAR_ROSTER_INDEX
    and #$00FF
    asl a
    asl a
    sta.l $7E1816
    sep #$20
.a8
    lda #0
    pha
    plb
    rep #$30
.a16
.i16
    lda #ActorBehavior_Context
    tcd
    ; Clear the primitive's whole drift state, not another actor's state.
    ldx #$A0
ActorBehavior_Bind__clear:
    .a16
.i16
    stz $00,x
    inx
    inx
    cpx #$C8
    bcc ActorBehavior_Bind__clear
    stz $00
    stz $02
    stz $04
    stz $06
    stz $0C
    stz $0E
    stz $2C
    ; Internal S5 equation-selection ABI only; not a source certification.
    lda #1
    sta $E0
    sta $B4
    lda $14
    jsr ActorBehavior_TargetToSource
    lda $20
    sta $A0
    lda $22
    sta $A2
    ldx $16
    lda.l ActorBehavior_ModelSpeed,x
    sta $AC
    lda.l StageEnv_DataBank+ActorBehavior_ModelSpeed+2,x
    sta $AE
    ora $AC
    beq ActorBehavior_Bind__bad
    lda.l ActorBehavior_SpawnCount
    cmp #65
    bcs ActorBehavior_Bind__bad
    asl a
    asl a
    sta $18
    ldx #0
ActorBehavior_Bind__find:
    .a16
.i16
    cpx $18
    bcs ActorBehavior_Bind__bad
    sep #$20
.a8
    lda.l ActorBehavior_SpawnRecords,x
    cmp.l Game_StageIndex
    bne ActorBehavior_Bind__next
    lda.l StageEnv_DataBank+ActorBehavior_SpawnRecords+1,x
    cmp.l Spawn_Index
    bne ActorBehavior_Bind__next
    rep #$20
.a16
    lda.l StageEnv_DataBank+ActorBehavior_SpawnRecords+2,x
    sta $B0
    jsl S5_DriftBind
    lda $B6
    beq ActorBehavior_Bind__bad
    ldx $12
    lda #1
    sta.l ActorBehavior_Samples,x
    lda.l Nmi_FrameCounter
    ; Spawn's first actor pass may share this frame: allow it one tick batch.
    dec a
    sta.l ActorBehavior_LastFrame,x
    jsr ActorBehavior_Save
    brl ActorBehavior_Return
ActorBehavior_Bind__next:
    rep #$20
.a16
    inx
    inx
    inx
    inx
    bra ActorBehavior_Bind__find
ActorBehavior_Bind__bad:
    rep #$30
.a16
.i16
    ldx $12
    lda #1
    sta.l ActorBehavior_Fault,x
    brl ActorBehavior_Return
ActorBehavior_Bind__bad_actor:
    rep #$30
.a16
.i16
    tdc
    sec
    sbc #$0A00
    tax
    lda #1
    sta.l ActorBehavior_Fault,x
    brl ActorBehavior_Return

; A=signed16 target world/camera X. Return s32 source units at 20/22.
; Fixture coordinates/camera must fit the engine's signed16 world domain.
; 3200 = $0C80. Software shift/add avoids shared hardware multiply state.
ActorBehavior_TargetToSource:
    .a16
.i16
    sta $24
    stz $26
    cmp #$8000
    bcc ActorBehavior_TargetToSource__nonnegative
    lda #$FFFF
    sta $26
ActorBehavior_TargetToSource__nonnegative:
    .a16
.i16
    stz $20
    stz $22
    ldy #12
    lda #3200
    sta $28
ActorBehavior_TargetToSource__bit:
    .a16
.i16
    lsr $28
    bcc ActorBehavior_TargetToSource__shift
    lda $20
    clc
    adc $24
    sta $20
    lda $22
    adc $26
    sta $22
ActorBehavior_TargetToSource__shift:
    .a16
.i16
    asl $24
    rol $26
    dey
    bne ActorBehavior_TargetToSource__bit
    rts

ActorBehavior_Think:
    php
    rep #$31
.a16
.i16
    phx
    phy
    phb
    phd
    tdc
    sec
    sbc #$0A00
    tax
    lda.l ActorBehavior_Alive,x
    bne ActorBehavior_Think__live
    brl ActorBehavior_Return
ActorBehavior_Think__live:
    .a16
.i16
    lda.l Nmi_FrameCounter
    cmp.l ActorBehavior_LastFrame,x
    bne ActorBehavior_Think__new_frame
    brl ActorBehavior_Return
ActorBehavior_Think__new_frame:
    .a16
.i16
    sta.l ActorBehavior_LastFrame,x
    txa
    sta.l ActorBehavior_Row
    sep #$20
.a8
    lda #0
    pha
    plb
    rep #$30
.a16
.i16
    lda #ActorBehavior_Context
    tcd
    ldy #0
ActorBehavior_Think__load:
    .a16
.i16
    lda.l ActorBehavior_State,x
    sta $18A0,y
    inx
    inx
    iny
    iny
    cpy #40
    bcc ActorBehavior_Think__load
    ldx $12
    lda.l ActorBehavior_Remainder,x
    sta $04
    lda.l ActorBehavior_Remainder+2,x
    sta $06
    lda.l ActorBehavior_Ticks,x
    sta $0C
    lda.l ActorBehavior_Ticks+2,x
    sta $0E
    lda.l Screen_PosX
    jsr ActorBehavior_TargetToSource
    lda $20
    sta $A8
    lda $22
    sta $AA
    lda.l ActorBehavior_ClockDenominator
    sta $08
    lda.l StageEnv_DataBank+ActorBehavior_ClockDenominator+2
    sta $0A
    sep #$20
.a8
    lda.l $00213F              ; actual MMIO, not a debugger register peek
    bmi ActorBehavior_Think__short_frame
    rep #$20
.a16
    lda.l ActorBehavior_ClockLongNumerator
    sta $00
    lda.l StageEnv_DataBank+ActorBehavior_ClockLongNumerator+2
    bra ActorBehavior_Think__clock_ready
ActorBehavior_Think__short_frame:
    rep #$20
.a16
    lda.l ActorBehavior_ClockShortNumerator
    sta $00
    lda.l StageEnv_DataBank+ActorBehavior_ClockShortNumerator+2
ActorBehavior_Think__clock_ready:
    .a16
    sta $02
    jsl S5_ClockAdvance
ActorBehavior_Think__project:
    .a16
.i16
    jsr ActorBehavior_Save
    ; Signed floor division by 3200, full 32-bit dividend; quotient low
    ; word is the engine's signed/wrapping world coordinate representation.
    lda $A0
    sta $20
    lda $A2
    sta $22
    stz $2A
    bpl ActorBehavior_Think__positive
    inc $2A
    lda #0
    sec
    sbc $20
    sta $20
    lda #0
    sbc $22
    sta $22
ActorBehavior_Think__positive:
    .a16
.i16
    stz $24
    stz $26
    ldy #32
ActorBehavior_Think__divide:
    .a16
.i16
    asl $20
    rol $22
    rol $24
    asl $26
    lda $24
    cmp #3200
    bcc ActorBehavior_Think__divide_next
    sbc #3200
    sta $24
    inc $26
ActorBehavior_Think__divide_next:
    .a16
.i16
    dey
    bne ActorBehavior_Think__divide
    lda $2A
    beq ActorBehavior_Think__store_position
    lda #0
    sec
    sbc $26
    sta $26
    lda $24
    beq ActorBehavior_Think__store_position
    dec $26
ActorBehavior_Think__store_position:
    .a16
.i16
    ldx $12
    lda $26
    sta.l $7E0A00+CHAR_POS_X,x
    ; Do not change facing: flip is independent of source drift direction.
ActorBehavior_Return:
    rep #$30
.a16
.i16
    pld
    plb
    ply
    plx
    plp
    rtl

ActorBehavior_Save:
    .a16
.i16
    ldx $12
    ldy #0
ActorBehavior_Save__loop:
    .a16
.i16
    lda $18A0,y
    sta.l ActorBehavior_State,x
    inx
    inx
    iny
    iny
    cpy #40
    bcc ActorBehavior_Save__loop
    ldx $12
    lda $04
    sta.l ActorBehavior_Remainder,x
    lda $06
    sta.l ActorBehavior_Remainder+2,x
    lda $0C
    sta.l ActorBehavior_Ticks,x
    lda $0E
    sta.l ActorBehavior_Ticks+2,x
    lda.l ActorBehavior_Alive,x
    bne ActorBehavior_Save__alive
    jsl HudOpponentHost_RetireX
ActorBehavior_Save__alive:
    rts

S5_HostRandom03:
    sep #$20
.a8
    jsl Core_Random_Get
    rep #$20
.a16
    and #$00FF
    sta $30
    asl a
    sta $32
    asl a
    asl a
    asl a
    asl a
    sec
    sbc $32
    sta $BE
    rtl

S5_HostSourceTick:
    rep #$30
.a16
.i16
    lda $0C
    and #1
    bne S5_HostSourceTick__done
    jsl S5_DriftTick
S5_HostSourceTick__done:
    .a16
.i16
    rtl

; Legacy child admission reads HP directly in jump.pasm. Only during that
; synchronous call, expose live noncombat occupancy as HP=1; restore zero
; before any actor combat/clear work resumes. No changes to the emitter's
; RNG, animation or admission rules for accepted actors.
ActorBehavior_EmitterThink:
    php
    rep #$30
.a16
.i16
    phx
    phy
    lda #1
    jsr ActorBehavior_ProtectOccupancy
    jsl Anim_SteamerThink
    rep #$30
.a16
.i16
    lda #0
    jsr ActorBehavior_ProtectOccupancy
    ply
    plx
    plp
    rtl
ActorBehavior_ProtectOccupancy:
    .a16
.i16
    tay
    ldx #CHAR_ZP_LEN
ActorBehavior_ProtectOccupancy__loop:
    sep #$20
.a8
    lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
    cmp #CHAR_INPUT_DRIVEN_NONCOMBAT
    bne ActorBehavior_ProtectOccupancy__next
    lda.l ActorBehavior_Alive,x
    beq ActorBehavior_ProtectOccupancy__next
    tya
    sta.l $7E0A00+CHAR_HP,x
ActorBehavior_ProtectOccupancy__next:
    rep #$30
.a16
.i16
    txa
    clc
    adc #CHAR_ZP_LEN
    tax
    cpx #CHAR_ZP_LEN*6
    bcc ActorBehavior_ProtectOccupancy__loop
    rts

.include "actor_s5_isolated.pasm"
.include "actor_s5_clock_isolated.pasm"
ActorBehavior_End:
