; Opt-in exclusive foreign-world birth pool. No original-BOR slot alias and
; no automatic gameplay activation. The owner validates templates/CRC, stable
; tokens, reserved bytes and physical BW-RAM ownership before granting B4A3.
; Only compiler-admitted TYPE_NONE idle initializers without initial callbacks
; or frame/environment effects can execute. Other model policies fault.
VmSourceWorld_Ready = $7FF740
VmSourceWorld_Level = $7FF742
VmSourceWorld_PoolBase = $7FF744
VmSourceWorld_SideBase = $7FF746
VmSourceWorld_Count = $7FF748
VmSourceWorld_TemplateBase = $7FF74A
VmSourceWorld_TemplateBank = $7FF74C
VmSourceWorld_TemplateCount = $7FF74E
VmSourceWorld_TemplateBytes = $7FF750
VmSourceWorld_Time = $7FF752
VmSourceWorld_Model = $7FF756
VmSourceWorld_Index = $7FF758
VmSourceWorld_Row = $7FF75A
VmSourceWorld_ViewOffset = $7FF75C
VmSourceWorld_SideOffset = $7FF75E
VmSourceWorld_Read = $7FF760
VmSourceWorld_TokenLo = $7FF762
VmSourceWorld_TokenHi = $7FF764
VmSourceWorld_HealthLo = $7FF766
VmSourceWorld_HealthHi = $7FF768
VmSourceWorld_Players = $7FF76A
VmSourceWorld_AdvanceX = $7FF76C   ; Q16.16, ACCEPTED_COMPAT
VmSourceWorld_AdvanceY = $7FF770
VmSourceWorld_ScrollAxis = $7FF774 ; 0=horizontal, 1=inward/outward
SOURCE_WORLD_POOL = $414000
SOURCE_WORLD_SIDES = $416800
SOURCE_WORLD_CAPACITY = 128
SOURCE_WORLD_VIEW_STRIDE = 80
SOURCE_WORLD_SIDE_STRIDE = 64

Vm_SourceWorldSpawn:
.a16
.i16
    lda.l VmCall_Argc
    and #$00FF
    bne Vm_SourceWorldBranch_1
    jmp Vm_SourceWorldSpawn__owner
Vm_SourceWorldBranch_1:
.a16
.i16
    jmp Vm_SourceWorldSpawn__bad
Vm_SourceWorldSpawn__owner:
.a16
.i16
    lda.l VmSourceWorld_Ready
    cmp #$B4A3
    bne Vm_SourceWorldBranch_2
    jmp Vm_SourceWorldSpawn__level
Vm_SourceWorldBranch_2:
.a16
.i16
    jmp Vm_SourceWorldSpawn__bad
Vm_SourceWorldSpawn__level:
.a16
.i16
    lda.l VmSourceWorld_Level
    cmp #0
    beq Vm_SourceWorldBranch_3
    jmp Vm_SourceWorldSpawn__present
Vm_SourceWorldBranch_3:
.a16
.i16
    jmp Vm_NativeVariantDispatch__null_ok
Vm_SourceWorldSpawn__present:
.a16
.i16
    cmp #1
    bne Vm_SourceWorldBranch_4
    jmp Vm_SourceWorldSpawn__request
Vm_SourceWorldBranch_4:
.a16
.i16
    jmp Vm_SourceWorldSpawn__bad
Vm_SourceWorldSpawn__request:
.a16
.i16
    lda.l VmSourceSpawn_Ready
    cmp #$B4E1
    beq Vm_SourceWorldBranch_5
    jmp Vm_SourceWorldSpawn__bad
Vm_SourceWorldBranch_5:
.a16
.i16
    lda.l VmSourceSpawn_Flags
    and #$FFFE                    ; currently only checked name setter bound
    beq Vm_SourceWorldBranch_6
    jmp Vm_SourceWorldSpawn__bad
Vm_SourceWorldBranch_6:
.a16
.i16
    lda.l VmSourceSpawn_Model
    cmp #$FFFF
    beq Vm_SourceWorldBranch_7
    jmp Vm_SourceWorldSpawn__model
Vm_SourceWorldBranch_7:
.a16
.i16
    jmp Vm_NativeVariantDispatch__null_ok
Vm_SourceWorldSpawn__model:
.a16
.i16
    cmp.l VmSourceWorld_TemplateCount
    bcc Vm_SourceWorldBranch_8
    jmp Vm_SourceWorldSpawn__bad
Vm_SourceWorldBranch_8:
.a16
.i16
    sta.l VmSourceWorld_Model
    jsr Vm_SourceWorldValidate
    bcs Vm_SourceWorldBranch_9
    jmp Vm_SourceWorldSpawn__table
Vm_SourceWorldBranch_9:
.a16
.i16
    rtl
Vm_SourceWorldSpawn__bad:
.a16
.i16
    sec
    lda #VMERR_BAD_NATIVE
    rtl
Vm_SourceWorldSpawn__table:
.a16
.i16
    lda.l VmSourceWorld_TemplateBase
    clc
    adc #24
    sta.l VmSourceWorld_Row
    lda.l VmSourceWorld_Model
    asl a
    asl a
    asl a
    asl a
    asl a                         ; model*32
    sta.l VmSourceWorld_Read
    asl a
    asl a                         ; model*128
    clc
    adc.l VmSourceWorld_Read
    clc
    adc.l VmSourceWorld_Row
    sta.l VmSourceWorld_Row
    ldy #0
    jsr Vm_SourceWorldTemplateRead
    cmp.l VmSourceWorld_Model
    beq Vm_SourceWorldBranch_10
    jmp Vm_SourceWorldSpawn__bad
Vm_SourceWorldBranch_10:
.a16
.i16
    ldy #2
    jsr Vm_SourceWorldTemplateRead
    cmp #1                         ; admitted generic TYPE_NONE idle initializer
    beq Vm_SourceWorldBranch_11
    jmp Vm_SourceWorldSpawn__bad
Vm_SourceWorldBranch_11:
.a16
.i16
    lda #0
    sta.l VmSourceWorld_Index
    sta.l VmSourceWorld_ViewOffset
    sta.l VmSourceWorld_SideOffset
Vm_SourceWorldSpawn__scan:
.a16
.i16
    lda.l SourceWorldTick4086_Ready
    cmp #$B4D5
    bne Vm_SourceWorldSpawn__physical_scan
    jsr Vm_SourceWorldOrderSlot
    bcc Vm_SourceWorldSpawn__physical_scan
    jmp Vm_SourceWorldSpawn__bad
Vm_SourceWorldSpawn__physical_scan:
.a16
.i16
    lda.l VmSourceWorld_ViewOffset
    tax
    lda.l SOURCE_WORLD_POOL+4,x
    cmp #0
    bne Vm_SourceWorldBranch_12
    jmp Vm_SourceWorldSpawn__free
Vm_SourceWorldBranch_12:
.a16
.i16
    cmp #1
    beq Vm_SourceWorldBranch_13
    jmp Vm_SourceWorldSpawn__bad
Vm_SourceWorldBranch_13:
.a16
.i16
    lda.l VmSourceWorld_Index
    inc a
    sta.l VmSourceWorld_Index
    cmp.l VmSourceWorld_Count
    bcs Vm_SourceWorldBranch_14
    jmp Vm_SourceWorldSpawn__advance
Vm_SourceWorldBranch_14:
.a16
.i16
    jmp Vm_NativeVariantDispatch__null_ok ; source allocation failure is EMPTY
Vm_SourceWorldSpawn__advance:
.a16
.i16
    lda.l SourceWorldTick4086_Ready
    cmp #$B4D5
    bne Vm_SourceWorldSpawn__advance_physical
    jmp Vm_SourceWorldSpawn__scan
Vm_SourceWorldSpawn__advance_physical:
.a16
.i16
    lda.l VmSourceWorld_ViewOffset
    clc
    adc #SOURCE_WORLD_VIEW_STRIDE
    sta.l VmSourceWorld_ViewOffset
    lda.l VmSourceWorld_SideOffset
    clc
    adc #SOURCE_WORLD_SIDE_STRIDE
    sta.l VmSourceWorld_SideOffset
    bra Vm_SourceWorldSpawn__scan
Vm_SourceWorldSpawn__free:
.a16
.i16
    lda.l SOURCE_WORLD_POOL+6,x
    bne Vm_SourceWorldBranch_15
    jmp Vm_SourceWorldSpawn__token
Vm_SourceWorldBranch_15:
.a16
.i16
    jmp Vm_SourceWorldSpawn__bad
Vm_SourceWorldSpawn__token:
.a16
.i16
    lda.l SOURCE_WORLD_POOL,x
    sta.l VmSourceWorld_TokenLo
    lda.l SOURCE_WORLD_POOL+2,x
    sta.l VmSourceWorld_TokenHi
    ora.l VmSourceWorld_TokenLo
    beq Vm_SourceWorldBranch_16
    jmp Vm_SourceWorldSpawn__copy
Vm_SourceWorldBranch_16:
.a16
.i16
    jmp Vm_SourceWorldSpawn__bad
Vm_SourceWorldSpawn__copy:
.a16
.i16
    ldy #16                        ; template view payload, 72 bytes
Vm_SourceWorldSpawn__view:
.a16
.i16
    jsr Vm_SourceWorldTemplateRead
    sta.l VmSourceWorld_Read
    tya
    sec
    sbc #8                         ; template16 maps to view8
    clc
    adc.l VmSourceWorld_ViewOffset
    tax
    lda.l VmSourceWorld_Read
    sta.l SOURCE_WORLD_POOL,x
    iny
    iny
    cpy #88
    bcs Vm_SourceWorldBranch_17
    jmp Vm_SourceWorldSpawn__view
Vm_SourceWorldBranch_17:
.a16
.i16
Vm_SourceWorldSpawn__side:
.a16
.i16
    jsr Vm_SourceWorldTemplateRead
    sta.l VmSourceWorld_Read
    tya
    sec
    sbc #88
    clc
    adc.l VmSourceWorld_SideOffset
    tax
    lda.l VmSourceWorld_Read
    sta.l SOURCE_WORLD_SIDES,x
    iny
    iny
    cpy #152
    bcs Vm_SourceWorldBranch_18
    jmp Vm_SourceWorldSpawn__side
Vm_SourceWorldBranch_18:
.a16
.i16
    lda.l VmSourceWorld_SideOffset
    tax
    lda.l VmSourceWorld_Time
    sta.l SOURCE_WORLD_SIDES+12,x   ; birth timestamp
    lda.l VmSourceWorld_Time+2
    sta.l SOURCE_WORLD_SIDES+14,x
    lda.l VmSourceWorld_Time
    clc
    adc #1
    sta.l SOURCE_WORLD_SIDES+20,x   ; nextthink=time+1
    sta.l SOURCE_WORLD_SIDES+24,x   ; nextmove=time+1
    lda.l VmSourceWorld_Time+2
    adc #0
    sta.l SOURCE_WORLD_SIDES+22,x
    sta.l SOURCE_WORLD_SIDES+26,x
    lda.l VmSourceWorld_Time
    clc
    adc.l SOURCE_WORLD_SIDES+56,x   ; first calculate_edelay, compiler admitted
    sta.l SOURCE_WORLD_SIDES+8,x
    lda.l VmSourceWorld_Time+2
    adc.l SOURCE_WORLD_SIDES+58,x
    sta.l SOURCE_WORLD_SIDES+10,x
    ; smartspawn starts at request origin plus the level's scrolling advance.
    lda.l VmSourceWorld_ViewOffset
    tax
    lda.l VmSourceWorld_ScrollAxis
    beq Vm_SourceWorldBranch_19
    jmp Vm_SourceWorldSpawn__vertical
Vm_SourceWorldBranch_19:
.a16
.i16
    lda.l VmSourceWorld_AdvanceX
    sta.l SOURCE_WORLD_POOL+52,x
    lda.l VmSourceWorld_AdvanceX+2
    sta.l SOURCE_WORLD_POOL+54,x
    bra Vm_SourceWorldSpawn__publish
