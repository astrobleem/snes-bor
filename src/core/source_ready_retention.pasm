; Retain authenticated, unowned immutable ROM Ready rows until demand.
; The ORIGINAL 64-row allocator already evicts legal unowned Ready victims,
; checking all completed/retiring pins. No new capacity, Ready transitions,
; queue descriptors, ownership or presentation path. Pending/private jobs keep
; their original release behavior. Scope is sampled once per non-reentrant
; SCPU release loop; NMI never invokes this producer. Scratch was unused in194.
SourceReady_Scope = $7E46EE
.assert SourceReady_Scope >= SourcePrefetch_Submitted+2, "ready scope overlaps prefetch"
.assert SourceReady_Scope+2 <= SourceInput_Ring, "ready scope overlaps input ring"
SourceReady_StartRelease:
.a16
.i16
    php
    rep #$30
    cld
    pha
    phx
    phy
    phb
    phd
    lda #0
    sta.l SourceReady_Scope
    lda.l $7E46DE
    beq SourceReady_ScopeForeground
    brl SourceReady_ScopeDone
SourceReady_ScopeForeground:
.a16
.i16
    jsr SourceNpc_Scope
    bcs SourceReady_ScopeOwned
    brl SourceReady_ScopeDone
SourceReady_ScopeOwned:
.a16
.i16
    lda.l Game_StageIndex
    cmp #0
    beq SourceReady_ScopeG1
    brl SourceReady_ScopeDone
SourceReady_ScopeG1:
.a16
.i16
    lda.l $7E0A00+0+CHAR_INPUT_DRIVEN
    and #255
    cmp #1
    beq SourceReady_ScopeG2
    brl SourceReady_ScopeDone
SourceReady_ScopeG2:
.a16
.i16
    lda.l $7E0A00+0+CHAR_ROSTER_INDEX
    and #255
    cmp #22
    beq SourceReady_ScopeG3
    brl SourceReady_ScopeDone
SourceReady_ScopeG3:
.a16
.i16
    lda.l $7E0A00+0+CHAR_HP
    and #255
    cmp #0
    bne SourceReady_ScopeG4
    brl SourceReady_ScopeDone
SourceReady_ScopeG4:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy+0
    and #255
    cmp #2
    beq SourceReady_ScopeG5
    brl SourceReady_ScopeDone
SourceReady_ScopeG5:
.a16
.i16
    lda.l $7E0A00+133+CHAR_INPUT_DRIVEN
    and #255
    cmp #1
    beq SourceReady_ScopeG6
    brl SourceReady_ScopeDone
SourceReady_ScopeG6:
.a16
.i16
    lda.l $7E0A00+133+CHAR_ROSTER_INDEX
    and #255
    cmp #22
    beq SourceReady_ScopeG7
    brl SourceReady_ScopeDone
SourceReady_ScopeG7:
.a16
.i16
    lda.l $7E0A00+133+CHAR_HP
    and #255
    cmp #0
    bne SourceReady_ScopeG8
    brl SourceReady_ScopeDone
SourceReady_ScopeG8:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy+133
    and #255
    cmp #2
    beq SourceReady_ScopeG9
    brl SourceReady_ScopeDone
SourceReady_ScopeG9:
.a16
.i16
    lda #1
    sta.l SourceReady_Scope
SourceReady_ScopeDone:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    ; Execute the exact four-byte LDA replaced at the original call site.
    lda.l SourceVisual_ActorSlot
    rtl

; A8/I16 at the release loop. Preserve all registers and flags except C.
; This means KEEP an already Ready row, never mark Ready or publish it.
SourceReady_KeepEvictable:
.a8
.i16
    php
    rep #$30
    cld
    pha
    phx
    phy
    phb
    phd
    lda.l SourceReady_Scope
    cmp #1
    bne SourceReady_Fallback
    cpx #512
    bcs SourceReady_Fallback
    txa
    and #7
    bne SourceReady_Fallback
    lda.l SourceVisual_BlockCache+2,x
    cmp #2
    bne SourceReady_Fallback
    lda.l SourceVisual_BlockCache+4,x
    cmp #$0400 ; no actor owners, all four rows completed
    bne SourceReady_Fallback
    lda.l SourceVisual_BlockCache+6,x
    cmp #$A502 ; original immutable-ROM kind2/tagA5
    bne SourceReady_Fallback
    pld
    plb
    ply
    plx
    pla
    plp
    sec
    rtl
SourceReady_Fallback:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    jml SourceIdle_KeepBlock
SourceReady_End:
