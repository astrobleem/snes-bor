; Mutable cached-model animation pointers, represented by immutable frame
; handles. This is one component of set_model_ex, not the complete model switch.
; B4E9 leases $43C000..$43DFFF when B609 is disabled; B609 owns
; $43DE00..$43DFFF and limits this cache to 7680 bytes. Paired B4FE descriptor.
; Source TYPE and script identity are separate; no source actor aliases exist.
SourceModelAnimationCopy4086_Ready = $7FFC50
SourceModelAnimationCopy4086_Models = $7FFC52
SourceModelAnimationCopy4086_Maximum = $7FFC54
SourceModelAnimationCopy4086_Bytes = $7FFC56
SourceModelAnimationCopy4086_OldModel = $7FFC58
SourceModelAnimationCopy4086_NewModel = $7FFC5A
SourceModelAnimationCopy4086_Flags = $7FFC5C
SourceModelAnimationCopy4086_OldOffset = $7FFC5E
SourceModelAnimationCopy4086_NewOffset = $7FFC60
SourceModelAnimationCopy4086_Index = $7FFC62
SourceModelAnimationCopy4086_RowBytes = $7FFC64
SourceModelAnimationCopy4086_Frames = $7FFC66
SourceModelAnimationCopy4086_Candidate = $7FFC68
SourceModelAnimationCopy4086_Offset = $7FFC6A
SourceModelAnimationCopy4086_Status = $7FFC6C ; 1 success,2 explicit fault
SOURCE_MODEL_ANIMATION_CACHE = $43C000

SourceModelAnimationCopy4086_Apply:
.a16
.i16
    php
    rep #$38
    phx
    phy
    lda.l SourceModelAnimationCopy4086_Ready
    cmp #$B4E9
    beq SourceModelAnimationCopy4086_Branch_1
    jmp SourceModelAnimationCopy4086_Bad
SourceModelAnimationCopy4086_Branch_1:
.a16
.i16
    lda.l SourceModelAnimationCopy4086_Models
    bne SourceModelAnimationCopy4086_Branch_2
    jmp SourceModelAnimationCopy4086_Bad
SourceModelAnimationCopy4086_Branch_2:
.a16
.i16
    cmp #129
    bcc SourceModelAnimationCopy4086_Branch_3
    jmp SourceModelAnimationCopy4086_Bad
SourceModelAnimationCopy4086_Branch_3:
.a16
.i16
    cmp.l SourceModelAnimationCopy4086_OldModel
    bne SourceModelAnimationCopy4086_Branch_4
    jmp SourceModelAnimationCopy4086_Bad
SourceModelAnimationCopy4086_Branch_4:
.a16
.i16
    bcs SourceModelAnimationCopy4086_Branch_5
    jmp SourceModelAnimationCopy4086_Bad
SourceModelAnimationCopy4086_Branch_5:
.a16
.i16
    cmp.l SourceModelAnimationCopy4086_NewModel
    bne SourceModelAnimationCopy4086_Branch_6
    jmp SourceModelAnimationCopy4086_Bad
SourceModelAnimationCopy4086_Branch_6:
.a16
.i16
    bcs SourceModelAnimationCopy4086_Branch_7
    jmp SourceModelAnimationCopy4086_Bad
SourceModelAnimationCopy4086_Branch_7:
.a16
.i16
    lda.l SourceModelAnimationCopy4086_Flags
    and #$FFF8
    beq SourceModelAnimationCopy4086_Branch_8
    jmp SourceModelAnimationCopy4086_Bad
SourceModelAnimationCopy4086_Branch_8:
.a16
.i16
    lda.l SourceModelAnimationCopy4086_Maximum
    bne SourceModelAnimationCopy4086_Branch_9
    jmp SourceModelAnimationCopy4086_Bad
SourceModelAnimationCopy4086_Branch_9:
.a16
.i16
    cmp #1025
    bcc SourceModelAnimationCopy4086_Branch_10
    jmp SourceModelAnimationCopy4086_Bad
SourceModelAnimationCopy4086_Branch_10:
.a16
.i16
    asl a
    sta.l SourceModelAnimationCopy4086_RowBytes
    lda #0
    ldx #0
SourceModelAnimationCopy4086_SizeLoop:
.a16
.i16
    clc
    adc.l SourceModelAnimationCopy4086_RowBytes
    bcc SourceModelAnimationCopy4086_Branch_11
    jmp SourceModelAnimationCopy4086_Bad
SourceModelAnimationCopy4086_Branch_11:
.a16
.i16
    inx
    pha
    txa
    cmp.l SourceModelAnimationCopy4086_Models
    pla
    bcs SourceModelAnimationCopy4086_Branch_12
    jmp SourceModelAnimationCopy4086_SizeLoop
SourceModelAnimationCopy4086_Branch_12:
.a16
.i16
    cmp #8193
    bcc SourceModelAnimationCopy4086_Branch_13
    jmp SourceModelAnimationCopy4086_Bad
SourceModelAnimationCopy4086_Branch_13:
.a16
.i16
    jsl SourceAttackCostState4086_CheckCacheSpan
    bcc SourceModelAnimationCopy4086_CostSpanChecked
    jmp SourceModelAnimationCopy4086_Bad
SourceModelAnimationCopy4086_CostSpanChecked:
.a16
.i16
    cmp.l SourceModelAnimationCopy4086_Bytes
    beq SourceModelAnimationCopy4086_Branch_14
    jmp SourceModelAnimationCopy4086_Bad
SourceModelAnimationCopy4086_Branch_14:
.a16
.i16
    lda.l SourceModelAnimationCopy4086_OldModel
    jsr SourceModelAnimationCopy4086_RowOffset
    sta.l SourceModelAnimationCopy4086_OldOffset
    lda.l SourceModelAnimationCopy4086_NewModel
    jsr SourceModelAnimationCopy4086_RowOffset
    sta.l SourceModelAnimationCopy4086_NewOffset
    lda.l SourceModelAnimationCopy4086_Flags
    bit #1
    beq SourceModelAnimationCopy4086_Branch_15
    jmp SourceModelAnimationCopy4086_Done
SourceModelAnimationCopy4086_Branch_15:
.a16
.i16
    lda.l SourceUpdateFrame4086_Ready
    cmp #$B4E3
    beq SourceModelAnimationCopy4086_Branch_16
    jmp SourceModelAnimationCopy4086_Bad
SourceModelAnimationCopy4086_Branch_16:
.a16
.i16
    lda.l SourceUpdateFrame4086_Bank
    cmp #64
    bcc SourceModelAnimationCopy4086_Branch_17
    jmp SourceModelAnimationCopy4086_Bad
SourceModelAnimationCopy4086_Branch_17:
.a16
.i16
    lda.l SourceUpdateFrame4086_Bytes
    cmp #16
    bcs SourceModelAnimationCopy4086_Branch_18
    jmp SourceModelAnimationCopy4086_Bad
SourceModelAnimationCopy4086_Branch_18:
.a16
.i16
    dec a
    clc
    adc.l SourceUpdateFrame4086_Base
    bcc SourceModelAnimationCopy4086_Branch_19
    jmp SourceModelAnimationCopy4086_Bad
SourceModelAnimationCopy4086_Branch_19:
.a16
.i16
    lda.l SourceUpdateFrame4086_Base
    cmp #$8000
    bcs SourceModelAnimationCopy4086_Branch_20
    jmp SourceModelAnimationCopy4086_Bad
SourceModelAnimationCopy4086_Branch_20:
.a16
.i16
    tax
    jsr SourceUpdateFrame4086_Read
    cmp #$3442
    beq SourceModelAnimationCopy4086_Branch_21
    jmp SourceModelAnimationCopy4086_Bad
