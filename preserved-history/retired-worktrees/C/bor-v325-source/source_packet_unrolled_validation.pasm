; Fixed eight-row NMI validation; same predicates and six-row/256B bounds.
; No cache/world/input/queue writes. Original deadline and DMA code retained.
SourcePacket_UnrolledQueue:
.a16
.i16
    lda #0
    sta.l SourcePacket_NmiQueueRows
lda.l DmaQueue+4
    and #$0040
    bne SourcePacket_UnrolledQ0_active
    brl SourcePacket_UnrolledQ0_next
SourcePacket_UnrolledQ0_active:
.a16
.i16
    lda.l SourcePacket_NmiMainBusy
    cmp #1
    beq SourcePacket_UnrolledQ0_busy
    lda.l DmaQueue+4
    and #255
    cmp #$40
    beq SourcePacket_UnrolledQ0_background
    cmp #$42
    beq SourcePacket_UnrolledQ0_background
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ0_background:
.a16
.i16
    lda.l DmaQueue_Owner+0
    and #255
    beq SourcePacket_UnrolledQ0_unowned
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ0_unowned:
.a16
.i16
    lda.l SourcePacket_NmiQueueRows
    inc a
    cmp #7
    bcc SourcePacket_UnrolledQ0_counted
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ0_counted:
.a16
.i16
    sta.l SourcePacket_NmiQueueRows
    brl SourcePacket_UnrolledQ0_next
SourcePacket_UnrolledQ0_busy:
.a16
.i16
    lda.l DmaQueue+7
    and #255
    cmp #$43
    bne SourcePacket_UnrolledQ0_notprivate
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ0_notprivate:
.a16
.i16
    lda.l DmaQueue+4
    and #31
    cmp #DMA_TYPE_OAM
    bne SourcePacket_UnrolledQ0_next
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ0_next:
.a16
.i16
lda.l DmaQueue+12
    and #$0040
    bne SourcePacket_UnrolledQ1_active
    brl SourcePacket_UnrolledQ1_next
SourcePacket_UnrolledQ1_active:
.a16
.i16
    lda.l SourcePacket_NmiMainBusy
    cmp #1
    beq SourcePacket_UnrolledQ1_busy
    lda.l DmaQueue+12
    and #255
    cmp #$40
    beq SourcePacket_UnrolledQ1_background
    cmp #$42
    beq SourcePacket_UnrolledQ1_background
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ1_background:
.a16
.i16
    lda.l DmaQueue_Owner+1
    and #255
    beq SourcePacket_UnrolledQ1_unowned
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ1_unowned:
.a16
.i16
    lda.l SourcePacket_NmiQueueRows
    inc a
    cmp #7
    bcc SourcePacket_UnrolledQ1_counted
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ1_counted:
.a16
.i16
    sta.l SourcePacket_NmiQueueRows
    brl SourcePacket_UnrolledQ1_next
SourcePacket_UnrolledQ1_busy:
.a16
.i16
    lda.l DmaQueue+15
    and #255
    cmp #$43
    bne SourcePacket_UnrolledQ1_notprivate
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ1_notprivate:
.a16
.i16
    lda.l DmaQueue+12
    and #31
    cmp #DMA_TYPE_OAM
    bne SourcePacket_UnrolledQ1_next
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ1_next:
.a16
.i16
lda.l DmaQueue+20
    and #$0040
    bne SourcePacket_UnrolledQ2_active
    brl SourcePacket_UnrolledQ2_next
SourcePacket_UnrolledQ2_active:
.a16
.i16
    lda.l SourcePacket_NmiMainBusy
    cmp #1
    beq SourcePacket_UnrolledQ2_busy
    lda.l DmaQueue+20
    and #255
    cmp #$40
    beq SourcePacket_UnrolledQ2_background
    cmp #$42
    beq SourcePacket_UnrolledQ2_background
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ2_background:
.a16
.i16
    lda.l DmaQueue_Owner+2
    and #255
    beq SourcePacket_UnrolledQ2_unowned
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ2_unowned:
.a16
.i16
    lda.l SourcePacket_NmiQueueRows
    inc a
    cmp #7
    bcc SourcePacket_UnrolledQ2_counted
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ2_counted:
.a16
.i16
    sta.l SourcePacket_NmiQueueRows
    brl SourcePacket_UnrolledQ2_next
