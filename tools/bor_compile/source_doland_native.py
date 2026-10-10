"""Source doland mutations and retained LAND-or-idle frame request."""
from source_animation_ids import configure
from source_engine_function_ids import function_id

def emit(work,sy):
 lines=[];serial=0;size=32;land=configure([])['authority']['enum']['ANI_LAND']
 def put(s):lines.extend(s.strip().splitlines())
 def label(n):put('CommonDoland_'+n+':\n.a16\n.i16')
 def branch(op,n='Bad'):
  nonlocal serial
  serial+=1;k='CommonDoland_Guard'+str(serial);put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+k+'\n jmp CommonDoland_'+n+'\n'+k+':\n.a16\n.i16')
 def require(at,v):put(f' lda.l {at}\n cmp #{v}');branch('bne')
 label('Run');put(f' php\n rep #$39\n phx\n phy\n phd\n tsc\n sec\n sbc #{size}\n tcs\n inc a\n tcd\n stx $14\n sty $16\n jsl {sy["SourceForeignWork_Check"]}');branch('bcs');require(work,0xb6bc)
 for off,dst in ((8,20),(10,22)):put(f' lda.l {work}+{off}\n cmp ${dst:02X}');branch('bne')
 for at,v in ((sy['VmSourceWorld_Ready'],0xb4a3),(sy['VmSourceWorld_PoolBase'],0x4000),(sy['VmSourceWorld_SideBase'],0x6800),(sy['SourceLifecycle4086_Ready'],0xb4fb)):require(at,v)
 for off in (0,2):put(f' lda.l {work}+{16+off}\n cmp.l {sy["VmSourceWorld_Time"]}+{off}');branch('bne')
 put(f' lda.l {sy["VmSourceWorld_Count"]}\n cmp #129');branch('bcs');put(f' lda.l {work}+4\n cmp.l {sy["VmSourceWorld_Count"]}');branch('bcs');put(' sta $00\n asl a\n asl a\n asl a\n asl a\n sta $0A\n asl a\n asl a\n sta $04\n clc\n adc $0A\n sta $02\n tax\n clc\n adc #$4000\n cmp.l $414000,x');branch('bne');require('$414002,x',0x41);require('$43904A,x',0xb4fb)
 put(f' lda.l {work}+2\n cmp #2');branch('beq','Good');put(' cmp #3');branch('beq','Retained');put(' cmp #0');branch('bne')
 require(sy['SourcePhysicsState4086_Ready'],0xb61c);require(sy['SourceDamageEffectsState4086_Ready'],0xb62f)
 put(' lda $00\n asl a\n asl a\n sta $12\n asl a\n asl a\n clc\n adc $12\n sta $0E\n tax');require('$437E10,x',0xb5fb);require('$437E12,x',0)
 put(' lda $00\n asl a\n asl a\n asl a\n sta $12\n asl a\n clc\n adc $12\n sta $0C\n tax');require('$7EF114,x',0xb62f);put(' lda.l $7EF116,x\n ldx $02\n cmp.l $439048,x');branch('bne');put(' ldx $04\n cmp.l $416800,x');branch('bne')
 put(f' jsl {sy["SourceAnimationInit4086_CheckIdle"]}');branch('bcs');put(f' jsl {sy["SourceUpdateFrame4086_CheckIdle"]}');branch('bcs')
 put(f' lda.l {work}+4\n sta.l {sy["SourceAnimationInit4086_Slot"]}\n lda #{land}\n sta.l {sy["SourceAnimationInit4086_Number"]}\n lda #0\n sta.l {sy["SourceAnimationInit4086_Reset"]}\n jsl {sy["SourceAnimationInit4086_Resolve"]}');branch('bcs')
 put(f' lda.l {sy["SourceAnimationInit4086_Count"]}');branch('beq','Absent')
 put(' ldx $02');require('$414018,x',1);require('$41401A,x',0);put(' lda.l $41401C,x\n ora.l $41401E,x');branch('beq','ReverseOne');put(' lda #0\n jmp CommonDoland_Direction')
 label('ReverseOne');put(' lda #1')
 label('Direction');put(f' sta $18\n lda #{function_id("common_land")}\n sta.l {work}+12\n lda #{land}\n sta.l {work}+14\n lda #2\n sta.l {work}+6\n jmp CommonDoland_Commit')
 label('Absent');put(f' lda #0\n sta.l {work}+12\n sta.l {work}+14\n lda #1\n sta.l {work}+6')
 label('Commit');put(' ldx $04\n lda #0\n sta.l $416824,x\n sta.l $416826,x\n sta.l $416828,x\n sta.l $41682A,x\n ldx $0E\n sta.l $437E00,x\n sta.l $437E02,x\n ldx $0C\n sta.l $7EF100,x\n sta.l $7EF102,x\n ldx $0A\n sta.l $42D80C,x\n sta.l $42D80E,x')
 put(f' ldx $02\n lda.l {work}+12\n sta.l $43900C,x\n lda #0\n sta.l $43900E,x\n lda.l {work}+6\n cmp #2');branch('bne','Pending');put(' lda $18\n sta.l $41401C,x\n lda #0\n sta.l $41401E,x')
 label('Pending');put(f' lda #3\n sta.l {work}+2')
 label('Retained');put(' lda #1\n jmp CommonDoland_Return')
 label('Good');put(' lda #0')
 label('Return');put(f' tay\n tsc\n clc\n adc #{size}\n tcs\n tya\n pld\n ply\n plx\n plp\n clc\n rtl')
 label('Bad');put(f' lda #4\n sta.l {work}+2\n tsc\n clc\n adc #{size}\n tcs\n pld\n ply\n plx\n plp\n sec\n rtl')
 return '\n'.join(lines)+'\n'
