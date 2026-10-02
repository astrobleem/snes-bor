; Generic static BG1 tilemap transfer. Bank 9 keeps the fixed bank-0 runtime
; below its interrupt-region boundary; the packed height selects 28 or 32
; rows for narrow pages, while wide pages retain their two-page transfer.

Bg_LoadScene_TilemapStatic:
    php
    sep #$20
.a8
    lda.l BgRecordStaging+2
    cmp #64
    beq Bg_LoadScene_TilemapStatic__wide
    rep #$31
.a16
.i16
    lda.l BgRecordStaging+4
    and #$00FF
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l BgDirSeekTmp
    lda #BG1_TILEMAP_VRAM_WORD
    sta $2116
    ldx #$0000
Bg_LoadScene_TilemapStatic__narrow:
    sep #$20
.a8
    lda $2001
    sta $2118
    lda $2001
    sta $2119
    rep #$31
.a16
.i16
    inx
    txa
    cmp.l BgDirSeekTmp
    bcc Bg_LoadScene_TilemapStatic__narrow
    bra Bg_LoadScene_TilemapStatic__done
Bg_LoadScene_TilemapStatic__wide:
    rep #$31
.a16
.i16
    lda #BG1_TILEMAP_VRAM_WORD
    sta $2116
    ldx #$0000
Bg_LoadScene_TilemapStatic__wide_loop:
    sep #$20
.a8
    lda $2001
    sta $2118
    lda $2001
    sta $2119
    rep #$31
.a16
.i16
    inx
    cpx #BG1_TILEMAP_WORDS_WIDE
    bcc Bg_LoadScene_TilemapStatic__wide_loop
Bg_LoadScene_TilemapStatic__done:
    plp
    rtl
