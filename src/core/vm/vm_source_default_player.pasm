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
