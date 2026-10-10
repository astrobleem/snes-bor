"""One-time fall motion child using the actual native source entity toss."""
from source_damage_tail_requirements import pack

def emit(work,req,sy,code_bank=39):
 if req['capability']!='SOURCE_ZERO_ESCAPE_FALLDIE_NOPAIN_COUNT_NO_TAIL_WEAPONLOSS_NO_GRAB':raise ValueError('DAMAGE_TAIL_MOTION_CAPABILITY')
 lines=[];serial=0;size=32
 def put(s):lines.extend(s.strip().splitlines())
 def label(n):put('DamageTailMotion_'+n+':\n.a16\n.i16')
 def branch(op,n='Bad'):
  nonlocal serial
  serial+=1;k='DamageTailMotion_Guard'+str(serial);put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc',bmi='bpl',bpl='bmi',bvc='bvs')[op]+' '+k+'\n jmp DamageTailMotion_'+n+'\n'+k+':\n.a16\n.i16')
 def require(at,v):put(f' lda.l {at}\n cmp #{v}');branch('bne')
 def offset(stride,dst):
  put(' lda $00\n asl a\n asl a')
  if stride==64:put(' asl a\n asl a\n asl a\n asl a')
  elif stride==80:put(' asl a\n asl a\n sta $1E\n asl a\n asl a\n clc\n adc $1E')
  elif stride==12:put(' sta $1E\n asl a\n clc\n adc $1E')
  elif stride==20:put(' sta $1E\n asl a\n asl a\n clc\n adc $1E')
  else:raise ValueError('TAIL_MOTION_STRIDE')
  put(f' sta ${dst:02X}')
 label('Run');put(f' php\n rep #$39\n phx\n phy\n phd\n tsc\n sec\n sbc #{size}\n tcs\n inc a\n tcd\n stx $1A\n sty $1C\n jsl {sy["SourceForeignWork_Check"]}');branch('bcs');require(work,0xb6b7)
 for off,dst in ((8,26),(10,28)):put(f' lda.l {work}+{off}\n cmp ${dst:02X}');branch('bne')
 for off in (12,14,20,22):require(work+off,0)
 put(f' lda.l {work}+2');branch('beq','Validate');put(' cmp #2');branch('bne')
 label('Validate')
 for at,v in ((sy['VmSourceWorld_Ready'],0xb4a3),(sy['VmSourceWorld_PoolBase'],0x4000),(sy['VmSourceWorld_SideBase'],0x6800),(sy['SourceLifecycle4086_Ready'],0xb4fb),(sy['SourceDamageState4086_Ready'],0xb62b),(sy['SourceEntityToss4086_Ready'],0xb624),(sy['SourceToss4086_Ready'],0xb4e2)):require(at,v)
 for off in (0,2):put(f' lda.l {work}+{16+off}\n cmp.l {sy["VmSourceWorld_Time"]}+{off}');branch('bne')
 put(f' lda.l {sy["VmSourceWorld_Count"]}\n cmp #129');branch('bcs');put(f' lda.l {work}+4\n cmp.l {sy["VmSourceWorld_Count"]}');branch('bcs');put(' sta $00')
 for stride,dst in ((80,2),(64,4),(12,6),(20,8)):offset(stride,dst)
 put(' ldx $02\n txa\n clc\n adc #$4000\n cmp.l $414000,x');branch('bne');require('$414002,x',0x41);require('$43904A,x',0xb4fb)
 put(' lda.l $439048,x');put(f' cmp #{len(req["models"])}');branch('bcs');put(' lda.l $439040,x\n ora.l $439042,x');branch('bne')
 put(f' lda.l {work}+6\n cmp #1');branch('bcc');put(f' cmp #{len(req["attacks"])+1}');branch('bcs');put(' dec a\n asl a\n asl a\n asl a\n asl a\n tax')
 for off,dst in ((0,10),(2,12),(4,14),(6,16),(8,18),(10,20),(12,22),(14,24)):put(f' lda.l DamageTailMotion_Attacks+{(code_bank<<16)+off},x\n sta ${dst:02X}')
 put(f' lda.l {work}+2\n cmp #2');branch('beq','Good')
 require(sy['SourceEntityToss4086_Status'],0)
 # Complete preflight before any actor mutation. Nonzero lift requires a
 # live canonical entity and representable Q16 half-pixel altitude increment.
 put(' lda $0E\n ora $10');branch('beq','Facing');put(' ldx $02\n lda.l $414004,x\n ora.l $414006,x');branch('beq');require('$414008,x',2);require('$41400A,x',0)
 put(' lda.l $41400C,x\n clc\n adc #$8000\n lda.l $41400E,x\n adc #0');branch('bvc','Facing');put(' jmp DamageTailMotion_Bad')
 label('Facing');put(' ldx $02\n lda.l $41401E,x');branch('bne','Write');put(' lda.l $41401C,x\n cmp #1');branch('bne','Write')
 put(' lda $0A\n eor #$FFFF\n clc\n adc #1\n sta $0A\n lda $0C\n eor #$FFFF\n adc #0\n sta $0C')
 label('Write');put(' ldx $04')
 for src,off in ((10,36),(12,38),(18,40),(20,42)):put(f' lda ${src:02X}\n sta.l $416800+{off},x')
 put(f' lda.l {work}+4\n sta.l {sy["SourceEntityToss4086_Slot"]}')
 for src,off in ((14,0),(16,2)):put(f' lda ${src:02X}\n sta.l {sy["SourceEntityToss4086_Lift"]}+{off}')
 put(f' jsl {sy["SourceEntityToss4086_Execute"]}');branch('bcs');require(sy['SourceEntityToss4086_Status'],2)
 put(' ldx $00\n txa\n asl a\n asl a\n asl a\n asl a\n tax')
 for src,off in ((22,12),(24,14)):put(f' lda ${src:02X}\n sta.l $42D800+{off},x')
 put(' ldx $06\n lda #0')
 for off in (0,2,4,6):put(f' sta.l $7FB900+{off},x')
 put(f' lda #2\n sta.l {work}+2')
 label('Good');put(f' tsc\n clc\n adc #{size}\n tcs\n pld\n lda #2\n ply\n plx\n plp\n clc\n rtl')
 label('Bad');put(f' lda #4\n sta.l {work}+2\n tsc\n clc\n adc #{size}\n tcs\n pld\n ply\n plx\n plp\n sec\n rtl')
 label('Attacks');put(' .dw '+','.join(str(v)for a in req['attacks']for n in (*a['dropv_q16'],a['damage_on_landing'])for v in (n&65535,(n>>16)&65535)))
 return '\n'.join(lines)+'\n'
