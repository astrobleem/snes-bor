; Post-constructor property owner. B5D4 grants paired model maps_loaded and
; NO_MODEL_OR_STAGE_SPAWN_EVENTS capability, derived offline from source.
; Palette identity is recorded here; physical uploads remain a separate owner.
; A pending boss-music service returns A=1; caller must acknowledge it before
; starting another spawn. No music is silently discarded.
SourceSmartSpawn4086_Ready = $43BB30
SourceSmartSpawn4086_Status = $43BB32 ; 0 idle,1 music pending,2 done,3 fault
SourceSmartSpawn4086_MapModel = $43BB34
SourceSmartSpawn4086_MapsLoaded = $43BB36
SourceSmartSpawn4086_BossMusic = $43BB38 ; 0 absent,1 required
SourceSmartSpawn4086_Players = $43BB3A
SourceSmartSpawn4086_View = $43BB3C
SourceSmartSpawn4086_Core = $43BB3E
SourceSmartSpawn4086_Body = $43BB40
SourceSmartSpawn4086_Health = $43BB42
SourceSmartSpawn4086_Map = $43BB46
SourceSmartSpawn4086_Boss = $43BB48
SourceSmartSpawn4086_Limit = $43BB4C
SourceSmartSpawn4086_End = $43BB4E
SourceSmartSpawn4086_Apply:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceSmartSpawn4086_Ready
 cmp #$B5D4
 beq SourceSmartSpawn4086_G1
 jmp SourceSmartSpawn4086_Bad
SourceSmartSpawn4086_G1:
.a16
.i16
 lda.l SourceSmartSpawn4086_Status
 beq SourceSmartSpawn4086_G2
 jmp SourceSmartSpawn4086_Bad
SourceSmartSpawn4086_G2:
.a16
.i16
 lda.l SourceStageQueue4086_Ready
 cmp #$B5D2
 beq SourceSmartSpawn4086_G3
 jmp SourceSmartSpawn4086_Bad
SourceSmartSpawn4086_G3:
.a16
.i16
 lda.l SourceStageQueue4086_Status
 cmp #2
 beq SourceSmartSpawn4086_G4
 jmp SourceSmartSpawn4086_Bad
SourceSmartSpawn4086_G4:
.a16
.i16
 lda.l SourceSmartSpawn4086_BossMusic
 cmp #2
 bcc SourceSmartSpawn4086_G5
 jmp SourceSmartSpawn4086_Bad
SourceSmartSpawn4086_G5:
.a16
.i16
 lda.l SourceSmartSpawn4086_MapModel
 cmp.l SourceCtorOwner4086_Model
 beq SourceSmartSpawn4086_G6
 jmp SourceSmartSpawn4086_Bad
SourceSmartSpawn4086_G6:
.a16
.i16
 jsl SourceCtorOwner4086_Result
 bcc SourceSmartSpawn4086_G7
 jmp SourceSmartSpawn4086_Bad
SourceSmartSpawn4086_G7:
.a16
.i16
 lda.l VmNativeVariant_Result
 cmp #BOR_VT_PTR
 beq SourceSmartSpawn4086_G8
 jmp SourceSmartSpawn4086_Bad
SourceSmartSpawn4086_G8:
.a16
.i16
 lda #4
 jsr SourceStageQueue4086_ReadRow
 cmp.l SourceSmartSpawn4086_MapModel
 beq SourceSmartSpawn4086_G9
 jmp SourceSmartSpawn4086_Bad
SourceSmartSpawn4086_G9:
.a16
.i16
 lda.l SourceDefaultInit4086_OwnerSlot
 asl a
 asl a
 asl a
 asl a
 pha
 asl a
 asl a
 sta.l SourceSmartSpawn4086_Body
 clc
 adc 1,s
 sta.l SourceSmartSpawn4086_View
 pla
 asl a
 clc
 adc.l SourceSmartSpawn4086_Body
 sta.l SourceSmartSpawn4086_Core
 lda.l SourceSmartSpawn4086_Body
 tax
 lda.l $43383E,x
 cmp #$B5C2
 beq SourceSmartSpawn4086_G10
 jmp SourceSmartSpawn4086_Bad
SourceSmartSpawn4086_G10:
.a16
.i16
 lda.l VmSourceWorld_Count
 beq SourceSmartSpawn4086_CountBad
 cmp #129
 bcc SourceSmartSpawn4086_CountValid
SourceSmartSpawn4086_CountBad:
.a16
.i16
 jmp SourceSmartSpawn4086_Bad
SourceSmartSpawn4086_CountValid:
.a16
.i16
 asl a
 asl a
 asl a
 asl a
 pha
 asl a
 asl a
 clc
 adc 1,s
 sta.l SourceSmartSpawn4086_Limit
 pla
 lda #0
 sta.l SourceSmartSpawn4086_Players
 ldx #0
 ldy #0
SourceSmartSpawn4086_Count:
.a16
.i16
 lda.l $414004,x
 ora.l $414006,x
 beq SourceSmartSpawn4086_CountNext
 phx
 tyx
 lda.l $40C048,x
 plx
 and #1
 beq SourceSmartSpawn4086_CountNext
 lda.l SourceSmartSpawn4086_Players
 inc a
 sta.l SourceSmartSpawn4086_Players
SourceSmartSpawn4086_CountNext:
.a16
.i16
 txa
 clc
 adc #80
 tax
 tya
 clc
 adc #96
 tay
 txa
 cmp.l SourceSmartSpawn4086_Limit
 bcc SourceSmartSpawn4086_Count
 lda.l SourceSmartSpawn4086_Players
 bne SourceSmartSpawn4086_HavePlayers
 inc a
 sta.l SourceSmartSpawn4086_Players
SourceSmartSpawn4086_HavePlayers:
.a16
.i16
 cmp #5
 bcc SourceSmartSpawn4086_G11
 jmp SourceSmartSpawn4086_Bad
SourceSmartSpawn4086_G11:
.a16
.i16
 dec a
 asl a
 asl a
 clc
 adc #28
 pha
 jsr SourceStageQueue4086_ReadRow
 sta.l SourceSmartSpawn4086_Health
 pla
 inc a
 inc a
 jsr SourceStageQueue4086_ReadRow
 sta.l SourceSmartSpawn4086_Health+2
 lda #48
 jsr SourceStageQueue4086_ReadRow
 sta.l SourceSmartSpawn4086_Boss
 lda #50
 jsr SourceStageQueue4086_ReadRow
 sta.l SourceSmartSpawn4086_Boss+2
 lda.l SourceSmartSpawn4086_Body
 tax
 lda.l $433830,x
 sta.l SourceSmartSpawn4086_Map
 bne SourceSmartSpawn4086_MapReady
 lda #46
 jsr SourceStageQueue4086_ReadRow
 bne SourceSmartSpawn4086_MapZero
 lda #44
 jsr SourceStageQueue4086_ReadRow
 cmp.l SourceSmartSpawn4086_MapsLoaded
 bcc SourceSmartSpawn4086_MapStore
 beq SourceSmartSpawn4086_MapStore
SourceSmartSpawn4086_MapZero:
.a16
.i16
 lda #0
SourceSmartSpawn4086_MapStore:
.a16
.i16
 sta.l SourceSmartSpawn4086_Map
SourceSmartSpawn4086_MapReady:
.a16
.i16
 lda #60
 jsr SourceStageQueue4086_ReadRow
 beq SourceSmartSpawn4086_NoAlias
 lda #64
 tay
SourceSmartSpawn4086_Alias:
.a16
.i16
 tya
 jsr SourceStageQueue4086_ReadRow
 pha
 tya
 sec
 sbc #64
 clc
 adc.l SourceSmartSpawn4086_Body
 tax
 pla
 sta.l $433800,x
 iny
 iny
 cpy #112
 bcc SourceSmartSpawn4086_Alias
SourceSmartSpawn4086_NoAlias:
.a16
.i16
 lda.l SourceSmartSpawn4086_Health
 ora.l SourceSmartSpawn4086_Health+2
 beq SourceSmartSpawn4086_NoHealth
 lda.l SourceSmartSpawn4086_View
 tax
 lda.l SourceSmartSpawn4086_Health
 sta.l $414024,x
 sta.l $414044,x
 lda.l SourceSmartSpawn4086_Health+2
 sta.l $414026,x
 sta.l $414046,x
 lda.l SourceSmartSpawn4086_Core
 tax
 lda.l SourceSmartSpawn4086_Health
 sta.l $40C03C,x
 lda.l SourceSmartSpawn4086_Health+2
 sta.l $40C03E,x
SourceSmartSpawn4086_NoHealth:
.a16
.i16
 lda.l SourceSmartSpawn4086_Body
 tax
 lda.l SourceSmartSpawn4086_Map
 sta.l $433830,x
 lda.l SourceSmartSpawn4086_Boss
 sta.l $433838,x
 lda.l SourceSmartSpawn4086_Boss+2
 sta.l $43383A,x
 lda #1
 sta.l $43383C,x
 lda.l SourceSmartSpawn4086_Boss
 ora.l SourceSmartSpawn4086_Boss+2
 beq SourceSmartSpawn4086_Done
 lda.l SourceSmartSpawn4086_BossMusic
 beq SourceSmartSpawn4086_Done
 lda #1
 sta.l SourceSmartSpawn4086_Status
 bra SourceSmartSpawn4086_Return
SourceSmartSpawn4086_Done:
.a16
.i16
 lda #2
 sta.l SourceSmartSpawn4086_Status
 lda #0
SourceSmartSpawn4086_Return:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
SourceSmartSpawn4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceSmartSpawn4086_Status
 ply
 plx
 plp
 sec
 rtl

; Call only after the requested source boss-music service completed successfully.
; Failed audio keeps the pending request; it must not call this acknowledgement.
SourceSmartSpawn4086_AckMusic:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceSmartSpawn4086_Ready
 cmp #$B5D4
 bne SourceSmartSpawn4086_AckBad
 lda.l SourceSmartSpawn4086_Status
 cmp #1
 bne SourceSmartSpawn4086_AckBad
 lda.l SourceSmartSpawn4086_BossMusic
 cmp #1
 bne SourceSmartSpawn4086_AckBad
 lda #2
 sta.l SourceSmartSpawn4086_Status
 lda #0
 jmp SourceSmartSpawn4086_Return
SourceSmartSpawn4086_AckBad:
.a16
.i16
 jmp SourceSmartSpawn4086_Bad
