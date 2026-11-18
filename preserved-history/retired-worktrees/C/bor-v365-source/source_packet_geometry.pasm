; Bounded source-position transport. Resource bytes and native actor state
; are immutable here. The first version refreshes only the foreground packet.
SOURCE_PACKET_BASE = $435120
SOURCE_PACKET_BUILD_META = $435340
SOURCE_PACKET_ACTIVE_META = $435380
SOURCE_PACKET_MOTION = $4353C0
SourcePacket_ReadSeq = $4353E0
SourcePacket_ReadStage = $4353E2
SourcePacket_ProjectInput = $435400
SourcePacket_ProjectSign = $435402
SourcePacket_ProjectQ = $435404
SourcePacket_ProjectR = $435406
SourcePacket_Slot = $435420
SourcePacket_Begin = $435422
SourcePacket_End = $435424
SourcePacket_Total = $435426
SourcePacket_Mask = $435428
SourcePacket_Sprite = $43542A
SourcePacket_Delta = $43542C
SourcePacket_NewX = $43542E
SourcePacket_Meta = $435430
SourcePacket_Snap = $435432
SourcePacket_Native = $435434
SourcePacket_CopyBusy = $435440
SourcePacket_ActiveValid = $435442
SourcePacket_ThisFrame = $435446
SourcePacket_Changed = $435448
SourcePacket_VCounter = $43544A
SourcePacket_NmiPending = $43544C
SourcePacket_RefreshAccepted = $43544E
SourcePacket_NmiMainBusy = $435450
SourcePacket_PendingCamera = $435452
SourcePacket_ActiveCamera = $435454
SourcePacket_NmiQueueTotal = $435456
SourcePacket_NmiRowLength = $435458
SourcePacket_NmiRowType = $43545A
SourcePacket_NmiRowSpan = $43545C
SourcePacket_NmiTargetEnd = $43545E
SourcePacket_NmiQueueRows = $435460
; Main-copy race bookkeeping only, after first-idle scratch ending46F.
SourcePacket_MainRetryNeeded = $435470
SourcePacket_MainRetryRemaining = $435472
SOURCE_PACKET_SIGNED_X = $435600

SourcePacket_PlayerMeta:
.a16
.i16
    tdc
    cmp #$0A00
    bne SourcePacket_LongBranch0
    brl SourcePacket_PlayerMeta__p1
SourcePacket_LongBranch0:
.a16
.i16
    cmp #$0A85
    beq SourcePacket_LongBranch1
    brl SourcePacket_PlayerMeta__none
SourcePacket_LongBranch1:
.a16
.i16
    ldx #32
    sec
    rts
SourcePacket_PlayerMeta__p1:
.a16
.i16
    ldx #0
    sec
    rts
SourcePacket_PlayerMeta__none:
.a16
.i16
    clc
    rts

SourcePacket_FrameBegin:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    phb
    phd
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq SourcePacket_FrameBegin__campaign3
    brl SourcePacket_FrameBegin__done
SourcePacket_FrameBegin__campaign3:
.a16
.i16
    lda #0
    sta.l SOURCE_PACKET_BUILD_META+16
    sta.l SOURCE_PACKET_BUILD_META+32+16
    sta.l SourcePacket_ThisFrame
    jsl SourceNpc_FrameBegin
SourcePacket_FrameBegin__done:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    rtl

SourcePacket_EmitStart:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    phb
    phd
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq SourcePacket_EmitStart__campaign3
    brl SourcePacket_EmitStart__done
SourcePacket_EmitStart__campaign3:
.a16
.i16
    jsr SourcePacket_PlayerMeta
    bcs SourcePacket_LongBranch2
    brl SourcePacket_EmitStart__done
SourcePacket_LongBranch2:
.a16
.i16
    lda #0
    sta.l SOURCE_PACKET_BUILD_META+16,x
    lda.l $7E53A0
    sta.l SOURCE_PACKET_BUILD_META,x
SourcePacket_EmitStart__done:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    rtl

SourcePacket_EmitFinish:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    phb
    phd
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq SourcePacket_EmitFinish__campaign3
    brl SourcePacket_EmitFinish__done
SourcePacket_EmitFinish__campaign3:
.a16
.i16
    jsr SourcePacket_PlayerMeta
    bcc SourcePacket_LongBranch3
    brl SourcePacket_EmitFinish__player
SourcePacket_LongBranch3:
.a16
.i16
    brl SourcePacket_EmitFinish__done
SourcePacket_EmitFinish__player:
.a16
.i16
    lda.l $7E53A0
    cmp.l SOURCE_PACKET_BUILD_META,x
    beq SourcePacket_LongBranch4
    brl SourcePacket_EmitFinish__has_bytes
SourcePacket_LongBranch4:
.a16
.i16
    brl SourcePacket_EmitFinish__done
SourcePacket_EmitFinish__has_bytes:
.a16
.i16
    sta.l SOURCE_PACKET_BUILD_META+2,x
    lda.l SourceVisual_EmitBaseX
    sta.l SOURCE_PACKET_BUILD_META+4,x
    lda.l SourceVisual_EmitBaseY
    sta.l SOURCE_PACKET_BUILD_META+6,x
    lda CHAR_ROSTER_INDEX
    and #$00FF
    sta.l SOURCE_PACKET_BUILD_META+8,x
    lda.l Game_StageIndex
    sta.l SOURCE_PACKET_BUILD_META+10,x
    lda.l SourceVisual_EntryScratch
    sta.l SOURCE_PACKET_BUILD_META+12,x
    lda.l SourceVisual_EntryScratch+2
    sta.l SOURCE_PACKET_BUILD_META+14,x
    lda CHAR_FACING_LEFT
    and #$00FF
    sta.l SOURCE_PACKET_BUILD_META+18,x
    lda.l SourceVisual_EntryScratch+4
    sta.l SOURCE_PACKET_BUILD_META+20,x
    lda.l SourceVisual_EntryScratch+8
    sta.l SOURCE_PACKET_BUILD_META+22,x
    cpx #0
    beq SourcePacket_LongBranch5
    brl SourcePacket_EmitFinish__p2_family
SourcePacket_LongBranch5:
.a16
.i16
    lda.l $7E19E4
    bra SourcePacket_EmitFinish__family
SourcePacket_EmitFinish__p2_family:
.a16
.i16
    lda.l $7E1AE4
SourcePacket_EmitFinish__family:
.a16
.i16
    sta.l SOURCE_PACKET_BUILD_META+24,x
    lda CHAR_SELECTED
    and #$00FF
    sta.l SOURCE_PACKET_BUILD_META+26,x
    lda #0
    sta.l SOURCE_PACKET_BUILD_META+28,x
    sta.l SOURCE_PACKET_BUILD_META+30,x
    lda #1
    sta.l SOURCE_PACKET_BUILD_META+16,x
SourcePacket_EmitFinish__done:
.a16
.i16
    jml SourceSecond_EmitDone
    nop
    nop
    nop

SourcePacket_PrepareGeometry:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    phb
    phd
    sep #$20
.a8
    lda #$43
    pha
    plb
    rep #$30
.a16
.i16
    lda #0
    sta.l SourcePacket_NmiPending
    sta.l SourcePacket_MainRetryNeeded
    lda.l Screen_PosX
    sta.l SourcePacket_ActiveCamera
    ldx #(SOURCE_PACKET_BUILD_META&$FFFF)
    ldy #(SOURCE_PACKET_ACTIVE_META&$FFFF)
    lda #63
    mvn $43,$43
    jsr SourcePacket_CheckRanges
    bcc SourcePacket_LongBranch6
    brl SourcePacket_PrepareGeometry__ranges
SourcePacket_LongBranch6:
.a16
.i16
    brl SourcePacket_PrepareGeometry__done
SourcePacket_PrepareGeometry__ranges:
.a16
.i16
    jsr SourcePacket_BuildSignedX
    lda #2
    sta.l SourcePacket_MainRetryRemaining
SourcePacket_PrepareGeometry__refresh:
.a16
.i16
    jsr SourcePacket_Refresh
    lda.l SourcePacket_MainRetryNeeded
    beq SourcePacket_PrepareGeometry__done
    lda.l SourcePacket_MainRetryRemaining
    beq SourcePacket_PrepareGeometry__done
    dec a
    sta.l SourcePacket_MainRetryRemaining
    ; Foreground compositor only. At most two bounded waits of64 polls;
    ; source/clock work is neither parked nor re-entered. NMI never retries.
    ldx #64
