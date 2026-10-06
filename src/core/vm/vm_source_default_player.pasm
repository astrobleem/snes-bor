; B503 synchronous TYPE_PLAYER field initialization after first-animation work.
; Assigns semantic callback IDs, not executable AI/damage bindings.
; Requires an existing animation, so the source drop/jump branch is not entered.
; Final idle/platform/wall work remains owned by the complete default initializer.
SourceDefaultPlayer4086_Ready = $7FFEB8
SourceDefaultPlayer4086_Slot = $7FFEBA
SourceDefaultPlayer4086_Status = $7FFEBC
SourceDefaultPlayer4086_Life = $7FFEBE
SourceDefaultPlayer4086_Core = $7FFEC0
SourceDefaultPlayer4086_Side = $7FFEC2
SourceDefaultPlayer4086_Action = $7FFEC4
SourceDefaultPlayer4086_InvLo = $7FFEC6
SourceDefaultPlayer4086_InvHi = $7FFEC8
SourceDefaultPlayer4086_TimeLo = $7FFECA
SourceDefaultPlayer4086_TimeHi = $7FFECC
SourceDefaultPlayer4086_Jump = $7FFECE

SourceDefaultPlayer4086_Apply:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceDefaultPlayer4086_Ready
 cmp #$B503
 beq SourceDefaultPlayer4086_Guard_1
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayer4086_Guard_1:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Status
 cmp #3
 bne SourceDefaultPlayer4086_Guard_2
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayer4086_Guard_2:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceDefaultPlayer4086_Guard_3
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayer4086_Guard_3:
.a16
.i16
 lda.l VmSourceWorld_Level
 bne SourceDefaultPlayer4086_Guard_4
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayer4086_Guard_4:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 beq SourceDefaultPlayer4086_Guard_5
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayer4086_Guard_5:
.a16
.i16
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 beq SourceDefaultPlayer4086_Guard_6
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayer4086_Guard_6:
.a16
.i16
 lda.l VmSourceWorld_Count
 bne SourceDefaultPlayer4086_Guard_7
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayer4086_Guard_7:
.a16
.i16
 cmp #129
 bcc SourceDefaultPlayer4086_Guard_8
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayer4086_Guard_8:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Slot
 cmp.l VmSourceWorld_Count
 bcc SourceDefaultPlayer4086_Guard_9
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayer4086_Guard_9:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Ready
 cmp #$B4EB
 beq SourceDefaultPlayer4086_Guard_10
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayer4086_Guard_10:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Entities
 cmp.l VmSourceWorld_Count
 beq SourceDefaultPlayer4086_Guard_11
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayer4086_Guard_11:
.a16
.i16
 lda.l SourceLifecycle4086_Ready
 cmp #$B4FB
 beq SourceDefaultPlayer4086_Guard_12
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayer4086_Guard_12:
.a16
.i16
 lda.l SourceLifecycle4086_Status
 cmp #3
 bne SourceDefaultPlayer4086_Guard_13
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayer4086_Guard_13:
.a16
.i16
 lda.l SourceDefaultChoice4086_Ready
 cmp #$B4FA
 beq SourceDefaultPlayer4086_Guard_14
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayer4086_Guard_14:
.a16
.i16
 lda.l SourceDefaultChoice4086_Status
 cmp #2
 beq SourceDefaultPlayer4086_Guard_15
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayer4086_Guard_15:
.a16
.i16
 lda.l SourceDefaultChoice4086_Slot
 cmp.l SourceDefaultPlayer4086_Slot
 beq SourceDefaultPlayer4086_Guard_16
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayer4086_Guard_16:
.a16
.i16
 jsl SourceAnimationInit4086_CheckIdle
 bcc SourceDefaultPlayer4086_Guard_17
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayer4086_Guard_17:
.a16
.i16
 lda.l SourceDefaultChoice4086_Service
 beq SourceDefaultPlayer4086_NoFirstCall
 lda.l SourceAnimationInit4086_State
 cmp #2
 beq SourceDefaultPlayer4086_Guard_18
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayer4086_Guard_18:
.a16
.i16
 lda.l SourceAnimationInit4086_Slot
 cmp.l SourceDefaultPlayer4086_Slot
 beq SourceDefaultPlayer4086_Guard_19
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayer4086_Guard_19:
.a16
.i16
SourceDefaultPlayer4086_NoFirstCall:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Slot
 asl a
 asl a
 asl a
 asl a
 sta.l SourceDefaultPlayer4086_Core
 asl a
 asl a
 sta.l SourceDefaultPlayer4086_Side
 clc
 adc.l SourceDefaultPlayer4086_Core
 sta.l SourceDefaultPlayer4086_Life
 clc
 adc #$4000
 tax
 cmp.l $410000,x
 beq SourceDefaultPlayer4086_Guard_20
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayer4086_Guard_20:
.a16
.i16
 lda.l $410002,x
 cmp #$0041
 beq SourceDefaultPlayer4086_Guard_21
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayer4086_Guard_21:
.a16
.i16
 lda.l $410004,x
 cmp #1
 beq SourceDefaultPlayer4086_Guard_22
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayer4086_Guard_22:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Core
 asl a
 clc
 adc.l SourceDefaultPlayer4086_Side
 sta.l SourceDefaultPlayer4086_Core
 tax
 lda.l $40C04A,x
 beq SourceDefaultPlayer4086_Guard_23
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayer4086_Guard_23:
.a16
.i16
 lda.l $40C048,x
 cmp #1
 beq SourceDefaultPlayer4086_Guard_24
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayer4086_Guard_24:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Side
 tax
 lda.l $416804,x
 bne SourceDefaultPlayer4086_Guard_25
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayer4086_Guard_25:
.a16
.i16
 lda.l $416800,x
 sta.l SourceDefaultPlayer4086_Action
 lda.l SourceDefaultPlayer4086_Life
 tax
 lda.l $43904A,x
 cmp #$B4FB
 beq SourceDefaultPlayer4086_Guard_26
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayer4086_Guard_26:
.a16
.i16
 lda.l $439048,x
 cmp.l SourceDefaultPlayer4086_Action
 beq SourceDefaultPlayer4086_Guard_27
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayer4086_Guard_27:
.a16
.i16
 lda.l $439038,x
 sta.l SourceDefaultPlayer4086_InvLo
 lda.l $43903A,x
 sta.l SourceDefaultPlayer4086_InvHi
 cmp #$8000
 bne SourceDefaultPlayer4086_MakeInvGood
 lda.l SourceDefaultPlayer4086_InvLo
 bne SourceDefaultPlayer4086_MakeInvGood
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayer4086_MakeInvGood:
.a16
.i16
 lda.l SourceDefaultChoice4086_TimeLo
 sta.l SourceDefaultPlayer4086_TimeLo
 lda.l SourceDefaultChoice4086_TimeHi
 sta.l SourceDefaultPlayer4086_TimeHi
 lda #0
 sta.l SourceDefaultPlayer4086_Action
 lda.l SourceDefaultPlayer4086_Slot
 sta.l SourceAnimationInit4086_Slot
 lda.l SourceDefaultChoice4086_Spawn
 sta.l SourceAnimationInit4086_Number
 jsl SourceAnimationInit4086_Resolve
 bcc SourceDefaultPlayer4086_SpawnResolved
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayer4086_SpawnResolved:
.a16
.i16
 lda.l SourceAnimationInit4086_Handle
 beq SourceDefaultPlayer4086_Respawn
 lda.l SourceAnimationInit4086_Count
 bne SourceDefaultPlayer4086_SpawnAction
SourceDefaultPlayer4086_Respawn:
.a16
.i16
 lda.l SourceDefaultChoice4086_Respawn
 sta.l SourceAnimationInit4086_Number
 jsl SourceAnimationInit4086_Resolve
 bcc SourceDefaultPlayer4086_RespawnResolved
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayer4086_RespawnResolved:
.a16
.i16
 lda.l SourceAnimationInit4086_Handle
 beq SourceDefaultPlayer4086_Commit
 lda.l SourceAnimationInit4086_Count
 beq SourceDefaultPlayer4086_Commit
SourceDefaultPlayer4086_SpawnAction:
.a16
.i16
 lda #4
 sta.l SourceDefaultPlayer4086_Action
SourceDefaultPlayer4086_Commit:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Life
 tax
 lda #2
 sta.l $439000,x
 lda #1
 sta.l $439004,x
 lda #3
 sta.l $439008,x
 lda #0
 sta.l $439002,x
 sta.l $439006,x
 sta.l $43900A,x
 lda.l SourceDefaultPlayer4086_Action
 beq SourceDefaultPlayer4086_Invincible
 sta.l $43900C,x
 lda #0
 sta.l $43900E,x
SourceDefaultPlayer4086_Invincible:
.a16
.i16
 lda.l SourceDefaultPlayer4086_TimeLo
 ora.l SourceDefaultPlayer4086_TimeHi
 beq SourceDefaultPlayer4086_Done
 lda.l SourceDefaultPlayer4086_InvLo
 ora.l SourceDefaultPlayer4086_InvHi
 beq SourceDefaultPlayer4086_Done
 lda #1
 sta.l $439018,x
 sta.l $439024,x
 lda #0
 sta.l $43901A,x
 sta.l $439026,x
 sta.l $43901E,x
 lda.l SourceDefaultPlayer4086_InvHi
 bmi SourceDefaultPlayer4086_Negative
 lda #1
 sta.l $43901C,x
 bra SourceDefaultPlayer4086_Deadline
SourceDefaultPlayer4086_Negative:
.a16
.i16
 lda #0
 sta.l $43901C,x
 lda.l SourceDefaultPlayer4086_InvLo
 eor #$FFFF
 clc
 adc #1
 sta.l SourceDefaultPlayer4086_InvLo
 lda.l SourceDefaultPlayer4086_InvHi
 eor #$FFFF
 adc #0
 sta.l SourceDefaultPlayer4086_InvHi
SourceDefaultPlayer4086_Deadline:
.a16
.i16
 lda.l SourceDefaultPlayer4086_InvLo
 clc
 adc.l SourceDefaultPlayer4086_TimeLo
 sta.l $439020,x
 lda.l SourceDefaultPlayer4086_InvHi
 adc.l SourceDefaultPlayer4086_TimeHi
 sta.l $439022,x
SourceDefaultPlayer4086_Done:
.a16
.i16
 lda #2
 sta.l SourceDefaultPlayer4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceDefaultPlayer4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceDefaultPlayer4086_Status
 ply
 plx
 plp
 sec
 rtl

