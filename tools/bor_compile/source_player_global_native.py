"""Checked module-tail player globals; existing score/lives/weapon/time stay canonical."""
from source_player_global_layout import layout

def emit(tail,state,sy):
 p=layout(tail);w=p['controls'];lines=[];serial=0
 def put(s):lines.extend(s.strip().splitlines())
 def label(n):put('PlayerGlobal_'+n+':\n.a16\n.i16')
 def branch(op,n='Bad'):
  nonlocal serial
  serial+=1;g='PlayerGlobal_Guard'+str(serial);put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+g+'\n jmp PlayerGlobal_'+n+'\n'+g+':\n.a16\n.i16')
 def require(at,v):put(f' lda.l {at}\n cmp #{v}');branch('bne')
 def prologue():put(' php\n rep #$39\n phx\n phy')
 def parent():
  require(state,0xb67b);require(state+12,tail['live_slot_count']);require(sy['VmState_SlotCount'],tail['live_slot_count'])
  for off in (0,2):put(f' lda.l {state}+{8+off}\n cmp.l {state}+{14+off}');branch('bne')
  put(f' lda.l {state}+8\n ora.l {state}+10');branch('beq')
 def check():
  require(w,0xb6c6);parent();require(w+16,tail['live_slot_count']);require(w+18,tail['live_slot_count'])
  for off in (0,2):put(f' lda.l {w}+{8+off}\n cmp.l {state}+{8+off}');branch('bne');put(f' cmp.l {w}+{12+off}');branch('bne')
 def idle():
  require(sy['VmState_FrameTop'],0);require(sy['SourceVMRun4086_Busy'],0);put(f' lda.l {sy["VmState_Status"]}\n and #$00FF\n cmp #2');branch('beq');put(' cmp #3');branch('beq')
 label('Init');prologue();require(w,0);parent();idle()
 put(' lda #0\n ldx #0');label('Clear');put(f' sta.l {w},x\n inx\n inx\n cpx #144');branch('bcc','Clear')
 for off in (0,2):put(f' lda.l {state}+{8+off}\n sta.l {w}+{8+off}\n sta.l {w}+{12+off}')
 put(f' lda #{tail["live_slot_count"]}\n sta.l {w}+16\n sta.l {w}+18\n lda #$B6C6\n sta.l {w}\n jmp PlayerGlobal_Good')
 label('Release');prologue();check();idle();put(f' lda #0\n sta.l {w}\n jmp PlayerGlobal_Good')
 for name,write in (('Read',False),('Write',True)):
  label(name);prologue();check();put(f' lda.l {w}+4\n cmp #$FFFF');branch('beq',name+'Global');put(' cmp #4');branch('bcs')
  put(f' lda.l {w}+6\n cmp #5');branch('bcs');put(' asl a\n asl a\n pha');put(f' lda.l {w}+4\n asl a\n asl a\n pha\n asl a\n asl a\n clc\n adc 1,s\n tax\n pla\n txa\n clc\n adc 1,s\n tax\n pla\n txa\n clc\n adc #{p["player_base"]&65535}\n tax\n jmp PlayerGlobal_'+name+'Value')
  label(name+'Global');put(f' lda.l {w}+6\n cmp #6');branch('bcs');put(f' asl a\n asl a\n clc\n adc #{p["global_base"]&65535}\n tax')
  label(name+'Value')
  for off in (0,2):
   if write:put(f' lda.l {w}+{20+off}\n sta.l $7F0000+{off},x')
   else:put(f' lda.l $7F0000+{off},x\n sta.l {w}+{20+off}')
  put(' jmp PlayerGlobal_Good')
 label('Good');put(f' lda #2\n sta.l {w}+2\n ply\n plx\n plp\n clc\n rtl')
 # A replacement module may own these addresses as live VM slots. A failed
 # lease check must not even publish a status into the old tail reservation.
 label('Bad');put(' ply\n plx\n plp\n sec\n rtl')
 return '\n'.join(lines)+'\n'
