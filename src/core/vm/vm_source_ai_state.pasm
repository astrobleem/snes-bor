; Source entity AI scalars, separate from idle/frame-effect flags.
; 128 physical rows of 24 bytes: noaicontrol32, remaining 20 bytes reserved.
; Both compiler-owned birth paths clear this row before publishing exists=1.
; In particular $43EB10 is reactive, never noaicontrol.
SOURCE_ENTITY_AI_STATE = $42F400
SOURCE_ENTITY_AI_STATE_STRIDE = 24
SOURCE_ENTITY_AI_STATE_END = $430000
SourceAIState4086_InitializeBirth:
.a16
.i16
 php
 rep #$38
 phx
 phy
 cmp #128
 bcs SourceAIState4086_Bad
 asl a
 asl a
 asl a
 pha
 asl a
 clc
 adc 1,s
 tax
 pla
 ldy #12
 lda #0
SourceAIState4086_Clear:
.a16
.i16
 sta.l SOURCE_ENTITY_AI_STATE,x
 inx
 inx
 dey
 bne SourceAIState4086_Clear
 ply
 plx
 plp
 clc
 rtl
SourceAIState4086_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
