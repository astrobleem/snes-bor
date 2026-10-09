"""Generation-bound active palette identities distinct from restore map state."""
from source_current_colourmap import layout
from source_hit_state_layout import layout as hits
from source_move_contact_layout import layout as movement


def emit(requirements,plan,sy,code_bank=39,phase=8,chr_capacity=None):
    if plan!=layout(plan['entities']) or requirements['schema']!='BYOR_CURRENT_COLOURMAP_REQUIREMENTS_V1':raise ValueError('CURRENT_COLOURMAP_NATIVE_PLAN')
    if not 1<=phase<=12:raise ValueError('CURRENT_COLOURMAP_PHASE')
    capacity=plan['chr_capacity']if chr_capacity is None else chr_capacity
    if not isinstance(capacity,int)or not 0<capacity<=plan['chr_capacity']:raise ValueError('CURRENT_COLOURMAP_CHR_CAPACITY')
    models=requirements['models'];count=len(models)
    if not 1<=count<=16 or any(m['id']!=i or m['maps_loaded']>65535 for i,m in enumerate(models)):raise ValueError('CURRENT_COLOURMAP_MODELS')
    w=plan['controls'];base=plan['base'];h=hits(plan['entities']);move=movement(plan['entities']);lines=[];serial=0;size=48
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('CurrentPalette_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;l='CurrentPalette_Guard'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+f' {l}\n jmp CurrentPalette_{n}\n{l}:\n.a16\n.i16')
    def require(at,v):put(f' lda.l {at}\n cmp #{v}');branch('bne')
    def offset(src,stride,dst):
        put(f' lda ${src:02X}\n asl a\n asl a')
        if stride==12:put(' sta $28\n asl a\n clc\n adc $28')
        elif stride in (16,64):put('\n'.join(' asl a'for _ in range(stride.bit_length()-3)))
        elif stride==96:put(' asl a\n asl a\n asl a\n sta $28\n asl a\n clc\n adc $28')
        elif stride==80:put(' asl a\n asl a\n sta $28\n asl a\n asl a\n clc\n adc $28')
        else:raise ValueError('CURRENT_COLOURMAP_OFFSET')
        put(f' sta ${dst:02X}')
    label('Run');put(f' php\n rep #$39\n phx\n phy\n phd\n tsc\n sec\n sbc #{size}\n tcs\n inc a\n tcd')
    put(f' jsl {sy["SourceForeignWork_Check"]}');branch('bcs');require(w,0xb6ab)
    for op,off in (('txa',8),('tya',10)):
        put(f' {op}\n cmp.l {w}+{off}');branch('bne');put(f' cmp.l {h["controls"]}+{off}');branch('bne')
    for at,v in ((w+16,base&65535),(w+18,0x42),(w+20,capacity),(w+22,plan['entities']),
                 (h['controls'],0xb6a0),(h['controls']+16,h['base']&65535),(h['controls']+18,0x42),(h['controls']+20,capacity),(h['controls']+22,plan['entities']),
                 (sy['VmSourceWorld_Ready'],0xb4a3),(sy['VmSourceWorld_PoolBase'],0x4000),(sy['VmSourceWorld_SideBase'],0x6800),(sy['VmSourceWorld_TemplateCount'],count),
                 (sy['SourceCtorState4086_Ready'],0xb5c2),(sy['SourceCtorState4086_Models'],count),(sy['SourceWorldTick4086_Ready'],0xb4d5),(sy['SourceWorldTick4086_State'],1),(sy['SourceWorldTick4086_Phase'],phase),(sy['SourceWorldTick4086_Pending'],1),(sy['SourceWorldTick4086_Fault'],0)):
        require(at,v)
    for off in (0,2):put(f' lda.l {sy["SourceWorldTick4086_TimeLo"]}+{off}\n cmp.l {sy["VmSourceWorld_Time"]}+{off}');branch('bne')
    put(f' lda.l {sy["VmSourceWorld_Count"]}');branch('beq');put(f' cmp #{plan["entities"]+1}');branch('bcs')
    put(f' lda.l {w}+4\n cmp.l {sy["VmSourceWorld_Count"]}');branch('bcs');put(' sta $00')
    offset(0,80,4);put(' tax\n clc\n adc #$4000\n cmp.l $414000,x');branch('bne');put(' lda.l $414002,x\n cmp #$41');branch('bne')
    offset(0,16,4);put(f' tax\n lda.l {h["base"]}+12,x\n cmp #$B6A1');branch('bne');put(f' lda.l {h["base"]}+14,x\n cmp $00');branch('bne')
    for off in (8,10):put(f' lda.l {h["base"]}+{off},x\n cmp.l {w}+{off}');branch('bne')
    offset(0,64,4);put(' tax\n lda.l $416800,x\n sta $06');put(f' cmp #{count}');branch('bcs')
    put(' lda.l $43383E,x\n cmp #$B5C2');branch('bne');put(' lda.l $433832,x\n sta $18\n cmp $06');branch('beq','BodyOwnerGood');put(f' lda.l {w}+24\n cmp #5');branch('bne');put(f' lda $18\n cmp.l {sy["SourceModelTransition4086_Old"]}');branch('bne');label('BodyOwnerGood')
    put(' lda.l $433830,x\n sta $08')
    offset(0,12,10);put(f' tax\n lda.l {w}+24\n cmp #1');branch('beq','Birth')
    # All later operations require an independently stamped active row.
    put(f' lda.l {base}+8,x\n cmp #$B6AC');branch('bne');put(f' lda.l {base}+10,x\n cmp $00');branch('bne')
    for off in (0,2):put(f' lda.l {base}+{4+off},x\n cmp.l {w}+{8+off}');branch('bne')
    put(f' lda.l {base},x\n sta $12\n cmp #{count}');branch('bcs')
    put(f' lda.l {w}+24\n cmp #5');branch('beq','ResetOwner')
    put(' lda $12\n cmp $06');branch('bne');put(' jmp CurrentPalette_OwnerGood')
    label('ResetOwner')
    for at,v in ((sy['SourceModelTransition4086_Ready'],0xb4f0),(sy['SourceModelTransition4086_State'],1),(sy['SourceModelTransition4086_Acknowledged'],0)):
        require(at,v)
    put(f' lda.l {sy["SourceModelTransition4086_Service"]}\n sta $16\n cmp #3');branch('beq','ResetServiceGood');put(' cmp #6');branch('bne')
    label('ResetServiceGood')
    put(f' lda.l {sy["SourceModelTransition4086_Slot"]}\n cmp $00');branch('bne')
    put(f' lda.l {sy["SourceModelTransition4086_New"]}\n cmp $06');branch('bne')
    put(f' lda.l {sy["SourceModelTransition4086_Old"]}\n cmp #{count}');branch('bcs');put(' sta $14\n cmp $06');branch('beq')
    put(' lda $12\n cmp $14');branch('beq','ResetIdentityGood');put(' cmp $06');branch('bne')
    label('ResetIdentityGood');offset(0,64,4);put(f' lda $04\n clc\n adc #$6800\n cmp.l {sy["SourceModelTransition4086_Side"]}');branch('bne')
    offset(0,96,4);put(f' lda $04\n clc\n adc #$C000\n cmp.l {sy["SourceModelTransition4086_Core"]}');branch('bne')
    put(' lda $16\n cmp #6');branch('bne','ResetTypeGood');put(' ldx $04')
    for off in (0,2):put(f' lda.l $40C048+{off},x\n cmp.l {sy["SourceModelTransition4086_OldTypeLo"]}+{off}');branch('bne')
    label('ResetTypeGood');offset(0,80,4);put(' tax\n lda.l $414004,x\n ora.l $414006,x');branch('beq')
    label('OwnerGood');put(' lda $12\n asl a\n tax');put(f' lda.l CurrentPalette_MapCounts+{code_bank<<16},x\n sta $10\n lda $0A\n tax\n lda.l {base}+2,x\n cmp $10');branch('bcc','PriorMapGood');branch('bne')
    label('PriorMapGood')
    put(f' lda.l {w}+24\n cmp #3');branch('beq','Read');put(' cmp #2');branch('beq','Select');put(' cmp #4');branch('beq','Restore');put(' cmp #5');branch('bne')
    label('Restore')
    put(' lda $08\n sta $0C\n lda #0\n sta $0E\n jmp CurrentPalette_Normalize')
    label('Birth');offset(0,80,4);put(' tax\n lda.l $414004,x\n ora.l $414006,x');branch('bne')
    put(' lda $08\n sta $0C\n lda #0\n sta $0E\n jmp CurrentPalette_Normalize')
    label('Select');put(f' lda.l {w}+28\n sta $0C\n lda.l {w}+30\n sta $0E')
    label('Normalize');put(f' lda $06\n asl a\n tax\n lda.l CurrentPalette_MapCounts+{code_bank<<16},x\n sta $10\n lda $0E');branch('bne','Base');put(' lda $0C\n cmp $10');branch('bcc','Chosen');branch('beq','Chosen')
    label('Base');put(' lda #0\n sta $0C')
    label('Chosen');put(' lda $0A\n tax\n lda $06');put(f' sta.l {base},x\n lda $0C\n sta.l {base}+2,x')
    for off in (0,2):put(f' lda.l {w}+{8+off}\n sta.l {base}+{4+off},x')
    put(f' lda #$B6AC\n sta.l {base}+8,x\n lda $00\n sta.l {base}+10,x')
    put(f' lda.l {w}+24\n cmp #4');branch('beq','StoreRestore');put(' cmp #5');branch('bne','Read');label('StoreRestore');offset(0,64,4);put(' tax\n lda $0C\n sta.l $433830,x');put(f' lda.l {w}+24\n cmp #5');branch('bne','Read');put(' lda $06\n sta.l $433832,x')
    label('Read');put(' lda $0A\n tax');put(f' lda.l {base},x\n sta.l {w}+36\n asl a\n tay\n lda.l {base}+2,x\n sta $0C\n tya\n tax\n lda.l CurrentPalette_MapCounts+{code_bank<<16},x\n cmp $0C');branch('bcc')
    put(f' lda $0C\n sta.l {w}+34')
    for name,status,carry in (('Good',2,'clc'),('Bad',3,'sec')):
        label(name);put(f' lda #{status}\n sta.l {w}+2\n tay\n tsc\n clc\n adc #{size}\n tcs\n tya\n pld\n ply\n plx\n plp\n {carry}\n rtl')
    label('MapCounts');put(' .dw '+','.join(str(m['maps_loaded'])for m in models))
    return '\n'.join(lines)+'\n'
