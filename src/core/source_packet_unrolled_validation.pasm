; Resume the exact original fifth-row guard at physical slot6.
; Entries0..6 have already passed original active flags and owner checks.
; Other layouts retain the original conservative rejection.
SourcePacket_UnrolledQueue:
.a16
.i16
    pha
    lda.l SourceReserve_Valid
    cmp #$1D1F
    bne SourcePacket_ResumeFallback
    lda.l SOURCE_PACKET_ACTIVE_META+12
    cmp #$0016
    bne SourcePacket_ResumeFallback
    lda.l SOURCE_PACKET_ACTIVE_META+44
    cmp #$0016
    bne SourcePacket_ResumeFallback
    cpx #48
    beq SourcePacket_ResumeBudget
SourcePacket_ResumeFallback:
.a16
.i16
    pla
    jml SourcePacket_NmiPublish__done
SourcePacket_ResumeBudget:
.a16
.i16
    pla
    sta.l SourcePacket_NmiQueueRows
    .db $F4
    .dw ((SourcePacket_NmiPublish__queue_scanned+11)&$FFFF)
    lda #0
    sta.l SourcePacket_NmiQueueTotal
    ldx #0
SourcePacket_Resume0_row:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    bne SourcePacket_Resume0_active
    brl SourcePacket_Resume0_next
SourcePacket_Resume0_active:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    sta.l SourcePacket_NmiRowType
    lda.l DmaQueue,x
    bne SourcePacket_Resume0_guard0
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume0_guard0:
.a16
.i16
    cmp #257
    bcc SourcePacket_Resume0_guard1
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume0_guard1:
.a16
.i16
    sta.l SourcePacket_NmiRowLength
    and #1
    beq SourcePacket_Resume0_guard2
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume0_guard2:
.a16
.i16
    lda.l DmaQueue+2,x
    and #1
    beq SourcePacket_Resume0_guard3
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume0_guard3:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    clc
    adc.l SourcePacket_NmiQueueTotal
    cmp #257
    bcc SourcePacket_Resume0_guard4
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume0_guard4:
.a16
.i16
    sta.l SourcePacket_NmiQueueTotal
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    beq SourcePacket_Resume0_source_bank
    cmp #$7F
    beq SourcePacket_Resume0_source_bank
    cmp #$40
    bcc SourcePacket_Resume0_rom_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume0_rom_bank:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$8000
    bcs SourcePacket_Resume0_source_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume0_source_bank:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    dec a
    sta.l SourcePacket_NmiRowSpan
    lda.l DmaQueue+5,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_Resume0_source_range
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume0_source_range:
.a16
.i16
    lda.l SourcePacket_NmiRowType
    cmp #$42
    beq SourcePacket_Resume0_palette_range
    ; Generic background work must not overwrite any of the64 held OBJ
    ; cache blocks at VRAM8000..BFFF, even if a bad row claims owner0.
    lda.l DmaQueue+2,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_Resume0_target_valid
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume0_target_valid:
.a16
.i16
    sta.l SourcePacket_NmiTargetEnd
    lda.l DmaQueue+2,x
    cmp #$8000
    bcc SourcePacket_Resume0_below_obj
    cmp #$C000
    bcs SourcePacket_Resume0_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume0_below_obj:
.a16
.i16
    lda.l SourcePacket_NmiTargetEnd
    cmp #$8000
    bcc SourcePacket_Resume0_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume0_palette_range:
.a16
.i16
    ; Background CGRAM is byte0..255. OBJ palettes remain resource-owned.
    lda.l DmaQueue+2,x
    cmp #256
    bcc SourcePacket_Resume0_palette_target
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume0_palette_target:
.a16
.i16
    clc
    adc.l SourcePacket_NmiRowLength
    cmp #257
    bcc SourcePacket_Resume0_next
    jml SourcePacket_CheckBackgroundBudget__bad

SourcePacket_Resume0_next:
.a16
.i16
    ldx #8
SourcePacket_Resume1_row:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    bne SourcePacket_Resume1_active
    brl SourcePacket_Resume1_next
SourcePacket_Resume1_active:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    sta.l SourcePacket_NmiRowType
    lda.l DmaQueue,x
    bne SourcePacket_Resume1_guard0
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume1_guard0:
.a16
.i16
    cmp #257
    bcc SourcePacket_Resume1_guard1
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume1_guard1:
.a16
.i16
    sta.l SourcePacket_NmiRowLength
    and #1
    beq SourcePacket_Resume1_guard2
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume1_guard2:
.a16
.i16
    lda.l DmaQueue+2,x
    and #1
    beq SourcePacket_Resume1_guard3
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume1_guard3:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    clc
    adc.l SourcePacket_NmiQueueTotal
    cmp #257
    bcc SourcePacket_Resume1_guard4
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume1_guard4:
.a16
.i16
    sta.l SourcePacket_NmiQueueTotal
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    beq SourcePacket_Resume1_source_bank
    cmp #$7F
    beq SourcePacket_Resume1_source_bank
    cmp #$40
    bcc SourcePacket_Resume1_rom_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume1_rom_bank:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$8000
    bcs SourcePacket_Resume1_source_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume1_source_bank:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    dec a
    sta.l SourcePacket_NmiRowSpan
    lda.l DmaQueue+5,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_Resume1_source_range
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume1_source_range:
.a16
.i16
    lda.l SourcePacket_NmiRowType
    cmp #$42
    beq SourcePacket_Resume1_palette_range
    ; Generic background work must not overwrite any of the64 held OBJ
    ; cache blocks at VRAM8000..BFFF, even if a bad row claims owner0.
    lda.l DmaQueue+2,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_Resume1_target_valid
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume1_target_valid:
.a16
.i16
    sta.l SourcePacket_NmiTargetEnd
    lda.l DmaQueue+2,x
    cmp #$8000
    bcc SourcePacket_Resume1_below_obj
    cmp #$C000
    bcs SourcePacket_Resume1_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume1_below_obj:
.a16
.i16
    lda.l SourcePacket_NmiTargetEnd
    cmp #$8000
    bcc SourcePacket_Resume1_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume1_palette_range:
.a16
.i16
    ; Background CGRAM is byte0..255. OBJ palettes remain resource-owned.
    lda.l DmaQueue+2,x
    cmp #256
    bcc SourcePacket_Resume1_palette_target
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume1_palette_target:
.a16
.i16
    clc
    adc.l SourcePacket_NmiRowLength
    cmp #257
    bcc SourcePacket_Resume1_next
    jml SourcePacket_CheckBackgroundBudget__bad

SourcePacket_Resume1_next:
.a16
.i16
    ldx #16
SourcePacket_Resume2_row:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    bne SourcePacket_Resume2_active
    brl SourcePacket_Resume2_next
SourcePacket_Resume2_active:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    sta.l SourcePacket_NmiRowType
    lda.l DmaQueue,x
    bne SourcePacket_Resume2_guard0
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume2_guard0:
.a16
.i16
    cmp #257
    bcc SourcePacket_Resume2_guard1
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume2_guard1:
.a16
.i16
    sta.l SourcePacket_NmiRowLength
    and #1
    beq SourcePacket_Resume2_guard2
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume2_guard2:
.a16
.i16
    lda.l DmaQueue+2,x
    and #1
    beq SourcePacket_Resume2_guard3
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume2_guard3:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    clc
    adc.l SourcePacket_NmiQueueTotal
    cmp #257
    bcc SourcePacket_Resume2_guard4
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume2_guard4:
.a16
.i16
    sta.l SourcePacket_NmiQueueTotal
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    beq SourcePacket_Resume2_source_bank
    cmp #$7F
    beq SourcePacket_Resume2_source_bank
    cmp #$40
    bcc SourcePacket_Resume2_rom_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume2_rom_bank:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$8000
    bcs SourcePacket_Resume2_source_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume2_source_bank:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    dec a
    sta.l SourcePacket_NmiRowSpan
    lda.l DmaQueue+5,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_Resume2_source_range
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume2_source_range:
.a16
.i16
    lda.l SourcePacket_NmiRowType
    cmp #$42
    beq SourcePacket_Resume2_palette_range
    ; Generic background work must not overwrite any of the64 held OBJ
    ; cache blocks at VRAM8000..BFFF, even if a bad row claims owner0.
    lda.l DmaQueue+2,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_Resume2_target_valid
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume2_target_valid:
.a16
.i16
    sta.l SourcePacket_NmiTargetEnd
    lda.l DmaQueue+2,x
    cmp #$8000
    bcc SourcePacket_Resume2_below_obj
    cmp #$C000
    bcs SourcePacket_Resume2_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume2_below_obj:
.a16
.i16
    lda.l SourcePacket_NmiTargetEnd
    cmp #$8000
    bcc SourcePacket_Resume2_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume2_palette_range:
.a16
.i16
    ; Background CGRAM is byte0..255. OBJ palettes remain resource-owned.
    lda.l DmaQueue+2,x
    cmp #256
    bcc SourcePacket_Resume2_palette_target
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume2_palette_target:
.a16
.i16
    clc
    adc.l SourcePacket_NmiRowLength
    cmp #257
    bcc SourcePacket_Resume2_next
    jml SourcePacket_CheckBackgroundBudget__bad

SourcePacket_Resume2_next:
.a16
.i16
    ldx #24
SourcePacket_Resume3_row:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    bne SourcePacket_Resume3_active
    brl SourcePacket_Resume3_next
SourcePacket_Resume3_active:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    sta.l SourcePacket_NmiRowType
    lda.l DmaQueue,x
    bne SourcePacket_Resume3_guard0
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume3_guard0:
.a16
.i16
    cmp #257
    bcc SourcePacket_Resume3_guard1
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume3_guard1:
.a16
.i16
    sta.l SourcePacket_NmiRowLength
    and #1
    beq SourcePacket_Resume3_guard2
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume3_guard2:
.a16
.i16
    lda.l DmaQueue+2,x
    and #1
    beq SourcePacket_Resume3_guard3
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume3_guard3:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    clc
    adc.l SourcePacket_NmiQueueTotal
    cmp #257
    bcc SourcePacket_Resume3_guard4
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume3_guard4:
.a16
.i16
    sta.l SourcePacket_NmiQueueTotal
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    beq SourcePacket_Resume3_source_bank
    cmp #$7F
    beq SourcePacket_Resume3_source_bank
    cmp #$40
    bcc SourcePacket_Resume3_rom_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume3_rom_bank:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$8000
    bcs SourcePacket_Resume3_source_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume3_source_bank:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    dec a
    sta.l SourcePacket_NmiRowSpan
    lda.l DmaQueue+5,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_Resume3_source_range
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume3_source_range:
.a16
.i16
    lda.l SourcePacket_NmiRowType
    cmp #$42
    beq SourcePacket_Resume3_palette_range
    ; Generic background work must not overwrite any of the64 held OBJ
    ; cache blocks at VRAM8000..BFFF, even if a bad row claims owner0.
    lda.l DmaQueue+2,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_Resume3_target_valid
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume3_target_valid:
.a16
.i16
    sta.l SourcePacket_NmiTargetEnd
    lda.l DmaQueue+2,x
    cmp #$8000
    bcc SourcePacket_Resume3_below_obj
    cmp #$C000
    bcs SourcePacket_Resume3_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume3_below_obj:
.a16
.i16
    lda.l SourcePacket_NmiTargetEnd
    cmp #$8000
    bcc SourcePacket_Resume3_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume3_palette_range:
.a16
.i16
    ; Background CGRAM is byte0..255. OBJ palettes remain resource-owned.
    lda.l DmaQueue+2,x
    cmp #256
    bcc SourcePacket_Resume3_palette_target
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume3_palette_target:
.a16
.i16
    clc
    adc.l SourcePacket_NmiRowLength
    cmp #257
    bcc SourcePacket_Resume3_next
    jml SourcePacket_CheckBackgroundBudget__bad

SourcePacket_Resume3_next:
.a16
.i16
    ldx #32
SourcePacket_Resume4_row:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    bne SourcePacket_Resume4_active
    brl SourcePacket_Resume4_next
SourcePacket_Resume4_active:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    sta.l SourcePacket_NmiRowType
    lda.l DmaQueue,x
    bne SourcePacket_Resume4_guard0
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume4_guard0:
.a16
.i16
    cmp #257
    bcc SourcePacket_Resume4_guard1
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume4_guard1:
.a16
.i16
    sta.l SourcePacket_NmiRowLength
    and #1
    beq SourcePacket_Resume4_guard2
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume4_guard2:
.a16
.i16
    lda.l DmaQueue+2,x
    and #1
    beq SourcePacket_Resume4_guard3
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume4_guard3:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    clc
    adc.l SourcePacket_NmiQueueTotal
    cmp #257
    bcc SourcePacket_Resume4_guard4
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume4_guard4:
.a16
.i16
    sta.l SourcePacket_NmiQueueTotal
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    beq SourcePacket_Resume4_source_bank
    cmp #$7F
    beq SourcePacket_Resume4_source_bank
    cmp #$40
    bcc SourcePacket_Resume4_rom_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume4_rom_bank:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$8000
    bcs SourcePacket_Resume4_source_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume4_source_bank:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    dec a
    sta.l SourcePacket_NmiRowSpan
    lda.l DmaQueue+5,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_Resume4_source_range
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume4_source_range:
.a16
.i16
    lda.l SourcePacket_NmiRowType
    cmp #$42
    beq SourcePacket_Resume4_palette_range
    ; Generic background work must not overwrite any of the64 held OBJ
    ; cache blocks at VRAM8000..BFFF, even if a bad row claims owner0.
    lda.l DmaQueue+2,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_Resume4_target_valid
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume4_target_valid:
.a16
.i16
    sta.l SourcePacket_NmiTargetEnd
    lda.l DmaQueue+2,x
    cmp #$8000
    bcc SourcePacket_Resume4_below_obj
    cmp #$C000
    bcs SourcePacket_Resume4_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume4_below_obj:
.a16
.i16
    lda.l SourcePacket_NmiTargetEnd
    cmp #$8000
    bcc SourcePacket_Resume4_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume4_palette_range:
.a16
.i16
    ; Background CGRAM is byte0..255. OBJ palettes remain resource-owned.
    lda.l DmaQueue+2,x
    cmp #256
    bcc SourcePacket_Resume4_palette_target
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume4_palette_target:
.a16
.i16
    clc
    adc.l SourcePacket_NmiRowLength
    cmp #257
    bcc SourcePacket_Resume4_next
    jml SourcePacket_CheckBackgroundBudget__bad

SourcePacket_Resume4_next:
.a16
.i16
    ldx #40
SourcePacket_Resume5_row:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    bne SourcePacket_Resume5_active
    brl SourcePacket_Resume5_next
SourcePacket_Resume5_active:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    sta.l SourcePacket_NmiRowType
    lda.l DmaQueue,x
    bne SourcePacket_Resume5_guard0
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume5_guard0:
.a16
.i16
    cmp #257
    bcc SourcePacket_Resume5_guard1
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume5_guard1:
.a16
.i16
    sta.l SourcePacket_NmiRowLength
    and #1
    beq SourcePacket_Resume5_guard2
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume5_guard2:
.a16
.i16
    lda.l DmaQueue+2,x
    and #1
    beq SourcePacket_Resume5_guard3
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume5_guard3:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    clc
    adc.l SourcePacket_NmiQueueTotal
    cmp #257
    bcc SourcePacket_Resume5_guard4
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume5_guard4:
.a16
.i16
    sta.l SourcePacket_NmiQueueTotal
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    beq SourcePacket_Resume5_source_bank
    cmp #$7F
    beq SourcePacket_Resume5_source_bank
    cmp #$40
    bcc SourcePacket_Resume5_rom_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume5_rom_bank:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$8000
    bcs SourcePacket_Resume5_source_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume5_source_bank:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    dec a
    sta.l SourcePacket_NmiRowSpan
    lda.l DmaQueue+5,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_Resume5_source_range
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume5_source_range:
.a16
.i16
    lda.l SourcePacket_NmiRowType
    cmp #$42
    beq SourcePacket_Resume5_palette_range
    ; Generic background work must not overwrite any of the64 held OBJ
    ; cache blocks at VRAM8000..BFFF, even if a bad row claims owner0.
    lda.l DmaQueue+2,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_Resume5_target_valid
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume5_target_valid:
.a16
.i16
    sta.l SourcePacket_NmiTargetEnd
    lda.l DmaQueue+2,x
    cmp #$8000
    bcc SourcePacket_Resume5_below_obj
    cmp #$C000
    bcs SourcePacket_Resume5_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume5_below_obj:
.a16
.i16
    lda.l SourcePacket_NmiTargetEnd
    cmp #$8000
    bcc SourcePacket_Resume5_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume5_palette_range:
.a16
.i16
    ; Background CGRAM is byte0..255. OBJ palettes remain resource-owned.
    lda.l DmaQueue+2,x
    cmp #256
    bcc SourcePacket_Resume5_palette_target
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume5_palette_target:
.a16
.i16
    clc
    adc.l SourcePacket_NmiRowLength
    cmp #257
    bcc SourcePacket_Resume5_next
    jml SourcePacket_CheckBackgroundBudget__bad

SourcePacket_Resume5_next:
.a16
.i16
    ldx #48
SourcePacket_Resume6_row:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    bne SourcePacket_Resume6_active
    brl SourcePacket_Resume6_next
SourcePacket_Resume6_active:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    sta.l SourcePacket_NmiRowType
    lda.l DmaQueue,x
    bne SourcePacket_Resume6_guard0
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume6_guard0:
.a16
.i16
    cmp #257
    bcc SourcePacket_Resume6_guard1
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume6_guard1:
.a16
.i16
    sta.l SourcePacket_NmiRowLength
    and #1
    beq SourcePacket_Resume6_guard2
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume6_guard2:
.a16
.i16
    lda.l DmaQueue+2,x
    and #1
    beq SourcePacket_Resume6_guard3
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume6_guard3:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    clc
    adc.l SourcePacket_NmiQueueTotal
    cmp #257
    bcc SourcePacket_Resume6_guard4
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume6_guard4:
.a16
.i16
    sta.l SourcePacket_NmiQueueTotal
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    beq SourcePacket_Resume6_source_bank
    cmp #$7F
    beq SourcePacket_Resume6_source_bank
    cmp #$40
    bcc SourcePacket_Resume6_rom_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume6_rom_bank:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$8000
    bcs SourcePacket_Resume6_source_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume6_source_bank:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    dec a
    sta.l SourcePacket_NmiRowSpan
    lda.l DmaQueue+5,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_Resume6_source_range
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume6_source_range:
.a16
.i16
    lda.l SourcePacket_NmiRowType
    cmp #$42
    beq SourcePacket_Resume6_palette_range
    ; Generic background work must not overwrite any of the64 held OBJ
    ; cache blocks at VRAM8000..BFFF, even if a bad row claims owner0.
    lda.l DmaQueue+2,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_Resume6_target_valid
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume6_target_valid:
.a16
.i16
    sta.l SourcePacket_NmiTargetEnd
    lda.l DmaQueue+2,x
    cmp #$8000
    bcc SourcePacket_Resume6_below_obj
    cmp #$C000
    bcs SourcePacket_Resume6_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume6_below_obj:
.a16
.i16
    lda.l SourcePacket_NmiTargetEnd
    cmp #$8000
    bcc SourcePacket_Resume6_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume6_palette_range:
.a16
.i16
    ; Background CGRAM is byte0..255. OBJ palettes remain resource-owned.
    lda.l DmaQueue+2,x
    cmp #256
    bcc SourcePacket_Resume6_palette_target
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume6_palette_target:
.a16
.i16
    clc
    adc.l SourcePacket_NmiRowLength
    cmp #257
    bcc SourcePacket_Resume6_next
    jml SourcePacket_CheckBackgroundBudget__bad

SourcePacket_Resume6_next:
.a16
.i16
    ldx #56
SourcePacket_Resume7_row:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    bne SourcePacket_Resume7_active
    brl SourcePacket_Resume7_next
SourcePacket_Resume7_active:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    sta.l SourcePacket_NmiRowType
    cmp #$40
    beq SourcePacket_Resume7_flags
    cmp #$42
    beq SourcePacket_Resume7_flags
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume7_flags:
.a16
.i16
    lda.l DmaQueue_Owner+7
    and #255
    beq SourcePacket_Resume7_unowned
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume7_unowned:
.a16
.i16
    lda #6
    sta.l SourcePacket_NmiQueueRows
    lda.l DmaQueue,x
    bne SourcePacket_Resume7_guard0
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume7_guard0:
.a16
.i16
    cmp #257
    bcc SourcePacket_Resume7_guard1
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume7_guard1:
.a16
.i16
    sta.l SourcePacket_NmiRowLength
    and #1
    beq SourcePacket_Resume7_guard2
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume7_guard2:
.a16
.i16
    lda.l DmaQueue+2,x
    and #1
    beq SourcePacket_Resume7_guard3
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume7_guard3:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    clc
    adc.l SourcePacket_NmiQueueTotal
    cmp #257
    bcc SourcePacket_Resume7_guard4
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume7_guard4:
.a16
.i16
    sta.l SourcePacket_NmiQueueTotal
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    beq SourcePacket_Resume7_source_bank
    cmp #$7F
    beq SourcePacket_Resume7_source_bank
    cmp #$40
    bcc SourcePacket_Resume7_rom_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume7_rom_bank:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$8000
    bcs SourcePacket_Resume7_source_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume7_source_bank:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    dec a
    sta.l SourcePacket_NmiRowSpan
    lda.l DmaQueue+5,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_Resume7_source_range
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume7_source_range:
.a16
.i16
    lda.l SourcePacket_NmiRowType
    cmp #$42
    beq SourcePacket_Resume7_palette_range
    ; Generic background work must not overwrite any of the64 held OBJ
    ; cache blocks at VRAM8000..BFFF, even if a bad row claims owner0.
    lda.l DmaQueue+2,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_Resume7_target_valid
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume7_target_valid:
.a16
.i16
    sta.l SourcePacket_NmiTargetEnd
    lda.l DmaQueue+2,x
    cmp #$8000
    bcc SourcePacket_Resume7_below_obj
    cmp #$C000
    bcs SourcePacket_Resume7_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume7_below_obj:
.a16
.i16
    lda.l SourcePacket_NmiTargetEnd
    cmp #$8000
    bcc SourcePacket_Resume7_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume7_palette_range:
.a16
.i16
    ; Background CGRAM is byte0..255. OBJ palettes remain resource-owned.
    lda.l DmaQueue+2,x
    cmp #256
    bcc SourcePacket_Resume7_palette_target
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Resume7_palette_target:
.a16
.i16
    clc
    adc.l SourcePacket_NmiRowLength
    cmp #257
    bcc SourcePacket_Resume7_next
    jml SourcePacket_CheckBackgroundBudget__bad

SourcePacket_Resume7_next:
.a16
.i16
    ldx #64
    lda #64
    cpx #64
    jml SourcePacket_CheckBackgroundBudget__good
SourcePacket_UnrolledEnd:
