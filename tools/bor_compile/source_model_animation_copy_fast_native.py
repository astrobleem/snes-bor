"""Validate both mutable animation rows with bounded register cursors.

Existing Apply checked row geometry and paired B4FE before this continuation.
Every handle, including zero, remains checked. Success resumes the unchanged
original inheritance/copy loop; failure uses its original stack unwind.
"""
import re


def emit(symbols):
    code="""ModelAnimationFast_Preflight:
.a16
.i16
 lda.l SourceModelAnimationCopy4086_OldOffset
 tax
 clc
 adc.l SourceModelAnimationCopy4086_RowBytes
 sta.l SourceModelAnimationCopy4086_Offset
 lda.l SourceModelAnimationCopy4086_NewOffset
 tay
ModelAnimationFast_Loop:
.a16
.i16
 lda.l $43C000,x
 cmp.l SourceModelAnimationCopy4086_Frames
 bcc ModelAnimationFast_OldGood
 beq ModelAnimationFast_OldGood
 jml BAD
ModelAnimationFast_OldGood:
.a16
.i16
 phx
 tyx
 lda.l $43C000,x
 cmp.l SourceModelAnimationCopy4086_Frames
 bcc ModelAnimationFast_NewGood
 beq ModelAnimationFast_NewGood
 plx
 jml BAD
ModelAnimationFast_NewGood:
.a16
.i16
 plx
 inx
 inx
 iny
 iny
 txa
 cmp.l SourceModelAnimationCopy4086_Offset
 bcc ModelAnimationFast_Loop
ModelAnimationFast_Done:
.a16
.i16
 jml CONTINUE
"""
    code=code.replace('BAD',str(symbols['SourceModelAnimationCopy4086_Bad'])).replace('CONTINUE',str(symbols['SourceModelAnimationCopy4086_Branch_30']))
    for name in sorted(symbols,key=len,reverse=True):
        if name.startswith('Source'):code=re.sub(r'\b'+name+r'\b',str(symbols[name]),code)
    return code
