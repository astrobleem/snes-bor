"""Generation-bound common_grabbed action and retained real idle request."""
from source_engine_function_ids import function_id

def emit(work,sy,*,kind='common_grabbed',requirements=None):
 if kind not in ('common_grabbed','common_block'):raise ValueError('COMMON_ACTION_PREFIX_KIND')
 if kind=='common_block'and(not requirements or not requirements['closed_zero_policy']):raise ValueError('COMMON_BLOCK_HOLDBLOCK_CAPABILITY_REQUIRED')
 if kind=='common_block'and not all(m['id']==i and m['holdblock']==0 and not m['declarations']for i,m in enumerate(requirements['models'])):raise ValueError('COMMON_BLOCK_CLOSED_MODEL_IDENTITY')
 lines=[];serial=0;size=24
 def put(s):lines.extend(s.strip().splitlines())
 def label(n):put('CommonGrabbed_'+n+':\n.a16\n.i16')
 def branch(op,n='Bad'):
  nonlocal serial
  serial+=1;k='CommonGrabbed_Guard'+str(serial);put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+k+'\n jmp CommonGrabbed_'+n+'\n'+k+':\n.a16\n.i16')
 def require(at,v):put(f' lda.l {at}\n cmp #{v}');branch('bne')
 label('Run');put(f' php\n rep #$39\n phx\n phy\n phd\n tsc\n sec\n sbc #{size}\n tcs\n inc a\n tcd\n stx $14\n sty $16\n jsl {sy["SourceForeignWork_Check"]}');branch('bcs');require(work,0xb6b9 if kind=='common_grabbed'else 0xb6ba)
 for off,dst in ((8,20),(10,22)):put(f' lda.l {work}+{off}\n cmp ${dst:02X}');branch('bne')
 put(f' lda.l {work}+2\n sta $08');branch('beq','Validate');put(' cmp #3');branch('beq','Validate');put(' cmp #2');branch('bne')
 label('Validate')
 for at,v in ((sy['VmSourceWorld_Ready'],0xb4a3),(sy['VmSourceWorld_PoolBase'],0x4000),(sy['VmSourceWorld_SideBase'],0x6800),(sy['SourceLifecycle4086_Ready'],0xb4fb)):require(at,v)
 for off in (0,2):put(f' lda.l {work}+{16+off}\n cmp.l {sy["VmSourceWorld_Time"]}+{off}');branch('bne')
 put(f' lda.l {sy["VmSourceWorld_Count"]}\n cmp #129');branch('bcs');put(f' lda.l {work}+4\n cmp.l {sy["VmSourceWorld_Count"]}');branch('bcs');put(' sta $00\n asl a\n asl a\n asl a\n asl a\n sta $12\n asl a\n asl a\n sta $04\n clc\n adc $12\n sta $02\n tax\n clc\n adc #$4000\n cmp.l $414000,x');branch('bne');require('$414002,x',0x41);require('$43904A,x',0xb4fb)
 put(' lda $08\n cmp #3');branch('beq','Retained');put(' cmp #2');branch('beq','Good');require('$43900C,x',function_id(kind));require('$43900E,x',0)
 # Source short-circuits on link before touching stalltime or starting idle.
 if kind=='common_grabbed':
  put(' ldx $04\n lda.l $40901C,x\n ora.l $40901E,x');branch('bne','Complete')
  require(sy['SourceFreeze4086_Ready'],0xb5df)
  put(' lda $00\n asl a\n asl a\n asl a\n sta $12\n asl a\n asl a\n clc\n adc $12\n tax');require('$42E024,x',0xb5df)
  put(' lda #0\n sta.l $42E008,x\n sta.l $42E00A,x')
 else:
  put(' ldx $04\n lda.l $416800,x');put(f' cmp #{len(requirements["models"])}');branch('bcs');put(' ldx $02\n cmp.l $439048,x');branch('bne')
  put(' lda $00\n asl a\n asl a\n sta $12\n asl a\n asl a\n clc\n adc $12\n tax\n lda.l $41F510,x');branch('bne','Complete')
  put(' lda $00\n asl a\n asl a\n asl a\n asl a\n asl a\n tax\n lda #0\n sta.l $43EB14,x\n sta.l $43EB16,x')
 put(f' lda #0\n sta.l {work}+12\n sta.l {work}+14\n ldx $02\n sta.l $43900C,x\n sta.l $43900E,x\n lda #1\n sta.l {work}+6\n lda #3\n sta.l {work}+2')
 label('Retained');put(' lda #1\n jmp CommonGrabbed_Return')
 label('Complete');put(f' lda #2\n sta.l {work}+2')
 label('Good');put(' lda #0')
 label('Return');put(f' tay\n tsc\n clc\n adc #{size}\n tcs\n tya\n pld\n ply\n plx\n plp\n clc\n rtl')
 label('Bad');put(f' lda #4\n sta.l {work}+2\n tsc\n clc\n adc #{size}\n tcs\n pld\n ply\n plx\n plp\n sec\n rtl')
 return ('\n'.join(lines)+'\n').replace('CommonGrabbed_','CommonBlock_'if kind=='common_block'else'CommonGrabbed_')
