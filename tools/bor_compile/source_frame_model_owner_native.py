"""Join native frame execution with synchronized model services and nested idle.

X/Y are the independent expected canvas generation. Required external effect
and VM continuation tickets return unchanged. The caller owns table admission,
script/native external services and world clock commit. No model-name policy.
"""
import re


def emit(symbols):
    assembly="""ModelFrameOwner_Run:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jsl SourceForeignWork_Check
 bcs ModelFrameOwner_Bad
ModelFrameOwner_Loop:
.a16
.i16
 jsl SourceFrameOwner4086_Run
 bcs ModelFrameOwner_Bad
 cmp #0
 beq ModelFrameOwner_Completed
 cmp #3
 beq ModelFrameOwner_Model
 cmp #4
 beq ModelFrameOwner_Idle
 jmp ModelFrameOwner_Good
ModelFrameOwner_Model:
.a16
.i16
 lda.l SourceFrameEffectBinding4086_State
 cmp #1
 bne ModelFrameOwner_Bad
 lda 3,s
 tax
 lda 1,s
 tay
 jsl ModelPipeline_Resume
 bcs ModelFrameOwner_Bad
 jmp ModelFrameOwner_Loop
ModelFrameOwner_Idle:
.a16
.i16
 lda.l SourceFrameEffectBinding4086_State
 cmp #2
 bne ModelFrameOwner_Bad
 lda.l SourceAnimationInit4086_State
 cmp #1
 bne ModelFrameOwner_Bad
 lda.l SourceAnimationInit4086_Issued
 bne ModelFrameOwner_Bad
 jsl SourceAnimationInit4086_StartNestedFrame
 bcs ModelFrameOwner_Bad
 jmp ModelFrameOwner_Loop
ModelFrameOwner_Completed:
.a16
.i16
 lda.l SourceFrameStack4086_Ready
 cmp #$B4ED
 bne ModelFrameOwner_Bad
 lda.l SourceFrameStack4086_Depth
 beq ModelFrameOwner_Done
 jsl SourceAnimationInit4086_FinishNestedFrame
 bcs ModelFrameOwner_Bad
 jmp ModelFrameOwner_Loop
ModelFrameOwner_Done:
.a16
.i16
 lda #0
ModelFrameOwner_Good:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
ModelFrameOwner_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
"""
    serial=[0]
    def relax(match):
        serial[0]+=1;label='ModelFrameOwner_Guard'+str(serial[0])
        return ' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[match[1]]+' '+label+'\n jmp '+match[2]+'\n'+label+':\n.a16\n.i16'
    assembly=re.sub(r'^ (beq|bne|bcc|bcs) (ModelFrameOwner_\w+)$',relax,assembly,flags=re.M)
    for name in sorted(symbols,key=len,reverse=True):
        if name.startswith('Source'):assembly=re.sub(r'\b'+name+r'\b',str(symbols[name]),assembly)
    return assembly
