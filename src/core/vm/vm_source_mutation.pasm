; Source entity property mutations, bank 28. World owner grants an additional
; lease ONLY while the V2 record properties are authoritative and exclusive.
; A read-view lease alone cannot authorize mutation. No original-BOR alias.
; Coordinates remain explicit ACCEPTED_COMPAT_Q16_16. Out-of-range INTEGER
; coordinates fault rather than wrap; nonnumeric components leave state intact
; as ScriptVariant_DecimalValue failures do in pinned Build 4086.
VmSourceMutation_Ready = $7FF6D4 ; .dw $B4A2 authoritative property-owner lease
VmSourceMutation_Name = $7FF6D6
VmSourceMutation_Char = $7FF6D8
VmSourceMutation_Arg = $7FF6DA
VmSourceMutation_Offset = $7FF6DC
VmSourceMutation_Lo = $7FF6DE
VmSourceMutation_Hi = $7FF6E0
VmSourceMutation_Tag = $7FF6E2
VmSourceMutation_Write = $7FF6E4

Vm_SourceEntityChange:
.a16
.i16
    lda.l VmNativeVariant_ContextValid
    cmp #$B48F
    beq Vm_SourceEntityChange__arity
    jmp Vm_SourceEntityChange__bad
Vm_SourceEntityChange__arity:
.a16
.i16
    lda.l VmCall_Argc
    and #$00FF
    cmp #3
    bcc Vm_SourceEntityChange__bad
    cmp #6
    bcs Vm_SourceEntityChange__bad
    jsr Vm_SourceEntityLocate
    bcc Vm_SourceEntityChange__located
    rtl
Vm_SourceEntityChange__located:
.a16
.i16
    cmp #0
    bne Vm_SourceEntityChange__lease
    jmp Vm_NativeVariantDispatch__null_ok
Vm_SourceEntityChange__lease:
.a16
.i16
    lda.l VmSourceMutation_Ready
    cmp #$B4A2
    bne Vm_SourceEntityChange__bad
    lda #1
    jsr Vm_SourceEntityArgSlot
    jsr Vm_SourceEntityResolveKey
    bcc Vm_SourceEntityChange__key
    jmp Vm_SourceEntityChange__bad
Vm_SourceEntityChange__key:
.a16
.i16
    lda #0
    sta.l VmSourceMutation_Name
Vm_SourceEntityChange__name:
.a16
.i16
    lda.l VmSourceMutation_Name
    tax
    lda.l Vm_SourceMutationNames,x
    and #$00FF
    cmp.l VmNativeVariant_KeyLength
    bne Vm_SourceEntityChange__next_name
    ldy #0
Vm_SourceEntityChange__char:
.a16
.i16
    jsr Vm_SourceModelKeyByte
    sta.l VmSourceMutation_Char
    tya
    clc
    adc.l VmSourceMutation_Name
    inc a
    tax
    lda.l Vm_SourceMutationNames,x
    and #$00FF
    cmp.l VmSourceMutation_Char
    bne Vm_SourceEntityChange__next_name
    iny
    tya
    cmp.l VmNativeVariant_KeyLength
    bcc Vm_SourceEntityChange__char
    jmp Vm_SourceEntityChange__property
Vm_SourceEntityChange__next_name:
.a16
.i16
    lda.l VmSourceMutation_Name
    clc
    adc #16
    sta.l VmSourceMutation_Name
    cmp #144
    bcc Vm_SourceEntityChange__name
Vm_SourceEntityChange__bad:
.a16
.i16
    sec
    lda #VMERR_BAD_NATIVE
    rtl

Vm_SourceEntityChange__property:
.a16
.i16
    lda.l VmSourceMutation_Name
    cmp #112
    bcc Vm_SourceEntityChange__view_property
    jmp Vm_SourceMotionProperty
Vm_SourceEntityChange__view_property:
.a16
.i16
    lda.l VmSourceMutation_Name
    clc
    adc #14
    tax
    lda.l Vm_SourceMutationNames,x
    and #$00FF
    sta.l VmSourceMutation_Offset
    ; Poppy's label+constant expression loses the ROM bank; increment X instead.
    inx
    lda.l Vm_SourceMutationNames,x
    and #$00FF
    sta.l VmSourceMutation_Tag
    lda #2
    sta.l VmSourceMutation_Arg
Vm_SourceEntityChange__component:
.a16
.i16
    lda.l VmSourceMutation_Arg
    jsr Vm_SourceEntityArgSlot
    jsr Vm_SourceMutationNumber
    bcc Vm_SourceEntityChange__number
    ; Carry means conversion failed; $FFFF means our explicit Q16 range fault.
    cmp #$FFFF
    bne Vm_SourceEntityChange__next_component
    jmp Vm_SourceEntityChange__bad
Vm_SourceEntityChange__number:
.a16
.i16
    lda.l VmSourceMutation_Offset
    tay
    jsr Vm_SourceEntityRead16
    cmp.l VmSourceMutation_Tag
    beq Vm_SourceEntityChange__tag_ok
    jmp Vm_SourceEntityChange__bad
Vm_SourceEntityChange__tag_ok:
.a16
.i16
    iny
    iny
    jsr Vm_SourceEntityRead16
    beq Vm_SourceEntityChange__reserved_ok
    jmp Vm_SourceEntityChange__bad
Vm_SourceEntityChange__reserved_ok:
.a16
.i16
    lda.l VmSourceMutation_Offset
    clc
    adc #4
    tay
    lda.l VmSourceMutation_Lo
    jsr Vm_SourceEntityWrite16
    iny
    iny
    lda.l VmSourceMutation_Hi
    jsr Vm_SourceEntityWrite16
Vm_SourceEntityChange__next_component:
.a16
.i16
    lda.l VmSourceMutation_Name
    bne Vm_SourceEntityChange__done ; only position is a multi-component field
    lda.l VmSourceMutation_Arg
    inc a
    sta.l VmSourceMutation_Arg
    lda.l VmCall_Argc
    and #$00FF
    cmp.l VmSourceMutation_Arg
    beq Vm_SourceEntityChange__done
    lda.l VmSourceMutation_Arg
    cmp #3
    bne Vm_SourceEntityChange__altitude
    lda #56                       ; second component is z
    bra Vm_SourceEntityChange__set_offset
Vm_SourceEntityChange__altitude:
.a16
.i16
    lda #8                        ; third component is altitude a/y
Vm_SourceEntityChange__set_offset:
.a16
.i16
    sta.l VmSourceMutation_Offset
    jmp Vm_SourceEntityChange__component
Vm_SourceEntityChange__done:
.a16
.i16
    jmp Vm_NativeVariantDispatch__null_ok ; source *pretvar=NULL

; X=variant slot, Tag=destination numeric type. Conversion failure is ordinary
; component no-op. Q16 coordinate range overflow is an explicit capability fault.
Vm_SourceMutationNumber:
.a16
.i16
    lda.l VmSlots_Wram,x
    and #$00FF
    cmp #BOR_VT_INTEGER
    beq Vm_SourceMutationNumber__integer
    cmp #BOR_VT_DECIMAL
    beq Vm_SourceMutationNumber__decimal
    lda #0
    sec
    rts
Vm_SourceMutationNumber__integer:
.a16
.i16
    lda.l VmSlots_Wram+4,x
    sta.l VmSourceMutation_Lo
    lda.l VmSlots_Wram+6,x
    sta.l VmSourceMutation_Hi
    lda.l VmSourceMutation_Tag
    cmp #BOR_VT_INTEGER
    beq Vm_SourceMutationNumber__ok
    ; Signed32 INTEGER must fit signed16 before shifting to Q16.16.
    lda.l VmSourceMutation_Lo
    bmi Vm_SourceMutationNumber__negative_integer
    lda.l VmSourceMutation_Hi
    beq Vm_SourceMutationNumber__shift
    bra Vm_SourceMutationNumber__overflow
Vm_SourceMutationNumber__negative_integer:
.a16
.i16
    lda.l VmSourceMutation_Hi
    cmp #$FFFF
    beq Vm_SourceMutationNumber__shift
Vm_SourceMutationNumber__overflow:
.a16
.i16
    lda #$FFFF
    sec
    rts
Vm_SourceMutationNumber__shift:
.a16
.i16
    lda.l VmSourceMutation_Lo
    sta.l VmSourceMutation_Hi
    lda #0
    sta.l VmSourceMutation_Lo
    bra Vm_SourceMutationNumber__ok
Vm_SourceMutationNumber__decimal:
.a16
.i16
    lda.l VmSlots_Wram+4,x
    sta.l VmSourceMutation_Lo
    lda.l VmSlots_Wram+6,x
    sta.l VmSourceMutation_Hi
    lda.l VmSourceMutation_Tag
    cmp #BOR_VT_DECIMAL
    beq Vm_SourceMutationNumber__ok
    ; Truncate Q16 toward zero; arithmetic high word floors negatives.
    lda.l VmSourceMutation_Hi
    bpl Vm_SourceMutationNumber__truncate
    lda.l VmSourceMutation_Lo
    beq Vm_SourceMutationNumber__floor
    lda.l VmSourceMutation_Hi
    inc a
    bra Vm_SourceMutationNumber__truncate
Vm_SourceMutationNumber__floor:
.a16
.i16
    lda.l VmSourceMutation_Hi
Vm_SourceMutationNumber__truncate:
.a16
.i16
    sta.l VmSourceMutation_Lo
    bmi Vm_SourceMutationNumber__sign
    lda #0
    bra Vm_SourceMutationNumber__high
Vm_SourceMutationNumber__sign:
.a16
.i16
    lda #$FFFF
Vm_SourceMutationNumber__high:
.a16
.i16
    sta.l VmSourceMutation_Hi
Vm_SourceMutationNumber__ok:
.a16
.i16
    clc
    rts

; A=value, Y=record offset. Preserve caller DBR and Y; borrow no direct page.
Vm_SourceEntityWrite16:
.a16
.i16
    sta.l VmSourceMutation_Write
    phb
    lda.l VmSourceEntity_Record
    pha
    sep #$20
.a8
    lda.l VmSourceEntity_Bank
    pha
    plb
    rep #$20
.a16
    lda.l VmSourceMutation_Write
    sta (1,s),y
    pla
    plb
    rts

; Same 16-byte format as read-property names. Positions are numeric payloads
; only: tags/record identity are immutable under this property capability.
Vm_SourceMutationNames:
    .db 8,"position",0,0,0,0,0,48,2
    .db 9,"direction",0,0,0,0,24,1
    .db 1,"x",0,0,0,0,0,0,0,0,0,0,0,0,48,2
    .db 1,"z",0,0,0,0,0,0,0,0,0,0,0,0,56,2
    .db 1,"a",0,0,0,0,0,0,0,0,0,0,0,0,8,2
    .db 1,"y",0,0,0,0,0,0,0,0,0,0,0,0,8,2
    .db 6,"health",0,0,0,0,0,0,0,32,1
    .db 8,"velocity",0,0,0,0,0,36,2
    .db 5,"speed",0,0,0,0,0,0,0,0,0,60,2
