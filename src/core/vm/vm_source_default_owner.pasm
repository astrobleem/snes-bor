; Closed generic ent_default_init continuation for TYPE_NONE/PLAYER/normal
; ENEMY/NPC and an empty platform/wall environment. Semantic callback IDs
; remain separate from executable AI. No source identity dispatch.
; These six bytes are inside the existing 528-byte frame snapshot, in gaps
; after ModelEntityCopy and AnimationInit, never B503 synchronous scratch.
SourceDefaultInit4086_Phase = $7FFC8C ; 0 idle,1 first,2 player,3 enemy,4 walk,5 idle,6 done,7 fault
SourceDefaultInit4086_OwnerSlot = $7FFC8E
SourceDefaultInit4086_Walk = $7FFCBA

; Begin: A=derived default WALK ID; B4FA slot/select/time/role inputs;
; B503 time/JUMP inputs; X/Y immutable current-stage B5DC context.
; Continue: caller republishes B503 time/JUMP and current-stage X/Y after
; every asynchronous frame service. Owner republishes the saved actor slot.
; Return A=1 means actual B4EC frame zero must run; A=0 means complete.
; Caller executes StartFrame, full callback/effect owners, then Continue.
; Begin/Continue do not implicitly run or acknowledge an unfinished frame.
SourceDefaultInit4086_Begin:
.a16
.i16
 php
 rep #$38
 phx
 phy
 pha
 lda.l SourceDefaultInit4086_Phase
 bne SourceDefaultOwner4086_Far_1
 jmp SourceDefaultOwner4086_BeginIdle
SourceDefaultOwner4086_Far_1:
.a16
.i16
 cmp #6
 bne SourceDefaultOwner4086_Far_2
 jmp SourceDefaultOwner4086_BeginIdle
SourceDefaultOwner4086_Far_2:
.a16
.i16
 pla
 jmp SourceDefaultOwner4086_Bad
SourceDefaultOwner4086_BeginIdle:
.a16
.i16
 jsl SourceAnimationInit4086_CheckIdle
 bcc SourceDefaultOwner4086_Far_3
 jmp SourceDefaultOwner4086_BeginBad
SourceDefaultOwner4086_Far_3:
.a16
.i16
 jsl SourceUpdateFrame4086_CheckIdle
 bcc SourceDefaultOwner4086_Far_4
 jmp SourceDefaultOwner4086_BeginBad
SourceDefaultOwner4086_Far_4:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Ready
 cmp #$B503
 beq SourceDefaultOwner4086_Far_5
 jmp SourceDefaultOwner4086_BeginBad
SourceDefaultOwner4086_Far_5:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Status
 cmp #3
 bne SourceDefaultOwner4086_Far_6
 jmp SourceDefaultOwner4086_BeginBad
SourceDefaultOwner4086_Far_6:
.a16
.i16
 pla
 cmp #1025
 bcc SourceDefaultOwner4086_Far_7
 jmp SourceDefaultOwner4086_Bad
SourceDefaultOwner4086_Far_7:
.a16
.i16
 sta.l SourceDefaultInit4086_Walk
 lda.l SourceDefaultChoice4086_Slot
 sta.l SourceDefaultInit4086_OwnerSlot
 sta.l SourceDefaultPlayer4086_Slot
 jsl SourceDefaultChoice4086_Begin
 bcc SourceDefaultOwner4086_Far_8
 jmp SourceDefaultOwner4086_Bad
SourceDefaultOwner4086_Far_8:
.a16
.i16
 lda.l SourceDefaultChoice4086_Service
 bne SourceDefaultOwner4086_Far_9
 jmp SourceDefaultOwner4086_Dispatch
SourceDefaultOwner4086_Far_9:
.a16
.i16
 lda #1
 sta.l SourceDefaultInit4086_Phase
 jmp SourceDefaultOwner4086_Pending
SourceDefaultOwner4086_BeginBad:
.a16
.i16
 pla
 jmp SourceDefaultOwner4086_Bad

SourceDefaultInit4086_Continue:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceDefaultInit4086_Phase
 bne SourceDefaultOwner4086_Far_10
 jmp SourceDefaultOwner4086_Bad
SourceDefaultOwner4086_Far_10:
.a16
.i16
 cmp #6
 bcc SourceDefaultOwner4086_Far_11
 jmp SourceDefaultOwner4086_Bad
SourceDefaultOwner4086_Far_11:
.a16
.i16
 lda.l SourceDefaultInit4086_OwnerSlot
 cmp.l SourceAnimationInit4086_Slot
 beq SourceDefaultOwner4086_Far_12
 jmp SourceDefaultOwner4086_Bad
