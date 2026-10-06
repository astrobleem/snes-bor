; Generic 4086 clock owner, opt-in. NTSC/224-line/non-interlace contract.
; NMI counts physical fields before the visual busy gate. The opt-out path
; preserves the ordinary timer. A granted foreign lease retires that timer:
; only one clock owner may advance its field counter. Capture $213F.7 once at
; the epoch and derive short fields outside NMI. No model-name policy.
; Observe A=old running state (0 paused,1 running), returns A=due ticks,C=fault.
; Drain every due tick through Commit only AFTER its entire world update. The
; caller publishes Time into its world/script context BEFORE that update.
; X/Y/D/DBR/P preserved except returned C. Neither routine executes gameplay.
SourceClock4086_Ready = $7FFA00
SourceClock4086_FieldsLo = $7FFA02
SourceClock4086_FieldsHi = $7FFA04
SourceClock4086_ShortsLo = $7FFA06
SourceClock4086_ShortsHi = $7FFA08
SourceClock4086_LastFieldsLo = $7FFA0A
SourceClock4086_LastFieldsHi = $7FFA0C
SourceClock4086_LastShortsLo = $7FFA0E
SourceClock4086_LastShortsHi = $7FFA10
SourceClock4086_PhaseLo = $7FFA12
SourceClock4086_PhaseHi = $7FFA14
SourceClock4086_Due = $7FFA16
SourceClock4086_TimeLo = $7FFA18
SourceClock4086_TimeHi = $7FFA1A
SourceClock4086_Fault = $7FFA1C
SourceClock4086_Sequence = $7FFA1E
SourceClock4086_Initialized = $7FFA20
SourceClock4086_PreviousShort = $7FFA22 ; immutable epoch odd-field bit
SourceClock4086_Snapshot = $7FFA24 ; fields,shorts: eight bytes
SourceClock4086_SnapshotSeq = $7FFA2C
SourceClock4086_DeltaFields = $7FFA2E
SourceClock4086_DeltaShorts = $7FFA30
SourceClock4086_Shift = $7FFA32
SourceClock4086_RawLo = $7FFA34
SourceClock4086_RawHi = $7FFA36
SourceClock4086_Running = $7FFA38

SourceClock4086_NmiGate:
.a16
.i16
    php
    rep #$20
    pha
    lda.l SourceClock4086_Ready
    cmp #$B4C5
    bne SourceClock4086_NmiGate__ordinary
    lda.l SourceClock4086_Initialized
    cmp #$B4C6
    beq SourceClock4086_NmiGate__count
    lda #$B4C6
    sta.l SourceClock4086_Initialized
    bra SourceClock4086_NmiGate__field
SourceClock4086_NmiGate__count:
.a16
.i16
    lda.l SourceClock4086_FieldsLo
    inc a
    sta.l SourceClock4086_FieldsLo
    bne SourceClock4086_NmiGate__owned_done
    lda.l SourceClock4086_FieldsHi
    inc a
    sta.l SourceClock4086_FieldsHi
    bra SourceClock4086_NmiGate__owned_done
SourceClock4086_NmiGate__field:
.a16
.i16
    sep #$20
.a8
    lda.l $00213F
    rep #$20
.a16
    and #$0080
    sta.l SourceClock4086_PreviousShort
SourceClock4086_NmiGate__owned_done:
.a16
.i16
    pla
    plp
    rtl
SourceClock4086_NmiGate__ordinary:
.a16
.i16
    ; The same PHP/REP20/PHA frame as the original timer's prologue.
    jml StageTimer_NmiField__after_save

SourceClock4086_Start:
.a16
.i16
    php
    rep #$31
    pha
    phx
    lda #0
    sta.l SourceClock4086_Ready
    ldx #2
SourceClock4086_Start__clear:
.a16
.i16
    sta.l SourceClock4086_Ready,x
    inx
    inx
    cpx #$0050
    bcc SourceClock4086_Start__clear
    lda #$B4C5
    sta.l SourceClock4086_Ready
    plx
    pla
    plp
    rtl

SourceClock4086_Observe:
.a16
.i16
    php
    rep #$31
    phx
    phy
    cmp #2
    bcc SourceClock4086_Observe__mode
    jmp SourceClock4086_Observe__bad
SourceClock4086_Observe__mode:
.a16
.i16
    sta.l SourceClock4086_Running
    lda.l SourceClock4086_Ready
    cmp #$B4C5
    beq SourceClock4086_Observe__owner
    jmp SourceClock4086_Observe__bad
