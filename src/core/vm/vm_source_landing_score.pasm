; Source self-landing opponent/MP/score preparation. No actor/player writes.
; Current magic_type1 with another opponent requires the MP backend.
; Signed score multiplication admits raw force<=65535 and signed16 multiple;
; zero operands stay exact across the full source int32 input domain.
; A0 admitted, A1 required, C1 malformed lease/token. Caller owns B636 context.
SourceLandingCallback4086_CheckOpponent:
.a16
.i16
 lda #0
 sta.l SourceLandingCallback4086_ScoreFlag
 lda.l SourceLandingCallback4086_Side
 tax
 lda.l $40900C,x
 sta.l SourceLandingCallback4086_Opponent
 lda.l $40900E,x
 sta.l SourceLandingCallback4086_Opponent+2
 bne SourceLandingCallback4086_OppNonNull
 lda.l SourceLandingCallback4086_Opponent
 bne SourceLandingCallback4086_OppNullBad
 jmp SourceLandingCallback4086_ScoreGood
SourceLandingCallback4086_OppNullBad:
.a16
.i16
 jmp SourceLandingCallback4086_ScoreBad
SourceLandingCallback4086_OppNonNull:
.a16
.i16
 cmp #$41
 beq SourceLandingCallback4086_OppBank
 jmp SourceLandingCallback4086_ScoreBad
SourceLandingCallback4086_OppBank:
.a16
.i16
 lda.l SourceLandingCallback4086_Opponent
 cmp #$4000
 bcs SourceLandingCallback4086_OppLower
 jmp SourceLandingCallback4086_ScoreBad
SourceLandingCallback4086_OppLower:
.a16
.i16
 cmp #$6800
 bcc SourceLandingCallback4086_OppUpper
 jmp SourceLandingCallback4086_ScoreBad
SourceLandingCallback4086_OppUpper:
.a16
.i16
 sec
 sbc #$4000
 sta.l SourceLandingCallback4086_OppView
 ldx #0
SourceLandingCallback4086_OppDivide:
.a16
.i16
 cmp #80
 bcc SourceLandingCallback4086_OppRemainder
 sec
 sbc #80
 inx
 bra SourceLandingCallback4086_OppDivide
SourceLandingCallback4086_OppRemainder:
.a16
.i16
 cmp #0
 beq SourceLandingCallback4086_OppAligned
 jmp SourceLandingCallback4086_ScoreBad
SourceLandingCallback4086_OppAligned:
.a16
.i16
 txa
 cmp.l VmSourceWorld_Count
 bcc SourceLandingCallback4086_OppSlot
 jmp SourceLandingCallback4086_ScoreBad
SourceLandingCallback4086_OppSlot:
.a16
.i16
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l SourceLandingCallback4086_OppCore
 asl a
 sta.l SourceLandingCallback4086_OppSide
 clc
 adc.l SourceLandingCallback4086_OppCore
 sta.l SourceLandingCallback4086_OppCore
 lda.l SourceLandingCallback4086_OppView
 tax
 lda.l SOURCE_WORLD_POOL,x
 cmp.l SourceLandingCallback4086_Opponent
 beq SourceLandingCallback4086_OppTokenLow
 jmp SourceLandingCallback4086_ScoreBad
SourceLandingCallback4086_OppTokenLow:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+2,x
 cmp #$41
 beq SourceLandingCallback4086_OppTokenHigh
 jmp SourceLandingCallback4086_ScoreBad
SourceLandingCallback4086_OppTokenHigh:
.a16
.i16
 lda.l $43904A,x
 cmp #$B4FB
 beq SourceLandingCallback4086_OppLife
 jmp SourceLandingCallback4086_ScoreBad
SourceLandingCallback4086_OppLife:
.a16
.i16
 lda.l $439048,x
 cmp.l SourceModelEntityCopy4086_Models
 bcc SourceLandingCallback4086_OppModelRange
 jmp SourceLandingCallback4086_ScoreBad
SourceLandingCallback4086_OppModelRange:
.a16
.i16
 pha
 lda.l SourceLandingCallback4086_OppSide
 tax
 pla
 cmp.l $416800,x
 beq SourceLandingCallback4086_OppModelMatches
 jmp SourceLandingCallback4086_ScoreBad
SourceLandingCallback4086_OppModelMatches:
.a16
.i16
 lda.l SourceLandingCallback4086_OppView
 cmp.l SourceLandingCallback4086_View
 beq SourceLandingCallback4086_OppGood
 lda.l SourceLandingCallback4086_MagicType+2
 bne SourceLandingCallback4086_OppGood
 lda.l SourceLandingCallback4086_MagicType
 cmp #1
 bne SourceLandingCallback4086_OppGood
 jmp SourceLandingCallback4086_ScoreRequired
SourceLandingCallback4086_OppGood:
.a16
.i16
 jmp SourceLandingCallback4086_ScoreGood
SourceLandingCallback4086_PrepareScore:
.a16
.i16
 lda.l SourceLandingDamage4086_Force
 sta.l SourceLandingCallback4086_RawForce
 lda.l SourceLandingDamage4086_Force+2
 sta.l SourceLandingCallback4086_RawForce+2
 lda.l SourceLandingCallback4086_Callback
 cmp #1
 bne SourceLandingCallback4086_ScoreAttackReady
 lda.l SourceLandingCallback4086_HealthCheat
 ora.l SourceLandingCallback4086_HealthCheat+2
 bne SourceLandingCallback4086_ScoreZeroAttack
 lda.l SourceLandingCallback4086_NoHurt
 ora.l SourceLandingCallback4086_NoHurt+2
 beq SourceLandingCallback4086_ScoreAttackReady
 lda.l SourceLandingCallback4086_Core
 tax
 lda.l $40C048,x
 and #2
 beq SourceLandingCallback4086_ScoreAttackReady
SourceLandingCallback4086_ScoreZeroAttack:
.a16
.i16
 lda #0
 sta.l SourceLandingCallback4086_RawForce
 sta.l SourceLandingCallback4086_RawForce+2
SourceLandingCallback4086_ScoreAttackReady:
.a16
.i16
 lda.l SourceLandingCallback4086_Opponent
 ora.l SourceLandingCallback4086_Opponent+2
 bne SourceLandingCallback4086_ScoreHasOpponent
 jmp SourceLandingCallback4086_ScoreGood
SourceLandingCallback4086_ScoreHasOpponent:
.a16
.i16
 lda.l SourceLandingCallback4086_OppView
 tax
 lda.l SOURCE_WORLD_POOL+40,x
 cmp #BOR_VT_INTEGER
 beq SourceLandingCallback4086_ScorePlayerTag
 jmp SourceLandingCallback4086_ScoreBad
SourceLandingCallback4086_ScorePlayerTag:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+42,x
 beq SourceLandingCallback4086_ScorePlayerReserved
 jmp SourceLandingCallback4086_ScoreBad
SourceLandingCallback4086_ScorePlayerReserved:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+44,x
 sta.l SourceLandingCallback4086_ScorePlayer
 lda.l SOURCE_WORLD_POOL+46,x
 sta.l SourceLandingCallback4086_ScorePlayer+2
 lda #1
 sta.l SourceLandingCallback4086_ScoreFlag
 lda.l SourceLandingCallback4086_RawForce
 sta.l SourceLandingCallback4086_ScoreAmount
 lda.l SourceLandingCallback4086_RawForce+2
 sta.l SourceLandingCallback4086_ScoreAmount+2
 lda.l SourceLandingCallback4086_OppView
 cmp.l SourceLandingCallback4086_View
 bne SourceLandingCallback4086_ScoreOther
 jmp SourceLandingCallback4086_ScoreGood
SourceLandingCallback4086_ScoreOther:
.a16
.i16
 lda.l SourceLandingCallback4086_OppCore
 tax
 lda.l $40C048,x
 and #1
 bne SourceLandingCallback4086_ScoreOtherPlayer
 jmp SourceLandingCallback4086_ScoreGood
SourceLandingCallback4086_ScoreOtherPlayer:
.a16
.i16
 lda.l SourceLandingCallback4086_Core
 tax
 lda.l $40C000,x
 ora.l $40C002,x
 bne SourceLandingCallback4086_ScoreNonzeroMultiplier
 jmp SourceLandingCallback4086_ScoreZeroProduct
SourceLandingCallback4086_ScoreNonzeroMultiplier:
.a16
.i16
 lda.l SourceLandingCallback4086_RawForce
 ora.l SourceLandingCallback4086_RawForce+2
 bne SourceLandingCallback4086_ScoreNonzeroForce
 jmp SourceLandingCallback4086_ScoreZeroProduct
SourceLandingCallback4086_ScoreNonzeroForce:
.a16
.i16
 lda.l SourceLandingCallback4086_RawForce+2
 beq SourceLandingCallback4086_ScoreForce16
 jmp SourceLandingCallback4086_ScoreRequired
SourceLandingCallback4086_ScoreForce16:
.a16
.i16
 lda #0
 sta.l SourceLandingCallback4086_Negative
 lda.l $40C002,x
 beq SourceLandingCallback4086_ScorePositiveMultiplier
 cmp #$FFFF
 beq SourceLandingCallback4086_ScoreNegativeMultiplier
 jmp SourceLandingCallback4086_ScoreRequired
SourceLandingCallback4086_ScorePositiveMultiplier:
.a16
.i16
 lda.l $40C000,x
 bpl SourceLandingCallback4086_ScoreMultiplierReady
 jmp SourceLandingCallback4086_ScoreRequired
SourceLandingCallback4086_ScoreNegativeMultiplier:
.a16
.i16
 lda.l $40C000,x
 bmi SourceLandingCallback4086_ScoreNegative16
 jmp SourceLandingCallback4086_ScoreRequired
SourceLandingCallback4086_ScoreNegative16:
.a16
.i16
 eor #$FFFF
 inc a
 pha
 lda #1
 sta.l SourceLandingCallback4086_Negative
 pla
SourceLandingCallback4086_ScoreMultiplierReady:
.a16
.i16
 sta.l SourceLandingCallback4086_Multiplier
 lda.l SourceLandingCallback4086_RawForce
 sta.l SourceLandingCallback4086_Operand
 lda #0
 sta.l SourceLandingCallback4086_Operand+2
 sta.l SourceLandingCallback4086_ScoreAmount
 sta.l SourceLandingCallback4086_ScoreAmount+2
 lda #16
 sta.l SourceLandingCallback4086_Count
SourceLandingCallback4086_ScoreMultiply:
.a16
.i16
 lda.l SourceLandingCallback4086_Multiplier
 lsr a
 sta.l SourceLandingCallback4086_Multiplier
 bcc SourceLandingCallback4086_ScoreShift
 clc
 lda.l SourceLandingCallback4086_ScoreAmount
 adc.l SourceLandingCallback4086_Operand
 sta.l SourceLandingCallback4086_ScoreAmount
 lda.l SourceLandingCallback4086_ScoreAmount+2
 adc.l SourceLandingCallback4086_Operand+2
 sta.l SourceLandingCallback4086_ScoreAmount+2
SourceLandingCallback4086_ScoreShift:
.a16
.i16
 lda.l SourceLandingCallback4086_Operand
 asl a
 sta.l SourceLandingCallback4086_Operand
 lda.l SourceLandingCallback4086_Operand+2
 rol a
 sta.l SourceLandingCallback4086_Operand+2
 lda.l SourceLandingCallback4086_Count
 dec a
 sta.l SourceLandingCallback4086_Count
 bne SourceLandingCallback4086_ScoreMultiply
 lda.l SourceLandingCallback4086_Negative
 beq SourceLandingCallback4086_ScoreGood
 sec
 lda #0
 sbc.l SourceLandingCallback4086_ScoreAmount
 sta.l SourceLandingCallback4086_ScoreAmount
 lda #0
 sbc.l SourceLandingCallback4086_ScoreAmount+2
 sta.l SourceLandingCallback4086_ScoreAmount+2
 bra SourceLandingCallback4086_ScoreGood
SourceLandingCallback4086_ScoreZeroProduct:
.a16
.i16
 lda #0
 sta.l SourceLandingCallback4086_ScoreAmount
 sta.l SourceLandingCallback4086_ScoreAmount+2
SourceLandingCallback4086_ScoreGood:
.a16
.i16
 lda #0
 clc
 rts
SourceLandingCallback4086_ScoreRequired:
.a16
.i16
 lda #1
 clc
 rts
SourceLandingCallback4086_ScoreBad:
.a16
.i16
 sec
 rts
