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


def emit_timed(symbols):
    """Run the actual phase-7 operator; caller retains world Ack/clock ownership."""
    code="""ModelTimedFrameOwner_Run:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jsl SourceForeignWork_Check
 bcs ModelTimedFrameOwner_Bad
 lda.l SourceWorldTick4086_Ready
 cmp #$B4D5
 bne ModelTimedFrameOwner_Bad
 lda.l SourceWorldTick4086_State
 cmp #1
 bne ModelTimedFrameOwner_Bad
 lda.l SourceWorldTick4086_Pending
 cmp #1
 bne ModelTimedFrameOwner_Bad
 lda.l SourceWorldTick4086_Phase
 cmp #7
 bne ModelTimedFrameOwner_Bad
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 bne ModelTimedFrameOwner_Bad
 lda.l SourceWorldTick4086_Fault
 bne ModelTimedFrameOwner_Bad
 lda.l SourceWorldTick4086_TimeLo
 cmp.l VmSourceWorld_Time
 bne ModelTimedFrameOwner_Bad
 lda.l SourceWorldTick4086_TimeHi
 cmp.l VmSourceWorld_Time+2
 bne ModelTimedFrameOwner_Bad
 lda.l SourceUpdateAnimation4086_Ready
 cmp #$B60F
 bne ModelTimedFrameOwner_Bad
 lda.l SourceUpdateAnimation4086_State
 beq ModelTimedFrameOwner_Begin
 cmp #1
 beq ModelTimedFrameOwner_Resume
 cmp #2
 beq ModelTimedFrameOwner_Resume
 jmp ModelTimedFrameOwner_Bad
ModelTimedFrameOwner_Resume:
.a16
.i16
 lda.l SourceUpdateAnimation4086_Slot
 cmp.l SourceWorldTick4086_Slot
 bne ModelTimedFrameOwner_Bad
 lda.l SourceUpdateAnimation4086_TimeLo
 cmp.l SourceWorldTick4086_TimeLo
 bne ModelTimedFrameOwner_Bad
 lda.l SourceUpdateAnimation4086_TimeHi
 cmp.l SourceWorldTick4086_TimeHi
 bne ModelTimedFrameOwner_Bad
 lda.l SourceUpdateAnimation4086_Side
 cmp.l SourceWorldTick4086_Side
 bne ModelTimedFrameOwner_Bad
 lda.l SourceUpdateFrame4086_Slot
 cmp.l SourceUpdateAnimation4086_Slot
 bne ModelTimedFrameOwner_Bad
 lda.l SourceUpdateAnimation4086_State
 cmp #2
 beq ModelTimedFrameOwner_Done
 jmp ModelTimedFrameOwner_Frame
ModelTimedFrameOwner_Begin:
.a16
.i16
 jsl SourceUpdateAnimation4086_Begin
 bcs ModelTimedFrameOwner_Bad
 cmp #0
 beq ModelTimedFrameOwner_Done
 cmp #1
 bne ModelTimedFrameOwner_Bad
ModelTimedFrameOwner_Frame:
.a16
.i16
 lda 3,s
 tax
 lda 1,s
 tay
 jsl ModelFrameOwner_Run
 bcs ModelTimedFrameOwner_Bad
 cmp #0
 bne ModelTimedFrameOwner_Good
 jsl SourceUpdateAnimation4086_Continue
 bcs ModelTimedFrameOwner_Bad
ModelTimedFrameOwner_Done:
.a16
.i16
 jsl SourceUpdateAnimation4086_CheckWorldAck
 bcs ModelTimedFrameOwner_Bad
 lda #0
ModelTimedFrameOwner_Good:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
ModelTimedFrameOwner_Bad:
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
        serial[0]+=1;label='ModelTimedFrameOwner_Guard'+str(serial[0])
        return ' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[match[1]]+' '+label+'\n jmp '+match[2]+'\n'+label+':\n.a16\n.i16'
    code=re.sub(r'^ (beq|bne|bcc|bcs) (ModelTimedFrameOwner_\w+)$',relax,code,flags=re.M)
    for name in sorted(symbols,key=len,reverse=True):
        if name.startswith(('Source','VmSourceWorld_')):code=re.sub(r'\b'+name+r'\b',str(symbols[name]),code)
    return code