SourceClock4086_Observe__owner:
.a16
.i16
    lda.l SourceClock4086_Due
    beq SourceClock4086_Observe__snapshot
    jmp SourceClock4086_Observe__bad
SourceClock4086_Observe__snapshot:
.a16
.i16
    ldx #0
SourceClock4086_Observe__copy:
.a16
.i16
    lda.l SourceClock4086_FieldsLo,x
    sta.l SourceClock4086_Snapshot,x
    inx
    inx
    cpx #4
    bcc SourceClock4086_Observe__copy
    ; No S-CPU foreground read runs during NMI. Re-reading the low counter
    ; detects an intervening NMI, including a carry into its high word.
    lda.l SourceClock4086_FieldsLo
    cmp.l SourceClock4086_Snapshot
    bne SourceClock4086_Observe__snapshot
    lda.l SourceClock4086_Snapshot
    sec
    sbc.l SourceClock4086_LastFieldsLo
    sta.l SourceClock4086_DeltaFields
    lda.l SourceClock4086_Snapshot+2
    sbc.l SourceClock4086_LastFieldsHi
    beq SourceClock4086_Observe__delta_hi
    jmp SourceClock4086_Observe__bad
SourceClock4086_Observe__delta_hi:
.a16
.i16
    lda.l SourceClock4086_DeltaFields
    bpl SourceClock4086_Observe__short_delta
    jmp SourceClock4086_Observe__bad
SourceClock4086_Observe__short_delta:
.a16
.i16
    ; Derive only this bounded interval's short fields. Accumulate the
    ; observed short total separately so a 32-bit physical-field wrap does
    ; not reset it to half of the wrapped field counter.
    lda.l SourceClock4086_PreviousShort
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    eor.l SourceClock4086_LastFieldsLo
    and #1
    clc
    adc.l SourceClock4086_DeltaFields
    lsr a
    clc
    adc.l SourceClock4086_LastShortsLo
    sta.l SourceClock4086_Snapshot+4
    lda.l SourceClock4086_LastShortsHi
    adc #0
    sta.l SourceClock4086_Snapshot+6
    lda.l SourceClock4086_Snapshot+4
    sec
    sbc.l SourceClock4086_LastShortsLo
    sta.l SourceClock4086_DeltaShorts
    lda.l SourceClock4086_Snapshot+6
    sbc.l SourceClock4086_LastShortsHi
    beq SourceClock4086_Observe__short_hi
    jmp SourceClock4086_Observe__bad
SourceClock4086_Observe__short_hi:
.a16
.i16
    lda.l SourceClock4086_DeltaFields
    cmp.l SourceClock4086_DeltaShorts
    bcs SourceClock4086_Observe__compute
    jmp SourceClock4086_Observe__bad
SourceClock4086_Observe__compute:
.a16
.i16
    lda #0
    sta.l SourceClock4086_RawLo
    sta.l SourceClock4086_RawHi
    lda.l SourceClock4086_DeltaFields
    sta.l SourceClock4086_Shift
    ldx #0
SourceClock4086_Observe__field_bit:
.a16
.i16
    lda.l SourceClock4086_Shift
    beq SourceClock4086_Observe__short_begin
    lsr a
    sta.l SourceClock4086_Shift
    bcc SourceClock4086_Observe__field_next
    lda.l SourceClock4086_RawLo
    clc
    adc.l SourceClock4086_CreditTicksLo,x
    sta.l SourceClock4086_RawLo
    lda.l SourceClock4086_RawHi
    adc.l SourceClock4086_CreditTicksHi,x
    sta.l SourceClock4086_RawHi
    lda.l SourceClock4086_PhaseLo
    clc
    adc.l SourceClock4086_CreditRemainderLo,x
    sta.l SourceClock4086_PhaseLo
    lda.l SourceClock4086_PhaseHi
    adc.l SourceClock4086_CreditRemainderHi,x
    sta.l SourceClock4086_PhaseHi
    jsr SourceClock4086_Reduce
SourceClock4086_Observe__field_next:
.a16
.i16
    txa
    clc
    adc #2
    tax
    jmp SourceClock4086_Observe__field_bit
SourceClock4086_Observe__short_begin:
.a16
.i16
    lda.l SourceClock4086_DeltaShorts
    sta.l SourceClock4086_Shift
    ldx #0
