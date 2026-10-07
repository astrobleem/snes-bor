; Literal check_energy predicate over staged full signed32 source fields.
; Current mutable animation/entity binding is a separate adapter.
SourceCheckEnergy4086_Ready = $43BE62
SourceCheckEnergy4086_Status = $43BE64
SourceCheckEnergy4086_Which = $43BE66
SourceCheckEnergy4086_Cost = $43BE6A
SourceCheckEnergy4086_Only = $43BE6E
SourceCheckEnergy4086_Disable = $43BE72
SourceCheckEnergy4086_Type = $43BE76
SourceCheckEnergy4086_Seal = $43BE7A
SourceCheckEnergy4086_MP = $43BE7E
SourceCheckEnergy4086_Health = $43BE82
SourceCheckEnergy4086_Present = $43BE86
SourceCheckEnergy4086_Result = $43BE88
SourceCheckEnergy4086_Left = $43BE8C
SourceCheckEnergy4086_Right = $43BE90
SourceCheckEnergy4086_End = $43BE94
SourceCheckEnergy4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceCheckEnergy4086_Ready
 cmp #$B5FA
 beq SourceCheckEnergy4086_Lease
 jmp SourceCheckEnergy4086_Bad
SourceCheckEnergy4086_Lease:
.a16
.i16
 lda.l SourceCheckEnergy4086_Status
 beq SourceCheckEnergy4086_Start
 cmp #2
 beq SourceCheckEnergy4086_Start
 jmp SourceCheckEnergy4086_Bad
SourceCheckEnergy4086_Start:
.a16
.i16
 lda #1
 sta.l SourceCheckEnergy4086_Status
 lda.l SourceCheckEnergy4086_Present
 bne SourceCheckEnergy4086_DisabledByType
 jmp SourceCheckEnergy4086_False
SourceCheckEnergy4086_DisabledByType:
.a16
.i16
 lda.l SourceCheckEnergy4086_Disable+2
 cmp.l SourceCheckEnergy4086_Type+2
 bne SourceCheckEnergy4086_NegativeDisable
 lda.l SourceCheckEnergy4086_Disable
 cmp.l SourceCheckEnergy4086_Type
 bne SourceCheckEnergy4086_NegativeDisable
 jmp SourceCheckEnergy4086_False
SourceCheckEnergy4086_NegativeDisable:
.a16
.i16
 lda.l SourceCheckEnergy4086_Disable+2
 cmp #$FFFF
 bne SourceCheckEnergy4086_SealGate
 lda.l SourceCheckEnergy4086_Disable
 cmp #$FFFF
 bne SourceCheckEnergy4086_DisableAI
 jmp SourceCheckEnergy4086_False
SourceCheckEnergy4086_DisableAI:
.a16
.i16
 cmp #$FFFE
 bne SourceCheckEnergy4086_DisablePlayerNPC
 lda.l SourceCheckEnergy4086_Type
 and #514
 beq SourceCheckEnergy4086_SealGate
 jmp SourceCheckEnergy4086_False
SourceCheckEnergy4086_DisablePlayerNPC:
.a16
.i16
 cmp #$FFFD
 bne SourceCheckEnergy4086_DisablePlayerEnemy
 lda.l SourceCheckEnergy4086_Type
 and #513
 beq SourceCheckEnergy4086_SealGate
 jmp SourceCheckEnergy4086_False
SourceCheckEnergy4086_DisablePlayerEnemy:
.a16
.i16
 cmp #$FFFC
 bne SourceCheckEnergy4086_SealGate
 lda.l SourceCheckEnergy4086_Type
 and #3
 beq SourceCheckEnergy4086_SealGate
 jmp SourceCheckEnergy4086_False
SourceCheckEnergy4086_SealGate:
.a16
.i16
 lda.l SourceCheckEnergy4086_Seal
 ora.l SourceCheckEnergy4086_Seal+2
 beq SourceCheckEnergy4086_WhichGate
 lda.l SourceCheckEnergy4086_Seal
 sta.l SourceCheckEnergy4086_Left
 lda.l SourceCheckEnergy4086_Seal+2
 sta.l SourceCheckEnergy4086_Left+2
 lda.l SourceCheckEnergy4086_Cost
 sta.l SourceCheckEnergy4086_Right
 lda.l SourceCheckEnergy4086_Cost+2
 sta.l SourceCheckEnergy4086_Right+2
 jsr SourceCheckEnergy4086_CompareSigned
 cmp #$FFFF
 bne SourceCheckEnergy4086_WhichGate
 jmp SourceCheckEnergy4086_False
