; Enter only at BG2PlayDispatch__normal after original ModeMap binding.
; That binding returns a byte-valued mode (A high=0), X=stage, C=0.
; Preserve its original PHP frame; guards do not modify X/Y/D/DB or V.
; The fast case changes ONLY the same repair cursor as an already-covered
; zero-camera request. All published camera/pending fields must already match.
SourceFpNoop_Gate:
.a16
.i16
    php
    lda.l SourceReserve_Valid
    cmp #7455
    beq SourceFpNoop_Reserved
    brl SourceFpNoop_Original
SourceFpNoop_Reserved:
.a16
.i16
    lda.l SourceSecond_Consumed
    cmp #1
    beq SourceFpNoop_Consumed
    brl SourceFpNoop_Original
SourceFpNoop_Consumed:
.a16
.i16
    lda.l $434E7E
    cmp #19792
    beq SourceFpNoop_Magic
    brl SourceFpNoop_Original
SourceFpNoop_Magic:
.a16
.i16
    lda.l $434E50
    and #255
    cmp #2
    beq SourceFpNoop_Attack
    lda.l $434E74
    and #255
    cmp #2
    beq SourceFpNoop_Attack
    brl SourceFpNoop_Original
SourceFpNoop_Attack:
.a16
.i16
    lda.l Game_State
    cmp #0
    beq SourceFpNoop_Playing
    brl SourceFpNoop_Original
SourceFpNoop_Playing:
.a16
.i16
    lda.l Game_StageIndex
    cmp #0
    beq SourceFpNoop_Stage0
    brl SourceFpNoop_Original
SourceFpNoop_Stage0:
.a16
.i16
    lda.l Screen_PosX
    cmp #0
    beq SourceFpNoop_Camera0
    brl SourceFpNoop_Original
SourceFpNoop_Camera0:
.a16
.i16
    lda.l Nmi_FrameBusy
    and #255
    cmp #0
    beq SourceFpNoop_MainFree
    brl SourceFpNoop_Original
SourceFpNoop_MainFree:
.a16
.i16
    lda.l StageFp_BG2Loaded
    and #255
    cmp #1
    beq SourceFpNoop_Loaded
    brl SourceFpNoop_Original
SourceFpNoop_Loaded:
.a16
.i16
    lda.l StageFp_BG2Fault
    ora.l StageFp_BG2DmaPending
    ora.l Msu1_StreamBusy
    ora.l StreamScrollFp_ColPending
    and #255
    beq SourceFpNoop_NoPending
    brl SourceFpNoop_Original
SourceFpNoop_NoPending:
.a16
.i16
    lda.l StreamScrollFp_PendCol
    cmp #65535
    beq SourceFpNoop_NoColumn
    brl SourceFpNoop_Original
SourceFpNoop_NoColumn:
.a16
.i16
    lda.l StreamScrollFp_Budget
    and #255
    cmp #0
    beq SourceFpNoop_NoBudget
    brl SourceFpNoop_Original
SourceFpNoop_NoBudget:
.a16
.i16
    lda.l StageFp_Num
    cmp #0
    beq SourceFpNoop_Num0
    brl SourceFpNoop_Original
SourceFpNoop_Num0:
.a16
.i16
    lda.l StageFp_Rem
    cmp #0
    beq SourceFpNoop_Rem0
    brl SourceFpNoop_Original
SourceFpNoop_Rem0:
.a16
.i16
    lda.l StageFp_Request
    cmp #0
    beq SourceFpNoop_Request0
    brl SourceFpNoop_Original
SourceFpNoop_Request0:
.a16
.i16
    lda.l StageFp_Ready
    and #255
    cmp #1
    beq SourceFpNoop_Ready
    brl SourceFpNoop_Original
SourceFpNoop_Ready:
.a16
.i16
    lda.l StreamScrollFp_CameraCol
    cmp #0
    beq SourceFpNoop_Column0
    brl SourceFpNoop_Original
SourceFpNoop_Column0:
.a16
.i16
    lda.l StreamScrollFp_DesiredLo
    cmp #0
    beq SourceFpNoop_Desired0
    brl SourceFpNoop_Original
SourceFpNoop_Desired0:
.a16
.i16
    lda.l StreamScrollFp_DesiredHi
    cmp #32
    beq SourceFpNoop_Desired32
    brl SourceFpNoop_Original
SourceFpNoop_Desired32:
.a16
.i16
    lda.l StreamScrollFp_StagedLo
    cmp #0
    beq SourceFpNoop_Staged0
    brl SourceFpNoop_Original
SourceFpNoop_Staged0:
.a16
.i16
    lda.l StreamScrollFp_StagedHi
    cmp #32
    bcs SourceFpNoop_Fast
    brl SourceFpNoop_Original
SourceFpNoop_Fast:
.a16
.i16
    ; NMI with ColPending=0 neither reads nor advances the repair cursor.
    ; Every other FP value is already the exact value the original writes.
    lda.l StreamScrollFp_RepairCur
    cmp #32
    bcc SourceFpNoop_Cursor
    lda #0
SourceFpNoop_Cursor:
.a16
.i16
    inc a
    sta.l StreamScrollFp_RepairCur
    lda #0 ; original done returns the saved FrameBusy byte, proven zero
    plp
    rep #$30
.a16
.i16
    sec
    rtl
SourceFpNoop_Original:
.a16
.i16
    ; Reconstruct the exact replaced prefix. Binding's A high and C are 0.
    lda #0
    clc
    sep #$20
.a8
    lda.l Nmi_FrameBusy
    pha
    jml SourceFpNoop_OriginalBusyBody
SourceFpNoop_End:
