; B635 no-attached-item, nonplayer dropweapon(1) component.
; Executes actual set_weapon resolution and actual same-model early return.
; Attached item1, player2, required model change3; faults4. No fake service Ack.
SourceDropWeapon4086_Ready = $7FBF92
SourceDropWeapon4086_Slot = $7FBF94
SourceDropWeapon4086_Status = $7FBF96
SourceDropWeapon4086_Phase = $7FBF98
SourceDropWeapon4086_Flags = $7FBF9A
SourceDropWeapon4086_Side = $7FBF9C
SourceDropWeapon4086_Weapon = $7FBF9E
SourceDropWeapon4086_End = $7FBFA0
SourceDropWeapon4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceDropWeapon4086_Ready
 cmp #$B635
 beq SourceDropWeapon4086_G1
 jmp SourceDropWeapon4086_Bad
SourceDropWeapon4086_G1:
.a16
.i16
 lda.l SourceDropWeapon4086_Slot
 cmp #128
 bcc SourceDropWeapon4086_G2
 jmp SourceDropWeapon4086_Bad
SourceDropWeapon4086_G2:
.a16
.i16
 sta.l SourceWeapon4086_Slot
 sta.l SourceModelTransition4086_Slot
 asl a
 asl a
 asl a
 asl a
 sta.l SourceDropWeapon4086_Weapon
 asl a
 sta.l SourceDropWeapon4086_Flags
 asl a
 sta.l SourceDropWeapon4086_Side
 clc
 adc.l SourceDropWeapon4086_Weapon
 tax
 lda.l SourceLifecycle4086_Ready
 cmp #$B4FB
 beq SourceDropWeapon4086_G3
 jmp SourceDropWeapon4086_Bad
SourceDropWeapon4086_G3:
.a16
.i16
 lda.l $43904A,x
 cmp #$B4FB
 beq SourceDropWeapon4086_G4
 jmp SourceDropWeapon4086_Bad
SourceDropWeapon4086_G4:
.a16
.i16
 lda.l $439048,x
 tay
 lda.l SourceDropWeapon4086_Side
 tax
 tya
 cmp.l $416800,x
 beq SourceDropWeapon4086_G5
 jmp SourceDropWeapon4086_Bad
SourceDropWeapon4086_G5:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Ready
 cmp #$B4EB
 beq SourceDropWeapon4086_G6
 jmp SourceDropWeapon4086_Bad
SourceDropWeapon4086_G6:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Models
 cmp.l SourceWeapon4086_Models
 beq SourceDropWeapon4086_G7
 jmp SourceDropWeapon4086_Bad
SourceDropWeapon4086_G7:
.a16
.i16
 jsl SourceModelTransition4086_CheckIdle
 bcc SourceDropWeapon4086_G8
 jmp SourceDropWeapon4086_Bad
SourceDropWeapon4086_G8:
.a16
.i16
 lda.l SourceDropWeapon4086_Flags
 tax
 lda.l $43EB1C,x
 ora.l $43EB1E,x
 beq SourceDropWeapon4086_NoItem
 lda #1
 jmp SourceDropWeapon4086_Return
SourceDropWeapon4086_NoItem:
.a16
.i16
 lda.l SourceDropWeapon4086_Side
 clc
 adc.l SourceDropWeapon4086_Flags
 tax
 lda.l $40C048,x
 bit #1
 beq SourceDropWeapon4086_Nonplayer
 lda #2
 jmp SourceDropWeapon4086_Return
SourceDropWeapon4086_Nonplayer:
.a16
.i16
 lda #0
 sta.l SourceDropWeapon4086_Phase
 sta.l SourceWeapon4086_NumberLo
 sta.l SourceWeapon4086_NumberHi
 sta.l SourceWeapon4086_AnimFlagLo
 sta.l SourceWeapon4086_AnimFlagHi
SourceDropWeapon4086_Resolve:
.a16
.i16
 jsl SourceWeapon4086_Resolve
 bcc SourceDropWeapon4086_G9
 jmp SourceDropWeapon4086_Bad
SourceDropWeapon4086_G9:
.a16
.i16
 lda.l SourceDropWeapon4086_Side
 tax
 lda.l $416800,x
 cmp.l SourceWeapon4086_Selected
 beq SourceDropWeapon4086_Same
 lda #3
 jmp SourceDropWeapon4086_Return
SourceDropWeapon4086_Same:
.a16
.i16
 lda.l SourceWeapon4086_Selected
 sta.l SourceModelTransition4086_New
 jsl SourceModelTransition4086_Begin
 bcc SourceDropWeapon4086_G10
 jmp SourceDropWeapon4086_Bad
SourceDropWeapon4086_G10:
.a16
.i16
 lda.l SourceModelTransition4086_State
 cmp #2
 beq SourceDropWeapon4086_G11
 jmp SourceDropWeapon4086_Bad
SourceDropWeapon4086_G11:
.a16
.i16
 lda.l SourceDropWeapon4086_Phase
 bne SourceDropWeapon4086_Done
 lda.l SourceDropWeapon4086_Weapon
 tax
 lda.l $43E20A,x
 bmi SourceDropWeapon4086_Done
 bne SourceDropWeapon4086_Override
 lda.l $43E208,x
 beq SourceDropWeapon4086_Done
SourceDropWeapon4086_Override:
.a16
.i16
 lda.l $43E208,x
 sta.l SourceWeapon4086_NumberLo
 lda.l $43E20A,x
 sta.l SourceWeapon4086_NumberHi
 lda #1
 sta.l SourceDropWeapon4086_Phase
 jmp SourceDropWeapon4086_Resolve
SourceDropWeapon4086_Done:
.a16
.i16
 lda #0
SourceDropWeapon4086_Return:
.a16
.i16
 sta.l SourceDropWeapon4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceDropWeapon4086_Bad:
.a16
.i16
 lda #4
 sta.l SourceDropWeapon4086_Status
 ply
 plx
 plp
 sec
 rtl
