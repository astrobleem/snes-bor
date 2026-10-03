; S8 Normal ACCEPTED_COMPAT host, included with stage_bounds in main's bank15.
; No private globals: timer owns 100Hz credits, StageEnv owns per-actor state.
; Main CPU only. All public wrappers preserve P/X/Y/D/DBR; A clobbered.
; Bool wrappers return C explicitly. Physics sees PHYSICAL slots, never P2
; context aliases. Normal only (campaign3); Easy follows its existing path.
StageBoundsHost_Normal:
    rep #$31
.a16
.i16
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq StageBoundsHost_Normal__yes
    clc
    rtl
StageBoundsHost_Normal__yes:
    sec
    rtl

; Called BEFORE P2 context entry and by direct movement callers. Retired
; player slots restored by an OUT/join/continue path regain clean pit state.
StageBoundsHost_BeforeActor:
    php
    rep #$31
.a16
.i16
    phx
    phy
    jsl StageBoundsHost_Normal
    bcc StageBoundsHost_BeforeActor__no
    jsr StageBoundsHost_ReconcilePlayer
    jsl StageBounds_IsActive
    bcs StageBoundsHost_BeforeActor__owned
    jsr StageDrop_BeforeActor
    bcc StageBoundsHost_BeforeActor__no
StageBoundsHost_BeforeActor__owned:
    ply
    plx
    plp
    sec
    rtl
StageBoundsHost_BeforeActor__no:
    rep #$30
.a16
.i16
    ply
    plx
    plp
    clc
    rtl

StageBoundsHost_ReconcilePlayer:
.a16
.i16
    jsl StageBounds_Row
    lda.l StageBounds_State,x
    cmp #2
    bne StageBoundsHost_ReconcilePlayer__done
    txa
    beq StageBoundsHost_ReconcilePlayer__player
    cmp #CHAR_ZP_LEN
    bne StageBoundsHost_ReconcilePlayer__done
    lda.l G13_TwoPlayerEnabled
    and #$00FF
    beq StageBoundsHost_ReconcilePlayer__done
StageBoundsHost_ReconcilePlayer__player:
.a16
    lda CHAR_HP
    and #$00FF
    beq StageBoundsHost_ReconcilePlayer__done
    jsl StageBounds_ResetActor
StageBoundsHost_ReconcilePlayer__done:
    rts

; One drain at the gameplay boundary, before Core_Oop_Play. Every credit is
; applied to all six slots; no slot consumes another slot's gravity time.
StageBoundsHost_Physics:
    php
    rep #$31
.a16
.i16
    pha
    phx
    phy
    phd
    phb
    jsl StageBoundsHost_Normal
    bcc StageBoundsHost_Physics__done
    sep #$20
.a8
    lda #0
    pha
    plb
    rep #$31
.a16
.i16
    jsl StageTimer_TakeGravityTicks
    cmp #0                       ; API restores P; its returned Z is not A's Z
    beq StageBoundsHost_Physics__done
StageBoundsHost_Physics__tick:
.a16
.i16
    pha
    ldx #0
StageBoundsHost_Physics__slot:
.a16
.i16
    phx
    lda.l EntityDpBaseTable,x
    tcd
    jsr StageBoundsHost_ReconcilePlayer
    ; Collected timer items belong to the delayed-suicide service, not pits.
    lda 1,s
    tax
    lda.l StageTimer_Pending,x
    bne StageBoundsHost_Physics__next
    jsl G13_PlayerLifecycleIsOut
    bcs StageBoundsHost_Physics__next
    sep #$20
.a8
    lda CHAR_INPUT_DRIVEN
    cmp #CHAR_INPUT_DRIVEN_NONCOMBAT
    beq StageBoundsHost_Physics__next
    rep #$31
.a16
.i16
    jsl StageBounds_IsActive
    bcs StageBoundsHost_Physics__owned
    sep #$20
.a8
    lda CHAR_HP
    beq StageBoundsHost_Physics__next
StageBoundsHost_Physics__owned:
    rep #$31
.a16
.i16
    jsl StageBounds_Tick
    ; A death callback may have restored a player. Enter rechecks base/air.
    jsl StageBounds_Enter
StageBoundsHost_Physics__next:
    rep #$31
.a16
.i16
    pla
    clc
    adc #2
    tax
    cpx #12
    bcc StageBoundsHost_Physics__slot
    pla
    dec a
    bne StageBoundsHost_Physics__tick
StageBoundsHost_Physics__done:
    rep #$30
.a16
.i16
    plb
    pld
    ply
    plx
    pla
    plp
    rtl

; Post-axis commit: source player_move/common_move, not projectile/emitter
; drivers. Preserve caller width, X/Y, and all actor/render state except X.
StageBoundsHost_Clamp:
    php
    rep #$31
.a16
.i16
    phx
    phy
    jsl StageBoundsHost_Normal
    bcc StageBoundsHost_Clamp__done
    lda CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    beq StageBoundsHost_Clamp__apply
    cmp #CHAR_INPUT_DRIVEN_AI
    bne StageBoundsHost_Clamp__done
StageBoundsHost_Clamp__apply:
    jsl StageBounds_Clamp
StageBoundsHost_Clamp__done:
    rep #$30
.a16
.i16
    ply
    plx
    plp
    rtl

