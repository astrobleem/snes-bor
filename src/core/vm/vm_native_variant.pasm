; Generic typed source-script native boundary, outside bank 0.
; Legacy IDs <512 retain their INTEGER ABI. Source IDs >=512 return the
; complete eight-byte variant in Result. NULL and installed animation locals
; are bound; other source APIs fault until engine implementations exist.
; Result supports EMPTY/INTEGER/DECIMAL/PTR. STR requires lifetime ownership
; support before adding a dispatcher that returns it. No model alias is used.
; Scratch/context $7FF600..$7FF63B is outside earlier VM scratch $7FF50D.
VmNativeVariant_Result = $7FF600
VmNativeVariant_ContextValid = $7FF608 ; $B48F only while host owns context
VmNativeVariant_Self = $7FF610         ; four complete installed variants
VmNativeVariant_Frame = $7FF618
VmNativeVariant_AnimNum = $7FF620
VmNativeVariant_AnimHandle = $7FF628
VmNativeVariant_KeyIndex = $7FF630
VmNativeVariant_KeyBase = $7FF632
VmNativeVariant_KeyPool = $7FF634
VmNativeVariant_KeyLength = $7FF636
VmNativeVariant_NameIndex = $7FF638
VmNativeVariant_Char = $7FF63A

Vm_NativeVariantDispatch:
.a16
.i16
    rep #$30
    lda.l VmCall_TargetId
    cmp #$0201                     ; changeentityproperty, arities 3..5
    bcc Vm_NativeVariantDispatch__standard
    cmp #$0204
    bcs Vm_NativeVariantDispatch__standard
    jmp Vm_SourceEntityChange
Vm_NativeVariantDispatch__standard:
.a16
.i16
    cmp #$0205                     ; clearlocalvar(), instance-owned names
    bne Vm_NativeVariantDispatch__setlocal
    jmp Vm_SourceVarsClear
Vm_NativeVariantDispatch__setlocal:
.a16
.i16
    cmp #$0210                     ; setlocalvar(name, value)
    bne Vm_NativeVariantDispatch__builtin
    jmp Vm_SourceVarsSet
Vm_NativeVariantDispatch__builtin:
.a16
.i16
    cmp #$0200                     ; generic NULL() source API
    beq Vm_NativeVariantDispatch__null
    cmp #$0206                     ; clearspawnentry(), stable source API
    bne Vm_NativeVariantDispatch__entity
    jmp Vm_SourceSpawnClear
Vm_NativeVariantDispatch__entity:
.a16
.i16
    cmp #$0208                     ; getentityproperty(entity, property)
    bne Vm_NativeVariantDispatch__local
    jmp Vm_SourceEntityGet
Vm_NativeVariantDispatch__local:
.a16
.i16
    cmp #$0209                     ; getlocalvar(key), stable source ABI
    bne Vm_NativeVariantDispatch__spawn_name
    jmp Vm_NativeVariantGetLocal
Vm_NativeVariantDispatch__spawn_name:
.a16
.i16
    cmp #$0211                     ; setspawnentry(property,value)
    bne Vm_NativeVariantDispatch__spawn
    jmp Vm_SourceSpawnSetName
Vm_NativeVariantDispatch__spawn:
.a16
.i16
    cmp #$020B                     ; openborconstant(name or INTEGER)
    bne Vm_NativeVariantDispatch__birth
    jmp Vm_SourceConstantGet
Vm_NativeVariantDispatch__birth:
.a16
.i16
    cmp #$0212                     ; spawn(), checked source-world pool owner
    bne Vm_NativeVariantDispatch__unbound
    jmp Vm_SourceWorldSpawn
Vm_NativeVariantDispatch__unbound:
.a16
.i16
    sec
    lda #VMERR_BAD_NATIVE
    rtl
Vm_NativeVariantDispatch__null:
.a16
.i16
    lda.l VmCall_Argc
    and #$00FF
    beq Vm_NativeVariantDispatch__null_ok
    sec
    lda #VMERR_BAD_NATIVE
    rtl
