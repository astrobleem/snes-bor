"""Opt-in bank-local conservative capacity scan for the isolated MOTU owner.

Same 1,024 pending words, ref flags, temporary bitmap and decision as
early_capacity._predictor. No allocator admission or display policy changes.
The selected caller owns A16/I16, binary arithmetic and DP $3400. DBR and
stack are restored; the original A/X/Y, counters, bitmap and carry result
are retained. Native timing/certification is required before acceptance.
"""
from collections.abc import Sequence

START = 0x39B800
LIMIT = 0x39C000
PATCH = 0x39A506


def routine() -> list[str]:
    return '''
.bank 57
.org $B800
CsPredict:
.a16
.i16
 phb
 phy
 pea $4242
 plb
 plb
 lda #0
 ldx #0
CsClear:
.a16
.i16
 sta.l $003480,x
 inx
 inx
 cpx #76
 bcc CsClear
 sta $70
 sta $72
 sta $74
 ldy #0
CsMap:
.a16
.i16
 lda $C000,y
 cmp #$FFFF
 beq CsActor
 cmp #596
 bcs CsNext
 sta $76
 asl a
 tax
 lda $D000,x
 and #$8000
 beq CsNext
 phy
 lda #1
 sta $78
 lda $76
 and #15
 tay
 beq CsMaskReady
CsShift:
.a16
.i16
 asl $78
 dey
 bne CsShift
CsMaskReady:
.a16
.i16
 lda $76
 lsr a
 lsr a
 lsr a
 and #$FFFE
 tax
 lda.l $003480,x
 and $78
 bne CsSeen
 lda.l $003480,x
 ora $78
 sta.l $003480,x
 inc $74
CsSeen:
.a16
.i16
 ply
 bra CsNext
CsActor:
.a16
.i16
 inc $72
CsNext:
.a16
.i16
 iny
 iny
 cpy #2048
 bcs CsCountFree
 jmp CsMap
CsCountFree:
.a16
.i16
 lda #1024
 sta $18
 ldx #1192
CsFree:
.a16
.i16
 lda $D000,x
 and #$3FFF
 bne CsFreeNext
 inc $70
CsFreeNext:
.a16
.i16
 inx
 inx
 cpx #1536
 bcc CsFree
 ply
 plb
 lda $74
 beq CsYRetained
 ldy #0
CsYRetained:
.a16
.i16
 cmp #49
 bcs CsNotFit
 lda $72
 clc
 adc $74
 cmp $70
 bcc CsFit
 beq CsFit
CsNotFit:
.a16
.i16
 sec
 rts
CsFit:
.a16
.i16
 clc
 rts
CsCodeEnd:
.a16
.i16
'''.strip().splitlines()


def transform(source: Sequence[str], enabled: bool = True) -> list[str]:
    result = list(source)
    if not enabled:
        return result
    if any(s.strip() == 'CsPredict:' for s in result):
        raise ValueError('CAPACITY_SCAN_ALREADY_INSTALLED')
    needle = ['NbCapacityPredict:', '.a16', '.i16', 'lda #0', 'ldx #0']
    normalized = [s.strip() for s in result]
    hits = [i for i in range(len(result)-len(needle)+1)
            if normalized[i:i+len(needle)] == needle]
    if len(hits) != 1:
        raise ValueError('CAPACITY_SCAN_PINNED_ENTRY')
    i = hits[0]+3
    # Six original entry bytes become JMP + three NOPs. Every old label and
    # instruction beyond the two replaced immediates remains at its old PC.
    result[i:i+2] = [' jmp CsPredict', ' nop', ' nop', ' nop']
    return result + routine()
