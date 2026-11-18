; G13 bounded second-controller poll. Kept out of bank 0 so adding the
; independent state does not consume the fixed NMI-adjacent bank-0 budget.
; Entered by JSL from Core_Input_Poll and returns by RTL.
Core_Input_Poll_P2:
    rep #$31
.a16
.i16
    lda $421A            ; JOY2L/JOY2H from the SNES auto-joypad latch
    sta.l Input2_last_raw_Addr
    bit #INPUT_SIGNATURE_MASK
    bne Core_Input_Poll_P2__no_pad
    pha
    lda.l Input2_press_Addr
    sta.l Input2_old_Addr
    eor #$ffff
    sta.l Input2_trigger_Addr
    pla
    sta.l Input2_press_Addr
    and.l Input2_trigger_Addr
    sta.l Input2_trigger_Addr
    rtl

Core_Input_Poll_P2__no_pad:
    rep #$31
.a16
.i16
    lda #0
    sta.l Input2_press_Addr
    sta.l Input2_old_Addr
    sta.l Input2_trigger_Addr
    rtl

; Temporary verification-only epoch/record writer.
; Core_Input_Poll calls this only after the complete P2 poll has returned.
Verify_RecordPoll:
    php
    phx
    phy
    rep #$31
.a16
.i16
    lda.l Verify_InputPollEpoch
    inc a
    sta.l Verify_InputPollEpoch
    ply
    plx
    plp
    rtl

Verify_TraceAppend:
    php
    phx
    phy
    rep #$31
.a16
.i16
    lda.l Verify_TraceWriteIndex
    and #$00FF
    cmp #16
    bcs Verify_TraceAppend__overflow
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l Verify_TracePendingType
    sta.l Verify_TraceBase,x
    lda.l G13_TwoPlayerEnabled
    and #$01
    ora.l G13_P1Out
    and #$01
    sta.l Verify_TraceBase+1,x
    rep #$31
.a16
    lda.l Verify_InputPollEpoch
    sta.l Verify_TraceBase+2,x
    lda.l Input_trigger_Addr
    sta.l Verify_TraceBase+4,x
    lda.l Input2_trigger_Addr
    sta.l Verify_TraceBase+6,x
    sep #$20
.a8
    inc.l Verify_TraceWriteIndex
    inc.l Verify_TraceCount
    bra Verify_TraceAppend__done
Verify_TraceAppend__overflow:
    sep #$20
.a8
    lda #1
    sta.l Verify_TraceOverflow
Verify_TraceAppend__done:
    ply
    plx
    plp
    rtl
