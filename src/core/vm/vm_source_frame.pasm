; Generic offline frame dispatch. All code is outside bank 0. An owner must
; validate paired table/module CRCs once, then hold the ROM descriptor lease.
; Jobs are opt-in and consumed once. No model names or legacy player aliases.
; This is not a production source-world owner or a B48R loader.
VmSourceFrame_Base = $7FF660       ; .dw table ROM address >=$8000
VmSourceFrame_Bank = $7FF662       ; .db mapped ROM bank <64
VmSourceFrame_Bytes = $7FF664      ; .dw complete table length
VmSourceFrame_Programs = $7FF666   ; .dw cached checked header counts
VmSourceFrame_Handles = $7FF668
VmSourceFrame_Ready = $7FF66A      ; .dw $B4FD checked table lease
VmSourceFrame_Program = $7FF66C    ; .dw selected script program, zero based
VmSourceFrame_Entry = $7FF66E      ; .dw result IP or $FFFF empty
VmSourceFrame_Read = $7FF670
VmSourceFrame_Minimum = $7FF672
VmSourceFrame_Frame = $7FF674
VmSourceFrame_Handle = $7FF676
VmSourceFrame_Count = $7FF678
VmSourceFrame_Directory = $7FF67A
VmSourceFrame_Pending = $7FF67C    ; .dw $B4FC one submitted callback

; Replaces exactly the four-byte status LDA at Vm_Run+3. Opt-out returns
; the same status value. The source owner must not submit during RUNNING or
; YIELDED execution: installed locals belong to the active invocation.
Vm_SourceFrameGate:
.a16
.i16
    php
    rep #$31
    phx
    phy
    jsr Vm_SourceCallbackPoll
    bcc Vm_SourceFrameGate__callback_ok
    jmp Vm_SourceFrameGate__fault
Vm_SourceFrameGate__callback_ok:
.a16
.i16
    lda.l VmSourceFrame_Pending
    cmp #$B4FC
    beq Vm_SourceFrameGate__job
    jmp Vm_SourceFrameGate__return
Vm_SourceFrameGate__job:
.a16
.i16
    lda #0
    sta.l VmSourceFrame_Pending
    lda.l VmState_Status
    and #$00FF
    cmp #VMSTAT_RUNNING
    beq Vm_SourceFrameGate__bad
    cmp #VMSTAT_YIELDED
    beq Vm_SourceFrameGate__bad
    jsr Vm_SourceFrameLookup
    bcs Vm_SourceFrameGate__fault
    lda #0
    sta.l VmState_Error
    sta.l VmState_FrameTop
    lda.l VmSourceFrame_Entry
    cmp #$FFFF
    beq Vm_SourceFrameGate__empty
    sta.l VmState_Ip
    lda #VMSTAT_READY
    bra Vm_SourceFrameGate__status
Vm_SourceFrameGate__empty:
.a16
.i16
    lda #VMSTAT_DONE
Vm_SourceFrameGate__status:
.a16
.i16
    sep #$20
.a8
    sta.l VmState_Status
    rep #$30
.a16
.i16
    bra Vm_SourceFrameGate__return
Vm_SourceFrameGate__bad:
.a16
.i16
    lda #VMERR_BAD_NATIVE
Vm_SourceFrameGate__fault:
.a16
.i16
    sta.l VmState_Error
    lda #VMSTAT_FAULT
    bra Vm_SourceFrameGate__status
Vm_SourceFrameGate__return:
.a16
.i16
    ply
    plx
    lda.l VmState_Status
    plp
    rtl

; Return carry set/A=VMERR_BAD_NATIVE on invalid caller/table/job, otherwise
; Entry is a bounded IP or $FFFF. Validate context BEFORE an empty route.
Vm_SourceFrameLookup:
.a16
.i16
    lda #$FFFF
    sta.l VmSourceFrame_Entry
    lda.l VmNativeVariant_ContextValid
    cmp #$B48F
    beq Vm_SourceFrameLookup__context
    jmp Vm_SourceFrameLookup__bad
Vm_SourceFrameLookup__context:
.a16
.i16
    lda.l VmNativeVariant_Self
    and #$00FF
    cmp #BOR_VT_PTR
    bne Vm_SourceFrameLookup__reject
    lda.l VmNativeVariant_Self+4
    ora.l VmNativeVariant_Self+6
    beq Vm_SourceFrameLookup__reject
    lda.l VmNativeVariant_Frame
    and #$00FF
    cmp #BOR_VT_INTEGER
    bne Vm_SourceFrameLookup__reject
    lda.l VmNativeVariant_Frame+6
    bne Vm_SourceFrameLookup__reject
    lda.l VmNativeVariant_Frame+4
    sta.l VmSourceFrame_Frame
    lda.l VmNativeVariant_AnimHandle
    and #$00FF
    cmp #BOR_VT_INTEGER
    bne Vm_SourceFrameLookup__reject
    lda.l VmNativeVariant_AnimHandle+6
    bne Vm_SourceFrameLookup__reject
    lda.l VmNativeVariant_AnimHandle+4
    beq Vm_SourceFrameLookup__reject
    sta.l VmSourceFrame_Handle
    lda.l VmSourceFrame_Ready
    cmp #$B4FD
    bne Vm_SourceFrameLookup__reject
    lda.l VmSourceInstr_Ready
    cmp #$B48E
    bne Vm_SourceFrameLookup__reject
    bra Vm_SourceFrameLookup__descriptor
Vm_SourceFrameLookup__reject:
.a16
.i16
    jmp Vm_SourceFrameLookup__bad
