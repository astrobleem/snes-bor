; Normal living SCROLL_DOWN entry: BOR.C spawn() selects ANI_IDLE before
; smartspawn() assigns altitude; enemy_drop() waits for landing before AI.
; Included in bank15 through stage_bounds_host; zero new bank0 bytes.
; StageEnv row +102..103 was unused (bounds ends +101, row stride133).
; Whole-row StageEnv_ResetActors clears it; every successful spawn resets it.
; State: 0 not a source drop, 1 idle publication owed, 2 queued, 3 resident.
; No actor-name checks, no new media, no shared staging ownership shortcut.
StageDrop_State = StageEnv_Actors+102

; A16/I16, physical D; only called behind Normal gate, X/Y scratch.
StageDrop_ResetSpawn:
.a16
.i16
    jsl StageBounds_Row
    lda #0
    sta.l StageDrop_State,x
    lda.l Stage_ScrollDirection
    and #$00FF
    cmp #STAGE_SCROLL_DOWN
    bne StageDrop_ResetSpawn__done
    lda CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #CHAR_INPUT_DRIVEN_AI
    bne StageDrop_ResetSpawn__done
    lda CHAR_HP
    and #$00FF
    beq StageDrop_ResetSpawn__done
    lda CHAR_THROW_ZPOS
    beq StageDrop_ResetSpawn__done
    ; Always publish the new drop's own idle, even if this physical slot
    ; previously displayed a different role of the same model.
    lda #1
    sta.l StageDrop_State,x
    sep #$20
.a8
    lda #CHAR_SELECTED_THROWN
    sta CHAR_SELECTED
    rep #$30
.a16
.i16
StageDrop_ResetSpawn__done:
    rts

; C=true consumes the actor play pass, not gravity or the separate render
; pass. Outer bounds host preserves P/X/Y. Preserve DBR for MMIO loader.
StageDrop_BeforeActor:
.a16
.i16
    jsl StageBounds_Row
    lda.l StageDrop_State,x
    bne StageDrop_BeforeActor__active
    clc
    rts
StageDrop_BeforeActor__active:
.a16
.i16
    lda CHAR_HP
    and #$00FF
    bne StageDrop_BeforeActor__alive
    brl StageDrop_BeforeActor__retire
StageDrop_BeforeActor__alive:
.a16
.i16
    lda.l StageDrop_State,x
    cmp #3
    beq StageDrop_BeforeActor__physics
    lda.l Msu1_StreamBusy
    and #$00FF
    bne StageDrop_BeforeActor__physics
    lda.l StageDrop_State,x
    cmp #2
    beq StageDrop_BeforeActor__resident
    lda CHAR_IDLE_FCOUNT
    and #$00FF
    beq StageDrop_BeforeActor__physics ; fail closed, no fabricated asset
    phb
    sep #$20
.a8
    lda #0
    pha
    plb
    ; Borrow selector0 only for the authored idle frame-sound dispatch.
    lda CHAR_SELECTED
    pha
    stz CHAR_SELECTED
    rep #$30
.a16
.i16
    lda CHAR_IDLE_BASE_LO
    sta.l AnimHeaderStaging
    sep #$20
.a8
    lda CHAR_IDLE_BASE_HI
    sta.l AnimHeaderStaging+2
    lda #0
    jsl Msu1_LoadFrame_Long
    sep #$20
.a8
    pla
    sta CHAR_SELECTED
    plb
    stz CHAR_FRAME_INDEX
    lda #1
    sta CHAR_TICK_COUNTER
    rep #$30
.a16
.i16
    jsl StageBounds_Row
    lda #2
    sta.l StageDrop_State,x
    bra StageDrop_BeforeActor__physics
StageDrop_BeforeActor__resident:
.a16
.i16
    ; NMI clears StreamBusy only after the shared DMA queue has drained.
    ; Marking frame0 above was a request, NOT proof of residency.
    lda #3
    sta.l StageDrop_State,x
StageDrop_BeforeActor__physics:
.a16
.i16
    lda CHAR_THROW_ZPOS
    beq StageDrop_BeforeActor__ground
    sep #$20
.a8
    lda #CHAR_SELECTED_THROWN
    sta CHAR_SELECTED
    jsl Character_Throw_Play
    rep #$30
.a16
.i16
    sec
    rts
StageDrop_BeforeActor__ground:
.a16
.i16
    lda.l StageDrop_State,x
    cmp #3
    beq StageDrop_BeforeActor__ground_ready
    sec
    rts
StageDrop_BeforeActor__ground_ready:
.a16
.i16
    ; If idle transfer was delayed past landing, it must not consume FALL's
    ; first authored frame. Re-arm the existing fall/rise pipeline unchanged.
    sep #$20
.a8
    lda #$FF
    sta CHAR_FRAME_INDEX
    lda #1
    sta CHAR_TICK_COUNTER
    rep #$30
.a16
.i16
StageDrop_BeforeActor__retire:
    .a16
    .i16
    lda #0
    sta.l StageDrop_State,x
    jsl StageDrop_PersistentHandoff
    bcs StageDrop_BeforeActor__owned
StageDrop_BeforeActor__no:
    clc
    rts

StageDrop_BeforeActor__owned:
    sec
    rts

; Base-ROM no-op. The opt-in Normal SA-1 linker owns this four-byte seam and
; redirects it to the persistent-world landing handoff after overlay assembly.
; Keeping the stub here lets the ordinary distribution ROM assemble without
; importing candidate-only SA-1 symbols.
StageDrop_PersistentHandoff:
    clc
    rtl
    nop
    nop

; Hide unpublished old/blank slot art, including the mirror. Rendering
; resumes only after the native shared transfer-completion gate is clear.
StageDrop_Render:
.a16
.i16
    jsl StageBounds_Row
    lda.l StageDrop_State,x
    beq StageDrop_Render__no
    cmp #3
    beq StageDrop_Render__no
    sep #$20
.a8
    lda #$F0
    sta.l OamSetSprite_Y
    rep #$30
.a16
.i16
    sec
    rts
StageDrop_Render__no:
    clc
    rts
