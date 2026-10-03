; BOR.C 2591 checkhole, 2732 update_ents, 3104 player_move, 3997 common_move.
; Isolated compatibility-actor implementation; no catalog/model identity tests.
; Main supplies StageBounds_Records/RecordCount/DataBank from stage_bounds.py.
; Table and all 16-byte records must remain in the declared ROM bank.
;
; API: active actor D=$0A00+slot*CHAR_ZP_LEN, DBR unchanged. A/X/Y clobbered;
; all entries return A16/I16; binary arithmetic is required. CheckEndHole returns C; other
; routines return C set while a pit owns the actor. Call Enter once after
; gravity if base=0 and grounded; Tick once per source 100Hz gravity event,
; NEVER once per render. Active actors bypass compat AI/motion/throw gravity.
; Normal ACCEPTED_COMPAT stays ~60Hz. Main consumes floor(clock200/2)
; deltas from Dewey's clock (including remainder across frames); this is NOT
; an S6 source-world driver. Tick BEFORE Enter at each actor gravity event.
; Grounded boolean: base fraction/integer both 0 and abs(Q8.8 altitude)<=20,
; exactly source abs(a-base)<.1 after inverse 4/5 scaling. No velocity gate.
; Enter C=1 means pit owns actor (already active OR newly entered); C=0
; means no entry/ownership. CheckEndHole C=1 is geometry ONLY, at any height.
; Clamp runs only at BOR player_move/common_move bounds sites, not for every
; projectile/emitter. Render runs after Jump/StageEnv Y offsets and OBJ attrs,
; before any sprite is submitted. C set also means suppress shadow/mirror.
;
; WRAM ownership audit: StageEnv row +0..5 base/alias, +6..63 ActorBehavior,
; +64..73 S6Bridge, +74..87 S6Host. This module reserves +88..101 in all six
; 133-byte rows ($7E5567..5574 through $7E5800..580D, strided, NOT contiguous).
; StageEnv_ResetActors already clears all rows. ResetActor is additionally
; REQUIRED on each slot reuse and P1/P2 respawn, after old state is retired.
; No global scratch, no timer state, no new DP cells. NMI must not call these.
; Exact geometry is over inverse-scaled existing integer coordinates; original
; fractions lost by the accepted queue cannot be reconstructed.
;
; Exact shared-file integration checklist (main agent owns these edits):
; 1. Include this code in a bank with headroom and generated records in their
;    declared bank. Emit a None/zero row for every unaffected physical stage.
;    Use compiler StageIR, not converted BG width or physical-stage numbers.
; 2. Spawn_Play__slot45 / P1 and P2 respawn: ResetActor with the PHYSICAL
;    actor D before StageEnv_ApplySpawnBase. Never call under a temporary P2
;    alias D; resolve the physical slot first. StageEnv_ResetActors handles
;    stage-wide reset already, but does not replace per-slot respawn reset.
; 3. Character_PlayFrame__store_y, after both axis clamps: Clamp for actors
;    running player/common movement. At the source gravity phase run Tick
;    then Enter; C=1 bypasses ordinary Character_PlayFrame movement, AI and
;    Jump/Throw gravity without disabling the render pass. Do not route C=1
;    through __hold -> ordinary Y clamp (that would undo behind-panel depth).
; 4. Spawn_CheckHole: query CheckEndHole before ordinary holes/depth>=156;
;    preserve type2 by routing to Enter, NOT Anim_EnterHole. Pure predicate
;    queries from AI/shadows must not mutate lifecycle or award damage.
; 5. Character_RenderFrame: Render after Jump_ApplyOamYOffset and palette/
;    flip composition, before Core_Oam submission (and after compat blink
;    overrides). C=1 suppresses shadows/mirrors. OBJ priority0 is required
;    in addition to depth123; depth sorting alone cannot hide behind BG1.
; 6. Supply StageBounds_ApplyPitDamage_Long, D=physical actor, A16=10000.
;    Dispatch takedamage/kill semantics through the accepted actor owner,
;    including grab/drop/boss/HUD removal and P1/P2 death/life accounting.
;    State2 is already latched: do not call Tick again as a damage retry.
;    Return with D/DBR preserved; other registers may be clobbered. Do not
;    merely hide OAM or clear a source actor's compatibility HP projection.
;    Leave state2 until actual removal/reuse; ResetActor starts the new life.
; Tests expose snapshot_checks() for boundary, entry, retired and reset data.
StageBounds_State = StageEnv_Actors+88       ; u16 0=normal,1=falling,2=retired
StageBounds_Height = StageEnv_Actors+90      ; s16 in 1/25 target pixel
StageBounds_Velocity = StageEnv_Actors+92    ; s16, same units/gravity tick
StageBounds_DrawY = StageEnv_Actors+94       ; signed cached screen foot Y
StageBounds_Scratch = StageEnv_Actors+96     ; transient owner-local word
StageBounds_Slot = StageEnv_Actors+98        ; transient unlink self slot ID
StageBounds_EntryDepth = StageEnv_Actors+100 ; source projection at entry
StageBounds_GrabTargets = $7E0A00+CHAR_GRAB_TARGET
StageBounds_GrabbedBy = $7E0A00+CHAR_GRABBED_BY

StageBounds_Row:
    rep #$31
.a16
.i16
    tdc
    sec
    sbc #$0A00
    tax
    rtl

StageBounds_ResetActor:
.a16
.i16
    jsl StageBounds_Row
    lda #0
    sta.l StageBounds_State,x
    sta.l StageBounds_Height,x
    sta.l StageBounds_Velocity,x
    sta.l StageBounds_DrawY,x
    sta.l StageBounds_Scratch,x
    sta.l StageBounds_Slot,x
    sta.l StageBounds_EntryDepth,x
    ; A previous pit lowered this same owner's base. Spawn-base binding
    ; must follow this reset if the new model has an authored nonzero base.
    sta.l StageEnv_BaseFraction,x
    sta.l StageEnv_BaseInteger,x
    clc
    rtl

StageBounds_IsActive:
    jsl StageBounds_Row
    lda.l StageBounds_State,x
    beq StageBounds_False
    sec
    rtl
StageBounds_False:
    clc
    rtl

; Carry clear for absent metadata. A16/I16, X=physical record byte offset.
StageBounds_Record:
    rep #$31
.a16
.i16
    lda.l Game_StageIndex
    and #$00FF
    cmp #StageBounds_RecordCount
    bcs StageBounds_False
    asl a
    asl a
    asl a
    asl a
    tax
    sec
    rtl

StageBounds_Clamp:
.a16
.i16
    jsl StageBounds_IsActive
    bcs StageBounds_Clamp__done
    jsl StageBounds_Record
    bcc StageBounds_Clamp__done
    lda.l StageBounds_Records,x
    and #1
    beq StageBounds_Clamp__done
    lda CHAR_POS_Y
    and #$00FF
    clc
    adc.l StageBounds_DataBank+StageBounds_Records+2,x
    cmp CHAR_POS_X
    bcs StageBounds_Clamp__done
    sta CHAR_POS_X
StageBounds_Clamp__done:
    jml StageBounds_IsActive

; Pure source checkhole(int,int) exit test: works for airborne shadow/AI
; queries too. Ground/base checks belong to Enter, not this predicate.
StageBounds_CheckEndHole:
.a16
.i16
    jsl StageBounds_Record
    bcc StageBounds_CheckEndHole__no
    lda.l StageBounds_Records,x
    and #2
    beq StageBounds_CheckEndHole__no
    txa
    tay
    lda CHAR_POS_Y
    and #3
    asl a
    pha
    tya
    clc
    adc 1,s
    tax
    pla
    lda CHAR_POS_Y
    and #$00FF
    clc
    adc.l StageBounds_DataBank+StageBounds_Records+4,x
    cmp CHAR_POS_X
    bcc StageBounds_CheckEndHole__yes
    beq StageBounds_CheckEndHole__yes
StageBounds_CheckEndHole__no:
    clc
    rtl
StageBounds_CheckEndHole__yes:
    sec
    rtl

StageBounds_Enter:
    jsl StageBounds_IsActive
    bcc StageBounds_Enter__idle
    rtl
StageBounds_Enter__idle:
.a16
.i16
    lda.l StageEnv_BaseFraction,x
    ora.l StageEnv_BaseInteger,x
    bne StageBounds_Enter__no
    lda CHAR_THROW_ZPOS
    bpl StageBounds_Enter__altitude_magnitude
    eor #$FFFF
    inc a
StageBounds_Enter__altitude_magnitude:
.a16
    cmp #21
    bcs StageBounds_Enter__no
StageBounds_Enter__ground:
.a16
.i16
    jsl StageBounds_CheckEndHole
    bcs StageBounds_Enter__begin
StageBounds_Enter__no:
    clc
    rtl
StageBounds_Enter__begin:
.a16
.i16
    jsl StageBounds_Row
    lda CHAR_POS_Y
    and #$00FF
    sta.l StageBounds_EntryDepth,x
    ; Exact scaled panel depth is 123.2. Y is its integer projection 123;
    ; altitude in /25 units retains the .2 and preserves floor(screen Y).
    sta.l StageBounds_Scratch,x
    asl a
    asl a
    clc
    adc.l StageBounds_Scratch,x
    asl a
    asl a
    clc
    adc.l StageBounds_Scratch,x
    ; Above computes depth*21; add depth*4 to get depth*25.
    pha
    lda.l StageBounds_Scratch,x
    asl a
    asl a
    clc
    adc 1,s
    sta.l StageBounds_Scratch,x
    pla
    lda #3080
    sec
    sbc.l StageBounds_Scratch,x
    sta.l StageBounds_Height,x
    lda CHAR_THROW_ZPOS
    jsr StageBounds_ImportQ8
    clc
    adc.l StageBounds_Height,x
    sta.l StageBounds_Height,x
    ; BOR retains tossv when entering a hole, including a landing's negative
    ; velocity. Convert the existing Q8.8 velocity once, truncating to /25.
    lda CHAR_THROW_ZVEL
    jsr StageBounds_ImportQ8
    sta.l StageBounds_Velocity,x
    lda #0
    sta.l StageEnv_BaseFraction,x
    sta CHAR_THROW_ZPOS
    sta CHAR_THROW_ZVEL
    lda #$FCE0                    ; source base -1000 scaled to -800
    sta.l StageEnv_BaseInteger,x
    lda #123
    sta CHAR_POS_Y
    lda #1
    sta.l StageBounds_State,x
    jsl StageBounds_Unlink
    jsl StageBounds_CacheY
    sec
    rtl
; Unlink both directions, including being somebody else's victim. No new
; actor allocation or slot identity lookup. X initially owns this actor row.
StageBounds_Unlink:
.a16
.i16
    jsl StageBounds_Row
    txa
    ldy #0
StageBounds_Unlink__slot:
.a16
.i16
    cmp #CHAR_ZP_LEN
    bcc StageBounds_Unlink__have_slot
    sec
    sbc #CHAR_ZP_LEN
    iny
    bra StageBounds_Unlink__slot
StageBounds_Unlink__have_slot:
.a16
.i16
    tya
    sta.l StageBounds_Slot,x
    pha
    ldx #0
StageBounds_Unlink__scan:
.a16
.i16
    lda.l StageBounds_GrabTargets,x
    and #$00FF
    cmp 1,s
    bne StageBounds_Unlink__victim
    sep #$20
.a8
    lda #$FF
    sta.l StageBounds_GrabTargets,x
StageBounds_Unlink__victim:
    rep #$20
.a16
    lda.l StageBounds_GrabbedBy,x
    and #$00FF
    cmp 1,s
    bne StageBounds_Unlink__next
    sep #$20
.a8
    lda #$FF
    sta.l StageBounds_GrabbedBy,x
StageBounds_Unlink__next:
    rep #$30
.a16
.i16
    txa
    clc
    adc #CHAR_ZP_LEN
    tax
    cpx #CHAR_ZP_LEN*6
    bcc StageBounds_Unlink__scan
    pla
    sep #$20
.a8
    lda #$FF
    sta CHAR_GRAB_TARGET
    sta CHAR_GRABBED_BY
    jml StageBounds_Row

; Exactly one source gravity event; caller's shared clock owns cadence.
; A falling actor may animate but may not run ordinary AI/position/gravity.
StageBounds_Tick:
.a16
.i16
    jsl StageBounds_IsActive
    bcc StageBounds_Tick__done
    lda.l StageBounds_State,x
    cmp #2
    beq StageBounds_Tick__owned
    lda.l StageBounds_Height,x
    clc
    adc.l StageBounds_Velocity,x
    sta.l StageBounds_Height,x
    lda.l StageBounds_Velocity,x
    bpl StageBounds_Tick__accelerate
    cmp #$FF88                    ; -120/25 target = source -6
    bcc StageBounds_Tick__death
    beq StageBounds_Tick__death
StageBounds_Tick__accelerate:
.a16
    sec
    sbc #2                       ; source .1 scaled = 2/25 target
    sta.l StageBounds_Velocity,x
StageBounds_Tick__death:
.a16
    lda.l StageBounds_Height,x
    bpl StageBounds_Tick__draw
    cmp #$EC78                    ; strict source a < -250: target /25 < -5000
    bcs StageBounds_Tick__draw
    lda #2
    sta.l StageBounds_State,x
    ; Integration callback MUST dispatch source-equivalent pit damage/kill
    ; through the existing actor owner (including player lives, drops, boss
    ; accounting, native source actors). A=10000 source damage, active D.
    ; Called exactly once: retired state is stored before the external call.
    lda #10000
    jsl StageBounds_ApplyPitDamage_Long
    rep #$31
.a16
.i16
    sec
    rtl
StageBounds_Tick__draw:
    jsl StageBounds_CacheY
StageBounds_Tick__owned:
    sec
StageBounds_Tick__done:
    rtl

; Signed floor(height/25); all valid heights are -5120..3080 before death.
; Cache at physics time so render never advances the lifecycle or divides.
StageBounds_CacheY:
.a16
.i16
    jsl StageBounds_Row
    lda.l StageBounds_Height,x
    bmi StageBounds_CacheY__negative
    ldy #0
StageBounds_CacheY__positive_loop:
.a16
.i16
    cmp #25
    bcc StageBounds_CacheY__positive_done
    sec
    sbc #25
    iny
    bra StageBounds_CacheY__positive_loop
StageBounds_CacheY__positive_done:
.a16
.i16
    tya
    sta.l StageBounds_Scratch,x
    lda #123
    sec
    sbc.l StageBounds_Scratch,x
    bra StageBounds_CacheY__store
StageBounds_CacheY__negative:
.a16
.i16
    eor #$FFFF
    inc a
    clc
    adc #24
    ldy #0
StageBounds_CacheY__negative_loop:
.a16
.i16
    cmp #25
    bcc StageBounds_CacheY__negative_done
    sec
    sbc #25
    iny
    bra StageBounds_CacheY__negative_loop
StageBounds_CacheY__negative_done:
.a16
    tya
    clc
    adc #123
StageBounds_CacheY__store:
    sta.l StageBounds_DrawY,x
    rtl

StageBounds_Render:
.a16
.i16
    jsl StageBounds_IsActive
    bcc StageBounds_Render__done
    lda.l StageBounds_State,x
    cmp #2
    beq StageBounds_Render__hidden
    lda.l StageBounds_DrawY,x
    ; A signed off-screen foot must not wrap back onto the top of the screen.
    cmp #240
    bcs StageBounds_Render__hidden
    sep #$20
.a8
    sta.l OamSetSprite_Y
    bra StageBounds_Render__priority
StageBounds_Render__hidden:
    sep #$20
.a8
    lda #$F0
    sta.l OamSetSprite_Y
StageBounds_Render__priority:
    sep #$20
.a8
    lda.l OamSetSprite_Attr
    and #$CF                     ; OBJ priority 0 behind panels; keep palette/flip
    sta.l OamSetSprite_Attr
    rep #$31
.a16
.i16
    sec
StageBounds_Render__done:
    rtl

; Import signed Q8.8 altitude/velocity on entry. Decompose |Q8.8| into
; whole/fraction before multiplying, so even -$8000 cannot overflow a word.
; X remains this actor row; Y/scratch clobbered; uses no global multiply ABI.
StageBounds_ImportQ8:
.a16
.i16
    pha
    bpl StageBounds_ImportQ8__magnitude
    eor #$FFFF
    inc a
StageBounds_ImportQ8__magnitude:
.a16
    pha
    and #$00FF
    pha
    lda 3,s
    xba
    and #$00FF
    jsr StageBounds_Mul25
    pha
    lda 3,s
    jsr StageBounds_Mul25
    xba
    and #$00FF
    clc
    adc 1,s
    sta.l StageBounds_Scratch,x
    pla
    pla
    pla
    pla
    bpl StageBounds_ImportQ8__done
    lda.l StageBounds_Scratch,x
    eor #$FFFF
    inc a
    sta.l StageBounds_Scratch,x
StageBounds_ImportQ8__done:
    lda.l StageBounds_Scratch,x
    rts
StageBounds_Mul25:
.a16
.i16
    pha
    ldy #24
StageBounds_Mul25__loop:
    clc
    adc 1,s
    dey
    bne StageBounds_Mul25__loop
    sta.l StageBounds_Scratch,x
    pla
    lda.l StageBounds_Scratch,x
    rts
