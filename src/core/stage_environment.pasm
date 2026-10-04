; Generic post-spawn palette binding, all NPC slots, after final model load.
; Does not infer actor identity from aliases or select animation/physics state.
StageEnv_Start:
.include "../generated/stage_environment_maps.pasm"
.include "../generated/stage_environment_bases.pasm"
; Poppy retains label bank metadata for a bare long operand, but arithmetic
; (label+offset) loses it. Make the bank explicit for table-field expressions.
StageEnv_DataBank = $0D0000

; S3 retired this old queue allocation. Keep the 133-byte actor DP ABI stable:
; parallel metadata uses the same byte offset as its corresponding actor.
; Six rows reserve $7E550F..$7E582C, before existing scratch at $7E5893.
StageEnv_Actors = $7E550F
StageEnv_ActorRowsBytes = 798 ; six 133-byte sidecar rows
StageEnv_BaseFraction = $7E550F
StageEnv_BaseInteger = $7E5511
StageEnv_AliasId = $7E5513
StageEnv_ChildFraction = $7E5830
StageEnv_ChildInteger = $7E5832

StageEnv_ResetActors:
    jsl ActorBehavior_PreserveRoster
StageEnv_ResetActors__worker_call:
    ; Default builds keep this as a no-op. The opt-in Normal/SA-1 linker
    ; redirects this one reset boundary so the resident world is retired
    ; before StageEnv rows are cleared and reused by the next authored stage.
    jsl StageEnv_ResetActors__worker_hook
    php
    rep #$31
.a16
.i16
    phx
    ldx #0
    lda #0
StageEnv_ResetActors__loop:
    rep #$30
.a16
.i16
    sta.l StageEnv_Actors,x
    inx
    inx
    cpx #StageEnv_ActorRowsBytes
    bcc StageEnv_ResetActors__loop
    plx
    plp
    jsl ActorBehavior_RestoreRoster
    rtl

StageEnv_ResetActors__worker_hook:
    rtl

StageEnv_ApplySpawnBase:
    php
    rep #$31
.a16
.i16
    phx
    phy
    lda.l Spawn_ScratchSlotOfs
    tax
    lda #0
    sta.l StageEnv_BaseFraction,x
    sta.l StageEnv_BaseInteger,x
    sep #$20
.a8
    lda.l Spawn_B2Kind
    cmp #$FF
    beq StageEnv_ApplySpawnBase__child
    rep #$30
.a16
.i16
    ldx #0
StageEnv_ApplySpawnBase__find:
    rep #$30
.a16
.i16
    cpx #StageEnv_BaseRecordCount*6
    bcs StageEnv_ApplySpawnBase__done
    sep #$20
.a8
    lda.l StageEnv_BaseRecords,x
    cmp.l Game_StageIndex
    bne StageEnv_ApplySpawnBase__next
    lda.l StageEnv_DataBank+StageEnv_BaseRecords+1,x
    cmp.l Spawn_Index
    bne StageEnv_ApplySpawnBase__next
    rep #$20
.a16
    lda.l StageEnv_DataBank+StageEnv_BaseRecords+2,x
    pha
    lda.l StageEnv_DataBank+StageEnv_BaseRecords+4,x
    pha
    lda.l Spawn_ScratchSlotOfs
    tax
    pla
    sta.l StageEnv_BaseInteger,x
    pla
    sta.l StageEnv_BaseFraction,x
    bra StageEnv_ApplySpawnBase__done
StageEnv_ApplySpawnBase__next:
    rep #$30
.a16
.i16
    txa
    clc
    adc #6
    tax
    bra StageEnv_ApplySpawnBase__find
StageEnv_ApplySpawnBase__child:
    rep #$30
.a16
.i16
    lda.l StageEnv_ChildFraction
    sta.l StageEnv_BaseFraction,x
    lda.l StageEnv_ChildInteger
    sta.l StageEnv_BaseInteger,x
StageEnv_ApplySpawnBase__done:
    rep #$30
.a16
.i16
    ply
    plx
    plp
    rtl

StageEnv_ApplySpawnAlias:
    php
    rep #$31
.a16
.i16
    phx
    lda.l Spawn_ScratchSlotOfs
    tax
    lda #0
    sta.l StageEnv_AliasId,x
    sep #$20
.a8
    lda.l Spawn_B2Kind
    cmp #$FF
    beq StageEnv_ApplySpawnAlias__done
    rep #$30
.a16
.i16
    ldx #0
StageEnv_ApplySpawnAlias__find:
    rep #$30
.a16
.i16
    cpx #StageEnv_AliasRecordCount*4
    bcs StageEnv_ApplySpawnAlias__done
    sep #$20
.a8
    lda.l StageEnv_AliasRecords,x
    cmp.l Game_StageIndex
    bne StageEnv_ApplySpawnAlias__next
    lda.l StageEnv_DataBank+StageEnv_AliasRecords+1,x
    cmp.l Spawn_Index
    bne StageEnv_ApplySpawnAlias__next
    rep #$20
.a16
    lda.l StageEnv_DataBank+StageEnv_AliasRecords+2,x
    pha
    lda.l Spawn_ScratchSlotOfs
    tax
    pla
    sta.l StageEnv_AliasId,x
    bra StageEnv_ApplySpawnAlias__done
StageEnv_ApplySpawnAlias__next:
    rep #$30
.a16
.i16
    inx
    inx
    inx
    inx
    bra StageEnv_ApplySpawnAlias__find
StageEnv_ApplySpawnAlias__done:
    rep #$30
.a16
.i16
    plx
    plp
    rtl

StageEnv_CaptureChildBase:
    php
    rep #$31
.a16
.i16
    phx
    tdc
    sec
    sbc #$0A00
    tax
    lda.l StageEnv_BaseFraction,x
    sta.l StageEnv_ChildFraction
    lda.l StageEnv_BaseInteger,x
    sta.l StageEnv_ChildInteger
    plx
    plp
    rtl

StageEnv_EmitterThink:
    php
    sep #$20
.a8
    lda CHAR_INPUT_DRIVEN
    cmp #CHAR_INPUT_DRIVEN_NONCOMBAT
    bne StageEnv_EmitterThink__legacy
    jsl ActorBehavior_Think
    plp
    rtl
StageEnv_EmitterThink__legacy:
    .a8
    cmp #CHAR_INPUT_DRIVEN_STEAMER
    bne StageEnv_EmitterThink__steam
    jsl ActorBehavior_EmitterThink
    plp
    rtl
StageEnv_EmitterThink__steam:
    sep #$20
.a8
    cmp #CHAR_INPUT_DRIVEN_STEAM
    bne StageEnv_EmitterThink__done
    rep #$31
.a16
.i16
    phx
    tdc
    sec
    sbc #$0A00
    tax
    ; Source base += 1 at 200/THINK_SPEED=100Hz, scale .8 at 60Hz:
    ; 4/3 target pixels per frame, nearest Q16.16 = $00015555.
    lda.l StageEnv_BaseFraction,x
    clc
    adc #$5555
    sta.l StageEnv_BaseFraction,x
    lda.l StageEnv_BaseInteger,x
    adc #1
    sta.l StageEnv_BaseInteger,x
    plx
StageEnv_EmitterThink__done:
    plp
    rtl

StageEnv_ApplyBaseOffset:
    php
    rep #$31
.a16
.i16
    phx
    tdc
    sec
    sbc #$0A00
    tax
    sep #$20
.a8
    lda.l OamSetSprite_Y
    sec
    sbc.l StageEnv_BaseInteger,x
    sta.l OamSetSprite_Y
    rep #$30
.a16
.i16
    plx
    plp
    rtl

StageEnv_ApplySpawnMap:
    php
    phb
    phd
    rep #$31
.a16
.i16
    phx
    phy
    lda.l Spawn_ScratchSlotOfs
    clc
    adc #$0A00
    tcd
    sep #$20
.a8
    lda #$7E
    pha
    plb
    jsl ActorBehavior_RestoreCompat
    ; The ten-byte source queue supplies an unsigned lane byte. Hidden
    ; collected pickups park their old Y word at $7FFF; slots 1-3 write only
    ; the new low byte. Initialize the full new lane before the source-world
    ; bind, so a reused actor cannot inherit the pickup's hidden high byte.
    sep #$20
.a8
    stz CHAR_POS_Y+1
    rep #$20
.a16
    lda CHAR_ROSTER_INDEX
    and #$00FF
    tax
    sep #$20
.a8
    lda.l StageEnv_ModelMapCounts,x
    cmp.l Spawn_ScratchMap
    bcs StageEnv_ApplySpawnMap__valid
    lda #0                      ; source NULL map falls back to base palette
    bra StageEnv_ApplySpawnMap__selected
StageEnv_ApplySpawnMap__valid:
    sep #$20
.a8
    lda.l Spawn_ScratchMap
StageEnv_ApplySpawnMap__selected:
    sep #$20
.a8
    sta CHAR_MAP_INDEX
    sta.l MapApply_Index
    rep #$20
.a16
    lda CHAR_PALETTE_BASE_LO
    sta.l MapApply_PaletteBaseLo
    lda CHAR_MAP_BASE_LO
    sta.l MapApply_MapBaseLo
    sep #$20
.a8
    lda CHAR_PALETTE_BASE_HI
    sta.l MapApply_PaletteBaseHi
    lda CHAR_MAP_BASE_HI
    sta.l MapApply_MapBaseHi
    lda CHAR_PALETTE_SLOT
    sta.l MapApply_PaletteSlot
    ; Palette streaming uses absolute $2000/$2001 MMIO, not actor-bank WRAM.
    ; Restore its bank-zero hardware contract after collecting DP fields.
    lda #0
    pha
    plb
    jsl Anim_ApplyMapPalette
    jsl ActorBehavior_Bind
    rep #$30
.a16
.i16
    ply
    plx
    pld
    plb
    plp
    rtl
StageEnv_End:
