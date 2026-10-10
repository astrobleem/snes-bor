"""Native spawnplayer input reset using the already allocated source history rows.

A=index after source &3; X/Y=exclusive foreign generation. No constructor or
production consumer is installed. Exactly the two rings and combostep change.
"""
from source_player_input_4086 import ROW_BYTES,MAX_SPECIAL_INPUTS


def emit_history_reset(rows,sy):
    if rows&255 or not 0<=rows<=0x1000000-4*ROW_BYTES or (rows&65535)>65536-4*ROW_BYTES:
        raise ValueError('SPAWN_HISTORY_LAYOUT')
    return f"""SpawnHistory_Reset:
.a16
.i16
 php
 rep #$39
 pha
 phx
 phy
 jsl {sy['SourceForeignWork_Check']}
 bcs SpawnHistory_Bad
 lda 5,s
 cmp #4
 bcs SpawnHistory_Bad
 xba
 tax
 ldy #{MAX_SPECIAL_INPUTS*4}
 lda #0
SpawnHistory_Clear:
.a16
.i16
 sta.l {rows},x
 inx
 inx
 dey
 bne SpawnHistory_Clear
 txa
 sec
 sbc #{MAX_SPECIAL_INPUTS*8}
 tax
 lda #0
 sta.l {rows+232},x
 sta.l {rows+234},x
 ply
 plx
 pla
 plp
 clc
 rtl
SpawnHistory_Bad:
.a16
.i16
 ply
 plx
 pla
 plp
 sec
 rtl
"""