; Source action/drop preparation. A=1 requires actual ent_set_anim JUMP
; and frame-zero completion before invincibility/final environment work.
; This synchronous preparation has no independent pending ticket.
SourceDefaultPlayer4086_PrepareAction:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceDefaultPlayer4086_Ready
 cmp #$B503
 beq SourceDefaultPlayerAction4086_Guard_1
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_Guard_1:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Status
 cmp #3
 bne SourceDefaultPlayerAction4086_Guard_2
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_Guard_2:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceDefaultPlayerAction4086_Guard_3
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_Guard_3:
.a16
.i16
 lda.l VmSourceWorld_Level
 bne SourceDefaultPlayerAction4086_Guard_4
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_Guard_4:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 beq SourceDefaultPlayerAction4086_Guard_5
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_Guard_5:
.a16
.i16
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 beq SourceDefaultPlayerAction4086_Guard_6
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_Guard_6:
.a16
.i16
 lda.l VmSourceWorld_Count
 bne SourceDefaultPlayerAction4086_Guard_7
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_Guard_7:
.a16
.i16
 cmp #129
 bcc SourceDefaultPlayerAction4086_Guard_8
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_Guard_8:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Slot
 cmp.l VmSourceWorld_Count
 bcc SourceDefaultPlayerAction4086_Guard_9
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_Guard_9:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Ready
 cmp #$B4EB
 beq SourceDefaultPlayerAction4086_Guard_10
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_Guard_10:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Entities
 cmp.l VmSourceWorld_Count
 beq SourceDefaultPlayerAction4086_Guard_11
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_Guard_11:
.a16
.i16
 lda.l SourceLifecycle4086_Ready
 cmp #$B4FB
 beq SourceDefaultPlayerAction4086_Guard_12
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_Guard_12:
.a16
.i16
 lda.l SourceLifecycle4086_Status
 cmp #3
 bne SourceDefaultPlayerAction4086_Guard_13
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_Guard_13:
.a16
.i16
 lda.l SourceDefaultChoice4086_Ready
 cmp #$B4FA
 beq SourceDefaultPlayerAction4086_Guard_14
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_Guard_14:
.a16
.i16
 lda.l SourceDefaultChoice4086_Status
 cmp #2
 beq SourceDefaultPlayerAction4086_Guard_15
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_Guard_15:
.a16
.i16
 lda.l SourceDefaultChoice4086_Slot
 cmp.l SourceDefaultPlayer4086_Slot
 beq SourceDefaultPlayerAction4086_Guard_16
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_Guard_16:
.a16
.i16
 jsl SourceAnimationInit4086_CheckIdle
 bcc SourceDefaultPlayerAction4086_Guard_17
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_Guard_17:
.a16
.i16
 lda.l SourceDefaultChoice4086_Service
 beq SourceDefaultPlayerAction4086_NoFirstCall
 lda.l SourceAnimationInit4086_State
 cmp #2
 beq SourceDefaultPlayerAction4086_Guard_18
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_Guard_18:
.a16
.i16
 lda.l SourceAnimationInit4086_Slot
 cmp.l SourceDefaultPlayer4086_Slot
 beq SourceDefaultPlayerAction4086_Guard_19
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_Guard_19:
.a16
.i16
SourceDefaultPlayerAction4086_NoFirstCall:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Slot
 asl a
 asl a
 asl a
 asl a
 sta.l SourceDefaultPlayer4086_Core
 asl a
 asl a
 sta.l SourceDefaultPlayer4086_Side
 clc
 adc.l SourceDefaultPlayer4086_Core
 sta.l SourceDefaultPlayer4086_Life
 clc
 adc #$4000
 tax
 cmp.l $410000,x
 beq SourceDefaultPlayerAction4086_Guard_20
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_Guard_20:
.a16
.i16
 lda.l $410002,x
 cmp #$0041
 beq SourceDefaultPlayerAction4086_Guard_21
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_Guard_21:
.a16
.i16
 lda.l $410004,x
 cmp #1
 beq SourceDefaultPlayerAction4086_Guard_22
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_Guard_22:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Core
 asl a
 clc
 adc.l SourceDefaultPlayer4086_Side
 sta.l SourceDefaultPlayer4086_Core
 tax
 lda.l $40C04A,x
 beq SourceDefaultPlayerAction4086_Guard_23
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_Guard_23:
.a16
.i16
 lda.l $40C048,x
 cmp #1
 beq SourceDefaultPlayerAction4086_Guard_24
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_Guard_24:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Side
 tax
SourceDefaultPlayerAction4086_Guard_25:
.a16
.i16
 lda.l $416800,x
 sta.l SourceDefaultPlayer4086_Action
 lda.l SourceDefaultPlayer4086_Life
 tax
 lda.l $43904A,x
 cmp #$B4FB
 beq SourceDefaultPlayerAction4086_Guard_26
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_Guard_26:
.a16
.i16
 lda.l $439048,x
 cmp.l SourceDefaultPlayer4086_Action
 beq SourceDefaultPlayerAction4086_Guard_27
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_Guard_27:
.a16
.i16
 lda.l $439038,x
 sta.l SourceDefaultPlayer4086_InvLo
 lda.l $43903A,x
 sta.l SourceDefaultPlayer4086_InvHi
 cmp #$8000
 bne SourceDefaultPlayerAction4086_MakeInvGood
 lda.l SourceDefaultPlayer4086_InvLo
 bne SourceDefaultPlayerAction4086_MakeInvGood
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_MakeInvGood:
.a16
.i16
 lda.l SourceDefaultChoice4086_TimeLo
 sta.l SourceDefaultPlayer4086_TimeLo
 lda.l SourceDefaultChoice4086_TimeHi
 sta.l SourceDefaultPlayer4086_TimeHi
 lda #0
 sta.l SourceDefaultPlayer4086_Action
 lda.l SourceDefaultPlayer4086_Slot
 sta.l SourceAnimationInit4086_Slot
 lda.l SourceDefaultChoice4086_Spawn
 sta.l SourceAnimationInit4086_Number
 jsl SourceAnimationInit4086_Resolve
 bcc SourceDefaultPlayerAction4086_SpawnResolved
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_SpawnResolved:
.a16
.i16
 lda.l SourceAnimationInit4086_Handle
 beq SourceDefaultPlayerAction4086_Respawn
 lda.l SourceAnimationInit4086_Count
 bne SourceDefaultPlayerAction4086_SpawnAction
SourceDefaultPlayerAction4086_Respawn:
.a16
.i16
 lda.l SourceDefaultChoice4086_Respawn
 sta.l SourceAnimationInit4086_Number
 jsl SourceAnimationInit4086_Resolve
 bcc SourceDefaultPlayerAction4086_RespawnResolved
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_RespawnResolved:
.a16
.i16
 lda.l SourceAnimationInit4086_Handle
 beq SourceDefaultPlayerAction4086_DecideDrop
 lda.l SourceAnimationInit4086_Count
 beq SourceDefaultPlayerAction4086_DecideDrop
SourceDefaultPlayerAction4086_SpawnAction:
.a16
.i16
 lda #4
 sta.l SourceDefaultPlayer4086_Action
SourceDefaultPlayerAction4086_DecideDrop:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Action
 beq SourceDefaultPlayerAction4086_NoSpawn
 jmp SourceDefaultPlayerAction4086_Commit
SourceDefaultPlayerAction4086_NoSpawn:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Side
 tax
 lda.l $416804,x
 beq SourceDefaultPlayerAction4086_NoAnimation
 jmp SourceDefaultPlayerAction4086_Commit
SourceDefaultPlayerAction4086_NoAnimation:
.a16
.i16
 lda.l SourceDefaultPlayer4086_TimeLo
 ora.l SourceDefaultPlayer4086_TimeHi
 bne SourceDefaultPlayerAction4086_HasTime
 jmp SourceDefaultPlayerAction4086_Commit
SourceDefaultPlayerAction4086_HasTime:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Slot
 sta.l SourcePlayerSpawnHeight4086_Slot
 jsl SourcePlayerSpawnHeight4086_Query
 bcc SourceDefaultPlayerAction4086_HeightGood
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_HeightGood:
.a16
.i16
 lda.l SourcePlayerSpawnHeight4086_View
 tax
 lda.l $410008,x
 cmp #BOR_VT_DECIMAL
 beq SourceDefaultPlayerAction4086_HeightTag
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_HeightTag:
.a16
.i16
 lda.l $41000A,x
 beq SourceDefaultPlayerAction4086_HeightReserved
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_HeightReserved:
.a16
.i16
 lda.l SourcePlayerSpawnHeight4086_ValueHi
 eor #$8000
 sta.l SourceDefaultPlayer4086_InvHi
 lda.l $41000E,x
 eor #$8000
 cmp.l SourceDefaultPlayer4086_InvHi
 bcc SourceDefaultPlayerAction4086_Drop
 beq SourceDefaultPlayerAction4086_CompareLow
 jmp SourceDefaultPlayerAction4086_Commit
