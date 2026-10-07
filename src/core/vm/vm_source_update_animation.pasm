; Source timed update_animation owner; B60F requires installed paired B4AT/B4FE.
; Prefix executes once; FRAME uses the existing captured update_frame owner.
; Caller must execute every pending callback/effect before Continue.
; Textbox action input, onkill events and recursive minion kill remain explicit
; unbound capabilities. No frame, actor-name or palette-specific branch exists.
SourceUpdateAnimation4086_Ready = $40BF2E
SourceUpdateAnimation4086_State = $40BF30 ; 0 idle,1 frame pending,2 done,3 fault
SourceUpdateAnimation4086_Base = $40BF32
SourceUpdateAnimation4086_Bank = $40BF34
SourceUpdateAnimation4086_Bytes = $40BF36
SourceUpdateAnimation4086_Slot = $40BF38
SourceUpdateAnimation4086_Side = $40BF3A
SourceUpdateAnimation4086_Aux = $40BF3C
SourceUpdateAnimation4086_Handle = $40BF3E
SourceUpdateAnimation4086_Action = $40BF40
SourceUpdateAnimation4086_TableEnd = $40BF42
SourceUpdateAnimation4086_Animations = $40BF44
SourceUpdateAnimation4086_Row = $40BF46
SourceUpdateAnimation4086_TimeLo = $40BF48
SourceUpdateAnimation4086_TimeHi = $40BF4A
SourceUpdateAnimation4086_End = $40BF4C

