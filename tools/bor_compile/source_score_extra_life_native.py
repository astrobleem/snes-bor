"""Retain actual addscore extra-life ordering over an explicit sound child.

The ASAD child is admitted only for an isolated idle source-audio capability;
concurrent logical source mixing and score scripts remain separate services.
"""


def emit(sy,sample):
 lines=[];serial=0
 def put(s):lines.extend(s.strip().splitlines())
 def label(n):put('ScoreExtraLife_'+n+':\n.a16\n.i16')
 def jump(op,n):
  nonlocal serial
  serial+=1;g='ScoreExtraLife_Guard'+str(serial)
  put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc',bvs='bvc')[op]+f' {g}\n jmp ScoreExtraLife_{n}\n{g}:\n.a16\n.i16')
 def require(a,v):put(f' lda.l {a}\n cmp #{v}');jump('bne','Bad')
 label('Resume');put(' php\n rep #$39\n phx\n phy\n phd\n phb')
 for k,v in(('Ready',0xb631),('Status',1),('StatsReady',0xb633),('NoScriptsReady',0xb632),('ScriptMask',0)):
  require(sy['SourceScore4086_'+k],v)
 put(f' lda.l {sy["SourceScore4086_LifeScore"]}\n ora.l {sy["SourceScore4086_LifeScore"]}+2');jump('beq','Bad')
 put(f' lda.l {sy["SourceScore4086_Player"]}\n cmp #4');jump('bcs','Bad');put(' asl a\n asl a\n tax\n txa\n cmp.l '+str(sy['SourceScore4086_Offset']));jump('bne','Bad')
 for off in(0,2):put(f' lda.l $7FBFA0+{off},x\n cmp.l {sy["SourceScore4086_Old"]}+{off}');jump('bne','Bad')
 label('Loop');put(f' lda.l {sy["SourceScore4086_Next"]}+2\n cmp.l {sy["SourceScore4086_New"]}+2');jump('bcc','Life');jump('bne','Store');put(f' lda.l {sy["SourceScore4086_Next"]}\n cmp.l {sy["SourceScore4086_New"]}');jump('bcs','Store')
 label('Life');put(f' lda.l {sy["SourceScore4086_Offset"]}\n tax\n lda.l $7FBFB2,x\n cmp #$7FFF\n bne ScoreExtraLife_LifeDomain\n lda.l $7FBFB0,x\n cmp #$FFFF');jump('beq','Bad');label('LifeDomain')
 if sample>=0:
  # The source sound child precedes the lives increment. ASAD needs D/DB=0.
  put(' lda #0\n tcd\n sep #$20\n.a8\n pha\n plb\n rep #$30\n.a16\n.i16')
  put(f' lda #{sample}\n jsl {sy["SourceAudio_Start"]}');jump('bcs','SoundRejected')
 label('SoundAccepted');put(f' lda.l {sy["SourceScore4086_Offset"]}\n tax\n lda.l $7FBFB0,x\n clc\n adc #1\n sta.l $7FBFB0,x\n lda.l $7FBFB2,x\n adc #0\n sta.l $7FBFB2,x')
 for off in(0,2):put(f' lda.l {sy["SourceScore4086_Next"]}+{off}'+('\n clc'if off==0 else'')+f'\n adc.l {sy["SourceScore4086_LifeScore"]}+{off}\n sta.l {sy["SourceScore4086_Next"]}+{off}')
 put(' jmp ScoreExtraLife_Loop')
 label('SoundRejected');put(f' lda.l {sy["SourceAudio_Status"]}\n cmp #3');jump('beq','Required');put(' jmp ScoreExtraLife_Bad')
 label('Store');put(f' lda.l {sy["SourceScore4086_Offset"]}\n tax')
 for off in(0,2):put(f' lda.l {sy["SourceScore4086_New"]}+{off}\n sta.l $7FBFA0+{off},x')
 for n,status,carry in(('Good',0,'clc'),('Required',1,'clc'),('Bad',3,'sec')):
  label(n);put(f' lda #{status}\n sta.l {sy["SourceScore4086_Status"]}\n plb\n pld\n ply\n plx\n plp\n {carry}\n rtl')
 return '\n'.join(lines)+'\n'
