; Per-entity modeldata fallback component of pinned ent_set_model.
; B4EB leases model rows $40B000..$40B9FF (16*160) and entity rows
; $40C000..$40EFFF (128*96). Native animation cache has a separate lease.
; Cache row fields match source_model_switch_authority.FIELDS (39 int32 /
; float bit patterns); type at +156. Entity core: 18 int32 fallback fields,
; installed type +72, current MP +76, remaining 16 bytes reserved unchanged.
; Copying the old type back AFTER animation initialization belongs to the
; complete model-switch owner. This component returns it in OldTypeLo/Hi.
SourceModelEntityCopy4086_Ready = $7FFC70
SourceModelEntityCopy4086_Entities = $7FFC72
SourceModelEntityCopy4086_Models = $7FFC74
SourceModelEntityCopy4086_Slot = $7FFC76
SourceModelEntityCopy4086_Model = $7FFC78
SourceModelEntityCopy4086_View = $7FFC7A
SourceModelEntityCopy4086_Entity = $7FFC7C
SourceModelEntityCopy4086_Cache = $7FFC7E
SourceModelEntityCopy4086_Index = $7FFC80
SourceModelEntityCopy4086_OldTypeLo = $7FFC82
SourceModelEntityCopy4086_OldTypeHi = $7FFC84
SourceModelEntityCopy4086_Lo = $7FFC86
SourceModelEntityCopy4086_Hi = $7FFC88
SourceModelEntityCopy4086_Status = $7FFC8A ; 1 done,2 fault

SourceModelEntityCopy4086_Apply:
.a16
.i16
    php
    rep #$38
    phx
    phy
    lda.l SourceModelEntityCopy4086_Ready
    cmp #$B4EB
    beq SourceModelEntityCopy4086_Branch_1
    jmp SourceModelEntityCopy4086_Bad
SourceModelEntityCopy4086_Branch_1:
.a16
.i16
    lda.l VmSourceWorld_Ready
    cmp #$B4A3
    beq SourceModelEntityCopy4086_Branch_2
    jmp SourceModelEntityCopy4086_Bad
SourceModelEntityCopy4086_Branch_2:
.a16
.i16
    lda.l VmSourceWorld_PoolBase
    cmp #$4000
    beq SourceModelEntityCopy4086_Branch_3
    jmp SourceModelEntityCopy4086_Bad
SourceModelEntityCopy4086_Branch_3:
.a16
.i16
    lda.l SourceModelEntityCopy4086_Entities
    bne SourceModelEntityCopy4086_Branch_4
    jmp SourceModelEntityCopy4086_Bad
SourceModelEntityCopy4086_Branch_4:
.a16
.i16
    cmp #129
    bcc SourceModelEntityCopy4086_Branch_5
    jmp SourceModelEntityCopy4086_Bad
SourceModelEntityCopy4086_Branch_5:
.a16
.i16
    cmp.l SourceModelEntityCopy4086_Slot
    bne SourceModelEntityCopy4086_Branch_6
    jmp SourceModelEntityCopy4086_Bad
SourceModelEntityCopy4086_Branch_6:
.a16
.i16
    bcs SourceModelEntityCopy4086_Branch_7
    jmp SourceModelEntityCopy4086_Bad
SourceModelEntityCopy4086_Branch_7:
.a16
.i16
    lda.l VmSourceWorld_Count
    cmp.l SourceModelEntityCopy4086_Entities
    bcs SourceModelEntityCopy4086_Branch_8
    jmp SourceModelEntityCopy4086_Bad
SourceModelEntityCopy4086_Branch_8:
.a16
.i16
    lda.l SourceModelEntityCopy4086_Models
    bne SourceModelEntityCopy4086_Branch_9
    jmp SourceModelEntityCopy4086_Bad
SourceModelEntityCopy4086_Branch_9:
.a16
.i16
    cmp #17
    bcc SourceModelEntityCopy4086_Branch_10
    jmp SourceModelEntityCopy4086_Bad
SourceModelEntityCopy4086_Branch_10:
.a16
.i16
    cmp.l SourceModelEntityCopy4086_Model
    bne SourceModelEntityCopy4086_Branch_11
    jmp SourceModelEntityCopy4086_Bad
SourceModelEntityCopy4086_Branch_11:
.a16
.i16
    bcs SourceModelEntityCopy4086_Branch_12
    jmp SourceModelEntityCopy4086_Bad
SourceModelEntityCopy4086_Branch_12:
.a16
.i16
    lda.l SourceModelEntityCopy4086_Slot
    asl a
    asl a
    asl a
    asl a                         ; slot*16
    pha
    asl a
    asl a                         ; slot*64
    clc
    adc 1,s
    clc
    adc #$4000
    sta.l SourceModelEntityCopy4086_View
    pla
    asl a                         ; slot*32
    pha
    asl a                         ; slot*64
    clc
    adc 1,s
    clc
    adc #$C000
    sta.l SourceModelEntityCopy4086_Entity
    pla
    lda.l SourceModelEntityCopy4086_Model
    asl a
    asl a
    asl a
    asl a
    asl a                         ; model*32
    pha
    asl a
    asl a                         ; model*128
    clc
    adc 1,s
    clc
    adc #$B000
    sta.l SourceModelEntityCopy4086_Cache
    pla
    lda.l SourceModelEntityCopy4086_View
    tax
    lda.l $410020,x               ; INTEGER current health full tag/reserved
    cmp #BOR_VT_INTEGER
    beq SourceModelEntityCopy4086_Branch_13
    jmp SourceModelEntityCopy4086_Bad
SourceModelEntityCopy4086_Branch_13:
.a16
.i16
    lda.l $410022,x
    beq SourceModelEntityCopy4086_Branch_14
    jmp SourceModelEntityCopy4086_Bad
SourceModelEntityCopy4086_Branch_14:
.a16
.i16
    lda.l $410040,x               ; INTEGER model maxhealth full tag/reserved
    cmp #BOR_VT_INTEGER
    beq SourceModelEntityCopy4086_Branch_15
    jmp SourceModelEntityCopy4086_Bad
SourceModelEntityCopy4086_Branch_15:
.a16
.i16
    lda.l $410042,x
    beq SourceModelEntityCopy4086_Branch_16
    jmp SourceModelEntityCopy4086_Bad
SourceModelEntityCopy4086_Branch_16:
.a16
.i16
    lda.l VmSourceWorld_SideBase
    cmp #$6800
    beq SourceModelEntityCopy4086_SpeedPreflight
    jmp SourceModelEntityCopy4086_Bad
SourceModelEntityCopy4086_SpeedPreflight:
.a16
.i16
    jsr SourceModelEntityCopy4086_ProjectCachedSpeed
    bcc SourceModelEntityCopy4086_SpeedAdmitted
    jmp SourceModelEntityCopy4086_Bad
SourceModelEntityCopy4086_SpeedAdmitted:
.a16
.i16
    lda.l SourceModelAttackPolicy4086_Ready
    beq SourceModelEntityCopy4086_PolicyChecked
    lda.l SourceModelEntityCopy4086_Slot
    sta.l SourceModelAttackPolicy4086_Slot
    lda.l SourceModelEntityCopy4086_Model
    sta.l SourceModelAttackPolicy4086_Model
    jsl SourceModelAttackPolicy4086_Check
    bcc SourceModelEntityCopy4086_PolicyChecked
    jmp SourceModelEntityCopy4086_Bad
SourceModelEntityCopy4086_PolicyChecked:
.a16
.i16
    lda.l SourceLifecycle4086_Ready
    beq SourceModelEntityCopy4086_LifecycleDone
    lda.l SourceModelEntityCopy4086_Slot
    sta.l SourceLifecycle4086_Slot
    lda.l SourceModelEntityCopy4086_Model
    sta.l SourceLifecycle4086_Model
    lda #0
    sta.l SourceLifecycle4086_Reset
    jsl SourceLifecycle4086_Apply
    bcc SourceModelEntityCopy4086_LifecycleDone
    jmp SourceModelEntityCopy4086_Bad
SourceModelEntityCopy4086_LifecycleDone:
.a16
.i16
    lda.l SourceModelEntityCopy4086_Entity
    tax
    lda.l $400048,x
    sta.l SourceModelEntityCopy4086_OldTypeLo
    lda.l $40004A,x
    sta.l SourceModelEntityCopy4086_OldTypeHi
    lda #0
    sta.l SourceModelEntityCopy4086_Index
SourceModelEntityCopy4086_Field:
.a16
.i16
    lda.l SourceModelEntityCopy4086_Index
    asl a
    asl a
    clc
    adc.l SourceModelEntityCopy4086_Cache
    tax
    lda.l $400050,x               ; core fields start at cached FIELDS[20]
    sta.l SourceModelEntityCopy4086_Lo
    lda.l $400052,x
    sta.l SourceModelEntityCopy4086_Hi
    lda.l SourceModelEntityCopy4086_Index
    cmp #13
    bcs SourceModelEntityCopy4086_Branch_17
    jmp SourceModelEntityCopy4086_Negative
SourceModelEntityCopy4086_Branch_17:
.a16
.i16
    cmp #15
    bcs SourceModelEntityCopy4086_Branch_18
    jmp SourceModelEntityCopy4086_MinusOne
SourceModelEntityCopy4086_Branch_18:
.a16
.i16
    cmp #17
    bne SourceModelEntityCopy4086_Branch_19
    jmp SourceModelEntityCopy4086_MinusOne
SourceModelEntityCopy4086_Branch_19:
.a16
.i16
    ; Fields 15/16 are health and MP: copy old model maximum only if zero.
    lda.l SourceModelEntityCopy4086_Lo
    ora.l SourceModelEntityCopy4086_Hi
    bne SourceModelEntityCopy4086_Branch_20
    jmp SourceModelEntityCopy4086_Next
SourceModelEntityCopy4086_Branch_20:
.a16
.i16
    jmp SourceModelEntityCopy4086_Write
SourceModelEntityCopy4086_Negative:
.a16
.i16
    lda.l SourceModelEntityCopy4086_Hi
    bpl SourceModelEntityCopy4086_Branch_21
    jmp SourceModelEntityCopy4086_Next
SourceModelEntityCopy4086_Branch_21:
.a16
.i16
    jmp SourceModelEntityCopy4086_Write
SourceModelEntityCopy4086_MinusOne:
.a16
.i16
    lda.l SourceModelEntityCopy4086_Lo
    and.l SourceModelEntityCopy4086_Hi
    cmp #$FFFF
    bne SourceModelEntityCopy4086_Branch_22
    jmp SourceModelEntityCopy4086_Next
SourceModelEntityCopy4086_Branch_22:
.a16
.i16
SourceModelEntityCopy4086_Write:
.a16
.i16
    lda.l SourceModelEntityCopy4086_Index
    asl a
    asl a
    clc
    adc.l SourceModelEntityCopy4086_Entity
    tax
    lda.l SourceModelEntityCopy4086_Lo
    sta.l $400000,x
    lda.l SourceModelEntityCopy4086_Hi
    sta.l $400002,x
SourceModelEntityCopy4086_Next:
.a16
.i16
    lda.l SourceModelEntityCopy4086_Index
    inc a
    sta.l SourceModelEntityCopy4086_Index
    cmp #18
    bcs SourceModelEntityCopy4086_Branch_23
    jmp SourceModelEntityCopy4086_Field
SourceModelEntityCopy4086_Branch_23:
.a16
.i16
    lda.l SourceModelEntityCopy4086_Cache
    tax
    lda.l $40009C,x
    sta.l SourceModelEntityCopy4086_Lo
    lda.l $40009E,x
    sta.l SourceModelEntityCopy4086_Hi
    lda.l SourceModelEntityCopy4086_Entity
    tax
    lda.l SourceModelEntityCopy4086_Lo
    sta.l $400048,x
    lda.l SourceModelEntityCopy4086_Hi
    sta.l $40004A,x
    ; Source ent_copy_uninit clamps current health to the new effective max.
    lda.l $40003C,x
    sta.l SourceModelEntityCopy4086_Lo
    lda.l $40003E,x
    sta.l SourceModelEntityCopy4086_Hi
    lda.l SourceModelEntityCopy4086_View
    tax
    lda.l SourceModelEntityCopy4086_Lo
    sta.l $410044,x               ; view maxhealth value
    lda.l SourceModelEntityCopy4086_Hi
    sta.l $410046,x
    lda.l $410026,x
    jsr SourceModelEntityCopy4086_CompareHigh
    bcs SourceModelEntityCopy4086_Branch_24
    jmp SourceModelEntityCopy4086_HealthDone
SourceModelEntityCopy4086_Branch_24:
.a16
.i16
    beq SourceModelEntityCopy4086_Branch_25
    jmp SourceModelEntityCopy4086_ClampHealth
SourceModelEntityCopy4086_Branch_25:
.a16
.i16
    lda.l $410024,x
    cmp.l SourceModelEntityCopy4086_Lo
    bne SourceModelEntityCopy4086_Branch_26
    jmp SourceModelEntityCopy4086_HealthDone
SourceModelEntityCopy4086_Branch_26:
.a16
.i16
    bcs SourceModelEntityCopy4086_Branch_27
    jmp SourceModelEntityCopy4086_HealthDone
SourceModelEntityCopy4086_Branch_27:
.a16
.i16
SourceModelEntityCopy4086_ClampHealth:
.a16
.i16
    lda.l SourceModelEntityCopy4086_Lo
    sta.l $410024,x
    lda.l SourceModelEntityCopy4086_Hi
    sta.l $410026,x
SourceModelEntityCopy4086_HealthDone:
.a16
.i16
    lda.l SourceModelEntityCopy4086_Entity
    tax
    lda.l $400040,x               ; model maximum MP
    sta.l SourceModelEntityCopy4086_Lo
    lda.l $400042,x
    sta.l SourceModelEntityCopy4086_Hi
    lda.l $40004E,x               ; current MP high word
    jsr SourceModelEntityCopy4086_CompareHigh
    bcs SourceModelEntityCopy4086_Branch_28
    jmp SourceModelEntityCopy4086_Done
SourceModelEntityCopy4086_Branch_28:
.a16
.i16
    beq SourceModelEntityCopy4086_Branch_29
    jmp SourceModelEntityCopy4086_ClampMP
SourceModelEntityCopy4086_Branch_29:
.a16
.i16
    lda.l $40004C,x
    cmp.l SourceModelEntityCopy4086_Lo
    bne SourceModelEntityCopy4086_Branch_30
    jmp SourceModelEntityCopy4086_Done
SourceModelEntityCopy4086_Branch_30:
.a16
.i16
    bcs SourceModelEntityCopy4086_Branch_31
    jmp SourceModelEntityCopy4086_Done
SourceModelEntityCopy4086_Branch_31:
.a16
.i16
SourceModelEntityCopy4086_ClampMP:
.a16
.i16
    lda.l SourceModelEntityCopy4086_Lo
    sta.l $40004C,x
    lda.l SourceModelEntityCopy4086_Hi
    sta.l $40004E,x
SourceModelEntityCopy4086_Done:
.a16
.i16
    ; Re-read the same foreground-owned cached speed; no callback has run
    ; since preflight. The current modeldata movement field is side +60.
    jsr SourceModelEntityCopy4086_ProjectCachedSpeed
    bcc SourceModelEntityCopy4086_InstallSpeed
    jmp SourceModelEntityCopy4086_Bad
SourceModelEntityCopy4086_InstallSpeed:
.a16
.i16
    lda.l SourceModelEntityCopy4086_Slot
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    clc
    adc #$6800
    tax
    lda.l SourceModelEntityCopy4086_Lo
    sta.l $41003C,x
    lda.l SourceModelEntityCopy4086_Hi
    sta.l $41003E,x
    lda.l SourceLifecycle4086_Ready
    beq SourceModelEntityCopy4086_SpeedIdentityDone
    lda.l SourceModelEntityCopy4086_Cache
    tax
    lda.l $400002,x
    and #$7FFF
    ora.l $400000,x
    beq SourceModelEntityCopy4086_SpeedZero
    lda #1
    bra SourceModelEntityCopy4086_SpeedIdentity
SourceModelEntityCopy4086_SpeedZero:
.a16
.i16
    lda #0
SourceModelEntityCopy4086_SpeedIdentity:
.a16
.i16
    sta.l SourceModelEntityCopy4086_Index
    lda.l SourceModelEntityCopy4086_View
    sec
    sbc #$4000
    tax
    lda.l SourceModelEntityCopy4086_Index
    sta.l $439044,x
    lda #0
    sta.l $439046,x
    lda #$B508
    sta.l $43904C,x
SourceModelEntityCopy4086_SpeedIdentityDone:
.a16
.i16
    lda.l SourceModelAttackPolicy4086_Ready
    beq SourceModelEntityCopy4086_PolicyCopied
    jsl SourceModelAttackPolicy4086_Apply
    bcc SourceModelEntityCopy4086_PolicyCopied
    jmp SourceModelEntityCopy4086_Bad
SourceModelEntityCopy4086_PolicyCopied:
.a16
.i16
    lda #1
    sta.l SourceModelEntityCopy4086_Status
    ply
    plx
    plp
    clc
    rtl
SourceModelEntityCopy4086_Bad:
.a16
.i16
    lda #2
    sta.l SourceModelEntityCopy4086_Status
    ply
    plx
    plp
    sec
    rtl

; Signed int32 high-word ordering, exposing C and Z to the caller. Preserve X.
SourceModelEntityCopy4086_CompareHigh:
.a16
.i16
    eor #$8000
    pha
    lda.l SourceModelEntityCopy4086_Hi
    eor #$8000
    sta.l SourceModelEntityCopy4086_Hi
    pla
    cmp.l SourceModelEntityCopy4086_Hi
    php
    lda.l SourceModelEntityCopy4086_Hi
    eor #$8000
    sta.l SourceModelEntityCopy4086_Hi
    plp
    rts

; Pure binary32 -> Q16.16 compatibility projection. Input/output Lo/Hi;
; Index is synchronous scratch. Does not touch entities, cached models or
; any pending owner. C=1 rejects NaN/Inf or |speed| >=32768 before input writes.
; Signed zero projects to integer zero. This is not source float arithmetic.
SourceModelSpeed4086_ProjectQ16:
.a16
.i16
    php
    rep #$38
    phx
    phy
    lda.l SourceModelEntityCopy4086_Hi
    and #$8000
    pha
    lda.l SourceModelEntityCopy4086_Hi
    and #$7F80
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    cmp #142
    bcc SourceModelSpeed4086_Domain
    jmp SourceModelSpeed4086_Reject
SourceModelSpeed4086_Domain:
.a16
.i16
    cmp #111
    bcs SourceModelSpeed4086_Normal
    lda #0
    sta.l SourceModelEntityCopy4086_Lo
    sta.l SourceModelEntityCopy4086_Hi
    pla
    jmp SourceModelSpeed4086_Done
SourceModelSpeed4086_Normal:
.a16
.i16
    sta.l SourceModelEntityCopy4086_Index
    lda.l SourceModelEntityCopy4086_Hi
    and #$007F
    ora #$0080
    sta.l SourceModelEntityCopy4086_Hi
    lda.l SourceModelEntityCopy4086_Index
    cmp #134
    bcc SourceModelSpeed4086_RightCount
    sec
    sbc #134
    tay
    beq SourceModelSpeed4086_Sign
SourceModelSpeed4086_Left:
.a16
.i16
    lda.l SourceModelEntityCopy4086_Lo
    asl a
    sta.l SourceModelEntityCopy4086_Lo
    lda.l SourceModelEntityCopy4086_Hi
    rol a
    sta.l SourceModelEntityCopy4086_Hi
    dey
    bne SourceModelSpeed4086_Left
    bra SourceModelSpeed4086_Sign
SourceModelSpeed4086_RightCount:
.a16
.i16
    lda #134
    sec
    sbc.l SourceModelEntityCopy4086_Index
    tay
SourceModelSpeed4086_Right:
.a16
.i16
    lda.l SourceModelEntityCopy4086_Hi
    lsr a
    sta.l SourceModelEntityCopy4086_Hi
    lda.l SourceModelEntityCopy4086_Lo
    ror a
    sta.l SourceModelEntityCopy4086_Lo
    dey
    bne SourceModelSpeed4086_Right
SourceModelSpeed4086_Sign:
.a16
.i16
    pla
    bpl SourceModelSpeed4086_Done
    lda.l SourceModelEntityCopy4086_Lo
    eor #$FFFF
    clc
    adc #1
    sta.l SourceModelEntityCopy4086_Lo
    lda.l SourceModelEntityCopy4086_Hi
    eor #$FFFF
    adc #0
    sta.l SourceModelEntityCopy4086_Hi
SourceModelSpeed4086_Done:
.a16
.i16
    ply
    plx
    plp
    clc
    rtl
SourceModelSpeed4086_Reject:
.a16
.i16
    pla
    ply
    plx
    plp
    sec
    rtl

SourceModelEntityCopy4086_ProjectCachedSpeed:
.a16
.i16
    lda.l SourceModelEntityCopy4086_Cache
    tax
    lda.l $400000,x
    sta.l SourceModelEntityCopy4086_Lo
    lda.l $400002,x
    sta.l SourceModelEntityCopy4086_Hi
    jsl SourceModelSpeed4086_ProjectQ16
    rts