SourcePacket_UnrolledQ2_busy:
.a16
.i16
    lda.l DmaQueue+23
    and #255
    cmp #$43
    bne SourcePacket_UnrolledQ2_notprivate
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ2_notprivate:
.a16
.i16
    lda.l DmaQueue+20
    and #31
    cmp #DMA_TYPE_OAM
    bne SourcePacket_UnrolledQ2_next
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ2_next:
.a16
.i16
lda.l DmaQueue+28
    and #$0040
    bne SourcePacket_UnrolledQ3_active
    brl SourcePacket_UnrolledQ3_next
SourcePacket_UnrolledQ3_active:
.a16
.i16
    lda.l SourcePacket_NmiMainBusy
    cmp #1
    beq SourcePacket_UnrolledQ3_busy
    lda.l DmaQueue+28
    and #255
    cmp #$40
    beq SourcePacket_UnrolledQ3_background
    cmp #$42
    beq SourcePacket_UnrolledQ3_background
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ3_background:
.a16
.i16
    lda.l DmaQueue_Owner+3
    and #255
    beq SourcePacket_UnrolledQ3_unowned
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ3_unowned:
.a16
.i16
    lda.l SourcePacket_NmiQueueRows
    inc a
    cmp #7
    bcc SourcePacket_UnrolledQ3_counted
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ3_counted:
.a16
.i16
    sta.l SourcePacket_NmiQueueRows
    brl SourcePacket_UnrolledQ3_next
SourcePacket_UnrolledQ3_busy:
.a16
.i16
    lda.l DmaQueue+31
    and #255
    cmp #$43
    bne SourcePacket_UnrolledQ3_notprivate
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ3_notprivate:
.a16
.i16
    lda.l DmaQueue+28
    and #31
    cmp #DMA_TYPE_OAM
    bne SourcePacket_UnrolledQ3_next
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ3_next:
.a16
.i16
lda.l DmaQueue+36
    and #$0040
    bne SourcePacket_UnrolledQ4_active
    brl SourcePacket_UnrolledQ4_next
SourcePacket_UnrolledQ4_active:
.a16
.i16
    lda.l SourcePacket_NmiMainBusy
    cmp #1
    beq SourcePacket_UnrolledQ4_busy
    lda.l DmaQueue+36
    and #255
    cmp #$40
    beq SourcePacket_UnrolledQ4_background
    cmp #$42
    beq SourcePacket_UnrolledQ4_background
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ4_background:
.a16
.i16
    lda.l DmaQueue_Owner+4
    and #255
    beq SourcePacket_UnrolledQ4_unowned
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ4_unowned:
.a16
.i16
    lda.l SourcePacket_NmiQueueRows
    inc a
    cmp #7
    bcc SourcePacket_UnrolledQ4_counted
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ4_counted:
.a16
.i16
    sta.l SourcePacket_NmiQueueRows
    brl SourcePacket_UnrolledQ4_next
SourcePacket_UnrolledQ4_busy:
.a16
.i16
    lda.l DmaQueue+39
    and #255
    cmp #$43
    bne SourcePacket_UnrolledQ4_notprivate
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ4_notprivate:
.a16
.i16
    lda.l DmaQueue+36
    and #31
    cmp #DMA_TYPE_OAM
    bne SourcePacket_UnrolledQ4_next
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ4_next:
.a16
.i16
lda.l DmaQueue+44
    and #$0040
    bne SourcePacket_UnrolledQ5_active
    brl SourcePacket_UnrolledQ5_next
SourcePacket_UnrolledQ5_active:
.a16
.i16
    lda.l SourcePacket_NmiMainBusy
    cmp #1
    beq SourcePacket_UnrolledQ5_busy
    lda.l DmaQueue+44
    and #255
    cmp #$40
    beq SourcePacket_UnrolledQ5_background
    cmp #$42
    beq SourcePacket_UnrolledQ5_background
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ5_background:
.a16
.i16
    lda.l DmaQueue_Owner+5
    and #255
    beq SourcePacket_UnrolledQ5_unowned
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ5_unowned:
.a16
.i16
    lda.l SourcePacket_NmiQueueRows
    inc a
    cmp #7
    bcc SourcePacket_UnrolledQ5_counted
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ5_counted:
.a16
.i16
    sta.l SourcePacket_NmiQueueRows
    brl SourcePacket_UnrolledQ5_next
SourcePacket_UnrolledQ5_busy:
.a16
.i16
    lda.l DmaQueue+47
    and #255
    cmp #$43
    bne SourcePacket_UnrolledQ5_notprivate
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ5_notprivate:
.a16
.i16
    lda.l DmaQueue+44
    and #31
    cmp #DMA_TYPE_OAM
    bne SourcePacket_UnrolledQ5_next
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ5_next:
.a16
.i16
lda.l DmaQueue+52
    and #$0040
    bne SourcePacket_UnrolledQ6_active
    brl SourcePacket_UnrolledQ6_next
SourcePacket_UnrolledQ6_active:
.a16
.i16
    lda.l SourcePacket_NmiMainBusy
    cmp #1
    beq SourcePacket_UnrolledQ6_busy
    lda.l DmaQueue+52
    and #255
    cmp #$40
    beq SourcePacket_UnrolledQ6_background
    cmp #$42
    beq SourcePacket_UnrolledQ6_background
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ6_background:
.a16
.i16
    lda.l DmaQueue_Owner+6
    and #255
    beq SourcePacket_UnrolledQ6_unowned
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ6_unowned:
.a16
.i16
    lda.l SourcePacket_NmiQueueRows
    inc a
    cmp #7
    bcc SourcePacket_UnrolledQ6_counted
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ6_counted:
.a16
.i16
    sta.l SourcePacket_NmiQueueRows
    brl SourcePacket_UnrolledQ6_next
SourcePacket_UnrolledQ6_busy:
.a16
.i16
    lda.l DmaQueue+55
    and #255
    cmp #$43
    bne SourcePacket_UnrolledQ6_notprivate
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ6_notprivate:
.a16
.i16
    lda.l DmaQueue+52
    and #31
    cmp #DMA_TYPE_OAM
    bne SourcePacket_UnrolledQ6_next
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ6_next:
.a16
.i16
lda.l DmaQueue+60
    and #$0040
    bne SourcePacket_UnrolledQ7_active
    brl SourcePacket_UnrolledQ7_next
SourcePacket_UnrolledQ7_active:
.a16
.i16
    lda.l SourcePacket_NmiMainBusy
    cmp #1
    beq SourcePacket_UnrolledQ7_busy
    lda.l DmaQueue+60
    and #255
    cmp #$40
    beq SourcePacket_UnrolledQ7_background
    cmp #$42
    beq SourcePacket_UnrolledQ7_background
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ7_background:
.a16
.i16
    lda.l DmaQueue_Owner+7
    and #255
    beq SourcePacket_UnrolledQ7_unowned
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ7_unowned:
.a16
.i16
    lda.l SourcePacket_NmiQueueRows
    inc a
    cmp #7
    bcc SourcePacket_UnrolledQ7_counted
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ7_counted:
.a16
.i16
    sta.l SourcePacket_NmiQueueRows
    brl SourcePacket_UnrolledQ7_next
SourcePacket_UnrolledQ7_busy:
.a16
.i16
    lda.l DmaQueue+63
    and #255
    cmp #$43
    bne SourcePacket_UnrolledQ7_notprivate
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ7_notprivate:
.a16
.i16
    lda.l DmaQueue+60
    and #31
    cmp #DMA_TYPE_OAM
    bne SourcePacket_UnrolledQ7_next
    jml SourcePacket_NmiPublish__done
SourcePacket_UnrolledQ7_next:
.a16
.i16
ldx #64
    jml SourcePacket_NmiPublish__queue_scanned
SourcePacket_UnrolledBudget:
.a16
.i16
    lda #0
    sta.l SourcePacket_NmiQueueTotal
ldx #0
SourcePacket_UnrolledB0_row:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    bne SourcePacket_UnrolledB0_active
    brl SourcePacket_UnrolledB0_next
SourcePacket_UnrolledB0_active:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    sta.l SourcePacket_NmiRowType
    lda.l DmaQueue,x
    bne SourcePacket_UnrolledB0_guard0
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB0_guard0:
.a16
.i16
    cmp #257
    bcc SourcePacket_UnrolledB0_guard1
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB0_guard1:
.a16
.i16
    sta.l SourcePacket_NmiRowLength
    and #1
    beq SourcePacket_UnrolledB0_guard2
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB0_guard2:
.a16
.i16
    lda.l DmaQueue+2,x
    and #1
    beq SourcePacket_UnrolledB0_guard3
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB0_guard3:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    clc
    adc.l SourcePacket_NmiQueueTotal
    cmp #257
    bcc SourcePacket_UnrolledB0_guard4
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB0_guard4:
.a16
.i16
    sta.l SourcePacket_NmiQueueTotal
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    beq SourcePacket_UnrolledB0_source_bank
    cmp #$7F
    beq SourcePacket_UnrolledB0_source_bank
    cmp #$40
    bcc SourcePacket_UnrolledB0_rom_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB0_rom_bank:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$8000
    bcs SourcePacket_UnrolledB0_source_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB0_source_bank:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    dec a
    sta.l SourcePacket_NmiRowSpan
    lda.l DmaQueue+5,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_UnrolledB0_source_range
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB0_source_range:
.a16
.i16
    lda.l SourcePacket_NmiRowType
    cmp #$42
    beq SourcePacket_UnrolledB0_palette_range
    ; Generic background work must not overwrite any of the64 held OBJ
    ; cache blocks at VRAM8000..BFFF, even if a bad row claims owner0.
    lda.l DmaQueue+2,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_UnrolledB0_target_valid
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB0_target_valid:
.a16
.i16
    sta.l SourcePacket_NmiTargetEnd
    lda.l DmaQueue+2,x
    cmp #$8000
    bcc SourcePacket_UnrolledB0_below_obj
    cmp #$C000
    bcs SourcePacket_UnrolledB0_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB0_below_obj:
.a16
.i16
    lda.l SourcePacket_NmiTargetEnd
    cmp #$8000
    bcc SourcePacket_UnrolledB0_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB0_palette_range:
.a16
.i16
    ; Background CGRAM is byte0..255. OBJ palettes remain resource-owned.
    lda.l DmaQueue+2,x
    cmp #256
    bcc SourcePacket_UnrolledB0_palette_target
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB0_palette_target:
.a16
.i16
    clc
    adc.l SourcePacket_NmiRowLength
    cmp #257
    bcc SourcePacket_UnrolledB0_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB0_next:
.a16
.i16
ldx #8
SourcePacket_UnrolledB1_row:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    bne SourcePacket_UnrolledB1_active
    brl SourcePacket_UnrolledB1_next
SourcePacket_UnrolledB1_active:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    sta.l SourcePacket_NmiRowType
    lda.l DmaQueue,x
    bne SourcePacket_UnrolledB1_guard0
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB1_guard0:
.a16
.i16
    cmp #257
    bcc SourcePacket_UnrolledB1_guard1
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB1_guard1:
.a16
.i16
    sta.l SourcePacket_NmiRowLength
    and #1
    beq SourcePacket_UnrolledB1_guard2
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB1_guard2:
.a16
.i16
    lda.l DmaQueue+2,x
    and #1
    beq SourcePacket_UnrolledB1_guard3
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB1_guard3:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    clc
    adc.l SourcePacket_NmiQueueTotal
    cmp #257
    bcc SourcePacket_UnrolledB1_guard4
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB1_guard4:
.a16
.i16
    sta.l SourcePacket_NmiQueueTotal
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    beq SourcePacket_UnrolledB1_source_bank
    cmp #$7F
    beq SourcePacket_UnrolledB1_source_bank
    cmp #$40
    bcc SourcePacket_UnrolledB1_rom_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB1_rom_bank:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$8000
    bcs SourcePacket_UnrolledB1_source_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB1_source_bank:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    dec a
    sta.l SourcePacket_NmiRowSpan
    lda.l DmaQueue+5,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_UnrolledB1_source_range
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB1_source_range:
.a16
.i16
    lda.l SourcePacket_NmiRowType
    cmp #$42
    beq SourcePacket_UnrolledB1_palette_range
    ; Generic background work must not overwrite any of the64 held OBJ
    ; cache blocks at VRAM8000..BFFF, even if a bad row claims owner0.
    lda.l DmaQueue+2,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_UnrolledB1_target_valid
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB1_target_valid:
.a16
.i16
    sta.l SourcePacket_NmiTargetEnd
    lda.l DmaQueue+2,x
    cmp #$8000
    bcc SourcePacket_UnrolledB1_below_obj
    cmp #$C000
    bcs SourcePacket_UnrolledB1_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB1_below_obj:
.a16
.i16
    lda.l SourcePacket_NmiTargetEnd
    cmp #$8000
    bcc SourcePacket_UnrolledB1_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB1_palette_range:
.a16
.i16
    ; Background CGRAM is byte0..255. OBJ palettes remain resource-owned.
    lda.l DmaQueue+2,x
    cmp #256
    bcc SourcePacket_UnrolledB1_palette_target
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB1_palette_target:
.a16
.i16
    clc
    adc.l SourcePacket_NmiRowLength
    cmp #257
    bcc SourcePacket_UnrolledB1_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB1_next:
.a16
.i16
ldx #16
SourcePacket_UnrolledB2_row:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    bne SourcePacket_UnrolledB2_active
    brl SourcePacket_UnrolledB2_next
SourcePacket_UnrolledB2_active:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    sta.l SourcePacket_NmiRowType
    lda.l DmaQueue,x
    bne SourcePacket_UnrolledB2_guard0
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB2_guard0:
.a16
.i16
    cmp #257
    bcc SourcePacket_UnrolledB2_guard1
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB2_guard1:
.a16
.i16
    sta.l SourcePacket_NmiRowLength
    and #1
    beq SourcePacket_UnrolledB2_guard2
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB2_guard2:
.a16
.i16
    lda.l DmaQueue+2,x
    and #1
    beq SourcePacket_UnrolledB2_guard3
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB2_guard3:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    clc
    adc.l SourcePacket_NmiQueueTotal
    cmp #257
    bcc SourcePacket_UnrolledB2_guard4
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB2_guard4:
.a16
.i16
    sta.l SourcePacket_NmiQueueTotal
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    beq SourcePacket_UnrolledB2_source_bank
    cmp #$7F
    beq SourcePacket_UnrolledB2_source_bank
    cmp #$40
    bcc SourcePacket_UnrolledB2_rom_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB2_rom_bank:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$8000
    bcs SourcePacket_UnrolledB2_source_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB2_source_bank:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    dec a
    sta.l SourcePacket_NmiRowSpan
    lda.l DmaQueue+5,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_UnrolledB2_source_range
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB2_source_range:
.a16
.i16
    lda.l SourcePacket_NmiRowType
    cmp #$42
    beq SourcePacket_UnrolledB2_palette_range
    ; Generic background work must not overwrite any of the64 held OBJ
    ; cache blocks at VRAM8000..BFFF, even if a bad row claims owner0.
    lda.l DmaQueue+2,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_UnrolledB2_target_valid
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB2_target_valid:
.a16
.i16
    sta.l SourcePacket_NmiTargetEnd
    lda.l DmaQueue+2,x
    cmp #$8000
    bcc SourcePacket_UnrolledB2_below_obj
    cmp #$C000
    bcs SourcePacket_UnrolledB2_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB2_below_obj:
.a16
.i16
    lda.l SourcePacket_NmiTargetEnd
    cmp #$8000
    bcc SourcePacket_UnrolledB2_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB2_palette_range:
.a16
.i16
    ; Background CGRAM is byte0..255. OBJ palettes remain resource-owned.
    lda.l DmaQueue+2,x
    cmp #256
    bcc SourcePacket_UnrolledB2_palette_target
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB2_palette_target:
.a16
.i16
    clc
    adc.l SourcePacket_NmiRowLength
    cmp #257
    bcc SourcePacket_UnrolledB2_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB2_next:
.a16
.i16
ldx #24
SourcePacket_UnrolledB3_row:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    bne SourcePacket_UnrolledB3_active
    brl SourcePacket_UnrolledB3_next
SourcePacket_UnrolledB3_active:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    sta.l SourcePacket_NmiRowType
    lda.l DmaQueue,x
    bne SourcePacket_UnrolledB3_guard0
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB3_guard0:
.a16
.i16
    cmp #257
    bcc SourcePacket_UnrolledB3_guard1
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB3_guard1:
.a16
.i16
    sta.l SourcePacket_NmiRowLength
    and #1
    beq SourcePacket_UnrolledB3_guard2
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB3_guard2:
.a16
.i16
    lda.l DmaQueue+2,x
    and #1
    beq SourcePacket_UnrolledB3_guard3
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB3_guard3:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    clc
    adc.l SourcePacket_NmiQueueTotal
    cmp #257
    bcc SourcePacket_UnrolledB3_guard4
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB3_guard4:
.a16
.i16
    sta.l SourcePacket_NmiQueueTotal
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    beq SourcePacket_UnrolledB3_source_bank
    cmp #$7F
    beq SourcePacket_UnrolledB3_source_bank
    cmp #$40
    bcc SourcePacket_UnrolledB3_rom_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB3_rom_bank:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$8000
    bcs SourcePacket_UnrolledB3_source_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB3_source_bank:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    dec a
    sta.l SourcePacket_NmiRowSpan
    lda.l DmaQueue+5,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_UnrolledB3_source_range
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB3_source_range:
.a16
.i16
    lda.l SourcePacket_NmiRowType
    cmp #$42
    beq SourcePacket_UnrolledB3_palette_range
    ; Generic background work must not overwrite any of the64 held OBJ
    ; cache blocks at VRAM8000..BFFF, even if a bad row claims owner0.
    lda.l DmaQueue+2,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_UnrolledB3_target_valid
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB3_target_valid:
.a16
.i16
    sta.l SourcePacket_NmiTargetEnd
    lda.l DmaQueue+2,x
    cmp #$8000
    bcc SourcePacket_UnrolledB3_below_obj
    cmp #$C000
    bcs SourcePacket_UnrolledB3_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB3_below_obj:
.a16
.i16
    lda.l SourcePacket_NmiTargetEnd
    cmp #$8000
    bcc SourcePacket_UnrolledB3_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB3_palette_range:
.a16
.i16
    ; Background CGRAM is byte0..255. OBJ palettes remain resource-owned.
    lda.l DmaQueue+2,x
    cmp #256
    bcc SourcePacket_UnrolledB3_palette_target
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB3_palette_target:
.a16
.i16
    clc
    adc.l SourcePacket_NmiRowLength
    cmp #257
    bcc SourcePacket_UnrolledB3_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB3_next:
.a16
.i16
ldx #32
SourcePacket_UnrolledB4_row:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    bne SourcePacket_UnrolledB4_active
    brl SourcePacket_UnrolledB4_next
SourcePacket_UnrolledB4_active:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    sta.l SourcePacket_NmiRowType
    lda.l DmaQueue,x
    bne SourcePacket_UnrolledB4_guard0
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB4_guard0:
.a16
.i16
    cmp #257
    bcc SourcePacket_UnrolledB4_guard1
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB4_guard1:
.a16
.i16
    sta.l SourcePacket_NmiRowLength
    and #1
    beq SourcePacket_UnrolledB4_guard2
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB4_guard2:
.a16
.i16
    lda.l DmaQueue+2,x
    and #1
    beq SourcePacket_UnrolledB4_guard3
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB4_guard3:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    clc
    adc.l SourcePacket_NmiQueueTotal
    cmp #257
    bcc SourcePacket_UnrolledB4_guard4
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB4_guard4:
.a16
.i16
    sta.l SourcePacket_NmiQueueTotal
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    beq SourcePacket_UnrolledB4_source_bank
    cmp #$7F
    beq SourcePacket_UnrolledB4_source_bank
    cmp #$40
    bcc SourcePacket_UnrolledB4_rom_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB4_rom_bank:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$8000
    bcs SourcePacket_UnrolledB4_source_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB4_source_bank:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    dec a
    sta.l SourcePacket_NmiRowSpan
    lda.l DmaQueue+5,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_UnrolledB4_source_range
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB4_source_range:
.a16
.i16
    lda.l SourcePacket_NmiRowType
    cmp #$42
    beq SourcePacket_UnrolledB4_palette_range
    ; Generic background work must not overwrite any of the64 held OBJ
    ; cache blocks at VRAM8000..BFFF, even if a bad row claims owner0.
    lda.l DmaQueue+2,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_UnrolledB4_target_valid
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB4_target_valid:
.a16
.i16
    sta.l SourcePacket_NmiTargetEnd
    lda.l DmaQueue+2,x
    cmp #$8000
    bcc SourcePacket_UnrolledB4_below_obj
    cmp #$C000
    bcs SourcePacket_UnrolledB4_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB4_below_obj:
.a16
.i16
    lda.l SourcePacket_NmiTargetEnd
    cmp #$8000
    bcc SourcePacket_UnrolledB4_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB4_palette_range:
.a16
.i16
    ; Background CGRAM is byte0..255. OBJ palettes remain resource-owned.
    lda.l DmaQueue+2,x
    cmp #256
    bcc SourcePacket_UnrolledB4_palette_target
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB4_palette_target:
.a16
.i16
    clc
    adc.l SourcePacket_NmiRowLength
    cmp #257
    bcc SourcePacket_UnrolledB4_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB4_next:
.a16
.i16
ldx #40
SourcePacket_UnrolledB5_row:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    bne SourcePacket_UnrolledB5_active
    brl SourcePacket_UnrolledB5_next
SourcePacket_UnrolledB5_active:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    sta.l SourcePacket_NmiRowType
    lda.l DmaQueue,x
    bne SourcePacket_UnrolledB5_guard0
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB5_guard0:
.a16
.i16
    cmp #257
    bcc SourcePacket_UnrolledB5_guard1
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB5_guard1:
.a16
.i16
    sta.l SourcePacket_NmiRowLength
    and #1
    beq SourcePacket_UnrolledB5_guard2
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB5_guard2:
.a16
.i16
    lda.l DmaQueue+2,x
    and #1
    beq SourcePacket_UnrolledB5_guard3
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB5_guard3:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    clc
    adc.l SourcePacket_NmiQueueTotal
    cmp #257
    bcc SourcePacket_UnrolledB5_guard4
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB5_guard4:
.a16
.i16
    sta.l SourcePacket_NmiQueueTotal
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    beq SourcePacket_UnrolledB5_source_bank
    cmp #$7F
    beq SourcePacket_UnrolledB5_source_bank
    cmp #$40
    bcc SourcePacket_UnrolledB5_rom_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB5_rom_bank:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$8000
    bcs SourcePacket_UnrolledB5_source_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB5_source_bank:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    dec a
    sta.l SourcePacket_NmiRowSpan
    lda.l DmaQueue+5,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_UnrolledB5_source_range
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB5_source_range:
.a16
.i16
    lda.l SourcePacket_NmiRowType
    cmp #$42
    beq SourcePacket_UnrolledB5_palette_range
    ; Generic background work must not overwrite any of the64 held OBJ
    ; cache blocks at VRAM8000..BFFF, even if a bad row claims owner0.
    lda.l DmaQueue+2,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_UnrolledB5_target_valid
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB5_target_valid:
.a16
.i16
    sta.l SourcePacket_NmiTargetEnd
    lda.l DmaQueue+2,x
    cmp #$8000
    bcc SourcePacket_UnrolledB5_below_obj
    cmp #$C000
    bcs SourcePacket_UnrolledB5_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB5_below_obj:
.a16
.i16
    lda.l SourcePacket_NmiTargetEnd
    cmp #$8000
    bcc SourcePacket_UnrolledB5_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB5_palette_range:
.a16
.i16
    ; Background CGRAM is byte0..255. OBJ palettes remain resource-owned.
    lda.l DmaQueue+2,x
    cmp #256
    bcc SourcePacket_UnrolledB5_palette_target
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB5_palette_target:
.a16
.i16
    clc
    adc.l SourcePacket_NmiRowLength
    cmp #257
    bcc SourcePacket_UnrolledB5_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB5_next:
.a16
.i16
ldx #48
SourcePacket_UnrolledB6_row:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    bne SourcePacket_UnrolledB6_active
    brl SourcePacket_UnrolledB6_next
SourcePacket_UnrolledB6_active:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    sta.l SourcePacket_NmiRowType
    lda.l DmaQueue,x
    bne SourcePacket_UnrolledB6_guard0
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB6_guard0:
.a16
.i16
    cmp #257
    bcc SourcePacket_UnrolledB6_guard1
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB6_guard1:
.a16
.i16
    sta.l SourcePacket_NmiRowLength
    and #1
    beq SourcePacket_UnrolledB6_guard2
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB6_guard2:
.a16
.i16
    lda.l DmaQueue+2,x
    and #1
    beq SourcePacket_UnrolledB6_guard3
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB6_guard3:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    clc
    adc.l SourcePacket_NmiQueueTotal
    cmp #257
    bcc SourcePacket_UnrolledB6_guard4
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB6_guard4:
.a16
.i16
    sta.l SourcePacket_NmiQueueTotal
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    beq SourcePacket_UnrolledB6_source_bank
    cmp #$7F
    beq SourcePacket_UnrolledB6_source_bank
    cmp #$40
    bcc SourcePacket_UnrolledB6_rom_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB6_rom_bank:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$8000
    bcs SourcePacket_UnrolledB6_source_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB6_source_bank:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    dec a
    sta.l SourcePacket_NmiRowSpan
    lda.l DmaQueue+5,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_UnrolledB6_source_range
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB6_source_range:
.a16
.i16
    lda.l SourcePacket_NmiRowType
    cmp #$42
    beq SourcePacket_UnrolledB6_palette_range
    ; Generic background work must not overwrite any of the64 held OBJ
    ; cache blocks at VRAM8000..BFFF, even if a bad row claims owner0.
    lda.l DmaQueue+2,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_UnrolledB6_target_valid
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB6_target_valid:
.a16
.i16
    sta.l SourcePacket_NmiTargetEnd
    lda.l DmaQueue+2,x
    cmp #$8000
    bcc SourcePacket_UnrolledB6_below_obj
    cmp #$C000
    bcs SourcePacket_UnrolledB6_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB6_below_obj:
.a16
.i16
    lda.l SourcePacket_NmiTargetEnd
    cmp #$8000
    bcc SourcePacket_UnrolledB6_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB6_palette_range:
.a16
.i16
    ; Background CGRAM is byte0..255. OBJ palettes remain resource-owned.
    lda.l DmaQueue+2,x
    cmp #256
    bcc SourcePacket_UnrolledB6_palette_target
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB6_palette_target:
.a16
.i16
    clc
    adc.l SourcePacket_NmiRowLength
    cmp #257
    bcc SourcePacket_UnrolledB6_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB6_next:
.a16
.i16
ldx #56
SourcePacket_UnrolledB7_row:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    bne SourcePacket_UnrolledB7_active
    brl SourcePacket_UnrolledB7_next
SourcePacket_UnrolledB7_active:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    sta.l SourcePacket_NmiRowType
    lda.l DmaQueue,x
    bne SourcePacket_UnrolledB7_guard0
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB7_guard0:
.a16
.i16
    cmp #257
    bcc SourcePacket_UnrolledB7_guard1
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB7_guard1:
.a16
.i16
    sta.l SourcePacket_NmiRowLength
    and #1
    beq SourcePacket_UnrolledB7_guard2
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB7_guard2:
.a16
.i16
    lda.l DmaQueue+2,x
    and #1
    beq SourcePacket_UnrolledB7_guard3
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB7_guard3:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    clc
    adc.l SourcePacket_NmiQueueTotal
    cmp #257
    bcc SourcePacket_UnrolledB7_guard4
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB7_guard4:
.a16
.i16
    sta.l SourcePacket_NmiQueueTotal
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    beq SourcePacket_UnrolledB7_source_bank
    cmp #$7F
    beq SourcePacket_UnrolledB7_source_bank
    cmp #$40
    bcc SourcePacket_UnrolledB7_rom_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB7_rom_bank:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$8000
    bcs SourcePacket_UnrolledB7_source_bank
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB7_source_bank:
.a16
.i16
    lda.l SourcePacket_NmiRowLength
    dec a
    sta.l SourcePacket_NmiRowSpan
    lda.l DmaQueue+5,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_UnrolledB7_source_range
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB7_source_range:
.a16
.i16
    lda.l SourcePacket_NmiRowType
    cmp #$42
    beq SourcePacket_UnrolledB7_palette_range
    ; Generic background work must not overwrite any of the64 held OBJ
    ; cache blocks at VRAM8000..BFFF, even if a bad row claims owner0.
    lda.l DmaQueue+2,x
    clc
    adc.l SourcePacket_NmiRowSpan
    bcc SourcePacket_UnrolledB7_target_valid
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB7_target_valid:
.a16
.i16
    sta.l SourcePacket_NmiTargetEnd
    lda.l DmaQueue+2,x
    cmp #$8000
    bcc SourcePacket_UnrolledB7_below_obj
    cmp #$C000
    bcs SourcePacket_UnrolledB7_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB7_below_obj:
.a16
.i16
    lda.l SourcePacket_NmiTargetEnd
    cmp #$8000
    bcc SourcePacket_UnrolledB7_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB7_palette_range:
.a16
.i16
    ; Background CGRAM is byte0..255. OBJ palettes remain resource-owned.
    lda.l DmaQueue+2,x
    cmp #256
    bcc SourcePacket_UnrolledB7_palette_target
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB7_palette_target:
.a16
.i16
    clc
    adc.l SourcePacket_NmiRowLength
    cmp #257
    bcc SourcePacket_UnrolledB7_next
    jml SourcePacket_CheckBackgroundBudget__bad
SourcePacket_UnrolledB7_next:
.a16
.i16
ldx #64
    lda #64
    cpx #64
    jml SourcePacket_CheckBackgroundBudget__good
SourcePacket_UnrolledEnd:
