; At most one consecutive idle/walk NPC completed-picture reuse per actor.
; Existing emitter validates model/stage/generation/resources and emits current
; instance position. Attack, damage/stun, dead and first pictures never defer.
; Private six-byte scratch fits audited4355D0..4355D5 gap before signedX435600.
SourceNpcFast_SkipMask = $4355D0
SourceNpcFast_Role = $4355D2
SourceNpcFast_Bit = $4355D4
SourceNpcFast_Hook:
.a16
.i16
    ; Keep opening movement/release and current attacks on the original
    ; path. Only amortize NPCs during the measured post-attack idle phase.
    ; WRAM hints precede Try's original ownership scope for all BW-RAM.
    tdc
    cmp #$0B0A
    bcc SourceNpcFast_Resume
    cmp #$0C9A
    bcs SourceNpcFast_Resume
    lda.l $7E0A00+CHAR_SELECTED
    and #$00FF
    cmp #3
    bcs SourceNpcFast_Resume
    cmp #2
    beq SourceNpcFast_CheckPeerGrounded
    lda.l $7E0A85+CHAR_SELECTED
    and #$00FF
    cmp #2
    bne SourceNpcFast_Resume
    bra SourceNpcFast_CheckLiveIdle
SourceNpcFast_CheckPeerGrounded:
.a16
.i16
    lda.l $7E0A85+CHAR_SELECTED
    and #$00FF
    cmp #3
    bcs SourceNpcFast_Resume
SourceNpcFast_CheckLiveIdle:
.a16
.i16
    lda.l SourceVisual_Sa1RuntimeRole
    and #$00FF
    bne SourceNpcFast_Resume
    lda.l SourceVisual_Sa1RuntimeRole+133
    and #$00FF
    bne SourceNpcFast_Resume
    jsl SourceNpcFast_Try
    bcc SourceNpcFast_Resume
    jml SourceVisual_RenderCurrent__retired
SourceNpcFast_Resume:
.a16
.i16
    sep #$20
.a8
    lda #0
    jml SourceVisual_RenderCurrent__lookup_resume
SourceNpcFast_Try:
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
    tdc
    cmp #$0B0A
    beq SourceNpcFast_PhysicalNpc
    cmp #$0B8F
    beq SourceNpcFast_PhysicalNpc
    cmp #$0C14
    beq SourceNpcFast_PhysicalNpc
    cmp #$0C99
    beq SourceNpcFast_PhysicalNpc
    brl SourceNpcFast_Miss
SourceNpcFast_PhysicalNpc:
.a16
.i16
    lda.l SourceVisual_ServiceOnly
    cmp #0
    beq SourceNpcFast_Guard0
    brl SourceNpcFast_Miss
SourceNpcFast_Guard0:
.a16
.i16
    lda.l $7E46DE
    cmp #0
    beq SourceNpcFast_Guard1
    brl SourceNpcFast_Miss
SourceNpcFast_Guard1:
.a16
.i16
    lda.l Game_CampaignId
    and #255
    cmp #3
    beq SourceNpcFast_Guard2
    brl SourceNpcFast_Miss
SourceNpcFast_Guard2:
.a16
.i16
    lda.l Game_State
    cmp #0
    beq SourceNpcFast_Guard3
    brl SourceNpcFast_Miss
SourceNpcFast_Guard3:
.a16
.i16
    lda.l $7E175E
    cmp #2
    beq SourceNpcFast_Guard4
    brl SourceNpcFast_Miss
SourceNpcFast_Guard4:
.a16
.i16
    lda.l $7E1760
    cmp #1
    beq SourceNpcFast_Guard5
    brl SourceNpcFast_Miss
SourceNpcFast_Guard5:
.a16
.i16
    lda.l $7E46DC
    cmp #1
    beq SourceNpcFast_Guard6
    brl SourceNpcFast_Miss
SourceNpcFast_Guard6:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #6752
    beq SourceNpcFast_Guard7
    brl SourceNpcFast_Miss
SourceNpcFast_Guard7:
.a16
.i16
    lda.l SourceVisual_CompletedMagic
    cmp #49229
    beq SourceNpcFast_Guard8
    brl SourceNpcFast_Miss
SourceNpcFast_Guard8:
.a16
.i16
    lda.l SVActor_Magic
    cmp #44057
    beq SourceNpcFast_Guard9
    brl SourceNpcFast_Miss
SourceNpcFast_Guard9:
.a16
.i16
    lda CHAR_INPUT_DRIVEN
    and #255
    cmp #2
    beq SourceNpcFast_Guard10
    brl SourceNpcFast_Miss
SourceNpcFast_Guard10:
.a16
.i16
    lda CHAR_HIT_STUN
    and #255
    cmp #0
    beq SourceNpcFast_Guard11
    brl SourceNpcFast_Miss
SourceNpcFast_Guard11:
.a16
.i16
    lda CHAR_HP
    and #$00FF
    bne SourceNpcFast_Guard12
    brl SourceNpcFast_Miss
SourceNpcFast_Guard12:
.a16
.i16
    lda CHAR_SELECTED
    and #$00FF
    cmp #3
    bcc SourceNpcFast_Guard13
    brl SourceNpcFast_Miss
SourceNpcFast_Guard13:
.a16
.i16
    tdc
    sec
    sbc #$0A00
    tax
    lda.l SourceVisual_Sa1OwnerPolicy,x
    and #$00FF
    cmp #2
    beq SourceNpcFast_Guard14
    brl SourceNpcFast_Miss
SourceNpcFast_Guard14:
.a16
.i16
    lda.l SourceVisual_Sa1RuntimeRole,x
    and #$00FF
    cmp #2
    bcc SourceNpcFast_Guard15
    brl SourceNpcFast_Miss
SourceNpcFast_Guard15:
.a16
.i16
    sta.l SourceNpcFast_Role
    ; Current's short-call ABI takes SourceVisual_ActorSlot, normally set
    ; by SelectResidency. Resolve it from the already authenticated real DP.
    tdc
    sec
    sbc #$0A00
    ldx #0
SourceNpcFast_SlotLoop:
.a16
.i16
    cmp #0
    beq SourceNpcFast_SlotReady
    sec
    sbc #133
    inx
    bra SourceNpcFast_SlotLoop
SourceNpcFast_SlotReady:
.a16
.i16
    txa
    sta.l SourceVisual_ActorSlot
    jsl SourceNpcFast_Current
    bcs SourceNpcFast_Guard16
    brl SourceNpcFast_Miss
SourceNpcFast_Guard16:
.a16
.i16
    lda.l SVActor_Base
    tax
    lda.l SVActor_Data+1,x
    and #$00FF
    cmp.l SourceNpcFast_Role
    beq SourceNpcFast_Guard17
    brl SourceNpcFast_Miss
SourceNpcFast_Guard17:
.a16
.i16
    lda.l SVActor_Slot
    sec
    sbc #2
    tax
    lda #1
SourceNpcFast_Shift:
.a16
.i16
    cpx #0
    beq SourceNpcFast_Mask
    asl a
    dex
    bra SourceNpcFast_Shift
SourceNpcFast_Mask:
.a16
.i16
    sta.l SourceNpcFast_Bit
    lda.l SourceNpcFast_SkipMask
    and #15
    eor.l SourceNpcFast_Bit
    sta.l SourceNpcFast_SkipMask
    and.l SourceNpcFast_Bit
    bne SourceNpcFast_Reuse
    brl SourceNpcFast_Miss
SourceNpcFast_Reuse:
.a16
.i16
    sep #$20
.a8
    lda #$27
    sta.l SourceVisual_Error
    rep #$30
.a16
.i16
    jsl SourceNpcFast_Emit
    bcs SourceNpcFast_Hit
SourceNpcFast_Miss:
.a16
.i16
    rep #$30
    pld
    plb
    ply
    plx
    pla
    plp
    clc
    rtl
SourceNpcFast_Hit:
.a16
.i16
    rep #$30
    pld
    plb
    ply
    plx
    pla
    plp
    sec
    rtl
SourceNpcFast_Current:
.a16
.i16
    .db $F4
    .dw ((SourcePalette_Bridge_SVActor_Enabled+2)&$FFFF)
    jml SVActor_Current
SourceNpcFast_Emit:
.a16
.i16
    .db $F4
    .dw ((SourcePalette_Bridge_SVActor_Enabled+2)&$FFFF)
    jml SVActor_Emit
SourceNpcFast_End:
