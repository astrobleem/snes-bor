"""Closed death blink policy and retained real set_rise request from common_lie."""
from source_engine_function_ids import function_id
from source_recovery_state_layout import layout

def emit(work,plan,req,sy):
 if plan!=layout()or not req['source_zero_death_policy']:raise ValueError('COMMON_LIE_DEATH_POLICY_REQUIRED')
 rb=plan['base'];rw=plan['controls'];lines=[];serial=0
 def put(s):lines.extend(s.strip().splitlines())
 def label(n):put('CommonLie_'+n+':\n.a16\n.i16')
 def branch(op,n='Bad'):
  nonlocal serial
  serial+=1;l='CommonLie_Guard'+str(serial);put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+l+'\n jmp CommonLie_'+n+'\n'+l+':\n.a16\n.i16')
 def require(at,v):put(f' lda.l {at}\n cmp #{v}');branch('bne')
 label('Run');put(f' php\n rep #$39\n phx\n phy\n phd\n tsc\n sec\n sbc #32\n tcs\n inc a\n tcd\n stx $14\n sty $16\n jsl {sy["SourceForeignWork_Check"]}');branch('bcs');require(work,0xb6c4)
 for off,dst in ((8,20),(10,22)):put(f' lda.l {work}+{off}\n cmp ${dst:02X}');branch('bne')
 for at,v in ((sy['VmSourceWorld_Ready'],0xb4a3),(sy['VmSourceWorld_PoolBase'],0x4000),(sy['VmSourceWorld_SideBase'],0x6800),(sy['SourceLifecycle4086_Ready'],0xb4fb)):require(at,v)
 for off in (0,2):put(f' lda.l {work}+{16+off}\n cmp.l {sy["VmSourceWorld_Time"]}+{off}');branch('bne')
 put(f' lda.l {sy["VmSourceWorld_Count"]}\n cmp #129');branch('bcs');put(f' lda.l {work}+4\n cmp.l {sy["VmSourceWorld_Count"]}');branch('bcs')
 put(' sta $00\n asl a\n asl a\n asl a\n asl a\n sta $0A\n sta $0E\n asl a\n asl a\n sta $04\n clc\n adc $0E\n sta $02\n tax\n clc\n adc #$4000\n cmp.l $414000,x');branch('bne');require('$414002,x',0x41);require('$43904A,x',0xb4fb)
 put(f' lda.l {work}+2\n cmp #2');branch('beq','Good');put(' cmp #3');branch('beq','Retained');put(' cmp #0');branch('bne');require('$43900C,x',function_id('common_lie'));require('$43900E,x',0);require('$414020,x',1);require('$414022,x',0)
 put(' lda.l $414026,x\n and #$8000');branch('bne','Dead');put(' lda.l $414024,x\n ora.l $414026,x');branch('beq','Dead')
 # Source unsigned deadline comparison, then exact projected altitude/base
 # equality and vertical-velocity truth. No inair threshold is substituted.
 require(sy['SourceFreeze4086_Ready'],0xb5df)
 put(' lda $00\n asl a\n asl a\n asl a\n sta $0E\n asl a\n asl a\n clc\n adc $0E\n sta $06\n tax');require('$42E024,x',0xb5df)
 put(f' lda.l {work}+18\n cmp.l $42E00A,x');branch('bcc','Complete');branch('bne','Altitude');put(f' lda.l {work}+16\n cmp.l $42E008,x');branch('bcc','Complete')
 label('Altitude')
 put(' ldx $02');require('$414008,x',2);require('$41400A,x',0)
 for off in (0,2):put(f' ldx $02\n lda.l $41400C+{off},x\n ldx $04\n cmp.l $416830+{off},x');branch('bne','Complete')
 put(' lda.l $41682C,x\n ora.l $41682E,x');branch('bne','Complete')
 require(sy['SourceDamageState4086_Ready'],0xb62b)
 put(' lda $00\n asl a\n asl a\n sta $0E\n asl a\n clc\n adc $0E\n tax\n lda.l $7FB908,x')
 put(f' sta.l {work}+12\n lda #0\n sta.l {work}+14\n sta.l {work}+20\n sta.l {work}+22\n lda #1\n sta.l {work}+6\n lda #3\n sta.l {work}+2')
 label('Retained');put(' lda #1\n jmp CommonLie_Return')
 label('Dead');require(sy['SourceFreeze4086_Ready'],0xb5df);require(sy['SourceCtorState4086_Ready'],0xb5c2)
 put(' ldx $04');require('$43383E,x',0xb5c2);put(' lda.l $416800,x\n ldx $02\n cmp.l $439048,x');branch('bne');put(f' cmp #{len(req["models"])}');branch('bcs')
 put(' lda $00\n asl a\n asl a\n asl a\n sta $0E\n asl a\n asl a\n clc\n adc $0E\n sta $06\n tax');require('$42E024,x',0xb5df)
 for at,v in ((rw,0xb6c0),(rw+16,rb&65535),(rw+18,0x42),(rw+22,128)):require(at,v)
 put(f' lda.l {rw}+20');branch('beq');put(f' cmp #{plan["chr_capacity"]+1}');branch('bcs')
 for off in (8,10):put(f' lda.l {rw}+{off}\n cmp.l {work}+{off}');branch('bne')
 put(' ldx $0A');require(f'{rb}+12,x',0xb6c1);put(f' lda.l {rb}+14,x\n cmp $00');branch('bne')
 for off in (8,10):put(f' lda.l {rb}+{off},x\n cmp.l {work}+{off}');branch('bne')
 put(' lda $00\n asl a\n asl a\n asl a\n asl a\n asl a\n sta $0E\n asl a\n clc\n adc $0E\n tax\n lda.l $40C048,x\n and #1');branch('beq','Suicide')
 put(f' lda #{function_id("player_blink")}\n jmp CommonLie_DeathAction')
 label('Suicide');put(f' lda #{function_id("suicide")}')
 label('DeathAction');put(f' ldx $02\n sta.l $43900C,x\n lda #0\n sta.l $43900E,x\n ldx $0A\n lda #1\n sta.l {rb},x\n lda #0\n sta.l {rb}+2,x\n ldx $06\n lda.l {work}+16\n clc\n adc #400\n sta.l $42E008,x\n lda.l {work}+18\n adc #0\n sta.l $42E00A,x')
 label('Complete');put(f' lda #2\n sta.l {work}+2')
 label('Good');put(' lda #0')
 label('Return');put(' tay\n tsc\n clc\n adc #32\n tcs\n tya\n pld\n ply\n plx\n plp\n clc\n rtl')
 label('Bad');put(f' lda #4\n sta.l {work}+2\n tsc\n clc\n adc #32\n tcs\n pld\n ply\n plx\n plp\n sec\n rtl')
 return '\n'.join(lines)+'\n'
