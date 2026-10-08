; B62F independent source projectile/staydown/guard state, 128*24 bytes.
; $7EF100..$7EFCFF; G12 bounded trace ends $7EF040, code guard/frontpanel
; ends below $7EF000. No alias with VM slots or the DMA queue arena.
; +0 projectile, +4 staydown.rise, +8 riseattack, +12 riseattack_stall,
; +16 current modeldata.guardpoints, +20 marker, +22 copied model identity.
; Source toexplode is an independent signed DWORD per physical actor at
; $7EFD00..$7EFEFF. Birth clears it; bomb/projectile services must update it.
; B4DI CRC/source pair is validated by compiler/installer before both leases.
SourceDamageEffectsState4086_Ready = $7FBF2E
SourceDamageEffectsState4086_Offset = $7FBF30
SourceDamageEffectsState4086_Life = $7FBF32
SourceDamageEffectsState4086_Model = $7FBF34
SourceDamageEffectsState4086_Guard = $7FBF36
SourceDamageEffectsState4086_End = $7FBF3A
SOURCE_ENTITY_DAMAGE_EFFECTS = $7EF100
SOURCE_ENTITY_DAMAGE_EFFECTS_STRIDE = 24
SOURCE_ENTITY_DAMAGE_EFFECTS_END = $7EFD00
SOURCE_ENTITY_TOEXPLODE = $7EFD00
SOURCE_ENTITY_TOEXPLODE_END = $7EFF00
SourceDamageEffectsState4086_InitializeBirth:
.a16
.i16
 php
 rep #$38
 pha
 phx
 phy
 lda.l SourceDamageEffectsState4086_Ready
 bne SourceDamageEffectsState4086_Enabled
 jmp SourceDamageEffectsState4086_Good
SourceDamageEffectsState4086_Enabled:
.a16
.i16
 cmp #$B62F
 beq SourceDamageEffectsState4086_G1
 jmp SourceDamageEffectsState4086_Bad
SourceDamageEffectsState4086_G1:
.a16
.i16
 lda.l SourceLandingDrop4086_Ready
 cmp #$B62E
 beq SourceDamageEffectsState4086_G2
 jmp SourceDamageEffectsState4086_Bad
SourceDamageEffectsState4086_G2:
.a16
.i16
 lda.l SourceLifecycle4086_Ready
 cmp #$B4FB
 beq SourceDamageEffectsState4086_G3
 jmp SourceDamageEffectsState4086_Bad
SourceDamageEffectsState4086_G3:
.a16
.i16
 lda 5,s
 cmp #128
 bcc SourceDamageEffectsState4086_G4
 jmp SourceDamageEffectsState4086_Bad
SourceDamageEffectsState4086_G4:
.a16
.i16
 asl a
 asl a
 asl a
 sta.l SourceDamageEffectsState4086_Offset
 asl a
 clc
 adc.l SourceDamageEffectsState4086_Offset
 sta.l SourceDamageEffectsState4086_Offset
 lda 5,s
 asl a
 asl a
 asl a
 asl a
 sta.l SourceDamageEffectsState4086_Life
 asl a
 asl a
 clc
 adc.l SourceDamageEffectsState4086_Life
 sta.l SourceDamageEffectsState4086_Life
 tax
 lda.l $43904A,x
 cmp #$B4FB
 beq SourceDamageEffectsState4086_G5
 jmp SourceDamageEffectsState4086_Bad
SourceDamageEffectsState4086_G5:
.a16
.i16
 lda.l $439048,x
 sta.l SourceDamageEffectsState4086_Model
 cmp.l SourceLandingDrop4086_Models
 bcc SourceDamageEffectsState4086_G6
 jmp SourceDamageEffectsState4086_Bad
SourceDamageEffectsState4086_G6:
.a16
.i16
 lda.l SourceLandingDrop4086_Models
 beq SourceDamageEffectsState4086_BadTable
 cmp #17
 bcs SourceDamageEffectsState4086_BadTable
 asl a
 asl a
 asl a
 asl a
 clc
 adc #24
 cmp.l SourceLandingDrop4086_Bytes
 bne SourceDamageEffectsState4086_BadTable
 clc
 adc.l SourceLandingDrop4086_Base
 bcs SourceDamageEffectsState4086_BadTable
 lda.l SourceLandingDrop4086_Base
 cmp #$8000
 bcc SourceDamageEffectsState4086_BadTable
 lda.l SourceLandingDrop4086_Bank
 cmp #$100
 bcc SourceDamageEffectsState4086_BankByte
 jmp SourceDamageEffectsState4086_Bad
SourceDamageEffectsState4086_BankByte:
.a16
.i16
 cmp #$40
 bcc SourceDamageEffectsState4086_BankGood
 cmp #$C0
 bcs SourceDamageEffectsState4086_BankGood
SourceDamageEffectsState4086_BadTable:
.a16
.i16
 jmp SourceDamageEffectsState4086_Bad
SourceDamageEffectsState4086_BankGood:
.a16
.i16
 lda 5,s
 asl a
 asl a
 asl a
 asl a
 asl a
 asl a
 tax
 lda.l $416800,x
 cmp.l SourceDamageEffectsState4086_Model
 beq SourceDamageEffectsState4086_G7
 jmp SourceDamageEffectsState4086_Bad
SourceDamageEffectsState4086_G7:
.a16
.i16
 lda.l SourceDamageEffectsState4086_Model
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
 cmp.l SourceDamageEffectsState4086_Model
 beq SourceDamageEffectsState4086_G8
 jmp SourceDamageEffectsState4086_Bad
SourceDamageEffectsState4086_G8:
.a16
.i16
 inx
 inx
 jsr SourceLandingDrop4086_Read
 beq SourceDamageEffectsState4086_G9
 jmp SourceDamageEffectsState4086_Bad
SourceDamageEffectsState4086_G9:
.a16
.i16
 txa
 clc
 adc #10
 tax
 jsr SourceLandingDrop4086_Read
 sta.l SourceDamageEffectsState4086_Guard
 inx
 inx
 jsr SourceLandingDrop4086_Read
 sta.l SourceDamageEffectsState4086_Guard+2
 lda.l SourceDamageEffectsState4086_Offset
 tax
 ldy #12
 lda #0
SourceDamageEffectsState4086_Clear:
.a16
.i16
 sta.l SOURCE_ENTITY_DAMAGE_EFFECTS,x
 inx
 inx
 dey
 bne SourceDamageEffectsState4086_Clear
 lda.l SourceDamageEffectsState4086_Offset
 tax
 lda.l SourceDamageEffectsState4086_Guard
 sta.l SOURCE_ENTITY_DAMAGE_EFFECTS+16,x
 lda.l SourceDamageEffectsState4086_Guard+2
 sta.l SOURCE_ENTITY_DAMAGE_EFFECTS+18,x
 lda #$B62F
 sta.l SOURCE_ENTITY_DAMAGE_EFFECTS+20,x
 lda.l SourceDamageEffectsState4086_Model
 sta.l SOURCE_ENTITY_DAMAGE_EFFECTS+22,x
 lda 5,s
 asl a
 asl a
 tax
 lda #0
 sta.l SOURCE_ENTITY_TOEXPLODE,x
 sta.l SOURCE_ENTITY_TOEXPLODE+2,x
SourceDamageEffectsState4086_Good:
.a16
.i16
 ply
 plx
 pla
 plp
 clc
 rtl
SourceDamageEffectsState4086_Bad:
.a16
.i16
 ply
 plx
 pla
 plp
 sec
 rtl
