"""Literal ent_unlink over an admitted canonical source actor pool.

A is the physical actor slot; X/Y are the expected canvas generation.
All pointer checks precede actor writes. Source exists/dead are not predicates.
"""


def emit(sy):
 lines=[];serial=0;size=24
 def put(s):lines.extend(s.strip().splitlines())
 def label(n):put('EntUnlink_'+n+':\n.a16\n.i16')
 def guard(op):
  nonlocal serial
  serial+=1;g='EntUnlink_Guard'+str(serial)
  put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+f' {g}\n jmp EntUnlink_Bad\n{g}:\n.a16\n.i16')
 def require(a,v):put(f' lda.l {a}\n cmp #{v}');guard('bne')
 def offsets(slot,rel,core):
  put(f' lda ${slot:02X}\n asl a\n asl a\n asl a\n asl a\n asl a\n sta ${core:02X}\n asl a\n sta ${rel:02X}\n clc\n adc ${core:02X}\n sta ${core:02X}')
 label('Run');put(f' php\n rep #$39\n phx\n phy\n phd\n pha\n tsc\n sec\n sbc #{size}\n tcs\n inc a\n tcd\n lda ${size:02X}\n sta $00')
 put(f' jsl {sy["SourceForeignWork_Check"]}');guard('bcs')
 require(sy['VmSourceWorld_Ready'],0xb4a3);require(sy['VmSourceWorld_PoolBase'],0x4000)
 put(f' lda.l {sy["VmSourceWorld_Count"]}\n cmp #129');guard('bcs');put(' sta $0C\n lda $00\n cmp $0C');guard('bcs')
 offsets(0,2,4)
 put(' lda $02\n lsr a\n lsr a\n clc\n adc $02\n tax\n clc\n adc #$4000\n cmp.l $414000,x');guard('bne');require('$414002,x',0x41)
 put(' ldx $02\n lda.l $40901C,x\n sta $08\n lda.l $40901E,x\n sta $0A\n ora $08\n bne EntUnlink_HasLink\n jmp EntUnlink_Target\nEntUnlink_HasLink:\n.a16\n.i16')
 put(' lda $0A\n cmp #$41');guard('bne');put(' lda $08\n sec\n sbc #$4000');guard('bcc');put(' ldx #0')
 label('Decode');put(' cmp #80\n bcc EntUnlink_Decoded\n sec\n sbc #80\n inx\n cpx #128');guard('bcs');put(' jmp EntUnlink_Decode')
 label('Decoded');put(' cmp #0');guard('bne');put(' txa\n cmp $0C');guard('bcs');put(' cmp $00');guard('beq');put(' sta $06\n lda $08\n tax\n cmp.l $410000,x');guard('bne');require('$410002,x',0x41)
 offsets(6,14,16)
 # Literal source write order: linked actor first, then target. A self-link
 # is rejected: clearing its link makes the subsequent C dereference NULL.
 put(' ldx $0E\n lda #0\n sta.l $40901C,x\n sta.l $40901E,x\n ldx $10\n sta.l $40C050,x\n sta.l $40C052,x')
 label('Target');put(' ldx $02\n lda #0\n sta.l $40901C,x\n sta.l $40901E,x\n ldx $04\n sta.l $40C050,x\n sta.l $40C052,x')
 for n,value,carry in(('Good',0,'clc'),('Bad',3,'sec')):
  label(n);put(f' lda #{value}\n tay\n tsc\n clc\n adc #{size+2}\n tcs\n tya\n pld\n ply\n plx\n plp\n {carry}\n rtl')
 return '\n'.join(lines)+'\n'
