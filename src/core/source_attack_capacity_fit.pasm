; Capacity fallback for the first P2 attack during authored encounters.
; Formed accepted role/frame remains authoritative; only choose its authored
; first pose when frame1 cannot fit and frame0 can. No resource/world writes.
SourceAttackFit_Free = $436240
SourceAttackFit_Resident0 = $436242
SourceAttackFit_Resident1 = $436244
SourceAttackFit_RowFree = $436246
SourceAttackFit_Prefer:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
tdc
cmp #2693
    beq SourceAttackFit_G15
    brl SourceAttackFit_Done
SourceAttackFit_G15:
.a16
.i16
lda.l Game_CampaignId
and #255
cmp #3
    beq SourceAttackFit_G22
    brl SourceAttackFit_Done
SourceAttackFit_G22:
.a16
.i16
lda.l Game_State
cmp #0
    beq SourceAttackFit_G30
    brl SourceAttackFit_Done
SourceAttackFit_G30:
.a16
.i16
lda.l Game_StageIndex
cmp #0
    beq SourceAttackFit_G37
    brl SourceAttackFit_Done
SourceAttackFit_G37:
.a16
.i16
jsl SourceSpawnByte_Read
cmp #3
    bcs SourceAttackFit_G44
    brl SourceAttackFit_Done
SourceAttackFit_G44:
.a16
.i16
lda.l $7E46DE
cmp #0
    beq SourceAttackFit_G51
    brl SourceAttackFit_Done
SourceAttackFit_G51:
.a16
.i16
lda.l $7E175E
cmp #2
    beq SourceAttackFit_G58
    brl SourceAttackFit_Done
SourceAttackFit_G58:
.a16
.i16
lda.l $7E1760
cmp #1
    beq SourceAttackFit_G65
    brl SourceAttackFit_Done
SourceAttackFit_G65:
.a16
.i16
lda.l $7E46DC
cmp #1
    beq SourceAttackFit_G72
    brl SourceAttackFit_Done
SourceAttackFit_G72:
.a16
.i16
lda.l SourceInput_Magic
cmp #6752
    beq SourceAttackFit_G79
    brl SourceAttackFit_Done
SourceAttackFit_G79:
.a16
.i16
lda.l SVActor_Magic
cmp #44057
    beq SourceAttackFit_G86
    brl SourceAttackFit_Done
SourceAttackFit_G86:
.a16
.i16
lda.l SourceVisual_Key
cmp #534
    beq SourceAttackFit_G93
    brl SourceAttackFit_Done
SourceAttackFit_G93:
.a16
.i16
lda.l SourceVisual_Key+2
cmp #1
    beq SourceAttackFit_G100
    brl SourceAttackFit_Done
SourceAttackFit_G100:
.a16
.i16
lda.l SourceVisual_Sa1OwnerPolicy+133
and #255
cmp #2
    beq SourceAttackFit_G107
    brl SourceAttackFit_Done
SourceAttackFit_G107:
.a16
.i16
lda.l SVActor_Data+SVActor_Valid
cmp #1
    beq SourceAttackFit_G115
    brl SourceAttackFit_Done
SourceAttackFit_G115:
.a16
.i16
lda.l SVActor_Data+SVActor_Stage
cmp #0
    beq SourceAttackFit_G122
    brl SourceAttackFit_Done
SourceAttackFit_G122:
.a16
.i16
lda.l SVActor_Data+SVActor_Roster
cmp #22
    beq SourceAttackFit_G129
    brl SourceAttackFit_Done
SourceAttackFit_G129:
.a16
.i16
lda.l SVActor_Data+1
and #255
cmp #2
    bcc SourceAttackFit_G136
    brl SourceAttackFit_Done
SourceAttackFit_G136:
.a16
.i16
lda.l SVActor_Data+3
and #255
cmp #0
    beq SourceAttackFit_G144
    brl SourceAttackFit_Done
SourceAttackFit_G144:
.a16
.i16
lda.l $7E0A85+CHAR_HP
and #255
cmp #0
    bne SourceAttackFit_G152
    brl SourceAttackFit_Done
SourceAttackFit_G152:
.a16
.i16
lda.l $7E0A85+CHAR_INPUT_DRIVEN
and #255
cmp #1
    beq SourceAttackFit_G160
    brl SourceAttackFit_Done
SourceAttackFit_G160:
.a16
.i16
lda.l $7E0A85+CHAR_ROSTER_INDEX
and #255
cmp #22
    beq SourceAttackFit_G168
    brl SourceAttackFit_Done
SourceAttackFit_G168:
.a16
.i16
lda.l $7E0A85+CHAR_MAP_INDEX
and #255
cmp #0
    beq SourceAttackFit_G176
    brl SourceAttackFit_Done
SourceAttackFit_G176:
.a16
.i16
lda.l $7E0A85+CHAR_SELECTED
and #255
cmp #3
    bcc SourceAttackFit_G184
    brl SourceAttackFit_Done
SourceAttackFit_G184:
.a16
.i16
lda.l SourceVisual_State+32
    cmp #781
    bne SourceAttackFit_Count
    lda.l SourceVisual_State+38
    cmp #1
    bne SourceAttackFit_Count
    lda.l SourceVisual_State+60
    and #255
    bne SourceAttackFit_Count
    lda.l SourceVisual_State+61
    and #$FFFF
    cmp #$0216
    bne SourceAttackFit_Count
    brl SourceAttackFit_Choose0
SourceAttackFit_Count:
.a16
.i16
    lda #0
    sta.l SourceAttackFit_Free
    sta.l SourceAttackFit_Resident0
    sta.l SourceAttackFit_Resident1
    ldx #0
SourceAttackFit_Row:
.a16
.i16
    lda #0
    sta.l SourceAttackFit_RowFree
    lda.l SourceVisual_BlockCache+4,x
    and #$00FD
    ora.l SVActor_HeldBlocks,x
    ora.l SVActor_OldBlocks,x
    and #255
    bne SourceAttackFit_Protected
    lda.l SourceAttackFit_Free
    inc a
    sta.l SourceAttackFit_Free
    lda #1
    sta.l SourceAttackFit_RowFree
SourceAttackFit_Protected:
.a16
.i16
    lda.l SourceVisual_BlockCache+2,x
    bne SourceAttackFit_Present
    brl SourceAttackFit_Next
SourceAttackFit_Present:
.a16
.i16
    cmp #3
    bcc SourceAttackFit_StateValid
    brl SourceAttackFit_Next
SourceAttackFit_StateValid:
.a16
.i16
    lda.l SourceVisual_BlockCache,x
cmp #203
    bne SourceAttackFit_Not0_203
    brl SourceAttackFit_Hit0
SourceAttackFit_Not0_203:
.a16
.i16
cmp #4493
    bne SourceAttackFit_Not0_4493
    brl SourceAttackFit_Hit0
SourceAttackFit_Not0_4493:
.a16
.i16
cmp #6005
    bne SourceAttackFit_Not0_6005
    brl SourceAttackFit_Hit0
SourceAttackFit_Not0_6005:
.a16
.i16
cmp #6374
    bne SourceAttackFit_Not0_6374
    brl SourceAttackFit_Hit0
SourceAttackFit_Not0_6374:
.a16
.i16
cmp #11120
    bne SourceAttackFit_Not0_11120
    brl SourceAttackFit_Hit0
SourceAttackFit_Not0_11120:
.a16
.i16
cmp #11465
    bne SourceAttackFit_Not0_11465
    brl SourceAttackFit_Hit0
SourceAttackFit_Not0_11465:
.a16
.i16
cmp #12783
    bne SourceAttackFit_Not0_12783
    brl SourceAttackFit_Hit0
SourceAttackFit_Not0_12783:
.a16
.i16
cmp #13713
    bne SourceAttackFit_Not0_13713
    brl SourceAttackFit_Hit0
SourceAttackFit_Not0_13713:
.a16
.i16
cmp #14972
    bne SourceAttackFit_Not0_14972
    brl SourceAttackFit_Hit0
SourceAttackFit_Not0_14972:
.a16
.i16
cmp #15711
    bne SourceAttackFit_Not0_15711
    brl SourceAttackFit_Hit0
SourceAttackFit_Not0_15711:
.a16
.i16
cmp #28
    bne SourceAttackFit_Not1_28
    brl SourceAttackFit_Hit1
SourceAttackFit_Not1_28:
.a16
.i16
cmp #1175
    bne SourceAttackFit_Not1_1175
    brl SourceAttackFit_Hit1
SourceAttackFit_Not1_1175:
.a16
.i16
cmp #9736
    bne SourceAttackFit_Not1_9736
    brl SourceAttackFit_Hit1
SourceAttackFit_Not1_9736:
.a16
.i16
cmp #10359
    bne SourceAttackFit_Not1_10359
    brl SourceAttackFit_Hit1
SourceAttackFit_Not1_10359:
.a16
.i16
cmp #13362
    bne SourceAttackFit_Not1_13362
    brl SourceAttackFit_Hit1
SourceAttackFit_Not1_13362:
.a16
.i16
cmp #14503
    bne SourceAttackFit_Not1_14503
    brl SourceAttackFit_Hit1
SourceAttackFit_Not1_14503:
.a16
.i16
cmp #15476
    bne SourceAttackFit_Not1_15476
    brl SourceAttackFit_Hit1
SourceAttackFit_Not1_15476:
.a16
.i16
cmp #15931
    bne SourceAttackFit_Not1_15931
    brl SourceAttackFit_Hit1
SourceAttackFit_Not1_15931:
.a16
.i16
cmp #16376
    bne SourceAttackFit_Not1_16376
    brl SourceAttackFit_Hit1
SourceAttackFit_Not1_16376:
.a16
.i16
cmp #16457
    bne SourceAttackFit_Not1_16457
    brl SourceAttackFit_Hit1
SourceAttackFit_Not1_16457:
.a16
.i16
cmp #16873
    bne SourceAttackFit_Not1_16873
    brl SourceAttackFit_Hit1
SourceAttackFit_Not1_16873:
.a16
.i16
cmp #16947
    bne SourceAttackFit_Not1_16947
    brl SourceAttackFit_Hit1
SourceAttackFit_Not1_16947:
.a16
.i16
brl SourceAttackFit_Next
SourceAttackFit_NextBridge:
.a16
.i16
    brl SourceAttackFit_Next
SourceAttackFit_Hit0:
.a16
.i16
    lda.l SourceAttackFit_RowFree
    bne SourceAttackFit_Next
    lda.l SourceAttackFit_Resident0
    inc a
    sta.l SourceAttackFit_Resident0
    bra SourceAttackFit_Next
SourceAttackFit_Hit1:
.a16
.i16
    lda.l SourceAttackFit_RowFree
    bne SourceAttackFit_Next
    lda.l SourceAttackFit_Resident1
    inc a
    sta.l SourceAttackFit_Resident1
SourceAttackFit_Next:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #512
    bcs SourceAttackFit_CountDone
    brl SourceAttackFit_Row
SourceAttackFit_CountDone:
.a16
.i16
    lda.l SourceAttackFit_Resident1
    clc
    adc.l SourceAttackFit_Free
    cmp #12
    bcs SourceAttackFit_Done
    lda.l SourceAttackFit_Resident0
    clc
    adc.l SourceAttackFit_Free
    cmp #10
    bcc SourceAttackFit_Done
SourceAttackFit_Choose0:
.a16
.i16
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_Key+2
SourceAttackFit_Chosen:
.a8
.i16
    rep #$30
.a16
.i16
SourceAttackFit_Done:
.a16
.i16
    ply
    plx
    pla
    plp
    rtl
SourceAttackFit_End:
