; Keep the existing P1 deferral decision. P2 may reuse its completed
; ground picture while its first punch/jump media is produced by the same
; original foreground scheduler. No resource, queue, Ready or packet writes.
SourceUrgent_ShouldDefer:
.a16
.i16
    php
    rep #$30
    cld
    pha
    phx
    phy
    lda.l SourceVisual_ServiceOnly
    beq SourceUrgent_Compositor
    brl SourceUrgent_No
SourceUrgent_Compositor:
.a16
.i16
    tdc
    cmp #$0A00
    bne SourceUrgent_P2
    lda.l SourceVisual_CompletedValid
    bne SourceUrgent_P1Valid
    brl SourceUrgent_No
SourceUrgent_P1Valid:
.a16
.i16
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+6,x
    cmp #2
    beq SourceUrgent_NoP1
    brl SourceUrgent_Yes
SourceUrgent_NoP1:
.a16
.i16
    brl SourceUrgent_No
SourceUrgent_P2:
.a16
.i16
    cmp #$0A85
    beq SourceUrgent_P2Scope
    brl SourceUrgent_No
SourceUrgent_P2Scope:
.a16
.i16
    jsr SourceNpc_Scope
    bcs SourceUrgent_ScopeOK
    brl SourceUrgent_No
SourceUrgent_ScopeOK:
.a16
.i16
    lda.l Game_StageIndex
    cmp #0
    beq SourceUrgent_G5
    brl SourceUrgent_No
SourceUrgent_G5:
.a16
.i16
    lda.l SourceVisual_Record
    cmp #32
    beq SourceUrgent_G6
    brl SourceUrgent_No
SourceUrgent_G6:
.a16
.i16
    lda.l SourceVisual_State+38
    cmp #1
    beq SourceUrgent_G7
    brl SourceUrgent_No
SourceUrgent_G7:
.a16
.i16
    lda.l SourceVisual_State+61
    and #255
    cmp #22
    beq SourceUrgent_G8
    brl SourceUrgent_No
SourceUrgent_G8:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SourceUrgent_G9
    brl SourceUrgent_No
SourceUrgent_G9:
.a16
.i16
    lda.l SVActor_Data+SVActor_Stage
    cmp #0
    beq SourceUrgent_G10
    brl SourceUrgent_No
SourceUrgent_G10:
.a16
.i16
    lda.l SVActor_Data+SVActor_Roster
    cmp #22
    beq SourceUrgent_G11
    brl SourceUrgent_No
SourceUrgent_G11:
.a16
.i16
    lda.l $7E0A85+CHAR_INPUT_DRIVEN
    and #255
    cmp #1
    beq SourceUrgent_G12
    brl SourceUrgent_No
SourceUrgent_G12:
.a16
.i16
    lda.l $7E0A85+CHAR_ROSTER_INDEX
    and #255
    cmp #22
    beq SourceUrgent_G13
    brl SourceUrgent_No
SourceUrgent_G13:
.a16
.i16
    lda.l $7E0A85+CHAR_MAP_INDEX
    and #255
    cmp #0
    beq SourceUrgent_G14
    brl SourceUrgent_No
SourceUrgent_G14:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy+133
    and #255
    cmp #2
    beq SourceUrgent_G15
    brl SourceUrgent_No
SourceUrgent_G15:
.a16
.i16
    lda.l StageBounds_State+133
    cmp #0
    beq SourceUrgent_G16
    brl SourceUrgent_No
SourceUrgent_G16:
.a16
.i16
    lda.l $7E0A85+CHAR_HP
    and #$00FF
    bne SourceUrgent_Alive
    brl SourceUrgent_No
SourceUrgent_Alive:
.a16
.i16
    ; Limit this experiment to the first urgent pose after a ground picture.
    lda.l SVActor_Data+1
    and #$00FF
    cmp #2
    bcc SourceUrgent_GroundCompleted
    brl SourceUrgent_No
SourceUrgent_GroundCompleted:
.a16
.i16
    lda.l SourceVisual_State+62
    and #$00FF
    cmp #2
    beq SourceUrgent_Role
    cmp #7
    beq SourceUrgent_Role
    brl SourceUrgent_No
SourceUrgent_Role:
.a16
.i16
    cmp.l SourceVisual_Sa1RuntimeRole+133
    beq SourceUrgent_RoleMatches
    brl SourceUrgent_No
SourceUrgent_RoleMatches:
.a16
.i16
    ; Do not borrow the renderer's admission while an unseen NPC owns
    ; the shared producer. The original first-picture route stays intact.
    lda.l SVActor_LoadOwner
    cmp #3
    bcc SourceUrgent_Yes
    cmp #7
    bcs SourceUrgent_Yes
    dec a
    dec a
    asl a
    tax
    lda.l SVActor_Bases,x
    tax
    lda.l SVActor_Data+SVActor_Valid,x
    cmp #1
    beq SourceUrgent_Yes
    brl SourceUrgent_No
SourceUrgent_Yes:
.a16
.i16
    ply
    plx
    pla
    plp
    sec
    rtl
SourceUrgent_No:
.a16
.i16
    ply
    plx
    pla
    plp
    clc
    rtl
SourceUrgent_End:
