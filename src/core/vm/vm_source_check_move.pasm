; Generic check_move direct branch under ACCEPTED_COMPAT_Q16_16.
; B617 owns no-platform/null-trymove admission; compiler revokes on mutations.
; Phase11 movement subservice only. Gravity/binding/post-update Ack are separate.
; Checked two-axis publication, real freeze query, no position wrap.
SourceCheckMove4086_Ready = $40BFC8
SourceCheckMove4086_Status = $40BFCA
SourceCheckMove4086_View = $40BFCC
SourceCheckMove4086_Side = $40BFCE
SourceCheckMove4086_Aux = $40BFD0
SourceCheckMove4086_Mark = $40BFD2
SourceCheckMove4086_Due = $40BFD4
SourceCheckMove4086_Axis = $40BFD6
SourceCheckMove4086_X = $40BFD8
SourceCheckMove4086_Z = $40BFDC
SourceCheckMove4086_End = $40BFE0
SourceCheckMove4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceCheckMove4086_Ready
 cmp #$B617
 beq SourceCheckMove4086_Guard1
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard1:
.a16
.i16
 lda.l SourceCheckMove4086_Status
 cmp #0
 beq SourceCheckMove4086_Guard2
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard2:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceCheckMove4086_Guard3
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard3:
.a16
.i16
 lda.l SourceWorldTick4086_Ready
 cmp #$B4D5
 beq SourceCheckMove4086_Guard4
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard4:
.a16
.i16
 lda.l SourceWorldTick4086_State
 cmp #1
 beq SourceCheckMove4086_Guard5
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard5:
.a16
.i16
 lda.l SourceWorldTick4086_Phase
 cmp #11
 beq SourceCheckMove4086_Guard6
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard6:
.a16
.i16
 lda.l SourceWorldTick4086_Pending
 cmp #1
 beq SourceCheckMove4086_Guard7
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard7:
.a16
.i16
 lda.l SourceWorldTick4086_Fault
 cmp #0
 beq SourceCheckMove4086_Guard8
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard8:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 beq SourceCheckMove4086_Guard9
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard9:
.a16
.i16
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 beq SourceCheckMove4086_Guard10
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard10:
.a16
.i16
 lda.l SourceUpdateFrame4086_Ready
 cmp #$B4E3
 beq SourceCheckMove4086_Guard11
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard11:
.a16
.i16
 lda.l SourceFreeze4086_Ready
 cmp #$B5DF
 beq SourceCheckMove4086_FreezeLease
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_FreezeLease:
.a16
.i16
 lda.l SourceLifecycle4086_Ready
 cmp #$B4FB
 beq SourceCheckMove4086_Guard12
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard12:
.a16
.i16
 lda.l SourceSelf4086_Ready
 cmp #$B4F6
 beq SourceCheckMove4086_Guard13
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard13:
.a16
.i16
 lda.l SourceSelf4086_Active
 cmp #0
 beq SourceCheckMove4086_Guard14
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard14:
.a16
.i16
 lda.l SourceSelf4086_Fault
 cmp #0
 beq SourceCheckMove4086_Guard15
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard15:
.a16
.i16
 lda.l SourceWorldTick4086_TimeLo
 cmp.l VmSourceWorld_Time
 beq SourceCheckMove4086_Guard16
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard16:
.a16
.i16
 lda.l SourceWorldTick4086_TimeLo+2
 cmp.l VmSourceWorld_Time+2
 beq SourceCheckMove4086_Guard17
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard17:
.a16
.i16
 lda.l VmSourceWorld_Count
 cmp #129
 bcc SourceCheckMove4086_Guard18
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard18:
.a16
.i16
 lda.l SourceWorldTick4086_Slot
 cmp.l VmSourceWorld_Count
 bcc SourceCheckMove4086_Guard19
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard19:
.a16
.i16
 asl a
 asl a
 sta.l SourceCheckMove4086_Aux
 asl a
 asl a
 clc
 adc.l SourceCheckMove4086_Aux
 sta.l SourceCheckMove4086_Aux
 lda.l SourceWorldTick4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l SourceCheckMove4086_Mark
 asl a
 sta.l SourceCheckMove4086_Side
 lsr a
 lsr a
 clc
 adc.l SourceCheckMove4086_Side
 sta.l SourceCheckMove4086_View
 adc #$4000
 cmp.l SourceSelf4086_GlobalLow
 beq SourceCheckMove4086_Guard20
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard20:
.a16
.i16
 lda.l SourceSelf4086_GlobalHigh
 cmp #$41
 beq SourceCheckMove4086_Guard21
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard21:
.a16
.i16
 lda.l SourceCheckMove4086_View
 tax
 lda.l SOURCE_WORLD_POOL,x
 clc
 adc #0
 cmp.l SourceSelf4086_GlobalLow
 beq SourceCheckMove4086_Guard22
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard22:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+2,x
 cmp #$41
 beq SourceCheckMove4086_Guard23
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard23:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+4,x
 ora.l SOURCE_WORLD_POOL+6,x
 bne SourceCheckMove4086_Guard24
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard24:
.a16
.i16
 lda.l SourceCheckMove4086_Mark
 lsr a
 lsr a
 clc
 adc.l SourceCheckMove4086_Mark
 sta.l SourceCheckMove4086_Mark
 tax
 lda.l SOURCE_WORLD_FREEZE+36,x
 and #4
 beq SourceCheckMove4086_First
 jmp SourceCheckMove4086_Done
