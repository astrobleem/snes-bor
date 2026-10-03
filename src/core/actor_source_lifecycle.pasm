; Opt-in discrete source world consumers. Not production dispatch.
; D=world for count, D=actor for kill/display. DBR0,A16/I16,decimal clear.
; World44/46 player entities;4E/50 player opponent references.
; World48/4A/4C count scratch. Actor70=source oldhealth.
; Slot table and contexts must satisfy link_world_contexts admission.
; Unlinked kill is complete for these declared references. Linked kill fails
; closed until source ent_unlink ownership is represented (C4 is only a flag).
S6_CountEntities:
    rep #$30
    .a16
    .i16
    sta $48
    stz $4A
    stz $4C
    stz $3A
    lda $34
    cmp #151
    bcs S6_CountEntities__bad
S6_CountEntities__loop:
    .a16
    .i16
    lda $4A
    cmp $34
    bcs S6_CountEntities__done
    asl a
    tay
    lda [$30],y
    beq S6_CountEntities__next
    jsl S6_TargetPointer
    bcs S6_CountEntities__bad
    tax
    lda.l $7E00E0,x
    cmp #1
    bne S6_CountEntities__bad
    lda.l $7E00F6,x
    beq S6_CountEntities__next
    lda.l $7E00F2,x
    and $48
    beq S6_CountEntities__next
    inc $4C
S6_CountEntities__next:
    .a16
    .i16
    inc $4A
    bra S6_CountEntities__loop
S6_CountEntities__bad:
    .a16
    .i16
    lda #9
    sta $3A
    stz $4C
S6_CountEntities__done:
    .a16
    .i16
    lda $4C
    rtl

S6_KillUnlinked:
    rep #$30
    .a16
    .i16
    jsl S6_CheckPolicy
    bcs S6_KillUnlinked__done
    lda $C4
    bne S6_KillUnlinked__linked
    lda $36
    jsl S6_TargetPointer
    bcs S6_KillUnlinked__bad
    tax
    stz $F0
    stz $F6
    tdc
    cmp.l $7E0044,x
    bne S6_KillUnlinked__player1
    lda #0
    sta.l $7E0044,x
    tdc
S6_KillUnlinked__player1:
    .a16
    .i16
    cmp.l $7E0046,x
    bne S6_KillUnlinked__opponent0
    lda #0
    sta.l $7E0046,x
    tdc
S6_KillUnlinked__opponent0:
    .a16
    .i16
    cmp.l $7E004E,x
    bne S6_KillUnlinked__opponent1
    lda #0
    sta.l $7E004E,x
    tdc
S6_KillUnlinked__opponent1:
    .a16
    .i16
    cmp.l $7E0050,x
    bne S6_KillUnlinked__done
    lda #0
    sta.l $7E0050,x
S6_KillUnlinked__done:
    .a16
    .i16
    rtl
S6_KillUnlinked__linked:
    .a16
    .i16
    lda #4
    sta $FC
    rtl
S6_KillUnlinked__bad:
    .a16
    .i16
    lda #9
    sta $FC
    rtl

S6_DisplayHealth:
    rep #$30
    .a16
    .i16
    jsl S6_CheckPolicy
    bcs S6_DisplayHealth__done
    lda $70
    cmp $F0
    beq S6_DisplayHealth__done
    sec
    sbc $F0
    bvc S6_DisplayHealth__sign
    eor #$8000
S6_DisplayHealth__sign:
    .a16
    .i16
    bmi S6_DisplayHealth__increase
    dec $70
    rtl
S6_DisplayHealth__increase:
    .a16
    .i16
    inc $70
S6_DisplayHealth__done:
    .a16
    .i16
    rtl
