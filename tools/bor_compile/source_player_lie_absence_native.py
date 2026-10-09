"""Actual first validanim query in player_lie_check; absent lane only.

A present RISEATTACK explicitly requires the full set_riseattack owner. No
input, health, timer or actor state is synthesized or silently discarded.
"""


def emit(work,role,symbols):
    if not 0<=work<=0x1000000-16 or not 0<=role<=65535:raise ValueError('PLAYER_LIE_ABSENCE_EXTENT')
    return f"""
PlayerLieAbsent_Execute:
.a16
.i16
 php
 rep #$39
 pha
 phx
 phy
 lda.l {work}
 cmp #$B68B
 bne PlayerLieAbsent_Bad
 lda.l {work}+4
 sta.l {symbols['SourceAnimationInit4086_Slot']}
 lda #{role}
 sta.l {symbols['SourceAnimationInit4086_Number']}
 jsl {symbols['SourceAnimationInit4086_Resolve']}
 bcs PlayerLieAbsent_Bad
 lda.l {symbols['SourceAnimationInit4086_Handle']}
 beq PlayerLieAbsent_Done
 lda.l {symbols['SourceAnimationInit4086_Count']}
 beq PlayerLieAbsent_Done
 lda #3
 sta.l {work}+2
 ply
 plx
 pla
 plp
 sec
 rtl
PlayerLieAbsent_Done:
.a16
.i16
 lda #2
 sta.l {work}+2
 ply
 plx
 pla
 plp
 clc
 rtl
PlayerLieAbsent_Bad:
.a16
.i16
 lda #4
 sta.l {work}+2
 ply
 plx
 pla
 plp
 sec
 rtl
"""