Vm_SourceFrameLookup__descriptor:
.a16
.i16
    lda.l VmSourceFrame_Bank
    and #$00FF
    cmp #64
    bcs Vm_SourceFrameLookup__reject
    lda.l VmSourceFrame_Base
    cmp #$8000
    bcc Vm_SourceFrameLookup__reject
    lda.l VmSourceFrame_Bytes
    cmp #24
    bcc Vm_SourceFrameLookup__reject
    dec a
    clc
    adc.l VmSourceFrame_Base
    bcs Vm_SourceFrameLookup__reject
    lda.l VmSourceFrame_Programs
    beq Vm_SourceFrameLookup__reject
    cmp #513
    bcs Vm_SourceFrameLookup__reject
    cmp.l VmSourceFrame_Program
    beq Vm_SourceFrameLookup__reject
    bcc Vm_SourceFrameLookup__reject
    lda.l VmSourceFrame_Handles
    beq Vm_SourceFrameLookup__reject
    cmp #4097
    bcs Vm_SourceFrameLookup__reject
    cmp.l VmSourceFrame_Handle
    bcc Vm_SourceFrameLookup__reject
    ; Check the table header against the validated owner's cached counts.
    ldy #0
    jsr Vm_SourceFrameRead16
    cmp #$3442                     ; "B4"
    bne Vm_SourceFrameLookup__header_bad
    ldy #2
    jsr Vm_SourceFrameRead16
    cmp #$4446                     ; "FD"
    bne Vm_SourceFrameLookup__header_bad
    ldy #4
    jsr Vm_SourceFrameRead16
    cmp #1
    bne Vm_SourceFrameLookup__header_bad
    ldy #6
    jsr Vm_SourceFrameRead16
    cmp.l VmSourceFrame_Programs
    bne Vm_SourceFrameLookup__header_bad
    ldy #8
    jsr Vm_SourceFrameRead16
    cmp.l VmSourceFrame_Handles
    bne Vm_SourceFrameLookup__header_bad
    ldy #10
    jsr Vm_SourceFrameRead16
    bne Vm_SourceFrameLookup__header_bad
    bra Vm_SourceFrameLookup__directory
Vm_SourceFrameLookup__header_bad:
.a16
.i16
    jmp Vm_SourceFrameLookup__bad
Vm_SourceFrameLookup__directory:
.a16
.i16
    ; Minimum = header + counts + every program's handle directory. Checked
    ; addition prevents cached counts from wrapping a small descriptor.
    lda.l VmSourceFrame_Handles
    asl a
    clc
    adc #24
    sta.l VmSourceFrame_Minimum
    ldx #0
Vm_SourceFrameLookup__program:
.a16
.i16
    txa
    cmp.l VmSourceFrame_Program
    bne Vm_SourceFrameLookup__add_directory
    lda.l VmSourceFrame_Minimum
    sta.l VmSourceFrame_Directory
Vm_SourceFrameLookup__add_directory:
.a16
.i16
    lda.l VmSourceFrame_Handles
    asl a
    clc
    adc.l VmSourceFrame_Minimum
    bcs Vm_SourceFrameLookup__layout_bad
    sta.l VmSourceFrame_Minimum
    inx
    txa
    cmp.l VmSourceFrame_Programs
    bcc Vm_SourceFrameLookup__program
    lda.l VmSourceFrame_Bytes
    cmp.l VmSourceFrame_Minimum
    bcc Vm_SourceFrameLookup__layout_bad
    lda.l VmSourceFrame_Handle
    dec a
    asl a
    clc
    adc #24
    tay
    jsr Vm_SourceFrameRead16
    sta.l VmSourceFrame_Count
    cmp.l VmSourceFrame_Frame
    beq Vm_SourceFrameLookup__layout_bad
    bcc Vm_SourceFrameLookup__layout_bad
    lda.l VmSourceFrame_Handle
    dec a
    asl a
    clc
    adc.l VmSourceFrame_Directory
    tay
    jsr Vm_SourceFrameRead16
    cmp #$FFFF
    beq Vm_SourceFrameLookup__ok     ; valid foreign/default-script handle
    cmp.l VmSourceFrame_Minimum
    bcc Vm_SourceFrameLookup__layout_bad
    sta.l VmSourceFrame_Directory
    lda.l VmSourceFrame_Count
    asl a
    bcs Vm_SourceFrameLookup__layout_bad
    clc
    adc.l VmSourceFrame_Directory
    bcs Vm_SourceFrameLookup__layout_bad
    cmp.l VmSourceFrame_Bytes
    beq Vm_SourceFrameLookup__entry
    bcc Vm_SourceFrameLookup__entry
Vm_SourceFrameLookup__layout_bad:
.a16
.i16
    jmp Vm_SourceFrameLookup__bad
Vm_SourceFrameLookup__entry:
.a16
.i16
    lda.l VmSourceFrame_Frame
    asl a
    clc
    adc.l VmSourceFrame_Directory
    tay
    jsr Vm_SourceFrameRead16
    cmp #$FFFF
    beq Vm_SourceFrameLookup__ok
    cmp.l VmState_InstrCount
    bcs Vm_SourceFrameLookup__bad
    sta.l VmSourceFrame_Entry
Vm_SourceFrameLookup__ok:
.a16
.i16
    clc
    rts
Vm_SourceFrameLookup__bad:
.a16
.i16
    sec
    lda #VMERR_BAD_NATIVE
    rts

; All call sites prove Y+2 within Bytes and Base+Bytes within the ROM bank.
; Preserve Y/DBR; stack-relative indirect addressing never borrows DP.
Vm_SourceFrameRead16:
.a16
.i16
    phb
    lda.l VmSourceFrame_Base
    pha
    sep #$20
.a8
    lda.l VmSourceFrame_Bank
    pha
    plb
    rep #$20
.a16
    lda (1,s),y
    sta.l VmSourceFrame_Read
    pla
    plb
    lda.l VmSourceFrame_Read
    rts
