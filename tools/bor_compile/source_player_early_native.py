"""Canonical player_think entry prefix with mandatory real helper continuations.

State 2 continues the still-required controller body; state 4 returns from
player_think. Matching ENDLEVEL candidates reject until completion is owned.
"""


def emit(work,state,search,combo,charge,pain,symbols,fall=None,jump=None,lie=None,idle_profile=None,directional=None,buttons=None,release=None,attack=None):
    spans=((work,32),(state,64),(search,24),(combo,96),(charge,24),(pain,24))+(((fall,24),)if fall is not None else())+(((jump,32),)if jump is not None else())+(((lie,16),)if lie is not None else())+(((directional,64),)if directional is not None else())+(((buttons,48),)if buttons is not None else())+(((release,128),)if release is not None else())+(((attack,48),)if attack is not None else())
    for i,(a,n)in enumerate(spans):
        if not 0<=a<=0x1000000-n:raise ValueError('PLAYER_EARLY_EXTENT')
        if any(a<b+m and b<a+n for b,m in spans[i+1:]):raise ValueError('PLAYER_EARLY_OVERLAP')
    if idle_profile is not None and(idle_profile.get('capability')!='IMMUTABLE_ABSENT_ANIMATION_IDLE_ARRAY' or not idle_profile.get('models')):raise ValueError('PLAYER_EARLY_IDLE_CAPABILITY')
    if release is not None and(directional is None or buttons is None):raise ValueError('PLAYER_EARLY_RELEASE_REQUIRES_PRIOR_OWNERS')
    if attack is not None and release is None:raise ValueError('PLAYER_EARLY_ATTACK_REQUIRES_RELEASE_OWNER')
    lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('PlayerEarly_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;skip='PlayerEarly_Skip'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+skip+'\n jmp PlayerEarly_'+n+'\n'+skip+':\n.a16\n.i16')
    def offset(dest,stride):
        put(' lda #0')
        for bit in range(stride.bit_length()-1,-1,-1):
            put(' asl a')
            if stride&(1<<bit):put(f' clc\n adc.l {work}+4')
        put(f' sta.l {work}+{dest}')
    def state_read():
        put(f' lda.l {work}+4\n sta.l {state}+4\n jsl SourcePlayerState_Read');branch('bcs')
    label('Begin');put(f' php\n rep #$39\n phx\n phy\n lda.l {work}\n cmp #$B688');branch('bne')
    put(f' lda.l {work}+2');branch('beq','Ready');put(' cmp #2');branch('beq','Ready');put(' cmp #4');branch('bne')
    label('Ready');put(f' lda #1\n sta.l {work}+2');state_read()
    for dest,stride in ((18,80),(20,64),(22,24),(24,32),(26,96)):offset(dest,stride)
    put(f' lda.l {work}+22\n tax\n lda.l $42F404,x\n sta.l {work}+8\n lda.l $42F406,x\n sta.l {work}+10')
    put(f' lda.l {work}+18\n tax\n clc\n adc #$4000\n cmp.l $414000,x');branch('bne')
    put(' lda.l $414002,x\n cmp #$41');branch('bne')
    put(' lda.l $414028,x\n cmp #1');branch('bne')
    put(' lda.l $41402A,x\n ora.l $41402E,x');branch('bne')
    put(' lda.l $41402C,x\n cmp #4');branch('bcs')
    put(f' sta.l {work}+6\n asl a\n asl a\n tax\n lda.l $43FD86,x\n cmp #$41');branch('bne','Exit')
    put(f' lda.l {work}+18\n clc\n adc #$4000\n cmp.l $43FD84,x');branch('bne','Exit')
    put(f' lda.l {work}+18\n tax\n lda.l $439014,x\n ora.l $439016,x');branch('bne','Exit')
    put(f' lda.l {work}+4\n sta.l {search}+4\n lda #256\n sta.l {search}+6\n lda #0\n sta.l {search}+8\n jsl SourceFindHereEmpty_Execute');branch('bcs')
    put(f' lda.l {search}+2\n cmp #2');branch('bne')
    # Source time and rush.time are both u32; strict greater-than, no signed test.
    put(f' lda.l {work}+14\n cmp.l {state}+54');branch('bcc','Preinput');branch('bne','RushExpired')
    put(f' lda.l {work}+12\n cmp.l {state}+52');branch('bcc','Preinput');branch('beq','Preinput')
    label('RushExpired');put(f' lda #0\n sta.l {state}+20\n sta.l {state}+22\n lda #3\n sta.l {state}+6\n jsl SourcePlayerState_Write');branch('bcs')
    put(f' lda #5\n sta.l {state}+6\n jsl SourcePlayerState_Write');branch('bcs')
    label('Preinput');put(f' lda.l {work}+4\n sta.l {combo}+4\n lda #1\n sta.l {work}+16\n jsl SourceCombo_Begin');branch('bcs')
    label('ComboResult');put(f' lda.l {combo}+2\n cmp #4');branch('beq','Exit');put(' cmp #3');branch('beq','Pending');put(' cmp #2');branch('bne')
    state_read();put(f' lda.l {state}+32\n ora.l {state}+34');branch('bne','Charge')
    put(f' lda.l {work}+24\n tax\n lda.l $43EB04,x\n ora.l $43EB06,x');branch('bne','Pain')
    put(f' lda.l {work}+20\n tax\n lda.l $40901C,x\n ora.l $40901E,x');branch('beq','Continue')
    put(f' lda.l {work}+26\n tax\n lda.l $40C050,x\n ora.l $40C052,x');branch('bne','Continue')
    label('Pain');put(f' lda.l {work}+4\n sta.l {pain}+4\n lda #3\n sta.l {work}+16\n jsl PainServices_Begin');branch('bcs');put(' jmp PlayerEarly_HelperResult')
    label('Charge');put(f' lda.l {work}+4\n sta.l {charge}+4\n lda #2\n sta.l {work}+16\n jsl ChargeServices_Begin');branch('bcs')
    label('HelperResult');put(' cmp #0');branch('beq','Exit');put(' cmp #1');branch('bne')
    label('Pending');put(f' lda #3\n sta.l {work}+2\n lda #1\n ply\n plx\n plp\n clc\n rtl')
    label('FinishFrame');put(f' php\n rep #$39\n phx\n phy\n lda.l {work}\n cmp #$B688');branch('bne')
    put(f' lda.l {work}+2\n cmp #3');branch('bne')
    put(f' lda.l {work}+16\n cmp #1');branch('beq','ComboFinish');put(' cmp #2');branch('beq','ChargeFinish')
    if jump is not None:
        put(' cmp #4');branch('beq','JumpFinish')
    if buttons is not None:
        put(' cmp #5');branch('beq','ButtonFinish')
    if release is not None:
        put(' cmp #6');branch('beq','ReleaseFinish')
    if attack is not None:
        put(' cmp #7');branch('beq','AttackFinish')
    put(' cmp #3');branch('bne')
    put(' jsl PainServices_FinishFrame');branch('bcs');put(' jmp PlayerEarly_HelperResult')
    label('ChargeFinish');put(' jsl ChargeServices_FinishFrame');branch('bcs');put(' jmp PlayerEarly_HelperResult')
    if jump is not None:
        label('JumpFinish');put(' jsl PlayerJump_FinishFrame');branch('bcs');put(' jmp PlayerEarly_HelperResult')
    if buttons is not None:
        label('ButtonFinish');put(' jsl PlayerButton_FinishFrame');branch('bcs');put(' jmp PlayerEarly_ButtonResult')
    if release is not None:
        label('ReleaseFinish')
        put(f' lda.l {release}+4\n cmp.l {work}+4');branch('bne')
        put(f' lda.l {release}+6\n cmp.l {work}+6');branch('bne')
        put(' jsl PlayerRelease_FinishFrame');branch('bcs');put(' jmp PlayerEarly_ReleaseResult')
        label('FinishSound');put(f' php\n rep #$39\n phx\n phy\n lda.l {work}\n cmp #$B688');branch('bne')
        put(f' lda.l {work}+2\n cmp #7');branch('bne')
        if attack is not None:
            put(f' lda.l {work}+16\n cmp #7');branch('beq','AttackSoundFinish')
        put(f' lda.l {work}+16\n cmp #6');branch('bne')
        put(f' lda.l {release}+4\n cmp.l {work}+4');branch('bne')
        put(f' lda.l {release}+6\n cmp.l {work}+6');branch('bne')
        put(' jsl PlayerRelease_FinishSound');branch('bcs');put(' jmp PlayerEarly_ReleaseResult')
        label('SoundPending');put(f' lda #7\n sta.l {work}+2\n lda #$8001\n ply\n plx\n plp\n clc\n rtl')
    if attack is not None:
        def attack_identity():
            put(f' lda.l {attack}+4\n cmp.l {work}+4');branch('bne')
            put(f' lda.l {attack}+6\n cmp.l {work}+6');branch('bne')
        label('AttackFinish');attack_identity();put(' jsl PlayerAttack_FinishFrame');branch('bcs');put(' jmp PlayerEarly_AttackResult')
        label('AttackSoundFinish');attack_identity();put(' jsl PlayerAttack_FinishSound');branch('bcs');put(' jmp PlayerEarly_AttackResult')
        label('ResumeTarget');put(f' php\n rep #$39\n phx\n phy\n lda.l {work}\n cmp #$B688');branch('bne')
        put(f' lda.l {work}+2\n cmp #8');branch('bne');put(f' lda.l {work}+16\n cmp #7');branch('bne');attack_identity()
        put(' jsl PlayerAttack_ResumeTarget');branch('bcs');put(' jmp PlayerEarly_AttackResult')
        label('TargetPending');put(f' lda #8\n sta.l {work}+2\n lda #$8002\n ply\n plx\n plp\n clc\n rtl')
    label('ComboFinish');put(f' jsl {symbols["SourceAnimationInit4086_Ack"]}');branch('bcs')
    put(' jsl SourceCombo_Finish');branch('bcs');put(' jmp PlayerEarly_ComboResult')
    for name,status in (('Continue',2),('Exit',4)):
        label(name)
        if name=='Continue' and fall is not None:
            put(f' lda.l {symbols["SourceDamageEffectsState4086_Ready"]}\n cmp #$B62F');branch('bne')
            put(f' lda.l {work}+22\n tax\n lda.l $7EF114,x\n cmp #$B62F');branch('bne')
            put(f' lda.l $7EF116,x\n sta.l {work}+28\n lda.l {work}+20\n tax\n lda.l $416800,x\n cmp.l {work}+28');branch('bne')
            put(f' lda.l {work}+22\n tax\n lda.l $7EF102,x');branch('bne','NoFall')
            put(' lda.l $7EF100,x\n cmp #2');branch('bne','NoFall')
            put(f' lda.l {work}+4\n sta.l {fall}+4\n jsl PlayerFall_Execute');branch('bcs');put(' jmp PlayerEarly_Exit')
            label('NoFall')
        if name=='Continue' and (jump is not None or lie is not None):
            # A live grab needs its own owner; common_throw_wait is not admitted
            # in this closed controller lane. Never fall through a grab state.
            put(f' lda.l {work}+26\n tax\n lda.l $40C050,x\n ora.l $40C052,x');branch('beq','NoGrab')
            put(' lda.l $40C058,x\n ora.l $40C05A,x');branch('beq')
            label('NoGrab')
        if name=='Continue' and jump is not None:
            put(f' lda.l {work}+24\n tax\n lda.l $43EB08,x\n ora.l $43EB0A,x');branch('beq','NoJump')
            put(f' lda.l {work}+4\n sta.l {jump}+4\n lda #4\n sta.l {work}+16\n jsl PlayerJump_Begin');branch('bcs')
            put(' jmp PlayerEarly_HelperResult');label('NoJump')
        if name=='Continue' and lie is not None:
            put(f' lda.l {work}+24\n tax\n lda.l $43EB10,x\n ora.l $43EB12,x');branch('beq','NoLie')
            put(f' lda.l {work}+18\n tax\n lda.l $414008,x\n cmp #2');branch('bne')
            put(' lda.l $41400A,x');branch('bne')
            put(f' lda.l $41400C,x\n sta.l {work}+28\n lda.l $41400E,x\n sta.l {work}+30\n lda.l {work}+20\n tax\n lda.l $416830,x\n cmp.l {work}+28');branch('bne','NoLie')
            put(f' lda.l $416832,x\n cmp.l {work}+30');branch('bne','NoLie')
            put(' lda.l $41682C,x\n ora.l $41682E,x');branch('bne','NoLie')
            put(f' lda.l {work}+4\n sta.l {lie}+4\n jsl PlayerLieAbsent_Execute');branch('bcs')
            put(' jmp PlayerEarly_Exit');label('NoLie')
        if name=='Continue' and idle_profile is not None:
            put(f' lda.l {work}+24\n tax\n lda.l $43EB00,x\n ora.l $43EB02,x');branch('bne','NotBusy')
            # Current copied animation and source pointer must agree before the
            # compiler's immutable absence capability is consumed.
            put(f' lda.l {work}+18\n tax\n lda.l $414010,x\n cmp #1');branch('bne')
            put(' lda.l $414012,x\n ora.l $414016,x');branch('bne')
            put(f' lda.l $414014,x\n sta.l {symbols["SourceAnimationInit4086_Number"]}\n lda.l {work}+4\n sta.l {symbols["SourceAnimationInit4086_Slot"]}\n jsl {symbols["SourceAnimationInit4086_Resolve"]}');branch('bcs')
            put(f' lda.l {symbols["SourceAnimationInit4086_Handle"]}');branch('beq')
            put(f' sta.l {work}+28\n lda.l {symbols["SourceAnimationInit4086_Count"]}');branch('beq')
            put(f' lda.l {work}+20\n tax\n lda.l $416804,x\n cmp.l {work}+28');branch('bne')
            put(' lda.l $416800,x\n cmp #'+str(len(idle_profile['models'])));branch('bcs')
            put(' jmp PlayerEarly_Exit');label('NotBusy')
        if name=='Continue' and directional is not None:
            put(f' lda.l {work}+4\n sta.l {directional}+4\n lda.l {work}+6\n sta.l {directional}+6\n jsl PlayerDirectional_Execute');branch('bcs')
        if name=='Continue' and buttons is not None:
            put(f' lda.l {work}+4\n sta.l {buttons}+4\n lda.l {work}+6\n sta.l {buttons}+6\n lda #5\n sta.l {work}+16\n jsl PlayerButton_Begin');branch('bcs')
            label('ButtonResult');put(f' lda.l {buttons}+2\n cmp #4');branch('beq','Exit');put(' cmp #3');branch('beq','Pending');put(' cmp #2');branch('bne')
        if name=='Continue' and release is not None:
            put(f' lda.l {work}+4\n sta.l {release}+4\n lda.l {work}+6\n sta.l {release}+6\n lda.l {directional}+8\n sta.l {release}+8\n lda #6\n sta.l {work}+16\n jsl PlayerRelease_Begin');branch('bcs')
            label('ReleaseResult');put(f' lda.l {release}+2\n cmp #4');branch('beq','Exit');put(' cmp #3');branch('beq','SoundPending');put(' cmp #6');branch('beq','Pending');put(' cmp #2');branch('bne')
        if name=='Continue' and attack is not None:
            put(f' lda.l {work}+4\n sta.l {attack}+4\n lda.l {work}+6\n sta.l {attack}+6\n lda.l {directional}+8\n sta.l {attack}+8\n lda #7\n sta.l {work}+16\n jsl PlayerAttack_Begin');branch('bcs')
            label('AttackResult');put(f' lda.l {attack}+2\n cmp #4');branch('beq','Exit');put(' cmp #7');branch('beq','SoundPending');put(' cmp #3');branch('beq','Pending');put(' cmp #6');branch('beq','TargetPending');put(' cmp #2');branch('bne')
        put(f' lda #{status}\n sta.l {work}+2\n lda #0\n ply\n plx\n plp\n clc\n rtl')
    label('Bad');put(f' lda #5\n sta.l {work}+2\n ply\n plx\n plp\n sec\n rtl')
    return '\n'.join(lines)+'\n'
