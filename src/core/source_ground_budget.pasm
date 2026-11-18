; Main composition may keep a completed grounded P2 image while its next
; idle/walk media is prepared by the unchanged bounded foreground loader.
; First pictures, attacks, hurt, jumps and other campaigns keep the old path.
; This predicate performs no data, resource, queue, hardware or world writes.
SourceGroundBudget_HasCompleted:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    tdc
    cmp #$0A00
    bne SourceGroundBudget_P2
    lda.l SourceVisual_CompletedValid
    beq SourceGroundBudget_No
    brl SourceGroundBudget_Yes
SourceGroundBudget_No:
.a16
.i16
    ply
    plx
    pla
    plp
    clc
    rtl
SourceGroundBudget_P2:
.a16
.i16
    cmp #$0A85
    beq SourceGroundBudget_Target
    brl SourceGroundBudget_No
SourceGroundBudget_Target:
.a16
.i16
    lda.l Game_CampaignId
    cmp #3
    beq SourceGroundBudget_G1
    brl SourceGroundBudget_No
SourceGroundBudget_G1:
.a16
.i16
    lda.l Game_State
    cmp #0
    beq SourceGroundBudget_G2
    brl SourceGroundBudget_No
SourceGroundBudget_G2:
.a16
.i16
    lda.l Game_StageIndex
    cmp #0
    beq SourceGroundBudget_G3
    brl SourceGroundBudget_No
SourceGroundBudget_G3:
.a16
.i16
    lda.l $7E175E
    cmp #2
    beq SourceGroundBudget_G4
    brl SourceGroundBudget_No
SourceGroundBudget_G4:
.a16
.i16
    lda.l $7E1760
    cmp #1
    beq SourceGroundBudget_G5
    brl SourceGroundBudget_No
SourceGroundBudget_G5:
.a16
.i16
    lda.l $7E46DC
    cmp #1
    beq SourceGroundBudget_G6
    brl SourceGroundBudget_No
SourceGroundBudget_G6:
.a16
.i16
    lda.l $7E46DE
    cmp #0
    beq SourceGroundBudget_G7
    brl SourceGroundBudget_No
SourceGroundBudget_G7:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #6752
    beq SourceGroundBudget_G8
    brl SourceGroundBudget_No
SourceGroundBudget_G8:
.a16
.i16
    lda.l SourceVisual_CompletedMagic
    cmp #49229
    beq SourceGroundBudget_G9
    brl SourceGroundBudget_No
SourceGroundBudget_G9:
.a16
.i16
    lda.l SVActor_Magic
    cmp #44057
    beq SourceGroundBudget_G10
    brl SourceGroundBudget_No
SourceGroundBudget_G10:
.a16
.i16
    lda.l $7E0A85+CHAR_HP
    and #255
    cmp #0
    bne SourceGroundBudget_G11
    brl SourceGroundBudget_No
SourceGroundBudget_G11:
.a16
.i16
    lda.l $7E0A85+CHAR_INPUT_DRIVEN
    and #255
    cmp #1
    beq SourceGroundBudget_G12
    brl SourceGroundBudget_No
SourceGroundBudget_G12:
.a16
.i16
    lda.l $7E0A85+CHAR_ROSTER_INDEX
    and #255
    cmp #22
    beq SourceGroundBudget_G13
    brl SourceGroundBudget_No
SourceGroundBudget_G13:
.a16
.i16
    lda.l $7E0A85+CHAR_MAP_INDEX
    and #255
    cmp #0
    beq SourceGroundBudget_G14
    brl SourceGroundBudget_No
SourceGroundBudget_G14:
.a16
.i16
    lda.l $7E0A85+CHAR_SELECTED
    and #255
    cmp #3
    bcc SourceGroundBudget_G15
    brl SourceGroundBudget_No
SourceGroundBudget_G15:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy+133
    and #255
    cmp #2
    beq SourceGroundBudget_G16
    brl SourceGroundBudget_No
SourceGroundBudget_G16:
.a16
.i16
    lda.l SourceVisual_Sa1RuntimeRole+133
    and #255
    cmp #2
    bcc SourceGroundBudget_G17
    brl SourceGroundBudget_No
SourceGroundBudget_G17:
.a16
.i16
    lda.l SourceVisual_State+32+30
    and #255
    cmp #2
    bcc SourceGroundBudget_G18
    brl SourceGroundBudget_No
SourceGroundBudget_G18:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SourceGroundBudget_G19
    brl SourceGroundBudget_No
SourceGroundBudget_G19:
.a16
.i16
    lda.l SVActor_Data+SVActor_Stage
    cmp #0
    beq SourceGroundBudget_G20
    brl SourceGroundBudget_No
SourceGroundBudget_G20:
.a16
.i16
    lda.l SVActor_Data+SVActor_Roster
    cmp #22
    beq SourceGroundBudget_G21
    brl SourceGroundBudget_No
SourceGroundBudget_G21:
.a16
.i16
    lda.l SVActor_Data
    and #255
    cmp #22
    beq SourceGroundBudget_G22
    brl SourceGroundBudget_No
SourceGroundBudget_G22:
.a16
.i16
    lda.l SVActor_Data+1
    and #255
    cmp #2
    bcc SourceGroundBudget_G23
    brl SourceGroundBudget_No
SourceGroundBudget_G23:
.a16
.i16
    lda.l SVActor_Data+3
    and #255
    cmp #0
    beq SourceGroundBudget_G24
    brl SourceGroundBudget_No
SourceGroundBudget_G24:
.a16
.i16
    lda.l SVActor_Data+12
    and #255
    cmp #0
    bne SourceGroundBudget_G25
    brl SourceGroundBudget_No
SourceGroundBudget_G25:
.a16
.i16
    lda.l SVActor_Data+12
    and #255
    cmp #66
    bcc SourceGroundBudget_G26
    brl SourceGroundBudget_No
SourceGroundBudget_G26:
.a16
.i16
SourceGroundBudget_Yes:
.a16
.i16
    ply
    plx
    pla
    plp
    sec
    rtl
SourceGroundBudget_End:
