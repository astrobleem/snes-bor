"""Checked player_die recovery snapshot from current global self.

A is the original player index captured before the pdie script. The source
reads current global self afterward, so it may identify a different slot.
This leaf only binds the two recovery fields, not the whole death continuation.
"""
from source_player_global_layout import layout


def death_layout(tail):
    p=layout(tail);work=p['end']
    if work+48>tail['end']:raise ValueError('PLAYER_DIE_CONTINUATION_CAPACITY')
    return dict(base=work,bytes=48,end=work+48,remaining_bytes=tail['end']-work-48)


def emit_recovery_snapshot(tail,sy):
    plan=layout(tail);base=plan['player_base'];lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('PlayerDieSnapshot_'+n+':\n.a16\n.i16')
    def guard(op,n='Bad'):
        nonlocal serial
        serial+=1;g='PlayerDieSnapshot_Guard'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+g+'\n jmp PlayerDieSnapshot_'+n+'\n'+g+':\n.a16\n.i16')
    def require(at,value):put(f' lda.l {at}\n cmp #{value}');guard('bne')
    label('Run');put(' php\n rep #$39\n pha\n phx\n phy\n phd\n tsc\n sec\n sbc #16\n tcs\n inc a\n tcd\n lda 23,s\n cmp #4');guard('bcs');put(' sta $00')
    put(f' jsl {sy["SourceForeignWork_Check"]}');guard('bcs')
    put(' jsl PlayerGlobal_Check');guard('bcs')
    for at,v in ((sy['VmSourceWorld_Ready'],0xb4a3),(sy['VmSourceWorld_PoolBase'],0x4000),
                 (sy['SourceWorldTick4086_Ready'],0xb4d5),(sy['SourceWorldTick4086_State'],1),
                 (sy['SourceWorldTick4086_Phase'],8),(sy['SourceWorldTick4086_Pending'],1),
                 (sy['SourceWorldTick4086_Fault'],0),(sy['SourceSelf4086_Ready'],0xb4f6),
                 (sy['SourceSelf4086_Active'],0),(sy['SourceSelf4086_Fault'],0),
                 (sy['SourceSelf4086_GlobalHigh'],0x41),(sy['SourceModelEntityCopy4086_Ready'],0xb4eb)):
        require(at,v)
    for off in (0,2):put(f' lda.l {sy["SourceWorldTick4086_TimeLo"]}+{off}\n cmp.l {sy["VmSourceWorld_Time"]}+{off}');guard('bne')
    put(f' lda.l {sy["VmSourceWorld_Count"]}');guard('beq');put(' cmp #129');guard('bcs')
    put(f' cmp.l {sy["SourceModelEntityCopy4086_Entities"]}');guard('bne')
    put(f' lda.l {sy["SourceSelf4086_GlobalLow"]}\n sec\n sbc #$4000');guard('bcc');put(' sta $02\n ldx #0')
    label('FindSlot');put(' cmp #80');guard('bcc','SlotFound');put(' sec\n sbc #80\n inx');put(f' sta $06\n txa\n cmp.l {sy["VmSourceWorld_Count"]}');guard('bcs');put(' lda $06\n jmp PlayerDieSnapshot_FindSlot')
    label('SlotFound');put(' cmp #0');guard('bne');put(f' txa\n cmp.l {sy["VmSourceWorld_Count"]}');guard('bcs')
    put(' txa\n asl a\n asl a\n asl a\n asl a\n asl a\n sta $04\n asl a\n clc\n adc $04\n sta $04\n ldx $02')
    put(f' lda.l $414000,x\n cmp.l {sy["SourceSelf4086_GlobalLow"]}');guard('bne');require('$414002,x',0x41)
    put(' ldx $04')
    for offset,temp in ((60,8),(62,10),(64,12),(66,14)):put(f' lda.l $40C000+{offset},x\n sta ${temp:02X}')
    put(' lda $00\n asl a\n asl a\n sta $06\n asl a\n asl a\n clc\n adc $06\n tax')
    for offset,temp in ((8,8),(10,10),(12,12),(14,14)):put(f' lda ${temp:02X}\n sta.l {base+offset},x')
    put(' jmp PlayerDieSnapshot_Good')
    for name,carry in (('Good','clc'),('Bad','sec')):
        label(name);put(' tsc\n clc\n adc #16\n tcs\n pld\n ply\n plx\n pla\n plp\n '+carry+'\n rtl')
    return '\n'.join(lines)+'\n'


def emit_begin(tail,sy,requirements):
    """Absent-global-hook death prefix, real kill, and complete no-lives tail.

    Positive lives return the real required SPAWN service ticket (3). No spawn
    or respawn acknowledgement is fabricated. Work+4 supplies the actor slot;
    work+8/10 supplies its foreign generation, as in other source continuations.
    """
    if any(h['source_sha256']is not None for h in requirements['hooks']):raise ValueError('PLAYER_DIE_GLOBAL_SCRIPT_CHILD_REQUIRED')
    if requirements['rush_reset_policy']!=0:raise ValueError('PLAYER_DIE_RUSH_CAPTURE_BODY_REQUIRED')
    models=requirements['models'];count=len(models)
    if not 1<=count<=128:raise ValueError('PLAYER_DIE_MODEL_CAPACITY')
    p=layout(tail);w=death_layout(tail)['base'];g=p['global_base'];players=p['player_base'];lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('PlayerDie_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;k='PlayerDie_Guard'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc',bmi='bpl',bpl='bmi')[op]+' '+k+'\n jmp PlayerDie_'+n+'\n'+k+':\n.a16\n.i16')
    def require(at,v):put(f' lda.l {at}\n cmp #{v}');branch('bne')
    label('Begin');put(' php\n rep #$39\n phx\n phy\n phd\n tsc\n sec\n sbc #16\n tcs\n inc a\n tcd')
    put(f' jsl {sy["SourceForeignWork_Check"]}');branch('bcs');put(' jsl PlayerGlobal_Check');branch('bcs')
    require(w,0xb6c9)
    for op,off in (('txa',8),('tya',10)):put(f' {op}\n cmp.l {w}+{off}');branch('bne');put(f' cmp.l {p["controls"]}+{off}');branch('bne')
    for at,v in ((sy['VmSourceWorld_Ready'],0xb4a3),(sy['VmSourceWorld_PoolBase'],0x4000),(sy['VmSourceWorld_SideBase'],0x6800),
                 (sy['SourceWorldTick4086_Ready'],0xb4d5),(sy['SourceWorldTick4086_State'],1),(sy['SourceWorldTick4086_Phase'],8),
                 (sy['SourceWorldTick4086_Pending'],1),(sy['SourceWorldTick4086_Fault'],0),(sy['SourceSelf4086_Ready'],0xb4f6),
                 (sy['SourceSelf4086_Active'],0),(sy['SourceSelf4086_Fault'],0),(sy['SourceLifecycle4086_Ready'],0xb4fb),
                 (sy['SourceModelEntityCopy4086_Ready'],0xb4eb),(sy['SourceModelEntityCopy4086_Models'],count),
                 (sy['SourceWeapon4086_Ready'],0xb4f1),(g+8,0),(g+10,0)):require(at,v)
    for off in (0,2):
        put(f' lda.l {w}+{16+off}\n cmp.l {sy["VmSourceWorld_Time"]}+{off}');branch('bne')
        put(f' cmp.l {sy["SourceWorldTick4086_TimeLo"]}+{off}');branch('bne')
    put(f' lda.l {w}+4\n cmp.l {sy["VmSourceWorld_Count"]}');branch('bcs');put(' sta $00\n asl a\n asl a\n asl a\n asl a\n sta $02\n asl a\n asl a\n sta $04\n clc\n adc $02\n sta $02\n tax\n clc\n adc #$4000\n cmp.l $414000,x');branch('bne');require('$414002,x',0x41)
    put(f' lda.l {w}+2\n cmp #2');branch('beq','Complete');put(' cmp #1');branch('beq','Spawn');put(' cmp #0');branch('bne')
    put(f' lda.l {sy["VmSourceWorld_Count"]}');branch('beq');put(' cmp #129');branch('bcs')
    put(f' lda.l {w}+4\n cmp.l {sy["SourceWorldTick4086_Slot"]}');branch('bne')
    put(' ldx $02\n lda.l $414000,x');put(f' cmp.l {sy["SourceSelf4086_GlobalLow"]}');branch('bne');require(sy['SourceSelf4086_GlobalHigh'],0x41)
    for offset,value in ((40,1),(42,0),(46,0)):require(f'$414000+{offset},x',value)
    put(' lda $04\n lsr a\n clc\n adc $04\n tax\n lda.l $40C048,x\n and #1');branch('beq');require('$40C04A,x',0);put(' ldx $02')
    put(' lda.l $41402C,x\n cmp #4');branch('bcs');put(f' sta.l {w}+6\n asl a\n asl a\n sta $06\n tax\n lda.l $43FD84,x\n ldx $02\n cmp.l $414000,x');branch('bne')
    put(' ldx $06');require('$43FD86,x',0x41);put(' ldx $02');require('$43904A,x',0xb4fb)
    put(' lda.l $439048,x\n ldx $04\n cmp.l $416800,x');branch('bne');put(f' cmp #{count}');branch('bcs');put(' asl a\n tax')
    for name,off in (('NoDieLow',24),('NoDieHigh',26),('WeapLossLow',28),('WeapLossHigh',30)):put(f' lda.l PlayerDie_{name},x\n sta.l {w}+{off}')
    put(f' lda.l {w}+26');branch('bne','PreflightKill');put(f' lda.l {w}+24\n cmp #3');branch('beq','Prefix')
    label('PreflightKill');put(f' lda.l {w}+4\n sta.l {sy["SourceRetirement4086_Slot"]}\n jsl {sy["SourceRetirement4086_PreflightNoEvents"]}');branch('bcs')
    label('Prefix');put(' ldx $06');put(f' lda.l {g}+4\n ora.l {g}+6');branch('bne','LivesDone')
    put(' sec\n lda.l $7FBFB0,x\n sbc #1\n sta.l $7FBFB0,x\n lda.l $7FBFB2,x\n sbc #0\n sta.l $7FBFB2,x')
    label('LivesDone');put(' ldx $02');put(f' lda.l {g}\n cmp.l $414000,x');branch('bne','FirstDone');put(f' lda.l {g}+2\n cmp #$41');branch('bne','FirstDone');put(f' lda #0\n sta.l {g}\n sta.l {g}+2')
    label('FirstDone');put(' ldx $06\n lda #0\n sta.l $43FD84,x\n sta.l $43FD86,x')
    put(f' lda.l {w}+8\n tax\n lda.l {w}+10\n tay\n lda.l {w}+6\n jsl PlayerDieSnapshot_Run');branch('bcs')
    put(f' lda.l {w}+26');branch('bne','Kill');put(f' lda.l {w}+24\n cmp #3');branch('bne','Kill')
    put(' ldx $02\n lda #0\n sta.l $439000,x\n sta.l $439002,x\n sta.l $43900C,x\n sta.l $43900E,x')
    put(f' lda.l {w}+4\n asl a\n asl a\n asl a\n asl a\n asl a\n sta $04\n asl a\n clc\n adc $04\n tax\n lda #0\n sta.l $40C048,x\n sta.l $40C04A,x\n jmp PlayerDie_AfterKill')
    label('Kill');put(f' jsl {sy["SourceRetirement4086_ApplyNoEvents"]}');branch('bcs');require(sy['SourceRetirement4086_Status'],2)
    label('AfterKill');put(' ldx $06\n lda.l $7FBFB2,x');branch('bmi','NoLives');branch('bne','Spawn');put(' lda.l $7FBFB0,x');branch('bne','Spawn')
    label('NoLives');require(sy['SourceWait4086_Ready']if 'SourceWait4086_Ready'in sy else 0x43bbaa,0xb5d9)
    for i in range(4):put(f' lda.l $43FD84+{4*i}\n ora.l $43FD86+{4*i}');branch('bne','Weapon')
    put(' lda #4000\n sta.l $43BBB6\n lda #0\n sta.l $43BBB8')
    for i in (0,1):put(f' lda.l {players+20*i+4}\n ora.l {players+20*i+6}');branch('bne','Weapon')
    put(f' lda.l {g}+12\n ora.l {g}+14');branch('bne','SeparateCredits')
    put(f' lda.l {g}+18');branch('bmi','NoCredits');branch('bne','Weapon');put(f' lda.l {g}+16');branch('bne','Weapon');put(' jmp PlayerDie_NoCredits')
    label('SeparateCredits')
    for i in range(4):
        put(f' lda.l {players+20*i+2}');branch('bmi','CreditNext'+str(i));branch('bne','Weapon');put(f' lda.l {players+20*i}');branch('bne','Weapon');label('CreditNext'+str(i))
    label('NoCredits');put(' lda #200\n sta.l $43BBB6\n lda #0\n sta.l $43BBB8')
    label('Weapon');put(f' lda.l {w}+30');branch('bne','RushClear');put(f' lda.l {w}+28\n cmp #3');branch('bne','RushClear')
    put(' ldx $06');put(f' lda.l {sy["SourceWeapon4086_LevelWeaponLo"]}\n sta.l $43EA00,x\n lda.l {sy["SourceWeapon4086_LevelWeaponHi"]}\n sta.l $43EA02,x')
    label('RushClear');put(f' lda.l {w}+6\n asl a\n asl a\n sta $06\n asl a\n asl a\n clc\n adc $06\n tax\n lda #0\n sta.l {players+16},x\n sta.l {players+18},x\n lda #2\n sta.l {w}+2')
    label('Complete');put(f' lda #0\n sta.l {w}+20\n jmp PlayerDie_Return')
    label('Spawn');put(f' lda #1\n sta.l {w}+2\n lda #3\n sta.l {w}+20\n jmp PlayerDie_Return')
    label('Return');put(' tay\n tsc\n clc\n adc #16\n tcs\n tya\n pld\n ply\n plx\n plp\n clc\n rtl')
    label('Bad');put(' tsc\n clc\n adc #16\n tcs\n pld\n ply\n plx\n plp\n sec\n rtl')
    for name,field,high in (('NoDieLow','nodieblink',False),('NoDieHigh','nodieblink',True),('WeapLossLow','weaploss_type',False),('WeapLossHigh','weaploss_type',True)):
        put('PlayerDie_'+name+':\n .dw '+','.join(str((m[field]>>(16 if high else 0))&65535)for m in models))
    return '\n'.join(lines)+'\n'
