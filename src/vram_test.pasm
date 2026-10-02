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

    ; Forced blank, no BG
    lda #$8f
    sta $2100

    ; VRAM word increment after high byte
    lda #$80
    sta $2115

    ; Write 4 distinct words to VRAM starting at $0000
    ; Word 0 = $0001, Word 1 = $0002, Word 2 = $0003, Word 3 = $0004
    stz $2116           ; VMADDL = 0
    stz $2117           ; VMADDH = 0 (VRAM word $0000)

    lda #$01
    sta $2118           ; VMDATAL = $01
    stz $2119           ; VMDATAH = $00, commit word $0001
    lda #$02
    sta $2118           ; VMDATAL = $02
    stz $2119           ; VMDATAH = $00, commit word $0002
    lda #$03
    sta $2118
    stz $2119
    lda #$04
    sta $2118
    stz $2119

    ; Enable NMI
    lda #$81
    sta $4200
    wai
    lda #$0f
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