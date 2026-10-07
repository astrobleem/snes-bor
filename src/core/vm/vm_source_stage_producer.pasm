; Source queue-loop owner, not camera/completion/combat execution.
; B5D6 grants source-derived current-stage first/limit and immutable B5SQ.
; Caller applies update_scroller time/freeze prefix before Next and owns final
; completion/player/camera checks. No tick commits while a constructor is pending.
; Next A=1 requests a real constructor, A=0 queue branch done. Ack requires
; actual completed constructor and post-properties (including music ack).
SourceStageProducer4086_Ready = $43BB50
SourceStageProducer4086_State = $43BB52
SourceStageProducer4086_First = $43BB54
SourceStageProducer4086_Limit = $43BB56
SourceStageProducer4086_GroupMin = $43BB58
SourceStageProducer4086_GroupMax = $43BB5C
SourceStageProducer4086_Position = $43BB60
SourceStageProducer4086_Kind = $43BB64
SourceStageProducer4086_RequestIndex = $43BB66
SourceStageProducer4086_Time = $43BB68
SourceStageProducer4086_Completed = $43BB6C
SourceStageProducer4086_Enemies = $43BB6E
SourceStageProducer4086_Waiting = $43BB70
SourceStageProducer4086_GoTime = $43BB72
SourceStageProducer4086_At = $43BB76
SourceStageProducer4086_NewMin = $43BB7A
SourceStageProducer4086_NewMax = $43BB7E
SourceStageProducer4086_End = $43BB82
SourceStageProducer4086_Next:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceStageProducer4086_Ready
 cmp #$B5D6
 beq SourceStageProducer4086_G1
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_G1:
.a16
.i16
 lda.l SourceStageQueue4086_Ready
 cmp #$B5D2
 beq SourceStageProducer4086_G2
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_G2:
.a16
.i16
 lda.l SourceStageProducer4086_First
 cmp.l SourceStageProducer4086_Limit
 bcc SourceStageProducer4086_G3
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_G3:
.a16
.i16
 lda.l SourceStageQueue4086_Records
 cmp.l SourceStageProducer4086_Limit
 bcs SourceStageProducer4086_G4
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_G4:
.a16
.i16
 lda.l SourceStageQueue4086_Index
 cmp.l SourceStageProducer4086_First
 bcs SourceStageProducer4086_G5
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_G5:
.a16
.i16
 lda.l SourceStageProducer4086_Limit
 cmp.l SourceStageQueue4086_Index

 bcs SourceStageProducer4086_G6
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_G6:
.a16
.i16
 lda.l SourceStageProducer4086_Completed
 cmp #2
 bcc SourceStageProducer4086_G7
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_G7:
.a16
.i16
 lda.l SourceStageProducer4086_State
 cmp #2
 beq SourceStageProducer4086_Resume
 cmp #0
 beq SourceStageProducer4086_Begin
 cmp #4
 beq SourceStageProducer4086_Begin
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_Begin:
.a16
.i16
 lda.l VmSourceWorld_Time
 sta.l SourceStageProducer4086_Time
 lda.l VmSourceWorld_Time+2
 sta.l SourceStageProducer4086_Time+2
 lda.l SourceStageProducer4086_Completed
 beq SourceStageProducer4086_NotCompleted
 jmp SourceStageProducer4086_Done
SourceStageProducer4086_NotCompleted:
.a16
.i16
 lda #2
 jsl SourceCountEntities4086_Count

 bcc SourceStageProducer4086_G8
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_G8:
.a16
.i16
 sta.l SourceStageProducer4086_Enemies
 lda.l SourceStageProducer4086_GroupMin+2
 and #$8000
 beq SourceStageProducer4086_G9
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_G9:
.a16
.i16
 lda.l SourceStageProducer4086_GroupMin+2
 bne SourceStageProducer4086_EnterLoop
 lda.l SourceStageProducer4086_GroupMin

 bne SourceStageProducer4086_G10
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_G10:
.a16
.i16
 cmp.l SourceStageProducer4086_Enemies
 beq SourceStageProducer4086_MinDone
 bcc SourceStageProducer4086_MinDone
 bra SourceStageProducer4086_EnterLoop
SourceStageProducer4086_MinDone:
.a16
.i16
 jmp SourceStageProducer4086_Done
SourceStageProducer4086_Resume:
.a16
.i16
 lda.l VmSourceWorld_Time
 cmp.l SourceStageProducer4086_Time
 beq SourceStageProducer4086_G11
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_G11:
.a16
.i16
 lda.l VmSourceWorld_Time+2
 cmp.l SourceStageProducer4086_Time+2
 beq SourceStageProducer4086_G12
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_G12:
.a16
.i16
SourceStageProducer4086_EnterLoop:
.a16
.i16
 lda #2
 sta.l SourceStageProducer4086_State
