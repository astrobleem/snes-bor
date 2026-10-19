"""Native 65816 routine for decoding one checked WFR1 indexed-image row.

WFR1 is emitted by source_warm_frame_assets.encode_image: ten-byte header,
`height+1` little-endian u16 payload-relative row offsets, then row-local
(count,index) byte pairs. The entry takes A=row and X=cache slot. Control
fields live at control+$20 (24-bit C0..FF full-bank HiROM/SA1 alias pointer plus zero high byte),
control+$24 (exact image byte extent), and control+$28/$2a (expected width /
height). It decodes exactly one row to an eight-slot, 512-byte-per-slot cache.

The routine does not call any source/foreign work. Invalid input returns C=1;
the selected private cache row may be partially written on malformed RLE.
Caller registers, DP, DBR and stack are restored; only carry reports status.
"""
from __future__ import annotations

import hashlib


DEFAULT_CONTROL = 0x7E9400
DEFAULT_CACHE = 0x7E8400
FRAME_BYTES = 48
SLOT_BYTES = 512
SLOT_COUNT = 8
MAX_WIDTH = 511
MAX_HEIGHT = 255
MAX_IMAGE_BYTES = 0x7FFF


def emit(*, control_base=DEFAULT_CONTROL, output_cache=DEFAULT_CACHE):
    """Emit the bounded WFR1 DecodeRow routine for the fixed leased buffer."""
    if control_base != DEFAULT_CONTROL or output_cache != DEFAULT_CACHE:
        raise ValueError('WARM_RLE_FIXED_NATIVE_LEASE')
    text = r'''; Native WFR1 row decoder. A=row, X=cache slot 0..7; C is the only result.
WarmRle_DecodeRow:
.a16
.i16
 php
 rep #$38 ; A/X 16-bit and binary arithmetic regardless of caller D flag
 pha
 phx
 phy
 phb
 phd
 tsc
 sec
 sbc #48
 tcs
 inc a
 tcd
 ; Save the two entry inputs in the private stack-DP frame.
 lda $37 ; original A is saved above the frame (PHP+PHA+PHX+PHY+PHB+PHD)
 sta $14
 stx $16
 ; No source pointer is dereferenced until all CPU address bounds pass.
 lda.l $7E9420
 sta $00
 lda.l $7E9422
 sta $02
 and #$FF00
 beq WarmRle_PointerHighOK
 jmp WarmRle_Bad
WarmRle_PointerHighOK:
 lda $02
 and #$00FF
 cmp #$00C0
 bcs WarmRle_BankOK
WarmRle_PointerBad:
 jmp WarmRle_Bad
WarmRle_BankOK:
 lda.l $7E9424
 sta $04
 beq WarmRle_ExtentBad
 cmp #$8000
 bcc WarmRle_ExtentOK
WarmRle_ExtentBad:
 jmp WarmRle_Bad
WarmRle_ExtentOK:
 ; This integration admits the C0..FF full-bank HiROM/SA1 ROM alias. Permit
 ; either 32KiB half but reject a read that crosses its half-slot boundary.
 lda $00
 and #$7FFF
 clc
 adc $04
 cmp #$8001
 bcc WarmRle_SlotOK
 jmp WarmRle_Bad
WarmRle_SlotOK:
 lda.l $7E9428
 cmp #1
 bcs WarmRle_WidthNonzero
 jmp WarmRle_Bad
WarmRle_WidthNonzero:
 cmp #512
 bcc WarmRle_WidthOK
 jmp WarmRle_Bad
WarmRle_WidthOK:
 sta $06
 lda.l $7E942A
 cmp #1
 bcs WarmRle_HeightNonzero
 jmp WarmRle_Bad
WarmRle_HeightNonzero:
 cmp #256
 bcc WarmRle_HeightOK
 jmp WarmRle_Bad
WarmRle_HeightOK:
 sta $08
 lda $16
 cmp #8
 bcc WarmRle_SlotIndexOK
 jmp WarmRle_Bad
WarmRle_SlotIndexOK:
 lda $14
 cmp $08
 bcc WarmRle_RowOK
 jmp WarmRle_Bad
WarmRle_RowOK:
 ; Header and expected geometry must agree exactly.
 ldy #0
 lda [$00],y
 cmp #$4657 ; "WF"
 beq WarmRle_MagicFirstOK
 jmp WarmRle_Bad
WarmRle_MagicFirstOK:
 ldy #2
 lda [$00],y
 cmp #$3152 ; "R1"
 beq WarmRle_MagicOK
 jmp WarmRle_Bad
WarmRle_MagicOK:
 ldy #4
 lda [$00],y
 cmp $06
 beq WarmRle_HeaderWidthOK
 jmp WarmRle_Bad
WarmRle_HeaderWidthOK:
 ldy #6
 lda [$00],y
 cmp $08
 beq WarmRle_HeaderHeightOK
 jmp WarmRle_Bad
WarmRle_HeaderHeightOK:
 ldy #8
 lda [$00],y
 beq WarmRle_PayloadBad
 cmp #$8000
 bcc WarmRle_PayloadOK
WarmRle_PayloadBad:
 jmp WarmRle_Bad
WarmRle_PayloadOK:
 sta $0A
 ; Payload start is header(10) + 2*(height+1) == 12 + 2*height.
 lda $08
 asl a
 clc
 adc #12
 sta $0C
 clc
 adc $0A
 cmp $04
 beq WarmRle_ExtentExact
 jmp WarmRle_Bad
WarmRle_ExtentExact:
 ; Validate the global first and terminal offsets before row lookup.
 ldy #10
 lda [$00],y
 beq WarmRle_FirstOffsetOK
 jmp WarmRle_Bad
WarmRle_FirstOffsetOK:
 lda $0C
 sec
 sbc #2
 tay
 lda [$00],y
 cmp $0A
 beq WarmRle_LastOffsetOK
 jmp WarmRle_Bad
WarmRle_LastOffsetOK:
 ; Read only the requested row's two endpoints.
 lda $14
 asl a
 clc
 adc #10
 tay
 lda [$00],y
 sta $0E
 iny
 iny
 lda [$00],y
 sta $10
 lda $0E
 cmp $0A
 bcc WarmRle_RowStartInside
 jmp WarmRle_Bad
WarmRle_RowStartInside:
 lda $10
 cmp $0E
 bcc WarmRle_RowOrderBad
 beq WarmRle_RowOrderBad
 lda $10
 cmp $0A
 bcc WarmRle_RowEndInside
 beq WarmRle_RowEndInside
WarmRle_RowOrderBad:
 jmp WarmRle_Bad
WarmRle_RowEndInside:
 sec
 sbc $0E
 and #1
 beq WarmRle_RowPairsEven
 jmp WarmRle_Bad
WarmRle_RowPairsEven:
 lda $0E
 sta $12
 lda #0
 sta $1A
 ; Compute target byte offset = slot*512 + output column.
 lda $16
 asl a
 asl a
 asl a
 asl a
 asl a
 asl a
 asl a
 asl a
 asl a
 sta $18
WarmRle_RunLoop:
 lda $12
 cmp $10
 beq WarmRle_RowDecoded
 bcc WarmRle_HasPair
 jmp WarmRle_Bad
WarmRle_HasPair:
 clc
 adc #2
 cmp $10
 bcc WarmRle_PairFits
 beq WarmRle_PairFits
 jmp WarmRle_Bad
WarmRle_PairFits:
 lda $0C
 clc
 adc $12
 tay
 lda [$00],y
 and #$00FF
 beq WarmRle_RunBad
 sta $1C
 iny
 sep #$20
 lda [$00],y
 sta $1E
 rep #$20
 lda $1A
 clc
 adc $1C
 cmp $06
 bcc WarmRle_RunWithinWidth
 beq WarmRle_RunWithinWidth
WarmRle_RunBad:
 jmp WarmRle_Bad
WarmRle_RunWithinWidth:
WarmRle_RunWrite:
 lda $1C
 beq WarmRle_RunDone
 lda $18
 clc
 adc $1A
 tax
 sep #$20
 lda $1E
 sta.l $7E8400,x
 rep #$20
 inc $1A
 dec $1C
 jmp WarmRle_RunWrite
WarmRle_RunDone:
 lda $12
 clc
 adc #2
 sta $12
 jmp WarmRle_RunLoop
WarmRle_RowDecoded:
 lda $1A
 cmp $06
 beq WarmRle_Good
 jmp WarmRle_Bad
WarmRle_Good:
 tsc
 clc
 adc #48
 tcs
 pld
 plb
 ply
 plx
 pla
 plp
 clc
 rtl
WarmRle_Bad:
 tsc
 clc
 adc #48
 tcs
 pld
 plb
 ply
 plx
 pla
 plp
 sec
 rtl
'''
    return text


def evidence(source= None):
    """Small immutable code evidence; assembly is returned by `emit()`."""
    code = emit()
    return dict(schema='BYOR_WARM_RLE_NATIVE_V1', control_base=DEFAULT_CONTROL,
                output_cache=DEFAULT_CACHE, slot_bytes=SLOT_BYTES, slot_count=SLOT_COUNT,
                frame_bytes=FRAME_BYTES, max_width=MAX_WIDTH, max_height=MAX_HEIGHT,
                max_image_bytes=MAX_IMAGE_BYTES, assembly_sha256=hashlib.sha256(code.encode()).hexdigest(),
                address_policy='C0..FF full-bank HiROM/SA1 CPU alias; either half allowed; rejects 32KiB-half crossing and nonzero fourth byte',
                preserves=['A','X','Y','P except carry','DP','DBR','stack'],
                failure='Carry set; selected private cache bytes may be partially written',
                no_poppy_executable_in_path=False)
