"""Pinned player_takedamage's copied attack force, over captured globals.

The producer of the captured healthcheat/level.nohurt values remains separate.
The 96-byte source attack-chain control lease owns this snapshot and result.
"""


def emit(work,sy,*,allow_nonplayer=False,prefix="PlayerDamageForce"):
 lines=[];serial=0;size=16
 def put(s):lines.extend(s.strip().splitlines())
 def label(n):put(prefix+'_'+n+':\n.a16\n.i16')
 def guard(op,n='Bad'):
  nonlocal serial
  serial+=1;g=prefix+'_Guard'+str(serial)
  put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+f' {g}\n jmp {prefix}_{n}\n{g}:\n.a16\n.i16')
 def require(a,v):put(f' lda.l {a}\n cmp #{v}');guard('bne')
 label('Run');put(f' php\n rep #$39\n phx\n phy\n phd\n tsc\n sec\n sbc #{size}\n tcs\n inc a\n tcd')
 put(f' jsl {sy["SourceForeignWork_Check"]}');guard('bcs');require(work+64,0xb6b2)
 for op,off in(('txa',8),('tya',10)):put(f' {op}\n cmp.l {work}+{off}');guard('bne')
 for a,v in((sy['VmSourceWorld_Ready'],0xb4a3),(sy['VmSourceWorld_PoolBase'],0x4000),(sy['SourceWorldTick4086_Ready'],0xb4d5),(sy['SourceWorldTick4086_State'],1),(sy['SourceWorldTick4086_Phase'],8),(sy['SourceWorldTick4086_Pending'],1),(sy['SourceWorldTick4086_Fault'],0),(sy['SourceSelf4086_Ready'],0xb4f6),(sy['SourceSelf4086_Fault'],0),(sy['SourceSelf4086_GlobalHigh'],0x41)):require(a,v)
 for off in(0,2):put(f' lda.l {sy["SourceWorldTick4086_TimeLo"]}+{off}\n cmp.l {sy["VmSourceWorld_Time"]}+{off}');guard('bne')
 put(f' lda.l {sy["VmSourceWorld_Count"]}');guard('beq');put(' cmp #129');guard('bcs')
 for src,off in((0,4),(2,6)):
  put(f' lda.l {work}+{off}\n cmp.l {sy["VmSourceWorld_Count"]}');guard('bcs');put(f' sta ${src:02X}')
  put(' asl a\n asl a\n asl a\n asl a\n sta $04\n asl a\n asl a\n clc\n adc $04\n tax\n clc\n adc #$4000\n cmp.l $414000,x');guard('bne')
  if src==0:put(f' cmp.l {sy["SourceSelf4086_GlobalLow"]}');guard('bne')
  require('$414002,x',0x41)
  put(f' lda ${src:02X}\n asl a\n asl a\n asl a\n asl a\n asl a\n sta $04\n asl a\n clc\n adc $04\n tax\n lda.l $40C048,x')
  if src==0:
   put(' and #1')
   if allow_nonplayer:put(' sta $08')
   else:guard('beq')
  else:put(' and #2\n sta $06')
 if allow_nonplayer:
  require(work+60,0xb6b3);require(work+62,0)
  put(' lda $08');guard('beq','Raw')
 put(f' lda.l {work}+72\n ora.l {work}+74');guard('bne','Zero')
 put(f' lda.l {work}+76\n ora.l {work}+78');guard('beq','Raw');put(' lda $06');guard('bne','Zero')
 label('Raw')
 for off in(0,2):put(f' lda.l {work}+{68+off}\n sta.l {work}+{80+off}')
 put(' jmp '+prefix+'_Good');label('Zero');put(f' lda #0\n sta.l {work}+80\n sta.l {work}+82')
 for n,status,carry in(('Good',2,'clc'),('Bad',3,'sec')):
  label(n);put(f' lda #{status}\n sta.l {work}+66\n tay\n tsc\n clc\n adc #{size}\n tcs\n tya\n pld\n ply\n plx\n plp\n {carry}\n rtl')
 return '\n'.join(lines)+'\n'
