; Consume only an already queued, coherent, complete private OAM picture.
; No tile/CGRAM transfer, allocation, actor/resource/ownership/publication write.
; FrameBusy1 suppresses the generic drain; all other descriptors stay intact.
; This tail call returns through SourcePacket_NmiGate's original RTL frame.
; Persistent WRAM is disjoint from prefetch46E6..ED and input ring4700.
SourceQueued_Slot = $7E46EE
SourceQueued_Sum = $7E46F0
SourceQueued_Length = $7E46F2
SourceQueued_CameraX = $7E46F4
SourceQueued_CameraY = $7E46F6
SourceQueued_Stamp = $7E46F8
SourceQueued_ScrollX = $7E46FA
SourceQueued_ScrollY = $7E46FC
SourceQueued_Service:
.a16
.i16
    php
    rep #$30
    cld
    pha
    phx
    phy
    phb
    phd
    lda.l Game_CampaignId
    and #255
    cmp #3
    beq SourceQueued_Guard1
    brl SourceQueued_Done
SourceQueued_Guard1:
.a16
.i16
    lda.l Game_State
    cmp #0
    beq SourceQueued_Guard2
    brl SourceQueued_Invalidate
SourceQueued_Guard2:
.a16
.i16
    lda.l Game_StageIndex
    cmp #0
    beq SourceQueued_Guard3
    brl SourceQueued_Invalidate
SourceQueued_Guard3:
.a16
.i16
    lda.l $7E175E
    cmp #2
    beq SourceQueued_Guard4
    brl SourceQueued_Invalidate
SourceQueued_Guard4:
.a16
.i16
    lda.l $7E1760
    cmp #1
    beq SourceQueued_Guard5
    brl SourceQueued_Invalidate
SourceQueued_Guard5:
.a16
.i16
    lda.l $7E46DC
    cmp #1
    beq SourceQueued_Guard6
    brl SourceQueued_Invalidate
SourceQueued_Guard6:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #6752
    beq SourceQueued_Guard7
    brl SourceQueued_Invalidate
SourceQueued_Guard7:
.a16
.i16
    lda.l SourceVisual_CompletedMagic
    cmp #49229
    beq SourceQueued_Guard8
    brl SourceQueued_Invalidate
SourceQueued_Guard8:
.a16
.i16
    lda.l SVActor_Magic
    cmp #44057
    beq SourceQueued_Guard9
    brl SourceQueued_Invalidate
SourceQueued_Guard9:
.a16
.i16
    lda.l Nmi_Busy
    and #255
    cmp #0
    beq SourceQueued_Guard10
    brl SourceQueued_Invalidate
SourceQueued_Guard10:
.a16
.i16
    lda.l Nmi_HdmaEnableCurrent
    and #255
    cmp #0
    beq SourceQueued_Guard11
    brl SourceQueued_Invalidate
SourceQueued_Guard11:
.a16
.i16
    lda.l Nmi_FrameBusy
    and #$00FF
    bne SourceQueued_Busy
    ; NmiGate precedes the ordinary commit. Main is paused until that
    ; commit completes, so these shadows become the real hardware camera.
    lda.l Screen_PosX
    sta.l SourceQueued_CameraX
    lda.l Screen_PosY
    sta.l SourceQueued_CameraY
    lda.l Nmi_Bg1ScrollX
    sta.l SourceQueued_ScrollX
    lda.l Nmi_Bg1ScrollY
    sta.l SourceQueued_ScrollY
    lda #$4F53
    sta.l SourceQueued_Stamp
    brl SourceQueued_Done
SourceQueued_Busy:
.a16
.i16
    cmp #1
    beq SourceQueued_Guard12
    brl SourceQueued_Invalidate
SourceQueued_Guard12:
.a16
.i16
    lda.l SourceQueued_Stamp
    cmp #20307
    beq SourceQueued_Guard13
    brl SourceQueued_Done
SourceQueued_Guard13:
.a16
.i16
    lda.l Screen_PosX
    cmp.l SourceQueued_CameraX
    beq SourceQueued_Guard14
    brl SourceQueued_Done
SourceQueued_Guard14:
.a16
.i16
    lda.l Screen_PosY
    cmp.l SourceQueued_CameraY
    beq SourceQueued_Guard15
    brl SourceQueued_Done
SourceQueued_Guard15:
.a16
.i16
    lda.l Nmi_Bg1ScrollX
    cmp.l SourceQueued_ScrollX
    beq SourceQueued_Guard16
    brl SourceQueued_Done
SourceQueued_Guard16:
.a16
.i16
    lda.l Nmi_Bg1ScrollY
    cmp.l SourceQueued_ScrollY
    beq SourceQueued_Guard17
    brl SourceQueued_Done
SourceQueued_Guard17:
.a16
.i16
    lda.l SourcePacket_ActiveCamera
    cmp.l SourceQueued_CameraX
    beq SourceQueued_Guard18
    brl SourceQueued_Done
SourceQueued_Guard18:
.a16
.i16
    lda.l SourceVisual_CompletedEarly
    cmp #1
    beq SourceQueued_Guard19
    brl SourceQueued_Done
SourceQueued_Guard19:
.a16
.i16
    lda.l SourceVisual_CompletedHeld
    and #255
    cmp #0
    beq SourceQueued_Guard20
    brl SourceQueued_Done
SourceQueued_Guard20:
.a16
.i16
    lda.l SourcePacket_CopyBusy
    cmp #0
    beq SourceQueued_Guard21
    brl SourceQueued_Done
SourceQueued_Guard21:
.a16
.i16
    lda.l SourcePacket_ActiveValid
    cmp #1
    beq SourceQueued_Guard22
    brl SourceQueued_Done
SourceQueued_Guard22:
.a16
.i16
    lda.l SourcePacket_ThisFrame
    cmp #1
    beq SourceQueued_Guard23
    brl SourceQueued_Done
SourceQueued_Guard23:
.a16
.i16
    lda #$FFFF
    sta.l SourceQueued_Slot
    lda #0
    sta.l SourceQueued_Sum
    ldx #0
SourceQueued_Scan:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    bne SourceQueued_Active
    brl SourceQueued_Next
SourceQueued_Active:
.a16
.i16
    jsr SourceQueued_CheckOwner
    bcs SourceQueued_Guard24
    brl SourceQueued_Done
SourceQueued_Guard24:
.a16
.i16
    tay
    lda.l DmaQueue,x
    sta.l SourceQueued_Length
    cmp #1
    bcs SourceQueued_Guard25
    brl SourceQueued_Done
SourceQueued_Guard25:
.a16
.i16
    cmp #2817
    bcc SourceQueued_Guard26
    brl SourceQueued_Done
SourceQueued_Guard26:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    cmp #$41
    bne SourceQueued_NotOam
    brl SourceQueued_Oam
SourceQueued_NotOam:
.a16
.i16
    cmp #$40
    bne SourceQueued_NotVram
    brl SourceQueued_Vram
SourceQueued_NotVram:
.a16
.i16
    cmp #$42
    beq SourceQueued_Cgram
    ; Specialized ROM jobs and unknown/reverse/fixed descriptors retain
    ; their complete original path. This service never executes them.
    brl SourceQueued_Done
SourceQueued_Cgram:
.a16
.i16
    lda.l SourceQueued_Length
    cmp #33
    bcc SourceQueued_Guard27
    brl SourceQueued_Done
SourceQueued_Guard27:
.a16
.i16
    clc
    adc.l DmaQueue+2,x
    bcc SourceQueued_Guard28
    brl SourceQueued_Done
SourceQueued_Guard28:
.a16
.i16
    cmp #513
    bcc SourceQueued_Guard29
    brl SourceQueued_Done
SourceQueued_Guard29:
.a16
.i16
    brl SourceQueued_Source
SourceQueued_Vram:
.a16
.i16
    lda.l SourceQueued_Length
    cmp #257
    bcc SourceQueued_Guard30
    brl SourceQueued_Done
SourceQueued_Guard30:
.a16
.i16
    dec a
    clc
    adc.l DmaQueue+2,x
    bcc SourceQueued_Guard31
    brl SourceQueued_Done
SourceQueued_Guard31:
.a16
.i16
SourceQueued_Source:
.a16
.i16
    lda.l SourceQueued_Length
    bit #1
    beq SourceQueued_Guard32
    brl SourceQueued_Done
SourceQueued_Guard32:
.a16
.i16
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    beq SourceQueued_Wram
    cmp #$7F
    beq SourceQueued_Wram
    brl SourceQueued_Done
SourceQueued_Wram:
.a16
.i16
    lda.l SourceQueued_Length
    dec a
    clc
    adc.l DmaQueue+5,x
    bcc SourceQueued_Guard33
    brl SourceQueued_Done
SourceQueued_Guard33:
.a16
.i16
    brl SourceQueued_Add
SourceQueued_Oam:
.a16
.i16
    tya
    cmp #0
    beq SourceQueued_Guard34
    brl SourceQueued_Done
SourceQueued_Guard34:
.a16
.i16
    lda.l DmaQueue+4,x
    and #255
    cmp #65
    beq SourceQueued_Guard35
    brl SourceQueued_Done
SourceQueued_Guard35:
.a16
.i16
    lda.l DmaQueue,x
    cmp #544
    beq SourceQueued_Guard36
    brl SourceQueued_Done
SourceQueued_Guard36:
.a16
.i16
    lda.l DmaQueue+2,x
    cmp #0
    beq SourceQueued_Guard37
    brl SourceQueued_Done
SourceQueued_Guard37:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #20224
    beq SourceQueued_Guard38
    brl SourceQueued_Done
SourceQueued_Guard38:
.a16
.i16
    lda.l DmaQueue+7,x
    and #255
    cmp #67
    beq SourceQueued_Guard39
    brl SourceQueued_Done
SourceQueued_Guard39:
.a16
.i16
    lda.l SourceQueued_Slot
    cmp #65535
    beq SourceQueued_Guard40
    brl SourceQueued_Done
SourceQueued_Guard40:
.a16
.i16
    txa
    sta.l SourceQueued_Slot
SourceQueued_Add:
.a16
.i16
    lda.l SourceQueued_Length
    clc
    adc.l SourceQueued_Sum
    bcc SourceQueued_Guard41
    brl SourceQueued_Done
SourceQueued_Guard41:
.a16
.i16
    sta.l SourceQueued_Sum
    cmp #2817
    bcc SourceQueued_Guard42
    brl SourceQueued_Done
SourceQueued_Guard42:
.a16
.i16
SourceQueued_Next:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcs SourceQueued_Scanned
    brl SourceQueued_Scan
SourceQueued_Scanned:
.a16
.i16
    lda.l SourceQueued_Sum
    cmp.l DmaQueue_BudgetTotal
    beq SourceQueued_Guard43
    brl SourceQueued_Done
SourceQueued_Guard43:
.a16
.i16
    lda.l SourceQueued_Slot
    cmp #$FFFF
    bne SourceQueued_Guard44
    brl SourceQueued_Done
SourceQueued_Guard44:
.a16
.i16
    jsl SourceFp_ColumnWindow
    bcs SourceQueued_Guard45
    brl SourceQueued_Done
SourceQueued_Guard45:
.a16
.i16
    ; The source and both OAM tables were committed before Early=1 and
    ; Held=0. The same twelve-line window guard bounds this544-byte DMA.
    sep #$20
.a8
    lda #0
    pha
    plb
    rep #$30
.a16
    lda #0
    sta $2102
    lda #$4F00
    sta $4372
    lda #544
    sta $4375
    sep #$20
.a8
    lda #$43
    sta $4374
    lda #0
    sta $4370
    lda #4
    sta $4371
    lda #$80
SourceQueued_Physical:
.a8
.i16
    sta $420B
    rep #$30
.a16
    lda.l SourceQueued_Slot
    tax
    sep #$20
.a8
    lda #0
    sta.l DmaQueue+4,x
    rep #$30
.a16
    lda.l DmaQueue_BudgetTotal
    sec
    sbc #544
    sta.l DmaQueue_BudgetTotal
SourceQueued_Committed:
.a16
.i16
    brl SourceQueued_Done
SourceQueued_Invalidate:
.a16
.i16
    lda #0
    sta.l SourceQueued_Stamp
SourceQueued_Done:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    rtl
SourceQueued_CheckOwner:
.a16
.i16
    phx
    txa
    lsr a
    lsr a
    lsr a
    tax
    lda.l DmaQueue_Owner,x
    and #$00FF
    plx
    cmp #0
    beq SourceQueued_OwnerYes
    cmp #1
    beq SourceQueued_OwnerYes
    cmp #33
    beq SourceQueued_OwnerYes
    cmp #65
    beq SourceQueued_OwnerYes
    cmp #97
    beq SourceQueued_OwnerYes
    cmp #129
    beq SourceQueued_OwnerYes
    cmp #161
    beq SourceQueued_OwnerYes
    clc
    rts
SourceQueued_OwnerYes:
.a16
.i16
    sec
    rts
SourceQueued_End:
.a16
.i16