SourceDefaultOwner4086_Far_12:
.a16
.i16
 sta.l SourceDefaultPlayer4086_Slot
 jsl SourceUpdateFrame4086_CheckIdle
 bcc SourceDefaultOwner4086_FrameRetired
 jmp SourceDefaultOwner4086_Bad
SourceDefaultOwner4086_FrameRetired:
.a16
.i16
 jsl SourceAnimationInit4086_Ack
 bcc SourceDefaultOwner4086_Far_13
 jmp SourceDefaultOwner4086_Bad
SourceDefaultOwner4086_Far_13:
.a16
.i16
 lda.l SourceDefaultInit4086_Phase
 cmp #1
 bne SourceDefaultOwner4086_Far_14
 jmp SourceDefaultOwner4086_Dispatch
SourceDefaultOwner4086_Far_14:
.a16
.i16
 cmp #2
 bne SourceDefaultOwner4086_Far_15
 jmp SourceDefaultOwner4086_PlayerInv
SourceDefaultOwner4086_Far_15:
.a16
.i16
 cmp #5
 bne SourceDefaultOwner4086_Far_16
 jmp SourceDefaultOwner4086_Tail
SourceDefaultOwner4086_Far_16:
.a16
.i16
 jmp SourceDefaultOwner4086_Idle

SourceDefaultOwner4086_Dispatch:
.a16
.i16
 lda.l VmSourceWorld_Level
 bne SourceDefaultOwner4086_Far_17
 jmp SourceDefaultOwner4086_Idle
SourceDefaultOwner4086_Far_17:
.a16
.i16
 jsl SourceDefaultInit4086_CheckCurrent
 bcc SourceDefaultOwner4086_Far_18
 jmp SourceDefaultOwner4086_Bad
SourceDefaultOwner4086_Far_18:
.a16
.i16
 ; Check full 32-bit TYPE before selecting a source switch case. Selection
 ; after initial frame zero is fresh; later callbacks do not reselect it.
 jsr SourceDefaultOwner4086_Type
 bcc SourceDefaultOwner4086_TypeGood
 jmp SourceDefaultOwner4086_Bad
SourceDefaultOwner4086_TypeGood:
.a16
.i16
 bne SourceDefaultOwner4086_Far_20
 jmp SourceDefaultOwner4086_None
SourceDefaultOwner4086_Far_20:
.a16
.i16
 cmp #1
 bne SourceDefaultOwner4086_Far_21
 jmp SourceDefaultOwner4086_Player
SourceDefaultOwner4086_Far_21:
.a16
.i16
 cmp #2
 bne SourceDefaultOwner4086_Far_22
 jmp SourceDefaultOwner4086_Enemy
SourceDefaultOwner4086_Far_22:
.a16
.i16
 cmp #512
 bne SourceDefaultOwner4086_Far_23
 jmp SourceDefaultOwner4086_Enemy
SourceDefaultOwner4086_Far_23:
.a16
.i16
 jmp SourceDefaultOwner4086_Bad
SourceDefaultOwner4086_Player:
.a16
.i16
 jsl SourceDefaultPlayer4086_BeginAction
 bcc SourceDefaultOwner4086_Far_24
 jmp SourceDefaultOwner4086_Bad
SourceDefaultOwner4086_Far_24:
.a16
.i16
 cmp #0
 bne SourceDefaultOwner4086_Far_25
 jmp SourceDefaultOwner4086_PlayerInv
SourceDefaultOwner4086_Far_25:
.a16
.i16
 lda #2
 sta.l SourceDefaultInit4086_Phase
 jmp SourceDefaultOwner4086_Pending
SourceDefaultOwner4086_PlayerInv:
.a16
.i16
 jsl SourceDefaultPlayer4086_ApplyInvincibility
 bcc SourceDefaultOwner4086_Far_26
 jmp SourceDefaultOwner4086_Bad
SourceDefaultOwner4086_Far_26:
.a16
.i16
 jmp SourceDefaultOwner4086_Idle
SourceDefaultOwner4086_Enemy:
.a16
.i16
 jsl SourceDefaultEnemy4086_PrepareNormal
 bcc SourceDefaultOwner4086_Far_27
 jmp SourceDefaultOwner4086_Bad
SourceDefaultOwner4086_Far_27:
.a16
.i16
 cmp #0
 bne SourceDefaultOwner4086_Far_28
 jmp SourceDefaultOwner4086_Idle
SourceDefaultOwner4086_Far_28:
.a16
.i16
 jsl SourceDefaultEnemy4086_BeginHorizontalDrop
 bcc SourceDefaultOwner4086_Far_29
 jmp SourceDefaultOwner4086_Bad
SourceDefaultOwner4086_Far_29:
.a16
.i16
 cmp #0
 bne SourceDefaultOwner4086_Far_30
 jmp SourceDefaultOwner4086_Idle
SourceDefaultOwner4086_Far_30:
.a16
.i16
 lda #3
 sta.l SourceDefaultInit4086_Phase
 jmp SourceDefaultOwner4086_Pending
SourceDefaultOwner4086_None:
.a16
.i16
 lda.l SourceDefaultInit4086_OwnerSlot
 sta.l SourceAnimationInit4086_Slot
 lda.l SourceDefaultInit4086_Walk
 sta.l SourceAnimationInit4086_Number
 lda #0
 sta.l SourceAnimationInit4086_Reset
 jsl SourceAnimationInit4086_Resolve
 bcc SourceDefaultOwner4086_Far_31
 jmp SourceDefaultOwner4086_Bad
SourceDefaultOwner4086_Far_31:
.a16
.i16
 lda.l SourceAnimationInit4086_Handle
 bne SourceDefaultOwner4086_Far_32
 jmp SourceDefaultOwner4086_NoWalk
SourceDefaultOwner4086_Far_32:
.a16
.i16
 lda.l SourceAnimationInit4086_Count
 bne SourceDefaultOwner4086_Far_33
 jmp SourceDefaultOwner4086_NoWalk
SourceDefaultOwner4086_Far_33:
.a16
.i16
 jsl SourceDefaultNone4086_PrepareWalk
 bcc SourceDefaultOwner4086_Far_34
 jmp SourceDefaultOwner4086_Bad
SourceDefaultOwner4086_Far_34:
.a16
.i16
 jsl SourceWalk4086_BeginDefaultOnly
 bcc SourceDefaultOwner4086_Far_35
 jmp SourceDefaultOwner4086_Bad
SourceDefaultOwner4086_Far_35:
.a16
.i16
 cmp #0
 bne SourceDefaultOwner4086_Far_36
 jmp SourceDefaultOwner4086_Idle
SourceDefaultOwner4086_Far_36:
.a16
.i16
 lda #4
 sta.l SourceDefaultInit4086_Phase
 jmp SourceDefaultOwner4086_Pending
SourceDefaultOwner4086_NoWalk:
.a16
.i16
 jsl SourceDefaultNone4086_ApplyNoWalk
 bcc SourceDefaultOwner4086_Far_37
 jmp SourceDefaultOwner4086_Bad
SourceDefaultOwner4086_Far_37:
.a16
.i16
SourceDefaultOwner4086_Idle:
.a16
.i16
 lda.l SourceDefaultInit4086_OwnerSlot
 sta.l SourceDefaultPlayer4086_Slot
 jsl SourceDefaultInit4086_BeginIdle
 bcc SourceDefaultOwner4086_Far_38
 jmp SourceDefaultOwner4086_Bad
SourceDefaultOwner4086_Far_38:
.a16
.i16
 cmp #0
 bne SourceDefaultOwner4086_Far_39
 jmp SourceDefaultOwner4086_Tail
SourceDefaultOwner4086_Far_39:
.a16
.i16
 lda #5
 sta.l SourceDefaultInit4086_Phase
 jmp SourceDefaultOwner4086_Pending
SourceDefaultOwner4086_Tail:
.a16
.i16
 lda.l VmSourceWorld_Level
 bne SourceDefaultOwner4086_Far_40
 jmp SourceDefaultOwner4086_Complete
SourceDefaultOwner4086_Far_40:
.a16
.i16
 jsl SourceDefaultInit4086_FinalizeEmpty
 bcc SourceDefaultOwner4086_Far_41
 jmp SourceDefaultOwner4086_Bad
SourceDefaultOwner4086_Far_41:
.a16
.i16
SourceDefaultOwner4086_Complete:
.a16
.i16
 lda #6
 sta.l SourceDefaultInit4086_Phase
 lda #0
 bra SourceDefaultOwner4086_Return
SourceDefaultOwner4086_Pending:
.a16
.i16
 lda #1
SourceDefaultOwner4086_Return:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
SourceDefaultOwner4086_Bad:
.a16
.i16
 lda #7
 sta.l SourceDefaultInit4086_Phase
 lda #3
 sta.l SourceDefaultPlayer4086_Status
 ply
 plx
 plp
 sec
 rtl

; Keep the current-stage context registers intact across TYPE dispatch.
SourceDefaultOwner4086_Type:
.a16
.i16
 phx
 lda.l SourceDefaultPlayer4086_Core
 tax
 lda.l $40C04A,x
 beq SourceDefaultOwner4086_TypeLow
 plx
 sec
 rts
SourceDefaultOwner4086_TypeLow:
.a16
.i16
 lda.l $40C048,x
 plx
 ora #0
 clc
 rts
