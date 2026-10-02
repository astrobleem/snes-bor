; Source choose_difficulty() (BOR.C): cursor starts at 0, wraps through all
; generated set names plus Back, and confirms only unlocked sets. This port
; additionally requires content availability AND a mapped campaign. Names
; stay visible while gated. Up/Down and Left/Right are equivalent navigation;
; Select is Back, action buttons/Start confirm, from either physical pad.
;
; Main includes this CODE in free bank17. No private WRAM, DP, or DBR owner:
; cursor/phase are existing BorSet_Selected/BorDifficulty_Chosen; only the
; existing TextStaging/Text_StringIndex and DMA request scratch are reused.
; Exactly one 64-byte queued text row per difficulty frame. No second draw
; via CharSelect_DrawStepRow, and no mutation of P2 session/readiness state.
; Public entry accepts either A width, I16; exits A8/I16 except Draw/Clear
; (A16/I16, C=DMA accepted). Names and gates live in generated bank12 tables.

BorSetSelect_Begin:
    sep #$20
.a8
    lda #0                       ; source choose_difficulty selector = 0
    sta.l BorSet_Selected
    jsl BorSetSelect_Draw
    bcc BorSetSelect_Begin__done
    sep #$20
.a8
    lda #1
    sta.l BorDifficulty_Chosen
BorSetSelect_Begin__done:
    sep #$20
.a8
    rtl

BorSetSelect_Play:
    rep #$31
.a16
.i16
    lda.l Input_trigger
    ora.l Input2_trigger
    bit #$2000                   ; Select = source ESC/Back
    bne BorSetSelect_Play__back
    bit #$0A00                   ; Up or Left
    bne BorSetSelect_Play__previous
    bit #$0500                   ; Down or Right
    bne BorSetSelect_Play__next
    and #$D0F0                   ; B/Y/Start/A/X/L/R; NOT direction/Select
    beq BorSetSelect_Play__draw
    sep #$20
.a8
    lda.l BorSet_Selected
    cmp #BOR_SET_COUNT
    beq BorSetSelect_Play__back
    jsl BorSet_IsSelectable
    bcc BorSetSelect_Play__draw
    bra BorSetSelect_Play__confirm
BorSetSelect_Play__previous:
    sep #$20
.a8
    lda.l BorSet_Selected
    beq BorSetSelect_Play__wrap_previous
    dec a
    bra BorSetSelect_Play__store
BorSetSelect_Play__wrap_previous:
.a8
    lda #BOR_SET_COUNT
    bra BorSetSelect_Play__store
BorSetSelect_Play__next:
    sep #$20
.a8
    lda.l BorSet_Selected
    inc a
    cmp #BOR_SET_COUNT+1
    bcc BorSetSelect_Play__store
    lda #0
BorSetSelect_Play__store:
.a8
    sta.l BorSet_Selected
BorSetSelect_Play__draw:
    jsl BorSetSelect_Draw
    sep #$20
.a8
    rtl
BorSetSelect_Play__back:
    sep #$20
.a8
    lda #BOR_SET_COUNT
    sta.l BorSet_Selected
BorSetSelect_Play__confirm:
    sep #$20
.a8
    lda #2
    sta.l BorDifficulty_Chosen
    rtl

BorSetSelect_Finish:
    jsl BorSetSelect_Clear
    bcc BorSetSelect_Finish__done
    sep #$20
.a8
    lda #CHARSELECT_STEP_DRAW_HEADER
    sta.l CharSelect_Step
    lda.l BorSet_Selected
    cmp #BOR_SET_COUNT
    beq BorSetSelect_Finish__back
    lda #3
    sta.l BorDifficulty_Chosen
    rtl
BorSetSelect_Finish__back:
.a8
    lda #0
    sta.l BorSet_Selected
    sta.l BorDifficulty_Chosen
    rep #$31
.a16
.i16
    lda #GAME_STATE_TITLE
    sta.l Game_State
BorSetSelect_Finish__done:
    sep #$20
.a8
    rtl

; One-row adaptation: "DIFFICULTY < Easy      >  START", or LOCKED/OFF.
; Fixed-width generated source names are capped at ten visible glyphs. The
; generated stride, not a hardcoded shift, resolves each positional name.
BorSetSelect_Draw:
    rep #$31
.a16
.i16
    jsr BorSetSelect_Blank
    ldx #(BorSetSelect_Prefix-BorSetSelect_Strings)
    ldy #0
    jsr BorSetSelect_Label
    ldx #(BorSetSelect_Suffix-BorSetSelect_Strings)
    ldy #44
    jsr BorSetSelect_Label
    lda.l BorSet_Selected
    and #$00FF
    cmp #BOR_SET_COUNT
    beq BorSetSelect_Draw__back
    bcc BorSetSelect_Draw__name
    lda #0
    sep #$20
.a8
    sta.l BorSet_Selected
    rep #$31
.a16
.i16
BorSetSelect_Draw__name:
.a16
.i16
    tay
    lda #0
BorSetSelect_Draw__stride:
.a16
.i16
    cpy #0
    beq BorSetSelect_Draw__index
    clc
    adc #BOR_SET_NAME_WIDTH
    dey
    bra BorSetSelect_Draw__stride
BorSetSelect_Draw__index:
.a16
.i16
    sta.l Text_StringIndex
    ldx #24
    ldy #0
BorSetSelect_Draw__copy:
.a16
.i16
    cpy #BOR_SET_NAME_WIDTH
    bcs BorSetSelect_Draw__status
    cpy #10
    bcs BorSetSelect_Draw__status
    phx
    lda.l Text_StringIndex
    tax
    lda.l BorSet_Names,x
    and #$00FF
    plx
    beq BorSetSelect_Draw__status
    jsr BorSetSelect_Emit
    lda.l Text_StringIndex
    inc a
    sta.l Text_StringIndex
    iny
    bra BorSetSelect_Draw__copy
BorSetSelect_Draw__back:
.a16
.i16
    ldx #(BorSetSelect_Back-BorSetSelect_Strings)
    ldy #24
    jsr BorSetSelect_Label
    bra BorSetSelect_Draw__ready
BorSetSelect_Draw__status:
    sep #$20
.a8
    lda.l BorSet_Selected
    jsl BorSet_IsUnlocked
    bcc BorSetSelect_Draw__locked
    lda.l BorSet_Selected
    jsl BorSet_IsAvailable
    bcc BorSetSelect_Draw__off
BorSetSelect_Draw__ready:
    rep #$31
.a16
.i16
    ldx #(BorSetSelect_Ready-BorSetSelect_Strings)
    bra BorSetSelect_Draw__label
BorSetSelect_Draw__locked:
    rep #$31
.a16
.i16
    ldx #(BorSetSelect_Locked-BorSetSelect_Strings)
    bra BorSetSelect_Draw__label
BorSetSelect_Draw__off:
    rep #$31
.a16
.i16
    ldx #(BorSetSelect_Off-BorSetSelect_Strings)
BorSetSelect_Draw__label:
.a16
.i16
    ldy #50
    jsr BorSetSelect_Label
    jmp BorSetSelect_Queue

BorSetSelect_Clear:
    rep #$31
.a16
.i16
    jsr BorSetSelect_Blank
    jmp BorSetSelect_Queue

BorSetSelect_Blank:
.a16
.i16
    ldx #0
    lda #(FONT_TILE_INDEX_BASE | (HUD_ENTRY_HIGH * $100) | (FONT_CGRAM_PAL_ID * $0400))
BorSetSelect_Blank__loop:
.a16
.i16
    sta.l TextStaging,x
    inx
    inx
    cpx #TEXT_ROW_BYTES
    bcc BorSetSelect_Blank__loop
    rts

; A16 ASCII, X destination byte offset; preserves Y. Unsupported glyphs
; become spaces, matching the existing printable BOR-font contract.
BorSetSelect_Emit:
.a16
.i16
    cmp #FONT_ASCII_FIRST
    bcc BorSetSelect_Emit__space
    cmp #FONT_ASCII_LAST+1
    bcc BorSetSelect_Emit__glyph
BorSetSelect_Emit__space:
.a16
    lda #FONT_ASCII_FIRST
BorSetSelect_Emit__glyph:
.a16
    sec
    sbc #FONT_ASCII_FIRST
    clc
    adc #FONT_TILE_INDEX_BASE
    ora #(HUD_ENTRY_HIGH * $100)
    ora #(FONT_CGRAM_PAL_ID * $0400)
    sta.l TextStaging,x
    inx
    inx
    rts

; X offset in local immutable strings, Y destination byte offset.
BorSetSelect_Label:
.a16
.i16
    lda.l BorSetSelect_Strings,x
    and #$00FF
    beq BorSetSelect_Label__done
    phx
    tyx
    jsr BorSetSelect_Emit
    txy
    plx
    inx
    bra BorSetSelect_Label
BorSetSelect_Label__done:
.a16
.i16
    rts

BorSetSelect_Queue:
.a16
.i16
    lda #TextStaging
    sta.l DmaRequest_SourceAddrLow
    lda #(BG3_TILEMAP_VRAM_WORD*2 + CHARSELECT_ROW_INSTR*TEXT_ROW_BYTES)
    sta.l DmaRequest_TargetAddr
    lda #TEXT_ROW_BYTES
    sta.l DmaRequest_Length
    sep #$20
.a8
    lda #$7E
    sta.l DmaRequest_SourceBank
    lda #DMA_TYPE_VRAM
    sta.l DmaRequest_TypeFlags
    rep #$31
.a16
.i16
    jsl Core_Dma_Enqueue_Long
    rtl

BorSetSelect_Strings:
BorSetSelect_Prefix:
    .db "DIFFICULTY < ", 0
BorSetSelect_Suffix:
    .db ">", 0
BorSetSelect_Back:
    .db "Back", 0
BorSetSelect_Ready:
    .db "START", 0
BorSetSelect_Locked:
    .db "LOCKED", 0
BorSetSelect_Off:
    .db "OFF", 0