SourceUpdateAnimation4086_Begin:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceUpdateAnimation4086_Ready
 cmp #$B60F
 beq SourceUpdateAnimation4086_Guard1
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard1:
.a16
.i16
 lda.l SourceUpdateAnimation4086_State
 beq SourceUpdateAnimation4086_Start
 cmp #2
 beq SourceUpdateAnimation4086_Guard2
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard2:
.a16
.i16
SourceUpdateAnimation4086_Start:
.a16
.i16
 lda.l SourceWorldTick4086_Ready
 cmp #$B4D5
 beq SourceUpdateAnimation4086_Guard3
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard3:
.a16
.i16
 lda.l SourceWorldTick4086_State
 cmp #1
 beq SourceUpdateAnimation4086_Guard4
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard4:
.a16
.i16
 lda.l SourceWorldTick4086_Pending
 cmp #1
 beq SourceUpdateAnimation4086_Guard5
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard5:
.a16
.i16
 lda.l SourceWorldTick4086_Phase
 cmp #7
 beq SourceUpdateAnimation4086_Guard6
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard6:
.a16
.i16
 lda.l SourceWorldTick4086_TimeLo
 cmp.l VmSourceWorld_Time
 beq SourceUpdateAnimation4086_Guard7
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard7:
.a16
.i16
 sta.l SourceUpdateAnimation4086_TimeLo
 lda.l SourceWorldTick4086_TimeHi
 cmp.l VmSourceWorld_Time+2
 beq SourceUpdateAnimation4086_Guard8
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard8:
.a16
.i16
 sta.l SourceUpdateAnimation4086_TimeHi
 lda.l SourceWorldTick4086_Slot
 sta.l SourceUpdateAnimation4086_Slot
 sta.l SourceUpdateFrame4086_Slot
 ; Current request validates/captures actual geometry without actor writes.
 lda #0
 sta.l SourceUpdateFrame4086_Request
 jsl SourceUpdateFrame4086_Preflight
 bcc SourceUpdateAnimation4086_Guard9
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard9:
.a16
.i16
 lda.l SourceUpdateFrame4086_Side
 cmp.l SourceWorldTick4086_Side
 beq SourceUpdateAnimation4086_Guard10
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard10:
.a16
.i16
 sta.l SourceUpdateAnimation4086_Side
 tax
 lda.l $410006,x
 sta.l SourceAnimation4086_Frame
 lda.l $410008,x
 sta.l SourceAnimation4086_NextLo
 lda.l $41000A,x
 sta.l SourceAnimation4086_NextHi
 lda.l SourceUpdateFrame4086_View
 cmp.l SourceWorldTick4086_View
 beq SourceUpdateAnimation4086_Guard11
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard11:
.a16
.i16
 lda.l SourceUpdateFrame4086_Aux
 sta.l SourceUpdateAnimation4086_Aux
 tax
 lda.l $410010,x
 sta.l SourceAnimation4086_Direction
 lda.l SourceUpdateFrame4086_Handle
 sta.l SourceUpdateAnimation4086_Handle
 lda.l SourceUpdateFrame4086_Count
 sta.l SourceAnimation4086_Count
 lda.l SourceAutokillState4086_Ready
 cmp #$B60E
 beq SourceUpdateAnimation4086_Guard12
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard12:
.a16
.i16
 lda #0
 jsl SourceAutokillState4086_CheckCacheSpan
 bcc SourceUpdateAnimation4086_AutokillLease
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_AutokillLease:
.a16
.i16
 lda.l SourceUpdateAnimation4086_Slot
 asl a
 asl a
 tax
 lda.l SOURCE_ENTITY_AUTOKILL,x
 ora.l SOURCE_ENTITY_AUTOKILL+2,x
 sta.l SourceAnimation4086_Autokill
 lda.l SourceUpdateAnimation4086_TimeLo
 sta.l SourceAnimation4086_TimeLo
 lda.l SourceUpdateAnimation4086_TimeHi
 sta.l SourceAnimation4086_TimeHi
 ; Pointer identity selects the timing row; mutable animnum is not an alias key.
 lda.l SourceUpdateAnimation4086_Base
 cmp #$8000
 bcs SourceUpdateAnimation4086_Guard13
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard13:
.a16
.i16
 lda.l SourceUpdateAnimation4086_Bytes
 cmp #24
 bcs SourceUpdateAnimation4086_Guard14
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard14:
.a16
.i16
 clc
 adc.l SourceUpdateAnimation4086_Base
 bcc SourceUpdateAnimation4086_Guard15
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard15:
.a16
.i16
 sta.l SourceUpdateAnimation4086_TableEnd
 lda.l SourceUpdateAnimation4086_Bank
 cmp #64
 bcc SourceUpdateAnimation4086_Guard16
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard16:
.a16
.i16
 lda.l SourceUpdateAnimation4086_Base
 tax
 jsr SourceUpdateAnimation4086_Read
 cmp #$3442
 beq SourceUpdateAnimation4086_Guard17
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard17:
.a16
.i16
 inx
 inx
 jsr SourceUpdateAnimation4086_Read
 cmp #$5441
 beq SourceUpdateAnimation4086_Guard18
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard18:
.a16
.i16
 inx
 inx
 jsr SourceUpdateAnimation4086_Read
 cmp #1
 beq SourceUpdateAnimation4086_Guard19
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard19:
.a16
.i16
 inx
 inx
 jsr SourceUpdateAnimation4086_Read
 cmp.l SourceUpdateFrame4086_Animations
 beq SourceUpdateAnimation4086_Guard20
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard20:
.a16
.i16
 sta.l SourceUpdateAnimation4086_Animations
 asl a
 asl a
 asl a
 asl a
 clc
 adc #8
 clc
 adc.l SourceUpdateAnimation4086_Base
 bcc SourceUpdateAnimation4086_Guard21
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard21:
.a16
.i16
 cmp.l SourceUpdateAnimation4086_TableEnd
 bcc SourceUpdateAnimation4086_Guard22
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard22:
.a16
.i16
 lda.l SourceUpdateAnimation4086_Handle
 dec a
 asl a
 asl a
 asl a
 asl a
 clc
 adc #8
 clc
 adc.l SourceUpdateAnimation4086_Base
 sta.l SourceUpdateAnimation4086_Row
 tax
 jsr SourceUpdateAnimation4086_Read
 cmp.l SourceUpdateAnimation4086_Handle
 beq SourceUpdateAnimation4086_Guard23
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard23:
.a16
.i16
 inx
 inx ; source role intentionally not compared to mutable actor animnum
 inx
 inx
 jsr SourceUpdateAnimation4086_Read
 cmp.l SourceAnimation4086_Count
 beq SourceUpdateAnimation4086_Guard24
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard24:
.a16
.i16
 inx
 inx
 jsr SourceUpdateAnimation4086_Read
 sta.l SourceAnimation4086_LoopMode
 inx
 inx
 jsr SourceUpdateAnimation4086_Read
 sta.l SourceAnimation4086_LoopMin
 inx
 inx
 jsr SourceUpdateAnimation4086_Read
 sta.l SourceAnimation4086_LoopMax
 inx
 inx ; delay arrays belong to paired update_frame; installer validates pairing
 inx
 inx
 jsr SourceUpdateAnimation4086_Read
 beq SourceUpdateAnimation4086_Guard25
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard25:
.a16
.i16
 lda.l SourceAnimation4086_NextLo
 cmp.l SourceAnimation4086_TimeLo
 bne SourceUpdateAnimation4086_CheckTextbox
 lda.l SourceAnimation4086_NextHi
 cmp.l SourceAnimation4086_TimeHi
 beq SourceUpdateAnimation4086_Decide
