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
VmSourceCallback_FreeRows = $7FF7B6 ; first four unoccupied rows
VmSourceCallback_ScanEnd = $7FF7BE
VmSourceCallback_Mode = $7FF7B4
VmSourceCallback_Snapshot = $7FF7C0 ; four complete original installed variants

; Foreground world-owner gateway. Keep the existing fetch-driven boundary
; available to ordinary callers; direct ownership lives outside bank 0.
Vm_SourceCallbackOwnerCall:
.a16
.i16
    php
    rep #$38
    phx
    phy
    jsr Vm_SourceCallbackPoll
    bcs Vm_SourceCallbackOwnerCall__bad
    ply
    plx
    plp
    clc
    rtl
Vm_SourceCallbackOwnerCall__bad:
.a16
.i16
    ply
    plx
    plp
    sec
    rtl

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
    lda.l VmSourceCallback_Mode
    cmp #2
    bne Vm_SourceCallbackFastBegin
    jsr Vm_SourceCallbackValidateRows
    bcc Vm_SourceCallbackFastEnd
    jmp Vm_SourceCallbackPoll__bad
Vm_SourceCallbackFastEnd:
.a16
.i16
    jmp Vm_SourceCallbackPoll__end
Vm_SourceCallbackFastBegin:
.a16
.i16
    jsr Vm_SourceCallbackScan
    bcc Vm_SourceCallbackFastCapacity
    jmp Vm_SourceCallbackPoll__bad
Vm_SourceCallbackFastCapacity:
.a16
.i16
    lda.l VmSourceCallback_Free
    cmp.l VmSourceCallback_Missing
    bcs Vm_SourceCallbackFastSave
    jmp Vm_SourceCallbackPoll__bad
Vm_SourceCallbackFastSave:
.a16
.i16
    lda #0
    sta.l VmSourceCallback_Free
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
    lda.l VmSourceCallback_Key
    asl a
    tax
    lda.l VmSourceCallback_Rows,x
    cmp #$FFFF
    beq Vm_SourceCallbackBranch_29
    jmp Vm_SourceCallbackPoll__write
Vm_SourceCallbackBranch_29:
.a16
.i16
    lda.l VmSourceCallback_Free
    asl a
    tax
    lda.l VmSourceCallback_FreeRows,x
    sta.l VmSourceVars_Row
    lda.l VmSourceCallback_Free
    inc a
    sta.l VmSourceCallback_Free
    lda.l VmSourceCallback_Key
    asl a
    tax
    lda.l VmSourceVars_Row
    sta.l VmSourceCallback_Rows,x
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
    bra Vm_SourceCallbackBranch_32
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


; Names/row ownership are immutable for the B4A4 lease: set/clear changes only
; values. Scan once at BEGIN, preflight free capacity before any allocation,
; then validate all four cached names/owners at END. No sparse-pool assumption.
Vm_SourceCallbackScan:
.a16
.i16
    lda #$FFFF
    ldx #0
Vm_SourceCallbackScanInit:
.a16
.i16
    sta.l VmSourceCallback_Rows,x
    inx
    inx
    cpx #8
    bcs Vm_SourceCallbackFastBranch_1
    jmp Vm_SourceCallbackScanInit
Vm_SourceCallbackFastBranch_1:
.a16
.i16
    lda #4
    sta.l VmSourceCallback_Missing
    lda #0
    sta.l VmSourceCallback_Free
    lda.l VmSourceVars_Count
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l VmSourceCallback_ScanEnd
    ldx #0
Vm_SourceCallbackScanRow:
.a16
.i16
    lda.l SOURCE_VARIABLE_POOL+6,x
    beq Vm_SourceCallbackFastBranch_2
    jmp Vm_SourceCallbackScanOccupied
Vm_SourceCallbackFastBranch_2:
.a16
.i16
    lda.l VmSourceCallback_Free
    cmp #4
    bcc Vm_SourceCallbackFastBranch_3
    jmp Vm_SourceCallbackScanNext
Vm_SourceCallbackFastBranch_3:
.a16
.i16
    phx
    asl a
    tay
    txa
    tyx
    sta.l VmSourceCallback_FreeRows,x
    plx
    lda.l VmSourceCallback_Free
    inc a
    sta.l VmSourceCallback_Free
    bra Vm_SourceCallbackScanNext
Vm_SourceCallbackScanOccupied:
.a16
.i16
    jsr Vm_SourceCallbackMatchRow
    bcc Vm_SourceCallbackFastBranch_4
    jmp Vm_SourceCallbackScanNext
Vm_SourceCallbackFastBranch_4:
.a16
.i16
    ; A is the matched key's cache offset, X the immutable pool row.
    tay
    txa
    phx
    tyx
    pha
    lda.l VmSourceCallback_Rows,x
    cmp #$FFFF
    beq Vm_SourceCallbackFastBranch_5
    jmp Vm_SourceCallbackScanDuplicate
