"""Synchronous suicide through checked source no-event retirement.

Initialized kill/clear callbacks and recursive minion work remain explicit
failures in the underlying retirement contract, never an alive-bit shortcut.
"""
from source_engine_function_ids import function_id

def emit(work,sy):
 lines=[];serial=0
 def put(s):lines.extend(s.strip().splitlines())
 def label(n):put('Suicide_'+n+':\n.a16\n.i16')
 def branch(op,n='Bad'):
  nonlocal serial
  serial+=1;g='Suicide_Guard'+str(serial);put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+g+'\n jmp Suicide_'+n+'\n'+g+':\n.a16\n.i16')
 def require(at,v):put(f' lda.l {at}\n cmp #{v}');branch('bne')
 label('Run');put(f' php\n rep #$39\n phx\n phy\n phd\n tsc\n sec\n sbc #32\n tcs\n inc a\n tcd\n stx $14\n sty $16\n jsl {sy["SourceForeignWork_Check"]}');branch('bcs');require(work,0xb6c5)
 for off,dst in ((8,20),(10,22)):put(f' lda.l {work}+{off}\n cmp ${dst:02X}');branch('bne')
 for at,v in ((sy['VmSourceWorld_Ready'],0xb4a3),(sy['VmSourceWorld_PoolBase'],0x4000),(sy['VmSourceWorld_SideBase'],0x6800),(sy['SourceLifecycle4086_Ready'],0xb4fb)):require(at,v)
 for off in (0,2):put(f' lda.l {work}+{16+off}\n cmp.l {sy["VmSourceWorld_Time"]}+{off}');branch('bne')
 put(f' lda.l {sy["VmSourceWorld_Count"]}\n cmp #129');branch('bcs');put(f' lda.l {work}+4\n cmp.l {sy["VmSourceWorld_Count"]}');branch('bcs');put(' sta $00\n asl a\n asl a\n asl a\n asl a\n sta $0A\n asl a\n asl a\n sta $04\n clc\n adc $0A\n sta $02\n tax\n clc\n adc #$4000\n cmp.l $414000,x');branch('bne');require('$414002,x',0x41);require('$43904A,x',0xb4fb)
 put(f' lda.l {work}+2\n cmp #2');branch('beq','Good');put(' cmp #0');branch('bne');require('$43900C,x',function_id('suicide'));require('$43900E,x',0)
 require(sy['SourceFreeze4086_Ready'],0xb5df);put(' lda $00\n asl a\n asl a\n asl a\n sta $0E\n asl a\n asl a\n clc\n adc $0E\n tax');require('$42E024,x',0xb5df)
 put(f' lda.l {work}+18\n cmp.l $42E00A,x');branch('bcc','Complete');branch('bne','Due');put(f' lda.l {work}+16\n cmp.l $42E008,x');branch('bcc','Complete')
 label('Due')
 for at,v in ((sy['SourceCtorState4086_Ready'],0xb5c2),(sy['SourceScrollerPrefix4086_Ready'],0xb5d7),(sy['SourceSelf4086_Ready'],0xb4f6),(sy['SourceSelf4086_Active'],0),(sy['SourceSelf4086_Fault'],0)):require(at,v)
 put(' ldx $02\n lda.l $414000,x');put(f' cmp.l {sy["SourceSelf4086_GlobalLow"]}');branch('bne');require(sy['SourceSelf4086_GlobalHigh'],0x41)
 put(' ldx $04');require('$43383E,x',0xb5c2);put(' lda.l $416800,x\n ldx $02\n cmp.l $439048,x');branch('bne')
 completed=sy['SourceScrollerPrefix4086_Completed']
 for off,dst in ((0,12),(2,14)):
  put(f' lda.l {completed}+{off}\n cmp.l $43FD9C+{off}');branch('bne');put(f' ldx $04\n ora.l $433838+{off},x\n sta ${dst:02X}')
 put(f' lda.l {work}+4\n sta.l {sy["SourceRetirement4086_Slot"]}\n jsl {sy["SourceRetirement4086_PreflightNoEvents"]}');branch('bcs')
 # All retirement preflight succeeds before source completion publication.
 # Changing completion can only relax a no-event minion condition.
 for off,dst in ((0,12),(2,14)):put(f' lda ${dst:02X}\n sta.l {completed}+{off}\n sta.l $43FD9C+{off}')
 put(f' jsl {sy["SourceRetirement4086_ApplyNoEvents"]}');branch('bcs');require(sy['SourceRetirement4086_Status'],2)
 label('Complete');put(f' lda #2\n sta.l {work}+2')
 label('Good');put(' lda #0\n tay\n tsc\n clc\n adc #32\n tcs\n tya\n pld\n ply\n plx\n plp\n clc\n rtl')
 label('Bad');put(f' lda #4\n sta.l {work}+2\n lda #3\n sta.l {sy["SourceRetirement4086_Status"]}\n tsc\n clc\n adc #32\n tcs\n pld\n ply\n plx\n plp\n sec\n rtl')
 return '\n'.join(lines)+'\n'
