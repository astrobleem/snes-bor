"""common_idle_anim prefix for the admitted single ordinary idle series.

This differs from set_idle: other flags are retained, idling is ORed with two,
and velocity stopping tests the entity's current model pointer's cached type.
"""
import re


def emit(work,capability,symbols):
    models=capability['models'];count=len(models)
    if not 1<=count<=16 or any(m['capability']!='DEFAULT_IDLE_ONLY' or m['cached_subtype']!=0 for m in models):
        raise ValueError('COMMON_IDLE_NATIVE_CAPABILITY')
    if not 0<=work<=0x1000000-24:raise ValueError('COMMON_IDLE_NATIVE_EXTENT')
    code='''
SourceCommonIdle_Begin:
.a16
.i16
 php
 rep #$39
 phx
 phy
 lda.l W
 cmp #$B680
 bne SourceCommonIdle_Bad
 lda.l W+2
 beq SourceCommonIdle_Guards
 cmp #2
 bne SourceCommonIdle_Bad
SourceCommonIdle_Guards:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 bne SourceCommonIdle_Bad
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 bne SourceCommonIdle_Bad
 lda.l VmSourceWorld_Count
 beq SourceCommonIdle_Bad
 cmp #129
 bcs SourceCommonIdle_Bad
 cmp.l SourceModelEntityCopy4086_Entities
 bne SourceCommonIdle_Bad
 lda.l SourceModelEntityCopy4086_Ready
 cmp #$B4EB
 bne SourceCommonIdle_Bad
 lda.l SourceModelEntityCopy4086_Models
 cmp #MODELCOUNT
 bne SourceCommonIdle_Bad
 lda.l W+4
 cmp.l VmSourceWorld_Count
 bcs SourceCommonIdle_Bad
 sta.l SourceAnimationInit4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l W+6
 asl a
 sta.l W+10
 clc
 adc.l W+6
 sta.l W+8
 lda.l W+6
 tax
 lda.l $43EB16,x
 bne SourceCommonIdle_Bad
 lda.l $43EB14,x
 cmp #2
 bcs SourceCommonIdle_Bad
 ; Resolve before canonical writes, including all actual initializer leases.
 lda #0
 sta.l SourceAnimationInit4086_Number
 sta.l SourceAnimationInit4086_Reset
 jsl SourceAnimationInit4086_Resolve
 bcs SourceCommonIdle_Bad
 lda.l W+6
 tax
 lda.l $43EB00,x
 ora.l $43EB02,x
 beq SourceCommonIdle_Type
 lda.l $43EB00,x
 ora #2
 sta.l $43EB00,x
SourceCommonIdle_Type:
.a16
.i16
 lda.l W+10
 tax
 lda.l $416800,x
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l W+12
 asl a
 asl a
 clc
 adc.l W+12
 tax
 lda.l $40B09C,x
 ora.l $40B09E,x
 beq SourceCommonIdle_Animate
 lda.l W+10
 tax
 lda #0
 sta.l $416824,x
 sta.l $416826,x
 sta.l $416828,x
 sta.l $41682A,x
SourceCommonIdle_Animate:
.a16
.i16
 jsl SourceAnimationInit4086_Begin
 bcs SourceCommonIdle_Bad
 lda.l SourceAnimationInit4086_State
 cmp #1
 beq SourceCommonIdle_Pending
 cmp #2
 bne SourceCommonIdle_Bad
 lda #2
 sta.l W+2
 lda #0
 bra SourceCommonIdle_Good
SourceCommonIdle_Pending:
.a16
.i16
 lda #3
 sta.l W+2
 lda #1
SourceCommonIdle_Good:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
SourceCommonIdle_Finish:
.a16
.i16
 php
 rep #$39
 phx
 phy
 lda.l W
 cmp #$B680
 bne SourceCommonIdle_Bad
 lda.l W+2
 cmp #3
 bne SourceCommonIdle_Bad
 lda.l SourceAnimationInit4086_State
 cmp #2
 bne SourceCommonIdle_Bad
 lda.l SourceAnimationInit4086_Slot
 cmp.l W+4
 bne SourceCommonIdle_Bad
 jsl SourceSelf4086_CheckIdle
 bcs SourceCommonIdle_Bad
 lda #2
 sta.l W+2
 lda #0
 bra SourceCommonIdle_Good
SourceCommonIdle_Bad:
.a16
.i16
 lda #4
 sta.l W+2
 ply
 plx
 plp
 sec
 rtl
'''
    serial=0
    def far(m):
        nonlocal serial
        serial+=1;skip='SourceCommonIdle_Guard'+str(serial)
        return ' '+dict(beq='bne',bne='beq',bcs='bcc')[m[1]]+' '+skip+'\n jmp SourceCommonIdle_Bad\n'+skip+':\n.a16\n.i16'
    code=re.sub(r' (bne|beq|bcs) SourceCommonIdle_Bad',far,code)
    for name in set(re.findall(r'\b(?:VmSourceWorld|SourceModelEntityCopy4086|SourceAnimationInit4086|SourceSelf4086)_\w+\b',code)):
        if name not in symbols:raise ValueError('COMMON_IDLE_NATIVE_SYMBOL:'+name)
        code=re.sub(r'\b'+name+r'\b',str(symbols[name]),code)
    return re.sub(r'\bW\b',str(work),code).replace('MODELCOUNT',str(count))
