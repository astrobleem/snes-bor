; Shared source/accepted OAM admission. Called after private staging is built,
; BEFORE immutable packet submission. The compiler separately bounds capacity
; before staging, so Core_Oam_SetSprite cannot silently truncate this picture.
; Each visible interval starts at an OBJ Y or scanline0 (vertical wrap).
; Counting at those boundaries gives the exact maximum OBJ overlap. Slivers
; conservatively count the full configured width, including horizontal clipping.
; Main-only emitter scratch S7Pub_State+8..30; no packet/transfer ownership here.
S7Admission_Scanlines:
    rep #$30
.a16
.i16
    lda.l $7FAA02
    cmp #1
    bne S7Admission_Scanlines__compute
    lda.l Oam_CurrentSlot
    cmp.l $7FAA00
    bne S7Admission_Scanlines__compute
    ldx #0
S7Admission_Scanlines__cache_check:
.a16
.i16
    txa
    cmp.l Oam_CurrentSlot
    bcs S7Admission_Scanlines__cached
    jsr S7Admission_CacheKey
    cmp.l $7FA900,x
    bne S7Admission_Scanlines__compute
    lda.l S7Pub_State+18
    clc
    adc #4
    tax
    bra S7Admission_Scanlines__cache_check
S7Admission_Scanlines__cached:
.a16
.i16
    lda.l $7FAA04
    sta.l S7Pub_State+28
    lda.l $7FAA06
    sta.l S7Pub_State+30
    brl S7Admission_Scanlines__result
S7Admission_Scanlines__compute:
.a16
.i16
    lda #0
    sta.l S7Pub_State+28
    sta.l S7Pub_State+30
    sta.l S7Pub_State+16
    jsr S7Admission_Line
    lda #0
    sta.l S7Pub_State+10
S7Admission_Scanlines__loop:
.a16
.i16
    lda.l S7Pub_State+10
    cmp.l Oam_CurrentSlot
    bcs S7Admission_Scanlines__save
    tax
    lda.l Oam_Buffer+1,x
    and #255
    cmp #224
    bcs S7Admission_Scanlines__next
    sta.l S7Pub_State+16
    jsr S7Admission_Line
S7Admission_Scanlines__next:
.a16
.i16
    lda.l S7Pub_State+10
    clc
    adc #4
    sta.l S7Pub_State+10
    bra S7Admission_Scanlines__loop
S7Admission_Scanlines__save:
.a16
.i16
    lda.l S7Pub_State+28
    sta.l $7FAA04
    lda.l S7Pub_State+30
    sta.l $7FAA06
    lda.l Oam_CurrentSlot
    sta.l $7FAA00
    ldx #0
S7Admission_Scanlines__save_loop:
.a16
.i16
    txa
    cmp.l Oam_CurrentSlot
    bcs S7Admission_Scanlines__saved
    jsr S7Admission_CacheKey
    sta.l $7FA900,x
    lda.l S7Pub_State+18
    clc
    adc #4
    tax
    bra S7Admission_Scanlines__save_loop
S7Admission_Scanlines__saved:
.a16
.i16
    lda #1
    sta.l $7FAA02
S7Admission_Scanlines__result:
.a16
.i16
    lda.l S7Pub_State+28
    sta.l $7FA8DC
    cmp #33
    bcs S7Admission_Scanlines__blocked
    lda.l S7Pub_State+30
    sta.l $7FA8DE
    cmp #35
    bcs S7Admission_Scanlines__blocked
    sec
    rtl
S7Admission_Scanlines__blocked:
.a16
.i16
    lda #$D70A
    sta.l S7Pub_State+$FE
    clc
    rtl
S7Admission_Line:
.a16
.i16
    lda #0
    sta.l S7Pub_State+12
    sta.l S7Pub_State+14
    ldx #0
S7Admission_Line__loop:
.a16
.i16
    txa
    cmp.l Oam_CurrentSlot
    bcs S7Admission_Line__done
    sta.l S7Pub_State+18
    lsr a
    lsr a
    tax
    lda.l Oam_ExpandedHi,x
    and #2
    beq S7Admission_Line__small
    lda #64
    sta.l S7Pub_State+26
    lda #4
    bra S7Admission_Line__size
S7Admission_Line__small:
.a16
.i16
    lda #32
    sta.l S7Pub_State+26
    lda #2
S7Admission_Line__size:
.a16
.i16
    sta.l S7Pub_State+24
    lda.l S7Pub_State+18
    tax
    lda.l Oam_Buffer+1,x
    and #255
    sta.l S7Pub_State+8
    lda.l S7Pub_State+16
    sec
    sbc.l S7Pub_State+8
    and #255
    cmp.l S7Pub_State+26
    bcs S7Admission_Line__next
    lda.l S7Pub_State+12
    inc a
    sta.l S7Pub_State+12
    lda.l S7Pub_State+14
    clc
    adc.l S7Pub_State+24
    sta.l S7Pub_State+14
S7Admission_Line__next:
.a16
.i16
    txa
    clc
    adc #4
    tax
    bra S7Admission_Line__loop
S7Admission_Line__done:
.a16
.i16
    lda.l S7Pub_State+12
    cmp.l S7Pub_State+28
    bcc S7Admission_Line__slivers
    sta.l S7Pub_State+28
S7Admission_Line__slivers:
.a16
.i16
    lda.l S7Pub_State+14
    cmp.l S7Pub_State+30
    bcc S7Admission_Line__return
    sta.l S7Pub_State+30
S7Admission_Line__return:
.a16
.i16
    rts

; Input X=low OAM byte offset; output X=cache word offset, A=Y|(size<<8).
; X-high, flip, tile, model, palette and horizontal position cannot change the
; conservative full-width scanline count. These are the COMPLETE dependencies.
S7Admission_CacheKey:
.a16
.i16
    txa
    sta.l S7Pub_State+18
    lda.l Oam_Buffer+1,x
    and #255
    sta.l S7Pub_State+8
    txa
    lsr a
    lsr a
    tax
    lda.l Oam_ExpandedHi,x
    and #2
    xba
    ora.l S7Pub_State+8
    pha
    lda.l S7Pub_State+18
    lsr a
    tax
    pla
    rts
