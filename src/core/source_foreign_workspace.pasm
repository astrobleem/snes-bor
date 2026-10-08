; Opt-in foreign foreground workspace overlay of the retired original FP cache.
; No automatic enable. The whole Mode4 canvas owner must already have retired
; ordinary frontpanel producers and drained all eight legacy DMA descriptors.
; The source foreign renderer owns frontpanel/HUD composition separately.
; This lease never means MOTU gameplay admission. Bank zero is unchanged.
SourceForeignWork_Ready = $7FBFDA
SourceForeignWork_Status = $7FBFDC
SourceForeignWork_Generation = $7FBFDE
SourceForeignWork_End = $7FBFE2
SOURCE_FOREIGN_WORK_BASE = $7FA000
SOURCE_FOREIGN_WORK_BYTES = 6400
SOURCE_FOREIGN_WORK_END = $7FB900

; Init X/Y=nonzero 32-bit generation. Preserve A/X/Y/DBR/DP/P except carry.
; Only Ready=0 may initialize; reinitialization must be an explicit release.
SourceForeignWork_Init:
.a16
.i16
 php
 rep #$31
 pha
 phx
 phy
 lda.l SourceForeignWork_Ready
 beq SourceForeignWork_InitGeneration
 jmp SourceForeignWork_Bad
SourceForeignWork_InitGeneration:
.a16
.i16
 txa
 sta.l SourceForeignWork_Generation
 tya
 sta.l SourceForeignWork_Generation+2
 ora.l SourceForeignWork_Generation
 bne SourceForeignWork_InitCanvas
 jmp SourceForeignWork_Bad
SourceForeignWork_InitCanvas:
.a16
.i16
 jsl SourceForeignWork_CheckCanvas
 bcc SourceForeignWork_InitClear
 jmp SourceForeignWork_Bad
SourceForeignWork_InitClear:
.a16
.i16
 ldx #0
SourceForeignWork_InitQueue:
.a16
.i16
 lda.l DmaQueue+4,x
 and #DMA_OPT_ACTIVE
 beq SourceForeignWork_InitQueueNext
 jmp SourceForeignWork_Bad
SourceForeignWork_InitQueueNext:
.a16
.i16
 txa
 clc
 adc #8
 tax
 cpx #64
 bne SourceForeignWork_InitQueue
 ldx #0
 lda #0
SourceForeignWork_Clear:
.a16
.i16
 sta.l SOURCE_FOREIGN_WORK_BASE,x
 inx
 inx
 cpx #SOURCE_FOREIGN_WORK_BYTES
 bne SourceForeignWork_Clear
 lda #1
 sta.l SourceForeignWork_Status
 lda #$B671
 sta.l SourceForeignWork_Ready
 jmp SourceForeignWork_Good

; Check X/Y=current generation. No actor/player state is changed on rejection.
SourceForeignWork_Check:
.a16
.i16
 php
 rep #$31
 pha
 phx
 phy
 lda.l SourceForeignWork_Ready
 cmp #$B671
 beq SourceForeignWork_CheckGeneration
 jmp SourceForeignWork_Bad
SourceForeignWork_CheckGeneration:
.a16
.i16
 txa
 cmp.l SourceForeignWork_Generation
 beq SourceForeignWork_CheckHigh
 jmp SourceForeignWork_Bad
SourceForeignWork_CheckHigh:
.a16
.i16
 tya
 cmp.l SourceForeignWork_Generation+2
 beq SourceForeignWork_CheckNonzero
 jmp SourceForeignWork_Bad
SourceForeignWork_CheckNonzero:
.a16
.i16
 ora.l SourceForeignWork_Generation
 bne SourceForeignWork_CheckRetired
 jmp SourceForeignWork_Bad
SourceForeignWork_CheckRetired:
.a16
.i16
 jsl SourceForeignWork_CheckCanvas
 bcc SourceForeignWork_Good
 jmp SourceForeignWork_Bad
SourceForeignWork_Good:
.a16
.i16
 ply
 plx
 pla
 plp
 clc
 rtl
SourceForeignWork_Bad:
.a16
.i16
 lda #2
 sta.l SourceForeignWork_Status
 ply
 plx
 pla
 plp
 sec
 rtl

; The published raster owner ABI is 7FF840 B4B0 /7FF862 B4B1. This also
; excludes the original Mode1 frontpanel producer before overlay access.
SourceForeignWork_CheckCanvas:
.a16
.i16
 php
 rep #$31
 pha
 phx
 lda.l $7FF840
 cmp #$B4B0
 bne SourceForeignWork_CanvasBadNear
 lda.l $7FF862
 cmp #$B4B1
 bne SourceForeignWork_CanvasBadNear
 lda.l $7FF856
 bne SourceForeignWork_CanvasBadNear
 ; Explicit canvas handoff must retire the legacy water NMI owner too.
 ; Its state lies inside this overlay and cannot be inspected after leasing.
 lda.l $7FF866
 cmp #$B672
 bne SourceForeignWork_CanvasBadNear
 ; Scanline targets must not refer into this WRAM overlay.
 lda.l $7FF846
 and #$00FF
 cmp #$7F
 beq SourceForeignWork_CanvasBadNear
 lda.l StageFp_BG2Loaded
 and #$00FF
 bne SourceForeignWork_CanvasBadNear
 lda.l StageFp_BG2Active
 and #$00FF
 bne SourceForeignWork_CanvasBadNear
 lda.l StageFp_BG2DmaPending
 and #$00FF
 bne SourceForeignWork_CanvasBadNear
 lda.l StageFp_BG2Booting
 and #$00FF
 bne SourceForeignWork_CanvasBadNear
 lda.l StreamScrollFp_ColPending
 and #$00FF
 bne SourceForeignWork_CanvasBadNear
 lda.l StreamScrollFp_Enabled
 and #$00FF
 bne SourceForeignWork_CanvasBadNear
 bra SourceForeignWork_QueueStart
SourceForeignWork_CanvasBadNear:
.a16
.i16
 jmp SourceForeignWork_CanvasBad
SourceForeignWork_QueueStart:
.a16
.i16
 ldx #0
SourceForeignWork_QueueCheck:
.a16
.i16
 lda.l DmaQueue+4,x
 and #DMA_OPT_ACTIVE
 beq SourceForeignWork_QueueNext
 lda.l DmaQueue+7,x
 and #$00FF
 cmp #$7F
 bne SourceForeignWork_QueueNext
 lda.l DmaQueue+4,x
 and #DMA_OPT_FIXED_SOURCE
 bne SourceForeignWork_QueueFixed
 lda.l DmaQueue+5,x
 pha
 clc
 adc.l DmaQueue,x
 bcs SourceForeignWork_QueueStackBad
 cmp #$A001
 bcc SourceForeignWork_QueueStackGood
 pla
 cmp #$B900
 bcc SourceForeignWork_CanvasBad
 bra SourceForeignWork_QueueNext
SourceForeignWork_QueueFixed:
.a16
.i16
 lda.l DmaQueue+5,x
 cmp #$A000
 bcc SourceForeignWork_QueueNext
 cmp #$B900
 bcc SourceForeignWork_CanvasBad
 bra SourceForeignWork_QueueNext
SourceForeignWork_QueueStackGood:
.a16
.i16
 pla
SourceForeignWork_QueueNext:
.a16
.i16
 txa
 clc
 adc #8
 tax
 cpx #64
 bne SourceForeignWork_QueueCheck
 plx
 pla
 plp
 clc
 rtl
SourceForeignWork_QueueStackBad:
.a16
.i16
 pla
SourceForeignWork_CanvasBad:
.a16
.i16
 plx
 pla
 plp
 sec
 rtl
