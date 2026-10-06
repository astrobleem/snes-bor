; Generic BOR4086 playerkeys over an exclusively owned source-tick snapshot.
; The owner publishes held/new/released u32 source masks for 1..4 player slots
; before granting Ready. This API does not map SNES buttons or advance ticks.
; Read-only during an installed script context; no original-BOR actor alias.
VmSourceInput_Ready = $7FF8A0       ; $B4C2
VmSourceInput_Count = $7FF8A2
VmSourceInput_Tick = $7FF8A4        ; u32 owner timestamp
VmSourceInput_Data = $7FF8A8        ; four rows, held/new/released u32
VmSourceInput_Offset = $7FF8D8
VmSourceInput_Keys = $7FF8DA
VmSourceInput_Name = $7FF8DC
VmSourceInput_Hi = $7FF8DE
VmSourceInput_Lo = $7FF8E0

Vm_SourcePlayerKeys:
.a16
.i16
    lda.l VmNativeVariant_ContextValid
    cmp #$B48F
    beq Vm_SourcePlayerKeys__context
    jmp Vm_SourcePlayerKeys__bad
Vm_SourcePlayerKeys__context:
.a16
.i16
    lda.l VmCall_Argc
    and #$00FF
    cmp #3
    beq Vm_SourcePlayerKeys__arity
    jmp Vm_SourcePlayerKeys__bad
Vm_SourcePlayerKeys__arity:
.a16
.i16
    lda.l VmSourceInput_Ready
    cmp #$B4C2
    beq Vm_SourcePlayerKeys__lease
    jmp Vm_SourcePlayerKeys__bad
Vm_SourcePlayerKeys__lease:
.a16
.i16
    lda.l VmSourceInput_Count
    beq Vm_SourcePlayerKeys__reject
    cmp #5
    bcc Vm_SourcePlayerKeys__index
Vm_SourcePlayerKeys__reject:
.a16
.i16
    jmp Vm_SourcePlayerKeys__bad
Vm_SourcePlayerKeys__index:
.a16
.i16
    lda #0
    jsr Vm_SourceEntityArgSlot
    jsr Vm_SourceInputNumber
    pha
    lda.l VmSourceInput_Hi
    beq Vm_SourcePlayerKeys__index_hi
    pla
    jmp Vm_SourcePlayerKeys__bad
Vm_SourcePlayerKeys__index_hi:
.a16
.i16
    pla
    cmp.l VmSourceInput_Count
    bcs Vm_SourcePlayerKeys__reject
    asl a
    asl a
    sta.l VmSourceInput_Offset
    asl a
    clc
    adc.l VmSourceInput_Offset
    sta.l VmSourceInput_Offset
    lda #1
    jsr Vm_SourceEntityArgSlot
    jsr Vm_SourceInputNumber
    pha
    lda.l VmSourceInput_Hi
    bne Vm_SourcePlayerKeys__held
    pla
    cmp #1
    beq Vm_SourcePlayerKeys__pressed
    cmp #2
    beq Vm_SourcePlayerKeys__released
    bra Vm_SourcePlayerKeys__held_popped
Vm_SourcePlayerKeys__held:
.a16
.i16
    pla
Vm_SourcePlayerKeys__held_popped:
.a16
.i16
    lda #0
    bra Vm_SourcePlayerKeys__mode
Vm_SourcePlayerKeys__pressed:
.a16
.i16
    lda #4
    bra Vm_SourcePlayerKeys__mode
Vm_SourcePlayerKeys__released:
.a16
.i16
    lda #8
Vm_SourcePlayerKeys__mode:
.a16
.i16
    clc
    adc.l VmSourceInput_Offset
    tax
    lda.l VmSourceInput_Data,x
    sta.l VmSourceInput_Keys
    lda #2
    jsr Vm_SourceEntityArgSlot
    lda.l VmSlots_Wram,x
    and #$00FF
    cmp #BOR_VT_INTEGER
    beq Vm_SourcePlayerKeys__selector
    cmp #BOR_VT_STR
    beq Vm_SourcePlayerKeys__string
    jmp Vm_SourcePlayerKeys__zero
Vm_SourcePlayerKeys__selector:
.a16
.i16
    lda.l VmSlots_Wram+6,x
    beq Vm_SourcePlayerKeys__selector_hi
    jmp Vm_SourcePlayerKeys__zero
Vm_SourcePlayerKeys__selector_hi:
.a16
.i16
    lda.l VmSlots_Wram+4,x
    cmp #14
    bcc Vm_SourcePlayerKeys__selector_valid
    jmp Vm_SourcePlayerKeys__zero
Vm_SourcePlayerKeys__selector_valid:
.a16
.i16
    asl a
    asl a
    asl a
    asl a
    sta.l VmSourceInput_Name
    jmp Vm_SourcePlayerKeys__mask
Vm_SourcePlayerKeys__string:
.a16
.i16
    jsr Vm_SourceEntityResolveKey
    bcc Vm_SourcePlayerKeys__resolved
    jmp Vm_SourcePlayerKeys__bad
Vm_SourcePlayerKeys__resolved:
.a16
.i16
    lda #0
    sta.l VmSourceInput_Name
Vm_SourcePlayerKeys__search:
.a16
.i16
    lda.l VmSourceInput_Name
    tax
    lda.l Vm_SourceInputNames,x
    and #$00FF
    cmp.l VmNativeVariant_KeyLength
    bne Vm_SourcePlayerKeys__next
    ldy #0
Vm_SourcePlayerKeys__char:
.a16
.i16
    jsr Vm_SourceModelKeyByte
    sta.l VmNativeVariant_Char
    tya
    clc
    adc.l VmSourceInput_Name
    inc a
    tax
    lda.l Vm_SourceInputNames,x
    and #$00FF
    cmp.l VmNativeVariant_Char
    bne Vm_SourcePlayerKeys__next
    iny
    tya
    cmp.l VmNativeVariant_KeyLength
    bcc Vm_SourcePlayerKeys__char
    bra Vm_SourcePlayerKeys__mask
Vm_SourcePlayerKeys__next:
.a16
.i16
    lda.l VmSourceInput_Name
    clc
    adc #16
    sta.l VmSourceInput_Name
    cmp #224
    bcc Vm_SourcePlayerKeys__search
Vm_SourcePlayerKeys__zero:
.a16
.i16
    lda #0
    bra Vm_SourcePlayerKeys__result
Vm_SourcePlayerKeys__mask:
.a16
.i16
    lda.l VmSourceInput_Name
    clc
    adc #14
    tax
    lda.l Vm_SourceInputNames,x
    and.l VmSourceInput_Keys
Vm_SourcePlayerKeys__result:
.a16
.i16
    sta.l VmNativeVariant_Result+4
    lda #0
    sta.l VmNativeVariant_Result+2
    sta.l VmNativeVariant_Result+6
    lda #BOR_VT_INTEGER
    sta.l VmNativeVariant_Result
    clc
    rtl
Vm_SourcePlayerKeys__bad:
.a16
.i16
    sec
    lda #VMERR_BAD_NATIVE
    rtl

; X=variant slot offset. IntegerValue defaults failed conversions to zero.
; Q16 decimal conversion truncates toward zero, preserving negative fractions.
; Return A=low signed integer word, Hi=its high signed word.
Vm_SourceInputNumber:
.a16
.i16
    lda #0
    sta.l VmSourceInput_Hi
    lda.l VmSlots_Wram,x
    and #$00FF
    cmp #BOR_VT_INTEGER
    beq Vm_SourceInputNumber__integer
    cmp #BOR_VT_DECIMAL
    beq Vm_SourceInputNumber__decimal
    lda #0
    rts
Vm_SourceInputNumber__integer:
.a16
.i16
    lda.l VmSlots_Wram+6,x
    sta.l VmSourceInput_Hi
    lda.l VmSlots_Wram+4,x
    rts
Vm_SourceInputNumber__decimal:
.a16
.i16
    lda.l VmSlots_Wram+6,x
    sta.l VmSourceInput_Lo
    bpl Vm_SourceInputNumber__extend
    lda.l VmSlots_Wram+4,x
    beq Vm_SourceInputNumber__extend
    lda.l VmSourceInput_Lo
    inc a
    sta.l VmSourceInput_Lo
Vm_SourceInputNumber__extend:
.a16
.i16
    lda.l VmSourceInput_Lo
    bpl Vm_SourceInputNumber__return
    lda #$FFFF
    sta.l VmSourceInput_Hi
Vm_SourceInputNumber__return:
.a16
.i16
    lda.l VmSourceInput_Lo
    rts