SourceClock4086_Observe__short_bit:
.a16
.i16
    lda.l SourceClock4086_Shift
    beq SourceClock4086_Observe__publish
    lsr a
    sta.l SourceClock4086_Shift
    bcc SourceClock4086_Observe__short_next
    lda.l SourceClock4086_RawLo
    sec
    sbc.l SourceClock4086_ShortCreditTicksLo,x
    sta.l SourceClock4086_RawLo
    lda.l SourceClock4086_RawHi
    sbc.l SourceClock4086_ShortCreditTicksHi,x
    sta.l SourceClock4086_RawHi
    lda.l SourceClock4086_PhaseLo
    sec
    sbc.l SourceClock4086_ShortCreditRemainderLo,x
    sta.l SourceClock4086_PhaseLo
    lda.l SourceClock4086_PhaseHi
    sbc.l SourceClock4086_ShortCreditRemainderHi,x
    sta.l SourceClock4086_PhaseHi
    bcs SourceClock4086_Observe__short_next
    jsr SourceClock4086_Borrow
SourceClock4086_Observe__short_next:
.a16
.i16
    txa
    clc
    adc #2
    tax
    jmp SourceClock4086_Observe__short_bit
SourceClock4086_Observe__publish:
.a16
.i16
    ldx #0
SourceClock4086_Observe__last:
.a16
.i16
    lda.l SourceClock4086_Snapshot,x
    sta.l SourceClock4086_LastFieldsLo,x
    inx
    inx
    cpx #8
    bcc SourceClock4086_Observe__last
    lda.l SourceClock4086_Running
    beq SourceClock4086_Observe__zero
    lda.l SourceClock4086_RawHi
    bne SourceClock4086_Observe__one
    lda.l SourceClock4086_RawLo
    cmp #201
    bcs SourceClock4086_Observe__one
    cmp #51
    bcc SourceClock4086_Observe__due
    lda #50
    bra SourceClock4086_Observe__due
SourceClock4086_Observe__one:
.a16
.i16
    lda #1
    bra SourceClock4086_Observe__due
SourceClock4086_Observe__zero:
.a16
.i16
    lda #0
SourceClock4086_Observe__due:
.a16
.i16
    sta.l SourceClock4086_Due
    ply
    plx
    plp
    clc
    rtl
SourceClock4086_Observe__bad:
.a16
.i16
    lda #1
    sta.l SourceClock4086_Fault
    ply
    plx
    plp
    sec
    rtl

SourceClock4086_Reduce:
.a16
.i16
    lda.l SourceClock4086_PhaseHi
    cmp #SOURCE_CLOCK_MASTER_HI
    bcc SourceClock4086_Reduce__done
    bne SourceClock4086_Reduce__subtract
    lda.l SourceClock4086_PhaseLo
    cmp #SOURCE_CLOCK_MASTER_LO
    bcc SourceClock4086_Reduce__done
SourceClock4086_Reduce__subtract:
.a16
.i16
    lda.l SourceClock4086_PhaseLo
    sec
    sbc #SOURCE_CLOCK_MASTER_LO
    sta.l SourceClock4086_PhaseLo
    lda.l SourceClock4086_PhaseHi
    sbc #SOURCE_CLOCK_MASTER_HI
    sta.l SourceClock4086_PhaseHi
    lda.l SourceClock4086_RawLo
    inc a
    sta.l SourceClock4086_RawLo
    bne SourceClock4086_Reduce__done
    lda.l SourceClock4086_RawHi
    inc a
    sta.l SourceClock4086_RawHi
SourceClock4086_Reduce__done:
.a16
.i16
    rts

SourceClock4086_Borrow:
.a16
.i16
    lda.l SourceClock4086_PhaseLo
    clc
    adc #SOURCE_CLOCK_MASTER_LO
    sta.l SourceClock4086_PhaseLo
    lda.l SourceClock4086_PhaseHi
    adc #SOURCE_CLOCK_MASTER_HI
    sta.l SourceClock4086_PhaseHi
    lda.l SourceClock4086_RawLo
    sec
    sbc #1
    sta.l SourceClock4086_RawLo
    lda.l SourceClock4086_RawHi
    sbc #0
    sta.l SourceClock4086_RawHi
    rts

SourceClock4086_Commit:
.a16
.i16
    php
    rep #$31
    lda.l SourceClock4086_Ready
    cmp #$B4C5
    beq SourceClock4086_Commit_GuardWide_1
    jmp SourceClock4086_Commit__bad
