; End Game only, Normal campaign. No live-gameplay hook or new WRAM.
; Drain first: queue slot wrap is not FIFO. Commit TITLE only after the
; queued immutable clear physically retires, before title text is admitted.
.bank 5
.org $8B00
SourceQuit_EndGame:
    php
    rep #$30
    cld
.a16
.i16
    phx
    phy
    lda.l Game_CampaignId
    and #$FF
    cmp #3
    beq SourceQuit_Normal
    ply
    plx
    plp
    sep #$20
.a8
    lda #0
    jml SOURCE_QUIT_ORIGINAL_CONTINUE
SourceQuit_Normal:
.a16
.i16
    ldy #8
SourceQuit_Drain:
.a16
.i16
    jsr SourceQuit_Pending
    bcc SourceQuit_QueueClear
    cpy #0
    beq SourceQuit_Abort
    jsr SourceQuit_WaitField
    dey
    bra SourceQuit_Drain
SourceQuit_QueueClear:
.a16
.i16
    lda #$8800
    sta.l DmaRequest_SourceAddrLow
    lda #(BG3_TILEMAP_VRAM_WORD * 2)
    sta.l DmaRequest_TargetAddr
    lda #768
    sta.l DmaRequest_Length
    sep #$20
.a8
    lda #5
    sta.l DmaRequest_SourceBank
    lda #DMA_TYPE_VRAM
    sta.l DmaRequest_TypeFlags
    rep #$30
.a16
.i16
    jsl Core_Dma_Enqueue_Long
    bcc SourceQuit_Abort
    ldy #8
SourceQuit_WaitClear:
.a16
.i16
    jsr SourceQuit_Pending
    bcc SourceQuit_Commit
    cpy #0
    beq SourceQuit_Abort
    jsr SourceQuit_WaitField
    dey
    bra SourceQuit_WaitClear
SourceQuit_Abort:
.a16
.i16
    ply
    plx
    plp
    jml Game_State_Play__pausemenu_done
SourceQuit_Commit:
.a16
.i16
    lda #0
    sta.l Game_Lives
    sta.l G13_P2Lives
    sep #$20
.a8
    sta.l Pause_Step
    rep #$30
.a16
.i16
    lda #GAME_STATE_TITLE
    sta.l Game_State
    ply
    plx
    plp
    rep #$30
.a16
.i16
    lda #GAME_STATE_TITLE
    jml Game_State_Play__pausemenu_done

; A16/I16, C=1 pending or reserved; no descriptor edits or cancellation.
SourceQuit_Pending:
.a16
.i16
    ldx #0
SourceQuit_PendingSlot:
.a16
.i16
    lda.l DmaQueue+4,x
    and #DMA_OPT_ACTIVE | DMA_OPT_RESERVED
    bne SourceQuit_Busy
    txa
    clc
    adc #DMA_QUEUE_SLOT_SIZE
    tax
    cpx #DMA_QUEUE_SLOTS * DMA_QUEUE_SLOT_SIZE
    bcc SourceQuit_PendingSlot
    clc
    rts
SourceQuit_Busy:
.a16
.i16
    sec
    rts

; Normal's unconditional field counter advances even when a visual commit
; is skipped. No player/media preparation is serviced in this quit wait.
; Preserve the caller's bounded wait count; stream audio uses its existing
; foreground late pump, never NMI work. Counter wrap is an inequality.
SourceQuit_WaitField:
.a16
.i16
    phx
    phy
    lda.l StageTimer_FieldCounter
    pha
SourceQuit_WaitLoop:
.a16
.i16
    lda 1,s
    cmp.l StageTimer_FieldCounter
    bne SourceQuit_FieldDone
    sep #$20
.a8
    lda.l AudioStream_Enable
    beq SourceQuit_NoPump
    lda.l AudioSemantic_FootDieStreamActive
    beq SourceQuit_NoPump
    jsl Tad_StreamLatePump
SourceQuit_NoPump:
.a8
    rep #$30
.a16
.i16
    bra SourceQuit_WaitLoop
SourceQuit_FieldDone:
.a16
.i16
    pla
    ply
    plx
    rts
SourceQuit_CodeEnd:
.assert SourceQuit_CodeEnd <= $058F00, "quit cleanup exceeds audited ROM gap"

; Ordinary advancing-source VRAM transfer, no fixed/reverse flags.
.bank 5
.org $8800
SourceQuit_BlankRows:
SOURCE_QUIT_ZERO_DATA
SourceQuit_BlankEnd:
.assert SourceQuit_BlankEnd - SourceQuit_BlankRows == 768, "exact twelve HUD rows"