; Last request override, AFTER ordinary blink/altitude/attribute composition.
; C set means skip mirror emission for this owned request.
StageBoundsHost_Render:
    php
    rep #$31
.a16
.i16
    phx
    phy
    jsl StageBoundsHost_Normal
    bcc StageBoundsHost_Render__no
    jsr StageDrop_Render
    bcs StageBoundsHost_Render__owned
    jsl StageBounds_Render
    bcc StageBoundsHost_Render__no
StageBoundsHost_Render__owned:
    ply
    plx
    plp
    sec
    rtl
StageBoundsHost_Render__no:
    rep #$30
.a16
.i16
    ply
    plx
    plp
    clc
    rtl

; Shared successful-spawn point covers all old slot-specific paths plus
; slot45 and steamer children. Reset BEFORE authored base/alias binding.
StageBoundsHost_ResetSpawn:
    php
    rep #$31
.a16
.i16
    phx
    phy
    phd
    jsl StageBoundsHost_Normal
    bcc StageBoundsHost_ResetSpawn__done
    lda.l Spawn_ScratchSlotOfs
    clc
    adc #$0A00
    tcd
    jsl StageBounds_ResetActor
    jsr StageDrop_ResetSpawn
StageBoundsHost_ResetSpawn__done:
    rep #$30
.a16
.i16
    pld
    ply
    plx
    plp
    rtl

; Actual BOR pit death: player_takedamage a<PIT_DEPTH calls player_die;
; obstacle_takedamage a<=PIT_DEPTH kills BEFORE the item-spawn branch.
; The compat HP range is <=255, so force10000 is terminal. No hit score,
; pickup reward, fresh knockdown/blink delay, or fake drop at ground level.
StageBounds_ApplyPitDamage_Long:
    php
    rep #$31
.a16
.i16
    phx
    phy
    phd
    phb
    jsl StageBoundsHost_Normal
    bcs StageBoundsHost_ApplyPitDamage__normal
    jmp StageBoundsHost_ApplyPitDamage__done
StageBoundsHost_ApplyPitDamage__normal:
.a16
.i16
    jsl StageBounds_Row
    phx
    jsl HudOpponent_Remove
    plx
    ; Cancel pending item ownership using a slot ID, not an actor byte offset.
    txa
    ldy #0
StageBoundsHost_ApplyPitDamage__slot:
.a16
.i16
    cmp #CHAR_ZP_LEN
    bcc StageBoundsHost_ApplyPitDamage__have_slot
    sec
    sbc #CHAR_ZP_LEN
    iny
    bra StageBoundsHost_ApplyPitDamage__slot
StageBoundsHost_ApplyPitDamage__have_slot:
    tyx
    jsl StageTimer_CancelSlot
    sep #$20
.a8
    stz CHAR_HP
    stz CHAR_PICKUP_TYPE
    stz CHAR_HIT_APPLIED
    lda #CHAR_SELECTED_FALL
    sta CHAR_SELECTED
    lda #$FF
    sta CHAR_FALL_STATE_TIMER
    rep #$31
.a16
.i16
    tdc
    cmp #$0A00
    beq StageBoundsHost_ApplyPitDamage__p1
    cmp #$0A85
    bne StageBoundsHost_ApplyPitDamage__npc
    lda.l G13_TwoPlayerEnabled
    and #$00FF
    beq StageBoundsHost_ApplyPitDamage__npc
    jsl G13_SourcePlayerDeathP2
    bra StageBoundsHost_ApplyPitDamage__player_done
StageBoundsHost_ApplyPitDamage__p1:
    jsl G13_SourcePlayerDeathP1
StageBoundsHost_ApplyPitDamage__player_done:
    rep #$31
.a16
.i16
    jsr StageBoundsHost_ReconcilePlayer
    bra StageBoundsHost_ApplyPitDamage__done
StageBoundsHost_ApplyPitDamage__npc:
    ; HP0 is the canonical compat enemy/group/boss count and allocator gate.
    ; Keep the sticky IsBoss flag for the normal completion scanner.
    rep #$31
.a16
.i16
    jsl StageBounds_Row
    txa
    ldy #0
StageBoundsHost_ApplyPitDamage__item_slot:
.a16
.i16
    cmp #CHAR_ZP_LEN
    bcc StageBoundsHost_ApplyPitDamage__clear_item
    sec
    sbc #CHAR_ZP_LEN
    iny
    bra StageBoundsHost_ApplyPitDamage__item_slot
StageBoundsHost_ApplyPitDamage__clear_item:
.a16
.i16
    ; Item roster metadata is split across two pre-existing WRAM runs.
    cpy #4
    bcs StageBoundsHost_ApplyPitDamage__item45
    tya
    dec a
    tax
    sep #$20
.a8
    lda #0
    sta.l Entity1_ItemRosterIdx,x
    bra StageBoundsHost_ApplyPitDamage__done
StageBoundsHost_ApplyPitDamage__item45:
.a16
.i16
    tya
    sec
    sbc #4
    tax
    sep #$20
.a8
    lda #0
    sta.l Entity4_ItemRosterIdx,x
StageBoundsHost_ApplyPitDamage__done:
    rep #$30
.a16
.i16
    plb
    pld
    ply
    plx
    plp
    rtl

.include "stage_drop_host.pasm"
