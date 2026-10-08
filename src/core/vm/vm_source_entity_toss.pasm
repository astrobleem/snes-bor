; Explicit physical entity source toss(ent,lift), distinct from script tossentity's
; optional horizontal arguments. Q16.16 adaptation; zero lift is a literal no-op.
; Caller owns the canonical current entity and revokes B624 on table mutation.
SourceEntityToss4086_Ready = $41FFB0
SourceEntityToss4086_Status = $41FFB2
SourceEntityToss4086_Slot = $41FFB4
SourceEntityToss4086_Lift = $41FFB6
SourceEntityToss4086_View = $41FFBA
SourceEntityToss4086_Side = $41FFBC
SourceEntityToss4086_Position = $41FFBE
SourceEntityToss4086_End = $41FFC2
SourceEntityToss4086_Execute:
.a16
.i16
 php
 rep #$38
 pha
 phx
 phy
 lda.l SourceEntityToss4086_Ready
 cmp #$B624
 beq SourceEntityToss4086_Lease
 jmp SourceEntityToss4086_Bad
SourceEntityToss4086_Lease:
.a16
.i16
 lda.l SourceEntityToss4086_Status
 beq SourceEntityToss4086_Idle
 jmp SourceEntityToss4086_Bad
SourceEntityToss4086_Idle:
.a16
.i16
 lda.l SourceEntityToss4086_Lift
 ora.l SourceEntityToss4086_Lift+2
 bne SourceEntityToss4086_Nonzero
 jmp SourceEntityToss4086_Done
SourceEntityToss4086_Nonzero:
.a16
.i16
 lda.l SourceToss4086_Ready
 cmp #$B4E2
 beq SourceEntityToss4086_TossLease
 jmp SourceEntityToss4086_Bad
SourceEntityToss4086_TossLease:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceEntityToss4086_WorldLease
 jmp SourceEntityToss4086_Bad
SourceEntityToss4086_WorldLease:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 beq SourceEntityToss4086_Pool
 jmp SourceEntityToss4086_Bad
SourceEntityToss4086_Pool:
.a16
.i16
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 beq SourceEntityToss4086_Sides
 jmp SourceEntityToss4086_Bad
SourceEntityToss4086_Sides:
.a16
.i16
 lda.l VmSourceWorld_Count
 cmp #129
 bcc SourceEntityToss4086_Count
 jmp SourceEntityToss4086_Bad
SourceEntityToss4086_Count:
.a16
.i16
 lda.l SourceEntityToss4086_Slot
 cmp.l VmSourceWorld_Count
 bcc SourceEntityToss4086_SlotValid
 jmp SourceEntityToss4086_Bad
SourceEntityToss4086_SlotValid:
.a16
.i16
 asl a
 asl a
 asl a
 asl a
 sta.l SourceEntityToss4086_View
 asl a
 asl a
 sta.l SourceEntityToss4086_Side
 clc
 adc.l SourceEntityToss4086_View
 sta.l SourceEntityToss4086_View
 tax
 lda.l SOURCE_WORLD_POOL,x
 clc
 adc #$C000
 cmp.l SourceEntityToss4086_View
 beq SourceEntityToss4086_Pointer
 jmp SourceEntityToss4086_Bad
SourceEntityToss4086_Pointer:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+2,x
 cmp #$0041
 beq SourceEntityToss4086_PointerBank
 jmp SourceEntityToss4086_Bad
SourceEntityToss4086_PointerBank:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+4,x
 ora.l SOURCE_WORLD_POOL+6,x
 bne SourceEntityToss4086_Alive
 jmp SourceEntityToss4086_Bad
SourceEntityToss4086_Alive:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+8,x
 cmp #BOR_VT_DECIMAL
 beq SourceEntityToss4086_Tag
 jmp SourceEntityToss4086_Bad
SourceEntityToss4086_Tag:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+10,x
 beq SourceEntityToss4086_TagHigh
 jmp SourceEntityToss4086_Bad
SourceEntityToss4086_TagHigh:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+12,x
 clc
 adc #$8000
 sta.l SourceEntityToss4086_Position
 lda.l SOURCE_WORLD_POOL+14,x
 adc #0
 bvc SourceEntityToss4086_Fits
 jmp SourceEntityToss4086_Bad
SourceEntityToss4086_Fits:
.a16
.i16
 sta.l SourceEntityToss4086_Position+2
 lda.l SourceEntityToss4086_Position
 sta.l SOURCE_WORLD_POOL+12,x
 lda.l SourceEntityToss4086_Position+2
 sta.l SOURCE_WORLD_POOL+14,x
 lda.l SourceEntityToss4086_Side
 tax
 lda.l SourceEntityToss4086_Lift
 sta.l SOURCE_WORLD_SIDES+44,x
 lda.l SourceEntityToss4086_Lift+2
 sta.l SOURCE_WORLD_SIDES+46,x
 lda.l SourceEntityToss4086_Slot
 asl a
 asl a
 tax
 lda.l VmSourceWorld_Time
 clc
 adc #1
 sta.l SOURCE_WORLD_TOSS_TIMES,x
 lda.l VmSourceWorld_Time+2
 adc #0
 sta.l SOURCE_WORLD_TOSS_TIMES+2,x
SourceEntityToss4086_Done:
.a16
.i16
 lda #2
 sta.l SourceEntityToss4086_Status
 ply
 plx
 pla
 plp
 clc
 rtl
SourceEntityToss4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceEntityToss4086_Status
 ply
 plx
 pla
 plp
 sec
 rtl
