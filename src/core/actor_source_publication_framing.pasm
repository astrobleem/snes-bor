; Actor pixels are admitted only against the camera actually being committed
; by this NMI. A mismatched picture is rejected, not silently displayed with
; another camera's background. Its tile pool stays leased until a genuine
; source-excluded replacement picture completes. No source clock is changed.
S7Framing_Admit:
    rep #$30
.a16
.i16
    phx
    lda.l DmaQueue,x
    sta.l $7FAD26
    lda.l DmaQueue+7,x
    and #255
    cmp #$7F
    bne S7Framing_Admit__pass
    lda.l DmaQueue+5,x
    cmp #$8D00
    beq S7Framing_Admit__first
    cmp #$A600
    bne S7Framing_Admit__pass
    ldx #$1900
    bra S7Framing_Admit__check
S7Framing_Admit__first:
.a16
.i16
    ldx #0
S7Framing_Admit__check:
.a16
.i16
    lda.l $7FAD24
    bne S7Framing_Admit__protocol
    lda.l $7FAD26
    cmp #S7Framing_PacketBytes
    beq S7Framing_Admit__length_ok
S7Framing_Admit__protocol:
.a16
.i16
    lda #1
    sta.l $7F8F3E,x
    lda #$D70B
    sta.l S7Pub_State+$FE
    plx
    clc
    rtl
S7Framing_Admit__length_ok:
.a16
.i16
    lda.l $7F8F3C,x
    beq S7Framing_Admit__pass
    lda.l $7F8F3A,x
    cmp.l Nmi_Bg1ScrollX
    bne S7Framing_Admit__reject
    lda.l Nmi_Bg1ScrollY
    beq S7Framing_Admit__pass
S7Framing_Admit__reject:
.a16
.i16
    lda #1
    sta.l $7F8F3E,x
    lda #$D70C
    sta.l S7Pub_State+$FE
    plx
    clc
    rtl
S7Framing_Admit__pass:
.a16
.i16
    plx
    sec
    rtl

; NMI-only fallback storage $7FAB00..AD1F, followed by camera/source flag.
; The compiler reserves this gap below StreamCacheFp_Slot2Tile ($7FB000).
; Source pieces use SMALL OBJ and physical palettes 6/7; accepted allocations
; are independently checked to use palettes 0..5. Y=224 with SMALL 16x32
; cannot intersect a visible scanline or wrap. Accepted OAM is copied intact.
S7Framing_Remember:
    php
    rep #$30
.a16
.i16
    phx
    phy
    phb
    lda.l DmaQueue+7,x
    and #255
    cmp #$7F
    bne S7Framing_Remember__done
    lda.l DmaQueue+5,x
    cmp #$8D00
    beq S7Framing_Remember__first
    cmp #$A600
    bne S7Framing_Remember__done
    ldx #$1900
    bra S7Framing_Remember__copy_start
S7Framing_Remember__first:
.a16
.i16
    ldx #0
S7Framing_Remember__copy_start:
.a16
.i16
    lda.l $7F8F3C,x
    sta.l $7FAD22
    beq S7Framing_Remember__done
    lda.l $7F8F3A,x
    sta.l $7FAD20
    sep #$20
.a8
    lda #$7F
    pha
    plb
    rep #$30
.a16
.i16
    ldy #0
S7Framing_Remember__copy:
.a16
.i16
    lda $8D00,x
    sta $AB00,y
    inx
    inx
    iny
    iny
    cpy #544
    bcc S7Framing_Remember__copy
    ldx #0
S7Framing_Remember__hide:
.a16
.i16
    lda $AB03,x
    and #14
    cmp #12
    bcc S7Framing_Remember__next
    lda #$E000
    sta $AB00,x
S7Framing_Remember__next:
.a16
.i16
    inx
    inx
    inx
    inx
    cpx #512
    bcc S7Framing_Remember__hide
S7Framing_Remember__done:
.a16
.i16
    plb
    ply
    plx
    plp
    rtl

; Replaces the original A8 brightness load BEFORE forced-blank release.
; Runs even when no new OAM packet arrived. A framing fault
; replaces only source pixels, keeps shared accepted pixels, and requests the
; normal close fence. It never frees tiles or changes camera/source clocks.
S7Framing_ScrollX:
    php
    rep #$30
.a16
.i16
    phx
    phy
    lda.l $7FAD22
    beq S7Framing_ScrollX__done
    lda.l $7FAD20
    cmp.l Nmi_Bg1ScrollX
    bne S7Framing_ScrollX__retire
    lda.l Nmi_Bg1ScrollY
    beq S7Framing_ScrollX__done
S7Framing_ScrollX__retire:
.a16
.i16
    lda #544
    sta $4375
    lda #$AB00
    sta $4372
    lda #0
    sta $2102
    sep #$20
.a8
    lda #$7F
    sta $4374
    lda #0
    sta $4370
    lda #4
    sta $4371
    lda #$80
    sta $420B
    rep #$30
.a16
.i16
S7Framing_ScrollX__retired:
.a16
.i16
    lda #0
    sta.l $7FAD22
    lda #$D70C
    sta.l S7Pub_State+$FE
    lda.l S7Pub_State+$F2
    bne S7Framing_ScrollX__done
    lda #1
    sta.l $7FA8C0
S7Framing_ScrollX__done:
.a16
.i16
    ply
    plx
    plp
    lda.l Nmi_ScreenBrightness
    rtl
