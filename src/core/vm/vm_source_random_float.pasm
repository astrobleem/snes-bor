; Constant randf source capability: offline source binary32 -> native Q16
; lookup. Generic U24 table domain 0 <= maximum < 256, not actor identity.
; No RNG draw here: caller owns the one shared source stream and call order.
; Both kernels are synchronous and use stack-local scratch only.

; Input unsigned bits in SourceModelEntityCopy4086_Lo/Hi; A out unsigned
; remainder %10000. Preserve input, P (except C), X/Y/DP/DBR/SP.
SourceRandomFloat4086_Modulo10000:
.a16
.i16
 php
 rep #$38
 phx
 phy
 phb
 phd
 tsc
 sec
 sbc #6
 tcs
 inc a
 tcd
 sep #$20
.a8
 lda #0
 pha
 plb
 rep #$20
.a16
 lda.l SourceModelEntityCopy4086_Lo
 sta $00
 lda.l SourceModelEntityCopy4086_Hi
 sta $02
 lda #0
 sta $04
 ldx #32
SourceRandomFloat4086_ModuloBit:
.a16
.i16
 asl $00
 rol $02
 lda $04
 rol a
 cmp #10000
 bcc SourceRandomFloat4086_ModuloKeep
 sbc #10000
SourceRandomFloat4086_ModuloKeep:
.a16
.i16
 sta $04
 dex
 bne SourceRandomFloat4086_ModuloBit
 tay
 tsc
 clc
 adc #6
 tcs
 pld
 plb
 tya
 ply
 plx
 plp
 clc
 rtl

; A=ordinal 0..9999, X=LoROM table base, Y=bank 1..63.
; Output SourceModelEntityCopy4086_Lo/Hi only after valid immutable descriptor.
; Caller grants data identity from offline table hash. No entity writes.
SourceRandomFloat4086_LookupU24:
.a16
.i16
 php
 rep #$38
 pha
 phx
 phy
 phb
 cmp #10000
 bcc SourceRandomFloat4086_OrdinalGood
 jmp SourceRandomFloat4086_LookupBad
SourceRandomFloat4086_OrdinalGood:
.a16
.i16
 cpx #$8000
 bcs SourceRandomFloat4086_BaseLowGood
 jmp SourceRandomFloat4086_LookupBad
SourceRandomFloat4086_BaseLowGood:
.a16
.i16
 cpx #$8AB9
 bcs SourceRandomFloat4086_LookupBad
 tya
 beq SourceRandomFloat4086_LookupBad
 cmp #64
 bcs SourceRandomFloat4086_LookupBad
 sep #$20
.a8
 pha
 plb
 rep #$20
.a16
 lda.w $0000,x
 cmp #$3542
 bne SourceRandomFloat4086_LookupBad
 lda.w $0002,x
 cmp #$4652
 bne SourceRandomFloat4086_LookupBad
 lda.w $0004,x
 cmp #1
 bne SourceRandomFloat4086_LookupBad
 lda.w $0006,x
 cmp #3
 bne SourceRandomFloat4086_LookupBad
 lda.w $0008,x
 cmp #10000
 bne SourceRandomFloat4086_LookupBad
 lda.w $000A,x
 ora.w $0012,x
 ora.w $0014,x
 ora.w $0016,x
 bne SourceRandomFloat4086_LookupBad
 lda.w $0010,x
 cmp #24
 bne SourceRandomFloat4086_LookupBad
 ; Restored incoming A is five stack bytes above saved DBR.
 lda $06,s
 asl a
 clc
 adc $06,s
 clc
 adc #24
 clc
 adc $04,s
 tax
 lda.w $0000,x
 sta.l SourceModelEntityCopy4086_Lo
 sep #$20
.a8
 lda.w $0002,x
 rep #$20
.a16
 and #$00FF
 sta.l SourceModelEntityCopy4086_Hi
 plb
 ply
 plx
 pla
 plp
 clc
 rtl
SourceRandomFloat4086_LookupBad:
.a16
.i16
 plb
 ply
 plx
 pla
 plp
 sec
 rtl