SourceClock4086_Commit_GuardWide_1:
.a16
.i16
    lda.l SourceClock4086_Due
    bne SourceClock4086_Commit_GuardWide_2
    jmp SourceClock4086_Commit__bad
SourceClock4086_Commit_GuardWide_2:
.a16
.i16
    ; An admitted foreign traversal owns commit. A direct caller cannot turn
    ; its pending callback/physics requests into an empty completed tick.
    lda.l SourceWorldTick4086_Ready
    cmp #$B4D5
    bne SourceClock4086_Commit__retire
    lda.l SourceWorldTick4086_State
    cmp #4
    beq SourceClock4086_Commit_GuardWide_3
    jmp SourceClock4086_Commit__bad
SourceClock4086_Commit_GuardWide_3:
.a16
.i16
    lda.l SourceWorldTick4086_Pending
    beq SourceClock4086_Commit_GuardWide_4
    jmp SourceClock4086_Commit__bad
SourceClock4086_Commit_GuardWide_4:
.a16
.i16
SourceClock4086_Commit__retire:
.a16
.i16
    jsl SourceUpdateFrame4086_CheckIdle
    bcc SourceClock4086_Commit_GuardWide_5
    jmp SourceClock4086_Commit__bad
SourceClock4086_Commit_GuardWide_5:
.a16
.i16
    jsl SourceAnimationInit4086_CheckIdle
    bcc SourceClock4086_Commit_GuardWide_6
    jmp SourceClock4086_Commit__bad
SourceClock4086_Commit_GuardWide_6:
.a16
.i16
    jsl SourceFrameStack4086_CheckIdle
    bcc SourceClock4086_Commit_GuardWide_7
    jmp SourceClock4086_Commit__bad
SourceClock4086_Commit_GuardWide_7:
.a16
.i16
    jsl SourceModelAnimation4086_CheckIdle
    bcc SourceClock4086_Commit_GuardWide_8
    jmp SourceClock4086_Commit__bad
SourceClock4086_Commit_GuardWide_8:
.a16
.i16
    jsl SourceModelTransition4086_CheckIdle
    bcc SourceClock4086_Commit_GuardWide_9
    jmp SourceClock4086_Commit__bad
SourceClock4086_Commit_GuardWide_9:
.a16
.i16
    jsl SourceFrameEffectPlan4086_CheckIdle
    bcc SourceClock4086_Commit_GuardWide_10
    jmp SourceClock4086_Commit__bad
SourceClock4086_Commit_GuardWide_10:
.a16
.i16
    jsl SourceSelf4086_CheckIdle
    bcc SourceClock4086_Commit_GuardWide_11
    jmp SourceClock4086_Commit__bad
SourceClock4086_Commit_GuardWide_11:
.a16
.i16
    jsl SourceRetirement4086_CheckIdle
    bcc SourceClock4086_Commit_GuardWide_12
    jmp SourceClock4086_Commit__bad
SourceClock4086_Commit_GuardWide_12:
.a16
.i16
    jsl SourceBirthCore4086_CheckIdle
    bcc SourceClock4086_Commit_GuardWide_13
    jmp SourceClock4086_Commit__bad
SourceClock4086_Commit_GuardWide_13:
.a16
.i16
    jsl SourceLifecycle4086_CheckIdle
    bcc SourceClock4086_Commit_GuardWide_14
    jmp SourceClock4086_Commit__bad
SourceClock4086_Commit_GuardWide_14:
.a16
.i16
    jsl SourceEmptyInitEnvironment4086_CheckIdle
    bcc SourceClock4086_Commit_GuardWide_15
    jmp SourceClock4086_Commit__bad
SourceClock4086_Commit_GuardWide_15:
.a16
.i16
    lda.l SourceClock4086_Due
    dec a
    sta.l SourceClock4086_Due
    lda.l SourceClock4086_TimeLo
    inc a
    sta.l SourceClock4086_TimeLo
    bne SourceClock4086_Commit__done
    lda.l SourceClock4086_TimeHi
    inc a
    sta.l SourceClock4086_TimeHi
SourceClock4086_Commit__done:
.a16
.i16
    plp
    clc
    rtl
SourceClock4086_Commit__bad:
.a16
.i16
    lda #1
    sta.l SourceClock4086_Fault
    plp
    sec
    rtl