SourceStageProducer4086_Loop:
.a16
.i16
 lda.l SourceStageQueue4086_Index
 cmp.l SourceStageProducer4086_Limit
 bcc SourceStageProducer4086_HasRow
 jmp SourceStageProducer4086_Done
SourceStageProducer4086_HasRow:
.a16
.i16
 lda #2
 jsl SourceCountEntities4086_Count

 bcc SourceStageProducer4086_G13
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_G13:
.a16
.i16
 sta.l SourceStageProducer4086_Enemies
 lda.l SourceStageProducer4086_GroupMax+2
 and #$8000
 beq SourceStageProducer4086_G14
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_G14:
.a16
.i16
 lda.l SourceStageProducer4086_GroupMax+2
 bne SourceStageProducer4086_BelowMax
 lda.l SourceStageProducer4086_GroupMax

 bne SourceStageProducer4086_G15
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_G15:
.a16
.i16
 cmp.l SourceStageProducer4086_Enemies
 beq SourceStageProducer4086_MaxDone
 bcc SourceStageProducer4086_MaxDone
 bra SourceStageProducer4086_BelowMax
SourceStageProducer4086_MaxDone:
.a16
.i16
 jmp SourceStageProducer4086_Done
SourceStageProducer4086_BelowMax:
.a16
.i16
 jsl SourceStageQueue4086_ValidateCurrentRow

 bcc SourceStageProducer4086_G16
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_G16:
.a16
.i16
 lda #8
 jsr SourceStageQueue4086_ReadRow
 sta.l SourceStageProducer4086_At
 lda #10
 jsr SourceStageQueue4086_ReadRow
 sta.l SourceStageProducer4086_At+2
 eor.l SourceStageProducer4086_Position+2
 bpl SourceStageProducer4086_SameSign
 lda.l SourceStageProducer4086_Position+2
 bpl SourceStageProducer4086_Due
 jmp SourceStageProducer4086_Done
SourceStageProducer4086_SameSign:
.a16
.i16
 lda.l SourceStageProducer4086_Position+2
 cmp.l SourceStageProducer4086_At+2
 beq SourceStageProducer4086_CompareLow
 bcs SourceStageProducer4086_Due
 jmp SourceStageProducer4086_Done
SourceStageProducer4086_CompareLow:
.a16
.i16
 lda.l SourceStageProducer4086_Position
 cmp.l SourceStageProducer4086_At
 bcs SourceStageProducer4086_Due
 jmp SourceStageProducer4086_Done
SourceStageProducer4086_Due:
.a16
.i16
 lda #2
 jsr SourceStageQueue4086_ReadRow
 sta.l SourceStageProducer4086_Kind
 cmp #2
 beq SourceStageProducer4086_Wait
 cmp #3
 beq SourceStageProducer4086_Group
 jmp SourceStageProducer4086_Request
SourceStageProducer4086_Wait:
.a16
.i16
 lda #1
 sta.l SourceStageProducer4086_Waiting
 lda #0
 sta.l SourceStageProducer4086_GoTime
 sta.l SourceStageProducer4086_GoTime+2
 jmp SourceStageProducer4086_Advance
SourceStageProducer4086_Group:
.a16
.i16
 lda #52
 jsr SourceStageQueue4086_ReadRow
 sta.l SourceStageProducer4086_NewMin
 lda #54
 jsr SourceStageQueue4086_ReadRow
 sta.l SourceStageProducer4086_NewMin+2
 lda #56
 jsr SourceStageQueue4086_ReadRow
 sta.l SourceStageProducer4086_NewMax
 lda #58
 jsr SourceStageQueue4086_ReadRow
 sta.l SourceStageProducer4086_NewMax+2
 lda.l SourceStageProducer4086_NewMin+2
 and #$8000
 beq SourceStageProducer4086_G17
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_G17:
.a16
.i16
 lda.l SourceStageProducer4086_NewMin
 ora.l SourceStageProducer4086_NewMin+2
 bne SourceStageProducer4086_G18
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_G18:
.a16
.i16
 lda.l SourceStageProducer4086_NewMin
 sta.l SourceStageProducer4086_GroupMin
 lda.l SourceStageProducer4086_NewMin+2
 sta.l SourceStageProducer4086_GroupMin+2
 lda.l SourceStageProducer4086_NewMax+2
 and #$8000
 beq SourceStageProducer4086_G19
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_G19:
.a16
.i16
 lda.l SourceStageProducer4086_NewMax
 ora.l SourceStageProducer4086_NewMax+2
 bne SourceStageProducer4086_G20
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_G20:
.a16
.i16
 lda.l SourceStageProducer4086_NewMax
 sta.l SourceStageProducer4086_GroupMax
 lda.l SourceStageProducer4086_NewMax+2
 sta.l SourceStageProducer4086_GroupMax+2
