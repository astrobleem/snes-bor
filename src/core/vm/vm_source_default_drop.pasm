; Synchronous default-init current-entity guard. A out current TYPE low; callers dispatch over the full current TYPE.
; Caller republishes B503 slot after every nested/asynchronous service.
SourceDefaultInit4086_CheckCurrent:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceDefaultPlayer4086_Ready
 cmp #$B503
 beq SourceDefaultCurrent4086_Guard_1
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultCurrent4086_Guard_1:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Status
 cmp #3
 bne SourceDefaultCurrent4086_Guard_2
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultCurrent4086_Guard_2:
.a16
.i16
 jsl SourceAnimationInit4086_CheckIdle
 bcc SourceDefaultCurrent4086_AnimationIdle
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultCurrent4086_AnimationIdle:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceDefaultCurrent4086_Guard_3
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultCurrent4086_Guard_3:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 beq SourceDefaultCurrent4086_Guard_4
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultCurrent4086_Guard_4:
.a16
.i16
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 beq SourceDefaultCurrent4086_Guard_5
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultCurrent4086_Guard_5:
.a16
.i16
 lda.l VmSourceWorld_Count
 bne SourceDefaultCurrent4086_Guard_6
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultCurrent4086_Guard_6:
.a16
.i16
 cmp #129
 bcc SourceDefaultCurrent4086_Guard_7
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultCurrent4086_Guard_7:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Slot
 cmp.l VmSourceWorld_Count
 bcc SourceDefaultCurrent4086_Guard_8
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultCurrent4086_Guard_8:
.a16
.i16
 lda.l SourceLifecycle4086_Ready
 cmp #$B4FB
 beq SourceDefaultCurrent4086_Guard_9
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultCurrent4086_Guard_9:
.a16
.i16
 lda.l SourceLifecycle4086_Status
 cmp #3
 bne SourceDefaultCurrent4086_Guard_10
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultCurrent4086_Guard_10:
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
 beq SourceDefaultCurrent4086_Guard_11
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultCurrent4086_Guard_11:
.a16
.i16
 lda.l $410002,x
 cmp #$0041
 beq SourceDefaultCurrent4086_Guard_12
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultCurrent4086_Guard_12:
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
 beq SourceDefaultCurrent4086_Guard_13
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultCurrent4086_Guard_13:
.a16
.i16
 lda.l $439048,x
 cmp.l SourceDefaultPlayer4086_Action
 beq SourceDefaultCurrent4086_Guard_14
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultCurrent4086_Guard_14:
.a16
.i16
 lda.l VmSourceWorld_Level
 bne SourceDefaultCurrent4086_CoreLease
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultCurrent4086_CoreLease:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Ready
 cmp #$B4EB
 beq SourceDefaultCurrent4086_CoreCount
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultCurrent4086_CoreCount:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Entities
 cmp.l VmSourceWorld_Count
 beq SourceDefaultCurrent4086_Core
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultCurrent4086_Core:
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
 lda.l SourceLifecycle4086_Status
 cmp #3
 bne SourceDefaultCurrent4086_LifeGood
 jmp SourceDefaultPlayer4086_Bad
SourceDefaultCurrent4086_LifeGood:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Core
 tax
 lda.l $40C048,x
 ply
 plx
 plp
 clc
 rtl

; X/Y immutable B5DC context base/bank; B503 slot is caller-owned input.
; A=1 requires one shared RNG draw and the table expression; A=0 skips it.
; This helper never draws RNG or writes an entity. It publishes synchronous
; table base/bank in B503 TimeLo/TimeHi; caller uses these before any yield.
SourceDefaultEnemy4086_ChooseHorizontalDrop:
.a16
.i16
 php
 rep #$38
 phx
 phy
 phb
 jsl SourceDefaultInit4086_CheckCurrent
 bcc SourceHorizontalDrop4086_WideGuard_1
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_1:
.a16
.i16
 cmp #2
 beq SourceHorizontalDrop4086_TypeLowGood
 cmp #512
 beq SourceHorizontalDrop4086_WideGuard_2
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_2:
.a16
.i16
SourceHorizontalDrop4086_TypeLowGood:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Core
 tax
 lda.l $40C04A,x
 beq SourceHorizontalDrop4086_WideGuard_3
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_3:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Life
 tax
 lda.l $439032,x
 bne SourceHorizontalDrop4086_SubtypeGood
 lda.l $439030,x
 cmp #1
 bne SourceHorizontalDrop4086_WideGuard_4
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_4:
.a16
.i16
 cmp #3
 bne SourceHorizontalDrop4086_WideGuard_5
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_5:
.a16
.i16
SourceHorizontalDrop4086_SubtypeGood:
.a16
.i16
 lda.l SourceDefaultPlayer4086_Side
 tax
 lda.l $416800,x
 cmp.l SourceModelEntityCopy4086_Models
 bcc SourceHorizontalDrop4086_ModelGood
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_ModelGood:
.a16
.i16
 lda.l SourceEnvironment4086_Ready
 cmp #$B4D1
 beq SourceHorizontalDrop4086_WideGuard_6
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_6:
.a16
.i16
 lda.l VmSourceWorld_ScrollAxis
 beq SourceHorizontalDrop4086_WideGuard_7
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_7:
.a16
.i16
 ; Restore the input metadata pointer (saved X beneath DBR and Y).
 lda $04,s
 tax
 cpx #$8000
 bcs SourceHorizontalDrop4086_WideGuard_8
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_8:
.a16
.i16
 cpx #$FFE1
 bcc SourceHorizontalDrop4086_WideGuard_9
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_9:
.a16
.i16
 tya
 bne SourceHorizontalDrop4086_WideGuard_10
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_10:
.a16
.i16
 cmp #64
 bcc SourceHorizontalDrop4086_WideGuard_11
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_11:
.a16
.i16
 sep #$20
.a8
 pha
 plb
 rep #$20
.a16
 lda.w $0000,x
 cmp #$3542
 beq SourceHorizontalDrop4086_WideGuard_12
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_12:
.a16
.i16
 lda.w $0002,x
 cmp #$4344
 beq SourceHorizontalDrop4086_WideGuard_13
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_13:
.a16
.i16
 lda.w $0004,x
 cmp #1
 beq SourceHorizontalDrop4086_WideGuard_14
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_14:
.a16
.i16
 lda.w $0006,x
 cmp #32
 beq SourceHorizontalDrop4086_WideGuard_15
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_15:
.a16
.i16
 lda.w $0008,x
 bne SourceHorizontalDrop4086_WideGuard_16
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_16:
.a16
.i16
 cmp.l SourceEnvironment4086_Stage
 beq SourceHorizontalDrop4086_WideGuard_17
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_17:
.a16
.i16
 lda.w $000A,x
 ora.w $0016,x
 beq SourceHorizontalDrop4086_WideGuard_18
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_18:
.a16
.i16
 lda.w $0012,x
 cmp.l SourceModelEntityCopy4086_Models
 beq SourceHorizontalDrop4086_WideGuard_19
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_19:
.a16
.i16
 cmp.l VmSourceWorld_TemplateCount
 beq SourceHorizontalDrop4086_WideGuard_20
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_20:
.a16
.i16
 lda.w $0014,x
 cmp #40
 beq SourceHorizontalDrop4086_WideGuard_21
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_21:
.a16
.i16
 lda.w $000C,x
 cmp #2
 bcc SourceHorizontalDrop4086_WideGuard_22
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_22:
.a16
.i16
 sta.l SourceDefaultPlayer4086_InvHi
 lda.w $000E,x
 bne SourceHorizontalDrop4086_WideGuard_23
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_23:
.a16
.i16
 cmp #32738
 bcc SourceHorizontalDrop4086_WideGuard_24
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_24:
.a16
.i16
 sta.l SourceDefaultPlayer4086_InvLo
 lda.w $0010,x
 bne SourceHorizontalDrop4086_WideGuard_25
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_25:
.a16
.i16
 cmp #32728
 bcc SourceHorizontalDrop4086_WideGuard_26
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_26:
.a16
.i16
 sta.l SourceDefaultPlayer4086_Action
 lda.w $0018,x
 sta.l SourceDefaultPlayer4086_TimeLo
 lda.w $001A,x
 sta.l SourceDefaultPlayer4086_TimeHi
 lda #0
 pha
 lda.l SourceDefaultPlayer4086_TimeLo
 tax
 lda.l SourceDefaultPlayer4086_TimeHi
 tay
 pla
 jsl SourceRandomFloat4086_LookupU24
 bcc SourceHorizontalDrop4086_WideGuard_27
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_27:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Lo
 beq SourceHorizontalDrop4086_WideGuard_28
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_28:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Hi
 cmp.l SourceDefaultPlayer4086_Action
 beq SourceHorizontalDrop4086_WideGuard_29
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_29:
.a16
.i16
 ; Exact property tags: source positions are DECIMAL Q16 in this ABI.
 lda.l SourceDefaultPlayer4086_Life
 clc
 adc #$4000
 tax
 lda.l $410008,x
 cmp #2
 beq SourceHorizontalDrop4086_WideGuard_30
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_30:
.a16
.i16
 lda.l $41000A,x
 beq SourceHorizontalDrop4086_WideGuard_31
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_31:
.a16
.i16
 lda.l $410030,x
 cmp #2
 beq SourceHorizontalDrop4086_WideGuard_32
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_32:
.a16
.i16
 lda.l $410032,x
 beq SourceHorizontalDrop4086_WideGuard_33
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_33:
.a16
.i16
 lda.l SourceDefaultPlayer4086_InvHi
 beq SourceHorizontalDrop4086_SkipGuard_1
 jmp SourceHorizontalDrop4086_NoDraw
SourceHorizontalDrop4086_SkipGuard_1:
.a16
.i16
 lda.l $41000C,x
 ora.l $41000E,x
 beq SourceHorizontalDrop4086_SkipGuard_2
 jmp SourceHorizontalDrop4086_NoDraw
SourceHorizontalDrop4086_SkipGuard_2:
.a16
.i16
 ; Source advancex is an integer; explicitly reject a fractional camera.
 lda.l VmSourceWorld_AdvanceX
 beq SourceHorizontalDrop4086_WideGuard_34
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_34:
.a16
.i16
 lda.l VmSourceWorld_AdvanceX+2
 cmp #$8000
 bcc SourceHorizontalDrop4086_CameraPositive
 cmp #$801E
 bcs SourceHorizontalDrop4086_WideGuard_35
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_35:
.a16
.i16
 bra SourceHorizontalDrop4086_CameraBound
SourceHorizontalDrop4086_CameraPositive:
.a16
.i16
 sta.l SourceDefaultPlayer4086_Action
 lda #32767
 sec
 sbc.l SourceDefaultPlayer4086_InvLo
 sec
 sbc #30
 cmp.l SourceDefaultPlayer4086_Action
 bcs SourceHorizontalDrop4086_WideGuard_36
 jmp SourceHorizontalDrop4086_Bad
SourceHorizontalDrop4086_WideGuard_36:
.a16
.i16
SourceHorizontalDrop4086_CameraBound:
.a16
.i16
 lda.l VmSourceWorld_AdvanceX+2
 sec
 sbc #30
 eor #$8000
 sta.l SourceDefaultPlayer4086_Action
 lda.l $410036,x
 eor #$8000
 cmp.l SourceDefaultPlayer4086_Action
 bcs SourceHorizontalDrop4086_SkipGuard_3
 jmp SourceHorizontalDrop4086_NoDraw
SourceHorizontalDrop4086_SkipGuard_3:
.a16
.i16
 bne SourceHorizontalDrop4086_RightBound
 lda.l $410034,x
 bne SourceHorizontalDrop4086_SkipGuard_4
 jmp SourceHorizontalDrop4086_NoDraw
SourceHorizontalDrop4086_SkipGuard_4:
.a16
.i16
SourceHorizontalDrop4086_RightBound:
.a16
.i16
 lda.l VmSourceWorld_AdvanceX+2
 clc
 adc.l SourceDefaultPlayer4086_InvLo
 clc
 adc #30
 eor #$8000
 sta.l SourceDefaultPlayer4086_Action
 lda.l $410036,x
 eor #$8000
 cmp.l SourceDefaultPlayer4086_Action
 bcc SourceHorizontalDrop4086_SkipGuard_5
 jmp SourceHorizontalDrop4086_NoDraw
SourceHorizontalDrop4086_SkipGuard_5:
.a16
.i16
 lda #1
 bra SourceHorizontalDrop4086_Good
SourceHorizontalDrop4086_NoDraw:
.a16
.i16
 lda #0
SourceHorizontalDrop4086_Good:
.a16
.i16
 pha
 lda #2
 sta.l SourceDefaultPlayer4086_Status
 pla
 plb
 ply
 plx
 plp
 clc
 rtl
SourceHorizontalDrop4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceDefaultPlayer4086_Status
 plb
 ply
 plx
 plp
 sec
 rtl
