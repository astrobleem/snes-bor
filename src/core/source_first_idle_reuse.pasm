; First-picture media reduction, not a source animation change.
; A new idle NPC may initially display authored idle frame0 already held by
; another same-model NPC. Exact tile-ID sets across both remaps are proven
; by the catalog-derived mask. Its own geometry, palette and source lifetime
; still go through the ordinary catalog/allocator/full-picture publication.
SourceFirstIdle_MapMask = $435464
SourceFirstIdle_LeaseMode = $435466
SourceFirstIdle_TargetMask = $435468
SourceFirstIdle_TargetDP = $43546A
SourceFirstIdle_Replace = $43546C
SourceFirstIdle_Record = $43546E
SourceVisual_PreferSharedFirstIdle:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq SourceVisual_PreferSharedFirstIdle__campaign
    brl SourceVisual_PreferSharedFirstIdle__done
SourceVisual_PreferSharedFirstIdle__campaign:
.a16
.i16
    lda #0
    sta.l SourceFirstIdle_Replace
    tdc
    sta.l SourceFirstIdle_TargetDP
    cmp #$0B0A
    beq SourceVisual_PreferSharedFirstIdle__npc2
    cmp #$0B8F
    beq SourceVisual_PreferSharedFirstIdle__npc3
    cmp #$0C14
    beq SourceVisual_PreferSharedFirstIdle__npc4
    cmp #$0C99
    beq SourceVisual_PreferSharedFirstIdle__npc5
    brl SourceVisual_PreferSharedFirstIdle__done
SourceVisual_PreferSharedFirstIdle__npc2:
.a16
.i16
    ldy #4
    ldx #1280
    lda #64
    sta.l SourceFirstIdle_Record
    lda.l SourceVisual_State+64+6
    bra SourceVisual_PreferSharedFirstIdle__new_lease
SourceVisual_PreferSharedFirstIdle__npc3:
.a16
.i16
    ldy #8
    ldx #2560
    lda #96
    sta.l SourceFirstIdle_Record
    lda.l SourceVisual_State+96+6
    bra SourceVisual_PreferSharedFirstIdle__new_lease
SourceVisual_PreferSharedFirstIdle__npc4:
.a16
.i16
    ldy #16
    ldx #3840
    lda #128
    sta.l SourceFirstIdle_Record
    lda.l SourceVisual_State+128+6
    bra SourceVisual_PreferSharedFirstIdle__new_lease
SourceVisual_PreferSharedFirstIdle__npc5:
.a16
.i16
    ldy #32
    ldx #5120
    lda #160
    sta.l SourceFirstIdle_Record
    lda.l SourceVisual_State+160+6
SourceVisual_PreferSharedFirstIdle__new_lease:
.a16
.i16
    cmp #2
    bcc SourceVisual_PreferSharedFirstIdle__empty_lease
    brl SourceVisual_PreferSharedFirstIdle__done
SourceVisual_PreferSharedFirstIdle__empty_lease:
.a16
.i16
    sta.l SourceFirstIdle_LeaseMode
    tya
    sta.l SourceFirstIdle_TargetMask
    lda.l SVActor_Data+SVActor_Valid,x
    cmp #0
    beq SourceVisual_PreferSharedFirstIdle__empty_picture
    brl SourceVisual_PreferSharedFirstIdle__done
SourceVisual_PreferSharedFirstIdle__empty_picture:
.a16
.i16
    lda.l SourceVisual_CompletedMagic
    cmp #$C04D
    beq SourceVisual_PreferSharedFirstIdle__completed
    brl SourceVisual_PreferSharedFirstIdle__done
SourceVisual_PreferSharedFirstIdle__completed:
.a16
.i16
    lda.l SVActor_Magic
    cmp #$AC19
    beq SourceVisual_PreferSharedFirstIdle__actor
    brl SourceVisual_PreferSharedFirstIdle__done
SourceVisual_PreferSharedFirstIdle__actor:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SourceVisual_PreferSharedFirstIdle__input
    brl SourceVisual_PreferSharedFirstIdle__done
SourceVisual_PreferSharedFirstIdle__input:
.a16
.i16
    lda.l Game_State
    beq SourceVisual_PreferSharedFirstIdle__playing
    brl SourceVisual_PreferSharedFirstIdle__done
SourceVisual_PreferSharedFirstIdle__playing:
.a16
.i16
    lda.l Stage_Mirror
    and #$00FF
    beq SourceVisual_PreferSharedFirstIdle__mirror
    brl SourceVisual_PreferSharedFirstIdle__done
SourceVisual_PreferSharedFirstIdle__mirror:
.a16
.i16
    lda CHAR_HP
    and #$00FF
    bne SourceVisual_PreferSharedFirstIdle__alive
    brl SourceVisual_PreferSharedFirstIdle__done
SourceVisual_PreferSharedFirstIdle__alive:
.a16
.i16
    lda.l SourceVisual_Key+1
    and #$00FF
    beq SourceVisual_PreferSharedFirstIdle__idle
    brl SourceVisual_PreferSharedFirstIdle__done
SourceVisual_PreferSharedFirstIdle__idle:
.a16
.i16
    lda.l SourceVisual_Key+2
    and #$00FF
    bne SourceVisual_PreferSharedFirstIdle__later_idle
    brl SourceVisual_PreferSharedFirstIdle__done
SourceVisual_PreferSharedFirstIdle__later_idle:
.a16
.i16
    lda CHAR_ROSTER_INDEX
    and #$00FF
    cmp.l SourceVisual_Key
    beq SourceVisual_PreferSharedFirstIdle__native_model
    brl SourceVisual_PreferSharedFirstIdle__done
SourceVisual_PreferSharedFirstIdle__native_model:
.a16
.i16
    sep #$20
.a8
    lda CHAR_MAP_INDEX
    cmp.l SourceVisual_Key+3
    rep #$30
.a16
.i16
    beq SourceVisual_PreferSharedFirstIdle__native_map
    brl SourceVisual_PreferSharedFirstIdle__done
SourceVisual_PreferSharedFirstIdle__native_map:
.a16
.i16
    tdc
    sec
    sbc #$0A00
    tax
    lda.l SourceVisual_Sa1OwnerPolicy,x
    and #$00FF
    cmp #1
    beq SourceVisual_PreferSharedFirstIdle__bound
    cmp #2
    beq SourceVisual_PreferSharedFirstIdle__bound
    brl SourceVisual_PreferSharedFirstIdle__done
SourceVisual_PreferSharedFirstIdle__bound:
.a16
.i16
    ; Only redirect an unshown lease which has acquired NO tile pins.
    ; The normal replacement path below still fences queued physical DMA.
    lda.l SourceFirstIdle_LeaseMode
    beq SourceVisual_PreferSharedFirstIdle__unstarted_ok
    lda.l SourceFirstIdle_Record
    tax
    lda.l SourceVisual_State+28,x
    and #$00FF
    beq SourceVisual_PreferSharedFirstIdle__unseen
    brl SourceVisual_PreferSharedFirstIdle__done
SourceVisual_PreferSharedFirstIdle__unseen:
.a16
.i16
    lda.l SourceVisual_State+29,x
    cmp.l SourceVisual_Key
    beq SourceVisual_PreferSharedFirstIdle__same_idle
    brl SourceVisual_PreferSharedFirstIdle__done
SourceVisual_PreferSharedFirstIdle__same_idle:
.a16
.i16
    ldx #0
SourceVisual_PreferSharedFirstIdle__pins:
.a16
.i16
    lda.l SourceVisual_BlockCache+4,x
    ora.l SVActor_HeldBlocks,x
    ora.l SVActor_OldBlocks,x
    and.l SourceFirstIdle_TargetMask
    beq SourceVisual_PreferSharedFirstIdle__next_pin
    brl SourceVisual_PreferSharedFirstIdle__done
SourceVisual_PreferSharedFirstIdle__next_pin:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #512
    bcc SourceVisual_PreferSharedFirstIdle__pins
    ldx #0
SourceVisual_PreferSharedFirstIdle__palettes:
.a16
.i16
    lda.l SVActor_HeldPalettes,x
    ora.l SVActor_OldPalettes,x
    and.l SourceFirstIdle_TargetMask
    beq SourceVisual_PreferSharedFirstIdle__next_palette
    brl SourceVisual_PreferSharedFirstIdle__done
SourceVisual_PreferSharedFirstIdle__next_palette:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourceVisual_PreferSharedFirstIdle__palettes
SourceVisual_PreferSharedFirstIdle__unstarted_ok:
.a16
.i16
    lda.l SourceVisual_Key+3
    and #$00FF
    cmp #16
    bcc SourceVisual_PreferSharedFirstIdle__map
    brl SourceVisual_PreferSharedFirstIdle__done
SourceVisual_PreferSharedFirstIdle__map:
.a16
.i16
    tay
    lda #1
SourceVisual_PreferSharedFirstIdle__map_shift:
.a16
.i16
    cpy #0
    beq SourceVisual_PreferSharedFirstIdle__map_bit
    asl a
    dey
    bra SourceVisual_PreferSharedFirstIdle__map_shift
SourceVisual_PreferSharedFirstIdle__map_bit:
.a16
.i16
    tay
    lda.l SourceVisual_Key
    and #$00FF
    asl a
    tax
    lda.l SourceFirstIdle_MapMasks,x
    sta.l SourceFirstIdle_MapMask
    tya
    and.l SourceFirstIdle_MapMask
    
    bne SourceVisual_PreferSharedFirstIdle__donors
    brl SourceVisual_PreferSharedFirstIdle__done
SourceVisual_PreferSharedFirstIdle__donors:
.a16
.i16
    ldx #1280
SourceVisual_PreferSharedFirstIdle__donor:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid,x
    cmp #1
    beq SourceVisual_PreferSharedFirstIdle__valid
    brl SourceVisual_PreferSharedFirstIdle__next
SourceVisual_PreferSharedFirstIdle__valid:
.a16
.i16
    lda.l SVActor_Data+SVActor_Stage,x
    cmp.l Game_StageIndex
    beq SourceVisual_PreferSharedFirstIdle__stage
    brl SourceVisual_PreferSharedFirstIdle__next
SourceVisual_PreferSharedFirstIdle__stage:
.a16
.i16
    lda.l SVActor_Data+SVActor_Roster,x
    cmp.l SourceVisual_Key
    beq SourceVisual_PreferSharedFirstIdle__roster
    brl SourceVisual_PreferSharedFirstIdle__next
SourceVisual_PreferSharedFirstIdle__roster:
.a16
.i16
    lda.l SVActor_Data,x
    cmp.l SourceVisual_Key
    beq SourceVisual_PreferSharedFirstIdle__role
    brl SourceVisual_PreferSharedFirstIdle__next
SourceVisual_PreferSharedFirstIdle__role:
.a16
.i16
    lda.l SVActor_Data+2,x
    and #$00FF
    beq SourceVisual_PreferSharedFirstIdle__frame0
    brl SourceVisual_PreferSharedFirstIdle__next
SourceVisual_PreferSharedFirstIdle__frame0:
.a16
.i16
    lda.l SVActor_Data+12,x
    and #$00FF
    cmp #1
    bcs SourceVisual_PreferSharedFirstIdle__nonempty
    brl SourceVisual_PreferSharedFirstIdle__next
SourceVisual_PreferSharedFirstIdle__nonempty:
.a16
.i16
    cmp #66
    bcc SourceVisual_PreferSharedFirstIdle__count
    brl SourceVisual_PreferSharedFirstIdle__next
SourceVisual_PreferSharedFirstIdle__count:
.a16
.i16
    lda.l SVActor_Data+3,x
    and #$00FF
    cmp #16
    bcc SourceVisual_PreferSharedFirstIdle__donor_map
    brl SourceVisual_PreferSharedFirstIdle__next
SourceVisual_PreferSharedFirstIdle__donor_map:
.a16
.i16
    tay
    lda #1
SourceVisual_PreferSharedFirstIdle__donor_shift:
.a16
.i16
    cpy #0
    beq SourceVisual_PreferSharedFirstIdle__donor_bit
    asl a
    dey
    bra SourceVisual_PreferSharedFirstIdle__donor_shift
SourceVisual_PreferSharedFirstIdle__donor_bit:
.a16
.i16
    and.l SourceFirstIdle_MapMask
    bne SourceVisual_PreferSharedFirstIdle__choose
    brl SourceVisual_PreferSharedFirstIdle__next
SourceVisual_PreferSharedFirstIdle__choose:
.a16
.i16
    lda.l SourceFirstIdle_LeaseMode
    sta.l SourceFirstIdle_Replace
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_Key+2
    rep #$30
.a16
.i16
    brl SourceVisual_PreferSharedFirstIdle__done
SourceVisual_PreferSharedFirstIdle__next:
.a16
.i16
    txa
    clc
    adc #1280
    tax
    cpx #6400
    bcs SourceVisual_PreferSharedFirstIdle__done
    brl SourceVisual_PreferSharedFirstIdle__donor
SourceVisual_PreferSharedFirstIdle__done:
.a16
.i16
    ply
    plx
    pla
    plp
    rtl

SourceFirstIdle_MapMasks:
    .dw $000F,$0007,$000F,$000F,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0003,$0001,$0001
    .dw $0001,$0001,$0001,$0001,$0001,$0001,$0003,$0003,$0003,$0003,$0003,$0001,$0003,$003F,$000F,$0003
    .dw $001F,$0001,$0001,$0000,$0001,$0003,$0001,$0001,$0003,$007F,$0003,$0001,$0007,$0001,$0001,$0001
    .dw $003F,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000
    .dw $0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000
    .dw $0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000
    .dw $0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000
    .dw $0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000
    .dw $0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000
    .dw $0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000
    .dw $0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000
    .dw $0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000
    .dw $0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000
    .dw $0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000
    .dw $0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000
    .dw $0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000,$0000

; C=1 only for the same unstarted idle lease just proposed by FindEntry.
; This grants entry to the existing DMA-fenced replacement path, never Ready.
SourceVisual_FirstIdleCanReplace:
.a16
.i16
    phx
    lda.l SourceFirstIdle_Replace
    cmp #1
    bne SourceVisual_FirstIdleCanReplace__no
    tdc
    cmp.l SourceFirstIdle_TargetDP
    bne SourceVisual_FirstIdleCanReplace__no
    lda.l SourceVisual_ActorSlot
    cmp #2
    bcc SourceVisual_FirstIdleCanReplace__no
    cmp #6
    bcs SourceVisual_FirstIdleCanReplace__no
    lda.l SourceVisual_Record
    cmp.l SourceFirstIdle_Record
    bne SourceVisual_FirstIdleCanReplace__no
    tax
    lda.l SourceVisual_State+6,x
    cmp #1
    bne SourceVisual_FirstIdleCanReplace__no
    lda.l SourceVisual_State+28,x
    and #$00FF
    bne SourceVisual_FirstIdleCanReplace__no
    lda.l SourceVisual_State+29,x
    cmp.l SourceVisual_Key
    bne SourceVisual_FirstIdleCanReplace__no
    lda.l SourceVisual_Key+1
    bne SourceVisual_FirstIdleCanReplace__no
    lda #0
    sta.l SourceFirstIdle_Replace
    plx
    sec
    rtl
SourceVisual_FirstIdleCanReplace__no:
.a16
.i16
    plx
    clc
    rtl
