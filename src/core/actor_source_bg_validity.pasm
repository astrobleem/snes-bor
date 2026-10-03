; Opt-in S7 BG no-eviction validity lease. Not a production include.
; $7E1640..165F: above Screen end $162A, below source world $1700.
; A completed staged column remains exact while asset identity is unchanged,
; no slot has been evicted since cache init, and all pixel/map transfers have
; completed. Any eviction disables this optimization until next stage load.
; New dynamic BG writers must explicitly invalidate; otherwise fail admission.
S7BG_Valid = $7E1640
S7BG_Tainted = $7E1642
S7BG_Identity = $7E1644

S7BG_Init:
    php
    sei
    rep #$31
    .a16
    .i16
    lda #0
    sta.l S7BG_Valid
    sta.l S7BG_Tainted
    jml S7BG_InitResume

; Hook only the original allocator's occupied-slot branch. Free allocations
; have no added cost and cannot invalidate an existing binding.
S7BG_Eviction:
    .a16
    .i16
    php
    pha
    lda #0
    sta.l S7BG_Valid
    lda #1
    sta.l S7BG_Tainted
    pla
    plp
    sta.l StreamCache_OldTile
    jml S7BG_EvictionResume

S7BG_BootReady:
    .a16
    .i16
    pha
    rep #$31
    .a16
    .i16
    ; Every initial column/pixel was written synchronously under forced blank.
    ; Capture the immutable asset identity, not the current camera coordinate.
    lda.l Game_StageIndex
    sta.l S7BG_Identity
    lda.l StreamScroll_TilemapOffLo
    sta.l S7BG_Identity+2
    lda.l StreamScroll_TilemapOffHi
    and #$00FF
    sta.l S7BG_Identity+4
    lda.l StreamStage_TilesBaseLo
    sta.l S7BG_Identity+6
    lda.l StreamStage_TilesBaseHi
    and #$00FF
    sta.l S7BG_Identity+8
    lda.l StreamScroll_WidthTiles
    sta.l S7BG_Identity+10
    lda.l StreamScroll_HeightTiles
    sta.l S7BG_Identity+12
    lda.l S7BG_Tainted
    bne S7BG_BootReady__done
    lda #$B671
    sta.l S7BG_Valid
S7BG_BootReady__done:
    .a16
    .i16
    pla
    plp
    rep #$31
    .a16
    .i16
    jml S7BG_Bank0Rts

; Hook replaces only STA PendCol after the original picker has run.
; Thus uncapped Screen_TargetX demand and the original repair cursor advance
; are preserved, as are extension decisions and all service opportunities.
S7BG_AfterPick:
    .a16
    .i16
    php
    pha
    phx
    lda.l S7BG_Valid
    cmp #$B671
    beq S7BG_AfterPick__lease
    jmp S7BG_Slow
S7BG_AfterPick__lease:
    .a16
    .i16
    lda.l StreamScroll_DesiredLo
    cmp.l StreamScroll_StagedLo
    bcs S7BG_AfterPick__lo
    jmp S7BG_Slow
S7BG_AfterPick__lo:
    .a16
    .i16
    lda.l StreamScroll_StagedHi
    cmp.l StreamScroll_DesiredHi
    bcs S7BG_AfterPick__inside
    jmp S7BG_Slow
S7BG_AfterPick__inside:
    .a16
    .i16
    lda.l StreamScroll_PendCol
    cmp #$FFFF
    beq S7BG_AfterPick__pending
    jmp S7BG_Slow
S7BG_AfterPick__pending:
    .a16
    .i16
    lda.l StreamScroll_ColPending
    and #$00FF
    beq S7BG_AfterPick__identity
    jmp S7BG_Slow
S7BG_AfterPick__identity:
    .a16
    .i16
    lda.l Game_StageIndex
    cmp.l S7BG_Identity
    beq S7BG_Id1
    brl S7BG_Invalidate
S7BG_Id1:
    .a16
    .i16
    lda.l StreamScroll_TilemapOffLo
    cmp.l S7BG_Identity+2
    beq S7BG_Id2
    brl S7BG_Invalidate
S7BG_Id2:
    .a16
    .i16
    lda.l StreamScroll_TilemapOffHi
    and #$00FF
    cmp.l S7BG_Identity+4
    beq S7BG_Id3
    brl S7BG_Invalidate
S7BG_Id3:
    .a16
    .i16
    lda.l StreamStage_TilesBaseLo
    cmp.l S7BG_Identity+6
    beq S7BG_Id4
    brl S7BG_Invalidate
S7BG_Id4:
    .a16
    .i16
    lda.l StreamStage_TilesBaseHi
    and #$00FF
    cmp.l S7BG_Identity+8
    beq S7BG_Id5
    brl S7BG_Invalidate
S7BG_Id5:
    .a16
    .i16
    lda.l StreamScroll_WidthTiles
    cmp.l S7BG_Identity+10
    beq S7BG_Id6
    brl S7BG_Invalidate
S7BG_Id6:
    .a16
    .i16
    lda.l StreamScroll_HeightTiles
    cmp.l S7BG_Identity+12
    beq S7BG_Id7
    brl S7BG_Invalidate
S7BG_Id7:
    .a16
    .i16
    ldx #0
S7BG_Queue:
    .a16
    .i16
    lda.l DmaQueue+4,x
    and #$0040
    bne S7BG_Slow
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc S7BG_Queue
S7BG_Fast:
    .a16
    .i16
    lda #S7BG_Enable
    beq S7BG_Slow
    ; Hits never refresh SlotStamp. A successful repair advances CurrentStamp
    ; once; preserve that effect and the picker's already-advanced RepairCur.
    sep #$20
    .a8
    lda.l StreamCache_CurrentStamp
    inc a
    sta.l StreamCache_CurrentStamp
    rep #$30
    .a16
    .i16
    plx
    pla
    plp
    ; Original Play epilogue restores its saved P; no Seek/Resolve/ColPending.
    jml S7BG_PlayFinish
S7BG_Invalidate:
    .a16
    .i16
    lda #0
    sta.l S7BG_Valid
S7BG_Slow:
    .a16
    .i16
    plx
    pla
    plp
    sta.l StreamScroll_PendCol
    jml S7BG_PickResume
