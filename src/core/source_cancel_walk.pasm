; Cancel a never-shown walking lease after a coherent accepted idle.
; No fabricated emission/ack, resource release, DMA or input writes.
; Original replacement DMA fence and completed idle resource validation remain.
SourceCancelWalk_Replace:
.a16
.i16
    jsl SourceIdle_CanReplace
    bcs SourceCancelWalk_ReplaceDone
    php
    rep #$30
    pha
    lda.l SourceVisual_Key
    cmp #22
    beq SourceCancelWalk_ReplaceIdle
    cmp #278
    bne SourceCancelWalk_ReplaceNo
    pla
    plp
    jml SourceCancelIdle_Walking
SourceCancelWalk_ReplaceIdle:
.a16
.i16
    lda.l SourceVisual_Key+2
    bne SourceCancelWalk_ReplaceNo
    pla
    plp
    jml SourceCancelWalk_Idle
SourceCancelWalk_ReplaceNo:
.a16
.i16
    pla
    plp
    clc
SourceCancelWalk_ReplaceDone:
.a16
.i16
    rtl

; Reconstruct the original TDC/CMP prefix on every ordinary path.
; A rejected new walk falls back to the original pinned completed idle.
SourceCancelWalk_CanPublish:
.a16
.i16
    php
    rep #$30
    pha
    lda.l SourceVisual_Key
    cmp #278
    beq SourceCancelWalk_PublishWalk
    cmp #22
    bne SourceCancelWalk_PublishOrdinary
    jsl SourceCancelIdle_Walking
    bra SourceCancelWalk_PublishCheck
SourceCancelWalk_PublishWalk:
.a16
.i16
    jsl SourceCancelWalk_Idle
SourceCancelWalk_PublishCheck:
.a16
.i16
    bcc SourceCancelWalk_PublishOrdinary
    pla
    plp
    tdc
    cmp #$0A00
    jml SourceVisual_CompletedCanPublish__no
SourceCancelWalk_PublishOrdinary:
.a16
.i16
    pla
    plp
    tdc
    cmp #$0A00
    jml SourceCancelWalk_CanPublishContinue

; Read-only predicate; preserves A/X/Y/D/DB/P except carry. No scratch RAM.
SourceCancelWalk_Idle:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    lda.l $7E46DE
    beq SourceCancelWalk_G66
    brl SourceCancelWalk_No
SourceCancelWalk_G66:
.a16
.i16
    lda.l Game_CampaignId
    and #255
    cmp #3
    beq SourceCancelWalk_G72
    brl SourceCancelWalk_No
SourceCancelWalk_G72:
.a16
.i16
    lda.l Game_State
    beq SourceCancelWalk_G80
    brl SourceCancelWalk_No
SourceCancelWalk_G80:
.a16
.i16
    lda.l Game_StageIndex
    beq SourceCancelWalk_G86
    brl SourceCancelWalk_No
SourceCancelWalk_G86:
.a16
.i16
    lda.l $7E175E
    cmp #2
    beq SourceCancelWalk_G92
    brl SourceCancelWalk_No
SourceCancelWalk_G92:
.a16
.i16
    lda.l $7E1760
    cmp #1
    beq SourceCancelWalk_G99
    brl SourceCancelWalk_No
SourceCancelWalk_G99:
.a16
.i16
    lda.l $7E46DC
    cmp #1
    beq SourceCancelWalk_G106
    brl SourceCancelWalk_No
SourceCancelWalk_G106:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SourceCancelWalk_G113
    brl SourceCancelWalk_No
SourceCancelWalk_G113:
.a16
.i16
    lda.l SourceVisual_CompletedMagic
    cmp #$C04D
    beq SourceCancelWalk_G120
    brl SourceCancelWalk_No
SourceCancelWalk_G120:
.a16
.i16
    lda.l SVActor_Magic
    cmp #$AC19
    beq SourceCancelWalk_G127
    brl SourceCancelWalk_No
SourceCancelWalk_G127:
.a16
.i16
    lda.l SourceVisual_Key
    and #255
    cmp #22
    beq SourceCancelWalk_G134
    brl SourceCancelWalk_No
SourceCancelWalk_G134:
.a16
.i16
    lda.l SourceVisual_Key+3
    and #255
    beq SourceCancelWalk_G142
    brl SourceCancelWalk_No
SourceCancelWalk_G142:
.a16
.i16
    tdc
    cmp #$0A00
    beq SourceCancelWalk_P1
    cmp #$0A85
    beq SourceCancelWalk_P2
    brl SourceCancelWalk_No
SourceCancelWalk_P1:
.a16
.i16
    ldx #0
    ldy #0
    bra SourceCancelWalk_Native
SourceCancelWalk_P2:
.a16
.i16
    ldx #133
    ldy #32
SourceCancelWalk_Native:
.a16
.i16
    lda.l $7E0A00+CHAR_HP,x
    and #255
    bne SourceCancelWalk_G169
    brl SourceCancelWalk_No
SourceCancelWalk_G169:
.a16
.i16
    lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
    and #255
    cmp #1
    beq SourceCancelWalk_G176
    brl SourceCancelWalk_No
SourceCancelWalk_G176:
.a16
.i16
    lda.l $7E0A00+CHAR_ROSTER_INDEX,x
    and #255
    cmp #22
    beq SourceCancelWalk_G184
    brl SourceCancelWalk_No
SourceCancelWalk_G184:
.a16
.i16
    lda.l $7E0A00+CHAR_MAP_INDEX,x
    and #255
    beq SourceCancelWalk_G192
    brl SourceCancelWalk_No
SourceCancelWalk_G192:
.a16
.i16
    lda.l $7E0A00+CHAR_SELECTED,x
    and #255
    cmp #3
    bcc SourceCancelWalk_G199
    brl SourceCancelWalk_No
SourceCancelWalk_G199:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy,x
    and #255
    cmp #2
    beq SourceCancelWalk_G207
    brl SourceCancelWalk_No
SourceCancelWalk_G207:
.a16
.i16
    lda.l StageBounds_State,x
    beq SourceCancelWalk_G215
    brl SourceCancelWalk_No
SourceCancelWalk_G215:
.a16
.i16
    tya
    cmp.l SourceVisual_Record
    beq SourceCancelWalk_G221
    brl SourceCancelWalk_No
SourceCancelWalk_G221:
.a16
.i16
    tya
    tax
    lda.l SourceVisual_State+6,x
    cmp #1
    beq SourceCancelWalk_Mode
    cmp #2
    beq SourceCancelWalk_G234
    brl SourceCancelWalk_No
SourceCancelWalk_G234:
.a16
.i16
SourceCancelWalk_Mode:
.a16
.i16
    lda.l SourceVisual_State+28,x
    and #255
    beq SourceCancelWalk_G242
    brl SourceCancelWalk_No
SourceCancelWalk_G242:
.a16
.i16
    lda.l SourceVisual_State+29,x
    cmp #278
    beq SourceCancelWalk_G249
    brl SourceCancelWalk_No
SourceCancelWalk_G249:
.a16
.i16
    tya
    beq SourceCancelWalk_P1Picture
    brl SourceCancelWalk_P2Picture
SourceCancelWalk_P1Picture:
.a16
.i16
    lda.l SourceVisual_CompletedValid
    cmp #1
    beq SourceCancelWalk_G258
    brl SourceCancelWalk_No
SourceCancelWalk_G258:
.a16
.i16
    lda.l SourceVisual_CompletedStage
    beq SourceCancelWalk_G265
    brl SourceCancelWalk_No
SourceCancelWalk_G265:
.a16
.i16
    lda.l SourceVisual_CompletedRoster
    cmp #22
    beq SourceCancelWalk_G271
    brl SourceCancelWalk_No
SourceCancelWalk_G271:
.a16
.i16
    lda.l SourceVisual_CompletedEntry
    cmp #22
    beq SourceCancelWalk_G278
    brl SourceCancelWalk_No
SourceCancelWalk_G278:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+2
    beq SourceCancelWalk_G285
    brl SourceCancelWalk_No
SourceCancelWalk_G285:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+12
    and #255
    bne SourceCancelWalk_G291
    brl SourceCancelWalk_No
SourceCancelWalk_G291:
.a16
.i16
    cmp #66
    bcc SourceCancelWalk_G298
    brl SourceCancelWalk_No
SourceCancelWalk_G298:
.a16
.i16
    lda.l $434E9C
    beq SourceCancelWalk_G304
    brl SourceCancelWalk_No
SourceCancelWalk_G304:
.a16
.i16
    ldx #0
    brl SourceCancelWalk_Snapshot
SourceCancelWalk_P2Picture:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SourceCancelWalk_G315
    brl SourceCancelWalk_No
SourceCancelWalk_G315:
.a16
.i16
    lda.l SVActor_Data+SVActor_Stage
    beq SourceCancelWalk_G322
    brl SourceCancelWalk_No
SourceCancelWalk_G322:
.a16
.i16
    lda.l SVActor_Data+SVActor_Roster
    cmp #22
    beq SourceCancelWalk_G328
    brl SourceCancelWalk_No
SourceCancelWalk_G328:
.a16
.i16
    lda.l SVActor_Data
    cmp #22
    beq SourceCancelWalk_G335
    brl SourceCancelWalk_No
SourceCancelWalk_G335:
.a16
.i16
    lda.l SVActor_Data+2
    beq SourceCancelWalk_G342
    brl SourceCancelWalk_No
SourceCancelWalk_G342:
.a16
.i16
    lda.l SVActor_Data+12
    and #255
    bne SourceCancelWalk_G348
    brl SourceCancelWalk_No
SourceCancelWalk_G348:
.a16
.i16
    cmp #66
    bcc SourceCancelWalk_G355
    brl SourceCancelWalk_No
SourceCancelWalk_G355:
.a16
.i16
    lda.l $434E9E
    cmp #133
    beq SourceCancelWalk_G361
    brl SourceCancelWalk_No
SourceCancelWalk_G361:
.a16
.i16
    ldx #36
SourceCancelWalk_Snapshot:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    beq SourceCancelWalk_G372
    brl SourceCancelWalk_No
SourceCancelWalk_G372:
.a16
.i16
    lda.l $434E2C
    beq SourceCancelWalk_G379
    brl SourceCancelWalk_No
SourceCancelWalk_G379:
.a16
.i16
    lda.l $434E7C
    pha
    and #1
    beq SourceCancelWalk_G387
    brl SourceCancelWalk_PopNo
SourceCancelWalk_G387:
.a16
.i16
    lda.l $434E34+8,x
    cmp #9
    beq SourceCancelWalk_G393
    brl SourceCancelWalk_PopNo
SourceCancelWalk_G393:
.a16
.i16
    lda.l $434E34+12,x
    cmp #1
    beq SourceCancelWalk_G400
    brl SourceCancelWalk_PopNo
SourceCancelWalk_G400:
.a16
.i16
    lda.l $434E34+14,x
    beq SourceCancelWalk_G407
    brl SourceCancelWalk_PopNo
SourceCancelWalk_G407:
.a16
.i16
    lda.l $434E34+22,x
    and #255
    cmp #2
    beq SourceCancelWalk_G413
    brl SourceCancelWalk_PopNo
SourceCancelWalk_G413:
.a16
.i16
    lda.l $434E34+28,x
    and #255
    beq SourceCancelWalk_G421
    brl SourceCancelWalk_PopNo
SourceCancelWalk_G421:
.a16
.i16
    lda.l $434E34+32,x
    and #255
    cmp #8
    beq SourceCancelWalk_G428
    brl SourceCancelWalk_PopNo
SourceCancelWalk_G428:
.a16
.i16
    lda.l $434E34+4,x
    beq SourceCancelWalk_G436
    brl SourceCancelWalk_PopNo
SourceCancelWalk_G436:
.a16
.i16
    lda.l $434E34+16,x
    bne SourceCancelWalk_G442
    brl SourceCancelWalk_PopNo
SourceCancelWalk_G442:
.a16
.i16
    lda.l $434E7C
    cmp 1,s
    beq SourceCancelWalk_G448
    brl SourceCancelWalk_PopNo
SourceCancelWalk_G448:
.a16
.i16
    pla
    ply
    plx
    pla
    plp
    sec
    rtl
SourceCancelWalk_PopNo:
.a16
.i16
    pla
SourceCancelWalk_No:
.a16
.i16
    ply
    plx
    pla
    plp
    clc
    rtl
; Reverse transition: an unfinished idle animation cannot delay accepted walking.
SourceCancelIdle_Walking:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    lda.l $7E46DE
    beq SourceCancelIdle_G66
    brl SourceCancelIdle_No
SourceCancelIdle_G66:
.a16
.i16
    lda.l Game_CampaignId
    and #255
    cmp #3
    beq SourceCancelIdle_G72
    brl SourceCancelIdle_No
SourceCancelIdle_G72:
.a16
.i16
    lda.l Game_State
    beq SourceCancelIdle_G80
    brl SourceCancelIdle_No
SourceCancelIdle_G80:
.a16
.i16
    lda.l Game_StageIndex
    beq SourceCancelIdle_G86
    brl SourceCancelIdle_No
SourceCancelIdle_G86:
.a16
.i16
    lda.l $7E175E
    cmp #2
    beq SourceCancelIdle_G92
    brl SourceCancelIdle_No
SourceCancelIdle_G92:
.a16
.i16
    lda.l $7E1760
    cmp #1
    beq SourceCancelIdle_G99
    brl SourceCancelIdle_No
SourceCancelIdle_G99:
.a16
.i16
    lda.l $7E46DC
    cmp #1
    beq SourceCancelIdle_G106
    brl SourceCancelIdle_No
SourceCancelIdle_G106:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SourceCancelIdle_G113
    brl SourceCancelIdle_No
SourceCancelIdle_G113:
.a16
.i16
    lda.l SourceVisual_CompletedMagic
    cmp #$C04D
    beq SourceCancelIdle_G120
    brl SourceCancelIdle_No
SourceCancelIdle_G120:
.a16
.i16
    lda.l SVActor_Magic
    cmp #$AC19
    beq SourceCancelIdle_G127
    brl SourceCancelIdle_No
SourceCancelIdle_G127:
.a16
.i16
    lda.l SourceVisual_Key
    and #255
    cmp #22
    beq SourceCancelIdle_G134
    brl SourceCancelIdle_No
SourceCancelIdle_G134:
.a16
.i16
    lda.l SourceVisual_Key+3
    and #255
    beq SourceCancelIdle_G142
    brl SourceCancelIdle_No
SourceCancelIdle_G142:
.a16
.i16
    tdc
    cmp #$0A00
    beq SourceCancelIdle_P1
    cmp #$0A85
    beq SourceCancelIdle_P2
    brl SourceCancelIdle_No
SourceCancelIdle_P1:
.a16
.i16
    ldx #0
    ldy #0
    bra SourceCancelIdle_Native
SourceCancelIdle_P2:
.a16
.i16
    ldx #133
    ldy #32
SourceCancelIdle_Native:
.a16
.i16
    lda.l $7E0A00+CHAR_HP,x
    and #255
    bne SourceCancelIdle_G169
    brl SourceCancelIdle_No
SourceCancelIdle_G169:
.a16
.i16
    lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
    and #255
    cmp #1
    beq SourceCancelIdle_G176
    brl SourceCancelIdle_No
SourceCancelIdle_G176:
.a16
.i16
    lda.l $7E0A00+CHAR_ROSTER_INDEX,x
    and #255
    cmp #22
    beq SourceCancelIdle_G184
    brl SourceCancelIdle_No
SourceCancelIdle_G184:
.a16
.i16
    lda.l $7E0A00+CHAR_MAP_INDEX,x
    and #255
    beq SourceCancelIdle_G192
    brl SourceCancelIdle_No
SourceCancelIdle_G192:
.a16
.i16
    lda.l $7E0A00+CHAR_SELECTED,x
    and #255
    cmp #3
    bcc SourceCancelIdle_G199
    brl SourceCancelIdle_No
SourceCancelIdle_G199:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy,x
    and #255
    cmp #2
    beq SourceCancelIdle_G207
    brl SourceCancelIdle_No
SourceCancelIdle_G207:
.a16
.i16
    lda.l StageBounds_State,x
    beq SourceCancelIdle_G215
    brl SourceCancelIdle_No
SourceCancelIdle_G215:
.a16
.i16
    tya
    cmp.l SourceVisual_Record
    beq SourceCancelIdle_G221
    brl SourceCancelIdle_No
SourceCancelIdle_G221:
.a16
.i16
    tya
    tax
    lda.l SourceVisual_State+6,x
    cmp #1
    beq SourceCancelIdle_Mode
    cmp #2
    beq SourceCancelIdle_G234
    brl SourceCancelIdle_No
SourceCancelIdle_G234:
.a16
.i16
SourceCancelIdle_Mode:
.a16
.i16
    lda.l SourceVisual_State+28,x
    and #255
    beq SourceCancelIdle_G242
    brl SourceCancelIdle_No
SourceCancelIdle_G242:
.a16
.i16
    lda.l SourceVisual_State+29,x
    cmp #22
    beq SourceCancelIdle_G249
    brl SourceCancelIdle_No
SourceCancelIdle_G249:
.a16
.i16
    tya
    beq SourceCancelIdle_P1Picture
    brl SourceCancelIdle_P2Picture
SourceCancelIdle_P1Picture:
.a16
.i16
    lda.l SourceVisual_CompletedValid
    cmp #1
    beq SourceCancelIdle_G258
    brl SourceCancelIdle_No
SourceCancelIdle_G258:
.a16
.i16
    lda.l SourceVisual_CompletedStage
    beq SourceCancelIdle_G265
    brl SourceCancelIdle_No
SourceCancelIdle_G265:
.a16
.i16
    lda.l SourceVisual_CompletedRoster
    cmp #22
    beq SourceCancelIdle_G271
    brl SourceCancelIdle_No
SourceCancelIdle_G271:
.a16
.i16
    lda.l SourceVisual_CompletedEntry
    cmp #22
    beq SourceCancelIdle_G278
    brl SourceCancelIdle_No
SourceCancelIdle_G278:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+2
    beq SourceCancelIdle_G285
    brl SourceCancelIdle_No
SourceCancelIdle_G285:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+12
    and #255
    bne SourceCancelIdle_G291
    brl SourceCancelIdle_No
SourceCancelIdle_G291:
.a16
.i16
    cmp #66
    bcc SourceCancelIdle_G298
    brl SourceCancelIdle_No
SourceCancelIdle_G298:
.a16
.i16
    lda.l $434E9C
    beq SourceCancelIdle_G304
    brl SourceCancelIdle_No
SourceCancelIdle_G304:
.a16
.i16
    ldx #0
    brl SourceCancelIdle_Snapshot
SourceCancelIdle_P2Picture:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SourceCancelIdle_G315
    brl SourceCancelIdle_No
SourceCancelIdle_G315:
.a16
.i16
    lda.l SVActor_Data+SVActor_Stage
    beq SourceCancelIdle_G322
    brl SourceCancelIdle_No
SourceCancelIdle_G322:
.a16
.i16
    lda.l SVActor_Data+SVActor_Roster
    cmp #22
    beq SourceCancelIdle_G328
    brl SourceCancelIdle_No
SourceCancelIdle_G328:
.a16
.i16
    lda.l SVActor_Data
    cmp #22
    beq SourceCancelIdle_G335
    brl SourceCancelIdle_No
SourceCancelIdle_G335:
.a16
.i16
    lda.l SVActor_Data+2
    beq SourceCancelIdle_G342
    brl SourceCancelIdle_No
SourceCancelIdle_G342:
.a16
.i16
    lda.l SVActor_Data+12
    and #255
    bne SourceCancelIdle_G348
    brl SourceCancelIdle_No
SourceCancelIdle_G348:
.a16
.i16
    cmp #66
    bcc SourceCancelIdle_G355
    brl SourceCancelIdle_No
SourceCancelIdle_G355:
.a16
.i16
    lda.l $434E9E
    cmp #133
    beq SourceCancelIdle_G361
    brl SourceCancelIdle_No
SourceCancelIdle_G361:
.a16
.i16
    ldx #36
SourceCancelIdle_Snapshot:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    beq SourceCancelIdle_G372
    brl SourceCancelIdle_No
SourceCancelIdle_G372:
.a16
.i16
    lda.l $434E2C
    beq SourceCancelIdle_G379
    brl SourceCancelIdle_No
SourceCancelIdle_G379:
.a16
.i16
    lda.l $434E7C
    pha
    and #1
    beq SourceCancelIdle_G387
    brl SourceCancelIdle_PopNo
SourceCancelIdle_G387:
.a16
.i16
    lda.l $434E34+8,x
    cmp #18
    beq SourceCancelIdle_G393
    brl SourceCancelIdle_PopNo
SourceCancelIdle_G393:
.a16
.i16
    lda.l $434E34+12,x
    cmp #1
    beq SourceCancelIdle_G400
    brl SourceCancelIdle_PopNo
SourceCancelIdle_G400:
.a16
.i16
    lda.l $434E34+14,x
    beq SourceCancelIdle_G407
    brl SourceCancelIdle_PopNo
SourceCancelIdle_G407:
.a16
.i16
    lda.l $434E34+22,x
    and #255
    cmp #2
    beq SourceCancelIdle_G413
    brl SourceCancelIdle_PopNo
SourceCancelIdle_G413:
.a16
.i16
    lda.l $434E34+28,x
    and #255
    cmp #1
    beq SourceCancelIdle_G421
    brl SourceCancelIdle_PopNo
SourceCancelIdle_G421:
.a16
.i16
    lda.l $434E34+32,x
    and #255
    cmp #8
    beq SourceCancelIdle_G428
    brl SourceCancelIdle_PopNo
SourceCancelIdle_G428:
.a16
.i16
    lda.l $434E34+4,x
    beq SourceCancelIdle_G436
    brl SourceCancelIdle_PopNo
SourceCancelIdle_G436:
.a16
.i16
    lda.l $434E34+16,x
    bne SourceCancelIdle_G442
    brl SourceCancelIdle_PopNo
SourceCancelIdle_G442:
.a16
.i16
    lda.l $434E7C
    cmp 1,s
    beq SourceCancelIdle_G448
    brl SourceCancelIdle_PopNo
SourceCancelIdle_G448:
.a16
.i16
    pla
    ply
    plx
    pla
    plp
    sec
    rtl
SourceCancelIdle_PopNo:
.a16
.i16
    pla
SourceCancelIdle_No:
.a16
.i16
    ply
    plx
    pla
    plp
    clc
    rtl
SourceCancelWalk_End:
