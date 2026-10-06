; ent_set_model's animation transition AFTER installation of new modeldata.
; The caller restores prior entity type only after this owner completes.
; B4EF requires source-derived role IDs and default calculate_edelay inputs;
; nondefault entity-delay models must use another explicitly admitted backend.
SourceModelAnimation4086_Ready = $7FFCE0
SourceModelAnimation4086_State = $7FFCE2 ; 1 initialization pending,2 done,3 fault
SourceModelAnimation4086_Slot = $7FFCE4
SourceModelAnimation4086_Sync = $7FFCE6
SourceModelAnimation4086_TimeLo = $7FFCE8
SourceModelAnimation4086_TimeHi = $7FFCEA
SourceModelAnimation4086_Select = $7FFCEC
SourceModelAnimation4086_Idle = $7FFCEE
SourceModelAnimation4086_Spawn = $7FFCF0
SourceModelAnimation4086_Respawn = $7FFCF2
SourceModelAnimation4086_SelectAnimation = $7FFCF4
SourceModelAnimation4086_Frame = $7FFCF6
SourceModelAnimation4086_FrameOffset = $7FFCF8
SourceModelAnimation4086_Delay = $7FFCFA
SourceModelAnimation4086_DelayPolicy = $7FFCFC ; 1 checked source default edelay
SourceModelAnimation4086_Branch = $7FFCFE ; 1 synchronized,2 ent_set_anim

SourceModelAnimation4086_CheckIdle:
.a16
.i16
    php
    rep #$38
    pha
    lda.l SourceModelAnimation4086_Ready
    beq SourceModelAnimation4086_IdleGood
    cmp #$B4EF
    bne SourceModelAnimation4086_IdleBad
    lda.l SourceModelAnimation4086_State
    beq SourceModelAnimation4086_IdleGood
    cmp #2
    bne SourceModelAnimation4086_IdleBad
SourceModelAnimation4086_IdleGood:
.a16
.i16
    pla
    plp
    clc
    rtl
SourceModelAnimation4086_IdleBad:
.a16
.i16
    pla
    plp
    sec
    rtl

SourceModelAnimation4086_Begin:
.a16
.i16
    php
    rep #$38
    phx
    phy
    lda.l SourceModelAnimation4086_Ready
    cmp #$B4EF
    beq SourceModelAnimation4086_Relaxed_1
    jmp SourceModelAnimation4086_Bad
SourceModelAnimation4086_Relaxed_1:
.a16
.i16
    lda.l SourceModelAnimation4086_State
    cmp #1
    bne SourceModelAnimation4086_Relaxed_2
    jmp SourceModelAnimation4086_Bad
SourceModelAnimation4086_Relaxed_2:
.a16
.i16
    cmp #3
    bne SourceModelAnimation4086_Relaxed_3
    jmp SourceModelAnimation4086_Bad
SourceModelAnimation4086_Relaxed_3:
.a16
.i16
    lda.l SourceModelAnimation4086_DelayPolicy
    cmp #1
    beq SourceModelAnimation4086_Relaxed_4
    jmp SourceModelAnimation4086_Bad
SourceModelAnimation4086_Relaxed_4:
.a16
.i16
    lda.l SourceModelAnimation4086_Slot
    cmp #128
    bcc SourceModelAnimation4086_Relaxed_5
    jmp SourceModelAnimation4086_Bad
SourceModelAnimation4086_Relaxed_5:
.a16
.i16
    sta.l SourceAnimationInit4086_Slot
    ; Request current source animation identity; Resolve validates all leases,
    ; cache bounds, variant tag, selected B4AI/B4FE row and frame count.
    asl a
    asl a
    asl a
    asl a
    sta.l SourceModelAnimation4086_FrameOffset
    asl a
    asl a
    clc
    adc.l SourceModelAnimation4086_FrameOffset
    clc
    adc #$4000
    tax
    lda.l $410014,x
    cmp.l SourceModelAnimationCopy4086_Maximum
    bcc SourceModelAnimation4086_CurrentNumberGood
    jmp SourceModelAnimation4086_Bad ; source out-of-bounds model access
SourceModelAnimation4086_CurrentNumberGood:
.a16
.i16
    sta.l SourceAnimationInit4086_Number
    jsl SourceAnimationInit4086_Resolve
    bcc SourceModelAnimation4086_Relaxed_6
    jmp SourceModelAnimation4086_Bad
SourceModelAnimation4086_Relaxed_6:
.a16
.i16
    lda.l SourceModelAnimation4086_Sync
    bne SourceModelAnimation4086_Relaxed_7
    jmp SourceModelAnimation4086_Initialize
SourceModelAnimation4086_Relaxed_7:
.a16
.i16
    lda.l SourceAnimationInit4086_Handle
    bne SourceModelAnimation4086_Relaxed_8
    jmp SourceModelAnimation4086_Initialize
SourceModelAnimation4086_Relaxed_8:
.a16
.i16
    lda.l SourceAnimationInit4086_Count
    bne SourceModelAnimation4086_SyncCountGood
    jmp SourceModelAnimation4086_Bad ; zero-frame sync would read delay[-1]
SourceModelAnimation4086_SyncCountGood:
.a16
.i16
    lda.l SourceAnimationInit4086_Side
    tax
    lda.l $410006,x
    cmp.l SourceAnimationInit4086_Count
    bcc SourceModelAnimation4086_KeepFrame
    lda.l SourceAnimationInit4086_Count
    dec a
SourceModelAnimation4086_KeepFrame:
.a16
.i16
    sta.l SourceModelAnimation4086_Frame
    ; Preflight the complete directory and chosen frame delay before mutation.
    lda.l SourceAnimationInit4086_Handle
    dec a
    asl a
    asl a
    asl a
    clc
    adc #22
    clc
    adc.l SourceUpdateFrame4086_Base
    tax
    jsr SourceUpdateFrame4086_Read
    clc
    adc.l SourceUpdateFrame4086_Base
    bcc SourceModelAnimation4086_FramePointerInBank
    jmp SourceModelAnimation4086_Bad
SourceModelAnimation4086_FramePointerInBank:
.a16
.i16
    sta.l SourceModelAnimation4086_FrameOffset
    lda.l SourceUpdateFrame4086_Animations
    asl a
    asl a
    asl a
    clc
    adc #144
    clc
    adc.l SourceUpdateFrame4086_Base
    cmp.l SourceModelAnimation4086_FrameOffset
    beq SourceModelAnimation4086_FramePointerGood
    bcc SourceModelAnimation4086_Relaxed_9
    jmp SourceModelAnimation4086_Bad
SourceModelAnimation4086_Relaxed_9:
.a16
.i16
SourceModelAnimation4086_FramePointerGood:
.a16
.i16
    lda.l SourceModelAnimation4086_Frame
    asl a
    asl a
    asl a
    bcc SourceModelAnimation4086_Relaxed_10
    jmp SourceModelAnimation4086_Bad
SourceModelAnimation4086_Relaxed_10:
.a16
.i16
    pha
    asl a
    bcc SourceModelAnimation4086_Relaxed_11
    jmp SourceModelAnimation4086_DropBad
SourceModelAnimation4086_Relaxed_11:
.a16
.i16
    clc
    adc 1,s
    bcc SourceModelAnimation4086_Relaxed_12
    jmp SourceModelAnimation4086_DropBad
SourceModelAnimation4086_Relaxed_12:
.a16
.i16
    clc
    adc.l SourceModelAnimation4086_FrameOffset
    bcc SourceModelAnimation4086_Relaxed_13
    jmp SourceModelAnimation4086_DropBad
SourceModelAnimation4086_Relaxed_13:
.a16
.i16
    clc
    adc #24
    bcc SourceModelAnimation4086_Relaxed_14
    jmp SourceModelAnimation4086_DropBad
SourceModelAnimation4086_Relaxed_14:
.a16
.i16
    pha
    lda.l SourceUpdateFrame4086_Base
    clc
    adc.l SourceUpdateFrame4086_Bytes
    bcc SourceModelAnimation4086_Relaxed_15
    jmp SourceModelAnimation4086_DropTwoBad
SourceModelAnimation4086_Relaxed_15:
.a16
.i16
    cmp 1,s
    bcs SourceModelAnimation4086_Relaxed_16
    jmp SourceModelAnimation4086_DropTwoBad
SourceModelAnimation4086_Relaxed_16:
.a16
.i16
    pla
    sec
    sbc #4
    tax
    jsr SourceUpdateFrame4086_Read
    sta.l SourceModelAnimation4086_Delay
    inx
    inx
    jsr SourceUpdateFrame4086_Read
    beq SourceModelAnimation4086_Relaxed_17
    jmp SourceModelAnimation4086_DropBad
SourceModelAnimation4086_Relaxed_17:
.a16
.i16
    pla
    lda.l SourceAnimationInit4086_Side
    tax
    lda.l SourceAnimationInit4086_Handle
    sta.l $410004,x
    lda.l SourceModelAnimation4086_Frame
    sta.l $410006,x
    lda.l SourceModelAnimation4086_TimeLo
    clc
    adc.l SourceModelAnimation4086_Delay
    sta.l $410008,x
    lda.l SourceModelAnimation4086_TimeHi
    adc #0
    sta.l $41000A,x
    lda #1
    sta.l SourceModelAnimation4086_Branch
    jmp SourceModelAnimation4086_Done
SourceModelAnimation4086_DropTwoBad:
.a16
.i16
    pla
SourceModelAnimation4086_DropBad:
.a16
.i16
    pla
    jmp SourceModelAnimation4086_Bad

SourceModelAnimation4086_Initialize:
.a16
.i16
    ; Check role numbers before selecting through source validanim semantics.
    lda.l SourceModelAnimation4086_Idle
    cmp.l SourceModelAnimationCopy4086_Maximum
    bcc SourceModelAnimation4086_Relaxed_18
    jmp SourceModelAnimation4086_Bad
SourceModelAnimation4086_Relaxed_18:
.a16
.i16
    lda.l SourceModelAnimation4086_Spawn
    cmp.l SourceModelAnimationCopy4086_Maximum
    bcc SourceModelAnimation4086_Relaxed_19
    jmp SourceModelAnimation4086_Bad
SourceModelAnimation4086_Relaxed_19:
.a16
.i16
    lda.l SourceModelAnimation4086_Respawn
    cmp.l SourceModelAnimationCopy4086_Maximum
    bcc SourceModelAnimation4086_Relaxed_20
    jmp SourceModelAnimation4086_Bad
SourceModelAnimation4086_Relaxed_20:
.a16
.i16
    lda.l SourceModelAnimation4086_SelectAnimation
    cmp.l SourceModelAnimationCopy4086_Maximum
    bcc SourceModelAnimation4086_Relaxed_21
    jmp SourceModelAnimation4086_Bad
SourceModelAnimation4086_Relaxed_21:
.a16
.i16
    lda.l SourceAnimationInit4086_Core
    tax
    lda.l $400048,x ; new modeldata TYPE before old entity TYPE restoration
    bit #1
    beq SourceModelAnimation4086_ChooseSpawn
    lda.l SourceModelAnimation4086_Select
    bne SourceModelAnimation4086_ChooseSelect
    lda.l SourceModelAnimation4086_TimeLo
    ora.l SourceModelAnimation4086_TimeHi
    beq SourceModelAnimation4086_ChooseSpawn
    lda.l SourceModelAnimation4086_Respawn
    jsr SourceModelAnimation4086_Valid
    bcc SourceModelAnimation4086_Relaxed_22
    jmp SourceModelAnimation4086_Bad
SourceModelAnimation4086_Relaxed_22:
.a16
.i16
    bne SourceModelAnimation4086_Selected
SourceModelAnimation4086_ChooseSpawn:
.a16
.i16
    lda.l SourceModelAnimation4086_Spawn
    jsr SourceModelAnimation4086_Valid
    bcc SourceModelAnimation4086_Relaxed_23
    jmp SourceModelAnimation4086_Bad
SourceModelAnimation4086_Relaxed_23:
.a16
.i16
    bne SourceModelAnimation4086_Selected
    bra SourceModelAnimation4086_ChooseIdle
SourceModelAnimation4086_ChooseSelect:
.a16
.i16
    lda.l SourceModelAnimation4086_SelectAnimation
    jsr SourceModelAnimation4086_Valid
    bcc SourceModelAnimation4086_Relaxed_24
    jmp SourceModelAnimation4086_Bad
SourceModelAnimation4086_Relaxed_24:
.a16
.i16
    bne SourceModelAnimation4086_Selected
SourceModelAnimation4086_ChooseIdle:
.a16
.i16
    lda.l SourceModelAnimation4086_Idle
    sta.l SourceAnimationInit4086_Number
SourceModelAnimation4086_Selected:
.a16
.i16
    ; Only now clear attacking, then invoke actual ent_set_anim ownership.
    lda.l SourceAnimationInit4086_Core
    tax
    lda #0
    sta.l $400058,x
    sta.l $40005A,x
    sta.l SourceAnimationInit4086_Reset
    jsl SourceAnimationInit4086_Begin
    bcc SourceModelAnimation4086_Relaxed_25
    jmp SourceModelAnimation4086_Bad
SourceModelAnimation4086_Relaxed_25:
.a16
.i16
    lda #2
    sta.l SourceModelAnimation4086_Branch
    lda.l SourceAnimationInit4086_State
    cmp #2
    bne SourceModelAnimation4086_Relaxed_26
    jmp SourceModelAnimation4086_Done
SourceModelAnimation4086_Relaxed_26:
.a16
.i16
    lda #1
    sta.l SourceModelAnimation4086_State
    ply
    plx
    plp
    clc
    rtl
SourceModelAnimation4086_Done:
.a16
.i16
    lda #2
    sta.l SourceModelAnimation4086_State
    ply
    plx
    plp
    clc
    rtl
SourceModelAnimation4086_Bad:
.a16
.i16
    lda #3
    sta.l SourceModelAnimation4086_State
    ply
    plx
    plp
    sec
    rtl

SourceModelAnimation4086_Valid:
.a16
.i16
    sta.l SourceAnimationInit4086_Number
    jsl SourceAnimationInit4086_Resolve
    bcs SourceModelAnimation4086_Invalid
    lda.l SourceAnimationInit4086_Count
    ora #0
    clc
SourceModelAnimation4086_Invalid:
.a16
.i16
    rts

SourceModelAnimation4086_Ack:
.a16
.i16
    php
    rep #$38
    phx
    phy
    lda.l SourceModelAnimation4086_Ready
    cmp #$B4EF
    beq SourceModelAnimation4086_Relaxed_27
    jmp SourceModelAnimation4086_Bad
SourceModelAnimation4086_Relaxed_27:
.a16
.i16
    lda.l SourceModelAnimation4086_State
    cmp #1
    beq SourceModelAnimation4086_Relaxed_28
    jmp SourceModelAnimation4086_Bad
SourceModelAnimation4086_Relaxed_28:
.a16
.i16
    lda.l SourceAnimationInit4086_State
    cmp #2
    beq SourceModelAnimation4086_Relaxed_29
    jmp SourceModelAnimation4086_Bad
SourceModelAnimation4086_Relaxed_29:
.a16
.i16
    lda.l SourceAnimationInit4086_Slot
    cmp.l SourceModelAnimation4086_Slot
    beq SourceModelAnimation4086_Relaxed_30
    jmp SourceModelAnimation4086_Bad
SourceModelAnimation4086_Relaxed_30:
.a16
.i16
    jmp SourceModelAnimation4086_Done
