; Native S8 callback adapters, bank 5 (included by hud_opponent.pasm).
; All public calls preserve A (including B), X/Y/P/D/DBR. I16 inputs.
; No new WRAM. Only HUD state is written. Campaign gate is in Target/Remove.
;
; Physical-player proof from current source:
; CharacterEntity_Play enters ContextEnter with D=$0A85 and ContextEnter
; swaps Input_* and Player_Jump* only: it never copies actor rows or changes
; D. ApplyDamage, TryGrab__do, VsPlayer__hp_ok and their callers retain the
; attacker's physical D. Thus D-PlayerEntity_DpBase is the physical attacker,
; even while Player_Jump* aliases P2. A slot-1 NPC is NOT P2 unless enabled.
; No inferred player ownership from model, selected animation, or roster ID.
;
; ApplyDamage entry / VsPlayer__hp_ok: X = victim BYTE OFFSET, D=attacker.
; In particular TryGrabVsPlayer's old comment saying X=attacker is stale:
; main.pasm explicitly loads G13_AiTargetOffset into X before that call.
; Same-size replacement for main's STA.l PlayerEntity_Hp,x. A8/I16;
; STA leaves flags untouched and VictimX restores them, including carry.
HudOpponentHost_StorePlayerHp:
.a8
.i16
    sta.l PlayerEntity_Hp,x
    jml HudOpponentHost_VictimX

HudOpponentHost_VictimX:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    bra HudOpponentHost_VictimX__body

; TryGrab__do has clobbered X in its eligibility probes. Saved target is
; authoritative for both player->NPC and NPC->player successful grabs.
HudOpponentHost_Grab:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    lda.l HitApply_EntityBase
    tax
HudOpponentHost_VictimX__body:
.a16
.i16
    txy
    tdc
    sec
    sbc #PlayerEntity_DpBase
    tax
    jsr HudOpponentHost_Exchange
    ply
    plx
    pla
    plp
    rtl

; Private A16/I16: X/Y physical offsets, update every player participant.
; Both directions matter when an NPC grabs/throws/hits P1 or P2.
HudOpponentHost_Exchange:
    txa
    jsr HudOpponent_ValidSlot
    bcc HudOpponentHost_Exchange__done
    tya
    jsr HudOpponent_ValidSlot
    bcc HudOpponentHost_Exchange__done
    pha
    txa
    cmp 1,s
    beq HudOpponentHost_Exchange__self
    pla
    jsl HudOpponent_Target
    phx
    tyx
    ply
    jsl HudOpponent_Target
HudOpponentHost_Exchange__done:
    rts
HudOpponentHost_Exchange__self:
    pla
    rts

; Retirement / reuse adapters. X version matches Spawn_ResetKnockdownFall
; entry; Self version matches terminal fall and emitter/pit retirement.
HudOpponentHost_RetireSelf:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    tdc
    sec
    sbc #PlayerEntity_DpBase
    tax
    bra HudOpponentHost_RetireX__body
HudOpponentHost_RetireX:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
HudOpponentHost_RetireX__body:
.a16
.i16
    lda.l Game_CampaignId
    and #$FF
    cmp #3
    bne HudOpponentHost_RetireX__done
    jsl HudOpponent_Remove
    ; Source drawstatus suppresses an absent player's own opponent row too.
    cpx #0
    beq HudOpponentHost_RetireX__p1
    cpx #CHAR_ZP_LEN
    bne HudOpponentHost_RetireX__done
    lda.l G13_TwoPlayerEnabled
    and #$FF
    beq HudOpponentHost_RetireX__done
    lda #0
    sta.l HudOpponent_Targets+2
    bra HudOpponentHost_RetireX__done
HudOpponentHost_RetireX__p1:
.a16
.i16
    lda #0
    sta.l HudOpponent_Targets
HudOpponentHost_RetireX__done:
    ply
    plx
    pla
    plp
    rtl

; Legacy __vsN_dy_ok has neither victim X nor actor D: overlap is called
; from the game service with G13_PickupForP2 carrying the collector. These
; wrappers are placed BEFORE TriggerGet/Audio/ApplyPickup clobber context.
HudOpponentHost_Collect1:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    ldy #CHAR_ZP_LEN
    bra HudOpponentHost_Collect__body
HudOpponentHost_Collect2:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    ldy #CHAR_ZP_LEN*2
    bra HudOpponentHost_Collect__body
HudOpponentHost_Collect3:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    ldy #CHAR_ZP_LEN*3
    bra HudOpponentHost_Collect__body
HudOpponentHost_Collect4:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    ldy #CHAR_ZP_LEN*4
    bra HudOpponentHost_Collect__body
HudOpponentHost_Collect5:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    ldy #CHAR_ZP_LEN*5
HudOpponentHost_Collect__body:
.a16
.i16
    ldx #0
    lda.l G13_PickupForP2
    and #$FF
    beq HudOpponentHost_Collect__target
    ldx #CHAR_ZP_LEN
HudOpponentHost_Collect__target:
    jsl HudOpponent_Target
    ply
    plx
    pla
    plp
    rtl

; StageTimerHost_Collect uses ORDINALS X=item(0..5), Y=collector(0..1).
; This adapter only sets the HUD opponent; timer host still owns get/hide.
HudOpponentHost_CollectSlots:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    cpx #6
    bcs HudOpponentHost_CollectSlots__done
    cpy #2
    bcs HudOpponentHost_CollectSlots__done
    txa
    asl a
    tax
    lda.l HudOpponentHost_SlotOffsets,x
    pha
    tya
    asl a
    tax
    lda.l HudOpponentHost_SlotOffsets,x
    tax
    pla
    tay
    jsl HudOpponent_Target
HudOpponentHost_CollectSlots__done:
    ply
    plx
    pla
    plp
    rtl

; StageTimerHost_Retire uses X=item ORDINAL, unlike the native byte offset.
HudOpponentHost_RetireSlot:
    php
    rep #$30
.a16
.i16
    pha
    phx
    cpx #6
    bcs HudOpponentHost_RetireSlot__done
    txa
    asl a
    tax
    lda.l HudOpponentHost_SlotOffsets,x
    tax
    jsl HudOpponentHost_RetireX
HudOpponentHost_RetireSlot__done:
    plx
    pla
    plp
    rtl

; Native instant-hide cases (dead props, OUT players) have no kill callback.
; Run once before the HUD reads the actor rows, after all combat/collection.
; HP=0 alone is deliberately NOT enough to retire a falling enemy/player.
; Slot reuse is handled at Spawn_ResetKnockdownFall, even for identical names.
HudOpponentHost_PurgeRetired:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    lda.l Game_CampaignId
    and #$FF
    cmp #3
    bne HudOpponentHost_PurgeRetired__done
    ldy #0
HudOpponentHost_PurgeRetired__loop:
.a16
.i16
    tyx
    lda.l HudOpponentHost_SlotOffsets,x
    tax
    lda.l $7E0A00+CHAR_HP,x
    and #$FF
    bne HudOpponentHost_PurgeRetired__next
    lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
    and #$FF
    beq HudOpponentHost_PurgeRetired__retire
    cmp #CHAR_INPUT_DRIVEN_PROP
    beq HudOpponentHost_PurgeRetired__retire
    cmp #CHAR_INPUT_DRIVEN_STEAMER
    beq HudOpponentHost_PurgeRetired__retire
    cmp #CHAR_INPUT_DRIVEN_STEAM
    beq HudOpponentHost_PurgeRetired__retire
    cmp #CHAR_INPUT_DRIVEN_NONCOMBAT
    bne HudOpponentHost_PurgeRetired__native
    lda.l ActorBehavior_Alive,x
    beq HudOpponentHost_PurgeRetired__retire
    bra HudOpponentHost_PurgeRetired__next
HudOpponentHost_PurgeRetired__native:
.a16
.i16
    lda.l $7E0A00+CHAR_FALL_STATE_TIMER,x
    and #$FF
    cmp #$FF
    beq HudOpponentHost_PurgeRetired__retire
    cpx #0
    bne HudOpponentHost_PurgeRetired__p2
    lda.l G13_P1Out
    and #$FF
    bne HudOpponentHost_PurgeRetired__retire
    bra HudOpponentHost_PurgeRetired__next
HudOpponentHost_PurgeRetired__p2:
.a16
.i16
    cpx #CHAR_ZP_LEN
    bne HudOpponentHost_PurgeRetired__next
    lda.l G13_TwoPlayerEnabled
    and #$FF
    beq HudOpponentHost_PurgeRetired__next
    lda.l G13_P2Out
    and #$FF
    beq HudOpponentHost_PurgeRetired__next
HudOpponentHost_PurgeRetired__retire:
    jsl HudOpponentHost_RetireX
HudOpponentHost_PurgeRetired__next:
.a16
.i16
    iny
    iny
    cpy #12
    bcc HudOpponentHost_PurgeRetired__loop
HudOpponentHost_PurgeRetired__done:
    ply
    plx
    pla
    plp
    rtl
HudOpponentHost_SlotOffsets:
    .dw 0,CHAR_ZP_LEN,CHAR_ZP_LEN*2,CHAR_ZP_LEN*3,CHAR_ZP_LEN*4,CHAR_ZP_LEN*5
HudOpponentHost_End:
