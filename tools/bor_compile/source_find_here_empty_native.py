"""Prove the type-filtered find_ent_here candidate set is empty at runtime.

A matching live candidate requires the full geometry/vulnerability/test owner;
it is an explicit admission failure, never a synthesized null search result.
"""
import re


def emit(work,symbols):
    if not 0<=work<=0x1000000-24:raise ValueError('FIND_HERE_EMPTY_EXTENT')
    code='''
SourceFindHereEmpty_Execute:
.a16
.i16
 php
 rep #$39
 pha
 phx
 phy
 lda #0
 sta.l W+16
 sta.l W+18
 lda.l W
 cmp #$B67D
 bne SourceFindHereEmpty_Bad
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 bne SourceFindHereEmpty_Bad
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 bne SourceFindHereEmpty_Bad
 lda.l VmSourceWorld_Count
 beq SourceFindHereEmpty_Bad
 cmp #129
 bcs SourceFindHereEmpty_Bad
 lda.l SourceModelEntityCopy4086_Ready
 cmp #$B4EB
 bne SourceFindHereEmpty_Bad
 lda.l SourceModelEntityCopy4086_Entities
 cmp.l VmSourceWorld_Count
 bne SourceFindHereEmpty_Bad
 lda.l W+4
 cmp #$FFFF
 beq SourceFindHereEmpty_Start
 cmp.l VmSourceWorld_Count
 bcs SourceFindHereEmpty_Bad
SourceFindHereEmpty_Start:
.a16
.i16
 lda #0
 sta.l W+10
 sta.l W+12
 sta.l W+14
SourceFindHereEmpty_Loop:
.a16
.i16
 lda.l W+10
 cmp.l W+4
 beq SourceFindHereEmpty_Next
 lda.l W+12
 tax
 lda.l $414004,x
 ora.l $414006,x
 beq SourceFindHereEmpty_Next
 lda.l W+14
 tax
 lda.l $40C048,x
 and.l W+6
 sta.l W+20
 lda.l $40C04A,x
 and.l W+8
 ora.l W+20
 bne SourceFindHereEmpty_RequiresCandidateOwner
SourceFindHereEmpty_Next:
.a16
.i16
 lda.l W+12
 clc
 adc #80
 sta.l W+12
 lda.l W+14
 clc
 adc #96
 sta.l W+14
 lda.l W+10
 inc a
 sta.l W+10
 cmp.l VmSourceWorld_Count
 bcc SourceFindHereEmpty_Loop
 lda #2
 sta.l W+2
 ply
 plx
 pla
 plp
 clc
 rtl
SourceFindHereEmpty_RequiresCandidateOwner:
.a16
.i16
 lda #3
 bra SourceFindHereEmpty_Fault
SourceFindHereEmpty_Bad:
.a16
.i16
 lda #4
SourceFindHereEmpty_Fault:
.a16
.i16
 sta.l W+2
 ply
 plx
 pla
 plp
 sec
 rtl
'''
    for name in ('VmSourceWorld_Ready','VmSourceWorld_PoolBase','VmSourceWorld_Count',
                 'SourceModelEntityCopy4086_Ready','SourceModelEntityCopy4086_Entities'):
        if name not in symbols:raise ValueError('FIND_HERE_EMPTY_SYMBOL:'+name)
        code=re.sub(r'\b'+name+r'\b',str(symbols[name]),code)
    # Guard exits use far jumps so extending a guard never invalidates branches.
    serial=0
    def far(match):
        nonlocal serial
        serial+=1;skip='SourceFindHereEmpty_Guard'+str(serial)
        opposite={'bne':'beq','beq':'bne','bcs':'bcc'}[match[1]]
        return ' '+opposite+' '+skip+'\n jmp SourceFindHereEmpty_Bad\n'+skip+':\n.a16\n.i16'
    code=re.sub(r' (bne|beq|bcs) SourceFindHereEmpty_Bad',far,code)
    return re.sub(r'\bW\b',str(work),code)
