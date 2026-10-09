"""World continuation for timed source frames with model transitions.

Caller owns Begin, other world services, external frame tickets and clock commit.
No service is acknowledged until its actual native operator has completed.
"""
import re


def emit(symbols, *, attack_service=None):
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
    if attack_service is not None:
        if not re.fullmatch(r'[A-Za-z_]\w*',attack_service):raise ValueError('WORLD_ATTACK_SERVICE_LABEL')
        code=code.replace(' cmp #7\n bne WorldModelOwner_Good',' cmp #8\n beq WorldModelOwner_Attack\n cmp #7\n bne WorldModelOwner_Good')
        at=code.index('WorldModelOwner_Good:')
        code=code[:at]+"""WorldModelOwner_Attack:
.a16
.i16
 lda 3,s
 tax
 lda 1,s
 tay
 jsl ATTACKSERVICE
 bcs WorldModelOwner_Bad
 cmp #0
 bne WorldModelOwner_Good
 lda #8
 jsl SourceWorldTick4086_Ack
 bcs WorldModelOwner_Bad
 jmp WorldModelOwner_Poll
""".replace('ATTACKSERVICE',attack_service)+code[at:]
    serial=[0]
    def relax(m):
        serial[0]+=1;label='WorldModelOwner_Guard'+str(serial[0])
        return ' '+dict(beq='bne',bne='beq',bcs='bcc')[m[1]]+' '+label+'\n jmp '+m[2]+'\n'+label+':\n.a16\n.i16'
    code=re.sub(r'^ (beq|bne|bcs) (WorldModelOwner_\w+)$',relax,code,flags=re.M)
    for name in sorted(symbols,key=len,reverse=True):
        if name.startswith('Source'):code=re.sub(r'\b'+name+r'\b',str(symbols[name]),code)
    return code
