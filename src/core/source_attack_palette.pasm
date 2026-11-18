; Prepare only a single physical-player attack palette in an existing
; foreground service visit. No tile Ready, presentation or held-pin writes.
; The ordinary post-tile palette fence still controls every publication.
SourceVisual_PrewarmAttackPalette:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    lda.l $7E46DE
    cmp #0
    beq SourceVisual_PrewarmAttackPalette__guard0
    brl SourceVisual_PrewarmAttackPalette__done
SourceVisual_PrewarmAttackPalette__guard0:
.a16
.i16
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq SourceVisual_PrewarmAttackPalette__guard1
    brl SourceVisual_PrewarmAttackPalette__done
SourceVisual_PrewarmAttackPalette__guard1:
.a16
.i16
    lda.l Game_State
    cmp #0
    beq SourceVisual_PrewarmAttackPalette__guard2
    brl SourceVisual_PrewarmAttackPalette__done
SourceVisual_PrewarmAttackPalette__guard2:
.a16
.i16
    lda.l $7E175E
    cmp #2
    beq SourceVisual_PrewarmAttackPalette__guard3
    brl SourceVisual_PrewarmAttackPalette__done
SourceVisual_PrewarmAttackPalette__guard3:
.a16
.i16
    lda.l $7E1760
    cmp #1
    beq SourceVisual_PrewarmAttackPalette__guard4
    brl SourceVisual_PrewarmAttackPalette__done
SourceVisual_PrewarmAttackPalette__guard4:
.a16
.i16
    lda.l $7E46DC
    cmp #1
    beq SourceVisual_PrewarmAttackPalette__guard5
    brl SourceVisual_PrewarmAttackPalette__done
SourceVisual_PrewarmAttackPalette__guard5:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SourceVisual_PrewarmAttackPalette__guard6
    brl SourceVisual_PrewarmAttackPalette__done
SourceVisual_PrewarmAttackPalette__guard6:
.a16
.i16
    lda.l SourceVisual_ServiceOnly
    cmp #1
    beq SourceVisual_PrewarmAttackPalette__guard7
    brl SourceVisual_PrewarmAttackPalette__done
SourceVisual_PrewarmAttackPalette__guard7:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    cmp #2
    bcc SourceVisual_PrewarmAttackPalette__guard8
    brl SourceVisual_PrewarmAttackPalette__done
SourceVisual_PrewarmAttackPalette__guard8:
.a16
.i16
    ; BW-RAM is read only after the WRAM ownership/conversion guards.
    jsl SourcePalette_Bridge_SVActor_Enabled
    bcs SourceVisual_PrewarmAttackPalette__enabled
    brl SourceVisual_PrewarmAttackPalette__done
SourceVisual_PrewarmAttackPalette__enabled:
.a16
.i16
    tdc
    cmp #$0A00
    beq SourceVisual_PrewarmAttackPalette__dp0
    cmp #$0A85
    beq SourceVisual_PrewarmAttackPalette__dp1
    brl SourceVisual_PrewarmAttackPalette__done
SourceVisual_PrewarmAttackPalette__dp0:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    beq SourceVisual_PrewarmAttackPalette__physical
    brl SourceVisual_PrewarmAttackPalette__done
SourceVisual_PrewarmAttackPalette__dp1:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    cmp #1
    beq SourceVisual_PrewarmAttackPalette__physical
    brl SourceVisual_PrewarmAttackPalette__done
SourceVisual_PrewarmAttackPalette__physical:
.a16
.i16
    lda CHAR_HP
    and #$00FF
    cmp #0
    bne SourceVisual_PrewarmAttackPalette__guard9
    brl SourceVisual_PrewarmAttackPalette__done
SourceVisual_PrewarmAttackPalette__guard9:
.a16
.i16
    lda CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    beq SourceVisual_PrewarmAttackPalette__guard10
    brl SourceVisual_PrewarmAttackPalette__done
SourceVisual_PrewarmAttackPalette__guard10:
.a16
.i16
    lda CHAR_SELECTED
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
    bne SourceVisual_PrewarmAttackPalette__guard11
    brl SourceVisual_PrewarmAttackPalette__done
SourceVisual_PrewarmAttackPalette__guard11:
.a16
.i16
    lda CHAR_ROSTER_INDEX
    and #$00FF
    cmp #22
    beq SourceVisual_PrewarmAttackPalette__guard12
    brl SourceVisual_PrewarmAttackPalette__done
SourceVisual_PrewarmAttackPalette__guard12:
.a16
.i16
    lda.l SourceVisual_EntryScratch
    and #$00FF
    cmp #22
    beq SourceVisual_PrewarmAttackPalette__guard13
    brl SourceVisual_PrewarmAttackPalette__done
SourceVisual_PrewarmAttackPalette__guard13:
.a16
.i16
    lda.l SourceVisual_EntryScratch+1
    and #$00FF
    cmp #2
    beq SourceVisual_PrewarmAttackPalette__guard14
    brl SourceVisual_PrewarmAttackPalette__done
SourceVisual_PrewarmAttackPalette__guard14:
.a16
.i16
    lda.l SourceVisual_EntryScratch+14
    and #$00FF
    cmp #1
    beq SourceVisual_PrewarmAttackPalette__guard15
    brl SourceVisual_PrewarmAttackPalette__done
SourceVisual_PrewarmAttackPalette__guard15:
.a16
.i16
    ; The existing player loader can progress beside an already-visible
    ; NPC producer. Only a producer still missing its first picture excludes it.
    jsl SourcePalette_Bridge_SVActor_LoadOwnerNeedsFirstPicture
    bcc SourceVisual_PrewarmAttackPalette__owner
    brl SourceVisual_PrewarmAttackPalette__done
SourceVisual_PrewarmAttackPalette__owner:
.a16
.i16
    tdc
    sec
    sbc #$0A00
    tax
    lda.l SourceVisual_Sa1OwnerPolicy,x
    and #$00FF
    cmp #2
    beq SourceVisual_PrewarmAttackPalette__policy
    brl SourceVisual_PrewarmAttackPalette__done
SourceVisual_PrewarmAttackPalette__policy:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    asl a
    asl a
    cmp.l SourceVisual_Record
    beq SourceVisual_PrewarmAttackPalette__record
    brl SourceVisual_PrewarmAttackPalette__done
SourceVisual_PrewarmAttackPalette__record:
.a16
.i16
    tax
    lda.l SourceVisual_State,x
    cmp.l SourceVisual_EntryIndexSaved
    beq SourceVisual_PrewarmAttackPalette__guard16
    brl SourceVisual_PrewarmAttackPalette__done
SourceVisual_PrewarmAttackPalette__guard16:
.a16
.i16
    lda.l SourceVisual_State+6,x
    cmp #1
    beq SourceVisual_PrewarmAttackPalette__guard17
    brl SourceVisual_PrewarmAttackPalette__done
SourceVisual_PrewarmAttackPalette__guard17:
.a16
.i16
    lda.l SourceVisual_State+4,x
    cmp #0
    beq SourceVisual_PrewarmAttackPalette__guard18
    brl SourceVisual_PrewarmAttackPalette__done
SourceVisual_PrewarmAttackPalette__guard18:
.a16
.i16
    lda.l SourceVisual_State+28,x
    and #$00FF
    cmp #0
    beq SourceVisual_PrewarmAttackPalette__guard19
    brl SourceVisual_PrewarmAttackPalette__done
SourceVisual_PrewarmAttackPalette__guard19:
.a16
.i16
    lda.l SourceVisual_State+30,x
    and #$00FF
    cmp #2
    beq SourceVisual_PrewarmAttackPalette__guard20
    brl SourceVisual_PrewarmAttackPalette__done
SourceVisual_PrewarmAttackPalette__guard20:
.a16
.i16
    ; Never rewrite palette staging while a real descriptor reads it.
    jsl SourcePalette_Bridge_SourceRom_HasPaletteDma
    bcc SourceVisual_PrewarmAttackPalette__staging_free
    brl SourceVisual_PrewarmAttackPalette__done
SourceVisual_PrewarmAttackPalette__staging_free:
.a16
.i16
    ; Preserve the normal OAM slot/byte reservation before reading media.
    lda #32
    jsl SourcePalette_Bridge_SourceRom_CheckDmaSlot
    bcs SourceVisual_PrewarmAttackPalette__slot
    brl SourceVisual_PrewarmAttackPalette__done
SourceVisual_PrewarmAttackPalette__slot:
.a16
.i16
    jsl SourcePalette_Bridge_SourceVisual_AllocatePalettes
    bcs SourceVisual_PrewarmAttackPalette__allocated
    brl SourceVisual_PrewarmAttackPalette__done
SourceVisual_PrewarmAttackPalette__allocated:
.a16
.i16
    jsl SourcePalette_Bridge_SourceVisual_QueuePalettes
    bcc SourceVisual_PrewarmAttackPalette__done
    lda.l SourceVisual_Record
    tax
    lda #1
    sta.l SourceVisual_State+4,x
SourceVisual_PrewarmAttackPalette__done:
.a16
.i16
    rep #$30
    ply
    plx
    pla
    plp
    rtl

