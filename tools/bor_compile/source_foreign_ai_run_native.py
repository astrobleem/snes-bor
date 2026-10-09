"""Extend the actual check_ai dispatcher with generic compiled player/jump owners.

Uses the existing AIRun controls. Legacy callback requests enter the unchanged
dispatcher with the same saved CPU stack. New sound/target requests remain
explicit; a frame acknowledgment cannot retire either service.
"""
from source_engine_function_ids import function_id


def emit(tryjump,dojump,player,sample_jump,symbols):
    if not -2147483648<=sample_jump<=2147483647:raise ValueError('FOREIGN_AI_JUMP_SOUND_DOMAIN')
    spans=((tryjump,64),(dojump,80))+(((player,32),)if player is not None else())
    for i,(a,n)in enumerate(spans):
        if not 0<=a<=0x1000000-n or any(a<b+m and b<a+n for b,m in spans[i+1:]):raise ValueError('FOREIGN_AI_CONTROL_LAYOUT')
    lines=[];serial=0;state=symbols['SourceAIRun4086_State'];pending=symbols['SourceAIRun4086_PendingKind']
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('ForeignAIRun_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;skip='ForeignAIRun_Skip'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+skip+'\n jmp ForeignAIRun_'+n+'\n'+skip+':\n.a16\n.i16')
    def entry(n):
        label(n);put(f' php\n rep #$39\n phx\n phy\n lda.l {symbols["SourceAIRun4086_Ready"]}\n cmp #$B5E6');branch('bne')
    entry('Begin');put(f' lda.l {state}');branch('beq','BeginReady');put(' cmp #2');branch('bne')
    label('BeginReady');put(f' jsl {symbols["SourceAI4086_Begin"]}');branch('bcs');put(' jmp ForeignAIRun_Dispatch')
    entry('Continue');put(f' lda.l {state}\n cmp #1');branch('bne')
    put(f' jsl {symbols["SourceAI4086_CheckOwner"]}');branch('bcs')
    put(f' lda.l {pending}\n cmp #$0212');branch('beq','DoJumpFrame');put(f' cmp #{function_id("common_jump")}');branch('beq','LandFrame');put(f' cmp #{function_id("common_jumpland")}');branch('beq','LandFrame')
    if player is not None:
        put(' cmp #$0402');branch('beq','PlayerFrame')
    # After this same-stack tail call, the legacy routine restores our saved
    # X/Y/P exactly once. Its Far10 starts after its own identical prologue.
    put(f' jml {symbols["SourceAIRun4086_Far10"]}')
    label('DoJumpFrame');put(' jsl ForeignAIRun_CheckDoJumpOwner');branch('bcs');put(' jsl DoJump_FinishFrame');branch('bcs');put(' jmp ForeignAIRun_ActionComplete')
    label('LandFrame');put(' jsl ForeignAIRun_CheckActionOwner');branch('bcs')
    put(f' lda.l {dojump}\n cmp #$B695');branch('bne')
    put(f' lda.l {dojump}+4\n cmp.l {symbols["SourceAI4086_Slot"]}');branch('bne')
    put(f' lda.l {dojump}+10\n cmp.l {symbols["SourceAI4086_Callback"]}');branch('bne')
    put(' jsl CommonJump_FinishFrame');branch('bcs');put(' jmp ForeignAIRun_ActionComplete')
    if player is not None:
        label('PlayerFrame');put(' jsl ForeignAIRun_CheckPlayerOwner');branch('bcs');put(' jsl PlayerController_FinishFrame');branch('bcs');put(' jmp ForeignAIRun_PlayerResult')
    entry('FinishSound');put(f' lda.l {state}\n cmp #4');branch('bne');put(f' jsl {symbols["SourceAI4086_CheckOwner"]}');branch('bcs')
    put(f' lda.l {pending}\n cmp #$0112');branch('beq','JumpSound')
    if player is not None:
        put(' cmp #$0102');branch('beq','PlayerSound')
    put(' jmp ForeignAIRun_Bad')
    label('JumpSound');put(' jsl ForeignAIRun_CheckDoJumpOwner');branch('bcs');put(' jsl DoJump_FinishSound');branch('bcs');put(' jmp ForeignAIRun_DoJumpResult')
    if player is not None:
        label('PlayerSound');put(' jsl ForeignAIRun_CheckPlayerOwner');branch('bcs');put(' jsl PlayerController_FinishSound');branch('bcs');put(' jmp ForeignAIRun_PlayerResult')
        entry('ResumeTarget');put(f' lda.l {state}\n cmp #5');branch('bne');put(f' lda.l {pending}\n cmp #$0202');branch('bne')
        put(f' jsl {symbols["SourceAI4086_CheckOwner"]}');branch('bcs');put(' jsl ForeignAIRun_CheckPlayerOwner');branch('bcs');put(' jsl PlayerController_ResumeTarget');branch('bcs');put(' jmp ForeignAIRun_PlayerResult')
    label('Dispatch');put(' cmp #0');branch('beq','Done')
    put(f' lda.l {symbols["SourceAI4086_Callback"]}+2');branch('bne','Legacy')
    put(f' lda.l {symbols["SourceAI4086_State"]}\n cmp #1');branch('bne','Think')
    put(f' lda.l {symbols["SourceAI4086_Callback"]}\n cmp #{function_id("common_prejump")}');branch('beq','Prejump')
    put(f' cmp #{function_id("common_jump")}');branch('beq','Jump');put(f' cmp #{function_id("common_jumpland")}');branch('beq','Jumpland');put(' jmp ForeignAIRun_Legacy')
    label('Think')
    if player is not None:
        put(f' lda.l {symbols["SourceAI4086_State"]}\n cmp #2');branch('bne','Legacy')
        put(f' lda.l {symbols["SourceAI4086_Callback"]}\n cmp #{function_id("player_think")}');branch('beq','Player')
    label('Legacy');put(f' lda.l {symbols["SourceAI4086_State"]}\n jml {symbols["SourceAIRun4086_Dispatch"]}')
    label('Prejump');put(f' lda.l {tryjump}\n cmp #$B692');branch('bne')
    put(f' lda.l {tryjump}+2');branch('beq','PrejumpSlot');put(' cmp #2');branch('beq','PrejumpSlot');put(' cmp #4');branch('bne')
    label('PrejumpSlot');put(f' lda.l {symbols["SourceAI4086_Slot"]}\n sta.l {tryjump}+4\n jsl TryJump_CommonPrejump');branch('bcs')
    put(f' lda.l {tryjump}+2\n cmp #4');branch('beq','ActionComplete');put(' cmp #5');branch('bne')
    label('PrejumpRequired')
    put(' jsl ForeignAIRun_CheckJumpLease');branch('bcs')
    put(f' lda #$B693\n sta.l {dojump}\n lda #0\n sta.l {dojump}+2')
    for at in range(4,20,2):put(f' lda.l {tryjump}+{at}\n sta.l {dojump}+{at}')
    put(f' lda #{sample_jump&65535}\n sta.l {dojump}+20\n lda #{(sample_jump>>16)&65535}\n sta.l {dojump}+22\n jsl DoJump_Begin');branch('bcs')
    label('DoJumpResult');put(f' lda.l {dojump}+2\n cmp #2');branch('beq','ActionComplete');put(' cmp #4');branch('beq','JumpFramePending');put(' cmp #3');branch('bne')
    put(f' lda #$0112\n sta.l {pending}\n lda #4\n sta.l {state}\n lda #$8001\n jmp ForeignAIRun_Exit')
    label('JumpFramePending');put(' lda #$0212\n jmp ForeignAIRun_FramePending')
    for name,call,identity in (('Jump','CommonJump_Begin','common_jump'),('Jumpland','CommonJump_Jumpland','common_jumpland')):
        label(name);put(' jsl ForeignAIRun_CheckJumpLease');branch('bcs')
        put(f' lda.l {symbols["SourceAI4086_Slot"]}\n sta.l {dojump}+4\n jsl {call}');branch('bcs')
        put(f' lda.l {dojump}+2\n cmp #2');branch('beq','ActionComplete');put(' cmp #3');branch('bne')
        put(f' lda #{function_id(identity)}\n jmp ForeignAIRun_FramePending')
    if player is not None:
        label('Player');put(f' lda.l {player}\n cmp #$B688');branch('bne')
        put(f' lda.l {player}+2');branch('beq','PlayerReady');put(' cmp #2');branch('beq','PlayerReady');put(' cmp #4');branch('bne')
        label('PlayerReady')
        put(f' lda.l {symbols["SourceClock4086_TimeLo"]}\n sta.l {player}+12\n lda.l {symbols["SourceClock4086_TimeHi"]}\n sta.l {player}+14\n lda.l {symbols["SourceAI4086_Slot"]}\n sta.l {player}+4\n jsl PlayerController_Begin');branch('bcs')
        label('PlayerResult');put(f' lda.l {player}+2\n cmp #4');branch('beq','ThinkComplete');put(' cmp #3');branch('beq','PlayerFramePending');put(' cmp #7');branch('beq','PlayerSoundPending');put(' cmp #8');branch('beq','PlayerTargetPending')
        # An absent-JUMPDELAY dojump request requires its full owner. The
        # present source fixture does not admit silently returning from it.
        put(' jmp ForeignAIRun_Bad')
        label('PlayerFramePending');put(' lda #$0402\n jmp ForeignAIRun_FramePending')
        for name,kind,result_state,result in (('PlayerSoundPending',0x0102,4,0x8001),('PlayerTargetPending',0x0202,5,0x8002)):
            label(name);put(f' lda #{kind}\n sta.l {pending}\n lda #{result_state}\n sta.l {state}\n lda #{result}\n jmp ForeignAIRun_Exit')
        label('ThinkComplete');put(' lda #2\n jmp ForeignAIRun_Resume')
    label('ActionComplete')
    # The source action completed; release its descriptor-control lease only
    # after all dojump services have finished. Persistent row data is retained.
    put(f' lda.l {symbols["SourceAI4086_Callback"]}+2');branch('bne','ActionResume')
    put(f' lda.l {symbols["SourceAI4086_Callback"]}\n cmp #{function_id("common_prejump")}');branch('bne','ActionResume')
    put(f' lda #4\n sta.l {tryjump}+2')
    label('ActionResume');put(' lda #1')
    label('Resume');put(f' jsl {symbols["SourceAI4086_Continue"]}');branch('bcs');put(' jmp ForeignAIRun_Dispatch')
    label('FramePending');put(f' sta.l {pending}\n lda #1\n sta.l {state}\n jmp ForeignAIRun_Exit')
    label('Done');put(f' lda #2\n sta.l {state}\n lda #0\n sta.l {pending}')
    label('Exit');put(' ply\n plx\n plp\n clc\n rtl')
    label('Bad');put(f' lda #3\n sta.l {state}\n ply\n plx\n plp\n sec\n rtl')
    label('CheckJumpLease');put(f' lda.l {dojump}\n cmp #$B693');branch('beq','DoLease');put(' cmp #$B695');branch('bne','LeaseBad')
    put(f' lda.l {dojump}+2');branch('beq','LeaseGood');put(' cmp #2');branch('beq','LeaseGood');put(' jmp ForeignAIRun_LeaseBad')
    label('DoLease');put(f' lda.l {dojump}+2\n cmp #2');branch('bne','LeaseBad')
    label('LeaseGood');put(' clc\n rtl');label('LeaseBad');put(' sec\n rtl')
    label('CheckDoJumpOwner');put(' jsl ForeignAIRun_CheckActionOwner');branch('bcs','LeaseBad')
    put(f' lda.l {symbols["SourceAI4086_Callback"]}\n cmp #{function_id("common_prejump")}');branch('bne','LeaseBad')
    put(f' lda.l {dojump}\n cmp #$B693');branch('bne','LeaseBad')
    put(f' lda.l {dojump}+4\n cmp.l {symbols["SourceAI4086_Slot"]}');branch('bne','LeaseBad');put(' clc\n rtl')
    label('CheckActionOwner');put(f' lda.l {symbols["SourceAI4086_State"]}\n cmp #1');branch('bne','LeaseBad')
    put(f' lda.l {symbols["SourceAI4086_Callback"]}+2');branch('bne','LeaseBad');put(' clc\n rtl')
    if player is not None:
        label('CheckPlayerOwner');put(f' lda.l {symbols["SourceAI4086_State"]}\n cmp #2');branch('bne','LeaseBad')
        put(f' lda.l {symbols["SourceAI4086_Callback"]}+2');branch('bne','LeaseBad')
        put(f' lda.l {symbols["SourceAI4086_Callback"]}\n cmp #{function_id("player_think")}');branch('bne','LeaseBad')
        put(f' lda.l {player}\n cmp #$B688');branch('bne','LeaseBad')
        put(f' lda.l {player}+4\n cmp.l {symbols["SourceAI4086_Slot"]}');branch('bne','LeaseBad');put(' clc\n rtl')
    return '\n'.join(lines)+'\n'