Vm_SourceWorldSpawn__vertical:
.a16
.i16
    lda.l VmSourceWorld_AdvanceY
    sta.l SOURCE_WORLD_POOL+60,x
    lda.l VmSourceWorld_AdvanceY+2
    sta.l SOURCE_WORLD_POOL+62,x
Vm_SourceWorldSpawn__publish:
.a16
.i16
    lda.l SourceToss4086_Ready
    cmp #$B4E2
    bne Vm_SourceWorldSpawn__publish_alive
    lda.l VmSourceWorld_SideOffset
    lsr a
    lsr a
    lsr a
    lsr a                         ; physical slot*4 in extended toss-time array
    tax
    lda #0
    sta.l SOURCE_WORLD_TOSS_TIMES,x
    sta.l SOURCE_WORLD_TOSS_TIMES+2,x
Vm_SourceWorldSpawn__publish_alive:
.a16
.i16
    jsl SourceUpdateFrame4086_InitializeBirth
    lda.l VmSourceWorld_ViewOffset
    tax
    lda #1
    sta.l SOURCE_WORLD_POOL+4,x     ; publish only after complete initialization
    lda.l SourceWorldTick4086_Ready
    cmp #$B4D5
    bne Vm_SourceWorldSpawn__return_token
    jsr SourceWorldTick4086_CountLive
    lda.l SourceWorldTick4086_Live
    cmp.l SourceWorldTick4086_Maximum
    bcc Vm_SourceWorldSpawn__return_token
    sta.l SourceWorldTick4086_Maximum
Vm_SourceWorldSpawn__return_token:
.a16
.i16
    lda #BOR_VT_PTR
    sta.l VmNativeVariant_Result
    lda #0
    sta.l VmNativeVariant_Result+2
    lda.l VmSourceWorld_TokenLo
    sta.l VmNativeVariant_Result+4
    lda.l VmSourceWorld_TokenHi
    sta.l VmNativeVariant_Result+6
    clc
    rtl

; The live world's pointer permutation is authoritative for free-slot choice.
; The opt-out path above retains the original independent birth fixture ABI.
Vm_SourceWorldOrderSlot:
.a16
.i16
    lda.l VmSourceWorld_Index
    asl a
    tax
    lda.l SOURCE_TARGET_ORDER,x
    cmp.l VmSourceWorld_Count
    bcs Vm_SourceWorldOrderSlot__bad
    asl a
    asl a
    asl a
    asl a
    sta.l VmSourceWorld_Read
    asl a
    asl a
    sta.l VmSourceWorld_SideOffset
    clc
    adc.l VmSourceWorld_Read
    sta.l VmSourceWorld_ViewOffset
    clc
    rts
Vm_SourceWorldOrderSlot__bad:
.a16
.i16
    sec
    rts

Vm_SourceWorldValidate:
.a16
.i16
    lda.l VmSourceWorld_PoolBase
    cmp #$4000
    beq Vm_SourceWorldBranch_20
    jmp Vm_SourceWorldValidate__bad
Vm_SourceWorldBranch_20:
.a16
.i16
    lda.l VmSourceWorld_SideBase
    cmp #$6800
    beq Vm_SourceWorldBranch_21
    jmp Vm_SourceWorldValidate__bad
Vm_SourceWorldBranch_21:
.a16
.i16
    lda.l VmSourceWorld_Count
    bne Vm_SourceWorldBranch_22
    jmp Vm_SourceWorldValidate__bad
Vm_SourceWorldBranch_22:
.a16
.i16
    cmp #129
    bcc Vm_SourceWorldBranch_23
    jmp Vm_SourceWorldValidate__bad
Vm_SourceWorldBranch_23:
.a16
.i16
    lda.l VmSourceWorld_TemplateCount
    bne Vm_SourceWorldBranch_24
    jmp Vm_SourceWorldValidate__bad
Vm_SourceWorldBranch_24:
.a16
.i16
    cmp #129
    bcc Vm_SourceWorldBranch_25
    jmp Vm_SourceWorldValidate__bad
Vm_SourceWorldBranch_25:
.a16
.i16
    lda.l VmSourceWorld_Players
    bne Vm_SourceWorldBranch_26
    jmp Vm_SourceWorldValidate__bad
Vm_SourceWorldBranch_26:
.a16
.i16
    cmp #5
    bcc Vm_SourceWorldBranch_27
    jmp Vm_SourceWorldValidate__bad
Vm_SourceWorldBranch_27:
.a16
.i16
    lda.l VmSourceWorld_ScrollAxis
    cmp #2
    bcc Vm_SourceWorldBranch_28
    jmp Vm_SourceWorldValidate__bad
Vm_SourceWorldBranch_28:
.a16
.i16
    lda.l VmSourceWorld_TemplateBank
    and #$00FF
    cmp #64
    bcc Vm_SourceWorldBranch_29
    jmp Vm_SourceWorldValidate__bad
Vm_SourceWorldBranch_29:
.a16
.i16
    lda.l VmSourceWorld_TemplateBase
    cmp #$8000
    bcs Vm_SourceWorldBranch_30
    jmp Vm_SourceWorldValidate__bad
Vm_SourceWorldBranch_30:
.a16
.i16
    sta.l VmSourceWorld_Row
    lda.l VmSourceWorld_TemplateCount
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l VmSourceWorld_Read
    asl a
    asl a
    clc
    adc.l VmSourceWorld_Read
    clc
    adc #24
    cmp.l VmSourceWorld_TemplateBytes
    beq Vm_SourceWorldBranch_31
    jmp Vm_SourceWorldValidate__bad
Vm_SourceWorldBranch_31:
.a16
.i16
    dec a                         ; last byte, bank boundary inclusive
    clc
    adc.l VmSourceWorld_TemplateBase
    bcc Vm_SourceWorldBranch_32
    jmp Vm_SourceWorldValidate__bad
Vm_SourceWorldBranch_32:
.a16
.i16
    ldy #0
    jsr Vm_SourceWorldTemplateRead
    cmp #$3442                    ; B4
    beq Vm_SourceWorldBranch_33
    jmp Vm_SourceWorldValidate__bad
Vm_SourceWorldBranch_33:
.a16
.i16
    ldy #2
    jsr Vm_SourceWorldTemplateRead
    cmp #$5442                    ; BT
    beq Vm_SourceWorldBranch_34
    jmp Vm_SourceWorldValidate__bad
Vm_SourceWorldBranch_34:
.a16
.i16
    ldy #4
    jsr Vm_SourceWorldTemplateRead
    cmp #1
    beq Vm_SourceWorldBranch_35
    jmp Vm_SourceWorldValidate__bad
Vm_SourceWorldBranch_35:
.a16
.i16
    ldy #6
    jsr Vm_SourceWorldTemplateRead
    cmp #160
    beq Vm_SourceWorldBranch_36
    jmp Vm_SourceWorldValidate__bad
Vm_SourceWorldBranch_36:
.a16
.i16
    ldy #8
    jsr Vm_SourceWorldTemplateRead
    cmp.l VmSourceWorld_TemplateCount
    beq Vm_SourceWorldBranch_37
    jmp Vm_SourceWorldValidate__bad
Vm_SourceWorldBranch_37:
.a16
.i16
    ldy #10
    jsr Vm_SourceWorldTemplateRead
    cmp #0
    beq Vm_SourceWorldBranch_38
    jmp Vm_SourceWorldValidate__bad
Vm_SourceWorldBranch_38:
.a16
.i16
    clc
    rts
Vm_SourceWorldValidate__bad:
.a16
.i16
    sec
    lda #VMERR_BAD_NATIVE
    rts

Vm_SourceWorldTemplateRead:
.a16
.i16
    phb
    lda.l VmSourceWorld_Row
    pha
    sep #$20
.a8
    lda.l VmSourceWorld_TemplateBank
    pha
    plb
    rep #$20
.a16
    lda (1,s),y
    sta.l VmSourceWorld_Read
    pla
    plb
    lda.l VmSourceWorld_Read
    rts
