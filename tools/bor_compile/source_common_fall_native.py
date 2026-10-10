"""Closed source common_fall through lie transition; doland remains a ticket."""
from source_engine_function_ids import function_id
from source_model_switch_4086 import ENTITY_CORE_FIELDS

def emit(work,speedup,req,sy):
 if not req['source_staydown_zero']or not req['riseattack_zero']or req['live_inherited_rise_values']!=[-1,0,100]:raise ValueError('COMMON_FALL_CLOSED_DEADLINE_CAPABILITY')
 lines=[];serial=0;size=32;rise=ENTITY_CORE_FIELDS.index('risetime.rise')*4
 def put(s):lines.extend(s.strip().splitlines())
 def label(n):put('CommonFall_'+n+':\n.a16\n.i16')
 def branch(op,n='Bad'):
  nonlocal serial
  serial+=1;k='CommonFall_Guard'+str(serial);put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+k+'\n jmp CommonFall_'+n+'\n'+k+':\n.a16\n.i16')
 def require(at,v):put(f' lda.l {at}\n cmp #{v}');branch('bne')
 label('Run');put(f' php\n rep #$39\n phx\n phy\n phd\n tsc\n sec\n sbc #{size}\n tcs\n inc a\n tcd\n stx $14\n sty $16\n jsl {sy["SourceForeignWork_Check"]}');branch('bcs');require(work,0xb6bb)
 for off,dst in ((8,20),(10,22)):put(f' lda.l {work}+{off}\n cmp ${dst:02X}');branch('bne')
 for at,v in ((sy['VmSourceWorld_Ready'],0xb4a3),(sy['VmSourceWorld_PoolBase'],0x4000),(sy['VmSourceWorld_SideBase'],0x6800),(sy['SourceLifecycle4086_Ready'],0xb4fb)):require(at,v)
 for off in (0,2):put(f' lda.l {work}+{16+off}\n cmp.l {sy["VmSourceWorld_Time"]}+{off}');branch('bne')
 put(f' lda.l {sy["VmSourceWorld_Count"]}\n cmp #129');branch('bcs');put(f' lda.l {work}+4\n cmp.l {sy["VmSourceWorld_Count"]}');branch('bcs');put(' sta $00\n asl a\n asl a\n asl a\n asl a\n sta $12\n sta $0A\n asl a\n asl a\n sta $04\n clc\n adc $12\n sta $02\n tax\n clc\n adc #$4000\n cmp.l $414000,x');branch('bne');require('$414002,x',0x41);require('$43904A,x',0xb4fb)
 put(f' lda.l {work}+2\n cmp #2');branch('beq','Good');put(' cmp #1');branch('beq','Ticket');put(' cmp #0');branch('bne');require('$43900C,x',function_id('common_fall'));require('$43900E,x',0)
 require(sy['SourcePhysicsState4086_Ready'],0xb61c);put(' ldx $0A\n lda.l $42D800,x\n ora.l $42D802,x');branch('bne','Complete')
 put(' ldx $02');require('$414008,x',2);require('$41400A,x',0)
 for off,n in ((0,'Lo'),(2,'Hi')):put(f' lda.l $41400C+{off},x\n sta.l {sy["SourceModelEntityCopy4086_"+n]}')
 put(' ldx $04')
 for off,n in ((0,'Lo'),(2,'Hi')):put(f' lda.l $416830+{off},x\n sta.l {sy["SourceDefaultPlayer4086_Inv"+n]}')
 put(f' jsl {sy["SourceInAir4086_Q16Compatibility"]}');branch('bcs');put(' cmp #0');branch('bne','Complete');put(' ldx $04\n lda.l $41682C,x\n ora.l $41682E,x');branch('bne','Complete')
 # All writes follow the complete landed-path preflight.
 require(sy['SourceDamageEffectsState4086_Ready'],0xb62f);require(sy['SourceFreeze4086_Ready'],0xb5df);require(sy['SourceCtorState4086_Ready'],0xb5c2);require(sy['SourceLandingVelocity4086_Ready'],0xb626);require(sy['SourceScrollerPrefix4086_Ready'],0xb5d7)
 put(' lda $00\n asl a\n asl a\n asl a\n sta $12\n asl a\n clc\n adc $12\n sta $0C\n tax');require('$7EF114,x',0xb62f);put(' lda.l $7EF116,x\n ldx $02\n cmp.l $439048,x');branch('bne');put(' ldx $04\n cmp.l $416800,x');branch('bne');put(f' cmp #{len(req["models"])}');branch('bcs')
 put(' ldx $0C\n lda.l $7EF104,x\n ora.l $7EF106,x\n ora.l $7EF108,x\n ora.l $7EF10A,x');branch('bne')
 put(' lda $00\n asl a\n asl a\n asl a\n sta $12\n asl a\n asl a\n clc\n adc $12\n sta $0E\n tax');require('$42E024,x',0xb5df)
 put(' lda $00\n asl a\n asl a\n asl a\n asl a\n asl a\n sta $12\n asl a\n clc\n adc $12\n sta $10\n tax')
 put(f' lda.l $40C000+{rise}+2,x\n cmp #$FFFF');branch('beq','NegativeRise');put(' cmp #0');branch('bne');put(f' lda.l $40C000+{rise},x\n cmp #0');branch('beq','RiseZero');put(' cmp #100');branch('bne');put(' lda #100\n jmp CommonFall_Delay')
 label('NegativeRise');require(f'$40C000+{rise},x',65535);put(' lda #201\n jmp CommonFall_Delay')
 label('RiseZero');put(' lda #200')
 label('Delay');put(' sta $18\n lda $04\n tax');require('$43383E,x',0xb5c2);put(f' lda.l {speedup}\n cmp #2');branch('bcs')
 put(' ldx $0C\n lda.l $7EF102,x');branch('bne','ProjectileHigh');put(' lda.l $7EF100,x\n cmp #2');branch('beq','ProjectileTwo');put(' cmp #0');branch('beq','Boss');put(' jmp CommonFall_Boss')
 label('ProjectileHigh');put(' and #$8000');branch('bne','Boss');put(' jmp CommonFall_Boss')
 label('ProjectileTwo');put(' ldx $0A\n lda.l $42D80E,x\n cmp #$FFFF');branch('bne','Boss');put(' lda.l $42D80C,x\n cmp #$FFFE');branch('beq','RequestLand');put(' cmp #$FFFF');branch('bne','Boss');put(f' lda.l {sy["SourceLandingVelocity4086_Autoland"]}+2');branch('bne','Boss')
 put(f' lda.l {sy["SourceLandingVelocity4086_Autoland"]}\n cmp #1');branch('beq','RequestLand')
 label('Boss');put(' ldx $04\n lda.l $433838,x\n ora.l $43383A,x');branch('beq','Lie');put(f' lda.l {sy["SourceScrollerPrefix4086_Completed"]}\n ora.l {sy["SourceScrollerPrefix4086_Completed"]}+2');branch('beq','Lie');put(f' lda #1\n sta.l {speedup}')
 label('Lie');put(f' ldx $02\n lda #{function_id("common_lie")}\n sta.l $43900C,x\n lda #0\n sta.l $43900E,x\n ldx $0E\n lda.l {work}+16\n clc\n adc $18\n sta.l $42E008,x\n lda.l {work}+18\n adc #0\n sta.l $42E00A,x\n ldx $0C\n lda.l {work}+16\n sta.l $7EF10C,x\n lda.l {work}+18\n sta.l $7EF10E,x\n lda #0\n sta.l $7EF104,x\n sta.l $7EF106,x\n sta.l $7EF108,x\n sta.l $7EF10A,x')
 label('Complete');put(f' lda #2\n sta.l {work}+2')
 label('Good');put(' lda #0\n jmp CommonFall_Return')
 label('RequestLand');put(f' lda #1\n sta.l {work}+6\n sta.l {work}+2')
 label('Ticket');put(' lda #1')
 label('Return');put(f' tay\n tsc\n clc\n adc #{size}\n tcs\n tya\n pld\n ply\n plx\n plp\n clc\n rtl')
 label('Bad');put(f' lda #4\n sta.l {work}+2\n tsc\n clc\n adc #{size}\n tcs\n pld\n ply\n plx\n plp\n sec\n rtl')
 return '\n'.join(lines)+'\n'
