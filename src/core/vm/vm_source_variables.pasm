; Persistent named local variables, owned by a script INSTANCE, not its model
; program. Animation current/default callbacks share the entity's instance.
; Exact byte/case-sensitive names; cleanup empties values and retains names.
; Indexed variables and stored STR values remain explicitly unbound.
; The exclusive pool owner validates all records before publishing B4A4.
VmSourceVars_Ready = $7FF780
VmSourceVars_Owner = $7FF782
VmSourceVars_Scope = $7FF786
VmSourceVars_Count = $7FF788
VmSourceVars_Base = $7FF78A
VmSourceVars_Bank = $7FF78C
VmSourceVars_Row = $7FF78E
VmSourceVars_Index = $7FF790
VmSourceVars_Free = $7FF792
VmSourceVars_Arg = $7FF794
VmSourceVars_Tag = $7FF796
VmSourceVars_Char = $7FF798
SOURCE_VARIABLE_POOL = $418800
SOURCE_VARIABLE_CAPACITY = 384
SOURCE_VARIABLE_STRIDE = 64

Vm_SourceVarsGet:
.a16
.i16
    jsr Vm_SourceVarsValidate
    bcc Vm_SourceVarsBranch_1
    jmp Vm_SourceVarsGet__bad
Vm_SourceVarsBranch_1:
.a16
.i16
    lda.l VmCall_Argc
    and #$00FF
    cmp #1
    beq Vm_SourceVarsBranch_2
    jmp Vm_SourceVarsGet__bad
Vm_SourceVarsBranch_2:
.a16
.i16
    jsr Vm_SourceVarsResolveKey
    bcc Vm_SourceVarsBranch_3
    jmp Vm_SourceVarsGet__bad
Vm_SourceVarsBranch_3:
.a16
.i16
    lda.l VmNativeVariant_KeyLength
    beq Vm_SourceVarsBranch_4
    jmp Vm_SourceVarsGet__lookup
Vm_SourceVarsBranch_4:
.a16
.i16
    jmp Vm_NativeVariantDispatch__null_ok
Vm_SourceVarsGet__lookup:
.a16
.i16
    jsr Vm_SourceVarsFind
    cmp #$FFFF
    beq Vm_SourceVarsBranch_5
    jmp Vm_SourceVarsGet__found
Vm_SourceVarsBranch_5:
.a16
.i16
    jmp Vm_NativeVariantDispatch__null_ok
Vm_SourceVarsGet__found:
.a16
.i16
    tax
    lda.l SOURCE_VARIABLE_POOL+8,x
    jsr Vm_SourceVarsCheckTag
    bcc Vm_SourceVarsBranch_6
    jmp Vm_SourceVarsGet__bad
Vm_SourceVarsBranch_6:
.a16
.i16
    lda.l SOURCE_VARIABLE_POOL+10,x
    beq Vm_SourceVarsBranch_7
    jmp Vm_SourceVarsGet__bad
Vm_SourceVarsBranch_7:
.a16
.i16
    lda.l SOURCE_VARIABLE_POOL+8,x
    sta.l VmNativeVariant_Result
    lda.l SOURCE_VARIABLE_POOL+10,x
    sta.l VmNativeVariant_Result+2
    lda.l SOURCE_VARIABLE_POOL+12,x
    sta.l VmNativeVariant_Result+4
    lda.l SOURCE_VARIABLE_POOL+14,x
    sta.l VmNativeVariant_Result+6
    clc
    rtl
Vm_SourceVarsGet__bad:
.a16
.i16
    sec
    lda #VMERR_BAD_NATIVE
    rtl

Vm_SourceVarsSet:
.a16
.i16
    jsr Vm_SourceVarsValidate
    bcc Vm_SourceVarsBranch_8
    jmp Vm_SourceVarsSet__bad
Vm_SourceVarsBranch_8:
.a16
.i16
    lda.l VmCall_Argc
    and #$00FF
    cmp #2
    beq Vm_SourceVarsBranch_9
    jmp Vm_SourceVarsSet__bad
Vm_SourceVarsBranch_9:
.a16
.i16
    jsr Vm_SourceVarsResolveKey
    bcc Vm_SourceVarsBranch_10
    jmp Vm_SourceVarsSet__bad
Vm_SourceVarsBranch_10:
.a16
.i16
    lda.l VmNativeVariant_KeyLength
    beq Vm_SourceVarsBranch_11
    jmp Vm_SourceVarsSet__value
Vm_SourceVarsBranch_11:
.a16
.i16
    lda #0                         ; empty name returns INTEGER 0, no allocation
    jmp Vm_SourceVarsIntegerResult
Vm_SourceVarsSet__value:
.a16
.i16
    lda #1
    jsr Vm_SourceEntityArgSlot
    txa
    sta.l VmSourceVars_Arg
    lda.l VmSlots_Wram,x
    jsr Vm_SourceVarsCheckTag
    bcc Vm_SourceVarsBranch_12
    jmp Vm_SourceVarsSet__bad
Vm_SourceVarsBranch_12:
.a16
.i16
    sta.l VmSourceVars_Tag
    lda.l VmSlots_Wram+2,x
    beq Vm_SourceVarsBranch_13
    jmp Vm_SourceVarsSet__bad
Vm_SourceVarsBranch_13:
.a16
.i16
    lda.l VmSourceVars_Tag
    beq Vm_SourceVarsBranch_14
    jmp Vm_SourceVarsSet__lookup
Vm_SourceVarsBranch_14:
.a16
.i16
    lda.l VmSlots_Wram+4,x
    ora.l VmSlots_Wram+6,x
    beq Vm_SourceVarsBranch_15
    jmp Vm_SourceVarsSet__bad
Vm_SourceVarsBranch_15:
.a16
.i16
Vm_SourceVarsSet__lookup:
.a16
.i16
    jsr Vm_SourceVarsFind
    cmp #$FFFF
    beq Vm_SourceVarsBranch_16
    jmp Vm_SourceVarsSet__existing
Vm_SourceVarsBranch_16:
.a16
.i16
    lda.l VmSourceVars_Free
    cmp #$FFFF
    bne Vm_SourceVarsBranch_17
    jmp Vm_SourceVarsSet__bad
Vm_SourceVarsBranch_17:
.a16
.i16
    sta.l VmSourceVars_Row
    tax
    lda.l VmSourceVars_Owner
    sta.l SOURCE_VARIABLE_POOL,x
    lda.l VmSourceVars_Owner+2
    sta.l SOURCE_VARIABLE_POOL+2,x
    lda.l VmSourceVars_Scope
    sta.l SOURCE_VARIABLE_POOL+4,x
    lda.l VmNativeVariant_KeyLength
    sta.l SOURCE_VARIABLE_POOL+6,x
    ldy #0
Vm_SourceVarsSet__key:
.a16
.i16
    jsr Vm_SourceVarsKeyByte
    sta.l VmSourceVars_Char
    tya
    clc
    adc.l VmSourceVars_Row
    tax
    lda.l VmSourceVars_Char
    sta.l SOURCE_VARIABLE_POOL+16,x ; overlapping words also store terminating 0
    iny
    tya
    cmp.l VmNativeVariant_KeyLength
    bcs Vm_SourceVarsBranch_18
    jmp Vm_SourceVarsSet__key
Vm_SourceVarsBranch_18:
.a16
.i16
    lda.l VmSourceVars_Row
Vm_SourceVarsSet__existing:
.a16
.i16
    sta.l VmSourceVars_Row
    lda.l VmSourceVars_Arg
    tax
    lda.l VmSlots_Wram,x
    sta.l VmNativeVariant_Result
    lda.l VmSlots_Wram+2,x
    sta.l VmNativeVariant_Result+2
    lda.l VmSlots_Wram+4,x
    sta.l VmNativeVariant_Result+4
    lda.l VmSlots_Wram+6,x
    sta.l VmNativeVariant_Result+6
    lda.l VmSourceVars_Row
    tax
    lda.l VmNativeVariant_Result
    sta.l SOURCE_VARIABLE_POOL+8,x
    lda.l VmNativeVariant_Result+2
    sta.l SOURCE_VARIABLE_POOL+10,x
    lda.l VmNativeVariant_Result+4
    sta.l SOURCE_VARIABLE_POOL+12,x
    lda.l VmNativeVariant_Result+6
    sta.l SOURCE_VARIABLE_POOL+14,x
    lda #1
    jmp Vm_SourceVarsIntegerResult
Vm_SourceVarsSet__bad:
.a16
.i16
    sec
    lda #VMERR_BAD_NATIVE
    rtl

Vm_SourceVarsClear:
.a16
.i16
    jsr Vm_SourceVarsValidate
    bcc Vm_SourceVarsBranch_19
    jmp Vm_SourceVarsClear__bad
Vm_SourceVarsBranch_19:
.a16
.i16
    lda.l VmCall_Argc
    and #$00FF
    beq Vm_SourceVarsBranch_20
    jmp Vm_SourceVarsClear__bad
Vm_SourceVarsBranch_20:
.a16
.i16
    lda #0
    sta.l VmSourceVars_Row
    sta.l VmSourceVars_Index
Vm_SourceVarsClear__loop:
.a16
.i16
    lda.l VmSourceVars_Row
    tax
    lda.l SOURCE_VARIABLE_POOL+6,x
    bne Vm_SourceVarsBranch_21
    jmp Vm_SourceVarsClear__next
Vm_SourceVarsBranch_21:
.a16
.i16
    lda.l SOURCE_VARIABLE_POOL,x
    cmp.l VmSourceVars_Owner
    beq Vm_SourceVarsBranch_22
    jmp Vm_SourceVarsClear__next
Vm_SourceVarsBranch_22:
.a16
.i16
    lda.l SOURCE_VARIABLE_POOL+2,x
    cmp.l VmSourceVars_Owner+2
    beq Vm_SourceVarsBranch_23
    jmp Vm_SourceVarsClear__next
Vm_SourceVarsBranch_23:
.a16
.i16
    lda.l SOURCE_VARIABLE_POOL+4,x
    cmp.l VmSourceVars_Scope
    beq Vm_SourceVarsBranch_24
    jmp Vm_SourceVarsClear__next
Vm_SourceVarsBranch_24:
.a16
.i16
    lda #0
    sta.l SOURCE_VARIABLE_POOL+8,x
    sta.l SOURCE_VARIABLE_POOL+10,x
    sta.l SOURCE_VARIABLE_POOL+12,x
    sta.l SOURCE_VARIABLE_POOL+14,x
Vm_SourceVarsClear__next:
.a16
.i16
    lda.l VmSourceVars_Row
    clc
    adc #64
    sta.l VmSourceVars_Row
    lda.l VmSourceVars_Index
    inc a
    sta.l VmSourceVars_Index
    cmp.l VmSourceVars_Count
    bcs Vm_SourceVarsBranch_25
    jmp Vm_SourceVarsClear__loop
Vm_SourceVarsBranch_25:
.a16
.i16
    jmp Vm_NativeVariantDispatch__null_ok
Vm_SourceVarsClear__bad:
.a16
.i16
    sec
    lda #VMERR_BAD_NATIVE
    rtl

Vm_SourceVarsIntegerResult:
.a16
.i16
    sta.l VmNativeVariant_Result+4
    lda #BOR_VT_INTEGER
    sta.l VmNativeVariant_Result
    lda #0
    sta.l VmNativeVariant_Result+2
    sta.l VmNativeVariant_Result+6
    clc
    rtl

Vm_SourceVarsValidate:
.a16
.i16
    lda.l VmNativeVariant_ContextValid
    cmp #$B48F
    beq Vm_SourceVarsBranch_26
    jmp Vm_SourceVarsValidate__bad
Vm_SourceVarsBranch_26:
.a16
.i16
    lda.l VmSourceWorld_Ready
    cmp #$B4A3
    beq Vm_SourceVarsBranch_27
    jmp Vm_SourceVarsValidate__bad
Vm_SourceVarsBranch_27:
.a16
.i16
    lda.l VmSourceVars_Ready
    cmp #$B4A4
    beq Vm_SourceVarsBranch_28
    jmp Vm_SourceVarsValidate__bad
Vm_SourceVarsBranch_28:
.a16
.i16
    lda.l VmSourceVars_Base
    cmp #$8800
    beq Vm_SourceVarsBranch_29
    jmp Vm_SourceVarsValidate__bad
Vm_SourceVarsBranch_29:
.a16
.i16
    lda.l VmSourceVars_Bank
    and #$00FF
    cmp #$0041
    beq Vm_SourceVarsBranch_30
    jmp Vm_SourceVarsValidate__bad
Vm_SourceVarsBranch_30:
.a16
.i16
    lda.l VmSourceVars_Count
    bne Vm_SourceVarsBranch_31
    jmp Vm_SourceVarsValidate__bad
Vm_SourceVarsBranch_31:
.a16
.i16
    cmp #385
    bcc Vm_SourceVarsBranch_32
    jmp Vm_SourceVarsValidate__bad
Vm_SourceVarsBranch_32:
.a16
.i16
    lda.l VmSourceVars_Scope
    bne Vm_SourceVarsBranch_33
    jmp Vm_SourceVarsValidate__bad
Vm_SourceVarsBranch_33:
.a16
.i16
    lda.l VmSourceVars_Owner
    ora.l VmSourceVars_Owner+2
    bne Vm_SourceVarsBranch_34
    jmp Vm_SourceVarsValidate__bad
Vm_SourceVarsBranch_34:
.a16
.i16
    ; The original caller snapshot retains identity even if a source script
    ; overwrites/clears its named "self" variable inside this instance.
    lda.l VmNativeVariant_Self
    cmp #BOR_VT_PTR
    beq Vm_SourceVarsBranch_35
    jmp Vm_SourceVarsValidate__bad
Vm_SourceVarsBranch_35:
.a16
.i16
    lda.l VmNativeVariant_Self+4
    cmp.l VmSourceVars_Owner
    beq Vm_SourceVarsBranch_36
    jmp Vm_SourceVarsValidate__bad
Vm_SourceVarsBranch_36:
.a16
.i16
    lda.l VmNativeVariant_Self+6
    cmp.l VmSourceVars_Owner+2
    beq Vm_SourceVarsBranch_37
    jmp Vm_SourceVarsValidate__bad
Vm_SourceVarsBranch_37:
.a16
.i16
    clc
    rts
Vm_SourceVarsValidate__bad:
.a16
.i16
    sec
    lda #VMERR_BAD_NATIVE
    rts

Vm_SourceVarsResolveKey:
.a16
.i16
    lda #0
    jsr Vm_SourceEntityArgSlot
    jsr Vm_SourceEntityResolveKey
    bcc Vm_SourceVarsBranch_38
    jmp Vm_SourceVarsResolveKey__bad
Vm_SourceVarsBranch_38:
.a16
.i16
    lda.l VmNativeVariant_KeyLength
    cmp #48
    bcc Vm_SourceVarsBranch_39
    jmp Vm_SourceVarsResolveKey__bad
Vm_SourceVarsBranch_39:
.a16
.i16
    cmp #0
    bne Vm_SourceVarsBranch_40
    jmp Vm_SourceVarsResolveKey__ok
Vm_SourceVarsBranch_40:
.a16
.i16
    ldy #0
Vm_SourceVarsResolveKey__char:
.a16
.i16
    jsr Vm_SourceVarsKeyByte
    bne Vm_SourceVarsBranch_41
    jmp Vm_SourceVarsResolveKey__bad
Vm_SourceVarsBranch_41:
.a16
.i16
    iny
    tya
    cmp.l VmNativeVariant_KeyLength
    bcs Vm_SourceVarsBranch_42
    jmp Vm_SourceVarsResolveKey__char
Vm_SourceVarsBranch_42:
.a16
.i16
Vm_SourceVarsResolveKey__ok:
.a16
.i16
    clc
    rts
Vm_SourceVarsResolveKey__bad:
.a16
.i16
    sec
    lda #VMERR_BAD_NATIVE
    rts

; Exact name lookup: A=row byte offset or $FFFF, plus first free row cached.
Vm_SourceVarsFind:
.a16
.i16
    lda #$FFFF
    sta.l VmSourceVars_Free
    lda #0
    sta.l VmSourceVars_Row
    sta.l VmSourceVars_Index
Vm_SourceVarsFind__row:
.a16
.i16
    lda.l VmSourceVars_Row
    tax
    lda.l SOURCE_VARIABLE_POOL+6,x
    beq Vm_SourceVarsBranch_43
    jmp Vm_SourceVarsFind__occupied
Vm_SourceVarsBranch_43:
.a16
.i16
    lda.l VmSourceVars_Free
    cmp #$FFFF
    beq Vm_SourceVarsBranch_44
    jmp Vm_SourceVarsFind__next
Vm_SourceVarsBranch_44:
.a16
.i16
    lda.l VmSourceVars_Row
    sta.l VmSourceVars_Free
    bra Vm_SourceVarsFind__next
Vm_SourceVarsFind__occupied:
.a16
.i16
    cmp.l VmNativeVariant_KeyLength
    beq Vm_SourceVarsBranch_45
    jmp Vm_SourceVarsFind__next
Vm_SourceVarsBranch_45:
.a16
.i16
    lda.l SOURCE_VARIABLE_POOL,x
    cmp.l VmSourceVars_Owner
    beq Vm_SourceVarsBranch_46
    jmp Vm_SourceVarsFind__next
Vm_SourceVarsBranch_46:
.a16
.i16
    lda.l SOURCE_VARIABLE_POOL+2,x
    cmp.l VmSourceVars_Owner+2
    beq Vm_SourceVarsBranch_47
    jmp Vm_SourceVarsFind__next
Vm_SourceVarsBranch_47:
.a16
.i16
    lda.l SOURCE_VARIABLE_POOL+4,x
    cmp.l VmSourceVars_Scope
    beq Vm_SourceVarsBranch_48
    jmp Vm_SourceVarsFind__next
Vm_SourceVarsBranch_48:
.a16
.i16
    ldy #0
Vm_SourceVarsFind__char:
.a16
.i16
    jsr Vm_SourceVarsKeyByte
    sta.l VmSourceVars_Char
    tya
    clc
    adc.l VmSourceVars_Row
    tax
    lda.l SOURCE_VARIABLE_POOL+16,x
    and #$00FF
    cmp.l VmSourceVars_Char
    beq Vm_SourceVarsBranch_49
    jmp Vm_SourceVarsFind__next
Vm_SourceVarsBranch_49:
.a16
.i16
    iny
    tya
    cmp.l VmNativeVariant_KeyLength
    bcs Vm_SourceVarsBranch_50
    jmp Vm_SourceVarsFind__char
Vm_SourceVarsBranch_50:
.a16
.i16
    lda.l VmSourceVars_Row
    rts
Vm_SourceVarsFind__next:
.a16
.i16
    lda.l VmSourceVars_Row
    clc
    adc #64
    sta.l VmSourceVars_Row
    lda.l VmSourceVars_Index
    inc a
    sta.l VmSourceVars_Index
    cmp.l VmSourceVars_Count
    bcs Vm_SourceVarsBranch_51
    jmp Vm_SourceVarsFind__row
Vm_SourceVarsBranch_51:
.a16
.i16
    lda #$FFFF
    rts

Vm_SourceVarsKeyByte:
.a16
.i16
    tya
    clc
    adc.l VmNativeVariant_KeyBase
    tax
    lda.l VmNativeVariant_KeyPool
    cmp #2                         ; internal ROM names, never source arguments
    beq Vm_SourceVarsKeyByte__internal
    cmp #0
    bne Vm_SourceVarsBranch_52
    jmp Vm_SourceVarsKeyByte__literal
Vm_SourceVarsBranch_52:
.a16
.i16
    lda.l VmStrPool_Wram,x
    bra Vm_SourceVarsKeyByte__return
Vm_SourceVarsKeyByte__literal:
.a16
.i16
    lda.l VmCode_Wram,x
    bra Vm_SourceVarsKeyByte__return
Vm_SourceVarsKeyByte__internal:
.a16
.i16
    lda.l Vm_SourceCallbackNames,x
Vm_SourceVarsKeyByte__return:
.a16
.i16
    and #$00FF
    rts

; Full header word must contain only a supported tag (flags byte zero).
Vm_SourceVarsCheckTag:
.a16
.i16
    cmp #BOR_VT_EMPTY
    bne Vm_SourceVarsBranch_53
    jmp Vm_SourceVarsCheckTag__ok
Vm_SourceVarsBranch_53:
.a16
.i16
    cmp #BOR_VT_INTEGER
    bne Vm_SourceVarsBranch_54
    jmp Vm_SourceVarsCheckTag__ok
Vm_SourceVarsBranch_54:
.a16
.i16
    cmp #BOR_VT_DECIMAL
    bne Vm_SourceVarsBranch_55
    jmp Vm_SourceVarsCheckTag__ok
Vm_SourceVarsBranch_55:
.a16
.i16
    cmp #BOR_VT_PTR
    bne Vm_SourceVarsBranch_56
    jmp Vm_SourceVarsCheckTag__ok
Vm_SourceVarsBranch_56:
.a16
.i16
    sec
    rts
Vm_SourceVarsCheckTag__ok:
.a16
.i16
    clc
    rts
