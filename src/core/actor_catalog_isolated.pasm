; Reusable project/model/role/profile/frame catalog lookup. Native A16/I16,
; DBR=0, D=caller-owned 256-byte low WRAM. JSL/RTL, clobbers A/X/Y/P.
; Inputs A0 catalog u24, A4 project u32, A8 actor u16, AA role u16,
; AC profile u16 (1 exact,2 explicit compat), AE actual frame u16.
; Outputs B0 current frame u24, B4 count, B6 status (0 OK,1 absent,2 bad),
; B8 table u24. Clears all outputs on failure. Scratch BC..EF.
; Catalog and all frame payloads must reside within its declared single-bank
; extent. No actor names, role names, legacy state gates or host pointers.
ActorCatalog_Lookup:
    rep #$30
    .a16
    .i16
    stz $B0
    stz $B2
    stz $B4
    stz $B8
    stz $BA
    lda #2
    sta $B6
    lda $A0
    cmp #$FFF1
    bcs ActorCatalog_EarlyReturn
    ldy #0
    ldx #0
ActorCatalog_HeaderCopy:
    .a16
    .i16
    lda [$A0],y
    sta $C0,x
    iny
    iny
    inx
    inx
    cpy #16
    bcc ActorCatalog_HeaderCopy
    lda $C0
    cmp #$3543
    bne ActorCatalog_EarlyReturn
    lda $C2
    cmp #1
    bne ActorCatalog_EarlyReturn
    lda $C4
    cmp $A4
    bne ActorCatalog_EarlyReturn
    lda $C6
    cmp $A6
    bne ActorCatalog_EarlyReturn
    lda $CA
    cmp #16
    bne ActorCatalog_EarlyReturn
    lda $CE
    bne ActorCatalog_EarlyReturn
    lda $C8
    beq ActorCatalog_EarlyReturn
    cmp #2048
    bcs ActorCatalog_EarlyReturn
    asl a
    asl a
    asl a
    asl a
    clc
    adc #16
    sta $BE
    cmp $CC
    bcs ActorCatalog_EarlyReturn
    lda $CC
    dec a
    clc
    adc $A0
    bcs ActorCatalog_EarlyReturn
    lda #16
    sta $BC
    bra ActorCatalog_Scan
ActorCatalog_EarlyReturn:
    .a16
    .i16
    rtl
ActorCatalog_Scan:
    .a16
    .i16
    ldy $BC
    ldx #0
ActorCatalog_EntryCopy:
    .a16
    .i16
    lda [$A0],y
    sta $D0,x
    iny
    iny
    inx
    inx
    cpx #16
    bcc ActorCatalog_EntryCopy
    lda $D0
    cmp $A8
    bne ActorCatalog_Next
    lda $D2
    cmp $AA
    bne ActorCatalog_Next
    lda $D4
    cmp $AC
    bne ActorCatalog_Next
    cmp #1
    beq ActorCatalog_Validate
    cmp #2
    beq ActorCatalog_Validate
    rtl
ActorCatalog_Next:
    .a16
    .i16
    lda $BC
    clc
    adc #16
    sta $BC
    cmp $BE
    bcc ActorCatalog_Scan
    lda #1
    sta $B6
    rtl
ActorCatalog_Validate:
    .a16
    .i16
    lda $D6
    ora $DE
    bne ActorCatalog_EarlyReturn
    lda $DC
    cmp $A2
    bne ActorCatalog_EarlyReturn
    lda $D8
    beq ActorCatalog_EarlyReturn
    cmp #2048
    bcs ActorCatalog_EarlyReturn
    cmp $AE
    beq ActorCatalog_EarlyReturn
    bcc ActorCatalog_EarlyReturn
    asl a
    asl a
    asl a
    asl a
    asl a
    sta $E4
    lda $DA
    sec
    sbc $A0
    bcc ActorCatalog_EarlyReturn
    cmp $BE
    bcc ActorCatalog_EarlyReturn
    clc
    adc $E4
    bcs ActorCatalog_EarlyReturn
    cmp $CC
    beq ActorCatalog_Found
    bcc ActorCatalog_Found
    rtl
ActorCatalog_Found:
    .a16
    .i16
    lda $D8
    sta $B4
    lda $DA
    sta $B8
    lda $DC
    sta $BA
    sta $B2
    lda $AE
    asl a
    asl a
    asl a
    asl a
    asl a
    clc
    adc $DA
    sta $B0
    stz $B6
    rtl
