"""Validate both mutable animation rows with bounded register cursors.

Existing Apply checked row geometry and paired B4FE before this continuation.
Every handle, including zero, remains checked. Success resumes the unchanged
original inheritance/copy loop; failure uses its original stack unwind.
"""
import re


def emit(symbols,copy_loop=False):
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
    if copy_loop:
        code+="""ModelAnimationFast_Copy:
.a16
.i16
 lda.l SourceModelAnimationCopy4086_OldOffset
 tax
 clc
 adc.l SourceModelAnimationCopy4086_RowBytes
 sta.l SourceModelAnimationCopy4086_Offset
 lda.l SourceModelAnimationCopy4086_NewOffset
 tay
ModelAnimationFast_CopyLoop:
.a16
.i16
 phx
 tyx
 lda.l $43C000,x
 bne ModelAnimationFast_CopyPopNext
 plx
 lda.l $43C000,x
 beq ModelAnimationFast_CopyNext
 sta.l SourceModelAnimationCopy4086_Candidate
 phx
 dec a
 asl a
 asl a
 asl a
 clc
 adc #18
 clc
 adc.l SourceUpdateFrame4086_Base
 tax
 phb
 sep #$20
.a8
 lda.l SourceUpdateFrame4086_Bank
 pha
 plb
 rep #$20
.a16
 lda.w $0000,x
 plb
 ora #0
 beq ModelAnimationFast_CopyPopNext
 tyx
 lda.l SourceModelAnimationCopy4086_Candidate
 sta.l $43C000,x
ModelAnimationFast_CopyPopNext:
.a16
.i16
 plx
ModelAnimationFast_CopyNext:
.a16
.i16
 inx
 inx
 iny
 iny
 txa
 cmp.l SourceModelAnimationCopy4086_Offset
 bcc ModelAnimationFast_CopyLoop
 lda.l SourceModelAnimationCopy4086_RowBytes
 sta.l SourceModelAnimationCopy4086_Index
ModelAnimationFast_CopyDone:
.a16
.i16
 jml COPYDONE
"""
        code=code.replace('COPYDONE',str(symbols['SourceModelAnimationCopy4086_Done']))
    code=code.replace('BAD',str(symbols['SourceModelAnimationCopy4086_Bad'])).replace('CONTINUE',str(symbols['SourceModelAnimationCopy4086_Branch_30']))
    for name in sorted(symbols,key=len,reverse=True):
        if name.startswith('Source'):code=re.sub(r'\b'+name+r'\b',str(symbols[name]),code)
    return code
