; Explicit ACCEPTED_COMPAT_C_RUNTIME_RAND_WIN32, measured against msvcrt.dll.
; Separate process-wide C rand stream; never share engine rand32 seed/calls.
; Profile 1: seed = seed*214013+2531011 modulo2^32; result=(seed>>16)&32767.
; Owner must install the profile/state before publishing B5EA. This primitive
; does not reset on an actor birth, tick, stage transition, or campaign restart.
SourceCRandom4086_Ready = $43BD56
SourceCRandom4086_SeedLo = $43BD58
SourceCRandom4086_SeedHi = $43BD5A
SourceCRandom4086_CallsLo = $43BD5C
SourceCRandom4086_CallsHi = $43BD5E
SourceCRandom4086_Busy = $43BD60
SourceCRandom4086_Result = $43BD62 ; integer32, 0..32767
SourceCRandom4086_Profile = $43BD66
SourceCRandom4086_End = $43BD68
SourceCRandom4086_Next:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceCRandom4086_Ready
 cmp #$B5EA
 beq SourceCRandom4086_ReadyOk
 jmp SourceCRandom4086_Bad
SourceCRandom4086_ReadyOk:
.a16
.i16
 lda.l SourceCRandom4086_Profile
 cmp #1
 beq SourceCRandom4086_ProfileOk
 jmp SourceCRandom4086_Bad
SourceCRandom4086_ProfileOk:
.a16
.i16
 lda.l SourceCRandom4086_Busy
 beq SourceCRandom4086_Idle
 jmp SourceCRandom4086_Bad
SourceCRandom4086_Idle:
.a16
.i16
 phb
 phd
 lda #1
 sta.l SourceCRandom4086_Busy
 tsc
 sec
 sbc #16
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
 ; Shift the 18-bit constant, not the variable seed, to bound loop cost.
 lda.l SourceCRandom4086_SeedLo
 sta $04
 lda.l SourceCRandom4086_SeedHi
 sta $06
 lda #$43FD
 sta $00
 lda #$0003
 sta $02
 stz $08
 stz $0A
 ldx #18
SourceCRandom4086_Multiply:
.a16
.i16
 lsr $02
 ror $00
 bcc SourceCRandom4086_Shift
 lda $08
 clc
 adc $04
 sta $08
 lda $0A
 adc $06
 sta $0A
SourceCRandom4086_Shift:
.a16
.i16
 asl $04
 rol $06
 dex
 bne SourceCRandom4086_Multiply
 lda $08
 clc
 adc #$9EC3
 sta.l SourceCRandom4086_SeedLo
 lda $0A
 adc #$0026
 sta.l SourceCRandom4086_SeedHi
 and #$7FFF
 sta.l SourceCRandom4086_Result
 lda #0
 sta.l SourceCRandom4086_Result+2
 lda.l SourceCRandom4086_CallsLo
 clc
 adc #1
 sta.l SourceCRandom4086_CallsLo
 lda.l SourceCRandom4086_CallsHi
 adc #0
 sta.l SourceCRandom4086_CallsHi
 lda #0
 sta.l SourceCRandom4086_Busy
 tsc
 clc
 adc #16
 tcs
 pld
 plb
 ply
 plx
 plp
 clc
 rtl
SourceCRandom4086_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
