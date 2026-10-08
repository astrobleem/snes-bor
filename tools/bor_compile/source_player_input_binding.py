"""Bind native history to real source role pointers and typed entity direction.

Storage is supplied by an exclusive caller lease; no production overlay is
implicitly allocated. Entity movetime storage belongs to the same lifetime
owner and must be initialized at birth, including non-player entities.
"""
import re


def emit(rows,work,shadow,movetimes,owner,magic,symbols):
    extents=((rows,1024),(work,32),(shadow,64),(movetimes,512),(owner,2))
    for i,(a,n)in enumerate(extents):
        if not 0<=a<=0x1000000-n:raise ValueError('PLAYER_INPUT_BINDING_EXTENT')
        for b,m in extents[i+1:]:
            if a<b+m and b<a+n:raise ValueError('PLAYER_INPUT_BINDING_OVERLAP')
    code='''
PlayerHistoryBinding_Refresh:
.a16
.i16
 php
 rep #$31
 pha
 phx
 phy
 lda.l O
 cmp #M
 beq PlayerHistoryBinding_Snapshot
 jmp PlayerHistoryBinding_Fault
PlayerHistoryBinding_Snapshot:
.a16
.i16
 lda.l VmSourceInput_Ready
 cmp #$B4C2
 beq PlayerHistoryBinding_Count
 jmp PlayerHistoryBinding_Fault
PlayerHistoryBinding_Count:
.a16
.i16
 lda.l VmSourceInput_Count
 dec a
 cmp #4
 bcc PlayerHistoryBinding_Rows
 jmp PlayerHistoryBinding_Fault
PlayerHistoryBinding_Rows:
.a16
.i16
 ldx #0
PlayerHistoryBinding_ValidateRow:
.a16
.i16
 lda.l R+234,x
 beq PlayerHistoryBinding_Step
 jmp PlayerHistoryBinding_Fault
PlayerHistoryBinding_Step:
.a16
.i16
 lda.l R+232,x
 cmp #27
 bcc PlayerHistoryBinding_NextValidation
 jmp PlayerHistoryBinding_Fault
PlayerHistoryBinding_NextValidation:
.a16
.i16
 txa
 clc
 adc #256
 tax
 cpx #1024
 bne PlayerHistoryBinding_ValidateRow
 lda #0
 sta.l W
PlayerHistoryBinding_Port:
.a16
.i16
 lda.l W
 asl a
 asl a
 tax
 lda.l $43FD84,x
 sta.l SourceRetirement4086_ArgLo
 lda.l $43FD86,x
 sta.l SourceRetirement4086_ArgHi
 jsl SourceRetirement4086_ResolvePointer
 bcc PlayerHistoryBinding_Resolved
 jmp PlayerHistoryBinding_Fault
PlayerHistoryBinding_Resolved:
.a16
.i16
 sta.l W+2
 lda.l W
 asl a
 asl a
 asl a
 asl a
 tax
 lda.l W+2
 sta.l H+12,x
 cmp #$FFFF
 bne PlayerHistoryBinding_Present
 lda #0
 sta.l H,x
 sta.l H+2,x
 sta.l H+4,x
 sta.l H+6,x
 sta.l H+8,x
 sta.l H+10,x
 jmp PlayerHistoryBinding_NextPort
PlayerHistoryBinding_Present:
.a16
.i16
 lda.l SourceRetirement4086_ArgLo
 sta.l H+8,x
 lda.l SourceRetirement4086_ArgHi
 sta.l H+10,x
 lda.l W+2
 asl a
 asl a
 tax
 lda.l T,x
 sta.l W+4
 lda.l T+2,x
 sta.l W+6
 lda.l SourceRetirement4086_ArgLo
 tax
 lda.l $410018,x
 cmp #1
 beq PlayerHistoryBinding_DirectionTag
 jmp PlayerHistoryBinding_Fault
PlayerHistoryBinding_DirectionTag:
.a16
.i16
 lda.l $41001A,x
 beq PlayerHistoryBinding_IndexTag
 jmp PlayerHistoryBinding_Fault
PlayerHistoryBinding_IndexTag:
.a16
.i16
 lda.l $410028,x
 cmp #1
 beq PlayerHistoryBinding_IndexReserved
 jmp PlayerHistoryBinding_Fault
PlayerHistoryBinding_IndexReserved:
.a16
.i16
 lda.l $41002A,x
 ora.l $41002E,x
 beq PlayerHistoryBinding_IndexValue
 jmp PlayerHistoryBinding_Fault
PlayerHistoryBinding_IndexValue:
.a16
.i16
 lda.l $41002C,x
 cmp.l W
 beq PlayerHistoryBinding_Token
 jmp PlayerHistoryBinding_Fault
PlayerHistoryBinding_Token:
.a16
.i16
 lda.l $410000,x
 cmp.l SourceRetirement4086_ArgLo
 beq PlayerHistoryBinding_TokenHigh
 jmp PlayerHistoryBinding_Fault
PlayerHistoryBinding_TokenHigh:
.a16
.i16
 lda.l $410002,x
 cmp.l SourceRetirement4086_ArgHi
 beq PlayerHistoryBinding_Capture
 jmp PlayerHistoryBinding_Fault
PlayerHistoryBinding_Capture:
.a16
.i16
 lda.l $41001C,x
 sta.l W+8
 lda.l $41001E,x
 sta.l W+10
 lda.l W
 asl a
 asl a
 asl a
 asl a
 tax
 lda.l W+4
 sta.l H,x
 lda.l W+6
 sta.l H+2,x
 lda.l W+8
 sta.l H+4,x
 lda.l W+10
 sta.l H+6,x
PlayerHistoryBinding_NextPort:
.a16
.i16
 lda.l W
 inc a
 sta.l W
 cmp #4
 beq PlayerHistoryBinding_Publish
 jmp PlayerHistoryBinding_Port
PlayerHistoryBinding_Publish:
.a16
.i16
'''
    for i in range(4):
        row=256*i;h=16*i
        for dest,src in ((236,0),(238,2),(244,4),(246,6),(248,8),(250,10)):
            code+=f' lda.l H+{h+src}\n sta.l R+{row+dest}\n'
        code+=f''' lda.l H+{h+12}
 cmp #$FFFF
 beq PlayerHistoryBinding_Absent{i}
 lda #1
 bra PlayerHistoryBinding_SetPresent{i}
PlayerHistoryBinding_Absent{i}:
.a16
.i16
 lda #0
PlayerHistoryBinding_SetPresent{i}:
.a16
.i16
 sta.l R+{row+240}
 lda #0
 sta.l R+{row+242}
'''
    code+=''' jsl PlayerHistory_Refresh
 bcc PlayerHistoryBinding_WriteBack
 jmp PlayerHistoryBinding_Fault
PlayerHistoryBinding_WriteBack:
.a16
.i16
'''
    for i in range(4):
        row=256*i;h=16*i
        code+=f''' lda.l H+{h+12}
 cmp #$FFFF
 beq PlayerHistoryBinding_NoWrite{i}
 asl a
 asl a
 tax
 lda.l R+{row+236}
 sta.l T,x
 lda.l R+{row+238}
 sta.l T+2,x
PlayerHistoryBinding_NoWrite{i}:
.a16
.i16
'''
    code+=''' ply
 plx
 pla
 plp
 clc
 rtl
PlayerHistoryBinding_Fault:
.a16
.i16
 ply
 plx
 pla
 plp
 sec
 rtl
'''
    values=dict(R=rows,W=work,H=shadow,T=movetimes,O=owner,M=magic)
    for name in ('VmSourceInput_Ready','VmSourceInput_Count','SourceRetirement4086_ArgLo','SourceRetirement4086_ArgHi','SourceRetirement4086_ResolvePointer'):
        values[name]=symbols[name]
    for name,value in values.items():code=re.sub(r'\b'+name+r'\b',str(value),code)
    return code
