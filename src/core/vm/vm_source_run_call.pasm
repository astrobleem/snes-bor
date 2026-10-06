; Foreground JSL entry into the existing bank-0 JSR VM, with zero bank-0 growth.
; The fake RTS continuation is the existing Vm_Fetch gateway. Only an active
; portal and a non-RUNNING VM can consume that continuation. Ordinary fetches
; retain their original saved P and implementation. No recursive VM execution.
; A=terminal/cooperative VM status, C=1 FAULT or rejected call. X/Y/D/DBR/P
; (except C) are preserved. Caller must handle YIELDED before acknowledging a
; world service. This portal executes bytecode; it does not bind engine APIs.
SourceVMRun4086_Ready = $7FFB30
SourceVMRun4086_Busy = $7FFB32
SourceVMRun4086_Status = $7FFB34
SourceVMRun4086_Error = $7FFB36
SourceVMRun4086_ScratchEnd = $7FFB38

SourceVMRun4086_Call:
.a16
.i16
    php
    rep #$38
    phd
    phb
    phx
    phy
    lda.l SourceVMRun4086_Ready
    cmp #$B4D7
    bne SourceVMRun4086_Rejected
    lda.l SourceVMRun4086_Busy
    bne SourceVMRun4086_Rejected
    lda.l VmNativeVariant_ContextValid
    cmp #$B48F
    bne SourceVMRun4086_Rejected
    lda.l VmState_Status
    and #$00FF
    cmp #VMSTAT_RUNNING
    beq SourceVMRun4086_Rejected
    cmp #VMSTAT_READY
    bcc SourceVMRun4086_Rejected
    cmp #VMSTAT_FAULT+1
    bcs SourceVMRun4086_Rejected
    lda #$B4D8
    sta.l SourceVMRun4086_Busy
    pea $0000
    pld
    sep #$20
.a8
    lda #0
    pha
    plb
    rep #$30
.a16
.i16
    pea Vm_Fetch-1
    jml Vm_Run
SourceVMRun4086_Rejected:
.a16
.i16
    lda #VMERR_BAD_NATIVE
    sta.l SourceVMRun4086_Error
    lda #$FFFF
    sta.l SourceVMRun4086_Status
    ply
    plx
    plb
    pld
    plp
    sec
    rtl

; Entered from Vm_FetchSource after its PHP/REP31, not by a normal JSL caller.
; Vm_Run already restored its own P and consumed the synthetic RTS address.
SourceVMRun4086_Return:
.a16
.i16
    lda.l VmState_Status
    and #$00FF
    sta.l SourceVMRun4086_Status
    lda.l VmState_Error
    sta.l SourceVMRun4086_Error
    lda #0
    sta.l SourceVMRun4086_Busy
    plp                           ; the fetch gateway's saved P
    rep #$38
    pla                           ; discard gateway JSL return PC
    sep #$20
.a8
    pla                           ; discard gateway JSL return bank
    rep #$30
.a16
.i16
    lda.l SourceVMRun4086_Status
    cmp #VMSTAT_FAULT
    beq SourceVMRun4086_Return__fault
    lda.l SourceVMRun4086_Status
    ply
    plx
    plb
    pld
    plp                           ; the source owner's saved P
    clc
    rtl
SourceVMRun4086_Return__fault:
.a16
.i16
    lda.l SourceVMRun4086_Status
    ply
    plx
    plb
    pld
    plp
    sec
    rtl
