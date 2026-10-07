; Source stage completion condition, after admitted scroller prefix.
; Uses actual native type/existence pool and all four source player-role tokens.
; Role checks preserve C's !dead test (no extra exists/type eligibility test).
; A=1 completed, A=0 not completed, C=fault. Never certifies a Demo itself.
SourceStageCompletion4086_Ready = $43BB9A
SourceStageCompletion4086_Status = $43BB9C
SourceStageCompletion4086_LevelType = $43BB9E
SourceStageCompletion4086_RoleCursor = $43BBA2
SourceStageCompletion4086_View = $43BBA4
SourceStageCompletion4086_Live = $43BBA6
SourceStageCompletion4086_Low = $43BBA8
SourceStageCompletion4086_End = $43BBAA
SourceStageCompletion4086_Check:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceStageCompletion4086_Ready
 cmp #$B5D8
 beq SourceStageCompletion4086_G1
 jmp SourceStageCompletion4086_Bad
SourceStageCompletion4086_G1:
.a16
.i16
 lda.l SourceScrollerPrefix4086_Ready
 cmp #$B5D7
 beq SourceStageCompletion4086_G2
 jmp SourceStageCompletion4086_Bad
SourceStageCompletion4086_G2:
.a16
.i16
 lda.l SourceScrollerPrefix4086_State
 cmp #2
 beq SourceStageCompletion4086_G3
 jmp SourceStageCompletion4086_Bad
SourceStageCompletion4086_G3:
.a16
.i16
 lda.l SourceStageProducer4086_Ready
 cmp #$B5D6
 beq SourceStageCompletion4086_G4
 jmp SourceStageCompletion4086_Bad
SourceStageCompletion4086_G4:
.a16
.i16
 lda.l SourceStageProducer4086_State
 beq SourceStageCompletion4086_G5
 jmp SourceStageCompletion4086_Bad
SourceStageCompletion4086_G5:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceStageCompletion4086_G6
 jmp SourceStageCompletion4086_Bad
SourceStageCompletion4086_G6:
.a16
.i16
 lda.l SourceStageQueue4086_Index
 cmp.l SourceStageProducer4086_Limit
 bcs SourceStageCompletion4086_QueueEnd
 jmp SourceStageCompletion4086_NotComplete
SourceStageCompletion4086_QueueEnd:
.a16
.i16
 lda #2
 jsl SourceCountEntities4086_Count

 bcc SourceStageCompletion4086_G7
 jmp SourceStageCompletion4086_Bad
SourceStageCompletion4086_G7:
.a16
.i16
 cmp #0
 beq SourceStageCompletion4086_NoEnemies
 jmp SourceStageCompletion4086_NotComplete
SourceStageCompletion4086_NoEnemies:
.a16
.i16
 lda #0
 sta.l SourceStageCompletion4086_RoleCursor
 sta.l SourceStageCompletion4086_Live
SourceStageCompletion4086_RoleLoop:
.a16
.i16
 lda.l SourceStageCompletion4086_RoleCursor
 tax
 lda.l $43FD84,x
 sta.l SourceStageCompletion4086_Low
 ora.l $43FD86,x
 beq SourceStageCompletion4086_NextRole
 lda.l $43FD86,x
 cmp #$41
 beq SourceStageCompletion4086_G8
 jmp SourceStageCompletion4086_Bad
SourceStageCompletion4086_G8:
.a16
.i16
 lda.l SourceStageCompletion4086_Low
 cmp #$4000
 bcs SourceStageCompletion4086_G9
 jmp SourceStageCompletion4086_Bad
SourceStageCompletion4086_G9:
.a16
.i16
 cmp #$6800
 bcc SourceStageCompletion4086_G10
 jmp SourceStageCompletion4086_Bad
SourceStageCompletion4086_G10:
.a16
.i16
 sec
 sbc #$4000
 sta.l SourceStageCompletion4086_View
 ldx #0
SourceStageCompletion4086_Divide:
.a16
.i16
 cmp #80
 bcc SourceStageCompletion4086_Remainder
 sec
 sbc #80
 inx
 bra SourceStageCompletion4086_Divide
SourceStageCompletion4086_Remainder:
.a16
.i16
 ora #0
 beq SourceStageCompletion4086_G11
 jmp SourceStageCompletion4086_Bad
SourceStageCompletion4086_G11:
.a16
.i16
 txa
 cmp.l VmSourceWorld_Count
 bcc SourceStageCompletion4086_G12
 jmp SourceStageCompletion4086_Bad
SourceStageCompletion4086_G12:
.a16
.i16
 lda.l SourceStageCompletion4086_View
 tax
 lda.l $414000,x
 cmp.l SourceStageCompletion4086_Low
 beq SourceStageCompletion4086_G13
 jmp SourceStageCompletion4086_Bad
SourceStageCompletion4086_G13:
.a16
.i16
 lda.l $414002,x
 cmp #$41
 beq SourceStageCompletion4086_G14
 jmp SourceStageCompletion4086_Bad
SourceStageCompletion4086_G14:
.a16
.i16
 lda.l $439014,x
 ora.l $439016,x
 bne SourceStageCompletion4086_NextRole
 lda #1
 sta.l SourceStageCompletion4086_Live
SourceStageCompletion4086_NextRole:
.a16
.i16
 lda.l SourceStageCompletion4086_RoleCursor
 clc
 adc #4
 sta.l SourceStageCompletion4086_RoleCursor
 cmp #16
 bcs SourceStageCompletion4086_RolesDone
 jmp SourceStageCompletion4086_RoleLoop
SourceStageCompletion4086_RolesDone:
.a16
.i16
 lda.l SourceStageCompletion4086_Live
 bne SourceStageCompletion4086_HasPlayer
 jmp SourceStageCompletion4086_NotComplete
SourceStageCompletion4086_HasPlayer:
.a16
.i16
 lda #256
 jsl SourceCountEntities4086_Count

 bcc SourceStageCompletion4086_G15
 jmp SourceStageCompletion4086_Bad
SourceStageCompletion4086_G15:
.a16
.i16
 cmp #0
 beq SourceStageCompletion4086_NoEndLevel
 jmp SourceStageCompletion4086_NotComplete
SourceStageCompletion4086_NoEndLevel:
.a16
.i16
 lda.l SourceStageCompletion4086_LevelType
 ora.l SourceStageCompletion4086_LevelType+2
 beq SourceStageCompletion4086_Complete
 lda.l SourceStageCompletion4086_LevelType+2
 bne SourceStageCompletion4086_NotComplete
 lda.l SourceStageCompletion4086_LevelType
 cmp #1
 bne SourceStageCompletion4086_NotComplete
 lda #12
 jsl SourceCountEntities4086_Count

 bcc SourceStageCompletion4086_G16
 jmp SourceStageCompletion4086_Bad
SourceStageCompletion4086_G16:
.a16
.i16
 cmp #0
 bne SourceStageCompletion4086_NotComplete
SourceStageCompletion4086_Complete:
.a16
.i16
 lda #1
 sta.l SourceScrollerPrefix4086_Completed
 sta.l SourceStageProducer4086_Completed
 lda #0
 sta.l SourceScrollerPrefix4086_Completed+2
 lda #2
 sta.l SourceStageCompletion4086_Status
 lda #1
 bra SourceStageCompletion4086_Return
SourceStageCompletion4086_NotComplete:
.a16
.i16
 lda #2
 sta.l SourceStageCompletion4086_Status
 lda #0
SourceStageCompletion4086_Return:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
SourceStageCompletion4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceStageCompletion4086_Status
 sta.l SourceStageProducer4086_State
 ply
 plx
 plp
 sec
 rtl
