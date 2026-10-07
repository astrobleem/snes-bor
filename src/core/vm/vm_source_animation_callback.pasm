; Non-recursive foreground execute_animation_script owner. B4CO identities are
; compiler derived. The installer validates model/code/metadata/dispatch CRCs
; together before granting B4E6; no actor-name branch exists in this owner.
; Begin captures current/default program pointers and installs locals ONCE.
; Run resumes the current/default VM through cooperative yields, then clears
; the boundary ONCE. After the current script, default eligibility is checked
; against the CURRENT model/defaultmodel IDs, as in pinned engine authority.
; The caller acknowledges update_frame's SCRIPT service only after DONE.
; Nested engine-triggered execution remains an explicit separate capability.
SourceAnimationCallback4086_Ready = $7FFC00
SourceAnimationCallback4086_State = $7FFC02 ; 0 idle,1 current,2 default,3 done,4 fault
SourceAnimationCallback4086_Status = $7FFC04
SourceAnimationCallback4086_Fault = $7FFC06
SourceAnimationCallback4086_Base = $7FFC08
SourceAnimationCallback4086_Bank = $7FFC0A
SourceAnimationCallback4086_Bytes = $7FFC0C
SourceAnimationCallback4086_Models = $7FFC0E
SourceAnimationCallback4086_Programs = $7FFC10
SourceAnimationCallback4086_MetadataBytes = $7FFC12
SourceAnimationCallback4086_CurrentRow = $7FFC14
SourceAnimationCallback4086_DefaultRow = $7FFC16
SourceAnimationCallback4086_CurrentModel = $7FFC18
SourceAnimationCallback4086_DefaultModel = $7FFC1A
SourceAnimationCallback4086_InitSource = $7FFC1C
SourceAnimationCallback4086_InitTarget = $7FFC1E
SourceAnimationCallback4086_InitWords = $7FFC20
SourceAnimationCallback4086_SelectedRow = $7FFC22
SourceAnimationCallback4086_Temporary = $7FFC24
SourceAnimationCallback4086_SelectedModel = $7FFC26
SourceAnimationCallback4086_Program = $7FFC28
SourceAnimationCallback4086_SlotBase = $7FFC2A
SourceAnimationCallback4086_Slots = $7FFC2C
SourceAnimationCallback4086_Initializers = $7FFC2E
SourceAnimationCallback4086_ScratchEnd = $7FFC30

SourceAnimationCallback4086_Begin:
.a16
.i16
    php
    rep #$38
    phx
    phy
    lda.l SourceAnimationCallback4086_Ready
    cmp #$B4E6
    beq SourceAnimationCallback4086_Branch_1
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_1:
.a16
.i16
    lda.l SourceAnimationCallback4086_State
    bne SourceAnimationCallback4086_Branch_2
    jmp SourceAnimationCallback4086_Begin__idle
SourceAnimationCallback4086_Branch_2:
.a16
.i16
    cmp #3
    beq SourceAnimationCallback4086_Branch_3
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_3:
.a16
.i16
SourceAnimationCallback4086_Begin__idle:
.a16
.i16
    lda.l VmSourceCallback_Active
    beq SourceAnimationCallback4086_Branch_4
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_4:
.a16
.i16
    lda.l SourceVMRun4086_Busy
    beq SourceAnimationCallback4086_Branch_5
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_5:
.a16
.i16
    lda.l VmState_Status
    and #$00FF
    cmp #VMSTAT_RUNNING
    bne SourceAnimationCallback4086_Branch_6
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_6:
.a16
.i16
    cmp #VMSTAT_YIELDED
    bne SourceAnimationCallback4086_Branch_7
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_7:
.a16
.i16
    cmp #VMSTAT_FAULT
    bne SourceAnimationCallback4086_Branch_8
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_8:
.a16
.i16
    lda.l SourceUpdateFrame4086_Ready
    cmp #$B4E3
    beq SourceAnimationCallback4086_Branch_9
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_9:
.a16
.i16
    lda.l SourceUpdateFrame4086_State
    cmp #1
    beq SourceAnimationCallback4086_Branch_10
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_10:
.a16
.i16
    lda.l SourceUpdateFrame4086_Pending
    cmp #1
    beq SourceAnimationCallback4086_Branch_11
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_11:
.a16
.i16
    lda.l VmSourceFrame_Ready
    cmp #$B4FD
    beq SourceAnimationCallback4086_Branch_12
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_12:
.a16
.i16
    lda.l VmSourceInstr_Ready
    cmp #$B48E
    beq SourceAnimationCallback4086_Branch_13
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_13:
.a16
.i16
    lda.l SourceVMRun4086_Ready
    cmp #$B4D7
    beq SourceAnimationCallback4086_Branch_14
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_14:
.a16
.i16
    lda.l SourceAnimationCallback4086_Base
    cmp #$8000
    bcs SourceAnimationCallback4086_Branch_15
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_15:
.a16
.i16
    lda.l SourceAnimationCallback4086_Bank
    cmp #64
    bcc SourceAnimationCallback4086_Branch_16
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_16:
.a16
.i16
    lda.l SourceAnimationCallback4086_Bytes
    cmp #48
    bcs SourceAnimationCallback4086_Branch_17
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_17:
.a16
.i16
    clc
    adc.l SourceAnimationCallback4086_Base
    bcc SourceAnimationCallback4086_Branch_18
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_18:
.a16
.i16
    lda.l SourceAnimationCallback4086_Base
    tax
    jsr SourceAnimationCallback4086_Read
    cmp #$3442
    beq SourceAnimationCallback4086_Branch_19
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_19:
.a16
.i16
    inx
    inx
    jsr SourceAnimationCallback4086_Read
    cmp #$4F43
    beq SourceAnimationCallback4086_Branch_20
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_20:
.a16
.i16
    inx
    inx
    jsr SourceAnimationCallback4086_Read
    cmp #1
    beq SourceAnimationCallback4086_Branch_21
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_21:
.a16
.i16
    inx
    inx
    jsr SourceAnimationCallback4086_Read
    cmp #16
    beq SourceAnimationCallback4086_Branch_22
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_22:
.a16
.i16
    inx
    inx
    jsr SourceAnimationCallback4086_Read
    bne SourceAnimationCallback4086_Branch_23
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_23:
.a16
.i16
    cmp #512
    bcc SourceAnimationCallback4086_Branch_24
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_24:
.a16
.i16
    sta.l SourceAnimationCallback4086_Models
    cmp.l VmSourceModels_Count
    beq SourceAnimationCallback4086_Branch_25
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_25:
.a16
.i16
    asl a
    asl a
    asl a
    asl a
    clc
    adc #32
    cmp.l SourceAnimationCallback4086_Bytes
    beq SourceAnimationCallback4086_Branch_26
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_26:
.a16
.i16
    inx
    inx
    jsr SourceAnimationCallback4086_Read
    cmp.l VmSourceFrame_Programs
    beq SourceAnimationCallback4086_Branch_27
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_27:
.a16
.i16
    sta.l SourceAnimationCallback4086_Programs
    inx
    inx
    jsr SourceAnimationCallback4086_Read
    bne SourceAnimationCallback4086_Branch_28
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_28:
.a16
.i16
    cmp #17761
    bcc SourceAnimationCallback4086_Branch_29
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_29:
.a16
.i16
    sta.l SourceAnimationCallback4086_MetadataBytes
    inx
    inx
    jsr SourceAnimationCallback4086_Read
    beq SourceAnimationCallback4086_Branch_30
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_30:
.a16
.i16
    lda.l SourceUpdateFrame4086_Side
    tax
    lda.l $410000,x
    sta.l SourceAnimationCallback4086_CurrentModel
    jsr SourceAnimationCallback4086_FindRow
    bcc SourceAnimationCallback4086_Branch_31
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_31:
.a16
.i16
    sta.l SourceAnimationCallback4086_CurrentRow
    lda.l SourceUpdateFrame4086_Side
    tax
    lda.l $410002,x
    sta.l SourceAnimationCallback4086_DefaultModel
    jsr SourceAnimationCallback4086_FindRow
    bcc SourceAnimationCallback4086_Branch_32
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_32:
.a16
.i16
    sta.l SourceAnimationCallback4086_DefaultRow
    lda.l SourceAnimationCallback4086_CurrentRow
    tax
    inx
    inx
    jsr SourceAnimationCallback4086_Read
    cmp #$FFFF
    beq SourceAnimationCallback4086_Branch_33
    jmp SourceAnimationCallback4086_Begin__context
SourceAnimationCallback4086_Branch_33:
.a16
.i16
    lda.l SourceAnimationCallback4086_DefaultRow
    tax
    inx
    inx
    jsr SourceAnimationCallback4086_Read
    cmp #$FFFF
    beq SourceAnimationCallback4086_Branch_34
    jmp SourceAnimationCallback4086_Begin__context
SourceAnimationCallback4086_Branch_34:
.a16
.i16
    ; Neither script initialized: source does not allocate installed locals.
    jmp SourceAnimationCallback4086_Done
SourceAnimationCallback4086_Begin__context:
.a16
.i16
    lda.l VmSourceVars_Ready
    cmp #$B4A4
    beq SourceAnimationCallback4086_Branch_35
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_35:
.a16
.i16
    lda.l VmSourceCallback_Ready
    cmp #$B4A5
    beq SourceAnimationCallback4086_Branch_36
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_36:
.a16
.i16
    lda.l SourceUpdateFrame4086_View
    tax
    lda.l $410000,x
    sta.l VmSourceVars_Owner
    sta.l VmNativeVariant_Self+4
    lda.l $410002,x
    sta.l VmSourceVars_Owner+2
    sta.l VmNativeVariant_Self+6
    ora.l VmNativeVariant_Self+4
    bne SourceAnimationCallback4086_Branch_37
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_37:
.a16
.i16
    lda #BOR_VT_PTR
    sta.l VmNativeVariant_Self
    lda #1
    sta.l VmSourceVars_Scope
    lda #BOR_VT_INTEGER
    sta.l VmNativeVariant_Frame
    sta.l VmNativeVariant_AnimNum
    sta.l VmNativeVariant_AnimHandle
    lda #0
    sta.l VmNativeVariant_Self+2
    sta.l VmNativeVariant_Frame+2
    sta.l VmNativeVariant_Frame+6
    sta.l VmNativeVariant_AnimNum+2
    sta.l VmNativeVariant_AnimHandle+2
    sta.l VmNativeVariant_AnimHandle+6
    sta.l SourceAnimationCallback4086_Fault
    sta.l VmState_Error
    lda.l SourceUpdateFrame4086_Request
    sta.l VmNativeVariant_Frame+4
    lda.l SourceUpdateFrame4086_AnimIdLo
    sta.l VmNativeVariant_AnimNum+4
    lda.l SourceUpdateFrame4086_AnimIdHi
    sta.l VmNativeVariant_AnimNum+6
    lda.l SourceUpdateFrame4086_Handle
    sta.l VmNativeVariant_AnimHandle+4
    lda #$B48F
    sta.l VmNativeVariant_ContextValid
    lda #1
    sta.l VmSourceCallback_Request
    sep #$20
.a8
    lda #VMSTAT_DONE
    sta.l VmState_Status
    rep #$30
.a16
.i16
    jsl Vm_SourceCallbackOwnerCall
    bcc SourceAnimationCallback4086_Branch_38
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_38:
.a16
.i16
    lda #1
    sta.l SourceAnimationCallback4086_State
    lda.l SourceAnimationCallback4086_CurrentRow
    jsr SourceAnimationCallback4086_Prepare
    bcc SourceAnimationCallback4086_Branch_39
    jmp SourceAnimationCallback4086_CloseFault
SourceAnimationCallback4086_Branch_39:
.a16
.i16
    jmp SourceAnimationCallback4086_Ok

; Resume one VM span. YIELD is returned to the foreground owner; the shared
; boundary remains active and its locals are not reinstalled on resume.
SourceAnimationCallback4086_Run:
.a16
.i16
    php
    rep #$38
    phx
    phy
    lda.l SourceAnimationCallback4086_Ready
    cmp #$B4E6
    beq SourceAnimationCallback4086_Branch_40
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_40:
.a16
.i16
    lda.l SourceAnimationCallback4086_State
    cmp #1
    bne SourceAnimationCallback4086_Branch_41
    jmp SourceAnimationCallback4086_Run__span
SourceAnimationCallback4086_Branch_41:
.a16
.i16
    cmp #2
    bne SourceAnimationCallback4086_Branch_42
    jmp SourceAnimationCallback4086_Run__span
SourceAnimationCallback4086_Branch_42:
.a16
.i16
    cmp #3
    bne SourceAnimationCallback4086_Branch_43
    jmp SourceAnimationCallback4086_Ok
SourceAnimationCallback4086_Branch_43:
.a16
.i16
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Run__span:
.a16
.i16
    jsl SourceVMRun4086_Call
    bcc SourceAnimationCallback4086_Branch_44
    jmp SourceAnimationCallback4086_CloseFault
SourceAnimationCallback4086_Branch_44:
.a16
.i16
    cmp #VMSTAT_YIELDED
    bne SourceAnimationCallback4086_Branch_45
    jmp SourceAnimationCallback4086_Ok
SourceAnimationCallback4086_Branch_45:
.a16
.i16
    cmp #VMSTAT_DONE
    beq SourceAnimationCallback4086_Branch_46
    jmp SourceAnimationCallback4086_CloseFault
SourceAnimationCallback4086_Branch_46:
.a16
.i16
    lda.l SourceAnimationCallback4086_State
    cmp #2
    bne SourceAnimationCallback4086_Branch_47
    jmp SourceAnimationCallback4086_Close
SourceAnimationCallback4086_Branch_47:
.a16
.i16
    lda.l SourceUpdateFrame4086_Side
    tax
    lda.l $410000,x                ; source tests fresh eligibility here
    cmp.l $410002,x
    bne SourceAnimationCallback4086_Branch_48
    jmp SourceAnimationCallback4086_Close
SourceAnimationCallback4086_Branch_48:
.a16
.i16
    lda #2
    sta.l SourceAnimationCallback4086_State
    lda.l SourceAnimationCallback4086_DefaultRow
    jsr SourceAnimationCallback4086_Prepare
    bcc SourceAnimationCallback4086_Branch_49
    jmp SourceAnimationCallback4086_CloseFault
SourceAnimationCallback4086_Branch_49:
.a16
.i16
    jmp SourceAnimationCallback4086_Run__span
SourceAnimationCallback4086_Close:
.a16
.i16
    lda #2
    sta.l VmSourceCallback_Request
    jsl Vm_SourceCallbackOwnerCall
    bcc SourceAnimationCallback4086_Branch_50
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_50:
.a16
.i16
SourceAnimationCallback4086_Done:
.a16
.i16
    lda #3
    sta.l SourceAnimationCallback4086_State
    sep #$20
.a8
    lda #VMSTAT_DONE
    sta.l VmState_Status
    rep #$30
.a16
.i16
    jmp SourceAnimationCallback4086_Ok
SourceAnimationCallback4086_CloseFault:
.a16
.i16
    lda.l VmSourceCallback_Active
    cmp #$B4A6
    beq SourceAnimationCallback4086_Branch_51
    jmp SourceAnimationCallback4086_Bad
SourceAnimationCallback4086_Branch_51:
.a16
.i16
    lda #2
    sta.l VmSourceCallback_Request
    jsl Vm_SourceCallbackOwnerCall
SourceAnimationCallback4086_Bad:
.a16
.i16
    lda #1
    sta.l SourceAnimationCallback4086_Fault
    lda #4
    sta.l SourceAnimationCallback4086_State
    lda #VMSTAT_FAULT
    sta.l SourceAnimationCallback4086_Status
    ply
    plx
    plp
    sec
    rtl
SourceAnimationCallback4086_Ok:
.a16
.i16
    lda.l VmState_Status
    and #$00FF
    sta.l SourceAnimationCallback4086_Status
    ply
    plx
    plp
    clc
    rtl

; Find a complete, bounded model descriptor. No native program alias exists.
SourceAnimationCallback4086_FindRow:
.a16
.i16
    sta.l SourceAnimationCallback4086_SelectedModel
    cmp.l SourceAnimationCallback4086_Models
    bcc SourceAnimationCallback4086_Branch_52
    jmp SourceAnimationCallback4086_HelperBad
SourceAnimationCallback4086_Branch_52:
.a16
.i16
    asl a
    asl a
    asl a
    asl a
    clc
    adc #32
    clc
    adc.l SourceAnimationCallback4086_Base
    sta.l SourceAnimationCallback4086_SelectedRow
    tax
    jsr SourceAnimationCallback4086_Read
    cmp.l SourceAnimationCallback4086_SelectedModel
    beq SourceAnimationCallback4086_Branch_53
    jmp SourceAnimationCallback4086_HelperBad
SourceAnimationCallback4086_Branch_53:
.a16
.i16
    inx
    inx
    jsr SourceAnimationCallback4086_Read
    cmp #$FFFF
    bne SourceAnimationCallback4086_Branch_54
    jmp SourceAnimationCallback4086_FindRow__empty
SourceAnimationCallback4086_Branch_54:
.a16
.i16
    cmp.l SourceAnimationCallback4086_Programs
    bcc SourceAnimationCallback4086_Branch_55
    jmp SourceAnimationCallback4086_HelperBad
SourceAnimationCallback4086_Branch_55:
.a16
.i16
    lda.l SourceAnimationCallback4086_SelectedRow
    clc
    adc #10
    tax
    jsr SourceAnimationCallback4086_Read
    cmp #1                         ; stable shared installed-local capability
    beq SourceAnimationCallback4086_Branch_56
    jmp SourceAnimationCallback4086_HelperBad
SourceAnimationCallback4086_Branch_56:
.a16
.i16
SourceAnimationCallback4086_FindRow__ok:
.a16
.i16
    lda.l SourceAnimationCallback4086_SelectedRow
    clc
    rts
SourceAnimationCallback4086_FindRow__empty:
.a16
.i16
    ldy #6
SourceAnimationCallback4086_FindRow__zero:
.a16
.i16
    inx
    inx
    jsr SourceAnimationCallback4086_Read
    beq SourceAnimationCallback4086_Branch_57
    jmp SourceAnimationCallback4086_HelperBad
SourceAnimationCallback4086_Branch_57:
.a16
.i16
    dey
    beq SourceAnimationCallback4086_Branch_58
    jmp SourceAnimationCallback4086_FindRow__zero
SourceAnimationCallback4086_Branch_58:
.a16
.i16
    bra SourceAnimationCallback4086_FindRow__ok

; Copy this program's immutable initial slots; never erase persistent instance
; variables. Matrix frame routes use the original installed caller snapshot.
SourceAnimationCallback4086_Prepare:
.a16
.i16
    sta.l SourceAnimationCallback4086_SelectedRow
    tax
    inx
    inx
    jsr SourceAnimationCallback4086_Read
    cmp #$FFFF
    bne SourceAnimationCallback4086_Branch_59
    jmp SourceAnimationCallback4086_Prepare__empty
SourceAnimationCallback4086_Branch_59:
.a16
.i16
    cmp.l SourceAnimationCallback4086_Programs
    bcc SourceAnimationCallback4086_Branch_60
    jmp SourceAnimationCallback4086_HelperBad
SourceAnimationCallback4086_Branch_60:
.a16
.i16
    sta.l SourceAnimationCallback4086_Program
    sta.l VmSourceFrame_Program
    inx
    inx
    jsr SourceAnimationCallback4086_Read
    sta.l SourceAnimationCallback4086_SlotBase
    inx
    inx
    jsr SourceAnimationCallback4086_Read
    bne SourceAnimationCallback4086_Branch_61
    jmp SourceAnimationCallback4086_HelperBad
SourceAnimationCallback4086_Branch_61:
.a16
.i16
    cmp #VM_SLOT_MAX+1
    bcc SourceAnimationCallback4086_Branch_62
    jmp SourceAnimationCallback4086_HelperBad
SourceAnimationCallback4086_Branch_62:
.a16
.i16
    sta.l SourceAnimationCallback4086_Slots
    clc
    adc.l SourceAnimationCallback4086_SlotBase
    bcc SourceAnimationCallback4086_Branch_63
    jmp SourceAnimationCallback4086_HelperBad
SourceAnimationCallback4086_Branch_63:
.a16
.i16
    cmp.l VmState_SlotCount
    bcs SourceAnimationCallback4086_Branch_64
    jmp SourceAnimationCallback4086_Prepare__slot_range
SourceAnimationCallback4086_Branch_64:
.a16
.i16
    beq SourceAnimationCallback4086_Branch_65
    jmp SourceAnimationCallback4086_HelperBad
SourceAnimationCallback4086_Branch_65:
.a16
.i16
SourceAnimationCallback4086_Prepare__slot_range:
.a16
.i16
    inx
    inx
    jsr SourceAnimationCallback4086_Read
    sta.l SourceAnimationCallback4086_Initializers
    cmp #64
    bcs SourceAnimationCallback4086_Branch_66
    jmp SourceAnimationCallback4086_HelperBad
SourceAnimationCallback4086_Branch_66:
.a16
.i16
    lda.l SourceAnimationCallback4086_Slots
    asl a
    asl a
    asl a
    clc
    adc.l SourceAnimationCallback4086_Initializers
    bcc SourceAnimationCallback4086_Branch_67
    jmp SourceAnimationCallback4086_HelperBad
SourceAnimationCallback4086_Branch_67:
.a16
.i16
    cmp.l SourceAnimationCallback4086_MetadataBytes
    bcs SourceAnimationCallback4086_Branch_68
    jmp SourceAnimationCallback4086_Prepare__init_range
SourceAnimationCallback4086_Branch_68:
.a16
.i16
    beq SourceAnimationCallback4086_Branch_69
    jmp SourceAnimationCallback4086_HelperBad
SourceAnimationCallback4086_Branch_69:
.a16
.i16
SourceAnimationCallback4086_Prepare__init_range:
.a16
.i16
    ; Select and validate the route before touching temporary slots. An empty
    ; optimized route has no bytecode reads/writes and requires no slot reset.
    lda #$B4FC
    sta.l VmSourceFrame_Pending
    jsl Vm_SourceFrameGate
    and #$00FF
    cmp #VMSTAT_FAULT
    bne SourceAnimationCallback4086_Prepare__route_valid
    jmp SourceAnimationCallback4086_HelperBad
SourceAnimationCallback4086_Prepare__route_valid:
.a16
.i16
    cmp #VMSTAT_DONE
    bne SourceAnimationCallback4086_Prepare__copy_required
    jmp SourceAnimationCallback4086_Prepare__empty
SourceAnimationCallback4086_Prepare__copy_required:
.a16
.i16
    jsl SourceAnimationSlots4086_Release
    bcc SourceAnimationCallback4086_Prepare__slots_released
    jmp SourceAnimationCallback4086_HelperBad
SourceAnimationCallback4086_Prepare__slots_released:
.a16
.i16
    lda.l SourceAnimationCallback4086_Initializers
    clc
    adc #$9AA0                    ; VmCode_Wram low16, validated metadata range
    tax
    lda.l SourceAnimationCallback4086_SlotBase
    asl a
    asl a
    asl a
    clc
    adc #$C000                    ; VmSlots_Wram low16, bounded slot range
    tay
    lda.l SourceAnimationCallback4086_Slots
    asl a
    asl a
    asl a
    dec a                         ; MVN count is bytes minus one
    phb
    mvn $7F,$7E                   ; encoded destination bank, source bank
    plb                           ; MVN changes DBR, not the owner context
    clc
    rts
SourceAnimationCallback4086_Prepare__empty:
.a16
.i16
    sep #$20
.a8
    lda #VMSTAT_DONE
    sta.l VmState_Status
    rep #$30
.a16
.i16
    clc
    rts
SourceAnimationCallback4086_HelperBad:
.a16
.i16
    sec
    rts
SourceAnimationCallback4086_Read:
.a16
.i16
    phb
    sep #$20
.a8
    lda.l SourceAnimationCallback4086_Bank
    pha
    plb
    rep #$20
.a16
    lda.w $0000,x
    plb
    ora #0
    rts
