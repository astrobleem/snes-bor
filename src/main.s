; ============================================================================
; SNES-BOR — Minimal Rectangle Demo (wla-dx, HiROM, S-CPU only)
; ============================================================================

.MEMORYMAP
  DEFAULTSLOT 0
  SLOTSIZE $8000
  SLOT 0 $8000
  SLOT 1 $8000
.ENDME

.ROMBANKSIZE $8000
.ROMBANKS $80

.SNESHIROM
.SNESROMTYPE SA1

.BANK 0 SLOT 0
.ORG $8000
.SECTION "MainCode" SUPERFREE

reset:
    sei
    clc
    xce
    rep #$30
.a16
.i16
    lda #$1fff
    tcs
    sep #$20
.a8

    ; PPU init
    lda #$8f
    sta $2100          ; forced blank
    lda #$01
    sta $2105          ; mode 1
    lda #$58
    sta $2107          ; BG1 tilemap at $5800
    lda #$00
    sta $210b          ; BG1 tiles at $0000
    lda #$01
    sta $212c          ; enable BG1
    stz $212d

    ; Palette: color 0 = black, color 1 = green
    stz $2121
    stz $2122
    stz $2122
    lda #$01
    sta $2121
    lda #$e0
    sta $2122
    lda #$03
    sta $2122         ; green = $03E0

    ; VRAM word increment
    lda #$80
    sta $2115

    ; Upload solid 4bpp tile 0 (all green) to VRAM $0000
    stz $2116
    stz $2117
    ldx #8
tlp01:
    lda #$ff
    sta $2118
    stz $2119
    dex
    bne tlp01
    ldx #8
tlp23:
    stz $2118
    stz $2119
    dex
    bne tlp23

    ; Fill BG1 tilemap at $5800 (word $2C00)
    ; 16 cols x 12 rows = 128x96 rectangle
    rep #$20
.a16
    lda #$2c00
    sta $00
    sep #$20
.a8
    ldy #12
trow:
    rep #$20
.a16
    lda $00
    sep #$20
.a8
    sta $2116
    xba
    sta $2117
    ldx #16
tcol:
    stz $2118
    stz $2119
    dex
    bne tcol
    rep #$20
.a16
    lda $00
    clc
    adc #$0020
    sta $00
    sep #$20
.a8
    dey
    bne trow

    ; Enable NMI
    lda #$81
    sta $4200

    ; Release forced blank
    lda #$0f
    sta $2100

main_loop:
    wai
    bra main_loop

.ENDS

.SECTION "NMI" SUPERFREE
nmi_handler:
    phb
    phd
    php
    rep #$30
.a16
    sep #$20
.a8
    lda $4210
    rep #$30
.a16
    inc $00
    plp
    pld
    plb
    rti
.ENDS

.SECTION "Stubs" SUPERFREE
irq_handler:
    rti
cop_handler:
    rti
brk_handler:
    rti
.ENDS

; Native vectors at $FFEA (HiROM bank 0)
.BANK 0 SLOT 0
.ORG $FFEA
.SECTION "VecN" FORCE
    .dw $0000
    .dw $0000
    .dw $0000
    .dw nmi_handler
    .dw $0000
    .dw $0000
.ENDS

; Emulation vectors at $FFFA (HiROM bank 0)
.BANK 0 SLOT 0
.ORG $FFFA
.SECTION "VecE" FORCE
    .dw cop_handler
    .dw $0000
    .dw brk_handler
    .dw $0000
    .dw $0000
    .dw $0000
    .dw reset
    .dw irq_handler
.ENDS