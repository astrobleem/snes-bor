; Read-only early attack-packet preparation. The original NMI refresh first
; seals a source snapshot. This helper stages only 80 player low-OAM bytes
; and 20 expanded-high bytes in disjoint private BW-RAM. It never publishes.
SourceAttackPacket_Low = $437600
SourceAttackPacket_High = $437650
SourceAttackPacket_Delta0 = $437670
SourceAttackPacket_Delta1 = $437672
SourceAttackPacket_Work = $437674
SourceAttackPacket_HighBit = $437676
SourceAttackPacket_Magic = $437680
SourceAttackPacket_Seq = $437682

SourceAttackPacket_NmiPrepare:
.a16
.i16
    jsl SourcePacket_NmiPrepare
    php
    rep #$30
    pha
    phx
    phy
    phb
    lda #0
    sta.l SourceAttackPacket_Magic
    lda.l SourcePacket_ActiveValid
    cmp #1
    bne SourceAttackPacket_Reject0
    lda.l SourcePacket_CopyBusy
    bne SourceAttackPacket_Reject0
    lda.l SourcePacket_RefreshAccepted
    cmp #1
    bne SourceAttackPacket_Reject0
    lda.l SourcePacket_NmiPending
    bne SourceAttackPacket_Reject0
    lda.l $434E7C
    cmp.l SourcePacket_ReadSeq
    bne SourceAttackPacket_Reject0
    and #1
    bne SourceAttackPacket_Reject0
    lda.l Game_StageIndex
    bne SourceAttackPacket_Reject0
    lda.l $4119E6
    and #$00FF
    cmp #9
    bne SourceAttackPacket_Reject0
    lda.l $411AE6
    and #$00FF
    cmp #9
    bne SourceAttackPacket_Reject0
    bra SourceAttackPacket_Guard1
SourceAttackPacket_Reject0:
    brl SourceAttackPacket_Done
SourceAttackPacket_Guard1:
    lda.l SourceAttackTemplate_Base
    cmp #SourceAttackTemplate_Magic
    bne SourceAttackPacket_Reject1
    lda.l SourceAttackTemplate_Base+128
    cmp #SourceAttackTemplate_Magic
    bne SourceAttackPacket_Reject1
    lda.l SOURCE_PACKET_ACTIVE_META
    bne SourceAttackPacket_Reject1
    lda.l SOURCE_PACKET_ACTIVE_META+2
    cmp #44
    bne SourceAttackPacket_Reject1
    lda.l SOURCE_PACKET_ACTIVE_META+32
    cmp #44
    bne SourceAttackPacket_Reject1
    lda.l SOURCE_PACKET_ACTIVE_META+34
    cmp #80
    bne SourceAttackPacket_Reject1
    lda.l SourceAttackTemplate_Base+10
    bne SourceAttackPacket_Reject1
    lda.l SourceAttackTemplate_Base+12
    cmp #40
    bne SourceAttackPacket_Reject1
    lda.l SourceAttackTemplate_Base+128+10
    cmp #40
    bne SourceAttackPacket_Reject1
    lda.l SourceAttackTemplate_Base+128+12
    cmp #80
    bne SourceAttackPacket_Reject1
    bra SourceAttackPacket_Build
SourceAttackPacket_Reject1:
    brl SourceAttackPacket_Done
SourceAttackPacket_Build:

    lda.l SOURCE_PACKET_ACTIVE_META+4
    clc
    adc.l SOURCE_PACKET_ACTIVE_META+30
    sec
    sbc.l SourceAttackTemplate_Base+14
    sta.l SourceAttackPacket_Delta0
    lda.l SOURCE_PACKET_ACTIVE_META+36
    clc
    adc.l SOURCE_PACKET_ACTIVE_META+62
    sec
    sbc.l SourceAttackTemplate_Base+128+14
    sta.l SourceAttackPacket_Delta1
    ; Both copies and all rebases happen before the magic is committed.
    sep #$20
.a8
    lda #$43
    pha
    plb
    rep #$30
.a16
    ldx #$7420
    ldy #$7600
    lda #39
    mvn $43,$43
    ldx #$74A0
    ldy #$7628
    lda #39
    mvn $43,$43
    ldx #0
    ldy #0
SourceAttackPacket_P1:
.a16
.i16
    lda.w $7448,y
    and #1
    xba
    sta.l SourceAttackPacket_Work
    lda.l SourceAttackTemplate_Base+32,x
    and #$00FF
    ora.l SourceAttackPacket_Work
    clc
    adc.l SourceAttackPacket_Delta0
    and #$01FF
    sta.l SourceAttackPacket_Work
    sep #$20
.a8
    sta.l SourceAttackPacket_Low,x
    rep #$20
.a16
    lda.l SourceAttackPacket_Work
    xba
    and #1
    sta.l SourceAttackPacket_HighBit
    lda.w $7448,y
    and #2
    ora.l SourceAttackPacket_HighBit
    sep #$20
.a8
    sta.w $7650,y
    rep #$20
.a16
    txa
    clc
    adc #4
    tax
    iny
    cpy #10
    bcc SourceAttackPacket_P1
    ldx #0
    ldy #0
SourceAttackPacket_P2:
.a16
.i16
    lda.w $74C8,y
    and #1
    xba
    sta.l SourceAttackPacket_Work
    lda.l SourceAttackTemplate_Base+128+32,x
    and #$00FF
    ora.l SourceAttackPacket_Work
    clc
    adc.l SourceAttackPacket_Delta1
    and #$01FF
    sta.l SourceAttackPacket_Work
    sep #$20
.a8
    sta.l SourceAttackPacket_Low+40,x
    rep #$20
.a16
    lda.l SourceAttackPacket_Work
    xba
    and #1
    sta.l SourceAttackPacket_HighBit
    lda.w $74C8,y
    and #2
    ora.l SourceAttackPacket_HighBit
    sep #$20
.a8
    sta.w $765A,y
    rep #$20
.a16
    txa
    clc
    adc #4
    tax
    iny
    cpy #10
    bcc SourceAttackPacket_P2
    lda.l SourcePacket_ReadSeq
    sta.l SourceAttackPacket_Seq
    lda #$A771
    sta.l SourceAttackPacket_Magic
SourceAttackPacket_Done:
.a16
.i16
    plb
    ply
    plx
    pla
    plp
    rtl
