"""Explicit VM-tail lease and lossless entity state access, compiler planned.

Module replacement must release this lease first. The existing loader is boot
only; its production foreign loader/constructor hooks remain caller work.
Generation and loaded slot extent are checked on every entity access.
"""
import re


def emit(plan, work, symbols):
    count=plan['live_slot_count'];base=plan['base'];extent=plan['entity_state_bytes']
    if plan['entity_stride']!=24 or extent!=plan['entities']*24 or not 1<=plan['entities']<=128:
        raise ValueError('PLAYER_STATE_NATIVE_PLAN')
    if base!=0x7fc000+count*8 or base+extent>0x7fe000:
        raise ValueError('PLAYER_STATE_NATIVE_TAIL')
    if not 0<=work<=0x1000000-64 or work<base+extent and base<work+64:
        raise ValueError('PLAYER_STATE_NATIVE_CONTROLS')
    code='''
SourcePlayerState_Init:
.a16
.i16
 php
 rep #$39
 pha
 phx
 phy
 lda.l W
 beq SourcePlayerState_InitGeneration
 jmp SourcePlayerState_Bad
SourcePlayerState_InitGeneration:
.a16
.i16
 lda.l W+8
 ora.l W+10
 bne SourcePlayerState_InitModule
 jmp SourcePlayerState_Bad
SourcePlayerState_InitModule:
.a16
.i16
 lda.l VmState_SlotCount
 cmp #COUNT
 beq SourcePlayerState_InitIdle
 jmp SourcePlayerState_Bad
SourcePlayerState_InitIdle:
.a16
.i16
 lda.l VmState_FrameTop
 beq SourcePlayerState_InitBusy
 jmp SourcePlayerState_Bad
SourcePlayerState_InitBusy:
.a16
.i16
 lda.l SourceVMRun4086_Busy
 beq SourcePlayerState_InitStatus
 jmp SourcePlayerState_Bad
SourcePlayerState_InitStatus:
.a16
.i16
 sep #$20
.a8
 lda.l VmState_Status
 cmp #2
 beq SourcePlayerState_InitActive
 cmp #3
 beq SourcePlayerState_InitActive
 rep #$20
.a16
 lda #COUNT
 sta.l W+12
 lda.l W+8
 sta.l W+14
 lda.l W+10
 sta.l W+16
 lda #0
 ldx #0
SourcePlayerState_ClearAll:
.a16
.i16
 sta.l B,x
 inx
 inx
 cpx #BYTES
 bcc SourcePlayerState_ClearAll
 lda #$B67B
 sta.l W
 jmp SourcePlayerState_Good
SourcePlayerState_InitActive:
.a8
.i16
 rep #$20
.a16
 jmp SourcePlayerState_Bad
SourcePlayerState_ClearBirth:
.a16
.i16
 php
 rep #$39
 pha
 phx
 phy
 jsr SourcePlayerState_Check
 bcc SourcePlayerState_ClearRow
 jmp SourcePlayerState_Bad
SourcePlayerState_ClearRow:
.a16
.i16
 lda #0
 ldy #12
SourcePlayerState_ClearRowLoop:
.a16
.i16
 sta.l B,x
 inx
 inx
 dey
 bne SourcePlayerState_ClearRowLoop
 jmp SourcePlayerState_Good
SourcePlayerState_Read:
.a16
.i16
 php
 rep #$39
 pha
 phx
 phy
 jsr SourcePlayerState_Check
 bcc SourcePlayerState_ReadRow
 jmp SourcePlayerState_Bad
SourcePlayerState_ReadRow:
.a16
.i16
 ldy #0
SourcePlayerState_ReadLoop:
.a16
.i16
 lda.l B,x
 phx
 tyx
 sta.l W+32,x
 plx
 inx
 inx
 iny
 iny
 cpy #24
 bcc SourcePlayerState_ReadLoop
 jmp SourcePlayerState_Good
SourcePlayerState_Write:
.a16
.i16
 php
 rep #$39
 pha
 phx
 phy
 jsr SourcePlayerState_Check
 bcc SourcePlayerState_WriteField
 jmp SourcePlayerState_Bad
SourcePlayerState_WriteField:
.a16
.i16
 lda.l W+6
 cmp #6
 bcc SourcePlayerState_WriteOffset
 jmp SourcePlayerState_Bad
SourcePlayerState_WriteOffset:
.a16
.i16
 asl a
 asl a
 clc
 adc.l W+18
 tax
 lda.l W+20
 sta.l B,x
 lda.l W+22
 sta.l B+2,x
 jmp SourcePlayerState_Good
SourcePlayerState_Release:
.a16
.i16
 php
 rep #$39
 pha
 phx
 phy
 jsr SourcePlayerState_CheckLease
 bcc SourcePlayerState_ReleaseIdle
 jmp SourcePlayerState_Bad
SourcePlayerState_ReleaseIdle:
.a16
.i16
 lda.l VmState_FrameTop
 ora.l SourceVMRun4086_Busy
 beq SourcePlayerState_ReleaseStatus
 jmp SourcePlayerState_Bad
SourcePlayerState_ReleaseStatus:
.a16
.i16
 sep #$20
.a8
 lda.l VmState_Status
 cmp #2
 beq SourcePlayerState_ReleaseActive
 cmp #3
 beq SourcePlayerState_ReleaseActive
 rep #$20
.a16
 lda #0
 sta.l W
 sta.l W+12
 sta.l W+14
 sta.l W+16
 jmp SourcePlayerState_Good
SourcePlayerState_ReleaseActive:
.a8
.i16
 rep #$20
.a16
 jmp SourcePlayerState_Bad
SourcePlayerState_Check:
.a16
.i16
 jsr SourcePlayerState_CheckLease
 bcc SourcePlayerState_CheckWorld
 rts
SourcePlayerState_CheckWorld:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 bne SourcePlayerState_CheckBad
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 bne SourcePlayerState_CheckBad
 lda.l VmSourceWorld_Count
 beq SourcePlayerState_CheckBad
 cmp #ENTITIES+1
 bcs SourcePlayerState_CheckBad
 lda.l W+4
 cmp.l VmSourceWorld_Count
 bcs SourcePlayerState_CheckBad
 asl a
 asl a
 asl a
 sta.l W+18
 asl a
 clc
 adc.l W+18
 sta.l W+18
 tax
 clc
 rts
SourcePlayerState_CheckLease:
.a16
.i16
 lda.l W
 cmp #$B67B
 bne SourcePlayerState_CheckBad
 lda.l W+12
 cmp #COUNT
 bne SourcePlayerState_CheckBad
 lda.l VmState_SlotCount
 cmp.l W+12
 bne SourcePlayerState_CheckBad
 lda.l W+8
 cmp.l W+14
 bne SourcePlayerState_CheckBad
 lda.l W+10
 cmp.l W+16
 bne SourcePlayerState_CheckBad
 ora.l W+8
 beq SourcePlayerState_CheckBad
 clc
 rts
SourcePlayerState_CheckBad:
.a16
.i16
 sec
 rts
SourcePlayerState_Good:
.a16
.i16
 lda #2
 sta.l W+2
 ply
 plx
 pla
 plp
 clc
 rtl
SourcePlayerState_Bad:
.a16
.i16
 lda #3
 sta.l W+2
 ply
 plx
 pla
 plp
 sec
 rtl
'''
    values=dict(W=work,B=base,COUNT=count,BYTES=extent,ENTITIES=plan['entities'])
    for name in ('VmState_SlotCount','VmState_FrameTop','VmState_Status','SourceVMRun4086_Busy',
                 'VmSourceWorld_Ready','VmSourceWorld_PoolBase','VmSourceWorld_Count'):
        if name not in symbols:raise ValueError('PLAYER_STATE_NATIVE_SYMBOL:'+name)
        values[name]=symbols[name]
    for name,value in values.items():code=re.sub(r'\b'+name+r'\b',str(value),code)
    return code
