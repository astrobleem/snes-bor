; Independent immutable player ROM jobs only. No scene/OAM/palette drain.
; Owner zero is unpublished: clear it before descriptor writes, then the
; existing TrackRequest final byte store publishes the complete ownership.
SourceBusy_StoreSource:
.a16
.i16
    sta.l DmaQueue+5,x
    php
    rep #$30
    pha
    phx
    txa
    lsr a
    lsr a
    lsr a
    tax
    sep #$20
.a8
    lda #0
    sta.l DmaQueue_Owner,x
    rep #$30
.a16
.i16
    plx
    pla
    plp
    rtl
SourceBusy_NmiGate:
.a16
.i16
    jsl SourcePacket_NmiPublish
    jsl SourceBusy_Drain
    rtl
SourceBusy_Drain:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    phd
    cld
    lda.l Nmi_FrameBusy
    and #$FFFF
    bne SourceBusy_Busy
    brl SourceBusy_Done
SourceBusy_Busy:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    beq SourceBusy_LiveMagic
    brl SourceBusy_Done
SourceBusy_LiveMagic:
.a16
.i16
    lda.l $434E7C
    and #1
    beq SourceBusy_LiveEven
    brl SourceBusy_Done
SourceBusy_LiveEven:
.a16
.i16
    lda.l $434E50
    and #255
    cmp #7
    bne SourceBusy_NoJump1
    brl SourceBusy_Done
SourceBusy_NoJump1:
.a16
.i16
    lda.l $434E74
    and #255
    cmp #7
    bne SourceBusy_NoJump2
    brl SourceBusy_Done
SourceBusy_NoJump2:
.a16
.i16
    lda.l Game_StageIndex
    beq SourceBusy_Stage
    brl SourceBusy_Done
SourceBusy_Stage:
.a16
.i16
    lda.l Nmi_HdmaEnableCurrent
    and #$0080
    beq SourceBusy_ChannelFree
    brl SourceBusy_Done
SourceBusy_ChannelFree:
.a16
.i16
    lda #0
    tcd
    sep #$20
.a8
    pha
    plb
    rep #$30
.a16
.i16
    ldx #0
SourceBusy_Scan:
.a16
.i16
    jsl SourceBusy_ValidateJob
    bcc SourceBusy_Next
    ; Six full physical lines remain at line255: >8184 master clocks.
    ; Actual original whole-block handler costs <=5000 measured clocks.
    sep #$20
.a8
    lda $4212
    bmi SourceBusy_Vblank
    brl SourceBusy_Done8
SourceBusy_Vblank:
.a8
.i16
    lda $2137
    lda $213D
    rep #$30
.a16
    and #255
    pha
    sep #$20
.a8
    lda $213D
    and #1
    rep #$30
.a16
    and #255
    xba
    ora 1,s
    ply
    cmp #256
    bcc SourceBusy_Beam
    brl SourceBusy_Done
SourceBusy_Beam:
.a16
.i16
    sep #$20
.a8
    lda $4212
    bmi SourceBusy_Transfer
    brl SourceBusy_Done8
SourceBusy_Transfer:
.a8
.i16
    rep #$30
.a16
    ; Synthetic short call through the existing bank0 RTL return, leaving
    ; original physical transfer and fourth-row completion logic intact.
    phk
    .db $F4
    .dw ((SourceBusy_Transferred-1)&$FFFF)
    .db $F4
    .dw ((Core_Dma_Enqueue_Long+2)&$FFFF)
    jml Core_Dma_TransferSourceBlock
SourceBusy_Transferred:
.a16
.i16
    sep #$20
.a8
    lda #0
    sta.l DmaQueue+4,x
    rep #$30
.a16
    phx
    txa
    lsr a
    lsr a
    lsr a
    tax
    sep #$20
.a8
    lda #0
    sta.l DmaQueue_Owner,x
    rep #$30
.a16
    plx
    ; Keep the foreground budget conservative; do not race its increment.
SourceBusy_Next:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcs SourceBusy_Done
    brl SourceBusy_Scan
SourceBusy_Done8:
.a8
.i16
    rep #$30
SourceBusy_Done:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    rtl
SourceBusy_FindHot:
.a16
.i16
    ldy #0
SourceBusy_FindHot__loop:
.a16
.i16
    cmp.w SourcePrefetch_HotIdsLo,y
    beq SourceBusy_FindHot__yes
    iny
    iny
    cpy #SourcePrefetch_HotCount*2
    bcc SourceBusy_FindHot__loop
    clc
    rts
SourceBusy_FindHot__yes:
.a16
.i16
    sec
    rts

SourceBusy_ValidateJob:
.a16
.i16
    php
    rep #$30
    phx
    phy
    phb
    phd
    txy
    txa
    and #7
    beq SourceBusy_ValidateJob__guard0
    brl SourceBusy_ValidateJob__no
SourceBusy_ValidateJob__guard0:
.a16
.i16
    cpx #64
    bcc SourceBusy_ValidateJob__guard1
    brl SourceBusy_ValidateJob__no
SourceBusy_ValidateJob__guard1:
.a16
.i16
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq SourceBusy_ValidateJob__guard2
    brl SourceBusy_ValidateJob__no
SourceBusy_ValidateJob__guard2:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SourceBusy_ValidateJob__guard3
    brl SourceBusy_ValidateJob__no
SourceBusy_ValidateJob__guard3:
.a16
.i16
    lda.l SourceVisual_CompletedMagic
    cmp #$C04D
    beq SourceBusy_ValidateJob__guard4
    brl SourceBusy_ValidateJob__no
SourceBusy_ValidateJob__guard4:
.a16
.i16
    txa
    lsr a
    lsr a
    lsr a
    tax
    lda.l DmaQueue_Owner,x
    and #$00FF
    cmp #1
    beq SourceBusy_ValidateJob__guard5
    cmp #33
    beq SourceBusy_ValidateJob__guard5
    brl SourceBusy_ValidateJob__no
SourceBusy_ValidateJob__guard5:
.a16
.i16
    tya
    clc
    adc #$0480
    tcd
    sep #$20
.a8
    lda #$3C
    pha
    plb
    rep #$30
.a16
.i16
    lda $04
    and #$00FF
    cmp #DMA_TYPE_SOURCE_BLOCK | DMA_OPT_ACTIVE
    beq SourceBusy_ValidateJob__guard6
    brl SourceBusy_ValidateJob__no
SourceBusy_ValidateJob__guard6:
.a16
.i16
    lda $00
    cmp #256
    beq SourceBusy_ValidateJob__guard7
    brl SourceBusy_ValidateJob__no
SourceBusy_ValidateJob__guard7:
.a16
.i16
    lda $02
    sec
    sbc #$8000
    bcs SourceBusy_ValidateJob__guard8
    brl SourceBusy_ValidateJob__no
SourceBusy_ValidateJob__guard8:
.a16
.i16
    tay
    and #$C63F
    beq SourceBusy_ValidateJob__guard9
    brl SourceBusy_ValidateJob__no
SourceBusy_ValidateJob__guard9:
.a16
.i16
    tya
    and #$3800
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    pha
    tya
    and #$01C0
    lsr a
    lsr a
    lsr a
    clc
    adc 1,s
    plx
    tax
    lda.l SourceVisual_BlockCache+2,x
    cmp #1
    beq SourceBusy_ValidateJob__guard10
    brl SourceBusy_ValidateJob__no
SourceBusy_ValidateJob__guard10:
.a16
.i16
    lda.l SourceVisual_BlockCache+5,x
    and #255
    cmp #4
    beq SourceBusy_ValidateJob__guard11
    brl SourceBusy_ValidateJob__no
SourceBusy_ValidateJob__guard11:
.a16
.i16
    lda.l SourceVisual_BlockCache+7,x
    and #$00FF
    cmp #0
    beq SourceBusy_ValidateJob__tag
    brl SourceBusy_ValidateJob__no
SourceBusy_ValidateJob__tag:
.a16
.i16
    lda.l SourceVisual_BlockCache+6,x
    and #255
    cmp #1
    beq SourceBusy_Owner1
    cmp #2
    beq SourceBusy_Owner2
    brl SourceBusy_ValidateJob__no
SourceBusy_Owner1:
.a16
.i16
    lda #1
    bra SourceBusy_MatchOwner
SourceBusy_Owner2:
.a16
.i16
    lda #33
SourceBusy_MatchOwner:
.a16
.i16
    pha
    txy
    tdc
    sec
    sbc #$0480
    lsr a
    lsr a
    lsr a
    tax
    lda.l DmaQueue_Owner,x
    and #255
    cmp 1,s
    beq SourceBusy_OwnerMatched
    pla
    brl SourceBusy_ValidateJob__no
SourceBusy_OwnerMatched:
.a16
.i16
    pla
    tyx
    lda.l SourceVisual_BlockCache+6,x
    and #255
    cmp #1
    beq SourceBusy_Attack1
    lda.l $434E74
    bra SourceBusy_AttackRole
SourceBusy_Attack1:
.a16
.i16
    lda.l $434E50
SourceBusy_AttackRole:
.a16
.i16
    and #255
    cmp #2
    beq SourceBusy_AttackAccepted
    brl SourceBusy_ValidateJob__no
SourceBusy_AttackAccepted:
.a16
.i16
    lda.l SourceVisual_BlockCache,x
    jsr SourceBusy_FindHot
    bcs SourceBusy_ValidateJob__guard13
    brl SourceBusy_ValidateJob__no
SourceBusy_ValidateJob__guard13:
.a16
.i16
    lda $05
    cmp.w SourcePrefetch_HotAddressesLo,y
    beq SourceBusy_ValidateJob__guard14
    brl SourceBusy_ValidateJob__no
SourceBusy_ValidateJob__guard14:
.a16
.i16
    lda $07
    and #$00FF
    cmp.w SourcePrefetch_HotBanksLo,y
    beq SourceBusy_ValidateJob__guard15
    brl SourceBusy_ValidateJob__no
SourceBusy_ValidateJob__guard15:
.a16
.i16
    txa
    pld
    plb
    ply
    plx
    plp
    sec
    rtl
SourceBusy_ValidateJob__no:
.a16
.i16
    lda #0
    pld
    plb
    ply
    plx
    plp
    clc
    rtl

; Exact replacement for the skipped-NMI LDA2/STA FrameOver pair only.
SourceBusy_SkippedGate:
.a8
.i16
    lda #2
    sta.l Nmi_FrameOver
    php
    rep #$30
.a16
    pha
    phx
    lda.l $434E50
    and #255
    cmp #2
    beq SourceBusy_SkipAttack
    lda.l $434E74
    and #255
    cmp #2
    beq SourceBusy_SkipAttack
    brl SourceBusy_SkipDone
SourceBusy_SkipAttack:
.a16
.i16
    ldx #0
SourceBusy_SkipQueue:
.a16
.i16
    lda.l DmaQueue+4,x
    and #255
    cmp #67
    beq SourceBusy_SkipDrain
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourceBusy_SkipQueue
    brl SourceBusy_SkipDone
SourceBusy_SkipDrain:
.a16
.i16
    jsl SourceBusy_Drain
SourceBusy_SkipDone:
.a16
.i16
    plx
    pla
    plp
    rtl
SourceBusy_End:
.a16
.i16
