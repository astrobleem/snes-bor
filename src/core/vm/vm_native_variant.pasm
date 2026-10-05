; Generic typed source-script native boundary, outside bank 0.
; Legacy IDs <512 retain their INTEGER ABI. Source IDs >=512 return the
; complete eight-byte variant in Result. Currently NULL only is bound;
; every other source API faults until its engine implementation is present.
; Result supports EMPTY/INTEGER/DECIMAL/PTR. STR requires lifetime ownership
; support before adding a dispatcher that returns it. No model alias is used.
; Scratch $7FF600..$7FF607 is outside existing VM scratch ending $7FF50D.
VmNativeVariant_Result = $7FF600

Vm_NativeVariantDispatch:
.a16
.i16
    rep #$30
    lda.l VmCall_TargetId
    cmp #$0200                     ; generic NULL() source API
    beq Vm_NativeVariantDispatch__null
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
