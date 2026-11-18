
; Unhooked trusted-caller API. A/Y = expected ticket low/high, X = offset
; of an exclusively owned40-byte descriptor in bank43. No RAM allocated here.
; Record: magic0,kind2,ticket4/6,scene8/10,camera12,stage14,physical16/18,
; idle-display-mask20,root-lease22,retire-ticket24/26,retire-pending28,done30.
; Caller must latch the matching NMI image/ticket and protect/reset this record.
.bank 39
.org $9000
SourceIdleOwner_Adopt:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    txa
    and #1
    beq SourceIdleOwner_A0
    brl SourceIdleOwner_AdoptNo
SourceIdleOwner_A0:
.a16
.i16
    cpx #$FFD9
    bcc SourceIdleOwner_A1
    brl SourceIdleOwner_AdoptNo
SourceIdleOwner_A1:
.a16
.i16
    lda.l $7E46DE
    beq SourceIdleOwner_A2
    brl SourceIdleOwner_AdoptNo
SourceIdleOwner_A2:
.a16
.i16
    lda.l SourcePacket_CopyBusy
    cmp #1
    beq SourceIdleOwner_A3
    brl SourceIdleOwner_AdoptNo
SourceIdleOwner_A3:
.a16
.i16
    lda.l $430000,x
    cmp #$1DAD
    beq SourceIdleOwner_A4
    brl SourceIdleOwner_AdoptNo
SourceIdleOwner_A4:
.a16
.i16
    lda.l $430002,x
    cmp #2
    beq SourceIdleOwner_A5
    brl SourceIdleOwner_AdoptNo
SourceIdleOwner_A5:
.a16
.i16
    lda.l $430004,x
    cmp $05,s
    beq SourceIdleOwner_A6
    brl SourceIdleOwner_AdoptNo
SourceIdleOwner_A6:
.a16
.i16
    lda.l $430006,x
    cmp $01,s
    beq SourceIdleOwner_A7
    brl SourceIdleOwner_AdoptNo
SourceIdleOwner_A7:
.a16
.i16
    lda.l $430010,x
    cmp $05,s
    beq SourceIdleOwner_A8
    brl SourceIdleOwner_AdoptNo
SourceIdleOwner_A8:
.a16
.i16
    lda.l $430012,x
    cmp $01,s
    beq SourceIdleOwner_A9
    brl SourceIdleOwner_AdoptNo
SourceIdleOwner_A9:
.a16
.i16
    lda.l $43001E,x
    cmp #1
    beq SourceIdleOwner_A10
    brl SourceIdleOwner_AdoptNo
SourceIdleOwner_A10:
.a16
.i16
    lda.l $430014,x
    cmp #3
    beq SourceIdleOwner_A11
    brl SourceIdleOwner_AdoptNo
SourceIdleOwner_A11:
.a16
.i16
    lda.l $430016,x
    cmp #1
    beq SourceIdleOwner_A12
    brl SourceIdleOwner_AdoptNo
SourceIdleOwner_A12:
.a16
.i16
    lda.l $43001C,x
    beq SourceIdleOwner_A13
    brl SourceIdleOwner_AdoptNo
SourceIdleOwner_A13:
.a16
.i16
    lda.l SourceNextScene_Magic
    cmp #$5343
    beq SourceIdleOwner_A14
    brl SourceIdleOwner_AdoptNo
SourceIdleOwner_A14:
.a16
.i16
    lda.l $430008,x
    cmp.l SourceNextScene_Low
    beq SourceIdleOwner_A15
    brl SourceIdleOwner_AdoptNo
SourceIdleOwner_A15:
.a16
.i16
    lda.l $43000A,x
    cmp.l SourceNextScene_High
    beq SourceIdleOwner_A16
    brl SourceIdleOwner_AdoptNo
SourceIdleOwner_A16:
.a16
.i16
    lda.l $43000C,x
    cmp.l Screen_PosX
    beq SourceIdleOwner_A17
    brl SourceIdleOwner_AdoptNo
SourceIdleOwner_A17:
.a16
.i16
    lda.l $43000C,x
    beq SourceIdleOwner_A18
    brl SourceIdleOwner_AdoptNo
SourceIdleOwner_A18:
.a16
.i16
    lda.l $43000E,x
    cmp.l Game_StageIndex
    beq SourceIdleOwner_A19
    brl SourceIdleOwner_AdoptNo
SourceIdleOwner_A19:
.a16
.i16
    lda.l $43000E,x
    beq SourceIdleOwner_A20
    brl SourceIdleOwner_AdoptNo
SourceIdleOwner_A20:
.a16
.i16
    jsl SourceIdleOwner_QueueDrained
    bcs SourceIdleOwner_A21
    brl SourceIdleOwner_AdoptNo
SourceIdleOwner_A21:
.a16
.i16
    jsl SourceIdleOwner_RootLease
    bcs SourceIdleOwner_A22
    brl SourceIdleOwner_AdoptNo
SourceIdleOwner_A22:
.a16
.i16
    jsl SourceIdleBase_AdoptCanonical
    bcs SourceIdleOwner_A23
    brl SourceIdleOwner_AdoptNo
SourceIdleOwner_A23:
.a16
.i16
    lda #3 ; attack-building owner, not Ready/publication
    sta.l $430002,x
    ply
    plx
    pla
    plp
    sec
    rtl
SourceIdleOwner_AdoptNo:
.a16
.i16
    ply
    plx
    pla
    plp
    clc
    rtl
SourceIdleOwner_Retire:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    txa
    and #1
    beq SourceIdleOwner_R0
    brl SourceIdleOwner_RetireNo
SourceIdleOwner_R0:
.a16
.i16
    cpx #$FFD9
    bcc SourceIdleOwner_R1
    brl SourceIdleOwner_RetireNo
SourceIdleOwner_R1:
.a16
.i16
    lda.l $7E46DE
    beq SourceIdleOwner_R2
    brl SourceIdleOwner_RetireNo
SourceIdleOwner_R2:
.a16
.i16
    lda.l $430000,x
    cmp #$1DAD
    beq SourceIdleOwner_R3
    brl SourceIdleOwner_RetireNo
SourceIdleOwner_R3:
.a16
.i16
    lda.l $430002,x
    cmp #4
    beq SourceIdleOwner_R4
    brl SourceIdleOwner_RetireNo
SourceIdleOwner_R4:
.a16
.i16
    lda.l $430014,x
    beq SourceIdleOwner_R5
    brl SourceIdleOwner_RetireNo
SourceIdleOwner_R5:
.a16
.i16
    lda.l $430016,x
    cmp #1
    beq SourceIdleOwner_R6
    brl SourceIdleOwner_RetireNo
SourceIdleOwner_R6:
.a16
.i16
    lda.l $43001C,x
    cmp #1
    beq SourceIdleOwner_R7
    brl SourceIdleOwner_RetireNo
SourceIdleOwner_R7:
.a16
.i16
    lda.l $430018,x
    cmp $05,s
    beq SourceIdleOwner_R8
    brl SourceIdleOwner_RetireNo
SourceIdleOwner_R8:
.a16
.i16
    lda.l $43001A,x
    cmp $01,s
    beq SourceIdleOwner_R9
    brl SourceIdleOwner_RetireNo
SourceIdleOwner_R9:
.a16
.i16
    lda.l $430010,x
    cmp $05,s
    beq SourceIdleOwner_R10
    brl SourceIdleOwner_RetireNo
SourceIdleOwner_R10:
.a16
.i16
    lda.l $430012,x
    cmp $01,s
    beq SourceIdleOwner_R11
    brl SourceIdleOwner_RetireNo
SourceIdleOwner_R11:
.a16
.i16
    lda.l $43001E,x
    cmp #1
    beq SourceIdleOwner_R12
    brl SourceIdleOwner_RetireNo
SourceIdleOwner_R12:
.a16
.i16
    lda.l $430020,x
    beq SourceIdleOwner_R13
    brl SourceIdleOwner_RetireNo
SourceIdleOwner_R13:
.a16
.i16
    lda.l SourceVisual_CompletedPending
    beq SourceIdleOwner_R14
    brl SourceIdleOwner_RetireNo
SourceIdleOwner_R14:
.a16
.i16
    jsl SourceIdleOwner_QueueDrained
    bcs SourceIdleOwner_R15
    brl SourceIdleOwner_RetireNo
SourceIdleOwner_R15:
.a16
.i16
    jsl SourceIdleOwner_RootLease
    bcs SourceIdleOwner_R16
    brl SourceIdleOwner_RetireNo
SourceIdleOwner_R16:
.a16
.i16
    lda.l SourceReserve_Valid
    cmp #$1D1E
    beq SourceIdleOwner_KeepSharedRoot
    cmp #$1D1F
    beq SourceIdleOwner_KeepSharedRoot
    phx
    ldx #0
SourceIdleOwner_ClearRoot:
.a16
.i16
    lda.l SVActor_HeldBlocks,x
    and #$FFFE
    sta.l SVActor_HeldBlocks,x
    lda.l SVActor_OldBlocks,x
    and #$FFFE
    sta.l SVActor_OldBlocks,x
    txa
    clc
    adc #8
    tax
    cpx #80
    bcc SourceIdleOwner_ClearRoot
    lda.l SVActor_HeldPalettes
    and #$FFFE
    sta.l SVActor_HeldPalettes
    lda.l SVActor_OldPalettes
    and #$FFFE
    sta.l SVActor_OldPalettes
    plx
SourceIdleOwner_KeepSharedRoot:
.a16
.i16
    lda #0
    sta.l $430016,x
    sta.l $43001C,x
    ply
    plx
    pla
    plp
    sec
    rtl
SourceIdleOwner_RetireNo:
.a16
.i16
    ply
    plx
    pla
    plp
    clc
    rtl
SourceIdleOwner_QueueDrained:
.a16
.i16
    php
    rep #$30
    pha
    phx
    lda.l Oam_UploadFlag
    bne SourceIdleOwner_QueueNo
    ldx #0
SourceIdleOwner_QueueLoop:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$005F
    cmp #(DMA_OPT_ACTIVE | DMA_TYPE_OAM)
    beq SourceIdleOwner_QueueNo
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourceIdleOwner_QueueLoop
    plx
    pla
    plp
    sec
    rtl
SourceIdleOwner_QueueNo:
.a16
.i16
    plx
    pla
    plp
    clc
    rtl
SourceIdleOwner_RootLease:
.a16
.i16
    php
    rep #$30
    pha
    phx
    ldx #0
SourceIdleOwner_RootLoop:
.a16
.i16
    lda.l SourceIdleOwner_RootIds,x
    pha
    phx
    txa
    asl a
    asl a
    tax
    lda.l SourceVisual_BlockCache,x
    cmp $03,s
    bne SourceIdleOwner_BadRootRow
    lda.l SourceVisual_BlockCache+2,x
    cmp #2
    bne SourceIdleOwner_BadRootRow
    lda.l SVActor_HeldBlocks,x
    ora.l SVActor_OldBlocks,x
    and #1
    beq SourceIdleOwner_BadRootRow
    plx
    pla
    inx
    inx
    cpx #20
    bcc SourceIdleOwner_RootLoop
    lda.l SourceVisual_PaletteCache
    cmp #361
    bne SourceIdleOwner_RootNo
    lda.l SourceVisual_PaletteCache+3
    and #255
    cmp #1
    bne SourceIdleOwner_RootNo
    lda.l SVActor_HeldPalettes
    ora.l SVActor_OldPalettes
    and #1
    beq SourceIdleOwner_RootNo
    plx
    pla
    plp
    sec
    rtl
SourceIdleOwner_BadRootRow:
.a16
.i16
    plx
    pla
SourceIdleOwner_RootNo:
.a16
.i16
    plx
    pla
    plp
    clc
    rtl
; Read-only union-lease predicate for a future legacy-drop hook. Caller
; must still clear its own legacy claim; only physical bit0 release is held.
SourceIdleOwner_KeepPins:
.a16
.i16
    php
    rep #$30
    pha
    txa
    and #1
    bne SourceIdleOwner_KeepNo
    cpx #$FFD9
    bcs SourceIdleOwner_KeepNo
    lda.l $430000,x
    cmp #$1DAD
    bne SourceIdleOwner_KeepNo
    lda.l $430016,x
    cmp #1
    bne SourceIdleOwner_KeepNo
    pla
    plp
    sec
    rtl
SourceIdleOwner_KeepNo:
.a16
.i16
    pla
    plp
    clc
    rtl
SourceIdleOwner_RootIds:
    .dw 8842,2633,5886,13304,1592,12228,7241,559,3618,11343
SourceIdleOwner_End:
.assert * <= $27A000, "idle owner primitives exceed verified gap"
