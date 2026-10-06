"""Generic palette IRQ gate ABI, emitted outside bank zero.

The IRQ vector reuses the existing Vm_Fetch JSL/RTS gateway. Ordinary fetches
must run with I=0 whenever this gateway is installed; the source-world owner must
prove that invariant. NMI inserts an extra hardware return frame so the
existing bank-zero Core_Nmi_Play/RTI sequence reaches a post-NMI setup hook.
No production installation or admission is implied by emitting this code.
"""

READY=0x7ff840
NMI_FAST=0xa78000
IRQ_FAST=0xa79000
AFTER_FAST=0xa7b000


def emit():
    return '''
SourceRaster_Ready = $7FF840
SourceRaster_Row = $7FF842
SourceRaster_TargetBase = $7FF844
SourceRaster_TargetBank = $7FF846
SourceRaster_PayloadBase = $7FF848
SourceRaster_PayloadBank = $7FF84A
SourceRaster_Bytes = $7FF84C
SourceRaster_InitialBase = $7FF84E
SourceRaster_InitialBank = $7FF850
SourceRaster_BaseEnable = $7FF852
SourceRaster_Active = $7FF854
SourceRaster_Fault = $7FF856
SourceRaster_OriginalA = $7FF858
SourceRaster_Frames = $7FF85A
SourceRaster_Restoring = $7FF85C
SourceRaster_Targets = $7FF900
SourceRasterNmiFast = $A78000
SourceRasterIrqFast = $A79000
SourceRasterAfterFast = $A7B000

.bank 39
.org $8000
SourceRasterNmiGate:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phb
    lda.l SourceRaster_Ready
    cmp #$B4B0
    beq SourceRasterNmiOwned
    plb
    plx
    pla
    plp
    jml StageWater_Nmi
SourceRasterNmiOwned:
.a16
.i16
    jsl StageWater_Nmi
    tsc
    sec
    sbc #4
    tcs
    sep #$20
.a8
    ; Shift saved DBR/X/A/P and the gateway's JSL return down four bytes.
    ; Ascending copy order preserves each source before it is overwritten.
    lda 5,s
    sta 1,s
    lda 6,s
    sta 2,s
    lda 7,s
    sta 3,s
    lda 8,s
    sta 4,s
    lda 9,s
    sta 5,s
    lda 10,s
    sta 6,s
    lda 11,s
    sta 7,s
    lda 12,s
    sta 8,s
    lda 13,s
    sta 9,s
    lda 6,s
    sta 10,s
    lda #$00
    sta 11,s
    lda #$B0
    sta 12,s
    lda #$A7
    sta 13,s
    rep #$30
.a16
.i16
    plb
    plx
    pla
    plp
    rtl

.org $9000
SourceRasterIrqGate:
.a16
.i16
    ; Entered with original A and PHP already saved by the fetch prologue.
    phx
    lda.l $004211
    lda.l SourceRaster_Row
    cmp #224
    bcs SourceRasterIrqDisable
    tax
    inc a
    sta.l SourceRaster_Row
    sta.l $004209
    sep #$20
.a8
    lda.l SourceRaster_Targets,x
    sta.l $002121
    lda.l SourceRaster_Bytes
    sta.l $004375
    lda #$80
    sta.l $00420B
    bra SourceRasterIrqRestore
SourceRasterIrqDisable:
.a16
.i16
    sep #$20
.a8
    lda.l SourceRaster_BaseEnable
    sta.l $004200
SourceRasterIrqRestore:
.a8
.i16
    rep #$30
.a16
    plx
    pla
    sta.l SourceRaster_OriginalA
    tsc
    clc
    adc #4
    tcs
    lda.l SourceRaster_OriginalA
SourceRasterIrqReturn:
.a16
.i16
    rti

.org $B000
SourceRasterNmiAfter:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phb
    lda #0
    sta.l SourceRaster_Active
    sta.l SourceRaster_Row
    lda #1
    sta.l SourceRaster_Restoring
    lda.l SourceRaster_Ready
    cmp #$B4B0
    beq SourceRasterAfterReady
    jmp SourceRasterAfterDisabled
SourceRasterAfterReady:
.a16
.i16
    lda.l SourceRaster_Fault
    beq SourceRasterAfterValid
    jmp SourceRasterAfterDisabled
SourceRasterAfterValid:
.a16
.i16
    ; The immutable descriptor/CRC, palette slot bounds and ownership are
    ; validated by the installer. This hook performs no allocation.
    sep #$20
.a8
    lda.l SourceRaster_BaseEnable
    sta.l $004200
    lda #0
    sta.l $002181
    lda #$F9
    sta.l $002182
    lda #1
    sta.l $002183
    lda #0
    sta.l $004370
    lda #$80
    sta.l $004371
    rep #$20
.a16
    lda.l SourceRaster_TargetBase
    sta.l $004372
    lda #224
    sta.l $004375
    sep #$20
.a8
    lda.l SourceRaster_TargetBank
    sta.l $004374
    lda #$80
    sta.l $00420B
    lda #4
    sta.l $002121
    lda #0
    sta.l $004370
    lda #$22
    sta.l $004371
    rep #$20
.a16
    lda.l SourceRaster_InitialBase
    sta.l $004372
    lda #472
    sta.l $004375
    sep #$20
.a8
    lda.l SourceRaster_InitialBank
    sta.l $004374
    lda #$80
    sta.l $00420B
    rep #$20
.a16
    lda.l SourceRaster_PayloadBase
    sta.l $004372
    lda.l SourceRaster_Bytes
    sta.l $004375
    sep #$20
.a8
    lda.l SourceRaster_PayloadBank
    sta.l $004374
    rep #$20
.a16
    lda.l SourceRaster_Frames
    inc a
    sta.l SourceRaster_Frames
    lda #1
    sta.l SourceRaster_Active
    lda #0
    sta.l $004209
    sep #$20
.a8
    lda.l SourceRaster_BaseEnable
    ora #$30
    sta.l $004200
    bra SourceRasterAfterRestore
SourceRasterAfterDisabled:
.a16
.i16
    sep #$20
.a8
    lda.l SourceRaster_BaseEnable
    sta.l $004200
SourceRasterAfterRestore:
.a8
.i16
    lda #0
    sta.l SourceRaster_Restoring
    rep #$30
.a16
    plb
    plx
    pla
    plp
SourceRasterAfterReturn:
.a16
.i16
    rti
'''


def fetch_prologue():
    """Replace PHP/REP; installation requires all ordinary fetches to have I=0.

    Testing the lease on every IRQ costs the transfer window. This prologue
    is an opt-in foreign-profile gateway, not an unconditional static-path edit.
    The installer must prove the I=0 invariant before redirecting either vector.
    """
    return '''
    php
    rep #$31
    pha
    lda 3,s
    and #4
    beq SourceRasterFetchOrdinary
    jml SourceRasterIrqFast
SourceRasterFetchOrdinary:
.a16
.i16
    pla
'''
