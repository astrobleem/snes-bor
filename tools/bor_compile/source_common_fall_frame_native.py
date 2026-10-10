"""Tail-call common_fall's doland ticket into the real source frame owner."""

def emit(work):
 text=f'''CommonFallFrame_Run:
.a16
.i16
 php
 rep #$39
 phx
 phy
 lda.l {work}
 cmp #$B6BC
 beq CommonFallFrame_Doland
 cmp #$B6BB
 bne CommonFallFrame_Bad
 jsl CommonFall_Run
 bcs CommonFallFrame_Bad
 cmp #0
 beq CommonFallFrame_Good
 cmp #1
 bne CommonFallFrame_Bad
 lda.l {work}+2
 cmp #1
 bne CommonFallFrame_Bad
 lda.l {work}+6
 cmp #1
 bne CommonFallFrame_Bad
 ; doland is a tail call: common_fall returns immediately after the child.
 ; Its slot, independent generation and time survive this ownership transfer.
 lda #$B6BC
 sta.l {work}
 lda #0
 sta.l {work}+2
 sta.l {work}+6
 sta.l {work}+12
 sta.l {work}+14
 sta.l {work}+20
 sta.l {work}+22
CommonFallFrame_Doland:
.a16
.i16
 jsl CommonDolandFrame_Run
 bcs CommonFallFrame_Bad
 cmp #0
 bne CommonFallFrame_Ticket
 lda #$B6BB
 sta.l {work}
 lda #2
 sta.l {work}+2
 lda #0
 sta.l {work}+6
CommonFallFrame_Good:
.a16
.i16
 lda #0
CommonFallFrame_Ticket:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
CommonFallFrame_Bad:
.a16
.i16
 lda #4
 sta.l {work}+2
 ply
 plx
 plp
 sec
 rtl
'''

 # Keep failure guards valid after future child code grows.
 serial=0;lines=[]
 for line in text.splitlines():
  parts=line.strip().split()
  if len(parts)==2 and parts[0]in ('beq','bne','bcc','bcs'):
   serial+=1;op,target=parts;name='CommonFallFrame_Guard'+str(serial)
   lines.extend([' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+name,' jmp '+target,name+':','.a16','.i16'])
  else:lines.append(line)
 return '\n'.join(lines)+'\n'
