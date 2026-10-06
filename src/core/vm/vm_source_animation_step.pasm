; Timed-advance decision only, from af23dc9 update_animation. No model names.
; Foreground-only, non-reentrant. Caller owns the $7FFA50..7FFA7F request.
; C=1 invalid request; C=0 outputs Action (0 none,1 update_frame,2 stop,3 kill)
; and FrameResult. STOP/KILL leave the current frame unchanged. Caller MUST
; execute update_frame callbacks/side effects or kill cleanup before tick commit.
; This routine does not change pool state, nextanim, animating or world time.
SourceAnimation4086_Count = $7FFA50
SourceAnimation4086_Frame = $7FFA52
SourceAnimation4086_Direction = $7FFA54
SourceAnimation4086_LoopMode = $7FFA56
SourceAnimation4086_LoopMin = $7FFA58
SourceAnimation4086_LoopMax = $7FFA5A
SourceAnimation4086_Autokill = $7FFA5C
SourceAnimation4086_NextLo = $7FFA5E
SourceAnimation4086_NextHi = $7FFA60
SourceAnimation4086_TimeLo = $7FFA62
SourceAnimation4086_TimeHi = $7FFA64
SourceAnimation4086_Action = $7FFA66
SourceAnimation4086_FrameResult = $7FFA68
SourceAnimation4086_Fault = $7FFA6A

SourceAnimation4086_Decide:
.a16
.i16
    php
    rep #$38
    pha
    lda #0
    sta.l SourceAnimation4086_Action
    sta.l SourceAnimation4086_Fault
    lda.l SourceAnimation4086_Frame
    sta.l SourceAnimation4086_FrameResult
    lda.l SourceAnimation4086_Count
    beq SourceAnimation4086_Bad
    bmi SourceAnimation4086_Bad
    lda.l SourceAnimation4086_Frame
    cmp.l SourceAnimation4086_Count
    bcs SourceAnimation4086_Bad
    lda.l SourceAnimation4086_LoopMin
    cmp.l SourceAnimation4086_Count
    bcs SourceAnimation4086_Bad
    lda.l SourceAnimation4086_LoopMax
    cmp.l SourceAnimation4086_Count
    bcc SourceAnimation4086_DirectionCheck
    bne SourceAnimation4086_Bad
SourceAnimation4086_DirectionCheck:
.a16
.i16
    lda.l SourceAnimation4086_Direction
    cmp #$FFFF
    beq SourceAnimation4086_TimeCheck
    cmp #2
    bcs SourceAnimation4086_Bad
    bra SourceAnimation4086_TimeCheck
SourceAnimation4086_Bad:
.a16
.i16
    lda #1
    sta.l SourceAnimation4086_Fault
    pla
    plp
    sec
    rtl
SourceAnimation4086_TimeCheck:
.a16
.i16
    lda.l SourceAnimation4086_NextLo
    cmp.l SourceAnimation4086_TimeLo
    beq SourceAnimation4086_TimeHigh
    jmp SourceAnimation4086_Done
SourceAnimation4086_TimeHigh:
.a16
.i16
    lda.l SourceAnimation4086_NextHi
    cmp.l SourceAnimation4086_TimeHi
    beq SourceAnimation4086_Advance
    jmp SourceAnimation4086_Done
SourceAnimation4086_Advance:
.a16
.i16
    lda.l SourceAnimation4086_Frame
    clc
    adc.l SourceAnimation4086_Direction
    sta.l SourceAnimation4086_FrameResult
    lda.l SourceAnimation4086_LoopMode
    beq SourceAnimation4086_Ordinary
    lda.l SourceAnimation4086_LoopMax
    beq SourceAnimation4086_Ordinary
    cmp.l SourceAnimation4086_FrameResult
    beq SourceAnimation4086_LoopStart
    lda.l SourceAnimation4086_FrameResult
    cmp.l SourceAnimation4086_Count
    bcs SourceAnimation4086_Stop
    bra SourceAnimation4086_FrameRequest
SourceAnimation4086_Ordinary:
.a16
.i16
    lda.l SourceAnimation4086_FrameResult
    cmp.l SourceAnimation4086_Count
    bcc SourceAnimation4086_FrameRequest
    lda.l SourceAnimation4086_LoopMode
    beq SourceAnimation4086_Stop
SourceAnimation4086_LoopStart:
.a16
.i16
    lda.l SourceAnimation4086_FrameResult
    bmi SourceAnimation4086_ReverseWrap
    lda #0
    bra SourceAnimation4086_LoopMinCheck
SourceAnimation4086_ReverseWrap:
.a16
.i16
    lda.l SourceAnimation4086_Count
    dec a
SourceAnimation4086_LoopMinCheck:
.a16
.i16
    sta.l SourceAnimation4086_FrameResult
    lda.l SourceAnimation4086_LoopMin
    beq SourceAnimation4086_FrameRequest
    sta.l SourceAnimation4086_FrameResult
SourceAnimation4086_FrameRequest:
.a16
.i16
    lda.l SourceAnimation4086_Direction
    beq SourceAnimation4086_Done
    lda #1
    sta.l SourceAnimation4086_Action
    bra SourceAnimation4086_Done
SourceAnimation4086_Stop:
.a16
.i16
    lda #2
    sta.l SourceAnimation4086_Action
    lda.l SourceAnimation4086_Autokill
    beq SourceAnimation4086_Done
    lda #3
    sta.l SourceAnimation4086_Action
SourceAnimation4086_Done:
.a16
.i16
    lda.l SourceAnimation4086_Action
    cmp #1
    beq SourceAnimation4086_Return
    lda.l SourceAnimation4086_Frame
    sta.l SourceAnimation4086_FrameResult
SourceAnimation4086_Return:
.a16
.i16
    pla
    plp
    clc
    rtl
