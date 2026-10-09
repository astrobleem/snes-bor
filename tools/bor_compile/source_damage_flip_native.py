"""Native checkdamageflip over source entity rows, with a closed model policy.

Caller leases 24 foreign bytes: B6AA/status/defender/attacker/generation DWORD/
no_pain DWORD/force_direction DWORD. FFFF attacker is NULL. Model nopain and
noflip must be immutable zero; actual defense pain must be zero. The caller
owns attack descriptor identity and must run drop/effects before this service.
"""


def emit(requirements,work,sy):
    if requirements['capability']!='SOURCE_ZERO_PAIN_ZERO_NOFLIP':
        raise ValueError('DAMAGE_FLIP_CAPABILITY')
    models=len(requirements['models'])
    if not 1<=models<=16 or any(m['id']!=i or any(m[n] for n in ('nopain','noflip','defense_pain')) for i,m in enumerate(requirements['models'])):
        raise ValueError('DAMAGE_FLIP_MODEL_POLICY')
    lines=[];serial=0;size=48
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('DamageFlip_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;l='DamageFlip_Guard'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+f' {l}\n jmp DamageFlip_{n}\n{l}:\n.a16\n.i16')
    def require(at,v):put(f' lda.l {at}\n cmp #{v}');branch('bne')
    def offset(src,stride,dst):
        put(f' lda ${src:02X}\n asl a\n asl a\n asl a')
        if stride==80:put(' asl a\n sta $28\n asl a\n asl a\n clc\n adc $28')
        elif stride==40:put(' sta $28\n asl a\n asl a\n clc\n adc $28')
        elif stride==20:raise ValueError('FLIP_OFFSET')
        elif stride in (32,64):put('\n'.join(' asl a'for _ in range(stride.bit_length()-4)))
        else:raise ValueError('FLIP_OFFSET')
        put(f' sta ${dst:02X}')
    label('Run');put(f' php\n rep #$39\n phx\n phy\n phd\n tsc\n sec\n sbc #{size}\n tcs\n inc a\n tcd')
    put(f' jsl {sy["SourceForeignWork_Check"]}');branch('bcs');require(work,0xb6aa)
    for op,off in (('txa',8),('tya',10)):put(f' {op}\n cmp.l {work}+{off}');branch('bne')
    for at,v in ((sy['VmSourceWorld_Ready'],0xb4a3),(sy['VmSourceWorld_PoolBase'],0x4000),(sy['VmSourceWorld_SideBase'],0x6800),(sy['SourceWorldTick4086_Ready'],0xb4d5),(sy['SourceWorldTick4086_State'],1),(sy['SourceWorldTick4086_Phase'],8),(sy['SourceWorldTick4086_Pending'],1),(sy['SourceWorldTick4086_Fault'],0),(sy['SourceSelf4086_Ready'],0xb4f6),(sy['SourceSelf4086_Fault'],0),(sy['SourceSelf4086_GlobalHigh'],0x41)):
        require(at,v)
    for off in (0,2):put(f' lda.l {sy["SourceWorldTick4086_TimeLo"]}+{off}\n cmp.l {sy["VmSourceWorld_Time"]}+{off}');branch('bne')
    put(f' lda.l {sy["VmSourceWorld_Count"]}');branch('beq');put(' cmp #129');branch('bcs')
    put(f' lda.l {work}+4\n cmp.l {sy["VmSourceWorld_Count"]}');branch('bcs');put(' sta $00')
    offset(0,80,4);put(f' lda $04\n clc\n adc #$4000\n cmp.l {sy["SourceSelf4086_GlobalLow"]}');branch('bne')
    put(f' lda.l {work}+6\n cmp #$FFFF');branch('beq','Good');put(' cmp $00');branch('beq','Good');put(f' cmp.l {sy["VmSourceWorld_Count"]}');branch('bcs');put(' sta $02')
    # Validate actual row tokens and typed integer directions/Q16 positions.
    for src in (0,2):
        offset(src,80,4);put(' tax\n clc\n adc #$4000\n cmp.l $414000,x');branch('bne');put(' lda.l $414002,x\n cmp #$41');branch('bne')
        for off,val in ((24,1),(26,0),(48,2),(50,0)):put(f' lda.l $414000+{off},x\n cmp #{val}');branch('bne')
        dst=8 if src==0 else 12
        for off in (0,2):put(f' lda.l $414034+{off},x\n sta ${dst+off:02X}')
    require(sy['SourceFreeze4086_Ready'],0xb5df);require(sy['SourceFactors4086_Ready'],0xb5f1);require(sy['SourceFactors4086_Models'],models)
    offset(0,64,4);put(f' tax\n lda.l $416800,x\n cmp #{models}');branch('bcs');put(' sta $10')
    put(' lda $00\n asl a\n asl a\n tax\n lda.l $43B902,x\n cmp #$B5F1');branch('bne');put(' lda.l $43B900,x\n cmp $10');branch('bne')
    offset(0,32,4);put(' tax\n lda.l $432814,x\n ora.l $432816,x');branch('bne')
    offset(0,40,4);put(' tax\n lda.l $42E000,x\n ora.l $42E002,x');branch('bne','Good')
    put(f' lda.l {work}+12\n ora.l {work}+14');branch('beq','Eligible')
    put(' lda $00\n asl a\n asl a\n sta $28\n asl a\n asl a\n clc\n adc $28\n tax\n lda.l $437E10,x\n cmp #$B5FB');branch('bne');put(' lda.l $437E00,x\n ora.l $437E02,x');branch('beq','Good')
    label('Eligible');put(f' lda.l {work}+16\n sta $12\n lda.l {work}+18\n sta $14')
    for value,name in ((0,'Toward'),(1,'Same'),(2,'Right'),(0xffffffff,'Opposite'),(0xfffffffe,'Left')):
        put(f' lda $14\n cmp #{value>>16}');branch('bne','DispatchNext'+name);put(f' lda $12\n cmp #{value&65535}');branch('beq',name);label('DispatchNext'+name)
    put(' jmp DamageFlip_Good')
    label('Toward');put(' lda $0A\n eor #$8000\n sta $16\n lda $0E\n eor #$8000\n cmp $16');branch('bcc','Left');branch('bne','Right');put(' lda $08\n cmp $0C');branch('bcc','Right');branch('bne','Left');put(' jmp DamageFlip_Good')
    label('Same');offset(2,80,4);put(' tax\n lda.l $41401C,x\n sta $18\n lda.l $41401E,x\n sta $1A\n jmp DamageFlip_Commit')
    label('Opposite');offset(2,80,4);put(' tax\n lda.l $41401C,x\n ora.l $41401E,x');branch('beq','Right');put(' jmp DamageFlip_Left')
    label('Right');put(' lda #1\n sta $18\n lda #0\n sta $1A\n jmp DamageFlip_Commit')
    label('Left');put(' lda #0\n sta $18\n sta $1A')
    label('Commit');offset(0,80,4);put(' tax\n lda $18\n sta.l $41401C,x\n lda $1A\n sta.l $41401E,x')
    for name,status,carry in (('Good',2,'clc'),('Bad',3,'sec')):
        label(name);put(f' lda #{status}\n sta.l {work}+2\n tay\n tsc\n clc\n adc #{size}\n tcs\n tya\n pld\n ply\n plx\n plp\n {carry}\n rtl')
    return '\n'.join(lines)+'\n'