SourcePacket_PrepareGeometry__wait:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    bne SourcePacket_PrepareGeometry__wait_next
    lda.l $434E7C
    and #1
    beq SourcePacket_PrepareGeometry__refresh
SourcePacket_PrepareGeometry__wait_next:
.a16
.i16
    dex
    bne SourcePacket_PrepareGeometry__wait
    bra SourcePacket_PrepareGeometry__refresh
SourcePacket_PrepareGeometry__done:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    rtl

; C=two nonoverlapping owned ranges, <=26 actual sprites in total.
SourcePacket_CheckRanges:
.a16
.i16
    lda #0
    sta.l SourcePacket_Total
    ldx #0
SourcePacket_CheckRanges__actor:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+16,x
    cmp #1
    beq SourcePacket_LongBranch7
    brl SourcePacket_CheckRanges__next
SourcePacket_LongBranch7:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META,x
    sta.l SourcePacket_Begin
    lda.l SOURCE_PACKET_ACTIVE_META+2,x
    sta.l SourcePacket_End
    ora.l SourcePacket_Begin
    and #3
    beq SourcePacket_LongBranch8
    brl SourcePacket_CheckRanges__bad
SourcePacket_LongBranch8:
.a16
.i16
    lda.l SourcePacket_End
    cmp #513
    bcc SourcePacket_LongBranch9
    brl SourcePacket_CheckRanges__bad
SourcePacket_LongBranch9:
.a16
.i16
    cmp.l SourcePacket_Begin
    bne SourcePacket_LongBranch10
    brl SourcePacket_CheckRanges__bad
SourcePacket_LongBranch10:
.a16
.i16
    bcs SourcePacket_LongBranch11
    brl SourcePacket_CheckRanges__bad
SourcePacket_LongBranch11:
.a16
.i16
    sec
    sbc.l SourcePacket_Begin
    clc
    adc.l SourcePacket_Total
    cmp #105
    bcc SourcePacket_LongBranch12
    brl SourcePacket_CheckRanges__bad
SourcePacket_LongBranch12:
.a16
.i16
    sta.l SourcePacket_Total
SourcePacket_CheckRanges__next:
.a16
.i16
    txa
    clc
    adc #32
    tax
    cpx #64
    bcs SourcePacket_LongBranch13
    brl SourcePacket_CheckRanges__actor
SourcePacket_LongBranch13:
.a16
.i16
    lda.l SourcePacket_Total
    bne SourcePacket_LongBranch14
    brl SourcePacket_CheckRanges__bad
SourcePacket_LongBranch14:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+16
    and.l SOURCE_PACKET_ACTIVE_META+48
    cmp #1
    beq SourcePacket_LongBranch15
    brl SourcePacket_CheckRanges__good
SourcePacket_LongBranch15:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+2
    cmp.l SOURCE_PACKET_ACTIVE_META+32
    bcs SourcePacket_LongBranch16
    brl SourcePacket_CheckRanges__good
SourcePacket_LongBranch16:
.a16
.i16
    bne SourcePacket_LongBranch17
    brl SourcePacket_CheckRanges__good
SourcePacket_LongBranch17:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+34
    cmp.l SOURCE_PACKET_ACTIVE_META
    bcs SourcePacket_LongBranch18
    brl SourcePacket_CheckRanges__good
SourcePacket_LongBranch18:
.a16
.i16
    bne SourcePacket_LongBranch19
    brl SourcePacket_CheckRanges__good
SourcePacket_LongBranch19:
.a16
.i16
SourcePacket_CheckRanges__bad:
.a16
.i16
    lda #0
    sta.l SOURCE_PACKET_ACTIVE_META+16
    sta.l SOURCE_PACKET_ACTIVE_META+48
    sta.l SourcePacket_Total
    clc
    rts
SourcePacket_CheckRanges__good:
.a16
.i16
    sec
    rts

; Foreground only: save each original signed9bit X at its OAM byte offset.
SourcePacket_BuildSignedX:
.a16
.i16
    lda #0
    sta.l SourcePacket_Meta
SourcePacket_BuildSignedX__actor:
.a16
.i16
    lda.l SourcePacket_Meta
    tax
    lda.l SOURCE_PACKET_ACTIVE_META+16,x
    cmp #1
    beq SourcePacket_LongBranch20
    brl SourcePacket_BuildSignedX__next_actor
SourcePacket_LongBranch20:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+2,x
    sta.l SourcePacket_End
    lda.l SOURCE_PACKET_ACTIVE_META,x
    sta.l SourcePacket_Sprite
SourcePacket_BuildSignedX__sprite:
.a16
.i16
    lda.l SourcePacket_Sprite
    lsr a
    lsr a
    lsr a
    lsr a
    tay
    lda.l SourcePacket_Sprite
    and #15
    lsr a
    lsr a
    tax
    lda.l SourcePacket_XMasks,x
    and #$00FF
    sta.l SourcePacket_Mask
    lda.w $5320,y
    and.w $5428
    bne SourcePacket_LongBranch21
    brl SourcePacket_BuildSignedX__positive
SourcePacket_LongBranch21:
.a16
.i16
    lda.l SourcePacket_Sprite
    tax
    lda.w $5120,x
    and #$00FF
    ora #$FF00
    bra SourcePacket_BuildSignedX__store
SourcePacket_BuildSignedX__positive:
.a16
.i16
    lda.l SourcePacket_Sprite
    tax
    lda.w $5120,x
    and #$00FF
SourcePacket_BuildSignedX__store:
.a16
.i16
    sta.w $5600,x
    lda.l SourcePacket_Sprite
    clc
    adc #4
    sta.l SourcePacket_Sprite
    cmp.l SourcePacket_End
    bcs SourcePacket_LongBranch22
    brl SourcePacket_BuildSignedX__sprite
SourcePacket_LongBranch22:
.a16
.i16
SourcePacket_BuildSignedX__next_actor:
.a16
.i16
    lda.l SourcePacket_Meta
    clc
    adc #32
    sta.l SourcePacket_Meta
    cmp #64
    bcs SourcePacket_LongBranch23
    brl SourcePacket_BuildSignedX__actor
SourcePacket_LongBranch23:
.a16
.i16
    rts

; A=signed SOURCE coordinate, C=valid, A=exact nearest4/5. Own scratch only.
SourcePacket_ProjectX:
.a16
.i16
    sta.l SourcePacket_ProjectInput
    lda #0
    sta.l SourcePacket_ProjectSign
    lda.l SourcePacket_ProjectInput
    bmi SourcePacket_LongBranch24
    brl SourcePacket_ProjectX__absolute
SourcePacket_LongBranch24:
.a16
.i16
    lda #1
    sta.l SourcePacket_ProjectSign
    lda.l SourcePacket_ProjectInput
    eor #$FFFF
    inc a
SourcePacket_ProjectX__absolute:
.a16
.i16
    cmp #$4000
    bcs SourcePacket_LongBranch25
    brl SourcePacket_ProjectX__valid
SourcePacket_LongBranch25:
.a16
.i16
    clc
    rts
SourcePacket_ProjectX__valid:
.a16
.i16
    sta.l SourcePacket_ProjectInput
    and #$00FF
    tax
    lda.l SourcePacket_QLo,x
    and #$00FF
    sta.l SourcePacket_ProjectQ
    lda.l SourcePacket_RLo,x
    and #$00FF
    sta.l SourcePacket_ProjectR
    lda.l SourcePacket_ProjectInput
    xba
    and #$00FF
    asl a
    tax
    lda.l SourcePacket_QHi,x
    clc
    adc.l SourcePacket_ProjectQ
    sta.l SourcePacket_ProjectQ
    txa
    lsr a
    tax
    lda.l SourcePacket_RHi,x
    and #$00FF
    clc
    adc.l SourcePacket_ProjectR
    clc
    adc #2
    tax
    lda.l SourcePacket_Carry,x
    and #$00FF
    clc
    adc.l SourcePacket_ProjectQ
    sta.l SourcePacket_ProjectQ
    lda.l SourcePacket_ProjectSign
    bne SourcePacket_LongBranch26
    brl SourcePacket_ProjectX__positive
SourcePacket_LongBranch26:
.a16
.i16
    lda.l SourcePacket_ProjectQ
    eor #$FFFF
    inc a
    sec
    rts
SourcePacket_ProjectX__positive:
.a16
.i16
    lda.l SourcePacket_ProjectQ
    sec
    rts

; Copy both source positions/bindings under the producer's sequence fence.
; DBR43; no foreground/world/input/cache state is ever modified.
SourcePacket_Refresh:
.a16
.i16
    lda #0
    sta.l SourcePacket_RefreshAccepted
    sta.l SourcePacket_MainRetryNeeded
    sta.l SourcePacket_Changed
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    bne SourcePacket_LongBranch27
    brl SourcePacket_Refresh__guard0
SourcePacket_LongBranch27:
.a16
.i16
    brl SourcePacket_Refresh__done
SourcePacket_Refresh__guard0:
.a16
.i16
    lda.l SourceVisual_CompletedMagic
    cmp #$C04D
    bne SourcePacket_LongBranch28
    brl SourcePacket_Refresh__guard1
SourcePacket_LongBranch28:
.a16
.i16
    brl SourcePacket_Refresh__done
SourcePacket_Refresh__guard1:
.a16
.i16
    lda.l SVActor_Magic
    cmp #$AC19
    bne SourcePacket_LongBranch29
    brl SourcePacket_Refresh__guard2
SourcePacket_LongBranch29:
.a16
.i16
    brl SourcePacket_Refresh__done
SourcePacket_Refresh__guard2:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
    bne SourcePacket_LongBranch30
    brl SourcePacket_Refresh__guard3
SourcePacket_LongBranch30:
.a16
.i16
    brl SourcePacket_Refresh__done
SourcePacket_Refresh__guard3:
.a16
.i16
    lda.l $7E1760
    cmp #1
    bne SourcePacket_LongBranch31
    brl SourcePacket_Refresh__guard4
SourcePacket_LongBranch31:
.a16
.i16
    brl SourcePacket_Refresh__done
SourcePacket_Refresh__guard4:
.a16
.i16
    lda.l $7E46DC
    cmp #1
    bne SourcePacket_LongBranch32
    brl SourcePacket_Refresh__guard5
SourcePacket_LongBranch32:
.a16
.i16
    brl SourcePacket_Refresh__done
SourcePacket_Refresh__guard5:
.a16
.i16
    lda.l Game_State
    cmp #0
    bne SourcePacket_LongBranch33
    brl SourcePacket_Refresh__guard6
SourcePacket_LongBranch33:
.a16
.i16
    brl SourcePacket_Refresh__done
SourcePacket_Refresh__guard6:
.a16
.i16
    lda.l Stage_Mirror
    and #$00FF
    bne SourcePacket_LongBranch34
    brl SourcePacket_Refresh__guard7
SourcePacket_LongBranch34:
.a16
.i16
    brl SourcePacket_Refresh__done
SourcePacket_Refresh__guard7:
.a16
.i16
    lda.l $41200A
    and #$00FF
    bne SourcePacket_LongBranch35
    brl SourcePacket_Refresh__guard8
SourcePacket_LongBranch35:
.a16
.i16
    brl SourcePacket_Refresh__done
SourcePacket_Refresh__guard8:
.a16
.i16
    lda.l Screen_PosX
    cmp #$4000
    bcs SourcePacket_LongBranch36
    brl SourcePacket_Refresh__guard9
SourcePacket_LongBranch36:
.a16
.i16
    brl SourcePacket_Refresh__done
SourcePacket_Refresh__guard9:
.a16
.i16
    jsr SourcePacket_CheckRanges
    bcc SourcePacket_LongBranch37
    brl SourcePacket_Refresh__guard10
SourcePacket_LongBranch37:
.a16
.i16
    brl SourcePacket_Refresh__done
SourcePacket_Refresh__guard10:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    bne SourcePacket_LongBranch38
    brl SourcePacket_Refresh__guard11
SourcePacket_LongBranch38:
.a16
.i16
    ; The source producer was busy or changed during the coherent copy.
    lda #1
    sta.l SourcePacket_MainRetryNeeded
    brl SourcePacket_Refresh__done
SourcePacket_Refresh__guard11:
.a16
.i16
    lda.l $434E7C
    sta.l SourcePacket_ReadSeq
    and #1
    bne SourcePacket_LongBranch39
    brl SourcePacket_Refresh__guard12
SourcePacket_LongBranch39:
.a16
.i16
    ; The source producer was busy or changed during the coherent copy.
    lda #1
    sta.l SourcePacket_MainRetryNeeded
    brl SourcePacket_Refresh__done
SourcePacket_Refresh__guard12:
.a16
.i16
    lda.l $434E2C
    sta.l SourcePacket_ReadStage
    lda #0
    sta.l SourcePacket_Slot
SourcePacket_Refresh__read_actor:
.a16
.i16
    lda.l SourcePacket_Slot
    asl a
    tax
    lda.l SourcePacket_SourceRows,x
    tay
    lda.l SourcePacket_Slot
    asl a
    asl a
    asl a
    asl a
    tax
    lda.w $4E34,y
    sta.w $53C0,x
    lda.w $4E3C,y
    sta.w $53C2,x
    lda.w $4E40,y
    sta.w $53C4,x
    lda.w $4E42,y
    sta.w $53C6,x
    lda.w $4E44,y
    sta.w $53C8,x
    lda.w $4E4A,y
    sta.w $53CA,x
    lda.l SourcePacket_Slot
    asl a
    tay
    lda.w $4E9C,y
    sta.w $53CC,x
    lda.l SourcePacket_Slot
    inc a
    sta.l SourcePacket_Slot
    cmp #2
    bcs SourcePacket_LongBranch40
    brl SourcePacket_Refresh__read_actor
SourcePacket_LongBranch40:
.a16
.i16
    lda.l $434E7C
    cmp.l SourcePacket_ReadSeq
    bne SourcePacket_LongBranch41
    brl SourcePacket_Refresh__guard13
SourcePacket_LongBranch41:
.a16
.i16
    ; The source producer was busy or changed during the coherent copy.
    lda #1
    sta.l SourcePacket_MainRetryNeeded
    brl SourcePacket_Refresh__done
SourcePacket_Refresh__guard13:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    bne SourcePacket_LongBranch42
    brl SourcePacket_Refresh__guard14
SourcePacket_LongBranch42:
.a16
.i16
    ; The source producer was busy or changed during the coherent copy.
    lda #1
    sta.l SourcePacket_MainRetryNeeded
    brl SourcePacket_Refresh__done
SourcePacket_Refresh__guard14:
.a16
.i16
    lda.l SourcePacket_ReadStage
    cmp.l Game_StageIndex
    bne SourcePacket_LongBranch43
    brl SourcePacket_Refresh__guard15
SourcePacket_LongBranch43:
.a16
.i16
    brl SourcePacket_Refresh__done
SourcePacket_Refresh__guard15:
.a16
.i16
    lda #1
    sta.l SourcePacket_RefreshAccepted
    lda #0
    sta.l SourcePacket_Slot
SourcePacket_Refresh__actor:
.a16
.i16
    lda.l SourcePacket_Slot
    asl a
    asl a
    asl a
    asl a
    sta.l SourcePacket_Snap
    tax
    asl a
    sta.l SourcePacket_Meta
    tay
    lda.l SourcePacket_Slot
    bne SourcePacket_LongBranch44
    brl SourcePacket_Refresh__p1_native
SourcePacket_LongBranch44:
.a16
.i16
    lda #133
SourcePacket_Refresh__p1_native:
.a16
.i16
    sta.l SourcePacket_Native
    lda.w $5390,y
    cmp #1
    bne SourcePacket_LongBranch45
    brl SourcePacket_Refresh__guard16
SourcePacket_LongBranch45:
.a16
.i16
    brl SourcePacket_Refresh__next_actor
SourcePacket_Refresh__guard16:
.a16
.i16
    lda.w $538A,y
    cmp.l Game_StageIndex
    bne SourcePacket_LongBranch46
    brl SourcePacket_Refresh__guard17
SourcePacket_LongBranch46:
.a16
.i16
    brl SourcePacket_Refresh__next_actor
SourcePacket_Refresh__guard17:
.a16
.i16
    lda.w $538C,y
    and #$00FF
    cmp.w $5388,y
    bne SourcePacket_LongBranch47
    brl SourcePacket_Refresh__guard18
SourcePacket_LongBranch47:
.a16
.i16
    brl SourcePacket_Refresh__next_actor
SourcePacket_Refresh__guard18:
.a16
.i16
    lda.w $539A,y
    cmp #CHAR_SELECTED_JUMP
    beq SourcePacket_LongBranch48
    brl SourcePacket_Refresh__guard19
SourcePacket_LongBranch48:
.a16
.i16
    brl SourcePacket_Refresh__next_actor
SourcePacket_Refresh__guard19:
.a16
.i16
    lda.w $53C4,x
    cmp #1
    bne SourcePacket_LongBranch49
    brl SourcePacket_Refresh__guard20
SourcePacket_LongBranch49:
.a16
.i16
    brl SourcePacket_Refresh__next_actor
SourcePacket_Refresh__guard20:
.a16
.i16
    lda.w $53C6,x
    bne SourcePacket_LongBranch50
    brl SourcePacket_Refresh__guard21
SourcePacket_LongBranch50:
.a16
.i16
    brl SourcePacket_Refresh__next_actor
SourcePacket_Refresh__guard21:
.a16
.i16
    lda.w $53C8,x
    beq SourcePacket_LongBranch51
    brl SourcePacket_Refresh__guard22
SourcePacket_LongBranch51:
.a16
.i16
    brl SourcePacket_Refresh__next_actor
SourcePacket_Refresh__guard22:
.a16
.i16
    lda.w $53C8,x
    and #$8000
    bne SourcePacket_LongBranch52
    brl SourcePacket_Refresh__guard23
SourcePacket_LongBranch52:
.a16
.i16
    brl SourcePacket_Refresh__next_actor
SourcePacket_Refresh__guard23:
.a16
.i16
    lda.w $53CA,x
    and #$00FF
    cmp #2
    bne SourcePacket_LongBranch53
    brl SourcePacket_Refresh__guard24
SourcePacket_LongBranch53:
.a16
.i16
    brl SourcePacket_Refresh__next_actor
SourcePacket_Refresh__guard24:
.a16
.i16
    lda.w $53CC,x
    cmp.l SourcePacket_Native
    bne SourcePacket_LongBranch54
    brl SourcePacket_Refresh__guard25
SourcePacket_LongBranch54:
.a16
.i16
    brl SourcePacket_Refresh__next_actor
SourcePacket_Refresh__guard25:
.a16
.i16
    lda.w $53C2,x
    cmp.w $5398,y
    beq SourcePacket_LocomotionFamily__accepted
    ; E4 changes9<->18 at idle/walk edges in the measured source world.
    ; Translate the already-owned image through that edge; never substitute
    ; a pose or permit an unrelated animation family to cross this guard.
    cmp #9
    beq SourcePacket_LocomotionFamily__new_ground
    cmp #18
    beq SourcePacket_LocomotionFamily__new_ground
    brl SourcePacket_LongBranch55
SourcePacket_LocomotionFamily__new_ground:
.a16
.i16
    lda.w $5398,y
    cmp #9
    beq SourcePacket_LocomotionFamily__accepted
    cmp #18
    beq SourcePacket_LocomotionFamily__accepted
    brl SourcePacket_LongBranch55
SourcePacket_LocomotionFamily__accepted:
.a16
.i16
    brl SourcePacket_Refresh__guard26
SourcePacket_LongBranch55:
.a16
.i16
    brl SourcePacket_Refresh__next_actor
SourcePacket_Refresh__guard26:
.a16
.i16
    lda.l SourcePacket_Native
    tax
    lda.l $7E0A00+CHAR_HP,x
    and #$00FF
    beq SourcePacket_LongBranch56
    brl SourcePacket_Refresh__guard27
SourcePacket_LongBranch56:
.a16
.i16
    brl SourcePacket_Refresh__next_actor
SourcePacket_Refresh__guard27:
.a16
.i16
    lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
    and #$00FF
    cmp #1
    bne SourcePacket_LongBranch57
    brl SourcePacket_Refresh__guard28
SourcePacket_LongBranch57:
.a16
.i16
    brl SourcePacket_Refresh__next_actor
SourcePacket_Refresh__guard28:
.a16
.i16
    lda.l $7E0A00+CHAR_ROSTER_INDEX,x
    and #$00FF
    cmp.w $5388,y
    bne SourcePacket_LongBranch58
    brl SourcePacket_Refresh__guard29
SourcePacket_LongBranch58:
.a16
.i16
    brl SourcePacket_Refresh__next_actor
SourcePacket_Refresh__guard29:
.a16
.i16
    lda.l $7E0A00+CHAR_SELECTED,x
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
    beq SourcePacket_LongBranch59
    brl SourcePacket_Refresh__guard30
SourcePacket_LongBranch59:
.a16
.i16
    brl SourcePacket_Refresh__next_actor
SourcePacket_Refresh__guard30:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy,x
    and #$00FF
    cmp #2
    bne SourcePacket_LongBranch60
    brl SourcePacket_Refresh__guard31
SourcePacket_LongBranch60:
.a16
.i16
    brl SourcePacket_Refresh__next_actor
SourcePacket_Refresh__guard31:
.a16
.i16
    ; Keep signed projection/subtraction strictly inside16bit range.
    lda.w $5384,y
    bmi SourcePacket_LongBranch61
    brl SourcePacket_Refresh__foot_positive
SourcePacket_LongBranch61:
.a16
.i16
    cmp #$F800
    bcc SourcePacket_LongBranch62
    brl SourcePacket_Refresh__foot_valid
SourcePacket_LongBranch62:
.a16
.i16
    brl SourcePacket_Refresh__next_actor
SourcePacket_Refresh__foot_positive:
.a16
.i16
    cmp #$0800
    bcs SourcePacket_LongBranch63
    brl SourcePacket_Refresh__foot_valid
SourcePacket_LongBranch63:
.a16
.i16
    brl SourcePacket_Refresh__next_actor
SourcePacket_Refresh__foot_valid:
.a16
.i16
    lda.l SourcePacket_Snap
    tax
    lda.w $53C0,x
    jsr SourcePacket_ProjectX
    bcc SourcePacket_LongBranch64
    brl SourcePacket_Refresh__projected
SourcePacket_LongBranch64:
.a16
.i16
    brl SourcePacket_Refresh__next_actor
SourcePacket_Refresh__projected:
.a16
.i16
    sec
    sbc.l Screen_PosX
    sec
    sbc.w $5384,y
    cmp.w $539E,y
    beq SourcePacket_LongBranch65
    brl SourcePacket_Refresh__changed
SourcePacket_LongBranch65:
.a16
.i16
    brl SourcePacket_Refresh__next_actor
SourcePacket_Refresh__changed:
.a16
.i16
    sta.l SourcePacket_Delta
    sta.w $539E,y
    lda.w $5382,y
    sta.l SourcePacket_End
    lda.w $5380,y
    sta.l SourcePacket_Begin
    and #15
    lsr a
    lsr a
    tax
    lda.l SourcePacket_XMasks,x
    and #$00FF
    sta.l SourcePacket_Mask
    lda.l SourcePacket_Begin
    lsr a
    lsr a
    lsr a
    lsr a
    clc
    adc #512
    tay
    lda.l SourcePacket_Begin
    tax
SourcePacket_Refresh__sprite:
.a16
.i16
    lda.w $5600,x
    clc
    adc.w $542C
    bpl SourcePacket_LongBranch66
    brl SourcePacket_Refresh__negative_x
SourcePacket_LongBranch66:
.a16
.i16
    cmp #$0100
    bcs SourcePacket_LongBranch67
    brl SourcePacket_Refresh__x_valid
SourcePacket_LongBranch67:
.a16
.i16
    lda #$FF00
    bra SourcePacket_Refresh__x_valid
SourcePacket_Refresh__negative_x:
.a16
.i16
    cmp #$FF00
    bcc SourcePacket_LongBranch68
    brl SourcePacket_Refresh__x_valid
SourcePacket_LongBranch68:
.a16
.i16
    ; X=-256 hides every legal OBJ size; no vertical wrap or Y mutation.
    lda #$FF00
SourcePacket_Refresh__x_valid:
.a16
.i16
    sta.l SourcePacket_NewX
    sep #$20
.a8
    sta.w $4F00,x
    xba
    and #1
    bne SourcePacket_LongBranch69
    brl SourcePacket_Refresh__clear_xbit
SourcePacket_LongBranch69:
.a8
.i16
    lda.w $4F00,y
    ora.w $5428
    sta.w $4F00,y
    bra SourcePacket_Refresh__xbit_done
SourcePacket_Refresh__clear_xbit:
.a8
.i16
    lda.w $5428
    eor #$FF
    and.w $4F00,y
    sta.w $4F00,y
SourcePacket_Refresh__xbit_done:
.a8
.i16
    lda.w $5428
    asl a
    asl a
    beq SourcePacket_LongBranch70
    brl SourcePacket_Refresh__same_hi_byte
SourcePacket_LongBranch70:
.a8
.i16
    lda #1
    iny
SourcePacket_Refresh__same_hi_byte:
.a8
.i16
    sta.w $5428
    rep #$30
.a16
.i16
    inx
    inx
    inx
    inx
    cpx.w $5424
    bcs SourcePacket_LongBranch71
    brl SourcePacket_Refresh__sprite
SourcePacket_LongBranch71:
.a16
.i16
    lda #1
    sta.l SourcePacket_Changed
SourcePacket_Refresh__next_actor:
.a16
.i16
    lda.l SourcePacket_Slot
    inc a
    sta.l SourcePacket_Slot
    cmp #2
    bcc SourcePacket_LongBranch72
    brl SourcePacket_Refresh__done
SourcePacket_LongBranch72:
.a16
.i16
    brl SourcePacket_Refresh__actor
SourcePacket_Refresh__done:
.a16
.i16
    rts

; The private full544 row already supplies the entire high table. Cancel
; only this-frame exact redundant legacy high rows under the compositor gate.
; Called once per completed submission, even when no resources await retirement.
; The existing exact-row and scope guards remain the sole cancellation authority.
SourcePacket_CancelFrameHi:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    ldx #0
SourcePacket_CancelFrameHi__scan:
.a16
.i16
    jsr SourcePacket_IsQueueRow
    bcs SourcePacket_CancelFrameHi__found
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourcePacket_CancelFrameHi__scan
    bra SourcePacket_CancelFrameHi__done
SourcePacket_CancelFrameHi__found:
.a16
.i16
    jsl SourcePacket_CancelRedundantHi
SourcePacket_CancelFrameHi__done:
.a16
.i16
    ply
    plx
    pla
    plp
    rtl

SourcePacket_CancelRedundantHi:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    phb
    phd
    jsr SourcePacket_IsQueueRow
    bcc SourcePacket_LongBranch73
    brl SourcePacket_CancelRedundantHi__guard32
SourcePacket_LongBranch73:
.a16
.i16
    brl SourcePacket_CancelRedundantHi__done
SourcePacket_CancelRedundantHi__guard32:
.a16
.i16
    lda.l SourcePacket_ThisFrame
    cmp #1
    bne SourcePacket_LongBranch74
    brl SourcePacket_CancelRedundantHi__guard33
SourcePacket_LongBranch74:
.a16
.i16
    brl SourcePacket_CancelRedundantHi__done
SourcePacket_CancelRedundantHi__guard33:
.a16
.i16
    lda.l SourcePacket_ActiveValid
    cmp #1
    bne SourcePacket_LongBranch75
    brl SourcePacket_CancelRedundantHi__guard34
SourcePacket_LongBranch75:
.a16
.i16
    brl SourcePacket_CancelRedundantHi__done
SourcePacket_CancelRedundantHi__guard34:
.a16
.i16
    lda.l SourcePacket_CopyBusy
    bne SourcePacket_LongBranch76
    brl SourcePacket_CancelRedundantHi__guard35
SourcePacket_LongBranch76:
.a16
.i16
    brl SourcePacket_CancelRedundantHi__done
SourcePacket_CancelRedundantHi__guard35:
.a16
.i16
    lda.l SourceVisual_CompletedHeld
    and #$00FF
    cmp #1
    bne SourcePacket_LongBranch77
    brl SourcePacket_CancelRedundantHi__guard36
SourcePacket_LongBranch77:
.a16
.i16
    brl SourcePacket_CancelRedundantHi__done
SourcePacket_CancelRedundantHi__guard36:
.a16
.i16
    lda.l Nmi_FrameBusy
    and #$00FF
    cmp #1
    bne SourcePacket_LongBranch78
    brl SourcePacket_CancelRedundantHi__guard37
SourcePacket_LongBranch78:
.a16
.i16
    brl SourcePacket_CancelRedundantHi__done
SourcePacket_CancelRedundantHi__guard37:
.a16
.i16
    lda.l SourceVisual_CompletedMagic
    cmp #$C04D
    bne SourcePacket_LongBranch79
    brl SourcePacket_CancelRedundantHi__guard38
SourcePacket_LongBranch79:
.a16
.i16
    brl SourcePacket_CancelRedundantHi__done
SourcePacket_CancelRedundantHi__guard38:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
    bne SourcePacket_LongBranch80
    brl SourcePacket_CancelRedundantHi__guard39
SourcePacket_LongBranch80:
.a16
.i16
    brl SourcePacket_CancelRedundantHi__done
SourcePacket_CancelRedundantHi__guard39:
.a16
.i16
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    bne SourcePacket_LongBranch81
    brl SourcePacket_CancelRedundantHi__guard40
SourcePacket_LongBranch81:
.a16
.i16
    brl SourcePacket_CancelRedundantHi__done
SourcePacket_CancelRedundantHi__guard40:
.a16
.i16
    lda.l SVActor_Magic
    cmp #$AC19
    beq SourcePacket_CancelRedundantHi__actor_scope
    brl SourcePacket_CancelRedundantHi__done
SourcePacket_CancelRedundantHi__actor_scope:
.a16
.i16
    lda.l $7E1760
    cmp #1
    beq SourcePacket_CancelRedundantHi__host_scope
    brl SourcePacket_CancelRedundantHi__done
SourcePacket_CancelRedundantHi__host_scope:
.a16
.i16
    lda.l $7E46DC
    cmp #1
    beq SourcePacket_CancelRedundantHi__armed_scope
    brl SourcePacket_CancelRedundantHi__done
SourcePacket_CancelRedundantHi__armed_scope:
.a16
.i16
    ldx #0
SourcePacket_CancelRedundantHi__row:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    cmp #$41
    beq SourcePacket_LongBranch82
    brl SourcePacket_CancelRedundantHi__next
SourcePacket_LongBranch82:
.a16
.i16
    lda.l DmaQueue,x
    bne SourcePacket_CancelRedundantHi__length_nonzero
    brl SourcePacket_CancelRedundantHi__next
SourcePacket_CancelRedundantHi__length_nonzero:
.a16
.i16
    cmp #33
    bcc SourcePacket_CancelRedundantHi__length_valid
    brl SourcePacket_CancelRedundantHi__next
SourcePacket_CancelRedundantHi__length_valid:
.a16
.i16
    lda.l DmaQueue+2,x
    cmp #$0100
    beq SourcePacket_LongBranch84
    brl SourcePacket_CancelRedundantHi__next
SourcePacket_LongBranch84:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$5300
    beq SourcePacket_LongBranch85
    brl SourcePacket_CancelRedundantHi__next
SourcePacket_LongBranch85:
.a16
.i16
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    beq SourcePacket_LongBranch86
    brl SourcePacket_CancelRedundantHi__next
SourcePacket_LongBranch86:
.a16
.i16
    phx
    txa
    lsr a
    lsr a
    lsr a
    tax
    lda.l DmaQueue_Owner,x
    and #$00FF
    plx
    cmp #0
    beq SourcePacket_LongBranch87
    brl SourcePacket_CancelRedundantHi__next
SourcePacket_LongBranch87:
.a16
.i16
    lda.l DmaQueue_BudgetTotal
    cmp.l DmaQueue,x
    bcs SourcePacket_LongBranch88
    brl SourcePacket_CancelRedundantHi__next
SourcePacket_LongBranch88:
.a16
.i16
    sec
    sbc.l DmaQueue,x
    sta.l DmaQueue_BudgetTotal
    sep #$20
.a8
    lda #0
    sta.l DmaQueue+4,x
    rep #$30
.a16
.i16
SourcePacket_CancelRedundantHi__next:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcs SourcePacket_LongBranch89
    brl SourcePacket_CancelRedundantHi__row
SourcePacket_LongBranch89:
.a16
.i16
SourcePacket_CancelRedundantHi__done:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    rtl

; Position-only transport while the normal compositor is busy. No queue
; draining, tile/palette writes, OAM completion flags, or resource retirement.
SourcePacket_NmiGate:
    jsl SourceInput_NmiGate
    jsl SourcePacket_NmiPublish
    rtl

