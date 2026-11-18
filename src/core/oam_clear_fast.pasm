; Same active-shadow bytes as Core_Oam_ClearActive, with fewer NMI stores.
; STZ has no long form: establish/preserve DBR=$7E and use an explicit low16
; alias only for STZ. All ordinary indexed WRAM stores remain canonical long.
Oam_ClearActiveZero_Lo = (Oam_Buffer + 2) & $FFFF
Core_Oam_ClearActiveFast:
    rep #$31
.a16
.i16
    phb
    sep #$20
.a8
    lda #$7E
    pha
    plb
    rep #$31
.a16
.i16
    lda #0
    sta.l Oam_CurrentSlot
    lda.l Oam_HighWaterSlot
    lsr a
    lsr a
    bne Core_Oam_ClearActiveFast__main
    brl Core_Oam_ClearActiveFast__empty
Core_Oam_ClearActiveFast__main:
.a16
.i16
    tay
    ldx #0
    lda #OAM_DEFAULT_Y * 256 + OAM_HIDDEN_X
Core_Oam_ClearActiveFast__main_loop:
.a16
.i16
    sta.l Oam_Buffer,x
    stz.w Oam_ClearActiveZero_Lo,x
    inx
    inx
    inx
    inx
    dey
    bne Core_Oam_ClearActiveFast__main_loop
    ldx #0
    lda.l Oam_HighWaterSlot
    lsr a
    lsr a
    lsr a
    beq Core_Oam_ClearActiveFast__hi_tail
    tay
    lda #OAM_HIDDEN_HI * 257
Core_Oam_ClearActiveFast__hi_loop:
.a16
.i16
    sta.l Oam_ExpandedHi,x
    inx
    inx
    dey
    bne Core_Oam_ClearActiveFast__hi_loop
Core_Oam_ClearActiveFast__hi_tail:
.a16
.i16
    lda.l Oam_HighWaterSlot
    and #4
    beq Core_Oam_ClearActiveFast__return
    sep #$20
.a8
    lda #OAM_HIDDEN_HI
    sta.l Oam_ExpandedHi,x
    inx
    rep #$31
.a16
.i16
Core_Oam_ClearActiveFast__return:
.a16
.i16
    plb
    lda #OAM_HIDDEN_HI
    cmp #OAM_HIDDEN_HI
    rep #$31
.a16
.i16
    jml Core_Oam_ClearActive__return
Core_Oam_ClearActiveFast__empty:
.a16
.i16
    plb
    rep #$31
.a16
.i16
    lda #0
    jml Core_Oam_ClearActive__return