SourceDefaultPlayerAction4086_CompareLow:
.a16
.i16
 lda.l $41000C,x
 cmp.l SourcePlayerSpawnHeight4086_ValueLo
 bcc SourceDefaultPlayerAction4086_Drop
 jmp SourceDefaultPlayerAction4086_Commit
SourceDefaultPlayerAction4086_Drop:
.a16
.i16
 lda #5
 sta.l SourceDefaultPlayer4086_Action
 lda.l SourceDefaultPlayer4086_Jump
 sta.l SourceAnimationInit4086_Number
 jsl SourceAnimationInit4086_Resolve
 bcc SourceDefaultPlayerAction4086_JumpResolved
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_JumpResolved:
.a16
.i16
 lda.l SourceAnimationInit4086_Handle
 beq SourceDefaultPlayerAction4086_Commit
 lda.l SourceAnimationInit4086_Count
 beq SourceDefaultPlayerAction4086_Commit
 lda #$8005
 sta.l SourceDefaultPlayer4086_Action
 lda #0
 sta.l SourceAnimationInit4086_Reset
SourceDefaultPlayerAction4086_Commit:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Life
 tax
 lda #2
 sta.l $439000,x
 lda #1
 sta.l $439004,x
 lda #3
 sta.l $439008,x
 lda #0
 sta.l $439002,x
 sta.l $439006,x
 sta.l $43900A,x
 lda.l SourceDefaultPlayer4086_Action
 and #$7FFF
 beq SourceDefaultPlayerAction4086_MetadataDone
 sta.l $43900C,x
 lda #0
 sta.l $43900E,x
 lda.l SourceDefaultPlayer4086_Action
 and #$7FFF
 cmp #5
 bne SourceDefaultPlayerAction4086_MetadataDone
 lda.l SourcePlayerSpawnHeight4086_View
 tax
 lda.l SourcePlayerSpawnHeight4086_ValueLo
 sta.l $41000C,x
 lda.l SourcePlayerSpawnHeight4086_ValueHi
 sta.l $41000E,x
SourceDefaultPlayerAction4086_MetadataDone:
.a16
.i16
 lda #2
 sta.l SourceDefaultPlayer4086_Status
 lda.l SourceDefaultPlayer4086_Action
 bmi SourceDefaultPlayerAction4086_NeedJump
 lda #0
 bra SourceDefaultPlayerAction4086_Return
SourceDefaultPlayerAction4086_NeedJump:
.a16
.i16
 lda #1
SourceDefaultPlayerAction4086_Return:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl

; Synchronous prepared action executor. Existing B4EC owns any resulting
; frame-zero continuation; no duplicate pending ticket outside its snapshot.
SourceDefaultPlayer4086_BeginAction:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jsl SourceDefaultPlayer4086_PrepareAction
 bcc SourceDefaultPlayerAction4086_BeginGood
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_BeginGood:
.a16
.i16
 cmp #1
 beq SourceDefaultPlayerAction4086_BeginJump
 lda #0
 ply
 plx
 plp
 clc
 rtl
SourceDefaultPlayerAction4086_BeginJump:
.a16
.i16
 jsl SourceAnimationInit4086_Begin
 bcc SourceDefaultPlayerAction4086_BeginDone
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerAction4086_BeginDone:
.a16
.i16
 lda #1
 ply
 plx
 plp
 clc
 rtl

; Post-JUMP selected PLAYER case. Caller supplies current source time in
; TimeLo/Hi. Read fresh modeldata even if the callback changed TYPE/model.
; Preserve valid dead pointers; source C continues its selected case.
SourceDefaultPlayer4086_ApplyInvincibility:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceDefaultPlayer4086_Ready
 cmp #$B503
 beq SourceDefaultPlayerInv4086_Guard_1
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerInv4086_Guard_1:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Status
 cmp #3
 bne SourceDefaultPlayerInv4086_Guard_2
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerInv4086_Guard_2:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceDefaultPlayerInv4086_Guard_3
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerInv4086_Guard_3:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 beq SourceDefaultPlayerInv4086_Guard_4
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerInv4086_Guard_4:
.a16
.i16
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 beq SourceDefaultPlayerInv4086_Guard_5
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerInv4086_Guard_5:
.a16
.i16
 lda.l VmSourceWorld_Count
 bne SourceDefaultPlayerInv4086_Guard_6
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerInv4086_Guard_6:
.a16
.i16
 cmp #129
 bcc SourceDefaultPlayerInv4086_Guard_7
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerInv4086_Guard_7:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Slot
 cmp.l VmSourceWorld_Count
 bcc SourceDefaultPlayerInv4086_Guard_8
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerInv4086_Guard_8:
.a16
.i16
 lda.l SourceLifecycle4086_Ready
 cmp #$B4FB
 beq SourceDefaultPlayerInv4086_Guard_9
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerInv4086_Guard_9:
.a16
.i16
 lda.l SourceLifecycle4086_Status
 cmp #3
 bne SourceDefaultPlayerInv4086_Guard_10
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerInv4086_Guard_10:
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
 beq SourceDefaultPlayerInv4086_Guard_11
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerInv4086_Guard_11:
.a16
.i16
 lda.l $410002,x
 cmp #$0041
 beq SourceDefaultPlayerInv4086_Guard_12
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerInv4086_Guard_12:
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
 beq SourceDefaultPlayerInv4086_Guard_13
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerInv4086_Guard_13:
.a16
.i16
 lda.l $439048,x
 cmp.l SourceDefaultPlayer4086_Action
 beq SourceDefaultPlayerInv4086_Guard_14
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerInv4086_Guard_14:
.a16
.i16
 lda.l $439038,x
 sta.l SourceDefaultPlayer4086_InvLo
 lda.l $43903A,x
 sta.l SourceDefaultPlayer4086_InvHi
 cmp #$8000
 bne SourceDefaultPlayerInv4086_DurationGood
 lda.l SourceDefaultPlayer4086_InvLo
 bne SourceDefaultPlayerInv4086_DurationGood
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultPlayerInv4086_DurationGood:
.a16
.i16
SourceDefaultPlayerInv4086_Invincible:
.a16
.i16
 lda.l SourceDefaultPlayer4086_TimeLo
 ora.l SourceDefaultPlayer4086_TimeHi
 beq SourceDefaultPlayerInv4086_Done
 lda.l SourceDefaultPlayer4086_InvLo
 ora.l SourceDefaultPlayer4086_InvHi
 beq SourceDefaultPlayerInv4086_Done
 lda #1
 sta.l $439018,x
 sta.l $439024,x
 lda #0
 sta.l $43901A,x
 sta.l $439026,x
 sta.l $43901E,x
 lda.l SourceDefaultPlayer4086_InvHi
 bmi SourceDefaultPlayerInv4086_Negative
 lda #1
 sta.l $43901C,x
 bra SourceDefaultPlayerInv4086_Deadline
SourceDefaultPlayerInv4086_Negative:
.a16
.i16
 lda #0
 sta.l $43901C,x
 lda.l SourceDefaultPlayer4086_InvLo
 eor #$FFFF
 clc
 adc #1
 sta.l SourceDefaultPlayer4086_InvLo
 lda.l SourceDefaultPlayer4086_InvHi
 eor #$FFFF
 adc #0
 sta.l SourceDefaultPlayer4086_InvHi
SourceDefaultPlayerInv4086_Deadline:
.a16
.i16
 lda.l SourceDefaultPlayer4086_InvLo
 clc
 adc.l SourceDefaultPlayer4086_TimeLo
 sta.l $439020,x
 lda.l SourceDefaultPlayer4086_InvHi
 adc.l SourceDefaultPlayer4086_TimeHi
 sta.l $439022,x
SourceDefaultPlayerInv4086_Done:
.a16
.i16
 lda #2
 sta.l SourceDefaultPlayer4086_Status
 ply
 plx
 plp
 clc
 rtl

; Generic ent_default_init tail when an animation already exists. Uses the
; shared B503 synchronous field-component lease/slot, not actor identity.
; Empty platform/wall capability is required only for positive query flags.
SourceDefaultInit4086_FinalizeEmpty:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceDefaultPlayer4086_Ready
 cmp #$B503
 beq SourceDefaultInitTail4086_Guard_1
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultInitTail4086_Guard_1:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Status
 cmp #3
 bne SourceDefaultInitTail4086_Guard_2
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultInitTail4086_Guard_2:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceDefaultInitTail4086_Guard_3
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultInitTail4086_Guard_3:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 beq SourceDefaultInitTail4086_Guard_4
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultInitTail4086_Guard_4:
.a16
.i16
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 beq SourceDefaultInitTail4086_Guard_5
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultInitTail4086_Guard_5:
.a16
.i16
 lda.l VmSourceWorld_Count
 bne SourceDefaultInitTail4086_Guard_6
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultInitTail4086_Guard_6:
.a16
.i16
 cmp #129
 bcc SourceDefaultInitTail4086_Guard_7
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultInitTail4086_Guard_7:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Slot
 cmp.l VmSourceWorld_Count
 bcc SourceDefaultInitTail4086_Guard_8
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultInitTail4086_Guard_8:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Ready
 cmp #$B4EB
 beq SourceDefaultInitTail4086_Guard_9
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultInitTail4086_Guard_9:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Entities
 cmp.l VmSourceWorld_Count
 beq SourceDefaultInitTail4086_Guard_10
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultInitTail4086_Guard_10:
.a16
.i16
 jsl SourceAnimationInit4086_CheckIdle
 bcc SourceDefaultInitTail4086_Guard_11
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultInitTail4086_Guard_11:
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
 clc
 adc #$4000
 tax
 cmp.l $410000,x
 beq SourceDefaultInitTail4086_Guard_12
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultInitTail4086_Guard_12:
.a16
.i16
 lda.l $410002,x
 cmp #$0041
 beq SourceDefaultInitTail4086_Guard_13
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultInitTail4086_Guard_13:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Side
 clc
 adc.l SourceDefaultPlayer4086_Life
 clc
 adc.l SourceDefaultPlayer4086_Life
 sta.l SourceDefaultPlayer4086_Core
 lda.l SourceDefaultPlayer4086_Side
 tax
 lda.l $416804,x
 bne SourceDefaultInitTail4086_Guard_14
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultInitTail4086_Guard_14:
.a16
.i16
 lda.l VmSourceWorld_Level
 bne SourceDefaultInitTail4086_Level
 jmp SourceDefaultInitTail4086_Done
SourceDefaultInitTail4086_Level:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Core
 tax
 lda.l $40C00A,x
 bmi SourceDefaultInitTail4086_NoPlatform
 bne SourceDefaultInitTail4086_Query
 lda.l $40C008,x
 bne SourceDefaultInitTail4086_Query
SourceDefaultInitTail4086_NoPlatform:
.a16
.i16
 lda.l $40C006,x
 bmi SourceDefaultInitTail4086_Clamp
 bne SourceDefaultInitTail4086_Query
 lda.l $40C004,x
 beq SourceDefaultInitTail4086_Clamp
SourceDefaultInitTail4086_Query:
.a16
.i16
 jsl SourceEmptyInitEnvironment4086_Query
 bcc SourceDefaultInitTail4086_Clamp
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultInitTail4086_Clamp:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Core
 tax
 lda.l $40C002,x
 bpl SourceDefaultInitTail4086_Done
 lda #0
 sta.l $40C000,x
 sta.l $40C002,x
SourceDefaultInitTail4086_Done:
.a16
.i16
 lda #2
 sta.l SourceDefaultPlayer4086_Status
 ply
 plx
 plp
 clc
 rtl

; Generic final set_idle when current animation is absent. DEFAULT_IDLE_ONLY
; registry lease is required; expensive dispatch stays in the compiler.
; Returns A=1 with the existing B4EC frame-zero continuation, otherwise A=0.
; Caller must complete actual frame zero/Ack, then FinalizeEmpty.
SourceDefaultInit4086_BeginIdle:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceDefaultPlayer4086_Ready
 cmp #$B503
 beq SourceDefaultInitIdle4086_Guard_1
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultInitIdle4086_Guard_1:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Status
 cmp #3
 bne SourceDefaultInitIdle4086_Guard_2
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultInitIdle4086_Guard_2:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceDefaultInitIdle4086_Guard_3
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultInitIdle4086_Guard_3:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 beq SourceDefaultInitIdle4086_Guard_4
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultInitIdle4086_Guard_4:
.a16
.i16
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 beq SourceDefaultInitIdle4086_Guard_5
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultInitIdle4086_Guard_5:
.a16
.i16
 lda.l VmSourceWorld_Count
 bne SourceDefaultInitIdle4086_Guard_6
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultInitIdle4086_Guard_6:
.a16
.i16
 cmp #129
 bcc SourceDefaultInitIdle4086_Guard_7
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultInitIdle4086_Guard_7:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Slot
 cmp.l VmSourceWorld_Count
 bcc SourceDefaultInitIdle4086_Guard_8
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultInitIdle4086_Guard_8:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Ready
 cmp #$B4EB
 beq SourceDefaultInitIdle4086_Guard_9
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultInitIdle4086_Guard_9:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Entities
 cmp.l VmSourceWorld_Count
 beq SourceDefaultInitIdle4086_Guard_10
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultInitIdle4086_Guard_10:
.a16
.i16
 jsl SourceAnimationInit4086_CheckIdle
 bcc SourceDefaultInitIdle4086_Guard_11
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultInitIdle4086_Guard_11:
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
 clc
 adc #$4000
 tax
 cmp.l $410000,x
 beq SourceDefaultInitIdle4086_Guard_12
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultInitIdle4086_Guard_12:
.a16
.i16
 lda.l $410002,x
 cmp #$0041
 beq SourceDefaultInitIdle4086_Guard_13
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultInitIdle4086_Guard_13:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Side
 clc
 adc.l SourceDefaultPlayer4086_Life
 clc
 adc.l SourceDefaultPlayer4086_Life
 sta.l SourceDefaultPlayer4086_Core
 lda.l SourceDefaultPlayer4086_Side
 tax
 lda.l $416804,x
 bne SourceDefaultInitIdle4086_Existing
 jmp SourceDefaultInitIdle4086_Needed
SourceDefaultInitIdle4086_Needed:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Slot
 sta.l SourceIdle4086_Slot
 sta.l SourceAnimationInit4086_Slot
 lda #0
 sta.l SourceAnimationInit4086_Number
 sta.l SourceAnimationInit4086_Reset
 jsl SourceAnimationInit4086_Resolve
 bcc SourceDefaultInitIdle4086_Present
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultInitIdle4086_Present:
.a16
.i16
 lda.l SourceAnimationInit4086_Handle
 beq SourceDefaultInitIdle4086_Absent
 lda.l SourceAnimationInit4086_Count
 bne SourceDefaultInitIdle4086_Prepare
SourceDefaultInitIdle4086_Absent:
.a16
.i16
 ; This capability requires a nonempty idle. Missing idle needs a separate
 ; source no-animation continuation, never an invented frame-zero service.
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultInitIdle4086_Prepare:
.a16
.i16
 jsl SourceIdle4086_Prepare
 bcc SourceDefaultInitIdle4086_Begin
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultInitIdle4086_Begin:
.a16
.i16
 jsl SourceAnimationInit4086_Begin
 bcc SourceDefaultInitIdle4086_Pending
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultInitIdle4086_Pending:
.a16
.i16
 lda.l SourceAnimationInit4086_State
 cmp #1
 beq SourceDefaultInitIdle4086_Issued
 jmp SourceDefaultInitIdle4086_Existing
SourceDefaultInitIdle4086_Issued:
.a16
.i16
 lda #2
 sta.l SourceDefaultPlayer4086_Status
 lda #1
 ply
 plx
 plp
 clc
 rtl
SourceDefaultInitIdle4086_Existing:
.a16
.i16
 lda #2
 sta.l SourceDefaultPlayer4086_Status
 lda #0
 ply
 plx
 plp
 clc
 rtl

; Generic current TYPE_NONE branch, with no valid source walk animation.
; Caller supplies compiler-derived walk number in AnimationInit.Number.
; Requires current B4FB model state and the checked animation cache.
; A walk-capable model explicitly requires the separate walk service.
SourceDefaultNone4086_ApplyNoWalk:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceDefaultPlayer4086_Ready
 cmp #$B503
 beq SourceDefaultNone4086_Guard_1
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNone4086_Guard_1:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Status
 cmp #3
 bne SourceDefaultNone4086_Guard_2
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNone4086_Guard_2:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceDefaultNone4086_Guard_3
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNone4086_Guard_3:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 beq SourceDefaultNone4086_Guard_4
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNone4086_Guard_4:
.a16
.i16
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 beq SourceDefaultNone4086_Guard_5
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNone4086_Guard_5:
.a16
.i16
 lda.l VmSourceWorld_Count
 bne SourceDefaultNone4086_Guard_6
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNone4086_Guard_6:
.a16
.i16
 cmp #129
 bcc SourceDefaultNone4086_Guard_7
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNone4086_Guard_7:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Slot
 cmp.l VmSourceWorld_Count
 bcc SourceDefaultNone4086_Guard_8
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNone4086_Guard_8:
.a16
.i16
 lda.l SourceLifecycle4086_Ready
 cmp #$B4FB
 beq SourceDefaultNone4086_Guard_9
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNone4086_Guard_9:
.a16
.i16
 lda.l SourceLifecycle4086_Status
 cmp #3
 bne SourceDefaultNone4086_Guard_10
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNone4086_Guard_10:
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
 beq SourceDefaultNone4086_Guard_11
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNone4086_Guard_11:
.a16
.i16
 lda.l $410002,x
 cmp #$0041
 beq SourceDefaultNone4086_Guard_12
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNone4086_Guard_12:
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
 beq SourceDefaultNone4086_Guard_13
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNone4086_Guard_13:
.a16
.i16
 lda.l $439048,x
 cmp.l SourceDefaultPlayer4086_Action
 beq SourceDefaultNone4086_Guard_14
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNone4086_Guard_14:
.a16
.i16
 lda.l VmSourceWorld_Level
 bne SourceDefaultNone4086_CoreLease
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNone4086_CoreLease:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Ready
 cmp #$B4EB
 beq SourceDefaultNone4086_CoreCount
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNone4086_CoreCount:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Entities
 cmp.l VmSourceWorld_Count
 beq SourceDefaultNone4086_Core
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNone4086_Core:
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
 lda.l $40C048,x
 ora.l $40C04A,x
 beq SourceDefaultNone4086_Walk
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNone4086_Walk:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Slot
 sta.l SourceAnimationInit4086_Slot
 lda #0
 sta.l SourceAnimationInit4086_Reset
 jsl SourceAnimationInit4086_Resolve
 bcc SourceDefaultNone4086_CheckWalk
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNone4086_CheckWalk:
.a16
.i16
 lda.l SourceAnimationInit4086_Handle
 beq SourceDefaultNone4086_Apply
 lda.l SourceAnimationInit4086_Count
 beq SourceDefaultNone4086_Apply
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNone4086_Apply:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Life
 tax
 lda #1
 sta.l $439010,x
 lda #0
 sta.l $439012,x
 lda.l SourceDefaultPlayer4086_Core
 tax
 lda.l $40C016,x
 bpl SourceDefaultNone4086_Adjust
 lda #1
 sta.l $40C014,x
 lda #0
 sta.l $40C016,x
