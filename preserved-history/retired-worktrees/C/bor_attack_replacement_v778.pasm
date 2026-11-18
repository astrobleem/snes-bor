
; Retain an acknowledged attack while a newer normal scene still contains
; an old jump. No new ownership/ticket is fabricated; no image/pin writes.
; Same-generation path preserves the original predicate exactly.
.bank 39
.org $A000
SourceAttackReplacement_Generation:
.a16
.i16
    php
    rep #$30
    pha
    lda.l SourceNextScene_Low
    cmp.l SourceAttackOwned_PhysicalLow
    bne SourceAttackReplacement_Cross
    lda.l SourceNextScene_High
    cmp.l SourceAttackOwned_PhysicalHigh
    beq SourceAttackReplacement_Yes
SourceAttackReplacement_Cross:
    lda.l SourceAttackOwned_State
    cmp #2
    beq SourceAttackReplacement_Check0
    brl SourceAttackReplacement_No
SourceAttackReplacement_Check0:
.a16
.i16
    lda.l SourceAttackOwned_Busy
    cmp #0
    beq SourceAttackReplacement_Check1
    brl SourceAttackReplacement_No
SourceAttackReplacement_Check1:
.a16
.i16
    lda.l Game_CampaignId
    cmp #3
    beq SourceAttackReplacement_Check2
    brl SourceAttackReplacement_No
SourceAttackReplacement_Check2:
.a16
.i16
    lda.l Game_StageIndex
    cmp #0
    beq SourceAttackReplacement_Check3
    brl SourceAttackReplacement_No
SourceAttackReplacement_Check3:
.a16
.i16
    lda.l Screen_PosX
    cmp #0
    beq SourceAttackReplacement_Check4
    brl SourceAttackReplacement_No
SourceAttackReplacement_Check4:
.a16
.i16
    lda.l SourceAttackOwned_Camera
    cmp #0
    beq SourceAttackReplacement_Check5
    brl SourceAttackReplacement_No
SourceAttackReplacement_Check5:
.a16
.i16
    lda.l SourceNextScene_Magic
    cmp #21315
    beq SourceAttackReplacement_Check6
    brl SourceAttackReplacement_No
SourceAttackReplacement_Check6:
.a16
.i16
    lda.l $437A9A
    cmp #3
    beq SourceAttackReplacement_Check7
    brl SourceAttackReplacement_No
SourceAttackReplacement_Check7:
.a16
.i16
    lda.l $437A9C
    cmp #3
    beq SourceAttackReplacement_Check8
    brl SourceAttackReplacement_No
SourceAttackReplacement_Check8:
.a16
.i16
    lda.l $434E7E
    cmp #19792
    beq SourceAttackReplacement_Check9
    brl SourceAttackReplacement_No
SourceAttackReplacement_Check9:
.a16
.i16
    lda.l $434E9A
    cmp #0
    beq SourceAttackReplacement_Check10
    brl SourceAttackReplacement_No
SourceAttackReplacement_Check10:
.a16
.i16
    lda.l $434E9C
    cmp #0
    beq SourceAttackReplacement_Check11
    brl SourceAttackReplacement_No
SourceAttackReplacement_Check11:
.a16
.i16
    lda.l $434E9E
    cmp #133
    beq SourceAttackReplacement_Check12
    brl SourceAttackReplacement_No
SourceAttackReplacement_Check12:
.a16
.i16
    lda.l $434E7C
    pha
    and #1
    beq SourceAttackReplacement_Even
    brl SourceAttackReplacement_PopNo
SourceAttackReplacement_Even:
    lda.l $434E3C
    cmp #0
    beq SourceAttackReplacement_Live0
    brl SourceAttackReplacement_PopNo
SourceAttackReplacement_Live0:
.a16
.i16
    lda.l $434E60
    cmp #0
    beq SourceAttackReplacement_Live1
    brl SourceAttackReplacement_PopNo
SourceAttackReplacement_Live1:
.a16
.i16
    lda.l $7E0A0B
    and #255
    cmp #0
    beq SourceAttackReplacement_Live2
    brl SourceAttackReplacement_PopNo
SourceAttackReplacement_Live2:
.a16
.i16
    lda.l $7E0A90
    and #255
    cmp #0
    beq SourceAttackReplacement_Live3
    brl SourceAttackReplacement_PopNo
SourceAttackReplacement_Live3:
.a16
.i16
    lda.l $7E0A43
    cmp #0
    beq SourceAttackReplacement_Live4
    brl SourceAttackReplacement_PopNo
SourceAttackReplacement_Live4:
.a16
.i16
    lda.l $7E0AC8
    cmp #0
    beq SourceAttackReplacement_Live5
    brl SourceAttackReplacement_PopNo
SourceAttackReplacement_Live5:
.a16
.i16
    jsl SourceStandby_FaceLive
    bcs SourceAttackReplacement_Face
    brl SourceAttackReplacement_PopNo
SourceAttackReplacement_Face:
    lda.l $43538C
    cmp #$0716
    beq SourceAttackReplacement_Jump
    lda.l $4353AC
    cmp #$0716
    beq SourceAttackReplacement_Jump
    brl SourceAttackReplacement_PopNo
SourceAttackReplacement_Jump:
    lda.l $434E7C
    cmp $01,s
    beq SourceAttackReplacement_Stable
    brl SourceAttackReplacement_PopNo
SourceAttackReplacement_Stable:
    pla
SourceAttackReplacement_Yes:
    pla
    plp
    sec
    rtl
SourceAttackReplacement_PopNo:
    pla
SourceAttackReplacement_No:
    pla
    plp
    clc
    rtl
SourceAttackReplacement_End:
.assert * <= $27B000, "replacement guard exceeds blank code"
