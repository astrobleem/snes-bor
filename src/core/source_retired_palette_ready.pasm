; A pending physical palette may already have retired while this player
; waited for its next compositor visit. Acknowledge using the ORIGINAL
; global staging fence and retirement routine before full lease validation.
; No media reads, publication, pin changes or Ready shortcut.
SourcePaletteRetired_ReadyLease:
.a16
.i16
    lda.l Game_CampaignId
    and #255
    cmp #3
    beq SourcePaletteRetired_Guard0
    brl SourcePaletteRetired_Validate
SourcePaletteRetired_Guard0:
.a16
.i16
    lda.l Game_State
    cmp #0
    beq SourcePaletteRetired_Guard1
    brl SourcePaletteRetired_Validate
SourcePaletteRetired_Guard1:
.a16
.i16
    lda.l $7E46DE
    cmp #0
    beq SourcePaletteRetired_Guard2
    brl SourcePaletteRetired_Validate
SourcePaletteRetired_Guard2:
.a16
.i16
    lda.l $7E175E
    cmp #2
    beq SourcePaletteRetired_Guard3
    brl SourcePaletteRetired_Validate
SourcePaletteRetired_Guard3:
.a16
.i16
    lda.l $7E1760
    cmp #1
    beq SourcePaletteRetired_Guard4
    brl SourcePaletteRetired_Validate
SourcePaletteRetired_Guard4:
.a16
.i16
    lda.l $7E46DC
    cmp #1
    beq SourcePaletteRetired_Guard5
    brl SourcePaletteRetired_Validate
SourcePaletteRetired_Guard5:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #6752
    beq SourcePaletteRetired_Guard6
    brl SourcePaletteRetired_Validate
SourcePaletteRetired_Guard6:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    cmp #2
    bcc SourcePaletteRetired_Player
    brl SourcePaletteRetired_Validate
SourcePaletteRetired_Player:
.a16
.i16
    asl a
    asl a
    asl a
    asl a
    asl a
    cmp.l SourceVisual_Record
    beq SourcePaletteRetired_Record
    brl SourcePaletteRetired_Validate
SourcePaletteRetired_Record:
.a16
.i16
    tax
    lda.l SourceVisual_State+28,x
    and #255
    beq SourcePaletteRetired_Unemitted
    brl SourcePaletteRetired_Validate
SourcePaletteRetired_Unemitted:
.a16
.i16
    lda.l SourceVisual_State+6,x
    cmp #2
    beq SourcePaletteRetired_Tiles
    brl SourcePaletteRetired_Validate
SourcePaletteRetired_Tiles:
.a16
.i16
    lda.l SourceVisual_State+4,x
    cmp #1
    beq SourcePaletteRetired_Queued
    brl SourcePaletteRetired_Validate
SourcePaletteRetired_Queued:
.a16
.i16
    lda.l SourceVisual_State,x
    cmp.l SourceVisual_EntryIndexSaved
    beq SourcePaletteRetired_Identity
    brl SourcePaletteRetired_Validate
SourcePaletteRetired_Identity:
.a16
.i16
    lda.l SourceVisual_EntryScratch+14
    and #255
    cmp #1
    beq SourcePaletteRetired_OnePalette
    brl SourcePaletteRetired_Validate
SourcePaletteRetired_OnePalette:
.a16
.i16
    lda.l SourceVisual_State+16,x
    and #255
    beq SourcePaletteRetired_Validate
    cmp #9
    bcs SourcePaletteRetired_Validate
    dec a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_PaletteCache,x
    cmp.l SourceVisual_PieceTable+10
    bne SourcePaletteRetired_Validate
    lda.l SourceVisual_PaletteCache+3,x
    and #255
    cmp #2
    bne SourcePaletteRetired_Validate
    jsl SourcePalette_Bridge_SourceRom_HasPaletteDma
    bcs SourcePaletteRetired_Validate
    jsl SourcePaletteRetired_Mark
SourcePaletteRetired_Validate:
.a16
.i16
    jsl SourcePaletteRetired_OriginalReady
    bcc SourcePaletteRetired_NotReady
    jml SourcePaletteRetired_ReadyReturn
SourcePaletteRetired_NotReady:
.a16
.i16
    jml SourceVisual_LoadResources__need_admission
SourcePaletteRetired_OriginalReady:
.a16
.i16
    .db $F4
    .dw ((SourcePalette_Bridge_SVActor_Enabled+2)&$FFFF)
    jml SVActor_ReadyLease
SourcePaletteRetired_Mark:
.a16
.i16
    .db $F4
    .dw ((SourcePalette_Bridge_SVActor_Enabled+2)&$FFFF)
    jml SourceVisual_MarkPaletteDmaRetired
SourcePaletteRetired_End:
