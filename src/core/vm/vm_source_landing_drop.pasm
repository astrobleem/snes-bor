; B62E: checkdamagedrop for zero-drop landing attacks, unit knockdown defense.
; Standalone callback component, never an acknowledgement of full takedamage.
; B4DI immutable model inputs paired by installer; CRC is checked offline.
SourceLandingDrop4086_Ready = $7FBF14
SourceLandingDrop4086_Status = $7FBF16
SourceLandingDrop4086_Slot = $7FBF18
SourceLandingDrop4086_Life = $7FBF1A
SourceLandingDrop4086_Combat = $7FBF1C
SourceLandingDrop4086_Damage = $7FBF1E
SourceLandingDrop4086_Model = $7FBF20
SourceLandingDrop4086_Base = $7FBF22
SourceLandingDrop4086_Bank = $7FBF24
SourceLandingDrop4086_Bytes = $7FBF26
SourceLandingDrop4086_Models = $7FBF28
SourceLandingDrop4086_Count = $7FBF2A
SourceLandingDrop4086_End = $7FBF2E
SourceLandingDrop4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceLandingDrop4086_Ready
 cmp #$B62E
 beq SourceLandingDrop4086_G1
 jmp SourceLandingDrop4086_Bad
SourceLandingDrop4086_G1:
.a16
.i16
 lda.l SourceDamageState4086_Ready
 cmp #$B62B
 beq SourceLandingDrop4086_G2
 jmp SourceLandingDrop4086_Bad
SourceLandingDrop4086_G2:
.a16
.i16
 lda.l SourceLifecycle4086_Ready
 cmp #$B4FB
 beq SourceLandingDrop4086_G3
 jmp SourceLandingDrop4086_Bad
SourceLandingDrop4086_G3:
.a16
.i16
 lda.l SourceFactors4086_Ready
 cmp #$B5F1
 beq SourceLandingDrop4086_G4
 jmp SourceLandingDrop4086_Bad
SourceLandingDrop4086_G4:
.a16
.i16
 lda.l SourceLandingDrop4086_Slot
 cmp #128
 bcc SourceLandingDrop4086_G5
 jmp SourceLandingDrop4086_Bad
SourceLandingDrop4086_G5:
.a16
.i16
 asl a
 asl a
 pha
 asl a
 asl a
 sta.l SourceLandingDrop4086_Life
 clc
 adc 1,s
 sta.l SourceLandingDrop4086_Combat
 lda 1,s
 asl a
 clc
 adc 1,s
 sta.l SourceLandingDrop4086_Damage
 pla
 tax
 lda.l $43B902,x
 cmp #$B5F1
 beq SourceLandingDrop4086_G6
 jmp SourceLandingDrop4086_Bad
SourceLandingDrop4086_G6:
.a16
.i16
 lda.l $43B900,x
 sta.l SourceLandingDrop4086_Model
 lda.l SourceLandingDrop4086_Life
 asl a
 asl a
 clc
 adc.l SourceLandingDrop4086_Life
 sta.l SourceLandingDrop4086_Life
 tax
 lda.l $43904A,x
 cmp #$B4FB
 beq SourceLandingDrop4086_G7
 jmp SourceLandingDrop4086_Bad
SourceLandingDrop4086_G7:
.a16
.i16
 lda.l $439048,x
 cmp.l SourceLandingDrop4086_Model
 beq SourceLandingDrop4086_G8
 jmp SourceLandingDrop4086_Bad
SourceLandingDrop4086_G8:
.a16
.i16
 lda.l SourceLandingDrop4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 pha
 asl a
 tax
 lda.l $416800,x
 cmp.l SourceLandingDrop4086_Model
 beq SourceLandingDrop4086_G9
 pla
 jmp SourceLandingDrop4086_Bad
SourceLandingDrop4086_G9:
.a16
.i16
 pla
 tax
 lda.l $432808,x
 bne SourceLandingDrop4086_FactorBad
 lda.l $43280A,x
 cmp #$3F80
 beq SourceLandingDrop4086_G10
