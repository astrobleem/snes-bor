; S8 flattened BG1 target adaptation. NO automatic production integration.
; Host includes this code and generated tables in bank 14.
; Public calls preserve P/A/X/Y/D/DBR (NMI entry accepts interrupted widths).
; Channel 6 only; channel 0 TAD and channel 7 DMA are untouched.
; Begin/End bracket the playing dispatcher; Nmi runs before Core_Nmi_Play.
; Init precedes the first BG load and NMI enable; Reset precedes later loads.
; Full contract and known visual compromises: docs/bor_environment_s8_water.md.
; Verified gap: FP Slot2Tile ends $7FB201, FP SlotStamp starts $7FB800.
; Exactly 1380 bytes; no FP cache allocation is reduced or reused.
StageWater_Work = $7FB220
StageWater_WorkEnd = $7FB784
StageWater_Frame = StageWater_Work
StageWater_ActiveOffset = StageWater_Work+2
StageWater_Pending = StageWater_Work+4
StageWater_Enabled = StageWater_Work+5
StageWater_Mode = StageWater_Work+6
StageWater_Rocking = StageWater_Work+7
StageWater_Height = StageWater_Work+8
StageWater_Phase = StageWater_Work+9
StageWater_RockY = StageWater_Work+10
StageWater_Drift = StageWater_Work+12
StageWater_WriteOffset = StageWater_Work+14
StageWater_Row = StageWater_Work+16
StageWater_Dx = StageWater_Work+18
StageWater_Dirty = StageWater_Work+20
StageWater_PendingY = StageWater_Work+22
StageWater_SavedBusy = StageWater_Work+24
StageWater_Held = StageWater_Work+25
StageWater_Buffer = StageWater_Work+32

; Keep the fixed bank-0 reset region bounded without changing cold-init order.
; Tail entry preserves the original caller's widths and return stack.
StageWater_ColdInit:
    jsl Tad_StreamInit
    jsl SceneVideo_Init
    jml StageWater_Init

; Boot entry: do not interpret uninitialized Held/Enabled bytes as state.
StageWater_Init:
    php
    rep #$30
.a16
.i16
    pha
    phx
    jmp StageWater_Reset__clear

StageWater_Reset:
    php
    rep #$30
.a16
.i16
    pha
    phx
    sep #$20
.a8
    lda.l StageWater_Held
    beq StageWater_Reset__offset
    lda.l StageWater_SavedBusy
    sta.l Nmi_FrameBusy
StageWater_Reset__offset:
    ; Only undo a vertical offset owned by this adapter.
    sep #$20
.a8
    lda.l StageWater_Enabled
    ora.l StageWater_Pending
    beq StageWater_Reset__clear
    rep #$20
.a16
    lda #0
    sta.l Nmi_Bg1ScrollY
    sep #$20
.a8
    lda.l Nmi_HdmaEnable
    and #$BF
    sta.l Nmi_HdmaEnable
StageWater_Reset__clear:
    rep #$30
.a16
.i16
    ldx #0
    lda #0
StageWater_Reset__loop:
.a16
.i16
    sta.l StageWater_Work,x
    inx
    inx
    cpx #32
    bcc StageWater_Reset__loop
    rep #$30
.a16
.i16
    plx
    pla
    plp
    rtl

StageWater_Begin:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    cld
    lda #0
    sta.l StageWater_Dirty
    lda.l Game_State
    beq StageWater_Begin__playing
    jmp StageWater_Begin__done
StageWater_Begin__playing:
    sep #$20
.a8
    lda.l Game_CampaignId
    cmp #3
    beq StageWater_Begin__normal
    jmp StageWater_Begin__done
StageWater_Begin__normal:
    lda.l StageWater_Pending
    beq StageWater_Begin__free
    jmp StageWater_Begin__done
StageWater_Begin__free:
    rep #$30
.a16
.i16
    lda.l Game_StageIndex
    and #$00FF
    tax
    sep #$20
.a8
    lda.l StageWater_ModeMap,x
    sta.l StageWater_Mode
    lda.l StageWater_RockMap,x
    sta.l StageWater_Rocking
    ora.l StageWater_Mode
    sta.l StageWater_Enabled
    bne StageWater_Begin__active
    jmp StageWater_Begin__done
StageWater_Begin__active:
.a8
    ; Compute the frame's immutable water parameters now, but do not hold the
    ; NMI lease across streaming or actor/resource service. Those producers
    ; may legitimately wait for the DMA queue to drain, which can only happen
    ; in NMI. StageWater_OamBegin takes the short lease immediately before
    ; OAM composition, then StageWater_End publishes the matching raster.
    lda.l StageWater_HeightMap,x
    sta.l StageWater_Height
    rep #$30
.a16
.i16
    lda.l StageWater_Frame
    tax
    lda #0
    sta.l StageWater_RockY
    sta.l StageWater_Drift
    sep #$20
.a8
    lda.l StageWater_PhaseFrames,x
    sta.l StageWater_Phase
    lda.l StageWater_Rocking
    beq StageWater_Begin__phase
    lda.l StageWater_RockYFrames,x
    sta.l StageWater_RockY
    lda.l StageWater_DriftFrames,x
    sta.l StageWater_Drift
    bpl StageWater_Begin__phase
    lda #$FF
    sta.l StageWater_Drift+1
StageWater_Begin__phase:
.a8
    ; phase -= source background height * 5, modulo 256
    lda.l StageWater_Height
    asl a
    asl a
    clc
    adc.l StageWater_Height
    sta.l StageWater_Dx
    lda.l StageWater_Phase
    sec
    sbc.l StageWater_Dx
    sta.l StageWater_Phase
    lda #1
    sta.l StageWater_Dirty
StageWater_Begin__done:
    rep #$30
.a16
.i16
    ply
    plx
    pla
    plp
    rtl

; Acquire only for the coupled OAM/raster publication window. All streaming,
; actor animation loads, and source-resource admission have already had a
; chance to run with NMI DMA service enabled.
StageWater_OamBegin:
    php
    rep #$30
.a16
.i16
    sep #$20
.a8
    lda.l StageWater_Dirty
    beq StageWater_OamBegin__done
    lda.l StageWater_Held
    bne StageWater_OamBegin__done
    lda.l Nmi_FrameBusy
    sta.l StageWater_SavedBusy
    lda #1
    sta.l StageWater_Held
    sta.l Nmi_FrameBusy
StageWater_OamBegin__done:
    rep #$30
.a16
.i16
    plp
    rtl

; Insert BEFORE hide/cull decisions, immediately after Jump_ApplyOamYOffset.
StageWater_ApplyOamY:
    php
    rep #$20
.a16
    pha
    cld
    sep #$20
.a8
    lda.l Game_CampaignId
    cmp #3
    bne StageWater_ApplyOamY__done
    lda.l StageWater_Enabled
    beq StageWater_ApplyOamY__done
    lda.l OamSetSprite_Y
    sec
    sbc.l StageWater_RockY
    sta.l OamSetSprite_Y
StageWater_ApplyOamY__done:
    rep #$20
.a16
    pla
    plp
    rtl

; Build the INACTIVE table, then publish one byte last. NMI may interrupt the
; build: it retains the previous immutable table until Pending becomes one.
StageWater_End:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    cld
    lda.l StageWater_Dirty
    bne StageWater_End__build
    jmp StageWater_End__done
StageWater_End__build:
.a16
.i16
    lda.l StageWater_ActiveOffset
    eor #674
    sta.l StageWater_WriteOffset
    tax
    lda #0
    sta.l StageWater_Row
StageWater_End__row:
.a16
.i16
    ; X is byte offset in the two-buffer allocation. Save while indexing ROM.
    phx
    lda.l StageWater_Row
    tax
    lda #0
    sta.l StageWater_Dx
    sep #$20
.a8
    lda.l StageWater_SourceRows,x
    cmp #160
    bcs StageWater_End__offset_ready
    lda.l StageWater_Rocking
    beq StageWater_End__wave
    rep #$20
.a16
    lda.l StageWater_Drift
    sta.l StageWater_Dx
    bra StageWater_End__offset_ready
StageWater_End__wave:
    sep #$20
.a8
    lda.l StageWater_SourceRows,x
    cmp.l StageWater_Height
    bcc StageWater_End__offset_ready
    lda.l StageWater_Mode
    beq StageWater_End__offset_ready
    lda.l StageWater_RowPhases,x
    clc
    adc.l StageWater_Phase
    rep #$20
.a16
    and #$00FF
    tax
    sep #$20
.a8
    lda.l StageWater_Mode
    cmp #15
    beq StageWater_End__wave15
    lda.l StageWater_Wave2,x
    bra StageWater_End__wave_value
StageWater_End__wave15:
    sep #$20
.a8
    lda.l StageWater_Wave15,x
StageWater_End__wave_value:
    sep #$20
.a8
    sta.l StageWater_Dx
    bpl StageWater_End__offset_ready
    lda #$FF
    sta.l StageWater_Dx+1
StageWater_End__offset_ready:
    rep #$30
