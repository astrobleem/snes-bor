; Opt-in 128x16-byte actual source physics state. Immutable allocation:
; $42D800..$42DFFF, immediately before source freeze rows at $42E000.
; B61C requires the bounded reused CHR workspace to end at or before $42D800.
; Fields: falling32, hithead token32, landed_on_platform token32,
; damage_on_landing32. Pinned spawn memset zeros all before exists publication.
; This initializer does not execute active gravity or landing.
SourcePhysicsState4086_Ready = $40BFFE
SOURCE_ENTITY_PHYSICS = $42D800
SOURCE_ENTITY_PHYSICS_STRIDE = 16
SOURCE_ENTITY_PHYSICS_END = $42E000
SourcePhysicsState4086_InitializeBirth:
.a16
.i16
 php
 rep #$38
 pha
 phx
 phy
 lda.l SourcePhysicsState4086_Ready
 beq SourcePhysicsState4086_Good
 cmp #$B61C
 bne SourcePhysicsState4086_Bad
 lda 5,s ; saved physical slot, below Y/X
 cmp #128
 bcs SourcePhysicsState4086_Bad
 asl a
 asl a
 asl a
 asl a
 tax
 ldy #8
 lda #0
SourcePhysicsState4086_Clear:
.a16
.i16
 sta.l SOURCE_ENTITY_PHYSICS,x
 inx
 inx
 dey
 bne SourcePhysicsState4086_Clear
SourcePhysicsState4086_Good:
.a16
.i16
 ply
 plx
 pla
 plp
 clc
 rtl
SourcePhysicsState4086_Bad:
.a16
.i16
 ply
 plx
 pla
 plp
 sec
 rtl