SourceCheckMove4086_First:
.a16
.i16
 lda.l SourceCheckMove4086_Side
 tax
 lda.l SOURCE_WORLD_SIDES,x
 cmp.l SourceEmptyInitEnvironment4086_Models
 bcc SourceCheckMove4086_ModelRange
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_ModelRange:
.a16
.i16
 pha
 lda.l SourceCheckMove4086_View
 tax
 pla
 cmp.l $439048,x
 beq SourceCheckMove4086_ModelIdentity
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_ModelIdentity:
.a16
.i16
 lda.l $43904A,x
 cmp #$B4FB
 beq SourceCheckMove4086_ModelLease
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_ModelLease:
.a16
.i16
 jsl SourceEmptyInitEnvironment4086_Query
 bcc SourceCheckMove4086_Guard25
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard25:
.a16
.i16
 jsl SourceFreeze4086_Query
 bcc SourceCheckMove4086_Guard26
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard26:
.a16
.i16
 pha
 lda #0
 sta.l SourceCheckMove4086_Due
 sta.l SourceCheckMove4086_X
 sta.l SourceCheckMove4086_X+2
 sta.l SourceCheckMove4086_Z
 sta.l SourceCheckMove4086_Z+2
 ; Query result is restored to A before zeroing the staging outputs.
 pla
 beq SourceCheckMove4086_Timer
 jmp SourceCheckMove4086_ValidatePositions
SourceCheckMove4086_Timer:
.a16
.i16
 lda.l SourceCheckMove4086_Side
 tax
 lda.l SOURCE_WORLD_SIDES+26,x
 cmp.l VmSourceWorld_Time+2
 bcc SourceCheckMove4086_IsDue
 beq SourceCheckMove4086_TimerLow
 jmp SourceCheckMove4086_ValidatePositions
SourceCheckMove4086_TimerLow:
.a16
.i16
 lda.l SOURCE_WORLD_SIDES+24,x
 cmp.l VmSourceWorld_Time
 bcc SourceCheckMove4086_IsDue
 beq SourceCheckMove4086_IsDue
 jmp SourceCheckMove4086_ValidatePositions
SourceCheckMove4086_IsDue:
.a16
.i16
 lda #1
 sta.l SourceCheckMove4086_Due
 lda.l SourceCheckMove4086_Aux
 tax
 lda.l SOURCE_UPDATE_FRAME_AUX,x
 sta.l SourceCheckMove4086_X
 lda.l SOURCE_UPDATE_FRAME_AUX+2,x
 sta.l SourceCheckMove4086_X+2
 lda.l SOURCE_UPDATE_FRAME_AUX+4,x
 sta.l SourceCheckMove4086_Z
 lda.l SOURCE_UPDATE_FRAME_AUX+6,x
 sta.l SourceCheckMove4086_Z+2
 ora.l SourceCheckMove4086_X
 ora.l SourceCheckMove4086_X+2
 ora.l SourceCheckMove4086_Z
 beq SourceCheckMove4086_ValidatePositions
 lda.l SourceCheckMove4086_View
 tax
 lda.l $43904A,x
 cmp #$B4FB
 beq SourceCheckMove4086_Guard27
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard27:
.a16
.i16
 lda.l $439004,x
 ora.l $439006,x
 beq SourceCheckMove4086_Guard28
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard28:
.a16
.i16
SourceCheckMove4086_ValidatePositions:
.a16
.i16
 lda.l SourceCheckMove4086_View
 tax
 lda.l SOURCE_WORLD_POOL+48,x
 cmp #BOR_VT_DECIMAL
 beq SourceCheckMove4086_Guard29
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard29:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+50,x
 beq SourceCheckMove4086_Guard30
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard30:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+56,x
 cmp #BOR_VT_DECIMAL
 beq SourceCheckMove4086_Guard31
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard31:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+58,x
 beq SourceCheckMove4086_Guard32
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard32:
.a16
.i16
 clc
 lda.l SOURCE_WORLD_POOL+52,x
 adc.l SourceCheckMove4086_X
 sta.l SourceCheckMove4086_X
 lda.l SOURCE_WORLD_POOL+54,x
 adc.l SourceCheckMove4086_X+2

 bvc SourceCheckMove4086_Guard33
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard33:
.a16
.i16
 sta.l SourceCheckMove4086_X+2
 clc
 lda.l SOURCE_WORLD_POOL+60,x
 adc.l SourceCheckMove4086_Z
 sta.l SourceCheckMove4086_Z
 lda.l SOURCE_WORLD_POOL+62,x
 adc.l SourceCheckMove4086_Z+2

 bvc SourceCheckMove4086_Guard34
 jmp SourceCheckMove4086_Bad
SourceCheckMove4086_Guard34:
.a16
.i16
 sta.l SourceCheckMove4086_Z+2
 lda.l SourceCheckMove4086_X
 sta.l SOURCE_WORLD_POOL+52,x
 lda.l SourceCheckMove4086_X+2
 sta.l SOURCE_WORLD_POOL+54,x
 lda.l SourceCheckMove4086_Z
 sta.l SOURCE_WORLD_POOL+60,x
 lda.l SourceCheckMove4086_Z+2
 sta.l SOURCE_WORLD_POOL+62,x
 lda.l SourceCheckMove4086_Due
 beq SourceCheckMove4086_ZeroDisplacement
 lda.l SourceCheckMove4086_Side
 tax
 clc
 lda.l VmSourceWorld_Time
 adc #1
 sta.l SOURCE_WORLD_SIDES+24,x
 lda.l VmSourceWorld_Time+2
 adc #0
 sta.l SOURCE_WORLD_SIDES+26,x
 bra SourceCheckMove4086_MarkMoved
SourceCheckMove4086_ZeroDisplacement:
.a16
.i16
 lda.l SourceCheckMove4086_Aux
 tax
 lda #0
 sta.l SOURCE_UPDATE_FRAME_AUX,x
 sta.l SOURCE_UPDATE_FRAME_AUX+2,x
 sta.l SOURCE_UPDATE_FRAME_AUX+4,x
 sta.l SOURCE_UPDATE_FRAME_AUX+6,x
SourceCheckMove4086_MarkMoved:
.a16
.i16
 lda.l SourceCheckMove4086_Mark
 tax
 lda.l SOURCE_WORLD_FREEZE+36,x
 ora #4
 sta.l SOURCE_WORLD_FREEZE+36,x
SourceCheckMove4086_Done:
.a16
.i16
 lda #2
 sta.l SourceCheckMove4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceCheckMove4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceCheckMove4086_Status
 ply
 plx
 plp
 sec
 rtl
