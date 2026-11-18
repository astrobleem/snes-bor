; Ready-idle retry only after the original fifth-row rejection.
; One pass validates flags, ownership, counts, source/target and byte budget.
SourcePacket_UnrolledQueue:
.a16
.i16
    lda.l SourceReserve_Valid
    cmp #$1D1F
    bne SourcePacket_SingleFallback
    lda.l SOURCE_PACKET_ACTIVE_META+12
    cmp #$0016
    bne SourcePacket_SingleFallback
    lda.l SOURCE_PACKET_ACTIVE_META+44
    cmp #$0016
    beq SourcePacket_SingleIdle
SourcePacket_SingleFallback:
.a16
.i16
    jml SourcePacket_NmiPublish__done
SourcePacket_SingleIdle:
.a16
.i16
    .db $F4
    .dw ((SourcePacket_NmiPublish__queue_scanned+11)&$FFFF)
    lda #0
    sta.l SourcePacket_NmiQueueRows
    sta.l SourcePacket_NmiQueueTotal
    ldx #0
SourcePacket_Single0_row:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    bne SourcePacket_Single0_active
    brl SourcePacket_Single0_next
SourcePacket_Single0_active:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    sta.l SourcePacket_NmiRowType
    cmp #$40
    beq SourcePacket_Single0_flags
    cmp #$42
    beq SourcePacket_Single0_flags
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single0_flags:
.a16
.i16
    lda.l DmaQueue_Owner+0
    and #255
    beq SourcePacket_Single0_unowned
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single0_unowned:
.a16
.i16
    lda.l SourcePacket_NmiQueueRows
    inc a
    cmp #7
    bcc SourcePacket_Single0_counted
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single0_counted:
.a16
.i16
    sta.l SourcePacket_NmiQueueRows
    lda.l DmaQueue,x
    bne SourcePacket_Single0_guard0
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single0_guard0:
.a16
.i16
    cmp #257
    bcc SourcePacket_Single0_guard1
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single0_guard1:
.a16
.i16
    sta.l SourcePacket_NmiRowLength
    and #1
    beq SourcePacket_Single0_guard2
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single0_guard2:
.a16
.i16
    lda.l DmaQueue+2,x
    and #1
    beq SourcePacket_Single0_guard3
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single0_guard3:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    clc
    adc.l SourcePacket_NmiQueueTotal
    cmp #257
    bcc SourcePacket_Single0_guard4
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single0_guard4:
.a16
.i16
    sta.l SourcePacket_NmiQueueTotal
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    beq SourcePacket_Single0_source_bank
    cmp #$7F
    beq SourcePacket_Single0_source_bank
    cmp #$40
    bcc SourcePacket_Single0_rom_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single0_rom_bank:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$8000
    bcs SourcePacket_Single0_source_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single0_source_bank:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    dec a
    sta.l SourcePacket_NmiRowSpan
    lda.l DmaQueue+5,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_Single0_source_range
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single0_source_range:
.a16
.i16
    lda.l SourcePacket_NmiRowType
    cmp #$42
    beq SourcePacket_Single0_palette_range
    ; Generic background work must not overwrite any of the64 held OBJ
    ; cache blocks at VRAM8000..BFFF, even if a bad row claims owner0.
    lda.l DmaQueue+2,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_Single0_target_valid
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single0_target_valid:
.a16
.i16
    sta.l SourcePacket_NmiTargetEnd
    lda.l DmaQueue+2,x
    cmp #$8000
    bcc SourcePacket_Single0_below_obj
    cmp #$C000
    bcs SourcePacket_Single0_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single0_below_obj:
.a16
.i16
    lda.l SourcePacket_NmiTargetEnd
    cmp #$8000
    bcc SourcePacket_Single0_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single0_palette_range:
.a16
.i16
    ; Background CGRAM is byte0..255. OBJ palettes remain resource-owned.
    lda.l DmaQueue+2,x
    cmp #256
    bcc SourcePacket_Single0_palette_target
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single0_palette_target:
.a16
.i16
    clc
    adc.l SourcePacket_NmiRowLength
    cmp #257
    bcc SourcePacket_Single0_next
    jml SourcePacket_CheckBackgroundBudget__bad

SourcePacket_Single0_next:
.a16
.i16
    ldx #8
SourcePacket_Single1_row:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    bne SourcePacket_Single1_active
    brl SourcePacket_Single1_next
SourcePacket_Single1_active:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    sta.l SourcePacket_NmiRowType
    cmp #$40
    beq SourcePacket_Single1_flags
    cmp #$42
    beq SourcePacket_Single1_flags
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single1_flags:
.a16
.i16
    lda.l DmaQueue_Owner+1
    and #255
    beq SourcePacket_Single1_unowned
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single1_unowned:
.a16
.i16
    lda.l SourcePacket_NmiQueueRows
    inc a
    cmp #7
    bcc SourcePacket_Single1_counted
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single1_counted:
.a16
.i16
    sta.l SourcePacket_NmiQueueRows
    lda.l DmaQueue,x
    bne SourcePacket_Single1_guard0
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single1_guard0:
.a16
.i16
    cmp #257
    bcc SourcePacket_Single1_guard1
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single1_guard1:
.a16
.i16
    sta.l SourcePacket_NmiRowLength
    and #1
    beq SourcePacket_Single1_guard2
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single1_guard2:
.a16
.i16
    lda.l DmaQueue+2,x
    and #1
    beq SourcePacket_Single1_guard3
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single1_guard3:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    clc
    adc.l SourcePacket_NmiQueueTotal
    cmp #257
    bcc SourcePacket_Single1_guard4
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single1_guard4:
.a16
.i16
    sta.l SourcePacket_NmiQueueTotal
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    beq SourcePacket_Single1_source_bank
    cmp #$7F
    beq SourcePacket_Single1_source_bank
    cmp #$40
    bcc SourcePacket_Single1_rom_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single1_rom_bank:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$8000
    bcs SourcePacket_Single1_source_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single1_source_bank:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    dec a
    sta.l SourcePacket_NmiRowSpan
    lda.l DmaQueue+5,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_Single1_source_range
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single1_source_range:
.a16
.i16
    lda.l SourcePacket_NmiRowType
    cmp #$42
    beq SourcePacket_Single1_palette_range
    ; Generic background work must not overwrite any of the64 held OBJ
    ; cache blocks at VRAM8000..BFFF, even if a bad row claims owner0.
    lda.l DmaQueue+2,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_Single1_target_valid
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single1_target_valid:
.a16
.i16
    sta.l SourcePacket_NmiTargetEnd
    lda.l DmaQueue+2,x
    cmp #$8000
    bcc SourcePacket_Single1_below_obj
    cmp #$C000
    bcs SourcePacket_Single1_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single1_below_obj:
.a16
.i16
    lda.l SourcePacket_NmiTargetEnd
    cmp #$8000
    bcc SourcePacket_Single1_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single1_palette_range:
.a16
.i16
    ; Background CGRAM is byte0..255. OBJ palettes remain resource-owned.
    lda.l DmaQueue+2,x
    cmp #256
    bcc SourcePacket_Single1_palette_target
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single1_palette_target:
.a16
.i16
    clc
    adc.l SourcePacket_NmiRowLength
    cmp #257
    bcc SourcePacket_Single1_next
    jml SourcePacket_CheckBackgroundBudget__bad

SourcePacket_Single1_next:
.a16
.i16
    ldx #16
SourcePacket_Single2_row:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    bne SourcePacket_Single2_active
    brl SourcePacket_Single2_next
SourcePacket_Single2_active:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    sta.l SourcePacket_NmiRowType
    cmp #$40
    beq SourcePacket_Single2_flags
    cmp #$42
    beq SourcePacket_Single2_flags
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single2_flags:
.a16
.i16
    lda.l DmaQueue_Owner+2
    and #255
    beq SourcePacket_Single2_unowned
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single2_unowned:
.a16
.i16
    lda.l SourcePacket_NmiQueueRows
    inc a
    cmp #7
    bcc SourcePacket_Single2_counted
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single2_counted:
.a16
.i16
    sta.l SourcePacket_NmiQueueRows
    lda.l DmaQueue,x
    bne SourcePacket_Single2_guard0
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single2_guard0:
.a16
.i16
    cmp #257
    bcc SourcePacket_Single2_guard1
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single2_guard1:
.a16
.i16
    sta.l SourcePacket_NmiRowLength
    and #1
    beq SourcePacket_Single2_guard2
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single2_guard2:
.a16
.i16
    lda.l DmaQueue+2,x
    and #1
    beq SourcePacket_Single2_guard3
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single2_guard3:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    clc
    adc.l SourcePacket_NmiQueueTotal
    cmp #257
    bcc SourcePacket_Single2_guard4
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single2_guard4:
.a16
.i16
    sta.l SourcePacket_NmiQueueTotal
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    beq SourcePacket_Single2_source_bank
    cmp #$7F
    beq SourcePacket_Single2_source_bank
    cmp #$40
    bcc SourcePacket_Single2_rom_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single2_rom_bank:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$8000
    bcs SourcePacket_Single2_source_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single2_source_bank:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    dec a
    sta.l SourcePacket_NmiRowSpan
    lda.l DmaQueue+5,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_Single2_source_range
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single2_source_range:
.a16
.i16
    lda.l SourcePacket_NmiRowType
    cmp #$42
    beq SourcePacket_Single2_palette_range
    ; Generic background work must not overwrite any of the64 held OBJ
    ; cache blocks at VRAM8000..BFFF, even if a bad row claims owner0.
    lda.l DmaQueue+2,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_Single2_target_valid
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single2_target_valid:
.a16
.i16
    sta.l SourcePacket_NmiTargetEnd
    lda.l DmaQueue+2,x
    cmp #$8000
    bcc SourcePacket_Single2_below_obj
    cmp #$C000
    bcs SourcePacket_Single2_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single2_below_obj:
.a16
.i16
    lda.l SourcePacket_NmiTargetEnd
    cmp #$8000
    bcc SourcePacket_Single2_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single2_palette_range:
.a16
.i16
    ; Background CGRAM is byte0..255. OBJ palettes remain resource-owned.
    lda.l DmaQueue+2,x
    cmp #256
    bcc SourcePacket_Single2_palette_target
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single2_palette_target:
.a16
.i16
    clc
    adc.l SourcePacket_NmiRowLength
    cmp #257
    bcc SourcePacket_Single2_next
    jml SourcePacket_CheckBackgroundBudget__bad

SourcePacket_Single2_next:
.a16
.i16
    ldx #24
SourcePacket_Single3_row:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    bne SourcePacket_Single3_active
    brl SourcePacket_Single3_next
SourcePacket_Single3_active:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    sta.l SourcePacket_NmiRowType
    cmp #$40
    beq SourcePacket_Single3_flags
    cmp #$42
    beq SourcePacket_Single3_flags
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single3_flags:
.a16
.i16
    lda.l DmaQueue_Owner+3
    and #255
    beq SourcePacket_Single3_unowned
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single3_unowned:
.a16
.i16
    lda.l SourcePacket_NmiQueueRows
    inc a
    cmp #7
    bcc SourcePacket_Single3_counted
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single3_counted:
.a16
.i16
    sta.l SourcePacket_NmiQueueRows
    lda.l DmaQueue,x
    bne SourcePacket_Single3_guard0
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single3_guard0:
.a16
.i16
    cmp #257
    bcc SourcePacket_Single3_guard1
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single3_guard1:
.a16
.i16
    sta.l SourcePacket_NmiRowLength
    and #1
    beq SourcePacket_Single3_guard2
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single3_guard2:
.a16
.i16
    lda.l DmaQueue+2,x
    and #1
    beq SourcePacket_Single3_guard3
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single3_guard3:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    clc
    adc.l SourcePacket_NmiQueueTotal
    cmp #257
    bcc SourcePacket_Single3_guard4
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single3_guard4:
.a16
.i16
    sta.l SourcePacket_NmiQueueTotal
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    beq SourcePacket_Single3_source_bank
    cmp #$7F
    beq SourcePacket_Single3_source_bank
    cmp #$40
    bcc SourcePacket_Single3_rom_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single3_rom_bank:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$8000
    bcs SourcePacket_Single3_source_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single3_source_bank:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    dec a
    sta.l SourcePacket_NmiRowSpan
    lda.l DmaQueue+5,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_Single3_source_range
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single3_source_range:
.a16
.i16
    lda.l SourcePacket_NmiRowType
    cmp #$42
    beq SourcePacket_Single3_palette_range
    ; Generic background work must not overwrite any of the64 held OBJ
    ; cache blocks at VRAM8000..BFFF, even if a bad row claims owner0.
    lda.l DmaQueue+2,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_Single3_target_valid
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single3_target_valid:
.a16
.i16
    sta.l SourcePacket_NmiTargetEnd
    lda.l DmaQueue+2,x
    cmp #$8000
    bcc SourcePacket_Single3_below_obj
    cmp #$C000
    bcs SourcePacket_Single3_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single3_below_obj:
.a16
.i16
    lda.l SourcePacket_NmiTargetEnd
    cmp #$8000
    bcc SourcePacket_Single3_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single3_palette_range:
.a16
.i16
    ; Background CGRAM is byte0..255. OBJ palettes remain resource-owned.
    lda.l DmaQueue+2,x
    cmp #256
    bcc SourcePacket_Single3_palette_target
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single3_palette_target:
.a16
.i16
    clc
    adc.l SourcePacket_NmiRowLength
    cmp #257
    bcc SourcePacket_Single3_next
    jml SourcePacket_CheckBackgroundBudget__bad

SourcePacket_Single3_next:
.a16
.i16
    ldx #32
SourcePacket_Single4_row:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    bne SourcePacket_Single4_active
    brl SourcePacket_Single4_next
SourcePacket_Single4_active:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    sta.l SourcePacket_NmiRowType
    cmp #$40
    beq SourcePacket_Single4_flags
    cmp #$42
    beq SourcePacket_Single4_flags
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single4_flags:
.a16
.i16
    lda.l DmaQueue_Owner+4
    and #255
    beq SourcePacket_Single4_unowned
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single4_unowned:
.a16
.i16
    lda.l SourcePacket_NmiQueueRows
    inc a
    cmp #7
    bcc SourcePacket_Single4_counted
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single4_counted:
.a16
.i16
    sta.l SourcePacket_NmiQueueRows
    lda.l DmaQueue,x
    bne SourcePacket_Single4_guard0
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single4_guard0:
.a16
.i16
    cmp #257
    bcc SourcePacket_Single4_guard1
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single4_guard1:
.a16
.i16
    sta.l SourcePacket_NmiRowLength
    and #1
    beq SourcePacket_Single4_guard2
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single4_guard2:
.a16
.i16
    lda.l DmaQueue+2,x
    and #1
    beq SourcePacket_Single4_guard3
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single4_guard3:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    clc
    adc.l SourcePacket_NmiQueueTotal
    cmp #257
    bcc SourcePacket_Single4_guard4
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single4_guard4:
.a16
.i16
    sta.l SourcePacket_NmiQueueTotal
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    beq SourcePacket_Single4_source_bank
    cmp #$7F
    beq SourcePacket_Single4_source_bank
    cmp #$40
    bcc SourcePacket_Single4_rom_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single4_rom_bank:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$8000
    bcs SourcePacket_Single4_source_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single4_source_bank:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    dec a
    sta.l SourcePacket_NmiRowSpan
    lda.l DmaQueue+5,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_Single4_source_range
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single4_source_range:
.a16
.i16
    lda.l SourcePacket_NmiRowType
    cmp #$42
    beq SourcePacket_Single4_palette_range
    ; Generic background work must not overwrite any of the64 held OBJ
    ; cache blocks at VRAM8000..BFFF, even if a bad row claims owner0.
    lda.l DmaQueue+2,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_Single4_target_valid
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single4_target_valid:
.a16
.i16
    sta.l SourcePacket_NmiTargetEnd
    lda.l DmaQueue+2,x
    cmp #$8000
    bcc SourcePacket_Single4_below_obj
    cmp #$C000
    bcs SourcePacket_Single4_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single4_below_obj:
.a16
.i16
    lda.l SourcePacket_NmiTargetEnd
    cmp #$8000
    bcc SourcePacket_Single4_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single4_palette_range:
.a16
.i16
    ; Background CGRAM is byte0..255. OBJ palettes remain resource-owned.
    lda.l DmaQueue+2,x
    cmp #256
    bcc SourcePacket_Single4_palette_target
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single4_palette_target:
.a16
.i16
    clc
    adc.l SourcePacket_NmiRowLength
    cmp #257
    bcc SourcePacket_Single4_next
    jml SourcePacket_CheckBackgroundBudget__bad

SourcePacket_Single4_next:
.a16
.i16
    ldx #40
SourcePacket_Single5_row:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    bne SourcePacket_Single5_active
    brl SourcePacket_Single5_next
SourcePacket_Single5_active:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    sta.l SourcePacket_NmiRowType
    cmp #$40
    beq SourcePacket_Single5_flags
    cmp #$42
    beq SourcePacket_Single5_flags
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single5_flags:
.a16
.i16
    lda.l DmaQueue_Owner+5
    and #255
    beq SourcePacket_Single5_unowned
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single5_unowned:
.a16
.i16
    lda.l SourcePacket_NmiQueueRows
    inc a
    cmp #7
    bcc SourcePacket_Single5_counted
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single5_counted:
.a16
.i16
    sta.l SourcePacket_NmiQueueRows
    lda.l DmaQueue,x
    bne SourcePacket_Single5_guard0
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single5_guard0:
.a16
.i16
    cmp #257
    bcc SourcePacket_Single5_guard1
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single5_guard1:
.a16
.i16
    sta.l SourcePacket_NmiRowLength
    and #1
    beq SourcePacket_Single5_guard2
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single5_guard2:
.a16
.i16
    lda.l DmaQueue+2,x
    and #1
    beq SourcePacket_Single5_guard3
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single5_guard3:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    clc
    adc.l SourcePacket_NmiQueueTotal
    cmp #257
    bcc SourcePacket_Single5_guard4
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single5_guard4:
.a16
.i16
    sta.l SourcePacket_NmiQueueTotal
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    beq SourcePacket_Single5_source_bank
    cmp #$7F
    beq SourcePacket_Single5_source_bank
    cmp #$40
    bcc SourcePacket_Single5_rom_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single5_rom_bank:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$8000
    bcs SourcePacket_Single5_source_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single5_source_bank:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    dec a
    sta.l SourcePacket_NmiRowSpan
    lda.l DmaQueue+5,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_Single5_source_range
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single5_source_range:
.a16
.i16
    lda.l SourcePacket_NmiRowType
    cmp #$42
    beq SourcePacket_Single5_palette_range
    ; Generic background work must not overwrite any of the64 held OBJ
    ; cache blocks at VRAM8000..BFFF, even if a bad row claims owner0.
    lda.l DmaQueue+2,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_Single5_target_valid
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single5_target_valid:
.a16
.i16
    sta.l SourcePacket_NmiTargetEnd
    lda.l DmaQueue+2,x
    cmp #$8000
    bcc SourcePacket_Single5_below_obj
    cmp #$C000
    bcs SourcePacket_Single5_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single5_below_obj:
.a16
.i16
    lda.l SourcePacket_NmiTargetEnd
    cmp #$8000
    bcc SourcePacket_Single5_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single5_palette_range:
.a16
.i16
    ; Background CGRAM is byte0..255. OBJ palettes remain resource-owned.
    lda.l DmaQueue+2,x
    cmp #256
    bcc SourcePacket_Single5_palette_target
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single5_palette_target:
.a16
.i16
    clc
    adc.l SourcePacket_NmiRowLength
    cmp #257
    bcc SourcePacket_Single5_next
    jml SourcePacket_CheckBackgroundBudget__bad

SourcePacket_Single5_next:
.a16
.i16
    ldx #48
SourcePacket_Single6_row:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    bne SourcePacket_Single6_active
    brl SourcePacket_Single6_next
SourcePacket_Single6_active:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    sta.l SourcePacket_NmiRowType
    cmp #$40
    beq SourcePacket_Single6_flags
    cmp #$42
    beq SourcePacket_Single6_flags
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single6_flags:
.a16
.i16
    lda.l DmaQueue_Owner+6
    and #255
    beq SourcePacket_Single6_unowned
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single6_unowned:
.a16
.i16
    lda.l SourcePacket_NmiQueueRows
    inc a
    cmp #7
    bcc SourcePacket_Single6_counted
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single6_counted:
.a16
.i16
    sta.l SourcePacket_NmiQueueRows
    lda.l DmaQueue,x
    bne SourcePacket_Single6_guard0
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single6_guard0:
.a16
.i16
    cmp #257
    bcc SourcePacket_Single6_guard1
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single6_guard1:
.a16
.i16
    sta.l SourcePacket_NmiRowLength
    and #1
    beq SourcePacket_Single6_guard2
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single6_guard2:
.a16
.i16
    lda.l DmaQueue+2,x
    and #1
    beq SourcePacket_Single6_guard3
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single6_guard3:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    clc
    adc.l SourcePacket_NmiQueueTotal
    cmp #257
    bcc SourcePacket_Single6_guard4
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single6_guard4:
.a16
.i16
    sta.l SourcePacket_NmiQueueTotal
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    beq SourcePacket_Single6_source_bank
    cmp #$7F
    beq SourcePacket_Single6_source_bank
    cmp #$40
    bcc SourcePacket_Single6_rom_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single6_rom_bank:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$8000
    bcs SourcePacket_Single6_source_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single6_source_bank:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    dec a
    sta.l SourcePacket_NmiRowSpan
    lda.l DmaQueue+5,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_Single6_source_range
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single6_source_range:
.a16
.i16
    lda.l SourcePacket_NmiRowType
    cmp #$42
    beq SourcePacket_Single6_palette_range
    ; Generic background work must not overwrite any of the64 held OBJ
    ; cache blocks at VRAM8000..BFFF, even if a bad row claims owner0.
    lda.l DmaQueue+2,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_Single6_target_valid
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single6_target_valid:
.a16
.i16
    sta.l SourcePacket_NmiTargetEnd
    lda.l DmaQueue+2,x
    cmp #$8000
    bcc SourcePacket_Single6_below_obj
    cmp #$C000
    bcs SourcePacket_Single6_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single6_below_obj:
.a16
.i16
    lda.l SourcePacket_NmiTargetEnd
    cmp #$8000
    bcc SourcePacket_Single6_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single6_palette_range:
.a16
.i16
    ; Background CGRAM is byte0..255. OBJ palettes remain resource-owned.
    lda.l DmaQueue+2,x
    cmp #256
    bcc SourcePacket_Single6_palette_target
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single6_palette_target:
.a16
.i16
    clc
    adc.l SourcePacket_NmiRowLength
    cmp #257
    bcc SourcePacket_Single6_next
    jml SourcePacket_CheckBackgroundBudget__bad

SourcePacket_Single6_next:
.a16
.i16
    ldx #56
SourcePacket_Single7_row:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    bne SourcePacket_Single7_active
    brl SourcePacket_Single7_next
SourcePacket_Single7_active:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    sta.l SourcePacket_NmiRowType
    cmp #$40
    beq SourcePacket_Single7_flags
    cmp #$42
    beq SourcePacket_Single7_flags
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single7_flags:
.a16
.i16
    lda.l DmaQueue_Owner+7
    and #255
    beq SourcePacket_Single7_unowned
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single7_unowned:
.a16
.i16
    lda.l SourcePacket_NmiQueueRows
    inc a
    cmp #7
    bcc SourcePacket_Single7_counted
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single7_counted:
.a16
.i16
    sta.l SourcePacket_NmiQueueRows
    lda.l DmaQueue,x
    bne SourcePacket_Single7_guard0
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single7_guard0:
.a16
.i16
    cmp #257
    bcc SourcePacket_Single7_guard1
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single7_guard1:
.a16
.i16
    sta.l SourcePacket_NmiRowLength
    and #1
    beq SourcePacket_Single7_guard2
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single7_guard2:
.a16
.i16
    lda.l DmaQueue+2,x
    and #1
    beq SourcePacket_Single7_guard3
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single7_guard3:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    clc
    adc.l SourcePacket_NmiQueueTotal
    cmp #257
    bcc SourcePacket_Single7_guard4
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single7_guard4:
.a16
.i16
    sta.l SourcePacket_NmiQueueTotal
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    beq SourcePacket_Single7_source_bank
    cmp #$7F
    beq SourcePacket_Single7_source_bank
    cmp #$40
    bcc SourcePacket_Single7_rom_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single7_rom_bank:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$8000
    bcs SourcePacket_Single7_source_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single7_source_bank:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    dec a
    sta.l SourcePacket_NmiRowSpan
    lda.l DmaQueue+5,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_Single7_source_range
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single7_source_range:
.a16
.i16
    lda.l SourcePacket_NmiRowType
    cmp #$42
    beq SourcePacket_Single7_palette_range
    ; Generic background work must not overwrite any of the64 held OBJ
    ; cache blocks at VRAM8000..BFFF, even if a bad row claims owner0.
    lda.l DmaQueue+2,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_Single7_target_valid
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single7_target_valid:
.a16
.i16
    sta.l SourcePacket_NmiTargetEnd
    lda.l DmaQueue+2,x
    cmp #$8000
    bcc SourcePacket_Single7_below_obj
    cmp #$C000
    bcs SourcePacket_Single7_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single7_below_obj:
.a16
.i16
    lda.l SourcePacket_NmiTargetEnd
    cmp #$8000
    bcc SourcePacket_Single7_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single7_palette_range:
.a16
.i16
    ; Background CGRAM is byte0..255. OBJ palettes remain resource-owned.
    lda.l DmaQueue+2,x
    cmp #256
    bcc SourcePacket_Single7_palette_target
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_Single7_palette_target:
.a16
.i16
    clc
    adc.l SourcePacket_NmiRowLength
    cmp #257
    bcc SourcePacket_Single7_next
    jml SourcePacket_CheckBackgroundBudget__bad

SourcePacket_Single7_next:
.a16
.i16
    ldx #64
    lda #64
    cpx #64
    jml SourcePacket_CheckBackgroundBudget__good
SourcePacket_UnrolledEnd:
