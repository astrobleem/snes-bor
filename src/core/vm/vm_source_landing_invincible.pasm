; Actual checkdamage lethal invincibility recovery for empty damage scripts.
; Source position is admitted Q16.16, lifespancountdown is signed int32 at
; side+16 (actual constructor field), invincible is signed int32 life+24.
; Source pit comparison here is STRICT y<PIT_DEPTH (-250), not <=.
; A0 recovered positive result, A1 requires death service, C1 malformed tag.
; Only private B636 Result is written. Caller owns model/entity/self/time.
SourceLandingCallback4086_ResolveInvincible:
.a16
.i16
 lda.l SourceLandingCallback4086_View
 tax
 lda.l SOURCE_WORLD_POOL+8,x
 cmp #BOR_VT_DECIMAL
 beq SourceLandingCallback4086_InvPositionTag
 jmp SourceLandingCallback4086_InvBad
SourceLandingCallback4086_InvPositionTag:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+10,x
 beq SourceLandingCallback4086_InvPositionReserved
 jmp SourceLandingCallback4086_InvBad
SourceLandingCallback4086_InvPositionReserved:
.a16
.i16
 ; Every Q16 value in[-256,256) is exactly binary32. For wider positions,
 ; require multiples of128 Q16 units: exact across the full Q16 range.
 ; This avoids deciding a source float comparison from an inexact value.
 lda.l SOURCE_WORLD_POOL+14,x
 bmi SourceLandingCallback4086_InvNegativePosition
 cmp #$0100
 bcc SourceLandingCallback4086_InvExactPosition
 bra SourceLandingCallback4086_InvWidePosition
SourceLandingCallback4086_InvNegativePosition:
.a16
.i16
 cmp #$FF00
 bcs SourceLandingCallback4086_InvExactPosition
SourceLandingCallback4086_InvWidePosition:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+12,x
 and #$007F
 bne SourceLandingCallback4086_InvRequired
SourceLandingCallback4086_InvExactPosition:
.a16
.i16
 ; Q16 high-word sign ordering: -250 has high word FF06 and low word0.
 lda.l SOURCE_WORLD_POOL+14,x
 eor #$8000
 cmp #$7F06
 bcc SourceLandingCallback4086_InvRequired
 lda.l $43901A,x
 bne SourceLandingCallback4086_InvRequired
 lda.l $439018,x
 cmp #2
 beq SourceLandingCallback4086_InvTwo
 cmp #3
 beq SourceLandingCallback4086_InvThree
 bra SourceLandingCallback4086_InvRequired
SourceLandingCallback4086_InvTwo:
.a16
.i16
 lda #1
 pha
 lda #0
 bra SourceLandingCallback4086_InvLifespan
SourceLandingCallback4086_InvThree:
.a16
.i16
 lda.l SourceLandingCallback4086_Max
 pha
 lda.l SourceLandingCallback4086_Max+2
SourceLandingCallback4086_InvLifespan:
.a16
.i16
 pha
 lda.l SourceLandingCallback4086_Side
 tax
 lda.l SOURCE_WORLD_SIDES+18,x
 bmi SourceLandingCallback4086_InvPopRequired
 pla
 sta.l SourceLandingCallback4086_Result+2
 pla
 sta.l SourceLandingCallback4086_Result
 ora.l SourceLandingCallback4086_Result+2
 beq SourceLandingCallback4086_InvRequired
 lda #0
 clc
 rts
SourceLandingCallback4086_InvPopRequired:
.a16
.i16
 pla
 pla
SourceLandingCallback4086_InvRequired:
.a16
.i16
 lda #1
 clc
 rts
SourceLandingCallback4086_InvBad:
.a16
.i16
 sec
 rts
