; Unused eight-byte tail follows the 24-byte saved entry at $7EEFE0..F7.
; Zero certifies there are no private jobs awaiting a physical cookie.
; Future producer must increment under FrameBusy after successful enqueue;
; authenticated first completion decrements exactly once. Init clears it.
SourcePrefetch_PhysicalPending = $7EEFF8
SourcePrefetch_HotIds:
    .dw $2B70,$1775,$118D,$3A7C,$3591,$31EF,$2CC9,$3D5F,$18E6,$00CB,$4233,$4049,$2877,$3E3B,$2608,$3FF8,$3432,$0497,$41E9,$38A7,$001C,$3C74
SourcePrefetch_HotAddresses:
    .dw $B700,$DD00,$A700,$D900,$A700,$FD00,$CD00,$FA00,$F000,$8D00,$B700,$A000,$9400,$8700,$FB00,$9E00,$9A00,$B200,$B400,$C700,$8100,$F400
SourcePrefetch_HotBanks:
    .dw $003A,$0036,$0036,$003B,$003B,$003A,$003A,$003B,$0036,$0035,$003C,$003C,$003A,$003C,$0037,$003C,$003B,$0035,$003C,$003B,$0035,$003B

; v167 plumbing: private optional ROM-prefetch completion certificate.
; No producer is enabled in this phase. Existing job descriptor ABI unchanged.
; Cookie helper reads WRAM and immutable ROM only, NEVER actor BW-RAM.
; Cache tagA6=awaiting four physical rows; A7=all four physical rows matched.
SourcePrefetch_HotCount = 22
SourcePrefetch_HotIdsLo = SourcePrefetch_HotIds & $FFFF
SourcePrefetch_HotAddressesLo = SourcePrefetch_HotAddresses & $FFFF
SourcePrefetch_HotBanksLo = SourcePrefetch_HotBanks & $FFFF

; A16/I16, DBR=$3C. A=global ID, C=found, Y=word offset. A/X preserved.
SourcePrefetch_FindHot:
.a16
.i16
    ldy #0
SourcePrefetch_FindHot__loop:
.a16
.i16
    cmp.w SourcePrefetch_HotIdsLo,y
    beq SourcePrefetch_FindHot__yes
    iny
    iny
    cpy #SourcePrefetch_HotCount*2
    bcc SourcePrefetch_FindHot__loop
    clc
    rts
SourcePrefetch_FindHot__yes:
.a16
.i16
    sec
    rts

; A16/I16, X=queue-byte offset. C1/A=cache-record offset on exact match.
; Preserve X/Y/D/DB/P except C. No writes to guest data, queue or BW-RAM.
SourcePrefetch_ValidateJob:
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
    beq SourcePrefetch_ValidateJob__guard0
    brl SourcePrefetch_ValidateJob__no
SourcePrefetch_ValidateJob__guard0:
.a16
.i16
    cpx #64
    bcc SourcePrefetch_ValidateJob__guard1
    brl SourcePrefetch_ValidateJob__no
SourcePrefetch_ValidateJob__guard1:
.a16
.i16
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq SourcePrefetch_ValidateJob__guard2
    brl SourcePrefetch_ValidateJob__no
SourcePrefetch_ValidateJob__guard2:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SourcePrefetch_ValidateJob__guard3
    brl SourcePrefetch_ValidateJob__no
SourcePrefetch_ValidateJob__guard3:
.a16
.i16
    lda.l SourceVisual_CompletedMagic
    cmp #$C04D
    beq SourcePrefetch_ValidateJob__guard4
    brl SourcePrefetch_ValidateJob__no
SourcePrefetch_ValidateJob__guard4:
.a16
.i16
    txa
    lsr a
    lsr a
    lsr a
    tax
    lda.l DmaQueue_Owner,x
    and #$00FF
    beq SourcePrefetch_ValidateJob__guard5
    brl SourcePrefetch_ValidateJob__no
SourcePrefetch_ValidateJob__guard5:
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
    beq SourcePrefetch_ValidateJob__guard6
    brl SourcePrefetch_ValidateJob__no
SourcePrefetch_ValidateJob__guard6:
.a16
.i16
    lda $00
    cmp #256
    beq SourcePrefetch_ValidateJob__guard7
    brl SourcePrefetch_ValidateJob__no
SourcePrefetch_ValidateJob__guard7:
.a16
.i16
    lda $02
    sec
    sbc #$8000
    bcs SourcePrefetch_ValidateJob__guard8
    brl SourcePrefetch_ValidateJob__no
SourcePrefetch_ValidateJob__guard8:
.a16
.i16
    tay
    and #$C63F
    beq SourcePrefetch_ValidateJob__guard9
    brl SourcePrefetch_ValidateJob__no
SourcePrefetch_ValidateJob__guard9:
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
    beq SourcePrefetch_ValidateJob__guard10
    brl SourcePrefetch_ValidateJob__no
SourcePrefetch_ValidateJob__guard10:
.a16
.i16
    lda.l SourceVisual_BlockCache+5,x
    cmp #$0204
    beq SourcePrefetch_ValidateJob__guard11
    brl SourcePrefetch_ValidateJob__no
SourcePrefetch_ValidateJob__guard11:
.a16
.i16
    lda.l SourceVisual_BlockCache+7,x
    and #$00FF
    cmp #$00A6
    beq SourcePrefetch_ValidateJob__tag
    cmp #$00A7
    beq SourcePrefetch_ValidateJob__tag
    brl SourcePrefetch_ValidateJob__no
SourcePrefetch_ValidateJob__tag:
.a16
.i16
    lda.l SourceVisual_BlockCache,x
    jsr SourcePrefetch_FindHot
    bcs SourcePrefetch_ValidateJob__guard13
    brl SourcePrefetch_ValidateJob__no
SourcePrefetch_ValidateJob__guard13:
.a16
.i16
    lda $05
    cmp.w SourcePrefetch_HotAddressesLo,y
    beq SourcePrefetch_ValidateJob__guard14
    brl SourcePrefetch_ValidateJob__no
SourcePrefetch_ValidateJob__guard14:
.a16
.i16
    lda $07
    and #$00FF
    cmp.w SourcePrefetch_HotBanksLo,y
    beq SourcePrefetch_ValidateJob__guard15
    brl SourcePrefetch_ValidateJob__no
SourcePrefetch_ValidateJob__guard15:
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
SourcePrefetch_ValidateJob__no:
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

; JML continuation after the FOURTH MDMA write, not an enqueue acknowledgment.
; Original handler's Y remains on the real short-call stack. Original ABI:
; A=$0800,C1,M16/I16, originalX/Y/D/DB. Original short return is in bank0.
SourcePrefetch_AfterPhysical:
.a8
.i16
    rep #$31
.a16
.i16
    lda.l SourcePrefetch_PhysicalPending
    beq SourcePrefetch_AfterPhysical__return
    txy
    txa
    lsr a
    lsr a
    lsr a
    tax
    lda.l DmaQueue_Owner,x
    and #$00FF
    bne SourcePrefetch_AfterPhysical__ordinary
    tyx
    phx
    jsl SourcePrefetch_ValidateJob
    bcc SourcePrefetch_AfterPhysical__not_private
    tax
    sep #$20
.a8
    lda.l SourceVisual_BlockCache+7,x
    cmp #$A6
    bne SourcePrefetch_AfterPhysical__cookie_written
    lda #$A7
    sta.l SourceVisual_BlockCache+7,x
    rep #$31
.a16
.i16
    lda.l SourcePrefetch_PhysicalPending
    beq SourcePrefetch_AfterPhysical__cookie_written
    dec a
    sta.l SourcePrefetch_PhysicalPending
SourcePrefetch_AfterPhysical__cookie_written:
.a8
.i16
    rep #$31
.a16
.i16
SourcePrefetch_AfterPhysical__not_private:
.a16
.i16
    plx
    bra SourcePrefetch_AfterPhysical__return
SourcePrefetch_AfterPhysical__ordinary:
.a16
.i16
    tyx
SourcePrefetch_AfterPhysical__return:
.a16
.i16
    lda #2048
    sec
    ply
    jml Core_Dma_SourceBlock_Return
SourcePrefetch_CanRetire:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    txa
    and #7
    beq SourcePrefetch_CanRetire__local0
    brl SourcePrefetch_CanRetire__no
SourcePrefetch_CanRetire__local0:
.a16
.i16
    cpx #512
    bcc SourcePrefetch_CanRetire__local1
    brl SourcePrefetch_CanRetire__no
SourcePrefetch_CanRetire__local1:
.a16
.i16
    ; Both high owner bits already belong to P1 completed/retiring artwork.
    ; Private state is a reset-on-allocation tag, never an owner-bit alias.
    lda.l SourceVisual_BlockCache+7,x
    and #$00FF
    cmp #$00A6
    beq SourcePrefetch_CanRetire__no_tag
    cmp #$00A7
    beq SourcePrefetch_CanRetire__local2
    brl SourcePrefetch_CanRetire__yes
SourcePrefetch_CanRetire__no_tag:
.a16
.i16
    brl SourcePrefetch_CanRetire__no
SourcePrefetch_CanRetire__local2:
.a16
.i16
    lda.l $7E46DE
    beq SourcePrefetch_CanRetire__local3
    brl SourcePrefetch_CanRetire__no
SourcePrefetch_CanRetire__local3:
.a16
.i16
    jsr SourceNpc_Scope
    bcs SourcePrefetch_CanRetire__local4
    brl SourcePrefetch_CanRetire__no
SourcePrefetch_CanRetire__local4:
.a16
.i16
    lda.l SourceVisual_BlockCache+2,x
    cmp #1
    beq SourcePrefetch_CanRetire__local5
    brl SourcePrefetch_CanRetire__no
SourcePrefetch_CanRetire__local5:
.a16
.i16
    lda.l SourceVisual_BlockCache+5,x
    cmp #$0204
    beq SourcePrefetch_CanRetire__local6
    brl SourcePrefetch_CanRetire__no
SourcePrefetch_CanRetire__local6:
.a16
.i16
    lda.l SourceVisual_BlockCache+7,x
    and #$00FF
    cmp #$00A7
    beq SourcePrefetch_CanRetire__local7
    brl SourcePrefetch_CanRetire__no
SourcePrefetch_CanRetire__local7:
.a16
.i16
    lda.l SVActor_HeldBlocks,x
    ora.l SVActor_OldBlocks,x
    and #$00FF
    beq SourcePrefetch_CanRetire__local8
    brl SourcePrefetch_CanRetire__no
SourcePrefetch_CanRetire__local8:
.a16
.i16
    sep #$20
.a8
    lda #$3C
    pha
    plb
    rep #$30
.a16
.i16
    lda.l SourceVisual_BlockCache,x
    jsr SourcePrefetch_FindHot
    bcs SourcePrefetch_CanRetire__local9
    brl SourcePrefetch_CanRetire__no
SourcePrefetch_CanRetire__local9:
.a16
.i16
SourcePrefetch_CanRetire__yes:
.a16
.i16
    plb
    ply
    plx
    pla
    plp
    sec
    rtl
SourcePrefetch_CanRetire__no:
.a16
.i16
    rep #$30
    plb
    ply
    plx
    pla
    plp
    clc
    rtl

; Narrow optional retention only. Ordinary lowest legal victim can evict it.
; Called after original desired-owner removal and held/retiring protection.
SourcePrefetch_KeepReady:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    lda.l SourceVisual_BlockCache+2,x
    cmp #2
    beq SourcePrefetch_KeepReady__local0
    brl SourcePrefetch_KeepReady__no
SourcePrefetch_KeepReady__local0:
.a16
.i16
    lda.l SourceVisual_BlockCache+5,x
    cmp #$0204
    beq SourcePrefetch_KeepReady__local1
    brl SourcePrefetch_KeepReady__no
SourcePrefetch_KeepReady__local1:
.a16
.i16
    lda.l SourceVisual_BlockCache+7,x
    and #$00FF
    cmp #$00A7
    beq SourcePrefetch_KeepReady__local2
    brl SourcePrefetch_KeepReady__no
SourcePrefetch_KeepReady__local2:
.a16
.i16
    jsr SourceNpc_Scope
    bcs SourcePrefetch_KeepReady__local3
    brl SourcePrefetch_KeepReady__no
SourcePrefetch_KeepReady__local3:
.a16
.i16
    lda.l Game_StageIndex
    beq SourcePrefetch_KeepReady__stage0
    brl SourcePrefetch_KeepReady__no
SourcePrefetch_KeepReady__stage0:
.a16
.i16
    sep #$20
.a8
    lda #$3C
    pha
    plb
    rep #$30
.a16
.i16
    lda.l SourceVisual_BlockCache,x
    jsr SourcePrefetch_FindHot
    bcs SourcePrefetch_KeepReady__local4
    brl SourcePrefetch_KeepReady__no
SourcePrefetch_KeepReady__local4:
.a16
.i16
    plb
    ply
    plx
    pla
    plp
    sec
    rtl
SourcePrefetch_KeepReady__no:
.a16
.i16
    rep #$30
    plb
    ply
    plx
    pla
    plp
    clc
    rtl


SourcePrefetch_KeepPending:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    lda.l SourceVisual_BlockCache+2,x
    cmp #1
    bne SourcePrefetch_KeepPending__no
    lda.l SourceVisual_BlockCache+5,x
    cmp #$0204
    bne SourcePrefetch_KeepPending__no
    lda.l SourceVisual_BlockCache+7,x
    and #$00FF
    cmp #$00A6
    beq SourcePrefetch_KeepPending__tag
    cmp #$00A7
    bne SourcePrefetch_KeepPending__no
SourcePrefetch_KeepPending__tag:
.a16
.i16
    sep #$20
.a8
    lda #$3C
    pha
    plb
    rep #$30
.a16
.i16
    lda.l SourceVisual_BlockCache,x
    jsr SourcePrefetch_FindHot
    bcc SourcePrefetch_KeepPending__no
    plb
    ply
    plx
    pla
    plp
    sec
    rtl
SourcePrefetch_KeepPending__no:
.a16
.i16
    plb
    ply
    plx
    pla
    plp
    clc
    rtl

; No producer/hook until completion and full-cache plumbing is proven.
SourcePrefetch_Tick:
.a16
.i16
    rtl