SourceDefaultNone4086_Adjust:
.a16
.i16
 lda.l $40C026,x
 bpl SourceDefaultNone4086_Speed
 lda #1
 sta.l $40C024,x
 lda #0
 sta.l $40C026,x
SourceDefaultNone4086_Speed:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Side
 tax
 lda #0
 sta.l $416820,x
 lda #2
 sta.l $416822,x
 lda #2
 sta.l SourceDefaultPlayer4086_Status
 ply
 plx
 plp
 clc
 rtl

; DEFAULT_WALK_ONLY: compiler proves max_walks=1 for the closed registry.
; Entity walkmode int32 is lifecycle +44 (calloc zero, retained on model copy).
; Caller supplies derived default WALK in AnimationInit.Number. A is only a
; pending-frame service flag; common_walk_anim return is unused by default init.
SourceWalk4086_BeginDefaultOnly:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceDefaultPlayer4086_Ready
 cmp #$B503
 beq SourceWalkDefault4086_Guard_1
 jmp SourceDefaultPlayer4086_Bad
SourceWalkDefault4086_Guard_1:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Status
 cmp #3
 bne SourceWalkDefault4086_Guard_2
 jmp SourceDefaultPlayer4086_Bad
SourceWalkDefault4086_Guard_2:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceWalkDefault4086_Guard_3
 jmp SourceDefaultPlayer4086_Bad
SourceWalkDefault4086_Guard_3:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 beq SourceWalkDefault4086_Guard_4
 jmp SourceDefaultPlayer4086_Bad
SourceWalkDefault4086_Guard_4:
.a16
.i16
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 beq SourceWalkDefault4086_Guard_5
 jmp SourceDefaultPlayer4086_Bad
SourceWalkDefault4086_Guard_5:
.a16
.i16
 lda.l VmSourceWorld_Count
 bne SourceWalkDefault4086_Guard_6
 jmp SourceDefaultPlayer4086_Bad
SourceWalkDefault4086_Guard_6:
.a16
.i16
 cmp #129
 bcc SourceWalkDefault4086_Guard_7
 jmp SourceDefaultPlayer4086_Bad
SourceWalkDefault4086_Guard_7:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Slot
 cmp.l VmSourceWorld_Count
 bcc SourceWalkDefault4086_Guard_8
 jmp SourceDefaultPlayer4086_Bad
SourceWalkDefault4086_Guard_8:
.a16
.i16
 lda.l SourceLifecycle4086_Ready
 cmp #$B4FB
 beq SourceWalkDefault4086_Guard_9
 jmp SourceDefaultPlayer4086_Bad
SourceWalkDefault4086_Guard_9:
.a16
.i16
 lda.l SourceLifecycle4086_Status
 cmp #3
 bne SourceWalkDefault4086_Guard_10
 jmp SourceDefaultPlayer4086_Bad
SourceWalkDefault4086_Guard_10:
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
 beq SourceWalkDefault4086_Guard_11
 jmp SourceDefaultPlayer4086_Bad
SourceWalkDefault4086_Guard_11:
.a16
.i16
 lda.l $410002,x
 cmp #$0041
 beq SourceWalkDefault4086_Guard_12
 jmp SourceDefaultPlayer4086_Bad
SourceWalkDefault4086_Guard_12:
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
 beq SourceWalkDefault4086_Guard_13
 jmp SourceDefaultPlayer4086_Bad
SourceWalkDefault4086_Guard_13:
.a16
.i16
 lda.l $439048,x
 cmp.l SourceDefaultPlayer4086_Action
 beq SourceWalkDefault4086_Guard_14
 jmp SourceDefaultPlayer4086_Bad
SourceWalkDefault4086_Guard_14:
.a16
.i16
 lda.l $43902E,x
 beq SourceWalkDefault4086_Mode
 jmp SourceDefaultPlayer4086_Bad
SourceWalkDefault4086_Mode:
.a16
.i16
 lda.l $43902C,x
 cmp #2
 bcc SourceWalkDefault4086_Resolve
 jmp SourceDefaultPlayer4086_Bad
SourceWalkDefault4086_Resolve:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Slot
 sta.l SourceAnimationInit4086_Slot
 lda #0
 sta.l SourceAnimationInit4086_Reset
 jsl SourceAnimationInit4086_Resolve
 bcc SourceWalkDefault4086_Present
 jmp SourceDefaultPlayer4086_Bad
SourceWalkDefault4086_Present:
.a16
.i16
 lda.l SourceAnimationInit4086_Handle
 beq SourceWalkDefault4086_NoPending
 lda.l SourceAnimationInit4086_Count
 beq SourceWalkDefault4086_NoPending
 jsl SourceAnimationInit4086_Begin
 bcc SourceWalkDefault4086_CheckPending
 jmp SourceDefaultPlayer4086_Bad
SourceWalkDefault4086_CheckPending:
.a16
.i16
 lda.l SourceAnimationInit4086_State
 cmp #1
 bne SourceWalkDefault4086_NoPending
 lda #2
 sta.l SourceDefaultPlayer4086_Status
 lda #1
 ply
 plx
 plp
 clc
 rtl
SourceWalkDefault4086_NoPending:
.a16
.i16
 lda #2
 sta.l SourceDefaultPlayer4086_Status
 lda #0
 ply
 plx
 plp
 clc
 rtl

