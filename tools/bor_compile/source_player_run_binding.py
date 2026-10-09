"""Capture oldrunning and the entry player row, then cancel from fresh state."""
import re


def emit(work,run,tuple_work,ground,binding,history,input_owner,input_magic):
    extents=((work,32),(run,48),(tuple_work,64),(ground,128),(binding,32),(history,1024),(input_owner,2))
    for i,(a,n)in enumerate(extents):
        if not 0<=a<=0x1000000-n:raise ValueError('RUN_BINDING_EXTENT')
        if any(a<b+m and b<a+n for b,m in extents[i+1:]):raise ValueError('RUN_BINDING_OVERLAP')
    if history&255 or not 1<=input_magic<=65535:raise ValueError('RUN_BINDING_INPUT_ABI')
    code='''
SourceRunBinding_CaptureEntry:
.a16
.i16
 php
 rep #$39
 pha
 phx
 phy
 lda.l W
 cmp #$B681
 bne SourceRunBinding_Bad
 lda.l W+2
 beq SourceRunBinding_Capture
 cmp #2
 bne SourceRunBinding_Bad
SourceRunBinding_Capture:
.a16
.i16
 jsl GroundBinding_Capture
 bcs SourceRunBinding_Bad
 lda.l B+4
 sta.l W+4
 lda.l B+8
 tax
 lda.l $414028,x
 cmp #1
 bne SourceRunBinding_Bad
 lda.l $41402A,x
 ora.l $41402E,x
 bne SourceRunBinding_Bad
 lda.l $41402C,x
 cmp #4
 bcs SourceRunBinding_Bad
 sta.l W+6
 lda.l G+24
 sta.l W+8
 lda.l G+26
 sta.l W+10
 lda #1
 sta.l W+2
 jmp SourceRunBinding_Good
SourceRunBinding_Cancel:
.a16
.i16
 php
 rep #$39
 pha
 phx
 phy
 lda.l W
 cmp #$B681
 bne SourceRunBinding_Bad
 lda.l W+2
 cmp #1
 bne SourceRunBinding_Bad
 lda.l O
 cmp #MAGIC
 bne SourceRunBinding_Bad
 lda.l R
 cmp #$B677
 bne SourceRunBinding_Bad
 lda.l R+2
 beq SourceRunBinding_Current
 cmp #2
 bne SourceRunBinding_Bad
SourceRunBinding_Current:
.a16
.i16
 lda.l B+4
 cmp.l W+4
 bne SourceRunBinding_Bad
 lda.l W+6
 cmp #4
 bcs SourceRunBinding_Bad
 jsl GroundBinding_Capture
 bcs SourceRunBinding_Bad
 lda.l W+4
 sta.l T+4
 jsl SourceRunTuple_Read
 bcs SourceRunBinding_Bad
 lda.l G+24
 sta.l R+4
 lda.l G+26
 sta.l R+6
 lda.l W+8
 sta.l R+8
 lda.l W+10
 sta.l R+10
 lda.l T+32
 sta.l R+12
 lda.l T+34
 sta.l R+14
 lda.l W+6
 xba
 tax
 lda.l H+216,x
 sta.l R+16
 lda.l H+218,x
 sta.l R+18
 lda.l G+52
 sta.l R+20
 lda.l G+54
 sta.l R+22
 lda.l G+56
 sta.l R+24
 lda.l G+58
 sta.l R+26
 jsl SourcePlayerRun_Execute
 bcs SourceRunBinding_Bad
 ; No callback can intervene between the fresh capture and publication.
 lda.l B+12
 tax
 lda.l R+28
 sta.l $42F404,x
 sta.l G+24
 lda.l R+30
 sta.l $42F406,x
 sta.l G+26
 lda #2
 sta.l W+2
SourceRunBinding_Good:
.a16
.i16
 ply
 plx
 pla
 plp
 clc
 rtl
SourceRunBinding_Bad:
.a16
.i16
 lda #4
 sta.l W+2
 ply
 plx
 pla
 plp
 sec
 rtl
'''
    values=dict(W=work,R=run,T=tuple_work,G=ground,B=binding,H=history,O=input_owner,MAGIC=input_magic)
    for k,v in values.items():code=re.sub(r'\b'+k+r'\b',str(v),code)
    serial=0
    def far(m):
        nonlocal serial
        serial+=1;skip='SourceRunBinding_Guard'+str(serial)
        return ' '+dict(beq='bne',bne='beq',bcs='bcc')[m[1]]+' '+skip+'\n jmp SourceRunBinding_Bad\n'+skip+':\n.a16\n.i16'
    return re.sub(r' (bne|beq|bcs) SourceRunBinding_Bad',far,code)