SourceLandingDrop4086_FactorBad:
.a16
.i16
 jmp SourceLandingDrop4086_Bad
SourceLandingDrop4086_G10:
.a16
.i16
 lda.l SourceLandingDrop4086_Combat
 tax
 lda.l SOURCE_ENTITY_COMBAT+16,x
 cmp #$B5FB
 beq SourceLandingDrop4086_G11
 jmp SourceLandingDrop4086_Bad
SourceLandingDrop4086_G11:
.a16
.i16
 lda.l SOURCE_ENTITY_COMBAT+18,x
 beq SourceLandingDrop4086_G12
 jmp SourceLandingDrop4086_Bad
SourceLandingDrop4086_G12:
.a16
.i16
 lda.l SourceLandingDrop4086_Bank
 cmp #$80
 bcc SourceLandingDrop4086_BankLow
 cmp #$C0
 bcs SourceLandingDrop4086_BankGood
 jmp SourceLandingDrop4086_Bad
SourceLandingDrop4086_BankLow:
.a16
.i16
 cmp #$40
 bcc SourceLandingDrop4086_BankGood
 jmp SourceLandingDrop4086_Bad
SourceLandingDrop4086_BankGood:
.a16
.i16
 lda.l SourceLandingDrop4086_Base
 cmp #$8000
 bcs SourceLandingDrop4086_G13
 jmp SourceLandingDrop4086_Bad
SourceLandingDrop4086_G13:
.a16
.i16
 lda.l SourceLandingDrop4086_Models
 beq SourceLandingDrop4086_TableBad
 cmp #17
 bcs SourceLandingDrop4086_TableBad
 asl a
 asl a
 asl a
 asl a
 clc
 adc #24
 cmp.l SourceLandingDrop4086_Bytes
 bne SourceLandingDrop4086_TableBad
 clc
 adc.l SourceLandingDrop4086_Base
 bcc SourceLandingDrop4086_G14
SourceLandingDrop4086_TableBad:
.a16
.i16
 jmp SourceLandingDrop4086_Bad
SourceLandingDrop4086_G14:
.a16
.i16
 lda.l SourceLandingDrop4086_Base
 tax
 jsr SourceLandingDrop4086_Read
 cmp #$3442
 bne SourceLandingDrop4086_TableBad
 inx
 inx
 jsr SourceLandingDrop4086_Read
 cmp #$4944
 bne SourceLandingDrop4086_TableBad
 inx
 inx
 jsr SourceLandingDrop4086_Read
 cmp #1
 bne SourceLandingDrop4086_TableBad
 inx
 inx
 jsr SourceLandingDrop4086_Read
 cmp #16
 bne SourceLandingDrop4086_TableBad
 inx
 inx
 jsr SourceLandingDrop4086_Read
 cmp.l SourceLandingDrop4086_Models
 bne SourceLandingDrop4086_TableBad
 lda.l SourceLandingDrop4086_Model
 cmp.l SourceLandingDrop4086_Models
 bcc SourceLandingDrop4086_G15
 jmp SourceLandingDrop4086_Bad
SourceLandingDrop4086_G15:
.a16
.i16
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
 cmp.l SourceLandingDrop4086_Model
 beq SourceLandingDrop4086_G16
 jmp SourceLandingDrop4086_Bad
SourceLandingDrop4086_G16:
.a16
.i16
 inx
 inx
 jsr SourceLandingDrop4086_Read
 beq SourceLandingDrop4086_G17
 jmp SourceLandingDrop4086_Bad
SourceLandingDrop4086_G17:
.a16
.i16
 inx
 inx
 jsr SourceLandingDrop4086_Read
 tay
 inx
 inx
 jsr SourceLandingDrop4086_Read
 sta.l SourceLandingDrop4086_Count+2
 tya
 ora.l SourceLandingDrop4086_Count+2
 beq SourceLandingDrop4086_NotAnimal
 lda.l SourceLandingDrop4086_Combat
 tax
 lda #1
 sta.l SOURCE_ENTITY_COMBAT,x
 lda #0
 sta.l SOURCE_ENTITY_COMBAT+2,x
 jmp SourceLandingDrop4086_Good
SourceLandingDrop4086_NotAnimal:
.a16
.i16
 lda.l SourceLandingDrop4086_Combat
 tax
 lda.l SOURCE_ENTITY_COMBAT,x
 ora.l SOURCE_ENTITY_COMBAT+2,x
 beq SourceLandingDrop4086_CheckCount
 jmp SourceLandingDrop4086_Good
SourceLandingDrop4086_CheckCount:
.a16
.i16
 lda.l SourceLandingDrop4086_Damage
 tax
 lda.l SOURCE_ENTITY_DAMAGE_STATE,x
 sta.l SourceLandingDrop4086_Count
 lda.l SOURCE_ENTITY_DAMAGE_STATE+2,x
 sta.l SourceLandingDrop4086_Count+2
 and #$7F80
 cmp #$7F80
 bne SourceLandingDrop4086_Timer
 jmp SourceLandingDrop4086_Bad
SourceLandingDrop4086_Timer:
.a16
.i16
 lda.l SOURCE_ENTITY_DAMAGE_STATE+4,x
 ora.l SOURCE_ENTITY_DAMAGE_STATE+6,x
 beq SourceLandingDrop4086_Commit
 lda.l SOURCE_ENTITY_DAMAGE_STATE+6,x
 cmp.l VmSourceWorld_Time+2
 bcc SourceLandingDrop4086_Reset
 bne SourceLandingDrop4086_Commit
 lda.l SOURCE_ENTITY_DAMAGE_STATE+4,x
 cmp.l VmSourceWorld_Time
 bcs SourceLandingDrop4086_Commit
SourceLandingDrop4086_Reset:
.a16
.i16
 lda.l SourceLandingDrop4086_Life
 tax
 lda.l $439042,x
 sta.l SourceLandingDrop4086_Count+2
 and #$7F80
 cmp #$7F80
 bne SourceLandingDrop4086_ResetLow
 jmp SourceLandingDrop4086_Bad
SourceLandingDrop4086_ResetLow:
.a16
.i16
 lda.l $439040,x
 sta.l SourceLandingDrop4086_Count
SourceLandingDrop4086_Commit:
.a16
.i16
 lda.l SourceLandingDrop4086_Damage
 tax
 lda.l SourceLandingDrop4086_Count
 sta.l SOURCE_ENTITY_DAMAGE_STATE,x
 lda.l SourceLandingDrop4086_Count+2
 sta.l SOURCE_ENTITY_DAMAGE_STATE+2,x
 lda.l VmSourceWorld_Time
 clc
 adc #200
 sta.l SOURCE_ENTITY_DAMAGE_STATE+4,x
 lda.l VmSourceWorld_Time+2
 adc #0
 sta.l SOURCE_ENTITY_DAMAGE_STATE+6,x
 lda #0
 tay
 lda.l SourceLandingDrop4086_Count+2
 bpl SourceLandingDrop4086_Drop
 and #$7FFF
 ora.l SourceLandingDrop4086_Count
 beq SourceLandingDrop4086_Drop
 iny
SourceLandingDrop4086_Drop:
.a16
.i16
 tya
 pha
 lda.l SourceLandingDrop4086_Combat
 tax
 pla
 sta.l SOURCE_ENTITY_COMBAT,x
 lda #0
 sta.l SOURCE_ENTITY_COMBAT+2,x
SourceLandingDrop4086_Good:
.a16
.i16
 lda #2
 sta.l SourceLandingDrop4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceLandingDrop4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceLandingDrop4086_Status
 ply
 plx
 plp
 sec
 rtl
SourceLandingDrop4086_Read:
.a16
.i16
 phb
 sep #$20
.a8
 lda.l SourceLandingDrop4086_Bank
 pha
 plb
 rep #$20
.a16
 lda.w $0000,x
 plb
 ora #0
 rts
