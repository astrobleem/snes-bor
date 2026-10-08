; B62B: source dynamic damage state. 128 x 12 bytes, WRAM $7FB900..$7FBEFF.
; FP cache ends $7FB900 exclusive; VM slots begin $7FC000. Separate lease.
; Source spawn copies binary32 model knockdowncount; memset clears the rest.
; +0 binary32 knockdowncount, +4 uint32 knockdowntime, +8 int32 damagetype.
SourceDamageState4086_Ready = $7FBF00
SOURCE_ENTITY_DAMAGE_STATE = $7FB900
SOURCE_ENTITY_DAMAGE_STATE_STRIDE = 12
SOURCE_ENTITY_DAMAGE_STATE_END = $7FBF00
SourceDamageState4086_InitializeBirth:
.a16
.i16
 php
 rep #$38
 pha
 phx
 phy
 lda.l SourceDamageState4086_Ready
 beq SourceDamageState4086_Good
 cmp #$B62B
 bne SourceDamageState4086_Bad
 lda.l SourceLifecycle4086_Ready
 cmp #$B4FB
 bne SourceDamageState4086_Bad
 lda 5,s
 cmp #128
 bcs SourceDamageState4086_Bad
 asl a
 asl a
 pha
 asl a
 asl a
 sta.l SourceDamageState4086_BirthOffset
 asl a
 asl a
 clc
 adc.l SourceDamageState4086_BirthOffset
 tax
 lda.l $43904A,x
 cmp #$B4FB
 bne SourceDamageState4086_PopBad
 lda.l $439042,x
 and #$7F80
 cmp #$7F80
 beq SourceDamageState4086_PopBad
 lda.l $439040,x
 tay
 lda.l $439042,x
 sta.l SourceDamageState4086_BirthValueHigh
 pla
 pha
 asl a
 clc
 adc 1,s
 tax
 pla
 tya
 sta.l SOURCE_ENTITY_DAMAGE_STATE,x
 lda.l SourceDamageState4086_BirthValueHigh
 sta.l SOURCE_ENTITY_DAMAGE_STATE+2,x
 lda #0
 sta.l SOURCE_ENTITY_DAMAGE_STATE+4,x
 sta.l SOURCE_ENTITY_DAMAGE_STATE+6,x
 sta.l SOURCE_ENTITY_DAMAGE_STATE+8,x
 sta.l SOURCE_ENTITY_DAMAGE_STATE+10,x
SourceDamageState4086_Good:
.a16
.i16
 ply
 plx
 pla
 plp
 clc
 rtl
SourceDamageState4086_PopBad:
.a16
.i16
 pla
SourceDamageState4086_Bad:
.a16
.i16
 ply
 plx
 pla
 plp
 sec
 rtl
; Synchronous private scratch; never held across a callback.
SourceDamageState4086_BirthOffset = $7FBF02
SourceDamageState4086_BirthValueHigh = $7FBF04
