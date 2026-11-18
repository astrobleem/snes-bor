; Spend a permitted ordinary idle-refresh visit on canonical attack0 media.
; Only two already valid idle0 pictures may be reused; movement, first idle,
; attacks, jumps, NPC-first priority, inputs and incoherent snapshots retain
; the original path. Existing once-per-field producer and physical fences apply.
; Cursor0..9 bounds cosmetic deferrals to the ten first-pose candidates.
SourceIdleAttack_PreferFirst:
.a16
.i16
    php
    rep #$30
    cld
    pha
    lda.l SourceVisual_ServiceOnly
    cmp #0
    beq SourceIdleAttack_G1
    brl SourceIdleAttack_Restore
SourceIdleAttack_G1:
.a16
.i16
    lda.l SourceVisual_Key
    cmp #22
    beq SourceIdleAttack_G2
    brl SourceIdleAttack_Restore
SourceIdleAttack_G2:
.a16
.i16
    lda.l SourceVisual_Key+2
    cmp #1
    bcs SourceIdleAttack_G3
    brl SourceIdleAttack_Restore
SourceIdleAttack_G3:
.a16
.i16
    cmp #18
    bcc SourceIdleAttack_G4
    brl SourceIdleAttack_Restore
SourceIdleAttack_G4:
.a16
.i16
    tdc
    cmp #$0A00
    beq SourceIdleAttack_Player
    cmp #$0A85
    beq SourceIdleAttack_Player
    brl SourceIdleAttack_Restore
SourceIdleAttack_Player:
.a16
.i16
    lda.l SourcePrefetch_Cursor
    cmp #10
    bcc SourceIdleAttack_G5
    brl SourceIdleAttack_Restore
SourceIdleAttack_G5:
.a16
.i16
    lda.l SourceVisual_State
    cmp #923
    beq SourceIdleAttack_G6
    brl SourceIdleAttack_Restore
SourceIdleAttack_G6:
.a16
.i16
    lda.l SourceVisual_State+32
    cmp #923
    beq SourceIdleAttack_G7
    brl SourceIdleAttack_Restore
SourceIdleAttack_G7:
.a16
.i16
    lda.l SourceVisual_CompletedEntry
    cmp #22
    beq SourceIdleAttack_G8
    brl SourceIdleAttack_Restore
SourceIdleAttack_G8:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+2
    cmp #0
    beq SourceIdleAttack_G9
    brl SourceIdleAttack_Restore
SourceIdleAttack_G9:
.a16
.i16
    lda.l SourceVisual_CompletedStage
    cmp #0
    beq SourceIdleAttack_G10
    brl SourceIdleAttack_Restore
SourceIdleAttack_G10:
.a16
.i16
    lda.l SVActor_Data
    cmp #22
    beq SourceIdleAttack_G11
    brl SourceIdleAttack_Restore
SourceIdleAttack_G11:
.a16
.i16
    lda.l SVActor_Data+2
    cmp #0
    beq SourceIdleAttack_G12
    brl SourceIdleAttack_Restore
SourceIdleAttack_G12:
.a16
.i16
    lda.l SVActor_Data+SVActor_Stage
    cmp #0
    beq SourceIdleAttack_G13
    brl SourceIdleAttack_Restore
SourceIdleAttack_G13:
.a16
.i16
    lda.l SourcePrefetch_Cursor
    pha
    jsl SourcePrefetch_DuringWait
    lda.l SourcePrefetch_Cursor
    cmp 1,s
    beq SourceIdleAttack_DropCursor
    bcc SourceIdleAttack_DropCursor
    cmp #11
    bcs SourceIdleAttack_DropCursor
    lda #0
    sta.l SourceVisual_Key+2
SourceIdleAttack_Deferred:
.a16
.i16
SourceIdleAttack_DropCursor:
    pla
SourceIdleAttack_Restore:
.a16
.i16
    pla
    plp
    jml SourceIdle_PreferFirst
SourceIdleAttack_End:
