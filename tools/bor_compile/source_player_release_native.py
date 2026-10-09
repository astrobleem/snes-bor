"""Canonical attack-release continuation for immutable integral charge times.

SoundPending must be serviced by the source sound owner. Ack=1 means accepted,
2 means a source priority rejection; physical backend busy is neither. Frame
pending requires the real frame owner before FinishFrame. No service is skipped.
"""
from source_player_run_4086 import KEYS
from source_u32_float_threshold_native import emit as threshold


def emit(work, history, input_owner, input_magic, profile, body, charge_role, symbols):
    spans=((work,128),(history,1024),(input_owner,2))
    for i,(a,n) in enumerate(spans):
        if not 0<=a<=0x1000000-n:raise ValueError('PLAYER_RELEASE_EXTENT')
        if any(a<b+m and b<a+n for b,m in spans[i+1:]):raise ValueError('PLAYER_RELEASE_OVERLAP')
    if history&255 or not 1<=input_magic<=65535 or not 0<=charge_role<=65535:raise ValueError('PLAYER_RELEASE_INPUT')
    if profile.get('capability')!='INTEGRAL_CHARGETIME_WIN32_X87_ABSENT_CHARGEATTACK':raise ValueError('PLAYER_RELEASE_CAPABILITY')
    if profile.get('evaluation_policy')!='WIN32_X87_EXTENDED':raise ValueError('PLAYER_RELEASE_EVALUATION')
    models=profile['models'];count=len(models)
    if not 1<=count<=16 or len(body['models'])!=count:raise ValueError('PLAYER_RELEASE_MODELS')
    for i,(m,b) in enumerate(zip(models,body['models'])):
        if m['id']!=i or b['index']!=i or m['source_sha256']!=b['source_sha256']:raise ValueError('PLAYER_RELEASE_PROFILE_IDENTITY')
        d=m['final_attack_duration']
        if d is not None and(type(d)is not int or not 0<=d<=65535):raise ValueError('PLAYER_RELEASE_DURATION')
        f=b['fields']
        if m['chainlength']!=f['chainlength'] or not 0<=f['chainlength']<=12 or len(f['atchain'])!=12 or any(not 0<=n<=7 for n in f['atchain']):raise ValueError('PLAYER_RELEASE_CHAIN')
        if m['final_attack']is not None and not 0<=m['final_attack']<=65535:raise ValueError('PLAYER_RELEASE_ROLE')
    lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('PlayerRelease_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;skip='PlayerRelease_Skip'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+skip+'\n jmp PlayerRelease_'+n+'\n'+skip+':\n.a16\n.i16')
    def prologue(n):label(n);put(' php\n rep #$39\n phx\n phy')
    def offset(dest,stride):
        put(' lda #0')
        for bit in range(stride.bit_length()-1,-1,-1):
            put(' asl a')
            if stride&(1<<bit):put(f' clc\n adc.l {work}+4')
        put(f' sta.l {work}+{dest}')
    def guard(address,magic):put(f' lda.l {address}\n cmp #{magic}');branch('bne')
    def resolve_charge(suffix):
        put(f' lda.l {work}+4\n sta.l {symbols["SourceAnimationInit4086_Slot"]}\n lda #{charge_role}\n sta.l {symbols["SourceAnimationInit4086_Number"]}')
        label('QueryCharge'+suffix);put(f' jsl {symbols["SourceAnimationInit4086_Resolve"]}');branch('bcs')
        put(f' lda.l {symbols["SourceAnimationInit4086_Handle"]}');branch('beq','ChargeAbsent'+suffix)
        put(f' lda.l {symbols["SourceAnimationInit4086_Count"]}');branch('bne')
        label('ChargeAbsent'+suffix)
    prologue('Begin');guard(work,0xb68f);guard(input_owner,input_magic)
    put(f' lda.l {work}+2');branch('beq','Ready');put(' cmp #2');branch('beq','Ready');put(' cmp #4');branch('bne')
    label('Ready');put(f' lda #1\n sta.l {work}+2\n lda.l {work}+6\n cmp #4');branch('bcs')
    put(f' xba\n tax\n lda.l {history}+228,x\n and #{KEYS["attack"]}');branch('beq','Continue')
    put(' jsl PlayerRelease_Bind');branch('bcs')
    put(f' lda.l {work}+30\n tax\n lda.l $42E008,x\n ora.l $42E00A,x');branch('beq','ClearStall')
    put(f' lda.l {work}+8');branch('beq','ClearStall')
    resolve_charge('First');resolve_charge('Second')
    put(' jsl PlayerRelease_ReadFinal');branch('bcs')
    put(f' lda.l {work}+40');branch('beq','ClearStall')
    put(f' lda.l {work}+46');branch('beq')
    put(f' lda.l {work}+30\n tax\n lda.l $42E008,x\n sta.l {work}+68\n lda.l $42E00A,x\n sta.l {work}+70\n lda.l {symbols["SourceClock4086_TimeLo"]}\n sta.l {work}+72\n lda.l {symbols["SourceClock4086_TimeHi"]}\n sta.l {work}+74\n lda.l {work}+38\n sta.l {work}+76\n lda #0\n sta.l {work}+78\n lda #$B68E\n sta.l {work}+64\n jsl U32FloatThreshold_Execute');branch('bcs')
    put(f' lda.l {work}+80');branch('beq','ClearStall')
    put(f' lda.l {work}+24\n tax\n lda #17\n sta.l $43900C,x\n lda #0\n sta.l $43900E,x\n lda.l {work}+26\n tax\n lda #1\n sta.l $40C058,x\n lda #0\n sta.l $40C05A,x\n lda.l {work}+28\n tax\n lda #0\n sta.l $43EB00,x\n sta.l $43EB02,x\n lda.l {work}+32\n tax\n lda #0\n sta.l $437E08,x\n sta.l $437E0A,x\n lda.l {work}+22\n tax\n lda #0\n sta.l $416824,x\n sta.l $416826,x\n sta.l $416828,x\n sta.l $41682A,x\n lda.l {work}+30\n tax\n lda #0\n sta.l $42E008,x\n sta.l $42E00A,x\n sta.l {work}+42\n lda.l {work}+14\n and #$8000');branch('bne','Animation')
    put(f' lda #3\n sta.l {work}+2\n lda #$8001');put(' jmp PlayerRelease_Exit')
    prologue('FinishSound');guard(work,0xb68f)
    put(f' lda.l {work}+2\n cmp #3');branch('bne')
    put(f' lda.l {work}+42\n cmp #1');branch('beq','SoundDone');put(' cmp #2');branch('bne')
    label('SoundDone');put(' jsl PlayerRelease_Bind');branch('bcs')
    label('Animation');resolve_charge('AfterSound');put(' jsl PlayerRelease_ReadFinal');branch('bcs')
    put(f' lda.l {work}+40');branch('beq')
    put(f' lda.l {work}+36\n sta.l {symbols["SourceAnimationInit4086_Number"]}\n lda.l {work}+4\n sta.l {symbols["SourceAnimationInit4086_Slot"]}\n lda #0\n sta.l {symbols["SourceAnimationInit4086_Reset"]}');label('BeforeAnimation');put(f' jsl {symbols["SourceAnimationInit4086_Begin"]}');branch('bcs')
    put(f' lda.l {symbols["SourceAnimationInit4086_State"]}\n cmp #2');branch('beq','Return');put(' cmp #1');branch('bne')
    put(f' lda #6\n sta.l {work}+2\n lda #$8002');put(' jmp PlayerRelease_Exit')
    prologue('FinishFrame');guard(work,0xb68f)
    put(f' lda.l {work}+2\n cmp #6');branch('bne')
    put(f' lda.l {symbols["SourceAnimationInit4086_Slot"]}\n cmp.l {work}+4');branch('bne')
    put(f' lda.l {symbols["SourceAnimationInit4086_Number"]}\n cmp.l {work}+36');branch('bne')
    put(f' jsl {symbols["SourceAnimationInit4086_Ack"]}');branch('bcs')
    label('Return');put(f' lda #4\n sta.l {work}+2\n lda #0');put(' jmp PlayerRelease_Exit')
    label('ClearStall');put(f' lda.l {work}+30\n tax\n lda #0\n sta.l $42E008,x\n sta.l $42E00A,x')
    label('Continue');put(f' lda #2\n sta.l {work}+2\n lda #0')
    label('Exit');put(' ply\n plx\n plp\n clc\n rtl')
    label('Bad');put(f' lda #5\n sta.l {work}+2\n ply\n plx\n plp\n sec\n rtl')
    label('Bind')
    for a,m in ((symbols['VmSourceWorld_Ready'],0xb4a3),(symbols['VmSourceWorld_PoolBase'],0x4000),(symbols['SourceModelEntityCopy4086_Ready'],0xb4eb),(symbols['SourceClock4086_Ready'],0xb4c5),(symbols['SourceFreeze4086_Ready'],0xb5df)):
        put(f' lda.l {a}\n cmp #{m}');branch('bne','BindBad')
    put(f' lda.l {symbols["VmSourceWorld_Count"]}');branch('beq','BindBad');put(' cmp #129');branch('bcs','BindBad')
    put(f' lda.l {work}+4\n cmp.l {symbols["VmSourceWorld_Count"]}');branch('bcs','BindBad')
    put(f' lda.l {symbols["SourceModelEntityCopy4086_Models"]}\n cmp #{count}');branch('bne','BindBad')
    for dst,stride in ((20,80),(22,64),(24,80),(26,96),(28,32),(30,40),(32,20)):offset(dst,stride)
    put(f' lda.l {work}+20\n tax\n clc\n adc #$4000\n cmp.l $414000,x');branch('bne','BindBad')
    put(' lda.l $414002,x\n cmp #$41');branch('bne','BindBad')
    put(f' lda.l {work}+24\n tax\n lda.l $43904A,x\n cmp #$B4FB');branch('bne','BindBad')
    put(f' lda.l {work}+32\n tax\n lda.l $437E10,x\n cmp #$B5FB');branch('bne','BindBad')
    put(' lda.l $437E12,x');branch('bne','BindBad')
    put(f' lda.l {work}+22\n tax\n lda.l $416800,x\n cmp #{count}');branch('bcs','BindBad');put(f' sta.l {work}+34\n clc\n rtl')
    label('BindBad');put(' sec\n rtl')
    label('ReadFinal');put(f' lda.l {work}+34\n tax\n lda.l {work}+4\n jsl {symbols["SourceAttackBody4086_ReadEntity"]}');branch('bcs','ReadBad')
    for i in range(count):put(f' lda.l {work}+34\n cmp #{i}');branch('beq','Model'+str(i))
    put(' jmp PlayerRelease_ReadBad')
    for i,(m,b) in enumerate(zip(models,body['models'])):
        label('Model'+str(i));f=b['fields'];packed=sum(n<<(3*j)for j,n in enumerate(f['atchain']))|(f['chainlength']<<36)
        for off,expected in ((0,packed&65535),(2,(packed>>16)&65535),(4,(packed>>32)&255)):
            put(f' lda.l {symbols["SourceAttackBody4086_Chain"]}+{off}')
            if off==4:put(' and #255')
            put(f' cmp #{expected}');branch('bne','ReadBad')
        put(f' lda #{m["final_attack"] or 0}\n sta.l {work}+36\n lda #{m["final_attack_duration"] or 0}\n sta.l {work}+38\n lda #{m["chainlength"]}\n sta.l {work}+40\n lda #{int(m["final_attack_duration"] is not None)}\n sta.l {work}+46\n clc\n rtl')
    label('ReadBad');put(' sec\n rtl')
    return '\n'.join(lines)+'\n'+threshold(work+64,profile['evaluation_policy'])
