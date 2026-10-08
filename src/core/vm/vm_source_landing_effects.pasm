; B630 zeroed landing-attack effects, with independent B62F source state.
; Frozen requires actual unfrozen/colourmap service (status1), never opaque.
; Q16 coordinates in [-256,256) are exact binary32 values; outside status2.
; This helper is not a complete takedamage callback and does not WorldAck.
SourceLandingEffects4086_Ready = $7FBF3A
SourceLandingEffects4086_Status = $7FBF3C
SourceLandingEffects4086_Slot = $7FBF3E
SourceLandingEffects4086_Row = $7FBF40
SourceLandingEffects4086_View = $7FBF42
SourceLandingEffects4086_Side = $7FBF44
SourceLandingEffects4086_Combat = $7FBF46
SourceLandingEffects4086_Freeze = $7FBF48
SourceLandingEffects4086_Model = $7FBF4A
SourceLandingEffects4086_NoDrop = $7FBF4C
SourceLandingEffects4086_Delta = $7FBF50
SourceLandingEffects4086_BaseValue = $7FBF54
SourceLandingEffects4086_Temp = $7FBF58
SourceLandingEffects4086_Drop = $7FBF5A
SourceLandingEffects4086_End = $7FBF5E
SourceLandingEffects4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceLandingEffects4086_Ready
 cmp #$B630
 beq SourceLandingEffects4086_G1
 jmp SourceLandingEffects4086_Bad
SourceLandingEffects4086_G1:
.a16
.i16
 lda.l SourceDamageEffectsState4086_Ready
 cmp #$B62F
 beq SourceLandingEffects4086_G2
 jmp SourceLandingEffects4086_Bad
SourceLandingEffects4086_G2:
.a16
.i16
 lda.l SourceLandingDrop4086_Ready
 cmp #$B62E
 beq SourceLandingEffects4086_G3
 jmp SourceLandingEffects4086_Bad
SourceLandingEffects4086_G3:
.a16
.i16
 lda.l SourceLifecycle4086_Ready
 cmp #$B4FB
 beq SourceLandingEffects4086_G4
 jmp SourceLandingEffects4086_Bad
SourceLandingEffects4086_G4:
.a16
.i16
 lda.l SourceFreeze4086_Ready
 cmp #$B5DF
 beq SourceLandingEffects4086_G5
 jmp SourceLandingEffects4086_Bad
SourceLandingEffects4086_G5:
.a16
.i16
 lda.l SourceLandingEffects4086_Slot
 cmp #128
 bcc SourceLandingEffects4086_G6
 jmp SourceLandingEffects4086_Bad
SourceLandingEffects4086_G6:
.a16
.i16
 asl a
 asl a
 asl a
 sta.l SourceLandingEffects4086_Temp
 asl a
 clc
 adc.l SourceLandingEffects4086_Temp
 sta.l SourceLandingEffects4086_Row
 lda.l SourceLandingEffects4086_Temp
 asl a
 sta.l SourceLandingEffects4086_View
 asl a
 asl a
 sta.l SourceLandingEffects4086_Side
 clc
 adc.l SourceLandingEffects4086_View
 sta.l SourceLandingEffects4086_View
 lda.l SourceLandingEffects4086_Temp
 asl a
 asl a
 clc
 adc.l SourceLandingEffects4086_Temp
 sta.l SourceLandingEffects4086_Freeze
 lsr a
 sta.l SourceLandingEffects4086_Combat
 lda.l SourceLandingEffects4086_View
 tax
 lda.l $43904A,x
 cmp #$B4FB
 beq SourceLandingEffects4086_G7
 jmp SourceLandingEffects4086_Bad
SourceLandingEffects4086_G7:
.a16
.i16
 lda.l $439048,x
 sta.l SourceLandingEffects4086_Model
 cmp.l SourceLandingDrop4086_Models
 bcc SourceLandingEffects4086_G8
 jmp SourceLandingEffects4086_Bad
SourceLandingEffects4086_G8:
.a16
.i16
 lda.l SourceLandingEffects4086_Side
 tax
 lda.l $416800,x
 cmp.l SourceLandingEffects4086_Model
 beq SourceLandingEffects4086_G9
 jmp SourceLandingEffects4086_Bad
SourceLandingEffects4086_G9:
.a16
.i16
 lda.l SourceLandingEffects4086_Row
 tax
 lda.l SOURCE_ENTITY_DAMAGE_EFFECTS+20,x
 cmp #$B62F
 beq SourceLandingEffects4086_G10
 jmp SourceLandingEffects4086_Bad
SourceLandingEffects4086_G10:
.a16
.i16
 lda.l SOURCE_ENTITY_DAMAGE_EFFECTS+22,x
 cmp.l SourceLandingEffects4086_Model
 beq SourceLandingEffects4086_G11
 jmp SourceLandingEffects4086_Bad
SourceLandingEffects4086_G11:
.a16
.i16
 lda.l SourceLandingEffects4086_Combat
 tax
 lda.l SOURCE_ENTITY_COMBAT+16,x
 cmp #$B5FB
 beq SourceLandingEffects4086_G12
 jmp SourceLandingEffects4086_Bad
SourceLandingEffects4086_G12:
.a16
.i16
 lda.l SOURCE_ENTITY_COMBAT+18,x
 beq SourceLandingEffects4086_G13
 jmp SourceLandingEffects4086_Bad
SourceLandingEffects4086_G13:
.a16
.i16
 lda.l SOURCE_ENTITY_COMBAT,x
 sta.l SourceLandingEffects4086_Drop
 lda.l SOURCE_ENTITY_COMBAT+2,x
 sta.l SourceLandingEffects4086_Drop+2
 lda.l SourceLandingDrop4086_Models
 cmp #17
 bcc SourceLandingEffects4086_G14
 jmp SourceLandingEffects4086_Bad
SourceLandingEffects4086_G14:
.a16
.i16
 ora #0
 bne SourceLandingEffects4086_G15
 jmp SourceLandingEffects4086_Bad
SourceLandingEffects4086_G15:
.a16
.i16
 asl a
 asl a
 asl a
 asl a
 clc
 adc #24
 cmp.l SourceLandingDrop4086_Bytes
 beq SourceLandingEffects4086_G16
 jmp SourceLandingEffects4086_Bad
SourceLandingEffects4086_G16:
.a16
.i16
 clc
 adc.l SourceLandingDrop4086_Base
 bcc SourceLandingEffects4086_G17
 jmp SourceLandingEffects4086_Bad
SourceLandingEffects4086_G17:
.a16
.i16
 lda.l SourceLandingDrop4086_Base
 cmp #$8000
 bcs SourceLandingEffects4086_G18
 jmp SourceLandingEffects4086_Bad
SourceLandingEffects4086_G18:
.a16
.i16
 lda.l SourceLandingDrop4086_Bank
 cmp #$100
 bcc SourceLandingEffects4086_G19
 jmp SourceLandingEffects4086_Bad
SourceLandingEffects4086_G19:
.a16
.i16
 cmp #$40
 bcc SourceLandingEffects4086_BankGood
 cmp #$C0
 bcs SourceLandingEffects4086_BankGood
 jmp SourceLandingEffects4086_Bad
SourceLandingEffects4086_BankGood:
.a16
.i16
 lda.l SourceLandingEffects4086_Model
 asl a
 asl a
 asl a
 asl a
 clc
 adc #24
 clc
 adc.l SourceLandingDrop4086_Base
 tax
 jsr SourceLandingDrop4086_Read
 cmp.l SourceLandingEffects4086_Model
 beq SourceLandingEffects4086_G20
 jmp SourceLandingEffects4086_Bad
SourceLandingEffects4086_G20:
.a16
.i16
 inx
 inx
 jsr SourceLandingDrop4086_Read
 beq SourceLandingEffects4086_G21
 jmp SourceLandingEffects4086_Bad
SourceLandingEffects4086_G21:
.a16
.i16
 txa
 clc
 adc #6
 tax
 jsr SourceLandingDrop4086_Read
 sta.l SourceLandingEffects4086_NoDrop
 inx
 inx
 jsr SourceLandingDrop4086_Read
 sta.l SourceLandingEffects4086_NoDrop+2
 lda.l SourceLandingEffects4086_Freeze
 tax
 lda.l SOURCE_WORLD_FREEZE,x
 ora.l SOURCE_WORLD_FREEZE+2,x
 beq SourceLandingEffects4086_NotFrozen
 lda #1
 jmp SourceLandingEffects4086_Pending
SourceLandingEffects4086_NotFrozen:
.a16
.i16
 lda.l SourceLandingEffects4086_View
 tax
 lda.l $414008,x
 cmp #2
 beq SourceLandingEffects4086_G22
 jmp SourceLandingEffects4086_Bad
SourceLandingEffects4086_G22:
.a16
.i16
 lda.l $41400A,x
 beq SourceLandingEffects4086_G23
 jmp SourceLandingEffects4086_Bad
SourceLandingEffects4086_G23:
.a16
.i16
 lda.l $41400C,x
 sta.l SourceLandingEffects4086_Delta
 lda.l $41400E,x
 sta.l SourceLandingEffects4086_Delta+2
 jsr SourceLandingEffects4086_CoordinateDomain
 bcc SourceLandingEffects4086_PositionBounded
 jmp SourceLandingEffects4086_Arithmetic
SourceLandingEffects4086_PositionBounded:
.a16
.i16
 lda.l SourceLandingEffects4086_Side
 tax
 lda.l $416830,x
 sta.l SourceLandingEffects4086_BaseValue
 lda.l $416832,x
 sta.l SourceLandingEffects4086_BaseValue+2
 jsr SourceLandingEffects4086_CoordinateDomain
 bcc SourceLandingEffects4086_BaseBounded
 jmp SourceLandingEffects4086_Arithmetic
SourceLandingEffects4086_BaseBounded:
.a16
.i16
 lda.l SourceLandingEffects4086_BaseValue+2
 eor #$8000
 sta.l SourceLandingEffects4086_Temp
 lda.l SourceLandingEffects4086_Delta+2
 eor #$8000
 cmp.l SourceLandingEffects4086_Temp
 bcc SourceLandingEffects4086_BaseAbove
 bne SourceLandingEffects4086_PositionAbove
 lda.l SourceLandingEffects4086_Delta
 cmp.l SourceLandingEffects4086_BaseValue
 bcc SourceLandingEffects4086_BaseAbove
SourceLandingEffects4086_PositionAbove:
.a16
.i16
 lda.l SourceLandingEffects4086_Delta
 sec
 sbc.l SourceLandingEffects4086_BaseValue
 sta.l SourceLandingEffects4086_Delta
 lda.l SourceLandingEffects4086_Delta+2
 sbc.l SourceLandingEffects4086_BaseValue+2
 sta.l SourceLandingEffects4086_Delta+2
 bra SourceLandingEffects4086_DropPlan
SourceLandingEffects4086_BaseAbove:
.a16
.i16
 lda.l SourceLandingEffects4086_BaseValue
 sec
 sbc.l SourceLandingEffects4086_Delta
 sta.l SourceLandingEffects4086_Delta
 lda.l SourceLandingEffects4086_BaseValue+2
 sbc.l SourceLandingEffects4086_Delta+2
 sta.l SourceLandingEffects4086_Delta+2
SourceLandingEffects4086_DropPlan:
.a16
.i16
 lda.l SourceLandingEffects4086_NoDrop
 ora.l SourceLandingEffects4086_NoDrop+2
 beq SourceLandingEffects4086_Air
 lda #0
 sta.l SourceLandingEffects4086_Drop
 sta.l SourceLandingEffects4086_Drop+2
SourceLandingEffects4086_Air:
.a16
.i16
 lda.l SourceLandingEffects4086_NoDrop+2
 bmi SourceLandingEffects4086_AirAllowed
 bne SourceLandingEffects4086_Commit
 lda.l SourceLandingEffects4086_NoDrop
 cmp #2
 bcs SourceLandingEffects4086_Commit
SourceLandingEffects4086_AirAllowed:
.a16
.i16
 lda.l SourceLandingEffects4086_Delta+2
 bne SourceLandingEffects4086_Airborne
 lda.l SourceLandingEffects4086_Delta
 cmp #6554
 bcc SourceLandingEffects4086_Commit
SourceLandingEffects4086_Airborne:
.a16
.i16
 lda #1
 sta.l SourceLandingEffects4086_Drop
 lda #0
 sta.l SourceLandingEffects4086_Drop+2
SourceLandingEffects4086_Commit:
.a16
.i16
 lda.l SourceLandingEffects4086_Combat
 tax
 lda.l SourceLandingEffects4086_Drop
 sta.l SOURCE_ENTITY_COMBAT,x
 lda.l SourceLandingEffects4086_Drop+2
 sta.l SOURCE_ENTITY_COMBAT+2,x
 lda.l SourceLandingEffects4086_Row
 tax
 lda #0
 sta.l SOURCE_ENTITY_DAMAGE_EFFECTS,x
 sta.l SOURCE_ENTITY_DAMAGE_EFFECTS+2,x
 lda.l SourceLandingEffects4086_Drop
 ora.l SourceLandingEffects4086_Drop+2
 beq SourceLandingEffects4086_Done
 lda #0
 sta.l SOURCE_ENTITY_DAMAGE_EFFECTS+4,x
 sta.l SOURCE_ENTITY_DAMAGE_EFFECTS+6,x
 sta.l SOURCE_ENTITY_DAMAGE_EFFECTS+8,x
 sta.l SOURCE_ENTITY_DAMAGE_EFFECTS+10,x
SourceLandingEffects4086_Done:
.a16
.i16
 lda #4
SourceLandingEffects4086_Pending:
.a16
.i16
 sta.l SourceLandingEffects4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceLandingEffects4086_Arithmetic:
.a16
.i16
 lda #2
 jmp SourceLandingEffects4086_Pending
SourceLandingEffects4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceLandingEffects4086_Status
 ply
 plx
 plp
 sec
 rtl
SourceLandingEffects4086_CoordinateDomain:
.a16
.i16
 bmi SourceLandingEffects4086_CoordinateNegative
 cmp #$0100
 bcs SourceLandingEffects4086_CoordinateBad
 clc
 rts
SourceLandingEffects4086_CoordinateNegative:
.a16
.i16
 cmp #$FF00
 bcc SourceLandingEffects4086_CoordinateBad
 clc
 rts
SourceLandingEffects4086_CoordinateBad:
.a16
.i16
 sec
 rts

