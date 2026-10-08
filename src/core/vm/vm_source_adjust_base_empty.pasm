; B620 closed no-hole/basemap/platform/wall source world. Native adjust_base
; uses actual current B4PH frame BASE/Y and Q16 instance altbase. No gravity,
; no freeze gate: source adjusts base before checking freeze. Atomic on overflow.
SourceAdjustBaseEmpty4086_Ready = $41FF50
SourceAdjustBaseEmpty4086_Status = $41FF52
SourceAdjustBaseEmpty4086_View = $41FF54
SourceAdjustBaseEmpty4086_Side = $41FF56
SourceAdjustBaseEmpty4086_Aux = $41FF58
SourceAdjustBaseEmpty4086_Mark = $41FF5A
SourceAdjustBaseEmpty4086_Due = $41FF5C
SourceAdjustBaseEmpty4086_Core = $41FF5E
SourceAdjustBaseEmpty4086_X = $41FF60
SourceAdjustBaseEmpty4086_Z = $41FF64
SourceAdjustBaseEmpty4086_End = $41FF68
SourceAdjustBaseEmpty4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceAdjustBaseEmpty4086_Ready
 cmp #$B620
 beq SourceAdjustBaseEmpty4086_Guard1
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_Guard1:
.a16
.i16
 lda.l SourceAdjustBaseEmpty4086_Status
 cmp #0
 beq SourceAdjustBaseEmpty4086_Guard2
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_Guard2:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceAdjustBaseEmpty4086_Guard3
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_Guard3:
.a16
.i16
 lda.l SourceWorldTick4086_Ready
 cmp #$B4D5
 beq SourceAdjustBaseEmpty4086_Guard4
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_Guard4:
.a16
.i16
 lda.l SourceWorldTick4086_State
 cmp #1
 beq SourceAdjustBaseEmpty4086_Guard5
 cmp #2 ; actual arrange_ents POST_UPDATE owner
 beq SourceAdjustBaseEmpty4086_Guard5
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_Guard5:
.a16
.i16
 lda.l SourceWorldTick4086_Phase
 cmp #11
 beq SourceAdjustBaseEmpty4086_Guard6
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_Guard6:
.a16
.i16
 lda.l SourceWorldTick4086_Pending
 cmp #1
 beq SourceAdjustBaseEmpty4086_Guard7
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_Guard7:
.a16
.i16
 lda.l SourceWorldTick4086_Fault
 cmp #0
 beq SourceAdjustBaseEmpty4086_Guard8
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_Guard8:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 beq SourceAdjustBaseEmpty4086_Guard9
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_Guard9:
.a16
.i16
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 beq SourceAdjustBaseEmpty4086_Guard10
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_Guard10:
.a16
.i16
 lda.l SourceUpdateFrame4086_Ready
 cmp #$B4E3
 beq SourceAdjustBaseEmpty4086_Guard11
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_Guard11:
.a16
.i16
 lda.l SourceFreeze4086_Ready
 cmp #$B5DF
 beq SourceAdjustBaseEmpty4086_FreezeLease
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_FreezeLease:
.a16
.i16
 lda.l SourceLifecycle4086_Ready
 cmp #$B4FB
 beq SourceAdjustBaseEmpty4086_Guard12
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_Guard12:
.a16
.i16
 lda.l SourceSelf4086_Ready
 cmp #$B4F6
 beq SourceAdjustBaseEmpty4086_Guard13
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_Guard13:
.a16
.i16
 lda.l SourceSelf4086_Active
 cmp #0
 beq SourceAdjustBaseEmpty4086_Guard14
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_Guard14:
.a16
.i16
 lda.l SourceSelf4086_Fault
 cmp #0
 beq SourceAdjustBaseEmpty4086_Guard15
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_Guard15:
.a16
.i16
 lda.l SourceWorldTick4086_TimeLo
 cmp.l VmSourceWorld_Time
 beq SourceAdjustBaseEmpty4086_Guard16
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_Guard16:
.a16
.i16
 lda.l SourceWorldTick4086_TimeLo+2
 cmp.l VmSourceWorld_Time+2
 beq SourceAdjustBaseEmpty4086_Guard17
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_Guard17:
.a16
.i16
 lda.l VmSourceWorld_Count
 cmp #129
 bcc SourceAdjustBaseEmpty4086_Guard18
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_Guard18:
.a16
.i16
 lda.l SourceWorldTick4086_Slot
 cmp.l VmSourceWorld_Count
 bcc SourceAdjustBaseEmpty4086_Guard19
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_Guard19:
.a16
.i16
 asl a
 asl a
 sta.l SourceAdjustBaseEmpty4086_Aux
 asl a
 asl a
 clc
 adc.l SourceAdjustBaseEmpty4086_Aux
 sta.l SourceAdjustBaseEmpty4086_Aux
 lda.l SourceWorldTick4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l SourceAdjustBaseEmpty4086_Mark
 asl a
 sta.l SourceAdjustBaseEmpty4086_Side
 lsr a
 lsr a
 clc
 adc.l SourceAdjustBaseEmpty4086_Side
 sta.l SourceAdjustBaseEmpty4086_View
 adc #$4000
 cmp.l SourceSelf4086_GlobalLow
 beq SourceAdjustBaseEmpty4086_Guard20
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_Guard20:
.a16
.i16
 lda.l SourceSelf4086_GlobalHigh
 cmp #$41
 beq SourceAdjustBaseEmpty4086_Guard21
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_Guard21:
.a16
.i16
 lda.l SourceAdjustBaseEmpty4086_View
 tax
 lda.l SOURCE_WORLD_POOL,x
 clc
 adc #0
 cmp.l SourceSelf4086_GlobalLow
 beq SourceAdjustBaseEmpty4086_Guard22
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_Guard22:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+2,x
 cmp #$41
 beq SourceAdjustBaseEmpty4086_Guard23
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_Guard23:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+4,x
 ora.l SOURCE_WORLD_POOL+6,x
 bne SourceAdjustBaseEmpty4086_Guard24
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_Guard24:
.a16
.i16
 lda.l SourceAdjustBaseEmpty4086_Mark
 lsr a
 lsr a
 clc
 adc.l SourceAdjustBaseEmpty4086_Mark
 sta.l SourceAdjustBaseEmpty4086_Mark
 tax
 lda.l SOURCE_WORLD_FREEZE+36,x
 and #8
 beq SourceAdjustBaseEmpty4086_First
 jmp SourceAdjustBaseEmpty4086_Done
SourceAdjustBaseEmpty4086_First:
.a16
.i16
 lda.l SourceAdjustBaseEmpty4086_Side
 tax
 lda.l SOURCE_WORLD_SIDES,x
 cmp.l SourceEmptyInitEnvironment4086_Models
 bcc SourceAdjustBaseEmpty4086_ModelRange
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_ModelRange:
.a16
.i16
 pha
 lda.l SourceAdjustBaseEmpty4086_View
 tax
 pla
 cmp.l $439048,x
 beq SourceAdjustBaseEmpty4086_ModelIdentity
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_ModelIdentity:
.a16
.i16
 lda.l $43904A,x
 cmp #$B4FB
 beq SourceAdjustBaseEmpty4086_ModelLease
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_ModelLease:
.a16
.i16
 jsl SourceEmptyInitEnvironment4086_Query
 bcc SourceAdjustBaseEmpty4086_ExtraGuard1
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_ExtraGuard1:
.a16
.i16
 lda.l SourcePhysicsState4086_Ready
 cmp #$B61C
 beq SourceAdjustBaseEmpty4086_ExtraGuard2
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_ExtraGuard2:
.a16
.i16
 lda.l SourceWorldTick4086_Slot
 asl a
 asl a
 asl a
 asl a
 tax
 lda.l SOURCE_ENTITY_PHYSICS+8,x
 ora.l SOURCE_ENTITY_PHYSICS+10,x
 beq SourceAdjustBaseEmpty4086_ExtraGuard3
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_ExtraGuard3:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Ready
 cmp #$B4EB
 beq SourceAdjustBaseEmpty4086_ExtraGuard4
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_ExtraGuard4:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Entities
 cmp.l VmSourceWorld_Count
 beq SourceAdjustBaseEmpty4086_ExtraGuard5
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_ExtraGuard5:
.a16
.i16
 lda.l SourceWorldTick4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l SourceAdjustBaseEmpty4086_Core
 asl a
 clc
 adc.l SourceAdjustBaseEmpty4086_Core
 sta.l SourceAdjustBaseEmpty4086_Core
 lda.l SourceAdjustBaseEmpty4086_View
 tax
 lda.l SOURCE_WORLD_POOL+8,x
 cmp #BOR_VT_DECIMAL
 beq SourceAdjustBaseEmpty4086_ExtraGuard6
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_ExtraGuard6:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+10,x
 beq SourceAdjustBaseEmpty4086_ExtraGuard7
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_ExtraGuard7:
.a16
.i16
 lda.l SourceAnimationPhysics4086_Ready
 cmp #$B61F
 beq SourceAdjustBaseEmpty4086_ExtraGuard8
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_ExtraGuard8:
.a16
.i16
 lda.l SourceAdjustBaseEmpty4086_Side
 tax
 lda.l SOURCE_WORLD_SIDES+4,x
 sta.l SourceAnimationPhysics4086_Handle
 lda.l SOURCE_WORLD_SIDES+6,x
 sta.l SourceAnimationPhysics4086_Frame
 lda #0
 sta.l SourceAnimationPhysics4086_Status
 jsl SourceAnimationPhysics4086_Query
 bcc SourceAdjustBaseEmpty4086_ExtraGuard9
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_ExtraGuard9:
.a16
.i16
 lda.l SourceAdjustBaseEmpty4086_Side
 tax
 lda.l SOURCE_WORLD_SIDES+48,x
 sta.l SourceAdjustBaseEmpty4086_X
 lda.l SOURCE_WORLD_SIDES+50,x
 sta.l SourceAdjustBaseEmpty4086_X+2
 lda #0
 sta.l SourceAdjustBaseEmpty4086_Due
 lda.l SourceAdjustBaseEmpty4086_Core
 tax
 lda.l $40C026,x
 bmi SourceAdjustBaseEmpty4086_Adjust
 ora.l $40C024,x
 beq SourceAdjustBaseEmpty4086_Adjust
 jmp SourceAdjustBaseEmpty4086_Publish
SourceAdjustBaseEmpty4086_Adjust:
.a16
.i16
 lda.l SourceAdjustBaseEmpty4086_X
 bne SourceAdjustBaseEmpty4086_FrameBase
 lda.l SourceAdjustBaseEmpty4086_X+2
 cmp #$FC18
 bne SourceAdjustBaseEmpty4086_FrameBase
 lda.l $40C012,x
 bmi SourceAdjustBaseEmpty4086_FrameBase
 ora.l $40C010,x
 beq SourceAdjustBaseEmpty4086_FrameBase
 lda.l SourceAdjustBaseEmpty4086_View
 tax
 lda.l SOURCE_WORLD_POOL+14,x
 bmi SourceAdjustBaseEmpty4086_Stop
 lda #0
 sta.l SourceAdjustBaseEmpty4086_X
 sta.l SourceAdjustBaseEmpty4086_X+2
 bra SourceAdjustBaseEmpty4086_FrameBase
SourceAdjustBaseEmpty4086_Stop:
.a16
.i16
 lda #1
 sta.l SourceAdjustBaseEmpty4086_Due
 jmp SourceAdjustBaseEmpty4086_Publish
SourceAdjustBaseEmpty4086_FrameBase:
.a16
.i16
 lda.l SourceAdjustBaseEmpty4086_X
 bne SourceAdjustBaseEmpty4086_NonPit
 lda.l SourceAdjustBaseEmpty4086_X+2
 cmp #$FC18
 bne SourceAdjustBaseEmpty4086_NonPit
 jmp SourceAdjustBaseEmpty4086_Publish
SourceAdjustBaseEmpty4086_NonPit:
.a16
.i16
 lda.l SourceAnimationPhysics4086_FrameBase+2
 bmi SourceAdjustBaseEmpty4086_NegativeFrameBase
 cmp #0
 beq SourceAdjustBaseEmpty4086_ExtraGuard10
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_ExtraGuard10:
.a16
.i16
 lda.l SourceAnimationPhysics4086_FrameBase
 cmp #$8000
 bcc SourceAdjustBaseEmpty4086_ExtraGuard11
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_ExtraGuard11:
.a16
.i16
 cmp #0
 beq SourceAdjustBaseEmpty4086_NegativeFrameBase
 sta.l SourceAdjustBaseEmpty4086_Z+2
 lda.l SourceAdjustBaseEmpty4086_Aux
 tax
 lda.l SOURCE_UPDATE_FRAME_AUX+8,x
 sta.l SourceAdjustBaseEmpty4086_Z
 lda.l SOURCE_UPDATE_FRAME_AUX+10,x
 clc
 adc.l SourceAdjustBaseEmpty4086_Z+2
 bvc SourceAdjustBaseEmpty4086_ExtraGuard12
 jmp SourceAdjustBaseEmpty4086_Bad
SourceAdjustBaseEmpty4086_ExtraGuard12:
.a16
.i16
 sta.l SourceAdjustBaseEmpty4086_Z+2
 bmi SourceAdjustBaseEmpty4086_ClipBase
 lda.l SourceAdjustBaseEmpty4086_Z
 sta.l SourceAdjustBaseEmpty4086_X
 lda.l SourceAdjustBaseEmpty4086_Z+2
 sta.l SourceAdjustBaseEmpty4086_X+2
 bra SourceAdjustBaseEmpty4086_Publish
SourceAdjustBaseEmpty4086_ClipBase:
.a16
.i16
 lda #0
 sta.l SourceAdjustBaseEmpty4086_X
 sta.l SourceAdjustBaseEmpty4086_X+2
 bra SourceAdjustBaseEmpty4086_Publish
SourceAdjustBaseEmpty4086_NegativeFrameBase:
.a16
.i16
 lda.l SourceAnimationPhysics4086_FrameY
 ora.l SourceAnimationPhysics4086_FrameY+2
 bne SourceAdjustBaseEmpty4086_Publish
 lda #0
 sta.l SourceAdjustBaseEmpty4086_X
 sta.l SourceAdjustBaseEmpty4086_X+2
SourceAdjustBaseEmpty4086_Publish:
.a16
.i16
 lda.l SourceAdjustBaseEmpty4086_Side
 tax
 lda.l SourceAdjustBaseEmpty4086_X
 sta.l SOURCE_WORLD_SIDES+48,x
 lda.l SourceAdjustBaseEmpty4086_X+2
 sta.l SOURCE_WORLD_SIDES+50,x
 lda.l SourceAdjustBaseEmpty4086_Due
 beq SourceAdjustBaseEmpty4086_Done
 lda #0
 sta.l SOURCE_WORLD_SIDES+36,x
 sta.l SOURCE_WORLD_SIDES+38,x
 sta.l SOURCE_WORLD_SIDES+40,x
 sta.l SOURCE_WORLD_SIDES+42,x
SourceAdjustBaseEmpty4086_Done:
.a16
.i16
 lda #2
 sta.l SourceAdjustBaseEmpty4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceAdjustBaseEmpty4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceAdjustBaseEmpty4086_Status
 ply
 plx
 plp
 sec
 rtl

; Optional source POST subservice after its owner binds the selected self.
SourceAdjustBaseEmpty4086_RunPost:
.a16
.i16
 lda.l SourceAdjustBaseEmpty4086_Ready
 beq SourceAdjustBaseEmpty4086_PostDisabled
 cmp #$B620
 bne SourceAdjustBaseEmpty4086_PostBad
 lda.l SourceAdjustBaseEmpty4086_Status
 beq SourceAdjustBaseEmpty4086_PostReady
 cmp #2
 bne SourceAdjustBaseEmpty4086_PostBad
SourceAdjustBaseEmpty4086_PostReady:
.a16
.i16
 lda #0
 sta.l SourceAdjustBaseEmpty4086_Status
 jsl SourceAdjustBaseEmpty4086_Execute
 rtl
SourceAdjustBaseEmpty4086_PostDisabled:
.a16
.i16
 clc
 rtl
SourceAdjustBaseEmpty4086_PostBad:
.a16
.i16
 sec
 rtl
