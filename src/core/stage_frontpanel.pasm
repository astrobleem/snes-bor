; Normal source camera helpers for the full-height BG2 adapter.
; Runtime ownership and full renderer: stage_frontpanel_bg2.pasm.
; No HDMA and no BG3 scrolling: HUD retains the accepted fixed layer.
StageFp_Work = $7FB784
StageFp_Num = StageFp_Work
StageFp_Rem = StageFp_Work+2
StageFp_Request = StageFp_Work+4
StageFp_Ready = StageFp_Work+9
StageFp_WorkEnd = StageFp_Work+28
StageFp_ViewportColumns = 33

; Cold/reset request initialization. P/A/X preserved; no MMIO.
StageFp_Init:
    php
    rep #$30
.a16
.i16
    pha
    phx
    lda #0
    ldx #0
StageFp_Init__loop:
.a16
.i16
    sta.l StageFp_Work,x
    inx
    inx
    cpx #10                     ; request scratch only; no PPU state
    bcc StageFp_Init__loop
    plx
    pla
    plp
    rtl


; A16/I16, returns source mode only for live Normal gameplay/pause/clear.
StageFp_Mode:
.a16
.i16
    lda.l Game_State
    cmp #GAME_STATE_PLAYING
    beq StageFp_Mode__scene
    cmp #GAME_STATE_PAUSED
    beq StageFp_Mode__scene
    cmp #GAME_STATE_STAGECLEAR
    bne StageFp_Mode__off
StageFp_Mode__scene:
.a16
.i16
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    bne StageFp_Mode__off
    lda.l Game_StageIndex
    and #$00FF
    cmp #StageFp_MapCount
    bcs StageFp_Mode__off
    tax
    lda.l StageFp_ModeMap,x
    and #$00FF
    rts
StageFp_Mode__off:
.a16
.i16
    lda #0
    rts


; A16/I16; C=1/A=next missing column, C=0 inactive. A/X/P clobbered.
StageFp_Pick:
    rep #$30
.a16
.i16
    cld
    jsr StageFp_Mode
    bne StageFp_Pick__on
    clc
    rtl
StageFp_Pick__on:
.a16
.i16
    cmp #2
    bne StageFp_Pick__horizontal
    lda #0
    bra StageFp_Pick__request
StageFp_Pick__horizontal:
.a16
.i16
    lda.l Screen_PosX
    sta.l StageFp_Num
    lda #0
    sta.l StageFp_Rem
    ldx #16
StageFp_Pick__divide:
.a16
.i16
    lda.l StageFp_Num
    asl a
    sta.l StageFp_Num
    lda.l StageFp_Rem
    rol a
    cmp #5
    bcc StageFp_Pick__remainder
    sbc #5
    sta.l StageFp_Rem
    lda.l StageFp_Num
    ora #1
    sta.l StageFp_Num
    bra StageFp_Pick__next
StageFp_Pick__remainder:
.a16
.i16
    sta.l StageFp_Rem
StageFp_Pick__next:
.a16
.i16
    dex
    bne StageFp_Pick__divide
    lda.l StageFp_Rem
    tax
    lda.l StageFp_Remainder,x
    and #$00FF
    sta.l StageFp_Rem
    lda.l StageFp_Num
    asl a
    asl a
    asl a
    sec
    sbc.l StageFp_Num
    clc
    adc.l StageFp_Rem
StageFp_Pick__request:
.a16
.i16
    sta.l StageFp_Request
    pha
    sep #$20
.a8
    lda #1
    sta.l StageFp_Ready
    rep #$20
.a16
    pla
    lsr a
    lsr a
    lsr a
    sta.l StreamScrollFp_CameraCol
    sta.l StreamScrollFp_DesiredLo
    clc
    adc #32                    ; 33 visible columns for sub-tile motion
    sta.l StreamScrollFp_DesiredHi
    lda.l StreamScrollFp_DesiredLo
    cmp.l StreamScrollFp_StagedLo
    bcs StageFp_Pick__right
    lda.l StreamScrollFp_StagedLo
    dec a
    sec
    rtl
StageFp_Pick__right:
.a16
.i16
    lda.l StreamScrollFp_DesiredHi
    cmp.l StreamScrollFp_StagedHi
    bcc StageFp_Pick__repair
    beq StageFp_Pick__repair
    lda.l StreamScrollFp_StagedHi
    inc a
    sec
    rtl
StageFp_Pick__repair:
.a16
.i16
    lda.l StreamScrollFp_RepairCur
    cmp.l StreamScrollFp_DesiredLo
    bcs StageFp_Pick__repair_hi
    lda.l StreamScrollFp_DesiredLo
StageFp_Pick__repair_hi:
.a16
.i16
    cmp.l StreamScrollFp_DesiredHi
    bcc StageFp_Pick__selected
    lda.l StreamScrollFp_DesiredLo
StageFp_Pick__selected:
.a16
.i16
    pha
    inc a
    sta.l StreamScrollFp_RepairCur
    pla
    sec
    rtl


StageFp_Remainder:
    .db 0,1,2,4,5,0
