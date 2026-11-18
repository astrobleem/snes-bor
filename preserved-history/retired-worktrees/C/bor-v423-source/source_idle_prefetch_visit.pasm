; Existing bounded prefetch gets a safe visit after a metadata seek.
; It never reads MSU data and restores the pending row cursor/registers.
; All original snapshot, input-journal, DMA budget, free-slot, private-job
; and physical completion guards remain authoritative.
SourceIdlePrefetch_SeekThenVisit:
.a16
.i16
    jsl SourceIdlePrefetch_Seek
    jsl SourcePrefetch_DuringWait
    rep #$31
    rtl
SourceIdlePrefetch_Seek:
.a16
.i16
    .db $F4
    .dw ((SourcePalette_Bridge_SVActor_Enabled+2)&$FFFF)
    jml SourceVisual_Seek
SourceIdlePrefetch_P1:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    ldx #0
    lda.l SourceVisual_State+6,x
    cmp #1
    beq SourceIdlePrefetch_P1Mode
    cmp #2
    beq SourceIdlePrefetch_P1Mode
    brl SourceIdlePrefetch_No
SourceIdlePrefetch_P1Mode:
.a16
.i16
    lda.l SourceVisual_State+28,x
    and #255
    cmp #2
    bcc SourceIdlePrefetch_P1Picture
    brl SourceIdlePrefetch_No
SourceIdlePrefetch_P1Picture:
.a16
.i16
    lda.l SourceVisual_CompletedValid
    cmp #1
    beq SourceIdlePrefetch_P1Guard0
    brl SourceIdlePrefetch_No
SourceIdlePrefetch_P1Guard0:
.a16
.i16
    lda.l SourceVisual_CompletedStage
    cmp #0
    beq SourceIdlePrefetch_P1Guard1
    brl SourceIdlePrefetch_No
SourceIdlePrefetch_P1Guard1:
.a16
.i16
    lda.l SourceVisual_CompletedRoster
    cmp #22
    beq SourceIdlePrefetch_P1Guard2
    brl SourceIdlePrefetch_No
SourceIdlePrefetch_P1Guard2:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+1
    and #255
    cmp #0
    beq SourceIdlePrefetch_P1Guard3
    brl SourceIdlePrefetch_No
SourceIdlePrefetch_P1Guard3:
.a16
.i16
    brl SourceIdlePrefetch_Yes
SourceIdlePrefetch_P2:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    ldx #32
    lda.l SourceVisual_State+6,x
    cmp #1
    beq SourceIdlePrefetch_P2Mode
    cmp #2
    beq SourceIdlePrefetch_P2Mode
    brl SourceIdlePrefetch_No
SourceIdlePrefetch_P2Mode:
.a16
.i16
    lda.l SourceVisual_State+28,x
    and #255
    cmp #2
    bcc SourceIdlePrefetch_P2Picture
    brl SourceIdlePrefetch_No
SourceIdlePrefetch_P2Picture:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SourceIdlePrefetch_P2Guard0
    brl SourceIdlePrefetch_No
SourceIdlePrefetch_P2Guard0:
.a16
.i16
    lda.l SVActor_Data+SVActor_Stage
    cmp #0
    beq SourceIdlePrefetch_P2Guard1
    brl SourceIdlePrefetch_No
SourceIdlePrefetch_P2Guard1:
.a16
.i16
    lda.l SVActor_Data+SVActor_Roster
    cmp #22
    beq SourceIdlePrefetch_P2Guard2
    brl SourceIdlePrefetch_No
SourceIdlePrefetch_P2Guard2:
.a16
.i16
    lda.l SVActor_Data+1
    and #255
    cmp #0
    beq SourceIdlePrefetch_P2Guard3
    brl SourceIdlePrefetch_No
SourceIdlePrefetch_P2Guard3:
.a16
.i16
    brl SourceIdlePrefetch_Yes
SourceIdlePrefetch_Yes:
.a16
.i16
    ply
    plx
    pla
    plp
    sec
    rtl
SourceIdlePrefetch_No:
.a16
.i16
    ply
    plx
    pla
    plp
    clc
    rtl
SourceIdlePrefetch_End:
