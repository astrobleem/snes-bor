; Generic immutable model-name table and live loaded-model bitmap. This is
; identity lookup, not a gameplay model loader or entity allocator. The owner
; validates B4MR CRC/records before publishing the descriptor lease. findmodel
; sees only loaded models. No actor name, type or palette policy is hard-coded.
VmSourceModels_Ready = $7FF6C0     ; .dw $B4A1 checked table lease
VmSourceModels_Base = $7FF6C2
VmSourceModels_Bank = $7FF6C4      ; .db ROM bank <64
VmSourceModels_Count = $7FF6C6
VmSourceModels_Bytes = $7FF6C8
VmSourceModels_Index = $7FF6CA
VmSourceModels_Read = $7FF6CC
VmSourceModels_Offset = $7FF6CE
VmSourceModels_Char = $7FF6D0
VmSourceModels_NameIndex = $7FF6D2
VmSourceModels_Loaded = $7FF700    ; 64-byte mutable bitmap, owned by loader
VM_SOURCE_MODELS_BITMAP_BYTES = 64

Vm_SourceSpawnSetName:
.a16
.i16
    lda.l VmCall_Argc
    and #$00FF
    cmp #2
    beq Vm_SourceSpawnSetName__request
    jmp Vm_SourceSpawnSetName__bad
Vm_SourceSpawnSetName__request:
.a16
.i16
    lda.l VmSourceSpawn_Ready
    cmp #$B4E1
    beq Vm_SourceSpawnSetName__property
    jmp Vm_SourceSpawnSetName__bad
Vm_SourceSpawnSetName__property:
.a16
.i16
    lda #0
    jsr Vm_SourceEntityArgSlot
    jsr Vm_SourceEntityResolveKey
    bcc Vm_SourceSpawnSetName__key
    jmp Vm_SourceSpawnSetName__bad
Vm_SourceSpawnSetName__key:
.a16
.i16
    lda.l VmNativeVariant_KeyLength
    cmp #4
    bne Vm_SourceSpawnSetName__bad
    ldy #0
Vm_SourceSpawnSetName__key_char:
.a16
.i16
    jsr Vm_SourceModelKeyByte
    ; KeyByte uses X for backing storage; rebuild the word-table index.
    sta.l VmSourceModels_Char
    tya
    asl a
    tax
    lda.l VmSourceModels_Char
    cmp.l Vm_SourceModelNameKey,x
    bne Vm_SourceSpawnSetName__bad
    iny
    cpy #4
    bcc Vm_SourceSpawnSetName__key_char
    lda #1
    jsr Vm_SourceEntityArgSlot
    jsr Vm_SourceEntityResolveKey
    bcs Vm_SourceSpawnSetName__bad
    jsr Vm_SourceModelLookup
    bcs Vm_SourceSpawnSetName__bad
    sta.l VmSourceSpawn_Model
    lda.l VmSourceSpawn_Flags
    ora #1
    sta.l VmSourceSpawn_Flags
    ; setspawnentry returns INTEGER 1 even if findmodel returns NULL.
    lda #BOR_VT_INTEGER
    sta.l VmNativeVariant_Result
    lda #0
    sta.l VmNativeVariant_Result+2
    sta.l VmNativeVariant_Result+6
    lda #1
    sta.l VmNativeVariant_Result+4
    clc
    rtl
Vm_SourceSpawnSetName__bad:
.a16
.i16
    sec
    lda #VMERR_BAD_NATIVE
    rtl

Vm_SourceModelLookup:
.a16
.i16
    lda.l VmSourceModels_Ready
    cmp #$B4A1
    beq Vm_SourceModelLookup__descriptor
    jmp Vm_SourceModelLookup__bad
Vm_SourceModelLookup__descriptor:
.a16
.i16
    lda.l VmSourceModels_Bank
    and #$00FF
    cmp #64
    bcs Vm_SourceModelLookup__reject
    lda.l VmSourceModels_Base
    cmp #$8000
    bcc Vm_SourceModelLookup__reject
    lda.l VmSourceModels_Count
    beq Vm_SourceModelLookup__reject
    cmp #512
    bcs Vm_SourceModelLookup__reject
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    clc
    adc #24
    cmp.l VmSourceModels_Bytes
    bne Vm_SourceModelLookup__reject
    dec a
    clc
    adc.l VmSourceModels_Base
    bcs Vm_SourceModelLookup__reject
    ldy #0
    jsr Vm_SourceModelRead16
    cmp #$3442                     ; "B4"
    bne Vm_SourceModelLookup__reject
    ldy #2
    jsr Vm_SourceModelRead16
    cmp #$524D                     ; "MR"
    bne Vm_SourceModelLookup__reject
    ldy #4
    jsr Vm_SourceModelRead16
    cmp #1
    bne Vm_SourceModelLookup__reject
    ldy #6
    jsr Vm_SourceModelRead16
    cmp #64
    bne Vm_SourceModelLookup__reject
    ldy #8
    jsr Vm_SourceModelRead16
    cmp.l VmSourceModels_Count
    bne Vm_SourceModelLookup__reject
    ldy #10
    jsr Vm_SourceModelRead16
    bne Vm_SourceModelLookup__reject
    bra Vm_SourceModelLookup__body
