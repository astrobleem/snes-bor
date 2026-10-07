; Generic typed source entity read view. Bank 28, no bank-0 growth.
; Host world owns/publishes 80-byte V2 records; this code never aliases the
; legacy player/CharacterEntity layout. Descriptor is a script-time lease,
; not a production world allocator. Q16.16 coordinates are ACCEPTED_COMPAT.
; B48B header: opaque u32 token, alive u16, reserved u16. B5EF source-world
; header: opaque u32 token, source exists int32. Eight eight-byte variant
; properties follow: a, animationID, direction, health, playerindex, x, z,
; maxhealth (modeldata.health, not a copy of current entity health).
; Build 4086 af23dc9 openborscript.c is the property/type authority.
VmSourceEntity_Base = $7FF642
VmSourceEntity_Bank = $7FF644
VmSourceEntity_Count = $7FF646
VmSourceEntity_Ready = $7FF648 ; $B48B V2 or $B5EF source exists32 lease
VmSourceEntity_TokenLo = $7FF64A
VmSourceEntity_TokenHi = $7FF64C
VmSourceEntity_Index = $7FF64E
VmSourceEntity_Record = $7FF650
VmSourceEntity_Read = $7FF652
VmSourceEntity_Property = $7FF654

Vm_SourceEntityGet:
.a16
.i16
    lda.l VmNativeVariant_ContextValid
    cmp #$B48F
    beq Vm_SourceEntityGet__context
    jmp Vm_SourceEntityGet__bad
Vm_SourceEntityGet__context:
.a16
.i16
    lda.l VmCall_Argc
    and #$00FF
    cmp #2
    beq Vm_SourceEntityGet__args
    jmp Vm_SourceEntityGet__bad
Vm_SourceEntityGet__args:
.a16
.i16
    jsr Vm_SourceEntityLocate
    bcc Vm_SourceEntityGet__located
    rtl
Vm_SourceEntityGet__located:
.a16
.i16
    cmp #0
    bne Vm_SourceEntityGet__found
    jmp Vm_NativeVariantDispatch__null_ok
Vm_SourceEntityGet__bad:
.a16
.i16
    sec
    lda #VMERR_BAD_NATIVE
    rtl
Vm_SourceEntityGet__found:
.a16
.i16
    lda #1
    jsr Vm_SourceEntityArgSlot
    jsr Vm_SourceEntityResolveKey
    bcc Vm_SourceEntityGet__key
    jmp Vm_SourceEntityGet__bad
Vm_SourceEntityGet__key:
.a16
.i16
    lda #0
    sta.l VmNativeVariant_NameIndex
Vm_SourceEntityGet__name:
.a16
.i16
    lda.l VmNativeVariant_NameIndex
    tax
    lda.l Vm_SourceEntityNames,x
    and #$00FF
    cmp.l VmNativeVariant_KeyLength
    beq Vm_SourceEntityGet__name_length_ok
    jmp Vm_SourceEntityGet__next_name
Vm_SourceEntityGet__name_length_ok:
.a16
.i16
    ldy #0
Vm_SourceEntityGet__char:
.a16
.i16
    tya
    clc
    adc.l VmNativeVariant_NameIndex
    inc a
    tax
    lda.l Vm_SourceEntityNames,x
    and #$00FF
    sta.l VmNativeVariant_Char
    tya
    clc
    adc.l VmNativeVariant_KeyBase
    tax
    lda.l VmNativeVariant_KeyPool
    beq Vm_SourceEntityGet__literal_char
    lda.l VmStrPool_Wram,x
    bra Vm_SourceEntityGet__compare_char
Vm_SourceEntityGet__literal_char:
.a16
.i16
    lda.l VmCode_Wram,x
Vm_SourceEntityGet__compare_char:
.a16
.i16
    and #$00FF
    cmp #$0041
    bcc Vm_SourceEntityGet__lowered
    cmp #$005B
    bcs Vm_SourceEntityGet__lowered
    clc
    adc #$0020
Vm_SourceEntityGet__lowered:
.a16
.i16
    cmp.l VmNativeVariant_Char
    bne Vm_SourceEntityGet__next_name
    iny
    tya
    cmp.l VmNativeVariant_KeyLength
    bcc Vm_SourceEntityGet__char
    lda.l VmNativeVariant_NameIndex
    clc
    adc #14
    tax
    lda.l Vm_SourceEntityNames,x ; property offset and expected variant tag
    sta.l VmSourceEntity_Property
    and #$00FF
    tay
    jsr Vm_SourceEntityRead16
    sta.l VmNativeVariant_Result
    lda.l VmSourceEntity_Property
    xba
    and #$00FF
    cmp.l VmNativeVariant_Result
    beq Vm_SourceEntityGet__copy
    jmp Vm_SourceEntityGet__bad
Vm_SourceEntityGet__copy:
.a16
.i16
    iny
    iny
    jsr Vm_SourceEntityRead16
    bne Vm_SourceEntityGet__copy_bad
    sta.l VmNativeVariant_Result+2
    iny
    iny
    jsr Vm_SourceEntityRead16
    sta.l VmNativeVariant_Result+4
    iny
    iny
    jsr Vm_SourceEntityRead16
    sta.l VmNativeVariant_Result+6
    clc
    rtl
Vm_SourceEntityGet__copy_bad:
.a16
.i16
    jmp Vm_SourceEntityGet__bad
Vm_SourceEntityGet__next_name:
.a16
.i16
    lda.l VmNativeVariant_NameIndex
    clc
    adc #16
    sta.l VmNativeVariant_NameIndex
    cmp #160
    bcs Vm_SourceEntityGet__name_bad
    jmp Vm_SourceEntityGet__name
Vm_SourceEntityGet__name_bad:
.a16
.i16
    jmp Vm_SourceEntityGet__bad

; Shared checked entity lookup. A=0 null/EMPTY, A=1 found; carry set error.
; Caller validates API arity and holds the source context.
Vm_SourceEntityLocate:
.a16
.i16
    lda #0
    jsr Vm_SourceEntityArgSlot
    lda.l VmSlots_Wram,x
    and #$00FF
    bne Vm_SourceEntityLocate__ptr
    jmp Vm_SourceEntityLocate__null
Vm_SourceEntityLocate__ptr:
.a16
.i16
    cmp #BOR_VT_PTR
    beq Vm_SourceEntityLocate__token
    jmp Vm_SourceEntityLocate__bad
Vm_SourceEntityLocate__token:
.a16
.i16
    lda.l VmSlots_Wram+4,x
    sta.l VmSourceEntity_TokenLo
    ora.l VmSlots_Wram+6,x
    bne Vm_SourceEntityLocate__nonzero
    jmp Vm_SourceEntityLocate__null
Vm_SourceEntityLocate__nonzero:
.a16
.i16
    lda.l VmSlots_Wram+6,x
    sta.l VmSourceEntity_TokenHi
    lda.l VmSourceEntity_Ready
    cmp #$B48B
    beq Vm_SourceEntityLocate__lease
    cmp #$B5EF
    beq Vm_SourceEntityLocate__lease
    jmp Vm_SourceEntityLocate__bad
Vm_SourceEntityLocate__lease:
.a16
.i16
    lda.l VmSourceEntity_Bank
    and #$00FF
    cmp #$007E
    beq Vm_SourceEntityLocate__bank_ok
    cmp #$007F
    beq Vm_SourceEntityLocate__bank_ok
    cmp #$0041
    bne Vm_SourceEntityLocate__bank_bad
    ; Physical BW-RAM records belong only to the exclusive foreign pool owner.
    lda.l VmSourceWorld_Ready
    cmp #$B4A3
    bne Vm_SourceEntityLocate__bank_bad
    lda.l VmSourceEntity_Base
    cmp #$4000
    bne Vm_SourceEntityLocate__bank_bad
    lda.l VmSourceEntity_Count
    cmp.l VmSourceWorld_Count
    bne Vm_SourceEntityLocate__bank_bad
    cmp #129
    bcc Vm_SourceEntityLocate__bank_ok
Vm_SourceEntityLocate__bank_bad:
.a16
.i16
    jmp Vm_SourceEntityLocate__bad
Vm_SourceEntityLocate__bank_ok:
.a16
.i16
    lda.l VmSourceEntity_Count
    bne Vm_SourceEntityLocate__count_nonzero
    jmp Vm_SourceEntityLocate__bad
Vm_SourceEntityLocate__count_nonzero:
.a16
.i16
    cmp #513
    bcc Vm_SourceEntityLocate__count_bounded
    jmp Vm_SourceEntityLocate__bad
Vm_SourceEntityLocate__count_bounded:
.a16
.i16
    asl a
    asl a
    asl a
    asl a
    sta.l VmSourceEntity_Read ; count*16
    asl a
    asl a
    clc
    adc.l VmSourceEntity_Read ; count*80, max 512*80 fits u16
    clc
    adc.l VmSourceEntity_Base
    bcs Vm_SourceEntityLocate__bad
    lda #0
    sta.l VmSourceEntity_Index
    lda.l VmSourceEntity_Base
    sta.l VmSourceEntity_Record
Vm_SourceEntityLocate__scan:
.a16
.i16
    lda.l VmSourceEntity_Ready
    cmp #$B5EF
    beq Vm_SourceEntityLocate__source_exists
    ldy #4
    jsr Vm_SourceEntityRead16
    cmp #1
    bne Vm_SourceEntityLocate__next
    bra Vm_SourceEntityLocate__live
Vm_SourceEntityLocate__source_exists:
.a16
.i16
    ldy #4
    jsr Vm_SourceEntityRead16
    cmp #0
    bne Vm_SourceEntityLocate__live
    ldy #6
    jsr Vm_SourceEntityRead16
    cmp #0
    beq Vm_SourceEntityLocate__next
Vm_SourceEntityLocate__live:
.a16
.i16
    ldy #0
    jsr Vm_SourceEntityRead16
    cmp.l VmSourceEntity_TokenLo
    bne Vm_SourceEntityLocate__next
    ldy #2
    jsr Vm_SourceEntityRead16
    cmp.l VmSourceEntity_TokenHi
    beq Vm_SourceEntityLocate__found
Vm_SourceEntityLocate__next:
.a16
.i16
    lda.l VmSourceEntity_Index
    inc a
    sta.l VmSourceEntity_Index
    cmp.l VmSourceEntity_Count
    bcs Vm_SourceEntityLocate__bad
    lda.l VmSourceEntity_Record
    clc
    adc #80
    sta.l VmSourceEntity_Record
    bra Vm_SourceEntityLocate__scan
Vm_SourceEntityLocate__bad:
.a16
.i16
    sec
    lda #VMERR_BAD_NATIVE
    rts
Vm_SourceEntityLocate__null:
.a16
.i16
    lda #0
    clc
    rts
Vm_SourceEntityLocate__found:
.a16
.i16
    lda #1
    clc
    rts

; A = argument ordinal, X = byte offset of full variant in slot array.
Vm_SourceEntityArgSlot:
.a16
.i16
    clc
    adc.l VmCall_ArgListIndex
    asl a
    clc
    adc.l VmCall_ArgSlotsOff
    tax
    lda.l VmCode_Wram,x
    asl a
    asl a
    asl a
    tax
    rts

; Read record[Y] preserving Y and caller DBR, without borrowing direct page.
Vm_SourceEntityRead16:
.a16
.i16
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
    lda (1,s),y
    sta.l VmSourceEntity_Read
    pla
    plb
    lda.l VmSourceEntity_Read
    rts

; 16-byte records: length, 13 name bytes, source-record offset, expected tag.
Vm_SourceEntityNames:
    .db 1,"a",0,0,0,0,0,0,0,0,0,0,0,0,8,2
    .db 11,"animationid",0,0,16,1
    .db 9,"direction",0,0,0,0,24,1
    .db 6,"health",0,0,0,0,0,0,0,32,1
    .db 11,"playerindex",0,0,40,1
    .db 1,"x",0,0,0,0,0,0,0,0,0,0,0,0,48,2
    .db 1,"z",0,0,0,0,0,0,0,0,0,0,0,0,56,2
    .db 1,"y",0,0,0,0,0,0,0,0,0,0,0,0,8,2
    .db 7,"animnum",0,0,0,0,0,0,16,1
    .db 9,"maxhealth",0,0,0,0,64,1

; Resolve a complete STR variant at slot byte offset X into key scratch.
Vm_SourceEntityResolveKey:
.a16
.i16
    lda.l VmSlots_Wram,x
    and #$00FF
    cmp #BOR_VT_STR
    beq Vm_SourceEntityResolveKey__string
    jmp Vm_SourceEntityResolveKey__bad ; numeric-index locals not yet bound
Vm_SourceEntityResolveKey__string:
.a16
.i16
    lda.l VmSlots_Wram+2,x
    sta.l VmNativeVariant_KeyLength
    lda.l VmSlots_Wram+6,x
    and #$8000
    beq Vm_SourceEntityResolveKey__literal
    lda #1
    sta.l VmNativeVariant_KeyPool
    lda.l VmNativeVariant_KeyLength
    cmp #VMSTRPOOL_MAX_LEN+1
    bcc Vm_SourceEntityResolveKey__pool_length
    jmp Vm_SourceEntityResolveKey__bad
Vm_SourceEntityResolveKey__pool_length:
.a16
.i16
    lda.l VmSlots_Wram+4,x
    cmp #VMSTRPOOL_OBJ_COUNT
    bcc Vm_SourceEntityResolveKey__pool_ok
    jmp Vm_SourceEntityResolveKey__bad
Vm_SourceEntityResolveKey__pool_ok:
.a16
.i16
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    inc a
    inc a
    sta.l VmNativeVariant_KeyBase
    bra Vm_SourceEntityResolveKey__ok
Vm_SourceEntityResolveKey__literal:
.a16
.i16
    lda #0
    sta.l VmNativeVariant_KeyPool
    lda.l VmSlots_Wram+4,x
    sta.l VmNativeVariant_KeyIndex
    lda.l VmStr_StringsOff
    tax
    lda.l VmCode_Wram,x
    cmp.l VmNativeVariant_KeyIndex
    bne Vm_SourceEntityResolveKey__check_index
    jmp Vm_SourceEntityResolveKey__bad
Vm_SourceEntityResolveKey__check_index:
.a16
.i16
    bcs Vm_SourceEntityResolveKey__literal_index
    jmp Vm_SourceEntityResolveKey__bad
Vm_SourceEntityResolveKey__literal_index:
.a16
.i16
    inc a                         ; count+1 u16 offsets, after count word
    asl a
    inc a
    inc a
    clc
    adc.l VmStr_StringsOff
    sta.l VmNativeVariant_KeyBase
    lda.l VmNativeVariant_KeyIndex
    asl a
    inc a
    inc a
    clc
    adc.l VmStr_StringsOff
    tax
    lda.l VmCode_Wram,x
    clc
    adc.l VmNativeVariant_KeyBase
    sta.l VmNativeVariant_KeyBase
    clc
    adc.l VmNativeVariant_KeyLength
    cmp #VM_CODE_MAX+1
    bcc Vm_SourceEntityResolveKey__ok
    jmp Vm_SourceEntityResolveKey__bad
Vm_SourceEntityResolveKey__ok:
.a16
.i16
    clc
    rts
Vm_SourceEntityResolveKey__bad:
.a16
.i16
    sec
    rts
