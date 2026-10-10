"""Execute retained common_pain idle/block animation children via real owners."""
from source_animation_ids import configure

def emit(work,sy,*,prefix="CommonPain"):
 if prefix not in ('CommonPain','CommonGrabbed','CommonBlock'):raise ValueError('COMMON_ACTION_FRAME_PREFIX')
 lines=[];serial=0;block=configure([])['authority']['enum']['ANI_BLOCK']
 def put(s):lines.extend(s.strip().splitlines())
 def label(n):put('CommonPainFrame_'+n+':\n.a16\n.i16')
 def branch(op,n='Bad'):
  nonlocal serial
  serial+=1;k='CommonPainFrame_Guard'+str(serial);put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+k+'\n jmp CommonPainFrame_'+n+'\n'+k+':\n.a16\n.i16')
 def require(at,v):put(f' lda.l {at}\n cmp #{v}');branch('bne')
 label('Run');put(' php\n rep #$39\n phx\n phy\n jsl CommonPain_Run');branch('bcs');put(' cmp #0');branch('beq','Good');require(work+2,3)
 put(f' lda.l {work}+6\n cmp #1');branch('beq','IdleRole');put(' cmp #2');branch('bne');require(work+14,block);put(' jmp CommonPainFrame_Begin')
 label('IdleRole');require(work+14,0)
 label('Begin');put(f' lda.l {work}+20');branch('bne','Resume')
 put(f' lda.l {work}+6\n cmp #1');branch('beq','Idle')
 # ent_set_anim ignores an invalid requested block animation. It has no
 # fallback. Resolve the actual cache, then skip frame issuance on absence.
 put(f' lda.l {work}+4\n sta.l {sy["SourceAnimationInit4086_Slot"]}\n lda.l {work}+14\n sta.l {sy["SourceAnimationInit4086_Number"]}\n lda #1\n sta.l {sy["SourceAnimationInit4086_Reset"]}\n jsl {sy["SourceAnimationInit4086_Resolve"]}');branch('bcs')
 put(f' lda.l {sy["SourceAnimationInit4086_Count"]}');branch('beq','Complete');put(f' jsl {sy["SourceAnimationInit4086_Begin"]}');branch('bcs');put(' jmp CommonPainFrame_Capture')
 label('Idle');put(f' lda.l {work}+4\n sta.l {sy["SourceIdle4086_Slot"]}\n jsl {sy["SourceSetIdle4086_Begin"]}');branch('bcs')
 label('Capture')
 for src,dst in ((sy['SourceAnimationInit4086_Handle'],work+20),(sy['SourceAnimationInit4086_Count'],work+22)):put(f' lda.l {src}\n sta.l {dst}')
 label('Resume')
 for src,dst in ((sy['SourceAnimationInit4086_Slot'],work+4),(sy['SourceAnimationInit4086_Number'],work+14),(sy['SourceAnimationInit4086_Handle'],work+20),(sy['SourceAnimationInit4086_Count'],work+22)):
  put(f' lda.l {src}\n cmp.l {dst}');branch('bne')
 put(f' lda.l {sy["SourceAnimationInit4086_State"]}\n cmp #2');branch('beq','Complete');put(' cmp #1');branch('bne')
 put(f' lda.l {sy["SourceAnimationInit4086_Issued"]}\n cmp #1');branch('beq','Frame');put(' cmp #0');branch('bne');put(f' jsl {sy["SourceAnimationInit4086_StartFrame"]}');branch('bcs')
 label('Frame');put(f' jsl {sy["SourceFrameOwner4086_Run"]}');branch('bcs');put(' cmp #0');branch('bne','Ticket')
 put(f' jsl {sy["SourceAnimationInit4086_Ack"]}');branch('bcs');require(sy['SourceAnimationInit4086_State'],2)
 label('Complete');put(f' lda #2\n sta.l {work}+2')
 label('Good');put(' lda #0')
 label('Ticket');put(' ply\n plx\n plp\n clc\n rtl')
 label('Bad');put(f' lda #4\n sta.l {work}+2\n ply\n plx\n plp\n sec\n rtl')
 return ('\n'.join(lines)+'\n').replace('CommonPain_',prefix+'_').replace('CommonPainFrame_',prefix+'Frame_')
