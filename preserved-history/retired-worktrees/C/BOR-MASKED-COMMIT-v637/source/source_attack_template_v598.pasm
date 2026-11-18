; Exact default-stage attack-0 OAM template, one 128-byte record per player.
; Captured only after the normal emitter succeeds, with separate next-pose
; held pins. This slice never publishes or changes OAM/DMA/world state.
SourceAttackTemplate_Base = $437400
SourceAttackTemplate_Magic = $A770

SourceAttackTemplate_Capture:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    lda.l SourceVisual_Key
    cmp #$0216
    beq SourceAttackTemplate_G1
    brl SourceAttackTemplate_Done
SourceAttackTemplate_G1:
.a16
.i16
    lda.l SourceVisual_Key+2
    beq SourceAttackTemplate_G2
    brl SourceAttackTemplate_Done
SourceAttackTemplate_G2:
.a16
.i16
    lda.l SourceVisual_PieceCount
    cmp #10
    beq SourceAttackTemplate_G3
    brl SourceAttackTemplate_Done
SourceAttackTemplate_G3:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    cmp #2
    bcc SourceAttackTemplate_G4
    brl SourceAttackTemplate_Done
SourceAttackTemplate_G4:
.a16
.i16
    asl a
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SOURCE_PACKET_BUILD_META,x
    sta.l SourceAttackTemplate_Begin
    lda.l SOURCE_PACKET_BUILD_META+2,x
    sta.l SourceAttackTemplate_End
    sec
    sbc.l SourceAttackTemplate_Begin
    cmp #40
    beq SourceAttackTemplate_G5
    brl SourceAttackTemplate_Done
SourceAttackTemplate_G5:
.a16
.i16
    lda.l SourceAttackTemplate_End
    cmp #513
    bcc SourceAttackTemplate_G6
    brl SourceAttackTemplate_Done
SourceAttackTemplate_G6:
.a16
.i16
    lda.l SourceAttackTemplate_Begin
    and #3
    beq SourceAttackTemplate_G7
    brl SourceAttackTemplate_Done
SourceAttackTemplate_G7:
.a16
.i16
    jsl SourceNextPins_Acquire
    bcs SourceAttackTemplate_G8
    brl SourceAttackTemplate_Done
SourceAttackTemplate_G8:
.a16
.i16
    ; Invalidate before mutating bytes protected by the optional pin owner.
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    tax
    lda #0
    sta.l SourceAttackTemplate_Base,x
    lda.l Game_StageIndex
    sta.l SourceAttackTemplate_Base+2,x
    lda CHAR_ROSTER_INDEX
    and #$00FF
    sta.l SourceAttackTemplate_Base+4,x
    lda.l SourceVisual_Key
    sta.l SourceAttackTemplate_Base+6,x
    lda.l SourceVisual_Key+2
    sta.l SourceAttackTemplate_Base+8,x
    lda.l SourceAttackTemplate_Begin
    sta.l SourceAttackTemplate_Base+10,x
    lda.l SourceAttackTemplate_End
    sta.l SourceAttackTemplate_Base+12,x
    lda CHAR_POS_X
    sta.l SourceAttackTemplate_Base+14,x
    lda CHAR_POS_Y
    sta.l SourceAttackTemplate_Base+16,x
    lda.l Screen_PosX
    sta.l SourceAttackTemplate_Base+18,x
    lda CHAR_FACING_LEFT
    and #$00FF
    sta.l SourceAttackTemplate_Base+20,x
    lda.l SourceVisual_EntryIndexSaved
    sta.l SourceAttackTemplate_Base+22,x
    ; MVN copies exactly the visible 40 low-OAM bytes and ten expanded-high
    ; bytes. It changes DB; PHB/PLB protect the caller's data bank.
    lda.l SourceAttackTemplate_Begin
    clc
    adc #(Oam_Buffer&$FFFF)
    tax
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    clc
    adc #$7420
    tay
    lda #39
    mvn $43,$7E
    lda.l SourceAttackTemplate_Begin
    lsr a
    lsr a
    clc
    adc #(Oam_ExpandedHi&$FFFF)
    tax
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    clc
    adc #$7448
    tay
    lda #9
    mvn $43,$7E
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    tax
    lda #SourceAttackTemplate_Magic
    sta.l SourceAttackTemplate_Base,x
    jsl SourceAttackLease_Capture
SourceAttackTemplate_Done:
.a16
.i16
    plb
    ply
    plx
    pla
    plp
    rtl

SourceAttackTemplate_Invalidate:
.a16
.i16
    lda #0
    sta.l SourceAttackTemplate_Base
    sta.l SourceAttackTemplate_Base+128
    rtl

; Private scratch after the two 128-byte records.
SourceAttackTemplate_Begin = $437500
SourceAttackTemplate_End = $437502

; Optional standby pins never block the ordinary allocator indefinitely.
; No scan during startup or until one exact template has been captured.
SourceAttackTemplate_ReleasePressure:
.a16
.i16
    php
    rep #$30
    pha
    phx
    lda.l SourceAttackTemplate_Base
    cmp #SourceAttackTemplate_Magic
    beq SourceAttackTemplate_PressureScanStart
    lda.l SourceAttackTemplate_Base+128
    cmp #SourceAttackTemplate_Magic
    bne SourceAttackTemplate_PressureNo
SourceAttackTemplate_PressureScanStart:
.a16
.i16
    ldx #0
SourceAttackTemplate_PressureScan:
.a16
.i16
    lda.l SVActor_HeldBlocks,x
    and #$00C0
    bne SourceAttackTemplate_PressureDrop
    txa
    clc
    adc #8
    tax
    cpx #512
    bcc SourceAttackTemplate_PressureScan
SourceAttackTemplate_PressureNo:
.a16
.i16
    plx
    pla
    plp
    clc
    rtl
SourceAttackTemplate_PressureDrop:
.a16
.i16
    jsl SourceAttackOwned_MayRelease
    bcc SourceAttackTemplate_PressureNo
    jsl SourceAttackTemplate_Invalidate
    lda #0
    jsl SourceNextPins_ReleaseUnpublished
    lda #1
    jsl SourceNextPins_ReleaseUnpublished
    plx
    pla
    plp
    sec
    rtl
