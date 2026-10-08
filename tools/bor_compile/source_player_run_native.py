"""Native source running predicate over an explicit 48-byte caller lease.

Velocity operands use the established finite Q16 presentation ABI; only their
sign and zero are queried here. No canonical actor allocation is implicit.
"""
import re
from source_player_run_4086 import KEYS


def emit(work):
    if not 0<=work<=0x1000000-48:raise ValueError('PLAYER_RUN_NATIVE_EXTENT')
    code='''
SourcePlayerRun_Execute:
 php
 rep #$39
 phx
 phy
 lda.l W
 cmp #$B677
 bne SourcePlayerRun_Fault
 lda.l W+2
 beq SourcePlayerRun_Ready
 cmp #2
 bne SourcePlayerRun_Fault
SourcePlayerRun_Ready:
 lda.l W+4
 sta.l W+28
 lda.l W+6
 sta.l W+30
 ora.l W+4
 beq SourcePlayerRun_Complete
 lda #0
 sta.l W+34
 sta.l W+36
 sta.l W+38
 sta.l W+40
 lda.l W+16
 and #LEFT
 beq SourcePlayerRun_Right
 lda #$FFFF
 sta.l W+34
SourcePlayerRun_Right:
 lda.l W+16
 and #RIGHT
 beq SourcePlayerRun_Up
 lda.l W+34
 inc a
 sta.l W+34
SourcePlayerRun_Up:
 lda.l W+16
 and #UP
 beq SourcePlayerRun_Down
 lda #$FFFF
 sta.l W+36
SourcePlayerRun_Down:
 lda.l W+16
 and #DOWN
 beq SourcePlayerRun_Old
 lda.l W+36
 inc a
 sta.l W+36
SourcePlayerRun_Old:
 lda.l W+8
 ora.l W+10
 beq SourcePlayerRun_Flags
 lda.l W+22
 bmi SourcePlayerRun_VxNegative
 ora.l W+20
 beq SourcePlayerRun_Vz
 lda #1
 sta.l W+38
 bra SourcePlayerRun_Vz
SourcePlayerRun_VxNegative:
 lda #$FFFF
 sta.l W+38
SourcePlayerRun_Vz:
 lda.l W+26
 bmi SourcePlayerRun_VzNegative
 ora.l W+24
 beq SourcePlayerRun_Flags
 lda #1
 sta.l W+40
 bra SourcePlayerRun_Flags
SourcePlayerRun_VzNegative:
 lda #$FFFF
 sta.l W+40
SourcePlayerRun_Flags:
 lda.l W+12
 ora.l W+14
 bne SourcePlayerRun_FlagsNonzero
 lda.l W+36
 bne SourcePlayerRun_Stop
 lda.l W+34
 beq SourcePlayerRun_Stop
 bra SourcePlayerRun_Complete
SourcePlayerRun_FlagsNonzero:
 lda.l W+12
 and #4
 bne SourcePlayerRun_FreeRun
 lda.l W+34
 beq SourcePlayerRun_Stop
 clc
 adc.l W+38
 beq SourcePlayerRun_Stop
 bra SourcePlayerRun_Complete
SourcePlayerRun_FreeRun:
 lda.l W+34
 beq SourcePlayerRun_VerticalOnly
 lda.l W+36
 beq SourcePlayerRun_HorizontalOnly
 lda.l W+34
 sec
 sbc.l W+38
 bpl SourcePlayerRun_AbsX
 eor #$FFFF
 inc a
SourcePlayerRun_AbsX:
 sta.l W+42
 lda.l W+36
 sec
 sbc.l W+40
 bpl SourcePlayerRun_AbsZ
 eor #$FFFF
 inc a
SourcePlayerRun_AbsZ:
 clc
 adc.l W+42
 cmp #3
 bcs SourcePlayerRun_Stop
 bra SourcePlayerRun_Complete
SourcePlayerRun_VerticalOnly:
 lda.l W+36
 beq SourcePlayerRun_Stop
 clc
 adc.l W+40
 beq SourcePlayerRun_Stop
 bra SourcePlayerRun_Complete
SourcePlayerRun_HorizontalOnly:
 lda.l W+34
 clc
 adc.l W+38
 beq SourcePlayerRun_Stop
 bra SourcePlayerRun_Complete
SourcePlayerRun_Stop:
 lda #0
 sta.l W+28
 sta.l W+30
SourcePlayerRun_Complete:
 lda #2
 sta.l W+2
 lda.l W+28
 ply
 plx
 plp
 clc
 rtl
SourcePlayerRun_Fault:
 lda #3
 sta.l W+2
 lda #0
 ply
 plx
 plp
 sec
 rtl
'''
    for name,value in dict(W=work,LEFT=KEYS['moveleft'],RIGHT=KEYS['moveright'],UP=KEYS['moveup'],DOWN=KEYS['movedown']).items():
        code=re.sub(r'\b'+name+r'\b',str(value),code)
    inv=dict(beq='bne',bne='beq',bmi='bpl',bpl='bmi',bcc='bcs',bcs='bcc')
    code=re.sub(r'^ (beq|bne|bmi|bpl|bcc|bcs) (SourcePlayerRun_\w+)$',lambda m:f' {inv[m[1]]} SourcePlayerRun_Skip{m.start()}\n jmp {m[2]}\nSourcePlayerRun_Skip{m.start()}:',code,flags=re.M)
    code=re.sub(r'^ bra (SourcePlayerRun_\w+)$',r' jmp \1',code,flags=re.M)
    return re.sub(r'^(SourcePlayerRun_\w+:)$',r'\1\n.a16\n.i16',code,flags=re.M)