SourceStageProducer4086_Advance:
.a16
.i16
 lda.l SourceStageQueue4086_Index
 inc a
 sta.l SourceStageQueue4086_Index
 jmp SourceStageProducer4086_Loop
SourceStageProducer4086_Request:
.a16
.i16
 lda.l SourceCtorOwner4086_Phase
 beq SourceStageProducer4086_CtorIdle
 cmp #2

 beq SourceStageProducer4086_G21
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_G21:
.a16
.i16
SourceStageProducer4086_CtorIdle:
.a16
.i16
 lda.l SourceSmartSpawn4086_Status
 beq SourceStageProducer4086_PropertiesIdle
 cmp #2
 beq SourceStageProducer4086_PropertiesIdle
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_PropertiesIdle:
.a16
.i16
 lda.l SourceStageProducer4086_Kind
 beq SourceStageProducer4086_Empty
 jsl SourceStageQueue4086_PrepareSpawn

 bcc SourceStageProducer4086_G22
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_G22:
.a16
.i16
 lda #0
 sta.l SourceSmartSpawn4086_Status
 bra SourceStageProducer4086_Issue
SourceStageProducer4086_Empty:
.a16
.i16
 lda #$FFFF
 sta.l SourceSpawnSlot4086_Model
SourceStageProducer4086_Issue:
.a16
.i16
 lda.l SourceStageQueue4086_Index
 sta.l SourceStageProducer4086_RequestIndex
 lda #0
 sta.l SourceCtorOwner4086_Phase
 lda #1
 sta.l SourceStageProducer4086_State
 jmp SourceStageProducer4086_Return
SourceStageProducer4086_Done:
.a16
.i16
 lda #4
 sta.l SourceStageProducer4086_State
 lda #0
SourceStageProducer4086_Return:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
SourceStageProducer4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceStageProducer4086_State
 ply
 plx
 plp
 sec
 rtl
SourceStageProducer4086_AckSpawn:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceStageProducer4086_Ready
 cmp #$B5D6
 beq SourceStageProducer4086_G23
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_G23:
.a16
.i16
 lda.l SourceStageProducer4086_State
 cmp #1
 beq SourceStageProducer4086_G24
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_G24:
.a16
.i16
 lda.l SourceStageQueue4086_Index
 cmp.l SourceStageProducer4086_RequestIndex
 beq SourceStageProducer4086_G25
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_G25:
.a16
.i16
 lda.l VmSourceWorld_Time
 cmp.l SourceStageProducer4086_Time
 beq SourceStageProducer4086_G26
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_G26:
.a16
.i16
 lda.l VmSourceWorld_Time+2
 cmp.l SourceStageProducer4086_Time+2
 beq SourceStageProducer4086_G27
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_G27:
.a16
.i16
 jsl SourceCtorOwner4086_Result
 bcc SourceStageProducer4086_G28
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_G28:
.a16
.i16
 lda.l SourceStageProducer4086_Kind
 cmp #2
 bcc SourceStageProducer4086_AckKindValid
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_AckKindValid:
.a16
.i16
 ora #0
 beq SourceStageProducer4086_AckEmpty
 lda.l VmNativeVariant_Result
 cmp #BOR_VT_PTR
 beq SourceStageProducer4086_G29
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_G29:
.a16
.i16
 lda.l SourceCtorOwner4086_Model
 cmp.l SourceStageQueue4086_Model
 beq SourceStageProducer4086_G30
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_G30:
.a16
.i16
 lda.l SourceSmartSpawn4086_Ready
 cmp #$B5D4
 beq SourceStageProducer4086_AckPropertyLease
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_AckPropertyLease:
.a16
.i16
 lda.l SourceSmartSpawn4086_MapModel
 cmp.l SourceCtorOwner4086_Model
 beq SourceStageProducer4086_AckPropertyModel
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_AckPropertyModel:
.a16
.i16
 lda.l SourceSmartSpawn4086_Status
 cmp #2
 beq SourceStageProducer4086_G31
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_G31:
.a16
.i16
 bra SourceStageProducer4086_AckAdvance
SourceStageProducer4086_AckEmpty:
.a16
.i16
 lda.l VmNativeVariant_Result
 ora.l VmNativeVariant_Result+2
 ora.l VmNativeVariant_Result+4
 ora.l VmNativeVariant_Result+6
 beq SourceStageProducer4086_G32
 jmp SourceStageProducer4086_Bad
SourceStageProducer4086_G32:
.a16
.i16
SourceStageProducer4086_AckAdvance:
.a16
.i16
 lda.l SourceStageQueue4086_Index
 inc a
 sta.l SourceStageQueue4086_Index
 lda #2
 sta.l SourceStageProducer4086_State
 lda #0
 jmp SourceStageProducer4086_Return
