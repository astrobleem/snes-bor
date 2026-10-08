; Generic ordinary arrow_move, zero-ptype constructor policy, Q16.16 movement.
; B616 lease requires compiler-owned ptype=0; any ptype mutation revokes it.
; No CHASE fallback and no fabricated wall index. Nonempty walls need backend.
; Caller is common_think MOVE; validates all leases before publishing velocity.
SourceArrowMove4086_Ready = $40BFC0
SourceArrowMove4086_Status = $40BFC2
SourceArrowMove4086_Lo = $40BFC4
SourceArrowMove4086_Hi = $40BFC6
SourceArrowMove4086_End = $40BFC8
SourceArrowMove4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceArrowMove4086_Ready
 cmp #$B616
 beq SourceArrowMove4086_Lease
 jmp SourceArrowMove4086_Bad
SourceArrowMove4086_Lease:
.a16
.i16
 lda.l SourceArrowMove4086_Status
 beq SourceArrowMove4086_Owner
 jmp SourceArrowMove4086_Bad
SourceArrowMove4086_Owner:
.a16
.i16
 jsl SourceCommonThink4086_CheckOwner
 bcc SourceArrowMove4086_State
 jmp SourceArrowMove4086_Bad
SourceArrowMove4086_State:
.a16
.i16
 lda.l SourceCommonThink4086_State
 cmp #8
 beq SourceArrowMove4086_Core
 jmp SourceArrowMove4086_Bad
SourceArrowMove4086_Core:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Ready
 cmp #$B4EB
 beq SourceArrowMove4086_Life
 jmp SourceArrowMove4086_Bad
SourceArrowMove4086_Life:
.a16
.i16
 lda.l SourceAI4086_Life
 tax
 lda.l $43904A,x
 cmp #$B4FB
 beq SourceArrowMove4086_Subtype
 jmp SourceArrowMove4086_Bad
SourceArrowMove4086_Subtype:
.a16
.i16
 lda.l $439032,x
 bne SourceArrowMove4086_SpeedLease
 lda.l $439030,x
 cmp #11
 bne SourceArrowMove4086_SpeedLease
 jmp SourceArrowMove4086_Bad
SourceArrowMove4086_SpeedLease:
.a16
.i16
 lda.l $43904C,x
 cmp #$B508
 beq SourceArrowMove4086_Stage
 jmp SourceArrowMove4086_Bad
SourceArrowMove4086_Stage:
.a16
.i16
 ; World callback owner requires a real source level. Wall lease is immutable.
 lda.l SourceEnvironment4086_Ready
 cmp #$B4D1
 beq SourceArrowMove4086_WallCount
 jmp SourceArrowMove4086_Bad
SourceArrowMove4086_WallCount:
.a16
.i16
 lda.l SourceEnvironment4086_WallCount
 beq SourceArrowMove4086_StageIdentity
 jmp SourceArrowMove4086_Bad
SourceArrowMove4086_StageIdentity:
.a16
.i16
 lda.l SourceEnvironment4086_Stage
 beq SourceArrowMove4086_StageBad
 cmp.l VmSourceWorld_Level
 beq SourceArrowMove4086_Direction
SourceArrowMove4086_StageBad:
.a16
.i16
 jmp SourceArrowMove4086_Bad
SourceArrowMove4086_Direction:
.a16
.i16
 lda.l SourceAI4086_View
 tax
 lda.l $410018,x
 cmp #BOR_VT_INTEGER
 beq SourceArrowMove4086_DirectionReserved
 jmp SourceArrowMove4086_Bad
SourceArrowMove4086_DirectionReserved:
.a16
.i16
 lda.l $41001A,x
 beq SourceArrowMove4086_Value
 jmp SourceArrowMove4086_Bad
SourceArrowMove4086_Value:
.a16
.i16
 lda.l $41001E,x
 bne SourceArrowMove4086_Done
 lda.l $41001C,x
 cmp #2
 bcs SourceArrowMove4086_Done
 tay
 lda.l SourceAI4086_Side
 tax
 lda.l SOURCE_WORLD_SIDES+60,x
 sta.l SourceArrowMove4086_Lo
 lda.l SOURCE_WORLD_SIDES+62,x
 sta.l SourceArrowMove4086_Hi
 cpy #1
 beq SourceArrowMove4086_Publish
 ; Checked negation. -32768 is outside the symmetric Q16 source domain.
 cmp #$8000
 bne SourceArrowMove4086_Negate
 lda.l SourceArrowMove4086_Lo
 beq SourceArrowMove4086_Bad
SourceArrowMove4086_Negate:
.a16
.i16
 sec
 lda #0
 sbc.l SourceArrowMove4086_Lo
 sta.l SourceArrowMove4086_Lo
 lda #0
 sbc.l SourceArrowMove4086_Hi
 sta.l SourceArrowMove4086_Hi
SourceArrowMove4086_Publish:
.a16
.i16
 lda.l SourceArrowMove4086_Lo
 sta.l SOURCE_WORLD_SIDES+36,x
 lda.l SourceArrowMove4086_Hi
 sta.l SOURCE_WORLD_SIDES+38,x
SourceArrowMove4086_Done:
.a16
.i16
 ; autokill |= 0 retains the real per-entity autokill value, without replacement.
 lda #2
 sta.l SourceArrowMove4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceArrowMove4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceArrowMove4086_Status
 ply
 plx
 plp
 sec
 rtl