SourceCheckEnergy4086_WhichGate:
.a16
.i16
 lda.l SourceCheckEnergy4086_Which+2
 beq SourceCheckEnergy4086_WhichLow
 jmp SourceCheckEnergy4086_False
SourceCheckEnergy4086_WhichLow:
.a16
.i16
 lda.l SourceCheckEnergy4086_Which
 beq SourceCheckEnergy4086_HealthGate
 cmp #1
 beq SourceCheckEnergy4086_MPGate
 jmp SourceCheckEnergy4086_False
SourceCheckEnergy4086_MPGate:
.a16
.i16
 lda.l SourceCheckEnergy4086_Only+2
 bne SourceCheckEnergy4086_MPCompare
 lda.l SourceCheckEnergy4086_Only
 cmp #2
 bne SourceCheckEnergy4086_MPCompare
 jmp SourceCheckEnergy4086_False
SourceCheckEnergy4086_MPCompare:
.a16
.i16
 lda.l SourceCheckEnergy4086_MP
 sta.l SourceCheckEnergy4086_Left
 lda.l SourceCheckEnergy4086_MP+2
 sta.l SourceCheckEnergy4086_Left+2
 lda.l SourceCheckEnergy4086_Cost
 sta.l SourceCheckEnergy4086_Right
 lda.l SourceCheckEnergy4086_Cost+2
 sta.l SourceCheckEnergy4086_Right+2
 jsr SourceCheckEnergy4086_CompareSigned
 cmp #$FFFF
 bne SourceCheckEnergy4086_True
 jmp SourceCheckEnergy4086_False
SourceCheckEnergy4086_HealthGate:
.a16
.i16
 lda.l SourceCheckEnergy4086_Only+2
 bne SourceCheckEnergy4086_HealthCompare
 lda.l SourceCheckEnergy4086_Only
 cmp #1
 bne SourceCheckEnergy4086_HealthCompare
 jmp SourceCheckEnergy4086_False
SourceCheckEnergy4086_HealthCompare:
.a16
.i16
 lda.l SourceCheckEnergy4086_Health
 sta.l SourceCheckEnergy4086_Left
 lda.l SourceCheckEnergy4086_Health+2
 sta.l SourceCheckEnergy4086_Left+2
 lda.l SourceCheckEnergy4086_Cost
 sta.l SourceCheckEnergy4086_Right
 lda.l SourceCheckEnergy4086_Cost+2
 sta.l SourceCheckEnergy4086_Right+2
 jsr SourceCheckEnergy4086_CompareSigned
 cmp #1
 beq SourceCheckEnergy4086_True
 jmp SourceCheckEnergy4086_False
SourceCheckEnergy4086_True:
.a16
.i16
 lda #1
 bra SourceCheckEnergy4086_Done
SourceCheckEnergy4086_False:
.a16
.i16
 lda #0
SourceCheckEnergy4086_Done:
.a16
.i16
 sta.l SourceCheckEnergy4086_Result
 lda #0
 sta.l SourceCheckEnergy4086_Result+2
 lda #2
 sta.l SourceCheckEnergy4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceCheckEnergy4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceCheckEnergy4086_Status
 ply
 plx
 plp
 sec
 rtl
SourceCheckEnergy4086_CompareSigned:
.a16
.i16
 lda.l SourceCheckEnergy4086_Right+2
 eor #$8000
 sta.l SourceCheckEnergy4086_Right+2
 lda.l SourceCheckEnergy4086_Left+2
 eor #$8000
 cmp.l SourceCheckEnergy4086_Right+2
 bcc SourceCheckEnergy4086_Less
 bne SourceCheckEnergy4086_Greater
 lda.l SourceCheckEnergy4086_Left
 cmp.l SourceCheckEnergy4086_Right
 bcc SourceCheckEnergy4086_Less
 bne SourceCheckEnergy4086_Greater
 lda #0
 rts
SourceCheckEnergy4086_Less:
.a16
.i16
 lda #$FFFF
 rts
SourceCheckEnergy4086_Greater:
.a16
.i16
 lda #1
 rts
