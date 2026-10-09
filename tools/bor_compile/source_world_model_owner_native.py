"""World continuation for timed source frames with model transitions.

Caller owns Begin, other world services, external frame tickets and clock commit.
No service is acknowledged until its actual native operator has completed.
"""
import re


def emit(symbols):
    code="""WorldModelOwner_Run:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jsl SourceForeignWork_Check
 bcs WorldModelOwner_Bad
WorldModelOwner_Poll:
.a16
.i16
 jsl SourceWorldTick4086_Poll
 bcs WorldModelOwner_Bad
 cmp #7
 bne WorldModelOwner_Good
 lda 3,s
 tax
 lda 1,s
 tay
 jsl ModelTimedFrameOwner_Run
 bcs WorldModelOwner_Bad
 cmp #0
 bne WorldModelOwner_Good
 lda #7
 jsl SourceWorldTick4086_Ack
 bcs WorldModelOwner_Bad
 jmp WorldModelOwner_Poll
WorldModelOwner_Good:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
WorldModelOwner_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
"""
    serial=[0]
    def relax(m):
        serial[0]+=1;label='WorldModelOwner_Guard'+str(serial[0])
        return ' '+dict(bne='beq',bcs='bcc')[m[1]]+' '+label+'\n jmp '+m[2]+'\n'+label+':\n.a16\n.i16'
    code=re.sub(r'^ (bne|bcs) (WorldModelOwner_\w+)$',relax,code,flags=re.M)
    for name in sorted(symbols,key=len,reverse=True):
        if name.startswith('Source'):code=re.sub(r'\b'+name+r'\b',str(symbols[name]),code)
    return code
