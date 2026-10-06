; Generic normal enemy/NPC default-init preparation. Biker/arrow reject.
; Semantic callbacks only; A=1 requests the source drop service, A=0 skips it.
; Source-sized random/drop/air/animation work still belongs to the full owner.
SourceDefaultEnemy4086_PrepareNormal:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceDefaultPlayer4086_Ready
 cmp #$B503
 beq SourceDefaultEnemy4086_Guard_1
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultEnemy4086_Guard_1:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Status
 cmp #3
 bne SourceDefaultEnemy4086_Guard_2
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultEnemy4086_Guard_2:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceDefaultEnemy4086_Guard_3
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultEnemy4086_Guard_3:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 beq SourceDefaultEnemy4086_Guard_4
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultEnemy4086_Guard_4:
.a16
.i16
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 beq SourceDefaultEnemy4086_Guard_5
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultEnemy4086_Guard_5:
.a16
.i16
 lda.l VmSourceWorld_Count
 bne SourceDefaultEnemy4086_Guard_6
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultEnemy4086_Guard_6:
.a16
.i16
 cmp #129
 bcc SourceDefaultEnemy4086_Guard_7
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultEnemy4086_Guard_7:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Slot
 cmp.l VmSourceWorld_Count
 bcc SourceDefaultEnemy4086_Guard_8
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultEnemy4086_Guard_8:
.a16
.i16
 lda.l SourceLifecycle4086_Ready
 cmp #$B4FB
 beq SourceDefaultEnemy4086_Guard_9
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultEnemy4086_Guard_9:
.a16
.i16
 lda.l SourceLifecycle4086_Status
 cmp #3
 bne SourceDefaultEnemy4086_Guard_10
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultEnemy4086_Guard_10:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Slot
 asl a
 asl a
 asl a
 asl a
 sta.l SourceDefaultPlayer4086_Life
 asl a
 asl a
 sta.l SourceDefaultPlayer4086_Side
 clc
 adc.l SourceDefaultPlayer4086_Life
 sta.l SourceDefaultPlayer4086_Life
 clc
 adc #$4000
 tax
 cmp.l $410000,x
 beq SourceDefaultEnemy4086_Guard_11
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultEnemy4086_Guard_11:
.a16
.i16
 lda.l $410002,x
 cmp #$0041
 beq SourceDefaultEnemy4086_Guard_12
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultEnemy4086_Guard_12:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Side
 tax
 lda.l $416800,x
 sta.l SourceDefaultPlayer4086_Action
 lda.l SourceDefaultPlayer4086_Life
 tax
 lda.l $43904A,x
 cmp #$B4FB
 beq SourceDefaultEnemy4086_Guard_13
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultEnemy4086_Guard_13:
.a16
.i16
 lda.l $439048,x
 cmp.l SourceDefaultPlayer4086_Action
 beq SourceDefaultEnemy4086_Guard_14
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultEnemy4086_Guard_14:
.a16
.i16
 lda.l VmSourceWorld_Level
 bne SourceDefaultEnemy4086_CoreLease
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultEnemy4086_CoreLease:
.a16
.i16
 lda.l SourceLifecycle4086_Status
 cmp #3
 bne SourceDefaultEnemy4086_LifeIdle
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultEnemy4086_LifeIdle:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Ready
 cmp #$B4EB
 beq SourceDefaultEnemy4086_CoreCount
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultEnemy4086_CoreCount:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Entities
 cmp.l VmSourceWorld_Count
 beq SourceDefaultEnemy4086_Core
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultEnemy4086_Core:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l SourceDefaultPlayer4086_Core
 asl a
 clc
 adc.l SourceDefaultPlayer4086_Core
 sta.l SourceDefaultPlayer4086_Core
 tax
 lda.l $40C04A,x
 beq SourceDefaultEnemy4086_TypeLow
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultEnemy4086_TypeLow:
.a16
.i16
 lda.l $40C048,x
 cmp #2
 beq SourceDefaultEnemy4086_Walk
 cmp #512
 beq SourceDefaultEnemy4086_Walk
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultEnemy4086_Walk:
.a16
.i16
 lda.l SourceDefaultChoice4086_Ready
 cmp #$B4FA
 beq SourceDefaultEnemy4086_ChoiceStatus
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultEnemy4086_ChoiceStatus:
.a16
.i16
 lda.l SourceDefaultChoice4086_Status
 cmp #3
 bne SourceDefaultEnemy4086_Subtype
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultEnemy4086_Subtype:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Life
 tax
 lda.l $439032,x
 bne SourceDefaultEnemy4086_Normal
 lda.l $439030,x
 cmp #1
 beq SourceDefaultEnemy4086_Reject
 cmp #3
 beq SourceDefaultEnemy4086_Reject
SourceDefaultEnemy4086_Normal:
.a16
.i16
 lda.l $439034,x
 ora.l $439036,x
 beq SourceDefaultEnemy4086_SpeedTruth
 lda #0
 sta.l SourceDefaultPlayer4086_InvLo
 sta.l SourceDefaultPlayer4086_InvHi
 bra SourceDefaultEnemy4086_ResolveSpawn
SourceDefaultEnemy4086_SpeedTruth:
.a16
.i16
 lda.l $43904C,x
 cmp #$B508
 bne SourceDefaultEnemy4086_Reject
 lda.l $439046,x
 bne SourceDefaultEnemy4086_Reject
 lda.l $439044,x
 cmp #2
 bcs SourceDefaultEnemy4086_Reject
 sta.l SourceDefaultPlayer4086_InvLo
 lda.l SourceDefaultPlayer4086_Side
 tax
 lda.l $41683C,x
 ora.l $41683E,x
 beq SourceDefaultEnemy4086_ZeroProjection
 lda.l SourceDefaultPlayer4086_InvLo
 beq SourceDefaultEnemy4086_Reject
 bra SourceDefaultEnemy4086_KeepSpeed
SourceDefaultEnemy4086_ZeroProjection:
.a16
.i16
 lda.l SourceDefaultPlayer4086_InvLo
 bne SourceDefaultEnemy4086_KeepSpeed
 lda #0
 sta.l SourceDefaultPlayer4086_InvLo
 lda #1
 sta.l SourceDefaultPlayer4086_InvHi
 bra SourceDefaultEnemy4086_ResolveSpawn
SourceDefaultEnemy4086_KeepSpeed:
.a16
.i16
 lda.l $41683C,x
 sta.l SourceDefaultPlayer4086_InvLo
 lda.l $41683E,x
 sta.l SourceDefaultPlayer4086_InvHi
 bra SourceDefaultEnemy4086_ResolveSpawn
SourceDefaultEnemy4086_Reject:
.a16
.i16
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultEnemy4086_ResolveSpawn:
.a16
.i16
 lda #0
 sta.l SourceDefaultPlayer4086_Action
 lda.l SourceDefaultPlayer4086_Slot
 sta.l SourceAnimationInit4086_Slot
 lda #0
 sta.l SourceAnimationInit4086_Reset
 lda.l SourceDefaultChoice4086_Spawn
 sta.l SourceAnimationInit4086_Number
 jsl SourceAnimationInit4086_Resolve
 bcc SourceDefaultEnemy4086_SpawnResolved
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultEnemy4086_SpawnResolved:
.a16
.i16
 lda.l SourceAnimationInit4086_Handle
 beq SourceDefaultEnemy4086_Respawn
 lda.l SourceAnimationInit4086_Count
 bne SourceDefaultEnemy4086_SpawnAction
SourceDefaultEnemy4086_Respawn:
.a16
.i16
 lda.l SourceDefaultChoice4086_Respawn
 sta.l SourceAnimationInit4086_Number
 jsl SourceAnimationInit4086_Resolve
 bcc SourceDefaultEnemy4086_RespawnResolved
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultEnemy4086_RespawnResolved:
.a16
.i16
 lda.l SourceAnimationInit4086_Handle
 beq SourceDefaultEnemy4086_Commit
 lda.l SourceAnimationInit4086_Count
 beq SourceDefaultEnemy4086_Commit
SourceDefaultEnemy4086_SpawnAction:
.a16
.i16
 lda #4
 sta.l SourceDefaultPlayer4086_Action
SourceDefaultEnemy4086_Commit:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Core
 tax
 lda.l $40C000,x
 ora.l $40C002,x
 bne SourceDefaultEnemy4086_Callbacks
 lda.l $40C048,x
 cmp #512
 beq SourceDefaultEnemy4086_NpcMultiple
 lda #5
 sta.l $40C000,x
 lda #0
 sta.l $40C002,x
 bra SourceDefaultEnemy4086_Callbacks
SourceDefaultEnemy4086_NpcMultiple:
.a16
.i16
 lda #$FFFF
 sta.l $40C000,x
 sta.l $40C002,x
SourceDefaultEnemy4086_Callbacks:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Life
 tax
 lda #6
 sta.l $439000,x
 lda #10
 sta.l $439004,x
 lda #9
 sta.l $439008,x
 lda #0
 sta.l $439002,x
 sta.l $439006,x
 sta.l $43900A,x
 lda.l SourceDefaultPlayer4086_Action
 beq SourceDefaultEnemy4086_Nograb
 sta.l $43900C,x
 lda #0
 sta.l $43900E,x
SourceDefaultEnemy4086_Nograb:
.a16
.i16
 lda.l $439032,x
 bne SourceDefaultEnemy4086_Speed
 lda.l $439030,x
 cmp #2
 bne SourceDefaultEnemy4086_Speed
 lda #1
 sta.l $439010,x
 lda #0
 sta.l $439012,x
SourceDefaultEnemy4086_Speed:
.a16
.i16
 lda.l $439034,x
 ora.l $439036,x
 beq SourceDefaultEnemy4086_DefaultSpeed
 lda #0
 sta.l $439044,x
 sta.l $439046,x
 lda #$B508
 sta.l $43904C,x
 bra SourceDefaultEnemy4086_WriteSpeed
SourceDefaultEnemy4086_DefaultSpeed:
.a16
.i16
 lda.l $439044,x
 bne SourceDefaultEnemy4086_WriteSpeed
 lda #1
 sta.l $439044,x
 lda #0
 sta.l $439046,x
SourceDefaultEnemy4086_WriteSpeed:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Side
 tax
 lda.l SourceDefaultPlayer4086_InvLo
 sta.l $41683C,x
 lda.l SourceDefaultPlayer4086_InvHi
 sta.l $41683E,x
 lda #2
 sta.l SourceDefaultPlayer4086_Status
 ply
 plx
 lda.l SourceDefaultPlayer4086_Action
 beq SourceDefaultEnemy4086_NeedDrop
 lda #0
 bra SourceDefaultEnemy4086_Done
SourceDefaultEnemy4086_NeedDrop:
.a16
.i16
 lda #1
SourceDefaultEnemy4086_Done:
.a16
.i16
 plp
 clc
 rtl
