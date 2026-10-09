"""Derive the current damage request from the real retained block/contact state.

No actor writes or acknowledgements. Capture is idempotent within the same
tick/contact; a new request resets the subsequent common-body service cursor.
"""
from source_current_colourmap import layout as colours
from source_hit_state_layout import layout as hits
from source_hit_contact_layout import layout as contacts
from source_hit_block_native import DAMAGE_REQUIRED


def emit(attacks,work,sy,code_bank=39):
 w=colours()['controls'];h=hits()['controls'];hb=hits()['base'];c=contacts()['controls'];lines=[];serial=0
 def put(s):lines.extend(s.strip().splitlines())
 def label(n):put('DamageContactCapture_'+n+':\n.a16\n.i16')
 def branch(op,n='Bad'):
  nonlocal serial
  serial+=1;g='DamageContactCapture_Guard'+str(serial)
  put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+f' {g}\n jmp DamageContactCapture_{n}\n{g}:\n.a16\n.i16')
 def require(a,v):put(f' lda.l {a}\n cmp #{v}');branch('bne')
 label('Run');put(' php\n rep #$39\n phx\n phy')
 put(' jsl HitBlock_Run');branch('bcs');put(f' cmp #{DAMAGE_REQUIRED}');branch('bne')
 require(w,0xb6ab);require(work+60,0xb6b3);require(work+62,0)
 for off in(0,2):put(f' lda.l {w}+{8+off}\n cmp.l {h}+{8+off}');branch('bne')
 # Re-query the actual physical attacker's current descriptor, not a fixture
 # or a model-name lookup. Source block selection is already retained.
 put(f' lda.l {sy["SourceCollisionFrame4086_Status"]}\n cmp #3');branch('beq')
 put(f' lda #0\n sta.l {sy["SourceCollisionFrame4086_Status"]}')
 put(f' lda.l {h}+4\n jsl {sy["SourceCollisionFrame4086_QueryEntity"]}');branch('bcs')
 put(f' lda.l {sy["SourceCollisionFrame4086_Attack"]}\n cmp #1');branch('bcc');put(f' cmp #{len(attacks)+1}');branch('bcs')
 # A valid existing snapshot stays live across child work within this tick.
 put(f' lda.l {work}+64\n cmp #$B6B2');branch('bne','New')
 put(f' lda.l {w}+40\n cmp #$B6AD');branch('bne','New')
 for a,b in((w+46,h+4),(w+48,c+58),(w+50,sy['SourceCollisionFrame4086_Attack']),(w+52,sy['SourceCollisionFrame4086_Frame']),(w+54,sy['SourceCollisionFrame4086_Handle']),(w+12,sy['SourceWorldTick4086_TimeLo']),(w+14,sy['SourceWorldTick4086_TimeHi'])):
  put(f' lda.l {a}\n cmp.l {b}');branch('bne','New')
 put(f' lda.l {h}+4\n asl a\n asl a\n asl a\n asl a\n tax')
 for off in(0,2):put(f' lda.l {hb}+{off},x\n cmp.l {w}+{56+off}');branch('bne','New')
 put(' jmp DamageContactCapture_Good')
 label('New')
 for a,b in((w+4,c+58),(w+48,c+58),(work+4,c+58),(w+46,h+4),(work+6,h+4),(w+50,sy['SourceCollisionFrame4086_Attack']),(w+52,sy['SourceCollisionFrame4086_Frame']),(w+54,sy['SourceCollisionFrame4086_Handle']),(w+12,sy['SourceWorldTick4086_TimeLo']),(w+14,sy['SourceWorldTick4086_TimeHi']),(work+8,h+8),(work+10,h+10)):
  put(f' lda.l {b}\n sta.l {a}')
 put(f' lda.l {h}+4\n asl a\n asl a\n asl a\n asl a\n tax')
 for off in(0,2):put(f' lda.l {hb}+{off},x\n sta.l {w}+{56+off}')
 put(f' lda.l {w}+50\n dec a\n asl a\n asl a\n tax')
 for off in(0,2):put(f' lda.l DamageContactCapture_Forces+{(code_bank<<16)+off},x\n sta.l {work}+{68+off}\n sta.l {work}+{80+off}')
 put(f' lda #0\n sta.l {w}+42\n sta.l {w}+44\n sta.l {work}+66\n lda #$B6AD\n sta.l {w}+40\n lda #$B6B2\n sta.l {work}+64')
 label('Good');put(' ply\n plx\n plp\n clc\n rtl');label('Bad');put(' ply\n plx\n plp\n sec\n rtl')
 label('Forces');put(' .dw '+','.join(str(v)for a in attacks for v in(a['attack_force']&65535,(a['attack_force']>>16)&65535)))
 return '\n'.join(lines)+'\n'
