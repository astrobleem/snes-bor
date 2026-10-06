; Scalar/weapon-list part of set_model_ex's mutable cached inheritance.
; B4EE exclusive model metadata at $40BA00..$40BBFF, sixteen 32-byte rows.
; +0 list identity (FFFF=NULL), +2 count, +4 modelflag; +8/+12 weaploss int32.
; This component does not install an entity model or initialize animations.
SourceModelCachedCopy4086_Ready = $7FFCC0
SourceModelCachedCopy4086_Models = $7FFCC2
SourceModelCachedCopy4086_Old = $7FFCC4
SourceModelCachedCopy4086_New = $7FFCC6
SourceModelCachedCopy4086_Flags = $7FFCC8
SourceModelCachedCopy4086_OldOffset = $7FFCCA
SourceModelCachedCopy4086_NewOffset = $7FFCCC
SourceModelCachedCopy4086_Index = $7FFCCE
SourceModelCachedCopy4086_Status = $7FFCD0
SourceModelCachedCopy4086_OldMeta = $7FFCD2
SourceModelCachedCopy4086_NewMeta = $7FFCD4

SourceModelCachedCopy4086_Apply:
.a16
.i16
    php
    rep #$38
    phx
    phy
    lda.l SourceModelCachedCopy4086_Ready
    cmp #$B4EE
    beq SourceModelCachedCopy4086_Relaxed_1
    jmp SourceModelCachedCopy4086_Bad
SourceModelCachedCopy4086_Relaxed_1:
.a16
.i16
    lda.l SourceModelEntityCopy4086_Ready
    cmp #$B4EB
    beq SourceModelCachedCopy4086_Relaxed_2
    jmp SourceModelCachedCopy4086_Bad
SourceModelCachedCopy4086_Relaxed_2:
.a16
.i16
    lda.l SourceModelCachedCopy4086_Models
    bne SourceModelCachedCopy4086_Relaxed_3
    jmp SourceModelCachedCopy4086_Bad
SourceModelCachedCopy4086_Relaxed_3:
.a16
.i16
    cmp #17
    bcc SourceModelCachedCopy4086_Relaxed_4
    jmp SourceModelCachedCopy4086_Bad
SourceModelCachedCopy4086_Relaxed_4:
.a16
.i16
    lda.l SourceModelCachedCopy4086_Old
    cmp.l SourceModelCachedCopy4086_Models
    bcc SourceModelCachedCopy4086_Relaxed_5
    jmp SourceModelCachedCopy4086_Bad
SourceModelCachedCopy4086_Relaxed_5:
.a16
.i16
    jsr SourceModelCachedCopy4086_Offset
    sta.l SourceModelCachedCopy4086_OldOffset
    lda.l SourceModelCachedCopy4086_New
    cmp.l SourceModelCachedCopy4086_Models
    bcc SourceModelCachedCopy4086_Relaxed_6
    jmp SourceModelCachedCopy4086_Bad
SourceModelCachedCopy4086_Relaxed_6:
.a16
.i16
    jsr SourceModelCachedCopy4086_Offset
    sta.l SourceModelCachedCopy4086_NewOffset
    lda.l SourceModelCachedCopy4086_Flags
    and #$FFF8
    beq SourceModelCachedCopy4086_Relaxed_7
    jmp SourceModelCachedCopy4086_Bad
SourceModelCachedCopy4086_Relaxed_7:
.a16
.i16
    ; NO_COPY must skip scalar AND metadata inheritance, without dereferencing
    ; an unused weapon list. Compiler installation owns source flag identity.
    lda.l SourceModelCachedCopy4086_Flags
    bit #1
    beq SourceModelCachedCopy4086_Relaxed_8
    jmp SourceModelCachedCopy4086_Done
SourceModelCachedCopy4086_Relaxed_8:
.a16
.i16
    lda.l SourceModelCachedCopy4086_Old
    jsr SourceModelCachedCopy4086_MetaOffset
    sta.l SourceModelCachedCopy4086_OldMeta
    lda.l SourceModelCachedCopy4086_New
    jsr SourceModelCachedCopy4086_MetaOffset
    sta.l SourceModelCachedCopy4086_NewMeta
    tax
    lda.l SourceModelCachedCopy4086_Flags
    bit #2
    bne SourceModelCachedCopy4086_PreflightDone
    jsr SourceModelCachedCopy4086_CheckMeta
    bcc SourceModelCachedCopy4086_Relaxed_9
    jmp SourceModelCachedCopy4086_Bad
SourceModelCachedCopy4086_Relaxed_9:
.a16
.i16
    lda.l SourceModelCachedCopy4086_OldMeta
    tax
    jsr SourceModelCachedCopy4086_CheckMeta
    bcc SourceModelCachedCopy4086_Relaxed_10
    jmp SourceModelCachedCopy4086_Bad
SourceModelCachedCopy4086_Relaxed_10:
.a16
.i16
SourceModelCachedCopy4086_PreflightDone:
.a16
.i16
    lda #0
    sta.l SourceModelCachedCopy4086_Index
    jsr SourceModelCachedCopy4086_IsZero
    bne SourceModelCachedCopy4086_SpeedDone
    jsr SourceModelCachedCopy4086_CopyField
SourceModelCachedCopy4086_SpeedDone:
.a16
.i16
    lda #4
    sta.l SourceModelCachedCopy4086_Index
    jsr SourceModelCachedCopy4086_IsZero
    bne SourceModelCachedCopy4086_RunDone
SourceModelCachedCopy4086_RunLoop:
.a16
.i16
    jsr SourceModelCachedCopy4086_CopyField
    lda.l SourceModelCachedCopy4086_Index
    clc
    adc #4
    sta.l SourceModelCachedCopy4086_Index
    cmp #24
    bcc SourceModelCachedCopy4086_RunLoop
SourceModelCachedCopy4086_RunDone:
.a16
.i16
    lda #24
    sta.l SourceModelCachedCopy4086_Index
SourceModelCachedCopy4086_NegativeLoop:
.a16
.i16
    lda.l SourceModelCachedCopy4086_NewOffset
    clc
    adc.l SourceModelCachedCopy4086_Index
    tax
    lda.l $400002,x
    bpl SourceModelCachedCopy4086_NextNegative
    jsr SourceModelCachedCopy4086_CopyField
SourceModelCachedCopy4086_NextNegative:
.a16
.i16
    lda.l SourceModelCachedCopy4086_Index
    clc
    adc #4
    sta.l SourceModelCachedCopy4086_Index
    cmp #80
    bcc SourceModelCachedCopy4086_NegativeLoop
    lda.l SourceModelCachedCopy4086_Flags
    bit #2
    beq SourceModelCachedCopy4086_Relaxed_11
    jmp SourceModelCachedCopy4086_Done
SourceModelCachedCopy4086_Relaxed_11:
.a16
.i16
    lda #152 ; weapnum
    sta.l SourceModelCachedCopy4086_Index
    jsr SourceModelCachedCopy4086_CopyField
    lda.l SourceModelCachedCopy4086_NewMeta
    tax
    lda.l $400000,x
    cmp #$FFFF
    beq SourceModelCachedCopy4086_Relaxed_12
    jmp SourceModelCachedCopy4086_Done
SourceModelCachedCopy4086_Relaxed_12:
.a16
.i16
    lda.l SourceModelCachedCopy4086_OldMeta
    tax
    lda.l $400000,x
    pha
    lda.l $400002,x
    pha
    lda.l SourceModelCachedCopy4086_NewMeta
    tax
    pla
    sta.l $400002,x
    pla
    sta.l $400000,x
SourceModelCachedCopy4086_Done:
.a16
.i16
    lda #1
    sta.l SourceModelCachedCopy4086_Status
    ply
    plx
    plp
    clc
    rtl
SourceModelCachedCopy4086_Bad:
.a16
.i16
    lda #2
    sta.l SourceModelCachedCopy4086_Status
    ply
    plx
    plp
    sec
    rtl

SourceModelCachedCopy4086_Offset:
.a16
.i16
    asl a
    asl a
    asl a
    asl a
    asl a
    pha
    asl a
    asl a
    clc
    adc #$B000
    sta.l SourceModelCachedCopy4086_Index
    pla
    clc
    adc.l SourceModelCachedCopy4086_Index
    rts
SourceModelCachedCopy4086_MetaOffset:
.a16
.i16
    asl a
    asl a
    asl a
    asl a
    asl a
    clc
    adc #$BA00
    rts

SourceModelCachedCopy4086_CheckMeta:
.a16
.i16
    lda.l $400002,x
    cmp #129
    bcs SourceModelCachedCopy4086_MetaBad
    lda.l $400000,x
    cmp #$FFFF
    bne SourceModelCachedCopy4086_MetaList
    lda.l $400002,x
    bne SourceModelCachedCopy4086_MetaBad
    clc
    rts
SourceModelCachedCopy4086_MetaList:
.a16
.i16
    cmp.l SourceModelCachedCopy4086_Models
    bcs SourceModelCachedCopy4086_MetaBad
    clc
    rts
SourceModelCachedCopy4086_MetaBad:
.a16
.i16
    sec
    rts

SourceModelCachedCopy4086_IsZero:
.a16
.i16
    lda.l SourceModelCachedCopy4086_NewOffset
    clc
    adc.l SourceModelCachedCopy4086_Index
    tax
    lda.l $400002,x
    and #$7FFF ; +0.0 and -0.0 compare equal to zero in source binary32
    ora.l $400000,x
    rts
SourceModelCachedCopy4086_CopyField:
.a16
.i16
    lda.l SourceModelCachedCopy4086_OldOffset
    clc
    adc.l SourceModelCachedCopy4086_Index
    tax
    lda.l $400000,x
    pha
    lda.l $400002,x
    pha
    lda.l SourceModelCachedCopy4086_NewOffset
    clc
    adc.l SourceModelCachedCopy4086_Index
    tax
    pla
    sta.l $400002,x
    pla
    sta.l $400000,x
    rts
