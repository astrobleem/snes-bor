"""Ranged player-think target provider using existing canonical target controls.

No new arena allocation. A=animation role (FFFF unbounded), X/Y=detection
adjustment low/high. The actual AI owner is required; common_think is never
fabricated. Shared unbounded presentation/dispatch code remains unchanged.
"""
from pathlib import Path
import re
from source_engine_function_ids import function_id


def emit(symbols,repository=None,chain=None):
    root=Path(repository)if repository is not None else Path(__file__).resolve().parents[2]
    ai=(root/'src/core/vm/vm_source_ai_target.pasm').read_text(encoding='cp1252')
    scan=(root/'src/core/vm/vm_source_target.pasm').read_text(encoding='cp1252')
    # Reuse the actual source scan and preference rules, adding only range
    # eligibility in the source order: type, range, dead, distance, stealth.
    ai=ai[ai.index('SourceAITarget4086_Owner:'):]
    scan=scan[scan.index('Vm_SourceFindTarget_Begin:'):scan.index('; Validate the complete pointer-order')]
    labels=set(re.findall(r'^(\w+):',ai+'\n'+scan,re.M))
    labels.add('Vm_SourceFindTarget_Bad');labels.add('Vm_NativeVariantDispatch__null_ok')
    for old in sorted(labels,key=len,reverse=True):
        new='NormalTarget_'+old
        ai=re.sub(r'\b'+old+r'\b',new,ai);scan=re.sub(r'\b'+old+r'\b',new,scan)
    old=' sta.l SourceTarget4086_DetectLo\n lda.l SOURCE_ENTITY_AI_STATE+18,x\n sta.l SourceTarget4086_DetectHi'
    new=' clc\n adc.l SourceAITarget4086_Result\n sta.l SourceTarget4086_DetectLo\n lda.l SOURCE_ENTITY_AI_STATE+18,x\n adc.l SourceAITarget4086_Result+2\n sta.l SourceTarget4086_DetectHi\n bvc NormalTarget_DetectOK\n jmp NormalTarget_SourceAITarget4086_Bad\nNormalTarget_DetectOK:\n.a16\n.i16'
    if ai.count(old)!=1:raise ValueError('NORMAL_TARGET_DETECT_REUSE_AUTHORITY')
    ai=ai.replace(old,new).replace(' jsl Vm_SourceFindTarget_Begin',' jsl NormalTarget_Vm_SourceFindTarget_Begin')
    old='    lda.l SOURCE_TARGET_META+4,x\n    beq NormalTarget_Vm_SourceFindTarget_Hostile\n    jmp NormalTarget_Vm_SourceFindTarget_Next'
    if scan.count(old)!=1:raise ValueError('NORMAL_TARGET_DEAD_FILTER_AUTHORITY')
    scan=scan.replace(old,'    jmp NormalTarget_Vm_SourceFindTarget_Hostile')
    old='    bne NormalTarget_Vm_SourceFindTarget_Stealth'
    if scan.count(old)!=1:raise ValueError('NORMAL_TARGET_TYPE_FILTER_AUTHORITY')
    scan=scan.replace(old,'    bne NormalTarget_RangeEligibility',1)
    needle='NormalTarget_Vm_SourceFindTarget_Stealth:'
    scan=scan.replace(needle,'''
NormalTarget_RangeEligibility:
.a16
.i16
 lda.l SourceEntityRange4086_Role
 cmp #$FFFF
 beq NormalTarget_RangePassed
 tax
 lda.l SourceTarget4086_CurrentSlot
 jsl NormalTarget_EntityRange
 bcc NormalTarget_RangeReturned
 jmp NormalTarget_Vm_SourceFindTarget_Corrupt
NormalTarget_RangeReturned:
.a16
.i16
 lda.l SourceEntityRange4086_Result
 ora.l SourceEntityRange4086_Result+2
 bne NormalTarget_RangePassed
 jmp NormalTarget_Vm_SourceFindTarget_Next
NormalTarget_RangePassed:
.a16
.i16
 ldx.l SourceTarget4086_Meta
 lda.l SOURCE_TARGET_META+4,x
 beq NormalTarget_Vm_SourceFindTarget_Stealth
 jmp NormalTarget_Vm_SourceFindTarget_Next
'''.replace(' ldx.l SourceTarget4086_Meta',' lda.l SourceTarget4086_Meta\n tax')+needle,1)
    prefix=f'''
NormalTarget_Begin:
.a16
.i16
 php
 rep #$39
 phx
 phy
 pha
 lda.l SourceAITarget4086_Ready
 cmp #$B5F3
 bne NormalTarget_EntryBad
 lda.l SourceAITarget4086_Status
 beq NormalTarget_EntryReady
 cmp #2
 bne NormalTarget_EntryBad
NormalTarget_EntryReady:
.a16
.i16
 jsr NormalTarget_CheckPlayerOwner
 bcs NormalTarget_EntryBad
 pla
 sta.l SourceEntityRange4086_Role
 txa
 sta.l SourceAITarget4086_Result
 tya
 sta.l SourceAITarget4086_Result+2
 lda #1
 sta.l SourceAITarget4086_Status
 jmp NormalTarget_SourceAITarget4086_Owner
NormalTarget_EntryBad:
.a16
.i16
 pla
 jmp NormalTarget_SourceAITarget4086_Bad
NormalTarget_CheckPlayerOwner:
.a16
.i16
 lda.l SourceAI4086_State
 cmp #2
 bne NormalTarget_OwnerBad
 lda.l SourceAI4086_Callback+2
 bne NormalTarget_OwnerBad
 lda.l SourceAI4086_Callback
 cmp #{function_id('player_think')}
 bne NormalTarget_OwnerBad
 jsl SourceAI4086_CheckOwner
 rts
NormalTarget_OwnerBad:
.a16
.i16
 sec
 rts
NormalTarget_EntityRange:
.a16
.i16
 php
 rep #$39
 phx
 phy
 sta.l SourceEntityRange4086_TargetSlot
 txa
 sta.l SourceEntityRange4086_Role
 lda.l SourceEntityRange4086_Ready
 cmp #$B5F9
 bne NormalTarget_EntityRangeBad
 lda.l SourceEntityRange4086_Status
 beq NormalTarget_EntityRangeReady
 cmp #2
 bne NormalTarget_EntityRangeBad
NormalTarget_EntityRangeReady:
.a16
.i16
 jsr NormalTarget_CheckPlayerOwner
 bcs NormalTarget_EntityRangeBad
 lda #1
 sta.l SourceEntityRange4086_Status
 jml SourceEntityRange4086_Guard3
NormalTarget_EntityRangeBad:
.a16
.i16
 jml SourceEntityRange4086_Bad
'''
    tail='''
NormalTarget_Vm_SourceFindTarget_Bad:
.a16
.i16
 sec
 rtl
NormalTarget_Vm_NativeVariantDispatch__null_ok:
.a16
.i16
 lda #0
 sta.l VmNativeVariant_Result
 sta.l VmNativeVariant_Result+2
 sta.l VmNativeVariant_Result+4
 sta.l VmNativeVariant_Result+6
 clc
 rtl
'''
    bridge=''
    if chain is not None:
        if not 0<=chain<=0x1000000-96:raise ValueError('NORMAL_TARGET_CHAIN_EXTENT')
        bridge=f'''
NormalTarget_AttackChain:
.a16
.i16
 php
 rep #$39
 phx
 phy
 jsr NormalTarget_CheckPlayerOwner
 bcs NormalTarget_ChainBad
 lda.l {chain}
 cmp #$B675
 bne NormalTarget_ChainBad
 lda.l {chain}+2
 cmp #3
 bne NormalTarget_ChainBad
 lda.l {chain}+4
 cmp.l SourceAI4086_Slot
 bne NormalTarget_ChainBad
 lda.l {chain}+18
 bne NormalTarget_ChainBad
 lda.l {chain}+12
 cmp #2
 bcs NormalTarget_ChainBad
 lda.l {chain}+50
 cmp.l {chain}+6
 bne NormalTarget_ChainBad
 cmp.l SourceModelAnimationCopy4086_Maximum
 bcs NormalTarget_ChainBad
 ldx #0
 ldy #0
 jsl NormalTarget_Begin
 bcs NormalTarget_ChainBad
 lda.l SourceAITarget4086_Status
 cmp #2
 bne NormalTarget_ChainBad
 lda.l SourceAITarget4086_Result
 sta.l {chain}+14
 lda.l SourceAITarget4086_Result+2
 sta.l {chain}+16
 lda.l {chain}+4
 sta.l {chain}+52
 lda.l {chain}+50
 sta.l {chain}+54
 ; Publish the response marker only after its complete identity and pointer.
 lda #$B676
 sta.l {chain}+18
 ply
 plx
 plp
 clc
 rtl
NormalTarget_ChainBad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
'''
    code=prefix+ai+'\n'+scan+tail+bridge
    # Every local branch stays in the compiled provider bank; public calls and
    # globals use resolved full addresses from the current native runtime.
    serial=[0]
    def relax(m):
        serial[0]+=1;label='NormalTarget_LongBranch'+str(serial[0])
        return m[1]+{'beq':'bne','bne':'beq','bcc':'bcs','bcs':'bcc','bvc':'bvs','bvs':'bvc'}[m[2]]+' '+label+'\n jmp '+m[3]+'\n'+label+':\n.a16\n.i16'
    code=re.sub(r'^(\s+)(beq|bne|bcc|bcs|bvc|bvs) (NormalTarget_\w+)$',relax,code,flags=re.M)
    for name in sorted(symbols,key=len,reverse=True):
        if name.startswith(('Source','Vm','SOURCE_','BOR_')):code=re.sub(r'\b'+re.escape(name)+r'\b',str(symbols[name]),code)
    return code
