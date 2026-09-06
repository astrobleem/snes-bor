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