Vm_NativeVariantDispatch__null_ok:
.a16
.i16
    lda #0
    sta.l VmNativeVariant_Result
    sta.l VmNativeVariant_Result+2
    sta.l VmNativeVariant_Result+4
    sta.l VmNativeVariant_Result+6
    clc
    rtl

; Installed frame locals belong to the calling script context. Self is a
; typed opaque entity pointer, never an implicit player index. An owned
; instance-variable lease selects persistent names; otherwise this bounded
; installed-context path supplies the four frame locals and absent EMPTY.
Vm_NativeVariantGetLocal:
.a16
.i16
    lda.l VmSourceVars_Ready
    beq Vm_NativeVariantGetLocal__installed
    cmp #$B4A4
    beq Vm_NativeVariantGetLocal__persistent
    jmp Vm_NativeVariantGetLocal__bad
Vm_NativeVariantGetLocal__persistent:
.a16
.i16
    jmp Vm_SourceVarsGet
Vm_NativeVariantGetLocal__installed:
.a16
.i16
    lda.l VmNativeVariant_ContextValid
    cmp #$B48F
    beq Vm_NativeVariantGetLocal__context
    jmp Vm_NativeVariantGetLocal__bad
Vm_NativeVariantGetLocal__context:
.a16
.i16
    lda.l VmCall_Argc
    and #$00FF
    cmp #1
    beq Vm_NativeVariantGetLocal__argument
    jmp Vm_NativeVariantGetLocal__bad
Vm_NativeVariantGetLocal__argument:
.a16
.i16
    lda.l VmCall_ArgListIndex
    asl a
    clc
    adc.l VmCall_ArgSlotsOff
    tax
    lda.l VmCode_Wram,x
    asl a
    asl a
    asl a
    tax
    lda.l VmSlots_Wram,x
    and #$00FF
    cmp #BOR_VT_STR
    beq Vm_NativeVariantGetLocal__string
    jmp Vm_NativeVariantGetLocal__bad ; numeric-index locals not yet bound
Vm_NativeVariantGetLocal__string:
.a16
.i16
    lda.l VmSlots_Wram+2,x
    sta.l VmNativeVariant_KeyLength
    lda.l VmSlots_Wram+6,x
    and #$8000
    beq Vm_NativeVariantGetLocal__literal
    lda #1
    sta.l VmNativeVariant_KeyPool
    lda.l VmSlots_Wram+4,x
    cmp #VMSTRPOOL_OBJ_COUNT
    bcc Vm_NativeVariantGetLocal__pool_ok
    jmp Vm_NativeVariantGetLocal__bad
Vm_NativeVariantGetLocal__pool_ok:
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
    bra Vm_NativeVariantGetLocal__search
Vm_NativeVariantGetLocal__literal:
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
    bne Vm_NativeVariantGetLocal__check_index
    jmp Vm_NativeVariantGetLocal__bad
Vm_NativeVariantGetLocal__check_index:
.a16
.i16
    bcs Vm_NativeVariantGetLocal__literal_index
    jmp Vm_NativeVariantGetLocal__bad
Vm_NativeVariantGetLocal__literal_index:
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
    bcc Vm_NativeVariantGetLocal__search
    jmp Vm_NativeVariantGetLocal__bad
Vm_NativeVariantGetLocal__search:
.a16
.i16
    lda #0
    sta.l VmNativeVariant_NameIndex
Vm_NativeVariantGetLocal__name:
.a16
.i16
    lda.l VmNativeVariant_NameIndex
    tax
    lda.l Vm_NativeVariantLocalNames,x
    and #$00FF
    cmp.l VmNativeVariant_KeyLength
    bne Vm_NativeVariantGetLocal__next
    ldy #0
Vm_NativeVariantGetLocal__char:
.a16
.i16
    tya
    clc
    adc.l VmNativeVariant_NameIndex
    inc a
    tax
    lda.l Vm_NativeVariantLocalNames,x
    and #$00FF
    sta.l VmNativeVariant_Char
    tya
    clc
    adc.l VmNativeVariant_KeyBase
    tax
    lda.l VmNativeVariant_KeyPool
    beq Vm_NativeVariantGetLocal__rom_char
    lda.l VmStrPool_Wram,x
    bra Vm_NativeVariantGetLocal__compare_char
Vm_NativeVariantGetLocal__rom_char:
.a16
.i16
    lda.l VmCode_Wram,x
Vm_NativeVariantGetLocal__compare_char:
.a16
.i16
    and #$00FF
    cmp.l VmNativeVariant_Char
    bne Vm_NativeVariantGetLocal__next
    iny
    tya
    cmp.l VmNativeVariant_KeyLength
    bcc Vm_NativeVariantGetLocal__char
    lda.l VmNativeVariant_NameIndex
    lsr a                         ; name record16 -> local record8
    tax
    lda.l VmNativeVariant_Self,x
    sta.l VmNativeVariant_Result
    lda.l VmNativeVariant_Self+2,x
    sta.l VmNativeVariant_Result+2
    lda.l VmNativeVariant_Self+4,x
    sta.l VmNativeVariant_Result+4
    lda.l VmNativeVariant_Self+6,x
    sta.l VmNativeVariant_Result+6
    clc
    rtl
Vm_NativeVariantGetLocal__next:
.a16
.i16
    lda.l VmNativeVariant_NameIndex
    clc
    adc #16
    sta.l VmNativeVariant_NameIndex
    cmp #64
    bcs Vm_NativeVariantGetLocal__absent
    jmp Vm_NativeVariantGetLocal__name
Vm_NativeVariantGetLocal__absent:
.a16
.i16
    jmp Vm_NativeVariantDispatch__null_ok ; absent named variable -> EMPTY
Vm_NativeVariantGetLocal__bad:
.a16
.i16
    sec
    lda #VMERR_BAD_NATIVE
    rtl

Vm_NativeVariantLocalNames:
    .db 4,"self",0,0,0,0,0,0,0,0,0,0,0
    .db 5,"frame",0,0,0,0,0,0,0,0,0,0
    .db 7,"animnum",0,0,0,0,0,0,0,0
    .db 10,"animhandle",0,0,0,0,0

; Called only after a successful native dispatch. Replaces the former
; bank-0 INTEGER store, freeing seven bank-0 bytes rather than growing it.
; Preserve the caller's P; all indexing uses explicit 16-bit width.
Vm_NativeVariantStore:
.a16
.i16
    php
    rep #$30
    lda.l VmPriv_B
    sta.l VmPriv_A                 ; preserve legacy observable scratch ABI
    asl a
    asl a
    asl a
    tax
    lda.l VmCall_TargetId
    cmp #$0200
    bcs Vm_NativeVariantStore__variant
    lda #BOR_VT_INTEGER
    sta.l VmSlots_Wram,x
    lda #0
    sta.l VmSlots_Wram+2,x
    lda.l VmPriv_LeftLo
    sta.l VmSlots_Wram+4,x
    lda.l VmPriv_LeftHi
    sta.l VmSlots_Wram+6,x
    plp
    rtl
Vm_NativeVariantStore__variant:
.a16
.i16
Vm_NativeVariantStore__release_begin:
.a16
.i16
    ; Source result destinations can still own a dynamic string argument.
    ; Release it before replacing the slot with EMPTY/INT/DECIMAL/PTR. Source
    ; natives returning STR remain unbound pending borrowed-result retention.
    lda.l VmPriv_B
    jsr Vm_SourceStr_ReleaseIfDynamic
Vm_NativeVariantStore__release_end:
.a16
.i16
    lda.l VmPriv_B
    asl a
    asl a
    asl a
    tax
Vm_NativeVariantStore__copy:
.a16
.i16
    lda.l VmNativeVariant_Result
    sta.l VmSlots_Wram,x
    lda.l VmNativeVariant_Result+2
    sta.l VmSlots_Wram+2,x
    lda.l VmNativeVariant_Result+4
    sta.l VmSlots_Wram+4,x
    lda.l VmNativeVariant_Result+6
    sta.l VmSlots_Wram+6,x
    plp
    rtl
