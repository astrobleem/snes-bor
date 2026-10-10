"""Real set_rise child: animation, callback/effects, checked Ack, source flags."""
def emit(work,sy):
 lines=[];serial=0
 def put(s):lines.extend(s.strip().splitlines())
 def label(n):put('SetRiseOwner_'+n+':\n.a16\n.i16')
 def branch(op,n='Bad'):
  nonlocal serial
  serial+=1;l='SetRiseOwner_Guard'+str(serial);put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+l+'\n jmp SetRiseOwner_'+n+'\n'+l+':\n.a16\n.i16')
 label('Run');put(f' php\n rep #$39\n phx\n phy\n jsl {sy["SourceForeignWork_Check"]}');branch('bcs');put(f' lda.l {work}\n cmp #$B6C3');branch('bne')
 put(f' lda.l {work}+2\n cmp #6');branch('beq','Flags');put(' cmp #7');branch('beq','Absent')
 put(' jsl SetRiseBegin_Run');branch('bcs');put(' cmp #0');branch('beq','Absent');put(' cmp #2');branch('beq','Flags');put(' cmp #1');branch('bne')
 put(' jsl SetRiseFrameOwner_Run');branch('bcs');put(' cmp #0');branch('bne','Return')
 put(f' jsl {sy["SourceAnimationInit4086_Ack"]}');branch('bcs');put(' jsl SetRiseBegin_Run');branch('bcs');put(' cmp #2');branch('bne')
 label('Flags');put(' jsl SetRiseFlags_Run');branch('bcs');put(f' lda.l {work}+2\n cmp #6');branch('bne');put(' lda #0\n jmp SetRiseOwner_Return')
 label('Absent');put(f' lda.l {work}+14\n cmp #$FFFF');branch('bne');put(f' lda.l {work}+16\n ora.l {work}+18');branch('bne');put(f' lda #7\n sta.l {work}+2\n lda #0')
 label('Return');put(' ply\n plx\n plp\n clc\n rtl')
 label('Bad');put(f' lda #4\n sta.l {work}+2\n ply\n plx\n plp\n sec\n rtl')
 return '\n'.join(lines)+'\n'
