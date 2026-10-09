"""Ordinary attack with mandatory real chain, target, frame and sound services.

The binding scratch uses the release owner's canonical row shape; callers
serialize both owners within one controller invocation. A live item candidate
requires its full owner. No target or physical sound result is synthesized.
"""
from source_player_run_4086 import KEYS


def emit(work,binding,chain,search,history,input_owner,profile,roles,symbols):
    spans=((work,48),(binding,128),(chain,96),(search,24),(history,1024),(input_owner,2))
    for i,(a,n)in enumerate(spans):
        if not 0<=a<=0x1000000-n:raise ValueError('PLAYER_ATTACK_EXTENT')
        if any(a<b+m and b<a+n for b,m in spans[i+1:]):raise ValueError('PLAYER_ATTACK_OVERLAP')
    if history&255 or profile.get('capability')!='READONLY_ALTERNATE_ATTACK_ABSENCE_WITH_EMPTY_ITEM_SEARCH':raise ValueError('PLAYER_ATTACK_CAPABILITY')
    if not 1<=len(profile['models'])<=16 or any(m['id']!=i for i,m in enumerate(profile['models'])):raise ValueError('PLAYER_ATTACK_MODELS')
    if any(not 0<=r<=65535 for r in roles.values()):raise ValueError('PLAYER_ATTACK_ROLES')
    lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('PlayerAttack_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;skip='PlayerAttack_Skip'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+skip+'\n jmp PlayerAttack_'+n+'\n'+skip+':\n.a16\n.i16')
    def prologue(n):label(n);put(' php\n rep #$39\n phx\n phy')
    def magic():put(f' lda.l {work}\n cmp #$B690');branch('bne')
    def resolve(role):
        put(f' lda.l {work}+4\n sta.l {symbols["SourceAnimationInit4086_Slot"]}\n lda #{roles[role]}\n sta.l {symbols["SourceAnimationInit4086_Number"]}')
        label('Query_'+role);put(f' jsl {symbols["SourceAnimationInit4086_Resolve"]}');branch('bcs')
    def absent(role):
        resolve(role);put(f' lda.l {symbols["SourceAnimationInit4086_Handle"]}');branch('beq','Absent'+role)
        put(f' lda.l {symbols["SourceAnimationInit4086_Count"]}');branch('bne')
        label('Absent'+role)
    def bind():
        put(f' lda.l {binding}\n cmp #$B68F');branch('bne')
        put(f' lda.l {work}+4\n sta.l {binding}+4\n lda.l {work}+6\n sta.l {binding}+6\n jsl PlayerRelease_Bind');branch('bcs')
        put(f' lda.l {symbols["SourceModelEntityCopy4086_Models"]}\n cmp #{len(profile["models"])}');branch('bne')
    def zero_velocity():put(f' lda.l {binding}+22\n tax\n lda #0\n sta.l $416824,x\n sta.l $416826,x\n sta.l $416828,x\n sta.l $41682A,x')
    def chain_slot():put(f' lda.l {chain}+4\n cmp.l {work}+4');branch('bne')
    prologue('Begin');magic()
    put(f' lda.l {input_owner}\n cmp #$B674');branch('bne')
    put(f' lda.l {work}+2');branch('beq','Ready');put(' cmp #2');branch('beq','Ready');put(' cmp #4');branch('bne')
    label('Ready');put(f' lda #1\n sta.l {work}+2\n lda.l {work}+6\n cmp #4');branch('bcs')
    put(f' xba\n tax\n lda.l {history}+224,x\n and #{KEYS["attack"]}');branch('beq','Continue')
    put(f' lda.l {work}+8');branch('beq','Continue');bind()
    put(f' lda.l {work}+6\n xba\n tax\n lda.l {history}+224,x\n and #{(~KEYS["attack"])&65535}\n sta.l {history}+224,x\n lda.l {binding}+30\n tax\n lda #0\n sta.l $42E008,x\n sta.l $42E00A,x')
    put(f' lda.l {work}+6\n xba\n tax\n lda.l {history}+216,x\n and #{KEYS["movedown"]}');branch('beq','Run');absent('duckattack')
    label('Run');put(f' lda.l {work}+4\n asl a\n asl a\n asl a\n sta.l {work}+20\n asl a\n clc\n adc.l {work}+20\n tax\n lda.l $42F404,x\n ora.l $42F406,x');branch('beq','Backward')
    resolve('runattack');put(f' lda.l {symbols["SourceAnimationInit4086_Handle"]}');branch('beq','Backward')
    put(f' lda.l {symbols["SourceAnimationInit4086_Count"]}');branch('beq','Backward')
    put(f' lda.l {binding}+24\n tax\n lda #17\n sta.l $43900C,x\n lda #0\n sta.l $43900E,x\n lda.l {binding}+26\n tax\n lda #1\n sta.l $40C058,x\n lda #0\n sta.l $40C05A,x\n lda.l {binding}+28\n tax\n lda #0\n sta.l $43EB00,x\n sta.l $43EB02,x\n lda.l {binding}+32\n tax\n lda #0\n sta.l $437E08,x\n sta.l $437E0A,x');zero_velocity()
    put(f' lda.l {work}+20\n asl a\n clc\n adc.l {work}+20\n tax\n lda #0\n sta.l $42F404,x\n sta.l $42F406,x\n lda #1\n sta.l {work}+16\n lda #{roles["runattack"]}\n sta.l {work}+18\n lda #0\n sta.l {symbols["SourceAnimationInit4086_Reset"]}\n jsl {symbols["SourceAnimationInit4086_Begin"]}');branch('bcs')
    put(f' lda.l {symbols["SourceAnimationInit4086_State"]}\n cmp #2');branch('beq','Return');put(' cmp #1');branch('bne');put(' jmp PlayerAttack_FramePending')
    label('Backward');absent('attackbackward');resolve('get')
    put(f' lda.l {symbols["SourceAnimationInit4086_Handle"]}');branch('beq','Charge');put(f' lda.l {symbols["SourceAnimationInit4086_Count"]}');branch('beq','Charge')
    put(f' lda.l {work}+4\n sta.l {search}+4\n lda #4\n sta.l {search}+6\n lda #0\n sta.l {search}+8\n jsl SourceFindHereEmpty_Execute');branch('bcs')
    label('Charge');put(f' lda.l {binding}+30\n tax\n lda.l {symbols["SourceClock4086_TimeLo"]}\n sta.l $42E008,x\n lda.l {symbols["SourceClock4086_TimeHi"]}\n sta.l $42E00A,x');zero_velocity()
    put(f' lda.l {binding}+28\n tax\n lda.l $43EB1C,x\n ora.l $43EB1E,x');branch('beq','ChainBegin')
    put(f' lda.l $43EB1C,x\n sta.l {symbols["SourceRetirement4086_ArgLo"]}\n lda.l $43EB1E,x\n sta.l {symbols["SourceRetirement4086_ArgHi"]}\n jsl {symbols["SourceRetirement4086_ResolvePointer"]}');branch('bcs')
    put(f' cmp #$FFFF');branch('beq');put(f' sta.l {work}+24')
    put(' lda #0')
    for bit in range(6,-1,-1):
        put(' asl a')
        if 80&(1<<bit):put(f' clc\n adc.l {work}+24')
    put(f' sta.l {work}+26\n tax\n lda.l $43904A,x\n cmp #$B4FB');branch('bne')
    put(' lda.l $439032,x');branch('bne','ChainBegin')
    put(' lda.l $439030,x\n cmp #9');branch('bne','ChainBegin');absent('throwattack')
    label('ChainBegin')
    put(f' lda #2\n sta.l {work}+16\n lda.l {work}+4\n sta.l {chain}+4\n jsl SourceAttackChain_Begin');branch('bcs')
    label('ChainResult');put(f' lda.l {chain}+2\n cmp #2');branch('beq','Continue');put(' cmp #3');branch('beq','TargetPending');put(' cmp #4');branch('beq','FramePending');put(' cmp #5');branch('bne')
    bind();put(f' lda.l {work}+14\n and #$8000');branch('bne','Return')
    put(f' lda.l {binding}+26\n tax\n lda.l $40C058,x\n ora.l $40C05A,x');branch('beq','Return')
    put(f' lda #0\n sta.l {work}+22\n lda #7\n sta.l {work}+2\n lda #$8003');put(' jmp PlayerAttack_Exit')
    prologue('ResumeTarget');magic();put(f' lda.l {work}+2\n cmp #6');branch('bne');chain_slot()
    put(' jsl SourceAttackChain_TargetResume');branch('bcs');put(' jmp PlayerAttack_ChainResult')
    prologue('FinishFrame');magic();put(f' lda.l {work}+2\n cmp #3');branch('bne')
    put(f' lda.l {symbols["SourceAnimationInit4086_Slot"]}\n cmp.l {work}+4');branch('bne')
    put(f' lda.l {work}+16\n cmp #1');branch('beq','RunFrame');put(' cmp #2');branch('bne');chain_slot()
    put(f' lda.l {symbols["SourceAnimationInit4086_Number"]}\n cmp.l {chain}+6');branch('bne')
    put(f' jsl {symbols["SourceAnimationInit4086_Ack"]}');branch('bcs');put(' jsl SourceAttackChain_Finish');branch('bcs');put(' jmp PlayerAttack_ChainResult')
    label('RunFrame');put(f' lda.l {symbols["SourceAnimationInit4086_Number"]}\n cmp.l {work}+18');branch('bne')
    put(f' jsl {symbols["SourceAnimationInit4086_Ack"]}');branch('bcs');put(' jmp PlayerAttack_Return')
    prologue('FinishSound');magic();put(f' lda.l {work}+2\n cmp #7');branch('bne')
    put(f' lda.l {work}+22\n cmp #1');branch('beq','Return');put(' cmp #2');branch('bne')
    label('Return');put(f' lda #4\n sta.l {work}+2\n lda #0');put(' jmp PlayerAttack_Exit')
    label('Continue');put(f' lda #2\n sta.l {work}+2\n lda #0');put(' jmp PlayerAttack_Exit')
    label('FramePending');put(f' lda #3\n sta.l {work}+2\n lda #$8002');put(' jmp PlayerAttack_Exit')
    label('TargetPending');put(f' lda #6\n sta.l {work}+2\n lda #$8001')
    label('Exit');put(' ply\n plx\n plp\n clc\n rtl')
    label('Bad');put(f' lda #5\n sta.l {work}+2\n ply\n plx\n plp\n sec\n rtl')
    return '\n'.join(lines)+'\n'