; Current TYPE_NONE walk setup, before common_walk_anim executes frame zero.
; Current modeldata speed is the side +60 Q16 compatibility field, refreshed
; by model copy and source speed property writes. Never substitutes a cached
; original model speed. Caller supplies compiler-derived WALK number.
SourceDefaultNone4086_PrepareWalk:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceDefaultPlayer4086_Ready
 cmp #$B503
 beq SourceDefaultNoneWalk4086_Guard_1
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNoneWalk4086_Guard_1:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Status
 cmp #3
 bne SourceDefaultNoneWalk4086_Guard_2
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNoneWalk4086_Guard_2:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceDefaultNoneWalk4086_Guard_3
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNoneWalk4086_Guard_3:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 beq SourceDefaultNoneWalk4086_Guard_4
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNoneWalk4086_Guard_4:
.a16
.i16
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 beq SourceDefaultNoneWalk4086_Guard_5
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNoneWalk4086_Guard_5:
.a16
.i16
 lda.l VmSourceWorld_Count
 bne SourceDefaultNoneWalk4086_Guard_6
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNoneWalk4086_Guard_6:
.a16
.i16
 cmp #129
 bcc SourceDefaultNoneWalk4086_Guard_7
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNoneWalk4086_Guard_7:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Slot
 cmp.l VmSourceWorld_Count
 bcc SourceDefaultNoneWalk4086_Guard_8
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNoneWalk4086_Guard_8:
.a16
.i16
 lda.l SourceLifecycle4086_Ready
 cmp #$B4FB
 beq SourceDefaultNoneWalk4086_Guard_9
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNoneWalk4086_Guard_9:
.a16
.i16
 lda.l SourceLifecycle4086_Status
 cmp #3
 bne SourceDefaultNoneWalk4086_Guard_10
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNoneWalk4086_Guard_10:
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
 beq SourceDefaultNoneWalk4086_Guard_11
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNoneWalk4086_Guard_11:
.a16
.i16
 lda.l $410002,x
 cmp #$0041
 beq SourceDefaultNoneWalk4086_Guard_12
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNoneWalk4086_Guard_12:
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
 beq SourceDefaultNoneWalk4086_Guard_13
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNoneWalk4086_Guard_13:
.a16
.i16
 lda.l $439048,x
 cmp.l SourceDefaultPlayer4086_Action
 beq SourceDefaultNoneWalk4086_Guard_14
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNoneWalk4086_Guard_14:
.a16
.i16
 lda.l VmSourceWorld_Level
 bne SourceDefaultNoneWalk4086_CoreLease
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNoneWalk4086_CoreLease:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Ready
 cmp #$B4EB
 beq SourceDefaultNoneWalk4086_CoreCount
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNoneWalk4086_CoreCount:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Entities
 cmp.l VmSourceWorld_Count
 beq SourceDefaultNoneWalk4086_Core
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNoneWalk4086_Core:
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
 lda.l $40C048,x
 ora.l $40C04A,x
 beq SourceDefaultNoneWalk4086_Walk
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNoneWalk4086_Walk:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Slot
 sta.l SourceAnimationInit4086_Slot
 lda #0
 sta.l SourceAnimationInit4086_Reset
 jsl SourceAnimationInit4086_Resolve
 bcc SourceDefaultNoneWalk4086_CheckWalk
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNoneWalk4086_CheckWalk:
.a16
.i16
 lda.l SourceAnimationInit4086_Handle
 beq SourceDefaultNoneWalk4086_Reject
 lda.l SourceAnimationInit4086_Count
 bne SourceDefaultNoneWalk4086_Mode
SourceDefaultNoneWalk4086_Reject:
.a16
.i16
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultNoneWalk4086_Mode:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Life
 tax
 lda.l $43902E,x
 bne SourceDefaultNoneWalk4086_Reject
 lda.l $43902C,x
 cmp #2
 bcs SourceDefaultNoneWalk4086_Reject
 lda.l SourceDefaultPlayer4086_Life
 clc
 adc #$4000
 tax
 lda.l $410018,x
 cmp #1
 bne SourceDefaultNoneWalk4086_Reject
 lda.l $41001A,x
 bne SourceDefaultNoneWalk4086_Reject
 lda.l $41001E,x
 bne SourceDefaultNoneWalk4086_Negative
 lda.l $41001C,x
 cmp #1
 bne SourceDefaultNoneWalk4086_Negative
 lda #1
 bra SourceDefaultNoneWalk4086_Direction
SourceDefaultNoneWalk4086_Negative:
.a16
.i16
 lda #0
SourceDefaultNoneWalk4086_Direction:
.a16
.i16
 sta.l SourceDefaultPlayer4086_Action
 lda.l SourceDefaultPlayer4086_Side
 tax
 lda.l $41683C,x
 sta.l SourceDefaultPlayer4086_InvLo
 lda.l $41683E,x
 sta.l SourceDefaultPlayer4086_InvHi
 lda.l SourceDefaultPlayer4086_Action
 bne SourceDefaultNoneWalk4086_Apply
 lda.l SourceDefaultPlayer4086_InvHi
 cmp #$8000
 bne SourceDefaultNoneWalk4086_Negate
 lda.l SourceDefaultPlayer4086_InvLo
 beq SourceDefaultNoneWalk4086_Reject
SourceDefaultNoneWalk4086_Negate:
.a16
.i16
 lda.l SourceDefaultPlayer4086_InvLo
 eor #$FFFF
 clc
 adc #1
 sta.l SourceDefaultPlayer4086_InvLo
 lda.l SourceDefaultPlayer4086_InvHi
 eor #$FFFF
 adc #0
 sta.l SourceDefaultPlayer4086_InvHi
SourceDefaultNoneWalk4086_Apply:

.a16
.i16
 lda.l SourceDefaultPlayer4086_Life
 tax
 lda #1
 sta.l $439010,x
 lda #0
 sta.l $439012,x
 lda.l SourceDefaultPlayer4086_Core
 tax
 lda.l $40C016,x
 bpl SourceDefaultNoneWalk4086_Adjust
 lda #1
 sta.l $40C014,x
 lda #0
 sta.l $40C016,x
SourceDefaultNoneWalk4086_Adjust:
.a16
.i16
 lda.l $40C026,x
 bpl SourceDefaultNoneWalk4086_Velocity
 lda #1
 sta.l $40C024,x
 lda #0
 sta.l $40C026,x
SourceDefaultNoneWalk4086_Velocity:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Life
 tax
 lda #15
 sta.l $439000,x
 lda #0
 sta.l $439002,x
 lda.l SourceDefaultPlayer4086_Side
 tax
 lda.l SourceDefaultPlayer4086_InvLo
 sta.l $416824,x
 lda.l SourceDefaultPlayer4086_InvHi
 sta.l $416826,x
 lda #2
 sta.l SourceDefaultPlayer4086_Status
 ply
 plx
 plp
 clc
 rtl
