; SOURCE_EXACT deadline prerequisite A/B. Called by a private bank0 JML hook
; replacing REP31 / LDA.l Nmi_FrameCounter at Core_Nmi_WaitFrame entry.
; Original caller used JSR, so both exits MUST jump back into bank0.
; Do not wait for another field if source world time has unconsumed fields.
; This does NOT certify the commit counter as an independent physical clock.
S7Deadline_Wait:
    rep #$31
    .a16
    .i16
    lda.l S6Host_Mode
    cmp #1
    bne S7Deadline_Wait__legacy
    lda.l Nmi_FrameCounter
    cmp.l S6Game_LastField
    beq S7Deadline_Wait__legacy
    jml S7Deadline_WaitReturn
S7Deadline_Wait__legacy:
    .a16
    .i16
    lda.l Nmi_FrameCounter
    jml S7Deadline_WaitLoop
