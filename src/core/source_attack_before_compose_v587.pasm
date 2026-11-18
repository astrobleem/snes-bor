; Borrow precisely the existing after-submit preparation visit for a
; coherent FIRST player attack, after retirement observation, before emission.
; All normal physical loader/palette/DMA/publication fences remain authoritative.
; Peer metadata uses46EE..F3. This scheduler owns only46F4..F7.
SourceAttack_Borrowed = $7E46F4
SourceAttack_Chosen = $7E46F6
SourceAttack_BeforeObserve:
.a16
.i16
    ; Preserve the original observer's entry flags, including decimal mode.
    jsl SVActor_Observe
    php
    rep #$30
    cld
    pha
    phx
    phy
    phb
    phd
    lda #0
    sta.l SourceAttack_Borrowed
    lda.l $7E46DE
    beq SourceAttack_Foreground
    brl SourceAttack_BeforeDone
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
    brl SourceAttack_BeforeDone
SourceAttack_InputCandidate:
.a16
.i16
    jsl SourceAttack_ScopeBridge
    bcs SourceAttack_Scope
    brl SourceAttack_BeforeDone
SourceAttack_Scope:
.a16
.i16
    lda.l Game_StageIndex
    beq SourceAttack_Stage
    brl SourceAttack_BeforeDone
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
    brl SourceAttack_BeforeDone
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
    brl SourceAttack_BeforeDone
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
    brl SourceAttack_BeforeDone
SourceAttack_Npc2OKValid:
.a16
.i16
    lda.l SVActor_Data+1280+SVActor_Stage
    beq SourceAttack_Npc2OKStage
    brl SourceAttack_BeforeDone
SourceAttack_Npc2OKStage:
.a16
.i16
    lda.l $7E0A00+266+CHAR_ROSTER_INDEX
    and #$00FF
    cmp.l SVActor_Data+1280+SVActor_Roster
    beq SourceAttack_Npc2OK
    brl SourceAttack_BeforeDone
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
    brl SourceAttack_BeforeDone
SourceAttack_Npc3OKValid:
.a16
.i16
    lda.l SVActor_Data+2560+SVActor_Stage
    beq SourceAttack_Npc3OKStage
    brl SourceAttack_BeforeDone
SourceAttack_Npc3OKStage:
.a16
.i16
    lda.l $7E0A00+399+CHAR_ROSTER_INDEX
    and #$00FF
    cmp.l SVActor_Data+2560+SVActor_Roster
    beq SourceAttack_Npc3OK
    brl SourceAttack_BeforeDone
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
    brl SourceAttack_BeforeDone
SourceAttack_Npc4OKValid:
.a16
.i16
    lda.l SVActor_Data+3840+SVActor_Stage
    beq SourceAttack_Npc4OKStage
    brl SourceAttack_BeforeDone
SourceAttack_Npc4OKStage:
.a16
.i16
    lda.l $7E0A00+532+CHAR_ROSTER_INDEX
    and #$00FF
    cmp.l SVActor_Data+3840+SVActor_Roster
    beq SourceAttack_Npc4OK
    brl SourceAttack_BeforeDone
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
    brl SourceAttack_BeforeDone
SourceAttack_Npc5OKValid:
.a16
.i16
    lda.l SVActor_Data+5120+SVActor_Stage
    beq SourceAttack_Npc5OKStage
    brl SourceAttack_BeforeDone
SourceAttack_Npc5OKStage:
.a16
.i16
    lda.l $7E0A00+665+CHAR_ROSTER_INDEX
    and #$00FF
    cmp.l SVActor_Data+5120+SVActor_Roster
    beq SourceAttack_Npc5OK
    brl SourceAttack_BeforeDone
SourceAttack_Npc5OK:
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
    brl SourceAttack_BeforeDone
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
SourceAttack_BeforeDone:
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
    ; Producer and consumer are independent. Drain before the next scene.
    jsl SourceVisual_SampleInput
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
SourceAttack_BeforeEnd:
