; Use the established palette allocator/queue/fence for one exact pending
; default-Kula walk palette while its immutable tiles are still transferring.
; All other poses retain the original attack prewarm routine unchanged.
SourceWalkPalette_Dispatch:
.a16
.i16
    php
    rep #$30
    pha
    lda.l SourceVisual_EntryScratch+1
    and #255
    cmp #1
    beq SourceWalkPalette_Selected
    pla
    plp
    jml SourceVisual_PrewarmAttackPalette
SourceWalkPalette_Selected:
.a16
.i16
    pla
    plp
    jml SourceVisual_PrewarmWalkPalette
; Prepare only a single physical-player attack palette in an existing
; foreground service visit. No tile Ready, presentation or held-pin writes.
; The ordinary post-tile palette fence still controls every publication.
SourceVisual_PrewarmWalkPalette:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    lda.l $7E46DE
    cmp #0
    beq SourceVisual_PrewarmWalkPalette__guard0
    brl SourceVisual_PrewarmWalkPalette__done
SourceVisual_PrewarmWalkPalette__guard0:
.a16
.i16
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq SourceVisual_PrewarmWalkPalette__guard1
    brl SourceVisual_PrewarmWalkPalette__done
SourceVisual_PrewarmWalkPalette__guard1:
.a16
.i16
    lda.l Game_State
    cmp #0
    beq SourceVisual_PrewarmWalkPalette__guard2
    brl SourceVisual_PrewarmWalkPalette__done
SourceVisual_PrewarmWalkPalette__guard2:
.a16
.i16
    lda.l $7E175E
    cmp #2
    beq SourceVisual_PrewarmWalkPalette__guard3
    brl SourceVisual_PrewarmWalkPalette__done
SourceVisual_PrewarmWalkPalette__guard3:
.a16
.i16
    lda.l $7E1760
    cmp #1
    beq SourceVisual_PrewarmWalkPalette__guard4
    brl SourceVisual_PrewarmWalkPalette__done
SourceVisual_PrewarmWalkPalette__guard4:
.a16
.i16
    lda.l $7E46DC
    cmp #1
    beq SourceVisual_PrewarmWalkPalette__guard5
    brl SourceVisual_PrewarmWalkPalette__done
SourceVisual_PrewarmWalkPalette__guard5:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SourceVisual_PrewarmWalkPalette__guard6
    brl SourceVisual_PrewarmWalkPalette__done
SourceVisual_PrewarmWalkPalette__guard6:
.a16
.i16
    lda.l SourceVisual_ServiceOnly
    cmp #2
    bcc SourceVisual_PrewarmWalkPalette__guard7
    brl SourceVisual_PrewarmWalkPalette__done
SourceVisual_PrewarmWalkPalette__guard7:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    cmp #2
    bcc SourceVisual_PrewarmWalkPalette__guard8
    brl SourceVisual_PrewarmWalkPalette__done
SourceVisual_PrewarmWalkPalette__guard8:
.a16
.i16
    ; BW-RAM is read only after the WRAM ownership/conversion guards.
    jsl SourcePalette_Bridge_SVActor_Enabled
    bcs SourceVisual_PrewarmWalkPalette__enabled
    brl SourceVisual_PrewarmWalkPalette__done
SourceVisual_PrewarmWalkPalette__enabled:
.a16
.i16
    tdc
    cmp #$0A00
    beq SourceVisual_PrewarmWalkPalette__dp0
    cmp #$0A85
    beq SourceVisual_PrewarmWalkPalette__dp1
    brl SourceVisual_PrewarmWalkPalette__done
SourceVisual_PrewarmWalkPalette__dp0:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    beq SourceVisual_PrewarmWalkPalette__physical
    brl SourceVisual_PrewarmWalkPalette__done
SourceVisual_PrewarmWalkPalette__dp1:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    cmp #1
    beq SourceVisual_PrewarmWalkPalette__physical
    brl SourceVisual_PrewarmWalkPalette__done
SourceVisual_PrewarmWalkPalette__physical:
.a16
.i16
    lda CHAR_HP
    and #$00FF
    cmp #0
    bne SourceVisual_PrewarmWalkPalette__guard9
    brl SourceVisual_PrewarmWalkPalette__done
SourceVisual_PrewarmWalkPalette__guard9:
.a16
.i16
    lda CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    beq SourceVisual_PrewarmWalkPalette__guard10
    brl SourceVisual_PrewarmWalkPalette__done
SourceVisual_PrewarmWalkPalette__guard10:
.a16
.i16
    lda CHAR_SELECTED
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
    bne SourceVisual_PrewarmWalkPalette__guard11
    brl SourceVisual_PrewarmWalkPalette__done
SourceVisual_PrewarmWalkPalette__guard11:
.a16
.i16
    lda CHAR_ROSTER_INDEX
    and #$00FF
    cmp #22
    beq SourceVisual_PrewarmWalkPalette__guard12
    brl SourceVisual_PrewarmWalkPalette__done
SourceVisual_PrewarmWalkPalette__guard12:
.a16
.i16
    lda.l SourceVisual_EntryScratch
    and #$00FF
    cmp #22
    beq SourceVisual_PrewarmWalkPalette__guard13
    brl SourceVisual_PrewarmWalkPalette__done
SourceVisual_PrewarmWalkPalette__guard13:
.a16
.i16
    lda.l SourceVisual_EntryScratch+1
    and #$00FF
    cmp #1
    beq SourceWalkPalette_MapCheck
    brl SourceVisual_PrewarmWalkPalette__done
SourceWalkPalette_MapCheck:
.a16
.i16
    lda CHAR_MAP_INDEX
    and #255
    beq SourceWalkPalette_NativeMap
    brl SourceVisual_PrewarmWalkPalette__done
SourceWalkPalette_NativeMap:
.a16
.i16
    lda.l SourceVisual_EntryScratch+3
    and #255
    beq SourceVisual_PrewarmWalkPalette__guard14
    brl SourceVisual_PrewarmWalkPalette__done
SourceVisual_PrewarmWalkPalette__guard14:
.a16
.i16
    lda.l SourceVisual_EntryScratch+14
    and #$00FF
    cmp #1
    beq SourceVisual_PrewarmWalkPalette__guard15
    brl SourceVisual_PrewarmWalkPalette__done
SourceVisual_PrewarmWalkPalette__guard15:
.a16
.i16
    ; The existing player loader can progress beside an already-visible
    ; NPC producer. Only a producer still missing its first picture excludes it.
    jsl SourcePalette_Bridge_SVActor_LoadOwnerNeedsFirstPicture
    bcc SourceVisual_PrewarmWalkPalette__owner
    brl SourceVisual_PrewarmWalkPalette__done
SourceVisual_PrewarmWalkPalette__owner:
.a16
.i16
    tdc
    sec
    sbc #$0A00
    tax
    lda.l SourceVisual_Sa1OwnerPolicy,x
    and #$00FF
    cmp #2
    beq SourceVisual_PrewarmWalkPalette__policy
    brl SourceVisual_PrewarmWalkPalette__done
SourceVisual_PrewarmWalkPalette__policy:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    asl a
    asl a
    cmp.l SourceVisual_Record
    beq SourceVisual_PrewarmWalkPalette__record
    brl SourceVisual_PrewarmWalkPalette__done
SourceVisual_PrewarmWalkPalette__record:
.a16
.i16
    tax
    lda.l SourceVisual_State,x
    cmp.l SourceVisual_EntryIndexSaved
    beq SourceVisual_PrewarmWalkPalette__guard16
    brl SourceVisual_PrewarmWalkPalette__done
SourceVisual_PrewarmWalkPalette__guard16:
.a16
.i16
    lda.l SourceVisual_State+6,x
    cmp #1
    beq SourceVisual_PrewarmWalkPalette__guard17
    brl SourceVisual_PrewarmWalkPalette__done
SourceVisual_PrewarmWalkPalette__guard17:
.a16
.i16
    lda.l SourceVisual_State+4,x
    cmp #0
    beq SourceVisual_PrewarmWalkPalette__guard18
    brl SourceVisual_PrewarmWalkPalette__done
SourceVisual_PrewarmWalkPalette__guard18:
.a16
.i16
    lda.l SourceVisual_State+28,x
    and #$00FF
    cmp #0
    beq SourceVisual_PrewarmWalkPalette__guard19
    brl SourceVisual_PrewarmWalkPalette__done
SourceVisual_PrewarmWalkPalette__guard19:
.a16
.i16
    lda.l SourceVisual_State+30,x
    and #$00FF
    cmp #1
    beq SourceVisual_PrewarmWalkPalette__guard20
    brl SourceVisual_PrewarmWalkPalette__done
SourceVisual_PrewarmWalkPalette__guard20:
.a16
.i16
    ; Never rewrite palette staging while a real descriptor reads it.
    jsl SourcePalette_Bridge_SourceRom_HasPaletteDma
    bcc SourceVisual_PrewarmWalkPalette__staging_free
    brl SourceVisual_PrewarmWalkPalette__done
SourceVisual_PrewarmWalkPalette__staging_free:
.a16
.i16
    ; Preserve the normal OAM slot/byte reservation before reading media.
    lda #32
    jsl SourcePalette_Bridge_SourceRom_CheckDmaSlot
    bcs SourceVisual_PrewarmWalkPalette__slot
    brl SourceVisual_PrewarmWalkPalette__done
SourceVisual_PrewarmWalkPalette__slot:
.a16
.i16
    jsl SourcePalette_Bridge_SourceVisual_AllocatePalettes
    bcs SourceVisual_PrewarmWalkPalette__allocated
    brl SourceVisual_PrewarmWalkPalette__done
SourceVisual_PrewarmWalkPalette__allocated:
.a16
.i16
    jsl SourcePalette_Bridge_SourceVisual_QueuePalettes
    bcc SourceVisual_PrewarmWalkPalette__done
    lda.l SourceVisual_Record
    tax
    lda #1
    sta.l SourceVisual_State+4,x
SourceVisual_PrewarmWalkPalette__done:
.a16
.i16
    rep #$30
    ply
    plx
    pla
    plp
    rtl


SourceWalkPalette_End:
