"""Common health call from a retained contact, optionally using prepared force."""
from source_current_colourmap import layout


def emit(attacks,work,sy,code_bank=39,*,captured_force=False,common_cursor=2):
 w=layout()['controls'];lines=[];serial=0
 def put(s):lines.extend(s.strip().splitlines())
 def guard(op):
  nonlocal serial
  serial+=1;g='HealthContact_Guard'+str(serial)
  put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+f' {g}\n jmp HealthContact_Bad\n{g}:\n.a16\n.i16')
 def equal(a,b):put(f' lda.l {a}\n cmp.l {b}');guard('bne')
 put('HealthContact_Run:\n.a16\n.i16\n php\n rep #$39\n phx\n phy')
 for a,v in((w+40,0xb6ad),(w+42,2),(w+44,common_cursor)):
  put(f' lda.l {a}\n cmp #{v}');guard('bne')
 for a,b in((w+48,work+4),(w+46,work+6),(w+8,work+8),(w+10,work+10),(w+50,sy['SourceCollisionFrame4086_Attack']),(w+54,sy['SourceCollisionFrame4086_Handle']),(w+52,sy['SourceCollisionFrame4086_Frame'])):equal(a,b)
 if captured_force:
  for a,v in((work+60,0xb6b3),(work+62,0),(work+64,0xb6b2),(work+66,2)):
   put(f' lda.l {a}\n cmp #{v}');guard('bne')
  for off in(0,2):equal(w+12+off,sy['SourceWorldTick4086_TimeLo']+off)
 else:
  # This call is common_takedamage. Player force filtering precedes checkdamage
  # and has a separate owner; reject that callback until it is supplied.
  put(f' lda.l {work}+4\n asl a\n asl a\n asl a\n asl a\n asl a\n pha\n asl a\n clc\n adc 1,s\n tax\n pla\n lda.l $40C048,x\n and #1');guard('bne')
 put(f' lda.l {w}+50\n cmp #1');guard('bcc');put(f' cmp #{len(attacks)+1}');guard('bcs')
 put(' dec a\n asl a\n asl a\n asl a\n tax')
 if captured_force:
  for off in(0,2):
   put(f' lda.l HealthContact_Attacks+{(code_bank<<16)+off},x\n cmp.l {work}+{68+off}');guard('bne')
  for off in(0,2):put(f' lda.l {work}+{80+off}\n sta.l {work}+{12+off}')
  for off,dst in((4,16),(6,18)):put(f' lda.l HealthContact_Attacks+{(code_bank<<16)+off},x\n sta.l {work}+{dst}')
 else:
  for off,dst in((0,12),(2,14),(4,16),(6,18)):put(f' lda.l HealthContact_Attacks+{(code_bank<<16)+off},x\n sta.l {work}+{dst}')
 put(f' lda #$B6B0\n sta.l {work}\n lda 3,s\n tax\n lda 1,s\n tay\n jsl CombatHealth_Run');guard('bcs')
 put(' ply\n plx\n plp\n clc\n rtl\nHealthContact_Bad:\n.a16\n.i16\n ply\n plx\n plp\n sec\n rtl\nHealthContact_Attacks:')
 put(' .dw '+','.join(str(v)for a in attacks for n in('attack_force','no_kill')for v in(a[n]&65535,(a[n]>>16)&65535)))
 return '\n'.join(lines)+'\n'
