"""Readonly source count_ents over the admitted 128-slot canonical pool.

A/Y carry the low/high signed32 type mask. Exists and type use literal C
truth semantics; dead/invincibility are deliberately not count predicates.
"""


def emit(sy):
 lines=[];serial=0;size=20
 def put(s):lines.extend(s.strip().splitlines())
 def label(n):put('CountEntities_'+n+':\n.a16\n.i16')
 def guard(op):
  nonlocal serial
  serial+=1;g='CountEntities_Guard'+str(serial)
  put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+f' {g}\n jmp CountEntities_Bad\n{g}:\n.a16\n.i16')
 def require(a,v):put(f' lda.l {a}\n cmp #{v}');guard('bne')
 label('Run');put(f' php\n rep #$39\n phx\n phy\n phd\n pha\n tsc\n sec\n sbc #{size}\n tcs\n inc a\n tcd\n lda ${size:02X}\n sta $00\n tya\n sta $02')
 # PHA is immediately above the allocated local frame (direct-page +size).
 put(f' lda.l {sy["SourceForeignWork_Generation"]}\n tax\n lda.l {sy["SourceForeignWork_Generation"]}+2\n tay\n jsl {sy["SourceForeignWork_Check"]}');guard('bcs')
 require(sy['VmSourceWorld_Ready'],0xb4a3);require(sy['VmSourceWorld_PoolBase'],0x4000)
 put(f' lda.l {sy["VmSourceWorld_Count"]}\n cmp #129');guard('bcs');put(' sta $04\n stz $06\n stz $08\n stz $0A\n stz $0C')
 label('Loop');put(' ldx $08\n lda.l $414004,x\n ora.l $414006,x\n beq CountEntities_Next')
 put(' lda $06\n cmp $04');guard('bcs')
 put(' lda $08\n clc\n adc #$4000\n cmp.l $414000,x');guard('bne');require('$414002,x',0x41)
 put(' ldx $0A\n lda.l $40C048,x\n and $00\n sta $0E\n lda.l $40C04A,x\n and $02\n ora $0E\n beq CountEntities_Next\n inc $0C')
 label('Next');put(' lda $08\n clc\n adc #80\n sta $08\n lda $0A\n clc\n adc #96\n sta $0A\n inc $06\n lda $06\n cmp #128\n bcs CountEntities_Good\n jmp CountEntities_Loop')
 for n,carry in(('Good','clc'),('Bad','sec')):
  label(n);put(f' lda $0C\n tay\n tsc\n clc\n adc #{size+2}\n tcs\n tya\n pld\n ply\n plx\n plp\n {carry}\n rtl')
 return '\n'.join(lines)+'\n'
