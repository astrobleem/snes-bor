"""Retained common_rise idle child, with actual persistent blink/time writes."""
from source_engine_function_ids import function_id
from source_recovery_state_layout import layout

def emit(work,plan,req,sy):
 if plan!=layout(plan['entities'])or plan['entities']!=128:raise ValueError('COMMON_RISE_RECOVERY_LAYOUT')
 models=req['models']
 if not 0<len(models)<=16 or any(m['id']!=i or not -0x7fffffff<=m['fields']['riseinv']<=0x7fffffff for i,m in enumerate(models)):raise ValueError('COMMON_RISE_MODEL_POLICY')
 base=plan['base'];rw=plan['controls'];lines=[];serial=0
 def put(s):lines.extend(s.strip().splitlines())
 def label(n):put('CommonRise_'+n+':\n.a16\n.i16')
 def branch(op,n='Bad'):
  nonlocal serial
  serial+=1;l='CommonRise_Guard'+str(serial);put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+l+'\n jmp CommonRise_'+n+'\n'+l+':\n.a16\n.i16')
 def require(at,v):put(f' lda.l {at}\n cmp #{v}');branch('bne')
 label('Run');put(f' php\n rep #$39\n phx\n phy\n phd\n tsc\n sec\n sbc #32\n tcs\n inc a\n tcd\n stx $14\n sty $16\n jsl {sy["SourceForeignWork_Check"]}');branch('bcs');require(work,0xb6c2)
 for off,dst in ((8,20),(10,22)):put(f' lda.l {work}+{off}\n cmp ${dst:02X}');branch('bne')
 put(f' lda.l {work}+2\n sta $08');branch('beq','Validate');put(' cmp #3');branch('beq','Validate');put(' cmp #2');branch('bne')
 label('Validate')
 for at,v in ((sy['VmSourceWorld_Ready'],0xb4a3),(sy['VmSourceWorld_PoolBase'],0x4000),(sy['VmSourceWorld_SideBase'],0x6800),(sy['SourceLifecycle4086_Ready'],0xb4fb)):require(at,v)
 for off in (0,2):put(f' lda.l {work}+{16+off}\n cmp.l {sy["VmSourceWorld_Time"]}+{off}');branch('bne')
 put(f' lda.l {sy["VmSourceWorld_Count"]}\n cmp #129');branch('bcs');put(f' lda.l {work}+4\n cmp.l {sy["VmSourceWorld_Count"]}');branch('bcs')
 put(' sta $00\n asl a\n asl a\n asl a\n asl a\n sta $0A\n sta $0E\n asl a\n asl a\n sta $04\n clc\n adc $0E\n sta $02\n tax\n clc\n adc #$4000\n cmp.l $414000,x');branch('bne');require('$414002,x',0x41);require('$43904A,x',0xb4fb)
 put(' lda $08\n cmp #3');branch('beq','Retained');put(' cmp #2');branch('beq','Good');require('$43900C,x',function_id('common_rise'));require('$43900E,x',0)
 put(' lda $00\n asl a\n asl a\n sta $0E\n asl a\n asl a\n clc\n adc $0E\n tax\n lda.l $41F510,x');branch('bne','Complete')
 # The stopped branch preflights every persistent owner before mutation.
 require(sy['SourceDamageEffectsState4086_Ready'],0xb62f)
 put(' ldx $04\n lda.l $416800,x');put(f' cmp #{len(models)}');branch('bcs');put(' sta $0C\n ldx $02\n cmp.l $439048,x');branch('bne')
 put(' lda $00\n asl a\n asl a\n asl a\n sta $0E\n asl a\n clc\n adc $0E\n sta $06\n tax');require('$7EF114,x',0xb62f);put(' lda.l $7EF116,x\n cmp $0C');branch('bne')
 # Poppy loses the long-address bank for a label+constant indexed operand.
 # Independent named word tables retain the full emitted cartridge address.
 put(' lda $0C\n asl a\n tax\n lda.l CommonRise_InvincibilityLow,x\n sta $18\n lda.l CommonRise_InvincibilityHigh,x\n sta $1A\n ora $18');branch('beq','Mutate')
 for at,v in ((rw,0xb6c0),(rw+16,base&65535),(rw+18,0x42),(rw+22,128)):require(at,v)
 put(f' lda.l {rw}+20');branch('beq');put(f' cmp #{plan["chr_capacity"]+1}');branch('bcs')
 for off in (8,10):put(f' lda.l {rw}+{off}\n cmp.l {work}+{off}');branch('bne')
 put(' ldx $0A');require(f'{base}+12,x',0xb6c1);put(f' lda.l {base}+14,x\n cmp $00');branch('bne')
 for off in (8,10):put(f' lda.l {base}+{off},x\n cmp.l {work}+{off}');branch('bne')
 put(' jsr CommonRise_ClearAction\n ldx $0A')
 # Source riseinv sign controls blink; ABS duration adds modulo uint32.
 put(' lda $1A\n and #$8000');branch('beq','Positive')
 put(' lda #0\n sec\n sbc $18\n sta $18\n lda #0\n sbc $1A\n sta $1A\n lda #0\n jmp CommonRise_Blink')
 label('Positive');put(' lda #1')
 label('Blink');put(f' sta.l {base},x\n lda #0\n sta.l {base}+2,x\n lda.l {work}+16\n clc\n adc $18\n sta.l {base}+4,x\n lda.l {work}+18\n adc $1A\n sta.l {base}+6,x\n ldx $02\n lda #1\n sta.l $439018,x\n lda #0\n sta.l $43901A,x')
 put(' jmp CommonRise_Request')
 label('Mutate');put(' jsr CommonRise_ClearAction')
 label('Request');put(f' lda #0\n sta.l {work}+12\n sta.l {work}+14\n lda #1\n sta.l {work}+6\n lda #3\n sta.l {work}+2')
 label('Retained');put(' lda #1\n jmp CommonRise_Return')
 label('Complete');put(f' lda #2\n sta.l {work}+2')
 label('Good');put(' lda #0')
 label('Return');put(' tay\n tsc\n clc\n adc #32\n tcs\n tya\n pld\n ply\n plx\n plp\n clc\n rtl')
 label('Bad');put(f' lda #4\n sta.l {work}+2\n tsc\n clc\n adc #32\n tcs\n pld\n ply\n plx\n plp\n sec\n rtl')
 label('ClearAction');put(' ldx $02\n lda #0\n sta.l $43900C,x\n sta.l $43900E,x\n ldx $06\n sta.l $7EF10C,x\n sta.l $7EF10E,x\n rts')
 put('CommonRise_InvincibilityLow:')
 for m in models:put(' .dw '+str(m['fields']['riseinv']&65535))
 put('CommonRise_InvincibilityHigh:')
 for m in models:put(' .dw '+str((m['fields']['riseinv']>>16)&65535))
 return '\n'.join(lines)+'\n'