SourcePacket_NmiPublish:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    phb
    phd
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq SourcePacket_NmiPublish__campaign3
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__campaign3:
.a16
.i16
    lda.l SourcePacket_ActiveValid
    cmp #1
    beq SourcePacket_NmiPublish__scope0
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__scope0:
.a16
.i16
    lda.l SourcePacket_CopyBusy
    beq SourcePacket_NmiPublish__scope1
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__scope1:
.a16
.i16
    lda.l SourcePacket_NmiPending
    cmp #1
    beq SourcePacket_NmiPublish__cached0
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__cached0:
.a16
.i16
    lda.l Nmi_FrameBusy
    and #$00FF
    cmp #2
    bcc SourcePacket_NmiPublish__scope2
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__scope2:
.a16
.i16
    sta.l SourcePacket_NmiMainBusy
    cmp #1
    bne SourcePacket_NmiPublish__camera_ready
    lda.l SourcePacket_ActiveCamera
    cmp.l Screen_PosX
    beq SourcePacket_NmiPublish__camera_ready
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__camera_ready:
.a16
.i16
    lda.l Nmi_HdmaEnableCurrent
    and #$0080
    beq SourcePacket_NmiPublish__scope3
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__scope3:
.a16
.i16
    lda.l $004212
    and #$0080
    bne SourcePacket_NmiPublish__scope4
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__scope4:
.a16
.i16
    ; A pending OAM row owns the next full picture. Any active bank43
    ; descriptor could touch private BW-RAM; reject rather than follow it.
    lda #0
    sta.l SourcePacket_NmiQueueRows
    ldx #0
SourcePacket_NmiPublish__queue:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    bne SourcePacket_NmiPublish__active_row
    brl SourcePacket_NmiPublish__next_row
SourcePacket_NmiPublish__active_row:
.a16
.i16
    ; First reject resource/special/reverse/unknown rows cheaply, before
    ; spending time on cached-actor validation or the normal PPU commit.
    lda.l SourcePacket_NmiMainBusy
    cmp #1
    beq SourcePacket_NmiPublish__busy_queue
    lda.l DmaQueue+4,x
    and #$00FF
    cmp #$40
    beq SourcePacket_NmiPublish__background_type
    cmp #$42
    beq SourcePacket_NmiPublish__background_type
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__background_type:
.a16
.i16
    phx
    txa
    lsr a
    lsr a
    lsr a
    tax
    lda.l DmaQueue_Owner,x
    and #$00FF
    plx
    cmp #0
    beq SourcePacket_NmiPublish__background_unowned
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__background_unowned:
.a16
.i16
    ; Descriptor validation costs time too: reject a fifth row before the
    ; expensive second pass. The measured eight-row case delayed normal PPU.
    lda.l SourcePacket_NmiQueueRows
    inc a
    cmp #5
    bcc SourcePacket_NmiPublish__background_counted
    jmp SourcePacket_UnrolledBudgetBridge
SourcePacket_NmiPublish__background_counted:
.a16
.i16
    sta.l SourcePacket_NmiQueueRows
    brl SourcePacket_NmiPublish__next_row
SourcePacket_NmiPublish__busy_queue:
.a16
.i16
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$43
    bne SourcePacket_NmiPublish__not_private_bank
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__not_private_bank:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$001F
    cmp #DMA_TYPE_OAM
    beq SourcePacket_NmiPublish__oam_blocked
    brl SourcePacket_NmiPublish__next_row
SourcePacket_NmiPublish__oam_blocked:
.a16
.i16
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__next_row:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcs SourcePacket_NmiPublish__queue_scanned
    brl SourcePacket_NmiPublish__queue
SourcePacket_NmiPublish__queue_scanned:
.a16
.i16
    lda.l SourcePacket_NmiMainBusy
    cmp #1
    beq SourcePacket_NmiPublish__queue_bounded
    jsr SourcePacket_CheckBackgroundBudget
    bcs SourcePacket_NmiPublish__queue_bounded
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__queue_bounded:
.a16
.i16
    lda.l SourcePacket_RefreshAccepted
    cmp #1
    beq SourcePacket_NmiPublish__cached1
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__cached1:
.a16
.i16
SourcePacket_NmiPublish__cached2:
.a16
.i16
    lda.l Game_State
    beq SourcePacket_NmiPublish__cached3
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__cached3:
.a16
.i16
    lda.l Stage_Mirror
    and #$00FF
    beq SourcePacket_NmiPublish__cached4
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__cached4:
.a16
.i16
    lda.l SourceVisual_CompletedMagic
    cmp #$C04D
    beq SourcePacket_NmiPublish__cached5
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__cached5:
.a16
.i16
    lda.l SVActor_Magic
    cmp #$AC19
    beq SourcePacket_NmiPublish__cached6
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__cached6:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SourcePacket_NmiPublish__cached7
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__cached7:
.a16
.i16
    lda.l $7E1760
    cmp #1
    beq SourcePacket_NmiPublish__cached8
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__cached8:
.a16
.i16
    lda.l $7E46DC
    cmp #1
    beq SourcePacket_NmiPublish__cached9
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__cached9:
.a16
.i16
    lda.l SourcePacket_ReadStage
    cmp.l Game_StageIndex
    beq SourcePacket_NmiPublish__cached10
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__cached10:
.a16
.i16
    lda.l SourcePacket_PendingCamera
    cmp.l Screen_PosX
    beq SourcePacket_NmiPublish__cached11
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__cached11:
.a16
.i16
    lda.l $435390
    cmp #1
    bne SourcePacket_NmiPublish__player0_next
    lda.l $7E0A00+CHAR_HP
    and #$00FF
    bne SourcePacket_NmiPublish__player0_guard0
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__player0_guard0:
.a16
.i16
    lda.l $7E0A00+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    beq SourcePacket_NmiPublish__player0_guard1
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__player0_guard1:
.a16
.i16
    lda.l $7E0A00+CHAR_ROSTER_INDEX
    and #$00FF
    cmp.l $435388
    beq SourcePacket_NmiPublish__player0_guard2
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__player0_guard2:
.a16
.i16
SourcePacket_NmiPublish__player0_next:
.a16
.i16
    lda.l $4353B0
    cmp #1
    bne SourcePacket_NmiPublish__player1_next
    lda.l $7E0A85+CHAR_HP
    and #$00FF
    bne SourcePacket_NmiPublish__player1_guard0
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__player1_guard0:
.a16
.i16
    lda.l $7E0A85+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    beq SourcePacket_NmiPublish__player1_guard1
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__player1_guard1:
.a16
.i16
    lda.l $7E0A85+CHAR_ROSTER_INDEX
    and #$00FF
    cmp.l $4353A8
    beq SourcePacket_NmiPublish__player1_guard2
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__player1_guard2:
.a16
.i16
SourcePacket_NmiPublish__player1_next:
.a16
.i16
    brl SourcePacket_NmiPublish__deadline
SourcePacket_NmiPublish__deadline:
.a16
.i16
    sep #$20
.a8
    lda.l $004212
    and #$80
    bne SourcePacket_NmiPublish__blank
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__blank:
.a8
.i16
    ; Latch the real beam after CPU projection. At NTSC line245 or earlier
    ; the544-byte transfer has over16 scanlines of blanking left.
    ; BOR's boot clears WRIO bit7. Temporarily enable software latching,
    ; preserving both controller-port output bits and every other I/O bit.
    lda.l $004213
    pha
    ora #$80
    sta.l $004201
    lda.l $002137
    lda.l $00213F
    lda.l $00213D
    sta.l SourcePacket_VCounter
    lda.l $00213D
    and #1
    sta.l SourcePacket_VCounter+1
    pla
    sta.l $004201
    lda.l SourcePacket_VCounter+1
    beq SourcePacket_NmiPublish__low_line
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__low_line:
.a8
.i16
    lda.l SourcePacket_VCounter
    cmp #225
    bcs SourcePacket_NmiPublish__after_active
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__after_active:
.a8
.i16
    cmp #246
    bcc SourcePacket_NmiPublish__bounded_line
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__bounded_line:
.a8
.i16
    lda.l SourcePacket_NmiMainBusy
    cmp #1
    beq SourcePacket_NmiPublish__dma
    ; An empty normal commit can still write BG/window registers afterward.
    ; Leave at least21 scanlines rather than the busy path's16.
    lda.l SourcePacket_VCounter
    cmp #241
    bcc SourcePacket_NmiPublish__dma
    brl SourcePacket_NmiPublish__done
