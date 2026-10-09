"""Generic player-capable no-attached-item dropweapon(1) presentation service.

Retains explicit required status for a different model and for attached items.
Uses existing real weapon resolver and same-model transition, with source player
weapnum/level fallback before resolution. Private code, no bank-zero growth.
"""
import re
from pathlib import Path


def emit(sy,model_pipeline=False):
    raw=Path('src/core/vm/vm_source_drop_weapon.pasm').read_text()
    old=' lda #2\n jmp SourceDropWeapon4086_Return\nSourceDropWeapon4086_Nonplayer:'
    if raw.count(old)!=1:raise ValueError('PLAYER_DROP_NATIVE_SOURCE_SHAPE')
    player='''
 lda.l SourceWeapon4086_Ready
 cmp #$B4F1
 beq SourceDropWeapon4086_PlayerReady
 jmp SourceDropWeapon4086_Bad
SourceDropWeapon4086_PlayerReady:
.a16
.i16
 lda.l SourceWeapon4086_Players
 beq SourceDropWeapon4086_PlayerBad
 cmp #5
 bcc SourceDropWeapon4086_PlayerCount
SourceDropWeapon4086_PlayerBad:
.a16
.i16
 jmp SourceDropWeapon4086_Bad
SourceDropWeapon4086_PlayerCount:
.a16
.i16
 lda.l SourceDropWeapon4086_Side
 clc
 adc.l SourceDropWeapon4086_Weapon
 tax
 lda.l $414028,x
 cmp #1
 bne SourceDropWeapon4086_PlayerBad
 lda.l $41402A,x
 ora.l $41402E,x
 bne SourceDropWeapon4086_PlayerBad
 lda.l $41402C,x
 cmp.l SourceWeapon4086_Players
 bcs SourceDropWeapon4086_PlayerBad
 asl a
 asl a
 tax
 lda.l $43EA00,x
 ora.l $43EA02,x
 beq SourceDropWeapon4086_PlayerLevel
 lda.l $43EA00,x
 sta.l SourceWeapon4086_NumberLo
 lda.l $43EA02,x
 sta.l SourceWeapon4086_NumberHi
 bra SourceDropWeapon4086_PlayerSelected
SourceDropWeapon4086_PlayerLevel:
.a16
.i16
 lda.l SourceWeapon4086_LevelWeaponLo
 sta.l SourceWeapon4086_NumberLo
 lda.l SourceWeapon4086_LevelWeaponHi
 sta.l SourceWeapon4086_NumberHi
SourceDropWeapon4086_PlayerSelected:
.a16
.i16
 lda #0
 sta.l SourceDropWeapon4086_Phase
 sta.l SourceWeapon4086_AnimFlagLo
 sta.l SourceWeapon4086_AnimFlagHi
 jmp SourceDropWeapon4086_Resolve
SourceDropWeapon4086_Nonplayer:'''
    raw=raw.replace(old,player).replace(' beq SourceDropWeapon4086_Nonplayer\n',' bne SourceDropWeapon4086_PlayerBegin\n jmp SourceDropWeapon4086_Nonplayer\nSourceDropWeapon4086_PlayerBegin:\n.a16\n.i16\n').replace('rep #$38','rep #$39').replace('SourceDropWeapon4086_','SourcePlayerDropWeapon4086_')
    if model_pipeline:
        anchor=' lda #3\n jmp SourcePlayerDropWeapon4086_Return\nSourcePlayerDropWeapon4086_Same:'
        if raw.count(anchor)!=1:raise ValueError('PLAYER_DROP_PIPELINE_SOURCE_SHAPE')
        body=''' lda.l SourceWeapon4086_Selected
 sta.l SourceModelTransition4086_New
 lda.l SourceWeapon4086_Sync
 sta.l SourceModelAnimation4086_Sync
 jsl SourceModelTransition4086_Begin
 bcc SourcePlayerDropWeapon4086_PipelineBegin
 jmp SourcePlayerDropWeapon4086_Bad
SourcePlayerDropWeapon4086_PipelineBegin:
.a16
.i16
 lda.l SourceForeignWork_Generation
 tax
 lda.l SourceForeignWork_Generation+2
 tay
 jsl ModelPipeline_Resume
 bcc SourcePlayerDropWeapon4086_PipelineComplete
 jmp SourcePlayerDropWeapon4086_Bad
SourcePlayerDropWeapon4086_PipelineComplete:
.a16
.i16
 jmp SourcePlayerDropWeapon4086_G10
SourcePlayerDropWeapon4086_Same:'''
        raw=raw.replace(anchor,body)
    def replace(m):
        n=m[0]
        return str(sy[n])if n in sy else n
    raw=re.sub(r'\b(?:Source(?:Weapon|ModelEntityCopy|ModelTransition|ModelAnimation|Lifecycle)4086_|SourceForeignWork_)[A-Za-z0-9_]+\b',replace,raw)
    return raw
