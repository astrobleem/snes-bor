"""Native common/player_trymove for explicitly leased flat closed scenes.

The caller owns 96 serialized bytes. No production arena allocation or full
check_move binding is implied. Bounds, live type filtering and random use real
source stores; unsupported candidate geometry fails instead of returning NULL.
"""
from dialect_4086 import ENGINE_COMMIT


def emit(req,work,sy):
    if not req['admitted'] or req['diagnostics'] or req['engine_commit']!=ENGINE_COMMIT or req['capability']!='SOURCE_FLAT_CLOSED_TRYMOVE':
        raise ValueError('FLAT_TRYMOVE_SOURCE_REQUIREMENTS')
    if not 0<=work<=0xffffff-96 or work&1:raise ValueError('FLAT_TRYMOVE_WORK_EXTENT')
    models=len(req['models']);lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('FlatTrymove_'+n+':\n.a16\n.i16')
    def jump(op,n='Bad'):
        nonlocal serial
        serial+=1;l='FlatTrymove_Guard'+str(serial)
        inv=dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc',bmi='bpl',bpl='bmi',bvc='bvs',bvs='bvc')[op]
        put(f' {inv} {l}\n jmp FlatTrymove_{n}\n{l}:\n.a16\n.i16')
    def equal(at,value):put(f' lda.l {at}\n cmp #{value}');jump('bne')
    def positive(at,skip):
        high=at.replace(',x','+2,x') if ',x' in at else at+'+2'
        put(f' lda.l {high}\n bmi FlatTrymove_{skip}\n bne FlatTrymove_Pos{skip}\n lda.l {at}\n beq FlatTrymove_{skip}')
        label('Pos'+skip)
    def compare(a,b):
        # Both operands are signed Q16.16. Bias the high words, compare low on equality.
        put(f' lda {a}+2\n eor #$8000\n sta $50\n lda {b}+2\n eor #$8000\n cmp $50')
    def less(a,b,target):
        nonlocal serial
        serial+=1;n='Cmp'+str(serial)
        compare(b,a);jump('bcc',target);put(' bne FlatTrymove_'+n+f'\n lda {a}\n cmp {b}');jump('bcc',target);label(n)
    def add(a,b,out):
        put(f' clc\n lda {a}\n adc {b}\n sta {out}\n lda {a}+2\n adc {b}+2');jump('bvs');put(f' sta {out}+2')
    def subtract(a,b,out):
        put(f' sec\n lda {a}\n sbc {b}\n sta {out}\n lda {a}+2\n sbc {b}+2');jump('bvs');put(f' sta {out}+2')
    label('Execute');put(' php\n rep #$39\n phx\n phy\n phd\n phb\n tsc\n sec\n sbc #96\n tcs\n inc a\n tcd')
    put(' sep #$20\n.a8\n lda #0\n pha\n plb\n rep #$20\n.a16')
    put(f' lda #0\n sta.l {work}+4')
    equal(work,0xb6a5);equal(work+2,0)
    put(f' jsl {sy["SourceForeignWork_Check"]}');jump('bcs')
    put(f' txa\n cmp.l {work}+12');jump('bne');put(f' tya\n cmp.l {work}+14');jump('bne')
    for n,v in (('SourceWorldTick4086_Ready',0xb4d5),('SourceWorldTick4086_Pending',1),('SourceWorldTick4086_Phase',11),('SourceWorldTick4086_Fault',0),('VmSourceWorld_Ready',0xb4a3),('VmSourceWorld_PoolBase',0x4000),('VmSourceWorld_SideBase',0x6800),('SourceLifecycle4086_Ready',0xb4fb),('SourceModelEntityCopy4086_Ready',0xb4eb),('SourceModelEntityCopy4086_Models',models),('SourceSelf4086_Ready',0xb4f6),('SourceSelf4086_Active',0),('SourceSelf4086_Fault',0),('SourceCameraMotion4086_Ready',0xb5db)):
        equal(sy[n],v)
    put(f' lda.l {sy["SourceWorldTick4086_State"]}\n cmp #1\n beq FlatTrymove_State\n cmp #2');jump('bne');label('State')
    for off in (0,2):
        put(f' lda.l {sy["VmSourceWorld_Time"]}+{off}\n cmp.l {sy["SourceWorldTick4086_TimeLo"]}+{off}');jump('bne')
    put(f' lda.l {sy["VmSourceWorld_Count"]}');jump('beq');put(' cmp #129');jump('bcs')
    put(f' cmp.l {sy["SourceModelEntityCopy4086_Entities"]}');jump('bne')
    put(f' lda.l {work}+10\n cmp.l {sy["SourceWorldTick4086_Slot"]}');jump('bne');put(f' cmp.l {sy["VmSourceWorld_Count"]}');jump('bcs')
    # DP physical offsets: view0, core2, flags4, side6, aux8, model10.
    put(' asl a\n asl a\n sta $00\n asl a\n asl a\n clc\n adc $00\n sta $08\n asl a\n asl a\n sta $00')
    put(f' cmp.l {sy["SourceWorldTick4086_View"]}');jump('bne')
    put(f' lda.l {work}+10\n asl a\n asl a\n asl a\n asl a\n asl a\n sta $04\n asl a\n sta $06')
    put(f' cmp.l {sy["SourceWorldTick4086_Side"]}');jump('bne');put(' clc\n adc $04\n sta $02')
    put(' ldx $00\n txa\n clc\n adc #$4000\n cmp.l $414000,x');jump('bne');put(f' cmp.l {sy["SourceSelf4086_GlobalLow"]}');jump('bne')
    equal(sy['SourceSelf4086_GlobalHigh'],0x41);put(' lda.l $414002,x\n cmp #$41');jump('bne');put(' lda.l $414004,x\n ora.l $414006,x');jump('beq')
    for off in (48,56):equal(f'$414000+{off},x',2);equal(f'$414000+{off+2},x',0)
    put(' lda.l $43904A,x\n cmp #$B4FB');jump('bne');put(' lda.l $43900A,x');jump('bne')
    put(' lda.l $439008,x\n cmp #3\n beq FlatTrymove_Callback\n cmp #9');jump('bne');label('Callback')
    put(' ldx $06\n lda.l $416800,x\n sta $0A\n ldx $00\n cmp.l $439048,x');jump('bne');put(f' cmp #{models}');jump('bcs')
    put(f' jsl {sy["SourceEmptyInitEnvironment4086_Query"]}');jump('bcs')
    for at,v in ((work+8,models),(sy['SourceEmptyInitEnvironment4086_Models'],models)):
        equal(at,v)
    put(f' lda.l {work}+6\n cmp.l {sy["VmSourceWorld_Level"]}');jump('bne')
    put(f' cmp.l {sy["SourceEnvironment4086_Stage"]}');jump('bne')
    # The W lease independently asserts no authored holes, movement scripts or mutations.
    equal(work+16,0);equal(work+18,0)
    put(' ldx $00')
    for at,dp in ((52,0x10),(60,0x14)):
        for off in (0,2):put(f' lda.l $414000+{at+off},x\n sta ${dp+off:02X}')
    put(' ldx $08')
    for at,dp in ((0,0x18),(4,0x1c)):
        for off in (0,2):put(f' lda.l $41F500+{at+off},x\n sta ${dp+off:02X}')
    put(' lda $18\n ora $1A\n ora $1C\n ora $1E');jump('beq','False')
    # Cache absence is a checked live invariant, not an actor-name exception.
    equal(sy['SourceModelAnimationCopy4086_Ready'],0xb4e9);equal(sy['SourceModelAnimationCopy4086_Models'],models)
    equal(sy['SourceModelAnimationCopy4086_Maximum'],168);equal(sy['SourceModelAnimationCopy4086_RowBytes'],336)
    put(' lda $0A\n sta $50\n lda #0\n tax');label('CacheOffset')
    put(' cpx $50\n beq FlatTrymove_Cache\n clc\n adc #336\n inx\n bra FlatTrymove_CacheOffset');label('Cache')
    put(' tax\n lda.l $43C022,x\n ora.l $43C028,x');jump('bne')
    # Conservative actual type scan, only when source obstacle policy is positive.
    put(' ldx $02');positive('$40C00C,x','NoCandidates')
    put(' lda #0\n sta $54\n sta $56\n sta $58');label('CandidateLoop')
    put(f' lda $54\n cmp.l {work}+10\n beq FlatTrymove_CandidateNext\n ldx $56\n lda.l $414004,x\n ora.l $414006,x\n beq FlatTrymove_CandidateNext\n ldx $58\n lda.l $40C048,x\n and #72');jump('bne','Required')
    label('CandidateNext');put(' lda $56\n clc\n adc #80\n sta $56\n lda $58\n clc\n adc #96\n sta $58\n inc $54\n lda $54')
    put(f' cmp.l {sy["VmSourceWorld_Count"]}\n bcc FlatTrymove_CandidateLoop');label('NoCandidates')
    put(' ldx $02\n lda.l $40C048,x\n and #1\n beq FlatTrymove_NoRandom')
    put(f' jsl {sy["SourceCRandom4086_Next"]}');jump('bcs');label('NoRandom')
    add('$10','$18','$20');add('$14','$1C','$24')
    for n,dp in (('MinZ',0x28),('MaxZ',0x2c)):
        for off in (0,2):put(f' lda.l {sy["SourceCameraMotion4086_"+n]}+{off}\n sta ${dp+off:02X}')
    # Depth globals are actual source integers represented in Q16, not fractional bounds.
    put(' lda $28\n ora $2C');jump('bne')
    put(' ldx $02');positive('$40C01C,x','MinDone');less('$24','$28','ClampMin');put(' jmp FlatTrymove_MinDone')
    label('ClampMin');subtract('$28','$14','$1C');label('MinDone')
    positive('$40C020,x','MaxDone');less('$2C','$24','ClampMax');put(' jmp FlatTrymove_MaxDone')
    label('ClampMax');subtract('$2C','$14','$1C');label('MaxDone')
    positive('$40C018,x','ScreenDone')
    for off in (0,2):put(f' lda.l {sy["VmSourceWorld_AdvanceX"]}+{off}\n sta ${0x30+off:02X}')
    put(' lda #0\n sta $38\n lda #10\n sta $3A');add('$30','$38','$34')
    put(f' lda.l {sy["SourceCameraMotion4086_HRes"]}\n cmp #20');jump('bcc');put(' cmp #32768');jump('bcs')
    put(' sec\n sbc #10\n sta $3A');add('$30','$38','$3C')
    less('$20','$34','ClampLeft');less('$3C','$20','ClampRight');put(' jmp FlatTrymove_ScreenDone')
    label('ClampLeft');subtract('$34','$10','$18');put(' jmp FlatTrymove_ScreenDone')
    label('ClampRight');subtract('$3C','$10','$18');label('ScreenDone')
    put(' lda $18\n ora $1A\n ora $1C\n ora $1E');jump('beq','False')
    add('$10','$18','$20');add('$14','$1C','$24')
    # Actual testmove's repeated bound checks may reject incompatible source bounds.
    positive('$40C01C,x','TestMinDone');put(' lda $1C\n ora $1E\n beq FlatTrymove_TestMinDone');less('$24','$28','False');label('TestMinDone')
    positive('$40C020,x','TestMaxDone');put(' lda $1C\n ora $1E\n beq FlatTrymove_TestMaxDone');less('$2C','$24','False');label('TestMaxDone')
    positive('$40C018,x','TestScreenDone');less('$20','$34','False');less('$3C','$20','False');label('TestScreenDone')
    # Result 1 means original displacement survived, 2 means adjusted displacement.
    put(' lda #1\n sta $40\n ldx $08')
    for a,b in ((0,0x18),(2,0x1a),(4,0x1c),(6,0x1e)):
        put(f' lda.l $41F500+{a},x\n cmp ${b:02X}\n bne FlatTrymove_Adjusted')
    put(' jmp FlatTrymove_Publish');label('Adjusted');put(' lda #2\n sta $40');label('Publish');put(' ldx $00')
    for at,dp in ((52,0x20),(60,0x24)):
        for off in (0,2):put(f' lda ${dp+off:02X}\n sta.l $414000+{at+off},x')
    put(f' lda $40\n sta.l {work}+4\n jmp FlatTrymove_Good')
    label('False');put(f' lda #0\n sta.l {work}+4');label('Good');put(' lda #2');put(f' sta.l {work}+2\n jmp FlatTrymove_ReturnGood')
    label('Required');put(' lda #4\n jmp FlatTrymove_Fault');label('Bad');put(' lda #3');label('Fault');put(f' sta.l {work}+2')
    put(' tsc\n clc\n adc #96\n tcs\n plb\n pld\n ply\n plx\n plp\n sec\n rtl')
    label('ReturnGood');put(' tsc\n clc\n adc #96\n tcs\n plb\n pld\n ply\n plx\n plp');put(f' lda.l {work}+4\n clc\n rtl')
    # Expand any remaining short conditional branches to keep generic registry bounds safe.
    import re
    code='\n'.join(lines)+'\n'
    serial2=[0]
    def relax(m):
        serial2[0]+=1;n='FlatTrymove_Relax'+str(serial2[0]);inv=dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc',bmi='bpl',bpl='bmi')[m[1]]
        return f' {inv} {n}\n jmp {m[2]}\n{n}:\n.a16\n.i16'
    code=re.sub(r'^ (beq|bne|bcc|bcs|bmi|bpl) (FlatTrymove_\w+)$',relax,code,flags=re.M)
    return re.sub(r'^ bra (FlatTrymove_\w+)$',r' jmp \1',code,flags=re.M)
