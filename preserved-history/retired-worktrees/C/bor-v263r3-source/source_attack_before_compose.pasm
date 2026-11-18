; Borrow precisely the existing after-submit preparation visit for a
; coherent FIRST player attack, after retirement observation, before emission.
; All normal physical loader/palette/DMA/publication fences remain authoritative.
; Peer metadata uses46EE..F3. This scheduler owns only46F4..F7.
SourceAttack_Borrowed = $7E46F4
SourceAttack_Chosen = $7E46F6
SourceAttack_BeforeObserve:
.a16
.i16
    jsl SVActor_Observe
    php
    rep #$30
    pha
    lda #0
    sta.l SourceAttack_Borrowed
    pla
    plp
    rtl

; Actor update/import has completed at this seam. A nested loader visit
; returns here with ServiceOnly restored before the ordinary compositor.
SourceAttack_PrepareInRenderer:
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
    lda.l SourceVisual_ServiceOnly
    beq SourceAttack_RenderCompositor
    brl SourceAttack_RenderDone
SourceAttack_RenderCompositor:
.a16
.i16
    lda.l SourceAttack_Borrowed
    cmp #1
    bne SourceAttack_RenderAvailable
    brl SourceAttack_RenderDone
SourceAttack_RenderAvailable:
.a16
.i16
    tdc
    cmp #$0A00
    beq SourceAttack_RenderPlayer
    cmp #$0A85
    beq SourceAttack_RenderPlayer
    brl SourceAttack_RenderDone
SourceAttack_RenderPlayer:
.a16
.i16
    lda.l $7E46DE
    beq SourceAttack_Foreground
    brl SourceAttack_RenderDone
SourceAttack_Foreground:
.a16
.i16
    ; WRAM-only cheap rejection keeps ordinary ground/jump passes unchanged.
    lda.l SourceInput_Selected1
    ora.l SourceInput_Selected2
    ora.l SourceInput_ReplayHeld1
    ora.l SourceInput_ReplayHeld2
    and #$4000
    bne SourceAttack_InputCandidate
    lda.l $7E0A00+CHAR_SELECTED
    and #$00FF
    cmp #2
    beq SourceAttack_InputCandidate
    lda.l $7E0A85+CHAR_SELECTED
    and #$00FF
    cmp #2
    beq SourceAttack_InputCandidate
    brl SourceAttack_RenderDone
SourceAttack_InputCandidate:
.a16
.i16
    jsl SourceAttack_ScopeBridge
    bcs SourceAttack_Scope
    brl SourceAttack_RenderDone
SourceAttack_Scope:
.a16
.i16
    lda.l Game_StageIndex
    beq SourceAttack_Stage
    brl SourceAttack_RenderDone
SourceAttack_Stage:
.a16
.i16
    ; Observe the original both-OAM-rows drain before any lease is touched.
    jsl SourceVisual_CompletedObserve
    lda.l $7E0A00+0+CHAR_HP
    and #$00FF
    beq SourceAttack_NoJump0
    lda.l $7E0A00+0+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    bne SourceAttack_NoJump0
    lda.l $7E0A00+0+CHAR_SELECTED
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
    bne SourceAttack_NoJump0
    brl SourceAttack_RenderDone
SourceAttack_NoJump0:
.a16
.i16
    lda.l $7E0A00+133+CHAR_HP
    and #$00FF
    beq SourceAttack_NoJump1
    lda.l $7E0A00+133+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    bne SourceAttack_NoJump1
    lda.l $7E0A00+133+CHAR_SELECTED
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
    bne SourceAttack_NoJump1
    brl SourceAttack_RenderDone
SourceAttack_NoJump1:
.a16
.i16
    ; A live NPC's first picture keeps its original preparation priority.
    lda.l $7E0A00+266+CHAR_HP
    and #$00FF
    beq SourceAttack_Npc2OK
    lda.l $7E0A00+266+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #2
    bne SourceAttack_Npc2OK
    lda.l SVActor_Data+1280+SVActor_Valid
    cmp #1
    beq SourceAttack_Npc2OKValid
    brl SourceAttack_RenderDone
SourceAttack_Npc2OKValid:
.a16
.i16
    lda.l SVActor_Data+1280+SVActor_Stage
    beq SourceAttack_Npc2OKStage
    brl SourceAttack_RenderDone
SourceAttack_Npc2OKStage:
.a16
.i16
    lda.l $7E0A00+266+CHAR_ROSTER_INDEX
    and #$00FF
    cmp.l SVActor_Data+1280+SVActor_Roster
    beq SourceAttack_Npc2OK
    brl SourceAttack_RenderDone
SourceAttack_Npc2OK:
.a16
.i16
    ; A live NPC's first picture keeps its original preparation priority.
    lda.l $7E0A00+399+CHAR_HP
    and #$00FF
    beq SourceAttack_Npc3OK
    lda.l $7E0A00+399+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #2
    bne SourceAttack_Npc3OK
    lda.l SVActor_Data+2560+SVActor_Valid
    cmp #1
    beq SourceAttack_Npc3OKValid
    brl SourceAttack_RenderDone
SourceAttack_Npc3OKValid:
.a16
.i16
    lda.l SVActor_Data+2560+SVActor_Stage
    beq SourceAttack_Npc3OKStage
    brl SourceAttack_RenderDone
SourceAttack_Npc3OKStage:
.a16
.i16
    lda.l $7E0A00+399+CHAR_ROSTER_INDEX
    and #$00FF
    cmp.l SVActor_Data+2560+SVActor_Roster
    beq SourceAttack_Npc3OK
    brl SourceAttack_RenderDone
SourceAttack_Npc3OK:
.a16
.i16
    ; A live NPC's first picture keeps its original preparation priority.
    lda.l $7E0A00+532+CHAR_HP
    and #$00FF
    beq SourceAttack_Npc4OK
    lda.l $7E0A00+532+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #2
    bne SourceAttack_Npc4OK
    lda.l SVActor_Data+3840+SVActor_Valid
    cmp #1
    beq SourceAttack_Npc4OKValid
    brl SourceAttack_RenderDone
SourceAttack_Npc4OKValid:
.a16
.i16
    lda.l SVActor_Data+3840+SVActor_Stage
    beq SourceAttack_Npc4OKStage
    brl SourceAttack_RenderDone
SourceAttack_Npc4OKStage:
.a16
.i16
    lda.l $7E0A00+532+CHAR_ROSTER_INDEX
    and #$00FF
    cmp.l SVActor_Data+3840+SVActor_Roster
    beq SourceAttack_Npc4OK
    brl SourceAttack_RenderDone
SourceAttack_Npc4OK:
.a16
.i16
    ; A live NPC's first picture keeps its original preparation priority.
    lda.l $7E0A00+665+CHAR_HP
    and #$00FF
    beq SourceAttack_Npc5OK
    lda.l $7E0A00+665+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #2
    bne SourceAttack_Npc5OK
    lda.l SVActor_Data+5120+SVActor_Valid
    cmp #1
    beq SourceAttack_Npc5OKValid
    brl SourceAttack_RenderDone
SourceAttack_Npc5OKValid:
.a16
.i16
    lda.l SVActor_Data+5120+SVActor_Stage
    beq SourceAttack_Npc5OKStage
    brl SourceAttack_RenderDone
SourceAttack_Npc5OKStage:
.a16
.i16
    lda.l $7E0A00+665+CHAR_ROSTER_INDEX
    and #$00FF
    cmp.l SVActor_Data+5120+SVActor_Roster
    beq SourceAttack_Npc5OK
    brl SourceAttack_RenderDone
SourceAttack_Npc5OK:
.a16
.i16
    jsr SourceAttack_PeerMotionSafe
    bcs SourceAttack_PeersSafe
    brl SourceAttack_RenderDone
SourceAttack_PeersSafe:
.a16
.i16
    lda #1
    jsl SourceWarm_ReadAttack
    bcs SourceAttack_FreshP2
    lda #1
    jsr SourceAttack_Pending
    bcs SourceAttack_FreshP2
    lda #0
    jsl SourceWarm_ReadAttack
    bcs SourceAttack_FreshP1
    lda #0
    jsr SourceAttack_Pending
    bcs SourceAttack_FreshP1
    brl SourceAttack_RenderDone
SourceAttack_FreshP2:
.a16
.i16
    lda #1
    bra SourceAttack_BorrowJob
SourceAttack_FreshP1:
.a16
.i16
    lda #0
SourceAttack_BorrowJob:
.a16
.i16
    sta.l SourceAttack_Chosen
    lda #1
    sta.l SourceAttack_Borrowed
    ; Same selected-player job and cursor advancement as the old producer.
    ; Borrowing its reserved NPC turn wraps phase2 to0, never exposes phase3.
    lda.l SourceRom_MediaPhase
    inc a
    cmp #3
    bcc SourceAttack_Phase
    lda #0
SourceAttack_Phase:
.a16
.i16
    sta.l SourceRom_MediaPhase
    lda.l SourceAttack_Chosen
    sta.l SourceRom_MediaCandidate
    eor #1
    sta.l SourceRom_PlayerMediaCursor
    lda.l SourceAttack_Chosen
    asl a
    tax
    lda.l SVActor_LoadDps,x
    tcd
SourceAttack_BorrowService:
.a16
.i16
    jsl SourceVisual_ServiceCurrent
SourceAttack_BorrowComplete:
.a16
.i16
    lda #0
    sta.l SourceVisual_ServiceOnly
SourceAttack_RenderDone:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    rtl

; Pending first-frame work has already passed the normal native admission.
; This is a wakeup for that existing exact lease, never a different request.
; Coherent accepted peer jumps retain priority before either native mirror
; catches up. This gate reads no motion outside the established owned scope.
SourceAttack_PeerMotionSafe:
.a16
.i16
    php
    rep #$30
    pha
    phy
    lda.l $434E7E
    cmp #$4D50
    bne SourceAttack_PeerNo
    lda.l $434E7C
    tay
    and #1
    bne SourceAttack_PeerNo
    lda.l $434E50
    and #$00FF
    cmp #7
    beq SourceAttack_PeerNo
    lda.l $434E74
    and #$00FF
    cmp #7
    beq SourceAttack_PeerNo
    tya
    cmp.l $434E7C
    bne SourceAttack_PeerNo
    ply
    pla
    plp
    sec
    rts
SourceAttack_PeerNo:
.a16
.i16
    ply
    pla
    plp
    clc
    rts

SourceAttack_Pending:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    cmp #2
    bcc SourceAttack_PendingSlot
    brl SourceAttack_PendingNo
SourceAttack_PendingSlot:
.a16
.i16
    tay
    asl a
    tax
    lda.l SVActor_LoadDps,x
    sec
    sbc #$0A00
    tax
    lda.l $7E0A00+CHAR_HP,x
    and #255
    cmp #0
    bne SourceAttack_PendingG1
    brl SourceAttack_PendingNo
SourceAttack_PendingG1:
.a16
.i16
    lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
    and #255
    cmp #1
    beq SourceAttack_PendingG2
    brl SourceAttack_PendingNo
SourceAttack_PendingG2:
.a16
.i16
    lda.l $7E0A00+CHAR_ROSTER_INDEX,x
    and #255
    cmp #22
    beq SourceAttack_PendingG3
    brl SourceAttack_PendingNo
SourceAttack_PendingG3:
.a16
.i16
    lda.l $7E0A00+CHAR_MAP_INDEX,x
    and #255
    cmp #0
    beq SourceAttack_PendingG4
    brl SourceAttack_PendingNo
SourceAttack_PendingG4:
.a16
.i16
    lda.l $7E0A00+CHAR_SELECTED,x
    and #255
    cmp #3
    bcc SourceAttack_PendingG5
    brl SourceAttack_PendingNo
SourceAttack_PendingG5:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy,x
    and #255
    cmp #2
    beq SourceAttack_PendingG6
    brl SourceAttack_PendingNo
SourceAttack_PendingG6:
.a16
.i16
    lda.l SourceVisual_Sa1RuntimeRole,x
    cmp #2
    beq SourceAttack_PendingG7
    brl SourceAttack_PendingNo
SourceAttack_PendingG7:
.a16
.i16
    lda.l StageBounds_State,x
    cmp #0
    beq SourceAttack_PendingG8
    brl SourceAttack_PendingNo
SourceAttack_PendingG8:
.a16
.i16
    tya
    asl a
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_State+6,x
    cmp #1
    beq SourceAttack_PendingG9
    brl SourceAttack_PendingNo
SourceAttack_PendingG9:
.a16
.i16
    lda.l SourceVisual_State,x
    cmp #781
    beq SourceAttack_PendingG10
    brl SourceAttack_PendingNo
SourceAttack_PendingG10:
.a16
.i16
    lda.l SourceVisual_State+29,x
    and #255
    cmp #22
    beq SourceAttack_PendingG11
    brl SourceAttack_PendingNo
SourceAttack_PendingG11:
.a16
.i16
    lda.l SourceVisual_State+30,x
    and #255
    cmp #2
    beq SourceAttack_PendingG12
    brl SourceAttack_PendingNo
SourceAttack_PendingG12:
.a16
.i16
    tya
    beq SourceAttack_PendingP1
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SourceAttack_PendingG13
    brl SourceAttack_PendingNo
SourceAttack_PendingG13:
.a16
.i16
    lda.l SVActor_Data+SVActor_Stage
    cmp #0
    beq SourceAttack_PendingG14
    brl SourceAttack_PendingNo
SourceAttack_PendingG14:
.a16
.i16
    lda.l SVActor_Data+SVActor_Roster
    cmp #22
    beq SourceAttack_PendingG15
    brl SourceAttack_PendingNo
SourceAttack_PendingG15:
.a16
.i16
    lda.l SVActor_Data
    and #255
    cmp #22
    beq SourceAttack_PendingG16
    brl SourceAttack_PendingNo
SourceAttack_PendingG16:
.a16
.i16
    lda.l SVActor_Data+1
    and #255
    cmp #2
    bcc SourceAttack_PendingG17
    brl SourceAttack_PendingNo
SourceAttack_PendingG17:
.a16
.i16
    lda.l SVActor_Data+12
    and #255
    cmp #0
    bne SourceAttack_PendingG18
    brl SourceAttack_PendingNo
SourceAttack_PendingG18:
.a16
.i16
    lda.l SVActor_Data+12
    and #255
    cmp #66
    bcc SourceAttack_PendingG19
    brl SourceAttack_PendingNo
SourceAttack_PendingG19:
.a16
.i16
    brl SourceAttack_PendingYes
SourceAttack_PendingP1:
.a16
.i16
    lda.l SourceVisual_CompletedValid
    cmp #1
    beq SourceAttack_PendingG20
    brl SourceAttack_PendingNo
SourceAttack_PendingG20:
.a16
.i16
    lda.l SourceVisual_CompletedStage
    cmp #0
    beq SourceAttack_PendingG21
    brl SourceAttack_PendingNo
SourceAttack_PendingG21:
.a16
.i16
    lda.l SourceVisual_CompletedRoster
    cmp #22
    beq SourceAttack_PendingG22
    brl SourceAttack_PendingNo
SourceAttack_PendingG22:
.a16
.i16
    lda.l SourceVisual_CompletedEntry
    and #255
    cmp #22
    beq SourceAttack_PendingG23
    brl SourceAttack_PendingNo
SourceAttack_PendingG23:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+1
    and #255
    cmp #2
    bcc SourceAttack_PendingG24
    brl SourceAttack_PendingNo
SourceAttack_PendingG24:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+12
    and #255
    cmp #0
    bne SourceAttack_PendingG25
    brl SourceAttack_PendingNo
SourceAttack_PendingG25:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+12
    and #255
    cmp #66
    bcc SourceAttack_PendingG26
    brl SourceAttack_PendingNo
SourceAttack_PendingG26:
.a16
.i16
SourceAttack_PendingYes:
.a16
.i16
    ply
    plx
    pla
    plp
    sec
    rts
SourceAttack_PendingNo:
.a16
.i16
    ply
    plx
    pla
    plp
    clc
    rts
SourceAttack_AfterSubmit:
.a16
.i16
    php
    rep #$30
    pha
    lda.l SourceAttack_Borrowed
    cmp #1
    bne SourceAttack_AfterOrdinary
    lda #0
    sta.l SourceAttack_Borrowed
    pla
    plp
SourceAttack_AfterSkip:
.a16
.i16
    rtl
SourceAttack_AfterOrdinary:
.a16
.i16
    pla
    plp
    jml SourceVisual_ServiceNpcsAfterSubmit
; Keep the original physical critical-completion check first. A later,
; cold P2 attack frame may hold its completed attack0 only while a new P1
; attack0 already in the OAM build awaits its FIRST whole-packet submission.
SourceAttack_CriticalOrDeferRepeat:
.a16
.i16
    jsl SourceCritical_CompleteReady
    bcs SourceAttack_CriticalReturn
    jsr SourceAttack_DeferRepeatP2
    bcc SourceAttack_CriticalReturn
    ; Consume only this callout's own JSL frame, never the renderer's frame.
    tsc
    inc a
    inc a
    inc a
    tcs
    lda #0
    clc
    jml SourceVisual_RenderCurrent__defer_pending
SourceAttack_CriticalReturn:
.a16
.i16
    rtl
SourceAttack_DeferRepeatP2:
.a16
.i16
    php
    rep #$30
    cld
    pha
    phx
    phy
    tdc
    cmp #$0A85
    beq SourceAttack_RepeatP2
    brl SourceAttack_RepeatNo
SourceAttack_RepeatP2:
.a16
.i16
    lda.l SourceVisual_ServiceOnly
    cmp #0
    beq SourceAttack_RepeatG1
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG1:
.a16
.i16
    lda.l $7E46DE
    cmp #0
    beq SourceAttack_RepeatG2
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG2:
.a16
.i16
    lda.l SourceVisual_Record
    cmp #32
    beq SourceAttack_RepeatG3
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG3:
.a16
.i16
    lda.l SourceVisual_State+38
    cmp #1
    beq SourceAttack_RepeatG4
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG4:
.a16
.i16
    lda.l SourceVisual_State+61
    cmp #534
    beq SourceAttack_RepeatG5
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG5:
.a16
.i16
    lda.l SourceVisual_EntryScratch
    cmp #534
    beq SourceAttack_RepeatG6
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG6:
.a16
.i16
    lda.l SourceVisual_EntryScratch+2
    cmp #1
    bcs SourceAttack_RepeatG7
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG7:
.a16
.i16
    lda.l SourceVisual_EntryScratch+2
    cmp #6
    bcc SourceAttack_RepeatG8
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG8:
.a16
.i16
    lda.l SourceVisual_State+32
    cmp #783
    bcs SourceAttack_RepeatG9
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG9:
.a16
.i16
    lda.l SourceVisual_State+32
    cmp #792
    bcc SourceAttack_RepeatG10
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG10:
.a16
.i16
    lda.l SourceVisual_State+32
    and #1
    cmp #1
    beq SourceAttack_RepeatG11
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG11:
.a16
.i16
    jsl SourceAttack_ScopeBridge
    bcs SourceAttack_RepeatScope
    brl SourceAttack_RepeatNo
SourceAttack_RepeatScope:
.a16
.i16
    lda.l Game_StageIndex
    cmp #0
    beq SourceAttack_RepeatG12
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG12:
.a16
.i16
    lda.l $7E0A00+0+CHAR_HP
    and #255
    cmp #0
    bne SourceAttack_RepeatG13
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG13:
.a16
.i16
    lda.l $7E0A00+0+CHAR_INPUT_DRIVEN
    and #255
    cmp #1
    beq SourceAttack_RepeatG14
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG14:
.a16
.i16
    lda.l $7E0A00+0+CHAR_ROSTER_INDEX
    and #255
    cmp #22
    beq SourceAttack_RepeatG15
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG15:
.a16
.i16
    lda.l $7E0A00+0+CHAR_MAP_INDEX
    and #255
    cmp #0
    beq SourceAttack_RepeatG16
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG16:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy+0
    and #255
    cmp #2
    beq SourceAttack_RepeatG17
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG17:
.a16
.i16
    lda.l StageBounds_State+0
    cmp #0
    beq SourceAttack_RepeatG18
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG18:
.a16
.i16
    lda.l $7E0A00+133+CHAR_HP
    and #255
    cmp #0
    bne SourceAttack_RepeatG19
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG19:
.a16
.i16
    lda.l $7E0A00+133+CHAR_INPUT_DRIVEN
    and #255
    cmp #1
    beq SourceAttack_RepeatG20
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG20:
.a16
.i16
    lda.l $7E0A00+133+CHAR_ROSTER_INDEX
    and #255
    cmp #22
    beq SourceAttack_RepeatG21
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG21:
.a16
.i16
    lda.l $7E0A00+133+CHAR_MAP_INDEX
    and #255
    cmp #0
    beq SourceAttack_RepeatG22
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG22:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy+133
    and #255
    cmp #2
    beq SourceAttack_RepeatG23
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG23:
.a16
.i16
    lda.l StageBounds_State+133
    cmp #0
    beq SourceAttack_RepeatG24
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG24:
.a16
.i16
    jsr SourceAttack_PeerMotionSafe
    bcs SourceAttack_RepeatPeers
    brl SourceAttack_RepeatNo
SourceAttack_RepeatPeers:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SourceAttack_RepeatG25
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG25:
.a16
.i16
    lda.l SVActor_Data+SVActor_Stage
    cmp #0
    beq SourceAttack_RepeatG26
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG26:
.a16
.i16
    lda.l SVActor_Data+SVActor_Roster
    cmp #22
    beq SourceAttack_RepeatG27
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG27:
.a16
.i16
    lda.l SVActor_Data
    cmp #534
    beq SourceAttack_RepeatG28
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG28:
.a16
.i16
    lda.l SVActor_Data+2
    cmp #0
    beq SourceAttack_RepeatG29
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG29:
.a16
.i16
    lda.l SourceVisual_CompletedValid
    cmp #1
    beq SourceAttack_RepeatG30
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG30:
.a16
.i16
    lda.l SourceVisual_CompletedStage
    cmp #0
    beq SourceAttack_RepeatG31
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG31:
.a16
.i16
    lda.l SourceVisual_CompletedRoster
    cmp #22
    beq SourceAttack_RepeatG32
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG32:
.a16
.i16
    lda.l SourceVisual_CompletedEntry
    cmp #534
    beq SourceAttack_RepeatG33
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG33:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+2
    cmp #0
    beq SourceAttack_RepeatG34
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG34:
.a16
.i16
    lda.l SourceVisual_CompletedAwait
    cmp #1
    beq SourceAttack_RepeatG35
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG35:
.a16
.i16
    lda.l SourceVisual_CompletedPending
    cmp #0
    beq SourceAttack_RepeatG36
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG36:
.a16
.i16
    lda.l SourceVisual_State
    cmp #781
    beq SourceAttack_RepeatG37
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG37:
.a16
.i16
    lda.l SourceVisual_State+6
    cmp #2
    beq SourceAttack_RepeatG38
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG38:
.a16
.i16
    lda.l SourceVisual_State+28
    and #255
    cmp #1
    beq SourceAttack_RepeatG39
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG39:
.a16
.i16
    lda.l SourcePacket_ActiveValid
    cmp #1
    beq SourceAttack_RepeatG40
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG40:
.a16
.i16
    lda.l SourcePacket_CopyBusy
    cmp #0
    beq SourceAttack_RepeatG41
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG41:
.a16
.i16
    lda.l SOURCE_PACKET_BUILD_META+8
    cmp #22
    beq SourceAttack_RepeatG42
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG42:
.a16
.i16
    lda.l SOURCE_PACKET_BUILD_META+10
    cmp #0
    beq SourceAttack_RepeatG43
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG43:
.a16
.i16
    lda.l SOURCE_PACKET_BUILD_META+12
    cmp #534
    beq SourceAttack_RepeatG44
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG44:
.a16
.i16
    lda.l SOURCE_PACKET_BUILD_META+14
    cmp #0
    beq SourceAttack_RepeatG45
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG45:
.a16
.i16
    lda.l SOURCE_PACKET_BUILD_META+16
    cmp #1
    beq SourceAttack_RepeatG46
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG46:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+8
    cmp #22
    beq SourceAttack_RepeatG47
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG47:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+10
    cmp #0
    beq SourceAttack_RepeatG48
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG48:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+14
    cmp #0
    beq SourceAttack_RepeatG49
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG49:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+16
    cmp #1
    beq SourceAttack_RepeatG50
    brl SourceAttack_RepeatNo
SourceAttack_RepeatG50:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+12
    cmp #$0016
    beq SourceAttack_RepeatYes
    cmp #$0116
    beq SourceAttack_RepeatYes
    brl SourceAttack_RepeatNo
SourceAttack_RepeatYes:
.a16
.i16
    ply
    plx
    pla
    plp
    sec
    rts
SourceAttack_RepeatNo:
.a16
.i16
    ply
    plx
    pla
    plp
    clc
    rts
SourceAttack_BeforeEnd:
