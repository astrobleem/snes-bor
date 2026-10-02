; S8 Normal opponent HUD. Included in bank 5 by hud_boss.pasm.
; BOR.C: spawn() copies model->name (2391), smartspawn() applies nonempty
; alias (4593); player[].opponent changes on grab/hit/pickup exchanges
; (3074/3087,3492,3593,3936,3982,3991,4414,4501,4558), kill() clears
; BOTH players' references (2425/2427). HP zero alone is not removal.
; Names are presentation only: never write roster, palette, alias or AI.
;
; Native integration is in vm_native_engine ApplyDamage/TryGrab/reuse,
; main VsPlayer, and actor_behavior stage reset/source retirement. The
; pre-draw purge handles native terminal fall/instant-hide/OUT retirement.
; hud_opponent_host.pasm documents physical DP and callback conventions.
; Core API: Target X=player BYTE OFFSET,Y=opponent BYTE OFFSET; Remove
; X=actor BYTE OFFSET. StageTimer's host already converts its slot ordinals.
; Legacy overlap collection adapters are supplied for the pickup owner;
; that owner's dy branches must notify collection before GET/audio/free.
; All hooks preserve A/X/Y/P/D/DBR and are campaign-3 gated. Six slots.
; No new main include/call needed for drawing: existing boss HUD dispatches.
; Build must regenerate stage_environment_bases.pasm from the full Normal
; spawn set; model names are generated independently from ROSTER_CONFIGS.
;
; Private WRAM $7E5A00..$7E5ACF, after timer state at $5900..$591F and
; before VM code $6000. No StageEnv tail reuse (source actor owns that).
; Rows 6 and 10: col1..10 bar, col12..31 full BOR MAX_NAME_LEN=20 name.
; DMA sources are immutable while queued; failed enqueue is retried.
; Reset invalidates rows but never modifies a pending DMA source.
HudOpponent_Targets = $7E5A00       ; two u16 offset+1 handles, zero=null
HudOpponent_Dirty = $7E5A04         ; two bytes (force row refresh)
HudOpponent_Player = $7E5A06        ; word 0/2
HudOpponent_BufferOffset = $7E5A08  ; word 0/64
HudOpponent_NamePtr = $7E5A0A       ; word ROM offset
HudOpponent_NameKind = $7E5A0C      ; word 0=model(bank5), 1=alias(bank13)
HudOpponent_Hp = $7E5A0E           ; byte scratch
HudOpponent_Remaining = $7E5A0F    ; byte scratch
HudOpponent_Rows = $7E5A10        ; 128 bytes, independent pending sources
HudOpponent_Work = $7E5A90        ; 64 bytes, never submitted to DMA
HudOpponent_End = $7E5AD0

HudOpponent_Reset:
    php
    rep #$30
.a16
.i16
    pha
    sep #$20
.a8
    lda.l Game_CampaignId
    cmp #3
    bne HudOpponent_Reset__done
    rep #$20
.a16
    lda #0
    sta.l HudOpponent_Targets
    sta.l HudOpponent_Targets+2
    lda #$0101
    sta.l HudOpponent_Dirty
HudOpponent_Reset__done:
    rep #$20
.a16
    pla
    plp
    rtl

; Validate an exact physical slot offset in A16. Carry set if valid.
HudOpponent_ValidSlot:
.a16
.i16
    cmp #0
    beq HudOpponent_ValidSlot__yes
    cmp #CHAR_ZP_LEN
    beq HudOpponent_ValidSlot__yes
    cmp #CHAR_ZP_LEN*2
    beq HudOpponent_ValidSlot__yes
    cmp #CHAR_ZP_LEN*3
    beq HudOpponent_ValidSlot__yes
    cmp #CHAR_ZP_LEN*4
    beq HudOpponent_ValidSlot__yes
    cmp #CHAR_ZP_LEN*5
    beq HudOpponent_ValidSlot__yes
    clc
    rts
HudOpponent_ValidSlot__yes:
    sec
    rts

HudOpponent_Target:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    lda.l Game_CampaignId
    and #$FF
    cmp #3
    bne HudOpponent_Target__done
    tya
    jsr HudOpponent_ValidSlot
    bcc HudOpponent_Target__done
    txa
    cmp #0
    beq HudOpponent_Target__p1
    cmp #CHAR_ZP_LEN
    bne HudOpponent_Target__done
    lda.l G13_TwoPlayerEnabled
    and #$FF
    beq HudOpponent_Target__done
    ldx #2
    bra HudOpponent_Target__store
HudOpponent_Target__p1:
.a16
.i16
    ldx #0
HudOpponent_Target__store:
    tya
    inc a
    sta.l HudOpponent_Targets,x
HudOpponent_Target__done:
    ply
    plx
    pla
    plp
    rtl

HudOpponent_Remove:
    php
    rep #$30
.a16
.i16
    pha
    phx
    lda.l Game_CampaignId
    and #$FF
    cmp #3
    bne HudOpponent_Remove__done
    txa
    jsr HudOpponent_ValidSlot
    bcc HudOpponent_Remove__done
    inc a
    cmp.l HudOpponent_Targets
    bne HudOpponent_Remove__p2
    pha
    lda #0
    sta.l HudOpponent_Targets
    pla
HudOpponent_Remove__p2:
.a16
.i16
    cmp.l HudOpponent_Targets+2
    bne HudOpponent_Remove__done
    lda #0
    sta.l HudOpponent_Targets+2
HudOpponent_Remove__done:
    plx
    pla
    plp
    rtl

HudOpponent_Play:
    jsl HudOpponentHost_PurgeRetired
    rep #$30
.a16
.i16
    lda #0
    sta.l HudOpponent_Player
    sta.l HudOpponent_BufferOffset
    jsr HudOpponent_Row
    rep #$30
.a16
.i16
    lda #2
    sta.l HudOpponent_Player
    lda #64
    sta.l HudOpponent_BufferOffset
    jsr HudOpponent_Row
    rtl

HudOpponent_Row:
    ; Do not overwrite either staging source until its prior DMA drained.
    rep #$30
.a16
.i16
    ldx #0
HudOpponent_Row__pending:
.a16
.i16
    lda.l DmaQueue+4,x
    and #DMA_OPT_ACTIVE
    beq HudOpponent_Row__next
    lda.l DmaQueue+7,x
    and #$FF
    cmp #$7E
    bne HudOpponent_Row__next
    lda.l HudOpponent_BufferOffset
    clc
    adc #HudOpponent_Rows & $FFFF
    cmp.l DmaQueue+5,x
    bne HudOpponent_Row__next
    rts
HudOpponent_Row__next:
.a16
.i16
    txa
    clc
    adc #DMA_QUEUE_SLOT_SIZE
    tax
    cpx #DMA_QUEUE_SLOTS*DMA_QUEUE_SLOT_SIZE
    bcc HudOpponent_Row__pending
    ldx #0
    lda #0
HudOpponent_Row__clear:
.a16
.i16
    sta.l HudOpponent_Work,x
    inx
    inx
    cpx #64
    bcc HudOpponent_Row__clear
    lda.l HudOpponent_Player
    tax
    beq HudOpponent_Row__target
    lda.l G13_TwoPlayerEnabled
    and #$FF
    bne HudOpponent_Row__target
    brl HudOpponent_Row__compare
HudOpponent_Row__target:
    lda.l HudOpponent_Targets,x
    bne HudOpponent_Row__have
    brl HudOpponent_Row__compare
HudOpponent_Row__have:
    dec a
    jsr HudOpponent_ValidSlot
    bcs HudOpponent_Row__valid
    brl HudOpponent_Row__compare
HudOpponent_Row__valid:
.a16
.i16
    tax
    lda.l $7E0A00+CHAR_HP,x
    and #$FF
    sta.l HudOpponent_Hp       ; high byte initializes bar scratch too
    lda.l StageEnv_AliasId,x
    beq HudOpponent_Row__model
    cmp #(StageEnv_AliasName1-StageEnv_AliasNamePtrs)/2
    bcs HudOpponent_Row__model
    asl a
    tay
    phx
    tyx
    lda.l StageEnv_AliasNamePtrs,x
    sta.l HudOpponent_NamePtr
    tax
    lda.l $0D0000,x
    and #$FF
    plx
    beq HudOpponent_Row__model ; empty alias has model fallback
    lda #1
    sta.l HudOpponent_NameKind
    bra HudOpponent_Row__draw
HudOpponent_Row__model:
.a16
.i16
    lda.l $7E0A00+CHAR_ROSTER_INDEX,x
    and #$FF
    cmp #HudOpponent_ModelCount
    bcc HudOpponent_Row__known
    lda #HudOpponent_Unknown
    bra HudOpponent_Row__modelptr
HudOpponent_Row__known:
    asl a
    tax
    lda.l HudOpponent_ModelPtrs,x
HudOpponent_Row__modelptr:
.a16
.i16
    sta.l HudOpponent_NamePtr
    lda #0
    sta.l HudOpponent_NameKind
HudOpponent_Row__draw:
.a16
.i16
    jsr HudOpponent_DrawBar
    ldy #24                  ; name starts at column 12
HudOpponent_Row__char:
    rep #$30
.a16
.i16
    lda.l HudOpponent_NamePtr
    tax
    lda.l HudOpponent_NameKind
    beq HudOpponent_Row__modelchar
    lda.l $0D0000,x
    bra HudOpponent_Row__glyph
HudOpponent_Row__modelchar:
    lda.l $050000,x
HudOpponent_Row__glyph:
.a16
.i16
    and #$FF
    beq HudOpponent_Row__compare
    cmp #FONT_ASCII_FIRST
    bcc HudOpponent_Row__replace
    cmp #FONT_ASCII_LAST+1
    bcc HudOpponent_Row__print
HudOpponent_Row__replace:
.a16
.i16
    lda #63                  ; '?' for unavailable font glyphs
HudOpponent_Row__print:
.a16
.i16
    sec
    sbc #FONT_ASCII_FIRST
    clc
    adc #FONT_TILE_INDEX_BASE
    ora #$2000 | (FONT_CGRAM_PAL_ID << 10)
    tyx
    sta.l HudOpponent_Work,x
    lda.l HudOpponent_NamePtr
    inc a
    sta.l HudOpponent_NamePtr
    iny
    iny
    cpy #64
    bcc HudOpponent_Row__char
HudOpponent_Row__compare:
    rep #$30
.a16
.i16
    lda.l HudOpponent_Player
    lsr a
    tax
    sep #$20
.a8
    lda.l HudOpponent_Dirty,x
    bne HudOpponent_Row__copy
    rep #$20
.a16
    lda.l HudOpponent_BufferOffset
    tax
    ldy #0
HudOpponent_Row__equal:
.a16
.i16
    phx
    tyx
    lda.l HudOpponent_Work,x
    plx
    cmp.l HudOpponent_Rows,x
    bne HudOpponent_Row__copy
    inx
    inx
    iny
    iny
    cpy #64
    bcc HudOpponent_Row__equal
    rts
HudOpponent_Row__copy:
    rep #$30
.a16
.i16
    lda.l HudOpponent_Player
    lsr a
    tax
    sep #$20
.a8
    lda #1
    sta.l HudOpponent_Dirty,x ; keep dirty until enqueue succeeds
    rep #$20
.a16
    lda.l HudOpponent_BufferOffset
    tax
    ldy #0
HudOpponent_Row__copyloop:
.a16
.i16
    phx
    tyx
    lda.l HudOpponent_Work,x
    plx
    sta.l HudOpponent_Rows,x
    inx
    inx
    iny
    iny
    cpy #64
    bcc HudOpponent_Row__copyloop
    lda.l HudOpponent_BufferOffset
    clc
    adc #HudOpponent_Rows & $FFFF
    sta.l DmaRequest_SourceAddrLow
    lda #64
    sta.l DmaRequest_Length
    lda.l HudOpponent_Player
    beq HudOpponent_Row__p1addr
    lda #(BG3_TILEMAP_VRAM_WORD+10*TEXT_ROW_ENTRIES)*2
    bra HudOpponent_Row__address
HudOpponent_Row__p1addr:
.a16
.i16
    lda #(BG3_TILEMAP_VRAM_WORD+HUD_ROW_BOSS*TEXT_ROW_ENTRIES)*2
HudOpponent_Row__address:
    sta.l DmaRequest_TargetAddr
    sep #$20
.a8
    lda #$7E
    sta.l DmaRequest_SourceBank
    lda #DMA_TYPE_VRAM
    sta.l DmaRequest_TypeFlags
    rep #$30
.a16
.i16
    jsl Core_Dma_Enqueue_Long
    bcc HudOpponent_Row__done
    lda.l HudOpponent_Player
    lsr a
    tax
    sep #$20
.a8
    lda #0
    sta.l HudOpponent_Dirty,x
HudOpponent_Row__done:
    rts

HudOpponent_DrawBar:
    rep #$30
.a16
.i16
    lda #HUD_TILE_CAP_LEFT | (HUD_ENTRY_HIGH << 8)
    sta.l HudOpponent_Work+2
    ldx #4
HudOpponent_DrawBar__body:
.a16
.i16
    lda.l HudOpponent_Hp
    and #$FF
    cmp #8
    bcc HudOpponent_DrawBar__partial
    sec
    sbc #8
    sta.l HudOpponent_Hp
    lda #8
    bra HudOpponent_DrawBar__tile
HudOpponent_DrawBar__partial:
.a16
.i16
    pha
    lda #0
    sta.l HudOpponent_Hp
    pla
HudOpponent_DrawBar__tile:
.a16
.i16
    clc
    adc #HUD_TILE_FILL_BASE
    ora #HUD_ENTRY_HIGH << 8
    sta.l HudOpponent_Work,x
    inx
    inx
    cpx #20
    bcc HudOpponent_DrawBar__body
    lda #HUD_TILE_CAP_RIGHT | (HUD_ENTRY_HIGH << 8)
    sta.l HudOpponent_Work+20
    rts

.include "../generated/hud_opponent_names.pasm"
.include "hud_opponent_host.pasm"
