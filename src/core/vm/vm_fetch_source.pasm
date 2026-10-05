; Generic immutable-ROM or legacy-RAM instruction fetch, outside bank 0.
; ROM mode requires an explicitly installed $B48E descriptor. Base+the
; complete instruction table must stay in one ROM bank; compiler/loader owns
; that checked lease. No solver or actor identity is consulted here.
VmSourceInstr_Base = $7FF63C       ; .dw ROM address, >=$8000
VmSourceInstr_Bank = $7FF63E       ; .db ROM bank
VmSourceInstr_Ready = $7FF640      ; .dw $B48E, else legacy WRAM fetch

Vm_FetchSourceInit:
.a16
.i16
    php
    rep #$31
    phx
    lda #0
    sta.l VmSourceInstr_Ready
    sta.l VmNativeVariant_ContextValid
    sta.l VmSourceEntity_Ready
    ; Dynamic pool headers need an actual cold-boot owner. Older string
    ; fixtures cleared them through debug writes; random WRAM is not free.
    ldx #0
Vm_FetchSourceInit__pool:
.a16
.i16
    lda #0
    sta.l VmStrPool_Wram,x
    txa
    clc
    adc #VMSTRPOOL_OBJ_SIZE
    tax
    cmp #VMSTRPOOL_OBJ_COUNT*VMSTRPOOL_OBJ_SIZE
    bcc Vm_FetchSourceInit__pool
    plx
    plp
    rtl

Vm_FetchSource:
.a16
.i16
    php
    rep #$31
    lda.l VmState_Ip
    cmp.l VmState_InstrCount
    bcc Vm_FetchSource__inrange
    plp
    sec
    lda #VMERR_BAD_JUMP
    rtl
Vm_FetchSource__inrange:
.a16
.i16
    lda.l VmSourceInstr_Ready
    cmp #$B48E
    beq Vm_FetchSource__rom
    lda.l VmState_Ip
    asl a
    asl a
    asl a
    clc
    adc.l VmPriv_InstrOff
    tax
    sep #$20
.a8
    lda.l VmCode_Wram,x
    sta.l VmPriv_Opcode
    inx
    lda.l VmCode_Wram,x
    sta.l VmPriv_Flags
    inx
    rep #$31
.a16
.i16
    lda.l VmCode_Wram,x
    sta.l VmPriv_A
    inx
    inx
    lda.l VmCode_Wram,x
    sta.l VmPriv_B
    inx
    inx
    lda.l VmCode_Wram,x
    sta.l VmPriv_C
    plp
    clc
    rtl
Vm_FetchSource__rom:
.a16
.i16
    phy
    phb
    lda.l VmState_Ip
    asl a
    asl a
    asl a
    clc
    adc.l VmSourceInstr_Base
    pha                         ; temporary 16-bit pointer at stack+1
    sep #$20
.a8
    lda.l VmSourceInstr_Bank
    pha
    plb                         ; indirect data bank only; PBR unaffected
    ldy #0
    lda (1,s),y
    sta.l VmPriv_Opcode
    iny
    lda (1,s),y
    sta.l VmPriv_Flags
    iny
    rep #$31
.a16
.i16
    lda (1,s),y
    sta.l VmPriv_A
    iny
    iny
    lda (1,s),y
    sta.l VmPriv_B
    iny
    iny
    lda (1,s),y
    sta.l VmPriv_C
    pla                         ; remove pointer, then restore caller bank/Y
    plb
    ply
    plp
    clc
    rtl