SourceUpdateAnimation4086_CheckTextbox:
.a16
.i16
 lda.l SourceUpdateAnimation4086_Slot
 ; slot*96, actual per-entity modeldata.type DWORD
 asl a
 asl a
 asl a
 asl a
 asl a
 pha
 asl a
 clc
 adc 1,s
 tax
 pla
 lda.l $40C048,x
 and #128
 beq SourceUpdateAnimation4086_Decide
 ; Unmatched nextanim with a skippable textbox needs actual bothnewkeys.
 lda.l SourceUpdateFrame4086_View
 sec
 sbc #$4000
 tax
 lda.l $439030,x
 cmp #6
 beq SourceUpdateAnimation4086_Guard26
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard26:
.a16
.i16
 lda.l $439032,x
 beq SourceUpdateAnimation4086_Guard27
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard27:
.a16
.i16
SourceUpdateAnimation4086_Decide:
.a16
.i16
 jsl SourceAnimation4086_Decide
 bcc SourceUpdateAnimation4086_Guard28
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard28:
.a16
.i16
 lda.l SourceAnimation4086_Action
 sta.l SourceUpdateAnimation4086_Action
 cmp #1
 bne SourceUpdateAnimation4086_CheckKill
 lda.l SourceAnimation4086_FrameResult
 sta.l SourceUpdateFrame4086_Request
 jsl SourceUpdateFrame4086_Preflight
 bcc SourceUpdateAnimation4086_Guard29
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard29:
.a16
.i16
 jmp SourceUpdateAnimation4086_Prefix
SourceUpdateAnimation4086_CheckKill:
.a16
.i16
 cmp #3
 bne SourceUpdateAnimation4086_Prefix
 lda.l SourceUpdateAnimation4086_Slot
 sta.l SourceRetirement4086_Slot
 jsl SourceRetirement4086_PreflightNoEvents
 bcc SourceUpdateAnimation4086_Guard30
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard30:
.a16
.i16
SourceUpdateAnimation4086_Prefix:
.a16
.i16
 jsl SourceUpdateAnimationPrefix4086_Execute
 bcc SourceUpdateAnimation4086_Guard31
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard31:
.a16
.i16
 lda.l SourceUpdateAnimation4086_Action
 bne SourceUpdateAnimation4086_HasAction
 jmp SourceUpdateAnimation4086_Done
SourceUpdateAnimation4086_HasAction:
.a16
.i16
 cmp #1
 bne SourceUpdateAnimation4086_StopAction
 jmp SourceUpdateAnimation4086_Frame
SourceUpdateAnimation4086_StopAction:
.a16
.i16
 lda.l SourceUpdateAnimation4086_Aux
 tax
 lda #0
 sta.l $410010,x
 lda.l SourceUpdateAnimation4086_Action
 cmp #3
 beq SourceUpdateAnimation4086_KillAction
 jmp SourceUpdateAnimation4086_Done
SourceUpdateAnimation4086_KillAction:
.a16
.i16
 jsl SourceRetirement4086_ApplyNoEvents
 bcc SourceUpdateAnimation4086_Guard32
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard32:
.a16
.i16
 jmp SourceUpdateAnimation4086_Done
SourceUpdateAnimation4086_Frame:
.a16
.i16
 lda.l SourceUpdateAnimation4086_Slot
 asl a
 asl a
 asl a
 pha
 asl a
 asl a
 clc
 adc 1,s
 tax
 pla
 lda.l $42E024,x
 ora #1
 sta.l $42E024,x
 jsl SourceUpdateFrame4086_Begin
 bcc SourceUpdateAnimation4086_Guard33
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard33:
.a16
.i16
 lda #1
 sta.l SourceUpdateAnimation4086_State
 jmp SourceUpdateAnimation4086_Return

; No repeated prefix/decision/payment. Caller completes actual frame services.
SourceUpdateAnimation4086_Continue:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceUpdateAnimation4086_Ready
 cmp #$B60F
 beq SourceUpdateAnimation4086_Guard34
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard34:
.a16
.i16
 lda.l SourceUpdateAnimation4086_State
 cmp #1
 beq SourceUpdateAnimation4086_Guard35
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard35:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceUpdateAnimation4086_ContinueWorldLease
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_ContinueWorldLease:
.a16
.i16
 lda.l SourceUpdateFrame4086_Ready
 cmp #$B4E3
 beq SourceUpdateAnimation4086_ContinueFrameLease
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_ContinueFrameLease:
.a16
.i16
 lda.l SourceWorldTick4086_Ready
 cmp #$B4D5
 beq SourceUpdateAnimation4086_Guard101
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard101:
.a16
.i16
 lda.l SourceWorldTick4086_State
 cmp #1
 beq SourceUpdateAnimation4086_Guard102
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard102:
.a16
.i16
 lda.l SourceWorldTick4086_Pending
 cmp #1
 beq SourceUpdateAnimation4086_Guard103
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard103:
.a16
.i16
 lda.l SourceWorldTick4086_TimeLo
 cmp.l SourceUpdateAnimation4086_TimeLo
 beq SourceUpdateAnimation4086_Guard104
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard104:
.a16
.i16
 cmp.l VmSourceWorld_Time
 beq SourceUpdateAnimation4086_Guard105
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard105:
.a16
.i16
 lda.l SourceWorldTick4086_TimeHi
 cmp.l SourceUpdateAnimation4086_TimeHi
 beq SourceUpdateAnimation4086_Guard106
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard106:
.a16
.i16
 cmp.l VmSourceWorld_Time+2
 beq SourceUpdateAnimation4086_Guard107
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard107:
.a16
.i16
 lda.l SourceWorldTick4086_Phase
 cmp #7
 beq SourceUpdateAnimation4086_Guard36
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard36:
.a16
.i16
 lda.l SourceWorldTick4086_Slot
 cmp.l SourceUpdateAnimation4086_Slot
 beq SourceUpdateAnimation4086_Guard37
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard37:
.a16
.i16
 lda.l SourceUpdateFrame4086_Slot
 cmp.l SourceUpdateAnimation4086_Slot
 beq SourceUpdateAnimation4086_Guard38
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard38:
.a16
.i16
 lda.l SourceUpdateFrame4086_State
 cmp #2
 beq SourceUpdateAnimation4086_Guard39
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard39:
.a16
.i16
 lda.l SourceUpdateFrame4086_Pending
 beq SourceUpdateAnimation4086_Guard40
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard40:
.a16
.i16
 jsl SourceFrameEffectPlan4086_CheckComplete
 bcc SourceUpdateAnimation4086_ContinuePlanComplete
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_ContinuePlanComplete:
.a16
.i16
 jsl SourceSelf4086_CheckIdle
 bcc SourceUpdateAnimation4086_Guard41
 jmp SourceUpdateAnimation4086_Bad
SourceUpdateAnimation4086_Guard41:
.a16
.i16
SourceUpdateAnimation4086_Done:
.a16
.i16
 lda #2
 sta.l SourceUpdateAnimation4086_State
 lda #0
SourceUpdateAnimation4086_Return:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
SourceUpdateAnimation4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceUpdateAnimation4086_State
 ply
 plx
 plp
 sec
 rtl
SourceUpdateAnimation4086_Read:
.a16
.i16
 phb
 sep #$20
.a8
 lda.l SourceUpdateAnimation4086_Bank
 pha
 plb
 rep #$20
.a16
 lda.w $0000,x
 plb
 ora #0
 rts

; World phase7 cannot retire before timed/frame owner completion. Outside the
; saturated bank28 traversal; disabled ordinary static source path is unchanged.
SourceUpdateAnimation4086_CheckWorldAck:
.a16
.i16
 php
 rep #$38
 pha
 lda.l SourceWorldTick4086_Phase
 cmp #7
 bne SourceUpdateAnimation4086_AckOk
 lda.l SourceUpdateAnimation4086_Ready
 beq SourceUpdateAnimation4086_AckOk
 cmp #$B60F
 bne SourceUpdateAnimation4086_AckBad
 lda.l SourceUpdateAnimation4086_State
 cmp #2
 bne SourceUpdateAnimation4086_AckBad
 lda.l SourceWorldTick4086_Slot
 cmp.l SourceUpdateAnimation4086_Slot
 bne SourceUpdateAnimation4086_AckBad
 lda.l SourceWorldTick4086_TimeLo
 cmp.l SourceUpdateAnimation4086_TimeLo
 bne SourceUpdateAnimation4086_AckBad
 lda.l SourceWorldTick4086_TimeHi
 cmp.l SourceUpdateAnimation4086_TimeHi
 bne SourceUpdateAnimation4086_AckBad
SourceUpdateAnimation4086_AckOk:
.a16
.i16
 pla
 plp
 clc
 rtl
SourceUpdateAnimation4086_AckBad:
.a16
.i16
 pla
 plp
 sec
 rtl

; Fresh phase7 issue invalidates prior actor/tick completion, like SCRIPT/AI.
; Preserve every register/flag; the bank28 caller only supplies its phase.
SourceUpdateAnimation4086_PrimeWorldPhase:
.a16
.i16
 php
 rep #$38
 pha
 lda.l SourceWorldTick4086_Phase
 cmp #7
 bne SourceUpdateAnimation4086_PrimeDone
 lda.l SourceUpdateAnimation4086_Ready
 cmp #$B60F
 bne SourceUpdateAnimation4086_PrimeDone
 lda #0
 sta.l SourceUpdateAnimation4086_State
SourceUpdateAnimation4086_PrimeDone:
.a16
.i16
 pla
 plp
 rtl
