; Release temporary slot ownership before immutable callback initialization.
; Pair snapshots hold their own retained references. Validate aggregate live
; aliases before any decrement, so malformed ownership cannot partially free.
SourceAnimationSlots4086_Release:
.a16
.i16
 php
 rep #$38
 phb
 phx
 phy
 phd
 tsc
 sec
 sbc #12
 tcs
 inc a
 tcd
 lda.l SourceAnimationCallback4086_Slots
 bne SourceAnimationSlots4086_CountValid
 jmp SourceAnimationSlots4086_Bad
SourceAnimationSlots4086_CountValid:
.a16
.i16
 sta $02
 lda.l SourceAnimationCallback4086_SlotBase
 sta $00
 clc
 adc $02
 bcc SourceAnimationSlots4086_RangeNoCarry
 jmp SourceAnimationSlots4086_Bad
SourceAnimationSlots4086_RangeNoCarry:
.a16
.i16
 cmp #1025
 bcc SourceAnimationSlots4086_RangeValid
 jmp SourceAnimationSlots4086_Bad
SourceAnimationSlots4086_RangeValid:
.a16
.i16
 lda #0
 sta $04
SourceAnimationSlots4086_Preflight:
.a16
.i16
 lda $04
 cmp $02
 bcc SourceAnimationSlots4086_Cell
 jmp SourceAnimationSlots4086_ReleaseStart
SourceAnimationSlots4086_Cell:
.a16
.i16
 clc
 adc $00
 jsr SourceNativeSnapshot4086_StringHandle
 bcc SourceAnimationSlots4086_Valid
 jmp SourceAnimationSlots4086_Bad
SourceAnimationSlots4086_Valid:
.a16
.i16
 cmp #$FFFF
 beq SourceAnimationSlots4086_Next
 sta $06
 lda #0
 sta $08
 sta $0A
SourceAnimationSlots4086_Aliases:
.a16
.i16
 lda $08
 cmp $02
 bcs SourceAnimationSlots4086_CountDone
 clc
 adc $00
 jsr SourceNativeSnapshot4086_StringHandle
 bcc SourceAnimationSlots4086_AliasValid
 jmp SourceAnimationSlots4086_Bad
SourceAnimationSlots4086_AliasValid:
.a16
.i16
 cmp $06
 bne SourceAnimationSlots4086_AliasNext
 inc $0A
SourceAnimationSlots4086_AliasNext:
.a16
.i16
 inc $08
 bra SourceAnimationSlots4086_Aliases
SourceAnimationSlots4086_CountDone:
.a16
.i16
 lda $06
 asl a
 asl a
 asl a
 asl a
 asl a
 asl a
 tax
 lda.l VmStrPool_Wram,x
 and #$00FF
 cmp $0A
 bcs SourceAnimationSlots4086_Next
 jmp SourceAnimationSlots4086_Bad
SourceAnimationSlots4086_Next:
.a16
.i16
 inc $04
 jmp SourceAnimationSlots4086_Preflight
SourceAnimationSlots4086_ReleaseStart:
.a16
.i16
 lda #0
 sta $04
SourceAnimationSlots4086_ReleaseCell:
.a16
.i16
 lda $04
 cmp $02
 bcs SourceAnimationSlots4086_Good
 clc
 adc $00
 jsr SourceNativeSnapshot4086_StringHandle
 cmp #$FFFF
 beq SourceAnimationSlots4086_ReleaseNext
 asl a
 asl a
 asl a
 asl a
 asl a
 asl a
 tax
 sep #$20
.a8
 lda.l VmStrPool_Wram,x
 dec a
 sta.l VmStrPool_Wram,x
 rep #$38
SourceAnimationSlots4086_ReleaseNext:
.a16
.i16
 inc $04
 bra SourceAnimationSlots4086_ReleaseCell
SourceAnimationSlots4086_Good:
.a16
.i16
tsc
clc
adc #12
tcs
pld
ply
plx
plb
plp
clc
rtl
SourceAnimationSlots4086_Bad:
.a16
.i16
tsc
clc
adc #12
tcs
pld
ply
plx
plb
plp
sec
rtl
