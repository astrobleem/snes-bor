"""Offline native command selection for source models without cancel commands.

Caller serializes the existing input, animation and costmove owners and grants
exclusive control/sequence storage. Cancel models fail explicitly until the
shared hit/cancel owner is bound. No actor identity selects runtime behavior.
"""
import re
from source_player_combo_authority import CONTROL


def emit(report,work,cost_work,history,sequence,input_owner,input_magic,symbols):
    models=report['models']
    if any(m['cancel_animations'] or any(c['cancel'] for c in m['combos']) for m in models):
        raise ValueError('SOURCE_COMBO_CANCEL_OWNER_REQUIRED')
    extents=((work,96),(cost_work,64),(history,1024),(sequence,110),(input_owner,2))
    for i,(a,n) in enumerate(extents):
        if not 0<=a<=0x1000000-n:raise ValueError('SOURCE_COMBO_NATIVE_EXTENT')
        for b,m in extents[i+1:]:
            if a<b+m and b<a+n:raise ValueError('SOURCE_COMBO_NATIVE_OVERLAP')
    if history&255:raise ValueError('SOURCE_COMBO_HISTORY_ALIGNMENT')
    if not isinstance(input_magic,int) or not 1<=input_magic<=65535:
        raise ValueError('SOURCE_COMBO_INPUT_MAGIC')
    code='''
SourceCombo_Begin:
.a16
.i16
 php
 rep #$31
 pha
 phx
 phy
 lda.l W
 cmp #$B673
 bne SourceCombo_Fault
 lda.l INPUTOWNER
 cmp #INPUTMAGIC
 bne SourceCombo_Fault
 lda.l W+2
 beq SourceCombo_Enter
 cmp #2
 beq SourceCombo_Enter
 cmp #4
 bne SourceCombo_Fault
SourceCombo_Enter:
 lda #1
 sta.l W+2
 lda #$FFFF
 sta.l W+8
 sta.l W+10
 lda.l C
 cmp #$B670
 bne SourceCombo_Fault
 lda.l C+2
 beq SourceCombo_World
 cmp #2
 beq SourceCombo_World
 cmp #4
 bne SourceCombo_Fault
SourceCombo_World:
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 bne SourceCombo_Fault
 lda.l VmSourceWorld_Count
 beq SourceCombo_Fault
 cmp #129
 bcs SourceCombo_Fault
 lda.l W+4
 cmp.l VmSourceWorld_Count
 bcs SourceCombo_Fault
 sta.l C+4
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l W+20
 lda.l W+4
 asl a
 asl a
 sta.l W+24
 asl a
 asl a
 clc
 adc.l W+24
 sta.l W+24
 asl a
 asl a
 sta.l W+22
 tax
 lda.l $414028,x
 cmp #1
 bne SourceCombo_Fault
 lda.l $41402A,x
 ora.l $41402E,x
 bne SourceCombo_Fault
 lda.l $41402C,x
 cmp #4
 bcs SourceCombo_Fault
 sta.l W+6
 xba
 tax
 lda.l H+224,x
 ora.l H+226,x
 beq SourceCombo_False
 lda.l W+20
 tax
 lda.l $43EB00,x
 ora.l $43EB02,x
 beq SourceCombo_False
 ; Existing scalar presentation uses the documented binary32 -> Q16 ABI.
 lda.l W+22
 tax
 lda.l $414008,x
 cmp #2
 bne SourceCombo_Fault
 lda.l $41400A,x
 bne SourceCombo_Fault
 lda.l $41400C,x
 sta.l W+36
 lda.l $41400E,x
 sta.l W+38
 lda.l W+24
 tax
 lda.l W+36
 sec
 sbc.l $41F508,x
 sta.l W+36
 lda.l W+38
 sbc.l $41F50A,x
 bvs SourceCombo_Fault
 bpl SourceCombo_HeightMagnitude
 sta.l W+38
 lda.l W+36
 eor #$FFFF
 clc
 adc #1
 sta.l W+36
 lda.l W+38
 eor #$FFFF
 adc #0
 bvs SourceCombo_Fault
SourceCombo_HeightMagnitude:
 cmp #1
 bcc SourceCombo_Current
 bne SourceCombo_False
 lda.l W+36
 bne SourceCombo_False
SourceCombo_Current:
 lda.l W+22
 tax
 lda.l $414010,x
 cmp #1
 bne SourceCombo_Fault
 lda.l $414012,x
 ora.l $414016,x
 bne SourceCombo_Fault
 lda.l W+4
 sta.l SourceAnimationInit4086_Slot
 lda.l $414014,x
 sta.l SourceAnimationInit4086_Number
 lda #0
 sta.l SourceAnimationInit4086_Reset
 jsl SourceAnimationInit4086_Resolve
 bcs SourceCombo_Fault
 lda.l SourceAnimationInit4086_Handle
 beq SourceCombo_Fault
 ; Resolve's Model control is scratch, reused by CheckHandle. Read the
 ; validated entity's current model from its canonical side row instead.
 lda.l W+4
 asl a
 asl a
 asl a
 asl a
 asl a
 asl a
 tax
 lda.l $416800,x
 sta.l W+12
'''
    for i,m in enumerate(models):
        code+=f''' lda.l W+12
 cmp #{i}
 bne SourceCombo_ModelNext{i}
'''
        for j,c in enumerate(m['combos']):
            if not 1<=len(c['input'])<=27 or not 0<=c['anim']<=65535:
                raise ValueError('SOURCE_COMBO_NATIVE_COMMAND')
            label=f'SourceCombo_Skip{i}_{j}'
            code+=f''' lda.l W+10
 cmp #$FFFF
 beq SourceCombo_Try{i}_{j}
 cmp #{len(c['input'])}
 bcs {label}
SourceCombo_Try{i}_{j}:
 lda #{c['anim']}
 sta.l C+6
 jsl SourceComboEnergy_Query
 bcs SourceCombo_Fault
 cmp #0
 beq {label}
 lda #{len(c['input'])}
 sta.l Q
'''
            for k,v in enumerate(c['input']):
                for offset,half in ((2+k*4,v&65535),(4+k*4,v>>16)):
                    code+=f' lda #{half}\n sta.l Q+{offset}\n'
            code+=f''' lda.l W+6
 jsl PlayerHistory_Match
 bcs SourceCombo_Fault
 cmp #0
 beq {label}
 lda #{c['anim']}
 sta.l W+8
 lda #{len(c['input'])}
 sta.l W+10
{label}:
'''
        code+=f' jmp SourceCombo_Selected\nSourceCombo_ModelNext{i}:\n'
    code+=''' jmp SourceCombo_Fault
SourceCombo_Selected:
 lda.l W+8
 cmp #$FFFF
 beq SourceCombo_False
 sta.l C+6
 lda.l W+20
 tax
 lda.l $43EB08,x
 sta.l C+12
 lda.l $43EB0A,x
 sta.l C+14
 lda #1
 sta.l C+8
 lda #0
 sta.l C+10
 jsl SourceCostMove_Begin
 bcs SourceCombo_Fault
 lda.l C+2
 cmp #2
 beq SourceCombo_False
 cmp #4
 beq SourceCombo_ClearKeys
 cmp #3
 bne SourceCombo_Fault
 lda #3
 sta.l W+2
 jmp SourceCombo_Return
SourceCombo_Finish:
.a16
.i16
 php
 rep #$31
 pha
 phx
 phy
 lda.l W
 cmp #$B673
 bne SourceCombo_Fault
 lda.l INPUTOWNER
 cmp #INPUTMAGIC
 bne SourceCombo_Fault
 lda.l W+2
 cmp #3
 bne SourceCombo_Fault
 jsl SourceCostMove_Finish
 bcs SourceCombo_Fault
SourceCombo_ClearKeys:
 ; Re-read playerindex after the real callback, as player_preinput does.
 lda.l W+22
 tax
 lda.l $414028,x
 cmp #1
 bne SourceCombo_Fault
 lda.l $41402A,x
 ora.l $41402E,x
 bne SourceCombo_Fault
 lda.l $41402C,x
 cmp #4
 bcs SourceCombo_Fault
 xba
 tax
 lda.l H+224,x
 and #CLEARCONTROL
 sta.l H+224,x
 lda #4
 sta.l W+2
 jmp SourceCombo_Return
SourceCombo_False:
 lda #2
 sta.l W+2
SourceCombo_Return:
 ply
 plx
 pla
 plp
 clc
 rtl
SourceCombo_Fault:
 lda #5
 sta.l W+2
 ply
 plx
 pla
 plp
 sec
 rtl
'''
    # Preserve explicit instruction widths at every generated entry/branch.
    code=re.sub(r'^(SourceCombo_[A-Za-z0-9_]+:)\n(?!\.a16)',r'\1\n.a16\n.i16\n',code,flags=re.M)
    values=dict(W=work,C=cost_work,H=history,Q=sequence,INPUTOWNER=input_owner,INPUTMAGIC=input_magic,CLEARCONTROL=(~CONTROL)&65535)
    for name in set(re.findall(r'\b(?:VmSourceWorld|SourceAnimationInit4086)_[A-Za-z0-9_]+\b',code)):
        values[name]=symbols[name]
    for n,v in values.items():code=re.sub(r'\b'+n+r'\b',str(v),code)
    # Unrolled source commands preserve source order; relax every conditional
    # so longer authored input lists cannot silently break branch range.
    count=[0]
    def relax(m):
        count[0]+=1;label='SourceCombo_Branch'+str(count[0])
        inverse=dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc',bvs='bvc',bpl='bmi')[m[1]]
        return f' {inverse} {label}\n jmp {m[2]}\n{label}:\n.a16\n.i16'
    return re.sub(r'^ (beq|bne|bcc|bcs|bvs|bpl) (SourceCombo_\w+)$',relax,code,flags=re.M)
