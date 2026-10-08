"""Native pinned 4086 input history. Caller supplies an exclusive memory lease.

This emitter does not reserve storage or install a gameplay owner. The caller
must supply 4 contiguous 256-byte rows, scratch and immutable combo storage.
Rows include captured entity direction/movetime; binding those to the live world
is a separate owner obligation. Refresh consumes one immutable outer snapshot.
"""
from source_player_input_4086 import *


def emit(rows, scratch, snapshot, sequence, owner, magic):
    addresses=(rows,scratch,snapshot,sequence,owner)
    if any(not isinstance(a,int) or not 0<=a<=0xffffff for a in addresses):
        raise ValueError('SOURCE_INPUT_NATIVE_ADDRESS')
    if rows&255 or (rows&65535)>64512 or (scratch&65535)>65480:
        raise ValueError('SOURCE_INPUT_NATIVE_LAYOUT')
    if not isinstance(magic,int)or not 1<=magic<=65535:raise ValueError('SOURCE_INPUT_NATIVE_MAGIC')
    extents=((rows,1024),(scratch,40),(snapshot,56),(sequence,110),(owner,2))
    if any(a+n>0x1000000 for a,n in extents):raise ValueError('SOURCE_INPUT_NATIVE_EXTENT')
    for i,(a,n)in enumerate(extents):
        for b,m in extents[i+1:]:
            if a<b+m and b<a+n:raise ValueError('SOURCE_INPUT_NATIVE_OVERLAP')
    names=dict(R=rows,S=scratch,I=snapshot,Q=sequence,O=owner,M=magic)
    code='''
PlayerHistory_Refresh:
.a16
.i16
 php
 rep #$31
 pha
 phx
 phy
 lda.l O
 cmp #M
 beq PlayerHistory_CheckSnapshot
 jmp PlayerHistory_Fault
PlayerHistory_CheckSnapshot:
.a16
.i16
 lda.l I
 cmp #$B4C2
 beq PlayerHistory_CheckCount
 jmp PlayerHistory_Fault
PlayerHistory_CheckCount:
.a16
.i16
 lda.l I+2
 dec a
 cmp #4
 bcc PlayerHistory_Validate
 jmp PlayerHistory_Fault
PlayerHistory_Validate:
.a16
.i16
 ldx #0
PlayerHistory_ValidateRow:
.a16
.i16
 lda.l R+234,x
 bne PlayerHistory_BadRow
 lda.l R+232,x
 cmp #27
 bcs PlayerHistory_BadRow
 txa
 clc
 adc #256
 tax
 cpx #1024
 bne PlayerHistory_ValidateRow
 lda #0
 sta.l S
 sta.l S+2
 sta.l S+4
 sta.l S+6
 sta.l S+8
 sta.l S+10
 lda.l I+4
 sta.l S+12
 lda.l I+6
 sta.l S+14
 jmp PlayerHistory_Row
PlayerHistory_BadRow:
.a16
.i16
 jmp PlayerHistory_Fault
PlayerHistory_Row:
.a16
.i16
 lda #0
 sta.l S+16
 sta.l S+18
 sta.l S+20
 sta.l S+22
 lda.l S+8
 lsr a
 lsr a
 lsr a
 lsr a
 lsr a
 lsr a
 lsr a
 lsr a
 cmp.l I+2
 bcs PlayerHistory_HaveControl
 lda.l S+10
 tax
 lda.l I+8,x
 sta.l S+16
 lda.l I+10,x
 sta.l S+18
 lda.l I+12,x
 sta.l S+20
 lda.l I+14,x
 sta.l S+22
PlayerHistory_HaveControl:
.a16
.i16
 lda.l S+8
 tax
'''
    for half in (0,2):
        code+=f''' lda.l S+{16+half}
 eor #$FFFF
 and.l R+{KEYS+half},x
 sta.l R+{RELEASEKEYS+half},x
 lda.l S+{16+half}
 sta.l R+{KEYS+half},x
 ora.l S+{half}
 sta.l S+{half}
 lda.l S+{20+half}
 sta.l R+{NEWKEYS+half},x
 ora.l S+{4+half}
 sta.l S+{4+half}
 lda.l R+{PLAYKEYS+half},x
 ora.l S+{20+half}
 and.l S+{16+half}
 sta.l R+{PLAYKEYS+half},x
'''
    code+=''' lda.l R+240,x
 ora.l R+242,x
 bne PlayerHistory_CheckExpiry
 jmp PlayerHistory_New
PlayerHistory_CheckExpiry:
.a16
.i16
 lda.l R+238,x
 cmp.l S+14
 bcc PlayerHistory_Clear
 beq PlayerHistory_CheckExpiryLow
 jmp PlayerHistory_New
PlayerHistory_CheckExpiryLow:
.a16
.i16
 lda.l R+236,x
 cmp.l S+12
 bcc PlayerHistory_Clear
 jmp PlayerHistory_New
PlayerHistory_Clear:
.a16
.i16
 lda #0
'''
    # Exact 27 dwords each. X remains row base; no illegal long,Y addressing.
    for off in range(0,216,2):code+=f' sta.l R+{off},x\n'
    code+=''' sta.l R+232,x
PlayerHistory_New:
.a16
.i16
 lda.l S+20
 ora.l S+22
 bne PlayerHistory_Record
 jmp PlayerHistory_NextRow
PlayerHistory_Record:
.a16
.i16
 lda.l R+240,x
 ora.l R+242,x
 beq PlayerHistory_Write
 lda.l S+12
 clc
 adc #50
 sta.l R+236,x
 lda.l S+14
 adc #0
 sta.l R+238,x
 lda.l S+20
 and #4
 beq PlayerHistory_Right
 lda.l R+244,x
 ora.l R+246,x
 beq PlayerHistory_Forward
 bra PlayerHistory_Backward
PlayerHistory_Right:
.a16
.i16
 lda.l S+20
 and #8
 beq PlayerHistory_Write
 lda.l R+244,x
 ora.l R+246,x
 bne PlayerHistory_Forward
PlayerHistory_Backward:
.a16
.i16
 lda.l S+22
 ora #$8000
 bra PlayerHistory_Relative
PlayerHistory_Forward:
.a16
.i16
 lda.l S+22
 ora #$4000
PlayerHistory_Relative:
.a16
.i16
 sta.l S+22
PlayerHistory_Write:
.a16
.i16
 lda.l R+232,x
 asl a
 asl a
 clc
 adc.l S+8
 tax
 lda.l S+12
 sta.l R,x
 lda.l S+14
 sta.l R+2,x
 lda.l S+20
 sta.l R+108,x
 lda.l S+22
 sta.l R+110,x
 lda.l S+8
 tax
 lda.l R+232,x
 inc a
 cmp #27
 bcc PlayerHistory_Step
 lda #0
PlayerHistory_Step:
.a16
.i16
 sta.l R+232,x
PlayerHistory_NextRow:
.a16
.i16
 lda.l S+10
 clc
 adc #12
 sta.l S+10
 lda.l S+8
 clc
 adc #256
 sta.l S+8
 cmp #1024
 beq PlayerHistory_Done
 jmp PlayerHistory_Row
PlayerHistory_Done:
.a16
.i16
 ply
 plx
 pla
 plp
 clc
 rtl
PlayerHistory_Fault:
.a16
.i16
 ply
 plx
 pla
 plp
 sec
 rtl
; Match fixed immutable sequence Q: word length + length uint32 masks.
; A=row index 0..3. A returns 0/1, C=1 malformed owner/row/sequence.
PlayerHistory_Match:
.a16
.i16
 php
 rep #$31
 phx
 phy
 cmp #4
 bcc PlayerHistory_MatchIndex
 jmp PlayerHistory_MatchFault
PlayerHistory_MatchIndex:
.a16
.i16
 xba
 tax
 sta.l S+24
 lda.l O
 cmp #M
 beq PlayerHistory_MatchLength
 jmp PlayerHistory_MatchFault
PlayerHistory_MatchLength:
.a16
.i16
 lda.l Q
 cmp #28
 bcc PlayerHistory_MatchStep
 jmp PlayerHistory_MatchFault
PlayerHistory_MatchStep:
.a16
.i16
 sta.l S+26
 lda.l R+234,x
 beq PlayerHistory_MatchStepLow
 jmp PlayerHistory_MatchFault
PlayerHistory_MatchStepLow:
.a16
.i16
 lda.l R+232,x
 cmp #27
 bcc PlayerHistory_MatchStart
 jmp PlayerHistory_MatchFault
PlayerHistory_MatchStart:
.a16
.i16
 sta.l S+28
PlayerHistory_MatchLoop:
.a16
.i16
 lda.l S+26
 beq PlayerHistory_Matched
 dec a
 sta.l S+26
 asl a
 asl a
 tax
 lda.l Q+2,x
 sta.l S+30
 lda.l Q+4,x
 sta.l S+32
 lda.l S+28
 bne PlayerHistory_MatchPrevious
 lda #27
PlayerHistory_MatchPrevious:
.a16
.i16
 dec a
 sta.l S+28
 asl a
 asl a
 clc
 adc.l S+24
 tax
 lda.l R+108,x
 and.l S+30
 sta.l S+34
 lda.l R+110,x
 and.l S+32
 ora.l S+34
 bne PlayerHistory_MatchLoop
 lda #0
 bra PlayerHistory_MatchReturn
PlayerHistory_Matched:
.a16
.i16
 lda #1
PlayerHistory_MatchReturn:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
PlayerHistory_MatchFault:
.a16
.i16
 lda #0
 ply
 plx
 plp
 sec
 rtl
'''
    import re
    for name,value in names.items():code=re.sub(r'\b'+name+r'\b',str(value),code)
    return code