.a16
.i16
    plx
    sep #$20
.a8
    lda #1
    sta.l StageWater_Buffer,x
    inx
    rep #$20
.a16
    lda.l Nmi_Bg1ScrollX
    clc
    adc.l StageWater_Dx
    sta.l StageWater_Buffer,x
    inx
    inx
    lda.l StageWater_Row
    inc a
    sta.l StageWater_Row
    cmp #224
    bcs StageWater_End__publish
    jmp StageWater_End__row
StageWater_End__publish:
    sep #$20
.a8
    lda #0
    sta.l StageWater_Buffer,x
    rep #$20
.a16
    lda.l StageWater_RockY
    sta.l StageWater_PendingY
    lda.l StageWater_Frame
    inc a
    cmp #5760
    bcc StageWater_End__frame
    lda #0
StageWater_End__frame:
    sta.l StageWater_Frame
    sep #$20
.a8
    lda #1
    sta.l StageWater_Pending
StageWater_End__done:
    sep #$20
.a8
    lda.l StageWater_Held
    beq StageWater_End__restore
    lda.l StageWater_SavedBusy
    sta.l Nmi_FrameBusy
    lda #0
    sta.l StageWater_Held
StageWater_End__restore:
    rep #$30
.a16
.i16
    ply
    plx
    pla
    plp
    rtl

; Called first in main's NMI stub, BEFORE Core_Nmi_Play's HDMAEN commit.
; Respect exactly its busy gate; never change a channel on a skipped commit.
StageWater_Nmi:
    php
    rep #$30
.a16
.i16
    pha
    cld
    sep #$20
.a8
    lda.l Nmi_FrameBusy
    ora.l Nmi_Busy
    beq StageWater_Nmi__commit
    jmp StageWater_Nmi__done
StageWater_Nmi__commit:
.a8
    lda.l Game_CampaignId
    cmp #3
    bne StageWater_Nmi__disable
    lda.l StageWater_Enabled
    beq StageWater_Nmi__disable
    lda.l StageWater_Pending
    beq StageWater_Nmi__done
    ; Disable only our channel while changing its source. Core_Nmi_Play
    ; then owns the normal global disable/commit and updates Current.
    lda.l Nmi_HdmaEnableCurrent
    and #$BF
    sta.l $00420C
    rep #$20
.a16
    lda.l StageWater_WriteOffset
    sta.l StageWater_ActiveOffset
    clc
    adc #(StageWater_Buffer & $FFFF)
    sta.l $004362
    lda.l StageWater_PendingY
    sta.l Nmi_Bg1ScrollY
    sep #$20
.a8
    lda #(StageWater_Buffer >> 16)
    sta.l $004364
    lda #2
    sta.l $004360
    lda #$0D
    sta.l $004361
    lda.l Nmi_HdmaEnable
    ora #$40
    sta.l Nmi_HdmaEnable
    lda #0
    sta.l StageWater_Pending
    bra StageWater_Nmi__done
StageWater_Nmi__disable:
    sep #$20
.a8
    lda.l Nmi_HdmaEnable
    and #$BF
    sta.l Nmi_HdmaEnable
StageWater_Nmi__done:
    rep #$30
.a16
.i16
    pla
    plp
    rtl

; Call at Bg_LoadScene__hud_done during forced blank, after the streaming
; loader has installed reserved blank tile 0. Clear otherwise unwritten map
; rows 28..31 so upward rocking exposes black instead of stale VRAM.
; Read the loader's index (Game_StageIndex may still identify the old stage).
StageWater_ClearGuard:
    php
    rep #$30
.a16
.i16
    pha
    phx
    sep #$20
.a8
    lda.l Game_CampaignId
    cmp #3
    bne StageWater_ClearGuard__done
    rep #$20
.a16
    lda.l Bg_LoadScene_StageIndex
    and #$00FF
    tax
    sep #$20
.a8
    lda.l StageWater_RockMap,x
    beq StageWater_ClearGuard__done
    lda #$80
    sta.l $002115
    rep #$20
.a16
    lda #$6380
    sta.l $002116
    ldx #128
    lda #0
StageWater_ClearGuard__page_a:
.a16
.i16
    sta.l $002118
    dex
    bne StageWater_ClearGuard__page_a
    lda #$6780
    sta.l $002116
    ldx #128
    lda #0
StageWater_ClearGuard__page_b:
    sta.l $002118
    dex
    bne StageWater_ClearGuard__page_b
StageWater_ClearGuard__done:
    rep #$30
.a16
.i16
    plx
    pla
    plp
    rtl
StageWater_EndCode:
