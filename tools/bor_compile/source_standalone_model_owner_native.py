"""Consume model-service frame children without a waiting parent frame.

X/Y carry the independent foreign generation. Nonzero external frame tickets
return unchanged; only actual frame completion is acknowledged. No table,
birth, world clock or presentation ownership is supplied by this emitter.
"""
import re


def emit(symbols):
    code='''StandaloneModelOwner_Resume:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jsl SourceForeignWork_Check
 bcs StandaloneModelOwner_Bad
 lda.l SourceModelTransition4086_Ready
 cmp #$B4F0
 bne StandaloneModelOwner_Bad
 lda.l SourceModelTransition4086_State
 cmp #2
 beq StandaloneModelOwner_Pipeline
 cmp #1
 bne StandaloneModelOwner_Bad
 lda.l SourceModelTransition4086_Service
 cmp #4
 bne StandaloneModelOwner_Pipeline
 lda.l SourceAnimationInit4086_Ready
 cmp #$B4EC
 bne StandaloneModelOwner_Bad
 lda.l SourceAnimationInit4086_Slot
 cmp.l SourceModelTransition4086_Slot
 bne StandaloneModelOwner_Bad
 lda.l SourceAnimationInit4086_State
 cmp #1
 bne StandaloneModelOwner_Pipeline
 lda.l SourceAnimationInit4086_Issued
 cmp #1
 beq StandaloneModelOwner_Child
 cmp #0
 bne StandaloneModelOwner_Bad
StandaloneModelOwner_Pipeline:
.a16
.i16
 lda 3,s
 tax
 lda 1,s
 tay
 jsl ModelPipeline_Resume
 bcs StandaloneModelOwner_Bad
 cmp #0
 beq StandaloneModelOwner_Good
 cmp #4
 bne StandaloneModelOwner_Bad
 jsl SourceAnimationInit4086_StartFrame
 bcs StandaloneModelOwner_Bad
StandaloneModelOwner_Child:
.a16
.i16
 lda.l SourceModelAnimation4086_Ready
 cmp #$B4EF
 bne StandaloneModelOwner_Bad
 lda.l SourceModelAnimation4086_State
 cmp #1
 bne StandaloneModelOwner_Bad
 lda.l SourceModelAnimation4086_Slot
 cmp.l SourceModelTransition4086_Slot
 bne StandaloneModelOwner_Bad
 lda.l SourceUpdateFrame4086_Slot
 cmp.l SourceModelTransition4086_Slot
 bne StandaloneModelOwner_Bad
 lda.l SourceFrameStack4086_Ready
 cmp #$B4ED
 bne StandaloneModelOwner_Bad
 lda.l SourceFrameStack4086_Depth
 bne StandaloneModelOwner_Bad
 lda 3,s
 tax
 lda 1,s
 tay
 jsl ModelFrameOwner_Run
 bcs StandaloneModelOwner_Bad
 cmp #0
 bne StandaloneModelOwner_Good
 jsl SourceAnimationInit4086_Ack
 bcs StandaloneModelOwner_Bad
 jmp StandaloneModelOwner_Pipeline
StandaloneModelOwner_Good:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
StandaloneModelOwner_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
'''
    serial=0
    def relax(m):
        nonlocal serial
        serial+=1
        label='StandaloneModelOwner_Guard'+str(serial)
        inverse=dict(beq='bne',bne='beq',bcs='bcc',bcc='bcs')[m[1]]
        return f' {inverse} {label}\n jmp {m[2]}\n{label}:\n.a16\n.i16'
    code=re.sub(r'^ (beq|bne|bcs|bcc) (StandaloneModelOwner_\w+)$',relax,code,flags=re.M)
    for name in sorted(symbols,key=len,reverse=True):
        if name.startswith('Source'):code=re.sub(r'\b'+name+r'\b',str(symbols[name]),code)
    return code
