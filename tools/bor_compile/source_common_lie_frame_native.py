"""Retained common_lie rise request with a separate serialized child lease."""
def emit(work,child,sy):
 if work==child:raise ValueError('COMMON_LIE_CHILD_CONTROL_ALIAS')
 lines=[];serial=0
 def put(s):lines.extend(s.strip().splitlines())
 def label(n):put('CommonLieFrame_'+n+':\n.a16\n.i16')
 def branch(op,n='Bad'):
  nonlocal serial
  serial+=1;l='CommonLieFrame_Guard'+str(serial);put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+l+'\n jmp CommonLieFrame_'+n+'\n'+l+':\n.a16\n.i16')
 label('Run');put(' php\n rep #$39\n phx\n phy\n jsl CommonLie_Run');branch('bcs');put(' cmp #0');branch('beq','Good');put(' cmp #1');branch('bne')
 put(f' lda.l {work}+2\n cmp #3');branch('bne');put(f' lda.l {work}+6\n cmp #1');branch('bne');put(f' lda.l {work}+14');branch('bne','Resume')
 # Only the parent control survives the frame; expensive selection is offline.
 # The child uses a different control region already saved by scoped callbacks.
 put(f' lda #$B6C3\n sta.l {child}\n lda #0\n sta.l {child}+2\n sta.l {child}+10\n sta.l {child}+12\n sta.l {child}+14\n sta.l {child}+16\n sta.l {child}+18\n sta.l {child}+20\n sta.l {child}+22\n lda.l {work}+4\n sta.l {child}+4\n lda.l {work}+12\n sta.l {child}+6\n and #$8000')
 branch('beq','PositiveType');put(' lda #$FFFF\n jmp CommonLieFrame_TypeHigh')
 label('PositiveType');put(' lda #0')
 label('TypeHigh');put(f' sta.l {child}+8\n lda #1\n sta.l {work}+14')
 label('Resume');put(f' lda.l {child}+4\n cmp.l {work}+4');branch('bne');put(f' lda.l {work}+8\n tax\n lda.l {work}+10\n tay\n jsl SetRiseOwner_Run');branch('bcs');put(' cmp #0');branch('bne','Return')
 put(f' lda #2\n sta.l {work}+2\n lda #0\n sta.l {work}+6')
 label('Good');put(' lda #0')
 label('Return');put(' ply\n plx\n plp\n clc\n rtl')
 label('Bad');put(f' lda #4\n sta.l {work}+2\n ply\n plx\n plp\n sec\n rtl')
 return '\n'.join(lines)+'\n'
