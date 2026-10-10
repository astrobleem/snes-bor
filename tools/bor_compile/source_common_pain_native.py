"""Native common_pain prefix; idle/block animation children remain retained debt."""
from source_engine_function_ids import function_id
from source_animation_ids import configure

def emit(work,sy):
 lines=[];serial=0;size=24;block=configure([])['authority']['enum']['ANI_BLOCK']
 def put(s):lines.extend(s.strip().splitlines())
 def label(n):put('CommonPain_'+n+':\n.a16\n.i16')
 def branch(op,n='Bad'):
  nonlocal serial
  serial+=1;k='CommonPain_Guard'+str(serial);put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+k+'\n jmp CommonPain_'+n+'\n'+k+':\n.a16\n.i16')
 def require(at,v):put(f' lda.l {at}\n cmp #{v}');branch('bne')
 label('Run');put(f' php\n rep #$39\n phx\n phy\n phd\n tsc\n sec\n sbc #{size}\n tcs\n inc a\n tcd\n stx $14\n sty $16\n jsl {sy["SourceForeignWork_Check"]}');branch('bcs');require(work,0xb6b8)
 for off,dst in ((8,20),(10,22)):put(f' lda.l {work}+{off}\n cmp ${dst:02X}');branch('bne')
 put(f' lda.l {work}+2\n sta $08');branch('beq','Validate');put(' cmp #3');branch('beq','Validate');put(' cmp #2');branch('bne')
 label('Validate')
 for at,v in ((sy['VmSourceWorld_Ready'],0xb4a3),(sy['VmSourceWorld_PoolBase'],0x4000),(sy['VmSourceWorld_SideBase'],0x6800),(sy['SourceLifecycle4086_Ready'],0xb4fb)):require(at,v)
 for off in (0,2):put(f' lda.l {work}+{16+off}\n cmp.l {sy["VmSourceWorld_Time"]}+{off}');branch('bne')
 put(f' lda.l {sy["VmSourceWorld_Count"]}\n cmp #129');branch('bcs');put(f' lda.l {work}+4\n cmp.l {sy["VmSourceWorld_Count"]}');branch('bcs');put(' sta $00\n asl a\n asl a\n asl a\n asl a\n sta $12\n asl a\n asl a\n sta $04\n clc\n adc $12\n sta $02\n tax\n clc\n adc #$4000\n cmp.l $414000,x');branch('bne');require('$414002,x',0x41);require('$43904A,x',0xb4fb)
 put(' lda $08\n cmp #3');branch('beq','Retained');put(' cmp #2');branch('beq','Good');require('$43900C,x',function_id('common_pain'));require('$43900E,x',0)
 put(' lda $00\n asl a\n asl a\n sta $12\n asl a\n asl a\n clc\n adc $12\n tax\n lda.l $41F510,x');branch('bne','Complete')
 put(' ldx $02');require('$414008,x',2);require('$41400A,x',0)
 for off,n in ((0,'Lo'),(2,'Hi')):put(f' lda.l $41400C+{off},x\n sta.l {sy["SourceModelEntityCopy4086_"+n]}')
 put(' ldx $04')
 for off,n in ((0,'Lo'),(2,'Hi')):put(f' lda.l $416830+{off},x\n sta.l {sy["SourceDefaultPlayer4086_Inv"+n]}')
 put(f' jsl {sy["SourceInAir4086_Q16Compatibility"]}');branch('bcs');put(' cmp #0');branch('bne','Complete')
 # Source order: clear inpain, then linked/block/idle action selection.
 put(' lda $00\n asl a\n asl a\n asl a\n asl a\n asl a\n sta $06\n tax\n lda #0\n sta.l $43EB04,x\n sta.l $43EB06,x\n ldx $04\n lda.l $40901C,x\n ora.l $40901E,x');branch('bne','Linked')
 put(' ldx $06\n lda.l $43EB14,x\n ora.l $43EB16,x');branch('bne','Block')
 put(f' lda #0\n sta.l {work}+12\n sta.l {work}+14\n lda #1\n sta.l {work}+6\n jmp CommonPain_Request')
 label('Block');put(f' lda #{function_id("common_block")}\n sta.l {work}+12\n lda #{block}\n sta.l {work}+14\n lda #2\n sta.l {work}+6')
 label('Request');put(f' ldx $02\n lda.l {work}+12\n sta.l $43900C,x\n lda #0\n sta.l $43900E,x\n lda #3\n sta.l {work}+2')
 label('Retained');put(' lda #1\n jmp CommonPain_Return')
 label('Linked');put(f' ldx $02\n lda #{function_id("common_grabbed")}\n sta.l $43900C,x\n lda #0\n sta.l $43900E,x')
 label('Complete');put(f' lda #2\n sta.l {work}+2')
 label('Good');put(' lda #0')
 label('Return');put(f' tay\n tsc\n clc\n adc #{size}\n tcs\n tya\n pld\n ply\n plx\n plp\n clc\n rtl')
 label('Bad');put(f' lda #4\n sta.l {work}+2\n tsc\n clc\n adc #{size}\n tcs\n pld\n ply\n plx\n plp\n sec\n rtl')
 return '\n'.join(lines)+'\n'
