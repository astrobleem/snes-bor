; Owner-driven animation callback boundary. Pinned execute_animation_script
; installs these locals once for current/default model callbacks, then empties
; only those four values. Persistent names survive. Cold boot leaves disabled.
; Ready $B4A5; Request 1 BEGIN, 2 END; Active $B4A6 inside the shared boundary.
; Caller installs validated context and instance descriptor before BEGIN.
; END requires a terminal VM and retains FAULT diagnostics. This is not a
; world traversal, physics tick or production callback owner.
VmSourceCallback_Ready = $7FF7A0
VmSourceCallback_Active = $7FF7A2
VmSourceCallback_Request = $7FF7A4
VmSourceCallback_Rows = $7FF7A6 ; four cached row offsets
VmSourceCallback_Key = $7FF7AE
VmSourceCallback_Missing = $7FF7B0
VmSourceCallback_Free = $7FF7B2
VmSourceCallback_Mode = $7FF7B4
VmSourceCallback_Snapshot = $7FF7C0 ; four complete original installed variants

Vm_SourceCallbackPoll:
.a16
.i16
    lda.l VmSourceCallback_Ready
    bne Vm_SourceCallbackBranch_1
    jmp Vm_SourceCallbackPoll__ok
Vm_SourceCallbackBranch_1:
.a16
.i16
    cmp #$B4A5
    beq Vm_SourceCallbackBranch_2
    jmp Vm_SourceCallbackPoll__bad
Vm_SourceCallbackBranch_2:
.a16
.i16
    lda.l VmSourceCallback_Request
    bne Vm_SourceCallbackBranch_3
    jmp Vm_SourceCallbackPoll__ok
Vm_SourceCallbackBranch_3:
.a16
.i16
    sta.l VmSourceCallback_Mode
    lda #0
    sta.l VmSourceCallback_Request
    lda.l VmState_Status
    and #$00FF
    cmp #VMSTAT_RUNNING
    bne Vm_SourceCallbackBranch_4
    jmp Vm_SourceCallbackPoll__bad
Vm_SourceCallbackBranch_4:
.a16
.i16
    cmp #VMSTAT_YIELDED
    bne Vm_SourceCallbackBranch_5
    jmp Vm_SourceCallbackPoll__bad
Vm_SourceCallbackBranch_5:
.a16
.i16
    jsr Vm_SourceVarsValidate
    bcc Vm_SourceCallbackBranch_6
    jmp Vm_SourceCallbackPoll__bad
Vm_SourceCallbackBranch_6:
.a16
.i16
    lda.l VmSourceVars_Scope
    cmp #1                         ; animation script instance kind
    beq Vm_SourceCallbackBranch_7
    jmp Vm_SourceCallbackPoll__bad
Vm_SourceCallbackBranch_7:
.a16
.i16
    lda.l VmSourceCallback_Mode
    cmp #1
    bne Vm_SourceCallbackBranch_8
    jmp Vm_SourceCallbackPoll__begin
Vm_SourceCallbackBranch_8:
.a16
.i16
    cmp #2
    beq Vm_SourceCallbackBranch_9
    jmp Vm_SourceCallbackPoll__bad
Vm_SourceCallbackBranch_9:
.a16
.i16
    lda.l VmSourceCallback_Active
    cmp #$B4A6
    beq Vm_SourceCallbackBranch_10
    jmp Vm_SourceCallbackPoll__bad
Vm_SourceCallbackBranch_10:
.a16
.i16
    lda.l VmState_Status
    and #$00FF
    cmp #VMSTAT_DONE
    bcs Vm_SourceCallbackBranch_11
    jmp Vm_SourceCallbackPoll__bad
Vm_SourceCallbackBranch_11:
.a16
.i16
    ; Require the same immutable caller snapshot across both model programs.
    ldx #0
Vm_SourceCallbackPoll__check_snapshot:
.a16
.i16
    lda.l VmNativeVariant_Self,x
    cmp.l VmSourceCallback_Snapshot,x
    beq Vm_SourceCallbackBranch_12
    jmp Vm_SourceCallbackPoll__bad
Vm_SourceCallbackBranch_12:
.a16
.i16
    inx
    inx
    cpx #32
    bcs Vm_SourceCallbackBranch_13
    jmp Vm_SourceCallbackPoll__check_snapshot
Vm_SourceCallbackBranch_13:
.a16
.i16
    jmp Vm_SourceCallbackPoll__preflight
Vm_SourceCallbackPoll__begin:
.a16
.i16
    lda.l VmSourceCallback_Active
    beq Vm_SourceCallbackBranch_14
    jmp Vm_SourceCallbackPoll__bad
Vm_SourceCallbackBranch_14:
.a16
.i16
    lda.l VmNativeVariant_Frame
    cmp #BOR_VT_INTEGER
    beq Vm_SourceCallbackBranch_15
    jmp Vm_SourceCallbackPoll__bad
Vm_SourceCallbackBranch_15:
.a16
.i16
    lda.l VmNativeVariant_Frame+2
    beq Vm_SourceCallbackBranch_16
    jmp Vm_SourceCallbackPoll__bad
Vm_SourceCallbackBranch_16:
.a16
.i16
    lda.l VmNativeVariant_AnimNum
    cmp #BOR_VT_INTEGER
    beq Vm_SourceCallbackBranch_17
    jmp Vm_SourceCallbackPoll__bad
Vm_SourceCallbackBranch_17:
.a16
.i16
    lda.l VmNativeVariant_AnimNum+2
    beq Vm_SourceCallbackBranch_18
    jmp Vm_SourceCallbackPoll__bad
Vm_SourceCallbackBranch_18:
.a16
.i16
    lda.l VmNativeVariant_AnimHandle
    cmp #BOR_VT_INTEGER
    beq Vm_SourceCallbackBranch_19
    jmp Vm_SourceCallbackPoll__bad
Vm_SourceCallbackBranch_19:
.a16
.i16
    lda.l VmNativeVariant_AnimHandle+2
    beq Vm_SourceCallbackBranch_20
    jmp Vm_SourceCallbackPoll__bad
Vm_SourceCallbackBranch_20:
.a16
.i16
    lda.l VmNativeVariant_Self+2
    beq Vm_SourceCallbackBranch_21
    jmp Vm_SourceCallbackPoll__bad
Vm_SourceCallbackBranch_21:
.a16
.i16
Vm_SourceCallbackPoll__preflight:
.a16
.i16
    lda #0
    sta.l VmSourceCallback_Key
    sta.l VmSourceCallback_Missing
Vm_SourceCallbackPoll__find:
.a16
.i16
    jsr Vm_SourceCallbackKey
    jsr Vm_SourceVarsFind
    pha
    lda.l VmSourceCallback_Key
    asl a
    tax
    pla
    sta.l VmSourceCallback_Rows,x
    cmp #$FFFF
    beq Vm_SourceCallbackBranch_22
    jmp Vm_SourceCallbackPoll__found
Vm_SourceCallbackBranch_22:
.a16
.i16
    lda.l VmSourceCallback_Missing
    inc a
    sta.l VmSourceCallback_Missing
Vm_SourceCallbackPoll__found:
.a16
.i16
    lda.l VmSourceCallback_Key
    inc a
    sta.l VmSourceCallback_Key
    cmp #4
    bcs Vm_SourceCallbackBranch_23
    jmp Vm_SourceCallbackPoll__find
Vm_SourceCallbackBranch_23:
.a16
.i16
    lda.l VmSourceCallback_Mode
    cmp #2
    bne Vm_SourceCallbackBranch_24
    jmp Vm_SourceCallbackPoll__end
Vm_SourceCallbackBranch_24:
.a16
.i16
    ; Count enough distinct free nodes BEFORE writing any namespace byte.
    lda #0
    sta.l VmSourceCallback_Free
    sta.l VmSourceVars_Index
    sta.l VmSourceVars_Row
Vm_SourceCallbackPoll__count:
.a16
.i16
    lda.l VmSourceVars_Row
    tax
    lda.l SOURCE_VARIABLE_POOL+6,x
    beq Vm_SourceCallbackBranch_25
    jmp Vm_SourceCallbackPoll__count_next
Vm_SourceCallbackBranch_25:
.a16
.i16
    lda.l VmSourceCallback_Free
    inc a
    sta.l VmSourceCallback_Free
Vm_SourceCallbackPoll__count_next:
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
    bcs Vm_SourceCallbackBranch_26
    jmp Vm_SourceCallbackPoll__count
Vm_SourceCallbackBranch_26:
.a16
.i16
    lda.l VmSourceCallback_Free
    cmp.l VmSourceCallback_Missing
    bcs Vm_SourceCallbackBranch_27
    jmp Vm_SourceCallbackPoll__bad
Vm_SourceCallbackBranch_27:
.a16
.i16
    ldx #0
Vm_SourceCallbackPoll__save:
.a16
.i16
    lda.l VmNativeVariant_Self,x
    sta.l VmSourceCallback_Snapshot,x
    inx
    inx
    cpx #32
    bcs Vm_SourceCallbackBranch_28
    jmp Vm_SourceCallbackPoll__save
Vm_SourceCallbackBranch_28:
.a16
.i16
    lda #0
    sta.l VmSourceCallback_Key
Vm_SourceCallbackPoll__install:
.a16
.i16
    jsr Vm_SourceCallbackKey
    jsr Vm_SourceVarsFind
    cmp #$FFFF
    beq Vm_SourceCallbackBranch_29
    jmp Vm_SourceCallbackPoll__write
Vm_SourceCallbackBranch_29:
.a16
.i16
    lda.l VmSourceVars_Free
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
Vm_SourceCallbackPoll__name:
.a16
.i16
    jsr Vm_SourceVarsKeyByte
    sta.l VmSourceVars_Char
    tya
    clc
    adc.l VmSourceVars_Row
    tax
    lda.l VmSourceVars_Char
    sta.l SOURCE_VARIABLE_POOL+16,x
    iny
    tya
    cmp.l VmNativeVariant_KeyLength
    bcs Vm_SourceCallbackBranch_30
    jmp Vm_SourceCallbackPoll__name
Vm_SourceCallbackBranch_30:
.a16
.i16
    lda.l VmSourceVars_Row
Vm_SourceCallbackPoll__write:
.a16
.i16
    tax
    lda.l VmSourceCallback_Key
    asl a
    asl a
    asl a
    tay
    phx
    tyx
    lda.l VmSourceCallback_Snapshot,x
    sta.l VmNativeVariant_Result
    lda.l VmSourceCallback_Snapshot+2,x
    sta.l VmNativeVariant_Result+2
    lda.l VmSourceCallback_Snapshot+4,x
    sta.l VmNativeVariant_Result+4
    lda.l VmSourceCallback_Snapshot+6,x
    sta.l VmNativeVariant_Result+6
    plx
    lda.l VmNativeVariant_Result
    sta.l SOURCE_VARIABLE_POOL+8,x
    lda.l VmNativeVariant_Result+2
    sta.l SOURCE_VARIABLE_POOL+10,x
    lda.l VmNativeVariant_Result+4
    sta.l SOURCE_VARIABLE_POOL+12,x
    lda.l VmNativeVariant_Result+6
    sta.l SOURCE_VARIABLE_POOL+14,x
    lda.l VmSourceCallback_Key
    inc a
    sta.l VmSourceCallback_Key
    cmp #4
    bcs Vm_SourceCallbackBranch_31
    jmp Vm_SourceCallbackPoll__install
Vm_SourceCallbackBranch_31:
.a16
.i16
    lda #$B4A6
    sta.l VmSourceCallback_Active
    jmp Vm_SourceCallbackPoll__ok
Vm_SourceCallbackPoll__end:
.a16
.i16
    lda.l VmSourceCallback_Missing
    beq Vm_SourceCallbackBranch_32
    jmp Vm_SourceCallbackPoll__bad
Vm_SourceCallbackBranch_32:
.a16
.i16
    ldy #0
Vm_SourceCallbackPoll__clear:
.a16
.i16
    tyx
    lda.l VmSourceCallback_Rows,x
    tax
    lda #0
    sta.l SOURCE_VARIABLE_POOL+8,x
    sta.l SOURCE_VARIABLE_POOL+10,x
    sta.l SOURCE_VARIABLE_POOL+12,x
    sta.l SOURCE_VARIABLE_POOL+14,x
    iny
    iny
    cpy #8
    bcs Vm_SourceCallbackBranch_33
    jmp Vm_SourceCallbackPoll__clear
Vm_SourceCallbackBranch_33:
.a16
.i16
    lda #0
    sta.l VmSourceCallback_Active
    sta.l VmNativeVariant_ContextValid
Vm_SourceCallbackPoll__ok:
.a16
.i16
    clc
    rts
Vm_SourceCallbackPoll__bad:
.a16
.i16
    sec
    lda #VMERR_BAD_NATIVE
    rts

; Index 0..3 selects original snapshot order self/frame/animnum/animhandle.
Vm_SourceCallbackKey:
.a16
.i16
    lda.l VmSourceCallback_Key
    asl a
    tax
    lda.l Vm_SourceCallbackNameOffsets,x
    sta.l VmNativeVariant_KeyBase
    lda.l Vm_SourceCallbackNameLengths,x
    sta.l VmNativeVariant_KeyLength
    lda #2
    sta.l VmNativeVariant_KeyPool
    rts

Vm_SourceCallbackNameOffsets:
    .dw 0,5,11,19
Vm_SourceCallbackNameLengths:
    .dw 4,5,7,10
Vm_SourceCallbackNames:
    .db "self",0,"frame",0,"animnum",0,"animhandle",0