SourcePacket_NmiPublish__dma:
.a8
.i16
    ; Preserve all seven channel registers modified by this direct DMA.
    lda.l $004370
    pha
    lda.l $004371
    pha
    lda.l $004372
    pha
    lda.l $004373
    pha
    lda.l $004374
    pha
    lda.l $004375
    pha
    lda.l $004376
    pha
    lda #0
    sta.l $002102
    sta.l $002103
    sta.l $004370
    sta.l $004372
    lda #4
    sta.l $004371
    lda #$4F
    sta.l $004373
    lda #$43
    sta.l $004374
    lda #$20
    sta.l $004375
    lda #2
    sta.l $004376
    lda #$80
SourcePacket_NmiPublish__transfer:
.a8
.i16
    sta.l $00420B
SourcePacket_NmiPublish__transferred:
.a8
.i16
    pla
    sta.l $004376
    pla
    sta.l $004375
    pla
    sta.l $004374
    pla
    sta.l $004373
    pla
    sta.l $004372
    pla
    sta.l $004371
    pla
    sta.l $004370
    rep #$30
.a16
.i16
    lda #0
    sta.l SourcePacket_NmiPending
SourcePacket_NmiPublish__done:
    rep #$30
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    rtl

; The linker installs the original same-field input/world clock call here.
; Projection follows every normal PPU write, so it cannot delay blanking.
; Called only after the immutable first pass proved every active row is
; unowned exact-forward VRAM40/CGRAM42. Sum REAL descriptor lengths, never
; trust the queue's accounting total. At most256 bytes and4 short setup paths.
SourcePacket_CheckBackgroundBudget:
.a16
.i16
    lda #0
    sta.l SourcePacket_NmiQueueTotal
    ldx #0
SourcePacket_CheckBackgroundBudget__row:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    bne SourcePacket_CheckBackgroundBudget__active
    brl SourcePacket_CheckBackgroundBudget__next
SourcePacket_CheckBackgroundBudget__active:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    sta.l SourcePacket_NmiRowType
    lda.l DmaQueue,x
    bne SourcePacket_CheckBackgroundBudget__guard0
    brl SourcePacket_CheckBackgroundBudget__bad
SourcePacket_CheckBackgroundBudget__guard0:
.a16
.i16
    cmp #257
    bcc SourcePacket_CheckBackgroundBudget__guard1
    brl SourcePacket_CheckBackgroundBudget__bad
SourcePacket_CheckBackgroundBudget__guard1:
.a16
.i16
    sta.l SourcePacket_NmiRowLength
    and #1
    beq SourcePacket_CheckBackgroundBudget__guard2
    brl SourcePacket_CheckBackgroundBudget__bad
SourcePacket_CheckBackgroundBudget__guard2:
.a16
.i16
    lda.l DmaQueue+2,x
    and #1
    beq SourcePacket_CheckBackgroundBudget__guard3
    brl SourcePacket_CheckBackgroundBudget__bad
SourcePacket_CheckBackgroundBudget__guard3:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    clc
    adc.l SourcePacket_NmiQueueTotal
    cmp #257
    bcc SourcePacket_CheckBackgroundBudget__guard4
    brl SourcePacket_CheckBackgroundBudget__bad
SourcePacket_CheckBackgroundBudget__guard4:
.a16
.i16
    sta.l SourcePacket_NmiQueueTotal
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    beq SourcePacket_CheckBackgroundBudget__source_bank
    cmp #$7F
    beq SourcePacket_CheckBackgroundBudget__source_bank
    cmp #$40
    bcc SourcePacket_CheckBackgroundBudget__rom_bank
    brl SourcePacket_CheckBackgroundBudget__bad
SourcePacket_CheckBackgroundBudget__rom_bank:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$8000
    bcs SourcePacket_CheckBackgroundBudget__source_bank
    brl SourcePacket_CheckBackgroundBudget__bad
SourcePacket_CheckBackgroundBudget__source_bank:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    dec a
    sta.l SourcePacket_NmiRowSpan
    lda.l DmaQueue+5,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_CheckBackgroundBudget__source_range
    brl SourcePacket_CheckBackgroundBudget__bad
SourcePacket_CheckBackgroundBudget__source_range:
.a16
.i16
    lda.l SourcePacket_NmiRowType
    cmp #$42
    beq SourcePacket_CheckBackgroundBudget__palette_range
    ; Generic background work must not overwrite any of the64 held OBJ
    ; cache blocks at VRAM8000..BFFF, even if a bad row claims owner0.
    lda.l DmaQueue+2,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_CheckBackgroundBudget__target_valid
    brl SourcePacket_CheckBackgroundBudget__bad
SourcePacket_CheckBackgroundBudget__target_valid:
.a16
.i16
    sta.l SourcePacket_NmiTargetEnd
    lda.l DmaQueue+2,x
    cmp #$8000
    bcc SourcePacket_CheckBackgroundBudget__below_obj
    cmp #$C000
    bcs SourcePacket_CheckBackgroundBudget__next
    brl SourcePacket_CheckBackgroundBudget__bad
SourcePacket_CheckBackgroundBudget__below_obj:
.a16
.i16
    lda.l SourcePacket_NmiTargetEnd
    cmp #$8000
    bcc SourcePacket_CheckBackgroundBudget__next
    brl SourcePacket_CheckBackgroundBudget__bad
SourcePacket_CheckBackgroundBudget__palette_range:
.a16
.i16
    ; Background CGRAM is byte0..255. OBJ palettes remain resource-owned.
    lda.l DmaQueue+2,x
    cmp #256
    bcc SourcePacket_CheckBackgroundBudget__palette_target
    brl SourcePacket_CheckBackgroundBudget__bad
SourcePacket_CheckBackgroundBudget__palette_target:
.a16
.i16
    clc
    adc.l SourcePacket_NmiRowLength
    cmp #257
    bcc SourcePacket_CheckBackgroundBudget__next
    brl SourcePacket_CheckBackgroundBudget__bad
SourcePacket_CheckBackgroundBudget__next:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcs SourcePacket_CheckBackgroundBudget__good
    brl SourcePacket_CheckBackgroundBudget__row
SourcePacket_CheckBackgroundBudget__good:
.a16
.i16
    sec
    rts
SourcePacket_CheckBackgroundBudget__bad:
.a16
.i16
    clc
    rts

SourcePacket_NmiTail:
SourcePacket_NmiTail__clock:
    nop
    nop
    nop
    nop
    jsl SourcePacket_NmiPrepare
    rtl

SourcePacket_NmiPrepare:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    phb
    phd
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq SourcePacket_NmiPrepare__campaign3
    brl SourcePacket_NmiPrepare__done
SourcePacket_NmiPrepare__campaign3:
.a16
.i16
    lda.l SourcePacket_ActiveValid
    cmp #1
    beq SourcePacket_NmiPrepare__active
    brl SourcePacket_NmiPrepare__done
SourcePacket_NmiPrepare__active:
.a16
.i16
    lda.l SourcePacket_CopyBusy
    beq SourcePacket_NmiPrepare__scan
    brl SourcePacket_NmiPrepare__done
SourcePacket_NmiPrepare__scan:
.a16
.i16
    ldx #0
SourcePacket_NmiPrepare__queue:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    beq SourcePacket_NmiPrepare__next
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$43
    bne SourcePacket_NmiPrepare__not_private
    brl SourcePacket_NmiPrepare__done
SourcePacket_NmiPrepare__not_private:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$001F
    cmp #DMA_TYPE_OAM
    bne SourcePacket_NmiPrepare__next
    brl SourcePacket_NmiPrepare__done
SourcePacket_NmiPrepare__next:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourcePacket_NmiPrepare__queue
    sep #$20
.a8
    lda #$43
    pha
    plb
    rep #$30
.a16
.i16
    jsr SourcePacket_Refresh
    lda.l SourcePacket_RefreshAccepted
    cmp #1
    bne SourcePacket_NmiPrepare__done
    lda.l SourcePacket_Changed
    beq SourcePacket_NmiPrepare__done
    lda.l Screen_PosX
    sta.l SourcePacket_PendingCamera
    lda #1
    sta.l SourcePacket_NmiPending
SourcePacket_NmiPrepare__done:
    rep #$30
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    rtl

SourcePacket_SourceRows:
    .dw 0,36
SourcePacket_XMasks:
    .db 1,4,16,64
SourcePacket_QLo:
    .db 0,0,1,2,3,4,4,5,6,7,8,8,9,10,11,12
    .db 12,13,14,15,16,16,17,18,19,20,20,21,22,23,24,24
    .db 25,26,27,28,28,29,30,31,32,32,33,34,35,36,36,37
    .db 38,39,40,40,41,42,43,44,44,45,46,47,48,48,49,50
    .db 51,52,52,53,54,55,56,56,57,58,59,60,60,61,62,63
    .db 64,64,65,66,67,68,68,69,70,71,72,72,73,74,75,76
    .db 76,77,78,79,80,80,81,82,83,84,84,85,86,87,88,88
    .db 89,90,91,92,92,93,94,95,96,96,97,98,99,100,100,101
    .db 102,103,104,104,105,106,107,108,108,109,110,111,112,112,113,114
    .db 115,116,116,117,118,119,120,120,121,122,123,124,124,125,126,127
    .db 128,128,129,130,131,132,132,133,134,135,136,136,137,138,139,140
    .db 140,141,142,143,144,144,145,146,147,148,148,149,150,151,152,152
    .db 153,154,155,156,156,157,158,159,160,160,161,162,163,164,164,165
    .db 166,167,168,168,169,170,171,172,172,173,174,175,176,176,177,178
    .db 179,180,180,181,182,183,184,184,185,186,187,188,188,189,190,191
    .db 192,192,193,194,195,196,196,197,198,199,200,200,201,202,203,204
SourcePacket_RLo:
    .db 0,4,3,2,1,0,4,3,2,1,0,4,3,2,1,0
    .db 4,3,2,1,0,4,3,2,1,0,4,3,2,1,0,4
    .db 3,2,1,0,4,3,2,1,0,4,3,2,1,0,4,3
    .db 2,1,0,4,3,2,1,0,4,3,2,1,0,4,3,2
    .db 1,0,4,3,2,1,0,4,3,2,1,0,4,3,2,1
    .db 0,4,3,2,1,0,4,3,2,1,0,4,3,2,1,0
    .db 4,3,2,1,0,4,3,2,1,0,4,3,2,1,0,4
    .db 3,2,1,0,4,3,2,1,0,4,3,2,1,0,4,3
    .db 2,1,0,4,3,2,1,0,4,3,2,1,0,4,3,2
    .db 1,0,4,3,2,1,0,4,3,2,1,0,4,3,2,1
    .db 0,4,3,2,1,0,4,3,2,1,0,4,3,2,1,0
    .db 4,3,2,1,0,4,3,2,1,0,4,3,2,1,0,4
    .db 3,2,1,0,4,3,2,1,0,4,3,2,1,0,4,3
    .db 2,1,0,4,3,2,1,0,4,3,2,1,0,4,3,2
    .db 1,0,4,3,2,1,0,4,3,2,1,0,4,3,2,1
    .db 0,4,3,2,1,0,4,3,2,1,0,4,3,2,1,0
SourcePacket_QHi:
    .dw 0,204,409,614,819,1024,1228,1433,1638,1843,2048,2252,2457,2662,2867,3072
    .dw 3276,3481,3686,3891,4096,4300,4505,4710,4915,5120,5324,5529,5734,5939,6144,6348
    .dw 6553,6758,6963,7168,7372,7577,7782,7987,8192,8396,8601,8806,9011,9216,9420,9625
    .dw 9830,10035,10240,10444,10649,10854,11059,11264,11468,11673,11878,12083,12288,12492,12697,12902
SourcePacket_RHi:
    .db 0,4,3,2,1,0,4,3,2,1,0,4,3,2,1,0
    .db 4,3,2,1,0,4,3,2,1,0,4,3,2,1,0,4
    .db 3,2,1,0,4,3,2,1,0,4,3,2,1,0,4,3
    .db 2,1,0,4,3,2,1,0,4,3,2,1,0,4,3,2
SourcePacket_Carry:
    .db 0,0,0,0,0,1,1,1,1,1,2

; Foreground frame-wait preparation only. NMI observes CopyBusy and never
; reads this in-flight private image. No DMA/PPU/resource or world writes.
; Carry means an attempt occurred, allowing the caller's one-attempt bound.
SourcePacket_ForegroundPrepare:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    phb
    phd
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq SourcePacket_ForegroundPrepare__scope0
    brl SourcePacket_ForegroundPrepare__skip
SourcePacket_ForegroundPrepare__scope0:
.a16
.i16
    lda.l $7E175E
    cmp #2
    beq SourcePacket_ForegroundPrepare__scope1
    brl SourcePacket_ForegroundPrepare__skip
SourcePacket_ForegroundPrepare__scope1:
.a16
.i16
    lda.l $7E1760
    cmp #1
    beq SourcePacket_ForegroundPrepare__scope2
    brl SourcePacket_ForegroundPrepare__skip
SourcePacket_ForegroundPrepare__scope2:
.a16
.i16
    lda.l $7E46DC
    cmp #1
    beq SourcePacket_ForegroundPrepare__scope3
    brl SourcePacket_ForegroundPrepare__skip
SourcePacket_ForegroundPrepare__scope3:
.a16
.i16
    lda.l Game_State
    cmp #0
    beq SourcePacket_ForegroundPrepare__scope4
    brl SourcePacket_ForegroundPrepare__skip
SourcePacket_ForegroundPrepare__scope4:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SourcePacket_ForegroundPrepare__scope5
    brl SourcePacket_ForegroundPrepare__skip
SourcePacket_ForegroundPrepare__scope5:
.a16
.i16
    lda.l SourcePacket_ActiveValid
    cmp #1
    beq SourcePacket_ForegroundPrepare__scope6
    brl SourcePacket_ForegroundPrepare__skip
SourcePacket_ForegroundPrepare__scope6:
.a16
.i16
    lda.l SourcePacket_CopyBusy
    cmp #0
    beq SourcePacket_ForegroundPrepare__scope7
    brl SourcePacket_ForegroundPrepare__skip
SourcePacket_ForegroundPrepare__scope7:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    beq SourcePacket_ForegroundPrepare__scope8
    brl SourcePacket_ForegroundPrepare__skip
SourcePacket_ForegroundPrepare__scope8:
.a16
.i16
    lda.l $434E7C
    and #1
    beq SourcePacket_ForegroundPrepare__scope9
    brl SourcePacket_ForegroundPrepare__skip
SourcePacket_ForegroundPrepare__scope9:
.a16
.i16
    lda.l $434E7C
    cmp.l SourcePacket_ReadSeq
    bne SourcePacket_ForegroundPrepare__scope10
    brl SourcePacket_ForegroundPrepare__skip
SourcePacket_ForegroundPrepare__scope10:
.a16
.i16
    ldx #0
SourcePacket_ForegroundPrepare__queue:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    beq SourcePacket_ForegroundPrepare__next
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$43
    beq SourcePacket_ForegroundPrepare__blocked
    lda.l DmaQueue+4,x
    and #$001F
    cmp #DMA_TYPE_OAM
    beq SourcePacket_ForegroundPrepare__blocked
SourcePacket_ForegroundPrepare__next:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourcePacket_ForegroundPrepare__queue
    bra SourcePacket_ForegroundPrepare__prepare
SourcePacket_ForegroundPrepare__blocked:
.a16
.i16
    brl SourcePacket_ForegroundPrepare__skip
SourcePacket_ForegroundPrepare__prepare:
.a16
.i16
    lda #1
    sta.l SourcePacket_CopyBusy
    sep #$20
.a8
    lda #$43
    pha
    plb
    rep #$30
.a16
.i16
    jsr SourcePacket_Refresh
    lda.l SourcePacket_RefreshAccepted
    cmp #1
    bne SourcePacket_ForegroundPrepare__release
    lda.l SourcePacket_Changed
    beq SourcePacket_ForegroundPrepare__release
    lda.l Screen_PosX
    sta.l SourcePacket_PendingCamera
    lda #1
    sta.l SourcePacket_NmiPending
SourcePacket_ForegroundPrepare__release:
.a16
.i16
    lda #0
    sta.l SourcePacket_CopyBusy
    pld
    plb
    ply
    plx
    pla
    plp
    sec
    rtl
SourcePacket_ForegroundPrepare__skip:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    clc
    rtl
SourcePacket_ForegroundPrepare__code_end:
