; Pinned source openborconstant ABI. INTEGER input is copied unchanged.
; Case-insensitive animation names use a compiler-derived immutable table.
; Live PLAYER_MIN_Z/MAX_Z additionally require the current level owner.
; Other constant families, strings not in the table and bad types fault.
; The CRC-validating loader grants B4A8 only after table validation.
VmSourceConstants_Ready = $7FF800
VmSourceConstants_Base = $7FF802
VmSourceConstants_Bank = $7FF804
VmSourceConstants_Count = $7FF806
VmSourceConstants_Bytes = $7FF808
VmSourceConstants_Arg = $7FF80A
VmSourceConstants_Row = $7FF80C
VmSourceConstants_Index = $7FF80E
VmSourceConstants_Read = $7FF810
VmSourceConstants_Char = $7FF812
VmSourceConstants_Kind = $7FF814
VmSourceConstants_Low = $7FF816
VmSourceConstants_High = $7FF818
VmSourceLevelBounds_Ready = $7FF820
VmSourceLevelBounds_Min = $7FF822
VmSourceLevelBounds_Max = $7FF826

Vm_SourceConstantGet:
.a16
.i16
    lda.l VmCall_Argc
    and #$00FF
    cmp #1
    bne Vm_SourceConstantSearchBranch_1
    jmp Vm_SourceConstantBranch_1
Vm_SourceConstantSearchBranch_1:
.a16
.i16
    jmp Vm_SourceConstantGet__bad
Vm_SourceConstantBranch_1:
.a16
.i16
    lda #0
    jsr Vm_SourceEntityArgSlot
    txa
    sta.l VmSourceConstants_Arg
    lda.l VmSlots_Wram,x
    cmp #BOR_VT_INTEGER
    beq Vm_SourceConstantSearchBranch_2
    jmp Vm_SourceConstantBranch_2
Vm_SourceConstantSearchBranch_2:
.a16
.i16
    jmp Vm_SourceConstantGet__integer
Vm_SourceConstantBranch_2:
.a16
.i16
    cmp #BOR_VT_STR
    bne Vm_SourceConstantSearchBranch_3
    jmp Vm_SourceConstantGet__string
Vm_SourceConstantSearchBranch_3:
.a16
.i16
    cmp #(BOR_VT_STR | $0200)     ; flags bit 1: owned dynamic string
    bne Vm_SourceConstantSearchBranch_4
    jmp Vm_SourceConstantBranch_3
Vm_SourceConstantSearchBranch_4:
.a16
.i16
    jmp Vm_SourceConstantGet__bad
Vm_SourceConstantBranch_3:
.a16
.i16
Vm_SourceConstantGet__string:
.a16
.i16
    lda.l VmSlots_Wram+2,x
    sta.l VmNativeVariant_KeyLength
    jsr Vm_SourceEntityResolveKey
    bcs Vm_SourceConstantSearchBranch_5
    jmp Vm_SourceConstantBranch_4
Vm_SourceConstantSearchBranch_5:
.a16
.i16
    jmp Vm_SourceConstantGet__bad
Vm_SourceConstantBranch_4:
.a16
.i16
    lda.l VmNativeVariant_KeyLength
    beq Vm_SourceConstantSearchBranch_6
    jmp Vm_SourceConstantBranch_5
Vm_SourceConstantSearchBranch_6:
.a16
.i16
    jmp Vm_SourceConstantGet__bad
Vm_SourceConstantBranch_5:
.a16
.i16
    cmp #32
    bcs Vm_SourceConstantSearchBranch_7
    jmp Vm_SourceConstantBranch_6
Vm_SourceConstantSearchBranch_7:
.a16
.i16
    jmp Vm_SourceConstantGet__bad
Vm_SourceConstantBranch_6:
.a16
.i16
    jsr Vm_SourceConstantValidate
    bcs Vm_SourceConstantSearchBranch_8
    jmp Vm_SourceConstantBranch_7
Vm_SourceConstantSearchBranch_8:
.a16
.i16
    jmp Vm_SourceConstantGet__bad
Vm_SourceConstantBranch_7:
.a16
.i16
    lda #0
    sta.l VmSourceConstants_Low
    lda.l VmSourceConstants_Count
    sta.l VmSourceConstants_High
Vm_SourceConstantGet__row:
.a16
.i16
    lda.l VmSourceConstants_Low
    cmp.l VmSourceConstants_High
    bcs Vm_SourceConstantSearchBranch_9
    jmp Vm_SourceConstantGet__search
Vm_SourceConstantSearchBranch_9:
.a16
.i16
    jmp Vm_SourceConstantGet__bad
Vm_SourceConstantGet__search:
.a16
.i16
    clc
    adc.l VmSourceConstants_High
    lsr a
    sta.l VmSourceConstants_Index
    asl a
    asl a
    asl a
    sta.l VmSourceConstants_Row
    asl a
    asl a
    clc
    adc.l VmSourceConstants_Row
    clc
    adc #24
    sta.l VmSourceConstants_Row
    tay
    jsr Vm_SourceConstantRead16
    cmp.l VmNativeVariant_KeyLength
    bne Vm_SourceConstantSearchBranch_10
    jmp Vm_SourceConstantGet__equal_length
Vm_SourceConstantSearchBranch_10:
.a16
.i16
    bcs Vm_SourceConstantSearchBranch_11
    jmp Vm_SourceConstantGet__raise_low
Vm_SourceConstantSearchBranch_11:
.a16
.i16
    jmp Vm_SourceConstantGet__lower_high
Vm_SourceConstantGet__equal_length:
.a16
.i16
    ldy #0
Vm_SourceConstantGet__char:
.a16
.i16
    jsr Vm_SourceModelKeyByte       ; lowercase literal/heap key byte
    sta.l VmSourceConstants_Char
    phy
    tya
    clc
    adc.l VmSourceConstants_Row
    adc #8
    tay
    jsr Vm_SourceConstantRead16
    and #$00FF
    ply
    cmp.l VmSourceConstants_Char
    bne Vm_SourceConstantSearchBranch_12
    jmp Vm_SourceConstantGet__equal_char
Vm_SourceConstantSearchBranch_12:
.a16
.i16
    bcs Vm_SourceConstantSearchBranch_13
    jmp Vm_SourceConstantGet__raise_low
Vm_SourceConstantSearchBranch_13:
.a16
.i16
    jmp Vm_SourceConstantGet__lower_high
Vm_SourceConstantGet__equal_char:
.a16
.i16
    iny
    tya
    cmp.l VmNativeVariant_KeyLength
    bcc Vm_SourceConstantSearchBranch_14
    jmp Vm_SourceConstantBranch_10
Vm_SourceConstantSearchBranch_14:
.a16
.i16
    jmp Vm_SourceConstantGet__char
Vm_SourceConstantBranch_10:
.a16
.i16
    lda.l VmSourceConstants_Row
    clc
    adc #2
    tay
    jsr Vm_SourceConstantRead16
    sta.l VmSourceConstants_Kind
    beq Vm_SourceConstantSearchBranch_15
    jmp Vm_SourceConstantBranch_11
Vm_SourceConstantSearchBranch_15:
.a16
.i16
    jmp Vm_SourceConstantGet__static
Vm_SourceConstantBranch_11:
.a16
.i16
    cmp #3
    bcs Vm_SourceConstantSearchBranch_16
    jmp Vm_SourceConstantBranch_12
Vm_SourceConstantSearchBranch_16:
.a16
.i16
    jmp Vm_SourceConstantGet__bad
Vm_SourceConstantBranch_12:
.a16
.i16
    lda.l VmSourceLevelBounds_Ready
    cmp #$B4A9
    bne Vm_SourceConstantSearchBranch_17
    jmp Vm_SourceConstantBranch_13
Vm_SourceConstantSearchBranch_17:
.a16
.i16
    jmp Vm_SourceConstantGet__bad
Vm_SourceConstantBranch_13:
.a16
.i16
    lda.l VmSourceWorld_Ready
    cmp #$B4A3
    bne Vm_SourceConstantSearchBranch_18
    jmp Vm_SourceConstantBranch_14
Vm_SourceConstantSearchBranch_18:
.a16
.i16
    jmp Vm_SourceConstantGet__bad
Vm_SourceConstantBranch_14:
.a16
.i16
    lda.l VmSourceWorld_Level
    cmp #1
    bne Vm_SourceConstantSearchBranch_19
    jmp Vm_SourceConstantBranch_15
Vm_SourceConstantSearchBranch_19:
.a16
.i16
    jmp Vm_SourceConstantGet__bad
Vm_SourceConstantBranch_15:
.a16
.i16
    lda.l VmSourceConstants_Kind
    cmp #1
    bne Vm_SourceConstantSearchBranch_20
    jmp Vm_SourceConstantBranch_16
Vm_SourceConstantSearchBranch_20:
.a16
.i16
    jmp Vm_SourceConstantGet__maximum
Vm_SourceConstantBranch_16:
.a16
.i16
    lda.l VmSourceLevelBounds_Min
    sta.l VmNativeVariant_Result+4
    lda.l VmSourceLevelBounds_Min+2
    sta.l VmNativeVariant_Result+6
    jmp Vm_SourceConstantGet__mapped
Vm_SourceConstantGet__maximum:
.a16
.i16
    lda.l VmSourceLevelBounds_Max
    sta.l VmNativeVariant_Result+4
    lda.l VmSourceLevelBounds_Max+2
    sta.l VmNativeVariant_Result+6
    jmp Vm_SourceConstantGet__mapped
Vm_SourceConstantGet__static:
.a16
.i16
    lda.l VmSourceConstants_Row
    clc
    adc #4
    tay
    jsr Vm_SourceConstantRead16
    sta.l VmNativeVariant_Result+4
    iny
    iny
    jsr Vm_SourceConstantRead16
    sta.l VmNativeVariant_Result+6
Vm_SourceConstantGet__mapped:
.a16
.i16
    lda #BOR_VT_INTEGER
    sta.l VmNativeVariant_Result
    lda #0
    sta.l VmNativeVariant_Result+2
    ; mapstrings_transconst converts the native argument before returning.
    lda.l VmSourceConstants_Arg
    lsr a
    lsr a
    lsr a
    jsr Vm_SourceStr_ReleaseIfDynamic
    lda.l VmSourceConstants_Arg
    tax
    lda.l VmNativeVariant_Result
    sta.l VmSlots_Wram,x
    lda.l VmNativeVariant_Result+2
    sta.l VmSlots_Wram+2,x
    lda.l VmNativeVariant_Result+4
    sta.l VmSlots_Wram+4,x
    lda.l VmNativeVariant_Result+6
    sta.l VmSlots_Wram+6,x
    clc
    rtl
Vm_SourceConstantGet__raise_low:
.a16
.i16
    lda.l VmSourceConstants_Index
    inc a
    sta.l VmSourceConstants_Low
    jmp Vm_SourceConstantGet__row
Vm_SourceConstantGet__lower_high:
.a16
.i16
    lda.l VmSourceConstants_Index
    sta.l VmSourceConstants_High
    jmp Vm_SourceConstantGet__row
Vm_SourceConstantGet__integer:
.a16
.i16
    lda.l VmSlots_Wram+2,x
    bne Vm_SourceConstantSearchBranch_21
    jmp Vm_SourceConstantBranch_18
Vm_SourceConstantSearchBranch_21:
.a16
.i16
    jmp Vm_SourceConstantGet__bad
Vm_SourceConstantBranch_18:
.a16
.i16
    lda #BOR_VT_INTEGER
    sta.l VmNativeVariant_Result
    lda #0
    sta.l VmNativeVariant_Result+2
    lda.l VmSlots_Wram+4,x
    sta.l VmNativeVariant_Result+4
    lda.l VmSlots_Wram+6,x
    sta.l VmNativeVariant_Result+6
    clc
    rtl
Vm_SourceConstantGet__bad:
.a16
.i16
    sec
    lda #VMERR_BAD_NATIVE
    rtl

Vm_SourceConstantValidate:
.a16
.i16
    lda.l VmSourceConstants_Ready
    cmp #$B4A8
    bne Vm_SourceConstantSearchBranch_22
    jmp Vm_SourceConstantBranch_19
Vm_SourceConstantSearchBranch_22:
.a16
.i16
    jmp Vm_SourceConstantValidate__bad
Vm_SourceConstantBranch_19:
.a16
.i16
    lda.l VmSourceConstants_Base
    cmp #$8000
    bcc Vm_SourceConstantSearchBranch_23
    jmp Vm_SourceConstantBranch_20
Vm_SourceConstantSearchBranch_23:
.a16
.i16
    jmp Vm_SourceConstantValidate__bad
Vm_SourceConstantBranch_20:
.a16
.i16
    lda.l VmSourceConstants_Bank
    cmp #64
    bcs Vm_SourceConstantSearchBranch_24
    jmp Vm_SourceConstantBranch_21
Vm_SourceConstantSearchBranch_24:
.a16
.i16
    jmp Vm_SourceConstantValidate__bad
Vm_SourceConstantBranch_21:
.a16
.i16
    lda.l VmSourceConstants_Count
    beq Vm_SourceConstantSearchBranch_25
    jmp Vm_SourceConstantBranch_22
Vm_SourceConstantSearchBranch_25:
.a16
.i16
    jmp Vm_SourceConstantValidate__bad
Vm_SourceConstantBranch_22:
.a16
.i16
    cmp #410
    bcs Vm_SourceConstantSearchBranch_26
    jmp Vm_SourceConstantBranch_23
Vm_SourceConstantSearchBranch_26:
.a16
.i16
    jmp Vm_SourceConstantValidate__bad
Vm_SourceConstantBranch_23:
.a16
.i16
    ; count*40+24; count <=409 already prevents arithmetic overflow.
    asl a
    asl a
    asl a
    sta.l VmSourceConstants_Read
    asl a
    asl a
    clc
    adc.l VmSourceConstants_Read
    clc
    adc #24
    cmp.l VmSourceConstants_Bytes
    bne Vm_SourceConstantSearchBranch_27
    jmp Vm_SourceConstantBranch_25
Vm_SourceConstantSearchBranch_27:
.a16
.i16
    jmp Vm_SourceConstantValidate__bad
Vm_SourceConstantBranch_25:
.a16
.i16
    dec a
    clc
    adc.l VmSourceConstants_Base
    bcs Vm_SourceConstantSearchBranch_28
    jmp Vm_SourceConstantBranch_26
Vm_SourceConstantSearchBranch_28:
.a16
.i16
    jmp Vm_SourceConstantValidate__bad
Vm_SourceConstantBranch_26:
.a16
.i16
    ldy #0
    jsr Vm_SourceConstantRead16
    cmp #$3442
    bne Vm_SourceConstantSearchBranch_29
    jmp Vm_SourceConstantBranch_27
Vm_SourceConstantSearchBranch_29:
.a16
.i16
    jmp Vm_SourceConstantValidate__bad
Vm_SourceConstantBranch_27:
.a16
.i16
    ldy #2
    jsr Vm_SourceConstantRead16
    cmp #$5443
    bne Vm_SourceConstantSearchBranch_30
    jmp Vm_SourceConstantBranch_28
Vm_SourceConstantSearchBranch_30:
.a16
.i16
    jmp Vm_SourceConstantValidate__bad
Vm_SourceConstantBranch_28:
.a16
.i16
    ldy #4
    jsr Vm_SourceConstantRead16
    cmp #1
    bne Vm_SourceConstantSearchBranch_31
    jmp Vm_SourceConstantBranch_29
Vm_SourceConstantSearchBranch_31:
.a16
.i16
    jmp Vm_SourceConstantValidate__bad
Vm_SourceConstantBranch_29:
.a16
.i16
    ldy #6
    jsr Vm_SourceConstantRead16
    cmp #40
    bne Vm_SourceConstantSearchBranch_32
    jmp Vm_SourceConstantBranch_30
Vm_SourceConstantSearchBranch_32:
.a16
.i16
    jmp Vm_SourceConstantValidate__bad
Vm_SourceConstantBranch_30:
.a16
.i16
    ldy #8
    jsr Vm_SourceConstantRead16
    cmp.l VmSourceConstants_Count
    bne Vm_SourceConstantSearchBranch_33
    jmp Vm_SourceConstantBranch_31
Vm_SourceConstantSearchBranch_33:
.a16
.i16
    jmp Vm_SourceConstantValidate__bad
Vm_SourceConstantBranch_31:
.a16
.i16
    ldy #10
    jsr Vm_SourceConstantRead16
    bne Vm_SourceConstantSearchBranch_34
    jmp Vm_SourceConstantBranch_32
Vm_SourceConstantSearchBranch_34:
.a16
.i16
    jmp Vm_SourceConstantValidate__bad
Vm_SourceConstantBranch_32:
.a16
.i16
    ldy #12
    jsr Vm_SourceConstantRead16
    clc
    adc #24
    cmp.l VmSourceConstants_Bytes
    bne Vm_SourceConstantSearchBranch_35
    jmp Vm_SourceConstantBranch_33
Vm_SourceConstantSearchBranch_35:
.a16
.i16
    jmp Vm_SourceConstantValidate__bad
Vm_SourceConstantBranch_33:
.a16
.i16
    ldy #14
    jsr Vm_SourceConstantRead16
    bne Vm_SourceConstantSearchBranch_36
    jmp Vm_SourceConstantBranch_34
Vm_SourceConstantSearchBranch_36:
.a16
.i16
    jmp Vm_SourceConstantValidate__bad
Vm_SourceConstantBranch_34:
.a16
.i16
    ldy #20
    jsr Vm_SourceConstantRead16
    bne Vm_SourceConstantSearchBranch_37
    jmp Vm_SourceConstantBranch_35
Vm_SourceConstantSearchBranch_37:
.a16
.i16
    jmp Vm_SourceConstantValidate__bad
Vm_SourceConstantBranch_35:
.a16
.i16
    ldy #22
    jsr Vm_SourceConstantRead16
    bne Vm_SourceConstantSearchBranch_38
    jmp Vm_SourceConstantBranch_36
Vm_SourceConstantSearchBranch_38:
.a16
.i16
    jmp Vm_SourceConstantValidate__bad
Vm_SourceConstantBranch_36:
.a16
.i16
    clc
    rts
Vm_SourceConstantValidate__bad:
.a16
.i16
    sec
    rts

Vm_SourceConstantRead16:
.a16
.i16
    phb
    lda.l VmSourceConstants_Base
    pha
    sep #$20
.a8
    lda.l VmSourceConstants_Bank
    pha
    plb
    rep #$20
.a16
    lda (1,s),y
    sta.l VmSourceConstants_Read
    pla
    plb
    lda.l VmSourceConstants_Read
    rts