Vm_SourceCallbackFastBranch_5:
.a16
.i16
    pla
    sta.l VmSourceCallback_Rows,x
    plx
    lda.l VmSourceCallback_Missing
    dec a
    sta.l VmSourceCallback_Missing
    bne Vm_SourceCallbackScanNext
    ; All names exist. BEGIN will allocate nothing, so no remaining free
    ; capacity needs inspection. Rows remain validated on END.
    clc
    rts
Vm_SourceCallbackScanNext:
.a16
.i16
    txa
    clc
    adc #64
    tax
    cmp.l VmSourceCallback_ScanEnd
    bcs Vm_SourceCallbackFastBranch_6
    jmp Vm_SourceCallbackScanRow
Vm_SourceCallbackFastBranch_6:
.a16
.i16
    clc
    rts
Vm_SourceCallbackScanDuplicate:
.a16
.i16
    pla
    plx
    sec
    rts

Vm_SourceCallbackValidateRows:
.a16
.i16
    lda.l VmSourceVars_Count
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l VmSourceCallback_ScanEnd
    ldy #0
Vm_SourceCallbackValidateNext:
.a16
.i16
    tyx
    lda.l VmSourceCallback_Rows,x
    cmp.l VmSourceCallback_ScanEnd
    bcc Vm_SourceCallbackFastBranch_7
    jmp Vm_SourceCallbackValidateBad
Vm_SourceCallbackFastBranch_7:
.a16
.i16
    bit #63
    beq Vm_SourceCallbackFastBranch_8
    jmp Vm_SourceCallbackValidateBad
Vm_SourceCallbackFastBranch_8:
.a16
.i16
    tax
    phy
    jsr Vm_SourceCallbackMatchRow
    ply
    bcc Vm_SourceCallbackFastBranch_9
    jmp Vm_SourceCallbackValidateBad
Vm_SourceCallbackFastBranch_9:
.a16
.i16
    sta.l VmSourceCallback_Key
    tya
    cmp.l VmSourceCallback_Key
    beq Vm_SourceCallbackFastBranch_10
    jmp Vm_SourceCallbackValidateBad
Vm_SourceCallbackFastBranch_10:
.a16
.i16
    iny
    iny
    cpy #8
    bcs Vm_SourceCallbackFastBranch_11
    jmp Vm_SourceCallbackValidateNext
Vm_SourceCallbackFastBranch_11:
.a16
.i16
    clc
    rts
Vm_SourceCallbackValidateBad:
.a16
.i16
    sec
    rts

; C=0/A=key*2 on exact matching owner, scope and terminated name. Preserve X.
Vm_SourceCallbackMatchRow:
.a16
.i16
    lda.l SOURCE_VARIABLE_POOL,x
    cmp.l VmSourceVars_Owner
    beq Vm_SourceCallbackFastBranch_12
    jmp Vm_SourceCallbackMatchBad
Vm_SourceCallbackFastBranch_12:
.a16
.i16
    lda.l SOURCE_VARIABLE_POOL+2,x
    cmp.l VmSourceVars_Owner+2
    beq Vm_SourceCallbackFastBranch_13
    jmp Vm_SourceCallbackMatchBad
Vm_SourceCallbackFastBranch_13:
.a16
.i16
    lda.l SOURCE_VARIABLE_POOL+4,x
    cmp.l VmSourceVars_Scope
    beq Vm_SourceCallbackFastBranch_14
    jmp Vm_SourceCallbackMatchBad
Vm_SourceCallbackFastBranch_14:
.a16
.i16
    lda.l SOURCE_VARIABLE_POOL+6,x
    cmp #4
    beq Vm_SourceCallbackFastBranch_15
    jmp Vm_SourceCallbackMatchTry1
Vm_SourceCallbackFastBranch_15:
.a16
.i16
    lda.l SOURCE_VARIABLE_POOL+16,x
    cmp #$6573
    beq Vm_SourceCallbackFastBranch_16
    jmp Vm_SourceCallbackMatchBad
Vm_SourceCallbackFastBranch_16:
.a16
.i16
    lda.l SOURCE_VARIABLE_POOL+18,x
    cmp #$666C
    beq Vm_SourceCallbackFastBranch_17
    jmp Vm_SourceCallbackMatchBad
Vm_SourceCallbackFastBranch_17:
.a16
.i16
    lda.l SOURCE_VARIABLE_POOL+20,x
    and #$00FF
    beq Vm_SourceCallbackFastBranch_18
    jmp Vm_SourceCallbackMatchBad
Vm_SourceCallbackFastBranch_18:
.a16
.i16
    lda #0
    clc
    rts
Vm_SourceCallbackMatchTry1:
.a16
.i16
    lda.l SOURCE_VARIABLE_POOL+6,x
    cmp #5
    beq Vm_SourceCallbackFastBranch_19
    jmp Vm_SourceCallbackMatchTry2
Vm_SourceCallbackFastBranch_19:
.a16
.i16
    lda.l SOURCE_VARIABLE_POOL+16,x
    cmp #$7266
    beq Vm_SourceCallbackFastBranch_20
    jmp Vm_SourceCallbackMatchBad
Vm_SourceCallbackFastBranch_20:
.a16
.i16
    lda.l SOURCE_VARIABLE_POOL+18,x
    cmp #$6D61
    beq Vm_SourceCallbackFastBranch_21
    jmp Vm_SourceCallbackMatchBad
Vm_SourceCallbackFastBranch_21:
.a16
.i16
    lda.l SOURCE_VARIABLE_POOL+20,x
    cmp #$0065
    beq Vm_SourceCallbackFastBranch_22
    jmp Vm_SourceCallbackMatchBad
Vm_SourceCallbackFastBranch_22:
.a16
.i16
    lda #2
    clc
    rts
Vm_SourceCallbackMatchTry2:
.a16
.i16
    lda.l SOURCE_VARIABLE_POOL+6,x
    cmp #7
    beq Vm_SourceCallbackFastBranch_23
    jmp Vm_SourceCallbackMatchTry3
Vm_SourceCallbackFastBranch_23:
.a16
.i16
    lda.l SOURCE_VARIABLE_POOL+16,x
    cmp #$6E61
    beq Vm_SourceCallbackFastBranch_24
    jmp Vm_SourceCallbackMatchBad
Vm_SourceCallbackFastBranch_24:
.a16
.i16
    lda.l SOURCE_VARIABLE_POOL+18,x
    cmp #$6D69
    beq Vm_SourceCallbackFastBranch_25
    jmp Vm_SourceCallbackMatchBad
Vm_SourceCallbackFastBranch_25:
.a16
.i16
    lda.l SOURCE_VARIABLE_POOL+20,x
    cmp #$756E
    beq Vm_SourceCallbackFastBranch_26
    jmp Vm_SourceCallbackMatchBad
Vm_SourceCallbackFastBranch_26:
.a16
.i16
    lda.l SOURCE_VARIABLE_POOL+22,x
    cmp #$006D
    beq Vm_SourceCallbackFastBranch_27
    jmp Vm_SourceCallbackMatchBad
Vm_SourceCallbackFastBranch_27:
.a16
.i16
    lda #4
    clc
    rts
Vm_SourceCallbackMatchTry3:
.a16
.i16
    lda.l SOURCE_VARIABLE_POOL+6,x
    cmp #10
    beq Vm_SourceCallbackFastBranch_28
    jmp Vm_SourceCallbackMatchTry4
Vm_SourceCallbackFastBranch_28:
.a16
.i16
    lda.l SOURCE_VARIABLE_POOL+16,x
    cmp #$6E61
    beq Vm_SourceCallbackFastBranch_29
    jmp Vm_SourceCallbackMatchBad
Vm_SourceCallbackFastBranch_29:
.a16
.i16
    lda.l SOURCE_VARIABLE_POOL+18,x
    cmp #$6D69
    beq Vm_SourceCallbackFastBranch_30
    jmp Vm_SourceCallbackMatchBad
Vm_SourceCallbackFastBranch_30:
.a16
.i16
    lda.l SOURCE_VARIABLE_POOL+20,x
    cmp #$6168
    beq Vm_SourceCallbackFastBranch_31
    jmp Vm_SourceCallbackMatchBad
Vm_SourceCallbackFastBranch_31:
.a16
.i16
    lda.l SOURCE_VARIABLE_POOL+22,x
    cmp #$646E
    beq Vm_SourceCallbackFastBranch_32
    jmp Vm_SourceCallbackMatchBad
Vm_SourceCallbackFastBranch_32:
.a16
.i16
    lda.l SOURCE_VARIABLE_POOL+24,x
    cmp #$656C
    beq Vm_SourceCallbackFastBranch_33
    jmp Vm_SourceCallbackMatchBad
Vm_SourceCallbackFastBranch_33:
.a16
.i16
    lda.l SOURCE_VARIABLE_POOL+26,x
    and #$00FF
    beq Vm_SourceCallbackFastBranch_34
    jmp Vm_SourceCallbackMatchBad
Vm_SourceCallbackFastBranch_34:
.a16
.i16
    lda #6
    clc
    rts
Vm_SourceCallbackMatchTry4:
.a16
.i16
Vm_SourceCallbackMatchBad:
.a16
.i16
    sec
    rts
