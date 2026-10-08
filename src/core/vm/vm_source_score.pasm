; B631 scalar addscore when no extra-life or score-script service is required.
; Such services remain explicit statuses1/2 without player-state writes.
; B632 certifies absent score scripts; B633 owns four score/lives records.
SourceScore4086_Ready = $7FBF5E
SourceScore4086_LifeScore = $7FBF60
SourceScore4086_Index = $7FBF64
SourceScore4086_Add = $7FBF68
SourceScore4086_ScriptMask = $7FBF6C
SourceScore4086_Status = $7FBF6E
SourceScore4086_Player = $7FBF70
SourceScore4086_Old = $7FBF72
SourceScore4086_New = $7FBF76
SourceScore4086_Next = $7FBF7A
SourceScore4086_Remainder = $7FBF7E
SourceScore4086_Quotient = $7FBF82
SourceScore4086_Count = $7FBF86
SourceScore4086_Offset = $7FBF88
SourceScore4086_Operand = $7FBF8A
SourceScore4086_NoScriptsReady = $7FBF8E
SourceScore4086_StatsReady = $7FBF90
SourceScore4086_End = $7FBF92
SOURCE_PLAYER_SCORES = $7FBFA0
SOURCE_PLAYER_LIVES = $7FBFB0
SOURCE_PLAYER_STATS_END = $7FBFC0
SourceScore4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceScore4086_Ready
 cmp #$B631
 beq SourceScore4086_G1
 jmp SourceScore4086_Bad
SourceScore4086_G1:
.a16
.i16
 lda.l SourceScore4086_Index+2
 bpl SourceScore4086_Nonnegative
 jmp SourceScore4086_Complete
SourceScore4086_Nonnegative:
.a16
.i16
 lda.l SourceScore4086_StatsReady
 cmp #$B633
 beq SourceScore4086_G2
 jmp SourceScore4086_Bad
SourceScore4086_G2:
.a16
.i16
 lda.l SourceScore4086_ScriptMask
 and #$FFF0
 beq SourceScore4086_G3
 jmp SourceScore4086_Bad
SourceScore4086_G3:
.a16
.i16
 lda.l SourceScore4086_LifeScore
 ora.l SourceScore4086_LifeScore+2
 bne SourceScore4086_G4
 jmp SourceScore4086_Bad
SourceScore4086_G4:
.a16
.i16
 lda.l SourceScore4086_Index
 and #3
 sta.l SourceScore4086_Player
 asl a
 asl a
 sta.l SourceScore4086_Offset
 tax
 lda.l SOURCE_PLAYER_SCORES,x
 sta.l SourceScore4086_Old
 sta.l SourceScore4086_Operand
 lda.l SOURCE_PLAYER_SCORES+2,x
 sta.l SourceScore4086_Old+2
 sta.l SourceScore4086_Operand+2
 cmp #$3B9A
 bcc SourceScore4086_OldBounded
 bne SourceScore4086_OldArithmetic
 lda.l SourceScore4086_Old
 cmp #$CA00
 bcc SourceScore4086_OldBounded
SourceScore4086_OldArithmetic:
.a16
.i16
 lda #4
 jmp SourceScore4086_Return
SourceScore4086_OldBounded:
.a16
.i16
 lda.l SourceScore4086_Old
 clc
 adc.l SourceScore4086_Add
 sta.l SourceScore4086_New
 lda.l SourceScore4086_Old+2
 adc.l SourceScore4086_Add+2
 sta.l SourceScore4086_New+2
 cmp #$3B9A
 bcc SourceScore4086_Capped
 bne SourceScore4086_Cap
 lda.l SourceScore4086_New
 cmp #$CA00
 bcc SourceScore4086_Capped
SourceScore4086_Cap:
.a16
.i16
 lda #$C9FF
 sta.l SourceScore4086_New
 lda #$3B9A
 sta.l SourceScore4086_New+2
SourceScore4086_Capped:
.a16
.i16
 lda #0
 sta.l SourceScore4086_Quotient
 sta.l SourceScore4086_Quotient+2
 sta.l SourceScore4086_Remainder
 sta.l SourceScore4086_Remainder+2
 lda #32
 sta.l SourceScore4086_Count
SourceScore4086_Divide:
.a16
.i16
 lda.l SourceScore4086_Operand
 asl a
 sta.l SourceScore4086_Operand
 lda.l SourceScore4086_Operand+2
 rol a
 sta.l SourceScore4086_Operand+2
 lda.l SourceScore4086_Remainder
 rol a
 sta.l SourceScore4086_Remainder
 lda.l SourceScore4086_Remainder+2
 rol a
 sta.l SourceScore4086_Remainder+2
 bcs SourceScore4086_Subtract
 cmp.l SourceScore4086_LifeScore+2
 bcc SourceScore4086_ZeroBit
 bne SourceScore4086_Subtract
 lda.l SourceScore4086_Remainder
 cmp.l SourceScore4086_LifeScore
 bcc SourceScore4086_ZeroBit
SourceScore4086_Subtract:
.a16
.i16
 lda.l SourceScore4086_Remainder
 sec
 sbc.l SourceScore4086_LifeScore
 sta.l SourceScore4086_Remainder
 lda.l SourceScore4086_Remainder+2
 sbc.l SourceScore4086_LifeScore+2
 sta.l SourceScore4086_Remainder+2
 lda.l SourceScore4086_Quotient
 asl a
 ora #1
 sta.l SourceScore4086_Quotient
 lda.l SourceScore4086_Quotient+2
 rol a
 sta.l SourceScore4086_Quotient+2
 bra SourceScore4086_DivideStep
SourceScore4086_ZeroBit:
.a16
.i16
 lda.l SourceScore4086_Quotient
 asl a
 sta.l SourceScore4086_Quotient
 lda.l SourceScore4086_Quotient+2
 rol a
 sta.l SourceScore4086_Quotient+2
SourceScore4086_DivideStep:
.a16
.i16
 lda.l SourceScore4086_Count
 dec a
 sta.l SourceScore4086_Count
 beq SourceScore4086_Divided
 jmp SourceScore4086_Divide
SourceScore4086_Divided:
.a16
.i16
 lda.l SourceScore4086_Old
 sec
 sbc.l SourceScore4086_Remainder
 sta.l SourceScore4086_Next
 lda.l SourceScore4086_Old+2
 sbc.l SourceScore4086_Remainder+2
 sta.l SourceScore4086_Next+2
 lda.l SourceScore4086_Next
 clc
 adc.l SourceScore4086_LifeScore
 sta.l SourceScore4086_Next
 lda.l SourceScore4086_Next+2
 adc.l SourceScore4086_LifeScore+2
 sta.l SourceScore4086_Next+2
 cmp.l SourceScore4086_New+2
 bcc SourceScore4086_ExtraLife
 bne SourceScore4086_Script
 lda.l SourceScore4086_New
 cmp.l SourceScore4086_Next
 bcc SourceScore4086_Script
 beq SourceScore4086_Script
SourceScore4086_ExtraLife:
.a16
.i16
 lda #1
 jmp SourceScore4086_Return
SourceScore4086_Script:
.a16
.i16
 lda.l SourceScore4086_Player
 tax
 lda.l SourceScore4086_ScriptMask
SourceScore4086_Mask:
.a16
.i16
 cpx #0
 beq SourceScore4086_Bit
 lsr a
 dex
 bra SourceScore4086_Mask
SourceScore4086_Bit:
.a16
.i16
 and #1
 beq SourceScore4086_NoScript
 lda #2
 jmp SourceScore4086_Return
SourceScore4086_NoScript:
.a16
.i16
 lda.l SourceScore4086_NoScriptsReady
 cmp #$B632
 beq SourceScore4086_G5
 jmp SourceScore4086_Bad
SourceScore4086_G5:
.a16
.i16
 lda.l SourceScore4086_Offset
 tax
 lda.l SourceScore4086_New
 sta.l SOURCE_PLAYER_SCORES,x
 lda.l SourceScore4086_New+2
 sta.l SOURCE_PLAYER_SCORES+2,x
SourceScore4086_Complete:
.a16
.i16
 lda #0
SourceScore4086_Return:
.a16
.i16
 sta.l SourceScore4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceScore4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceScore4086_Status
 ply
 plx
 plp
 sec
 rtl
