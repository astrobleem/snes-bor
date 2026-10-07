; Source dynamic combat subset. Independent from shallow cached-model copy.
; 128 x 20 bytes at $437E00..$4387FF. Held palette ends at $437E00,
; lifecycle rows begin at $439000; nested frame stack is $40F000..$40FFFF.
; Does not alias the separate sealtime timer or model maximum MP/health.
SOURCE_ENTITY_COMBAT = $437E00
SOURCE_ENTITY_COMBAT_STRIDE = 20
SOURCE_ENTITY_COMBAT_END = $438800
; DWORD drop+0,seal+4,combostep[0]+8,combotime+12; marker+16,reserved+18.
; Other player special-input indexes are not represented by this subset.
SourceCombatState4086_BirthClear:
.a16
.i16
 php
 rep #$38
 phx
 phy
 cmp #128
 bcc SourceCombatState4086_Slot
 jmp SourceCombatState4086_Bad
SourceCombatState4086_Slot:
.a16
.i16
 asl a
 asl a
 pha
 asl a
 asl a
 clc
 adc 1,s
 tax
 pla
 ldy #10
 lda #0
SourceCombatState4086_Clear:
.a16
.i16
 sta.l SOURCE_ENTITY_COMBAT,x
 inx
 inx
 dey
 bne SourceCombatState4086_Clear
 txa
 sec
 sbc #4
 tax
 lda #$B5FB
 sta.l SOURCE_ENTITY_COMBAT,x
 ply
 plx
 plp
 clc
 rtl
SourceCombatState4086_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