Vm_SourceModelLookup__reject:
.a16
.i16
    jmp Vm_SourceModelLookup__bad
Vm_SourceModelLookup__body:
.a16
.i16
    ldy #12
    jsr Vm_SourceModelRead16
    clc
    adc #24
    cmp.l VmSourceModels_Bytes
    bne Vm_SourceModelLookup__reject
    ldy #14
    jsr Vm_SourceModelRead16
    bne Vm_SourceModelLookup__reject
    ldy #20
    jsr Vm_SourceModelRead16
    bne Vm_SourceModelLookup__reject
    ldy #22
    jsr Vm_SourceModelRead16
    bne Vm_SourceModelLookup__reject
    lda #0
    sta.l VmSourceModels_Index
Vm_SourceModelLookup__row:
.a16
.i16
    lda.l VmSourceModels_Index
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    clc
    adc #24
    sta.l VmSourceModels_Offset
    tay
    jsr Vm_SourceModelRead16
    cmp.l VmSourceModels_Index
    beq Vm_SourceModelLookup__identity
    brl Vm_SourceModelLookup__bad
Vm_SourceModelLookup__identity:
.a16
.i16
    iny
    iny
    jsr Vm_SourceModelRead16
    beq Vm_SourceModelLookup__row_bad
    cmp #48
    bcs Vm_SourceModelLookup__row_bad
    cmp.l VmNativeVariant_KeyLength
    beq Vm_SourceModelLookup__loaded
    brl Vm_SourceModelLookup__next
Vm_SourceModelLookup__loaded:
.a16
.i16
    lda.l VmSourceModels_Index
    and #7
    tax
    lda.l Vm_SourceModelBitMasks,x
    and #$00FF
    sta.l VmSourceModels_Char
    lda.l VmSourceModels_Index
    lsr a
    lsr a
    lsr a
    tax
    sep #$20
.a8
    lda.l VmSourceModels_Loaded,x
    rep #$20
.a16
    and #$00FF
    and.l VmSourceModels_Char
    beq Vm_SourceModelLookup__next
    lda #0
    sta.l VmSourceModels_NameIndex
Vm_SourceModelLookup__char:
.a16
.i16
    lda.l VmSourceModels_NameIndex
    clc
    adc.l VmSourceModels_Offset
    clc
    adc #16
    tay
    jsr Vm_SourceModelRead16
    and #$00FF
    sta.l VmSourceModels_Char
    lda.l VmSourceModels_NameIndex
    tay
    jsr Vm_SourceModelKeyByte
    cmp.l VmSourceModels_Char
    bne Vm_SourceModelLookup__next
    lda.l VmSourceModels_NameIndex
    inc a
    sta.l VmSourceModels_NameIndex
    cmp.l VmNativeVariant_KeyLength
    bcc Vm_SourceModelLookup__char
    lda.l VmSourceModels_Index
    clc
    rts
Vm_SourceModelLookup__row_bad:
.a16
.i16
    jmp Vm_SourceModelLookup__bad
Vm_SourceModelLookup__next:
.a16
.i16
    lda.l VmSourceModels_Index
    inc a
    sta.l VmSourceModels_Index
    cmp.l VmSourceModels_Count
    bcs Vm_SourceModelLookup__absent
    brl Vm_SourceModelLookup__row
Vm_SourceModelLookup__absent:
.a16
.i16
    lda #$FFFF                    ; absent/unloaded findmodel is NULL, not fault
    clc
    rts
Vm_SourceModelLookup__bad:
.a16
.i16
    lda #VMERR_BAD_NATIVE
    sec
    rts

; Script key byte Y, ASCII case-folded. ResolveKey checked all backing ranges.
Vm_SourceModelKeyByte:
.a16
.i16
    tya
    clc
    adc.l VmNativeVariant_KeyBase
    tax
    lda.l VmNativeVariant_KeyPool
    beq Vm_SourceModelKeyByte__literal
    lda.l VmStrPool_Wram,x
    bra Vm_SourceModelKeyByte__fold
Vm_SourceModelKeyByte__literal:
.a16
.i16
    lda.l VmCode_Wram,x
Vm_SourceModelKeyByte__fold:
.a16
.i16
    and #$00FF
    cmp #65
    bcc Vm_SourceModelKeyByte__return
    cmp #91
    bcs Vm_SourceModelKeyByte__return
    ora #$20
Vm_SourceModelKeyByte__return:
.a16
.i16
    rts

Vm_SourceModelRead16:
.a16
.i16
    phb
    lda.l VmSourceModels_Base
    pha
    sep #$20
.a8
    lda.l VmSourceModels_Bank
    pha
    plb
    rep #$20
.a16
    lda (1,s),y
    sta.l VmSourceModels_Read
    pla
    plb
    lda.l VmSourceModels_Read
    rts

Vm_SourceModelNameKey:
    .dw 110,97,109,101             ; case-folded "name", u16 per character
Vm_SourceModelBitMasks:
    .db 1,2,4,8,16,32,64,128,0
