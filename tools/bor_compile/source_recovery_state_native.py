"""Persistent source blink/time storage; production lifetime supplied by caller."""
from source_recovery_state_layout import layout

def emit(plan,sy):
 if plan!=layout(plan['entities']):raise ValueError('RECOVERY_STATE_NATIVE_PLAN')
 w=plan['controls'];base=plan['base'];count=plan['entities'];lines=[];serial=0
 def put(s):lines.extend(s.strip().splitlines())
 def label(n):put('RecoveryState_'+n+':\n.a16\n.i16')
 def guard(op,n='Bad'):
  nonlocal serial
  serial+=1;l='RecoveryState_Guard'+str(serial);put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+l+'\n jmp RecoveryState_'+n+'\n'+l+':\n.a16\n.i16')
 for name in ('ClearBirth','Read','Write','ClearBlink'):
  label(name);put(' php\n rep #$39\n pha\n phx\n phy\n txa\n ora 1,s');guard('beq')
  for op,off in (('txa',8),('tya',10)):put(f' {op}\n cmp.l {w}+{off}');guard('bne')
  put(' jsr RecoveryState_Bind');guard('bcs');put(f' lda.l {w}+6\n tax')
  if name!='ClearBirth':put(' jsr RecoveryState_Live');guard('bcs')
  if name=='ClearBirth':
   put(f' lda #0\n sta.l {base},x\n sta.l {base}+2,x\n sta.l {base}+4,x\n sta.l {base}+6,x')
   for off in (8,10):put(f' lda.l {w}+{off}\n sta.l {base}+{off},x')
   put(f' lda #$B6C1\n sta.l {base}+12,x\n lda.l {w}+4\n sta.l {base}+14,x')
  elif name=='ClearBlink':put(f' lda #0\n sta.l {base},x\n sta.l {base}+2,x')
  else:
   for off in range(0,8,2):
    src,dst=(base+off,w+28+off)if name=='Read'else(w+28+off,base+off)
    put(f' lda.l {src}'+(',x'if name=='Read'else'')+f'\n sta.l {dst}'+(',x'if name=='Write'else''))
  put(' jmp RecoveryState_Good')
 label('Bind')
 for at,v in ((w,0xb6c0),(w+16,base&65535),(w+18,0x42),(w+22,count),(sy['VmSourceWorld_Ready'],0xb4a3)):
  put(f' lda.l {at}\n cmp #{v}');guard('bne','LeaseBad')
 put(f' lda.l {w}+20');guard('beq','LeaseBad');put(f' cmp #{plan["chr_capacity"]+1}');guard('bcs','LeaseBad')
 put(f' lda.l {sy["VmSourceWorld_Count"]}');guard('beq','LeaseBad');put(f' cmp #{count+1}');guard('bcs','LeaseBad')
 put(f' lda.l {w}+4\n cmp.l {sy["VmSourceWorld_Count"]}');guard('bcs','LeaseBad');put(f' asl a\n asl a\n asl a\n asl a\n sta.l {w}+6\n clc\n rts')
 label('Live');put(f' lda.l {base}+12,x\n cmp #$B6C1');guard('bne','LeaseBad');put(f' lda.l {base}+14,x\n cmp.l {w}+4');guard('bne','LeaseBad')
 for off in (8,10):put(f' lda.l {base}+{off},x\n cmp.l {w}+{off}');guard('bne','LeaseBad')
 put(' clc\n rts');label('LeaseBad');put(' sec\n rts')
 for name,status,carry in (('Good',2,'clc'),('Bad',3,'sec')):
  label(name);put(f' lda #{status}\n sta.l {w}+2\n ply\n plx\n pla\n plp\n {carry}\n rtl')
 return '\n'.join(lines)+'\n'