SourceModelAnimationCopy4086_Branch_21:
.a16
.i16
    inx
    inx
    jsr SourceUpdateFrame4086_Read
    cmp #$4546
    beq SourceModelAnimationCopy4086_Branch_22
    jmp SourceModelAnimationCopy4086_Bad
SourceModelAnimationCopy4086_Branch_22:
.a16
.i16
    inx
    inx
    jsr SourceUpdateFrame4086_Read
    cmp #1
    beq SourceModelAnimationCopy4086_Branch_23
    jmp SourceModelAnimationCopy4086_Bad
SourceModelAnimationCopy4086_Branch_23:
.a16
.i16
    inx
    inx
    jsr SourceUpdateFrame4086_Read
    bne SourceModelAnimationCopy4086_Branch_24
    jmp SourceModelAnimationCopy4086_Bad
SourceModelAnimationCopy4086_Branch_24:
.a16
.i16
    cmp #129
    bcc SourceModelAnimationCopy4086_Branch_25
    jmp SourceModelAnimationCopy4086_Bad
SourceModelAnimationCopy4086_Branch_25:
.a16
.i16
    sta.l SourceModelAnimationCopy4086_Frames
    asl a
    asl a
    asl a
    clc
    adc #16
    cmp.l SourceUpdateFrame4086_Bytes
    bne SourceModelAnimationCopy4086_Branch_26
    jmp SourceModelAnimationCopy4086_Bad
SourceModelAnimationCopy4086_Branch_26:
.a16
.i16
    bcc SourceModelAnimationCopy4086_Branch_27
    jmp SourceModelAnimationCopy4086_Bad
SourceModelAnimationCopy4086_Branch_27:
.a16
.i16
    ; Validate both source/destination rows before changing any cached pointer.
    lda #0
    sta.l SourceModelAnimationCopy4086_Index
SourceModelAnimationCopy4086_Preflight:
.a16
.i16
    lda.l SourceModelAnimationCopy4086_OldOffset
    clc
    adc.l SourceModelAnimationCopy4086_Index
    tax
    lda.l SOURCE_MODEL_ANIMATION_CACHE,x
    jsr SourceModelAnimationCopy4086_CheckHandle
    bcc SourceModelAnimationCopy4086_Branch_28
    jmp SourceModelAnimationCopy4086_Bad
SourceModelAnimationCopy4086_Branch_28:
.a16
.i16
    lda.l SourceModelAnimationCopy4086_NewOffset
    clc
    adc.l SourceModelAnimationCopy4086_Index
    tax
    lda.l SOURCE_MODEL_ANIMATION_CACHE,x
    jsr SourceModelAnimationCopy4086_CheckHandle
    bcc SourceModelAnimationCopy4086_Branch_29
    jmp SourceModelAnimationCopy4086_Bad
SourceModelAnimationCopy4086_Branch_29:
.a16
.i16
    lda.l SourceModelAnimationCopy4086_Index
    inc a
    inc a
    sta.l SourceModelAnimationCopy4086_Index
    cmp.l SourceModelAnimationCopy4086_RowBytes
    bcs SourceModelAnimationCopy4086_Branch_30
    jmp SourceModelAnimationCopy4086_Preflight
SourceModelAnimationCopy4086_Branch_30:
.a16
.i16
    lda #0
    sta.l SourceModelAnimationCopy4086_Index
SourceModelAnimationCopy4086_Copy:
.a16
.i16
    lda.l SourceModelAnimationCopy4086_NewOffset
    clc
    adc.l SourceModelAnimationCopy4086_Index
    tax
    lda.l SOURCE_MODEL_ANIMATION_CACHE,x
    beq SourceModelAnimationCopy4086_Branch_31
    jmp SourceModelAnimationCopy4086_Next
SourceModelAnimationCopy4086_Branch_31:
.a16
.i16
    lda.l SourceModelAnimationCopy4086_OldOffset
    clc
    adc.l SourceModelAnimationCopy4086_Index
    tax
    lda.l SOURCE_MODEL_ANIMATION_CACHE,x
    bne SourceModelAnimationCopy4086_Branch_32
    jmp SourceModelAnimationCopy4086_Next
SourceModelAnimationCopy4086_Branch_32:
.a16
.i16
    sta.l SourceModelAnimationCopy4086_Candidate
    jsr SourceModelAnimationCopy4086_FrameCount
    bne SourceModelAnimationCopy4086_Branch_33
    jmp SourceModelAnimationCopy4086_Next
SourceModelAnimationCopy4086_Branch_33:
.a16
.i16
    lda.l SourceModelAnimationCopy4086_NewOffset
    clc
    adc.l SourceModelAnimationCopy4086_Index
    tax
    lda.l SourceModelAnimationCopy4086_Candidate
    sta.l SOURCE_MODEL_ANIMATION_CACHE,x
SourceModelAnimationCopy4086_Next:
.a16
.i16
    lda.l SourceModelAnimationCopy4086_Index
    inc a
    inc a
    sta.l SourceModelAnimationCopy4086_Index
    cmp.l SourceModelAnimationCopy4086_RowBytes
    bcs SourceModelAnimationCopy4086_Branch_34
    jmp SourceModelAnimationCopy4086_Copy
SourceModelAnimationCopy4086_Branch_34:
.a16
.i16
SourceModelAnimationCopy4086_Done:
.a16
.i16
    lda #1
    sta.l SourceModelAnimationCopy4086_Status
    ply
    plx
    plp
    clc
    rtl
SourceModelAnimationCopy4086_Bad:
.a16
.i16
    lda #2
    sta.l SourceModelAnimationCopy4086_Status
    ply
    plx
    plp
    sec
    rtl

SourceModelAnimationCopy4086_RowOffset:
.a16
.i16
    tay
    lda #0
    cpy #0
    bne SourceModelAnimationCopy4086_Branch_35
    jmp SourceModelAnimationCopy4086_RowOffsetDone
SourceModelAnimationCopy4086_Branch_35:
.a16
.i16
SourceModelAnimationCopy4086_RowOffsetLoop:
.a16
.i16
    clc
    adc.l SourceModelAnimationCopy4086_RowBytes
    dey
    beq SourceModelAnimationCopy4086_Branch_36
    jmp SourceModelAnimationCopy4086_RowOffsetLoop
SourceModelAnimationCopy4086_Branch_36:
.a16
.i16
SourceModelAnimationCopy4086_RowOffsetDone:
.a16
.i16
    rts

SourceModelAnimationCopy4086_CheckHandle:
.a16
.i16
    bne SourceModelAnimationCopy4086_Branch_37
    jmp SourceModelAnimationCopy4086_HandleGood
SourceModelAnimationCopy4086_Branch_37:
.a16
.i16
    cmp.l SourceModelAnimationCopy4086_Frames
    bne SourceModelAnimationCopy4086_Branch_38
    jmp SourceModelAnimationCopy4086_HandleGood
SourceModelAnimationCopy4086_Branch_38:
.a16
.i16
    bcs SourceModelAnimationCopy4086_Branch_39
    jmp SourceModelAnimationCopy4086_HandleGood
SourceModelAnimationCopy4086_Branch_39:
.a16
.i16
    sec
    rts
SourceModelAnimationCopy4086_HandleGood:
.a16
.i16
    clc
    rts

; Candidate handle was validated, so its bounded B4FE directory owns this read.
SourceModelAnimationCopy4086_FrameCount:
.a16
.i16
    dec a
    asl a
    asl a
    asl a
    clc
    adc #18
    clc
    adc.l SourceUpdateFrame4086_Base
    tax
    jsr SourceUpdateFrame4086_Read
    rts
