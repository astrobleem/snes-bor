.snes
.bank 0
.org $8000

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

    ; Minimal PPU init
    lda #$80
    sta $2100           ; forced blank
    lda #$01
    sta $2105           ; mode 1
    lda #$04
    sta $2107           ; BG1 tilemap at $0400 (word $0200)
    lda #$00
    sta $210b           ; BG1 tiles at $0000
    lda #$01
    sta $212c           ; enable BG1

    ; Palette
    lda #$00
    sta $2121
    lda #$FF
    sta $2122
    lda #$7F
    sta $2122          ; color 0 = white
    lda #$0F
    sta $2121
    lda #$E0
    sta $2122
    lda #$03
    sta $2122          ; color 15 = green

    ; VRAM word increment
    lda #$80
    sta $2115

    ; Wait for VMAIN to take effect (one vblank)
    wai

    ; === Upload tile 0 (all color 15 = green) to VRAM $0000 ===
    stz $2116
    stz $2117
    ldx #$10
tile_loop:
    lda #$FF
    sta $2118
    lda #$FF
    sta $2119
    dex
    bne tile_loop

    ; === Fill tilemap at $0400 (word $0200) with tile 0 ===
    lda #$00
    sta $2116
    lda #$02
    sta $2117
    ldx #$0400
tmap_loop:
    stz $2118
    stz $2119
    dex
    bne tmap_loop

    ; Release forced blank
    lda #$0F
    sta $2100

main_loop:
    wai
    bra main_loop

nmi_handler:
    lda $4210
    rti
irq_handler:
    rti
cop_handler:
    rti
brk_handler:
    rti

.org $FFE0
.word $0000
.word $0000
.word cop_handler
.word brk_handler
.word $0000
.word nmi_handler
.word reset
.word irq_handler

.org $FFF0
.word $0000
.word $0000
.word cop_handler
.word $0000
.word $0000
.word nmi_handler
.word reset
.word irq_handler