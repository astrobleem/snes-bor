; Static immutable-resource jobs. All instance frames contribute to the lease.
S7Tile_Init:
    jsl S7Packet_Init
    rep #$30
    .a16
    .i16
    ldx #0
    lda #0
S7Tile_Init__loop:
    .a16
    .i16
    sta.l $7F8F24,x
    inx
    inx
    cpx #220
    bcc S7Tile_Init__loop
    rtl
S7Tile_NextJob:
    rep #$30
    .a16
    .i16
    lda.l $7F8F30
    clc
    adc #10
    sta.l $7F8F30
    lda.l $7F8F32
    inc a
    inc a
    sta.l $7F8F32
    cmp #S7Plan_Count*2
    rtl
S7Tile_Poll:
    jml S7Plan_Poll
S7Tile_Service:
    rep #$30
    .a16
    .i16
    lda #$FFFF
    sta.l $7F8F28
    lda #0
    sta.l S7Pub_State+$EE
    ldx #0
S7Tile_Service__scan:
    .a16
    .i16
    lda.l S7Pub_State+38,x
    beq S7Tile_Service__next
    lda.l S7Pub_State+42,x
    cmp.l $7F8F28
    bcs S7Tile_Service__max
    sta.l $7F8F28
S7Tile_Service__max:
    .a16
    .i16
    cmp.l S7Pub_State+$EE
    bcc S7Tile_Service__next
    sta.l S7Pub_State+$EE
S7Tile_Service__next:
    .a16
    .i16
    txa
    clc
    adc #32
    tax
    cpx #192
    bcc S7Tile_Service__scan
    rtl
S7Tile_Before:
    rep #$30
    .a16
    .i16
    lda #544
    sta.l $7F8F2A
    jsl S7Packet_Poll
    jsl S7Tile_Poll
    lda.l S7Pub_State+$EE
    sta.l $7F8F2C
    lda.l $7F8F24
    sta.l $7F8F2E
    jsl S7Tile_Schedule
    rtl
S7Tile_Schedule:
    jml S7Plan_Schedule
S7Tile_OamTail:
    php
    rep #$30
    .a16
    .i16
    lda.l S7Pub_State+6
    cmp #1
    beq S7Tile_OamTail__source
    jsl Core_Oam_Play_Long
    plp
    rtl
S7Tile_OamTail__source:
    .a16
    .i16
    jsl S7Tile_Before
    jsl S7Plan_Check
    bcc S7Tile_OamTail__miss
S7Tile_OamTail__submit:
    .a16
    .i16
    jsl S7Packet_Submit
    bcc S7Tile_OamTail__done
    lda #0
    sta.l $7F8F2A
    lda #5
    sta.l $7F8F2C
    lda.l $7F8F28
    cmp #$FFFF
    beq S7Tile_OamTail__done
    sta.l $7F8F2E
    jsl S7Tile_Schedule
S7Tile_OamTail__done:
    .a16
    .i16
    plp
    rtl
S7Tile_OamTail__miss:
    .a16
    .i16
    lda #$D703
    sta.l S7Pub_State+$FE
    lda.l S7Pub_State+$F0
    inc a
    sta.l S7Pub_State+$F0
    plp
    rtl
